"""Google Cloud Storage utilities for persisting analysis visualisations."""

from __future__ import annotations

import logging
from datetime import timedelta
from io import BytesIO
from typing import Optional

from google.cloud import storage

logger = logging.getLogger(__name__)


def upload_visualization_to_gcs(
    image_bytes: bytes,
    result_id: str,
    gcp_project_id: str,
    bucket_name: str,
    signed_url_ttl: timedelta = timedelta(days=7),
) -> str:
    """Upload the change visualisation PNG bytes to Cloud Storage and return a signed URL."""

    if not image_bytes:
        raise ValueError("image_bytes must not be empty")

    buffer = BytesIO(image_bytes)

    client = storage.Client(project=gcp_project_id)
    bucket = client.bucket(bucket_name)
    blob_path = f"analysis-maps/{result_id}-change-map.png"
    blob = bucket.blob(blob_path)

    logger.info("Uploading change visualisation to gs://%s/%s", bucket_name, blob_path)
    blob.upload_from_file(buffer, content_type="image/png")

    public_https = f"https://storage.googleapis.com/{bucket_name}/{blob_path}"
    return public_https

