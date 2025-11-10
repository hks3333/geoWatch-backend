#!/bin/bash

# GeoWatch Production Deployment Script
# This script deploys all 4 services to Google Cloud Run

set -e

PROJECT_ID="cloudrun-476105"
REGION="us-central1"
SERVICE_ACCOUNT="geowatch-sa@${PROJECT_ID}.iam.gserviceaccount.com"

echo "🚀 GeoWatch Production Deployment"
echo "=================================="
echo "Project: $PROJECT_ID"
echo "Region: $REGION"
echo ""

# Step 1: Create service account if it doesn't exist
echo "📋 Setting up service account..."
gcloud iam service-accounts describe $SERVICE_ACCOUNT --project=$PROJECT_ID 2>/dev/null || {
    echo "Creating service account..."
    gcloud iam service-accounts create geowatch-sa \
        --display-name="GeoWatch Service Account" \
        --project=$PROJECT_ID
}

# Grant permissions
echo "Granting IAM permissions..."
for role in roles/firestore.user roles/storage.admin roles/earthengine.admin roles/aiplatform.user; do
    gcloud projects add-iam-policy-binding $PROJECT_ID \
        --member=serviceAccount:$SERVICE_ACCOUNT \
        --role=$role \
        --quiet 2>/dev/null || true
done

# Step 2: Build and deploy backend
echo ""
echo "📦 Building and deploying Backend..."
gcloud builds submit \
    --config backend/cloudbuild.yaml \
    --project $PROJECT_ID

gcloud run deploy geowatch-backend \
    --image gcr.io/$PROJECT_ID/geowatch-backend:latest \
    --platform managed \
    --region $REGION \
    --memory 2Gi \
    --cpu 2 \
    --max-instances 5 \
    --min-instances 1 \
    --timeout 600 \
    --set-env-vars BACKEND_ENV=production,GCP_PROJECT_ID=$PROJECT_ID,ANALYSIS_WORKER_URL=https://geowatch-analysis-worker-${REGION}.run.app,REPORT_WORKER_URL=https://geowatch-report-worker-${REGION}.run.app \
    --service-account $SERVICE_ACCOUNT \
    --allow-unauthenticated \
    --project $PROJECT_ID

BACKEND_URL=$(gcloud run services describe geowatch-backend --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)
echo "✅ Backend deployed: $BACKEND_URL"

# Step 3: Build and deploy analysis worker
echo ""
echo "📦 Building and deploying Analysis Worker..."
gcloud builds submit \
    --config analysis-worker/cloudbuild.yaml \
    --project $PROJECT_ID

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

ANALYSIS_URL=$(gcloud run services describe geowatch-analysis-worker --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)
echo "✅ Analysis Worker deployed: $ANALYSIS_URL"

# Step 4: Build and deploy report worker
echo ""
echo "📦 Building and deploying Report Worker..."
gcloud builds submit \
    --config report-worker/cloudbuild.yaml \
    --project $PROJECT_ID

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

REPORT_URL=$(gcloud run services describe geowatch-report-worker --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)
echo "✅ Report Worker deployed: $REPORT_URL"

# Step 5: Deploy frontend
echo ""
echo "📦 Building and deploying Frontend..."
cd frontend
npm run build
cd ..

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

FRONTEND_URL=$(gcloud run services describe geowatch-frontend --platform managed --region $REGION --format 'value(status.url)' --project $PROJECT_ID)
echo "✅ Frontend deployed: $FRONTEND_URL"

# Summary
echo ""
echo "🎉 Deployment Complete!"
echo "=================================="
echo "Frontend:        $FRONTEND_URL"
echo "Backend:         $BACKEND_URL"
echo "Analysis Worker: $ANALYSIS_URL"
echo "Report Worker:   $REPORT_URL"
echo ""
echo "📊 Monitor your services:"
echo "https://console.cloud.google.com/run?project=$PROJECT_ID"
echo ""
echo "🧪 Test the deployment:"
echo "curl $BACKEND_URL/health"
