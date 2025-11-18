"""
Migration Converter - Transform v2.0 data to v3.0 format

Handles:
- HRPO → features.json conversion
- Governance config format updates
- Supabase schema migration
- Data validation and sanitization
"""

from pathlib import Path
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

from .v2_parser import V2Project


@dataclass
class ConversionResult:
    """Result of migration conversion"""
    success: bool
    features_json: Dict[str, Any]
    governance_yaml: Dict[str, Any]
    warnings: List[str]
    errors: List[str]
    metadata: Dict[str, Any]


class MigrationConverter:
    """
    Convert BuildRunner 2.0 data to 3.0 format

    Conversion mappings:
    - HRPO → features.json
    - governance.json → .buildrunner/governance.yaml
    - Supabase config → new format
    """

    def __init__(self, project: V2Project):
        """
        Initialize converter

        Args:
            project: Parsed v2.0 project
        """
        self.project = project
        self.warnings: List[str] = []
        self.errors: List[str] = []

    def convert(self) -> ConversionResult:
        """
        Convert v2.0 project to v3.0 format

        Returns:
            ConversionResult with converted data
        """
        result = ConversionResult(
            success=False,
            features_json={},
            governance_yaml={},
            warnings=[],
            errors=[],
            metadata={}
        )

        # Convert HRPO to features.json
        result.features_json = self.convert_hrpo_to_features(self.project.hrpo_data)

        # Convert governance config
        result.governance_yaml = self.convert_governance_config(self.project.governance_config)

        # Add migration metadata
        result.metadata = {
            "migration_date": datetime.now().isoformat(),
            "source_version": "2.0",
            "target_version": "3.0",
            "project_name": self.project.metadata.get("name", "Unknown"),
            "original_path": str(self.project.root_path),
            "features_migrated": len(self.project.features),
        }

        # Collect warnings and errors
        result.warnings = self.warnings.copy()
        result.errors = self.errors.copy()

        # Mark success if no errors
        result.success = len(result.errors) == 0

        return result

    def convert_hrpo_to_features(self, hrpo: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert HRPO format to features.json format

        Mapping:
        - hrpo.features → features array
        - hrpo.build_plan.phases → features with phases
        - hrpo.executive_summary → project description
        - hrpo.progress → overall progress

        Args:
            hrpo: HRPO data from v2.0

        Returns:
            features.json data structure
        """
        if not hrpo:
            self.warnings.append("No HRPO data to convert")
            return self._create_empty_features_json()

        features_json = {
            "project": {
                "name": self.project.metadata.get("name", "Migrated Project"),
                "version": "3.0.0",
                "description": hrpo.get("executive_summary", ""),
                "migrated_from_v2": True,
                "migration_date": datetime.now().isoformat()
            },
            "features": []
        }

        # Convert features list
        features_list = hrpo.get("features", [])
        for idx, feature in enumerate(features_list, 1):
            if isinstance(feature, str):
                # Simple string feature
                features_json["features"].append({
                    "id": f"feature_{idx}",
                    "name": feature,
                    "description": feature,
                    "status": "unknown",
                    "priority": "medium",
                    "migrated": True
                })
            elif isinstance(feature, dict):
                # Structured feature - preserve structure
                features_json["features"].append({
                    "id": f"feature_{idx}",
                    **feature,
                    "migrated": True
                })

        # Convert build plan phases to features
        build_plan = hrpo.get("build_plan", {})
        if build_plan and "phases" in build_plan:
            phase_id = len(features_json["features"]) + 1

            for phase in build_plan["phases"]:
                phase_name = phase.get("name", "Unknown Phase")
                steps = phase.get("steps", [])

                for step in steps:
                    step_name = step.get("name", "Unknown Step")
                    done = step.get("done", False)

                    features_json["features"].append({
                        "id": f"phase_{phase_id}",
                        "name": f"{phase_name}: {step_name}",
                        "description": f"Step {step.get('id', '?')}: {step_name}",
                        "status": "completed" if done else "not_started",
                        "priority": "medium",
                        "phase": phase_name,
                        "step_id": step.get("id"),
                        "migrated": True,
                        "source": "build_plan"
                    })
                    phase_id += 1

        # Add next version features
        next_features = hrpo.get("next_version_features", [])
        for idx, feature in enumerate(next_features, 1):
            features_json["features"].append({
                "id": f"future_{idx}",
                "name": feature,
                "description": feature,
                "status": "planned",
                "priority": "low",
                "migrated": True,
                "source": "next_version"
            })

        # Add progress metadata
        progress = hrpo.get("progress", {})
        if progress:
            features_json["project"]["progress"] = {
                "steps_completed": progress.get("steps_completed", 0),
                "total_steps": progress.get("total_steps", 0),
                "percent_complete": progress.get("percent_complete", 0.0)
            }

        # Add value proposition and audience
        if "value_proposition" in hrpo:
            features_json["project"]["value_proposition"] = hrpo["value_proposition"]

        if "intended_audience" in hrpo:
            features_json["project"]["target_users"] = hrpo["intended_audience"]

        return features_json

    def convert_governance_config(self, old_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Convert legacy governance.json to new YAML format

        Changes:
        - Rename fields for consistency
        - Update validation rules
        - Migrate quality thresholds
        - Convert to YAML structure

        Args:
            old_config: Legacy governance.json

        Returns:
            New governance config (YAML-compatible dict)
        """
        if not old_config:
            self.warnings.append("No governance config to convert")
            return self._create_default_governance()

        new_config = {
            "project": {
                "name": old_config.get("project", {}).get("name", "Unknown Project"),
                "slug": old_config.get("project", {}).get("slug", "unknown-project"),
            },
            "policies": {},
            "quality": {},
            "workflow": {},
            "migration": {
                "migrated_from_v2": True,
                "migration_date": datetime.now().isoformat()
            }
        }

        # Convert policies
        old_policies = old_config.get("policies", {})

        new_config["policies"] = {
            "require_tests": True,  # Default for v3.0
            "require_documentation": True,
            "auto_commit": old_policies.get("auto_completion_stamp", False),
            "spec_sync": old_policies.get("spec_hrpo_sync", True),
        }

        # Convert inline editor policy
        editor_policy = old_policies.get("inline_open_editor_policy", {})
        if editor_policy:
            new_config["policies"]["editor"] = {
                "enabled": editor_policy.get("enforced", True),
                "file_types": editor_policy.get("targets", []),
                "action": editor_policy.get("action", "")
            }

        # Convert full file output policy
        file_policy = old_policies.get("full_file_output_policy", {})
        if file_policy:
            new_config["policies"]["output"] = {
                "full_file_required": file_policy.get("enforced", True),
                "description": file_policy.get("description", "")
            }

        # Convert versioning
        versioning = old_config.get("versioning", {})
        if versioning:
            semver = versioning.get("semver", {})
            new_config["workflow"]["versioning"] = {
                "enabled": semver.get("enabled", True),
                "strategy": "semver",
                "rules": semver.get("rules", {}),
                "prerelease_tags": semver.get("prerelease_tags", [])
            }

        # Convert stages
        stages = old_config.get("stages", {})
        if stages:
            new_config["workflow"]["stages"] = {
                "order": stages.get("order", []),
                "aliases": stages.get("aliases", {}),
                "current": old_config.get("defaults", {}).get("default_stage", "GA")
            }

        # Add quality standards (new in v3.0)
        new_config["quality"] = {
            "min_test_coverage": 85,
            "max_complexity": 10,
            "require_type_hints": True,
            "code_formatting": "black",
            "migrated_defaults": True
        }

        return new_config

    def migrate_supabase_data(self, supabase_config: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        """
        Migrate Supabase configuration and schema

        Args:
            supabase_config: Legacy Supabase config

        Returns:
            Migrated Supabase config or None
        """
        if not supabase_config:
            return None

        migrated = {
            "version": "3.0",
            "migrated": True,
            "config": supabase_config.copy(),
            "migration_notes": []
        }

        # Check for required fields
        required_fields = ["SUPABASE_URL", "SUPABASE_KEY"]
        for field in required_fields:
            if field not in supabase_config:
                self.warnings.append(f"Missing Supabase field: {field}")
                migrated["migration_notes"].append(f"Missing: {field}")

        return migrated

    def _create_empty_features_json(self) -> Dict[str, Any]:
        """Create empty features.json structure"""
        return {
            "project": {
                "name": "Migrated Project",
                "version": "3.0.0",
                "description": "Migrated from BuildRunner 2.0",
                "migrated_from_v2": True
            },
            "features": []
        }

    def _create_default_governance(self) -> Dict[str, Any]:
        """Create default governance config"""
        return {
            "project": {
                "name": "Migrated Project",
                "slug": "migrated-project"
            },
            "policies": {
                "require_tests": True,
                "require_documentation": True
            },
            "quality": {
                "min_test_coverage": 85,
                "max_complexity": 10
            },
            "migration": {
                "migrated_from_v2": True,
                "migration_date": datetime.now().isoformat(),
                "note": "Created from default - no governance.json found"
            }
        }

    def format_features_json(self, features: Dict[str, Any]) -> str:
        """
        Format features.json for output

        Args:
            features: Features data

        Returns:
            Formatted JSON string
        """
        return json.dumps(features, indent=2)

    def format_governance_yaml(self, governance: Dict[str, Any]) -> str:
        """
        Format governance config as YAML

        Args:
            governance: Governance data

        Returns:
            YAML-formatted string
        """
        import yaml
        return yaml.dump(governance, default_flow_style=False, sort_keys=False)
