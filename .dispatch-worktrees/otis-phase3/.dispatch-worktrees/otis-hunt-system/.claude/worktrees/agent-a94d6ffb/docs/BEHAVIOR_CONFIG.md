# Behavior Configuration - BuildRunner 3.0

BuildRunner 3.0 uses a hierarchical configuration system to customize behavior across all projects or per-project.

## Configuration Hierarchy

BuildRunner loads configuration from multiple sources with this priority order (highest to lowest):

1. **Project Config** - `.buildrunner/behavior.yaml` (project-specific)
2. **Global Config** - `~/.buildrunner/global-behavior.yaml` (all projects)
3. **Defaults** - Built-in hardcoded values

Project settings override global, which override defaults. This allows you to:
- Set reasonable defaults globally
- Override for specific projects
- Share global config across machines

## File Locations

### Global Configuration

**Location:** `~/.buildrunner/global-behavior.yaml`

**Purpose:** Default settings for ALL BuildRunner projects

**Create:**
```bash
br config init --scope global
```

**When to use:**
- Personal preferences (use_rich, show_progress)
- Machine-specific settings (retry_delays for slow networks)
- Organization-wide standards

### Project Configuration

**Location:** `.buildrunner/behavior.yaml`

**Purpose:** Settings for THIS project only

**Create:**
```bash
br config init --scope project
```

**When to use:**
- Project-specific requirements
- Overriding team defaults
- Experimental projects with different needs

## Configuration Sections

### Debug Settings

Controls automated debugging and retry behavior.

```yaml
debug:
  # Enable automatic retry for transient failures
  auto_retry: true

  # Maximum number of retry attempts
  max_retries: 3

  # Retry delays in seconds (exponential backoff)
  retry_delays: [1, 2, 4, 8]

  # Automatically capture command output
  capture_output: true

  # Log debug information to context files
  log_to_context: true
```

**Use cases:**
- Disable auto-retry for deterministic tests: `auto_retry: false`
- Increase retries for flaky CI: `max_retries: 5`
- Faster retries for local dev: `retry_delays: [0.5, 1, 2]`

### Watch Settings

Controls error watcher daemon behavior.

```yaml
watch:
  # Enable error watcher by default
  enabled: false

  # File patterns to monitor
  patterns:
    - '*.log'
    - '*.err'
    - 'pytest.out'

  # Check interval in seconds
  check_interval: 2

  # Auto-update blockers.md when errors detected
  auto_update_blockers: true
```

**Use cases:**
- Monitor specific logs: `patterns: ['build.log', 'deploy.log']`
- Reduce CPU usage: `check_interval: 10`
- Disable for production: `enabled: false`

### Piping Settings

Controls command output capture behavior.

```yaml
piping:
  # Add timestamps to captured outputs
  auto_timestamp: true

  # Maximum output size to capture (characters)
  max_output_size: 100000

  # Context file for command outputs
  context_file: '.buildrunner/context/command-outputs.md'
```

**Use cases:**
- Capture large outputs: `max_output_size: 500000`
- Custom location: `context_file: 'logs/commands.md'`
- Disable timestamps: `auto_timestamp: false`

### CLI Settings

Controls command-line interface behavior.

```yaml
cli:
  # Use rich formatting for output
  use_rich: true

  # Show progress indicators
  show_progress: true

  # Confirm destructive operations
  confirm_destructive: true

  # Show hints and tips
  show_hints: true
```

**Use cases:**
- CI/CD environments: `use_rich: false` (plain text)
- Headless scripts: `confirm_destructive: false`
- Experienced users: `show_hints: false`

### Governance Settings

Controls governance enforcement.

```yaml
governance:
  # Enforce rules on git commit
  enforce_on_commit: true

  # Verify checksums before operations
  verify_checksums: true

  # Strict enforcement mode
  strict_mode: true

  # Auto-generate STATUS.md on feature complete
  auto_generate_status: true
```

**Use cases:**
- Experimental projects: `strict_mode: false`
- Pre-production: `enforce_on_commit: false`
- Always generate status: `auto_generate_status: true`

## Managing Configuration

### Setting Values

```bash
# Set globally (affects all projects)
br config set debug.auto_retry true --scope global

# Set for this project only
br config set debug.max_retries 5 --scope project

# Default scope is project
br config set watch.enabled true
```

### Getting Values

```bash
# Get specific value
br config get debug.auto_retry

# List all config
br config list
```

### Viewing Sources

To see where each value comes from:

```bash
br config list
```

Values are merged: project → global → defaults.

## Configuration Examples

### Example 1: Flaky Test Suite

**Problem:** Tests fail intermittently due to timing issues.

**Solution:**
```yaml
# .buildrunner/behavior.yaml
debug:
  auto_retry: true
  max_retries: 5
  retry_delays: [1, 2, 4, 8, 16]
```

### Example 2: Slow Network

**Problem:** Network-dependent tests timeout frequently.

**Solution:**
```yaml
# ~/.buildrunner/global-behavior.yaml
debug:
  retry_delays: [2, 5, 10, 20]  # Longer delays
  max_retries: 4
```

### Example 3: CI/CD Pipeline

**Problem:** Rich output causes issues in CI logs.

**Solution:**
```yaml
# .buildrunner/behavior.yaml
cli:
  use_rich: false
  show_progress: false
  confirm_destructive: false
```

### Example 4: Active Development

**Problem:** Need maximum debugging info during development.

**Solution:**
```yaml
# .buildrunner/behavior.yaml
debug:
  capture_output: true
  log_to_context: true

watch:
  enabled: true
  patterns:
    - '*.log'
    - '*.err'
    - 'build/*.log'
    - 'test-results/*.xml'

piping:
  max_output_size: 500000  # Capture large outputs
```

### Example 5: Production Project

**Problem:** Need strict governance for production code.

**Solution:**
```yaml
# .buildrunner/behavior.yaml
governance:
  strict_mode: true
  enforce_on_commit: true
  verify_checksums: true

cli:
  confirm_destructive: true
```

## Dot Notation

Config keys use dot notation: `section.subsection.key`

Examples:
- `debug.auto_retry`
- `watch.patterns`
- `cli.use_rich`
- `governance.strict_mode`

When setting nested values, intermediate objects are created automatically.

## Data Types

Configuration values are automatically parsed:

```bash
# Boolean
br config set debug.auto_retry true    # → true (boolean)
br config set debug.auto_retry false   # → false (boolean)

# Integer
br config set debug.max_retries 5      # → 5 (number)

# String
br config set cli.theme dark           # → "dark" (string)
```

Lists and complex objects must be edited in YAML files directly.

## Best Practices

1. **Start with defaults** - Don't override unless necessary
2. **Use global for preferences** - Personal settings like `use_rich`
3. **Use project for requirements** - Project-specific needs
4. **Document overrides** - Add comments in YAML explaining why
5. **Version control** - Commit `.buildrunner/behavior.yaml` to git
6. **Don't commit global** - Keep `~/.buildrunner/` out of repos
7. **Review periodically** - Remove unnecessary overrides

## Troubleshooting

### Config not taking effect?

Check the hierarchy:
```bash
br config list
```

Project config might be overriding global.

### Want to reset to defaults?

Delete the config file:
```bash
rm .buildrunner/behavior.yaml
# or
rm ~/.buildrunner/global-behavior.yaml
```

### Need to see default values?

Check `cli/config_manager.py` in the source code, or:
```bash
br config list
```

Defaults are loaded if no config files exist.

## Schema

Full configuration schema:

```yaml
debug:
  auto_retry: boolean
  max_retries: integer
  retry_delays: [integers]
  capture_output: boolean
  log_to_context: boolean

watch:
  enabled: boolean
  patterns: [strings]
  check_interval: integer
  auto_update_blockers: boolean

piping:
  auto_timestamp: boolean
  max_output_size: integer
  context_file: string

cli:
  use_rich: boolean
  show_progress: boolean
  confirm_destructive: boolean
  show_hints: boolean

governance:
  enforce_on_commit: boolean
  verify_checksums: boolean
  strict_mode: boolean
  auto_generate_status: boolean
```

---

For CLI commands, see [CLI.md](CLI.md).

For automated debugging features, see [AUTOMATED_DEBUGGING.md](AUTOMATED_DEBUGGING.md).
