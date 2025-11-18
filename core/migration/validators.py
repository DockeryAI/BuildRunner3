"""
Migration Validators

Pre-migration and post-migration validation to ensure data integrity
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

from .v2_parser import V2Project


@dataclass
class ValidationResult:
    """Result of validation"""
    passed: bool
    warnings: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    suggestions: List[str] = field(default_factory=list)


class MigrationValidator:
    """
    Validate projects before and after migration

    Pre-migration:
    - Valid v2.0 structure
    - No corrupt data
    - Git repository status

    Post-migration:
    - Data integrity preserved
    - All features migrated
    - Valid v3.0 format
    """

    def __init__(self, source_path: Path, target_path: Optional[Path] = None):
        """
        Initialize validator

        Args:
            source_path: Path to source v2.0 project
            target_path: Path to target v3.0 project (for post-migration)
        """
        self.source_path = Path(source_path)
        self.target_path = Path(target_path) if target_path else None

    def validate_pre_migration(self, project: V2Project) -> ValidationResult:
        """
        Validate v2.0 project before migration

        Checks:
        - Valid project structure
        - No corrupt data files
        - Git repository clean
        - Sufficient data for migration

        Args:
            project: Parsed v2.0 project

        Returns:
            ValidationResult with findings
        """
        result = ValidationResult(passed=True)

        # Check if project is valid
        if not project.is_valid:
            result.errors.append("Project is not valid for migration")
            result.passed = False

        # Collect project errors
        for error in project.errors:
            result.errors.append(error)
            result.passed = False

        # Collect project warnings
        for warning in project.warnings:
            result.warnings.append(warning)

        # Check for minimum data
        if not project.has_hrpo and not project.has_governance:
            result.errors.append("No HRPO or governance data found - nothing to migrate")
            result.passed = False

        # Check git status
        if project.has_git:
            git_status = self._check_git_status()
            if git_status:
                result.warnings.append(f"Git repository has uncommitted changes: {git_status}")
                result.suggestions.append("Commit or stash changes before migration")

        # Check features
        if len(project.features) == 0:
            result.warnings.append("No features found in project")
            result.suggestions.append("Ensure HRPO or governance.json contains feature data")

        # Large project warning
        if len(project.features) > 1000:
            result.warnings.append(f"Large project with {len(project.features)} features - migration may take time")

        # Check for Supabase
        if project.supabase_config:
            result.warnings.append("Supabase configuration found - will be migrated")
            result.suggestions.append("Verify Supabase connection after migration")

        return result

    def validate_post_migration(
        self,
        original_project: V2Project,
        features_json: Dict[str, Any],
        governance_config: Dict[str, Any]
    ) -> ValidationResult:
        """
        Validate migration results

        Checks:
        - No data loss
        - All features migrated
        - Valid v3.0 format
        - Feature count matches

        Args:
            original_project: Original v2.0 project
            features_json: Converted features.json
            governance_config: Converted governance config

        Returns:
            ValidationResult with findings
        """
        result = ValidationResult(passed=True)

        # Validate features.json structure
        if not self._validate_features_json_structure(features_json):
            result.errors.append("Invalid features.json structure")
            result.passed = False

        # Validate governance config structure
        if not self._validate_governance_structure(governance_config):
            result.errors.append("Invalid governance config structure")
            result.passed = False

        # Check feature count
        original_count = len(original_project.features)
        migrated_count = len(features_json.get("features", []))

        if migrated_count < original_count:
            result.warnings.append(f"Feature count mismatch: {original_count} → {migrated_count}")
            result.suggestions.append("Review feature migration for missing items")
        elif migrated_count > original_count:
            result.warnings.append(f"More features after migration: {original_count} → {migrated_count}")
            result.suggestions.append("Additional features may have been extracted from build plan")

        # Check for essential project data
        project_info = features_json.get("project", {})
        if not project_info.get("name"):
            result.warnings.append("Project name not set")

        if not project_info.get("description"):
            result.warnings.append("Project description missing")

        # Validate each feature
        features = features_json.get("features", [])
        for idx, feature in enumerate(features):
            if not self._validate_feature(feature):
                result.errors.append(f"Invalid feature at index {idx}")
                result.passed = False

        return result

    def validate_rollback_safe(self, project: V2Project) -> ValidationResult:
        """
        Check if migration can be safely rolled back

        Args:
            project: Original project

        Returns:
            ValidationResult
        """
        result = ValidationResult(passed=True)

        # Git must exist for safe rollback
        if not project.has_git:
            result.warnings.append("No git repository - rollback will rely on backup only")
            result.suggestions.append("Consider initializing git before migration")
        else:
            # Check for uncommitted changes
            status = self._check_git_status()
            if status:
                result.warnings.append("Uncommitted changes exist")
                result.suggestions.append("Commit changes to enable clean rollback")

        # Check if backup directory exists
        backup_dir = project.root_path / ".buildrunner" / "backups"
        if not backup_dir.exists():
            result.warnings.append("No backup directory found")
            result.suggestions.append("Migration will create backup automatically")

        return result

    def _validate_features_json_structure(self, features_json: Dict[str, Any]) -> bool:
        """
        Validate features.json has required structure

        Args:
            features_json: Features data

        Returns:
            True if valid
        """
        # Must have project and features
        if "project" not in features_json:
            return False

        if "features" not in features_json:
            return False

        if not isinstance(features_json["features"], list):
            return False

        return True

    def _validate_governance_structure(self, governance: Dict[str, Any]) -> bool:
        """
        Validate governance config structure

        Args:
            governance: Governance config

        Returns:
            True if valid
        """
        # Must have project info
        if "project" not in governance:
            return False

        # Should have policies or quality
        if "policies" not in governance and "quality" not in governance:
            return False

        return True

    def _validate_feature(self, feature: Dict[str, Any]) -> bool:
        """
        Validate single feature structure

        Args:
            feature: Feature data

        Returns:
            True if valid
        """
        # Must have id and name
        if "id" not in feature:
            return False

        if "name" not in feature:
            return False

        return True

    def _check_git_status(self) -> str:
        """
        Check git repository status

        Returns:
            Git status summary or empty string if clean
        """
        import subprocess

        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.source_path,
                capture_output=True,
                text=True,
                timeout=5
            )

            if result.returncode == 0:
                return result.stdout.strip()
            else:
                return ""
        except Exception:
            return ""

    def format_validation_result(self, result: ValidationResult, title: str = "Validation Result") -> str:
        """
        Format validation result for display

        Args:
            result: Validation result
            title: Title for output

        Returns:
            Formatted string
        """
        lines = []
        lines.append("=" * 60)
        lines.append(title)
        lines.append("=" * 60)
        lines.append("")

        lines.append(f"Status: {'✅ PASSED' if result.passed else '❌ FAILED'}")
        lines.append("")

        if result.errors:
            lines.append("Errors:")
            for error in result.errors:
                lines.append(f"  ❌ {error}")
            lines.append("")

        if result.warnings:
            lines.append("Warnings:")
            for warning in result.warnings:
                lines.append(f"  ⚠️  {warning}")
            lines.append("")

        if result.suggestions:
            lines.append("Suggestions:")
            for suggestion in result.suggestions:
                lines.append(f"  💡 {suggestion}")
            lines.append("")

        lines.append("=" * 60)

        return "\n".join(lines)
