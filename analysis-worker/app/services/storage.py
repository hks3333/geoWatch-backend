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
    
    # Start all exports in parallel
    tasks = {}
    for key, blob_path in paths.items():
        image = images[key]
        description = f"{result_id}_{key}"
        
        export_params = {
            'image': image,
            'description': description,
            'bucket': bucket_name,
            'fileNamePrefix': blob_path.replace('.tif', ''),
            'region': geometry,
            'scale': 10,
            'crs': 'EPSG:3857',
            'maxPixels': 1e13,
            'fileFormat': 'GeoTIFF',
            'formatOptions': {'cloudOptimized': True}
        }
        
        logger.info("Starting EE export: %s to gs://%s/%s", description, bucket_name, blob_path)
        task = ee.batch.Export.image.toCloudStorage(**export_params)
        task.start()
        tasks[key] = {'task': task, 'blob_path': blob_path, 'description': description}
    
    # Wait for all tasks to complete
    import time
    start_time = time.time()
    max_wait = 500
    urls = {}
    
    while tasks and (time.time() - start_time) < max_wait:
        for key in list(tasks.keys()):
            task_info = tasks[key]
            status = task_info['task'].status()
            state = status['state']
            
            if state == 'COMPLETED':
                blob_path = task_info['blob_path']
                final_blob_path = blob_path if blob_path.endswith('.tif') else f"{blob_path}.tif"
                urls[key] = f"https://storage.googleapis.com/{bucket_name}/{final_blob_path}"
                logger.info("Successfully exported %s: %s", key, urls[key])
                del tasks[key]
            elif state in ['FAILED', 'CANCELLED', 'CANCEL_REQUESTED']:
                error_msg = status.get('error_message', 'Unknown error')
                raise RuntimeError(f"EE export failed for {task_info['description']}: {error_msg}")
        
        if tasks:
            time.sleep(5)
    
    if tasks:
        raise TimeoutError(f"Exports timed out after {max_wait}s. Remaining: {list(tasks.keys())}")
    
    return urls

