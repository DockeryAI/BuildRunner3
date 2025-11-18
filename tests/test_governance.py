"""
Tests for core.governance module

Tests GovernanceManager functionality including loading, validation,
checksum verification, and rule queries.
"""

import hashlib
import pytest
import yaml
from pathlib import Path

from core.governance import (
    GovernanceManager,
    GovernanceError,
    GovernanceValidationError,
    GovernanceChecksumError,
    get_governance_manager,
)


class TestGovernanceManager:
    """Test suite for GovernanceManager class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory structure."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        governance_dir = project_dir / ".buildrunner" / "governance"
        governance_dir.mkdir(parents=True)

        return project_dir

    @pytest.fixture
    def sample_governance_config(self):
        """Sample valid governance configuration."""
        return {
            'project': {
                'name': 'TestProject',
                'version': '1.0.0',
            },
            'workflow': {
                'rules': {
                    'allowed_states': ['planned', 'in_progress', 'complete'],
                    'transitions': {
                        'planned': ['in_progress'],
                        'in_progress': ['complete'],
                        'complete': [],
                    }
                }
            },
            'validation': {
                'required_checks': ['tests_pass', 'lint_pass'],
                'coverage_threshold': 90,
            },
            'enforcement': {
                'policy': 'strict',
            }
        }

    @pytest.fixture
    def governance_with_config(self, temp_project, sample_governance_config):
        """Create a GovernanceManager with a valid config file."""
        gm = GovernanceManager(temp_project)
        config_file = temp_project / ".buildrunner" / "governance" / "governance.yaml"

        with open(config_file, 'w') as f:
            yaml.dump(sample_governance_config, f)

        return gm

    def test_init_default_path(self):
        """Test initialization with default path (current directory)."""
        gm = GovernanceManager()
        assert gm.project_root == Path.cwd()
        assert not gm._loaded

    def test_init_custom_path(self, temp_project):
        """Test initialization with custom project path."""
        gm = GovernanceManager(temp_project)
        assert gm.project_root == temp_project
        assert gm.governance_dir == temp_project / ".buildrunner" / "governance"
        assert gm.config_file == temp_project / ".buildrunner" / "governance" / "governance.yaml"

    def test_load_missing_file(self, temp_project):
        """Test that loading raises error when file doesn't exist."""
        gm = GovernanceManager(temp_project)

        with pytest.raises(GovernanceError, match="Governance config not found"):
            gm.load()

    def test_load_success(self, governance_with_config, sample_governance_config):
        """Test successful loading of governance config."""
        config = governance_with_config.load(verify_checksum=False)

        assert config == sample_governance_config
        assert governance_with_config._loaded is True

    def test_load_invalid_yaml(self, temp_project):
        """Test loading with invalid YAML syntax."""
        gm = GovernanceManager(temp_project)
        config_file = gm.config_file
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Write invalid YAML
        with open(config_file, 'w') as f:
            f.write("invalid: yaml: syntax: [unclosed")

        with pytest.raises(GovernanceError, match="Failed to parse"):
            gm.load(verify_checksum=False)

    def test_validate_success(self, governance_with_config, sample_governance_config):
        """Test validation with valid configuration."""
        governance_with_config.config = sample_governance_config
        governance_with_config.validate()  # Should not raise

    def test_validate_missing_section(self, governance_with_config):
        """Test validation fails when required section is missing."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            # Missing 'workflow' and 'validation'
        }

        with pytest.raises(GovernanceValidationError, match="Missing required section"):
            governance_with_config.validate()

    def test_validate_missing_project_name(self, governance_with_config):
        """Test validation fails when project.name is missing."""
        governance_with_config.config = {
            'project': {},  # Missing 'name'
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
        }

        with pytest.raises(GovernanceValidationError, match="project.name is required"):
            governance_with_config.validate()

    def test_validate_missing_workflow_rules(self, governance_with_config):
        """Test validation fails when workflow.rules is missing."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            'workflow': {},  # Missing 'rules'
            'validation': {'required_checks': []},
        }

        with pytest.raises(GovernanceValidationError, match="workflow.rules is required"):
            governance_with_config.validate()

    def test_save_creates_file(self, temp_project, sample_governance_config):
        """Test that save creates governance.yaml file."""
        gm = GovernanceManager(temp_project)
        gm.config = sample_governance_config

        gm.save(update_checksum=False)

        assert gm.config_file.exists()

        # Verify content
        with open(gm.config_file, 'r') as f:
            saved_config = yaml.safe_load(f)

        assert saved_config == sample_governance_config

    def test_save_no_config(self, temp_project):
        """Test that save fails when no config is set."""
        gm = GovernanceManager(temp_project)

        with pytest.raises(GovernanceError, match="No configuration to save"):
            gm.save()

    def test_generate_checksum(self, governance_with_config):
        """Test checksum generation."""
        # Load config first
        governance_with_config.load(verify_checksum=False)

        checksum = governance_with_config.generate_checksum()

        # SHA256 hex digest is 64 characters
        assert len(checksum) == 64
        assert all(c in '0123456789abcdef' for c in checksum)

        # Verify checksum file was created
        assert governance_with_config.checksum_file.exists()

    def test_generate_checksum_no_file(self, temp_project):
        """Test checksum generation fails when governance.yaml doesn't exist."""
        gm = GovernanceManager(temp_project)

        with pytest.raises(GovernanceError, match="Cannot generate checksum"):
            gm.generate_checksum()

    def test_verify_checksum_no_checksum_file(self, governance_with_config):
        """Test verify_checksum returns True when no checksum file exists."""
        # Load to create governance.yaml
        governance_with_config.load(verify_checksum=False)

        # Verify without checksum file
        assert governance_with_config.verify_checksum() is True

    def test_verify_checksum_match(self, governance_with_config):
        """Test verify_checksum returns True when checksums match."""
        governance_with_config.load(verify_checksum=False)
        governance_with_config.generate_checksum()

        assert governance_with_config.verify_checksum() is True

    def test_verify_checksum_mismatch(self, governance_with_config):
        """Test verify_checksum returns False when file is modified."""
        governance_with_config.load(verify_checksum=False)
        governance_with_config.generate_checksum()

        # Modify the file
        with open(governance_with_config.config_file, 'a') as f:
            f.write("\n# Modified\n")

        assert governance_with_config.verify_checksum() is False

    def test_load_with_checksum_verification(self, governance_with_config):
        """Test load verifies checksum when checksum file exists."""
        governance_with_config.load(verify_checksum=False)
        governance_with_config.generate_checksum()

        # Modify the file
        with open(governance_with_config.config_file, 'a') as f:
            f.write("\n# Tampered\n")

        # Load should fail checksum verification
        with pytest.raises(GovernanceChecksumError, match="checksum mismatch"):
            governance_with_config.load(verify_checksum=True)

    def test_get_workflow_rules(self, governance_with_config):
        """Test retrieving workflow rules."""
        governance_with_config.load(verify_checksum=False)
        rules = governance_with_config.get_workflow_rules()

        assert 'allowed_states' in rules
        assert 'transitions' in rules

    def test_get_workflow_rules_not_loaded(self, temp_project):
        """Test get_workflow_rules fails when not loaded."""
        gm = GovernanceManager(temp_project)

        with pytest.raises(GovernanceError, match="Governance not loaded"):
            gm.get_workflow_rules()

    def test_get_validation_rules(self, governance_with_config):
        """Test retrieving validation rules."""
        governance_with_config.load(verify_checksum=False)
        validation = governance_with_config.get_validation_rules()

        assert 'required_checks' in validation
        assert validation['coverage_threshold'] == 90

    def test_get_required_checks(self, governance_with_config):
        """Test retrieving required checks list."""
        governance_with_config.load(verify_checksum=False)
        checks = governance_with_config.get_required_checks()

        assert 'tests_pass' in checks
        assert 'lint_pass' in checks

    def test_get_feature_dependencies(self, governance_with_config):
        """Test retrieving feature dependencies."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
            'dependencies': {
                'feature-a': [],
                'feature-b': ['feature-a'],
                'feature-c': ['feature-a', 'feature-b'],
            }
        }
        governance_with_config._loaded = True

        deps_a = governance_with_config.get_feature_dependencies('feature-a')
        deps_b = governance_with_config.get_feature_dependencies('feature-b')
        deps_c = governance_with_config.get_feature_dependencies('feature-c')

        assert deps_a == []
        assert deps_b == ['feature-a']
        assert deps_c == ['feature-a', 'feature-b']

    def test_get_feature_dependencies_missing(self, governance_with_config):
        """Test retrieving dependencies for non-existent feature."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
            'dependencies': {}
        }
        governance_with_config._loaded = True

        deps = governance_with_config.get_feature_dependencies('nonexistent')
        assert deps == []

    def test_check_feature_can_start_no_deps(self, governance_with_config):
        """Test checking if feature can start when it has no dependencies."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
            'dependencies': {'feature-a': []}
        }
        governance_with_config._loaded = True

        can_start, missing = governance_with_config.check_feature_can_start(
            'feature-a', set()
        )

        assert can_start is True
        assert missing == []

    def test_check_feature_can_start_deps_met(self, governance_with_config):
        """Test feature can start when dependencies are met."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
            'dependencies': {'feature-b': ['feature-a']}
        }
        governance_with_config._loaded = True

        can_start, missing = governance_with_config.check_feature_can_start(
            'feature-b', {'feature-a'}
        )

        assert can_start is True
        assert missing == []

    def test_check_feature_can_start_deps_not_met(self, governance_with_config):
        """Test feature cannot start when dependencies are not met."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
            'dependencies': {'feature-b': ['feature-a']}
        }
        governance_with_config._loaded = True

        can_start, missing = governance_with_config.check_feature_can_start(
            'feature-b', set()
        )

        assert can_start is False
        assert missing == ['feature-a']

    def test_get_enforcement_policy(self, governance_with_config):
        """Test retrieving enforcement policy."""
        governance_with_config.load(verify_checksum=False)
        policy = governance_with_config.get_enforcement_policy()

        assert policy == 'strict'

    def test_get_enforcement_policy_default(self, governance_with_config):
        """Test enforcement policy defaults to strict."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
            # No 'enforcement' section
        }
        governance_with_config._loaded = True

        policy = governance_with_config.get_enforcement_policy()
        assert policy == 'strict'

    def test_is_strict_mode(self, governance_with_config):
        """Test is_strict_mode returns correct boolean."""
        governance_with_config.load(verify_checksum=False)
        assert governance_with_config.is_strict_mode() is True

    def test_is_strict_mode_false(self, governance_with_config):
        """Test is_strict_mode returns False for non-strict policy."""
        governance_with_config.config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
            'enforcement': {'policy': 'warn'}
        }
        governance_with_config._loaded = True

        assert governance_with_config.is_strict_mode() is False


class TestFactoryFunction:
    """Test the get_governance_manager factory function."""

    def test_get_governance_manager(self, tmp_path):
        """Test factory function creates manager."""
        gm = get_governance_manager(tmp_path)

        assert isinstance(gm, GovernanceManager)
        assert gm.project_root == tmp_path

    def test_get_governance_manager_loads_existing(self, tmp_path):
        """Test factory function loads existing config."""
        # Create config
        config_file = tmp_path / ".buildrunner" / "governance" / "governance.yaml"
        config_file.parent.mkdir(parents=True)

        config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        # Factory should load it
        gm = get_governance_manager(tmp_path)

        assert gm._loaded is True
        assert gm.config['project']['name'] == 'Test'
