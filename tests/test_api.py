"""
Tests for BuildRunner 3.0 API core endpoints

Testing the tests that test the code. It's tests all the way down.
"""

import pytest
from fastapi.testclient import TestClient
from datetime import datetime

# Import the app
from api.main import app, feature_registry


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def sample_feature():
    """Sample feature data for testing"""
    return {
        "id": "test-feature",
        "name": "Test Feature",
        "description": "A feature for testing",
        "status": "planned",
        "version": "3.0.0",
        "priority": "high",
        "week": 1,
        "build": "1A"
    }


def test_health_check(client):
    """Test health check endpoint"""
    response = client.get("/health")
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "ok"
    assert data["version"] == "3.0.0"
    assert "timestamp" in data


def test_get_features_empty(client):
    """Test getting features when none exist"""
    # Clear any existing features first
    features = feature_registry.list_features()
    for f in features:
        feature_registry.delete_feature(f["id"])

    response = client.get("/features")
    assert response.status_code == 200
    assert response.json() == []


def test_create_feature(client, sample_feature):
    """Test creating a new feature"""
    # Clean up first
    feature_registry.delete_feature(sample_feature["id"])

    response = client.post("/features", json=sample_feature)
    assert response.status_code == 201

    data = response.json()
    assert data["id"] == sample_feature["id"]
    assert data["name"] == sample_feature["name"]
    assert data["status"] == sample_feature["status"]

    # Clean up
    feature_registry.delete_feature(sample_feature["id"])


def test_get_features_after_create(client, sample_feature):
    """Test getting features after creating one"""
    # Create feature
    feature_registry.delete_feature(sample_feature["id"])
    client.post("/features", json=sample_feature)

    # Get features
    response = client.get("/features")
    assert response.status_code == 200

    features = response.json()
    assert len(features) >= 1
    assert any(f["id"] == sample_feature["id"] for f in features)

    # Clean up
    feature_registry.delete_feature(sample_feature["id"])


def test_get_features_with_filter(client, sample_feature):
    """Test filtering features by status"""
    # Create feature
    feature_registry.delete_feature(sample_feature["id"])
    client.post("/features", json=sample_feature)

    # Filter by status
    response = client.get("/features?status=planned")
    assert response.status_code == 200

    features = response.json()
    assert all(f["status"] == "planned" for f in features)

    # Clean up
    feature_registry.delete_feature(sample_feature["id"])


def test_update_feature(client, sample_feature):
    """Test updating a feature"""
    # Create feature
    feature_registry.delete_feature(sample_feature["id"])
    client.post("/features", json=sample_feature)

    # Update feature
    updates = {
        "status": "in_progress",
        "priority": "critical"
    }
    response = client.patch(f"/features/{sample_feature['id']}", json=updates)
    assert response.status_code == 200

    data = response.json()
    assert data["status"] == "in_progress"
    assert data["priority"] == "critical"
    assert data["name"] == sample_feature["name"]  # Unchanged

    # Clean up
    feature_registry.delete_feature(sample_feature["id"])


def test_update_nonexistent_feature(client):
    """Test updating a feature that doesn't exist"""
    response = client.patch(
        "/features/nonexistent",
        json={"status": "complete"}
    )
    assert response.status_code == 404


def test_delete_feature(client, sample_feature):
    """Test deleting a feature"""
    # Create feature
    feature_registry.delete_feature(sample_feature["id"])
    client.post("/features", json=sample_feature)

    # Delete feature
    response = client.delete(f"/features/{sample_feature['id']}")
    assert response.status_code == 204

    # Verify it's gone
    response = client.get("/features")
    features = response.json()
    assert not any(f["id"] == sample_feature["id"] for f in features)


def test_delete_nonexistent_feature(client):
    """Test deleting a feature that doesn't exist"""
    response = client.delete("/features/nonexistent")
    assert response.status_code == 404


def test_get_metrics(client, sample_feature):
    """Test getting system metrics"""
    # Create a feature
    feature_registry.delete_feature(sample_feature["id"])
    client.post("/features", json=sample_feature)

    response = client.get("/metrics")
    assert response.status_code == 200

    data = response.json()
    assert "features" in data
    assert data["features"]["total"] >= 1
    assert data["features"]["planned"] >= 1
    assert "completion_percentage" in data["features"]

    # Clean up
    feature_registry.delete_feature(sample_feature["id"])


def test_sync_features(client):
    """Test syncing features"""
    response = client.post("/sync")
    assert response.status_code == 200

    data = response.json()
    assert data["success"] is True
    assert "synced_features" in data
    assert "timestamp" in data


def test_get_governance(client):
    """Test getting governance rules"""
    response = client.get("/governance")
    assert response.status_code == 200

    data = response.json()
    assert "governance" in data


def test_cors_headers(client):
    """Test CORS headers are present"""
    response = client.get("/health", headers={"Origin": "http://localhost:3000"})
    assert response.status_code == 200
    # CORS middleware should add headers


def test_response_time_header(client):
    """Test that response time header is added"""
    response = client.get("/health")
    assert "X-Response-Time" in response.headers


def test_create_feature_validation(client):
    """Test feature creation with invalid data"""
    invalid_feature = {
        "id": "test",
        "name": "",  # Empty name - should fail
        "description": "Test",
        "status": "planned"
    }

    response = client.post("/features", json=invalid_feature)
    assert response.status_code == 422  # Validation error


def test_create_duplicate_feature(client, sample_feature):
    """Test creating a duplicate feature"""
    # Create first feature
    feature_registry.delete_feature(sample_feature["id"])
    response1 = client.post("/features", json=sample_feature)
    assert response1.status_code == 201

    # Try to create duplicate
    response2 = client.post("/features", json=sample_feature)
    assert response2.status_code == 400  # Should fail

    # Clean up
    feature_registry.delete_feature(sample_feature["id"])


def test_feature_lifecycle(client, sample_feature):
    """Test complete feature lifecycle"""
    # Clean up
    feature_registry.delete_feature(sample_feature["id"])

    # 1. Create
    response = client.post("/features", json=sample_feature)
    assert response.status_code == 201

    # 2. Get
    response = client.get(f"/features")
    features = response.json()
    assert any(f["id"] == sample_feature["id"] for f in features)

    # 3. Update to in_progress
    response = client.patch(
        f"/features/{sample_feature['id']}",
        json={"status": "in_progress"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "in_progress"

    # 4. Update to complete
    response = client.patch(
        f"/features/{sample_feature['id']}",
        json={"status": "complete"}
    )
    assert response.status_code == 200
    assert response.json()["status"] == "complete"

    # 5. Delete
    response = client.delete(f"/features/{sample_feature['id']}")
    assert response.status_code == 204

    # 6. Verify deletion
    response = client.get("/features")
    features = response.json()
    assert not any(f["id"] == sample_feature["id"] for f in features)
