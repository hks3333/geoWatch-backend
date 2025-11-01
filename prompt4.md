we are continuing to build the GeoWatch application. We have a working `backend-api`.

Our next two tasks are:

1.  **Correct a critical flaw** in the `backend-api`'s analysis trigger flow.
2.  **Build the new `analysis-worker` service** from scratch.


## 1\. The Critical Flaw and Correction

**The Flaw:**
The current `backend-api` trigger flow is broken.

1.  When `POST /monitoring-areas/{area_id}/analyze` is called, the `WorkerClient` is immediately triggered.
2.  The `Analysis Worker` (which we haven't built) is supposed to do its 3-minute job and then call the `POST /callbacks/analysis-complete` endpoint.
3.  That callback *requires* a `result_id` in its payload to know *which* document to update.
4.  However, no `analysis_results` document has been created yet. The backend "fired and forgot" without creating a placeholder. This is a fatal flaw.

**The Correction:**
You must generate the corrected code for the `backend-api` first. The new flow must be:

1.  `POST /.../analyze` is called.
2.  The backend **must first create a placeholder document** in the `analysis_results` collection with `processing_status: "in_progress"`.
3.  The backend gets the `result_id` of this new document.
4.  The backend calls the `Analysis Worker`, passing it this new `result_id`.
5.  The worker calls the callback with the `result_id`, which the backend can now use to find and update the placeholder.

**Please provide the complete, corrected code for these two `backend-api` files:**

1.  **`app/services/firestore_service.py`**: Add a new method `async def create_analysis_placeholder(self, area_id: str, area_type: str) -> str:`

      * This method should create a new document in `analysis_results`.
      * The document must contain `area_id`, `area_type`, `timestamp: datetime.now(timezone.utc)`, and `processing_status: "in_progress"`.
      * It must then update the document with its own `result_id` and return the `result_id`.

2.  **`app/services/worker_client.py`**: Update the `trigger_analysis` method signature to include `result_id: str`. This `result_id` must be added to the JSON payload sent to the worker.

3.  **`app/routes/monitoring_areas.py`**: Update the `create_monitoring_area` and `trigger_new_analysis` functions.

      * They must now `await db.create_analysis_placeholder(...)` *before* calling the worker.
      * They must pass the new `result_id` from Firestore to `await worker.trigger_analysis(...)`.

-----

## 2\. Build the Analysis Worker Service

After providing the corrections, generate the complete file set for the new **`analysis-worker` service**. This service will be in its own folder, parallel to `backend/`.

### Architecture Brief

The `analysis-worker` is a FastAPI service that runs on Cloud Run with a GPU. It has **one main endpoint: `POST /analyze`**.

  * This endpoint receives the `area_id`, `result_id`, `polygon`, and `type`.
  * It immediately returns a `202 Accepted` and runs the 3-minute analysis in a `BackgroundTasks`.

### 'Callback or Bust' Principle

The worker **must** adhere to the **'Callback or Bust'** principle.

  * The entire analysis logic (`run_the_full_analysis`) must be wrapped in a `try...except...finally` block.
  * The `finally` block **must** call the `backend-api`'s `POST /callbacks/analysis-complete` endpoint.
  * If the `try` block succeeds, it calls the callback with `status: "completed"` and the final data.
  * If the `try` block fails (`except`), it must call the callback with `status: "failed"` and the `error_message`.
  * This guarantees that the backend is *always* notified, and the user is never stuck in an `in_progress` state.

### A. Worker Folder Structure

Generate this folder structure for the new service:

```
analysis-worker/
├── main.py                     # FastAPI app, /analyze endpoint, background task logic
├── requirements.txt
├── Dockerfile                  # Must include torch, torchvision, and CUDA
├── .env.example
├── app/
│   ├── __init__.py
│   ├── config.py               # Environment variables (BACKEND_API_URL, GCP_PROJECT_ID)
│   ├── models.py               # Pydantic models for /analyze request
│   ├── services/
│   │   ├── __init__.py
│   │   ├── earth_engine.py     # Logic to fetch Dynamic World & Sentinel-2
│   │   ├── processor.py          # Logic for SAM (GPU) & change detection (Numpy)
│   │   ├── storage.py            # Logic to upload images to GCS
│   │   └── callback_client.py    # Logic to call the backend-api's callback
└── .dockerignore
```

### B. Worker `requirements.txt`

The `analysis-worker/requirements.txt` file must contain:

```
fastapi
uvicorn
httpx
pydantic-settings
google-cloud-storage
earthengine-api
numpy
Pillow
opencv-python-headless
torch
torchvision
segment-anything
google-auth
```

### C. Worker File Implementation

Provide the complete, production-ready code for the following **new `analysis-worker` files**:

1.  `analysis-worker/app/config.py`
2.  `analysis-worker/app/models.py`
3.  `analysis-worker/app/services/callback_client.py` (Must include Google OIDC token generation for service-to-service auth)
4.  `analysis-worker/main.py` (Must include the `POST /analyze` endpoint, the `BackgroundTasks` setup, and the `run_the_full_analysis` function skeleton with the 'Callback or Bust' `try...except...finally` logic.)
5.  `analysis-worker/Dockerfile` (This is critical. It must be a multi-stage build to be efficient and must correctly install the large GPU libraries like PyTorch with the correct CUDA version.)

After the task generate an md file listing everything you did and instructions to test. No need to install anything i will do that myself 