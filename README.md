# GeoWatch - Satellite Monitoring Platform

**Real-time environmental monitoring using satellite imagery and AI-powered analysis**

GeoWatch is a cloud-native platform that enables users to monitor environmental changes (forest cover, water bodies) using Sentinel-2 satellite imagery from Google Earth Engine. The system automatically detects changes, generates AI-powered reports, and provides an intuitive web interface for visualization.

---

## 🏗️ Architecture Overview

### System Components

GeoWatch consists of **4 microservices** deployed on **Google Cloud Run**, backed by **Firestore** for data storage and **Cloud Storage** for image assets:

```
┌─────────────────────────────────────────────────────────────────┐
│                         Frontend (React)                        │
│                    Cloud Run Service #1                         │
│  - User interface for creating monitoring areas                 │
│  - Visualizes analysis results and change detection maps        │
│  - Displays AI-generated reports                                │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTPS/REST API
                         ▼
┌─────────────────────────────────────────────────────────────────┐
│                     Backend API (FastAPI)                       │
│                    Cloud Run Service #2                         │
│  - Manages monitoring areas and analysis results                │
│  - Orchestrates worker services                                 │
│  - Handles callbacks from workers                               │
│  - Serves reports to frontend                                   │
└──────┬──────────────────────────────────────────┬───────────────┘
       │                                          │
       │ Triggers analysis                        │ Triggers report
       ▼                                          ▼
┌──────────────────────────┐          ┌──────────────────────────┐
│  Analysis Worker         │          │  Report Worker           │
│  Cloud Run Service #3    │          │  Cloud Run Service #4    │
│                          │          │                          │
│  - Fetches Sentinel-2    │          │  - Generates reports     │
│    imagery from GEE      │          │    using Gemini AI       │
│  - Performs change       │          │  - Summarizes findings   │
│    detection             │          │  - Provides insights     │
│  - Exports maps to GCS   │          │  - Sends callback        │
│  - Sends callback        │          │                          │
└──────┬───────────────────┘          └──────────┬───────────────┘
       │                                         │
       └─────────────┬───────────────────────────┘
                     ▼
         ┌───────────────────────┐
         │   Google Cloud        │
         │   Infrastructure      │
         │                       │
         │  • Firestore          │  ← Data storage
         │  • Cloud Storage      │  ← Image storage
         │  • Earth Engine       │  ← Satellite data
         │  • Gemini AI          │  ← Report generation
         └───────────────────────┘
```

---

## 🔧 Google Cloud Products Used

### 1. **Cloud Run** (4 Services)

**Purpose:** Serverless container platform for all microservices

| Service | Purpose | Resources | Auto-scaling |
|---------|---------|-----------|-------------|
| **Frontend** | React web app served via Nginx | 1 CPU, 1GB RAM | 0-10 instances |
| **Backend** | FastAPI orchestrator | 2 CPU, 2GB RAM | 1-5 instances |
| **Analysis Worker** | Earth Engine processing | 4 CPU, 4GB RAM | 1-3 instances |
| **Report Worker** | Gemini AI report generation | 2 CPU, 2GB RAM | 0-2 instances |

**Benefits:**
- Pay-per-use pricing (scales to zero when idle)
- Automatic HTTPS endpoints
- Built-in load balancing
- Zero infrastructure management

### 2. **Firestore** (NoSQL Database)

**Purpose:** Primary data store for all application data

**Collections:**
- `monitoring_areas` - User-defined regions to monitor
- `analysis_results` - Change detection results with metrics
- `analysis_reports` - AI-generated reports

**Why Firestore:**
- Real-time synchronization
- Automatic scaling
- Strong consistency
- Native GCP integration
- Async Python SDK support

### 3. **Cloud Storage** (Object Storage)

**Purpose:** Store exported satellite imagery and analysis maps

**Bucket:** `geowatch-cloudrun-476105`

**Stored Assets:**
- Baseline satellite images (GeoTIFF)
- Current satellite images (GeoTIFF)
- Difference/change masks (GeoTIFF)
- RGB composites for visualization

**Why Cloud Storage:**
- Cost-effective for large files
- Direct integration with Earth Engine exports
- Public URL generation for frontend display
- Lifecycle management for old data

### 4. **Google Earth Engine**

**Purpose:** Access and process Sentinel-2 satellite imagery

**Capabilities:**
- Query Sentinel-2 SR Harmonized collection
- Filter by date, location, and cloud coverage
- Compute NDVI (vegetation) and MNDWI (water) indices
- Perform cloud masking
- Create median composites
- Export results to Cloud Storage

**Data Source:** `COPERNICUS/S2_SR_HARMONIZED` (10m resolution)

### 5. **Gemini AI (Vertex AI)**

**Purpose:** Generate natural language reports from analysis data

**Model:** `gemini-1.5-flash`

**Capabilities:**
- Summarize change detection results
- Identify key findings and trends
- Provide actionable recommendations
- Generate markdown-formatted reports

---

## 🔄 Service Communication Flow

### 1. **User Creates Monitoring Area**

```
Frontend → Backend → Firestore
                  ↓
            Analysis Worker (triggered)
```

1. User draws rectangle on map
2. Frontend sends `POST /api/monitoring-areas`
3. Backend validates area (1-500 km²)
4. Backend stores in Firestore with status `pending`
5. Backend triggers Analysis Worker via HTTP POST

### 2. **Analysis Worker Processes Imagery**

```
Analysis Worker → Earth Engine → Cloud Storage → Backend (callback)
```

1. Worker receives analysis request
2. Initializes Earth Engine with service account
3. Fetches Sentinel-2 imagery (baseline + current)
4. Applies cloud masking
5. Computes change detection (NDVI/MNDWI)
6. Exports 4 images to Cloud Storage as GeoTIFFs
7. Sends callback to Backend with results
8. Backend updates Firestore with status `completed`

### 3. **Report Worker Generates Insights**

```
Backend → Report Worker → Gemini AI → Firestore → Backend (callback)
```

1. Backend triggers Report Worker after analysis completes
2. Worker fetches analysis data from Firestore
3. Constructs prompt with metrics and historical context
4. Calls Gemini AI API for report generation
5. Parses JSON response (summary, findings, recommendations)
6. Saves report to Firestore
7. Sends callback to Backend

### 4. **Frontend Displays Results**

```
Frontend → Backend → Firestore/Cloud Storage
```

1. Frontend polls `GET /api/monitoring-areas/{id}`
2. Backend returns area with latest analysis result
3. Frontend fetches images from Cloud Storage URLs
4. Frontend displays change maps and metrics
5. Frontend fetches report via `GET /api/reports/{id}`

---

## 📊 Data Flow

### Monitoring Area Lifecycle

```
1. CREATE → status: pending
   ↓
2. ANALYSIS TRIGGERED → status: pending
   ↓
3. ANALYSIS IN PROGRESS → processing_status: in_progress
   ↓
4. ANALYSIS COMPLETE → status: active, processing_status: completed
   ↓
5. REPORT GENERATED → report_id attached
```

### Analysis Result Structure

```json
{
  "result_id": "res_abc123",
  "area_id": "area_xyz789",
  "processing_status": "completed",
  "metrics": {
    "baseline_date": "2024-01",
    "current_date": "2024-11",
    "analysis_type": "forest",
    "loss_hectares": 12.5,
    "gain_hectares": 3.2,
    "net_change_percentage": -8.4
  },
  "image_urls": {
    "baseline_image": "gs://bucket/baseline.tif",
    "current_image": "gs://bucket/current.tif",
    "difference_image": "gs://bucket/diff.tif",
    "rgb_composite": "gs://bucket/rgb.tif"
  },
  "report_id": "report_def456"
}
```

---

## 🚀 Deployment

### Prerequisites

- Google Cloud Project with billing enabled
- APIs enabled: Cloud Run, Firestore, Cloud Storage, Earth Engine, Vertex AI
- Service account with roles:
  - `roles/run.invoker`
  - `roles/datastore.user`
  - `roles/storage.objectAdmin`
  - `roles/earthengine.writer`
  - `roles/aiplatform.user`

### Deploy Services

**1. Backend**
```bash
cd backend
gcloud run deploy geowatch-backend \
  --source . \
  --region europe-west1 \
  --memory 2Gi --cpu 2 \
  --min-instances 1 --max-instances 5 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=your-project
```

**2. Analysis Worker**
```bash
cd analysis-worker
gcloud run deploy geowatch-analysis-worker \
  --source . \
  --region europe-west1 \
  --memory 4Gi --cpu 4 --timeout 1800 \
  --min-instances 1 --max-instances 3 \
  --set-env-vars BACKEND_ENV=production,BACKEND_API_URL=<backend-url>/api
```

**3. Report Worker**
```bash
cd report-worker
gcloud run deploy geowatch-report-worker \
  --source . \
  --region europe-west1 \
  --memory 2Gi --cpu 2 \
  --min-instances 0 --max-instances 2 \
  --set-env-vars BACKEND_ENV=production,BACKEND_API_URL=<backend-url>/api
```

**4. Frontend**
```bash
cd frontend
gcloud run deploy geowatch-frontend \
  --source . \
  --region europe-west1 \
  --memory 1Gi --cpu 1 \
  --min-instances 0 --max-instances 10
```

---

## 🔐 Security

- **CORS:** Backend restricts origins to frontend domain only
- **Service-to-Service Auth:** Workers use OIDC tokens for callbacks
- **IAM:** Least-privilege service account per service
- **Secrets:** Environment variables injected via Cloud Run
- **Public Access:** Frontend and Backend allow unauthenticated (for demo)

---

## 📈 Monitoring & Costs

### Observability

- **Cloud Logging:** All services log to Cloud Logging
- **Cloud Monitoring:** CPU, memory, request metrics
- **Error Reporting:** Automatic error aggregation

### Estimated Monthly Costs (Light Usage)

| Service | Cost |
|---------|------|
| Cloud Run (4 services) | $30-50 |
| Firestore | $5-10 |
| Cloud Storage | $2-5 |
| Earth Engine | Free (public data) |
| Gemini AI | $5-15 |
| **Total** | **~$50-80/month** |

*Scales with usage. Heavy usage could reach $200-300/month.*

---

## 🛠️ Technology Stack

**Backend:** Python 3.11, FastAPI, Pydantic, httpx  
**Analysis Worker:** Python 3.10, Earth Engine API, NumPy  
**Report Worker:** Python 3.11, Gemini AI SDK  
**Frontend:** React 18, TypeScript, Vite, Leaflet, Axios  
**Infrastructure:** Docker, Cloud Run, Firestore, Cloud Storage  

---

## 📝 API Endpoints

### Backend API

- `GET /api/health` - Health check
- `GET /api/monitoring-areas` - List all areas
- `POST /api/monitoring-areas` - Create new area
- `GET /api/monitoring-areas/{id}` - Get area details
- `PATCH /api/monitoring-areas/{id}` - Update area name
- `DELETE /api/monitoring-areas/{id}` - Soft delete area
- `GET /api/monitoring-areas/{id}/latest` - Get latest result
- `POST /api/callbacks/analysis-complete` - Analysis callback
- `POST /api/callbacks/report-complete` - Report callback
- `GET /api/reports/{id}` - Get report by ID

---

## 📄 License

MIT License - See LICENSE file for details

---

## 👥 Contributors

Built with ❤️ using Google Cloud Platform