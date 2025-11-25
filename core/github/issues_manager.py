"""Issues Manager"""

from pathlib import Path
from typing import Optional
from .git_client import GitClient
from .github_client import GitHubClient


class IssuesManager:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)
        owner, repo = self.git.extract_repo_info()
        self.github = GitHubClient(owner=owner, repo=repo)

    def create_issue(self, title: str, body: str):
        """Create issue"""
        return self.github.create_issue(title, body)
