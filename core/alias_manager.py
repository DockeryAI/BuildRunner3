"""
Project Alias Manager
Handles project alias configuration for quick project switching
"""
import json
import os
from pathlib import Path
from typing import Dict, Optional


class AliasManager:
    """Manages project aliases for quick access"""

    def __init__(self):
        self.config_dir = Path.home() / ".buildrunner"
        self.alias_file = self.config_dir / "aliases.json"
        self._ensure_config_dir()

    def _ensure_config_dir(self):
        """Ensure config directory exists"""
        self.config_dir.mkdir(parents=True, exist_ok=True)
        if not self.alias_file.exists():
            self._save_aliases({})

    def _load_aliases(self) -> Dict[str, str]:
        """Load aliases from config file"""
        try:
            with open(self.alias_file, 'r') as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_aliases(self, aliases: Dict[str, str]):
        """Save aliases to config file"""
        with open(self.alias_file, 'w') as f:
            json.dump(aliases, f, indent=2)

    def set_alias(self, alias: str, project_path: str) -> bool:
        """
        Set an alias for a project path

        Args:
            alias: Alias name (e.g., 'br3', 'myapp')
            project_path: Absolute path to project directory

        Returns:
            bool: True if successful
        """
        # Validate alias name
        if not alias or not alias.replace('-', '').replace('_', '').isalnum():
            raise ValueError(f"Invalid alias name: {alias}. Use alphanumeric, dash, or underscore.")

        # Validate project path exists
        path = Path(project_path).resolve()
        if not path.exists():
            raise ValueError(f"Project path does not exist: {project_path}")

        if not path.is_dir():
            raise ValueError(f"Project path is not a directory: {project_path}")

        aliases = self._load_aliases()
        aliases[alias] = str(path)
        self._save_aliases(aliases)

        return True

    def get_alias(self, alias: str) -> Optional[str]:
        """
        Get project path for an alias

        Args:
            alias: Alias name

        Returns:
            str: Project path or None if not found
        """
        aliases = self._load_aliases()
        return aliases.get(alias)

    def remove_alias(self, alias: str) -> bool:
        """
        Remove an alias

        Args:
            alias: Alias name to remove

        Returns:
            bool: True if removed, False if not found
        """
        aliases = self._load_aliases()
        if alias in aliases:
            del aliases[alias]
            self._save_aliases(aliases)
            return True
        return False

    def list_aliases(self) -> Dict[str, str]:
        """
        List all aliases

        Returns:
            Dict[str, str]: Mapping of alias to project path
        """
        return self._load_aliases()

    def get_project_status_prompt(self, project_path: str) -> str:
        """
        Generate a prompt to bring Claude up to speed on project status

        Args:
            project_path: Path to project directory

        Returns:
            str: Prompt text to update Claude on project status
        """
        path = Path(project_path)
        project_name = path.name

        prompt = f"""I'm resuming work on the {project_name} project.

Project Directory: {project_path}

Please help me get up to speed:
1. Review the current git status and recent commits
2. Check for any TODO or FIXME comments in the codebase
3. Review the PROJECT_SPEC.md or README.md if they exist
4. Check for any failing tests or build issues
5. Summarize the current state and suggest next steps

Let's start building with BuildRunner3!"""

        return prompt


# Singleton instance
alias_manager = AliasManager()
