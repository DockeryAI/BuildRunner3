# BuildRunner Debug Workflow

**Problem Solved:** No more copy-pasting console output to Claude!

## Quick Start

### 1. Load Debug Aliases (One-time per shell session)
```bash
source .buildrunner/scripts/debug-aliases.sh
```

### 2. Run Tests with Auto-Logging
```bash
# Option A: Quick single command
tlog pytest tests/test_auth.py
tlog npm test
tlog python main.py

# Option B: Full debug session (interactive)
debug-start
```

### 3. Share Errors with Claude
```bash
# Extract just the errors
show-errors

# Copy everything to clipboard
copy-log

# Or just reference the file
# Tell Claude: "Check .buildrunner/debug-sessions/latest.log"
```

---

## Three Usage Modes

### Mode 1: Quick Test Logging (Recommended)
**Use when:** Running a single test command

```bash
# Load aliases
source .buildrunner/scripts/debug-aliases.sh

# Run test with auto-logging
tlog pytest tests/test_specific.py -v

# Extract errors for Claude
show-errors
```

**What happens:**
- Command output displayed normally
- Logged to `.buildrunner/debug-sessions/latest.log`
- Each command appended with timestamp
- No manual copy-paste needed

### Mode 2: Debug Session (Interactive)
**Use when:** Multiple test iterations, exploratory debugging

```bash
# Start debug session
debug-start

# Now in debug mode - all commands logged automatically
run pytest tests/
run npm test
run python script.py

# Exit when done
exit

# Share with Claude
show-errors
```

**What happens:**
- Enters interactive shell
- Every command automatically logged
- Session saved with unique ID
- Summary provided on exit

### Mode 3: BuildRunner Auto-Debug
**Use when:** Running full quality checks

```bash
# Run BuildRunner's comprehensive checks
br autodebug run

# Check status
br autodebug status

# Watch for changes
br autodebug watch
```

---

## Available Commands

### After sourcing debug-aliases.sh

| Command | Description | Example |
|---------|-------------|---------|
| `tlog <cmd>` | Run command with logging | `tlog pytest tests/` |
| `debug-start` | Start full debug session | `debug-start` |
| `show-errors` | Extract errors for Claude | `show-errors` |
| `show-log` | Show full latest log | `show-log` |
| `show-last` | Show last 50 lines | `show-last` |
| `copy-log` | Copy log to clipboard | `copy-log` |
| `clear-logs` | Clear all debug logs | `clear-logs` |

---

## Typical Workflow

### Scenario: Bug Fixing with Claude

1. **BuildRunner does initial checks**
   ```bash
   br autodebug run
   ```

2. **You find a bug and test**
   ```bash
   source .buildrunner/scripts/debug-aliases.sh
   tlog pytest tests/test_auth.py
   ```

3. **Extract error summary**
   ```bash
   show-errors
   ```

4. **Share with Claude**
   - Copy output from `show-errors`
   - Or: `copy-log` and paste
   - Or: Tell Claude: "Check .buildrunner/debug-sessions/latest.log"

5. **Iterate**
   ```bash
   # Make changes...
   tlog pytest tests/test_auth.py
   show-errors
   # Repeat until fixed
   ```

---

## Log File Locations

```
.buildrunner/debug-sessions/
├── latest.log              # Symlink to current session
├── session_20241124_143022.log
├── session_20241124_145133.log
└── session_20241124_151445.log
```

**latest.log** always points to your current debugging session

---

## Integration with Claude Code

### Method 1: Direct File Reference
```
You: "Check .buildrunner/debug-sessions/latest.log"
Claude: [reads file and analyzes errors]
```

### Method 2: Copy-Paste Errors
```bash
show-errors | pbcopy  # macOS
# Or use: copy-log
```
Then paste in Claude

### Method 3: Automatic Context (Future)
BuildRunner can be configured to automatically attach latest.log to Claude context

---

## Advanced Usage

### Custom Log Location
```bash
# Override log location
export LOGDIR="/custom/path/logs"
.buildrunner/scripts/log-test.sh pytest tests/
```

### Filter Specific Errors
```bash
# Show only Python tracebacks
grep -A 10 "Traceback" .buildrunner/debug-sessions/latest.log

# Show only assertion errors
grep -A 5 "AssertionError" .buildrunner/debug-sessions/latest.log

# Show only failed tests
grep "FAILED" .buildrunner/debug-sessions/latest.log
```

### Compare Sessions
```bash
# List all sessions
ls -lh .buildrunner/debug-sessions/

# Compare two sessions
diff session_20241124_143022.log session_20241124_145133.log
```

---

## Permanent Setup

Add to your `~/.zshrc` or `~/.bashrc`:

```bash
# Auto-load debug aliases for BuildRunner projects
if [ -f ".buildrunner/scripts/debug-aliases.sh" ]; then
    source .buildrunner/scripts/debug-aliases.sh
fi
```

Now debug commands available automatically when in BuildRunner projects.

---

## Troubleshooting

### "Command not found"
```bash
# Did you source the aliases?
source .buildrunner/scripts/debug-aliases.sh

# Or use full paths
.buildrunner/scripts/log-test.sh pytest tests/
```

### "No log file found"
```bash
# Run a test first to create the log
tlog pytest tests/
```

### "Permission denied"
```bash
# Make scripts executable
chmod +x .buildrunner/scripts/*.sh
```

---

## Benefits Over Manual Copy-Paste

✅ **Automatic** - No manual intervention needed
✅ **Complete** - Captures stderr and stdout
✅ **Timestamped** - Know when each test ran
✅ **Persistent** - Keep history of all debugging sessions
✅ **Fast** - Instant error extraction with `show-errors`
✅ **Clipboard** - One command to copy everything
✅ **Shareable** - Just reference a file path

---

## Example Session

```bash
# Start debugging
$ source .buildrunner/scripts/debug-aliases.sh
✅ Debug aliases loaded

# Run test
$ tlog pytest tests/test_auth.py -v
[test output...]
📝 Logged to: .buildrunner/debug-sessions/latest.log

# Extract errors
$ show-errors
📋 ERROR SUMMARY
🔴 FAILED COMMANDS:
  • 14:30:22 - pytest tests/test_auth.py -v
❌ ERROR MESSAGES:
  AssertionError: Expected 200, got 401

# Share with Claude
$ copy-log
✅ Log copied to clipboard
```

Now paste in Claude - no manual copying needed!

---

## Tips

1. **Use `tlog` for everything** - Make it a habit
2. **Check `show-errors` first** - Quick error summary
3. **Keep sessions** - Don't clear logs until bug is fixed
4. **Reference files** - Claude can read log files directly
5. **Combine with BuildRunner** - Use both `br autodebug` and `tlog`

---

*Generated: 2024-11-24*
*BuildRunner Version: 3.1.0*
