# BuildRunner 3.0 - CLI Documentation

Command-line interface for managing BuildRunner projects with automated debugging and behavior configuration.

## Installation

```bash
pip install buildrunner
```

## Core Commands

### Project Initialization

```bash
br init <project-name>
```

Initialize a new BuildRunner project. Creates `.buildrunner/` directory with:
- `features.json` - Feature tracking
- `behavior.yaml` - Project configuration
- `context/` - AI context files
- `governance/` - Governance rules

**Options:**
- `--force`, `-f` - Force re-initialization

### Feature Management

```bash
# Add a new feature
br feature add <name> [--id ID] [--priority PRIORITY]

# Mark feature as complete
br feature complete <feature-id>

# List all features
br feature list [--status STATUS]
```

**Example:**
```bash
br feature add "User Authentication" --id auth --priority high
br feature complete auth
br feature list --status in_progress
```

### Status & Progress

```bash
# Show project status
br status

# Generate STATUS.md
br generate
```

Status command displays:
- Project metrics (complete/in_progress/planned)
- Completion percentage
- Feature list with status icons

## Configuration Commands

### Managing Config

```bash
# Initialize global config
br config init --scope global

# Initialize project config
br config init --scope project

# Set configuration value
br config set <key> <value> [--scope SCOPE]

# Get configuration value
br config get <key>

# List all configuration
br config list
```

**Examples:**
```bash
# Enable auto-retry globally
br config set debug.auto_retry true --scope global

# Set max retries for this project
br config set debug.max_retries 5 --scope project

# Check current setting
br config get debug.auto_retry
```

### Configuration Hierarchy

1. **Project** (`.buildrunner/behavior.yaml`) - Highest priority
2. **Global** (`~/.buildrunner/global-behavior.yaml`) - Medium priority
3. **Defaults** (Built-in) - Lowest priority

Project settings override global, which override defaults.

## Automated Debugging Commands

### Pipe Command Output

```bash
br pipe <command> [--tags TAGS]
```

Runs command and automatically captures output to `.buildrunner/context/command-outputs.md`.

**Examples:**
```bash
br pipe "pytest tests/" --tags test,ci
br pipe "npm run build" --tags build
br pipe "git status"
```

Captured outputs include:
- Timestamp
- Command and return code
- Standard output and error
- Success/failure status

### Debug Diagnostics

```bash
br debug
```

Runs comprehensive diagnostics:
- Validates `features.json`
- Checks governance configuration
- Analyzes command failure patterns
- Provides auto-retry suggestions

Use when troubleshooting issues or after repeated failures.

### Error Watcher

```bash
br watch [--daemon]
```

Monitors log files for errors and auto-updates `.buildrunner/context/blockers.md`.

**Default patterns monitored:**
- `*.log`
- `*.err`
- `pytest.out`

Configure in `behavior.yaml`:
```yaml
watch:
  enabled: true
  patterns:
    - '*.log'
    - 'build.log'
```

## Sync (Placeholder)

```bash
br sync
```

Triggers Supabase sync. Implementation pending in Build 2B.

## Auto-Retry Logic

Commands automatically retry transient failures with exponential backoff:
- Attempt 1: Immediate
- Attempt 2: 1s delay
- Attempt 3: 2s delay
- Attempt 4: 4s delay

Configurable via:
```yaml
debug:
  auto_retry: true
  max_retries: 3
  retry_delays: [1, 2, 4, 8]
```

## Rich Formatting

CLI uses Rich library for professional output:
- Color-coded status messages
- Progress indicators
- Formatted tables
- Panels and layouts

Disable with:
```bash
br config set cli.use_rich false
```

## Tips

- Use `br debug` when things go wrong
- Use `br pipe` to capture output for AI analysis
- Use `br watch` during active development
- Configure globally, override per-project
- Check `.buildrunner/context/` for debugging info

## Exit Codes

- `0` - Success
- `1` - Error
- `130` - Interrupted (Ctrl+C)

---

For automated debugging details, see [AUTOMATED_DEBUGGING.md](AUTOMATED_DEBUGGING.md).

For behavior configuration details, see [BEHAVIOR_CONFIG.md](BEHAVIOR_CONFIG.md).
