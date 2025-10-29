"""
This module provides utility functions for geographical calculations,
specifically for converting rectangle bounds to polygon coordinates.
"""

from typing import List

from app.models.monitoring_area import LatLng, RectangleBounds

def rectangle_to_polygon(bounds: RectangleBounds) -> List[LatLng]:
    """
    Converts geographical rectangle bounds into a 4-point polygon.

    The polygon is represented as LatLng vertices, following a clockwise or
    counter-clockwise order starting from the south-west corner.

    Args:
        bounds (RectangleBounds): An object containing the south-west and
                                  north-east corners of the rectangle.

    Returns:
        List[LatLng]: A list of four LatLng objects representing the corners
                       of the rectangle.
    """
    sw = bounds.southWest
    ne = bounds.northEast

    # The four corners of the rectangle represented as LatLng objects
    # Order: South-West, North-West, North-East, South-East
    polygon = [
        LatLng(lat=sw.lat, lng=sw.lng),  # South-West
        LatLng(lat=ne.lat, lng=sw.lng),  # North-West
        LatLng(lat=ne.lat, lng=ne.lng),  # North-East
        LatLng(lat=sw.lat, lng=ne.lng),  # South-East
    ]
    return polygon


def polygon_to_worker_coordinates(polygon: List[LatLng]) -> List[List[float]]:
    """Convert polygon LatLng vertices into [lng, lat] pairs for worker payloads."""
    return [[vertex.lng, vertex.lat] for vertex in polygon]
