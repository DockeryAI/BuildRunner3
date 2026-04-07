"""Changelog Generator - Auto-generate changelogs from commits"""

from pathlib import Path
from typing import Optional, List
from .git_client import GitClient


class ChangelogGenerator:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)

    def generate(self, since_tag: Optional[str] = None) -> str:
        """Generate changelog"""
        if since_tag:
            commits = self.git.get_commits_since_tag(since_tag)
        else:
            commits = []

        changelog = "# Changelog\n\n"
        for commit in commits:
            changelog += f"- {commit}\n"
        return changelog
