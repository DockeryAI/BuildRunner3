---
description: Run /begin post-implementation tasks with plan gap analysis, migration checks, and edge function deployment
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Task, TodoWrite
---

# Post-Implementation Tasks

Run these steps in order. Do not stop until all are complete. Execute autonomously — do not ask for permission at any step. Apply migrations, deploy edge functions, fix drift, and finalize without pausing for confirmation.

Three phases: **Verify** (all checks before anything is marked done) → **Infrastructure** (migrations, edge functions) → **Finalize** (mark complete, release lock, commit).

---

# Phase 1: Verify

All verification must pass before any finalization actions.

---

## Step 1: Find Active Phase

```bash
BUILD_FILE=$(ls -t .buildrunner/builds/BUILD_*.md 2>/dev/null | head -1)
LOCK_DIR=$(ls -d .buildrunner/locks/phase-* 2>/dev/null | head -1)
if [ -n "$LOCK_DIR" ]; then
    PHASE_NUM=$(basename "$LOCK_DIR" | sed 's/phase-//')
    cat "$LOCK_DIR/claim.json" 2>/dev/null
fi
echo "BUILD: $BUILD_FILE"
echo "PHASE: $PHASE_NUM"
```

If no lock exists, stop - nothing to complete.

---

## Step 2: Auto-Review

Launch review subagent:

```
Task tool with subagent_type="general-purpose"
Prompt: "Review implementation for Phase [N]. Check: all deliverables complete, no TypeScript errors, tests pass, no security issues. Report issues found."
```

---

## Step 3: Apply Fixes

Fix any issues found in review. Commit each fix separately.

---

## Step 4: Plan Gap Analysis (Both Directions)

Check for drift in BOTH directions — missing items AND unplanned additions.

### 4a: Gather Evidence

1. Read the BUILD spec phase that was just completed — every task, deliverable, and acceptance criterion
2. Read the git diff since the phase lock commit: `git diff [lock-commit]..HEAD --stat` and `git diff [lock-commit]..HEAD -- src/` to see all changes
3. Read the git log for this session's commits

### 4b: Forward Check — Planned but Not Built

For each planned item, determine status:

- **Implemented** — done and committed
- **Partially implemented** — started but incomplete
- **Deferred** — not touched
- **Skipped** — intentionally left out

### 4c: Reverse Check — Built but Not Planned

For each significant addition in the diff (new components, new edge function calls, new service files, new features, new props/state that enable unplanned functionality):

- Does it map to a deliverable in the BUILD spec phase?
- If not → flag as **UNPLANNED ADDITION**

Focus on functional additions. Ignore: import reordering, minor refactors within planned work, variable renames, comment changes.

### 4d: Resolve Drift Autonomously

If ALL planned items were implemented AND no unplanned additions → report "All planned items implemented, no drift" and continue.

If gaps exist in either direction → **fix them automatically**:

**Missing items:** Implement them now. If a missing item cannot be implemented (e.g., blocked by external dependency), defer it to the next phase and note it in the final report.

**Unplanned additions:** Keep them and add them to the BUILD spec as completed deliverables.

Report what was resolved:

```
📋 DRIFT RESOLVED

IMPLEMENTED (was missing):
1. [Item] - now complete

ADDED TO SPEC (was unplanned):
1. [Item] - added as deliverable

DEFERRED (blocked):
1. [Item] - [reason] - moved to next phase
```

Continue to next step.

---

# Phase 2: Infrastructure

Migrations and edge function checks run after all verification passes.

---

## Step 5: Check Pending Migrations

Look for any unapplied Supabase migrations:

```bash
# Find migration files
ls -la supabase/migrations/*.sql 2>/dev/null | tail -20

# Check remote migration status (if supabase CLI available)
npx supabase migration list 2>/dev/null || echo "Supabase CLI not available - check manually"
```

If new migration files exist that haven't been applied:

1. Review the SQL for safety (no RLS disabling, no destructive DROP operations on production data)
2. Apply immediately: `npx supabase db push` (or appropriate command for the environment)
3. Report what was applied in the final report

---

## Step 6: Check Edge Functions for Deployment

Look for edge functions that may need deployment:

```bash
# Find edge function directories
ls -d supabase/functions/*/ 2>/dev/null

# Check for uncommitted or recently changed edge functions
git diff --name-only HEAD~5 -- supabase/functions/ 2>/dev/null
git diff --cached --name-only -- supabase/functions/ 2>/dev/null
```

If edge functions were added or modified in this phase:

1. List each changed function
2. Deploy immediately: `npx supabase functions deploy [function-name]` for each
3. Report what was deployed in the final report

---

# Phase 3: Finalize

Only runs after all verification and infrastructure checks pass.

---

## Step 7: Update BUILD Spec

1. Mark all task checkboxes `[x]` in the phase
2. Change phase Status to `✅ COMPLETE`
3. Update Progress line at top of BUILD file

Verify with:

```bash
grep -A3 "### Phase $PHASE_NUM" "$BUILD_FILE" | head -5
```

---

## Step 8: Release Lock

```bash
rm -rf ".buildrunner/locks/phase-${PHASE_NUM}"
rm -f .buildrunner/current-phase.json
ls -la ".buildrunner/locks/phase-${PHASE_NUM}" 2>&1 || echo "Lock released"
```

---

## Step 9: Commit Completion

```bash
git add -A && git commit -m "$(cat <<'EOF'
unlock: Phase [N] complete - [Phase Name]

Co-Authored-By: Claude Opus 4.6 <noreply@anthropic.com>
EOF
)"
```

---

## Step 10: Build/Deploy

**Detect project type and run the correct build/deploy step:**

1. Check BUILD spec for `Deploy:` field — use that command if present
2. If no Deploy field, detect from project files:

| Detection                                  | Project Type     | Command                         |
| ------------------------------------------ | ---------------- | ------------------------------- |
| `capacitor.config.ts` exists               | Capacitor native | `npm run build && npx cap sync` |
| `wrangler.toml` or `wrangler.jsonc` exists | Cloudflare       | `npm run build`                 |
| `electron-builder` in package.json         | Electron         | `npm run build`                 |
| `expo` in package.json                     | Expo             | `npx expo export`               |
| `tauri.conf.json` exists                   | Tauri            | `npm run build`                 |
| None of the above                          | Web app          | Kill port 3000, `npm run dev &` |

Run the detected command and report what was done.

---

## Step 11: Final Report

Check for remaining phases:

```bash
grep -c "Status:.*not_started\|Status:.*pending" "$BUILD_FILE" 2>/dev/null || echo "0"
```

Output:

- If 0 remaining: "BUILD COMPLETE - all phases done"
- If N remaining: "Phase [N] complete. [X] phases remain."

---

## Verification Checklist

Before stopping, verify ALL of these:

```bash
# 1. Lock gone
ls .buildrunner/locks/phase-* 2>&1 | grep -q "No such file" && echo "✓ Lock released"

# 2. BUILD updated
grep "Phase $PHASE_NUM" "$BUILD_FILE" | grep -q "COMPLETE" && echo "✓ BUILD updated"

# 3. Build/deploy completed (project-type dependent)
echo "✓ Build/deploy step executed (check Step 10 output)"

# 4. Commit exists
git log -1 --oneline | grep -q "unlock:" && echo "✓ Unlock committed"

# 5. Migrations applied (if any existed)
ls supabase/migrations/*.sql 2>/dev/null && echo "✓ Migrations present" || echo "✓ No migrations (skip)"

# 6. Edge functions deployed (if any changed)
git diff --name-only HEAD~5 -- supabase/functions/ 2>/dev/null | head -1 | grep -q . && echo "⚠ Check edge functions deployed" || echo "✓ No edge function changes (skip)"
```

All checks must pass. If any fail, fix before stopping.
