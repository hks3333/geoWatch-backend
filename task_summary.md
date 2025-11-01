# Task Summary

This is a summary of the tasks performed to correct the `backend-api` and create the new `analysis-worker` service.

## 1. `backend-api` Correction

The critical flaw in the `backend-api`'s analysis trigger flow was corrected. The new flow ensures a placeholder document is created in the `analysis_results` collection *before* the analysis worker is called. This guarantees that the worker has a `result_id` to callback to.

### Modified Files:

*   **`backend/app/services/firestore_service.py`**:
    *   Added a new method `create_analysis_placeholder` to create the placeholder document in Firestore.
*   **`backend/app/services/worker_client.py`**:
    *   Updated the `trigger_analysis` method to include the `result_id` in the payload sent to the worker.
*   **`backend/app/routes/monitoring_areas.py`**:
    *   Updated the `create_monitoring_area` and `trigger_new_analysis` functions to call `create_analysis_placeholder` and pass the `result_id` to the worker.

## 2. `analysis-worker` Service Creation

A new FastAPI-based service, `analysis-worker`, was created from scratch. This service is responsible for performing the heavy lifting of satellite image analysis.

### New Files and Folders:

*   **`analysis-worker/`**: The root directory for the new service.
    *   **`main.py`**: The main FastAPI application file. It defines the `/analyze` endpoint, which accepts analysis requests and runs them as background tasks.
    *   **`requirements.txt`**: Lists all the Python dependencies for the service, including `fastapi`, `torch`, `torchvision`, and `google-cloud-storage`.
    *   **`Dockerfile`**: A multi-stage Dockerfile for building a production-ready, GPU-enabled Docker image for the service.
    *   **`.dockerignore`**: Specifies files and directories to exclude from the Docker build context.
    *   **`.env.example`**: An example environment file.
    *   **`app/`**: The main application package.
        *   **`__init__.py`**: Initializes the `app` package.
        *   **`config.py`**: Defines the application's configuration using Pydantic settings.
        *   **`models.py`**: Defines the Pydantic models for the `/analyze` request payload and the callback payload.
        *   **`services/`**: A package for the service's business logic.
            *   **`__init__.py`**: Initializes the `services` package.
            *   **`callback_client.py`**: A client for sending authenticated callbacks to the `backend-api`.
            *   **`earth_engine.py`**: A skeleton module for interacting with Google Earth Engine.
            *   **`processor.py`**: A skeleton module for the core image processing and ML logic.
            *   **`storage.py`**: A skeleton module for uploading files to Google Cloud Storage.

## 3. Testing Instructions

### `backend-api`

1.  **Run the `backend-api`:**

    ```bash
    uvicorn main:app --host 0.0.0.0 --port 8000
    ```

2.  **Send a request to create a monitoring area:**

    ```bash
    curl -X POST "http://localhost:8000/monitoring-areas" -H "Content-Type: application/json" -d '
    {
      "name": "My Forest Area",
      "type": "forest",
      "rectangle_bounds": {
        "top_left": {"lat": 40.7, "lon": -74.0},
        "bottom_right": {"lat": 40.6, "lon": -73.9}
      }
    }'
    ```

3.  **Verify the logs:**
    *   You should see logs indicating that a placeholder was created in Firestore before the worker was triggered.

### `analysis-worker`

1.  **Build and run the Docker container:**

    ```bash
    docker build -t analysis-worker .
    docker run -p 8080:8080 --env-file .env analysis-worker
    ```

2.  **Send a request to the `/analyze` endpoint:**

    ```bash
    curl -X POST "http://localhost:8080/analyze" -H "Content-Type: application/json" -d '
    {
      "area_id": "some-area-id",
      "result_id": "some-result-id",
      "polygon": [[-74.0, 40.7], [-73.9, 40.7], [-73.9, 40.8], [-74.0, 40.8]],
      "type": "forest",
      "is_baseline": true
    }'
    ```

3.  **Verify the logs:**
    *   You should see logs indicating that the analysis has started, and after a few seconds, that the callback has been sent.
