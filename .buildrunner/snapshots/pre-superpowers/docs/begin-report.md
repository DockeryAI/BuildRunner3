# Final Report Reference

This document covers the BUILD completion check and final report templates.

---

## Pre-Report Verification

**Before outputting any final report, verify these items are COMPLETE:**

```
□ Step 5: Auto-Review executed (Task tool with opus subagent)
□ Step 6: Fixes applied and committed
□ Step 7: BUILD spec updated, lock released
□ Step 8: Build/deploy completed for detected project type
```

**If ANY of the above are incomplete, DO NOT output final report. Go back and complete the missing step.**

**Check your todo list:** All items from Steps 4-9 must show status: completed.

---

## BUILD Completion Check

**Execute this check and output the checklist before writing any final report.**

**Execute this command:**

```bash
grep -c "Status:.*not_started\|Status:.*pending" .buildrunner/builds/BUILD_*.md 2>/dev/null || echo "0"
```

**Output this checklist (copy template and fill in):**

```
═══════════════════════════════════════════════════════════════════
📋 BUILD COMPLETION CHECK
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ GREP EXECUTED                                                   │
├─────────────────────────────────────────────────────────────────┤
│ Command: grep -c "not_started\|pending" BUILD_*.md              │
│ Result: [N matches / 0 matches / error message]                │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ REMAINING PHASES                                                │
├─────────────────────────────────────────────────────────────────┤
│ □ Phases with not_started status: [N or 0]                     │
│ □ Phases with pending status: [N or 0]                         │
│ □ Total remaining: [N or 0]                                    │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
RESULT: [BUILD COMPLETE / N PHASES REMAIN]

→ If BUILD COMPLETE: Use template 9.2 with 🎉 celebration
→ If PHASES REMAIN: Use template 9.1 with ⚠️ next phase notice
═══════════════════════════════════════════════════════════════════
```

---

## Template 9.1: More Phases Remain

Use this template when the BUILD is NOT complete:

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

### Lock Released

- Other instances can now claim Phase [N+1]

### Build/Deploy

- Target: [detected project type]
- Command: [what was run]
- Status: ✅ Ready

---

**Phase [N]:** Complete

⚠️ Start fresh session for Phase [N+1].
```

---

## Template 9.2: BUILD Complete

Use this template when ALL phases are done:

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

### Build/Deploy

- Target: [detected project type]
- Command: [what was run]
- Status: ✅ Ready

---

🎉 **BUILD COMPLETE**

All [TOTAL] phases in BUILD\_[name].md have been completed.
No further work required for this build.
```

---

## Filled Example: More Phases Remain

```
═══════════════════════════════════════════════════════════════════
📋 BUILD COMPLETION CHECK
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ GREP EXECUTED                                                   │
├─────────────────────────────────────────────────────────────────┤
│ Command: grep -c "not_started\|pending" BUILD_*.md              │
│ Result: 3 matches                                              │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ REMAINING PHASES                                                │
├─────────────────────────────────────────────────────────────────┤
│ ☑ Phases with not_started status: 2                            │
│ ☑ Phases with pending status: 1                                │
│ ☑ Total remaining: 3                                           │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
RESULT: 3 PHASES REMAIN

→ Using template 9.1 with ⚠️ next phase notice
═══════════════════════════════════════════════════════════════════

## Phase 4 Complete

### Implementation
- Tasks completed: 3
- Commits: 4
- Tests: ✅ Passing

### Review
- Issues found: 2
- Issues fixed: 2

### Session Saved
- Decisions logged: 1
- Spec updated: ✅

### Lock Released
- Other instances can now claim Phase 5

### Build/Deploy
- Target: [detected project type]
- Command: [what was run]
- Status: ✅ Ready

---

**Phase 4:** Complete

⚠️ Start fresh session for Phase 5.
```

---

## Filled Example: BUILD Complete

```
═══════════════════════════════════════════════════════════════════
📋 BUILD COMPLETION CHECK
═══════════════════════════════════════════════════════════════════

┌─────────────────────────────────────────────────────────────────┐
│ GREP EXECUTED                                                   │
├─────────────────────────────────────────────────────────────────┤
│ Command: grep -c "not_started\|pending" BUILD_*.md              │
│ Result: 0                                                      │
└─────────────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────────────┐
│ REMAINING PHASES                                                │
├─────────────────────────────────────────────────────────────────┤
│ ☑ Phases with not_started status: 0                            │
│ ☑ Phases with pending status: 0                                │
│ ☑ Total remaining: 0                                           │
└─────────────────────────────────────────────────────────────────┘

═══════════════════════════════════════════════════════════════════
RESULT: BUILD COMPLETE

→ Using template 9.2 with 🎉 celebration
═══════════════════════════════════════════════════════════════════

## Phase 12 Complete

### Implementation
- Tasks completed: 4
- Commits: 5
- Tests: ✅ Passing

### Review
- Issues found: 1
- Issues fixed: 1

### Session Saved
- Decisions logged: 2
- Spec updated: ✅

### Build/Deploy
- Target: [detected project type]
- Command: [what was run]
- Status: ✅ Ready

---

🎉 **BUILD COMPLETE**

All 12 phases in BUILD_smb-content-intelligence.md have been completed.
No further work required for this build.
```
