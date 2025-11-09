"""
This module defines the API routes for managing monitoring areas.
It includes endpoints for creating, retrieving, updating, and deleting
monitoring areas, as well as triggering analysis.
"""

import logging
from typing import List

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import JSONResponse

from app.config import settings
from app.models.analysis_result import AnalysisResultInDB
from app.models.monitoring_area import (
    MonitoringAreaCreate,
    MonitoringAreaInDB,
    MonitoringAreaStatus,
)
from app.services.firestore_service import FirestoreService
from app.services.worker_client import WorkerClient
from app.utils.geometry import rectangle_to_polygon
from app.utils.validators import validate_area_size

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


# Dependency to get FirestoreService instance
def get_firestore_service() -> FirestoreService:
    """
    Provides a FirestoreService instance for dependency injection.
    """
    return FirestoreService(project_id=settings.GCP_PROJECT_ID)


# Dependency to get WorkerClient instance
def get_worker_client() -> WorkerClient:
    """
    Provides a WorkerClient instance for dependency injection.
    """
    return WorkerClient(worker_url=settings.ANALYSIS_WORKER_URL)


@router.post(
    "/monitoring-areas",
    status_code=status.HTTP_202_ACCEPTED,
    response_model=dict,
    summary="Create a new monitoring area and trigger initial analysis",
)
async def create_monitoring_area(
    area: MonitoringAreaCreate,
    db: FirestoreService = Depends(get_firestore_service),
    worker: WorkerClient = Depends(get_worker_client),
):
    """
    Creates a new monitoring area with the provided details.

    - Validates the input area size (1-500 km²).
    - Converts the rectangular bounds into a 4-point polygon.
    - Stores the new area in Firestore with a 'pending' status.
    - Triggers an immediate asynchronous analysis call to the Analysis Worker
      for baseline data capture.

    Returns:
        A dictionary containing the `area_id` of the newly created monitoring area.
    
    Raises:
        HTTPException: 400 if the area size is invalid.
        HTTPException: 500 if there's a database or worker communication error.
    """
    try:
        # 1. Validate input (area size 1-500 km²)
        validate_area_size(area.rectangle_bounds)
    except ValueError as e:
        logger.warning("Invalid area size for new monitoring area: %s", e)
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))

    # 2. Converts rectangle to 4-point polygon
    polygon = rectangle_to_polygon(area.rectangle_bounds)

    # Prepare data for Firestore
    new_area_data = MonitoringAreaInDB(
        **area.model_dump(),
        polygon=polygon,
        status=MonitoringAreaStatus.PENDING,
        baseline_captured=False,
        total_analyses=0,
    )

    try:
        # 3. Stores in Firestore
        area_id = await db.add_monitoring_area(new_area_data.model_dump(by_alias=True))
        logger.info("Monitoring area %s created in Firestore.", area_id)
    except Exception as e:
        logger.error("Failed to add monitoring area to Firestore: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create monitoring area due to database error.",
        )

    try:
        # 4. Create a placeholder for the analysis result
        result_id = await db.create_analysis_placeholder(area_id, area.type)
        logger.info(f"Created analysis placeholder {result_id} for area {area_id}")

        # 5. Immediately triggers first analysis (async call to Analysis Worker)
        await worker.trigger_analysis(
            area_id=area_id,
            result_id=result_id,
            polygon=polygon,
            area_type=area.type,
            is_baseline=True,
        )
        logger.info("Initial analysis triggered for monitoring area %s.", area_id)
    except Exception as e:
        logger.error("Failed to trigger initial analysis for area %s: %s", area_id, e)
        # This is a non-blocking operation, so we don't fail the request
        # but log the error and potentially update area status later.
        # For now, we proceed as 202 Accepted means the request was accepted for processing.

    return JSONResponse(content={"area_id": area_id}, status_code=status.HTTP_202_ACCEPTED)


@router.get(
    "/monitoring-areas",
    response_model=List[MonitoringAreaInDB],
    summary="Retrieve all monitoring areas",
)
async def get_all_monitoring_areas(
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Retrieves a list of all monitoring areas for the hardcoded demo user.
    Enriches each area with latest analysis info (last_checked_at, latest_change_percentage).

    Returns:
        List[MonitoringAreaInDB]: A list of all monitoring areas, including their
                                  current status and details.
    """
    try:
        areas_data = await db.get_all_monitoring_areas(user_id="demo_user")
        
        # Enrich each area with latest analysis info
        enriched_areas = []
        for area in areas_data:
            try:
                # Get latest completed result
                latest_result = await db.get_latest_analysis_result(area["area_id"])
                if latest_result and latest_result.get("processing_status") == "completed":
                    area["last_checked_at"] = latest_result.get("timestamp")
                    area["latest_change_percentage"] = latest_result.get("change_percentage")
            except Exception as e:
                logger.warning(f"Failed to get latest result for area {area['area_id']}: {e}")
                # Continue without enrichment
            
            enriched_areas.append(MonitoringAreaInDB(**area))
        
        return enriched_areas
    except Exception as e:
        logger.error("Failed to retrieve all monitoring areas: %s", e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitoring areas.",
        )


@router.get(
    "/monitoring-areas/{area_id}",
    response_model=MonitoringAreaInDB,
    summary="Retrieve a single monitoring area by ID",
)
async def get_monitoring_area_by_id(
    area_id: str,
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Retrieves the details of a single monitoring area specified by its ID.

    Args:
        area_id (str): The unique identifier of the monitoring area.

    Returns:
        MonitoringAreaInDB: The monitoring area object.

    Raises:
        HTTPException: 404 if the monitoring area is not found.
        HTTPException: 500 if there's a database error.
    """
    try:
        area_data = await db.get_monitoring_area(area_id)
        if not area_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring area with ID '{area_id}' not found.",
            )
        
        # Verify user_id
        if area_data.get("user_id") != "demo_user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have permission to access this resource.",
            )

        return MonitoringAreaInDB(**area_data)
    except HTTPException:
        # Re-raise HTTPException to be handled by FastAPI
        raise
    except Exception as e:
        logger.error("Failed to retrieve monitoring area %s: %s", area_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitoring area.",
        )


@router.get(
    "/monitoring-areas/{area_id}/results",
    response_model=dict,
    summary="Retrieve paginated analysis results for a monitoring area",
)
async def get_analysis_results_for_area(
    area_id: str,
    limit: int = 10,
    offset: int = 0,
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Retrieves paginated analysis results for a specific monitoring area.

    Args:
        area_id (str): The unique identifier of the monitoring area.
        limit (int): The maximum number of results to return (default: 10).
        offset (int): The number of results to skip (default: 0).

    Returns:
        dict: A dictionary containing a list of `AnalysisResultInDB` objects
              and an `analysis_in_progress` boolean flag.

    Raises:
        HTTPException: 500 if there's a database error.
    """
    if limit <= 0 or offset < 0:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Limit must be positive and offset must be non-negative.",
        )

    try:
        results_data = await db.get_analysis_results(area_id, limit, offset)
        results = [AnalysisResultInDB(**result) for result in results_data]

        analysis_in_progress = False
        if results and results[0].processing_status == "in_progress":
            analysis_in_progress = True

        return {"results": results, "analysis_in_progress": analysis_in_progress}
    except Exception as e:
        logger.error("Failed to retrieve analysis results for area %s: %s", area_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve analysis results.",
        )


@router.get(
    "/monitoring-areas/{area_id}/latest",
    response_model=dict,
    summary="Get the latest completed analysis result for a monitoring area",
)
async def get_latest_analysis_result(
    area_id: str,
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Retrieves the single most recent completed analysis result for a monitoring area.

    Args:
        area_id (str): The unique identifier of the monitoring area.

    Returns:
        dict: The latest completed analysis result.

    Raises:
        HTTPException: 404 if the area or result is not found.
        HTTPException: 403 if the user is not authorized.
        HTTPException: 500 if there's a database error.
    """
    try:
        area_data = await db.get_monitoring_area(area_id)
        if not area_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring area with ID '{area_id}' not found.",
            )

        if area_data.get("user_id") != "demo_user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have permission to access this resource.",
            )

        latest_result = await db.get_latest_analysis_result(area_id)
        if not latest_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"No completed analysis found for area '{area_id}'.",
            )

        return latest_result
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to get latest analysis for area %s: %s", area_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve latest analysis result.",
        )


@router.post(
    "/monitoring-areas/{area_id}/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Trigger a new analysis for a monitoring area",
)
async def trigger_new_analysis(
    area_id: str,
    db: FirestoreService = Depends(get_firestore_service),
    worker: WorkerClient = Depends(get_worker_client),
):
    """
    Triggers a new satellite image analysis for the specified monitoring area.

    - Retrieves the monitoring area details from Firestore.
    - Makes an asynchronous call to the Analysis Worker service.
    - Returns 202 Accepted immediately, as the analysis is processed asynchronously.

    Args:
        area_id (str): The unique identifier of the monitoring area.

    Raises:
        HTTPException: 404 if the monitoring area is not found.
        HTTPException: 500 if there's a database or worker communication error.
    """
    try:
        area_data = await db.get_monitoring_area(area_id)
        if not area_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring area with ID '{area_id}' not found.",
            )
        area = MonitoringAreaInDB(**area_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to retrieve monitoring area %s for analysis trigger: %s", area_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve monitoring area details.",
        )

    try:
        # 1. Create a placeholder for the analysis result
        result_id = await db.create_analysis_placeholder(area_id, area.type)
        logger.info(f"Created analysis placeholder {result_id} for area {area_id}")

        # 2. Trigger analysis with is_baseline=False for subsequent analyses
        await worker.trigger_analysis(
            area_id=area.area_id,
            result_id=result_id,
            polygon=area.polygon,
            area_type=area.type,
            is_baseline=False,
        )
        logger.info("New analysis triggered for monitoring area %s.", area_id)
    except Exception as e:
        logger.error("Failed to trigger new analysis for area %s: %s", area_id, e)
        # Similar to creation, this is async, so we accept the request
        # but log the error.

    return JSONResponse(content={"message": "Analysis triggered successfully"}, status_code=status.HTTP_202_ACCEPTED)


@router.patch(
    "/monitoring-areas/{area_id}",
    response_model=MonitoringAreaInDB,
    summary="Update a monitoring area's name",
)
async def update_monitoring_area_name(
    area_id: str,
    update_data: dict,
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Updates the name of a monitoring area.

    Args:
        area_id (str): The unique identifier of the monitoring area.
        update_data (dict): A dictionary containing the new name.

    Returns:
        MonitoringAreaInDB: The updated monitoring area object.

    Raises:
        HTTPException: 404 if the monitoring area is not found.
        HTTPException: 403 if the user is not authorized.
        HTTPException: 500 if there's a database error.
    """
    try:
        area_data = await db.get_monitoring_area(area_id)
        if not area_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring area with ID '{area_id}' not found.",
            )

        if area_data.get("user_id") != "demo_user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have permission to access this resource.",
            )

        await db.update_monitoring_area(area_id, {"name": update_data["name"]})
        updated_area_data = await db.get_monitoring_area(area_id)
        return MonitoringAreaInDB(**updated_area_data)
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to update monitoring area %s: %s", area_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update monitoring area.",
        )


@router.delete(
    "/monitoring-areas/{area_id}",
    status_code=status.HTTP_200_OK,
    summary="Soft delete a monitoring area",
)
async def soft_delete_monitoring_area(
    area_id: str,
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Soft deletes a monitoring area by setting its status to 'deleted'.

    Args:
        area_id (str): The unique identifier of the monitoring area to delete.

    Returns:
        dict: A confirmation message.

    Raises:
        HTTPException: 404 if the monitoring area is not found.
        HTTPException: 500 if there's a database error.
    """
    try:
        # First, check if the area exists
        area_data = await db.get_monitoring_area(area_id)
        if not area_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Monitoring area with ID '{area_id}' not found.",
            )
        
        if area_data.get("user_id") != "demo_user":
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Access forbidden: You do not have permission to access this resource.",
            )

        await db.soft_delete_monitoring_area(area_id)
        logger.info("Monitoring area %s soft-deleted.", area_id)
        return {"message": f"Monitoring area '{area_id}' soft-deleted successfully."}
    except HTTPException:
        raise
    except Exception as e:
        logger.error("Failed to soft delete monitoring area %s: %s", area_id, e)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to soft delete monitoring area.",
        )

