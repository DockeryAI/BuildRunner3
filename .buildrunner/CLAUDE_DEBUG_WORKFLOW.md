# Claude Code Debug Workflow

**Problem:** Claude finishes debugging, you test, find errors, now what?

## The Simple Workflow

### Step 1: Claude Finishes Work
```
Claude: "✅ All tests passing, everything debugged"
```

### Step 2: You Test & Find Errors
```bash
# In your terminal
$ pytest tests/test_auth.py
[errors appear in console]
```

### Step 3: Turn On Logging (One Command)
```bash
# In your terminal - run this ONCE
$ source .buildrunner/scripts/debug-aliases.sh && tlog pytest tests/test_auth.py
```

### Step 4: Tell Claude to Check Logs
```
You: "Check the debug logs"
```

Claude will automatically read `.buildrunner/debug-sessions/latest.log`

### Step 5: Claude Fixes & You Re-test
```bash
# In your terminal
$ tlog pytest tests/test_auth.py
```

Then back to Claude:
```
You: "Check the debug logs again"
```

**Repeat until fixed.**

---

## Even Simpler: Single Command Method

### When You Find Errors

Just run this ONE command in your terminal:
```bash
.buildrunner/scripts/log-test.sh pytest tests/test_auth.py
```

Then in Claude:
```
You: "Check .buildrunner/debug-sessions/latest.log"
```

Done. No aliases needed, no setup, just works.

---

## What's Happening Behind the Scenes

1. `log-test.sh` captures ALL console output (stdout + stderr)
2. Saves to `.buildrunner/debug-sessions/latest.log`
3. Claude can read that file directly
4. You never copy-paste

---

## Complete Workflow Example

### Starting State
```
Claude: "I've fixed the authentication bug. All tests should pass now."
```

### You Test
```bash
$ pytest tests/test_auth.py
# See errors in console
```

### You Log It
```bash
# Option A: With aliases loaded
$ source .buildrunner/scripts/debug-aliases.sh
$ tlog pytest tests/test_auth.py

# Option B: Direct script call
$ .buildrunner/scripts/log-test.sh pytest tests/test_auth.py
```

### You Tell Claude
```
You: "Still failing. Check .buildrunner/debug-sessions/latest.log"
```

### Claude Investigates
```
Claude: [reads log file]
Claude: "I see the issue - the JWT token is expired. Let me fix..."
[Claude makes changes]
Claude: "Fixed. Test again with: tlog pytest tests/test_auth.py"
```

### You Re-test
```bash
$ tlog pytest tests/test_auth.py
```

### You Confirm
```
You: "Check logs"
```

### Claude Verifies
```
Claude: [reads log file]
Claude: "✅ All tests passing now. No errors in log."
```

---

## Turn Logging On/Off

### Turn ON (once per terminal session)
```bash
source .buildrunner/scripts/debug-aliases.sh
```
Now `tlog` command is available.

### Turn OFF
Just close your terminal or:
```bash
unalias tlog
```

### Use Without Turning On
Don't want to load aliases? Use full path:
```bash
.buildrunner/scripts/log-test.sh pytest tests/test_auth.py
```

---

## Claude's Perspective

When you say "check debug logs" or "check latest.log", Claude will:

1. Read `.buildrunner/debug-sessions/latest.log`
2. Look for:
   - Failed commands
   - Error messages
   - Stack traces
   - Exit codes
3. Analyze and fix the issue
4. Ask you to re-test with logging on

---

## Quick Reference Card

### In Terminal
| Command | What It Does |
|---------|--------------|
| `source .buildrunner/scripts/debug-aliases.sh` | Load aliases (once) |
| `tlog <command>` | Run command with logging |
| `.buildrunner/scripts/log-test.sh <command>` | Log without aliases |

### In Claude
| What You Say | What Claude Does |
|--------------|------------------|
| "Check debug logs" | Reads latest.log |
| "Check .buildrunner/debug-sessions/latest.log" | Reads log file |
| "Show me the errors" | Extracts error summary |

---

## Common Scenarios

### Scenario 1: First Error
```
You: "Tests are failing"
You: [run] .buildrunner/scripts/log-test.sh pytest tests/
You: "Check .buildrunner/debug-sessions/latest.log"
Claude: [fixes issue]
```

### Scenario 2: Iterative Debugging
```
You: "Still broken"
You: [run] tlog pytest tests/
You: "Check logs"
Claude: [fixes]
You: [run] tlog pytest tests/
You: "Check logs"
Claude: "✅ Fixed"
```

### Scenario 3: Multiple Test Commands
```
You: [run] tlog pytest tests/test_auth.py
You: [run] tlog pytest tests/test_api.py
You: [run] tlog npm test
You: "Check logs - all three test runs"
Claude: [reads entire session]
```

---

## Pro Tips

1. **Load aliases once** at start of debug session
   ```bash
   source .buildrunner/scripts/debug-aliases.sh
   ```

2. **Always use `tlog`** when testing
   ```bash
   tlog pytest tests/
   tlog npm test
   tlog python script.py
   ```

3. **Just say "check logs"** to Claude
   ```
   You: "check logs"
   ```

4. **Keep logging on** during entire debug session

5. **Clear logs** when starting fresh
   ```bash
   clear-logs
   ```

---

## Troubleshooting

### "Claude can't find the log"
Make sure you ran a command with logging first:
```bash
tlog pytest tests/
```

### "Aliases not working"
Load them:
```bash
source .buildrunner/scripts/debug-aliases.sh
```

Or use full path:
```bash
.buildrunner/scripts/log-test.sh pytest tests/
```

### "I closed my terminal"
Logs are persistent! They're saved in `.buildrunner/debug-sessions/`
```
You: "Check .buildrunner/debug-sessions/latest.log from yesterday"
```

---

## The Bottom Line

**Before this system:**
```
You: [run test]
You: [see errors]
You: [copy errors]
You: [paste to Claude]
You: [explain context]
Claude: [fixes]
[repeat 10 times]
```

**With this system:**
```
You: tlog pytest tests/
You: "check logs"
Claude: [fixes]
You: tlog pytest tests/
You: "check logs"
Claude: "✅ done"
```

**That's it. No copy-pasting ever again.**
