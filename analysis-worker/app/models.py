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


class CallbackPayload(BaseModel):
    """
    Defines the structure of the JSON payload sent to the backend API's
    /callbacks/analysis-complete endpoint.

    Attributes:
        result_id (str): The unique identifier for the analysis result.
        status (str): The final status of the analysis ('completed' or 'failed').
        error_message (Optional[str]): A message describing the error if the
                                       analysis failed.
        generated_map_url (Optional[str]): The GCS URL of the generated analysis map.
        change_percentage (Optional[float]): The calculated percentage of change.
    """

    result_id: str
    status: str  # "completed" or "failed"
    error_message: Optional[str] = None
    generated_map_url: Optional[str] = None
    change_percentage: Optional[float] = None
