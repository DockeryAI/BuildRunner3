"""
Tests for core.governance_enforcer module

Tests GovernanceEnforcer functionality including state transitions,
dependency validation, commit validation, and enforcement policies.
"""

import json
import pytest
import yaml
from pathlib import Path

from core.governance import GovernanceManager
from core.governance_enforcer import (
    GovernanceEnforcer,
    EnforcementError,
    get_enforcer,
)


class TestGovernanceEnforcer:
    """Test suite for GovernanceEnforcer class."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create a temporary project directory structure."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()

        governance_dir = project_dir / ".buildrunner" / "governance"
        governance_dir.mkdir(parents=True)

        features_dir = project_dir / ".buildrunner"
        features_dir.mkdir(exist_ok=True)

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
                    'allowed_states': ['planned', 'in_progress', 'testing', 'complete', 'blocked'],
                    'transitions': {
                        'planned': ['in_progress', 'blocked'],
                        'in_progress': ['testing', 'blocked', 'planned'],
                        'testing': ['complete', 'in_progress', 'blocked'],
                        'blocked': ['planned', 'in_progress'],
                        'complete': [],
                    },
                    'branch_patterns': {
                        'feature': 'build/week{week_number}-{feature_name}',
                        'hotfix': 'hotfix/{feature_id}-{description}',
                    },
                    'commit_rules': {
                        'require_semantic_versioning': True,
                        'allowed_types': ['feat', 'fix', 'refactor', 'test', 'docs', 'chore'],
                    }
                }
            },
            'validation': {
                'required_checks': ['tests_pass', 'lint_pass'],
                'coverage_threshold': 90,
                'pre_commit': ['validate_features_json', 'check_governance_checksum'],
                'pre_push': ['run_tests', 'validate_governance_rules'],
            },
            'enforcement': {
                'policy': 'strict',
                'on_violation': {
                    'pre_commit': 'block',
                    'pre_push': 'block',
                    'dependency': 'block',
                    'coverage': 'warn',
                }
            },
            'dependencies': {
                'feature-a': [],
                'feature-b': ['feature-a'],
                'feature-c': ['feature-a', 'feature-b'],
            }
        }

    @pytest.fixture
    def enforcer_with_config(self, temp_project, sample_governance_config):
        """Create a GovernanceEnforcer with loaded config."""
        config_file = temp_project / ".buildrunner" / "governance" / "governance.yaml"

        with open(config_file, 'w') as f:
            yaml.dump(sample_governance_config, f)

        gm = GovernanceManager(temp_project)
        gm.load(verify_checksum=False)

        enforcer = GovernanceEnforcer(gm)
        return enforcer

    def test_init(self, temp_project, sample_governance_config):
        """Test enforcer initialization."""
        gm = GovernanceManager(temp_project)
        gm.config = sample_governance_config
        gm._loaded = True

        enforcer = GovernanceEnforcer(gm)

        assert enforcer.governance == gm
        assert enforcer.project_root == temp_project

    def test_validate_state_transition_valid(self, enforcer_with_config):
        """Test valid state transition."""
        is_valid, error = enforcer_with_config.validate_state_transition(
            'feature-a', 'planned', 'in_progress'
        )

        assert is_valid is True
        assert error is None

    def test_validate_state_transition_invalid(self, enforcer_with_config):
        """Test invalid state transition."""
        is_valid, error = enforcer_with_config.validate_state_transition(
            'feature-a', 'planned', 'complete'
        )

        assert is_valid is False
        assert 'Invalid transition' in error

    def test_validate_state_transition_from_complete(self, enforcer_with_config):
        """Test transition from complete state (terminal)."""
        is_valid, error = enforcer_with_config.validate_state_transition(
            'feature-a', 'complete', 'in_progress'
        )

        assert is_valid is False
        assert 'none' in error  # No allowed transitions

    def test_validate_state_transition_invalid_state(self, enforcer_with_config):
        """Test transition with invalid state."""
        is_valid, error = enforcer_with_config.validate_state_transition(
            'feature-a', 'invalid_state', 'in_progress'
        )

        assert is_valid is False
        assert 'Invalid state' in error

    def test_validate_feature_dependencies_no_deps(self, enforcer_with_config):
        """Test feature with no dependencies."""
        features_json = {
            'features': []
        }

        is_valid, missing = enforcer_with_config.validate_feature_dependencies(
            'feature-a', features_json
        )

        assert is_valid is True
        assert missing == []

    def test_validate_feature_dependencies_met(self, enforcer_with_config):
        """Test feature dependencies are met."""
        features_json = {
            'features': [
                {'id': 'feature-a', 'status': 'complete'},
            ]
        }

        is_valid, missing = enforcer_with_config.validate_feature_dependencies(
            'feature-b', features_json
        )

        assert is_valid is True
        assert missing == []

    def test_validate_feature_dependencies_not_met(self, enforcer_with_config):
        """Test feature dependencies are not met."""
        features_json = {
            'features': [
                {'id': 'feature-a', 'status': 'in_progress'},  # Not complete
            ]
        }

        is_valid, missing = enforcer_with_config.validate_feature_dependencies(
            'feature-b', features_json
        )

        assert is_valid is False
        assert 'feature-a' in missing

    def test_validate_feature_dependencies_partially_met(self, enforcer_with_config):
        """Test feature with multiple dependencies partially met."""
        features_json = {
            'features': [
                {'id': 'feature-a', 'status': 'complete'},
                {'id': 'feature-b', 'status': 'in_progress'},  # Not complete
            ]
        }

        is_valid, missing = enforcer_with_config.validate_feature_dependencies(
            'feature-c', features_json
        )

        assert is_valid is False
        assert 'feature-b' in missing
        assert 'feature-a' not in missing

    def test_validate_commit_message_valid(self, enforcer_with_config):
        """Test valid semantic versioning commit message."""
        messages = [
            'feat: Add new governance feature',
            'fix: Correct checksum validation',
            'refactor: Simplify state transition logic',
            'test: Add comprehensive tests',
            'docs: Update API documentation',
            'chore: Update dependencies',
            'feat(core): Add governance enforcer',
        ]

        for message in messages:
            is_valid, error = enforcer_with_config.validate_commit_message(message)
            assert is_valid is True, f"Failed for: {message}"
            assert error is None

    def test_validate_commit_message_invalid_format(self, enforcer_with_config):
        """Test invalid commit message format."""
        is_valid, error = enforcer_with_config.validate_commit_message(
            'Added some stuff'
        )

        assert is_valid is False
        assert 'semantic versioning format' in error

    def test_validate_commit_message_invalid_type(self, enforcer_with_config):
        """Test invalid commit type."""
        is_valid, error = enforcer_with_config.validate_commit_message(
            'invalid: This should fail'
        )

        assert is_valid is False
        assert 'Invalid commit type' in error

    def test_validate_commit_message_no_requirement(self, temp_project):
        """Test commit validation when not required."""
        config = {
            'project': {'name': 'Test'},
            'workflow': {
                'rules': {
                    'commit_rules': {'require_semantic_versioning': False}
                }
            },
            'validation': {'required_checks': []},
        }

        gm = GovernanceManager(temp_project)
        gm.config = config
        gm._loaded = True

        enforcer = GovernanceEnforcer(gm)

        is_valid, error = enforcer.validate_commit_message('Any message works')

        assert is_valid is True
        assert error is None

    def test_validate_branch_name_valid(self, enforcer_with_config):
        """Test valid branch names."""
        valid_branches = [
            'build/week1-governance',
            'build/week2-feature-registry',
            'hotfix/auth-token-expiry',
            'hotfix/fix-validation-bug',
        ]

        for branch in valid_branches:
            is_valid, error = enforcer_with_config.validate_branch_name(branch)
            assert is_valid is True, f"Failed for: {branch}"
            assert error is None

    def test_validate_branch_name_invalid(self, enforcer_with_config):
        """Test invalid branch name."""
        is_valid, error = enforcer_with_config.validate_branch_name(
            'random-branch-name'
        )

        assert is_valid is False
        assert "doesn't match any allowed patterns" in error

    def test_check_pre_commit_pass(self, enforcer_with_config, temp_project):
        """Test pre-commit checks pass."""
        # Create valid features.json
        features_file = temp_project / ".buildrunner" / "features.json"
        features_data = {
            'project': 'Test',
            'features': []
        }

        with open(features_file, 'w') as f:
            json.dump(features_data, f)

        # Generate checksum
        enforcer_with_config.governance.generate_checksum()

        passed, failed = enforcer_with_config.check_pre_commit()

        assert passed is True
        assert failed == []

    def test_check_pre_commit_fail_no_features_json(self, enforcer_with_config, temp_project):
        """Test pre-commit fails when features.json is missing."""
        passed, failed = enforcer_with_config.check_pre_commit()

        assert passed is False
        assert 'validate_features_json' in failed

    def test_check_pre_commit_fail_checksum_mismatch(self, enforcer_with_config, temp_project):
        """Test pre-commit fails when checksum doesn't match."""
        # Create valid features.json
        features_file = temp_project / ".buildrunner" / "features.json"
        features_data = {'project': 'Test', 'features': []}

        with open(features_file, 'w') as f:
            json.dump(features_data, f)

        # Generate checksum then modify file
        enforcer_with_config.governance.generate_checksum()

        with open(enforcer_with_config.governance.config_file, 'a') as f:
            f.write("\n# Modified\n")

        passed, failed = enforcer_with_config.check_pre_commit()

        assert passed is False
        assert 'check_governance_checksum' in failed

    def test_check_pre_push(self, enforcer_with_config):
        """Test pre-push checks."""
        passed, failed = enforcer_with_config.check_pre_push()

        # Should pass validation check (no actual test/coverage checks implemented)
        assert passed is True

    def test_enforce_pre_commit_strict_block(self, enforcer_with_config):
        """Test enforce blocks on pre-commit failure in strict mode."""
        # No features.json, so pre-commit will fail

        with pytest.raises(EnforcementError, match="Pre-commit checks failed"):
            enforcer_with_config.enforce('pre_commit')

    def test_enforce_state_transition_valid(self, enforcer_with_config):
        """Test enforce allows valid state transition."""
        context = {
            'feature_id': 'feature-a',
            'from_state': 'planned',
            'to_state': 'in_progress',
        }

        # Should not raise
        enforcer_with_config.enforce('state_transition', context)

    def test_enforce_state_transition_invalid(self, enforcer_with_config):
        """Test enforce blocks invalid state transition."""
        context = {
            'feature_id': 'feature-a',
            'from_state': 'planned',
            'to_state': 'complete',
        }

        with pytest.raises(EnforcementError, match="Invalid transition"):
            enforcer_with_config.enforce('state_transition', context)

    def test_enforce_dependency_met(self, enforcer_with_config):
        """Test enforce allows feature when dependencies are met."""
        context = {
            'feature_id': 'feature-b',
            'features_json': {
                'features': [
                    {'id': 'feature-a', 'status': 'complete'}
                ]
            }
        }

        # Should not raise
        enforcer_with_config.enforce('dependency', context)

    def test_enforce_dependency_not_met(self, enforcer_with_config):
        """Test enforce blocks feature when dependencies not met."""
        context = {
            'feature_id': 'feature-b',
            'features_json': {
                'features': [
                    {'id': 'feature-a', 'status': 'in_progress'}
                ]
            }
        }

        with pytest.raises(EnforcementError, match="Unmet dependencies"):
            enforcer_with_config.enforce('dependency', context)

    def test_enforce_warn_mode(self, enforcer_with_config, capsys):
        """Test enforce warns instead of blocking in warn mode."""
        # Change enforcement to warn
        enforcer_with_config.governance.config['enforcement']['on_violation']['state_transition'] = 'warn'

        context = {
            'feature_id': 'feature-a',
            'from_state': 'planned',
            'to_state': 'complete',
        }

        # Should not raise, but should print warning
        enforcer_with_config.enforce('state_transition', context)

        captured = capsys.readouterr()
        assert '⚠️' in captured.out
        assert 'WARNING' in captured.out

    def test_enforce_ignore_mode(self, enforcer_with_config):
        """Test enforce ignores violations in ignore mode."""
        # Change enforcement to ignore
        enforcer_with_config.governance.config['enforcement']['on_violation']['state_transition'] = 'ignore'

        context = {
            'feature_id': 'feature-a',
            'from_state': 'planned',
            'to_state': 'complete',
        }

        # Should not raise or warn
        enforcer_with_config.enforce('state_transition', context)

    def test_validate_features_json_valid(self, enforcer_with_config, temp_project):
        """Test _validate_features_json with valid file."""
        features_file = temp_project / ".buildrunner" / "features.json"
        features_data = {
            'project': 'Test',
            'features': []
        }

        with open(features_file, 'w') as f:
            json.dump(features_data, f)

        assert enforcer_with_config._validate_features_json() is True

    def test_validate_features_json_missing(self, enforcer_with_config):
        """Test _validate_features_json with missing file."""
        assert enforcer_with_config._validate_features_json() is False

    def test_validate_features_json_invalid_json(self, enforcer_with_config, temp_project):
        """Test _validate_features_json with invalid JSON."""
        features_file = temp_project / ".buildrunner" / "features.json"

        with open(features_file, 'w') as f:
            f.write("{invalid json")

        assert enforcer_with_config._validate_features_json() is False

    def test_validate_features_json_invalid_structure(self, enforcer_with_config, temp_project):
        """Test _validate_features_json with invalid structure."""
        features_file = temp_project / ".buildrunner" / "features.json"

        # Valid JSON but wrong structure (missing 'features' key)
        with open(features_file, 'w') as f:
            json.dump({'project': 'Test'}, f)

        assert enforcer_with_config._validate_features_json() is False

    def test_get_enforcement_report(self, enforcer_with_config, temp_project):
        """Test generating enforcement report."""
        # Create features.json for clean report
        features_file = temp_project / ".buildrunner" / "features.json"
        with open(features_file, 'w') as f:
            json.dump({'project': 'Test', 'features': []}, f)

        enforcer_with_config.governance.generate_checksum()

        report = enforcer_with_config.get_enforcement_report()

        assert report['policy'] == 'strict'
        assert report['strict_mode'] is True
        assert report['checksum_valid'] is True
        assert 'pre_commit' in report
        assert 'pre_push' in report
        assert report['pre_commit']['passed'] is True


class TestFactoryFunction:
    """Test the get_enforcer factory function."""

    def test_get_enforcer(self, tmp_path):
        """Test factory function creates enforcer."""
        # Create minimal governance config
        config_file = tmp_path / ".buildrunner" / "governance" / "governance.yaml"
        config_file.parent.mkdir(parents=True)

        config = {
            'project': {'name': 'Test'},
            'workflow': {'rules': {}},
            'validation': {'required_checks': []},
        }

        with open(config_file, 'w') as f:
            yaml.dump(config, f)

        enforcer = get_enforcer(tmp_path)

        assert isinstance(enforcer, GovernanceEnforcer)
        assert enforcer.project_root == tmp_path
        assert enforcer.governance._loaded is True
