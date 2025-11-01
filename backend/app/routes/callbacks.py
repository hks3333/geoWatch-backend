"""
This module defines the API routes for internal callbacks, such as from the
Analysis Worker.
"""

import logging
from typing import Dict, Any

from fastapi import APIRouter, Depends, HTTPException, status, Header
from pydantic import BaseModel

from app.config import settings
from app.services.firestore_service import FirestoreService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()


class AnalysisCompletionPayload(BaseModel):
    result_id: str
    status: str
    error_message: str = None
    generated_map_url: str = None
    change_percentage: float = None


# Dependency to get FirestoreService instance
def get_firestore_service() -> FirestoreService:
    """
    Provides a FirestoreService instance for dependency injection.
    """
    return FirestoreService(project_id=settings.GCP_PROJECT_ID)


async def verify_oidc_token(authorization: str = Header(default=None)):
    """
    Verifies the OIDC token from the Authorization header.
    In a real application, this would involve a library like google-auth
    to verify the token against Google's public keys.
    For this MVP, we will just check if the header is present.
    """
    if settings.BACKEND_ENV != "local":
        if not authorization or not authorization.startswith("Bearer "):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or missing Authorization header",
            )
    # In a real app, you would verify the token here.
    # For example:
    # from google.oauth2 import id_token
    # from google.auth.transport import requests
    # try:
    #     id_info = id_token.verify_oauth2_token(
    #         token, requests.Request(), audience=settings.WORKER_AUDIENCE
    #     )
    # except ValueError:
    #     raise HTTPException(
    #         status_code=status.HTTP_401_UNAUTHORIZED,
    #         detail="Invalid OIDC token",
    #     )


@router.post(
    "/callbacks/analysis-complete",
    status_code=status.HTTP_200_OK,
    summary="Callback for when analysis is complete",
    dependencies=[Depends(verify_oidc_token)],
)
async def analysis_complete_callback(
    payload: AnalysisCompletionPayload,
    db: FirestoreService = Depends(get_firestore_service),
):
    """
    Internal endpoint for the Analysis Worker to report its status.
    This is protected by Google Cloud's service-to-service authentication.
    """
    try:
        update_data = {
            "processing_status": payload.status,
        }
        if payload.status == "completed":
            update_data["generated_map_url"] = payload.generated_map_url
            update_data["change_percentage"] = payload.change_percentage
        elif payload.status == "failed":
            update_data["error_message"] = payload.error_message

        area_id = await db.update_analysis_result(payload.result_id, update_data)
        if area_id and payload.status in {"completed", "failed"}:
            await db.update_monitoring_area(
                area_id,
                {"status": "active" if payload.status == "completed" else "error"},
            )
        logger.info(
            "Analysis result %s updated to %s.",
            payload.result_id,
            payload.status,
        )
        return {"message": "Callback processed successfully"}
    except Exception as e:
        logger.error(
            "Failed to process analysis completion callback for result %s: %s",
            payload.result_id,
            e,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to process callback.",
        )
