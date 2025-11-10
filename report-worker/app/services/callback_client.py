"""
Client for sending callbacks to the backend after report generation.
"""
import logging
from typing import Dict, Any

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class CallbackClient:
    """Send report completion callbacks to backend."""
    
    def __init__(self, backend_url: str = None):
        """Initialize callback client."""
        self.backend_url = backend_url or settings.BACKEND_URL
        self.callback_endpoint = f"{self.backend_url}/api/callbacks/report-complete"
    
    async def send_completion_callback(
        self,
        report_id: str,
        area_id: str,
        result_id: str,
        status: str,
        summary: str = None,
        error_message: str = None
    ) -> bool:
        """
        Send report completion callback to backend.
        
        Args:
            report_id: Generated report ID
            area_id: Monitoring area ID
            result_id: Analysis result ID
            status: 'completed' or 'failed'
            summary: Brief summary (if completed)
            error_message: Error details (if failed)
            
        Returns:
            True if callback successful, False otherwise
        """
        payload = {
            "report_id": report_id,
            "area_id": area_id,
            "result_id": result_id,
            "status": status,
            "summary": summary,
            "error_message": error_message
        }
        
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    self.callback_endpoint,
                    json=payload
                )
                
                if response.status_code == 200:
                    logger.info(
                        f"Successfully sent callback for report {report_id}. "
                        f"Status: {response.status_code}"
                    )
                    return True
                else:
                    logger.warning(
                        f"Callback returned non-200 status for report {report_id}: "
                        f"{response.status_code}"
                    )
                    return False
                    
        except Exception as e:
            logger.error(f"Failed to send callback for report {report_id}: {e}")
            return False
