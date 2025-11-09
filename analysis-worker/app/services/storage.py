"""Google Cloud Storage utilities for persisting analysis visualisations."""

from __future__ import annotations

import logging
import time
from datetime import timedelta
from io import BytesIO
from typing import Dict, Optional

import ee
import httpx
from google.cloud import storage

logger = logging.getLogger(__name__)


def _export_ee_image_to_gcs(
    image: ee.Image,
    geometry: ee.Geometry,
    bucket_name: str,
    blob_path: str,
    description: str,
    file_format: str = 'GeoTIFF',
    max_wait_seconds: int = 300,
) -> str:
    """
    Export an Earth Engine image to GCS as Cloud-Optimized GeoTIFF.
    Returns the public HTTPS URL.
    """
    # Configure export parameters for COG
    export_params = {
        'image': image,
        'description': description,
        'bucket': bucket_name,
        'fileNamePrefix': blob_path.replace('.tif', ''),
        'region': geometry,
        'scale': 10,  # 10m resolution for Sentinel-2
        'crs': 'EPSG:3857',  # Web Mercator for Leaflet compatibility
        'maxPixels': 1e13,
        'fileFormat': file_format,
        'formatOptions': {
            'cloudOptimized': True,  # Enable COG
        }
    }
    
    logger.info("Starting EE export: %s to gs://%s/%s", description, bucket_name, blob_path)
    
    # Start the export task
    task = ee.batch.Export.image.toCloudStorage(**export_params)
    task.start()
    
    # Wait for task completion
    start_time = time.time()
    while True:
        status = task.status()
        state = status['state']
        
        if state == 'COMPLETED':
            logger.info("Export completed: %s", description)
            break
        elif state == 'FAILED':
            error_msg = status.get('error_message', 'Unknown error')
            raise RuntimeError(f"EE export failed for {description}: {error_msg}")
        elif state in ['CANCELLED', 'CANCEL_REQUESTED']:
            raise RuntimeError(f"EE export cancelled for {description}")
        
        # Check timeout
        elapsed = time.time() - start_time
        if elapsed > max_wait_seconds:
            task.cancel()
            raise TimeoutError(f"Export timed out after {max_wait_seconds}s for {description}")
        
        # Wait before checking again
        time.sleep(5)
    
    # Construct public URL
    # EE exports append .tif automatically
    final_blob_path = blob_path if blob_path.endswith('.tif') else f"{blob_path}.tif"
    public_url = f"https://storage.googleapis.com/{bucket_name}/{final_blob_path}"
    
    return public_url


def export_analysis_images_to_gcs(
    images: Dict[str, ee.Image],
    geometry: ee.Geometry,
    result_id: str,
    area_id: str,
    analysis_type: str,
    baseline_date: str,
    current_date: str,
    gcp_project_id: str,
    bucket_name: str,
) -> Dict[str, str]:
    """
    Export all analysis images to GCS as Cloud-Optimized GeoTIFFs.
    Returns dict with URLs for each image type.
    
    Storage structure:
    gs://bucket/area_id/
        images/
            YYYY-MM-DD_sentinel.tif
        computed/
            YYYY-MM-DD_forest.tif or YYYY-MM-DD_water.tif
        comparisons/
            result_id_diff.tif
    """
    # Initialize GCS client (for verification, EE handles upload)
    storage_client = storage.Client(project=gcp_project_id)
    bucket = storage_client.bucket(bucket_name)
    
    # Define blob paths
    base_path = f"{area_id}"
    
    paths = {
        'baseline_image': f"{base_path}/images/{baseline_date}_sentinel.tif",
        'current_image': f"{base_path}/images/{current_date}_sentinel.tif",
        'baseline_computed': f"{base_path}/computed/{baseline_date}_{analysis_type}.tif",
        'current_computed': f"{base_path}/computed/{current_date}_{analysis_type}.tif",
        'difference_image': f"{base_path}/comparisons/{result_id}_diff.tif",
    }
    
    urls = {}
    
    # Export each image
    for key, blob_path in paths.items():
        image = images[key]
        description = f"{result_id}_{key}"
        
        try:
            url = _export_ee_image_to_gcs(
                image=image,
                geometry=geometry,
                bucket_name=bucket_name,
                blob_path=blob_path,
                description=description,
                max_wait_seconds=300,
            )
            urls[key] = url
            logger.info("Successfully exported %s: %s", key, url)
        except Exception as e:
            logger.error("Failed to export %s: %s", key, e)
            raise
    
    return urls

