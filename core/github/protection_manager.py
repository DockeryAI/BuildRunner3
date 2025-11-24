"""Protection Manager"""
from pathlib import Path
from typing import Optional
from .git_client import GitClient
from .github_client import GitHubClient

class ProtectionManager:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)
        owner, repo = self.git.extract_repo_info()
        self.github = GitHubClient(owner=owner, repo=repo)
    
    def setup_protection(self, branch: str = 'main'):
        """Setup branch protection"""
        try:
            self.github.setup_branch_protection(branch)
            return True
        except Exception:
            return False
