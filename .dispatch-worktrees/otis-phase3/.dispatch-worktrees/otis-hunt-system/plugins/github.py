"""
GitHub Plugin for BuildRunner 3.0

Syncs issues to features, creates PRs from CLI, updates issue status.
Because manually managing GitHub is for people with too much time.
"""

import os
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

try:
    from github import Github, GithubException
    from github.Repository import Repository
    from github.Issue import Issue
    from github.PullRequest import PullRequest

    GITHUB_AVAILABLE = True
except ImportError:
    GITHUB_AVAILABLE = False
    Github = None
    GithubException = Exception

from dotenv import load_dotenv


class GitHubPlugin:
    """
    GitHub integration plugin.

    Optional plugin - system works fine without it.
    When enabled, syncs features with GitHub issues and manages PRs.
    """

    def __init__(self, token: Optional[str] = None, repo: Optional[str] = None):
        """
        Initialize GitHub plugin.

        Args:
            token: GitHub personal access token (or uses GITHUB_TOKEN env var)
            repo: Repository name in format "owner/repo" (or uses GITHUB_REPO env var)
        """
        load_dotenv()

        self.enabled = GITHUB_AVAILABLE
        self.token = token or os.getenv("GITHUB_TOKEN")
        self.repo_name = repo or os.getenv("GITHUB_REPO")
        self.client: Optional[Any] = None
        self.repo: Optional[Any] = None

        if not GITHUB_AVAILABLE:
            print("ℹ️  GitHub plugin disabled: PyGithub not installed")
            print("   Install with: pip install PyGithub")
            return

        if not self.token:
            print("ℹ️  GitHub plugin disabled: GITHUB_TOKEN not set")
            print("   Set token: export GITHUB_TOKEN=ghp_xxxxx")
            self.enabled = False
            return

        if not self.repo_name:
            print("ℹ️  GitHub plugin disabled: GITHUB_REPO not set")
            print("   Set repo: export GITHUB_REPO=owner/repo")
            self.enabled = False
            return

        try:
            self.client = Github(self.token)
            self.repo = self.client.get_repo(self.repo_name)
            print(f"✅ GitHub plugin enabled for {self.repo_name}")
        except Exception as e:
            print(f"⚠️  GitHub plugin initialization failed: {e}")
            self.enabled = False

    def is_enabled(self) -> bool:
        """Check if plugin is enabled and configured"""
        return self.enabled and self.client is not None

    def sync_issues_to_features(self, label: str = "feature") -> List[Dict[str, Any]]:
        """
        Sync GitHub issues with 'feature' label to BuildRunner features.

        Args:
            label: GitHub label to filter issues

        Returns:
            List of synced features
        """
        if not self.is_enabled():
            print("GitHub plugin not enabled - skipping issue sync")
            return []

        try:
            issues = self.repo.get_issues(state="open", labels=[label])
            features = []

            for issue in issues:
                feature = {
                    "id": f"gh-{issue.number}",
                    "name": issue.title,
                    "description": issue.body or "No description",
                    "status": self._map_issue_state(issue),
                    "priority": self._extract_priority(issue.labels),
                    "github_issue": issue.number,
                    "github_url": issue.html_url,
                }
                features.append(feature)

            print(f"✅ Synced {len(features)} GitHub issues to features")
            return features

        except Exception as e:
            print(f"⚠️  Failed to sync GitHub issues: {e}")
            return []

    def create_feature_from_issue(self, issue_number: int) -> Optional[Dict[str, Any]]:
        """
        Create a BuildRunner feature from a GitHub issue.

        Args:
            issue_number: GitHub issue number

        Returns:
            Feature dictionary or None
        """
        if not self.is_enabled():
            return None

        try:
            issue = self.repo.get_issue(issue_number)

            feature = {
                "id": f"gh-{issue.number}",
                "name": issue.title,
                "description": issue.body or "No description",
                "status": self._map_issue_state(issue),
                "priority": self._extract_priority(issue.labels),
                "github_issue": issue.number,
                "github_url": issue.html_url,
            }

            return feature

        except Exception as e:
            print(f"⚠️  Failed to create feature from issue #{issue_number}: {e}")
            return None

    def update_issue_status(
        self, issue_number: int, status: str, comment: Optional[str] = None
    ) -> bool:
        """
        Update GitHub issue status based on feature status.

        Args:
            issue_number: GitHub issue number
            status: Feature status (planned, in_progress, complete)
            comment: Optional comment to add to issue

        Returns:
            True if successful, False otherwise
        """
        if not self.is_enabled():
            return False

        try:
            issue = self.repo.get_issue(issue_number)

            # Add status label
            status_label = f"status:{status}"
            current_labels = [label.name for label in issue.labels]

            # Remove old status labels
            new_labels = [l for l in current_labels if not l.startswith("status:")]
            new_labels.append(status_label)

            issue.set_labels(*new_labels)

            # Add comment if provided
            if comment:
                issue.create_comment(comment)

            # Close issue if complete
            if status == "complete":
                issue.edit(state="closed")
                print(f"✅ Closed issue #{issue_number}")

            print(f"✅ Updated issue #{issue_number} status to {status}")
            return True

        except Exception as e:
            print(f"⚠️  Failed to update issue #{issue_number}: {e}")
            return False

    def create_pr(
        self, title: str, body: str, head_branch: str, base_branch: str = "main"
    ) -> Optional[str]:
        """
        Create a pull request from CLI.

        Args:
            title: PR title
            body: PR description
            head_branch: Source branch
            base_branch: Target branch (default: main)

        Returns:
            PR URL if successful, None otherwise
        """
        if not self.is_enabled():
            print("GitHub plugin not enabled - cannot create PR")
            return None

        try:
            pr = self.repo.create_pull(title=title, body=body, head=head_branch, base=base_branch)

            print(f"✅ Created PR #{pr.number}: {pr.html_url}")
            return pr.html_url

        except Exception as e:
            print(f"⚠️  Failed to create PR: {e}")
            return None

    def create_pr_from_feature(
        self, feature: Dict[str, Any], branch: str, base_branch: str = "main"
    ) -> Optional[str]:
        """
        Create a PR for a completed feature.

        Args:
            feature: Feature dictionary
            branch: Source branch
            base_branch: Target branch

        Returns:
            PR URL if successful
        """
        if not self.is_enabled():
            return None

        title = f"feat: {feature['name']}"

        body = f"""## {feature['name']}

{feature.get('description', 'No description')}

**Status:** {feature.get('status', 'unknown')}
**Priority:** {feature.get('priority', 'medium')}

🤖 Generated by BuildRunner 3.0

"""

        # Link to issue if exists
        if "github_issue" in feature:
            body += f"\nCloses #{feature['github_issue']}\n"

        return self.create_pr(title, body, branch, base_branch)

    def add_pr_comment(self, pr_number: int, comment: str) -> bool:
        """
        Add a comment to a pull request.

        Args:
            pr_number: PR number
            comment: Comment text

        Returns:
            True if successful
        """
        if not self.is_enabled():
            return False

        try:
            pr = self.repo.get_pull(pr_number)
            pr.create_issue_comment(comment)
            print(f"✅ Added comment to PR #{pr_number}")
            return True
        except Exception as e:
            print(f"⚠️  Failed to comment on PR #{pr_number}: {e}")
            return False

    def get_open_prs(self) -> List[Dict[str, Any]]:
        """
        Get list of open pull requests.

        Returns:
            List of PR dictionaries
        """
        if not self.is_enabled():
            return []

        try:
            prs = self.repo.get_pulls(state="open")
            result = []

            for pr in prs:
                result.append(
                    {
                        "number": pr.number,
                        "title": pr.title,
                        "url": pr.html_url,
                        "branch": pr.head.ref,
                        "base": pr.base.ref,
                        "state": pr.state,
                        "created_at": pr.created_at.isoformat(),
                    }
                )

            return result
        except Exception as e:
            print(f"⚠️  Failed to get open PRs: {e}")
            return []

    def _map_issue_state(self, issue: Any) -> str:
        """Map GitHub issue state to feature status"""
        if issue.state == "closed":
            return "complete"

        # Check for status labels
        for label in issue.labels:
            if label.name == "status:in_progress" or label.name == "in progress":
                return "in_progress"

        return "planned"

    def _extract_priority(self, labels: Any) -> str:
        """Extract priority from issue labels"""
        priority_map = {
            "priority:critical": "critical",
            "priority:high": "high",
            "priority:medium": "medium",
            "priority:low": "low",
            "critical": "critical",
            "high": "high",
            "medium": "medium",
            "low": "low",
        }

        for label in labels:
            if label.name in priority_map:
                return priority_map[label.name]

        return "medium"


# Global plugin instance
_github_plugin: Optional[GitHubPlugin] = None


def get_github_plugin() -> GitHubPlugin:
    """
    Get global GitHub plugin instance.

    Returns:
        GitHubPlugin instance
    """
    global _github_plugin
    if _github_plugin is None:
        _github_plugin = GitHubPlugin()
    return _github_plugin
