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
    """
    scl = image.select('SCL')
    bad_pixels = scl.eq(3).Or(scl.eq(8)).Or(scl.eq(9)).Or(scl.eq(10))
    
    # Count total pixels
    total_pixels = ee.Image.constant(1).reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=geometry,
        scale=10,
        maxPixels=1e13
    ).get('constant')
    
    # Count bad pixels
    bad_pixel_count = bad_pixels.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=10,
        maxPixels=1e13
    ).get('SCL')
    
    total = ee.Number(total_pixels).getInfo()
    bad = ee.Number(bad_pixel_count).getInfo()
    
    if total == 0:
        return 0.0
    
    return (bad / total) * 100.0


def _fetch_sentinel2_image(
    geometry: ee.Geometry, start: datetime, end: datetime
) -> Tuple[Optional[ee.Image], Optional[str]]:
    """
    Fetch the best Sentinel-2 image for the supplied window.
    Returns (image, date_string) or (None, None) if no image found.
    """
    collection = (
        ee.ImageCollection(S2_COLLECTION)
        .filterBounds(geometry)
        .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        .sort('CLOUDY_PIXEL_PERCENTAGE')
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
        "Found %d Sentinel-2 images in range %s to %s; selecting least cloudy",
        count,
        start.date(),
        end.date(),
    )

    # Get the least cloudy image
    image = collection.first()
    
    # Get the date of this image
    date_millis = ee.Number(image.get('system:time_start')).getInfo()
    image_date = datetime.fromtimestamp(date_millis / 1000).strftime('%Y-%m-%d')
    
    # Select only the bands we need: B2, B3, B4, B8, B11, SCL
    # B2=Blue, B3=Green, B4=Red, B8=NIR, B11=SWIR, SCL=Scene Classification
    image = image.select(['B2', 'B3', 'B4', 'B8', 'B11', 'SCL']).clip(geometry)

    return image, image_date


def fetch_sentinel2_images(
    polygon: List[List[float]],
    is_baseline: bool,
) -> Tuple[ee.Image, ee.Image, ee.Geometry, str, str]:
    """
    Retrieve baseline and current Sentinel-2 images for the region.
    
    Strategy:
    - Current image: Latest available in last 60 days
    - Baseline image: ~30 days before current image (±10 days window)
    
    Re-analysis behavior:
    - If triggered again, will fetch the LATEST image (last 60 days)
    - If no new Sentinel-2 pass occurred, will get the same image as before
    - Baseline is always calculated as 30 days before the current image
    - This means: If same current image, baseline will also be the same
    - Result: No change detected (which is correct - no new data available)
    
    Returns: (baseline_image, current_image, geometry, baseline_date, current_date)
    """
    geometry = _build_geometry(polygon)

    now = datetime.utcnow()
    
    # Current image: latest available (search last 60 days)
    current_end = now
    current_start = now - timedelta(days=60)

    current_image, current_date = _fetch_sentinel2_image(geometry, current_start, current_end)
    if current_image is None:
        raise RuntimeError("No Sentinel-2 data available for current window")

    # Baseline image: ~1 month before current (±10 days window)
    # Note: For both first and subsequent analyses, we use the same logic
    # This ensures consistent comparison windows
    baseline_center = datetime.strptime(current_date, '%Y-%m-%d') - timedelta(days=30)
    
    baseline_start = baseline_center - timedelta(days=10)
    baseline_end = baseline_center + timedelta(days=10)

    baseline_image, baseline_date = _fetch_sentinel2_image(geometry, baseline_start, baseline_end)
    if baseline_image is None:
        raise RuntimeError("No Sentinel-2 data available for baseline window")

    logger.info(
        "Fetched Sentinel-2 images (baseline: %s, current: %s)",
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
    Compute change detection with cloud masking.
    Returns dict with metrics and image objects for export.
    """
    # Calculate cloud coverage before masking
    baseline_cloud_coverage = _calculate_cloud_coverage(baseline_image, geometry)
    current_cloud_coverage = _calculate_cloud_coverage(current_image, geometry)
    
    logger.info(
        "Cloud coverage - Baseline: %.2f%%, Current: %.2f%%",
        baseline_cloud_coverage,
        current_cloud_coverage
    )
    
    # Apply cloud masking
    baseline_masked = _mask_s2_clouds(baseline_image)
    current_masked = _mask_s2_clouds(current_image)
    
    # Add indices (NDVI, MNDWI)
    baseline_with_indices = _add_indices(baseline_masked)
    current_with_indices = _add_indices(current_masked)
    
    # Create classification masks
    baseline_class = _create_classification_mask(baseline_with_indices, classification_type)
    current_class = _create_classification_mask(current_with_indices, classification_type)
    
    # Create combined cloud-free mask (pixels valid in both images)
    combined_cloud_mask = baseline_masked.select('B2').mask().And(current_masked.select('B2').mask())
    
    # Calculate total pixels in area
    total_pixels = ee.Image.constant(1).reduceRegion(
        reducer=ee.Reducer.count(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13
    ).get('constant')
    
    # Calculate cloud-free pixels
    cloud_free_pixels = combined_cloud_mask.reduceRegion(
        reducer=ee.Reducer.sum(),
        geometry=geometry,
        scale=scale,
        maxPixels=1e13
    ).get('B2')
    
    total_px = ee.Number(total_pixels).getInfo()
    cloud_free_px = ee.Number(cloud_free_pixels).getInfo()
    cloud_free_percentage = (cloud_free_px / total_px) * 100.0 if total_px > 0 else 0.0
    
    logger.info("Cloud-free pixels (available for analysis): %.2f%%", cloud_free_percentage)
    
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
    loss = baseline_class_masked.eq(1).And(current_class_masked.eq(0)).rename('loss')
    gain = baseline_class_masked.eq(0).And(current_class_masked.eq(1)).rename('gain')
    stable = baseline_class_masked.eq(1).And(current_class_masked.eq(1)).rename('stable')
    
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
