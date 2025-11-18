"""
Git Migration Handler

Handles git operations during migration:
- Preserve commit history
- Create migration commits
- Tag migration point
- Enable rollback
"""

from pathlib import Path
from typing import Optional, List
from dataclasses import dataclass
from datetime import datetime
import subprocess
import shutil


@dataclass
class GitMigrationResult:
    """Result of git migration operations"""
    success: bool
    commit_hash: Optional[str] = None
    tag_name: Optional[str] = None
    backup_created: bool = False
    backup_path: Optional[Path] = None
    errors: List[str] = None

    def __post_init__(self):
        if self.errors is None:
            self.errors = []


class GitMigrationHandler:
    """
    Handle git operations during migration

    Operations:
    - Preserve commit history
    - Create atomic migration commit
    - Tag migration point for rollback
    - Create git-tracked backups
    """

    def __init__(self, project_path: Path):
        """
        Initialize git handler

        Args:
            project_path: Path to project (must be git repository)
        """
        self.project_path = Path(project_path)
        self.git_dir = self.project_path / ".git"

    def is_git_repository(self) -> bool:
        """
        Check if project is a git repository

        Returns:
            True if git repository exists
        """
        return self.git_dir.exists() and self.git_dir.is_dir()

    def create_pre_migration_backup(self) -> GitMigrationResult:
        """
        Create backup before migration

        Creates:
        - Git tag marking pre-migration state
        - Backup directory with current files

        Returns:
            GitMigrationResult with backup details
        """
        result = GitMigrationResult(success=False)

        if not self.is_git_repository():
            result.errors.append("Not a git repository")
            return result

        # Create timestamped tag
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag_name = f"pre-migration-v2.0-{timestamp}"

        # Tag current state
        tag_success, tag_hash = self._create_git_tag(tag_name, "Pre-migration backup - BuildRunner 2.0")

        if not tag_success:
            result.errors.append("Failed to create backup tag")
            return result

        result.tag_name = tag_name
        result.commit_hash = tag_hash

        # Create file backup
        backup_dir = self.project_path / ".buildrunner" / "backups" / f"v2_{timestamp}"
        backup_dir.mkdir(parents=True, exist_ok=True)

        # Backup critical files
        files_to_backup = [
            ".runner/hrpo.json",
            ".runner/governance.json",
            ".runner/config.json",
        ]

        for file_path in files_to_backup:
            source = self.project_path / file_path
            if source.exists():
                dest = backup_dir / file_path
                dest.parent.mkdir(parents=True, exist_ok=True)
                try:
                    shutil.copy2(source, dest)
                except Exception as e:
                    result.errors.append(f"Failed to backup {file_path}: {e}")

        result.backup_path = backup_dir
        result.backup_created = True
        result.success = True

        return result

    def create_migration_commit(
        self,
        message: Optional[str] = None,
        files_to_add: Optional[List[str]] = None
    ) -> GitMigrationResult:
        """
        Create atomic migration commit

        Args:
            message: Custom commit message
            files_to_add: Specific files to add (or all if None)

        Returns:
            GitMigrationResult with commit details
        """
        result = GitMigrationResult(success=False)

        if not self.is_git_repository():
            result.errors.append("Not a git repository")
            return result

        # Default commit message
        if not message:
            message = f"""Migrate from BuildRunner 2.0 to 3.0

Automated migration performed on {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

Changes:
- Converted HRPO → features.json
- Migrated governance.json → .buildrunner/governance.yaml
- Created .buildrunner directory structure
- Preserved all v2.0 data in backups

Migration can be rolled back using:
git revert HEAD
# or
br migrate rollback
"""

        # Stage files
        if files_to_add:
            for file_path in files_to_add:
                self._run_git_command(["add", file_path])
        else:
            # Stage new migration files
            self._run_git_command(["add", "features.json"])
            self._run_git_command(["add", ".buildrunner/"])

        # Create commit
        success, output = self._run_git_command(["commit", "-m", message])

        if not success:
            result.errors.append(f"Failed to create commit: {output}")
            return result

        # Get commit hash
        success, commit_hash = self._run_git_command(["rev-parse", "HEAD"])

        if success:
            result.commit_hash = commit_hash.strip()

        result.success = True

        return result

    def tag_migration_point(self, version: str = "3.0.0") -> GitMigrationResult:
        """
        Tag the migration completion point

        Args:
            version: Version tag to create

        Returns:
            GitMigrationResult with tag details
        """
        result = GitMigrationResult(success=False)

        if not self.is_git_repository():
            result.errors.append("Not a git repository")
            return result

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        tag_name = f"migration-v{version}-{timestamp}"

        message = f"BuildRunner {version} migration complete"

        success, commit_hash = self._create_git_tag(tag_name, message)

        if not success:
            result.errors.append("Failed to create migration tag")
            return result

        result.tag_name = tag_name
        result.commit_hash = commit_hash
        result.success = True

        return result

    def rollback_migration(self, backup_tag: Optional[str] = None) -> GitMigrationResult:
        """
        Rollback migration to pre-migration state

        Args:
            backup_tag: Specific tag to roll back to (latest if None)

        Returns:
            GitMigrationResult with rollback details
        """
        result = GitMigrationResult(success=False)

        if not self.is_git_repository():
            result.errors.append("Not a git repository")
            return result

        # Find backup tag if not specified
        if not backup_tag:
            backup_tag = self._find_latest_backup_tag()

        if not backup_tag:
            result.errors.append("No backup tag found for rollback")
            return result

        # Reset to backup tag
        success, output = self._run_git_command(["reset", "--hard", backup_tag])

        if not success:
            result.errors.append(f"Failed to rollback: {output}")
            return result

        result.tag_name = backup_tag
        result.success = True

        return result

    def preserve_history(self) -> bool:
        """
        Verify git history is intact

        Returns:
            True if history preserved
        """
        if not self.is_git_repository():
            return False

        # Check that we can access history
        success, _ = self._run_git_command(["log", "--oneline", "-10"])

        return success

    def _create_git_tag(self, tag_name: str, message: str) -> tuple[bool, Optional[str]]:
        """
        Create annotated git tag

        Args:
            tag_name: Name of tag
            message: Tag annotation message

        Returns:
            (success, commit_hash) tuple
        """
        # Create tag
        success, output = self._run_git_command(["tag", "-a", tag_name, "-m", message])

        if not success:
            return False, None

        # Get current commit hash
        success, commit_hash = self._run_git_command(["rev-parse", "HEAD"])

        if success:
            return True, commit_hash.strip()

        return True, None

    def _find_latest_backup_tag(self) -> Optional[str]:
        """
        Find the most recent pre-migration backup tag

        Returns:
            Tag name or None
        """
        success, output = self._run_git_command(["tag", "-l", "pre-migration-*"])

        if not success or not output:
            return None

        tags = output.strip().split("\n")
        if tags:
            # Return most recent (tags are timestamped)
            return sorted(tags)[-1]

        return None

    def _run_git_command(self, args: List[str], timeout: int = 30) -> tuple[bool, str]:
        """
        Run git command

        Args:
            args: Git command arguments
            timeout: Command timeout in seconds

        Returns:
            (success, output) tuple
        """
        try:
            result = subprocess.run(
                ["git"] + args,
                cwd=self.project_path,
                capture_output=True,
                text=True,
                timeout=timeout
            )

            success = result.returncode == 0
            output = result.stdout if success else result.stderr

            return success, output.strip()
        except subprocess.TimeoutExpired:
            return False, f"Command timed out after {timeout}s"
        except Exception as e:
            return False, str(e)

    def get_current_commit(self) -> Optional[str]:
        """
        Get current commit hash

        Returns:
            Commit hash or None
        """
        success, commit_hash = self._run_git_command(["rev-parse", "HEAD"])

        if success:
            return commit_hash.strip()

        return None

    def get_commit_message(self, commit_hash: str) -> Optional[str]:
        """
        Get commit message for specific commit

        Args:
            commit_hash: Commit to query

        Returns:
            Commit message or None
        """
        success, message = self._run_git_command(["log", "--format=%B", "-n", "1", commit_hash])

        if success:
            return message.strip()

        return None
