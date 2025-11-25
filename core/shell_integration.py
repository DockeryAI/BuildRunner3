"""
Shell Integration - Manage shell aliases for BuildRunner projects

Handles reading/writing shell configuration files (.zshrc, .bashrc, .bash_profile)
to create project launch aliases.

Features:
- Auto-detect shell (zsh, bash)
- Add/remove aliases from shell config
- Backup config before modification
- Support multiple shells
- Generate launch commands with editor preferences
"""

import os
import logging
import shutil
from pathlib import Path
from typing import Optional, List, Tuple
from datetime import datetime

logger = logging.getLogger(__name__)


class ShellIntegration:
    """
    Manages shell configuration for project aliases

    Adds aliases to ~/.zshrc or ~/.bashrc:
    alias sales='cd ~/Projects/sales-assistant && claude --dangerously-skip-permissions'
    """

    # Shell config markers
    BR_MARKER_START = "# BuildRunner Project Aliases - DO NOT EDIT MANUALLY"
    BR_MARKER_END = "# End BuildRunner Project Aliases"

    def __init__(self):
        self.home = Path.home()
        self.shell_configs = self._detect_shell_configs()

    def _detect_shell_configs(self) -> List[Path]:
        """
        Detect which shell config files exist

        Returns:
            List of shell config file paths
        """
        possible_configs = [
            self.home / ".zshrc",
            self.home / ".bashrc",
            self.home / ".bash_profile",
        ]

        existing = [config for config in possible_configs if config.exists()]

        if not existing:
            # Default to .zshrc if nothing exists
            logger.warning("No shell config found, will create ~/.zshrc")
            return [self.home / ".zshrc"]

        return existing

    def get_primary_config(self) -> Path:
        """Get the primary shell config file to use"""
        # Prefer zsh (most common on macOS), then bash
        for config in self.shell_configs:
            if config.name == ".zshrc":
                return config

        return self.shell_configs[0]

    def backup_config(self, config_path: Path) -> Path:
        """
        Create a backup of shell config

        Args:
            config_path: Path to config file

        Returns:
            Path to backup file
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_path = config_path.parent / f"{config_path.name}.backup.{timestamp}"

        if config_path.exists():
            shutil.copy2(config_path, backup_path)
            logger.info(f"Created backup at {backup_path}")

        return backup_path

    def read_config(self, config_path: Path) -> str:
        """Read shell config file"""
        if not config_path.exists():
            return ""
        return config_path.read_text()

    def write_config(self, config_path: Path, content: str):
        """Write shell config file"""
        config_path.write_text(content)
        logger.debug(f"Updated {config_path}")

    def extract_br_section(self, content: str) -> Tuple[str, Optional[str], str]:
        """
        Extract BuildRunner alias section from config

        Args:
            content: Shell config content

        Returns:
            Tuple of (before_section, br_section, after_section)
            br_section is None if not found
        """
        if self.BR_MARKER_START not in content:
            return content, None, ""

        parts = content.split(self.BR_MARKER_START, 1)
        before = parts[0]

        if self.BR_MARKER_END not in parts[1]:
            # Malformed - marker start but no end
            logger.warning("Found BR marker start but no end marker")
            return content, None, ""

        middle_and_after = parts[1].split(self.BR_MARKER_END, 1)
        br_section = self.BR_MARKER_START + middle_and_after[0] + self.BR_MARKER_END
        after = middle_and_after[1]

        return before, br_section, after

    def generate_alias_command(
        self,
        alias: str,
        project_path: str,
        editor: str = "claude"
    ) -> str:
        """
        Generate shell alias command

        Args:
            alias: Alias name
            project_path: Project directory path
            editor: Editor command (claude, cursor, windsurf)

        Returns:
            Shell alias command string
        """
        # Editor-specific launch commands
        editor_commands = {
            "claude": "claude --dangerously-skip-permissions",
            "cursor": "cursor --disable-extensions --wait",
            "windsurf": "windsurf"
        }

        editor_cmd = editor_commands.get(editor, editor)

        return f"alias {alias}='cd {project_path} && {editor_cmd}'"

    def add_alias(
        self,
        alias: str,
        project_path: str,
        editor: str = "claude",
        backup: bool = True
    ) -> bool:
        """
        Add or update a project alias in shell config

        Args:
            alias: Alias name
            project_path: Project directory path
            editor: Editor to launch
            backup: Whether to backup config before modifying

        Returns:
            True if successful
        """
        config_path = self.get_primary_config()

        # Backup first
        if backup and config_path.exists():
            self.backup_config(config_path)

        # Read current config
        content = self.read_config(config_path)

        # Extract BR section
        before, br_section, after = self.extract_br_section(content)

        # Parse existing aliases
        existing_aliases = {}
        if br_section:
            for line in br_section.split("\n"):
                if line.startswith("alias "):
                    # Parse: alias name='...'
                    parts = line.split("=", 1)
                    if len(parts) == 2:
                        alias_name = parts[0].replace("alias ", "").strip()
                        existing_aliases[alias_name] = line

        # Add or update alias
        alias_cmd = self.generate_alias_command(alias, project_path, editor)
        existing_aliases[alias] = alias_cmd

        # Rebuild BR section
        new_br_lines = [
            "",
            self.BR_MARKER_START,
        ]
        for alias_line in sorted(existing_aliases.values()):
            new_br_lines.append(alias_line)
        new_br_lines.append(self.BR_MARKER_END)
        new_br_lines.append("")

        new_br_section = "\n".join(new_br_lines)

        # Rebuild config
        new_content = before.rstrip() + "\n" + new_br_section + after.lstrip()

        # Write back
        self.write_config(config_path, new_content)

        logger.info(f"Added alias '{alias}' to {config_path}")
        return True

    def remove_alias(self, alias: str, backup: bool = True) -> bool:
        """
        Remove a project alias from shell config

        Args:
            alias: Alias name to remove
            backup: Whether to backup config before modifying

        Returns:
            True if removed, False if not found
        """
        config_path = self.get_primary_config()

        if not config_path.exists():
            logger.warning(f"Config file not found: {config_path}")
            return False

        # Backup first
        if backup:
            self.backup_config(config_path)

        # Read current config
        content = self.read_config(config_path)

        # Extract BR section
        before, br_section, after = self.extract_br_section(content)

        if not br_section:
            logger.warning("No BuildRunner aliases found in config")
            return False

        # Parse existing aliases
        existing_aliases = {}
        found = False
        for line in br_section.split("\n"):
            if line.startswith("alias "):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    alias_name = parts[0].replace("alias ", "").strip()
                    if alias_name == alias:
                        found = True
                        continue  # Skip this alias
                    existing_aliases[alias_name] = line

        if not found:
            logger.warning(f"Alias '{alias}' not found in config")
            return False

        # Rebuild BR section (or remove if empty)
        if existing_aliases:
            new_br_lines = [
                "",
                self.BR_MARKER_START,
            ]
            for alias_line in sorted(existing_aliases.values()):
                new_br_lines.append(alias_line)
            new_br_lines.append(self.BR_MARKER_END)
            new_br_lines.append("")
            new_br_section = "\n".join(new_br_lines)
        else:
            # No aliases left, remove section entirely
            new_br_section = ""

        # Rebuild config
        new_content = before.rstrip() + "\n" + new_br_section + after.lstrip()

        # Write back
        self.write_config(config_path, new_content)

        logger.info(f"Removed alias '{alias}' from {config_path}")
        return True

    def list_aliases(self) -> List[Tuple[str, str]]:
        """
        List all BuildRunner aliases in shell config

        Returns:
            List of (alias_name, command) tuples
        """
        config_path = self.get_primary_config()

        if not config_path.exists():
            return []

        content = self.read_config(config_path)
        before, br_section, after = self.extract_br_section(content)

        if not br_section:
            return []

        aliases = []
        for line in br_section.split("\n"):
            if line.startswith("alias "):
                parts = line.split("=", 1)
                if len(parts) == 2:
                    alias_name = parts[0].replace("alias ", "").strip()
                    command = parts[1].strip().strip("'\"")
                    aliases.append((alias_name, command))

        return sorted(aliases)

    def get_reload_command(self) -> str:
        """
        Get command to reload shell config

        Returns:
            Shell command string
        """
        config_path = self.get_primary_config()
        return f"source {config_path}"


# Global shell integration instance
_shell_integration: Optional[ShellIntegration] = None


def get_shell_integration() -> ShellIntegration:
    """Get or create global shell integration instance"""
    global _shell_integration
    if _shell_integration is None:
        _shell_integration = ShellIntegration()
    return _shell_integration
