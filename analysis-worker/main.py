"""
This module is the main entry point for the Analysis Worker FastAPI application.
It defines the API endpoints, background tasks, and the core analysis logic.
"""

import logging

from fastapi import BackgroundTasks, FastAPI, HTTPException, status

from app.models import AnalysisPayload, CallbackPayload
from app.services.callback_client import callback_client

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Create FastAPI app instance
app = FastAPI(
    title="GeoWatch Analysis Worker",
    description="A service to perform satellite image analysis.",
    version="1.0.0",
)


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
        # In a real app, handle potential initialization failures

        # --------------------------------------------------------------------------
        # 2. FETCH IMAGERY (Sentinel-2, Dynamic World)
        #    - Use `app.services.earth_engine.get_imagery(...)`
        # --------------------------------------------------------------------------
        logger.info(f"Step 2/5: Fetching imagery for {payload.result_id}")
        # e.g., baseline_image, latest_image = get_imagery(payload.polygon, payload.is_baseline)

        # --------------------------------------------------------------------------
        # 3. PROCESS IMAGERY (SAM Segmentation & Change Detection)
        #    - Use `app.services.processor.run_segmentation(...)`
        #    - Use `app.services.processor.calculate_change(...)`
        # --------------------------------------------------------------------------
        logger.info(f"Step 3/5: Running ML segmentation for {payload.result_id}")
        # e.g., change_map, change_percentage = calculate_change(baseline_image, latest_image)

        # --------------------------------------------------------------------------
        # 4. GENERATE & UPLOAD VISUALIZATIONS
        #    - Create a visual map of the change detection.
        #    - Use `app.services.storage.upload_visualization(...)`
        # --------------------------------------------------------------------------
        logger.info(f"Step 4/5: Uploading visualization for {payload.result_id}")
        # e.g., map_url = upload_visualization(change_map)

        # --------------------------------------------------------------------------
        # 5. PREPARE SUCCESS PAYLOAD
        # --------------------------------------------------------------------------
        logger.info(f"Step 5/5: Finalizing results for {payload.result_id}")
        final_payload.status = "completed"
        # final_payload.generated_map_url = map_url
        # final_payload.change_percentage = change_percentage
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
            f"Sending final callback for result_id: {payload.result_id} with status: {final_payload.status}"
        )
        # This is a fire-and-forget task. The callback client handles its own errors.
        # In a production system, you might add this to a separate retry queue.
        # await callback_client.send_callback(final_payload)


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
