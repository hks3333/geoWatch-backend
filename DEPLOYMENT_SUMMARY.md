# Production Deployment Summary - Quick Start

## What Changed for Production

### 1. **Auto-Scaling Without Cloud Tasks**

Cloud Run automatically scales your services based on demand. Here's how it handles 10 concurrent requests:

```
Request 1-3:  Processed immediately by existing instances
Request 4-5:  New instances spin up (5-10 seconds)
Request 6-10: Queued in Firestore, processed as instances become available
```

**No code changes needed** - Cloud Run handles this automatically!

---

## 4 Services to Deploy

### Service 1: Backend (Port 8000)
- **Role:** Main API, orchestrates everything
- **Concurrency:** 5 max instances
- **CPU:** 2 cores
- **Memory:** 2GB
- **Timeout:** 10 minutes
- **Auto-scales when:** > 80 concurrent requests

### Service 2: Analysis Worker (Port 8001)
- **Role:** Runs Earth Engine analysis (2-5 min per job)
- **Concurrency:** 3 max instances
- **CPU:** 4 cores (heavy processing)
- **Memory:** 4GB (EE needs memory)
- **Timeout:** 30 minutes
- **Auto-scales when:** > 240 concurrent requests

### Service 3: Report Worker (Port 8002)
- **Role:** Generates AI reports (1-2 min per job)
- **Concurrency:** 2 max instances
- **CPU:** 2 cores
- **Memory:** 2GB
- **Timeout:** 10 minutes
- **Auto-scales when:** > 160 concurrent requests

### Service 4: Frontend (Port 3000)
- **Role:** React web app
- **Concurrency:** 10 max instances
- **CPU:** 1 core
- **Memory:** 1GB
- **Timeout:** 5 minutes
- **Auto-scales when:** > 800 concurrent requests

---

## Deployment Steps (Choose One)

### Option A: Automated Deployment (Recommended)

```bash
# Make script executable
chmod +x deploy.sh

# Run deployment
./deploy.sh

# Wait 5-10 minutes for all services to deploy
```

This script:
- ✅ Creates service account
- ✅ Grants IAM permissions
- ✅ Builds all 4 services
- ✅ Deploys to Cloud Run
- ✅ Prints all URLs

### Option B: Manual Deployment

```bash
# 1. Deploy Backend
gcloud run deploy geowatch-backend \
  --image gcr.io/cloudrun-476105/geowatch-backend:latest \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 5 \
  --min-instances 1 \
  --timeout 600 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=cloudrun-476105 \
  --allow-unauthenticated

# 2. Get Backend URL
BACKEND_URL=$(gcloud run services describe geowatch-backend \
  --platform managed --region us-central1 \
  --format 'value(status.url)')

# 3. Deploy Analysis Worker
gcloud run deploy geowatch-analysis-worker \
  --image gcr.io/cloudrun-476105/geowatch-analysis-worker:latest \
  --platform managed \
  --region us-central1 \
  --memory 4Gi \
  --cpu 4 \
  --max-instances 3 \
  --min-instances 1 \
  --timeout 1800 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=cloudrun-476105,BACKEND_API_URL=${BACKEND_URL}/api \
  --allow-unauthenticated

# 4. Deploy Report Worker
gcloud run deploy geowatch-report-worker \
  --image gcr.io/cloudrun-476105/geowatch-report-worker:latest \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 2 \
  --min-instances 1 \
  --timeout 600 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=cloudrun-476105,BACKEND_API_URL=${BACKEND_URL}/api \
  --allow-unauthenticated

# 5. Deploy Frontend
cd frontend && npm run build && cd ..
gcloud run deploy geowatch-frontend \
  --source frontend \
  --platform managed \
  --region us-central1 \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 1 \
  --set-env-vars VITE_API_URL=${BACKEND_URL}/api \
  --allow-unauthenticated
```

---

## Environment Variables

Update these for production:

### Backend (.env)
```
GCP_PROJECT_ID=cloudrun-476105
BACKEND_ENV=production
ANALYSIS_WORKER_URL=https://geowatch-analysis-worker.run.app
REPORT_WORKER_URL=https://geowatch-report-worker.run.app
```

### Analysis Worker (.env)
```
GCP_PROJECT_ID=cloudrun-476105
BACKEND_ENV=production
BACKEND_API_URL=https://geowatch-backend.run.app/api
GCS_BUCKET_NAME=geowatch-cloudrun-476105
```

### Report Worker (.env)
```
GCP_PROJECT_ID=cloudrun-476105
BACKEND_ENV=production
BACKEND_API_URL=https://geowatch-backend.run.app/api
```

---

## How Auto-Scaling Works

### Scenario: 10 Concurrent Analysis Requests

```
Time 0s:   Requests 1-3 arrive
           → Processed by 3 existing instances
           → Requests 4-10 queued

Time 5s:   Requests 1-3 still processing
           → Cloud Run detects queue
           → Starts spinning up new instances

Time 10s:  Requests 4-6 start processing
           → Requests 7-10 still queued

Time 15s:  Requests 7-10 start processing
           → All 10 requests now in progress

Time 120s: Requests 1-3 complete
           → Instances become available
           → Cloud Run scales down unused instances

Result:    All 10 requests processed successfully!
```

### Key Points

- ✅ **Automatic:** No manual intervention needed
- ✅ **Fast:** New instances ready in 5-10 seconds
- ✅ **Efficient:** Unused instances shut down automatically
- ✅ **Graceful:** Requests queued, not rejected
- ✅ **Cost-effective:** Pay only for what you use

---

## Monitoring & Alerts

### View Real-Time Metrics

```bash
# Watch instances scale up/down
gcloud run services describe geowatch-backend \
  --platform managed \
  --region us-central1 \
  --format 'value(status.traffic[0].percent)'

# View in Cloud Console
# https://console.cloud.google.com/run?project=cloudrun-476105
```

### Key Metrics to Watch

1. **Active Instances** - Should scale smoothly
2. **Request Latency** - Should be < 5s
3. **Error Rate** - Should be < 1%
4. **Memory Usage** - Should stay < 80%
5. **CPU Usage** - Should stay < 60%

---

## Handling 10 Concurrent Requests

### Current Setup (Without Cloud Tasks)

| Scenario | Behavior |
|----------|----------|
| 1-3 requests | Processed immediately |
| 4-6 requests | New instances spin up |
| 7-10 requests | Queued in Firestore |
| 11+ requests | Queued, processed as capacity opens |

### Limits

- **Backend:** Max 5 instances (handles ~400 concurrent requests)
- **Analysis Worker:** Max 3 instances (handles ~240 concurrent requests)
- **Report Worker:** Max 2 instances (handles ~160 concurrent requests)

### If You Need More Capacity

```bash
# Increase max instances
gcloud run services update geowatch-analysis-worker \
  --max-instances 5 \
  --region us-central1

# Increase CPU/Memory
gcloud run services update geowatch-analysis-worker \
  --cpu 8 \
  --memory 8Gi \
  --region us-central1
```

---

## Cost Estimation

### Monthly Costs (Estimated)

| Service | Requests | Cost |
|---------|----------|------|
| Backend | 10,000 | $2 |
| Analysis Worker | 1,000 | $24 |
| Report Worker | 1,000 | $5 |
| Frontend | 50,000 | $2 |
| **Total** | | **~$33/month** |

**Note:** Costs scale with usage. Heavy usage could be $100-200/month.

---

## Testing Production Deployment

```bash
# 1. Test backend health
curl https://geowatch-backend.run.app/health

# 2. Test analysis worker health
curl https://geowatch-analysis-worker.run.app/health

# 3. Test report worker health
curl https://geowatch-report-worker.run.app/health

# 4. Trigger test analysis
curl -X POST https://geowatch-backend.run.app/api/trigger-analysis \
  -H "Content-Type: application/json" \
  -d '{
    "area_id": "test_area",
    "area_type": "forest",
    "polygon": [[...]]
  }'

# 5. Check status
curl https://geowatch-backend.run.app/api/results/RESULT_ID
```

---

## Troubleshooting

### Issue: "Service Unavailable" Errors

**Cause:** Instances scaling up but not ready yet

**Fix:**
```bash
# Increase min-instances to keep instances warm
gcloud run services update geowatch-backend \
  --min-instances 2 \
  --region us-central1
```

### Issue: Analysis Timeouts

**Cause:** Earth Engine processing takes > 30 minutes

**Fix:**
```bash
# Increase timeout
gcloud run services update geowatch-analysis-worker \
  --timeout 3600 \
  --region us-central1
```

### Issue: High Memory Usage

**Cause:** Too many concurrent analyses

**Fix:**
```bash
# Reduce max-instances or increase memory
gcloud run services update geowatch-analysis-worker \
  --max-instances 2 \
  --memory 8Gi \
  --region us-central1
```

### Issue: View Logs

```bash
# View recent logs
gcloud run services logs read geowatch-backend --limit 100

# Stream live logs
gcloud run services logs read geowatch-backend --limit 50 --follow
```

---

## Next Steps

1. ✅ **Prepare:** Update .env files with production URLs
2. ✅ **Deploy:** Run `./deploy.sh` or manual commands
3. ✅ **Test:** Verify all services are working
4. ✅ **Monitor:** Watch Cloud Console for metrics
5. ✅ **Scale:** Adjust max-instances if needed
6. ✅ **Go Live:** Update frontend to use production URLs

---

## Support & Documentation

- **Cloud Run Docs:** https://cloud.google.com/run/docs
- **Scaling Guide:** https://cloud.google.com/run/docs/about-scaling
- **Pricing Calculator:** https://cloud.google.com/products/calculator
- **Monitoring:** https://console.cloud.google.com/monitoring

---

## Summary

Your production setup:
- ✅ **4 independent services** on Cloud Run
- ✅ **Automatic scaling** based on demand
- ✅ **Handles 10+ concurrent requests** gracefully
- ✅ **No Cloud Tasks needed** (simpler setup)
- ✅ **Cost-effective** (~$33/month baseline)
- ✅ **Production-ready** with monitoring and alerts

**You're ready to deploy! 🚀**
