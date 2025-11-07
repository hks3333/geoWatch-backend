"""
This module is the main entry point for the Analysis Worker FastAPI application.
It defines the API endpoints, background tasks, and the core analysis logic.
"""

import asyncio
import logging
from typing import List

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, status

from app.models import AnalysisPayload, CallbackPayload
from app.services.callback_client import callback_client
from app.services.earth_engine import (
    compute_change_products,
    fetch_dynamic_world_images,
    initialize_earth_engine,
)
from app.services.storage import upload_visualization_to_gcs
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
    It simulates a long-running (3-minute) process and adheres to the
    'Callback or Bust' principle.

    Args:
        payload (AnalysisPayload): The analysis job details.
    """
    logger.info(f"Starting analysis for result_id: {payload.result_id}")
    final_payload = CallbackPayload(result_id=payload.result_id, status="unknown")

    try:
        # --------------------------------------------------------------------------
        # 1. AUTHENTICATE & INITIALIZE SERVICES (Earth Engine, GCS, etc.)
        #    - This is where you would put your `ee.Authenticate()` and `ee.Initialize()`
        # --------------------------------------------------------------------------
        logger.info(f"Step 1/5: Initializing services for {payload.result_id}")
        if not initialize_earth_engine(settings.GCP_PROJECT_ID):
            raise RuntimeError("Failed to initialise Earth Engine")

        # --------------------------------------------------------------------------
        # 2. FETCH IMAGERY (Sentinel-2, Dynamic World)
        #    - Use `app.services.earth_engine.get_imagery(...)`
        # --------------------------------------------------------------------------
        logger.info(f"Step 2/5: Fetching imagery for {payload.result_id}")
        polygon_lnglat = _polygon_to_lnglat(payload.polygon)
        baseline_image, current_image, geometry = fetch_dynamic_world_images(
            polygon_lnglat,
            payload.is_baseline,
        )

        # --------------------------------------------------------------------------
        # 3. PROCESS IMAGERY (SAM Segmentation & Change Detection)
        #    - Use `app.services.processor.run_segmentation(...)`
        #    - Use `app.services.processor.calculate_change(...)`
        # --------------------------------------------------------------------------
        logger.info(f"Step 3/5: Running change detection for {payload.result_id}")
        metrics, visualization_url = compute_change_products(
            geometry,
            baseline_image,
            current_image,
            payload.type,
        )

        # --------------------------------------------------------------------------
        # 4. GENERATE & UPLOAD VISUALIZATIONS
        #    - Create a visual map of the change detection.
        #    - Use `app.services.storage.upload_visualization(...)`
        # --------------------------------------------------------------------------
        logger.info(f"Step 4/5: Uploading visualization for {payload.result_id}")
        try:
            with httpx.Client(timeout=60.0) as client:
                response = client.get(visualization_url)
                response.raise_for_status()
                image_bytes = response.content
        except Exception as viz_exc:
            raise RuntimeError(f"Failed to download visualization PNG: {viz_exc}") from viz_exc

        visualization_url = upload_visualization_to_gcs(
            image_bytes,
            payload.result_id,
            settings.GCP_PROJECT_ID,
            settings.GCS_BUCKET_NAME,
        )

        # --------------------------------------------------------------------------
        # 5. PREPARE SUCCESS PAYLOAD
        # --------------------------------------------------------------------------
        logger.info(f"Step 5/5: Finalizing results for {payload.result_id}")
        final_payload.status = "completed"
        final_payload.generated_map_url = visualization_url
        final_payload.change_percentage = metrics["net_change_percentage"]
        logger.info(f"Analysis successful for result_id: {payload.result_id}")

    except Exception as e:
        # If any step fails, log the error and prepare a 'failed' payload
        error_message = f"An unexpected error occurred: {e}"
        logger.error(
            f"Analysis failed for result_id: {payload.result_id}. Error: {error_message}"
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
