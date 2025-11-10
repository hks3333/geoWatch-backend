"""Utilities for interacting with Google Earth Engine using Sentinel-2 data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import ee

logger = logging.getLogger(__name__)

_EE_INITIALIZED = False

# Thresholds for classification
FOREST_NDVI_THRESHOLD = 0.35  # NDVI > 0.4 indicates vegetation/forest
WATER_MNDWI_THRESHOLD = 0.3  # MNDWI > 0.3 indicates water

# Sentinel-2 collection
S2_COLLECTION = 'COPERNICUS/S2_SR_HARMONIZED'


def initialize_earth_engine(gcp_project_id: str) -> bool:
    """Initialise the Earth Engine client using Application Default Credentials."""

    global _EE_INITIALIZED
    if _EE_INITIALIZED:
        return True

    try:
        logger.info("Initialising Earth Engine for project %s", gcp_project_id)
        ee.Initialize(project=gcp_project_id)
        _EE_INITIALIZED = True
        return True
    except Exception as exc:  # pragma: no cover - relies on EE credentials at runtime
        logger.exception("Failed to initialise Earth Engine: %s", exc)
        return False


def _build_geometry(polygon: List[List[float]]) -> ee.Geometry:
    """Return an EE geometry from a list of [lng, lat] vertices."""

    if not polygon:
        raise ValueError("Polygon must contain coordinates")

    ring = list(polygon)
    if ring[0] != ring[-1]:
        ring.append(ring[0])
    return ee.Geometry.Polygon([ring])


def _mask_s2_clouds(image: ee.Image) -> ee.Image:
    """
    Mask clouds using Sentinel-2 SCL (Scene Classification Layer) band.
    Removes: Cloud Shadow (3), Cloud Medium (8), Cloud High (9), Cirrus (10)
    """
    scl = image.select('SCL')
    # Bad pixels: cloud shadow, clouds, cirrus
    bad_pixels = scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10))
    # Good pixels mask
    good_pixels_mask = bad_pixels.Not()
    return image.updateMask(good_pixels_mask)


def _calculate_cloud_coverage(image: ee.Image, geometry: ee.Geometry) -> float:
    """
    Calculate percentage of cloud coverage in the image.
    Uses SCL (Scene Classification Layer) band:
    - 3: Cloud shadow
    - 8: Cloud medium probability
    - 9: Cloud high probability
    - 10: Thin cirrus
    """
    scl = image.select('SCL')
    # Pixels with clouds or cloud shadows - rename to 'clouds' for reduction
    cloud_pixels = scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10)).rename('clouds')
    
    # Count total valid pixels (not no-data)
    total_pixels = image.select('B2').mask().reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=geometry,
        scale=10,
        maxPixels=1e13
    ).get('B2')
    
    # Count cloud pixels
    cloud_pixel_count = cloud_pixels.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=10,
        maxPixels=1e13
    ).get('clouds')
    
    total = ee.Number(total_pixels).getInfo()
    clouds = ee.Number(cloud_pixel_count).getInfo() or 0
    
    if total is None or total == 0:
        return 0.0
    
    coverage = (clouds / total) * 100.0
    # Cloud coverage should never exceed 100%
    return min(coverage, 100.0)


def _create_monthly_composite(
    geometry: ee.Geometry, start: datetime, end: datetime
) -> Tuple[Optional[ee.Image], Optional[str]]:
    """
    Create a median composite from all Sentinel-2 images in a date range.
    This is more robust than selecting a single image, as it reduces noise and clouds.
    
    Returns: (composite_image, period_string) or (None, None) if no images found.
    """
    collection = (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(geometry)
        .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        .map(_mask_s2_clouds)  # Apply cloud masking to each image
    )

    try:
        count = collection.size().getInfo()
    except Exception as exc:
        logger.exception("Failed to inspect Sentinel-2 collection: %s", exc)
        raise

    if count == 0:
        logger.warning(
            "No Sentinel-2 images found in date range %s to %s",
            start.date(),
            end.date(),
        )
        return None, None

    logger.info(
        "Found %d Sentinel-2 images in range %s to %s; creating median composite",
        count,
        start.date(),
        end.date(),
    )

    # Create a median composite from all cloud-masked images
    # This is much more robust than selecting a single image
    composite = collection.median()
    
    # Select only the bands we need: B2, B3, B4, B8, B11
    # (SCL is not needed after cloud masking)
    # B2=Blue, B3=Green, B4=Red, B8=NIR, B11=SWIR
    composite = composite.select(['B2', 'B3', 'B4', 'B8', 'B11']).clip(geometry)
    
    # Use the end date as the composite date
    period_string = end.strftime('%Y-%m-%d')

    return composite, period_string


def _fetch_sentinel2_images(
    polygon: List[List[float]], classification_type: str
) -> Tuple[ee.Image, ee.Image, ee.Geometry, str, str]:
    """
    Retrieve baseline and current Sentinel-2 monthly composites for the region.
    
    Strategy for robust monthly monitoring:
    - Current Period: The entire previous full month (e.g., October 1-31)
    - Baseline Period: The entire month before that (e.g., September 1-30)
    - For each period: Create a median composite from ALL cloud-masked images
    
    This approach is much more robust than single-image selection because:
    - Median composites reduce noise and weather artifacts
    - Comparing whole months to whole months is apples-to-apples
    - You detect real land change, not daily weather variations
    
    Returns: (baseline_composite, current_composite, geometry, baseline_period, current_period)
    """
    geometry = _build_geometry(polygon)

    now = datetime.utcnow()
    
    # Determine the previous full month
    # If today is Nov 10, we want Oct 1-31 as current, Sep 1-30 as baseline
    first_of_this_month = now.replace(day=1)
    last_of_prev_month = first_of_this_month - timedelta(days=1)
    first_of_prev_month = last_of_prev_month.replace(day=1)
    
    first_of_baseline_month = (first_of_prev_month - timedelta(days=1)).replace(day=1)
    last_of_baseline_month = first_of_prev_month - timedelta(days=1)
    
    # Current period: entire previous month
    current_start = first_of_prev_month
    current_end = last_of_prev_month
    
    # Baseline period: entire month before that
    baseline_start = first_of_baseline_month
    baseline_end = last_of_baseline_month
    
    logger.info(
        "Creating monthly composites - Baseline: %s to %s, Current: %s to %s",
        baseline_start.strftime('%Y-%m-%d'),
        baseline_end.strftime('%Y-%m-%d'),
        current_start.strftime('%Y-%m-%d'),
        current_end.strftime('%Y-%m-%d'),
    )
    
    # Create current month composite
    current_image, current_date = _create_monthly_composite(geometry, current_start, current_end)
    if current_image is None:
        raise RuntimeError(f"No Sentinel-2 data available for current period ({current_start.strftime('%Y-%m-%d')} to {current_end.strftime('%Y-%m-%d')})")

    # Create baseline month composite
    baseline_image, baseline_date = _create_monthly_composite(geometry, baseline_start, baseline_end)
    if baseline_image is None:
        raise RuntimeError(f"No Sentinel-2 data available for baseline period ({baseline_start.strftime('%Y-%m-%d')} to {baseline_end.strftime('%Y-%m-%d')})")

    logger.info(
        "Created monthly composites (baseline: %s, current: %s)",
        baseline_date,
        current_date,
    )

    return baseline_image, current_image, geometry, baseline_date, current_date


def _add_indices(image: ee.Image) -> ee.Image:
    """
    Add NDVI and MNDWI bands to the image.
    NDVI = (NIR - Red) / (NIR + Red) = (B8 - B4) / (B8 + B4)
    MNDWI = (Green - SWIR) / (Green + SWIR) = (B3 - B11) / (B3 + B11)
    """
    ndvi = image.normalizedDifference(['B8', 'B4']).rename('NDVI')
    mndwi = image.normalizedDifference(['B3', 'B11']).rename('MNDWI')
    return image.addBands(ndvi).addBands(mndwi)


def _create_classification_mask(
    image: ee.Image, classification_type: str
) -> ee.Image:
    """
    Create binary mask for forest or water based on indices.
    """
    if classification_type == 'forest':
        # Forest: NDVI > threshold
        mask = image.select('NDVI').gt(FOREST_NDVI_THRESHOLD)
    elif classification_type == 'water':
        # Water: MNDWI > threshold
        mask = image.select('MNDWI').gt(WATER_MNDWI_THRESHOLD)
    else:
        raise ValueError(f"Unsupported classification type: {classification_type}")
    
    return mask.rename('classification')


def compute_change_products(
    geometry: ee.Geometry,
    baseline_image: ee.Image,
    current_image: ee.Image,
    classification_type: str,
    baseline_date: str,
    current_date: str,
    scale: int = 10,
) -> Dict:
    """
    Compute change detection from monthly composites.
    Note: Images are already cloud-masked and composited, so no additional masking needed.
    Returns dict with metrics and image objects for export.
    """
    logger.info(
        "Processing monthly composites (baseline: %s, current: %s)",
        baseline_date,
        current_date
    )
    
    # Images are already cloud-masked from the composite creation, so use them directly
    baseline_masked = baseline_image
    current_masked = current_image
    
    # For composites, cloud coverage is minimal (already masked), but report 0 for clarity
    baseline_cloud_coverage = 0.0
    current_cloud_coverage = 0.0
    
    # Add indices (NDVI, MNDWI)
    baseline_with_indices = _add_indices(baseline_masked)
    current_with_indices = _add_indices(current_masked)
    
    # Create classification masks
    baseline_class = _create_classification_mask(baseline_with_indices, classification_type)
    current_class = _create_classification_mask(current_with_indices, classification_type)
    
    # Create combined cloud-free mask (pixels valid in both images)
    combined_cloud_mask = baseline_masked.select('B2').mask().And(current_masked.select('B2').mask())
    
    # Calculate total pixels in area (reference: all pixels in geometry)
    total_pixels = baseline_masked.select('B2').reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13
    ).get('B2')
    
    # Calculate cloud-free pixels (pixels valid in both baseline and current)
    cloud_free_pixels = combined_cloud_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13
    ).get('B2')
    
    total_px = ee.Number(total_pixels).getInfo() or 0
    cloud_free_px = ee.Number(cloud_free_pixels).getInfo() or 0
    
    # Cloud-free percentage should never exceed 100%
    cloud_free_percentage = min((cloud_free_px / total_px) * 100.0 if total_px > 0 else 0.0, 100.0)
    
    logger.info("Cloud-free pixels (available for analysis): %.2f%% (%d/%d pixels)", cloud_free_percentage, int(cloud_free_px), int(total_px))
    
    # Create combined mask with classification (cloud-free AND meets classification criteria)
    combined_mask = combined_cloud_mask.And(baseline_class.mask()).And(current_class.mask())
    
    # Calculate pixels that meet classification criteria
    classified_pixels = combined_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13
    ).get('B2')
    
    classified_px = ee.Number(classified_pixels).getInfo()
    valid_pixels_percentage = (classified_px / total_px) * 100.0 if total_px > 0 else 0.0
    
    logger.info("Valid pixels (cloud-free AND classified as %s): %.2f%%", classification_type, valid_pixels_percentage)
    
    # Apply combined mask to classifications
    baseline_class_masked = baseline_class.updateMask(combined_mask)
    current_class_masked = current_class.updateMask(combined_mask)
    
    # Compute change: loss, gain, stable
    # Loss: was classified in baseline, not in current (1 -> 0)
    loss = baseline_class_masked.eq(1).And(current_class_masked.eq(0)).rename('loss')
    # Gain: not classified in baseline, is classified in current (0 -> 1)
    gain = baseline_class_masked.eq(0).And(current_class_masked.eq(1)).rename('gain')
    # Stable: classified in both baseline and current (1 -> 1)
    stable = baseline_class_masked.eq(1).And(current_class_masked.eq(1)).rename('stable')
    
    logger.debug("Change detection masks created: loss, gain, stable")
    
    # Calculate areas
    pixel_area_ha = ee.Image.pixelArea().divide(10000).rename('hectares')
    
    def sum_hectares(mask: ee.Image) -> float:
        result = (
            pixel_area_ha.updateMask(mask)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=scale,
                maxPixels=1e13,
            )
            .get('hectares')
        )
        if result is None:
            return 0.0
        return float(ee.Number(result).getInfo())
    
    loss_hectares = sum_hectares(loss)
    gain_hectares = sum_hectares(gain)
    stable_hectares = sum_hectares(stable)
    total_hectares = loss_hectares + gain_hectares + stable_hectares
    
    if total_hectares < 1e-6:
        total_hectares = 1e-6  # Avoid division by zero
    
    loss_percentage = (loss_hectares / total_hectares) * 100.0
    gain_percentage = (gain_hectares / total_hectares) * 100.0
    net_change_percentage = gain_percentage - loss_percentage
    
    # Create visualization image (RGB: Red=Loss, Green=Stable, Blue=Gain)
    visualization = ee.Image.cat(
        loss.multiply(255).unmask(0).rename('R'),
        stable.multiply(255).unmask(0).rename('G'),
        gain.multiply(255).unmask(0).rename('B')
    ).uint8().clip(geometry)
    
    # Prepare images for export (with Web Mercator projection for Leaflet)
    # Only keep essential bands to save space
    baseline_export = baseline_masked.select(['B4', 'B3', 'B2']).clip(geometry)  # RGB
    current_export = current_masked.select(['B4', 'B3', 'B2']).clip(geometry)  # RGB
    
    # Computed masks (single band, 0 or 1)
    baseline_computed = baseline_class_masked.unmask(0).uint8().clip(geometry)
    current_computed = current_class_masked.unmask(0).uint8().clip(geometry)
    
    # Get bounds for Leaflet
    bounds_info = geometry.bounds().getInfo()
    coords = bounds_info['coordinates'][0]
    # Extract [west, south, east, north]
    lons = [c[0] for c in coords]
    lats = [c[1] for c in coords]
    bounds = [min(lons), min(lats), max(lons), max(lats)]
    
    return {
        'metrics': {
            'analysis_type': classification_type,
            'baseline_date': baseline_date,
            'current_date': current_date,
            'baseline_cloud_coverage': baseline_cloud_coverage,
            'current_cloud_coverage': current_cloud_coverage,
            'valid_pixels_percentage': valid_pixels_percentage,
            'loss_hectares': loss_hectares,
            'gain_hectares': gain_hectares,
            'stable_hectares': stable_hectares,
            'total_hectares': total_hectares,
            'loss_percentage': loss_percentage,
            'gain_percentage': gain_percentage,
            'net_change_percentage': net_change_percentage,
        },
        'images': {
            'baseline_image': baseline_export,
            'current_image': current_export,
            'baseline_computed': baseline_computed,
            'current_computed': current_computed,
            'difference_image': visualization,
        },
        'bounds': bounds,
        'geometry': geometry,
    }
