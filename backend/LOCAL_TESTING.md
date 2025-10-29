# Local Development and Testing for GeoWatch Backend API

This document provides instructions on how to set up and run the GeoWatch Backend API locally for development and testing purposes.

## Prerequisites

Before you begin, ensure you have the following installed:

-   **Python 3.11**: The project is built with Python 3.11.
-   **pip**: Python's package installer (usually comes with Python).
-   **Google Cloud SDK**: Required for authenticating with Google Cloud services (Firestore, Cloud Storage). Follow the [official installation guide](https://cloud.google.com/sdk/docs/install).

## 1. Setup Virtual Environment

It's highly recommended to use a virtual environment to manage project dependencies.

1.  Navigate to the `backend` directory:
    ```bash
    cd C:\Users\hariy\OneDrive\Documents\PROJECTS\geoWatch\backend
    ```

2.  Create a virtual environment:
    ```bash
    python -m venv venv
    ```

3.  Activate the virtual environment:
    -   **Windows (Command Prompt):**
        ```bash
        .\venv\Scripts\activate
        ```
    -   **Windows (PowerShell):**
        ```powershell
        .\venv\Scripts\Activate.ps1
        ```
    -   **macOS/Linux:**
        ```bash
        source venv/bin/activate
        ```

## 2. Install Dependencies

With your virtual environment activated, install the required Python packages:

```bash
pip install -r requirements.txt
```

## 3. Google Cloud Authentication

The application needs credentials to access Google Cloud Firestore and Cloud Storage. Authenticate your local environment using the Google Cloud SDK:

```bash
gcloud auth application-default login
```

This command will open a browser window for you to log in with your Google account. Once authenticated, your local environment will have the necessary credentials.

## 4. Environment Variables

Create a `.env` file in the `backend` directory based on the `.env.example` template. This file will store your project-specific configuration.

1.  Copy the example file:
    ```bash
    copy .env.example .env
    ```
    (On macOS/Linux: `cp .env.example .env`)

2.  Edit the `.env` file and fill in the values:
    ```ini
    # .env
    GCP_PROJECT_ID="your-gcp-project-id" # e.g., my-geowatch-project-12345
    ANALYSIS_WORKER_URL="http://localhost:8001" # Or the actual URL of your deployed Analysis Worker
    # GOOGLE_APPLICATION_CREDENTIALS is usually handled by `gcloud auth application-default login`
    # but you can specify a path to a service account key file here if needed.
    # GOOGLE_APPLICATION_CREDENTIALS="/path/to/your/service-account-key.json"
    ```
    **Important**: Replace `your-gcp-project-id` with your actual Google Cloud Project ID. For `ANALYSIS_WORKER_URL`, if you don't have a deployed worker, you can use a placeholder like `http://localhost:8001` for local testing, but remember to update it for integration testing.

## 5. Run the Application

Start the FastAPI application using Uvicorn:

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

-   `main:app`: Refers to the `app` object inside `main.py`.
-   `--reload`: Enables auto-reloading on code changes (useful for development).
-   `--host 0.0.0.0`: Makes the server accessible from all network interfaces.
-   `--port 8000`: Runs the server on port 8000.

Once started, you should see output similar to:

```
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
INFO:     Started reloader process [PID] using statreload
INFO:     Started server process [PID]
INFO:     Waiting for application startup.
GeoWatch Backend API starting up...
INFO:     Application startup complete.
```

## 6. Access API Documentation

While the server is running, you can access the interactive API documentation:

-   **Swagger UI**: `http://localhost:8000/docs`
-   **ReDoc**: `http://localhost:8000/redoc`

## 7. Testing Endpoints

You can test the API endpoints using tools like `curl`, Postman, Insomnia, or directly from the Swagger UI.

### Example: Health Check

```bash
curl http://localhost:8000/api/health
# Expected output: {"status":"healthy"}
```

### Example: Create Monitoring Area

```bash
curl -X POST \
  http://localhost:8000/api/monitoring-areas \
  -H 'Content-Type: application/json' \
  -d '{
    "name": "Amazon Rainforest",
    "type": "forest",
    "rectangle_bounds": {
      "southWest": { "lat": -4.0, "lng": -70.0 },
      "northEast": { "lat": -3.0, "lng": -69.0 }
    }
  }'
```

This concludes the setup for local development. You can now start interacting with your GeoWatch Backend API!
