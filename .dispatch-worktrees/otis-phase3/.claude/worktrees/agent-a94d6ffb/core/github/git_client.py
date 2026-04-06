"""
Git Client - Wrapper around git commands

Provides safe, typed interface to git operations.
"""

import subprocess
import re
import os
from pathlib import Path
from typing import Optional, List, Tuple
from dataclasses import dataclass


@dataclass
class GitStatus:
    """Git repository status"""

    branch: str
    is_clean: bool
    staged_files: List[str]
    unstaged_files: List[str]
    untracked_files: List[str]
    commits_ahead: int
    commits_behind: int


class GitClient:
    """Safe wrapper around git commands"""

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize Git client

        Args:
            repo_path: Path to git repository (default: current directory)
        """
        self.repo_path = repo_path or Path.cwd()
        if not self._is_git_repo():
            raise ValueError(f"Not a git repository: {self.repo_path}")

    def _is_git_repo(self) -> bool:
        """Check if directory is a git repository"""
        try:
            subprocess.run(
                ["git", "rev-parse", "--git-dir"],
                cwd=self.repo_path,
                capture_output=True,
                check=True,
            )
            return True
        except subprocess.CalledProcessError:
            return False

    def _run(self, *args, check=True, capture_output=True) -> subprocess.CompletedProcess:
        """Run git command"""
        # Pass current environment to subprocess so BR_GITHUB_PUSH is inherited by hooks
        try:
            return subprocess.run(
                ["git"] + list(args),
                cwd=self.repo_path,
                capture_output=capture_output,
                text=True,
                check=check,
                env=os.environ.copy(),  # Inherit parent environment including BR_GITHUB_PUSH
            )
        except subprocess.CalledProcessError as e:
            # Include stderr in error message for better debugging
            error_msg = f"git {' '.join(args)} failed"
            if e.stderr:
                error_msg += f"\nSTDERR: {e.stderr}"
            if e.stdout:
                error_msg += f"\nSTDOUT: {e.stdout}"
            raise RuntimeError(error_msg) from e

    def current_branch(self) -> str:
        """Get current branch name"""
        result = self._run("branch", "--show-current")
        return result.stdout.strip()

    def create_branch(self, name: str, checkout: bool = True) -> None:
        """
        Create new branch

        Args:
            name: Branch name
            checkout: Whether to checkout the branch
        """
        if checkout:
            self._run("checkout", "-b", name)
        else:
            self._run("branch", name)

    def checkout(self, branch: str) -> None:
        """Checkout branch"""
        self._run("checkout", branch)

    def branch_exists(self, name: str) -> bool:
        """Check if branch exists"""
        result = self._run("branch", "--list", name, check=False)
        return bool(result.stdout.strip())

    def list_branches(self, remote: bool = False) -> List[str]:
        """List branches"""
        if remote:
            result = self._run("branch", "-r")
        else:
            result = self._run("branch")

        branches = []
        for line in result.stdout.splitlines():
            # Remove * and whitespace
            branch = line.strip().lstrip("* ").strip()
            if branch and not branch.startswith("("):
                branches.append(branch)
        return branches

    def delete_branch(self, name: str, force: bool = False) -> None:
        """Delete branch"""
        flag = "-D" if force else "-d"
        self._run("branch", flag, name)

    def get_status(self) -> GitStatus:
        """Get detailed repository status"""
        # Get current branch
        branch = self.current_branch()

        # Get status
        result = self._run("status", "--porcelain")
        staged = []
        unstaged = []
        untracked = []

        for line in result.stdout.splitlines():
            status = line[:2]
            file = line[3:]

            if status[0] != " " and status[0] != "?":
                staged.append(file)
            if status[1] != " ":
                unstaged.append(file)
            if status[0] == "?":
                untracked.append(file)

        # Get ahead/behind counts
        try:
            result = self._run(
                "rev-list", "--left-right", "--count", f"origin/{branch}...HEAD", check=False
            )
            if result.returncode == 0:
                parts = result.stdout.strip().split()
                behind = int(parts[0]) if len(parts) > 0 else 0
                ahead = int(parts[1]) if len(parts) > 1 else 0
            else:
                behind = 0
                ahead = 0
        except Exception:
            behind = 0
            ahead = 0

        return GitStatus(
            branch=branch,
            is_clean=not (staged or unstaged or untracked),
            staged_files=staged,
            unstaged_files=unstaged,
            untracked_files=untracked,
            commits_ahead=ahead,
            commits_behind=behind,
        )

    def fetch(self, remote: str = "origin", branch: Optional[str] = None) -> None:
        """Fetch from remote"""
        if branch:
            self._run("fetch", remote, branch)
        else:
            self._run("fetch", remote)

    def is_behind(self, remote_branch: str = "origin/main") -> Tuple[bool, int]:
        """
        Check if current branch is behind remote

        Returns:
            (is_behind, commit_count)
        """
        self.fetch()
        result = self._run("rev-list", "--count", f"HEAD..{remote_branch}", check=False)
        if result.returncode == 0:
            count = int(result.stdout.strip())
            return count > 0, count
        return False, 0

    def has_conflicts_with(self, target_branch: str) -> Tuple[bool, List[str]]:
        """
        Check if merging target branch would cause conflicts

        Returns:
            (has_conflicts, conflicting_files)
        """
        # Simulate merge without actually merging
        result = self._run("merge", "--no-commit", "--no-ff", target_branch, check=False)

        if result.returncode != 0:
            # Get conflicting files
            status_result = self._run("diff", "--name-only", "--diff-filter=U")
            conflicts = [f.strip() for f in status_result.stdout.splitlines() if f.strip()]

            # Abort merge
            self._run("merge", "--abort", check=False)

            return True, conflicts

        # Abort successful merge
        self._run("merge", "--abort", check=False)
        return False, []

    def create_tag(self, tag: str, message: Optional[str] = None, annotated: bool = True) -> None:
        """Create git tag"""
        if annotated and message:
            self._run("tag", "-a", tag, "-m", message)
        else:
            self._run("tag", tag)

    def push_tag(self, tag: str, remote: str = "origin") -> None:
        """Push tag to remote"""
        self._run("push", remote, tag)

    def list_tags(self, pattern: Optional[str] = None) -> List[str]:
        """List tags"""
        if pattern:
            result = self._run("tag", "--list", pattern)
        else:
            result = self._run("tag", "--list")
        return [t.strip() for t in result.stdout.splitlines() if t.strip()]

    def get_commits_since_tag(self, tag: str) -> List[str]:
        """Get commit messages since tag"""
        result = self._run("log", f"{tag}..HEAD", "--pretty=format:%s")
        return [line.strip() for line in result.stdout.splitlines() if line.strip()]

    def add(self, *files: str) -> None:
        """Stage files"""
        self._run("add", *files)

    def commit(self, message: str) -> None:
        """Create commit"""
        self._run("commit", "-m", message)

    def push(
        self, remote: str = "origin", branch: Optional[str] = None, set_upstream: bool = False
    ) -> None:
        """Push to remote"""
        args = ["push"]
        if set_upstream:
            args.append("-u")
        args.append(remote)
        if branch:
            args.append(branch)
        self._run(*args)

    def get_remote_url(self, remote: str = "origin") -> str:
        """Get remote URL"""
        result = self._run("remote", "get-url", remote)
        return result.stdout.strip()

    def extract_repo_info(self) -> Tuple[str, str]:
        """
        Extract owner and repo name from remote URL

        Returns:
            (owner, repo)
        """
        url = self.get_remote_url()

        # Match github.com URLs
        # https://github.com/owner/repo.git
        # git@github.com:owner/repo.git
        match = re.search(r"github\.com[:/]([^/]+)/([^/\.]+)", url)
        if match:
            return match.group(1), match.group(2)

        raise ValueError(f"Could not extract repo info from URL: {url}")
