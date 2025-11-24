"""
Conflict Detector - Detect merge conflicts before they happen
"""

from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass

from .git_client import GitClient


@dataclass
class ConflictInfo:
    """Conflict information"""
    has_conflicts: bool
    conflicting_files: List[str]
    commits_behind: int
    can_auto_resolve: bool


class ConflictDetector:
    """Detect and analyze merge conflicts"""

    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)

    def check_conflicts(self, target_branch: str = 'origin/main') -> ConflictInfo:
        """
        Check if merging target branch would cause conflicts

        Args:
            target_branch: Branch to check conflicts with

        Returns:
            ConflictInfo
        """
        # Fetch latest
        self.git.fetch()

        # Check if behind
        is_behind, count = self.git.is_behind(target_branch)

        if not is_behind:
            return ConflictInfo(
                has_conflicts=False,
                conflicting_files=[],
                commits_behind=0,
                can_auto_resolve=True
            )

        # Check for conflicts
        has_conflicts, files = self.git.has_conflicts_with(target_branch)

        return ConflictInfo(
            has_conflicts=has_conflicts,
            conflicting_files=files,
            commits_behind=count,
            can_auto_resolve=not has_conflicts
        )

    def sync_with_main(self, rebase: bool = True) -> Tuple[bool, str]:
        """
        Sync current branch with main

        Args:
            rebase: If True, rebase. If False, merge.

        Returns:
            (success, message)
        """
        current = self.git.current_branch()
        if current == 'main':
            return False, "Already on main branch"

        # Check for conflicts first
        info = self.check_conflicts()
        if info.has_conflicts:
            return False, f"Would cause conflicts in {len(info.conflicting_files)} files"

        # Fetch latest
        self.git.fetch('origin', 'main')

        try:
            if rebase:
                # Rebase on main
                import subprocess
                result = subprocess.run(
                    ['git', 'rebase', 'origin/main'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return True, f"Rebased {info.commits_behind} commits from main"
            else:
                # Merge main
                import subprocess
                result = subprocess.run(
                    ['git', 'merge', 'origin/main'],
                    cwd=self.repo_path,
                    capture_output=True,
                    text=True,
                    check=True
                )
                return True, f"Merged {info.commits_behind} commits from main"
        except subprocess.CalledProcessError as e:
            return False, f"Sync failed: {e.stderr}"

    def get_behind_status(self) -> str:
        """Get human-readable behind status"""
        info = self.check_conflicts()

        if info.commits_behind == 0:
            return "✅ Up to date with main"
        elif info.has_conflicts:
            return f"❌ {info.commits_behind} commits behind with conflicts in {len(info.conflicting_files)} files"
        else:
            return f"⚠️  {info.commits_behind} commits behind (can auto-sync)"
