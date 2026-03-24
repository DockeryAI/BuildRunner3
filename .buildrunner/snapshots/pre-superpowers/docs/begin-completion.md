# Phase Completion Reference

This document covers the mandatory phase completion checklist and lock release procedure.

---

## Phase Completion Steps

After implementation, review, and fixes are complete:

### 7.1 Extract Decisions
Scan conversation for architectural choices, patterns, trade-offs.

### 7.2 Log Decisions
```bash
br decision log "description" --type TYPE 2>/dev/null || \
echo "[$(date)] [TYPE] description" >> .buildrunner/decisions.log
```

### 7.3 Update BUILD Spec - Mark Deliverables
For each completed task in the phase, use Edit tool:
```markdown
- [x] [Completed task]
```

---

## Phase Completion Checklist

Output this checklist. Complete all boxes before releasing lock.

```
═══════════════════════════════════════════════════════════════════
📋 PHASE COMPLETION CHECKLIST - Phase [N]: [Phase Name]
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ DELIVERABLES                                                    │
├─────────────────────────────────────────────────────────────────┤
│ □ All task checkboxes marked [x] in BUILD spec                 │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STATUS FIELD                                                    │
├─────────────────────────────────────────────────────────────────┤
│ □ Phase **Status:** field changed to ✅ COMPLETE               │
│   (Used Edit tool to update BUILD_*.md)                        │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PROGRESS LINE (commonly forgotten)                              │
├─────────────────────────────────────────────────────────────────┤
│ □ Progress line at TOP of BUILD file updated                   │
│   (Added Phase [N] to "Complete" list)                         │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
ALL CHECKED? → Proceed to Release Lock
ANY MISSING? → Go back and complete before proceeding
═══════════════════════════════════════════════════════════════════
```

---

## Filled Example

```
═══════════════════════════════════════════════════════════════════
📋 PHASE COMPLETION CHECKLIST - Phase 4: Content Pool Migration
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ DELIVERABLES                                                    │
├─────────────────────────────────────────────────────────────────┤
│ ☑ All task checkboxes marked [x] in BUILD spec                 │
│   - [x] Create migration service                               │
│   - [x] Update useContentPool hook                             │
│   - [x] Add migration tests                                    │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ STATUS FIELD                                                    │
├─────────────────────────────────────────────────────────────────┤
│ ☑ Phase **Status:** field changed to ✅ COMPLETE               │
│   Edit: "**Status:** in_progress" → "**Status:** ✅ COMPLETE"  │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ PROGRESS LINE (commonly forgotten)                              │
├─────────────────────────────────────────────────────────────────┤
│ ☑ Progress line at TOP of BUILD file updated                   │
│   Edit: "Phases 1-3 Complete" → "Phases 1-4 Complete"          │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
ALL CHECKED? → Proceed to Release Lock ✅
═══════════════════════════════════════════════════════════════════
```

---

## Update Phase Status Field

Use Edit tool on BUILD_*.md to change the phase status:
- old_string: `**Status:** in_progress`
- new_string: `**Status:** ✅ COMPLETE`

---

## Update Progress Line (Often Missed)

The Progress line is at the TOP of the BUILD file (usually lines 5-10). This summarizes all phase statuses.

**Find current line:**
```bash
BUILD_FILE=$(ls -t .buildrunner/builds/BUILD_*.md 2>/dev/null | head -1)
grep "^Progress:" "$BUILD_FILE"
```

**Use Edit tool to add completed phase to "Complete" list.**

Example:
- old: `Progress: Phases 1-96 Complete; Phase 97 in_progress`
- new: `Progress: Phases 1-97 Complete`

---

## Release Lock

**Remove lock directory ONLY AFTER completion checklist is done:**

```bash
PHASE_NUM=[current phase number]
rm -rf ".buildrunner/locks/phase-${PHASE_NUM}"
```

**Verify removal:**
```bash
ls -la ".buildrunner/locks/phase-${PHASE_NUM}" 2>&1
# Expected: "No such file or directory"
```

**Output confirmation:**
```
🔓 Lock Released: Phase [N]
Verification: [directory removed / ERROR - still exists]
```

This allows other sessions to claim dependent phases.

---

## Final Commit

```bash
git add -A && git commit -m "$(cat <<'EOF'
unlock: Phase [N] complete - [Phase Name]

🤖 Generated with Claude Code
EOF
)"
```
