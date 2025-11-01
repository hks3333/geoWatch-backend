"""
This module provides a client for sending analysis completion callbacks
to the backend API. It handles authentication by generating OIDC tokens
for secure service-to-service communication.
"""

import logging
from typing import Optional

import httpx
from google.auth.transport import requests
from google.oauth2 import id_token

from app.config import settings
from app.models import CallbackPayload

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class CallbackClient:
    """
    A client for making authenticated calls to the backend API's callback endpoint.
    Ensures that the worker can securely notify the backend of analysis completion
    or failure.
    """

    def __init__(self, backend_api_url: str):
        """
        Initializes the CallbackClient with the backend API URL.

        Args:
            backend_api_url (str): The base URL of the backend API.
        """
        self.backend_api_url = backend_api_url.rstrip("/")
        self._client: Optional[httpx.AsyncClient] = None
        logger.info("CallbackClient initialized for URL: %s", self.backend_api_url)

    @property
    def client(self) -> httpx.AsyncClient:
        """Lazy initialization of the httpx.AsyncClient."""
        if self._client is None:
            self._client = httpx.AsyncClient()
        return self._client

    async def close(self) -> None:
        """Closes the httpx.AsyncClient."""
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    def _get_oidc_token(self) -> str:
        """
        Generates a Google-signed OIDC token for authenticating with the backend API.

        Returns:
            str: The generated OIDC token.

        Raises:
            Exception: If token generation fails.
        """
        try:
            # Create a request object for the token generation
            auth_req = requests.Request()

            # Generate the OIDC token for the target audience (the backend API URL)
            token = id_token.fetch_id_token(auth_req, self.backend_api_url)
            logger.info("Successfully generated OIDC token.")
            return token
        except Exception as e:
            logger.error("Failed to generate OIDC token: %s", e)
            raise

    async def send_callback(
        self, payload: CallbackPayload
    ) -> None:
        """
        Sends the analysis result payload to the backend API's callback endpoint.

        This method constructs the full callback URL, generates an OIDC token for
        authentication, and sends the payload as a POST request.

        Args:
            payload (CallbackPayload): The data to be sent in the callback.
        """
        callback_url = f"{self.backend_api_url}/callbacks/analysis-complete"
        
        try:
            # Generate the OIDC token for service-to-service authentication
            token = self._get_oidc_token()
            headers = {"Authorization": f"Bearer {token}"}

            # Send the POST request to the backend API
            response = await self.client.post(
                callback_url, json=payload.model_dump(), headers=headers, timeout=30.0
            )
            response.raise_for_status()  # Raise an exception for non-2xx status codes
            logger.info(
                "Successfully sent callback for result_id: %s. Status: %s",
                payload.result_id,
                response.status_code,
            )
        except httpx.HTTPStatusError as e:
            logger.error(
                "Callback failed for result_id: %s. Status: %s, Response: %s",
                payload.result_id,
                e.response.status_code,
                e.response.text,
            )
            # Depending on the error, you might want to implement a retry mechanism
        except Exception as e:
            logger.error(
                "An unexpected error occurred while sending callback for result_id: %s: %s",
                payload.result_id,
                e,
            )


# Create a single, reusable instance of the callback client
callback_client = CallbackClient(backend_api_url=settings.BACKEND_API_URL)
