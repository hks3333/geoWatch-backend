"""
This module defines the Pydantic models for Analysis Results, including their
structure for API responses and database storage.
"""

from datetime import datetime, timezone
from typing import Optional, Literal, List

from pydantic import BaseModel, Field


class ImageUrls(BaseModel):
    """URLs for all generated images from the Sentinel-2 analysis."""
    baseline_image: str = Field(..., description="Cloud-optimized GeoTIFF of baseline Sentinel-2 image")
    current_image: str = Field(..., description="Cloud-optimized GeoTIFF of current Sentinel-2 image")
    baseline_computed: str = Field(..., description="Computed mask (forest/water) for baseline")
    current_computed: str = Field(..., description="Computed mask (forest/water) for current")
    difference_image: str = Field(..., description="Visual difference map (red=loss, green=stable, blue=gain)")


class AnalysisMetrics(BaseModel):
    """Detailed metrics from the Sentinel-2 analysis."""
    analysis_type: str = Field(..., description="Type of analysis performed ('forest' or 'water')")
    baseline_date: str = Field(..., description="ISO date of baseline image")
    current_date: str = Field(..., description="ISO date of current image")
    baseline_cloud_coverage: float = Field(..., description="Percentage of clouds in baseline image")
    current_cloud_coverage: float = Field(..., description="Percentage of clouds in current image")
    valid_pixels_percentage: float = Field(..., description="Percentage of pixels analyzed (no clouds in both)")
    loss_hectares: float = Field(..., ge=0, description="Hectares of loss detected")
    gain_hectares: float = Field(..., ge=0, description="Hectares of gain detected")
    stable_hectares: float = Field(..., ge=0, description="Hectares remaining stable")
    total_hectares: float = Field(..., ge=0, description="Total hectares in ROI")
    loss_percentage: float = Field(..., description="Loss as percentage of total")
    gain_percentage: float = Field(..., description="Gain as percentage of total")
    net_change_percentage: float = Field(..., description="Net change (gain - loss) as percentage")


AnalysisProcessingStatus = Literal["in_progress", "completed", "failed"]


class AnalysisResultInDB(BaseModel):
    """
    Pydantic model for an analysis result as stored in the database.
    Updated for Sentinel-2 workflow with comprehensive metrics.
    """
    result_id: Optional[str] = Field(None, description="Unique identifier for the analysis result")
    area_id: str = Field(..., description="Reference to the monitoring area ID")
    area_type: Optional[str] = Field(None, description="Type of monitoring area ('forest' or 'water')")
    timestamp: Optional[datetime] = Field(
        None,
        description="Timestamp of when the analysis was recorded"
    )
    processing_status: AnalysisProcessingStatus = Field(
        "in_progress", description="Current processing status of the analysis result"
    )
    
    # New Sentinel-2 fields
    image_urls: Optional[ImageUrls] = Field(None, description="URLs to all generated GeoTIFF images")
    metrics: Optional[AnalysisMetrics] = Field(None, description="Detailed analysis metrics")
    bounds: Optional[List[float]] = Field(None, description="Bounding box [west, south, east, north] for Leaflet")
    
    # Top-level fields for easy querying
    baseline_date: Optional[str] = Field(None, description="ISO formatted date of the baseline image")
    current_date: Optional[str] = Field(None, description="ISO formatted date of the current image")
    analysis_type: Optional[str] = Field(None, description="Type of analysis performed")
    
    # Backward compatibility fields
    change_percentage: Optional[float] = Field(None, description="Net change percentage (backward compatibility)")
    generated_map_url: Optional[str] = Field(None, description="URL to difference image (backward compatibility)")
    
    # Error handling
    error_message: Optional[str] = Field(None, description="Error message if processing failed")

    class Config:
        populate_by_name = True
