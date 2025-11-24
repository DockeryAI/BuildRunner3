"""PR Manager"""
from pathlib import Path
from typing import Optional
from .git_client import GitClient
from .github_client import GitHubClient

class PRManager:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)
        owner, repo = self.git.extract_repo_info()
        self.github = GitHubClient(owner=owner, repo=repo)
    
    def create_pr(self, title: Optional[str] = None, draft: bool = False):
        """Create PR"""
        current = self.git.current_branch()
        if not title:
            title = f"Feature: {current}"
        body = "Auto-generated PR"
        return self.github.create_pull_request(title, body, current, draft=draft)
