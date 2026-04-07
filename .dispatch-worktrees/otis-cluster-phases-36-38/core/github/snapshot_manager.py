"""Snapshot Manager"""

from pathlib import Path
from typing import Optional
from .git_client import GitClient


class SnapshotManager:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)

    def create_snapshot(self, name: str):
        """Create snapshot"""
        tag = f"snapshot/{name}"
        self.git.create_tag(tag, f"Snapshot: {name}", annotated=True)
        return tag

    def list_snapshots(self):
        """List snapshots"""
        tags = self.git.list_tags("snapshot/*")
        return tags
