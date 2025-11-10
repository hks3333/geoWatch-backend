# Backend - Quick Reference Card

## Environment Variables

### Local Development
```bash
BACKEND_ENV=local
ANALYSIS_WORKER_URL=http://localhost:8001
REPORT_WORKER_URL=http://localhost:8002
```

### Production
```bash
BACKEND_ENV=production
ANALYSIS_WORKER_URL=https://geowatch-analysis-worker.run.app
REPORT_WORKER_URL=https://geowatch-report-worker.run.app
```

---

## Deployment Commands

### Build
```bash
gcloud builds submit \
  --config backend/cloudbuild.yaml \
  --project cloudrun-476105
```

### Deploy
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
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=cloudrun-476105,ANALYSIS_WORKER_URL=https://geowatch-analysis-worker.run.app,REPORT_WORKER_URL=https://geowatch-report-worker.run.app \
  --service-account geowatch-sa@cloudrun-476105.iam.gserviceaccount.com \
  --allow-unauthenticated \
  --project cloudrun-476105
```

### Get URL
```bash
gcloud run services describe geowatch-backend \
  --platform managed --region us-central1 \
  --format 'value(status.url)' \
  --project cloudrun-476105
```

---

## Testing

### Health Check
```bash
curl https://geowatch-backend.run.app/health
```

### View Logs
```bash
gcloud run services logs read geowatch-backend --limit 100
```

### Stream Logs
```bash
gcloud run services logs read geowatch-backend --limit 50 --follow
```

---

## Configuration

| Setting | Value | Purpose |
|---------|-------|---------|
| Memory | 2Gi | Sufficient for API |
| CPU | 2 | Handles ~400 req/s |
| Max Instances | 5 | Cost control |
| Min Instances | 1 | Cost optimization |
| Timeout | 600s | 10 minutes |

---

## Service Communication

| From | To | Purpose |
|------|----|---------| 
| Frontend | Backend | API calls |
| Backend | Analysis Worker | Trigger analysis |
| Backend | Report Worker | Trigger reports |
| Analysis Worker | Backend | Send callbacks |
| Report Worker | Backend | Send callbacks |
| Backend | Firestore | Store/retrieve data |

---

## CORS Origins

### Local
- `*` (all origins)

### Production
- `https://geowatch-frontend.run.app`
- `https://yourdomain.com` (add your custom domain)

---

## Troubleshooting

| Issue | Cause | Fix |
|-------|-------|-----|
| Service Unavailable | Workers unreachable | Deploy workers, check URLs |
| CORS Error | Origin not allowed | Add to allowed_origins list |
| Callbacks Not Received | Wrong Backend URL | Check BACKEND_API_URL in workers |
| High Latency | Not enough instances | Increase min-instances |
| Out of Memory | Too many requests | Increase memory or max-instances |

---

## Key Files

- `backend/main.py` - App entry point, CORS, logging
- `backend/app/config.py` - Environment configuration
- `backend/app/services/worker_client.py` - Communication with Analysis Worker
- `backend/app/routes/callbacks.py` - Receive callbacks from workers
- `backend/Dockerfile` - Docker image definition
- `backend/cloudbuild.yaml` - Cloud Build configuration

---

## Next Steps

1. ✅ Update environment variables
2. ✅ Build: `gcloud builds submit --config backend/cloudbuild.yaml`
3. ✅ Deploy: Run deploy command above
4. ✅ Get URL: Save the backend URL
5. ✅ Test: `curl https://geowatch-backend.run.app/health`
6. ⏭️ Deploy Analysis Worker with Backend URL
7. ⏭️ Deploy Report Worker with Backend URL
8. ⏭️ Deploy Frontend with Backend URL

---

## Important URLs to Save

```bash
# After deployment, save these:
BACKEND_URL="https://geowatch-backend-XXXXX.run.app"

# Use for other services:
ANALYSIS_WORKER_BACKEND_API_URL="${BACKEND_URL}/api"
REPORT_WORKER_BACKEND_API_URL="${BACKEND_URL}/api"
FRONTEND_VITE_API_URL="${BACKEND_URL}/api"
```
