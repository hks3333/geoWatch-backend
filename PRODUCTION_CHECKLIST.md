# Production Deployment Checklist

## Pre-Deployment (Do This First)

- [ ] **Commit all changes to git**
  ```bash
  git add .
  git commit -m "Production deployment ready"
  git push
  ```

- [ ] **Update environment variables**
  - [ ] Backend: Set `BACKEND_ENV=production`
  - [ ] Analysis Worker: Set `BACKEND_ENV=production`
  - [ ] Report Worker: Set `BACKEND_ENV=production`

- [ ] **Test locally one more time**
  ```bash
  # Start all 4 services locally
  # Backend: uvicorn main:app --port 8000
  # Analysis Worker: uvicorn main:app --port 8001
  # Report Worker: uvicorn main:app --port 8002
  # Frontend: npm run dev
  
  # Trigger a test analysis
  # Verify it completes end-to-end
  ```

- [ ] **Verify GCP project is set up**
  ```bash
  gcloud config set project cloudrun-476105
  gcloud auth login
  ```

---

## Deployment (Choose One Method)

### Method 1: Automated Script (Recommended)

- [ ] **Run deployment script**
  ```bash
  chmod +x deploy.sh
  ./deploy.sh
  ```

- [ ] **Wait for completion** (10-15 minutes)

- [ ] **Note the URLs printed at the end**

### Method 2: Manual Commands

- [ ] **Follow QUICK_DEPLOY.md step by step**

---

## Post-Deployment Verification

- [ ] **Test all services are running**
  ```bash
  curl https://geowatch-backend.run.app/health
  curl https://geowatch-analysis-worker.run.app/health
  curl https://geowatch-report-worker.run.app/health
  ```

- [ ] **Check Cloud Console**
  - [ ] All 4 services show "OK" status
  - [ ] No errors in logs
  - [ ] Instances are running

- [ ] **Test end-to-end workflow**
  - [ ] Create a monitoring area via frontend
  - [ ] Trigger analysis
  - [ ] Wait for completion (2-5 minutes)
  - [ ] Verify results appear
  - [ ] Verify report generates

- [ ] **Test with multiple concurrent requests**
  - [ ] Trigger 3 analyses simultaneously
  - [ ] Verify all complete successfully
  - [ ] Check Cloud Console for scaling

---

## Configuration Verification

### Backend Service

- [ ] **Environment variables set correctly**
  ```bash
  gcloud run services describe geowatch-backend \
    --platform managed --region us-central1 \
    --format 'value(spec.template.spec.containers[0].env)'
  ```

- [ ] **Resource limits correct**
  - [ ] CPU: 2
  - [ ] Memory: 2Gi
  - [ ] Max instances: 5
  - [ ] Timeout: 600s

- [ ] **Service account assigned**
  ```bash
  gcloud run services describe geowatch-backend \
    --platform managed --region us-central1 \
    --format 'value(spec.template.spec.serviceAccountName)'
  ```

### Analysis Worker Service

- [ ] **Environment variables set correctly**
  - [ ] BACKEND_API_URL points to backend
  - [ ] GCS_BUCKET_NAME is correct
  - [ ] BACKEND_ENV=production

- [ ] **Resource limits correct**
  - [ ] CPU: 4
  - [ ] Memory: 4Gi
  - [ ] Max instances: 3
  - [ ] Timeout: 1800s

### Report Worker Service

- [ ] **Environment variables set correctly**
  - [ ] BACKEND_API_URL points to backend
  - [ ] BACKEND_ENV=production

- [ ] **Resource limits correct**
  - [ ] CPU: 2
  - [ ] Memory: 2Gi
  - [ ] Max instances: 2
  - [ ] Timeout: 600s

### Frontend Service

- [ ] **Environment variables set correctly**
  - [ ] VITE_API_URL points to backend

- [ ] **Resource limits correct**
  - [ ] CPU: 1
  - [ ] Memory: 1Gi
  - [ ] Max instances: 10

---

## Monitoring Setup

- [ ] **Enable Cloud Logging**
  ```bash
  gcloud logging sinks create geowatch-logs \
    logging.googleapis.com/projects/cloudrun-476105/logs/geowatch
  ```

- [ ] **Setup error notifications**
  - [ ] Go to Cloud Console → Logging → Logs-based Metrics
  - [ ] Create metric for errors
  - [ ] Create alert policy

- [ ] **Setup performance alerts**
  - [ ] Alert if latency > 5s
  - [ ] Alert if error rate > 1%
  - [ ] Alert if CPU > 80%
  - [ ] Alert if memory > 80%

- [ ] **Monitor costs**
  - [ ] Go to Cloud Console → Billing
  - [ ] Set budget alert at $50/month

---

## DNS & Domain Setup (Optional)

- [ ] **Map custom domain to backend**
  ```bash
  gcloud run domain-mappings create \
    --service geowatch-backend \
    --domain api.yourdomain.com \
    --region us-central1
  ```

- [ ] **Map custom domain to frontend**
  ```bash
  gcloud run domain-mappings create \
    --service geowatch-frontend \
    --domain yourdomain.com \
    --region us-central1
  ```

- [ ] **Update DNS records** (follow Cloud Run instructions)

- [ ] **Test custom domains**
  ```bash
  curl https://api.yourdomain.com/health
  curl https://yourdomain.com
  ```

---

## Security Hardening

- [ ] **Disable unauthenticated access** (if needed)
  ```bash
  gcloud run services update geowatch-backend \
    --no-allow-unauthenticated \
    --region us-central1
  ```

- [ ] **Setup Cloud Armor** (DDoS protection)
  - [ ] Go to Cloud Console → Cloud Armor
  - [ ] Create security policy
  - [ ] Attach to backend service

- [ ] **Enable VPC Connector** (for private databases)
  - [ ] Create VPC connector
  - [ ] Update services to use it

- [ ] **Rotate service account keys**
  - [ ] Go to Cloud Console → IAM & Admin → Service Accounts
  - [ ] Delete old keys
  - [ ] Create new keys if needed

---

## Backup & Disaster Recovery

- [ ] **Enable Firestore backups**
  ```bash
  gcloud firestore backups create \
    --collection-filter='{}' \
    --retention-days=30
  ```

- [ ] **Enable GCS versioning** (for exported images)
  ```bash
  gsutil versioning set on gs://geowatch-cloudrun-476105
  ```

- [ ] **Document recovery procedures**
  - [ ] How to restore from backup
  - [ ] How to redeploy services
  - [ ] How to restore data

---

## Performance Tuning

- [ ] **Monitor initial performance**
  - [ ] Track response times
  - [ ] Track error rates
  - [ ] Track scaling behavior

- [ ] **Adjust based on metrics** (after 1 week)
  - [ ] Increase max-instances if hitting limits
  - [ ] Increase min-instances if cold starts are slow
  - [ ] Increase CPU/memory if utilization is high

- [ ] **Optimize Earth Engine queries**
  - [ ] Monitor analysis duration
  - [ ] Optimize composite creation if slow
  - [ ] Consider caching results

---

## Documentation

- [ ] **Update README with production URLs**
  ```markdown
  ## Production URLs
  - Frontend: https://geowatch-frontend.run.app
  - Backend API: https://geowatch-backend.run.app/api
  - Docs: https://geowatch-backend.run.app/docs
  ```

- [ ] **Document scaling limits**
  - [ ] Max concurrent requests per service
  - [ ] Max instances per service
  - [ ] Expected response times

- [ ] **Document troubleshooting procedures**
  - [ ] How to check logs
  - [ ] How to scale services
  - [ ] How to rollback

- [ ] **Document cost management**
  - [ ] Expected monthly costs
  - [ ] How to monitor spending
  - [ ] How to optimize costs

---

## Launch Checklist

- [ ] **Announce to users**
  - [ ] Send email with new URLs
  - [ ] Update website
  - [ ] Post on social media

- [ ] **Monitor first 24 hours**
  - [ ] Check logs every hour
  - [ ] Verify no errors
  - [ ] Monitor performance metrics

- [ ] **Be on-call for first week**
  - [ ] Monitor for issues
  - [ ] Respond to user reports
  - [ ] Make adjustments as needed

- [ ] **Schedule post-launch review**
  - [ ] Review metrics
  - [ ] Identify improvements
  - [ ] Plan optimizations

---

## Rollback Plan (If Issues Occur)

- [ ] **Identify the problem**
  ```bash
  gcloud run services logs read SERVICE_NAME --limit 100
  ```

- [ ] **Rollback to previous version**
  ```bash
  gcloud run revisions list --service SERVICE_NAME --region us-central1
  gcloud run services update-traffic SERVICE_NAME \
    --to-revisions REVISION_ID=100 \
    --region us-central1
  ```

- [ ] **Or redeploy previous commit**
  ```bash
  git checkout PREVIOUS_COMMIT
  ./deploy.sh
  ```

- [ ] **Notify users if needed**

---

## Post-Launch (Week 1)

- [ ] **Review metrics**
  - [ ] Response times
  - [ ] Error rates
  - [ ] Scaling behavior
  - [ ] Cost

- [ ] **Gather user feedback**
  - [ ] Any issues?
  - [ ] Performance OK?
  - [ ] Any feature requests?

- [ ] **Make optimizations**
  - [ ] Adjust scaling limits
  - [ ] Optimize queries
  - [ ] Fix any bugs

- [ ] **Document lessons learned**
  - [ ] What went well?
  - [ ] What could be better?
  - [ ] What to do differently next time?

---

## Success Criteria

✅ All 4 services deployed and running
✅ End-to-end workflow works
✅ Can handle 10 concurrent requests
✅ Error rate < 1%
✅ Response time < 5s
✅ Auto-scaling works smoothly
✅ Monitoring and alerts configured
✅ Logs are accessible
✅ Costs are within budget
✅ Users are happy

---

## Support Contacts

- **GCP Support:** https://cloud.google.com/support
- **Cloud Run Docs:** https://cloud.google.com/run/docs
- **Firestore Docs:** https://cloud.google.com/firestore/docs
- **Earth Engine Docs:** https://developers.google.com/earth-engine

---

**You're ready to launch! 🚀**
