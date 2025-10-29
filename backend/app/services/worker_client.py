"""
This module provides a client for communicating with the Analysis Worker service.
It handles making asynchronous HTTP calls to trigger satellite image analysis.
"""

import logging
from typing import List, Optional

import httpx

from app.models.monitoring_area import LatLng
from app.utils.geometry import polygon_to_worker_coordinates

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class WorkerClient:
    def __init__(self, worker_url: str):
        self.worker_url = worker_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("WorkerClient initialized with URL: %s", self.worker_url)
    
    @property
    def client(self):
        """Lazy initialization of HTTP client"""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client
    
    async def close(self):
        """Close the HTTP client"""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    async def trigger_analysis(
        self, area_id: str, polygon: List[LatLng], area_type: str, is_baseline: bool
    ) -> bool:
        """
        Triggers an analysis job on the Analysis Worker service.

        Args:
            area_id (str): The ID of the monitoring area.
            polygon (List[LatLng]): The polygon vertices of the area.
            area_type (str): The type of monitoring (e.g., "forest", "water").
            is_baseline (bool): True if this is the initial baseline analysis.

        Returns:
            bool: True if the analysis was successfully triggered, False otherwise.
        """
        endpoint = f"{self.worker_url}/analyze"
        payload = {
            "area_id": area_id,
            "polygon": polygon_to_worker_coordinates(polygon),
            "type": area_type,
            "is_baseline": is_baseline,
        }

        try:
            # In a real scenario, you'd add authentication (e.g., service account token)
            response = await self.client.post(endpoint, json=payload, timeout=30.0)
            response.raise_for_status()  # Raise an exception for bad status codes
            logger.info(
                "Successfully triggered analysis for area %s. Worker response: %s",
                area_id, response.json()
            )
            return True
        except httpx.RequestError as e:
            logger.error("Failed to connect to Analysis Worker for area %s: %s", area_id, e)
            return False
        except httpx.HTTPStatusError as e:
            logger.error(
                "Analysis Worker returned error for area %s - Status: %s, Response: %s",
                area_id, e.response.status_code, e.response.text
            )
            return False
        except Exception as e:
            logger.error("An unexpected error occurred triggering analysis for area %s: %s", area_id, e)
            return False
