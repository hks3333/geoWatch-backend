"""
This module is the main entry point for the Analysis Worker FastAPI application.
It defines the API endpoints, background tasks, and the core analysis logic.
"""

import asyncio
import logging
from typing import List

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, status

from app.models import AnalysisPayload, AnalysisMetrics, CallbackPayload, ImageUrls
from app.services.callback_client import callback_client
from app.services.earth_engine import (
    compute_change_products,
    fetch_sentinel2_images,
    initialize_earth_engine,
)
from app.services.storage import export_analysis_images_to_gcs
from app.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title="GeoWatch Analysis Worker",
    description="A service to perform satellite image analysis.",
    version="1.0.0",
)


def _polygon_to_lnglat(polygon: List[List[float]]) -> List[List[float]]:
    """Ensure polygon is in [lng, lat] ordering."""

    # MonitoringArea polygon is stored as LatLng, i.e., {lat, lng}; convert to list
    converted = []
    for point in polygon:
        if isinstance(point, dict):
            converted.append([point["lng"], point["lat"]])
        else:
            converted.append(point)
    return converted

def run_the_full_analysis(payload: AnalysisPayload):
    """
    The main analysis function, executed in the background.
    Performs Sentinel-2 based change detection with cloud masking.

    Args:
        payload (AnalysisPayload): The analysis job details.
    """
    logger.info(f"Starting Sentinel-2 analysis for result_id: {payload.result_id}")
    final_payload = CallbackPayload(result_id=payload.result_id, status="unknown")

    try:
        # --------------------------------------------------------------------------
        # 1. INITIALIZE EARTH ENGINE
        # --------------------------------------------------------------------------
        logger.info(f"Step 1/5: Initializing Earth Engine for {payload.result_id}")
        if not initialize_earth_engine(settings.GCP_PROJECT_ID):
            raise RuntimeError("Failed to initialise Earth Engine")

        # --------------------------------------------------------------------------
        # 2. FETCH SENTINEL-2 IMAGERY
        # --------------------------------------------------------------------------
        logger.info(f"Step 2/5: Fetching Sentinel-2 imagery for {payload.result_id}")
        polygon_lnglat = _polygon_to_lnglat(payload.polygon)
        
        baseline_image, current_image, geometry, baseline_date, current_date = fetch_sentinel2_images(
            polygon_lnglat,
            payload.is_baseline,
        )
        
        logger.info(
            "Retrieved images - Baseline: %s, Current: %s",
            baseline_date,
            current_date
        )

        # --------------------------------------------------------------------------
        # 3. COMPUTE CHANGE DETECTION WITH CLOUD MASKING
        # --------------------------------------------------------------------------
        logger.info(f"Step 3/5: Computing change detection for {payload.result_id}")
        logger.info(f"Analysis type: {payload.type}")
        
        results = compute_change_products(
            geometry=geometry,
            baseline_image=baseline_image,
            current_image=current_image,
            classification_type=payload.type,
            baseline_date=baseline_date,
            current_date=current_date,
        )
        
        metrics_dict = results['metrics']
        images_dict = results['images']
        bounds = results['bounds']
        
        logger.info(
            "Change detection complete - Loss: %.2f ha, Gain: %.2f ha, Net: %.2f%%",
            metrics_dict['loss_hectares'],
            metrics_dict['gain_hectares'],
            metrics_dict['net_change_percentage']
        )

        # --------------------------------------------------------------------------
        # 4. EXPORT ALL IMAGES TO GCS AS CLOUD-OPTIMIZED GEOTIFFS
        # --------------------------------------------------------------------------
        logger.info(f"Step 4/5: Exporting images to GCS for {payload.result_id}")
        
        image_urls_dict = export_analysis_images_to_gcs(
            images=images_dict,
            geometry=geometry,
            result_id=payload.result_id,
            area_id=payload.area_id,
            analysis_type=payload.type,
            baseline_date=baseline_date,
            current_date=current_date,
            gcp_project_id=settings.GCP_PROJECT_ID,
            bucket_name=settings.GCS_BUCKET_NAME,
        )
        
        logger.info("All images exported successfully")

        # --------------------------------------------------------------------------
        # 5. PREPARE SUCCESS CALLBACK PAYLOAD
        # --------------------------------------------------------------------------
        logger.info(f"Step 5/5: Finalizing results for {payload.result_id}")
        
        final_payload.status = "completed"
        final_payload.image_urls = ImageUrls(**image_urls_dict)
        final_payload.metrics = AnalysisMetrics(**metrics_dict)
        final_payload.bounds = bounds
        
        logger.info(f"Analysis successful for result_id: {payload.result_id}")

    except Exception as e:
        # If any step fails, log the error and prepare a 'failed' payload
        error_message = f"Analysis error: {str(e)}"
        logger.error(
            f"Analysis failed for result_id: {payload.result_id}. Error: {error_message}",
            exc_info=True
        )
        final_payload.status = "failed"
        final_payload.error_message = error_message

    finally:
        # 'CALLBACK OR BUST': This block MUST execute successfully.
        # It ensures the backend is always notified of the outcome.
        logger.info(
            "Sending final callback for result_id: %s with status: %s",
            payload.result_id,
            final_payload.status,
        )
        try:
            import asyncio as aio
            loop = aio.new_event_loop()
            aio.set_event_loop(loop)
            loop.run_until_complete(callback_client.send_callback(final_payload))
            loop.close()
        except Exception as callback_exc:
            logger.error("Failed to send callback: %s", callback_exc)


@app.post(
    "/analyze",
    status_code=status.HTTP_202_ACCEPTED,
    summary="Accepts an analysis request and runs it in the background",
)
async def analyze(
    payload: AnalysisPayload, background_tasks: BackgroundTasks
) -> dict:
    """
    This endpoint receives an analysis request, validates it, and queues the
    heavy lifting to be run as a background task.

    It immediately returns a 202 Accepted response to the client.

    Args:
        payload (AnalysisPayload): The details of the analysis to be performed.
        background_tasks (BackgroundTasks): FastAPI's mechanism for running
                                            background operations.

    Returns:
        dict: A confirmation message.
    """
    logger.info(f"Received analysis request for area_id: {payload.area_id}")

    # Add the main analysis function to the background tasks
    background_tasks.add_task(run_the_full_analysis, payload)

    # Immediately return a 202 response
    return {
        "message": "Analysis request accepted and is being processed in the background.",
        "result_id": payload.result_id,
    }


@app.on_event("shutdown")
async def shutdown_event():
    """
    Cleanly closes the HTTPX client on application shutdown.
    """
    await callback_client.close()


@app.get("/health", status_code=status.HTTP_200_OK, summary="Health check endpoint")
def health_check() -> dict:
    """
    A simple endpoint to confirm that the service is running.

    Returns:
        dict: A status message.
    """
    return {"status": "healthy"}
