"""
Tests for BuildRunner 3.0 API debug endpoints

Testing the debugging tools. So meta it hurts.
"""

import pytest
from fastapi.testclient import TestClient
import asyncio

from api.main import app, error_watcher, test_runner


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def cleanup():
    """Clean up after each test"""
    yield

    # Clear errors
    error_watcher.clear_errors()


def test_get_debug_status(client):
    """Test getting system status"""
    response = client.get("/debug/status")
    assert response.status_code == 200

    data = response.json()
    assert "status" in data
    assert data["status"] in ["healthy", "degraded", "critical"]
    assert "uptime" in data
    assert "version" in data
    assert data["version"] == "3.0.0"
    assert "features_loaded" in data
    assert "tests_running" in data
    assert "error_count" in data
    assert "issues" in data


def test_debug_status_healthy(client):
    """Test that status is healthy with no issues"""
    # Clear any existing errors
    error_watcher.clear_errors()

    response = client.get("/debug/status")
    data = response.json()

    # Should be healthy with no critical errors
    assert data["error_count"] == 0


def test_get_blockers(client):
    """Test getting blockers"""
    response = client.get("/debug/blockers")
    assert response.status_code == 200

    data = response.json()
    assert isinstance(data, list)


def test_run_test_debug(client):
    """Test running tests via debug endpoint"""
    response = client.post("/debug/test")
    assert response.status_code == 200

    data = response.json()
    assert "id" in data
    assert "timestamp" in data
    assert "status" in data
    assert "total" in data
    assert "passed" in data
    assert "failed" in data
    assert "duration" in data


def test_get_errors_empty(client):
    """Test getting errors when none exist"""
    error_watcher.clear_errors()

    response = client.get("/debug/errors")
    assert response.status_code == 200

    data = response.json()
    assert data["total_errors"] == 0
    assert "by_category" in data
    assert "by_severity" in data
    assert "recent_errors" in data
    assert len(data["recent_errors"]) == 0


def test_get_errors_with_data(client):
    """Test getting errors when some exist"""
    # Add some mock errors
    error_watcher.errors = [
        {
            "id": "err1",
            "timestamp": "2025-01-01T00:00:00",
            "message": "Test error 1",
            "traceback": None,
            "file_path": "test.py",
            "line_number": 10,
            "category": {"type": "syntax", "severity": "high", "confidence": 0.9},
            "context": {},
            "suggestions": ["Fix syntax"],
            "resolved": False,
        },
        {
            "id": "err2",
            "timestamp": "2025-01-01T00:01:00",
            "message": "Test error 2",
            "traceback": None,
            "file_path": "test.py",
            "line_number": 20,
            "category": {"type": "runtime", "severity": "medium", "confidence": 0.8},
            "context": {},
            "suggestions": ["Check runtime"],
            "resolved": False,
        },
    ]

    response = client.get("/debug/errors")
    assert response.status_code == 200

    data = response.json()
    assert data["total_errors"] == 2
    assert data["by_category"]["syntax"] == 1
    assert data["by_category"]["runtime"] == 1


def test_get_errors_filter_by_category(client):
    """Test filtering errors by category"""
    # Add mock errors
    error_watcher.errors = [
        {
            "id": "err1",
            "timestamp": "2025-01-01T00:00:00",
            "message": "Syntax error",
            "traceback": None,
            "file_path": "test.py",
            "line_number": 10,
            "category": {"type": "syntax", "severity": "high", "confidence": 0.9},
            "context": {},
            "suggestions": [],
            "resolved": False,
        },
        {
            "id": "err2",
            "timestamp": "2025-01-01T00:01:00",
            "message": "Runtime error",
            "traceback": None,
            "file_path": "test.py",
            "line_number": 20,
            "category": {"type": "runtime", "severity": "medium", "confidence": 0.8},
            "context": {},
            "suggestions": [],
            "resolved": False,
        },
    ]

    response = client.get("/debug/errors?category=syntax")
    assert response.status_code == 200

    data = response.json()
    # Should only have syntax errors in recent_errors
    for error in data["recent_errors"]:
        assert error["category"]["type"] == "syntax"


def test_get_errors_filter_by_severity(client):
    """Test filtering errors by severity"""
    error_watcher.errors = [
        {
            "id": "err1",
            "timestamp": "2025-01-01T00:00:00",
            "message": "Critical error",
            "traceback": None,
            "file_path": "test.py",
            "line_number": 10,
            "category": {"type": "syntax", "severity": "critical", "confidence": 0.9},
            "context": {},
            "suggestions": [],
            "resolved": False,
        },
        {
            "id": "err2",
            "timestamp": "2025-01-01T00:01:00",
            "message": "Low error",
            "traceback": None,
            "file_path": "test.py",
            "line_number": 20,
            "category": {"type": "runtime", "severity": "low", "confidence": 0.8},
            "context": {},
            "suggestions": [],
            "resolved": False,
        },
    ]

    response = client.get("/debug/errors?severity=critical")
    assert response.status_code == 200

    data = response.json()
    for error in data["recent_errors"]:
        assert error["category"]["severity"] == "critical"


def test_get_errors_unresolved_only(client):
    """Test getting only unresolved errors"""
    error_watcher.errors = [
        {
            "id": "err1",
            "timestamp": "2025-01-01T00:00:00",
            "message": "Unresolved error",
            "traceback": None,
            "file_path": "test.py",
            "line_number": 10,
            "category": {"type": "syntax", "severity": "high", "confidence": 0.9},
            "context": {},
            "suggestions": [],
            "resolved": False,
        },
        {
            "id": "err2",
            "timestamp": "2025-01-01T00:01:00",
            "message": "Resolved error",
            "traceback": None,
            "file_path": "test.py",
            "line_number": 20,
            "category": {"type": "runtime", "severity": "medium", "confidence": 0.8},
            "context": {},
            "suggestions": [],
            "resolved": True,
        },
    ]

    response = client.get("/debug/errors?unresolved_only=true")
    assert response.status_code == 200

    data = response.json()
    for error in data["recent_errors"]:
        assert error["resolved"] is False


def test_retry_command(client):
    """Test command retry endpoint"""
    response = client.post("/debug/retry/test-command-123")
    assert response.status_code == 200

    data = response.json()
    assert "command_id" in data
    assert data["command_id"] == "test-command-123"


def test_retry_command_with_force(client):
    """Test command retry with force flag"""
    response = client.post("/debug/retry/test-command-123?force=true")
    assert response.status_code == 200

    data = response.json()
    assert "command_id" in data
