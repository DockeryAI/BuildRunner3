"""
Tests for BuildRunner 3.0 API config endpoints

Because configuration management is always simple and never breaks, right?
"""

import pytest
from fastapi.testclient import TestClient
import os
from pathlib import Path

from api.main import app, config_service


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture(autouse=True)
def clean_project_config():
    """Clean project config before and after each test"""
    config_path = config_service.project_config_path
    if config_path.exists():
        # Backup existing config
        backup = config_path.with_suffix(".bak")
        if config_path.exists():
            config_path.rename(backup)

    yield

    # Restore backup
    if backup.exists():
        backup.rename(config_path)


def test_get_merged_config(client):
    """Test getting merged configuration"""
    response = client.get("/config")
    assert response.status_code == 200

    data = response.json()
    assert "global_config" in data
    assert "project_config" in data
    assert "merged" in data
    assert data["source"] == "merged"

    # Should have default config values
    assert "ai_behavior" in data["merged"]
    assert "auto_commit" in data["merged"]
    assert "testing" in data["merged"]
    assert "notifications" in data["merged"]


def test_get_global_config(client):
    """Test getting global configuration"""
    response = client.get("/config?source=global")
    assert response.status_code == 200

    data = response.json()
    assert data["source"] == "global"
    assert "merged" in data


def test_get_project_config(client):
    """Test getting project configuration"""
    response = client.get("/config?source=project")
    assert response.status_code == 200

    data = response.json()
    assert data["source"] == "project"


def test_update_config(client):
    """Test updating configuration"""
    updates = {
        "ai_behavior": {
            "auto_suggest_tests": False,
            "verbosity": "verbose"
        },
        "testing": {
            "auto_run": True,
            "coverage_threshold": 90
        }
    }

    response = client.patch("/config", json=updates)
    assert response.status_code == 200

    data = response.json()
    assert data["project_config"]["ai_behavior"]["auto_suggest_tests"] is False
    assert data["project_config"]["ai_behavior"]["verbosity"] == "verbose"
    assert data["project_config"]["testing"]["auto_run"] is True
    assert data["project_config"]["testing"]["coverage_threshold"] == 90


def test_update_config_partial(client):
    """Test partial config update"""
    updates = {
        "ai_behavior": {
            "verbosity": "quiet"
        }
    }

    response = client.patch("/config", json=updates)
    assert response.status_code == 200

    data = response.json()
    # Should only update specified values
    assert data["project_config"]["ai_behavior"]["verbosity"] == "quiet"


def test_get_config_schema(client):
    """Test getting config schema"""
    response = client.get("/config/schema")
    assert response.status_code == 200

    data = response.json()
    assert "schema" in data
    schema = data["schema"]

    # Check schema structure
    assert schema["type"] == "object"
    assert "properties" in schema
    assert "ai_behavior" in schema["properties"]
    assert "auto_commit" in schema["properties"]
    assert "testing" in schema["properties"]
    assert "notifications" in schema["properties"]


def test_config_persistence(client):
    """Test that config updates persist"""
    # Update config
    updates = {
        "ai_behavior": {
            "verbosity": "verbose",
            "max_retries": 5
        }
    }

    response1 = client.patch("/config", json=updates)
    assert response1.status_code == 200

    # Get config again
    response2 = client.get("/config?source=project")
    assert response2.status_code == 200

    data = response2.json()
    assert data["project_config"]["ai_behavior"]["verbosity"] == "verbose"
    assert data["project_config"]["ai_behavior"]["max_retries"] == 5


def test_config_merge_priority(client):
    """Test that project config overrides global config"""
    # Set project config
    updates = {
        "ai_behavior": {
            "verbosity": "verbose"
        }
    }

    client.patch("/config", json=updates)

    # Get merged config
    response = client.get("/config")
    data = response.json()

    # Project setting should override global/default
    assert data["merged"]["ai_behavior"]["verbosity"] == "verbose"


def test_config_default_values(client):
    """Test that default config values are present"""
    response = client.get("/config")
    data = response.json()

    merged = data["merged"]

    # Check default values
    assert "ai_behavior" in merged
    assert "auto_suggest_tests" in merged["ai_behavior"]
    assert "verbosity" in merged["ai_behavior"]

    assert "auto_commit" in merged
    assert "enabled" in merged["auto_commit"]

    assert "testing" in merged
    assert "coverage_threshold" in merged["testing"]

    assert "notifications" in merged
    assert "enabled" in merged["notifications"]


def test_update_all_config_sections(client):
    """Test updating all config sections"""
    updates = {
        "ai_behavior": {
            "auto_suggest_tests": True,
            "auto_fix_errors": True,
            "verbosity": "verbose",
            "max_retries": 5
        },
        "auto_commit": {
            "enabled": True,
            "on_feature_complete": True,
            "on_tests_pass": True,
            "require_approval": False
        },
        "testing": {
            "auto_run": True,
            "run_on_save": True,
            "coverage_threshold": 90,
            "fail_on_coverage_drop": True
        },
        "notifications": {
            "enabled": True,
            "on_error": True,
            "on_test_fail": True,
            "on_feature_complete": True
        }
    }

    response = client.patch("/config", json=updates)
    assert response.status_code == 200

    # Verify all sections updated
    response = client.get("/config?source=project")
    data = response.json()
    project_config = data["project_config"]

    assert project_config["ai_behavior"]["verbosity"] == "verbose"
    assert project_config["auto_commit"]["enabled"] is True
    assert project_config["testing"]["coverage_threshold"] == 90
    assert project_config["notifications"]["enabled"] is True


def test_config_file_creation(client):
    """Test that config file is created when updating"""
    config_path = config_service.project_config_path

    # Remove config file if it exists
    if config_path.exists():
        config_path.unlink()

    # Update config
    updates = {"ai_behavior": {"verbosity": "quiet"}}
    response = client.patch("/config", json=updates)
    assert response.status_code == 200

    # Verify file was created
    assert config_path.exists()
