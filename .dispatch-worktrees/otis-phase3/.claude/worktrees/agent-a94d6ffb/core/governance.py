"""
Governance Manager for BuildRunner 3.0

Handles loading, validation, and enforcement of governance rules defined in YAML.
Includes checksum verification to prevent unauthorized tampering.
"""

import hashlib
import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Set
import yaml


class GovernanceError(Exception):
    """Base exception for governance-related errors."""

    pass


class GovernanceValidationError(GovernanceError):
    """Raised when governance configuration validation fails."""

    pass


class GovernanceChecksumError(GovernanceError):
    """Raised when governance checksum verification fails."""

    pass


class GovernanceManager:
    """
    Manages governance rules for BuildRunner projects.

    Responsibilities:
    - Load and validate governance.yaml configuration
    - Verify checksums to prevent tampering
    - Provide rule query interface
    - Enforce workflow constraints
    """

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize GovernanceManager.

        Args:
            project_root: Root directory of the project. Defaults to current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.governance_dir = self.project_root / ".buildrunner" / "governance"
        self.config_file = self.governance_dir / "governance.yaml"
        self.checksum_file = self.governance_dir / ".governance.sha256"

        self.config: Dict[str, Any] = {}
        self._loaded = False

    def load(self, verify_checksum: bool = True) -> Dict[str, Any]:
        """
        Load governance configuration from YAML.

        Args:
            verify_checksum: Whether to verify the checksum before loading.

        Returns:
            The loaded governance configuration dictionary.

        Raises:
            GovernanceError: If file doesn't exist or can't be loaded.
            GovernanceChecksumError: If checksum verification fails.
            GovernanceValidationError: If configuration is invalid.
        """
        if not self.config_file.exists():
            raise GovernanceError(
                f"Governance config not found: {self.config_file}. "
                f"Run 'br init' to initialize governance."
            )

        # Verify checksum before loading
        if verify_checksum and self.checksum_file.exists():
            if not self.verify_checksum():
                raise GovernanceChecksumError(
                    "Governance configuration checksum mismatch! "
                    "File may have been tampered with. "
                    "Use 'br governance reset' if this is intentional."
                )

        # Load YAML
        try:
            with open(self.config_file, "r") as f:
                self.config = yaml.safe_load(f)
        except yaml.YAMLError as e:
            raise GovernanceError(f"Failed to parse governance.yaml: {e}")

        # Validate configuration structure
        self.validate()

        self._loaded = True
        return self.config

    def validate(self) -> None:
        """
        Validate the governance configuration structure.

        Raises:
            GovernanceValidationError: If configuration is invalid.
        """
        if not isinstance(self.config, dict):
            raise GovernanceValidationError("Governance config must be a dictionary")

        required_sections = ["project", "workflow", "validation"]
        for section in required_sections:
            if section not in self.config:
                raise GovernanceValidationError(f"Missing required section: {section}")

        # Validate project section
        project = self.config.get("project", {})
        if "name" not in project:
            raise GovernanceValidationError("project.name is required")

        # Validate workflow section
        workflow = self.config.get("workflow", {})
        if "rules" not in workflow:
            raise GovernanceValidationError("workflow.rules is required")

        # Validate validation section
        validation = self.config.get("validation", {})
        if "required_checks" not in validation:
            raise GovernanceValidationError("validation.required_checks is required")

    def save(self, update_checksum: bool = True) -> None:
        """
        Save the current governance configuration to YAML.

        Args:
            update_checksum: Whether to update the checksum after saving.

        Raises:
            GovernanceError: If save fails.
        """
        if not self.config:
            raise GovernanceError("No configuration to save")

        # Ensure directory exists
        self.governance_dir.mkdir(parents=True, exist_ok=True)

        # Write YAML with nice formatting
        try:
            with open(self.config_file, "w") as f:
                yaml.dump(self.config, f, default_flow_style=False, sort_keys=False, indent=2)
        except Exception as e:
            raise GovernanceError(f"Failed to save governance.yaml: {e}")

        # Update checksum
        if update_checksum:
            self.generate_checksum()

    def generate_checksum(self) -> str:
        """
        Generate and save SHA256 checksum of governance.yaml.

        Returns:
            The generated checksum hash string.

        Raises:
            GovernanceError: If checksum generation fails.
        """
        if not self.config_file.exists():
            raise GovernanceError("Cannot generate checksum: governance.yaml doesn't exist")

        # Calculate SHA256
        sha256_hash = hashlib.sha256()
        with open(self.config_file, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        checksum = sha256_hash.hexdigest()

        # Save checksum
        with open(self.checksum_file, "w") as f:
            f.write(f"{checksum}  {self.config_file.name}\n")

        return checksum

    def verify_checksum(self) -> bool:
        """
        Verify that governance.yaml matches its stored checksum.

        Returns:
            True if checksum matches, False otherwise.
        """
        if not self.checksum_file.exists():
            return True  # No checksum to verify against

        if not self.config_file.exists():
            return False

        # Read stored checksum
        with open(self.checksum_file, "r") as f:
            stored_checksum = f.read().strip().split()[0]

        # Calculate current checksum
        sha256_hash = hashlib.sha256()
        with open(self.config_file, "rb") as f:
            for byte_block in iter(lambda: f.read(4096), b""):
                sha256_hash.update(byte_block)

        current_checksum = sha256_hash.hexdigest()

        return current_checksum == stored_checksum

    def get_workflow_rules(self) -> Dict[str, Any]:
        """
        Get workflow rules from governance config.

        Returns:
            Dictionary of workflow rules.

        Raises:
            GovernanceError: If governance not loaded.
        """
        if not self._loaded:
            raise GovernanceError("Governance not loaded. Call load() first.")

        return self.config.get("workflow", {}).get("rules", {})

    def get_validation_rules(self) -> Dict[str, Any]:
        """
        Get validation rules from governance config.

        Returns:
            Dictionary of validation rules.

        Raises:
            GovernanceError: If governance not loaded.
        """
        if not self._loaded:
            raise GovernanceError("Governance not loaded. Call load() first.")

        return self.config.get("validation", {})

    def get_required_checks(self) -> List[str]:
        """
        Get list of required validation checks.

        Returns:
            List of required check names.

        Raises:
            GovernanceError: If governance not loaded.
        """
        validation = self.get_validation_rules()
        return validation.get("required_checks", [])

    def get_feature_dependencies(self, feature_id: str) -> List[str]:
        """
        Get dependencies for a specific feature.

        Args:
            feature_id: The feature ID to look up.

        Returns:
            List of feature IDs that must be completed first.

        Raises:
            GovernanceError: If governance not loaded.
        """
        if not self._loaded:
            raise GovernanceError("Governance not loaded. Call load() first.")

        dependencies = self.config.get("dependencies", {})
        return dependencies.get(feature_id, [])

    def check_feature_can_start(
        self, feature_id: str, completed_features: Set[str]
    ) -> tuple[bool, List[str]]:
        """
        Check if a feature can be started based on dependencies.

        Args:
            feature_id: The feature ID to check.
            completed_features: Set of already completed feature IDs.

        Returns:
            Tuple of (can_start: bool, missing_dependencies: List[str])

        Raises:
            GovernanceError: If governance not loaded.
        """
        required_deps = self.get_feature_dependencies(feature_id)
        missing = [dep for dep in required_deps if dep not in completed_features]

        return (len(missing) == 0, missing)

    def get_enforcement_policy(self) -> str:
        """
        Get the enforcement policy level.

        Returns:
            Policy level: 'strict', 'warn', or 'off'

        Raises:
            GovernanceError: If governance not loaded.
        """
        if not self._loaded:
            raise GovernanceError("Governance not loaded. Call load() first.")

        return self.config.get("enforcement", {}).get("policy", "strict")

    def is_strict_mode(self) -> bool:
        """
        Check if strict enforcement is enabled.

        Returns:
            True if strict mode is enabled.
        """
        return self.get_enforcement_policy() == "strict"


# Factory function for easy instantiation
def get_governance_manager(project_root: Optional[Path] = None) -> GovernanceManager:
    """
    Factory function to create and load a GovernanceManager.

    Args:
        project_root: Root directory of the project.

    Returns:
        Loaded GovernanceManager instance.
    """
    manager = GovernanceManager(project_root)
    if manager.config_file.exists():
        manager.load()
    return manager
