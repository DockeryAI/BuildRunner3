"""
Tests for BuildRunner 2.0 → 3.0 migration system

Tests cover:
- V2 project parsing
- Format conversion
- Pre/post migration validation
- Git operations
- Edge cases and error handling
"""

import pytest
import json
import tempfile
import shutil
from pathlib import Path
from datetime import datetime

from core.migration.v2_parser import V2ProjectParser, V2Project
from core.migration.converter import MigrationConverter
from core.migration.validators import MigrationValidator
from core.migration.git_handler import GitMigrationHandler


@pytest.fixture
def temp_v2_project():
    """Create temporary v2.0 project structure for testing"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        runner_dir = project_root / ".runner"
        runner_dir.mkdir()

        # Create minimal HRPO file
        hrpo = {
            "executive_summary": "Test Project",
            "value_proposition": "Testing migration",
            "intended_audience": ["Developers"],
            "features": ["Feature 1", "Feature 2", {"name": "Feature 3", "status": "done"}],
            "build_plan": {
                "phases": [
                    {
                        "name": "Phase 1",
                        "steps": [
                            {"id": 1, "name": "Step 1", "done": True},
                            {"id": 2, "name": "Step 2", "done": False},
                        ],
                    }
                ]
            },
            "progress": {"steps_completed": 1, "total_steps": 2, "percent_complete": 50.0},
        }

        with open(runner_dir / "hrpo.json", "w") as f:
            json.dump(hrpo, f)

        # Create governance file
        governance = {
            "project": {"name": "Test Project", "slug": "test-project"},
            "policies": {"stage_framework": True, "auto_completion_stamp": True},
            "versioning": {"semver": {"enabled": True, "rules": {"breaking_change": "MAJOR"}}},
        }

        with open(runner_dir / "governance.json", "w") as f:
            json.dump(governance, f)

        yield project_root


@pytest.fixture
def temp_v2_project_with_git(temp_v2_project):
    """Create v2.0 project with git repository"""
    import subprocess

    # Initialize git repo
    subprocess.run(["git", "init"], cwd=temp_v2_project, check=True, capture_output=True)
    subprocess.run(
        ["git", "config", "user.name", "Test User"],
        cwd=temp_v2_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(
        ["git", "config", "user.email", "test@example.com"],
        cwd=temp_v2_project,
        check=True,
        capture_output=True,
    )
    subprocess.run(["git", "add", "."], cwd=temp_v2_project, check=True, capture_output=True)
    subprocess.run(
        ["git", "commit", "-m", "Initial commit"],
        cwd=temp_v2_project,
        check=True,
        capture_output=True,
    )

    yield temp_v2_project


class TestV2ProjectParser:
    """Test V2 project parsing"""

    def test_parse_valid_project(self, temp_v2_project):
        """Test parsing valid v2.0 project"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        assert project.is_valid
        assert project.has_runner_dir
        assert project.has_hrpo
        assert project.has_governance
        assert len(project.features) > 0

    def test_parse_hrpo_data(self, temp_v2_project):
        """Test HRPO data extraction"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        assert project.hrpo_data["executive_summary"] == "Test Project"
        assert "features" in project.hrpo_data
        assert "build_plan" in project.hrpo_data

    def test_parse_governance_data(self, temp_v2_project):
        """Test governance config extraction"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        assert project.governance_config["project"]["name"] == "Test Project"
        assert project.governance_config["policies"]["stage_framework"] is True

    def test_extract_features_from_hrpo(self, temp_v2_project):
        """Test feature extraction from HRPO"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        # Should extract from features list + build plan steps
        assert len(project.features) >= 3  # At least 3 from features list

        # Check feature structure
        for feature in project.features:
            assert "name" in feature
            assert "status" in feature

    def test_parse_missing_runner_dir(self):
        """Test parsing project without .runner directory"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parser = V2ProjectParser(Path(tmpdir))
            project = parser.parse()

            assert not project.is_valid
            assert not project.has_runner_dir
            assert len(project.errors) > 0

    def test_parse_corrupt_hrpo(self, temp_v2_project):
        """Test parsing project with corrupt HRPO file"""
        # Corrupt the HRPO file
        hrpo_file = temp_v2_project / ".runner" / "hrpo.json"
        with open(hrpo_file, "w") as f:
            f.write("{ invalid json }")

        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        assert not project.has_hrpo
        assert len(project.errors) > 0

    def test_metadata_extraction(self, temp_v2_project):
        """Test metadata extraction"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        assert project.metadata["name"] == "Test Project"
        assert project.metadata["percent_complete"] == 50.0
        assert project.metadata["detected_version"] == "2.0"


class TestMigrationConverter:
    """Test format conversion"""

    def test_convert_hrpo_to_features(self, temp_v2_project):
        """Test HRPO to features.json conversion"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        result = converter.convert()

        assert result.success
        assert "features" in result.features_json
        assert len(result.features_json["features"]) > 0

    def test_features_json_structure(self, temp_v2_project):
        """Test features.json has correct structure"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        result = converter.convert()

        features_json = result.features_json

        # Check required fields
        assert "project" in features_json
        assert "features" in features_json
        assert features_json["project"]["migrated_from_v2"] is True

        # Check feature structure
        for feature in features_json["features"]:
            assert "id" in feature
            assert "name" in feature
            assert "status" in feature

    def test_convert_governance_config(self, temp_v2_project):
        """Test governance config conversion"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        result = converter.convert()

        governance = result.governance_yaml

        assert "project" in governance
        assert "policies" in governance
        assert governance["migration"]["migrated_from_v2"] is True

    def test_preserve_project_name(self, temp_v2_project):
        """Test project name preservation"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        result = converter.convert()

        assert result.features_json["project"]["name"] == "Test Project"
        assert result.governance_yaml["project"]["name"] == "Test Project"

    def test_feature_count_preservation(self, temp_v2_project):
        """Test all features are migrated"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        original_count = len(project.features)

        converter = MigrationConverter(project)
        result = converter.convert()

        migrated_count = len(result.features_json["features"])

        # Should be at least the same, may be more if build plan extracted
        assert migrated_count >= original_count

    def test_conversion_metadata(self, temp_v2_project):
        """Test conversion metadata is added"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        result = converter.convert()

        assert "migration_date" in result.metadata
        assert result.metadata["source_version"] == "2.0"
        assert result.metadata["target_version"] == "3.0"


class TestMigrationValidator:
    """Test migration validation"""

    def test_pre_migration_validation_valid(self, temp_v2_project):
        """Test pre-migration validation on valid project"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        validator = MigrationValidator(temp_v2_project)
        result = validator.validate_pre_migration(project)

        assert result.passed

    def test_pre_migration_validation_invalid(self):
        """Test pre-migration validation on invalid project"""
        with tempfile.TemporaryDirectory() as tmpdir:
            parser = V2ProjectParser(Path(tmpdir))
            project = parser.parse()

            validator = MigrationValidator(Path(tmpdir))
            result = validator.validate_pre_migration(project)

            assert not result.passed
            assert len(result.errors) > 0

    def test_post_migration_validation(self, temp_v2_project):
        """Test post-migration validation"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        conversion = converter.convert()

        validator = MigrationValidator(temp_v2_project)
        result = validator.validate_post_migration(
            project, conversion.features_json, conversion.governance_yaml
        )

        assert result.passed

    def test_feature_count_validation(self, temp_v2_project):
        """Test feature count is validated"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        conversion = converter.convert()

        validator = MigrationValidator(temp_v2_project)
        result = validator.validate_post_migration(
            project, conversion.features_json, conversion.governance_yaml
        )

        # Should have warnings if counts differ
        if len(project.features) != len(conversion.features_json["features"]):
            assert len(result.warnings) > 0


class TestGitMigrationHandler:
    """Test git operations during migration"""

    def test_is_git_repository(self, temp_v2_project_with_git):
        """Test git repository detection"""
        handler = GitMigrationHandler(temp_v2_project_with_git)
        assert handler.is_git_repository()

    def test_is_not_git_repository(self, temp_v2_project):
        """Test non-git project detection"""
        handler = GitMigrationHandler(temp_v2_project)
        assert not handler.is_git_repository()

    def test_create_pre_migration_backup(self, temp_v2_project_with_git):
        """Test pre-migration backup creation"""
        handler = GitMigrationHandler(temp_v2_project_with_git)
        result = handler.create_pre_migration_backup()

        assert result.success
        assert result.tag_name is not None
        assert result.tag_name.startswith("pre-migration-v2.0-")
        assert result.backup_created

    def test_get_current_commit(self, temp_v2_project_with_git):
        """Test getting current commit hash"""
        handler = GitMigrationHandler(temp_v2_project_with_git)
        commit = handler.get_current_commit()

        assert commit is not None
        assert len(commit) > 0

    def test_preserve_history(self, temp_v2_project_with_git):
        """Test git history preservation"""
        handler = GitMigrationHandler(temp_v2_project_with_git)
        assert handler.preserve_history()


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_large_feature_list(self, temp_v2_project):
        """Test handling large number of features"""
        # Add many features to HRPO
        hrpo_file = temp_v2_project / ".runner" / "hrpo.json"
        with open(hrpo_file, "r") as f:
            hrpo = json.load(f)

        # Add 100 features
        hrpo["features"] = [f"Feature {i}" for i in range(100)]

        with open(hrpo_file, "w") as f:
            json.dump(hrpo, f)

        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        result = converter.convert()

        assert result.success
        assert len(result.features_json["features"]) >= 100

    def test_missing_hrpo_and_governance(self):
        """Test project with no HRPO or governance"""
        with tempfile.TemporaryDirectory() as tmpdir:
            project_root = Path(tmpdir)
            runner_dir = project_root / ".runner"
            runner_dir.mkdir()

            parser = V2ProjectParser(project_root)
            project = parser.parse()

            assert not project.is_valid

    def test_empty_features_list(self, temp_v2_project):
        """Test project with empty features list"""
        hrpo_file = temp_v2_project / ".runner" / "hrpo.json"
        with open(hrpo_file, "r") as f:
            hrpo = json.load(f)

        hrpo["features"] = []
        del hrpo["build_plan"]

        with open(hrpo_file, "w") as f:
            json.dump(hrpo, f)

        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        converter = MigrationConverter(project)
        result = converter.convert()

        # Should still succeed but have warnings
        assert result.success
        assert len(result.warnings) > 0


class TestIntegration:
    """Integration tests for full migration workflow"""

    def test_complete_migration_workflow(self, temp_v2_project_with_git):
        """Test complete migration from start to finish"""
        # Step 1: Parse
        parser = V2ProjectParser(temp_v2_project_with_git)
        project = parser.parse()
        assert project.is_valid

        # Step 2: Pre-validation
        validator = MigrationValidator(temp_v2_project_with_git)
        pre_validation = validator.validate_pre_migration(project)
        assert pre_validation.passed

        # Step 3: Backup
        git_handler = GitMigrationHandler(temp_v2_project_with_git)
        backup = git_handler.create_pre_migration_backup()
        assert backup.success

        # Step 4: Convert
        converter = MigrationConverter(project)
        conversion = converter.convert()
        assert conversion.success

        # Step 5: Post-validation
        post_validation = validator.validate_post_migration(
            project, conversion.features_json, conversion.governance_yaml
        )
        assert post_validation.passed

        # Step 6: Write files
        features_file = temp_v2_project_with_git / "features.json"
        with open(features_file, "w") as f:
            json.dump(conversion.features_json, f)

        assert features_file.exists()

    def test_migration_preserves_data(self, temp_v2_project):
        """Test no data loss during migration"""
        parser = V2ProjectParser(temp_v2_project)
        project = parser.parse()

        original_summary = project.hrpo_data.get("executive_summary")
        original_features = len(project.features)

        converter = MigrationConverter(project)
        result = converter.convert()

        # Check data preserved
        migrated_summary = result.features_json["project"].get("description")
        migrated_features = len(result.features_json["features"])

        assert original_summary in migrated_summary
        assert migrated_features >= original_features
