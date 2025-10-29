"""
This module defines the Pydantic models for Monitoring Areas, including their
structure for API requests and database storage.
"""

from datetime import datetime, timezone

from pydantic import BaseModel, Field


class LatLng(BaseModel):
    """
    Pydantic model for a geographical point with latitude and longitude.
    """
    lat: float = Field(..., ge=-90, le=90, description="Latitude")
    lng: float = Field(..., ge=-180, le=180, description="Longitude")


class RectangleBounds(BaseModel):
    """
    Pydantic model for the southwest and northeast corners of a rectangle.
    """
    southWest: LatLng = Field(..., description="South-west corner of the rectangle")
    northEast: LatLng = Field(..., description="North-east corner of the rectangle")


MonitoringAreaType = Literal["forest", "water"]
MonitoringAreaStatus = Literal["active", "pending", "paused", "error", "deleted"]


class MonitoringAreaCreate(BaseModel):
    """
    Pydantic model for creating a new monitoring area.
    Used for incoming API requests.
    """
    name: str = Field(..., min_length=3, max_length=100, description="Name of the monitoring area")
    type: MonitoringAreaType = Field(..., description="Type of monitoring (forest or water)")
    rectangle_bounds: RectangleBounds = Field(..., description="Geographical bounding box of the area")
    user_id: str = Field("demo_user", description="User ID associated with the monitoring area")


class MonitoringAreaInDB(MonitoringAreaCreate):
    """
    Pydantic model for a monitoring area as stored in the database.
    Includes auto-generated fields and default values.
    """
    user_id: str = Field(..., description="User ID associated with the monitoring area")
    area_id: str = Field(None, description="Unique identifier for the monitoring area")
    polygon: List[List[float]] = Field(
        ..., min_length=4, max_length=4, description="GeoJSON-like polygon coordinates (4 points)"
    )
    status: MonitoringAreaStatus = Field(
        "pending", description="Current status of the monitoring area"
    )
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc),
        description="Timestamp of creation"
    )
    last_checked_at: Optional[datetime] = Field(
        None, description="Timestamp of the last analysis check"
    )
    baseline_captured: bool = Field(
        False, description="Indicates if the initial baseline image has been captured"
    )
    total_analyses: int = Field(0, description="Total number of analyses performed for this area")

    class Config:
        populate_by_name = True
