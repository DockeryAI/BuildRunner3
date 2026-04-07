# Week 1 Build Execution Prompts

**Workflow Reference:** See `.buildrunner/WORKFLOW_PRINCIPLES.md`

---

## Build 1A: Complete PRD Wizard

### Prompt for Claude Instance A

```
You are executing Build 1A: Complete PRD Wizard for BuildRunner 3.1.

CRITICAL INSTRUCTIONS:
1. Read `.buildrunner/WORKFLOW_PRINCIPLES.md` first
2. Follow `.buildrunner/builds/BUILD_1A_PRD_WIZARD.md` exactly
3. Work in BATCHES with verification gates (DO NOT skip verification)
4. Update CLAUDE.md and TodoWrite after each task
5. STOP at verification gates and report status

EXECUTION PATTERN:
- Work on Batch 1 (Tasks 1.1-1.3) ONLY
- After Batch 1: STOP and report completion
- Wait for verification approval
- Only then proceed to Batch 2 (Tasks 2.1-2.3)

START HERE:
1. Read the full task list: `.buildrunner/builds/BUILD_1A_PRD_WIZARD.md`
2. Follow setup instructions (git worktree, dependencies, state tracking)
3. Begin Batch 1: Core Infrastructure
   - Task 1.1: Create OpusClient (90 min)
   - Task 1.2: Create ModelSwitcher (90 min)
   - Task 1.3: Update Planning Mode (60 min)
4. Run Verification Gate 1 checklist
5. Report status and WAIT for approval

KEY REMINDERS:
- Update CLAUDE.md after EACH task
- Use TodoWrite to track progress
- No "build everything" - work in focused batches
- Test after each task
- Do not proceed past verification gates without confirmation

DO NOT:
- Skip verification gates
- Work on Batch 2 before Batch 1 is verified
- Create untested code
- Forget to update state tracking

When Batch 1 is complete, report:
---
✅ Batch 1 Complete: Core Infrastructure

Files Created:
- core/opus_client.py (387 lines)
- core/model_switcher.py (284 lines)
- core/planning_mode.py (156 lines added)

Tests: [X tests passing]
Coverage: [X%]

Verification Gate 1 Status:
- [ ] All files created: YES/NO
- [ ] Docstrings complete: YES/NO
- [ ] Tests pass: YES/NO
- [ ] No import errors: YES/NO
- [ ] CLAUDE.md updated: YES/NO
- [ ] TodoWrite updated: YES/NO

Ready for Batch 2: YES/NO
Blockers: [None / List any issues]
---

Begin execution now.
```

---

## Build 1B: Complete Design System

### Prompt for Claude Instance B

```
You are executing Build 1B: Complete Design System for BuildRunner 3.1.

CRITICAL INSTRUCTIONS:
1. Read `.buildrunner/WORKFLOW_PRINCIPLES.md` first
2. Follow `.buildrunner/builds/BUILD_1B_DESIGN_SYSTEM.md` exactly
3. Work in BATCHES with verification gates (DO NOT skip verification)
4. Update CLAUDE.md and TodoWrite after each task
5. STOP at verification gates and report status

EXECUTION PATTERN:
- Work on Batch 1 (Templates) ONLY
- After Batch 1: STOP and report completion
- Wait for verification approval
- Only then proceed to Batch 2 (Integration & Testing)

START HERE:
1. Read the full task list: `.buildrunner/builds/BUILD_1B_DESIGN_SYSTEM.md`
2. Follow setup instructions (git worktree, dependencies, state tracking)
3. Begin Batch 1: Create Templates
   - Task 1.1: 5 Industry YAML files (120 min)
   - Task 1.2: 5 Use Case YAML files (120 min)
4. Run Verification Gate 1 checklist
5. Report status and WAIT for approval

KEY REMINDERS:
- Update CLAUDE.md after EACH task
- Use TodoWrite to track progress
- Create complete, valid YAML files
- No placeholders or "TODO" sections
- Verify YAML syntax before committing

DO NOT:
- Skip verification gates
- Work on Batch 2 before Batch 1 is verified
- Create incomplete YAML files
- Forget to update state tracking

When Batch 1 is complete, report:
---
✅ Batch 1 Complete: Templates Created

Files Created:
- templates/industries/government.yaml (234 lines)
- templates/industries/legal.yaml (198 lines)
- templates/industries/nonprofit.yaml (187 lines)
- templates/industries/gaming.yaml (256 lines)
- templates/industries/manufacturing.yaml (223 lines)
- templates/use_cases/chat.yaml (187 lines)
- templates/use_cases/video.yaml (156 lines)
- templates/use_cases/calendar.yaml (198 lines)
- templates/use_cases/forms.yaml (234 lines)
- templates/use_cases/search.yaml (212 lines)

Tests: [X tests passing]

Verification Gate 1 Status:
- [ ] All 10 YAML files created: YES/NO
- [ ] YAML syntax valid: YES/NO
- [ ] All required sections present: YES/NO
- [ ] No placeholders/TODOs: YES/NO
- [ ] CLAUDE.md updated: YES/NO
- [ ] TodoWrite updated: YES/NO

Ready for Batch 2: YES/NO
Blockers: [None / List any issues]
---

Begin execution now.
```

---

## Concurrent Execution

Both builds run in PARALLEL in separate Claude instances:

### Terminal Window 1:
```bash
# Instance A working on Build 1A (PRD Wizard)
cd /Users/byronhudson/Projects/BuildRunner3
# Paste "Build 1A Prompt" to Claude Code instance A
```

### Terminal Window 2:
```bash
# Instance B working on Build 1B (Design System)
cd /Users/byronhudson/Projects/BuildRunner3
# Paste "Build 1B Prompt" to Claude Code instance B
```

Both instances work independently until both Batch 1s are complete.

---

## Verification Gate Coordination

### When Instance A Reports Batch 1 Complete:
1. Review CLAUDE.md in `../br3-prd-wizard/`
2. Check all verification criteria met
3. Run tests manually if needed
4. If approved: Reply "Approved - proceed to Batch 2"
5. If issues: Reply "Hold - [specific issues to fix]"

### When Instance B Reports Batch 1 Complete:
1. Review CLAUDE.md in `../br3-design-system/`
2. Check all YAML files valid and complete
3. Verify YAML syntax: `yamllint templates/industries/*.yaml templates/use_cases/*.yaml`
4. If approved: Reply "Approved - proceed to Batch 2"
5. If issues: Reply "Hold - [specific issues to fix]"

---

## When Both Builds Complete

### Both Instances Report Final Status:

**Instance A (Build 1A):**
```
✅ Build 1A Complete: PRD Wizard

Branch: build/v3.1-prd-wizard
Status: All tasks complete, tests passing, ready for integration

Files: [list]
Tests: [X passing, Y% coverage]
Ready for merge: YES
```

**Instance B (Build 1B):**
```
✅ Build 1B Complete: Design System

Branch: build/v3.1-design-system
Status: All tasks complete, tests passing, ready for integration

Files: [list]
Tests: [X passing, Y% coverage]
Ready for merge: YES
```

### Then Proceed to Integration:
Execute Build 1C (Week 1 Integration) to merge both branches.

---

## Monitoring Commands

### Check Build 1A Progress:
```bash
cd ../br3-prd-wizard
cat CLAUDE.md
git status
git log --oneline -5
```

### Check Build 1B Progress:
```bash
cd ../br3-design-system
cat CLAUDE.md
git status
git log --oneline -5
```

### Check Test Status:
```bash
# Build 1A
cd ../br3-prd-wizard && pytest tests/ -v --tb=short

# Build 1B
cd ../br3-design-system && pytest tests/ -v --tb=short
```

---

## Troubleshooting

### If Instance Gets Stuck:
1. Check CLAUDE.md for current state
2. Review TodoWrite status
3. Check for error messages in last commit
4. Provide specific guidance: "Complete Task X.Y, then update CLAUDE.md"

### If Tests Fail:
1. Read test output
2. Fix specific failing tests
3. Re-run verification gate
4. Do not proceed until tests pass

### If Verification Gate Fails:
1. Identify specific failing criteria
2. Fix issues
3. Re-run verification checklist
4. Get approval before proceeding

---

## Success Criteria

Week 1 is complete when:
- [x] Build 1A: All Batch 1 tasks complete ✓
- [x] Build 1A: All Batch 2 tasks complete ✓
- [x] Build 1A: Verification Gate 2 passed ✓
- [x] Build 1B: All Batch 1 tasks complete ✓
- [x] Build 1B: All Batch 2 tasks complete ✓
- [x] Build 1B: Verification Gate 2 passed ✓
- [x] Both branches pushed to GitHub ✓
- [x] Ready for Build 1C (Integration) ✓
