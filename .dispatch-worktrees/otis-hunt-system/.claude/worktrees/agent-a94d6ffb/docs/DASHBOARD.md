# Multi-Repo Dashboard

> Aggregate status across all your BuildRunner projects in one beautiful terminal UI

## Overview

The Multi-Repo Dashboard provides a unified view of all BuildRunner projects in a directory tree. Instead of checking each project individually, you can see aggregated metrics, health status, and alerts across your entire portfolio.

**Key Features:**
- 🔍 Automatic project discovery via filesystem scanning
- 📊 Multiple view modes (Overview, Detail, Timeline, Alerts)
- 🎨 Rich terminal UI with color-coded health indicators
- 🔄 Auto-refresh mode for real-time monitoring
- ⚠️ Smart alerts for stale, blocked, or problematic projects
- 📈 Progress tracking and completion metrics

## Installation

The dashboard is included in BuildRunner 3.0. Ensure you have the required dependencies:

```bash
pip install rich click pyyaml
```

## Quick Start

```bash
# Show dashboard for current directory
br dashboard show

# Show dashboard for specific directory
br dashboard show --path ~/projects

# Enable auto-refresh mode (updates every 30 seconds)
br dashboard show --watch

# Show specific view
br dashboard show --view alerts
br dashboard show --view timeline

# Show detailed view for a specific project
br dashboard show --detail MyProject
```

## Views

### Overview (Default)

Displays all projects with key metrics in a table format.

```bash
br dashboard show
```

**Example Output:**
```
📊 BuildRunner Multi-Repo Dashboard
┏━━━━━━━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━━━┳━━━━━━━━┳━━━━━━━━┳━━━━━━━━━━━━━━┓
┃ Project        ┃ Status ┃ Progress ┃ Features ┃ Active ┃ Health ┃ Last Updated ┃
┡━━━━━━━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━━━╇━━━━━━━━╇━━━━━━━━╇━━━━━━━━━━━━━━┩
│ BuildRunner    │   🔨   │   75%    │   12/16  │   3    │   🟢   │   Today      │
│ Dashboard      │   ✅   │  100%    │    8/8   │   -    │   🟢   │   Yesterday  │
│ API Server     │   🔨   │   60%    │   9/15   │   4    │   🟡   │   2d ago     │
│ Legacy Project │   📋   │   30%    │   3/10   │   0    │   🔴   │   10d ago    │
└────────────────┴────────┴──────────┴──────────┴────────┴────────┴──────────────┘

Total Projects: 4
Overall Completion: 62.5% (32/49 features)
Active: 2  Stale: 1  Blocked: 0
```

**Columns:**
- **Project**: Project name from features.json
- **Status**: Visual indicator (✅ complete, 🔨 in progress, 📋 planned)
- **Progress**: Completion percentage with color coding:
  - 🟢 Green: ≥75%
  - 🟡 Yellow: 50-74%
  - 🔴 Red: <50%
- **Features**: Completed/Total count
- **Active**: Number of features currently in progress
- **Health**: Overall project health (🟢 healthy, 🟡 warning, 🔴 critical)
- **Last Updated**: Time since last features.json update

### Detail View

Shows comprehensive information for a single project.

```bash
br dashboard show --detail BuildRunner
```

**Example Output:**
```
BuildRunner
/Users/me/projects/BuildRunner

📊 Status: active
📦 Version: 3.0.0
📈 Progress: 75% (12/16 features)

Features by Status:
  ✅ Completed: 12
  🔨 In Progress: 3
  📋 Planned: 1

Health: Healthy
Last Updated: 0 days ago

Active Features:
  • Multi-Repo Dashboard
  • Git Governance System
  • FastAPI Backend
```

### Alerts View

Shows only projects with potential issues requiring attention.

```bash
br dashboard show --view alerts
```

**Example Output:**
```
⚠️  Alerts
┏━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓
┃ Type         ┃ Project        ┃ Details                        ┃
┡━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┩
│ 🕐 Stale     │ Legacy Project │ No activity for 10 days        │
│ ⚠️  High WIP │ API Server     │ 8 features in progress (>5)    │
│ ⏸️  No Prog  │ New Project    │ 5 features planned, 0 active   │
└──────────────┴────────────────┴────────────────────────────────┘
```

**Alert Categories:**
- **🕐 Stale**: No updates in >7 days
- **🚫 Blocked**: Has active blockers (from context/blockers.md)
- **⏸️ No Progress**: Has planned features but none in progress
- **⚠️ High WIP**: More than 5 features in progress (potential bottleneck)

### Timeline View

Shows recent activity across all projects.

```bash
br dashboard show --view timeline
```

**Example Output:**
```
📅 Recent Activity (Last 30 Days)
┏━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━━━━━━┳━━━━━━━━━━┓
┃ Date               ┃ Project        ┃ Event               ┃ Progress ┃
┡━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━━━━━━╇━━━━━━━━━━┩
│ 2024-01-15 14:30   │ BuildRunner    │ updated             │    75%   │
│ 2024-01-14 09:15   │ Dashboard      │ updated             │   100%   │
│ 2024-01-13 16:45   │ API Server     │ updated             │    60%   │
│ 2024-01-05 11:20   │ Legacy Project │ updated             │    30%   │
└────────────────────┴────────────────┴─────────────────────┴──────────┘
```

## Auto-Refresh Mode

Watch mode automatically refreshes the dashboard every 30 seconds, perfect for monitoring during development or on a secondary screen.

```bash
br dashboard show --watch
```

**Usage:**
- Dashboard updates every 30 seconds
- Press `Ctrl+C` to exit
- Works with all view modes:
  ```bash
  br dashboard show --watch --view alerts
  ```

## Multi-Project Workflow

### Directory Structure

The dashboard scans recursively for `.buildrunner/features.json` files:

```
~/projects/
├── buildrunner/
│   └── .buildrunner/
│       └── features.json          ← Discovered
├── my-app/
│   └── .buildrunner/
│       └── features.json          ← Discovered
└── legacy/
    ├── backend/
    │   └── .buildrunner/
    │       └── features.json      ← Discovered
    └── frontend/
        └── .buildrunner/
            └── features.json      ← Discovered
```

**Scan Behavior:**
- Maximum depth: 5 levels
- Excludes: `.git`, `node_modules`, `.venv`, `venv`, `__pycache__`, `dist`, `build`
- Gracefully handles permission errors

### Best Practices

**1. Organize Projects by Category**
```bash
# Keep related projects together
~/work/clients/acme/
~/work/clients/beta/
~/work/internal/tools/

# Scan specific client projects
br dashboard show --path ~/work/clients/acme
```

**2. Use Alerts View for Daily Standup**
```bash
# Quick check for issues
br dashboard show --view alerts

# No alerts = all projects healthy
✅ No alerts - all projects healthy!
```

**3. Monitor with Watch Mode**
```bash
# On secondary screen/terminal
br dashboard show --watch --view overview

# Monitor specific alerts
br dashboard show --watch --view alerts
```

**4. Track Progress on Timelines**
```bash
# See recent activity
br dashboard show --view timeline

# Identify stagnant projects
# (anything not in timeline for 30 days)
```

## Health Indicators

Projects are automatically assigned health status based on multiple factors:

### 🟢 Healthy
- No blockers
- Updated within 7 days
- WIP ≤ completed features

### 🟡 Warning
- No blockers but:
  - Stale (>7 days since update), OR
  - High WIP (more in-progress than completed)

### 🔴 Critical
- Has active blockers
- Requires immediate attention

## Configuration

### Project Discovery

By default, the dashboard scans from the current directory. You can customize this:

```bash
# Scan from specific root
br dashboard show --path /path/to/projects

# Use in scripts
PROJECTS_ROOT=~/work/clients br dashboard show --path $PROJECTS_ROOT
```

### View Preferences

Set your preferred default view by creating a shell alias:

```bash
# In ~/.zshrc or ~/.bashrc
alias brd='br dashboard show --view overview --watch'
alias brda='br dashboard show --view alerts'
alias brdt='br dashboard show --view timeline'
```

## Architecture

### Components

```
cli/dashboard.py               # CLI interface (Click)
├── show command              # Main entry point
├── _generate_dashboard()     # Orchestrates scanning + rendering
├── _render_overview()        # Overview table
├── _render_detail_view()     # Single project detail
├── _render_alerts_view()     # Alerts table
└── _render_timeline_view()   # Timeline table

core/dashboard_views.py       # Data models and business logic
├── ProjectStatus             # Project data model
│   ├── is_stale             # Property: >7 days check
│   └── health_status        # Property: healthy/warning/critical
├── DashboardScanner          # Filesystem scanning
│   ├── discover_projects()  # Recursive search
│   └── _parse_project()     # Parse features.json
└── DashboardViews            # View data aggregation
    ├── get_overview_data()  # Aggregate all metrics
    ├── get_detail_data()    # Single project detail
    ├── get_timeline_data()  # Recent activity
    └── get_alerts_data()    # Filter problematic projects
```

### Data Flow

1. **Discovery Phase**
   - `DashboardScanner.discover_projects()` recursively searches for `.buildrunner/features.json`
   - Each file is parsed into a `ProjectStatus` object
   - Projects are sorted alphabetically

2. **Aggregation Phase**
   - `DashboardViews` receives list of projects
   - Calculates aggregate metrics (totals, percentages)
   - Filters projects by criteria (stale, blocked, etc.)

3. **Rendering Phase**
   - CLI functions receive aggregated data
   - Rich library components (Table, Panel) format output
   - Color coding applied based on thresholds

4. **Update Loop** (watch mode only)
   - `Live` context refreshes display
   - Re-runs discovery + aggregation every 30s
   - Maintains smooth UI updates

## Examples

### Example 1: Daily Standup Workflow

```bash
# Check for any issues first
br dashboard show --view alerts

# If alerts exist, get details
br dashboard show --detail ProjectName

# View overall progress
br dashboard show --view overview

# Check recent activity
br dashboard show --view timeline
```

### Example 2: Monitoring Build Progress

```bash
# Terminal 1: Watch overall progress
br dashboard show --watch --view overview

# Terminal 2: Work on features
cd ~/projects/myapp
br feature start "New Feature"
# ... make changes ...
br feature complete "New Feature"

# Terminal 1 automatically reflects changes after 30s
```

### Example 3: Managing Multiple Clients

```bash
# Create convenience scripts
cat > ~/bin/client-dashboard.sh << 'EOF'
#!/bin/bash
CLIENT=$1
br dashboard show --path ~/clients/$CLIENT --view overview
EOF

chmod +x ~/bin/client-dashboard.sh

# Usage
./client-dashboard.sh acme
./client-dashboard.sh beta
```

### Example 4: Integration with CI/CD

```bash
# In your CI pipeline
br dashboard show --path . --view alerts > alerts.txt

# Fail build if critical alerts exist
if grep -q "Blocked" alerts.txt; then
  echo "Critical blockers detected!"
  cat alerts.txt
  exit 1
fi
```

## Troubleshooting

### No Projects Found

```
No BuildRunner projects found.
Searched in: /current/path
Hint: Make sure projects have .buildrunner/features.json
```

**Solutions:**
- Verify `.buildrunner/features.json` exists in projects
- Check search path: `br dashboard show --path /correct/path`
- Ensure max depth (5 levels) isn't exceeded

### Incorrect Metrics

If metrics don't match expectations:
1. Check `features.json` is valid JSON
2. Verify `last_updated` timestamp format (ISO 8601)
3. Ensure `metrics.completion_percentage` is set
4. Run validation: `br validate` in project directory

### Permission Errors

The scanner gracefully skips directories it can't access. If you need to scan restricted directories:
```bash
# Run with appropriate permissions
sudo br dashboard show --path /protected/path
```

## Testing

The dashboard includes comprehensive test coverage (94%):

```bash
# Run dashboard tests
pytest tests/test_dashboard.py -v

# Check coverage
pytest tests/test_dashboard.py --cov=core.dashboard_views --cov=cli.dashboard --cov-report=term-missing
```

Test categories:
- ProjectStatus properties (health, staleness)
- Scanner filesystem discovery
- Project parsing (valid, invalid, missing fields)
- View aggregation (overview, detail, timeline, alerts)
- Integration tests (end-to-end workflows)

## Performance

**Scan Performance:**
- ~100 projects: <1 second
- ~500 projects: ~2-3 seconds
- Max depth limited to 5 levels to prevent deep recursion

**Optimization Tips:**
- Use `--path` to limit scan scope
- Avoid scanning large monorepos from root
- Exclude heavy directories (already skips `node_modules`, `.git`, etc.)

## Roadmap

Future enhancements planned:
- Export to CSV/JSON for reporting
- Custom alert thresholds via config
- Burndown charts and velocity tracking
- Project comparison mode
- Slack/email notifications for alerts
- Web UI alternative

## See Also

- [Feature Registry](FEATURES.md) - Single-project feature management
- [Git Governance](GOVERNANCE.md) - Branch protection and automation
- [API Reference](API.md) - FastAPI backend for dashboard data
- [BUILD_PLAN.md](../BUILD_PLAN.md) - Implementation plan for Build 4B
