# Lock Mechanics Reference

This document covers atomic lock acquisition, stale lock cleanup, and parallel work detection for the /begin command.

---

## Pre-Flight Checks (Step 0.5)

**Execute ALL checks BEFORE reading any BUILD spec.**

### 0.5.1 Sync with Remote

```bash
git fetch origin 2>/dev/null && git pull --rebase origin main 2>/dev/null || true
```

### 0.5.2 Scan ALL Existing Locks + Auto-Cleanup Stale Locks

**Check for lock DIRECTORIES (not files) - this is the atomic lock mechanism:**

```bash
mkdir -p .buildrunner/locks
for lock_dir in .buildrunner/locks/phase-*/; do
    if [ -d "$lock_dir" ]; then
        echo "=== LOCK FOUND: $lock_dir ==="
        cat "${lock_dir}claim.json" 2>/dev/null
    fi
done
```

**Build a map of ALL locked phases before proceeding.**

---

### Stale Lock Cleanup (AUTO-EXECUTE)

For each lock directory found, check if it's stale by comparing to BUILD spec status:

```bash
BUILD_FILE=$(ls -t .buildrunner/builds/BUILD_*.md 2>/dev/null | head -1)

for lock_dir in .buildrunner/locks/phase-*/; do
    if [ -d "$lock_dir" ]; then
        PHASE_NUM=$(echo "$lock_dir" | grep -oE '[0-9]+')

        # Check BUILD spec status for this phase
        STATUS=$(grep -A1 "### Phase ${PHASE_NUM}:" "$BUILD_FILE" 2>/dev/null | grep "Status:" | head -1)

        if echo "$STATUS" | grep -qE "COMPLETE|✅"; then
            echo "🧹 STALE LOCK: Phase ${PHASE_NUM} is COMPLETE but lock exists"
            rm -rf "$lock_dir"
            echo "   → Removed stale lock"
        fi
    fi
done
```

**Stale lock conditions (AUTO-REMOVE):**

| BUILD Spec Status | Lock Exists? | Action |
|-------------------|--------------|--------|
| `✅ COMPLETE` | Yes | **AUTO-REMOVE** - work is done, lock is orphaned |
| `in_progress` | Yes | **AUTO → Find Parallel Work** |
| `pending` / `not_started` | Yes | **AUTO → Find Parallel Work** |

**Why this is safe:**
- If phase is COMPLETE, work succeeded - lock is definitely stale
- For ALL other statuses, we CANNOT reliably detect if another instance is active

---

### Handle Non-Complete Locks

**For phases that are NOT marked COMPLETE, you CANNOT auto-remove locks.**

**Why "no uncommitted work" is NOT a valid staleness indicator:**
- An active instance may be in **planning phase** (reading files, no changes yet)
- An active instance may be in **code health check** (running searches)
- An active instance may be **waiting for user plan approval**
- An active instance may have **just claimed the lock** and is reading the spec

For any lock where BUILD spec status is NOT `COMPLETE`:

```
🔒 LOCK EXISTS - FINDING PARALLEL WORK

Phase [N]: [Phase Name] is locked (status: in_progress)
Lock claimed: [timestamp] by [host]

→ Proceeding to find parallel work...
```

**DO NOT ASK THE USER. AUTOMATICALLY proceed to find parallel work.**

---

### Why PID/Uncommitted Work Checks Are Broken

**PID check is fundamentally broken:**
- Claude Code spawns a new bash process for each Bash tool call
- `$$` captures that ephemeral bash subprocess PID, NOT Claude Code
- The bash process dies immediately after writing claim.json
- PID check will ALWAYS report "dead" even for active instances

**"No uncommitted work" check is fundamentally broken:**
- An active instance in planning/health-check/approval phase has no uncommitted work yet
- Cannot distinguish "crashed before writing code" from "actively reading/planning"

**After COMPLETE-only cleanup: If ANY non-COMPLETE lock remains → find parallel work automatically.**

---

### Check for Uncommitted Work (ONLY IF NO LOCKS FOUND)

**Skip this step if any locks found. Go directly to Find Parallel Work.**

This step only applies when there are NO locks (orphaned work from crashed session).

```bash
git status --porcelain | grep -E 'src/|supabase/|lib/'
```

**If uncommitted code exists AND no locks found:**
1. DO NOT proceed
2. Read files to identify which phase
3. Report and WAIT for user decision

```
⚠️ UNCOMMITTED WORK DETECTED (No active locks)

Files:
- src/hooks/useGenerateContent.ts
- src/components/QuickCreate/OutputEditor.tsx

This appears to be orphaned Phase 3 work (no lock exists).

Options:
1. Continue this work (I'll analyze and resume)
2. Stash/discard and start fresh
3. Different phase - tell me which
```

**Only if clean AND no locks:** Proceed to lock acquisition.

---

## Atomic Lock Acquisition (Step 1.5)

**This step uses atomic `mkdir` - only ONE instance can succeed.**

### Attempt Atomic Lock

```bash
PHASE_NUM=4
PHASE_NAME="Content Pool Migration"
BUILD_FILE="BUILD_smb-content-intelligence.md"

mkdir -p .buildrunner/locks

# ATOMIC OPERATION - only one process can succeed
if ! mkdir ".buildrunner/locks/phase-${PHASE_NUM}" 2>/dev/null; then
    echo "❌ LOCK FAILED - Phase ${PHASE_NUM} already claimed"
    cat ".buildrunner/locks/phase-${PHASE_NUM}/claim.json"
    # → Proceed to Find Parallel Work
fi
```

**If `mkdir` fails:** Another instance owns this phase. Find parallel work.

### Write Claim Metadata (Immediately After mkdir Success)

```bash
cat > ".buildrunner/locks/phase-${PHASE_NUM}/claim.json" << EOF
{
  "phase": ${PHASE_NUM},
  "name": "${PHASE_NAME}",
  "claimed_at": "$(date -u +%Y-%m-%dT%H:%M:%SZ)",
  "host": "$(hostname)",
  "build": "${BUILD_FILE}"
}
EOF
```

**Note:** No PID field - it's unreliable for staleness detection.

### Update BUILD Spec

Mark phase as `in_progress`:

```markdown
### Phase [N]
**Status:** in_progress
```

### Commit Lock (Broadcast)

```bash
git add -A && git commit -m "$(cat <<'EOF'
lock: claim Phase [N] - [Phase Name]

🤖 Generated with Claude Code
EOF
)"
```

**Only AFTER this commit succeeds:** Read full spec and proceed to planning.

**Output:**
```
✅ Locked Phase 4: Content Pool Migration
Commit: abc1234

Reading full spec and planning...
```

---

## Find Parallel Work (Step 1.6)

**Execute this step when lock fails OR when any lock exists.**

### File Extraction Checklist (MANDATORY)

**You MUST complete this checklist BEFORE determining parallelism.**

The "Depends on:" or "After:" fields in BUILD specs reflect CONCEPTUAL sequence, NOT file conflicts.
You MUST extract and compare actual files.

**Checklist (output this explicitly):**

```
📁 FILE EXTRACTION CHECKLIST

□ LOCKED phase files (from deliverables):
  - [file 1]
  - [file 2]
  - [file 3]

□ Candidate phase [N] files:
  - [file 1]
  - [file 2]

  Overlap with locked? [YES - list files / NO]

□ Candidate phase [M] files:
  - [file 1]
  - [file 2]

  Overlap with locked? [YES - list files / NO]

RESULT: Phases [X, Y] can parallelize (no file overlap)
```

**You MUST output this checklist before proceeding.**

---

### Smart Parallel Detection

**DO NOT just read listed dependencies. Analyze ACTUAL file conflicts.**

For each phase with status = "not_started":

1. **Extract touched files/directories:**

   **New format (preferred):** Look for `**Files:**` section in the phase:
   ```markdown
   **Files:**
     - src/hooks/useNewHook.ts (NEW)
     - src/components/Existing.tsx (MODIFY)
   ```

   **Legacy format:** Parse deliverable descriptions for file paths:
   - Look for component names → `src/components/*ComponentName*`
   - Look for hook names → `src/hooks/useHookName.ts`
   - Look for edge functions → `supabase/functions/function-name/`

2. **Compare with locked phase files:**
   - Extract same file patterns from locked phase deliverables
   - Check for overlapping directories or files

3. **Determine TRUE parallelism:**
   ```
   Phase can run in parallel IF:
     - Files/directories do NOT overlap with ANY locked phase
     - OR creates entirely NEW files (new edge function, new component)

   Phase CANNOT run in parallel IF:
     - Modifies same files as locked phase
     - Modifies files that locked phase also modifies
   ```

**Example Analysis:**
```
Locked: Phase 6 (Instagram Visual-First)
  Files: src/components/*Instagram*, src/components/QuickCreate/*

Checking Phase 7 (Story Content Gate):
  Files: supabase/functions/generate-content/, src/components/StoryInputModal (NEW)
  Overlap with Phase 6? NO (different edge function work, new component)
  → CAN PARALLELIZE ✅

Checking Phase 9 (Content Mix Visibility):
  Files: src/hooks/useContentMixRatio (NEW), src/components/ContentMixIndicator (NEW)
  Overlap with Phase 6? NO (calendar ≠ Instagram mockup)
  → CAN PARALLELIZE ✅
```

### Attempt Claims on Parallel Phases

For each phase that passes the file conflict check:
```
→ Attempt to claim this phase (go to lock acquisition with new phase)
```

**Claim the FIRST phase that succeeds.**

### Search for Independent Tasks (Advanced)

If no independent phases exist, check if locked phase has splittable tasks:

```
For each task in locked phase:
    If task has no dependencies on other tasks
    AND task touches completely different files:
        → Report as potential split opportunity
```

**Example:**
```
Phase 4 has potentially splittable tasks:
- 4.1-4.4: Content Pool migration (interdependent)
- 4.5-4.6: Deprecation cleanup (independent of 4.1-4.4)

Would you like me to claim tasks 4.5-4.6 only?
```

### No Parallel Work Available

**Only report this AFTER completing file analysis.**

**Case A: If NO remaining phases exist (all COMPLETE):**

```
🎉 BUILD COMPLETE

All phases in BUILD_[name].md have been completed.

Summary:
- Total phases: [N]
- All phases: ✅ COMPLETE

No further work required for this build.
```

**STOP HERE. BUILD IS DONE.**

---

**Case B: If remaining phases have file conflicts with locked phases:**

```
⏸️ NO PARALLEL WORK AVAILABLE

Currently locked:
- Phase 6: Instagram Visual-First Implementation
  Files: src/components/*Instagram*, generate-content edge function

Remaining phases analyzed:
- Phase 7: BLOCKED - modifies generate-content (same as Phase 6)
- Phase 8: BLOCKED - modifies generate-content (same as Phase 7)
- Phase 9: BLOCKED - true dependency on Phase 8 output
- etc.

All remaining phases have file conflicts. Stopping.
```

**STOP HERE. Do not proceed to planning. Do not offer to force-remove locks.**

---

## Lock Directory Structure

```
.buildrunner/
├── locks/
│   ├── phase-4/
│   │   └── claim.json
│   └── phase-7/           # (if parallel phases possible)
│       └── claim.json
├── builds/
│   └── BUILD_*.md
```

**claim.json format:**
```json
{
  "phase": 5,
  "name": "Platform Output Schema Consolidation",
  "claimed_at": "2026-01-01T10:30:00Z",
  "host": "Byrons-MacBook-Pro.local",
  "build": "BUILD_smb-content-intelligence.md"
}
```

**Note:** No PID field. PID-based staleness detection is fundamentally broken
for Claude Code (see above for explanation).

---

## Why Atomic mkdir Works

| Operation | Atomic? | Race Condition? |
|-----------|---------|-----------------|
| `cat > file` | No | Yes - both can write |
| `touch file` | No | Yes - both can create |
| `mkdir dir` | **Yes** | **No** - kernel guarantees one winner |

Two processes calling `mkdir` on same path:
- Process A: `mkdir phase-4` → SUCCESS
- Process B: `mkdir phase-4` → EEXIST (fails)

No race window. Guaranteed single winner.
