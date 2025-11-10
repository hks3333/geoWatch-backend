"""
This module provides a client for sending analysis completion callbacks
to the backend API. It handles authentication by generating OIDC tokens
for secure service-to-service communication.
"""

import asyncio
import logging

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
        logger.info("CallbackClient initialized for URL: %s", self.backend_api_url)

    async def close(self) -> None:
        """No-op close maintained for backwards compatibility."""
        logger.debug("CallbackClient.close() called - no persistent client to close.")

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
        
        headers = {}

        try:
            if settings.BACKEND_ENV != "local":
                token = self._get_oidc_token()
                headers["Authorization"] = f"Bearer {token}"
            else:
                logger.info(
                    "Skipping OIDC authentication for local environment callback"
                )

            # Send the POST request to the backend API with lightweight retry/backoff
            max_attempts = 3
            backoff = 1.0
            last_exception: Exception | None = None

            for attempt in range(1, max_attempts + 1):
                try:
                    async with httpx.AsyncClient() as client:
                        response = await client.post(
                            callback_url,
                            json=payload.model_dump(),
                            headers=headers,
                            timeout=30.0,
                        )
                    response.raise_for_status()
                    logger.info(
                        "Successfully sent callback for result_id: %s on attempt %d. Status: %s",
                        payload.result_id,
                        attempt,
                        response.status_code,
                    )
                    break
                except (httpx.HTTPStatusError, httpx.TransportError) as send_exc:
                    last_exception = send_exc
                    status_text = (
                        send_exc.response.status_code
                        if isinstance(send_exc, httpx.HTTPStatusError)
                        else "transport"
                    )
                    logger.warning(
                        "Callback attempt %d/%d failed for result_id %s (status: %s). Retrying in %.1fs...",
                        attempt,
                        max_attempts,
                        payload.result_id,
                        status_text,
                        backoff,
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(backoff)
                        backoff *= 2
                except Exception as send_exc:
                    last_exception = send_exc
                    logger.error(
                        "Unexpected error during callback attempt %d/%d for result_id %s: %s",
                        attempt,
                        max_attempts,
                        payload.result_id,
                        send_exc,
                    )
                    if attempt < max_attempts:
                        await asyncio.sleep(backoff)
                        backoff *= 2

            else:
                # Only executed if loop wasn't broken
                raise last_exception  # type: ignore[misc]
        except httpx.HTTPStatusError as e:
            logger.error(
                "Callback failed for result_id: %s. Status: %s, Response: %s",
                payload.result_id,
                e.response.status_code,
                e.response.text,
            )
        except Exception as e:
            logger.error(
                "An unexpected error occurred while sending callback for result_id: %s: %s",
                payload.result_id,
                e,
            )


# Create a single, reusable instance of the callback client
callback_client = CallbackClient(backend_api_url=settings.BACKEND_API_URL)
