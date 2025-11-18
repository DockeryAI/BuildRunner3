"""
Tests for cli.config_manager module
"""

import pytest
import yaml
from pathlib import Path

from cli.config_manager import (
    ConfigManager,
    ConfigError,
    get_config_manager
)


class TestConfigManager:
    """Test suite for ConfigManager."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temp project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / ".buildrunner").mkdir()
        return project_dir

    @pytest.fixture
    def config_manager(self, temp_project):
        """Create ConfigManager instance."""
        return ConfigManager(temp_project)

    def test_init_default_path(self):
        """Test initialization with default path."""
        cm = ConfigManager()
        assert cm.project_root == Path.cwd()
        assert cm.global_config_dir == Path.home() / ".buildrunner"

    def test_init_custom_path(self, temp_project):
        """Test initialization with custom path."""
        cm = ConfigManager(temp_project)
        assert cm.project_root == temp_project

    def test_load_defaults(self, config_manager):
        """Test loading returns defaults when no configs exist."""
        config = config_manager.load()

        assert 'debug' in config
        assert config['debug']['auto_retry'] is True
        assert config['debug']['max_retries'] == 3

    def test_load_global_config(self, config_manager, tmp_path):
        """Test loading global config."""
        # Create fake home directory
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        config_manager.global_config_dir = fake_home / ".buildrunner"
        config_manager.global_config_dir.mkdir()
        config_manager.global_config_file = config_manager.global_config_dir / "global-behavior.yaml"

        # Write global config
        global_config = {
            'debug': {
                'auto_retry': False
            }
        }
        with open(config_manager.global_config_file, 'w') as f:
            yaml.dump(global_config, f)

        config = config_manager.load()

        # Global should override defaults
        assert config['debug']['auto_retry'] is False
        assert config['debug']['max_retries'] == 3  # Still from defaults

    def test_load_project_config(self, config_manager):
        """Test loading project config."""
        # Write project config
        project_config = {
            'debug': {
                'max_retries': 5
            }
        }
        config_manager.project_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_manager.project_config_file, 'w') as f:
            yaml.dump(project_config, f)

        config = config_manager.load()

        # Project should override defaults
        assert config['debug']['max_retries'] == 5

    def test_config_hierarchy(self, config_manager, tmp_path):
        """Test project > global > defaults hierarchy."""
        # Setup fake home
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        config_manager.global_config_dir = fake_home / ".buildrunner"
        config_manager.global_config_dir.mkdir()
        config_manager.global_config_file = config_manager.global_config_dir / "global-behavior.yaml"

        # Write global config (overrides defaults)
        global_config = {
            'debug': {
                'auto_retry': False,
                'max_retries': 5
            }
        }
        with open(config_manager.global_config_file, 'w') as f:
            yaml.dump(global_config, f)

        # Write project config (overrides global)
        project_config = {
            'debug': {
                'max_retries': 10
            }
        }
        config_manager.project_config_file.parent.mkdir(parents=True, exist_ok=True)
        with open(config_manager.project_config_file, 'w') as f:
            yaml.dump(project_config, f)

        config = config_manager.load()

        # Project overrides global
        assert config['debug']['max_retries'] == 10
        # Global overrides defaults
        assert config['debug']['auto_retry'] is False

    def test_get_simple_key(self, config_manager):
        """Test getting simple config value."""
        config_manager.load()
        value = config_manager.get('debug.auto_retry')
        assert value is True

    def test_get_nested_key(self, config_manager):
        """Test getting nested config value."""
        config_manager.load()
        value = config_manager.get('debug.max_retries')
        assert value == 3

    def test_get_missing_key(self, config_manager):
        """Test getting non-existent key returns default."""
        config_manager.load()
        value = config_manager.get('nonexistent.key', default='test')
        assert value == 'test'

    def test_set_project_scope(self, config_manager):
        """Test setting project config value."""
        config_manager.load()
        config_manager.set('debug.auto_retry', False, scope='project')

        # Verify it was written
        with open(config_manager.project_config_file, 'r') as f:
            saved = yaml.safe_load(f)

        assert saved['debug']['auto_retry'] is False

    def test_set_global_scope(self, config_manager, tmp_path):
        """Test setting global config value."""
        # Setup fake home
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        config_manager.global_config_dir = fake_home / ".buildrunner"
        config_manager.global_config_file = fake_home / ".buildrunner" / "global-behavior.yaml"

        config_manager.load()
        config_manager.set('debug.auto_retry', False, scope='global')

        # Verify it was written
        assert config_manager.global_config_file.exists()
        with open(config_manager.global_config_file, 'r') as f:
            saved = yaml.safe_load(f)

        assert saved['debug']['auto_retry'] is False

    def test_set_invalid_scope(self, config_manager):
        """Test setting with invalid scope raises error."""
        config_manager.load()

        with pytest.raises(ConfigError, match="Invalid scope"):
            config_manager.set('debug.auto_retry', False, scope='invalid')

    def test_list_all_nested(self, config_manager):
        """Test listing all config as nested dict."""
        config_manager.load()
        config = config_manager.list_all(flat=False)

        assert isinstance(config, dict)
        assert 'debug' in config
        assert isinstance(config['debug'], dict)

    def test_list_all_flat(self, config_manager):
        """Test listing all config as flat dict."""
        config_manager.load()
        config = config_manager.list_all(flat=True)

        assert isinstance(config, dict)
        assert 'debug.auto_retry' in config
        assert 'debug.max_retries' in config

    def test_init_global_config(self, config_manager, tmp_path):
        """Test initializing global config file."""
        # Setup fake home
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        config_manager.global_config_dir = fake_home / ".buildrunner"
        config_manager.global_config_file = fake_home / ".buildrunner" / "global-behavior.yaml"

        config_file = config_manager.init_global_config()

        assert config_file.exists()

        # Verify it has defaults
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        assert 'debug' in config
        assert 'watch' in config

    def test_init_global_config_exists(self, config_manager, tmp_path):
        """Test initializing global config when it exists raises error."""
        fake_home = tmp_path / "home"
        fake_home.mkdir()
        config_manager.global_config_dir = fake_home / ".buildrunner"
        config_manager.global_config_dir.mkdir()
        config_manager.global_config_file = fake_home / ".buildrunner" / "global-behavior.yaml"

        # Create existing file
        config_manager.global_config_file.touch()

        with pytest.raises(ConfigError, match="already exists"):
            config_manager.init_global_config()

    def test_init_project_config(self, config_manager):
        """Test initializing project config file."""
        config_file = config_manager.init_project_config()

        assert config_file.exists()

        # Verify minimal config
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)

        assert 'debug' in config

    def test_get_config_sources(self, config_manager):
        """Test getting config from all sources separately."""
        sources = config_manager.get_config_sources()

        assert 'default' in sources
        assert 'global' in sources
        assert 'project' in sources
        assert len(sources['default']) > 0


class TestFactoryFunction:
    """Test factory function."""

    def test_get_config_manager(self, tmp_path):
        """Test factory function creates and loads manager."""
        cm = get_config_manager(tmp_path)

        assert isinstance(cm, ConfigManager)
        assert cm._config is not None  # Should be loaded
