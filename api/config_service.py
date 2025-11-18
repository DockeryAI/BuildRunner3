"""
Configuration service for BuildRunner 3.0

Loads, merges, and validates configuration from multiple sources.
Because one config file is never enough.
"""

import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ConfigService:
    """
    Manages configuration hierarchy and merging.

    Priority: project > global > defaults
    Because later configs should override earlier ones, except when they don't.
    """

    def __init__(self, project_root: Optional[str] = None):
        """
        Initialize config service.

        Args:
            project_root: Project root directory (defaults to current directory)
        """
        self.project_root = Path(project_root or os.getcwd())
        self.global_config_path = Path.home() / ".buildrunner" / "behavior.yaml"
        self.project_config_path = self.project_root / ".buildrunner" / "behavior.yaml"

        # Default config - the fallback when everything else fails
        self.default_config: Dict[str, Any] = {
            "ai_behavior": {
                "auto_suggest_tests": True,
                "auto_fix_errors": False,
                "verbosity": "normal",
                "max_retries": 3
            },
            "auto_commit": {
                "enabled": False,
                "on_feature_complete": True,
                "on_tests_pass": False,
                "require_approval": True
            },
            "testing": {
                "auto_run": False,
                "run_on_save": False,
                "coverage_threshold": 85,
                "fail_on_coverage_drop": True
            },
            "notifications": {
                "enabled": False,
                "on_error": True,
                "on_test_fail": True,
                "on_feature_complete": True
            }
        }

    def load_config(self, path: Path) -> Dict[str, Any]:
        """
        Load config from YAML file.

        Args:
            path: Path to config file

        Returns:
            Loaded config dict or empty dict if file doesn't exist
        """
        if not path.exists():
            return {}

        try:
            with open(path, 'r') as f:
                config = yaml.safe_load(f) or {}
            return config
        except Exception as e:
            # If we can't load the config, log it and return empty
            # Because crashing on a config file would be embarrassing
            print(f"Warning: Failed to load config from {path}: {e}")
            return {}

    def merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Deep merge two config dictionaries.

        Args:
            base: Base configuration
            override: Overriding configuration

        Returns:
            Merged configuration
        """
        result = base.copy()

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                # Recursively merge nested dicts
                result[key] = self.merge_configs(result[key], value)
            else:
                # Override value
                result[key] = value

        return result

    def get_global_config(self) -> Dict[str, Any]:
        """
        Get global configuration.

        Returns:
            Global config merged with defaults
        """
        global_config = self.load_config(self.global_config_path)
        return self.merge_configs(self.default_config, global_config)

    def get_project_config(self) -> Dict[str, Any]:
        """
        Get project-specific configuration.

        Returns:
            Project config (no defaults)
        """
        return self.load_config(self.project_config_path)

    def get_merged_config(self) -> Dict[str, Any]:
        """
        Get fully merged configuration.

        Priority: project > global > defaults

        Returns:
            Complete merged configuration
        """
        merged = self.default_config.copy()
        merged = self.merge_configs(merged, self.load_config(self.global_config_path))
        merged = self.merge_configs(merged, self.load_config(self.project_config_path))
        return merged

    def update_project_config(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update project configuration.

        Args:
            updates: Configuration updates to apply

        Returns:
            Updated project configuration
        """
        # Load current project config
        current = self.get_project_config()

        # Merge updates
        updated = self.merge_configs(current, updates)

        # Ensure .buildrunner directory exists
        buildrunner_dir = self.project_root / ".buildrunner"
        buildrunner_dir.mkdir(parents=True, exist_ok=True)

        # Write updated config
        with open(self.project_config_path, 'w') as f:
            yaml.dump(updated, f, default_flow_style=False, sort_keys=False)

        return updated

    def get_config_schema(self) -> Dict[str, Any]:
        """
        Get configuration schema.

        Returns:
            JSON schema for behavior.yaml
        """
        return {
            "type": "object",
            "properties": {
                "ai_behavior": {
                    "type": "object",
                    "properties": {
                        "auto_suggest_tests": {"type": "boolean"},
                        "auto_fix_errors": {"type": "boolean"},
                        "verbosity": {"type": "string", "enum": ["quiet", "normal", "verbose"]},
                        "max_retries": {"type": "integer", "minimum": 0, "maximum": 10}
                    }
                },
                "auto_commit": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "on_feature_complete": {"type": "boolean"},
                        "on_tests_pass": {"type": "boolean"},
                        "require_approval": {"type": "boolean"}
                    }
                },
                "testing": {
                    "type": "object",
                    "properties": {
                        "auto_run": {"type": "boolean"},
                        "run_on_save": {"type": "boolean"},
                        "coverage_threshold": {"type": "number", "minimum": 0, "maximum": 100},
                        "fail_on_coverage_drop": {"type": "boolean"}
                    }
                },
                "notifications": {
                    "type": "object",
                    "properties": {
                        "enabled": {"type": "boolean"},
                        "on_error": {"type": "boolean"},
                        "on_test_fail": {"type": "boolean"},
                        "on_feature_complete": {"type": "boolean"}
                    }
                }
            }
        }

    def validate_config(self, config: Dict[str, Any]) -> tuple[bool, list[str]]:
        """
        Validate configuration against schema.

        Args:
            config: Configuration to validate

        Returns:
            Tuple of (is_valid, error_messages)
        """
        errors = []

        # Basic validation - check for unknown keys at top level
        valid_keys = {"ai_behavior", "auto_commit", "testing", "notifications"}
        for key in config.keys():
            if key not in valid_keys:
                errors.append(f"Unknown configuration key: {key}")

        # Validate ai_behavior
        if "ai_behavior" in config:
            ai = config["ai_behavior"]
            if not isinstance(ai, dict):
                errors.append("ai_behavior must be a dictionary")
            else:
                if "verbosity" in ai and ai["verbosity"] not in ["quiet", "normal", "verbose"]:
                    errors.append("ai_behavior.verbosity must be 'quiet', 'normal', or 'verbose'")
                if "max_retries" in ai:
                    if not isinstance(ai["max_retries"], int) or ai["max_retries"] < 0 or ai["max_retries"] > 10:
                        errors.append("ai_behavior.max_retries must be an integer between 0 and 10")

        # Validate testing
        if "testing" in config:
            testing = config["testing"]
            if not isinstance(testing, dict):
                errors.append("testing must be a dictionary")
            else:
                if "coverage_threshold" in testing:
                    threshold = testing["coverage_threshold"]
                    if not isinstance(threshold, (int, float)) or threshold < 0 or threshold > 100:
                        errors.append("testing.coverage_threshold must be a number between 0 and 100")

        return len(errors) == 0, errors
