# GeoWatch Backend Implementation Details

This document outlines the technical implementations completed for the GeoWatch backend API as per the `GEMINI.md` instructions.

## 1. Project Setup

### Folder Structure
The following directory structure has been established:
```
backend/
├── main.py
├── requirements.txt
├── Dockerfile
├── .env.example
├── app/
│   ├── __init__.py
│   ├── config.py
│   ├── models/
│   │   ├── __init__.py
│   │   ├── monitoring_area.py
│   │   └── analysis_result.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── monitoring_areas.py
│   │   ├── analysis.py
│   │   └── health.py
│   ├── services/
│   │   ├── __init__.py
│   │   ├── firestore_service.py
│   │   ├── storage_service.py
│   │   └── worker_client.py
│   └── utils/
│       ├── __init__.py
│       ├── validators.py
│       └── geometry.py
└── tests/
    ├── test_monitoring_areas.py
    └── test_geometry.py
```

### `requirements.txt`
The `backend/requirements.txt` file has been created with the following dependencies:
- `fastapi`
- `uvicorn`
- `google-cloud-firestore`
- `google-cloud-storage`
- `pydantic`
- `httpx`

## 2. Configuration

### `.env.example`
The `backend/.env.example` file has been created to provide a template for environment variables, including:
- `GOOGLE_APPLICATION_CREDENTIALS=""`
- `GCP_PROJECT_ID=""`
- `ANALYSIS_WORKER_URL=""`

## 3. Firestore Service

### `backend/app/services/firestore_service.py`
This file implements the `FirestoreService` class, which encapsulates all interactions with Google Cloud Firestore. Key functionalities include:
-   **Initialization**: Connects to Firestore using `firestore_v1.AsyncClient` and sets up references to `monitoring_areas` and `analysis_results` collections. Includes error handling for connection failures.
-   **Monitoring Area Operations**:
    -   `add_monitoring_area(area_data)`: Adds a new monitoring area document and returns its ID.
    -   `get_monitoring_area(area_id)`: Retrieves a single monitoring area by ID.
    -   `get_all_monitoring_areas()`: Fetches all monitoring areas.
    -   `update_monitoring_area(area_id, update_data)`: Updates specific fields of a monitoring area.
    -   `soft_delete_monitoring_area(area_id)`: Sets the status of a monitoring area to "deleted".
-   **Analysis Result Operations**:
    -   `add_analysis_result(result_data)`: Adds a new analysis result document and returns its ID.
    -   `get_analysis_results(area_id, limit, offset)`: Retrieves paginated analysis results for a given monitoring area, ordered by timestamp.
-   **Error Handling & Logging**: Comprehensive `try-except` blocks and `logging` are used throughout the service to ensure robustness and traceability.
-   **Asynchronous Operations**: All database operations are implemented using `async/await` for non-blocking I/O, aligning with FastAPI's asynchronous nature.

## 4. Pydantic Models

### `backend/app/models/monitoring_area.py`
This file defines the Pydantic models for monitoring areas:
-   **`LatLng`**: Represents a geographical point with `lat` and `lng` (float, with validation for geographical ranges).
-   **`RectangleBounds`**: Defines a rectangular area using `southWest` and `northEast` `LatLng` points.
-   **`MonitoringAreaType`**: A `Literal` type for `"forest"` or `"water"`.
-   **`MonitoringAreaStatus`**: A `Literal` type for `"active"`, `"pending"`, `"paused"`, `"error"`, `"deleted"`.
-   **`MonitoringAreaCreate`**: Used for API request bodies when creating a new monitoring area, including `name`, `type`, and `rectangle_bounds`. Includes string length validation for `name`.
-   **`MonitoringAreaInDB`**: Represents the full monitoring area object as stored in Firestore, extending `MonitoringAreaCreate` with fields like `area_id`, `polygon`, `status`, `created_at`, `last_checked_at`, `baseline_captured`, and `total_analyses`. Default values and `datetime` serialization are configured.

### `backend/app/models/analysis_result.py`
This file defines the Pydantic models for analysis results:
-   **`AnalysisStatistics`**: Captures statistical data such as `loss_hectares`, `gain_hectares`, and `change_percentage` (float, with `ge=0` for hectares).
-   **`AnalysisImages`**: Stores Cloud Storage URLs for `baseline`, `current`, and `change_mask` images.
-   **`AnalysisProcessingStatus`**: A `Literal` type for `"in_progress"`, `"completed"`, `"failed"`.
-   **`AnalysisResultInDB`**: Represents the complete analysis result object as stored in Firestore, including `result_id`, `area_id`, `timestamp`, `baseline_date`, `current_date`, `change_detected`, `change_type`, `statistics`, `images`, `confidence`, `report_text`, `processing_status`, and `error_message`. Default values and `datetime` serialization are configured.
