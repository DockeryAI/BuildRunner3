# BuildRunner 3.1 - Command Reference

**Complete CLI reference for all commands**

---

## Feature Management

### `br feature add`
Add a new feature to track.

```bash
br feature add "Feature Name" [OPTIONS]

Options:
  --id TEXT            Custom feature ID (auto-generated if not provided)
  --description TEXT   Feature description
  --priority TEXT      Priority: low, medium, high, critical (default: medium)
  --status TEXT        Status: planned, in_progress, complete (default: planned)
  --week INT          Week number for planning
  --build TEXT        Build identifier

Examples:
  br feature add "User Auth"
  br feature add "Payment API" --priority critical --week 2
  br feature add "Dashboard" --id dash --description "Analytics dashboard"
```

### `br feature list`
List all features.

```bash
br feature list [OPTIONS]

Options:
  --status TEXT    Filter by status (planned, in_progress, complete)
  --priority TEXT  Filter by priority
  --format TEXT    Output format: table, json, yaml (default: table)

Examples:
  br feature list
  br feature list --status in_progress
  br feature list --format json
```

### `br feature get`
Get details for a specific feature.

```bash
br feature get FEATURE_ID [OPTIONS]

Options:
  --format TEXT    Output format: table, json, yaml

Examples:
  br feature get auth-system
  br feature get payment-api --format json
```

### `br feature update`
Update feature properties.

```bash
br feature update FEATURE_ID [OPTIONS]

Options:
  --status TEXT        New status
  --priority TEXT      New priority
  --description TEXT   New description
  --assignee TEXT      Assign to team member

Examples:
  br feature update auth --status in_progress
  br feature update payment --priority critical --assignee alice@example.com
```

### `br feature complete`
Mark feature as complete.

```bash
br feature complete FEATURE_ID

Examples:
  br feature complete auth-system
  br feature complete payment-api
```

---

## Status & Reporting

### `br status`
Display project status and metrics.

```bash
br status [OPTIONS]

Options:
  --format TEXT    Output format: table, json

Examples:
  br status
  br status --format json
```

### `br status generate`
Generate STATUS.md from features.json.

```bash
br status generate

Creates: STATUS.md in project root
```

---

## Design System

### `br design list`
List all 148 industry profiles.

```bash
br design list [OPTIONS]

Options:
  --category TEXT      Filter by category (Healthcare, Professional Services, etc.)
  -v, --verbose       Show detailed information

Examples:
  br design list
  br design list --category Healthcare
  br design list -v
```

### `br design profile`
Show detailed industry profile.

```bash
br design profile INDUSTRY_ID [OPTIONS]

Options:
  -f, --format TEXT   Output format: rich, json, yaml (default: rich)

Examples:
  br design profile restaurant
  br design profile msp-managed-service-provider
  br design profile dentist --format json
```

### `br design search`
Search profiles by name, category, or keywords.

```bash
br design search QUERY [OPTIONS]

Options:
  -n, --limit INT     Maximum results (default: 20)

Examples:
  br design search dental
  br design search "health care"
  br design search technology --limit 10
```

### `br design export`
Export Synapse profiles from TypeScript to YAML.

```bash
br design export [OPTIONS]

Options:
  -o, --output PATH   Output directory (default: synapse-profiles)

Examples:
  br design export
  br design export --output custom-dir
```

---

## Quality Management

### `br quality check`
Run quality checks on codebase.

```bash
br quality check [OPTIONS]

Options:
  --threshold INT    Minimum quality score (0-100, default: 70)
  --verbose         Show detailed report

Examples:
  br quality check
  br quality check --threshold 85
  br quality check --verbose
```

### `br quality report`
Generate detailed quality report.

```bash
br quality report [OPTIONS]

Options:
  --format TEXT     Output format: table, json
  --output PATH     Save report to file

Examples:
  br quality report
  br quality report --format json --output report.json
```

---

## Specification Management

### `br spec wizard`
Interactive PRD/spec builder.

```bash
br spec wizard

Interactive prompts for:
- Industry selection (from 148 profiles)
- Use case pattern
- Technical stack
- Features and requirements

Generates: PROJECT_SPEC.md
```

### `br spec validate`
Validate PROJECT_SPEC.md structure.

```bash
br spec validate [OPTIONS]

Options:
  --spec PATH      Path to spec file (default: PROJECT_SPEC.md)

Examples:
  br spec validate
  br spec validate --spec docs/SPEC.md
```

---

## Security

### `br security scan`
Scan for secrets and security issues.

```bash
br security scan [OPTIONS]

Options:
  --path PATH           Directory to scan (default: .)
  --patterns TEXT       Comma-separated patterns to check

Examples:
  br security scan
  br security scan --path src/
```

### `br security check`
Run pre-commit security checks.

```bash
br security check

Runs:
- Secret detection (13 patterns)
- SQL injection detection
- Security linting
```

---

## Parallel Orchestration

### `br parallel session create`
Create parallel execution session.

```bash
br parallel session create NAME [OPTIONS]

Options:
  --workers INT        Number of parallel workers (default: 4)
  --description TEXT   Session description

Examples:
  br parallel session create "Sprint 1" --workers 6
  br parallel session create "Feature Dev"
```

### `br parallel session list`
List all parallel sessions.

```bash
br parallel session list [OPTIONS]

Options:
  --active         Show only active sessions
  --format TEXT    Output format: table, json

Examples:
  br parallel session list
  br parallel session list --active
```

### `br parallel dashboard`
Launch real-time parallel execution dashboard.

```bash
br parallel dashboard [OPTIONS]

Options:
  --session TEXT    Session ID to monitor
  --interval INT    Update interval in seconds (default: 2)

Examples:
  br parallel dashboard
  br parallel dashboard --session sprint-1
```

---

## Telemetry

### `br telemetry stats`
View telemetry statistics.

```bash
br telemetry stats [OPTIONS]

Options:
  --period TEXT     Time period: day, week, month, all (default: week)
  --format TEXT     Output format: table, json

Examples:
  br telemetry stats
  br telemetry stats --period month
  br telemetry stats --format json
```

### `br telemetry query`
Query telemetry events.

```bash
br telemetry query [OPTIONS]

Options:
  --type TEXT          Event type filter
  --since TEXT         Start date (ISO format)
  --limit INT          Maximum results

Examples:
  br telemetry query --type TASK_COMPLETED
  br telemetry query --since 2025-11-01 --limit 100
```

---

## Model Routing

### `br routing estimate`
Estimate task complexity.

```bash
br routing estimate "TASK_DESCRIPTION"

Returns: Complexity level and recommended model

Examples:
  br routing estimate "Add user authentication"
  br routing estimate "Fix typo in documentation"
```

### `br routing cost`
View cost tracking.

```bash
br routing cost [OPTIONS]

Options:
  --period TEXT     Time period: day, week, month
  --breakdown      Show detailed breakdown

Examples:
  br routing cost
  br routing cost --period week --breakdown
```

---

## Configuration

### `br config get`
Get configuration value.

```bash
br config get KEY

Examples:
  br config get quality.min_coverage
  br config get telemetry.enabled
```

### `br config set`
Set configuration value.

```bash
br config set KEY VALUE [OPTIONS]

Options:
  --global    Set in global config (~/.buildrunner/config.yaml)

Examples:
  br config set quality.min_coverage 85
  br config set telemetry.enabled true --global
```

### `br config list`
List all configuration.

```bash
br config list [OPTIONS]

Options:
  --global    Show global config only
  --project   Show project config only

Examples:
  br config list
  br config list --global
```

---

## Governance

### `br governance check`
Run governance checks.

```bash
br governance check [OPTIONS]

Options:
  --type TEXT    Check type: pre_commit, pre_push, manual

Examples:
  br governance check
  br governance check --type pre_commit
```

### `br governance validate`
Validate governance configuration.

```bash
br governance validate

Validates: .buildrunner/governance.yaml
```

---

## Gap Analysis

### `br gaps analyze`
Analyze project completeness gaps.

```bash
br gaps analyze [OPTIONS]

Options:
  --spec PATH       Spec file to analyze
  --threshold INT   Completion threshold percentage

Examples:
  br gaps analyze
  br gaps analyze --spec PROJECT_SPEC.md --threshold 90
```

### `br gaps report`
Generate gap analysis report.

```bash
br gaps report [OPTIONS]

Options:
  --format TEXT     Output format: markdown, json
  --output PATH     Save to file

Examples:
  br gaps report
  br gaps report --format markdown --output GAPS.md
```

---

## Utility Commands

### `br init`
Initialize BuildRunner in project.

```bash
br init [PROJECT_NAME]

Creates:
- .buildrunner/features.json
- .buildrunner/config.yaml
- PROJECT_SPEC.md
- .gitignore updates

Examples:
  br init
  br init my-project
```

### `br health`
Check BuildRunner system health.

```bash
br health

Checks:
- Configuration validity
- File permissions
- Dependencies
- Git status
```

### `br version`
Show BuildRunner version.

```bash
br version

Shows: Version, build date, Python version
```

---

## Git Hooks

BuildRunner automatically installs git hooks:

**Pre-commit:**
- Validates features.json
- Runs quality checks
- Checks for secrets
- Runs linting

**Post-commit:**
- Auto-generates STATUS.md
- Updates metrics

**Pre-push:**
- Blocks incomplete features
- Runs full test suite
- Validates governance rules

**Bypass hooks:** `git commit --no-verify` (not recommended)

---

## MCP Tools (Claude Code)

BuildRunner exposes 9 tools via Model Context Protocol:

1. `feature_add` - Add new feature
2. `feature_complete` - Mark feature complete
3. `feature_list` - List all features
4. `feature_get` - Get feature details
5. `feature_update` - Update feature
6. `status_get` - Get project status
7. `status_generate` - Generate STATUS.md
8. `governance_check` - Run governance checks
9. `governance_validate` - Validate governance config

**Usage in Claude Code:**
```
Use BuildRunner to add feature "User Authentication"
Use BuildRunner to generate project status
```

---

## Environment Variables

```bash
BR_PROJECT_ROOT    # Override project root
BR_CONFIG_PATH     # Custom config file
BR_NO_TELEMETRY    # Disable telemetry (1/true)
BR_LOG_LEVEL       # Logging level (DEBUG/INFO/WARNING/ERROR)
BR_NO_HOOKS        # Disable git hooks (1/true)
```

---

## Exit Codes

- `0` - Success
- `1` - General error
- `2` - Configuration error
- `3` - Validation error
- `4` - Quality gate failure
- `5` - Test failure

---

*BuildRunner 3.1 - Complete Command Reference*
