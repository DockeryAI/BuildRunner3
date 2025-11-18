# BuildRunner 3.0 Plugins

Optional integrations that enhance BuildRunner without being required.

## Philosophy

**Plugins are optional.** BuildRunner works perfectly without them. When configured, they add useful features like:
- Syncing features with GitHub issues
- Publishing documentation to Notion
- Posting build notifications to Slack

All plugins degrade gracefully - if credentials aren't configured or packages aren't installed, BuildRunner continues working normally.

## Available Plugins

### 1. GitHub Plugin

Syncs issues to features, creates PRs from CLI, and updates issue status.

#### Installation

```bash
pip install PyGithub
```

#### Configuration

Create a GitHub personal access token at https://github.com/settings/tokens

Required permissions:
- `repo` - Full control of private repositories
- `workflow` - Update GitHub Action workflows

```bash
export GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
export GITHUB_REPO=owner/repo-name
```

#### Usage

```python
from plugins.github import get_github_plugin

github = get_github_plugin()

# Check if enabled
if github.is_enabled():
    # Sync GitHub issues with 'feature' label
    features = github.sync_issues_to_features(label="feature")

    # Create feature from specific issue
    feature = github.create_feature_from_issue(issue_number=123)

    # Update issue when feature status changes
    github.update_issue_status(
        issue_number=123,
        status="in_progress",
        comment="Working on this feature"
    )

    # Create PR for completed feature
    pr_url = github.create_pr(
        title="feat: New Feature",
        body="Implements feature X",
        head_branch="feature/new-feature",
        base_branch="main"
    )

    # Or create PR from feature dict
    pr_url = github.create_pr_from_feature(
        feature={"name": "My Feature", "description": "..."},
        branch="feature/my-feature"
    )

    # Add comment to PR
    github.add_pr_comment(pr_number=456, comment="LGTM!")

    # Get open PRs
    prs = github.get_open_prs()
```

#### Label Conventions

The GitHub plugin recognizes these labels:

**Priority Labels:**
- `priority:critical` → critical
- `priority:high` → high
- `priority:medium` → medium
- `priority:low` → low

**Status Labels:**
- `status:planned` → planned
- `status:in_progress` → in progress
- `status:complete` → complete

#### Issue Sync

Issues with the `feature` label are automatically synced:

```bash
# Issue #123 with label "feature" becomes:
{
  "id": "gh-123",
  "name": "Issue Title",
  "description": "Issue body",
  "status": "planned",
  "priority": "high",  # From priority:high label
  "github_issue": 123,
  "github_url": "https://github.com/owner/repo/issues/123"
}
```

### 2. Notion Plugin

Pushes STATUS.md and documentation to Notion.

#### Installation

```bash
pip install notion-client
```

#### Configuration

1. Create Notion integration at https://www.notion.so/my-integrations
2. Share your database with the integration
3. Get database ID from the database URL:
   `https://notion.so/workspace/DATABASE_ID?v=...`

```bash
export NOTION_TOKEN=secret_xxxxxxxxxxxxx
export NOTION_DATABASE_ID=xxxxxxxxxxxxx
```

#### Usage

```python
from plugins.notion import get_notion_plugin
from pathlib import Path

notion = get_notion_plugin()

if notion.is_enabled():
    # Push STATUS.md to Notion
    notion.push_status(Path(".buildrunner/STATUS.md"))

    # Sync all documentation
    results = notion.sync_documentation(Path("docs"))
    # Returns: {"API.md": True, "PLUGINS.md": True}

    # Create Notion page for a feature
    feature = {
        "name": "My Feature",
        "description": "Feature description",
        "status": "in_progress",
        "priority": "high",
        "version": "1.0.0"
    }
    page_url = notion.create_feature_page(feature)
```

#### Markdown Conversion

The Notion plugin converts markdown to Notion blocks:

**Supported:**
- Headers (`#`, `##`, `###`)
- Paragraphs
- Bullet lists (`- item`)
- Code blocks (````python`)

**Not yet supported:**
- Numbered lists
- Tables
- Images
- Links (converted to plain text)

### 3. Slack Plugin

Posts notifications and daily standups to Slack.

#### Installation

```bash
pip install slack-sdk
```

#### Configuration

1. Create Slack app at https://api.slack.com/apps
2. Add Bot Token Scopes:
   - `chat:write` - Send messages
   - `chat:write.public` - Send to public channels
3. Install app to workspace
4. Copy Bot User OAuth Token

```bash
export SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxx
export SLACK_CHANNEL=#builds  # Optional, defaults to #builds
```

#### Usage

```python
from plugins.slack import get_slack_plugin

slack = get_slack_plugin()

if slack.is_enabled():
    # Simple message
    slack.post_message("Build started!", channel="#dev")

    # Build notifications
    slack.post_build_start("Build 2B", "feature-branch")
    slack.post_build_success("Build 2B", "feature-branch", duration=120.5, tests_passed=84)
    slack.post_build_failure("Build 2B", "feature-branch", error="Tests failed")

    # Feature updates
    slack.post_feature_update(
        feature_name="API Backend",
        old_status="planned",
        new_status="in_progress"
    )

    # Daily standup
    features = [...]  # List of features
    metrics = {...}   # Project metrics
    slack.post_daily_standup(features, metrics)

    # Test results
    slack.post_test_results(
        total=100,
        passed=98,
        failed=2,
        coverage=85.5
    )

    # Deployments
    slack.post_deployment(
        environment="production",
        version="3.0.0",
        deployer="Roy"
    )
```

#### Message Formatting

Slack plugin uses Slack's Block Kit for rich formatting:

```python
# Custom blocks
blocks = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "*Build Status*\nAll tests passing ✅"
        }
    }
]
slack.post_message("Build complete", blocks=blocks)
```

## Integration Examples

### Automated GitHub Workflow

```python
from core.feature_registry import FeatureRegistry
from plugins.github import get_github_plugin

registry = FeatureRegistry()
github = get_github_plugin()

if github.is_enabled():
    # Sync issues to features
    features = github.sync_issues_to_features()

    for feature in features:
        # Add to registry
        registry.add_feature(
            feature_id=feature['id'],
            name=feature['name'],
            description=feature['description'],
            priority=feature['priority']
        )

        # Update issue
        github.update_issue_status(
            issue_number=feature['github_issue'],
            status="in_progress",
            comment="Feature added to BuildRunner registry"
        )
```

### Complete Build Notification

```python
from plugins.slack import get_slack_plugin
from plugins.github import get_github_plugin

slack = get_slack_plugin()
github = get_github_plugin()

# Build starts
if slack.is_enabled():
    slack.post_build_start("Build 2B", "feature/api-backend")

# ... run build ...

# Build completes
if slack.is_enabled():
    slack.post_build_success("Build 2B", "feature/api-backend", 180.0, 84)

# Create PR
if github.is_enabled():
    pr_url = github.create_pr(
        title="feat: Implement API backend",
        body="Complete Build 2B implementation",
        head_branch="feature/api-backend"
    )

    # Notify Slack about PR
    if slack.is_enabled():
        slack.post_message(f"PR created: {pr_url}", channel="#dev")
```

### Documentation Sync

```python
from pathlib import Path
from core.status_generator import StatusGenerator
from plugins.notion import get_notion_plugin

# Generate STATUS.md
generator = StatusGenerator()
generator.generate()

# Sync to Notion
notion = get_notion_plugin()
if notion.is_enabled():
    notion.push_status(Path(".buildrunner/STATUS.md"))
    notion.sync_documentation(Path("docs"))
```

## CLI Integration

Add plugin commands to your CLI:

```python
# cli/commands.py
import click
from plugins.github import get_github_plugin
from plugins.notion import get_notion_plugin
from plugins.slack import get_slack_plugin

@click.group()
def plugins():
    """Manage BuildRunner plugins"""
    pass

@plugins.command()
def sync_github():
    """Sync GitHub issues to features"""
    github = get_github_plugin()
    if not github.is_enabled():
        click.echo("GitHub plugin not configured")
        return

    features = github.sync_issues_to_features()
    click.echo(f"Synced {len(features)} features from GitHub")

@plugins.command()
def push_docs():
    """Push documentation to Notion"""
    notion = get_notion_plugin()
    if not notion.is_enabled():
        click.echo("Notion plugin not configured")
        return

    results = notion.sync_documentation(Path("docs"))
    successful = sum(1 for v in results.values() if v)
    click.echo(f"Synced {successful}/{len(results)} docs to Notion")

@plugins.command()
@click.argument('message')
def slack_notify(message):
    """Send Slack notification"""
    slack = get_slack_plugin()
    if not slack.is_enabled():
        click.echo("Slack plugin not configured")
        return

    slack.post_message(message)
    click.echo("Message sent to Slack")
```

## Testing Plugins

All plugins include comprehensive tests with mocking:

```bash
# Run plugin tests
pytest tests/test_plugins.py -v

# Check coverage
pytest tests/test_plugins.py --cov=plugins --cov-report=term-missing

# Test specific plugin
pytest tests/test_plugins.py::TestGitHubPlugin -v
```

## Troubleshooting

### GitHub Plugin

**Issue: "GitHub plugin not enabled"**
- Check `GITHUB_TOKEN` is set and valid
- Check `GITHUB_REPO` is in format `owner/repo`
- Verify token has `repo` scope

**Issue: "Failed to sync issues"**
- Check repository exists and you have access
- Verify issues have the correct label
- Check API rate limits

### Notion Plugin

**Issue: "Notion plugin not enabled"**
- Check `NOTION_TOKEN` is set
- Check `NOTION_DATABASE_ID` is correct
- Verify database is shared with integration

**Issue: "Failed to push status"**
- Check STATUS.md file exists
- Verify integration has write permissions
- Check Notion API status

### Slack Plugin

**Issue: "Slack plugin not enabled"**
- Check `SLACK_BOT_TOKEN` is set and starts with `xoxb-`
- Verify bot is installed in workspace
- Check bot has `chat:write` scope

**Issue: "Failed to post message"**
- Check channel exists and bot is invited
- Verify channel name starts with `#`
- Check bot permissions

## Best Practices

1. **Environment Variables**: Store credentials in `.env` file (never commit!)

```bash
# .env
GITHUB_TOKEN=ghp_xxxxxxxxxxxxx
GITHUB_REPO=myorg/myrepo
NOTION_TOKEN=secret_xxxxxxxxxxxxx
NOTION_DATABASE_ID=xxxxxxxxxxxxx
SLACK_BOT_TOKEN=xoxb-xxxxxxxxxxxxx
SLACK_CHANNEL=#builds
```

2. **Check Availability**: Always check if plugins are enabled

```python
github = get_github_plugin()
if github.is_enabled():
    # Use plugin
else:
    # Handle gracefully
```

3. **Error Handling**: Plugins handle errors internally but log warnings

4. **Testing**: Use mocks when testing code that uses plugins

```python
from unittest.mock import patch, Mock

@patch('plugins.github.Github')
def test_my_feature(mock_github):
    # Your test code
```

5. **Rate Limiting**: Be mindful of API rate limits
   - GitHub: 5000 requests/hour
   - Notion: 3 requests/second
   - Slack: Varies by method

## Security Notes

- **Never commit tokens** - Use environment variables or `.env` files
- **Token Rotation** - Rotate tokens regularly
- **Minimum Permissions** - Only grant necessary scopes
- **Audit Logs** - Monitor integration usage in service dashboards

## Roadmap

Future plugin possibilities:
- **Jira**: Issue tracking integration
- **Trello**: Board sync
- **Linear**: Feature management
- **Discord**: Team notifications
- **PagerDuty**: Incident management
- **Datadog**: Metrics and monitoring

Want to build a plugin? See `CONTRIBUTING.md` for guidelines.

## Plugin Development

### Creating a New Plugin

1. Create `plugins/myservice.py`
2. Implement graceful degradation:

```python
try:
    from myservice import Client
    MYSERVICE_AVAILABLE = True
except ImportError:
    MYSERVICE_AVAILABLE = False
    Client = None

class MyServicePlugin:
    def __init__(self, token=None):
        self.enabled = MYSERVICE_AVAILABLE
        self.token = token or os.getenv("MYSERVICE_TOKEN")

        if not MYSERVICE_AVAILABLE:
            print("ℹ️  MyService plugin disabled: package not installed")
            return

        if not self.token:
            print("ℹ️  MyService plugin disabled: MYSERVICE_TOKEN not set")
            self.enabled = False
            return

        try:
            self.client = Client(self.token)
            print("✅ MyService plugin enabled")
        except Exception as e:
            print(f"⚠️  MyService plugin initialization failed: {e}")
            self.enabled = False

    def is_enabled(self):
        return self.enabled and self.client is not None

    def my_method(self):
        if not self.is_enabled():
            print("MyService plugin not enabled")
            return None
        # Your code here
```

3. Add tests to `tests/test_plugins.py`
4. Document in this file

## Support

- **Issues**: Report bugs at https://github.com/yourorg/buildrunner/issues
- **Docs**: Full documentation at https://buildrunner.dev
- **Community**: Join discussions at https://discord.gg/buildrunner

---

Remember: **Plugins are optional**. BuildRunner works great without them. Use what makes sense for your team.
