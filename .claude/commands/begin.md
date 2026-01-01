---
description: Begin work - plan, execute, review, fix, save (complete phase automation)
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, EnterPlanMode, Task
model: opus
---

# Begin Work (Complete Automation)

**One command. One approval. Entire phase completed.**

Load context → Plan → Execute → Review → Fix → Save → Done.

---

## What This Command Does

After you approve the plan, everything else is automatic:
1. Execute ALL tasks in the phase (parallel when possible)
2. Run tests after implementation
3. Commit completed work
4. Spawn review subagent (fresh context)
5. Auto-fix any issues found
6. Save session (decisions, spec updates)
7. Final commit and report

**You only approve once**: The plan.

---

## Step 0: Locate Project Root

```bash
# Works from any directory - finds git root or uses current
PROJECT_ROOT=$(git rev-parse --show-toplevel 2>/dev/null || pwd)
```

All operations use `$PROJECT_ROOT` as base.

---

## Step 0.5: Parallel Mode Detection

Check if multi-instance parallel execution is active:

```bash
# Check for existing parallel state
PARALLEL_STATE="$PROJECT_ROOT/.buildrunner/parallel_state.json"
if [ -f "$PARALLEL_STATE" ] && [ -s "$PARALLEL_STATE" ]; then
  PARALLEL_MODE="join"
else
  PARALLEL_MODE="coordinator"
fi
```

**If PARALLEL_MODE="coordinator":** This is the first instance - proceed to Step 0.6
**If PARALLEL_MODE="join":** Another instance is coordinating - proceed to Step 0.7

---

## Step 0.6: Coordinator Setup (First Instance Only)

**Skip this step if PARALLEL_MODE="join"**

Initialize parallel coordination for this BUILD:

1. **Find BUILD spec** and initialize coordinator:
```python
from core.parallel_build_coordinator import ParallelBuildCoordinator
from pathlib import Path

# Find BUILD spec
build_spec = next(Path(".buildrunner/builds").glob("BUILD_*.md"), None)
if build_spec:
    coord = ParallelBuildCoordinator(build_spec)
    instance_id = coord.register_instance()  # Creates state, becomes coordinator
    analysis = coord.build_dependency_graph()
```

2. **Report parallel capacity:**
```markdown
## Parallel Build Coordinator Initialized

**BUILD:** [spec name]
**Phases:** [N total]
**Max parallel instances:** [analysis.max_parallel]
**Available phases:** [list from get_available_phases()]

Other Claude instances can run `/begin` to join and claim available phases.
```

3. **Claim first available phase:**
```python
available = coord.get_available_phases()
if available:
    claimed_phase = available[0]
    coord.claim_phase(instance_id, claimed_phase)
```

4. **Store instance_id** for use in later steps (heartbeat, completion).

**Important:** The `instance_id` and `coord` objects are used throughout execution.

---

## Step 0.7: Join Setup (Secondary Instances Only)

**Skip this step if PARALLEL_MODE="coordinator"**

Join existing parallel build session:

1. **Register with existing coordinator:**
```python
from core.parallel_build_coordinator import ParallelBuildCoordinator
from pathlib import Path

build_spec = next(Path(".buildrunner/builds").glob("BUILD_*.md"), None)
coord = ParallelBuildCoordinator(build_spec)
instance_id = coord.register_instance()  # Joins existing state (not coordinator)
```

2. **Claim an available phase:**
```python
available = coord.get_available_phases()
if available:
    claimed_phase = available[0]
    if coord.claim_phase(instance_id, claimed_phase):
        # Successfully claimed - proceed
        pass
    else:
        # Race condition - another instance claimed it
        # Try next available or wait
        pass
else:
    # No phases available right now
    status = coord.get_status()
    # Report and optionally wait
```

3. **Report join status:**
```markdown
## Joined Parallel Build

**Coordinator:** [status['coordinator_id']]
**This instance:** [instance_id]
**Claimed phase:** [N] - [Phase Name]
**Other running instances:** [count]

Working on Phase [N] independently. Other instances handle other phases.
```

4. **If no phases available:**
```markdown
## No Phases Available

**Status:** All phases either claimed or waiting on dependencies
**Running instances:** [list]
**Completed phases:** [list]

Options:
- Wait for a phase to become available (dependencies complete or instance releases)
- Exit and check back later with `/begin`
```

To wait for availability:
```python
import time
while not coord.get_available_phases():
    print("Waiting for available phase...")
    time.sleep(30)
    coord.update_heartbeat(instance_id)  # Stay alive
    coord.cleanup_stale_instances()  # Recover abandoned phases
```

---

## Step 1: Load Context (CURRENT PHASE ONLY)

```bash
# Find BUILD spec (checks current dir first, then project root)
ls -t .buildrunner/builds/BUILD_*.md 2>/dev/null | head -1 || \
ls -t "$PROJECT_ROOT/.buildrunner/builds/BUILD_"*.md 2>/dev/null | head -1
```

**If spec found:** Read and identify the CURRENT phase only (first `in_progress` or `not_started` phase).

**IMPORTANT: Only load ONE phase. Do NOT plan multiple phases at once.**

**Output:**
```markdown
## [Project Name] - Phase [N] (of [Total])

**This phase:** [Phase Name]
**Progress:** [X/Y] tasks complete in this phase

**This session will implement:**
1. [ ] [Task A]
2. [ ] [Task B]
3. [ ] [Task C]

⚠️ Planning THIS PHASE ONLY. Next phase requires new /begin.

Entering plan mode...
```

**If no spec:** Ask what to work on, then proceed.

---

## Step 2: Parallel Analysis (THIS PHASE ONLY)

Assess remaining tasks **in the current phase only**:

| Task | Scope | Independent? |
|------|-------|--------------|
| [A] | `src/auth/` | Yes |
| [B] | `src/api/` | Yes |
| [C] | `src/api/auth.ts` | No (needs A) |

Group into:
- **Parallel batch 1**: [A, B] - run simultaneously
- **Sequential**: [C] - after batch 1

**Do NOT look at tasks in future phases.**

---

## Step 3: Plan Mode

**Immediately use EnterPlanMode tool.**

In plan mode:
- Explore codebase for patterns
- Design implementation for ALL tasks
- Use AskUserQuestion ONLY for genuine blockers

**Plan output:**
```markdown
## Phase [N] Implementation Plan

### Parallel Batch 1
**Task A:** [approach, files]
**Task B:** [approach, files]

### Sequential
**Task C:** [approach, files]

### Verification
- Tests: [list]

### NOT doing
- [Explicit exclusions]
```

**Exit plan mode when complete.**

---

## Step 4: Execute (After Plan Approval)

**On approval, execute the ENTIRE phase automatically.**

### 4.1 Commit-Per-Task Pattern (IMPORTANT)

**Commit after EACH task completes, not at the end.** This:
- Preserves state if context runs out
- Creates natural recovery points
- Enables git bisect for debugging

### 4.2 Parallel Tasks
Use Task tool with `run_in_background: true` for independent tasks.
When a parallel batch completes, commit ALL completed tasks:
```bash
git add -A && git commit -m "$(cat <<'EOF'
feat: [batch description - tasks A, B]

🤖 Generated with Claude Code
EOF
)"
```

### 4.3 Sequential Tasks
Implement in order after dependencies. **Commit after EACH sequential task:**
```bash
git add -A && git commit -m "$(cat <<'EOF'
feat: [task C description]

🤖 Generated with Claude Code
EOF
)"
```

### 4.4 Test After All Tasks
```bash
npm test 2>&1 | tail -50 || pytest 2>&1 | tail -50 || go test ./... 2>&1 | tail -50
```

### 4.5 Heartbeat Updates (Parallel Mode Only)

**If in parallel mode (coordinator or join), update heartbeat regularly to prevent 5-minute timeout:**

After each task or batch completes (before commit):
```python
# Keep instance alive - prevents stale detection
if coord and instance_id:
    coord.update_heartbeat(instance_id)
```

Also update progress for visibility to other instances:
```python
# completed_tasks / total_tasks_in_phase
if coord and instance_id:
    progress = completed_tasks / total_tasks
    coord.update_progress(instance_id, progress)  # Also updates heartbeat
```

**Note:** `update_progress()` automatically calls `update_heartbeat()`, so calling progress is sufficient.

### 4.6 Sync Point Waiting (Parallel Mode Only)

**If the claimed phase has dependencies that aren't complete yet:**

Before starting execution, verify dependencies are satisfied:
```python
if coord and claimed_phase:
    available = coord.get_available_phases()
    if claimed_phase not in available:
        # Dependencies not yet complete - wait
        print(f"Phase {claimed_phase} blocked on dependencies. Waiting...")

        import time
        while claimed_phase not in coord.get_available_phases():
            print("Dependencies incomplete. Checking again in 30s...")
            time.sleep(30)
            coord.update_heartbeat(instance_id)  # Stay alive while waiting

            # Also check for stale instances to recover
            stale = coord.cleanup_stale_instances()
            if stale:
                print(f"Recovered {len(stale)} stale instances")

        print(f"Dependencies satisfied. Starting Phase {claimed_phase}")
```

**Coordinator responsibility:** The coordinator instance should periodically call `cleanup_stale_instances()` to recover phases from instances that crashed or timed out.

---

## Step 5: Auto-Review (No Pause) - MANDATORY

**YOU MUST immediately use the Task tool after implementation completes. Do NOT ask permission. Do NOT skip this step.**

**Execute this Task tool call:**
```
subagent_type: "general-purpose"
model: "opus"
prompt: "Review these files for bugs, over-engineering, missing edge cases, security issues: [LIST THE CHANGED FILES HERE]. For each issue found, provide EXACT code fix (file path, line number, old code, new code). Output as actionable fixes, not suggestions."
```

**This is NOT optional. If you completed Step 4, you MUST execute Step 5.**

---

## Step 6: Auto-Fix (No Pause)

**Apply all fixes from review:**

1. For each issue, use Edit tool to apply the fix
2. Run tests to verify fixes don't break anything
3. If tests fail, revert that fix

**After fixes:**
```bash
git add -A && git commit -m "$(cat <<'EOF'
fix: review fixes

🤖 Generated with Claude Code
EOF
)"
```

---

## Step 7: Auto-Save (No Pause)

### 7.1 Extract Decisions
Scan conversation for architectural choices, patterns, trade-offs.

### 7.2 Log Decisions
```bash
br decision log "description" --type TYPE 2>/dev/null || \
echo "[$(date)] [TYPE] description" >> .buildrunner/decisions.log
```

### 7.3 Update BUILD Spec
Mark completed tasks:
```markdown
- [x] [Completed task]
```

Add session notes:
```markdown
## Session - [DATE]
**Completed:** [list]
**Decisions:** [list]
```

### 7.4 Check Phase Completion
If all tasks done:
```markdown
### Phase [N]
**Status:** ✅ COMPLETE
```

### 7.4.5 Mark Phase Complete in Parallel State (Parallel Mode Only)

**If in parallel mode, update the coordinator state:**
```python
if coord and instance_id:
    # Mark this instance's phase as complete
    coord.mark_completed(instance_id)

    # Report parallel build status
    status = coord.get_status()
    print(f"Phase complete. {status['phases']['completed']}/{status['phases']['total']} phases done.")

    # If all phases complete, the BUILD is done
    if status['phases']['completed'] == status['phases']['total']:
        print("All phases complete! Parallel build finished.")
        # Optionally clean up parallel_state.json
```

### 7.5 Final Commit
```bash
git add -A && git commit -m "$(cat <<'EOF'
chore: session save - spec updated

🤖 Generated with Claude Code
EOF
)"
```

---

## Step 8: Final Report

```markdown
## Phase [N] Complete

### Implementation
- Tasks completed: [N]
- Commits: [N]
- Tests: ✅ Passing

### Review
- Issues found: [N]
- Issues fixed: [N]

### Session Saved
- Decisions logged: [N]
- Spec updated: ✅

### Parallel Build Status (if applicable)
- Mode: [Coordinator / Joined]
- Instance ID: [instance_id]
- This phase: [N] ✅ Complete
- Total phases: [completed]/[total]
- Other instances: [list or "none"]

---

**Phase [N]:** [Complete / X remaining]

[If complete:] ⚠️ Start fresh session for Phase [N+1].
[If more work:] Run `/begin` again to continue.
[If parallel build complete:] All phases done! Consider running `br parallel finish` to clean up.
```

---

## Interruption Rules

**PAUSE only for:**
- Plan approval (the ONE required pause)
- Genuine ambiguity requiring clarification
- Unrecoverable errors

**DO NOT pause for:**
- Entering plan mode
- Starting implementation
- Running tests
- Starting review ← **MANDATORY, just do it**
- Applying fixes ← **MANDATORY, just do it**
- Saving session ← **MANDATORY, just do it**
- Committing

**CRITICAL: Steps 5, 6, 7 are NOT optional. If Step 4 completes, you MUST execute Steps 5-7 without asking.**

---

## Rules

1. **Single phase only**: NEVER plan or execute multiple phases at once
2. **One approval**: Plan approval triggers everything for THIS phase
3. **Commit per task**: Commit after each task/batch, not at end (prevents context loss)
4. **Always parallel**: Detect and parallelize by default
5. **Auto-review**: Fresh-context review after implementation
6. **Auto-fix**: Apply fixes without asking
7. **Auto-save**: Persist state for next session
8. **Git is memory**: Commits are recovery points if context compacts
9. **No manual /review or /save needed**: All included
10. **Phase complete = new session**: After phase done, start fresh for next phase
