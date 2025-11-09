"""
Quick test script to verify the callback endpoint accepts the new structure.
Run this after starting the backend server.
"""

import requests
import json

# Test callback payload matching worker output
test_payload = {
    "result_id": "test_result_123",
    "status": "completed",
    "image_urls": {
        "baseline_image": "https://storage.googleapis.com/bucket/area/images/2024-10-15_sentinel.tif",
        "current_image": "https://storage.googleapis.com/bucket/area/images/2024-11-10_sentinel.tif",
        "baseline_computed": "https://storage.googleapis.com/bucket/area/computed/2024-10-15_forest.tif",
        "current_computed": "https://storage.googleapis.com/bucket/area/computed/2024-11-10_forest.tif",
        "difference_image": "https://storage.googleapis.com/bucket/area/comparisons/test_result_123_diff.tif"
    },
    "metrics": {
        "analysis_type": "forest",
        "baseline_date": "2024-10-15",
        "current_date": "2024-11-10",
        "baseline_cloud_coverage": 12.5,
        "current_cloud_coverage": 8.3,
        "valid_pixels_percentage": 85.7,
        "loss_hectares": 45.2,
        "gain_hectares": 12.8,
        "stable_hectares": 234.5,
        "total_hectares": 292.5,
        "loss_percentage": 15.45,
        "gain_percentage": 4.38,
        "net_change_percentage": -11.07
    },
    "bounds": [76.95, 9.82, 77.10, 9.97]
}

def test_callback():
    """Test the callback endpoint with new payload structure."""
    url = "http://localhost:8000/callbacks/analysis-complete"
    
    print("Testing callback endpoint...")
    print(f"URL: {url}")
    print(f"Payload: {json.dumps(test_payload, indent=2)}")
    
    try:
        response = requests.post(url, json=test_payload, timeout=10)
        print(f"\nResponse Status: {response.status_code}")
        print(f"Response Body: {response.json()}")
        
        if response.status_code == 200:
            print("\n✅ SUCCESS: Callback endpoint accepts new structure!")
        else:
            print(f"\n❌ FAILED: Status {response.status_code}")
            
    except requests.exceptions.ConnectionError:
        print("\n❌ ERROR: Could not connect to backend. Is it running?")
        print("Start backend with: uvicorn main:app --reload")
    except Exception as e:
        print(f"\n❌ ERROR: {e}")

if __name__ == "__main__":
    test_callback()
