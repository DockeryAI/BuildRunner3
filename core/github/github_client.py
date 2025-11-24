"""
GitHub API Client - Wrapper around PyGithub

Provides safe, typed interface to GitHub operations.
"""

import os
from typing import Optional, List, Dict, Any
from pathlib import Path
from dataclasses import dataclass


@dataclass
class PullRequest:
    """Pull request information"""
    number: int
    title: str
    body: str
    state: str
    url: str
    head_ref: str
    base_ref: str


@dataclass
class Release:
    """Release information"""
    tag_name: str
    name: str
    body: str
    draft: bool
    prerelease: bool
    url: str


class GitHubClient:
    """Safe wrapper around GitHub API"""

    def __init__(self, token: Optional[str] = None, owner: Optional[str] = None, repo: Optional[str] = None):
        """
        Initialize GitHub client

        Args:
            token: GitHub personal access token (or GITHUB_TOKEN env var)
            owner: Repository owner
            repo: Repository name
        """
        self.token = token or os.getenv('GITHUB_TOKEN')
        if not self.token:
            # Try to use gh CLI authentication
            import subprocess
            try:
                result = subprocess.run(
                    ['gh', 'auth', 'token'],
                    capture_output=True,
                    text=True,
                    check=True
                )
                self.token = result.stdout.strip()
            except (subprocess.CalledProcessError, FileNotFoundError):
                pass

        self.owner = owner
        self.repo = repo
        self._github = None
        self._repo = None

    def _get_github(self):
        """Lazy load PyGithub"""
        if self._github is None:
            try:
                from github import Github
                if self.token:
                    self._github = Github(self.token)
                else:
                    # Use without authentication (rate limited)
                    self._github = Github()
            except ImportError:
                raise ImportError(
                    "PyGithub not installed. Install with: pip install PyGithub"
                )
        return self._github

    def _get_repo(self):
        """Get repository object"""
        if self._repo is None:
            if not self.owner or not self.repo:
                raise ValueError("Owner and repo must be set")
            gh = self._get_github()
            self._repo = gh.get_repo(f"{self.owner}/{self.repo}")
        return self._repo

    def set_repo(self, owner: str, repo: str):
        """Set repository"""
        self.owner = owner
        self.repo = repo
        self._repo = None  # Reset cached repo

    def create_pull_request(
        self,
        title: str,
        body: str,
        head: str,
        base: str = 'main',
        draft: bool = False
    ) -> PullRequest:
        """
        Create pull request

        Args:
            title: PR title
            body: PR description
            head: Head branch (feature branch)
            base: Base branch (usually main)
            draft: Create as draft PR

        Returns:
            PullRequest object
        """
        repo = self._get_repo()
        pr = repo.create_pull(
            title=title,
            body=body,
            head=head,
            base=base,
            draft=draft
        )

        return PullRequest(
            number=pr.number,
            title=pr.title,
            body=pr.body,
            state=pr.state,
            url=pr.html_url,
            head_ref=pr.head.ref,
            base_ref=pr.base.ref
        )

    def list_pull_requests(self, state: str = 'open') -> List[PullRequest]:
        """List pull requests"""
        repo = self._get_repo()
        prs = repo.get_pulls(state=state)

        return [
            PullRequest(
                number=pr.number,
                title=pr.title,
                body=pr.body,
                state=pr.state,
                url=pr.html_url,
                head_ref=pr.head.ref,
                base_ref=pr.base.ref
            )
            for pr in prs
        ]

    def merge_pull_request(self, number: int, merge_method: str = 'merge') -> bool:
        """
        Merge pull request

        Args:
            number: PR number
            merge_method: merge, squash, or rebase

        Returns:
            True if merged successfully
        """
        repo = self._get_repo()
        pr = repo.get_pull(number)
        result = pr.merge(merge_method=merge_method)
        return result.merged

    def create_release(
        self,
        tag: str,
        name: str,
        body: str,
        draft: bool = False,
        prerelease: bool = False
    ) -> Release:
        """
        Create GitHub release

        Args:
            tag: Git tag for release
            name: Release name
            body: Release notes
            draft: Create as draft
            prerelease: Mark as prerelease

        Returns:
            Release object
        """
        repo = self._get_repo()
        release = repo.create_git_release(
            tag=tag,
            name=name,
            message=body,
            draft=draft,
            prerelease=prerelease
        )

        return Release(
            tag_name=release.tag_name,
            name=release.title,
            body=release.body,
            draft=release.draft,
            prerelease=release.prerelease,
            url=release.html_url
        )

    def list_releases(self) -> List[Release]:
        """List releases"""
        repo = self._get_repo()
        releases = repo.get_releases()

        return [
            Release(
                tag_name=r.tag_name,
                name=r.title,
                body=r.body,
                draft=r.draft,
                prerelease=r.prerelease,
                url=r.html_url
            )
            for r in releases
        ]

    def create_issue(
        self,
        title: str,
        body: str,
        labels: Optional[List[str]] = None,
        assignees: Optional[List[str]] = None
    ) -> int:
        """
        Create GitHub issue

        Returns:
            Issue number
        """
        repo = self._get_repo()
        issue = repo.create_issue(
            title=title,
            body=body,
            labels=labels or [],
            assignees=assignees or []
        )
        return issue.number

    def close_issue(self, number: int) -> None:
        """Close issue"""
        repo = self._get_repo()
        issue = repo.get_issue(number)
        issue.edit(state='closed')

    def setup_branch_protection(
        self,
        branch: str = 'main',
        require_reviews: int = 1,
        require_status_checks: bool = True,
        status_checks: Optional[List[str]] = None
    ) -> None:
        """
        Setup branch protection rules

        Args:
            branch: Branch to protect
            require_reviews: Number of required reviews
            require_status_checks: Require CI to pass
            status_checks: List of required status check names
        """
        repo = self._get_repo()
        branch_obj = repo.get_branch(branch)

        # Setup protection
        branch_obj.edit_protection(
            required_approving_review_count=require_reviews,
            enforce_admins=True,
            require_code_owner_reviews=False,
            required_linear_history=True,
            allow_force_pushes=False,
            allow_deletions=False
        )

        if require_status_checks and status_checks:
            branch_obj.edit_required_status_checks(
                strict=True,
                contexts=status_checks
            )

    def get_branch_protection_status(self, branch: str = 'main') -> Dict[str, Any]:
        """Get branch protection status"""
        repo = self._get_repo()
        try:
            branch_obj = repo.get_branch(branch)
            protection = branch_obj.get_protection()

            return {
                'protected': True,
                'required_reviews': protection.required_pull_request_reviews.required_approving_review_count if protection.required_pull_request_reviews else 0,
                'enforce_admins': protection.enforce_admins.enabled if protection.enforce_admins else False,
                'required_status_checks': [c for c in protection.required_status_checks.contexts] if protection.required_status_checks else []
            }
        except Exception:
            return {'protected': False}

    def is_authenticated(self) -> bool:
        """Check if client is authenticated"""
        if not self.token:
            return False
        try:
            gh = self._get_github()
            gh.get_user().login
            return True
        except Exception:
            return False
