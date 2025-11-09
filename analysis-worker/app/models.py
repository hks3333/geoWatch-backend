"""
This module defines the Pydantic models used for data validation and
serialization in the Analysis Worker service. These models ensure that
the data exchanged with the API endpoints is structured and type-safe.
"""

from typing import List, Optional

from pydantic import BaseModel, Field


class AnalysisPayload(BaseModel):
    """
    Defines the structure of the JSON payload expected by the /analyze endpoint.

    Attributes:
        area_id (str): The unique identifier for the monitoring area.
        result_id (str): The unique identifier for this specific analysis result.
        polygon (List[List[float]]): A list of [lon, lat] coordinates defining the
                                     monitoring area's boundary.
        type (str): The type of analysis to be performed (e.g., 'forest', 'water').
        is_baseline (bool): Flag indicating if this is the initial baseline analysis.
    """

    area_id: str = Field(..., description="The ID of the monitoring area.")
    result_id: str = Field(..., description="The ID for the analysis result document.")
    polygon: List[List[float]] = Field(
        ...,
        description="The polygon coordinates as a list of [lon, lat] pairs.",
        example=[[-74.0, 40.7], [-73.9, 40.7], [-73.9, 40.8], [-74.0, 40.8]],
    )
    type: str = Field(..., description="The type of monitoring area (e.g., 'forest').")
    is_baseline: bool = Field(
        False, description="Whether this is the first (baseline) analysis."
    )


class ImageUrls(BaseModel):
    """
    URLs for all generated images from the analysis.
    
    Attributes:
        baseline_image: Cloud-optimized GeoTIFF of baseline Sentinel-2 image
        current_image: Cloud-optimized GeoTIFF of current Sentinel-2 image
        baseline_computed: Computed mask (forest/water) for baseline
        current_computed: Computed mask (forest/water) for current
        difference_image: Visual difference map (red=loss, green=stable, blue=gain)
    """
    baseline_image: str
    current_image: str
    baseline_computed: str
    current_computed: str
    difference_image: str


class AnalysisMetrics(BaseModel):
    """
    Detailed metrics from the analysis.
    
    Attributes:
        analysis_type: Type of analysis performed ('forest' or 'water')
        baseline_date: ISO date of baseline image
        current_date: ISO date of current image
        baseline_cloud_coverage: Percentage of clouds in baseline image
        current_cloud_coverage: Percentage of clouds in current image
        valid_pixels_percentage: Percentage of pixels analyzed (no clouds in both)
        loss_hectares: Hectares of loss detected
        gain_hectares: Hectares of gain detected
        stable_hectares: Hectares remaining stable
        total_hectares: Total hectares in ROI
        loss_percentage: Loss as percentage of total
        gain_percentage: Gain as percentage of total
        net_change_percentage: Net change (gain - loss) as percentage
    """
    analysis_type: str
    baseline_date: str
    current_date: str
    baseline_cloud_coverage: float
    current_cloud_coverage: float
    valid_pixels_percentage: float
    loss_hectares: float
    gain_hectares: float
    stable_hectares: float
    total_hectares: float
    loss_percentage: float
    gain_percentage: float
    net_change_percentage: float


class CallbackPayload(BaseModel):
    """
    Defines the structure of the JSON payload sent to the backend API's
    /callbacks/analysis-complete endpoint.

    Attributes:
        result_id (str): The unique identifier for the analysis result.
        status (str): The final status of the analysis ('completed' or 'failed').
        error_message (Optional[str]): A message describing the error if the
                                       analysis failed.
        image_urls (Optional[ImageUrls]): URLs to all generated images.
        metrics (Optional[AnalysisMetrics]): Detailed analysis metrics.
        bounds (Optional[List[float]]): Bounding box [west, south, east, north] for Leaflet.
    """

    result_id: str
    status: str  # "completed" or "failed"
    error_message: Optional[str] = None
    image_urls: Optional[ImageUrls] = None
    metrics: Optional[AnalysisMetrics] = None
    bounds: Optional[List[float]] = None
