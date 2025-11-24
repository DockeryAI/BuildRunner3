"""Release Manager"""
from pathlib import Path
from typing import Optional
from .git_client import GitClient
from .github_client import GitHubClient
from .version_manager import VersionManager
from .changelog_generator import ChangelogGenerator

class ReleaseManager:
    def __init__(self, repo_path: Optional[Path] = None):
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)
        self.version_mgr = VersionManager(self.repo_path)
        self.changelog_gen = ChangelogGenerator(self.repo_path)
        owner, repo = self.git.extract_repo_info()
        self.github = GitHubClient(owner=owner, repo=repo)
    
    def create_release(self, bump_type: str = 'patch') -> str:
        """Create release"""
        old_version = self.version_mgr.get_current_version()
        new_version = self.version_mgr.bump_version(bump_type)
        
        # Update files
        self.version_mgr.update_version_files(new_version)
        
        # Create tag
        tag = f'v{new_version}'
        self.git.create_tag(tag, f'Release {new_version}')
        
        # Generate changelog
        changelog = self.changelog_gen.generate(f'v{old_version}')
        
        # Create GitHub release
        try:
            self.github.create_release(tag, f'Release {new_version}', changelog)
        except Exception:
            pass  # GitHub API might not be available
        
        return new_version
