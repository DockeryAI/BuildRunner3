# Week 1 Builds - Ready for Execution

**Status:** ✅ Complete and ready to execute
**Date:** January 17, 2025

---

## What's Ready

### ✅ Workflow Principles Document
**File:** `.buildrunner/WORKFLOW_PRINCIPLES.md`

Comprehensive workflow guidelines covering:
- PRD → Task List → Execution flow
- Directing Claude Code effectively
- Preventing missing components
- Batch size limits (3-5 tasks max)
- Verification gates
- Task decomposition strategies
- Memory management (CLAUDE.md + TodoWrite)
- Optimal execution patterns
- Anti-patterns to avoid

**Key Principle:** Claude performs best with **focused, bounded tasks** with clear success criteria. Think "surgical strikes" not "carpet bombing."

---

### ✅ Week 1 Atomic Task Lists

#### Build 1A: Complete PRD Wizard
**File:** `.buildrunner/builds/BUILD_1A_PRD_WIZARD.md`

**Features:**
- Real Anthropic Opus API integration
- Model switching protocol (Opus → Sonnet handoff)
- Planning mode auto-detection
- Full test coverage (85%+)

**Structure:**
- **Batch 1:** Core Infrastructure (3 tasks, ~4 hours)
  - Task 1.1: Create OpusClient (90 min)
  - Task 1.2: Create ModelSwitcher (90 min)
  - Task 1.3: Update Planning Mode (60 min)
  - ✅ Verification Gate 1

- **Batch 2:** Integration & Testing (3 tasks, ~4 hours)
  - Task 2.1: Complete Wizard (90 min)
  - Task 2.2: Write Tests (90 min)
  - Task 2.3: Update Docs (60 min)
  - ✅ Verification Gate 2

**Includes:**
- State tracking setup (CLAUDE.md)
- TodoWrite integration
- Complete code implementations
- Test specifications
- Acceptance criteria
- Verification checklists

---

#### Build 1B: Complete Design System
**File:** `.buildrunner/builds/BUILD_1B_DESIGN_SYSTEM.md`

**Features:**
- 5 missing industry profiles (Government, Legal, Nonprofit, Gaming, Manufacturing)
- 5 missing use case patterns (Chat, Video, Calendar, Forms, Search)
- Tailwind 4 integration
- Storybook component library generator
- Visual regression testing with Playwright

**Structure:**
- **Batch 1:** Create Templates (2 tasks, ~4 hours)
  - Task 1.1: 5 Industry YAML files (120 min)
  - Task 1.2: 5 Use Case YAML files (120 min)
  - ✅ Verification Gate 1

- **Batch 2:** Integration & Testing (3 tasks, ~4 hours)
  - Task 2.1: Tailwind Generator (90 min)
  - Task 2.2: Storybook Generator (90 min)
  - Task 2.3: Visual Regression (60 min)
  - Task 2.4: Tests & Docs (60 min)
  - ✅ Verification Gate 2

**Includes:**
- State tracking setup (CLAUDE.md)
- TodoWrite integration
- Complete YAML templates
- Generator implementations
- Test specifications
- Acceptance criteria

---

### ✅ Execution Prompts
**File:** `.buildrunner/builds/WEEK_1_PROMPTS.md`

Ready-to-use prompts for:
- **Build 1A:** Claude instance A prompt (copy-paste ready)
- **Build 1B:** Claude instance B prompt (copy-paste ready)
- Concurrent execution instructions
- Verification gate coordination
- Monitoring commands
- Troubleshooting guides

---

### ✅ Updated Master Plan
**File:** `BUILD_PLAN_V3.1-V3.4_ATOMIC.md`

Updated to:
- Reference workflow principles
- Indicate week-by-week atomic task list creation
- Mark Week 1 as complete
- Provide high-level structure for Weeks 2-20

---

## How to Execute Week 1

### Step 1: Review Workflow Principles
```bash
cat .buildrunner/WORKFLOW_PRINCIPLES.md
```
**Time:** 10 minutes
**Purpose:** Understand execution patterns and anti-patterns

---

### Step 2: Prepare Execution Environment

#### Terminal Window 1 (Build 1A):
```bash
cd /Users/byronhudson/Projects/BuildRunner3
# Open Claude Code instance A
```

#### Terminal Window 2 (Build 1B):
```bash
cd /Users/byronhudson/Projects/BuildRunner3
# Open Claude Code instance B
```

---

### Step 3: Launch Parallel Builds

#### In Claude Instance A:
```
Paste the "Build 1A Prompt" from .buildrunner/builds/WEEK_1_PROMPTS.md
```

#### In Claude Instance B:
```
Paste the "Build 1B Prompt" from .buildrunner/builds/WEEK_1_PROMPTS.md
```

Both instances will:
1. Read their respective atomic task lists
2. Create git worktrees
3. Install dependencies
4. Initialize state tracking (CLAUDE.md + TodoWrite)
5. Begin Batch 1 execution
6. Stop at Verification Gate 1 and report

---

### Step 4: Monitor Progress

#### Check Build 1A Status:
```bash
cd ../br3-prd-wizard
cat CLAUDE.md
git log --oneline -5
```

#### Check Build 1B Status:
```bash
cd ../br3-design-system
cat CLAUDE.md
git log --oneline -5
```

---

### Step 5: Verification Gates

#### When Instance A Reports "Batch 1 Complete":
1. Review CLAUDE.md
2. Check verification criteria (all checkboxes)
3. Run tests: `cd ../br3-prd-wizard && pytest tests/ -v`
4. If approved: Reply "Approved - proceed to Batch 2"
5. If issues: Reply "Hold - [specific issues]"

#### When Instance B Reports "Batch 1 Complete":
1. Review CLAUDE.md
2. Check all 10 YAML files created
3. Validate YAML: `yamllint templates/industries/*.yaml templates/use_cases/*.yaml`
4. If approved: Reply "Approved - proceed to Batch 2"
5. If issues: Reply "Hold - [specific issues]"

---

### Step 6: Completion

When both instances report "Build Complete":
- Verify both branches pushed to GitHub
- Check test coverage (target: 85%+)
- Review CLAUDE.md final status
- Proceed to Build 1C (Week 1 Integration)

---

## Key Features of This Approach

### ✅ Prevents Cognitive Overload
- Max 3-5 tasks per batch
- Clear boundaries between batches
- Verification gates force pauses

### ✅ Prevents Missing Components
- Explicit acceptance criteria
- Verification checklists
- State tracking (CLAUDE.md)
- TodoWrite progress tracking

### ✅ Enables Quality Control
- Test after each batch
- Verify before proceeding
- No "build everything" failures

### ✅ Maintains Context
- CLAUDE.md tracks what's done
- TodoWrite shows current state
- Clear handoff between batches

### ✅ Allows Recovery
- CLAUDE.md shows last known state
- Can resume from any batch
- Clear next steps always documented

---

## Estimated Timeline

### Build 1A (PRD Wizard):
- Batch 1: 4 hours
- Verification Gate 1: 30 min
- Batch 2: 4 hours
- Verification Gate 2: 30 min
- **Total: ~9 hours**

### Build 1B (Design System):
- Batch 1: 4 hours
- Verification Gate 1: 30 min
- Batch 2: 4 hours
- Verification Gate 2: 30 min
- **Total: ~9 hours**

### Parallel Execution:
**Total: ~9 hours** (both run simultaneously)

### Build 1C (Integration):
- Merge both branches: 30 min
- Integration testing: 1 hour
- Tag and push: 15 min
- **Total: ~2 hours**

**Week 1 Total: ~11 hours**

---

## Success Metrics

Week 1 is successful when:
- [x] Build 1A: All tasks complete, 85%+ coverage, tests passing
- [x] Build 1B: All tasks complete, 85%+ coverage, tests passing
- [x] Both branches pushed to GitHub
- [x] No verification gate failures
- [x] CLAUDE.md shows 100% completion
- [x] Ready for v3.1.0-alpha.1 release

---

## What Happens After Week 1

1. Execute Build 1C (Week 1 Integration)
2. Merge both branches to main
3. Tag v3.1.0-alpha.1
4. **Create Week 2 atomic task lists** (AI Review + Refactoring)
5. Repeat process for Week 2

---

## Files Created

Summary of all files ready for Week 1 execution:

```
.buildrunner/
├── WORKFLOW_PRINCIPLES.md         (New - 487 lines, workflow guidelines)
├── builds/
│   ├── BUILD_1A_PRD_WIZARD.md     (Updated - atomic task list with batches)
│   ├── BUILD_1B_DESIGN_SYSTEM.md  (New - atomic task list with batches)
│   ├── WEEK_1_PROMPTS.md          (New - execution prompts)
│   └── WEEK_1_READY.md            (This file - summary)
BUILD_PLAN_V3.1-V3.4_ATOMIC.md     (Updated - references workflow principles)
```

---

## Questions?

### How do I start?
Read WEEK_1_PROMPTS.md and paste the prompts into two Claude instances.

### What if something goes wrong?
Check CLAUDE.md for current state, review verification criteria, fix issues, re-run gate.

### Can I run builds sequentially instead of parallel?
Yes, but it will take ~18 hours instead of ~9 hours. Run Build 1A first, then Build 1B.

### What if tests fail?
Stop, fix the failing tests, re-run verification gate. Do not proceed until tests pass.

### How do I know what to work on next?
Check CLAUDE.md "Next Steps" section and TodoWrite status.

---

**Ready to Execute Week 1! 🚀**

Start by reading WEEK_1_PROMPTS.md and launching both Claude instances.
