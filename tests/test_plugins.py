"""
Tests for BuildRunner 3.0 Plugins

Testing optional integrations that may or may not be installed.
Because mocking third-party APIs is way more fun than using them.
"""

import pytest
from unittest.mock import Mock, MagicMock, patch
from pathlib import Path
import tempfile
import os

# Import plugins - they handle missing dependencies gracefully
from plugins.github import GitHubPlugin, get_github_plugin, GITHUB_AVAILABLE
from plugins.notion import NotionPlugin, get_notion_plugin, NOTION_AVAILABLE
from plugins.slack import SlackPlugin, get_slack_plugin, SLACK_AVAILABLE


# ============================================================================
# GitHub Plugin Tests
# ============================================================================


class TestGitHubPlugin:
    """Tests for GitHub plugin"""

    def test_github_plugin_without_dependencies(self):
        """Test that plugin gracefully handles missing PyGithub"""
        if not GITHUB_AVAILABLE:
            plugin = GitHubPlugin()
            assert not plugin.is_enabled()
            assert plugin.client is None

    def test_github_plugin_without_token(self):
        """Test that plugin requires GitHub token"""
        with patch.dict(os.environ, {}, clear=True):
            plugin = GitHubPlugin()
            if GITHUB_AVAILABLE:
                assert not plugin.is_enabled()

    def test_github_plugin_without_repo(self):
        """Test that plugin requires repository name"""
        with patch.dict(os.environ, {"GITHUB_TOKEN": "fake_token"}, clear=True):
            plugin = GitHubPlugin()
            if GITHUB_AVAILABLE:
                assert not plugin.is_enabled()

    @patch("plugins.github.Github")
    def test_github_plugin_initialization_success(self, mock_github):
        """Test successful GitHub plugin initialization"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_repo = Mock()
        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            assert plugin.is_enabled()
            assert plugin.repo is not None

    @patch("plugins.github.Github")
    def test_sync_issues_to_features(self, mock_github):
        """Test syncing GitHub issues to features"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        # Mock issue
        mock_issue = Mock()
        mock_issue.number = 123
        mock_issue.title = "Test Feature"
        mock_issue.body = "Test description"
        mock_issue.state = "open"
        mock_issue.html_url = "https://github.com/owner/repo/issues/123"
        mock_issue.labels = []

        mock_repo = Mock()
        mock_repo.get_issues.return_value = [mock_issue]

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            features = plugin.sync_issues_to_features()

            assert len(features) == 1
            assert features[0]["id"] == "gh-123"
            assert features[0]["name"] == "Test Feature"
            assert features[0]["github_issue"] == 123

    @patch("plugins.github.Github")
    def test_create_feature_from_issue(self, mock_github):
        """Test creating feature from GitHub issue"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_label = Mock()
        mock_label.name = "priority:high"

        mock_issue = Mock()
        mock_issue.number = 456
        mock_issue.title = "New Feature"
        mock_issue.body = "Feature description"
        mock_issue.state = "open"
        mock_issue.html_url = "https://github.com/owner/repo/issues/456"
        mock_issue.labels = [mock_label]

        mock_repo = Mock()
        mock_repo.get_issue.return_value = mock_issue

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            feature = plugin.create_feature_from_issue(456)

            assert feature is not None
            assert feature["id"] == "gh-456"
            assert feature["priority"] == "high"

    @patch("plugins.github.Github")
    def test_update_issue_status(self, mock_github):
        """Test updating GitHub issue status"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_issue = Mock()
        mock_issue.labels = []

        mock_repo = Mock()
        mock_repo.get_issue.return_value = mock_issue

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            result = plugin.update_issue_status(123, "in_progress", "Working on it")

            assert result is True
            mock_issue.set_labels.assert_called_once()
            mock_issue.create_comment.assert_called_once_with("Working on it")

    @patch("plugins.github.Github")
    def test_create_pr(self, mock_github):
        """Test creating pull request"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_pr = Mock()
        mock_pr.number = 789
        mock_pr.html_url = "https://github.com/owner/repo/pull/789"

        mock_repo = Mock()
        mock_repo.create_pull.return_value = mock_pr

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            pr_url = plugin.create_pr("Test PR", "PR body", "feature-branch")

            assert pr_url == "https://github.com/owner/repo/pull/789"
            mock_repo.create_pull.assert_called_once()

    @patch("plugins.github.Github")
    def test_create_pr_from_feature(self, mock_github):
        """Test creating PR from feature dict"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_pr = Mock()
        mock_pr.number = 101
        mock_pr.html_url = "https://github.com/owner/repo/pull/101"

        mock_repo = Mock()
        mock_repo.create_pull.return_value = mock_pr

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        feature = {
            "name": "Test Feature",
            "description": "Test description",
            "status": "complete",
            "priority": "high",
            "github_issue": 123,
        }

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            pr_url = plugin.create_pr_from_feature(feature, "feature-branch")

            assert pr_url is not None
            # Verify PR body contains issue reference
            call_args = mock_repo.create_pull.call_args
            assert "Closes #123" in call_args[1]["body"]

    @patch("plugins.github.Github")
    def test_get_open_prs(self, mock_github):
        """Test getting open pull requests"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_pr = Mock()
        mock_pr.number = 1
        mock_pr.title = "Test PR"
        mock_pr.html_url = "https://github.com/owner/repo/pull/1"
        mock_pr.head = Mock(ref="feature")
        mock_pr.base = Mock(ref="main")
        mock_pr.state = "open"
        mock_pr.created_at = Mock()
        mock_pr.created_at.isoformat.return_value = "2025-01-01T00:00:00"

        mock_repo = Mock()
        mock_repo.get_pulls.return_value = [mock_pr]

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            prs = plugin.get_open_prs()

            assert len(prs) == 1
            assert prs[0]["number"] == 1
            assert prs[0]["title"] == "Test PR"


# ============================================================================
# Notion Plugin Tests
# ============================================================================


class TestNotionPlugin:
    """Tests for Notion plugin"""

    def test_notion_plugin_without_dependencies(self):
        """Test that plugin gracefully handles missing notion-client"""
        if not NOTION_AVAILABLE:
            plugin = NotionPlugin()
            assert not plugin.is_enabled()
            assert plugin.client is None

    def test_notion_plugin_without_token(self):
        """Test that plugin requires Notion token"""
        with patch.dict(os.environ, {}, clear=True):
            plugin = NotionPlugin()
            if NOTION_AVAILABLE:
                assert not plugin.is_enabled()

    def test_notion_plugin_without_database_id(self):
        """Test that plugin requires database ID"""
        with patch.dict(os.environ, {"NOTION_TOKEN": "fake_token"}, clear=True):
            plugin = NotionPlugin()
            if NOTION_AVAILABLE:
                assert not plugin.is_enabled()

    @patch("plugins.notion.Client")
    def test_notion_plugin_initialization_success(self, mock_client_class):
        """Test successful Notion plugin initialization"""
        if not NOTION_AVAILABLE:
            pytest.skip("notion-client not available")

        mock_client = Mock()
        mock_client.databases.retrieve.return_value = {"id": "test_db"}
        mock_client_class.return_value = mock_client

        with patch.dict(
            os.environ, {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"}
        ):
            plugin = NotionPlugin()
            assert plugin.is_enabled()
            assert plugin.client is not None

    @patch("plugins.notion.Client")
    def test_push_status(self, mock_client_class):
        """Test pushing STATUS.md to Notion"""
        if not NOTION_AVAILABLE:
            pytest.skip("notion-client not available")

        mock_client = Mock()
        mock_client.databases.retrieve.return_value = {"id": "test_db"}
        mock_client.databases.query.return_value = {"results": []}
        mock_client.pages.create.return_value = {"id": "page_id", "url": "https://notion.so/page"}
        mock_client_class.return_value = mock_client

        # Create temp status file
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# BuildRunner Status\n\nAll systems go!")
            status_file = Path(f.name)

        try:
            with patch.dict(
                os.environ, {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"}
            ):
                plugin = NotionPlugin()
                result = plugin.push_status(status_file)

                assert result is True
                mock_client.pages.create.assert_called_once()
        finally:
            status_file.unlink()

    @patch("plugins.notion.Client")
    def test_sync_documentation(self, mock_client_class):
        """Test syncing documentation to Notion"""
        if not NOTION_AVAILABLE:
            pytest.skip("notion-client not available")

        mock_client = Mock()
        mock_client.databases.retrieve.return_value = {"id": "test_db"}
        mock_client.databases.query.return_value = {"results": []}
        mock_client.pages.create.return_value = {"id": "page_id"}
        mock_client_class.return_value = mock_client

        # Create temp docs directory
        with tempfile.TemporaryDirectory() as tmpdir:
            docs_dir = Path(tmpdir)
            (docs_dir / "API.md").write_text("# API Docs\n\nContent here")
            (docs_dir / "README.md").write_text("# README\n\nMore content")

            with patch.dict(
                os.environ, {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"}
            ):
                plugin = NotionPlugin()
                results = plugin.sync_documentation(docs_dir)

                assert len(results) == 2
                assert "API.md" in results
                assert "README.md" in results

    @patch("plugins.notion.Client")
    def test_create_feature_page(self, mock_client_class):
        """Test creating Notion page for feature"""
        if not NOTION_AVAILABLE:
            pytest.skip("notion-client not available")

        mock_client = Mock()
        mock_client.databases.retrieve.return_value = {"id": "test_db"}
        mock_client.pages.create.return_value = {
            "id": "page_id",
            "url": "https://notion.so/feature",
        }
        mock_client_class.return_value = mock_client

        feature = {
            "name": "Test Feature",
            "description": "Test description",
            "status": "planned",
            "priority": "high",
            "version": "1.0.0",
            "week": 1,
            "build": "1A",
        }

        with patch.dict(
            os.environ, {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"}
        ):
            plugin = NotionPlugin()
            url = plugin.create_feature_page(feature)

            assert url == "https://notion.so/feature"
            mock_client.pages.create.assert_called_once()


# ============================================================================
# Slack Plugin Tests
# ============================================================================


class TestSlackPlugin:
    """Tests for Slack plugin"""

    def test_slack_plugin_without_dependencies(self):
        """Test that plugin gracefully handles missing slack-sdk"""
        if not SLACK_AVAILABLE:
            plugin = SlackPlugin()
            assert not plugin.is_enabled()
            assert plugin.client is None

    def test_slack_plugin_without_token(self):
        """Test that plugin requires Slack bot token"""
        with patch.dict(os.environ, {}, clear=True):
            plugin = SlackPlugin()
            if SLACK_AVAILABLE:
                assert not plugin.is_enabled()

    @patch("plugins.slack.WebClient")
    def test_slack_plugin_initialization_success(self, mock_webclient):
        """Test successful Slack plugin initialization"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch.dict(
            os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token", "SLACK_CHANNEL": "#builds"}
        ):
            plugin = SlackPlugin()
            assert plugin.is_enabled()
            assert plugin.client is not None
            assert plugin.default_channel == "#builds"

    @patch("plugins.slack.WebClient")
    def test_post_message(self, mock_webclient):
        """Test posting message to Slack"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_message("Test message", "#test")

            assert result is True
            mock_client.chat_postMessage.assert_called_once()

    @patch("plugins.slack.WebClient")
    def test_post_build_start(self, mock_webclient):
        """Test posting build start notification"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_build_start("Build 2B", "feature-branch")

            assert result is True
            call_args = mock_client.chat_postMessage.call_args
            assert "Build 2B" in call_args[1]["text"]

    @patch("plugins.slack.WebClient")
    def test_post_build_success(self, mock_webclient):
        """Test posting build success notification"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_build_success("Build 2B", "feature-branch", 120.5, 84)

            assert result is True
            call_args = mock_client.chat_postMessage.call_args
            assert "84" in call_args[1]["text"]

    @patch("plugins.slack.WebClient")
    def test_post_build_failure(self, mock_webclient):
        """Test posting build failure notification"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_build_failure("Build 2B", "feature-branch", "Tests failed")

            assert result is True
            call_args = mock_client.chat_postMessage.call_args
            assert "failed" in call_args[1]["text"].lower()

    @patch("plugins.slack.WebClient")
    def test_post_feature_update(self, mock_webclient):
        """Test posting feature status update"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_feature_update("Test Feature", "planned", "in_progress")

            assert result is True

    @patch("plugins.slack.WebClient")
    def test_post_daily_standup(self, mock_webclient):
        """Test posting daily standup"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        features = [
            {"name": "Feature 1", "status": "in_progress"},
            {"name": "Feature 2", "status": "complete"},
        ]

        metrics = {
            "features_complete": 1,
            "features_in_progress": 1,
            "features_planned": 3,
            "completion_percentage": 20,
        }

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_daily_standup(features, metrics)

            assert result is True
            call_args = mock_client.chat_postMessage.call_args
            assert "Feature 1" in str(call_args[1]["blocks"])

    @patch("plugins.slack.WebClient")
    def test_post_test_results(self, mock_webclient):
        """Test posting test results"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_test_results(100, 98, 2, 85.5)

            assert result is True

    @patch("plugins.slack.WebClient")
    def test_post_deployment(self, mock_webclient):
        """Test posting deployment notification"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_deployment("production", "3.0.0", "Roy")

            assert result is True
            call_args = mock_client.chat_postMessage.call_args
            assert "production" in call_args[1]["text"]

    # ============================================================================
    # Integration Tests
    # ============================================================================

    @patch("plugins.github.Github")
    def test_github_error_handling(self, mock_github):
        """Test GitHub plugin error handling"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_repo = Mock()
        mock_repo.get_issues.side_effect = Exception("API Error")
        mock_repo.get_issue.side_effect = Exception("API Error")
        mock_repo.create_pull.side_effect = Exception("API Error")

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()

            # All operations should handle errors gracefully
            assert plugin.sync_issues_to_features() == []
            assert plugin.create_feature_from_issue(123) is None
            assert plugin.create_pr("test", "body", "branch") is None

    @patch("plugins.github.Github")
    def test_add_pr_comment(self, mock_github):
        """Test adding comment to PR"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_pr = Mock()
        mock_repo = Mock()
        mock_repo.get_pull.return_value = mock_pr

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            result = plugin.add_pr_comment(123, "Great work!")

            assert result is True
            mock_pr.create_issue_comment.assert_called_once_with("Great work!")

    @patch("plugins.github.Github")
    def test_update_issue_status_complete(self, mock_github):
        """Test updating issue to complete status closes it"""
        if not GITHUB_AVAILABLE:
            pytest.skip("PyGithub not available")

        mock_issue = Mock()
        mock_issue.labels = []

        mock_repo = Mock()
        mock_repo.get_issue.return_value = mock_issue

        mock_client = Mock()
        mock_client.get_repo.return_value = mock_repo
        mock_github.return_value = mock_client

        with patch.dict(os.environ, {"GITHUB_TOKEN": "test_token", "GITHUB_REPO": "owner/repo"}):
            plugin = GitHubPlugin()
            result = plugin.update_issue_status(123, "complete")

            assert result is True
            mock_issue.edit.assert_called_once_with(state="closed")


# ============================================================================
# Notion Plugin Additional Tests
# ============================================================================


class TestNotionPluginAdvanced:
    """Advanced tests for Notion plugin"""

    @patch("plugins.notion.Client")
    def test_push_status_nonexistent_file(self, mock_client_class):
        """Test pushing non-existent STATUS.md"""
        if not NOTION_AVAILABLE:
            pytest.skip("notion-client not available")

        mock_client = Mock()
        mock_client.databases.retrieve.return_value = {"id": "test_db"}
        mock_client_class.return_value = mock_client

        with patch.dict(
            os.environ, {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"}
        ):
            plugin = NotionPlugin()
            result = plugin.push_status(Path("/nonexistent/status.md"))

            assert result is False

    @patch("plugins.notion.Client")
    def test_sync_documentation_nonexistent_dir(self, mock_client_class):
        """Test syncing non-existent docs directory"""
        if not NOTION_AVAILABLE:
            pytest.skip("notion-client not available")

        mock_client = Mock()
        mock_client.databases.retrieve.return_value = {"id": "test_db"}
        mock_client_class.return_value = mock_client

        with patch.dict(
            os.environ, {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"}
        ):
            plugin = NotionPlugin()
            result = plugin.sync_documentation(Path("/nonexistent"))

            assert result == {}

    @patch("plugins.notion.Client")
    def test_markdown_conversion(self, mock_client_class):
        """Test markdown to Notion blocks conversion"""
        if not NOTION_AVAILABLE:
            pytest.skip("notion-client not available")

        mock_client = Mock()
        mock_client.databases.retrieve.return_value = {"id": "test_db"}
        mock_client_class.return_value = mock_client

        with patch.dict(
            os.environ, {"NOTION_TOKEN": "test_token", "NOTION_DATABASE_ID": "test_db"}
        ):
            plugin = NotionPlugin()

            markdown = """# Header 1
## Header 2
### Header 3

Regular paragraph

- Bullet 1
- Bullet 2

```python
def hello():
    print("world")
```
"""

            blocks = plugin._markdown_to_blocks(markdown)

            assert len(blocks) > 0
            # Should have headers
            assert any(b["type"] == "heading_1" for b in blocks)
            assert any(b["type"] == "heading_2" for b in blocks)
            assert any(b["type"] == "heading_3" for b in blocks)
            # Should have list items
            assert any(b["type"] == "bulleted_list_item" for b in blocks)
            # Should have code block
            assert any(b["type"] == "code" for b in blocks)


# ============================================================================
# Slack Plugin Additional Tests
# ============================================================================


class TestSlackPluginAdvanced:
    """Advanced tests for Slack plugin"""

    @patch("plugins.slack.WebClient")
    def test_slack_message_with_blocks(self, mock_webclient):
        """Test posting message with Slack blocks"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        blocks = [{"type": "section", "text": {"type": "plain_text", "text": "Test"}}]

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_message("Test", blocks=blocks)

            assert result is True
            call_args = mock_client.chat_postMessage.call_args
            assert call_args[1]["blocks"] == blocks

    @patch("plugins.slack.WebClient")
    def test_slack_error_handling(self, mock_webclient):
        """Test Slack plugin error handling"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.side_effect = Exception("Slack API Error")
        mock_webclient.return_value = mock_client

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_message("Test")

            assert result is False

    @patch("plugins.slack.WebClient")
    def test_daily_standup_no_active_features(self, mock_webclient):
        """Test daily standup with no active features"""
        if not SLACK_AVAILABLE:
            pytest.skip("slack-sdk not available")

        mock_client = Mock()
        mock_client.auth_test.return_value = {"ok": True}
        mock_client.chat_postMessage.return_value = {"ok": True}
        mock_webclient.return_value = mock_client

        features = []
        metrics = {
            "features_complete": 0,
            "features_in_progress": 0,
            "features_planned": 5,
            "completion_percentage": 0,
        }

        with patch.dict(os.environ, {"SLACK_BOT_TOKEN": "xoxb-test-token"}):
            plugin = SlackPlugin()
            result = plugin.post_daily_standup(features, metrics)

            assert result is True
            call_args = mock_client.chat_postMessage.call_args
            assert "No features currently in progress" in str(call_args[1]["blocks"])


class TestPluginIntegration:
    """Integration tests for plugin system"""

    def test_all_plugins_handle_missing_dependencies(self):
        """Test that all plugins handle missing dependencies gracefully"""
        # This test always passes because plugins are designed to degrade gracefully
        github = GitHubPlugin()
        notion = NotionPlugin()
        slack = SlackPlugin()

        # All plugins should initialize without crashing
        assert github is not None
        assert notion is not None
        assert slack is not None

    def test_plugin_singletons(self):
        """Test that get_*_plugin() returns singleton instances"""
        github1 = get_github_plugin()
        github2 = get_github_plugin()
        assert github1 is github2

        notion1 = get_notion_plugin()
        notion2 = get_notion_plugin()
        assert notion1 is notion2

        slack1 = get_slack_plugin()
        slack2 = get_slack_plugin()
        assert slack1 is slack2

    def test_disabled_plugins_return_safe_values(self):
        """Test that disabled plugins return safe default values"""
        with patch.dict(os.environ, {}, clear=True):
            github = GitHubPlugin()
            notion = NotionPlugin()
            slack = SlackPlugin()

            # All operations should return safe values when disabled
            assert github.sync_issues_to_features() == []
            assert github.get_open_prs() == []
            assert github.create_pr("test", "body", "branch") is None

            assert notion.sync_documentation(Path("/fake")) == {}
            assert notion.create_feature_page({}) is None

            assert slack.post_message("test") is False
            assert slack.post_build_start("test", "branch") is False
