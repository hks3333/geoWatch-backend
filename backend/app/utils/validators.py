"""
This module provides utility functions for validating various aspects of
monitoring area data, such as geographical size constraints.
"""

from geopy.distance import geodesic
from app.models.monitoring_area import RectangleBounds


def validate_area_size(bounds: RectangleBounds, min_km2: float = 1.0, max_km2: float = 100.0) -> None:
    """
    Validates that the geographical area defined by the rectangle bounds falls
    within a specified size range (in square kilometers).

    Args:
        bounds (RectangleBounds): The geographical bounding box of the area.
        min_km2 (float): The minimum allowed area in square kilometers.
        max_km2 (float): The maximum allowed area in square kilometers.

    Raises:
        ValueError: If the calculated area is outside the allowed range.
    """
    sw = bounds.southWest
    ne = bounds.northEast

    # Calculate the width (east-west distance) and height (north-south distance)
    # using geodesic distance for accuracy over a sphere.
    width_km = geodesic((sw.lat, sw.lng), (sw.lat, ne.lng)).km
    height_km = geodesic((sw.lat, sw.lng), (ne.lat, sw.lng)).km

    area_km2 = width_km * height_km

    if not (min_km2 <= area_km2 <= max_km2):
        raise ValueError(
            f"Monitoring area size must be between {min_km2} and {max_km2} km²."
            f" Calculated area: {area_km2:.2f} km²."
        )
