"""
This module defines the API routes for internal callbacks, such as from the
Analysis Worker.
"""

import logging
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel
import httpx

from app.config import settings
from app.services.firestore_service import FirestoreService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class ImageUrls(BaseModel):
    """URLs for all generated images from the analysis."""
    baseline_image: str
    current_image: str
    baseline_computed: str
    current_computed: str
    difference_image: str


class AnalysisMetrics(BaseModel):
    """Detailed metrics from the Sentinel-2 analysis."""
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


class AnalysisCompletionPayload(BaseModel):
    """Callback payload from the analysis worker."""
    result_id: str
    status: str
    error_message: Optional[str] = None
    image_urls: Optional[ImageUrls] = None
    metrics: Optional[AnalysisMetrics] = None
    bounds: Optional[List[float]] = None


# Dependency to get FirestoreService instance
def get_firestore_service() -> FirestoreService:
    """
    Provides a FirestoreService instance for dependency injection.
    """
    return FirestoreService(project_id=settings.GCP_PROJECT_ID)


async def verify_oidc_token(authorization: str = Header(default=None)):
    """
    Verifies the OIDC token from the Authorization header.
    In local mode, this is a no-op for testing.
    In production, this would verify the token against Google's public keys.
    """
    if settings.BACKEND_ENV == "local":
        logger.debug("Skipping OIDC verification in local mode")
        return True
    
    # Production mode: require valid Authorization header
    if not authorization or not authorization.startswith("Bearer "):
        logger.error("Missing or invalid Authorization header in production mode")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or missing Authorization header",
        )
    
    # In a real app, you would verify the token here.
    # For example:
    # from google.oauth2 import id_token
    # from google.auth.transport import requests
    # try:
    #     id_info = id_token.verify_oauth2_token(
    #         token, requests.Request(), audience=settings.WORKER_AUDIENCE
    #     )
    # except ValueError:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid OIDC token",
    #     )
    
    return True


@router.post(
    "/analysis-complete",
    status_code=status.HTTP_200_OK,
    summary="Callback for when analysis is complete",
    dependencies=[Depends(verify_oidc_token)],
)
async def analysis_complete_callback(
    payload: AnalysisCompletionPayload,
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Internal endpoint for the Analysis Worker to report its status.
    This is protected by Google Cloud's service-to-service authentication.
    """
    logger.info(f"Received analysis callback for result_id: {payload.result_id}, status: {payload.status}")
    
    try:
        update_data = {
            "processing_status": payload.status,
        }
        
        if payload.status == "completed":
            # Store new structured data
            if payload.image_urls:
                update_data["image_urls"] = payload.image_urls.model_dump()
            
            if payload.metrics:
                update_data["metrics"] = payload.metrics.model_dump()
                # Also store key dates and type at top level for easy querying
                update_data["baseline_date"] = payload.metrics.baseline_date
                update_data["current_date"] = payload.metrics.current_date
                update_data["analysis_type"] = payload.metrics.analysis_type
                
                # Backward compatibility: populate old fields
                update_data["change_percentage"] = payload.metrics.net_change_percentage
            
            if payload.bounds:
                update_data["bounds"] = payload.bounds
            
            # Backward compatibility: generated_map_url
            if payload.image_urls:
                update_data["generated_map_url"] = payload.image_urls.difference_image
                
        elif payload.status == "failed":
            update_data["error_message"] = payload.error_message

        area_id = await db.update_analysis_result(payload.result_id, update_data)
        
        if area_id and payload.status in {"completed", "failed"}:
            await db.update_monitoring_area(
                area_id,
                {"status": "active" if payload.status == "completed" else "error"},
            )
        
        # Trigger report generation for successful analyses
        if area_id and payload.status == "completed":
            try:
                await _trigger_report_generation(db, area_id, payload.result_id)
            except Exception as report_error:
                logger.error(f"Failed to trigger report generation: {report_error}")
                # Don't fail the callback if report generation fails
        
        logger.info(
            "Analysis result %s updated to %s.",
            payload.result_id,
            payload.status,
        )
        return {"message": "Callback processed successfully"}
    except Exception as e:
        logger.error(
            "Failed to process analysis completion callback for result %s: %s",
            payload.result_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process callback.",
        )


class ReportCompletionPayload(BaseModel):
    """Callback payload from the report worker."""
    report_id: str
    area_id: str
    result_id: str
    status: str
    summary: Optional[str] = None
    error_message: Optional[str] = None


@router.post("/report-complete")
async def report_complete_callback(
    payload: ReportCompletionPayload,
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Callback endpoint for report worker to notify report completion.
    """
    try:
        logger.info(f"Received report completion callback: {payload.report_id} - {payload.status}")
        
        # Update analysis result with report info
        update_data = {
            "report_id": payload.report_id,
            "report_status": payload.status,
            "report_summary": payload.summary
        }
        
        await db.update_analysis_result(payload.result_id, update_data)
        
        logger.info(f"Updated result {payload.result_id} with report {payload.report_id}")
        return {"message": "Report callback processed successfully"}
        
    except Exception as e:
        logger.error(f"Failed to process report callback: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process report callback"
        )


async def _trigger_report_generation(db: FirestoreService, area_id: str, result_id: str):
    """
    Trigger report generation by calling the report worker.
    
    Args:
        db: Firestore service instance
        area_id: Monitoring area ID
        result_id: Latest analysis result ID
    """
    logger.info(f"Triggering report generation for area {area_id}, result {result_id}")
    
    # Fetch area details
    area_data = await db.get_monitoring_area(area_id)
    if not area_data:
        logger.error(f"Area {area_id} not found, cannot generate report")
        return
    
    # Fetch latest result
    latest_result = None
    results_data = await db.get_analysis_results(area_id, limit=1, offset=0)
    if results_data:
        latest_result = results_data[0]
    
    if not latest_result or latest_result.get("result_id") != result_id:
        logger.error(f"Result {result_id} not found, cannot generate report")
        return
    
    # Fetch historical results (last 10)
    historical_results = await db.get_analysis_results(area_id, limit=10, offset=1)
    
    # Prepare request payload
    payload = {
        "area": {
            "area_id": area_data["area_id"],
            "name": area_data["name"],
            "type": area_data["type"],
            "created_at": area_data["created_at"].isoformat() if hasattr(area_data["created_at"], "isoformat") else str(area_data["created_at"]),
            "total_analyses": area_data.get("total_analyses", 0)
        },
        "latest_result": {
            "result_id": latest_result["result_id"],
            "timestamp": latest_result["timestamp"].isoformat() if hasattr(latest_result["timestamp"], "isoformat") else str(latest_result["timestamp"]),
            "processing_status": latest_result["processing_status"],
            "metrics": latest_result.get("metrics"),
            "error_message": latest_result.get("error_message")
        },
        "historical_results": [
            {
                "result_id": r["result_id"],
                "timestamp": r["timestamp"].isoformat() if hasattr(r["timestamp"], "isoformat") else str(r["timestamp"]),
                "processing_status": r["processing_status"],
                "metrics": r.get("metrics"),
                "error_message": r.get("error_message")
            }
            for r in historical_results
            if r.get("processing_status") == "completed"
        ]
    }
    
    # Call report worker
    report_worker_url = getattr(settings, "REPORT_WORKER_URL", "http://localhost:8002")
    
    try:
        async with httpx.AsyncClient(timeout=120.0) as client:
            response = await client.post(
                f"{report_worker_url}/generate-report",
                json=payload
            )
            
            if response.status_code == 200:
                logger.info(f"Successfully triggered report generation for area {area_id}")
            else:
                logger.warning(f"Report worker returned status {response.status_code}: {response.text}")
                
    except Exception as e:
        logger.error(f"Failed to call report worker: {e}")
        raise
