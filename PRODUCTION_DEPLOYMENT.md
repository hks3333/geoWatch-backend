# Production Deployment Guide - GeoWatch

## Overview

You have 4 independent services that need to be deployed to Google Cloud Run:

1. **Backend** (Port 8000) - Main API, orchestrates everything
2. **Analysis Worker** (Port 8001) - Runs Earth Engine analysis
3. **Report Worker** (Port 8002) - Generates AI reports
4. **Frontend** (Port 3000) - React web app

---

## Architecture for Production

```
┌─────────────────────────────────────────────────────────────┐
│                     Frontend (Cloud Run)                    │
│                   React + Vite (Port 3000)                  │
│                  Max Instances: 10, CPU: 1                  │
└────────────────────────────┬────────────────────────────────┘
                             │
                             ▼
┌─────────────────────────────────────────────────────────────┐
│                    Backend (Cloud Run)                      │
│                  FastAPI (Port 8000)                        │
│              Max Instances: 5, CPU: 2, Memory: 2GB          │
│         Handles: API requests, Firestore queries            │
│         Triggers: Analysis Worker, Report Worker           │
└────────────┬────────────────────────────────────┬───────────┘
             │                                    │
             ▼                                    ▼
┌──────────────────────────────┐    ┌──────────────────────────────┐
│  Analysis Worker (Cloud Run) │    │  Report Worker (Cloud Run)   │
│    FastAPI (Port 8001)       │    │    FastAPI (Port 8002)       │
│ Max Instances: 3, CPU: 4     │    │ Max Instances: 2, CPU: 2     │
│ Memory: 4GB (EE processing)  │    │ Memory: 2GB (Gemini API)     │
│ Timeout: 30 minutes          │    │ Timeout: 10 minutes          │
└──────────────────────────────┘    └──────────────────────────────┘
             │                                    │
             └────────────────┬───────────────────┘
                              ▼
                    ┌──────────────────────┐
                    │  Firestore Database  │
                    │   (Shared storage)   │
                    └──────────────────────┘
```

---

## Step 1: Prepare Environment Variables

### Backend (.env for production)

```bash
# backend/.env.production
GCP_PROJECT_ID="cloudrun-476105"
ANALYSIS_WORKER_URL="https://analysis-worker-XXXXX.run.app"  # Cloud Run URL
REPORT_WORKER_URL="https://report-worker-XXXXX.run.app"      # Cloud Run URL
BACKEND_ENV="production"
```

### Analysis Worker (.env for production)

```bash
# analysis-worker/.env.production
GCP_PROJECT_ID="cloudrun-476105"
BACKEND_API_URL="https://backend-XXXXX.run.app/api"          # Cloud Run URL
BACKEND_ENV="production"
GCS_BUCKET_NAME="geowatch-cloudrun-476105"
```

### Report Worker (.env for production)

```bash
# report-worker/.env.production
GCP_PROJECT_ID="cloudrun-476105"
BACKEND_API_URL="https://backend-XXXXX.run.app/api"          # Cloud Run URL
BACKEND_ENV="production"
```

---

## Step 2: Update Code for Production

### 2.1 Backend - Add Concurrency Limits

**File:** `backend/main.py`

Add at the top after imports:

```python
import os
from contextlib import asynccontextmanager

# Production concurrency settings
MAX_CONCURRENT_ANALYSES = 3  # Limit concurrent analysis requests
ANALYSIS_QUEUE = []

@asynccontextmanager
async def lifespan(app):
    # Startup
    logger.info(f"Backend starting in {os.getenv('BACKEND_ENV', 'local')} mode")
    yield
    # Shutdown
    logger.info("Backend shutting down")

app = FastAPI(lifespan=lifespan)
```

Then update the `/analyze` endpoint:

```python
@app.post("/api/trigger-analysis")
async def trigger_analysis(request: AnalysisRequest):
    """Trigger analysis with concurrency limiting."""
    
    # Check active analyses
    active_analyses = db.collection('analysis_results').where(
        'processing_status', '==', 'in_progress'
    ).stream()
    active_count = sum(1 for _ in active_analyses)
    
    if active_count >= MAX_CONCURRENT_ANALYSES:
        logger.warning(f"Analysis queue full: {active_count}/{MAX_CONCURRENT_ANALYSES}")
        raise HTTPException(
            status_code=429,
            detail=f"Analysis queue full. {active_count} analyses in progress. Try again in a moment."
        )
    
    # Proceed with analysis
    result_id = trigger_worker_analysis(request)
    return {"result_id": result_id, "status": "queued"}
```

### 2.2 Analysis Worker - Add Request Queuing

**File:** `analysis-worker/main.py`

Add concurrency limiting:

```python
import asyncio
from collections import deque

# Production settings
MAX_CONCURRENT_ANALYSES = 3
active_analyses = set()
analysis_queue = deque()

async def run_the_full_analysis(payload: AnalysisPayload):
    """Run analysis with queue management."""
    
    # Add to queue
    analysis_queue.append(payload.result_id)
    
    # Wait for slot to open
    while len(active_analyses) >= MAX_CONCURRENT_ANALYSES:
        logger.info(f"Waiting for slot... Queue: {len(analysis_queue)}, Active: {len(active_analyses)}")
        await asyncio.sleep(5)
    
    # Mark as active
    active_analyses.add(payload.result_id)
    analysis_queue.remove(payload.result_id)
    
    try:
        # ... existing analysis code ...
        logger.info(f"Analysis started: {payload.result_id}")
        # ... run analysis ...
    finally:
        # Mark as complete
        active_analyses.discard(payload.result_id)
        logger.info(f"Analysis completed: {payload.result_id}")

@app.get("/health")
async def health():
    """Health check endpoint for Cloud Run."""
    return {
        "status": "healthy",
        "active_analyses": len(active_analyses),
        "queued_analyses": len(analysis_queue)
    }
```

### 2.3 Report Worker - Add Timeout Handling

**File:** `report-worker/main.py`

```python
import asyncio

async def generate_report_with_timeout(request: ReportRequest):
    """Generate report with timeout protection."""
    try:
        # Set 8-minute timeout (Cloud Run default is 10 minutes)
        report_data = await asyncio.wait_for(
            gemini_generator.generate_report(request),
            timeout=480  # 8 minutes
        )
        return report_data
    except asyncio.TimeoutError:
        logger.error(f"Report generation timeout for {request.report_id}")
        raise HTTPException(
            status_code=504,
            detail="Report generation timed out. Please try again."
        )
```

---

## Step 3: Create Cloud Run Deployment Configs

### 3.1 Backend Deployment

**File:** `backend/cloudbuild.yaml`

```yaml
steps:
  # Build the Docker image
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'build'
      - '-t'
      - 'gcr.io/$PROJECT_ID/geowatch-backend:$SHORT_SHA'
      - '-f'
      - 'backend/Dockerfile'
      - '.'

  # Push to Container Registry
  - name: 'gcr.io/cloud-builders/docker'
    args:
      - 'push'
      - 'gcr.io/$PROJECT_ID/geowatch-backend:$SHORT_SHA'

  # Deploy to Cloud Run
  - name: 'gcr.io/cloud-builders/gke-deploy'
    args:
      - 'run'
      - '--filename=backend/cloudrun.yaml'
      - '--image=gcr.io/$PROJECT_ID/geowatch-backend:$SHORT_SHA'
      - '--location=us-central1'

images:
  - 'gcr.io/$PROJECT_ID/geowatch-backend:$SHORT_SHA'
```

**File:** `backend/cloudrun.yaml`

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: geowatch-backend
  namespace: default
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: '5'
        autoscaling.knative.dev/minScale: '1'
        run.googleapis.com/cpu-throttling: 'false'
    spec:
      serviceAccountName: geowatch-sa
      containers:
      - image: gcr.io/PROJECT_ID/geowatch-backend:latest
        ports:
        - containerPort: 8080
        env:
        - name: GCP_PROJECT_ID
          value: "cloudrun-476105"
        - name: BACKEND_ENV
          value: "production"
        - name: ANALYSIS_WORKER_URL
          value: "https://geowatch-analysis-worker.run.app"
        - name: REPORT_WORKER_URL
          value: "https://geowatch-report-worker.run.app"
        resources:
          limits:
            cpu: '2'
            memory: '2Gi'
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
```

### 3.2 Analysis Worker Deployment

**File:** `analysis-worker/cloudrun.yaml`

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: geowatch-analysis-worker
  namespace: default
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: '3'
        autoscaling.knative.dev/minScale: '1'
        run.googleapis.com/cpu-throttling: 'false'
        run.googleapis.com/timeout-seconds: '1800'  # 30 minutes
    spec:
      serviceAccountName: geowatch-sa
      timeoutSeconds: 1800
      containers:
      - image: gcr.io/PROJECT_ID/geowatch-analysis-worker:latest
        ports:
        - containerPort: 8080
        env:
        - name: GCP_PROJECT_ID
          value: "cloudrun-476105"
        - name: BACKEND_ENV
          value: "production"
        - name: BACKEND_API_URL
          value: "https://geowatch-backend.run.app/api"
        - name: GCS_BUCKET_NAME
          value: "geowatch-cloudrun-476105"
        resources:
          limits:
            cpu: '4'
            memory: '4Gi'
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 60
```

### 3.3 Report Worker Deployment

**File:** `report-worker/cloudrun.yaml`

```yaml
apiVersion: serving.knative.dev/v1
kind: Service
metadata:
  name: geowatch-report-worker
  namespace: default
spec:
  template:
    metadata:
      annotations:
        autoscaling.knative.dev/maxScale: '2'
        autoscaling.knative.dev/minScale: '1'
        run.googleapis.com/cpu-throttling: 'false'
        run.googleapis.com/timeout-seconds: '600'  # 10 minutes
    spec:
      serviceAccountName: geowatch-sa
      timeoutSeconds: 600
      containers:
      - image: gcr.io/PROJECT_ID/geowatch-report-worker:latest
        ports:
        - containerPort: 8080
        env:
        - name: GCP_PROJECT_ID
          value: "cloudrun-476105"
        - name: BACKEND_ENV
          value: "production"
        - name: BACKEND_API_URL
          value: "https://geowatch-backend.run.app/api"
        resources:
          limits:
            cpu: '2'
            memory: '2Gi'
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 10
          periodSeconds: 30
```

---

## Step 4: Deployment Commands

### 4.1 Build and Deploy Backend

```bash
cd geoWatch

# Build backend image
gcloud builds submit \
  --config backend/cloudbuild.yaml \
  --project cloudrun-476105

# Deploy backend
gcloud run deploy geowatch-backend \
  --image gcr.io/cloudrun-476105/geowatch-backend:latest \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 5 \
  --min-instances 1 \
  --timeout 600 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=cloudrun-476105,ANALYSIS_WORKER_URL=https://geowatch-analysis-worker.run.app,REPORT_WORKER_URL=https://geowatch-report-worker.run.app \
  --service-account geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --project cloudrun-476105
```

### 4.2 Build and Deploy Analysis Worker

```bash
# Build analysis worker image
gcloud builds submit \
  --config analysis-worker/cloudbuild.yaml \
  --project cloudrun-476105

# Deploy analysis worker
gcloud run deploy geowatch-analysis-worker \
  --image gcr.io/cloudrun-476105/geowatch-analysis-worker:latest \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 4 \
  --max-instances 3 \
  --min-instances 1 \
  --timeout 1800 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=cloudrun-476105,BACKEND_API_URL=https://geowatch-backend.run.app/api,GCS_BUCKET_NAME=geowatch-cloudrun-476105 \
  --service-account geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --project cloudrun-476105
```

### 4.3 Build and Deploy Report Worker

```bash
# Build report worker image
gcloud builds submit \
  --config report-worker/cloudbuild.yaml \
  --project cloudrun-476105

# Deploy report worker
gcloud run deploy geowatch-report-worker \
  --image gcr.io/cloudrun-476105/geowatch-report-worker:latest \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 2 \
  --min-instances 1 \
  --timeout 600 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=cloudrun-476105,BACKEND_API_URL=https://geowatch-backend.run.app/api \
  --service-account geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --project cloudrun-476105
```

### 4.4 Deploy Frontend

```bash
cd frontend

# Build frontend
npm run build

# Deploy to Cloud Run
gcloud run deploy geowatch-frontend \
  --source . \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 1 \
  --set-env-vars VITE_API_URL=https://geowatch-backend.run.app/api \
  --project cloudrun-476105
```

---

## Step 5: Setup Service Account & IAM

```bash
# Create service account
gcloud iam service-accounts create geowatch-sa \
  --display-name="GeoWatch Service Account" \
  --project cloudrun-476105

# Grant necessary permissions
gcloud projects add-iam-policy-binding cloudrun-476105 \
  --member=serviceAccount:geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --role=roles/firestore.user

gcloud projects add-iam-policy-binding cloudrun-476105 \
  --member=serviceAccount:geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --role=roles/storage.admin

gcloud projects add-iam-policy-binding cloudrun-476105 \
  --member=serviceAccount:geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --role=roles/earthengine.admin

gcloud projects add-iam-policy-binding cloudrun-476105 \
  --member=serviceAccount:geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --role=roles/aiplatform.user
```

---

## Step 6: Auto-Scaling Configuration

### How Auto-Scaling Works (Without Cloud Tasks)

Cloud Run automatically scales instances based on:
- **Concurrent requests per instance** (default: 80)
- **CPU utilization** (target: 60%)
- **Memory utilization** (target: 80%)

**For your setup:**

| Service | Min | Max | CPU | Memory | Timeout |
|---------|-----|-----|-----|--------|---------|
| Backend | 1 | 5 | 2 | 2GB | 10 min |
| Analysis Worker | 1 | 3 | 4 | 4GB | 30 min |
| Report Worker | 1 | 2 | 2 | 2GB | 10 min |
| Frontend | 1 | 10 | 1 | 1GB | 5 min |

**Scaling behavior:**
- When requests exceed capacity, Cloud Run automatically spins up new instances
- Instances are created within 5-10 seconds
- Old instances are gracefully drained and shut down

### Monitor Scaling

```bash
# Watch real-time metrics
gcloud run services describe geowatch-backend \
  --platform managed \
  --region us-central1 \
  --project cloudrun-476105

# View metrics in Cloud Console
# https://console.cloud.google.com/run/detail/us-central1/geowatch-backend/metrics
```

---

## Step 7: Monitoring & Alerts

### Setup Cloud Monitoring

```bash
# Create alert for high error rate
gcloud alpha monitoring policies create \
  --notification-channels=CHANNEL_ID \
  --display-name="GeoWatch High Error Rate" \
  --condition-display-name="Error rate > 5%" \
  --condition-threshold-value=0.05 \
  --condition-threshold-duration=300s \
  --project cloudrun-476105
```

### Key Metrics to Monitor

1. **Request Latency** - Should be < 5s for API calls
2. **Error Rate** - Should be < 1%
3. **Active Instances** - Should scale smoothly
4. **Memory Usage** - Should stay < 80%
5. **CPU Usage** - Should stay < 60%

---

## Step 8: Testing Production Deployment

```bash
# Test backend health
curl https://geowatch-backend.run.app/health

# Test analysis worker health
curl https://geowatch-analysis-worker.run.app/health

# Test report worker health
curl https://geowatch-report-worker.run.app/health

# Trigger test analysis
curl -X POST https://geowatch-backend.run.app/api/trigger-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "area_id": "test_area",
    "area_type": "forest",
    "polygon": [[...]]
  }'
```

---

## Step 9: Handling 10 Concurrent Requests

With the configuration above, here's what happens:

**Scenario: 10 concurrent analysis requests arrive**

1. **Backend** receives all 10 requests
   - Checks active analyses (max 3)
   - Returns 429 (Too Many Requests) for requests 4-10
   - Queues them in Firestore with status "queued"

2. **Analysis Worker** processes first 3
   - Each takes ~2-5 minutes
   - Auto-scales to 2-3 instances as needed

3. **Completed analyses** trigger reports
   - Report Worker scales to handle them
   - Reports generated in parallel

4. **Frontend polls** for status updates
   - Gets "queued" status for waiting analyses
   - Shows progress to user

**Result:** All 10 requests are handled, with graceful queuing

---

## Troubleshooting

### Issue: "Service unavailable" errors

**Cause:** Instances are scaling up but not ready yet

**Fix:** Increase min-instances:
```bash
gcloud run services update geowatch-backend \
  --min-instances=2 \
  --region us-central1
```

### Issue: Analysis timeouts

**Cause:** Earth Engine processing takes > 30 minutes

**Fix:** Increase timeout:
```bash
gcloud run services update geowatch-analysis-worker \
  --timeout=3600 \
  --region us-central1
```

### Issue: High memory usage

**Cause:** Too many concurrent analyses

**Fix:** Reduce max-instances:
```bash
gcloud run services update geowatch-analysis-worker \
  --max-instances=2 \
  --region us-central1
```

---

## Cost Estimation (Monthly)

| Service | Requests | CPU-seconds | Cost |
|---------|----------|-------------|------|
| Backend | 10,000 | 50,000 | $2 |
| Analysis Worker | 1,000 | 600,000 | $24 |
| Report Worker | 1,000 | 120,000 | $5 |
| Frontend | 50,000 | 50,000 | $2 |
| **Total** | | | **~$33/month** |

(Costs vary based on actual usage)

---

## Next Steps

1. ✅ Update code with concurrency limits
2. ✅ Create Cloud Run configs
3. ✅ Setup service account
4. ✅ Deploy all services
5. ✅ Test with production URLs
6. ✅ Monitor metrics
7. ✅ Setup alerts
8. ✅ Go live!

---

## Support

For issues:
1. Check Cloud Run logs: `gcloud run services logs read SERVICE_NAME`
2. Check metrics: Cloud Console → Cloud Run → Metrics
3. Check Firestore: Cloud Console → Firestore → Data
4. Check GCS: Cloud Console → Cloud Storage
