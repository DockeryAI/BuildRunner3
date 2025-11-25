"""
Unit tests for PRD Controller

Tests all functionality:
- PRD model creation and serialization
- File loading and parsing
- File saving and generation
- Version control
- Event system
- Natural language parsing
- Rollback functionality
- Concurrent access with locking
"""

import pytest
import tempfile
import shutil
import time
import threading
from pathlib import Path
from datetime import datetime

from core.prd.prd_controller import (
    PRDController,
    PRD,
    PRDFeature,
    PRDVersion,
    PRDChangeEvent,
    ChangeType,
    get_prd_controller,
)


class TestPRDModels:
    """Test PRD data models"""

    def test_prd_feature_creation(self):
        """Test creating PRDFeature"""
        feature = PRDFeature(
            id="test-1",
            name="Test Feature",
            description="Test description",
            priority="high",
            status="planned",
            requirements=["req1", "req2"],
            acceptance_criteria=["ac1", "ac2"],
        )

        assert feature.id == "test-1"
        assert feature.name == "Test Feature"
        assert feature.priority == "high"
        assert len(feature.requirements) == 2
        assert len(feature.acceptance_criteria) == 2

    def test_prd_creation(self):
        """Test creating PRD"""
        features = [PRDFeature(id="f1", name="Feature 1"), PRDFeature(id="f2", name="Feature 2")]

        prd = PRD(
            project_name="Test Project",
            version="1.0.0",
            overview="Test overview",
            features=features,
        )

        assert prd.project_name == "Test Project"
        assert prd.version == "1.0.0"
        assert len(prd.features) == 2

    def test_prd_to_dict(self):
        """Test PRD serialization"""
        feature = PRDFeature(id="f1", name="Feature 1")
        prd = PRD(project_name="Test", features=[feature])

        data = prd.to_dict()

        assert data["project_name"] == "Test"
        assert len(data["features"]) == 1
        assert data["features"][0]["id"] == "f1"

    def test_prd_from_dict(self):
        """Test PRD deserialization"""
        data = {
            "project_name": "Test",
            "version": "1.0.0",
            "features": [{"id": "f1", "name": "Feature 1"}],
        }

        prd = PRD.from_dict(data)

        assert prd.project_name == "Test"
        assert len(prd.features) == 1
        assert prd.features[0].name == "Feature 1"


class TestPRDController:
    """Test PRD Controller functionality"""

    @pytest.fixture
    def temp_spec(self):
        """Create temporary spec file"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"

        spec_path.write_text(
            """# Test Project

**Version:** 1.0.0

## Project Overview

Test project overview

## Feature 1: First Feature

**Priority:** high

### Description

First feature description

### Requirements

- Requirement 1
- Requirement 2

### Acceptance Criteria

- [ ] Criterion 1
- [ ] Criterion 2
"""
        )

        yield spec_path

        shutil.rmtree(temp_dir)

    def test_controller_initialization(self, temp_spec):
        """Test controller can be initialized"""
        controller = PRDController(temp_spec)

        assert controller.spec_path == temp_spec
        assert controller.prd is not None
        assert controller.prd.project_name == "Test Project"

    def test_load_from_file(self, temp_spec):
        """Test loading PRD from file"""
        controller = PRDController(temp_spec)
        controller.load_from_file()

        prd = controller.prd

        assert prd.project_name == "Test Project"
        assert prd.version == "1.0.0"
        assert prd.overview.strip() == "Test project overview"
        assert len(prd.features) == 1
        assert prd.features[0].name == "First Feature"
        assert prd.features[0].priority == "high"
        assert len(prd.features[0].requirements) == 2
        assert len(prd.features[0].acceptance_criteria) == 2

    def test_markdown_parsing(self, temp_spec):
        """Test markdown parsing extracts all sections"""
        controller = PRDController(temp_spec)

        feature = controller.prd.features[0]

        assert "First feature description" in feature.description
        assert "Requirement 1" in feature.requirements
        assert "Criterion 1" in feature.acceptance_criteria

    def test_save_to_file(self, temp_spec):
        """Test saving PRD to file"""
        controller = PRDController(temp_spec)

        # Modify PRD
        controller._prd.project_name = "Modified Project"
        controller._save_to_file()

        # Reload and verify
        controller.load_from_file()
        assert controller.prd.project_name == "Modified Project"

    def test_markdown_generation(self, temp_spec):
        """Test generating markdown from PRD"""
        controller = PRDController(temp_spec)

        markdown = controller._generate_markdown(controller.prd)

        assert "# Test Project" in markdown
        assert "**Version:** 1.0.0" in markdown
        assert "## Feature 1: First Feature" in markdown
        assert "**Priority:** High" in markdown

    def test_update_prd_add_feature(self, temp_spec):
        """Test adding feature via update_prd"""
        controller = PRDController(temp_spec)

        event = controller.update_prd(
            {
                "add_feature": {
                    "id": "new-feature",
                    "name": "New Feature",
                    "description": "New feature description",
                    "priority": "medium",
                }
            },
            author="test",
        )

        assert event.event_type == ChangeType.FEATURE_ADDED
        assert "new-feature" in event.affected_features
        assert len(controller.prd.features) == 2

    def test_update_prd_remove_feature(self, temp_spec):
        """Test removing feature via update_prd"""
        controller = PRDController(temp_spec)

        # Add a feature first
        controller.update_prd(
            {"add_feature": {"id": "to-remove", "name": "To Remove"}}, author="test"
        )

        # Remove it
        event = controller.update_prd({"remove_feature": "to-remove"}, author="test")

        assert event.event_type == ChangeType.FEATURE_REMOVED
        assert "to-remove" in event.affected_features
        assert len(controller.prd.features) == 1

    def test_update_prd_modify_feature(self, temp_spec):
        """Test modifying feature via update_prd"""
        controller = PRDController(temp_spec)

        event = controller.update_prd(
            {
                "update_feature": {
                    "id": "feature-1",
                    "updates": {"description": "Updated description", "priority": "low"},
                }
            },
            author="test",
        )

        assert event.event_type == ChangeType.FEATURE_UPDATED
        assert "feature-1" in event.affected_features

        feature = controller.prd.features[0]
        assert feature.description == "Updated description"
        assert feature.priority == "low"


class TestVersionControl:
    """Test version control functionality"""

    @pytest.fixture
    def controller(self):
        """Create controller with temp spec"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"
        spec_path.write_text("# Test\n")

        controller = PRDController(spec_path)

        yield controller

        shutil.rmtree(temp_dir)

    def test_version_saved_on_update(self, controller):
        """Test version is saved on each update"""
        initial_versions = len(controller.get_versions())

        controller.update_prd({"add_feature": {"id": "f1", "name": "Feature 1"}}, author="test")

        assert len(controller.get_versions()) == initial_versions + 1

    def test_version_contains_snapshot(self, controller):
        """Test version contains PRD snapshot"""
        controller.update_prd({"add_feature": {"id": "f1", "name": "Feature 1"}}, author="test")

        versions = controller.get_versions()
        assert len(versions) > 0

        version = versions[0]
        assert isinstance(version, PRDVersion)
        assert version.prd_snapshot is not None
        assert version.author == "test"

    def test_max_10_versions(self, controller):
        """Test only last 10 versions are kept"""
        # Make 15 updates
        for i in range(15):
            controller.update_prd(
                {"add_feature": {"id": f"f{i}", "name": f"Feature {i}"}}, author="test"
            )

        versions = controller.get_versions()
        assert len(versions) <= 10

    def test_rollback_to_version(self, controller):
        """Test rollback restores previous state"""
        # Add 3 features
        for i in range(3):
            controller.update_prd(
                {"add_feature": {"id": f"f{i}", "name": f"Feature {i}"}}, author="test"
            )

        assert len(controller.prd.features) == 3

        # Rollback to version 0 (after first feature)
        controller.rollback_to_version(0)

        assert len(controller.prd.features) == 1

    def test_rollback_emits_event(self, controller):
        """Test rollback emits event"""
        events = []

        def listener(event):
            events.append(event)

        controller.subscribe(listener)

        controller.update_prd({"add_feature": {"id": "f1", "name": "Feature 1"}}, author="test")

        controller.rollback_to_version(0)

        # Should have 2 events: add and rollback
        assert len(events) == 2
        assert events[1].diff.get("rollback") is not None


class TestEventSystem:
    """Test event system"""

    @pytest.fixture
    def controller(self):
        """Create controller with temp spec"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"
        spec_path.write_text("# Test\n")

        controller = PRDController(spec_path)

        yield controller

        shutil.rmtree(temp_dir)

    def test_subscribe_listener(self, controller):
        """Test subscribing event listener"""
        events = []

        def listener(event):
            events.append(event)

        controller.subscribe(listener)

        controller.update_prd({"add_feature": {"id": "f1", "name": "Feature 1"}}, author="test")

        assert len(events) == 1
        assert isinstance(events[0], PRDChangeEvent)

    def test_multiple_listeners(self, controller):
        """Test multiple listeners receive events"""
        events1 = []
        events2 = []

        def listener1(event):
            events1.append(event)

        def listener2(event):
            events2.append(event)

        controller.subscribe(listener1)
        controller.subscribe(listener2)

        controller.update_prd({"add_feature": {"id": "f1", "name": "Feature 1"}}, author="test")

        assert len(events1) == 1
        assert len(events2) == 1

    def test_unsubscribe_listener(self, controller):
        """Test unsubscribing stops receiving events"""
        events = []

        def listener(event):
            events.append(event)

        controller.subscribe(listener)
        controller.unsubscribe(listener)

        controller.update_prd({"add_feature": {"id": "f1", "name": "Feature 1"}}, author="test")

        assert len(events) == 0

    def test_listener_exception_doesnt_crash(self, controller):
        """Test listener exception doesn't crash system"""

        def bad_listener(event):
            raise Exception("Listener error")

        controller.subscribe(bad_listener)

        # Should not raise exception
        controller.update_prd({"add_feature": {"id": "f1", "name": "Feature 1"}}, author="test")

        # Controller should still work
        assert len(controller.prd.features) == 1


class TestNaturalLanguageParsing:
    """Test natural language parsing"""

    @pytest.fixture
    def controller(self):
        """Create controller with temp spec"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"
        spec_path.write_text("# Test\n")

        controller = PRDController(spec_path)

        yield controller

        shutil.rmtree(temp_dir)

    def test_parse_add_feature(self, controller):
        """Test parsing 'add feature X'"""
        updates = controller.parse_natural_language("add authentication feature")

        assert "add_feature" in updates
        assert updates["add_feature"]["name"] == "Authentication Feature"

    def test_parse_add_without_feature_word(self, controller):
        """Test parsing 'add X'"""
        updates = controller.parse_natural_language("add user login")

        assert "add_feature" in updates
        assert "user login" in updates["add_feature"]["name"].lower()

    def test_parse_remove_feature(self, controller):
        """Test parsing 'remove feature X'"""
        # Add a feature first
        controller.update_prd(
            {"add_feature": {"id": "auth", "name": "Authentication"}}, author="test"
        )

        updates = controller.parse_natural_language("remove auth")

        assert "remove_feature" in updates
        assert updates["remove_feature"] == "auth"

    def test_parse_invalid_input(self, controller):
        """Test parsing invalid input returns empty"""
        updates = controller.parse_natural_language("asdfasdf")

        assert updates == {}

    def test_parse_empty_input(self, controller):
        """Test parsing empty input returns empty"""
        updates = controller.parse_natural_language("")

        assert updates == {}


class TestConcurrency:
    """Test concurrent access with file locking"""

    @pytest.fixture
    def controller(self):
        """Create controller with temp spec"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"
        spec_path.write_text("# Test\n")

        controller = PRDController(spec_path)

        yield controller

        shutil.rmtree(temp_dir)

    def test_concurrent_updates_dont_corrupt(self, controller):
        """Test concurrent updates don't corrupt PRD"""
        errors = []

        def update_worker(i):
            try:
                controller.update_prd(
                    {"add_feature": {"id": f"concurrent-{i}", "name": f"Concurrent Feature {i}"}},
                    author=f"worker-{i}",
                )
            except Exception as e:
                errors.append(e)

        threads = [threading.Thread(target=update_worker, args=(i,)) for i in range(5)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # No errors should occur
        assert len(errors) == 0

        # All 5 features should be added
        assert len(controller.prd.features) == 5

    def test_file_locking_prevents_corruption(self, controller):
        """Test file lock prevents simultaneous writes"""
        # This test verifies that filelock is being used correctly
        # by checking that concurrent updates complete successfully

        def rapid_update(i):
            for j in range(3):
                controller.update_prd({"project_name": f"Update {i}-{j}"}, author="test")

        threads = [threading.Thread(target=rapid_update, args=(i,)) for i in range(3)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        # Should complete without errors
        # Last update should be visible
        assert "Update" in controller.prd.project_name


class TestSingleton:
    """Test singleton pattern"""

    def test_get_prd_controller_returns_singleton(self):
        """Test get_prd_controller returns same instance"""
        temp_dir = Path(tempfile.mkdtemp())
        spec_path = temp_dir / "PROJECT_SPEC.md"
        spec_path.write_text("# Test\n")

        try:
            # Reset singleton
            from core import prd_controller

            prd_controller._controller = None

            controller1 = get_prd_controller(spec_path)
            controller2 = get_prd_controller(spec_path)

            assert controller1 is controller2

        finally:
            shutil.rmtree(temp_dir)


def run_unit_tests():
    """Run all unit tests"""
    pytest.main([__file__, "-v", "--tb=short"])


if __name__ == "__main__":
    run_unit_tests()
