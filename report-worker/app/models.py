"""
Pydantic models for report generation requests and responses.
"""
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class AnalysisMetrics(BaseModel):
    """Metrics from a single analysis."""
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


class AnalysisResult(BaseModel):
    """Single analysis result with all details."""
    result_id: str
    timestamp: str
    processing_status: str
    metrics: Optional[AnalysisMetrics] = None
    error_message: Optional[str] = None


class MonitoringArea(BaseModel):
    """Monitoring area information."""
    area_id: str
    name: str
    type: str  # 'forest' or 'water'
    created_at: str
    total_analyses: int


class ReportGenerationRequest(BaseModel):
    """Request payload for report generation."""
    area: MonitoringArea
    latest_result: AnalysisResult
    historical_results: List[AnalysisResult] = Field(default_factory=list)
    
    class Config:
        json_schema_extra = {
            "example": {
                "area": {
                    "area_id": "abc123",
                    "name": "Amazon Rainforest Sector A",
                    "type": "forest",
                    "created_at": "2025-01-01T00:00:00Z",
                    "total_analyses": 5
                },
                "latest_result": {
                    "result_id": "result_123",
                    "timestamp": "2025-11-10T00:00:00Z",
                    "processing_status": "completed",
                    "metrics": {
                        "analysis_type": "forest",
                        "baseline_date": "2025-10-10",
                        "current_date": "2025-11-10",
                        "baseline_cloud_coverage": 5.2,
                        "current_cloud_coverage": 8.1,
                        "valid_pixels_percentage": 95.5,
                        "loss_hectares": 12.5,
                        "gain_hectares": 3.2,
                        "stable_hectares": 484.3,
                        "total_hectares": 500.0,
                        "loss_percentage": 2.5,
                        "gain_percentage": 0.64,
                        "net_change_percentage": -1.86
                    }
                },
                "historical_results": []
            }
        }


class ReportGenerationResponse(BaseModel):
    """Response with generated report."""
    report_id: str
    area_id: str
    generated_at: str
    report_markdown: str
    summary: str
    key_findings: List[str]
    recommendations: List[str]
