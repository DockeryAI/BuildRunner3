"""
Governance Enforcer for BuildRunner 3.0

Enforces governance rules, validates state transitions, checks dependencies,
and ensures compliance with workflow constraints.
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

from core.governance import GovernanceManager, GovernanceError


class EnforcementError(Exception):
    """Raised when governance enforcement fails."""

    pass


class GovernanceEnforcer:
    """
    Enforces governance rules defined in governance.yaml.

    Handles:
    - State transition validation
    - Feature dependency checking
    - Pre-commit validation
    - Workflow constraint enforcement
    """

    def __init__(self, governance_manager: GovernanceManager):
        """
        Initialize GovernanceEnforcer.

        Args:
            governance_manager: Loaded GovernanceManager instance.
        """
        self.governance = governance_manager
        self.project_root = governance_manager.project_root

    def validate_state_transition(
        self, feature_id: str, from_state: str, to_state: str
    ) -> Tuple[bool, Optional[str]]:
        """
        Validate that a state transition is allowed.

        Args:
            feature_id: ID of the feature being transitioned.
            from_state: Current state.
            to_state: Desired new state.

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        workflow_rules = self.governance.get_workflow_rules()
        transitions = workflow_rules.get("transitions", {})

        # Check if from_state is valid
        if from_state not in transitions:
            return (False, f"Invalid state: {from_state}")

        # Check if transition is allowed
        allowed_transitions = transitions.get(from_state, [])
        if to_state not in allowed_transitions:
            return (
                False,
                f"Invalid transition from '{from_state}' to '{to_state}'. "
                f"Allowed transitions: {', '.join(allowed_transitions) if allowed_transitions else 'none'}",
            )

        return (True, None)

    def validate_feature_dependencies(
        self, feature_id: str, features_json: Dict[str, Any]
    ) -> Tuple[bool, List[str]]:
        """
        Validate that all dependencies for a feature are satisfied.

        Args:
            feature_id: ID of the feature to validate.
            features_json: The entire features.json data.

        Returns:
            Tuple of (is_valid: bool, missing_dependencies: List[str])
        """
        # Get completed features
        completed_features = set()
        for feature in features_json.get("features", []):
            if feature.get("status") == "complete":
                completed_features.add(feature.get("id"))

        # Check dependencies
        can_start, missing = self.governance.check_feature_can_start(feature_id, completed_features)

        return (can_start, missing)

    def validate_commit_message(self, message: str) -> Tuple[bool, Optional[str]]:
        """
        Validate commit message against governance rules.

        Args:
            message: The commit message to validate.

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        workflow_rules = self.governance.get_workflow_rules()
        commit_rules = workflow_rules.get("commit_rules", {})

        require_semver = commit_rules.get("require_semantic_versioning", False)
        allowed_types = commit_rules.get("allowed_types", [])

        if not require_semver:
            return (True, None)  # No validation required

        # Parse commit message for semantic versioning
        # Format: <type>[(scope)]: <description>
        pattern = r"^(\w+)(?:\([^\)]+\))?: .+"
        match = re.match(pattern, message)

        if not match:
            return (
                False,
                f"Commit message must follow semantic versioning format: "
                f"<type>(scope): <description>",
            )

        commit_type = match.group(1)
        if allowed_types and commit_type not in allowed_types:
            return (
                False,
                f"Invalid commit type '{commit_type}'. "
                f"Allowed types: {', '.join(allowed_types)}",
            )

        return (True, None)

    def validate_branch_name(self, branch_name: str) -> Tuple[bool, Optional[str]]:
        """
        Validate branch name against governance rules.

        Args:
            branch_name: The branch name to validate.

        Returns:
            Tuple of (is_valid: bool, error_message: Optional[str])
        """
        workflow_rules = self.governance.get_workflow_rules()
        patterns = workflow_rules.get("branch_patterns", {})

        if not patterns:
            return (True, None)  # No patterns defined

        # Check if branch matches any allowed pattern
        # Convert patterns to regex (simple conversion)
        for branch_type, pattern_template in patterns.items():
            # Convert template to regex
            # Example: "build/week{week_number}-{feature_name}"
            # Becomes: "build/week\d+-[\w-]+"
            regex_pattern = pattern_template.replace("{week_number}", r"\d+")
            regex_pattern = regex_pattern.replace("{feature_name}", r"[\w-]+")
            regex_pattern = regex_pattern.replace("{feature_id}", r"[\w-]+")
            regex_pattern = regex_pattern.replace("{description}", r"[\w-]+")

            if re.match(f"^{regex_pattern}$", branch_name):
                return (True, None)

        return (
            False,
            f"Branch name '{branch_name}' doesn't match any allowed patterns. "
            f"Allowed patterns: {', '.join(patterns.values())}",
        )

    def check_pre_commit(self) -> Tuple[bool, List[str]]:
        """
        Run all pre-commit checks.

        Returns:
            Tuple of (all_passed: bool, failed_checks: List[str])
        """
        validation_rules = self.governance.get_validation_rules()
        pre_commit_checks = validation_rules.get("pre_commit", [])

        failed_checks = []

        for check in pre_commit_checks:
            if check == "validate_features_json":
                if not self._validate_features_json():
                    failed_checks.append("validate_features_json")

            elif check == "check_governance_checksum":
                if not self.governance.verify_checksum():
                    failed_checks.append("check_governance_checksum")

            elif check == "run_lint":
                # Placeholder - would integrate with linting tools
                pass

            elif check == "check_no_debug_statements":
                # Placeholder - would scan for debug statements
                pass

        return (len(failed_checks) == 0, failed_checks)

    def check_pre_push(self) -> Tuple[bool, List[str]]:
        """
        Run all pre-push checks.

        Returns:
            Tuple of (all_passed: bool, failed_checks: List[str])
        """
        validation_rules = self.governance.get_validation_rules()
        pre_push_checks = validation_rules.get("pre_push", [])

        failed_checks = []

        for check in pre_push_checks:
            if check == "run_tests":
                # Placeholder - would run pytest
                pass

            elif check == "check_coverage":
                # Placeholder - would check coverage
                pass

            elif check == "validate_governance_rules":
                try:
                    self.governance.validate()
                except GovernanceError:
                    failed_checks.append("validate_governance_rules")

        return (len(failed_checks) == 0, failed_checks)

    def enforce(self, check_type: str, context: Optional[Dict[str, Any]] = None) -> None:
        """
        Enforce governance rules based on check type.

        Args:
            check_type: Type of check ('pre_commit', 'pre_push', 'state_transition', etc.)
            context: Additional context for the check.

        Raises:
            EnforcementError: If enforcement fails and policy is strict.
        """
        enforcement_config = self.governance.config.get("enforcement", {})
        policy = enforcement_config.get("policy", "strict")
        on_violation = enforcement_config.get("on_violation", {})

        violation_action = on_violation.get(check_type, "block")

        if check_type == "pre_commit":
            passed, failed = self.check_pre_commit()
            if not passed:
                message = f"Pre-commit checks failed: {', '.join(failed)}"
                self._handle_violation(message, violation_action)

        elif check_type == "pre_push":
            passed, failed = self.check_pre_push()
            if not passed:
                message = f"Pre-push checks failed: {', '.join(failed)}"
                self._handle_violation(message, violation_action)

        elif check_type == "state_transition" and context:
            feature_id = context.get("feature_id")
            from_state = context.get("from_state")
            to_state = context.get("to_state")

            valid, error = self.validate_state_transition(feature_id, from_state, to_state)
            if not valid:
                self._handle_violation(error, violation_action)

        elif check_type == "dependency" and context:
            feature_id = context.get("feature_id")
            features_json = context.get("features_json")

            valid, missing = self.validate_feature_dependencies(feature_id, features_json)
            if not valid:
                message = f"Unmet dependencies for {feature_id}: {', '.join(missing)}"
                self._handle_violation(message, violation_action)

    def _handle_violation(self, message: str, action: str) -> None:
        """
        Handle a governance violation based on action.

        Args:
            message: The violation message.
            action: Action to take ('block', 'warn', 'ignore').

        Raises:
            EnforcementError: If action is 'block'.
        """
        if action == "block":
            raise EnforcementError(f"Governance violation: {message}")
        elif action == "warn":
            print(f"⚠️  WARNING: {message}")
        # 'ignore' does nothing

    def _validate_features_json(self) -> bool:
        """
        Validate that features.json exists and is valid.

        Returns:
            True if valid, False otherwise.
        """
        features_file = self.project_root / ".buildrunner" / "features.json"

        if not features_file.exists():
            return False

        try:
            with open(features_file, "r") as f:
                data = json.load(f)

            # Basic validation
            if not isinstance(data, dict):
                return False

            if "features" not in data:
                return False

            return True

        except (json.JSONDecodeError, IOError):
            return False

    def get_enforcement_report(self) -> Dict[str, Any]:
        """
        Generate a report of current governance enforcement status.

        Returns:
            Dictionary containing enforcement status and statistics.
        """
        report = {
            "policy": self.governance.get_enforcement_policy(),
            "strict_mode": self.governance.is_strict_mode(),
            "governance_file": str(self.governance.config_file),
            "checksum_valid": self.governance.verify_checksum(),
            "hooks_enabled": self.governance.config.get("hooks", {}).get("enabled", False),
        }

        # Check pre-commit status
        pre_commit_passed, pre_commit_failed = self.check_pre_commit()
        report["pre_commit"] = {"passed": pre_commit_passed, "failed_checks": pre_commit_failed}

        # Check pre-push status
        pre_push_passed, pre_push_failed = self.check_pre_push()
        report["pre_push"] = {"passed": pre_push_passed, "failed_checks": pre_push_failed}

        return report


# Factory function
def get_enforcer(project_root: Optional[Path] = None) -> GovernanceEnforcer:
    """
    Factory function to create a GovernanceEnforcer.

    Args:
        project_root: Root directory of the project.

    Returns:
        GovernanceEnforcer instance.
    """
    from core.governance import get_governance_manager

    governance = get_governance_manager(project_root)
    return GovernanceEnforcer(governance)
