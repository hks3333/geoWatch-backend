# Backend Production Setup - Complete Guide

## Overview

The Backend is the orchestrator for your GeoWatch system. It:
- ✅ Receives API requests from the frontend
- ✅ Manages monitoring areas and analysis results
- ✅ Communicates with Analysis Worker (triggers analysis)
- ✅ Communicates with Report Worker (triggers report generation)
- ✅ Stores/retrieves data from Firestore

---

## Code Changes for Production

### What Changed?

1. **Environment-Aware Configuration**
   - `BACKEND_ENV=local` → Uses localhost URLs, allows all CORS origins
   - `BACKEND_ENV=production` → Uses Cloud Run URLs, restricts CORS origins

2. **Improved Logging**
   - Startup logs show configuration
   - Worker client initialization tracked
   - Better error messages

3. **Proper Lifespan Management**
   - Worker client initialized on startup
   - Worker client closed on shutdown
   - Graceful error handling

### Files Modified

- `backend/main.py` - Added environment-aware CORS, logging, lifespan
- `backend/app/config.py` - Added URL validation, environment defaults

---

## Environment Variables

### Local Development (.env)

```bash
# backend/.env
GCP_PROJECT_ID="cloudrun-476105"
BACKEND_ENV="local"
ANALYSIS_WORKER_URL="http://localhost:8001"
REPORT_WORKER_URL="http://localhost:8002"
```

### Production (.env.production)

```bash
# backend/.env.production
GCP_PROJECT_ID="cloudrun-476105"
BACKEND_ENV="production"
ANALYSIS_WORKER_URL="https://geowatch-analysis-worker.run.app"
REPORT_WORKER_URL="https://geowatch-report-worker.run.app"
```

---

## How It Communicates with Other Services

### 1. Analysis Worker Communication

**When:** User triggers analysis
**How:** Backend sends HTTP POST to Analysis Worker

```
Frontend → Backend (/api/trigger-analysis)
           ↓
           Backend → Analysis Worker (/analyze)
           ↓
           Analysis Worker processes
           ↓
           Analysis Worker → Backend (/api/callbacks/analysis-complete)
           ↓
           Backend updates Firestore
           ↓
           Frontend polls and gets results
```

**Code Location:** `backend/app/services/worker_client.py`

```python
async def trigger_analysis(self, area_id, result_id, polygon, area_type, is_baseline):
    endpoint = f"{self.worker_url}/analyze"
    response = await self.client.post(endpoint, json=payload, timeout=30.0)
```

### 2. Report Worker Communication

**When:** Analysis completes, report generation triggered
**How:** Backend sends HTTP POST to Report Worker

```
Analysis Worker → Backend (/api/callbacks/analysis-complete)
                  ↓
                  Backend → Report Worker (/generate-report)
                  ↓
                  Report Worker generates report
                  ↓
                  Report Worker → Backend (/api/callbacks/report-complete)
                  ↓
                  Backend updates Firestore
```

**Code Location:** `backend/app/routes/callbacks.py`

### 3. Firestore Communication

**When:** Always
**How:** Direct Firestore SDK calls

```
Backend ↔ Firestore
- Read: monitoring areas, analysis results
- Write: create results, update status, store callbacks
```

---

## Step-by-Step Production Setup

### Step 1: Update Environment Variables

```bash
# Update backend/.env with production values
BACKEND_ENV="production"
ANALYSIS_WORKER_URL="https://geowatch-analysis-worker.run.app"
REPORT_WORKER_URL="https://geowatch-report-worker.run.app"
```

### Step 2: Build Docker Image

```bash
# From project root
gcloud builds submit \
  --config backend/cloudbuild.yaml \
  --project cloudrun-476105
```

**What this does:**
- Builds Docker image from `backend/Dockerfile`
- Pushes to `gcr.io/cloudrun-476105/geowatch-backend:latest`

### Step 3: Deploy to Cloud Run

```bash
gcloud run deploy geowatch-backend \
  --image gcr.io/cloudrun-476105/geowatch-backend:latest \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 5 \
  --min-instances 1 \
  --timeout 600 \
  --set-env-vars \
    BACKEND_ENV=production,\
    GCP_PROJECT_ID=cloudrun-476105,\
    ANALYSIS_WORKER_URL=https://geowatch-analysis-worker.run.app,\
    REPORT_WORKER_URL=https://geowatch-report-worker.run.app \
  --service-account geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --project cloudrun-476105
```

**Configuration Explained:**
- `--memory 2Gi` - 2GB RAM (sufficient for API)
- `--cpu 2` - 2 CPU cores (handles ~400 concurrent requests)
- `--max-instances 5` - Max 5 instances for cost control
- `--min-instances 1` - Keep 1 warm for fast response
- `--timeout 600` - 10 minute timeout for long operations
- `--allow-unauthenticated` - Allow frontend to call without auth

### Step 4: Get Backend URL

```bash
BACKEND_URL=$(gcloud run services describe geowatch-backend \
  --platform managed \
  --region us-central1 \
  --format 'value(status.url)' \
  --project cloudrun-476105)

echo "Backend URL: $BACKEND_URL"
# Output: https://geowatch-backend-XXXXX.run.app
```

**Save this URL** - You'll need it for other services!

### Step 5: Verify Deployment

```bash
# Test health endpoint
curl $BACKEND_URL/health

# Expected response:
# {"status": "healthy"}

# View startup logs
gcloud run services logs read geowatch-backend \
  --limit 50 \
  --region us-central1
```

---

## Service-to-Service Communication Setup

### For Analysis Worker to Call Backend

**Analysis Worker needs to know the Backend URL:**

```bash
# When deploying Analysis Worker, set:
BACKEND_API_URL="https://geowatch-backend-XXXXX.run.app/api"
```

### For Report Worker to Call Backend

**Report Worker needs to know the Backend URL:**

```bash
# When deploying Report Worker, set:
BACKEND_API_URL="https://geowatch-backend-XXXXX.run.app/api"
```

### For Frontend to Call Backend

**Frontend needs to know the Backend URL:**

```bash
# When deploying Frontend, set:
VITE_API_URL="https://geowatch-backend-XXXXX.run.app/api"
```

---

## Communication Flow Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        Frontend                             │
│                    (React Web App)                          │
│                                                             │
│  VITE_API_URL=https://geowatch-backend.run.app/api        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────┐
│                       Backend                               │
│                   (FastAPI Server)                          │
│                                                             │
│  BACKEND_ENV=production                                    │
│  ANALYSIS_WORKER_URL=https://geowatch-analysis-worker...  │
│  REPORT_WORKER_URL=https://geowatch-report-worker...      │
│                                                             │
│  ✅ Receives requests from Frontend                        │
│  ✅ Triggers Analysis Worker                              │
│  ✅ Triggers Report Worker                                │
│  ✅ Receives callbacks from Workers                        │
│  ✅ Stores/retrieves from Firestore                        │
└────────────┬────────────────────────────────┬──────────────┘
             │                                │
             ▼                                ▼
    ┌──────────────────────┐        ┌──────────────────────┐
    │ Analysis Worker      │        │  Report Worker       │
    │ (Earth Engine)       │        │  (Gemini AI)         │
    │                      │        │                      │
    │ BACKEND_API_URL=     │        │ BACKEND_API_URL=     │
    │ https://geowatch-... │        │ https://geowatch-... │
    └──────────────────────┘        └──────────────────────┘
             │                                │
             └────────────┬───────────────────┘
                          ▼
                  ┌──────────────────┐
                  │  Firestore       │
                  │  (Data Storage)  │
                  └──────────────────┘
```

---

## CORS Configuration

### Local Mode (BACKEND_ENV=local)

```python
# Allows all origins
allowed_origins = ["*"]
```

**Use for:** Local development with multiple frontend ports

### Production Mode (BACKEND_ENV=production)

```python
# Restricts to specific origins
allowed_origins = [
    "https://geowatch-frontend.run.app",
    "https://yourdomain.com",  # Your custom domain
]
```

**Use for:** Production with specific frontend URL

**To add more origins:**

Edit `backend/main.py` and add to the list:

```python
allowed_origins = [
    "https://geowatch-frontend.run.app",
    "https://yourdomain.com",
    "https://another-domain.com",  # Add here
]
```

Then redeploy.

---

## Monitoring & Debugging

### View Logs

```bash
# View recent logs
gcloud run services logs read geowatch-backend \
  --limit 100 \
  --region us-central1

# Stream live logs
gcloud run services logs read geowatch-backend \
  --limit 50 \
  --follow \
  --region us-central1

# Filter by severity
gcloud run services logs read geowatch-backend \
  --limit 100 \
  --region us-central1 \
  --filter 'severity=ERROR'
```

### Check Service Status

```bash
# View service details
gcloud run services describe geowatch-backend \
  --platform managed \
  --region us-central1

# View active revisions
gcloud run revisions list \
  --service geowatch-backend \
  --region us-central1

# View metrics
gcloud run services describe geowatch-backend \
  --platform managed \
  --region us-central1 \
  --format 'value(status.traffic[0].percent)'
```

### Test Endpoints

```bash
# Health check
curl https://geowatch-backend.run.app/health

# Get monitoring areas
curl https://geowatch-backend.run.app/api/monitoring-areas

# Get API docs
curl https://geowatch-backend.run.app/docs
```

---

## Troubleshooting

### Issue: "Service Unavailable" on Startup

**Cause:** Worker URLs are unreachable

**Fix:**
1. Verify Analysis Worker is deployed
2. Verify Report Worker is deployed
3. Check environment variables are correct
4. View logs: `gcloud run services logs read geowatch-backend --limit 50`

### Issue: CORS Errors in Frontend

**Cause:** Frontend origin not in allowed list

**Fix:**
1. Check frontend URL
2. Add to `allowed_origins` in `backend/main.py`
3. Redeploy backend

### Issue: Callbacks Not Received

**Cause:** Workers can't reach backend URL

**Fix:**
1. Verify `BACKEND_API_URL` in worker services
2. Test: `curl https://geowatch-backend.run.app/health`
3. Check firewall rules (should be open)

### Issue: High Latency

**Cause:** Not enough instances

**Fix:**
```bash
# Increase min instances to keep warm
gcloud run services update geowatch-backend \
  --min-instances 2 \
  --region us-central1
```

---

## Scaling Configuration

### Current Setup

- **Min instances:** 1 (cost-optimized)
- **Max instances:** 5 (handles ~400 concurrent requests)
- **CPU:** 2 cores
- **Memory:** 2GB

### For Higher Load

```bash
# Increase max instances
gcloud run services update geowatch-backend \
  --max-instances 10 \
  --region us-central1

# Increase CPU/Memory
gcloud run services update geowatch-backend \
  --cpu 4 \
  --memory 4Gi \
  --region us-central1

# Keep more instances warm
gcloud run services update geowatch-backend \
  --min-instances 2 \
  --region us-central1
```

---

## Rollback

### If Something Goes Wrong

```bash
# View previous revisions
gcloud run revisions list \
  --service geowatch-backend \
  --region us-central1

# Rollback to previous revision
gcloud run services update-traffic geowatch-backend \
  --to-revisions REVISION_ID=100 \
  --region us-central1

# Or redeploy from git
git checkout PREVIOUS_COMMIT
gcloud builds submit --config backend/cloudbuild.yaml
```

---

## Summary

✅ **Backend is production-ready**
- Environment-aware configuration
- Proper service-to-service communication
- Logging and monitoring
- CORS security
- Graceful startup/shutdown

✅ **Communication Setup**
- Analysis Worker → Backend (trigger analysis)
- Report Worker → Backend (trigger reports)
- Backend → Workers (callbacks)
- Frontend → Backend (API calls)

✅ **Deployment**
- Build with Cloud Build
- Deploy to Cloud Run
- Auto-scales 1-5 instances
- Handles ~400 concurrent requests

**Next:** Deploy Analysis Worker with correct Backend URL!
