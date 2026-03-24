# Lock Mechanics Reference

This document covers atomic lock acquisition, stale lock cleanup, and parallel work detection for the /begin command.

> **DO NOT USE AskUserQuestion ANYWHERE IN /begin.** It is broken with `skipDangerousModePermissionPrompt` (auto-resolves with empty answers, user never sees it). All user prompts must be plain text output followed by STOP — wait for user to type their reply.

---

## HARD RULE: Lock Found = Ask User (MANDATORY)

**When ANY lock exists for ANY phase, ALWAYS ask the user what they want to do.**

This rule overrides ALL heartbeat-based automatic decisions. Do not auto-proceed based on heartbeat age, uncommitted work, or any other heuristic. The user decides.

**HOW to ask:** Output the prompt as plain text, then STOP. Do not call any tools. Wait for the user to type their response.

### Lock Found Prompt (USE THIS EXACTLY)

When a lock is detected, **output this as plain text and STOP. Do NOT use AskUserQuestion (it is broken with skip-permissions mode).** Wait for the user to type their reply.

```
🔒 LOCK DETECTED

Phase [N]: [Phase Name]
  Claimed: [timestamp] by [host]
  Heartbeat: [X] minutes ago
  Status: [ACTIVE/POSSIBLY STALE/STALE based on heartbeat]

A lock exists for this phase.

Reply with:
1 — Look for parallel work (Recommended) - Find another phase I can work on
2 — Acquire lock and work on this phase - Take over (removes existing lock)
```

**STOP HERE. Do not call any tools. Wait for user to type 1 or 2.**

### Why This Rule Exists

- Heartbeat heuristics are imperfect (time zone issues, crashed sessions with fresh heartbeats)
- The user knows if they have another session running
- Prevents accidental work conflicts
- Simple and predictable behavior

---

## Heartbeat Mechanism

**Active instances update their heartbeat to signal they're still working.**

### Heartbeat File Location

```
.buildrunner/locks/phase-N/heartbeat
```

Contents: ISO timestamp of last activity.

### When to Update Heartbeat

Update heartbeat at these points (write current timestamp):

```bash
date -u +%Y-%m-%dT%H:%M:%SZ > ".buildrunner/locks/phase-${PHASE_NUM}/heartbeat"
```

**Update points:**
1. Immediately after lock acquisition (claim.json written)
2. After writing breadcrumb file (Step 2.5)
3. After plan file written (Step 3)
4. After each commit during execution (Step 4)
5. Before entering plan mode (last chance before potential context loss)

### Heartbeat Staleness Thresholds

| Heartbeat Age | Uncommitted Changes? | Recent Commits? | Verdict |
|---------------|---------------------|-----------------|---------|
| < 10 min | Any | Any | **ACTIVE** - do not touch |
| 10-30 min | Yes | Any | **ACTIVE** - working on changes |
| 10-30 min | No | Yes (< 30 min) | **ACTIVE** - recently committed |
| 10-30 min | No | No | **PROBABLY STALE** - ask user |
| > 30 min | No | No | **STALE** - auto-cleanup safe |
| > 30 min | Yes | Any | **PROBABLY STALE** - ask user (crashed mid-work?) |

### Check Heartbeat Function

```bash
check_heartbeat() {
    local lock_dir="$1"
    local heartbeat_file="${lock_dir}/heartbeat"

    if [ ! -f "$heartbeat_file" ]; then
        echo "NO_HEARTBEAT"
        return
    fi

    local heartbeat_time=$(cat "$heartbeat_file")
    local heartbeat_epoch=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$heartbeat_time" "+%s" 2>/dev/null || date -d "$heartbeat_time" "+%s" 2>/dev/null)
    local now_epoch=$(date "+%s")
    local age_minutes=$(( (now_epoch - heartbeat_epoch) / 60 ))

    echo "$age_minutes"
}
```

---

## Pre-Flight Checks (Step 0.5)

**Execute these checks before reading the BUILD spec.**

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

### Stale Lock Cleanup (WITH HEARTBEAT VALIDATION)

For each lock directory found, determine staleness using heartbeat + BUILD status:

```bash
BUILD_FILE=$(ls -t .buildrunner/builds/BUILD_*.md 2>/dev/null | head -1)

for lock_dir in .buildrunner/locks/phase-*/; do
    if [ -d "$lock_dir" ]; then
        PHASE_NUM=$(echo "$lock_dir" | grep -oE '[0-9]+')
        CLAIM_TIME=$(grep "claimed_at" "${lock_dir}/claim.json" 2>/dev/null | grep -oE '[0-9]{4}-[0-9]{2}-[0-9]{2}T[0-9]{2}:[0-9]{2}:[0-9]{2}Z')

        # Check BUILD spec status
        STATUS=$(grep -A1 "### Phase ${PHASE_NUM}:" "$BUILD_FILE" 2>/dev/null | grep "Status:" | head -1)

        # RULE 1: COMPLETE phases - always stale
        if echo "$STATUS" | grep -qE "COMPLETE|✅"; then
            echo "🧹 STALE: Phase ${PHASE_NUM} is COMPLETE"
            rm -rf "$lock_dir"
            continue
        fi

        # RULE 2: Check heartbeat
        HEARTBEAT_FILE="${lock_dir}/heartbeat"
        if [ -f "$HEARTBEAT_FILE" ]; then
            HEARTBEAT=$(cat "$HEARTBEAT_FILE")
            # Calculate age (macOS compatible)
            HEARTBEAT_EPOCH=$(date -j -f "%Y-%m-%dT%H:%M:%SZ" "$HEARTBEAT" "+%s" 2>/dev/null || echo "0")
            NOW_EPOCH=$(date "+%s")
            AGE_MINUTES=$(( (NOW_EPOCH - HEARTBEAT_EPOCH) / 60 ))

            if [ "$AGE_MINUTES" -lt 10 ]; then
                echo "✅ ACTIVE: Phase ${PHASE_NUM} - heartbeat ${AGE_MINUTES}m ago"
                echo "   → Finding parallel work..."
                continue
            fi
        else
            # No heartbeat file = old lock format, check claim time
            AGE_MINUTES=999
        fi

        # RULE 3: Check for uncommitted work matching this phase
        PHASE_FILES=$(grep -A20 "### Phase ${PHASE_NUM}:" "$BUILD_FILE" | grep -oE 'src/[^ ]+|supabase/[^ ]+' | head -5)
        HAS_UNCOMMITTED=false
        for f in $PHASE_FILES; do
            if git status --porcelain | grep -q "$f"; then
                HAS_UNCOMMITTED=true
                break
            fi
        done

        # RULE 4: Check for recent commits from this phase
        RECENT_COMMITS=$(git log --oneline --since="30 minutes ago" --grep="Phase ${PHASE_NUM}" 2>/dev/null | wc -l | tr -d ' ')

        # Decision matrix
        if [ "$AGE_MINUTES" -gt 30 ] && [ "$HAS_UNCOMMITTED" = false ] && [ "$RECENT_COMMITS" -eq 0 ]; then
            echo "🧹 STALE: Phase ${PHASE_NUM} - heartbeat ${AGE_MINUTES}m ago, no activity"
            rm -rf "$lock_dir"
        elif [ "$AGE_MINUTES" -gt 10 ] && [ "$HAS_UNCOMMITTED" = false ] && [ "$RECENT_COMMITS" -eq 0 ]; then
            echo "⚠️ POSSIBLY STALE: Phase ${PHASE_NUM} - heartbeat ${AGE_MINUTES}m ago"
            echo "   Claim: $CLAIM_TIME"
            echo "   No uncommitted changes, no recent commits"
            echo "   → Will ask user before removing"
            # Mark for user decision (don't auto-remove)
            touch "${lock_dir}/.possibly_stale"
        else
            echo "✅ ACTIVE: Phase ${PHASE_NUM} - uncommitted=$HAS_UNCOMMITTED, recent_commits=$RECENT_COMMITS"
            echo "   → Finding parallel work..."
        fi
    fi
done
```

**Stale lock decision matrix:**

| BUILD Status | Heartbeat Age | Uncommitted? | Recent Commits? | Action |
|--------------|---------------|--------------|-----------------|--------|
| `✅ COMPLETE` | Any | Any | Any | **AUTO-REMOVE** |
| Other | < 10 min | Any | Any | **ACTIVE** - find parallel |
| Other | 10-30 min | Yes | Any | **ACTIVE** - find parallel |
| Other | 10-30 min | No | Yes | **ACTIVE** - find parallel |
| Other | 10-30 min | No | No | **ASK USER** |
| Other | > 30 min | No | No | **AUTO-REMOVE** |
| Other | > 30 min | Yes | Any | **ASK USER** (crashed mid-work?) |

**Why heartbeat is reliable:**
- Active instance updates heartbeat at every significant action
- No heartbeat update + no git activity = instance is dead or stuck
- Avoids PID problems (bash subprocess PIDs are meaningless)

---

### Handle Non-Complete Locks

**For phases that are NOT marked COMPLETE, ALWAYS ASK THE USER.**

**See "HARD RULE: Lock Found = Ask User" at the top of this document.**

Regardless of heartbeat age, uncommitted work, or recent commits - if a lock exists and the phase is not COMPLETE, ask the user what they want to do.

**Heartbeat information is for USER CONTEXT only** (helps them decide), not for automatic decisions:
- < 10 min: Display as "ACTIVE"
- 10-30 min: Display as "POSSIBLY STALE"
- > 30 min: Display as "LIKELY STALE"

**Example prompt (output as plain text, then STOP):**

```
🔒 LOCK DETECTED

Phase 4: Content Pool Migration
  Claimed: 2026-01-22T10:30:00Z by Byrons-MacBook-Pro
  Heartbeat: 3 minutes ago
  Status: ACTIVE

A lock exists for this phase.

Reply with:
1 — Look for parallel work
2 — Acquire lock and work on this phase
```

**STOP HERE. Do not call any tools. Wait for user to type their choice.**

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

Output as plain text, then **STOP and wait for user to type their choice:**

```
⚠️ UNCOMMITTED WORK DETECTED (No active locks)

Files:
- src/hooks/useGenerateContent.ts
- src/components/QuickCreate/OutputEditor.tsx

This appears to be orphaned Phase 3 work (no lock exists).

Reply with:
1 — Continue this work (I'll analyze and resume)
2 — Stash/discard and start fresh
3 — Different phase - tell me which
```

**STOP HERE. Do not call any tools. Wait for user to type 1, 2, or 3.**

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

**Execute this step when lock fails OR when any ACTIVE lock exists.**

### Code-Validated Blocking (MANDATORY)

**DO NOT trust "Depends on:" in BUILD spec. Validate with actual code.**

For each candidate phase, perform this validation:

```
🔍 DEPENDENCY VALIDATION: Phase [N]

BUILD spec claims: "Depends on: Phase [X]"

CODE VALIDATION:
  1. Extract Phase N deliverable files
  2. Check if those files EXIST
  3. If exist: grep for imports/references to Phase X outputs
  4. If not exist: check if Phase X creates prerequisites

VERDICT: [TRUE DEPENDENCY | FALSE DEPENDENCY | FILE CONFLICT]
```

### Validation Commands

**Check if candidate phase files import from locked phase:**

```bash
# Extract locked phase outputs (components, hooks, functions)
LOCKED_EXPORTS=$(grep -E "export (function|const|class|interface|type)" src/path/to/locked-phase-file.ts | grep -oE '\b[A-Z][a-zA-Z]+\b' | head -10)

# Check if candidate phase imports them
for export in $LOCKED_EXPORTS; do
    grep -r "import.*$export" src/path/to/candidate-phase-files/ 2>/dev/null
done
```

**Check for file conflicts (both phases modify same file):**

```bash
# If same file appears in both phases' deliverables = FILE CONFLICT
```

**Check for type/interface dependencies:**

```bash
# Look for shared types that locked phase defines
grep -r "interface.*Phase[X]" --include="*.ts" src/
```

### File Extraction Checklist

Complete this checklist AFTER code validation.

```
📁 PARALLEL WORK ANALYSIS

LOCKED PHASES:
  Phase [X]: [Name]
    Status: ACTIVE (heartbeat [N]m ago)
    Files: [list from deliverables]
    Exports: [key functions/components created]

CANDIDATE PHASES:

  Phase [N]: [Name]
    Plan says: "Depends on: Phase X"

    CODE VALIDATION:
      □ Files exist? [YES/NO]
      □ Imports from Phase X? [YES - list / NO]
      □ File overlap with locked? [YES - list / NO]

    VERDICT: [CAN PARALLELIZE ✅ | BLOCKED - reason]

  Phase [M]: [Name]
    Plan says: "No dependencies"

    CODE VALIDATION:
      □ Files exist? [YES/NO]
      □ Imports from Phase X? [YES - list / NO]
      □ File overlap with locked? [YES - list / NO]

    VERDICT: [CAN PARALLELIZE ✅ | BLOCKED - reason]

RESULT: [Phases that can parallelize] OR [All blocked - reasons]
```

Output this checklist before proceeding.

---

### Smart Parallel Detection (Code-Validated)

**Analyze actual code dependencies, not just listed dependencies.**

For each phase with status = "not_started" or "pending":

1. **Extract touched files/directories from BUILD spec:**

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

2. **CODE VALIDATION (MANDATORY):**

   **For files that EXIST:**
   ```bash
   # Check for imports from locked phase
   grep -l "import.*from.*locked-phase-component" candidate-phase-files/
   ```

   **For files that DON'T EXIST yet:**
   - Check if they depend on types/interfaces from locked phase
   - Check if locked phase creates DB tables/functions they need

3. **Determine TRUE parallelism (code-validated):**

   | Condition | Verdict |
   |-----------|---------|
   | Files don't overlap AND no import dependencies | ✅ CAN PARALLELIZE |
   | Creates NEW files with no locked-phase imports | ✅ CAN PARALLELIZE |
   | Same files modified by both phases | ❌ FILE CONFLICT |
   | Candidate imports from locked phase outputs | ❌ TRUE DEPENDENCY |
   | Candidate needs DB schema from locked phase | ❌ TRUE DEPENDENCY |
   | Plan says "depends" but code shows no actual dependency | ✅ FALSE DEPENDENCY - can parallelize |

**Example Analysis (with code validation):**
```
Locked: Phase 6 (Instagram Visual-First)
  Files: src/components/InstagramMockup.tsx, src/hooks/useInstagramPreview.ts
  Exports: InstagramMockup, useInstagramPreview

Checking Phase 7 (Story Content Gate):
  Files: supabase/functions/generate-content/, src/components/StoryInputModal.tsx (NEW)
  Plan says: "Depends on: Phase 6"

  CODE VALIDATION:
    - StoryInputModal.tsx doesn't exist yet
    - generate-content/ exists, checking imports...
    - grep "InstagramMockup\|useInstagramPreview" supabase/functions/generate-content/
    - Result: NO MATCHES

  VERDICT: FALSE DEPENDENCY - Phase 7 doesn't actually import Phase 6 outputs
  → CAN PARALLELIZE ✅

Checking Phase 8 (Instagram Output Integration):
  Files: src/components/QuickCreate/OutputPanel.tsx (MODIFY)
  Plan says: "Depends on: Phase 6"

  CODE VALIDATION:
    - OutputPanel.tsx exists
    - grep "InstagramMockup\|useInstagramPreview" src/components/QuickCreate/OutputPanel.tsx
    - Result: FOUND - imports useInstagramPreview

  VERDICT: TRUE DEPENDENCY - Phase 8 imports from Phase 6
  → BLOCKED ❌
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

**Only report this AFTER completing CODE-VALIDATED analysis.**

**Case A: BUILD COMPLETE (all phases done):**

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

**Case B: ALL PHASES BLOCKED (with validation details):**

```
⏸️ ALL PHASES BLOCKED - VALIDATED

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
ACTIVE WORK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 6: Instagram Visual-First Implementation
  Status: ACTIVE (heartbeat 3m ago)
  Claimed: 2026-01-22T10:30:00Z by Byrons-MacBook-Pro
  Files being modified:
    - src/components/InstagramMockup.tsx
    - src/hooks/useInstagramPreview.ts

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
BLOCKED PHASES (CODE-VALIDATED)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Phase 7: Story Content Gate
  Plan claims: "No dependencies"
  CODE CHECK: supabase/functions/generate-content/index.ts
    → Line 45: import { InstagramMockup } from '../../src/...'
  VERDICT: ❌ TRUE DEPENDENCY - imports Phase 6 output
  Blocked by: Phase 6 (file dependency)

Phase 8: Output Panel Redesign
  Plan claims: "Depends on: Phase 6"
  CODE CHECK: src/components/QuickCreate/OutputPanel.tsx
    → Line 12: import { useInstagramPreview } from '../../hooks'
  VERDICT: ❌ TRUE DEPENDENCY - confirmed by code
  Blocked by: Phase 6 (import dependency)

Phase 9: Analytics Dashboard
  Plan claims: "Depends on: Phase 8"
  CODE CHECK: Files don't exist yet
    → Needs OutputPanel.tsx changes from Phase 8
  VERDICT: ❌ CHAIN BLOCKED - Phase 8 → Phase 6
  Blocked by: Phase 8 (which is blocked by Phase 6)

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
SUMMARY
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Active: 1 phase (Phase 6)
Blocked: 3 phases (all depend on Phase 6)
Parallel work: NONE AVAILABLE

Recommendation: Wait for Phase 6 to complete.
Estimated: Check back when Phase 6 heartbeat stops or commits appear.
```

**STOP HERE. TERMINATE /begin. Do not proceed to any further steps.**

Do not read current-phase.json, do not attempt to "continue" the work. Your analysis determined the lock is ACTIVE and owned by another instance. Exit cleanly with this report.

---

**Case C: POSSIBLY STALE LOCK BLOCKING WORK:**

Output as plain text, then **STOP and wait for user to type their choice:**

```
⚠️ BLOCKED BY POSSIBLY STALE LOCK

Phase 4: Content Pool Migration
  Claimed: 2026-01-22T08:15:00Z (2+ hours ago)
  Heartbeat: 45 minutes ago (STALE?)
  Uncommitted changes: None
  Recent commits: None

All remaining phases depend on Phase 4.

This lock MIGHT be stale (crashed instance), but there's no way to be 100% certain.

Reply with:
1 — Force-remove lock and claim Phase 4
2 — Wait longer (owner may return)
3 — Check other BUILDs for work
```

**STOP HERE. Do not call any tools. Wait for user to type 1, 2, or 3.**

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
