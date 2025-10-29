You are helping me build the backend API for GeoWatch, a satellite monitoring application. I'm using Python FastAPI, Google Cloud Firestore, and Cloud Storage. This backend will be deployed in google cloud run.

# PROJECT CONTEXT

GeoWatch monitors environmental changes using satellite imagery. Users create monitoring areas (rectangles on a map), and the system automatically analyzes satellite images every 5 days to detect forest loss or water changes.

# ARCHITECTURE

The backend API is one of 5 Cloud Run services:
1. Frontend (React) - calls this backend
2. **Backend API (FastAPI)** ← WE'RE BUILDING THIS
3. Cron Job - triggers scheduled analyses
4. Analysis Worker (GPU) - processes satellite imagery
5. Report Generator - creates natural language reports

The backend orchestrates everything. It does NOT do the heavy processing - it delegates to the Analysis Worker.

# TECH STACK

- Python 3.11
- FastAPI
- Google Cloud Firestore (database)
- Google Cloud Storage (image storage)
- Pydantic (data validation)
- httpx (async HTTP client for service-to-service calls)

# DATA MODELS

## Firestore Collections

**Collection: monitoring_areas**
```
{
  area_id: string (auto-generated)
  name: string
  type: "forest" | "water"
  rectangle_bounds: {
    southWest: { lat: number, lng: number },
    northEast: { lat: number, lng: number }
  }
  polygon: [[lng, lat], ...] (4 points, computed from rectangle)
  status: "active" | "pending" | "paused" | "error"
  created_at: timestamp
  last_checked_at: timestamp | null
  baseline_captured: boolean
  total_analyses: number
}
```

**Collection: analysis_results**
```
{
  result_id: string (auto-generated)
  area_id: string (reference to monitoring_areas)
  timestamp: timestamp
  baseline_date: string (ISO date)
  current_date: string (ISO date)
  change_detected: boolean
  change_type: "forest" | "water"
  statistics: {
    loss_hectares: number,
    gain_hectares: number,
    change_percentage: number
  }
  images: {
    baseline: string (Cloud Storage URL),
    current: string (Cloud Storage URL),
    change_mask: string (Cloud Storage URL)
  }
  confidence: number (0.0 to 1.0)
  report_text: string | null (populated by Report Generator)
  processing_status: "in_progress" | "completed" | "failed"
  error_message: string | null
}
```

# API ENDPOINTS TO IMPLEMENT

1. **GET /health**
   - Returns: `{"status": "healthy"}`

2. **POST /monitoring-areas**
   - Body: `{name, type, rectangle_bounds}`
   - Validates input (area size 1-100 km²)
   - Converts rectangle to 4-point polygon
   - Stores in Firestore
   - **Immediately triggers first analysis** (async call to Analysis Worker)
   - Returns: 202 Accepted with area_id

3. **GET /monitoring-areas**
   - Returns: List of all areas with latest status

4. **GET /monitoring-areas/{area_id}**
   - Returns: Single area details

5. **GET /monitoring-areas/{area_id}/results**
   - Query params: `?limit=10&offset=0`
   - Returns: Paginated analysis results
   - Includes: `analysis_in_progress` flag

6. **POST /monitoring-areas/{area_id}/analyze**
   - Triggers new analysis
   - Makes async call to Analysis Worker
   - Returns: 202 Accepted immediately

7. **DELETE /monitoring-areas/{area_id}**
   - Soft delete (set status to "deleted")
   - Returns: confirmation

# SERVICE COMMUNICATION

When triggering analysis, the backend calls:
```
POST https://analysis-worker-xyz.run.app/analyze
Authorization: Bearer {service_account_token}

Body:
{
  "area_id": "abc123",
  "polygon": [[lng, lat], ...],
  "type": "forest",
  "is_baseline": false
}
```

# PROJECT STRUCTURE

Create this folder structure:
```
backend/
├── main.py                     # FastAPI app
├── requirements.txt
├── Dockerfile
├── .env.example
├── app/
│   ├── __init__.py
│   ├── config.py              # Environment variables
│   ├── models/
│   │   ├── __init__.py
│   │   ├── monitoring_area.py # Pydantic models
│   │   └── analysis_result.py
│   ├── routes/
│   │   ├── __init__.py
│   │   ├── monitoring_areas.py # Area CRUD endpoints
│   │   ├── analysis.py         # Analysis trigger endpoints
│   │   └── health.py           # Health check
│   ├── services/
│   │   ├── __init__.py
│   │   ├── firestore_service.py # Database operations
│   │   ├── storage_service.py   # Cloud Storage operations
│   │   └── worker_client.py     # Call Analysis Worker
│   └── utils/
│       ├── __init__.py
│       ├── validators.py        # Input validation
│       └── geometry.py          # Rectangle → Polygon conversion
└── tests/
    ├── test_monitoring_areas.py
    └── test_geometry.py
```

# STEP-BY-STEP INSTRUCTIONS

I want you to guide me through building this backend, one file at a time, with:

1. Complete, production-ready code (no placeholders)
2. Error handling for all edge cases
3. Proper logging
4. Type hints and docstrings
5. Input validation with Pydantic
6. Async operations where appropriate

Start with:
1. Project setup (requirements.txt, folder structure)
2. Configuration (environment variables)
3. Firestore service (database operations)
4. Pydantic models
5. Route handlers (one endpoint at a time)
6. Worker client (service-to-service communication)
7. Main app (FastAPI setup with CORS, middleware)
8. Dockerfile for Cloud Run deployment
9. Local testing instructions

For each file, explain:
- What the code does
- Why it's structured that way
- How it fits into the overall system
- Any potential issues to watch for

Let's start with step 1: Project setup and requirements.txt