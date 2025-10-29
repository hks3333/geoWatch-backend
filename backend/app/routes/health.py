"""
This module defines the health check endpoint for the GeoWatch backend API.
"""

from fastapi import APIRouter

router = APIRouter()


@router.get("/health", summary="Health check endpoint")
async def health_check():
    """
    Returns a simple status to indicate that the service is healthy.

    This endpoint can be used by load balancers or orchestrators (like Cloud Run)
    to determine the liveness and readiness of the application.
    """
    return {"status": "healthy"}
