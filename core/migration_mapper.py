"""
Migration Mapper for BuildRunner 2.0 to 3.0

Handles conversion of data structures from BR 2.0 to BR 3.0:
- Governance JSON to YAML format
- HRPO data to features.json
- Features v2.0 to v3.0 schema
"""

import json
import yaml
from pathlib import Path
from typing import Dict, List, Any, Optional
from datetime import datetime


class MigrationMapper:
    """Maps BR 2.0 data structures to BR 3.0 format."""

    # Map BR 2.0 feature statuses to BR 3.0
    STATUS_MAP = {
        "complete": "complete",
        "completed": "complete",
        "in-progress": "in_progress",
        "in_progress": "in_progress",
        "working": "in_progress",
        "planned": "planned",
        "pending": "planned",
        "blocked": "blocked",
        "deprecated": "deprecated",
        "production_ready": "complete",
    }

    # Map BR 2.0 priorities to BR 3.0
    PRIORITY_MAP = {
        "critical": "critical",
        "high": "high",
        "medium": "medium",
        "low": "low",
        "p0": "critical",
        "p1": "high",
        "p2": "medium",
        "p3": "low",
    }

    def __init__(self, v2_root: Path):
        """
        Initialize migration mapper.

        Args:
            v2_root: Root directory of BR 2.0 project
        """
        self.v2_root = Path(v2_root)
        self.runner_dir = self.v2_root / ".runner"
        self.buildrunner_dir = self.v2_root / ".buildrunner"

    def convert_governance_to_yaml(self, governance_json: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert governance.json (v2.0) to governance.yaml (v3.0) format.

        Args:
            governance_json: BR 2.0 governance.json content

        Returns:
            BR 3.0 governance.yaml content
        """
        # Extract project info
        project = governance_json.get("project", {})
        policies = governance_json.get("policies", {})
        rules = governance_json.get("rules", {})
        versioning = governance_json.get("versioning", {})

        # Build v3.0 governance structure
        governance_v3 = {
            "project": {
                "name": project.get("name", "Unknown Project"),
                "slug": project.get("slug", "unknown-project"),
            },
            "enforcement": {
                "policy": "strict" if policies.get("enforce_inline_open_editor", False) else "warn",
                "on_violation": {
                    "pre_commit": (
                        "block" if policies.get("enforce_full_file_output", False) else "warn"
                    ),
                    "pre_push": "block",
                },
                "auto_fix": False,  # Not in v2.0
            },
            "rules": {
                "required_checks": [
                    "features_valid",
                    "governance_valid",
                    "checksums_valid",
                ],
                "optional_checks": [],
                "custom_checks": [],
            },
        }

        # Convert inline editor policy if exists
        inline_policy = policies.get("inline_open_editor_policy", {})
        if inline_policy:
            governance_v3["policies"] = {
                "file_editing": {
                    "enforced": inline_policy.get("enforced", False),
                    "targets": inline_policy.get("targets", []),
                    "action": inline_policy.get("action", "warn"),
                },
                "full_file_output": {
                    "enforced": policies.get("full_file_output_policy", {}).get("enforced", False),
                    "description": policies.get("full_file_output_policy", {}).get(
                        "description", ""
                    ),
                },
            }

        # Convert versioning if exists
        if versioning:
            semver = versioning.get("semver", {})
            if semver.get("enabled"):
                governance_v3["versioning"] = {
                    "scheme": "semver",
                    "rules": semver.get("rules", {}),
                    "prerelease_tags": semver.get("prerelease_tags", []),
                }

        return governance_v3

    def convert_hrpo_to_features(self, hrpo_data: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Convert HRPO data to BR 3.0 features format.

        Args:
            hrpo_data: BR 2.0 HRPO.json content

        Returns:
            List of BR 3.0 feature objects
        """
        features = []

        # Extract phases from HRPO
        phases = hrpo_data.get("phases", [])

        for phase_idx, phase in enumerate(phases):
            phase_id = f"phase-{phase_idx + 1}"
            phase_name = phase.get("name", f"Phase {phase_idx + 1}")
            phase_status = phase.get("status", "planned")

            # Create a feature for the phase
            phase_feature = {
                "id": self._slugify(phase_id),
                "name": phase_name,
                "status": self._map_status(phase_status),
                "priority": self._map_priority(phase.get("priority", "medium")),
                "description": phase.get("description", ""),
                "created": phase.get("created", datetime.now().isoformat()),
            }

            # Add metadata
            if "steps" in phase:
                phase_feature["metadata"] = {
                    "total_steps": len(phase["steps"]),
                    "migrated_from": "hrpo",
                }

            features.append(phase_feature)

            # Convert steps to sub-features
            for step_idx, step in enumerate(phase.get("steps", [])):
                step_id = f"{phase_id}-step-{step_idx + 1}"
                step_name = step.get("name", f"Step {step_idx + 1}")
                step_status = step.get("status", "planned")

                step_feature = {
                    "id": self._slugify(step_id),
                    "name": step_name,
                    "status": self._map_status(step_status),
                    "priority": self._map_priority(step.get("priority", "medium")),
                    "description": step.get("description", ""),
                    "parent": self._slugify(phase_id),
                    "created": step.get("created", datetime.now().isoformat()),
                    "metadata": {
                        "migrated_from": "hrpo",
                    },
                }

                features.append(step_feature)

        return features

    def convert_features_v2_to_v3(self, features_v2: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert features.json from v2.0 to v3.0 schema.

        Args:
            features_v2: BR 2.0 features.json content

        Returns:
            BR 3.0 features.json content
        """
        # Start with project metadata
        features_v3 = {
            "project": features_v2.get("project", "Unknown Project"),
            "version": "3.0.0",  # Upgrade version
            "status": self._convert_project_status(features_v2.get("status", "in_development")),
            "last_updated": datetime.now().isoformat(),
            "description": features_v2.get("description", ""),
        }

        # Convert features array
        converted_features = []
        for feature_v2 in features_v2.get("features", []):
            feature_v3 = self._convert_single_feature(feature_v2)
            converted_features.append(feature_v3)

        features_v3["features"] = converted_features

        # Calculate metrics
        features_v3["metrics"] = self._calculate_metrics(converted_features)

        return features_v3

    def _convert_single_feature(self, feature_v2: Dict[str, Any]) -> Dict[str, Any]:
        """Convert a single feature from v2.0 to v3.0 format."""
        feature_v3 = {
            "id": feature_v2.get("id", self._generate_id(feature_v2.get("name", "unknown"))),
            "name": feature_v2.get("name", "Unnamed Feature"),
            "status": self._map_status(feature_v2.get("status", "planned")),
            "priority": self._map_priority(feature_v2.get("priority", "medium")),
            "description": feature_v2.get("description", ""),
        }

        # Add optional fields if present
        if "version" in feature_v2:
            feature_v3["version"] = feature_v2["version"]

        if "created" in feature_v2:
            feature_v3["created"] = feature_v2["created"]
        else:
            feature_v3["created"] = datetime.now().isoformat()

        # Convert metadata
        metadata = {}

        if "components" in feature_v2:
            metadata["components"] = feature_v2["components"]

        if "tests" in feature_v2:
            metadata["tests"] = feature_v2["tests"]

        if "docs" in feature_v2:
            metadata["docs"] = feature_v2["docs"]

        if "database_tables" in feature_v2:
            metadata["database_tables"] = feature_v2["database_tables"]

        if "apis" in feature_v2:
            metadata["apis"] = feature_v2["apis"]

        # Mark as migrated
        metadata["migrated_from"] = "v2.0"

        if metadata:
            feature_v3["metadata"] = metadata

        return feature_v3

    def _convert_project_status(self, status_v2: str) -> str:
        """Convert project-level status from v2.0 to v3.0."""
        status_map = {
            "production_ready": "production",
            "in_development": "in_development",
            "planning": "planning",
            "deprecated": "deprecated",
            "archived": "archived",
        }
        return status_map.get(status_v2.lower(), "in_development")

    def _map_status(self, status: str) -> str:
        """Map v2.0 status to v3.0 status."""
        return self.STATUS_MAP.get(status.lower().replace(" ", "_"), "planned")

    def _map_priority(self, priority: str) -> str:
        """Map v2.0 priority to v3.0 priority."""
        return self.PRIORITY_MAP.get(priority.lower(), "medium")

    def _slugify(self, text: str) -> str:
        """Convert text to slug format."""
        return text.lower().replace(" ", "-").replace("_", "-")

    def _generate_id(self, name: str) -> str:
        """Generate ID from name."""
        return self._slugify(name)

    def _calculate_metrics(self, features: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Calculate project metrics from features."""
        total = len(features)
        complete = len([f for f in features if f.get("status") == "complete"])
        in_progress = len([f for f in features if f.get("status") == "in_progress"])
        planned = len([f for f in features if f.get("status") == "planned"])
        blocked = len([f for f in features if f.get("status") == "blocked"])

        return {
            "features_total": total,
            "features_complete": complete,
            "features_in_progress": in_progress,
            "features_planned": planned,
            "features_blocked": blocked,
            "completion_percentage": round((complete / total * 100) if total > 0 else 0, 1),
        }

    def merge_hrpo_features(
        self, existing_features: List[Dict[str, Any]], hrpo_features: List[Dict[str, Any]]
    ) -> List[Dict[str, Any]]:
        """
        Merge HRPO-derived features with existing features.

        Args:
            existing_features: Features from features.json
            hrpo_features: Features converted from HRPO

        Returns:
            Merged feature list
        """
        # Create a map of existing feature IDs
        existing_ids = {f["id"] for f in existing_features}

        # Add HRPO features that don't already exist
        merged = existing_features.copy()
        for hrpo_feature in hrpo_features:
            if hrpo_feature["id"] not in existing_ids:
                merged.append(hrpo_feature)

        return merged

    def extract_git_metadata(self) -> Dict[str, Any]:
        """
        Extract git metadata from BR 2.0 project.

        Returns:
            Git metadata (commits, branches, etc.)
        """
        import subprocess

        metadata = {
            "git_available": False,
            "current_branch": None,
            "last_commit": None,
            "commit_count": 0,
        }

        try:
            # Check if git is available
            result = subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.v2_root,
                capture_output=True,
                text=True,
                timeout=5,
            )

            if result.returncode == 0:
                metadata["git_available"] = True

                # Get current branch
                branch_result = subprocess.run(
                    ["git", "branch", "--show-current"],
                    cwd=self.v2_root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if branch_result.returncode == 0:
                    metadata["current_branch"] = branch_result.stdout.strip()

                # Get last commit
                commit_result = subprocess.run(
                    ["git", "log", "-1", "--pretty=format:%H %s"],
                    cwd=self.v2_root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if commit_result.returncode == 0:
                    metadata["last_commit"] = commit_result.stdout.strip()

                # Get commit count
                count_result = subprocess.run(
                    ["git", "rev-list", "--count", "HEAD"],
                    cwd=self.v2_root,
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
                if count_result.returncode == 0:
                    metadata["commit_count"] = int(count_result.stdout.strip())

        except (subprocess.TimeoutExpired, FileNotFoundError, ValueError):
            pass

        return metadata
