# Quick Start: Claude Debug Logging

## The Situation

```
Claude: "✅ Everything debugged!"
You: [test in terminal]
You: [see errors]
You: "Now what?"
```

## The Solution: 3 Steps

### Step 1: Run Your Test with `./clog`
```bash
./clog pytest tests/test_auth.py
```

### Step 2: Tell Claude
```
You: "check debug logs"
```

### Step 3: Repeat Until Fixed
```bash
./clog pytest tests/test_auth.py
```
```
You: "check debug logs"
```

**That's it.**

---

## Complete Example

### Initial State
```
[You're in Claude Code]
Claude: "I fixed the authentication bug. Tests should pass."
```

### You Test
```bash
# In your terminal
$ pytest tests/test_auth.py
FAILED - AssertionError: expected 200, got 401
```

### You Use clog
```bash
$ ./clog pytest tests/test_auth.py
[test runs and shows output]

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📝 Logged for Claude
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Tell Claude: 'check debug logs'
```

### Back to Claude
```
You: "check debug logs"

Claude: [reads .buildrunner/debug-sessions/latest.log]
Claude: "I see the issue. The JWT token validation is failing because..."
Claude: [fixes the code]
Claude: "Try again: ./clog pytest tests/test_auth.py"
```

### You Re-test
```bash
$ ./clog pytest tests/test_auth.py
[test runs]
```

### Back to Claude
```
You: "check debug logs"

Claude: [reads log]
Claude: "✅ All tests passing. Bug fixed."
```

---

## What Does `./clog` Do?

1. Runs your command (pytest, npm test, python script.py, etc.)
2. Shows output in your terminal normally
3. Saves everything to `.buildrunner/debug-sessions/latest.log`
4. Claude can read that file when you say "check debug logs"

---

## Common Commands

```bash
# Python tests
./clog pytest tests/

# JavaScript tests
./clog npm test

# Run a script
./clog python main.py

# Run anything
./clog <any command here>
```

---

## Turn Logging Off

Just don't use `./clog`:
```bash
# Without logging
$ pytest tests/

# With logging
$ ./clog pytest tests/
```

---

## What to Say to Claude

| You Say | Claude Does |
|---------|-------------|
| "check debug logs" | Reads latest.log and analyzes |
| "check logs" | Same as above |
| "show me the errors" | Extracts error summary |

---

## Pro Workflow

Keep this pattern during debugging:

```bash
# Terminal
./clog pytest tests/test_foo.py
```

```
# Claude
"check logs"
[Claude fixes]
```

```bash
# Terminal
./clog pytest tests/test_foo.py
```

```
# Claude
"check logs"
[Claude confirms fix]
```

Repeat until done. Never copy-paste again.

---

## Why This Works

**Before:**
- Run test
- See errors in console
- Select and copy errors
- Switch to Claude
- Paste
- Try to explain context
- Miss some error details
- Repeat

**Now:**
- Run `./clog pytest tests/`
- Say "check logs"
- Claude sees everything
- Claude fixes
- Repeat

**Saved time:** ~30 seconds per iteration
**Over 10 iterations:** 5 minutes saved
**Annoyance level:** Zero

---

## That's Everything

You now have:
- ✅ `./clog` command in project root
- ✅ Auto-logging to `.buildrunner/debug-sessions/latest.log`
- ✅ Claude knows to check that file
- ✅ No more copy-pasting

Just remember: `./clog <your test command>`
