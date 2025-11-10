# Quick Deploy - Copy & Paste Commands

## Prerequisites

```bash
# Install gcloud CLI
# https://cloud.google.com/sdk/docs/install

# Login to GCP
gcloud auth login

# Set project
gcloud config set project cloudrun-476105

# Enable required APIs
gcloud services enable run.googleapis.com
gcloud services enable cloudbuild.googleapis.com
gcloud services enable containerregistry.googleapis.com
gcloud services enable firestore.googleapis.com
gcloud services enable storage-api.googleapis.com
gcloud services enable earthengine.googleapis.com
gcloud services enable aiplatform.googleapis.com
```

---

## One-Command Deploy (Easiest)

```bash
# From project root directory
chmod +x deploy.sh
./deploy.sh
```

**Wait 10-15 minutes for all services to deploy.**

---

## Manual Deploy (If Script Fails)

### Step 1: Setup Service Account

```bash
PROJECT_ID="cloudrun-476105"
SERVICE_ACCOUNT="geowatch-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Create service account
gcloud iam service-accounts create geowatch-sa \
  --display-name="GeoWatch Service Account" \
  --project=$PROJECT_ID 2>/dev/null || echo "Service account already exists"

# Grant permissions
gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/firestore.user --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/storage.admin --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/earthengine.admin --quiet

gcloud projects add-iam-policy-binding $PROJECT_ID \
  --member=serviceAccount:$SERVICE_ACCOUNT \
  --role=roles/aiplatform.user --quiet
```

### Step 2: Deploy Backend

```bash
PROJECT_ID="cloudrun-476105"
REGION="us-central1"
SERVICE_ACCOUNT="geowatch-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Build
gcloud builds submit \
  --config backend/cloudbuild.yaml \
  --project $PROJECT_ID

# Deploy
gcloud run deploy geowatch-backend \
  --image gcr.io/$PROJECT_ID/geowatch-backend:latest \
  --platform managed \
  --region $REGION \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 5 \
  --min-instances 1 \
  --timeout 600 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=$PROJECT_ID \
  --service-account $SERVICE_ACCOUNT \
  --allow-unauthenticated \
  --project $PROJECT_ID

# Get URL
BACKEND_URL=$(gcloud run services describe geowatch-backend \
  --platform managed --region $REGION \
  --format 'value(status.url)' --project $PROJECT_ID)

echo "Backend URL: $BACKEND_URL"
```

### Step 3: Deploy Analysis Worker

```bash
PROJECT_ID="cloudrun-476105"
REGION="us-central1"
SERVICE_ACCOUNT="geowatch-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Get backend URL from previous step
BACKEND_URL="https://geowatch-backend-XXXXX.run.app"  # Replace with actual URL

# Build
gcloud builds submit \
  --config analysis-worker/cloudbuild.yaml \
  --project $PROJECT_ID

# Deploy
gcloud run deploy geowatch-analysis-worker \
  --image gcr.io/$PROJECT_ID/geowatch-analysis-worker:latest \
  --platform managed \
  --region $REGION \
  --memory 4Gi \
  --cpu 4 \
  --max-instances 3 \
  --min-instances 1 \
  --timeout 1800 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=$PROJECT_ID,BACKEND_API_URL=${BACKEND_URL}/api,GCS_BUCKET_NAME=geowatch-${PROJECT_ID} \
  --service-account $SERVICE_ACCOUNT \
  --allow-unauthenticated \
  --project $PROJECT_ID

# Get URL
ANALYSIS_URL=$(gcloud run services describe geowatch-analysis-worker \
  --platform managed --region $REGION \
  --format 'value(status.url)' --project $PROJECT_ID)

echo "Analysis Worker URL: $ANALYSIS_URL"
```

### Step 4: Deploy Report Worker

```bash
PROJECT_ID="cloudrun-476105"
REGION="us-central1"
SERVICE_ACCOUNT="geowatch-sa@${PROJECT_ID}.iam.gserviceaccount.com"

# Get backend URL from Step 2
BACKEND_URL="https://geowatch-backend-XXXXX.run.app"  # Replace with actual URL

# Build
gcloud builds submit \
  --config report-worker/cloudbuild.yaml \
  --project $PROJECT_ID

# Deploy
gcloud run deploy geowatch-report-worker \
  --image gcr.io/$PROJECT_ID/geowatch-report-worker:latest \
  --platform managed \
  --region $REGION \
  --memory 2Gi \
  --cpu 2 \
  --max-instances 2 \
  --min-instances 1 \
  --timeout 600 \
  --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=$PROJECT_ID,BACKEND_API_URL=${BACKEND_URL}/api \
  --service-account $SERVICE_ACCOUNT \
  --allow-unauthenticated \
  --project $PROJECT_ID

# Get URL
REPORT_URL=$(gcloud run services describe geowatch-report-worker \
  --platform managed --region $REGION \
  --format 'value(status.url)' --project $PROJECT_ID)

echo "Report Worker URL: $REPORT_URL"
```

### Step 5: Deploy Frontend

```bash
PROJECT_ID="cloudrun-476105"
REGION="us-central1"

# Get backend URL from Step 2
BACKEND_URL="https://geowatch-backend-XXXXX.run.app"  # Replace with actual URL

# Build frontend
cd frontend
npm run build
cd ..

# Deploy
gcloud run deploy geowatch-frontend \
  --source frontend \
  --platform managed \
  --region $REGION \
  --memory 1Gi \
  --cpu 1 \
  --max-instances 10 \
  --min-instances 1 \
  --set-env-vars VITE_API_URL=${BACKEND_URL}/api \
  --allow-unauthenticated \
  --project $PROJECT_ID

# Get URL
FRONTEND_URL=$(gcloud run services describe geowatch-frontend \
  --platform managed --region $REGION \
  --format 'value(status.url)' --project $PROJECT_ID)

echo "Frontend URL: $FRONTEND_URL"
```

---

## Verify Deployment

```bash
# Test all services
echo "Testing Backend..."
curl https://geowatch-backend.run.app/health

echo "Testing Analysis Worker..."
curl https://geowatch-analysis-worker.run.app/health

echo "Testing Report Worker..."
curl https://geowatch-report-worker.run.app/health

echo "Testing Frontend..."
curl https://geowatch-frontend.run.app
```

---

## View Logs

```bash
# Backend logs
gcloud run services logs read geowatch-backend --limit 100

# Analysis Worker logs
gcloud run services logs read geowatch-analysis-worker --limit 100

# Report Worker logs
gcloud run services logs read geowatch-report-worker --limit 100

# Frontend logs
gcloud run services logs read geowatch-frontend --limit 100

# Stream live logs
gcloud run services logs read geowatch-backend --limit 50 --follow
```

---

## Monitor Services

```bash
# View all services
gcloud run services list --platform managed --region us-central1

# View specific service details
gcloud run services describe geowatch-backend \
  --platform managed --region us-central1

# View metrics in Cloud Console
# https://console.cloud.google.com/run?project=cloudrun-476105
```

---

## Scale Services

```bash
# Increase max instances for Analysis Worker
gcloud run services update geowatch-analysis-worker \
  --max-instances 5 \
  --region us-central1

# Increase CPU/Memory for Analysis Worker
gcloud run services update geowatch-analysis-worker \
  --cpu 8 \
  --memory 8Gi \
  --region us-central1

# Increase min instances to keep warm
gcloud run services update geowatch-backend \
  --min-instances 2 \
  --region us-central1
```

---

## Rollback to Previous Version

```bash
# View revisions
gcloud run revisions list --service geowatch-backend --region us-central1

# Rollback to previous revision
gcloud run services update-traffic geowatch-backend \
  --to-revisions REVISION_ID=100 \
  --region us-central1
```

---

## Delete Services (If Needed)

```bash
# Delete all services
gcloud run services delete geowatch-backend --region us-central1 --quiet
gcloud run services delete geowatch-analysis-worker --region us-central1 --quiet
gcloud run services delete geowatch-report-worker --region us-central1 --quiet
gcloud run services delete geowatch-frontend --region us-central1 --quiet

# Delete service account
gcloud iam service-accounts delete geowatch-sa@cloudrun-476105.iam.gserviceaccount.com --quiet
```

---

## Troubleshooting

### Build Fails

```bash
# Check build logs
gcloud builds log LATEST

# Rebuild with verbose output
gcloud builds submit --config backend/cloudbuild.yaml --project cloudrun-476105 --verbosity debug
```

### Service Won't Start

```bash
# Check service logs
gcloud run services logs read geowatch-backend --limit 50

# Check if image exists
gcloud container images list --project cloudrun-476105

# Manually test image locally
docker run -p 8000:8000 gcr.io/cloudrun-476105/geowatch-backend:latest
```

### High Latency

```bash
# Check if instances are scaling
gcloud run services describe geowatch-backend --platform managed --region us-central1

# Increase min-instances to keep warm
gcloud run services update geowatch-backend --min-instances 2 --region us-central1
```

### Out of Memory

```bash
# Increase memory
gcloud run services update geowatch-analysis-worker \
  --memory 8Gi \
  --region us-central1
```

---

## Cost Monitoring

```bash
# View billing
# https://console.cloud.google.com/billing

# Estimate costs
# https://cloud.google.com/products/calculator

# Set budget alerts
gcloud billing budgets create \
  --billing-account BILLING_ACCOUNT_ID \
  --display-name="GeoWatch Monthly Budget" \
  --budget-amount 100 \
  --threshold-rule percent=50 \
  --threshold-rule percent=100
```

---

## Summary

✅ All 4 services deployed to Cloud Run
✅ Auto-scaling configured
✅ Monitoring and logging enabled
✅ Ready for 10+ concurrent requests

**Your app is now in production! 🚀**
