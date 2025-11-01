1. TEMPORARY USER HANDLING (No Auth)
For this hackathon MVP, we will skip Firebase Authentication.

We will add the user_id: string field to the monitoring_areas model.

For now, all created areas will be assigned a hardcoded static user_id (e.g., "demo_user").

All GET endpoints will filter by this hardcoded user_id to simulate a real user's view. This makes it easy to add real auth later without changing the database logic.

2. REFINE/ADD API ENDPOINTS
Let's finalize our endpoint list. Please add the following:

GET /health

POST /monitoring-areas

GET /monitoring-areas

Logic: Must only return areas where user_id == "demo_user" and status != "deleted".

GET /monitoring-areas/{area_id}

Logic: Must verify user_id is "demo_user".

PATCH /monitoring-areas/{area_id} (NEW)

Purpose: To update metadata, like the name.

Body: { "name": "New Area Name" }

DELETE /monitoring-areas/{area_id}

GET /monitoring-areas/{area_id}/results

GET /monitoring-areas/{area_id}/latest (NEW)

Purpose: Get only the single most recent analysis_result (where processing_status == "completed") for this area.

POST /monitoring-areas/{area_id}/analyze

3. ADD CRITICAL CALLBACK ENDPOINT
We need an internal endpoint for the Analysis Worker to report its status. This will be protected by Google Cloud's service-to-service authentication (validating the OIDC token in the Authorization header).

Endpoint: POST /callbacks/analysis-complete (Internal Auth)

Purpose: The Analysis Worker will call this when it succeeds or fails.

Body (from worker):

JSON

{
  "area_id": "abc123",
  "result_id": "res_xyz123",
  "status": "completed",
  "payload": { ... (the full analysis_result document data) }
}
OR

JSON

{
  "area_id": "abc123",
  "result_id": "res_xyz123",
  "status": "failed",
  "error_message": "Earth Engine timed out."
}
Backend Action: The backend will find the analysis_results document (which was created with processing_status: "in_progress") and update it with the final status, error message, and/or payload. This is how the frontend stops polling.