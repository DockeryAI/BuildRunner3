"""
Configuration Manager for BuildRunner 3.0

Manages hierarchical configuration: Project > Global > Defaults
Loads from ~/.buildrunner/global-behavior.yaml and .buildrunner/behavior.yaml
"""

import os
import yaml
from pathlib import Path
from typing import Any, Dict, Optional
from copy import deepcopy


class ConfigError(Exception):
    """Raised when configuration operations fail."""
    pass


class ConfigManager:
    """
    Manages Build Runner configuration with hierarchical loading.

    Hierarchy (highest to lowest priority):
    1. Project config: .buildrunner/behavior.yaml
    2. Global config: ~/.buildrunner/global-behavior.yaml
    3. Default config: Hardcoded defaults

    Attributes:
        project_root: Root directory of current project
        global_config_dir: ~/.buildrunner directory
        global_config_file: ~/.buildrunner/global-behavior.yaml
        project_config_file: .buildrunner/behavior.yaml
    """

    DEFAULT_CONFIG = {
        'debug': {
            'auto_retry': True,
            'max_retries': 3,
            'retry_delays': [1, 2, 4, 8],  # seconds
            'capture_output': True,
            'log_to_context': True,
        },
        'watch': {
            'enabled': False,
            'patterns': ['*.log', '*.err', 'pytest.out'],
            'check_interval': 2,  # seconds
            'auto_update_blockers': True,
        },
        'piping': {
            'auto_timestamp': True,
            'max_output_size': 100000,  # characters
            'context_file': '.buildrunner/context/command-outputs.md',
        },
        'cli': {
            'use_rich': True,
            'show_progress': True,
            'confirm_destructive': True,
        },
        'governance': {
            'enforce_on_commit': True,
            'verify_checksums': True,
            'strict_mode': True,
        },
        'profiles': {
            'default_profile': None,  # Auto-activate this profile in all projects
            'auto_activate': True,  # Auto-activate default profile
        },
        'build': {
            'auto_continue': True,  # Never pause for confirmation, build to 100% completion
            'require_user_approval': False,  # Don't ask for approval between tasks
            'stop_on_error': True,  # Only stop if there's a critical error
        }
    }

    def __init__(self, project_root: Optional[Path] = None):
        """
        Initialize ConfigManager.

        Args:
            project_root: Root directory of project. Defaults to current directory.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.global_config_dir = Path.home() / ".buildrunner"
        self.global_config_file = self.global_config_dir / "global-behavior.yaml"
        self.project_config_file = self.project_root / ".buildrunner" / "behavior.yaml"

        self._config: Optional[Dict[str, Any]] = None

    def load(self) -> Dict[str, Any]:
        """
        Load and merge configuration from all sources.

        Returns:
            Merged configuration dictionary.

        Raises:
            ConfigError: If configuration cannot be loaded.
        """
        # Start with defaults
        config = deepcopy(self.DEFAULT_CONFIG)

        # Load and merge global config
        if self.global_config_file.exists():
            try:
                with open(self.global_config_file, 'r') as f:
                    global_config = yaml.safe_load(f) or {}
                config = self._merge_configs(config, global_config)
            except Exception as e:
                raise ConfigError(f"Failed to load global config: {e}")

        # Load and merge project config
        if self.project_config_file.exists():
            try:
                with open(self.project_config_file, 'r') as f:
                    project_config = yaml.safe_load(f) or {}
                config = self._merge_configs(config, project_config)
            except Exception as e:
                raise ConfigError(f"Failed to load project config: {e}")

        self._config = config
        return config

    def _merge_configs(self, base: Dict[str, Any], override: Dict[str, Any]) -> Dict[str, Any]:
        """
        Recursively merge two configuration dictionaries.

        Args:
            base: Base configuration
            override: Configuration to merge (takes precedence)

        Returns:
            Merged configuration
        """
        result = deepcopy(base)

        for key, value in override.items():
            if key in result and isinstance(result[key], dict) and isinstance(value, dict):
                result[key] = self._merge_configs(result[key], value)
            else:
                result[key] = value

        return result

    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by dot-notation key.

        Args:
            key: Configuration key (e.g., 'debug.auto_retry')
            default: Default value if key not found

        Returns:
            Configuration value or default

        Examples:
            >>> config.get('debug.auto_retry')
            True
            >>> config.get('debug.max_retries')
            3
        """
        if self._config is None:
            self.load()

        keys = key.split('.')
        value = self._config

        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default

        return value

    def set(self, key: str, value: Any, scope: str = 'project') -> None:
        """
        Set configuration value.

        Args:
            key: Configuration key in dot notation (e.g., 'debug.auto_retry')
            value: Value to set
            scope: 'project' or 'global'

        Raises:
            ConfigError: If setting fails
        """
        if scope not in ['project', 'global']:
            raise ConfigError(f"Invalid scope: {scope}. Must be 'project' or 'global'.")

        config_file = self.project_config_file if scope == 'project' else self.global_config_file

        # Load existing config for this scope
        if config_file.exists():
            with open(config_file, 'r') as f:
                config = yaml.safe_load(f) or {}
        else:
            config = {}

        # Set value using dot notation
        keys = key.split('.')
        current = config

        for k in keys[:-1]:
            if k not in current:
                current[k] = {}
            current = current[k]

        current[keys[-1]] = value

        # Ensure directory exists
        config_file.parent.mkdir(parents=True, exist_ok=True)

        # Save config
        with open(config_file, 'w') as f:
            yaml.dump(config, f, default_flow_style=False, sort_keys=False)

        # Reload to update in-memory config
        self.load()

    def list_all(self, flat: bool = False) -> Dict[str, Any]:
        """
        List all configuration values.

        Args:
            flat: If True, return flat dict with dot-notation keys

        Returns:
            Configuration dictionary (nested or flat)
        """
        if self._config is None:
            self.load()

        if flat:
            return self._flatten_dict(self._config)
        return deepcopy(self._config)

    def _flatten_dict(self, d: Dict[str, Any], parent_key: str = '', sep: str = '.') -> Dict[str, Any]:
        """
        Flatten nested dictionary to dot-notation keys.

        Args:
            d: Dictionary to flatten
            parent_key: Parent key for recursion
            sep: Separator for keys

        Returns:
            Flattened dictionary
        """
        items = []
        for k, v in d.items():
            new_key = f"{parent_key}{sep}{k}" if parent_key else k
            if isinstance(v, dict):
                items.extend(self._flatten_dict(v, new_key, sep=sep).items())
            else:
                items.append((new_key, v))
        return dict(items)

    def init_global_config(self) -> Path:
        """
        Initialize global configuration file with defaults.

        Returns:
            Path to created global config file

        Raises:
            ConfigError: If initialization fails
        """
        self.global_config_dir.mkdir(parents=True, exist_ok=True)

        if self.global_config_file.exists():
            raise ConfigError(
                f"Global config already exists: {self.global_config_file}\n"
                f"Use 'br config set' to modify it."
            )

        with open(self.global_config_file, 'w') as f:
            yaml.dump(
                self.DEFAULT_CONFIG,
                f,
                default_flow_style=False,
                sort_keys=False
            )

        return self.global_config_file

    def init_project_config(self) -> Path:
        """
        Initialize project configuration file with defaults.

        Returns:
            Path to created project config file

        Raises:
            ConfigError: If initialization fails
        """
        self.project_config_file.parent.mkdir(parents=True, exist_ok=True)

        if self.project_config_file.exists():
            raise ConfigError(
                f"Project config already exists: {self.project_config_file}\n"
                f"Use 'br config set' to modify it."
            )

        # Start with minimal project config
        project_config = {
            'debug': {
                'auto_retry': True,
            },
            'cli': {
                'use_rich': True,
            }
        }

        with open(self.project_config_file, 'w') as f:
            yaml.dump(
                project_config,
                f,
                default_flow_style=False,
                sort_keys=False
            )

        return self.project_config_file

    def get_config_sources(self) -> Dict[str, Dict[str, Any]]:
        """
        Get configuration from all sources separately.

        Returns:
            Dictionary with 'default', 'global', 'project' keys
        """
        sources = {
            'default': deepcopy(self.DEFAULT_CONFIG),
            'global': {},
            'project': {}
        }

        if self.global_config_file.exists():
            with open(self.global_config_file, 'r') as f:
                sources['global'] = yaml.safe_load(f) or {}

        if self.project_config_file.exists():
            with open(self.project_config_file, 'r') as f:
                sources['project'] = yaml.safe_load(f) or {}

        return sources


# Factory function
def get_config_manager(project_root: Optional[Path] = None) -> ConfigManager:
    """
    Factory function to create and load a ConfigManager.

    Args:
        project_root: Root directory of project

    Returns:
        Loaded ConfigManager instance
    """
    manager = ConfigManager(project_root)
    manager.load()
    return manager
