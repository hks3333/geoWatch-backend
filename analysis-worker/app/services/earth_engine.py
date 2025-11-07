"""Utilities for interacting with Google Earth Engine using Dynamic World data."""

from __future__ import annotations

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import ee

logger = logging.getLogger(__name__)

_EE_INITIALIZED = False
CLASS_VALUE_MAP = {
    "forest": 1,
    "water": 0,
}


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


def _collect_dynamic_world(
    geometry: ee.Geometry, start: datetime, end: datetime
) -> Optional[ee.Image]:
    """Fetch a Dynamic World composite for the supplied window."""

    collection = (
        ee.ImageCollection("GOOGLE/DYNAMICWORLD/V1")
        .filterBounds(geometry)
        .filterDate(start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"))
        .select("label")
    )

    try:
        count = collection.size().getInfo()
    except Exception as exc:  # pragma: no cover - depends on EE API
        logger.exception("Failed to inspect Dynamic World collection: %s", exc)
        raise

    if count == 0:
        logger.warning(
            "No Dynamic World images found in date range %s to %s",
            start.date(),
            end.date(),
        )
        return None

    logger.info(
        "Found %d Dynamic World images in range %s to %s; computing mode composite",
        count,
        start.date(),
        end.date(),
    )

    image = collection.mode().clip(geometry)

    try:
        image = image.reproject(image.projection(), None, 10)
    except Exception as exc:  # pragma: no cover - depends on EE runtime
        logger.warning(
            "Falling back to EPSG:3857 reprojection at 10 m due to: %s",
            exc,
        )
        image = image.reproject(ee.Projection("EPSG:3857"), None, 10)

    return image


def fetch_dynamic_world_images(
    polygon: List[List[float]],
    is_baseline: bool,
) -> Tuple[ee.Image, ee.Image, ee.Geometry]:
    """Retrieve baseline and current Dynamic World composites for the region."""

    geometry = _build_geometry(polygon)

    now = datetime.utcnow()
    current_end = now
    current_start = now - timedelta(days=30)

    if is_baseline:
        baseline_end = current_end - timedelta(days=365)
        baseline_start = baseline_end - timedelta(days=30)
    else:
        baseline_end = current_end - timedelta(days=365)
        baseline_start = baseline_end - timedelta(days=30)

    current_image = _collect_dynamic_world(geometry, current_start, current_end)
    if current_image is None:
        raise RuntimeError("No Dynamic World data available for current window")

    baseline_image = _collect_dynamic_world(geometry, baseline_start, baseline_end)
    if baseline_image is None:
        raise RuntimeError("No Dynamic World data available for baseline window")

    logger.info(
        "Fetched Dynamic World composites (baseline window: %s → %s, current window: %s → %s)",
        baseline_start.date(),
        baseline_end.date(),
        current_start.date(),
        current_end.date(),
    )

    return baseline_image, current_image, geometry


def compute_change_products(
    geometry: ee.Geometry,
    baseline_image: ee.Image,
    current_image: ee.Image,
    classification_type: str,
    scale: int = 10,
) -> Tuple[Dict[str, float], str]:
    """Compute change metrics and return (metrics, visualization PNG URL)."""

    if classification_type not in CLASS_VALUE_MAP:
        raise ValueError(f"Unsupported classification type: {classification_type}")

    class_value = CLASS_VALUE_MAP[classification_type]

    baseline_mask = baseline_image.eq(class_value).selfMask().rename("baseline")
    current_mask = current_image.eq(class_value).selfMask().rename("current")

    loss = baseline_mask.And(current_mask.Not()).rename("loss")
    gain = baseline_mask.Not().And(current_mask).rename("gain")
    stable = baseline_mask.And(current_mask).rename("stable")
    total = baseline_mask.Or(current_mask).rename("total")

    pixel_area_ha = ee.Image.pixelArea().divide(10000).rename("hectares")

    def sum_hectares(mask: ee.Image) -> float:
        result = (
            pixel_area_ha.updateMask(mask)
            .reduceRegion(
                reducer=ee.Reducer.sum(),
                geometry=geometry,
                scale=scale,
                maxPixels=1e13,
            )
            .get("hectares")
        )
        if result is None:
            return 0.0
        return float(ee.Number(result).getInfo())

    loss_hectares = sum_hectares(loss)
    gain_hectares = sum_hectares(gain)
    stable_hectares = sum_hectares(stable)
    total_hectares = max(sum_hectares(total), 1e-6)

    loss_percentage = (loss_hectares / total_hectares) * 100.0
    gain_percentage = (gain_hectares / total_hectares) * 100.0
    net_change_percentage = gain_percentage - loss_percentage

    visualization = (
        ee.Image.cat(
            loss.multiply(255).rename("R"),
            stable.multiply(255).rename("G"),
            gain.multiply(255).rename("B"),
        )
        .uint8()
        .clip(geometry)
    )

    thumb_params = {
        "region": geometry,
        "dimensions": 768,
        "format": "png",
    }
    png_url = visualization.getThumbURL(thumb_params)

    metrics = {
        "loss_hectares": loss_hectares,
        "gain_hectares": gain_hectares,
        "stable_hectares": stable_hectares,
        "total_hectares": total_hectares,
        "loss_percentage": loss_percentage,
        "gain_percentage": gain_percentage,
        "net_change_percentage": net_change_percentage,
    }

    return metrics, png_url
