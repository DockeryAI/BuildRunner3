# Automated Debugging - BuildRunner 3.0

BuildRunner 3.0 includes automated debugging features to capture errors, retry transient failures, and provide AI-friendly context for troubleshooting.

## Philosophy

Traditional debugging is reactive - you run a command, it fails, you manually investigate. BuildRunner makes debugging proactive:

1. **Auto-capture** - Command outputs automatically saved
2. **Auto-detect** - Error watcher monitors for problems
3. **Auto-retry** - Transient failures retry with backoff
4. **Auto-context** - Errors logged for AI analysis

## Features

### 1. Command Output Piping

**Problem:** Command outputs scroll off screen, making it hard for AI assistants to help debug.

**Solution:** `br pipe <command>` captures all output to context files.

```bash
# Traditional way (output lost)
pytest tests/
# Shows output, but it's gone after scrolling

# BuildRunner way (output preserved)
br pipe "pytest tests/" --tags test
# Output displayed AND saved to .buildrunner/context/command-outputs.md
```

**What's captured:**
- Full command executed
- Return code
- Standard output
- Standard error
- Timestamp
- Optional tags for categorization

**Benefits:**
- AI assistants can read full error messages
- History of command executions preserved
- Easy to share debugging context with team
- Failures captured even if terminal disconnects

### 2. Error Watcher Daemon

**Problem:** Errors hidden in log files go unnoticed until it's too late.

**Solution:** `br watch` monitors log files and auto-detects errors.

```bash
# Start monitoring
br watch

# Or run one-time scan
br watch --daemon
```

**What it detects:**
- Python exceptions and tracebacks
- Test failures (pytest, jest, etc.)
- Build/compilation errors
- Network/connection errors
- File system errors
- Git errors and merge conflicts

**What it does:**
- Monitors files matching patterns (`*.log`, `*.err`, etc.)
- Extracts error messages automatically
- Updates `.buildrunner/context/blockers.md`
- Categorizes errors by type

**Configuration:**
```yaml
watch:
  enabled: true
  patterns:
    - '*.log'
    - '*.err'
    - 'pytest.out'
    - 'build.log'
  check_interval: 2  # seconds
  auto_update_blockers: true
```

### 3. Auto-Retry with Exponential Backoff

**Problem:** Transient failures (network glitches, file locks, race conditions) cause builds to fail unnecessarily.

**Solution:** Automatic retries with intelligent backoff.

**How it works:**
1. Command fails
2. BuildRunner detects if failure might be transient
3. Waits (1s, then 2s, then 4s, then 8s)
4. Retries up to max attempts (default: 3)
5. Logs all attempts

**Retry delays (exponential backoff):**
- Attempt 1: Immediate
- Attempt 2: 1 second wait
- Attempt 3: 2 seconds wait
- Attempt 4: 4 seconds wait
- Attempt 5: 8 seconds wait

**Transient failures detected:**
- Network timeouts
- File locks
- Database connection errors
- Resource temporarily unavailable
- Rate limit errors

**Configuration:**
```yaml
debug:
  auto_retry: true
  max_retries: 3
  retry_delays: [1, 2, 4, 8]
```

**Example:**
```bash
# First attempt fails with "Connection refused"
# Waits 1s, retries
# Second attempt fails
# Waits 2s, retries
# Third attempt succeeds
✅ Command succeeded after 3 attempts
```

### 4. Debug Command

**Problem:** When things go wrong, you don't know where to start debugging.

**Solution:** `br debug` runs comprehensive diagnostics.

```bash
br debug
```

**Checks performed:**
1. **features.json validation** - Schema and syntax
2. **Governance verification** - Config and checksums
3. **Command failure analysis** - Pattern detection
4. **Common error patterns** - What's failing most

**Output example:**
```
🔍 Running diagnostics...
✅ features.json valid
✅ Governance configured
✅ Governance checksum valid

📊 Command Analysis:
  Total commands: 24
  Failed commands: 3
  Failure rate: 12.5%

⚠️  Common error patterns:
  • Connection errors
  • File not found errors

💡 Suggestions:
  • Use 'br pipe <command>' to capture outputs
  • Use 'br watch' to monitor for errors
  • Check .buildrunner/context/ for details
```

## Workflow Integration

### During Development

```bash
# Start error watcher in background
br watch --daemon

# Run commands with auto-capture
br pipe "npm test"
br pipe "npm run build"

# Check status
br status
```

### When Debugging

```bash
# Run diagnostics
br debug

# Check recent command outputs
cat .buildrunner/context/command-outputs.md

# Check auto-detected errors
cat .buildrunner/context/blockers.md

# Try command with retry
br pipe "flaky-test.sh"  # Auto-retries if fails
```

### With AI Assistants

```bash
# Capture output for AI analysis
br pipe "pytest tests/test_complex.py" --tags failing

# AI can now read full context
claude: "Analyze .buildrunner/context/command-outputs.md"

# AI suggests fix, you implement, verify
br pipe "pytest tests/test_complex.py" --tags fixed
```

## Context Files

BuildRunner creates AI-friendly context files in `.buildrunner/context/`:

### command-outputs.md

Format:
```markdown
---
## Command Output - 2025-11-17 10:30:00 [test, ci]

**Command:** `pytest tests/`
**Return Code:** 1
**Status:** ❌ FAILED

### Standard Output
```
(test output)
```

### Standard Error
```
(error messages)
```
```

### blockers.md

Format:
```markdown
---
## Auto-Detected Error - 2025-11-17 10:32:15

**Source:** `tests/test.log`
**Detected By:** Error Watcher Daemon

### Python Error
```
ValueError: Invalid configuration
```
```

## Configuration Options

```yaml
debug:
  auto_retry: true            # Enable auto-retry
  max_retries: 3             # Max retry attempts
  retry_delays: [1, 2, 4, 8] # Backoff delays (seconds)
  capture_output: true        # Capture command outputs
  log_to_context: true       # Write to context files

watch:
  enabled: true              # Enable error watcher
  patterns:                  # Files to monitor
    - '*.log'
    - '*.err'
    - 'pytest.out'
  check_interval: 2          # Check frequency (seconds)
  auto_update_blockers: true # Update blockers.md

piping:
  auto_timestamp: true        # Add timestamps
  max_output_size: 100000    # Max capture size (chars)
  context_file: '.buildrunner/context/command-outputs.md'
```

## Best Practices

1. **Always use `br pipe` for important commands** - Preserves context for debugging
2. **Enable `br watch` during active development** - Catches errors early
3. **Run `br debug` when stuck** - Provides diagnostic overview
4. **Tag outputs appropriately** - Makes searching easier
5. **Review context files regularly** - Spot patterns in failures
6. **Configure retry delays for your environment** - Slower networks need longer delays

## Limitations

- **Daemon mode** - Currently runs as foreground process (background mode pending)
- **Timeout** - Commands timeout after 5 minutes
- **Output size** - Truncated at max_output_size (default 100KB)
- **Pattern matching** - May miss errors with unusual formats

## Future Enhancements

- Smart failure classification (network vs code vs environment)
- Automatic issue creation from detected errors
- Machine learning for error pattern detection
- Integration with APM tools (Sentry, DataDog)
- Historical failure rate tracking

---

For CLI command reference, see [CLI.md](CLI.md).

For configuration details, see [BEHAVIOR_CONFIG.md](BEHAVIOR_CONFIG.md).
