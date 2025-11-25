# Debug Logging Scripts

**Stop copy-pasting console output to Claude!**

## Quick Start

```bash
# 1. Load aliases
source .buildrunner/scripts/debug-aliases.sh

# 2. Run test with auto-logging
tlog pytest tests/test_auth.py

# 3. Extract errors for Claude
show-errors

# 4. Copy to clipboard
copy-log
```

That's it! All your test output is logged automatically.

## What Got Created

| File | Purpose |
|------|---------|
| `debug-session.sh` | Interactive debug session with auto-logging |
| `log-test.sh` | Quick command wrapper with logging |
| `extract-errors.sh` | Extract error summary for Claude |
| `debug-aliases.sh` | Convenient shell aliases |

## Three Ways to Use

### 1. Quick Test (Recommended)
```bash
tlog pytest tests/test_foo.py
show-errors
```

### 2. Debug Session
```bash
debug-start
# Run multiple commands...
exit
show-errors
```

### 3. BuildRunner Auto-Debug
```bash
br autodebug run
br autodebug status
```

## Full Documentation

See: `.buildrunner/DEBUG_WORKFLOW.md`

## Log Location

`.buildrunner/debug-sessions/latest.log`
