---
description: Begin work - plan, execute, finish (simplified)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Task, TodoWrite
model: opus
---

@~/.claude/docs/begin-locks.md
@~/.claude/docs/begin-health-check.md
@~/.claude/docs/begin-completion.md
@~/.claude/docs/begin-report.md

# Begin Work

**9 steps. Execute in order.**

---

## Step 1: Lock

Sync with remote, find next incomplete phase, acquire atomic lock.

```bash
cd "$(git rev-parse --show-toplevel)"
git fetch origin 2>/dev/null && git pull --rebase origin main 2>/dev/null || true
```

Find BUILD spec: `ls -t .buildrunner/builds/BUILD_*.md | head -1`

**Lock mechanics:** See @begin-locks.md for:

- **HARD RULE: Lock Found = Ask User** (MANDATORY - always ask, never auto-proceed)
- Code-validated parallel work detection
- Atomic mkdir acquisition

**CRITICAL - LOCK FOUND = ASK USER (plain text, not AskUserQuestion):**
If ANY lock exists (regardless of heartbeat age), output this text and **STOP. Do not call any tools. Wait for the user to type their choice.**

```
🔒 LOCK DETECTED

Phase [N]: [Phase Name]
  Claimed: [timestamp] by [host]
  Heartbeat: [X] minutes ago
  Status: [ACTIVE/POSSIBLY STALE/LIKELY STALE]

A lock exists for this phase.

Reply with:
1 — Look for parallel work (Recommended) - Find another phase I can work on
2 — Acquire lock and work on this phase - Take over (removes existing lock)
```

**STOP HERE. Output the text above and do nothing else until the user replies.**

- If user replies "1" or "parallel" → Find Parallel Work (see @begin-locks.md)
- If user replies "2" or "acquire" → Remove existing lock, claim phase, proceed

**After lock acquired:**

1. Write initial heartbeat:

```bash
date -u +%Y-%m-%dT%H:%M:%SZ > ".buildrunner/locks/phase-${PHASE_NUM}/heartbeat"
```

2. Commit the lock claim, then proceed.

---

## Step 2: Code Health Check

**Before planning, run code health checklist.**

See @begin-health-check.md for the template. Check for:

- Existing code to reuse (don't recreate)
- Competing/parallel implementations
- Dead code in files you'll touch
- API key exposure

Output the filled checklist. Add any cleanup tasks to your plan.

---

## Step 2.5: Phase Breadcrumb

**Write breadcrumb file for multi-instance coordination:**

```bash
cat > .buildrunner/current-phase.json << EOF
{"phase": [N], "name": "[Phase Name]", "started": "$(date -u +%Y-%m-%dT%H:%M:%SZ)"}
EOF
date -u +%Y-%m-%dT%H:%M:%SZ > ".buildrunner/locks/phase-${PHASE_NUM}/heartbeat"
```

---

## Step 3: Plan

Design implementation approach **inline** (do NOT use EnterPlanMode — it clears context). Read the phase requirements, research relevant files, then write your plan directly.

Present the plan to the user for approval. Wait for approval before proceeding.

Write plan to `.buildrunner/plans/phase-[N]-plan.md`.

**After plan written, update heartbeat:**

```bash
date -u +%Y-%m-%dT%H:%M:%SZ > ".buildrunner/locks/phase-${PHASE_NUM}/heartbeat"
```

---

## Step 4: Execute

Build everything per the approved plan:

- Commit per logical task
- **Update heartbeat after each commit:**
  ```bash
  date -u +%Y-%m-%dT%H:%M:%SZ > ".buildrunner/locks/phase-${PHASE_NUM}/heartbeat"
  ```
- Run tests after changes
- Mark todo items complete as you go

---

## Step 5: Auto-Review

Launch review subagent:

```
Task tool with subagent_type="general-purpose"
Prompt: "Review implementation for Phase [N]. Check:
- All deliverables complete
- No TypeScript errors
- Tests pass
- No security issues
Report issues found."
```

---

## Step 6: Fixes

Apply fixes for any issues found in review. Commit each fix.

---

## Step 7: Complete Phase

See @begin-completion.md for the checklist. Required:

- Mark all task checkboxes `[x]` in BUILD spec
- Update phase Status to `✅ COMPLETE`
- Update Progress line at top of BUILD file

---

## Step 8: Release Lock + Build/Deploy

```bash
PHASE_NUM=[N]
rm -rf ".buildrunner/locks/phase-${PHASE_NUM}"
rm -f .buildrunner/current-phase.json
```

**Detect project type and run the correct build/deploy step:**

1. Check BUILD spec for `Deploy:` field (top of file) — use that command if present
2. If no Deploy field, detect from project files:

| Detection                                  | Project Type                   | Command                         |
| ------------------------------------------ | ------------------------------ | ------------------------------- |
| `capacitor.config.ts` exists               | Capacitor native (iOS/Android) | `npm run build && npx cap sync` |
| `wrangler.toml` or `wrangler.jsonc` exists | Cloudflare Workers/Pages       | `npm run build`                 |
| `electron-builder` in package.json         | Electron                       | `npm run build`                 |
| `expo` in package.json                     | React Native/Expo              | `npx expo export`               |
| `tauri.conf.json` exists                   | Tauri                          | `npm run build`                 |
| None of the above                          | Web app (dev server)           | Kill port 3000, `npm run dev &` |

**Run the detected command and report what was done.**

Commit the completion:

```bash
git add -A && git commit -m "complete: Phase [N] - [Phase Name]"
```

---

## Step 9: Final Report

See @begin-report.md for:

- BUILD completion check (grep for remaining phases)
- Template 9.1 if more phases remain
- Template 9.2 if BUILD is complete

Output the appropriate report.

---

## Rules

1. One phase per /begin invocation
2. Commit per logical task (not batched)
3. Never stop with lock held
4. Only pause for plan approval (Step 3)
5. Complete Steps 7-9 even if context is low
6. **LOCK FOUND = ASK USER** - Never auto-proceed when a lock exists. Always ask.
