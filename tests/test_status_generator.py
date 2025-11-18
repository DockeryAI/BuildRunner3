"""Tests for STATUS.md Generator"""

import json
import pytest
import tempfile
import shutil
from pathlib import Path
from core.status_generator import StatusGenerator
from core.feature_registry import FeatureRegistry


@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def generator(temp_project):
    """Create StatusGenerator instance"""
    return StatusGenerator(temp_project)


@pytest.fixture
def registry(temp_project):
    """Create FeatureRegistry instance"""
    return FeatureRegistry(temp_project)


class TestStatusGenerator:
    """Test StatusGenerator class"""

    def test_generate_empty_status(self, generator):
        """Test generating status when features.json doesn't exist"""
        content = generator.generate()

        assert "No features.json found" in content

    def test_generate_with_features(self, generator, registry):
        """Test generating status with features"""
        # Add some features
        registry.add_feature("test1", "Test Feature 1", "Description 1", priority="high")
        registry.add_feature("test2", "Test Feature 2", "Description 2", priority="medium")
        registry.complete_feature("test1")

        content = generator.generate()

        # Check header
        assert "# BuildRunner Project - Status Report" in content
        assert "**Completion:** 50%" in content

        # Check metrics
        assert "✅ 1 features complete" in content
        assert "📋 1 features planned" in content

        # Check features
        assert "Test Feature 1" in content
        assert "Test Feature 2" in content

    def test_save_status(self, generator, registry):
        """Test saving STATUS.md file"""
        registry.add_feature("test", "Test", "Description")
        generator.save()

        assert generator.status_file.exists()

        with open(generator.status_file, 'r') as f:
            content = f.read()

        assert "Test" in content

    def test_format_feature_complete(self, generator, registry):
        """Test formatting complete feature"""
        registry.add_feature("test", "Complete Feature", "This is complete", week=1, build="1A")
        registry.complete_feature("test")

        content = generator.generate()

        assert "## ✅ Complete Features" in content
        assert "Complete Feature" in content
        assert "Week:** 1" in content
        assert "Build:** 1A" in content

    def test_format_feature_in_progress(self, generator, registry):
        """Test formatting in-progress feature"""
        registry.add_feature("test", "WIP Feature", "Work in progress")
        registry.update_feature("test", status="in_progress")

        content = generator.generate()

        assert "## 🚧 In Progress Features" in content
        assert "WIP Feature" in content

    def test_format_feature_planned(self, generator, registry):
        """Test formatting planned feature"""
        registry.add_feature("test", "Planned Feature", "Not started yet")

        content = generator.generate()

        assert "## 📋 Planned Features" in content
        assert "Planned Feature" in content

    def test_status_sections_order(self, generator, registry):
        """Test status sections appear in correct order"""
        registry.add_feature("complete", "Complete", "Done", priority="high")
        registry.add_feature("wip", "In Progress", "Working", priority="medium")
        registry.add_feature("planned", "Planned", "Not started", priority="low")

        registry.complete_feature("complete")
        registry.update_feature("wip", status="in_progress")

        content = generator.generate()

        # Find positions of each section
        complete_pos = content.find("## ✅ Complete Features")
        progress_pos = content.find("## 🚧 In Progress Features")
        planned_pos = content.find("## 📋 Planned Features")

        # Complete should come first
        assert complete_pos < progress_pos
        # In Progress should come before Planned
        assert progress_pos < planned_pos

    def test_generated_status_has_footer(self, generator, registry):
        """Test generated status includes footer"""
        registry.add_feature("test", "Test", "Description")
        content = generator.generate()

        assert "*Generated from `.buildrunner/features.json`" in content
        assert "*Generator: `core/status_generator.py`*" in content
