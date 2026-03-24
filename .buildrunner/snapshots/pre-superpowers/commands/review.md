---
description: Manual review + fix + save (usually not needed - /begin includes this)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Task
model: opus
---

# Review + Fix + Save (Manual)

**Note:** `/begin` now automatically runs review at the end. Use this only for:
- Manual review of specific changes
- Re-running review after manual edits
- Standalone review outside of `/begin` workflow

---

## Step 1: Identify Files

```bash
git diff --name-only HEAD~5 2>/dev/null | head -20 || \
git status --porcelain | awk '{print $2}' | head -20
```

---

## Step 2: Spawn Review Subagent

```
Task tool:
- subagent_type: "general-purpose"
- model: "opus"
- prompt: [below]
```

**Prompt:**
```
Review these files for bugs, over-engineering, missing edge cases, security issues.
Files: [list]

For each issue, provide EXACT code fix (line number, old code, new code).
```

---

## Step 3: Auto-Fix

Apply all fixes from review using Edit tool. Run tests after. Revert if tests fail.

```bash
git add -A && git commit -m "fix: review fixes

🤖 Generated with Claude Code"
```

---

## Step 4: Save Session (MANDATORY - Execute All)

**Do NOT skip this step. Execute ALL commands below.**

### 4.1 Log Decisions
Extract architectural decisions, patterns, trade-offs from the conversation and log them:

```bash
# For each significant decision made during the session:
echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] [TYPE] description" >> .buildrunner/decisions.log
```

Types: `[ARCHITECTURE]`, `[PATTERN]`, `[TRADE-OFF]`, `[DECISION]`, `[FIX]`

### 4.2 Update BUILD Spec
- Mark completed tasks with `[x]`
- Add FIX notes if issues were corrected
- Update phase status if complete

### 4.3 Commit Save
```bash
git add -A && git commit -m "docs: save session - [brief description]

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>"
```

---

## Step 5: Report

```markdown
## Review Complete

- Issues found: [N]
- Issues fixed: [N]
- Session saved: ✅
- Phase progress: [X/Y]
```

---

## Rules

1. **Auto-fix**: Don't ask, just fix
2. **Test after**: Verify fixes work
3. **Always save**: Persist for next session
4. **One commit**: Review fixes + spec updates together
