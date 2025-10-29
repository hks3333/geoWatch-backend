"""
This module provides utility functions for geographical calculations,
specifically for converting rectangle bounds to polygon coordinates.
"""

from typing import List

from app.models.monitoring_area import LatLng, RectangleBounds

def rectangle_to_polygon(bounds: RectangleBounds) -> List[List[float]]:
    """
    Converts geographical rectangle bounds into a 4-point polygon.

    The polygon is represented as a list of [longitude, latitude] pairs,
    following a clockwise or counter-clockwise order starting from the
    south-west corner.

    Args:
        bounds (RectangleBounds): An object containing the south-west and
                                  north-east corners of the rectangle.

    Returns:
        List[List[float]]: A list of four [longitude, latitude] pairs
                           representing the corners of the polygon.
    """
    sw = bounds.southWest
    ne = bounds.northEast

    # The four corners of the rectangle in [lng, lat] format
    # Order: South-West, North-West, North-East, South-East
    polygon = [
        [sw.lng, sw.lat],  # South-West
        [sw.lng, ne.lat],  # North-West
        [ne.lng, ne.lat],  # North-East
        [ne.lng, sw.lat],  # South-East
    ]
    return polygon
