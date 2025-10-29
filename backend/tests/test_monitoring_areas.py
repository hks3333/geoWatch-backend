
import pytest
from fastapi.testclient import TestClient
from main import app  # Import your FastAPI app

client = TestClient(app)

def test_create_and_get_monitoring_area():
    # 1. Create a new monitoring area
    create_response = client.post(
        "/api/monitoring-areas",
        json={
            "name": "Test Area",
            "type": "forest",
            "rectangle_bounds": {
                "southWest": {"lat": 10.0, "lng": 20.0},
                "northEast": {"lat": 10.1, "lng": 20.1},
            },
        },
    )
    assert create_response.status_code == 202
    area_id = create_response.json()["area_id"]
    assert area_id is not None

    # 2. Retrieve the area by ID
    get_response = client.get(f"/api/monitoring-areas/{area_id}")
    assert get_response.status_code == 200
    area_data = get_response.json()
    assert area_data["name"] == "Test Area"
    assert area_data["user_id"] == "demo_user"

    # 3. Get all areas and check if the new area is present
    get_all_response = client.get("/api/monitoring-areas")
    assert get_all_response.status_code == 200
    areas = get_all_response.json()
    assert any(area["area_id"] == area_id for area in areas)

    # 4. Update the area name
    update_response = client.patch(
        f"/api/monitoring-areas/{area_id}",
        json={"name": "Updated Test Area"},
    )
    assert update_response.status_code == 200
    updated_area_data = update_response.json()
    assert updated_area_data["name"] == "Updated Test Area"

    # 5. Get latest analysis (should be 404)
    get_latest_response = client.get(f"/api/monitoring-areas/{area_id}/latest")
    assert get_latest_response.status_code == 404

    # 6. Delete the area
    delete_response = client.delete(f"/api/monitoring-areas/{area_id}")
    assert delete_response.status_code == 200

    # 7. Verify the area is soft-deleted
    get_deleted_response = client.get(f"/api/monitoring-areas/{area_id}")
    assert get_deleted_response.status_code == 200 # The area still exists
    assert get_deleted_response.json()["status"] == "deleted"

    # 8. Verify the area is not in the main list anymore
    get_all_after_delete_response = client.get("/api/monitoring-areas")
    assert get_all_after_delete_response.status_code == 200
    areas_after_delete = get_all_after_delete_response.json()
    assert not any(area["area_id"] == area_id for area in areas_after_delete)

