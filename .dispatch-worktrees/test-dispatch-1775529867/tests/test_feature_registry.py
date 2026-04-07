"""Tests for Feature Registry System"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from core.feature_registry import FeatureRegistry


@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def registry(temp_project):
    """Create FeatureRegistry instance"""
    return FeatureRegistry(temp_project)


class TestFeatureRegistry:
    """Test FeatureRegistry class"""

    def test_init_creates_directory(self, registry):
        """Test initialization creates .buildrunner directory"""
        assert registry.features_file.parent.exists()

    def test_load_creates_default_structure(self, registry):
        """Test loading creates default structure when file doesn't exist"""
        data = registry.load()

        assert "project" in data
        assert "version" in data
        assert "features" in data
        assert "metrics" in data
        assert isinstance(data["features"], list)

    def test_save_and_load(self, registry):
        """Test saving and loading features.json"""
        test_data = {"project": "Test", "features": []}
        registry.save(test_data)

        loaded = registry.load()
        assert loaded["project"] == "Test"

    def test_add_feature(self, registry):
        """Test adding a new feature"""
        feature = registry.add_feature(
            feature_id="test-feature",
            name="Test Feature",
            description="A test feature",
            priority="high",
            week=1,
            build="1A",
        )

        assert feature["id"] == "test-feature"
        assert feature["name"] == "Test Feature"
        assert feature["status"] == "planned"
        assert feature["priority"] == "high"
        assert feature["week"] == 1
        assert feature["build"] == "1A"

        # Verify it was saved
        data = registry.load()
        assert len(data["features"]) == 1

    def test_add_duplicate_feature_raises_error(self, registry):
        """Test adding duplicate feature raises ValueError"""
        registry.add_feature("test", "Test", "Description")

        with pytest.raises(ValueError, match="already exists"):
            registry.add_feature("test", "Test 2", "Description 2")

    def test_complete_feature(self, registry):
        """Test marking feature as complete"""
        registry.add_feature("test", "Test", "Description")
        feature = registry.complete_feature("test")

        assert feature["status"] == "complete"

        # Verify metrics updated
        data = registry.load()
        assert data["metrics"]["features_complete"] == 1
        assert data["metrics"]["completion_percentage"] == 100

    def test_complete_nonexistent_feature_raises_error(self, registry):
        """Test completing nonexistent feature raises ValueError"""
        with pytest.raises(ValueError, match="not found"):
            registry.complete_feature("nonexistent")

    def test_update_feature(self, registry):
        """Test updating feature properties"""
        registry.add_feature("test", "Test", "Description")
        updated = registry.update_feature(
            "test", name="Updated Name", description="Updated Description", status="in_progress"
        )

        assert updated["name"] == "Updated Name"
        assert updated["description"] == "Updated Description"
        assert updated["status"] == "in_progress"

    def test_update_nonexistent_feature_returns_none(self, registry):
        """Test updating nonexistent feature returns None"""
        result = registry.update_feature("nonexistent", name="Test")
        assert result is None

    def test_get_feature(self, registry):
        """Test getting a specific feature"""
        registry.add_feature("test", "Test", "Description")
        feature = registry.get_feature("test")

        assert feature is not None
        assert feature["id"] == "test"

    def test_get_nonexistent_feature_returns_none(self, registry):
        """Test getting nonexistent feature returns None"""
        feature = registry.get_feature("nonexistent")
        assert feature is None

    def test_list_features(self, registry):
        """Test listing all features"""
        registry.add_feature("test1", "Test 1", "Description 1")
        registry.add_feature("test2", "Test 2", "Description 2")

        features = registry.list_features()
        assert len(features) == 2

    def test_list_features_filtered_by_status(self, registry):
        """Test listing features filtered by status"""
        registry.add_feature("test1", "Test 1", "Description 1")
        registry.add_feature("test2", "Test 2", "Description 2")
        registry.complete_feature("test1")

        complete = registry.list_features(status="complete")
        planned = registry.list_features(status="planned")

        assert len(complete) == 1
        assert len(planned) == 1
        assert complete[0]["id"] == "test1"

    def test_get_status(self, registry):
        """Test getting overall project status"""
        registry.add_feature("test1", "Test 1", "Description 1")
        registry.add_feature("test2", "Test 2", "Description 2")
        registry.complete_feature("test1")

        status = registry.get_status()

        assert status["total_features"] == 2
        assert status["metrics"]["features_complete"] == 1
        assert status["metrics"]["features_planned"] == 1
        assert status["metrics"]["completion_percentage"] == 50

    def test_metrics_calculation(self, registry):
        """Test metrics are calculated correctly"""
        # Add 4 features
        for i in range(4):
            registry.add_feature(f"test{i}", f"Test {i}", f"Description {i}")

        # Complete 1
        registry.complete_feature("test0")

        # Set 1 in progress
        registry.update_feature("test1", status="in_progress")

        data = registry.load()
        metrics = data["metrics"]

        assert metrics["features_complete"] == 1
        assert metrics["features_in_progress"] == 1
        assert metrics["features_planned"] == 2
        assert metrics["completion_percentage"] == 25  # 1 of 4 complete

    def test_last_updated_changes(self, registry):
        """Test last_updated timestamp changes on modifications"""
        data1 = registry.load()
        original_timestamp = data1.get("last_updated")

        registry.add_feature("test", "Test", "Description")

        data2 = registry.load()
        new_timestamp = data2.get("last_updated")

        assert new_timestamp != original_timestamp
