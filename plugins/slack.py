"""
Slack Plugin for BuildRunner 3.0

Posts notifications and daily standups to Slack.
Because email is dead and your team needs more distractions.
"""

import os
from typing import Optional, Dict, Any, List
from datetime import datetime

try:
    from slack_sdk import WebClient
    from slack_sdk.errors import SlackApiError
    SLACK_AVAILABLE = True
except ImportError:
    SLACK_AVAILABLE = False
    WebClient = None
    SlackApiError = Exception

from dotenv import load_dotenv


class SlackPlugin:
    """
    Slack integration plugin.

    Optional plugin - your team can live without notifications.
    When enabled, posts build status, feature updates, and daily standups.
    """

    def __init__(self, token: Optional[str] = None, channel: Optional[str] = None):
        """
        Initialize Slack plugin.

        Args:
            token: Slack bot token (or uses SLACK_BOT_TOKEN env var)
            channel: Default Slack channel (or uses SLACK_CHANNEL env var)
        """
        load_dotenv()

        self.enabled = SLACK_AVAILABLE
        self.token = token or os.getenv("SLACK_BOT_TOKEN")
        self.default_channel = channel or os.getenv("SLACK_CHANNEL", "#builds")
        self.client: Optional[Any] = None

        if not SLACK_AVAILABLE:
            print("ℹ️  Slack plugin disabled: slack-sdk not installed")
            print("   Install with: pip install slack-sdk")
            return

        if not self.token:
            print("ℹ️  Slack plugin disabled: SLACK_BOT_TOKEN not set")
            print("   Create bot at https://api.slack.com/apps")
            self.enabled = False
            return

        try:
            self.client = WebClient(token=self.token)
            # Test connection
            self.client.auth_test()
            print(f"✅ Slack plugin enabled (channel: {self.default_channel})")
        except Exception as e:
            print(f"⚠️  Slack plugin initialization failed: {e}")
            self.enabled = False

    def is_enabled(self) -> bool:
        """Check if plugin is enabled and configured"""
        return self.enabled and self.client is not None

    def post_message(
        self,
        text: str,
        channel: Optional[str] = None,
        blocks: Optional[List[Dict[str, Any]]] = None
    ) -> bool:
        """
        Post a message to Slack.

        Args:
            text: Message text (fallback for notifications)
            channel: Channel to post to (default: configured channel)
            blocks: Optional Slack blocks for rich formatting

        Returns:
            True if successful
        """
        if not self.is_enabled():
            print("Slack plugin not enabled - skipping message")
            return False

        channel = channel or self.default_channel

        try:
            self.client.chat_postMessage(
                channel=channel,
                text=text,
                blocks=blocks
            )
            print(f"✅ Posted to Slack: {channel}")
            return True

        except Exception as e:
            print(f"⚠️  Failed to post to Slack: {e}")
            return False

    def post_build_start(self, build_name: str, branch: str, channel: Optional[str] = None) -> bool:
        """
        Post notification that a build has started.

        Args:
            build_name: Name of the build
            branch: Git branch
            channel: Slack channel

        Returns:
            True if successful
        """
        text = f"🚀 Build started: {build_name} on {branch}"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🚀 Build Started*\n\n*Build:* {build_name}\n*Branch:* `{branch}`\n*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        ]

        return self.post_message(text, channel, blocks)

    def post_build_success(
        self,
        build_name: str,
        branch: str,
        duration: float,
        tests_passed: int,
        channel: Optional[str] = None
    ) -> bool:
        """
        Post notification that a build succeeded.

        Args:
            build_name: Name of the build
            branch: Git branch
            duration: Build duration in seconds
            tests_passed: Number of tests passed
            channel: Slack channel

        Returns:
            True if successful
        """
        text = f"✅ Build succeeded: {build_name} ({tests_passed} tests passed, {duration:.1f}s)"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*✅ Build Successful*\n\n*Build:* {build_name}\n*Branch:* `{branch}`\n*Tests:* {tests_passed} passed\n*Duration:* {duration:.1f}s"
                }
            }
        ]

        return self.post_message(text, channel, blocks)

    def post_build_failure(
        self,
        build_name: str,
        branch: str,
        error: str,
        channel: Optional[str] = None
    ) -> bool:
        """
        Post notification that a build failed.

        Args:
            build_name: Name of the build
            branch: Git branch
            error: Error message
            channel: Slack channel

        Returns:
            True if successful
        """
        text = f"❌ Build failed: {build_name} - {error}"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*❌ Build Failed*\n\n*Build:* {build_name}\n*Branch:* `{branch}`\n*Error:* ```{error}```\n*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        ]

        return self.post_message(text, channel, blocks)

    def post_feature_update(
        self,
        feature_name: str,
        old_status: str,
        new_status: str,
        channel: Optional[str] = None
    ) -> bool:
        """
        Post notification about feature status change.

        Args:
            feature_name: Feature name
            old_status: Previous status
            new_status: New status
            channel: Slack channel

        Returns:
            True if successful
        """
        emoji = {
            "planned": "📋",
            "in_progress": "🔨",
            "complete": "✅"
        }

        status_emoji = emoji.get(new_status, "📝")
        text = f"{status_emoji} Feature update: {feature_name} → {new_status}"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{status_emoji} Feature Status Update*\n\n*Feature:* {feature_name}\n*Status:* {old_status} → *{new_status}*"
                }
            }
        ]

        return self.post_message(text, channel, blocks)

    def post_daily_standup(
        self,
        features: List[Dict[str, Any]],
        metrics: Dict[str, Any],
        channel: Optional[str] = None
    ) -> bool:
        """
        Post daily standup summary.

        Args:
            features: List of features
            metrics: Project metrics
            channel: Slack channel

        Returns:
            True if successful
        """
        total = metrics.get('features_complete', 0) + metrics.get('features_in_progress', 0) + metrics.get('features_planned', 0)
        complete = metrics.get('features_complete', 0)
        in_progress = metrics.get('features_in_progress', 0)
        completion = metrics.get('completion_percentage', 0)

        # Get in_progress features
        active_features = [f for f in features if f.get('status') == 'in_progress']
        active_text = "\n".join([f"  • {f.get('name', 'Unknown')}" for f in active_features[:5]])

        if not active_text:
            active_text = "  • No features currently in progress"

        text = f"📊 Daily Standup: {complete}/{total} features complete ({completion}%)"

        blocks = [
            {
                "type": "header",
                "text": {
                    "type": "plain_text",
                    "text": "📊 BuildRunner Daily Standup"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Progress Overview*\n✅ {complete} complete\n🔨 {in_progress} in progress\n📋 {metrics.get('features_planned', 0)} planned\n\n*Completion:* {completion}%"
                }
            },
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*Active Features:*\n{active_text}"
                }
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": f"Generated at {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                    }
                ]
            }
        ]

        return self.post_message(text, channel, blocks)

    def post_test_results(
        self,
        total: int,
        passed: int,
        failed: int,
        coverage: float,
        channel: Optional[str] = None
    ) -> bool:
        """
        Post test results to Slack.

        Args:
            total: Total tests
            passed: Tests passed
            failed: Tests failed
            coverage: Code coverage percentage
            channel: Slack channel

        Returns:
            True if successful
        """
        status_emoji = "✅" if failed == 0 else "⚠️"
        text = f"{status_emoji} Tests: {passed}/{total} passed, {coverage}% coverage"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*{status_emoji} Test Results*\n\n*Total:* {total}\n*Passed:* {passed}\n*Failed:* {failed}\n*Coverage:* {coverage}%"
                }
            }
        ]

        return self.post_message(text, channel, blocks)

    def post_deployment(
        self,
        environment: str,
        version: str,
        deployer: str,
        channel: Optional[str] = None
    ) -> bool:
        """
        Post deployment notification.

        Args:
            environment: Deployment environment
            version: Version deployed
            deployer: Who deployed
            channel: Slack channel

        Returns:
            True if successful
        """
        text = f"🚀 Deployed {version} to {environment}"

        blocks = [
            {
                "type": "section",
                "text": {
                    "type": "mrkdwn",
                    "text": f"*🚀 Deployment*\n\n*Environment:* {environment}\n*Version:* {version}\n*Deployed by:* {deployer}\n*Time:* {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                }
            }
        ]

        return self.post_message(text, channel, blocks)


# Global plugin instance
_slack_plugin: Optional[SlackPlugin] = None


def get_slack_plugin() -> SlackPlugin:
    """
    Get global Slack plugin instance.

    Returns:
        SlackPlugin instance
    """
    global _slack_plugin
    if _slack_plugin is None:
        _slack_plugin = SlackPlugin()
    return _slack_plugin
