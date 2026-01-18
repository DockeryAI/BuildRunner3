# Build: /begin Skill Optimization

**Created:** 2026-01-18
**Status:** Phase 1 In Progress
**Progress:** Phase 1 in_progress

## Overview

Fix post-implementation step loss during context compaction and align /begin skill with Opus 4.5 best practices. Core issue: Steps 5-9 exist only in skill memory and are lost when context compacts after ExitPlanMode.

## Parallelization Matrix

| Phase | Key Files | Can Parallel With | Blocked By |
|-------|-----------|-------------------|------------|
| 1 | begin.md, docs/*.md (NEW) | - | - |
| 2 | begin.md | - | 1 (same file) |
| 3 | begin.md, docs/*.md | - | 1, 2 (same files) |
| 4 | docs/*.md only | 2, 3 | 1 (files must exist) |
| 5 | READ only | - | 1, 2, 3, 4 |

## Phases

### Phase 1: Structural Refactor
**Status:** in_progress
**Goal:** Core skill reduced to ~5KB with reference docs for details
**Files:**
  - ~/.claude/commands/begin.md (MODIFY - major rewrite)
  - .buildrunner/docs/begin-locks.md (NEW)
  - .buildrunner/docs/begin-health-check.md (NEW)
  - .buildrunner/docs/begin-completion.md (NEW)
  - .buildrunner/docs/begin-report.md (NEW)
**Blocked by:** None
**Deliverables:**
- [ ] Create `.buildrunner/docs/` directory structure
- [ ] Extract lock mechanics (Steps 0.5, 1.5, 1.6) to `begin-locks.md`
- [ ] Extract code health checklist (Step 2.5) to `begin-health-check.md`
- [ ] Extract phase completion checklist (Step 7.4) to `begin-completion.md`
- [ ] Extract final report templates (Step 9) to `begin-report.md`
- [ ] Rewrite core `begin.md` with step sequence + @ references

**Success Criteria:** Core skill <6KB, all reference docs created, @ syntax verified working

---

### Phase 2: Post-Implementation Persistence Fix
**Status:** not_started
**Goal:** Steps 5-9 survive context boundary by being embedded in plan
**Files:**
  - ~/.claude/commands/begin.md (MODIFY - Step 3 template)
**Blocked by:** Phase 1 (modifies same file)
**Deliverables:**
- [ ] Modify Step 3 plan template to include post-impl tasks as checkboxes
- [ ] Add workflow state file write at Step 1.5 (active-workflow.json)
- [ ] Add workflow state file delete at Step 7.5
- [ ] Add plan preamble referencing workflow state file

**Success Criteria:** Post-impl tasks visible in plan output, workflow state file created/deleted correctly

---

### Phase 3: Language De-escalation
**Status:** not_started
**Goal:** Remove aggressive language, align with Opus 4.5 sensitivity
**Files:**
  - ~/.claude/commands/begin.md (MODIFY)
  - .buildrunner/docs/begin-locks.md (MODIFY)
  - .buildrunner/docs/begin-health-check.md (MODIFY)
  - .buildrunner/docs/begin-completion.md (MODIFY)
**Blocked by:** Phase 1, Phase 2 (same files)
**Deliverables:**
- [ ] Remove all "CRITICAL" instances
- [ ] Remove all "MANDATORY" instances
- [ ] Convert "MUST" caps to lowercase or reword
- [ ] Remove "BLOCKING", "NO EXCEPTIONS", "non-negotiable"
- [ ] Eliminate repeated explanations (state once)

**Success Criteria:** Zero aggressive keywords, no repeated concepts

---

### Phase 4: Add Multishot Examples
**Status:** not_started
**Goal:** Each checklist has one filled example for better compliance
**Files:**
  - .buildrunner/docs/begin-health-check.md (MODIFY)
  - .buildrunner/docs/begin-completion.md (MODIFY)
  - .buildrunner/docs/begin-report.md (MODIFY)
**Blocked by:** Phase 1 (files must exist first)
**After:** Phase 3 (logical sequence, CAN parallelize with Phase 2/3)
**Deliverables:**
- [ ] Add filled Code Health Checklist example to begin-health-check.md
- [ ] Add filled Phase Completion Checklist example to begin-completion.md
- [ ] Add filled Final Report examples (both variants) to begin-report.md

**Success Criteria:** Each reference doc has template + completed example

---

### Phase 5: Validation & Testing
**Status:** not_started
**Goal:** Verify fix works end-to-end
**Files:**
  - ~/.claude/commands/begin.md (READ - verification only)
  - .buildrunner/docs/* (READ - verification only)
**Blocked by:** Phases 1-4
**Deliverables:**
- [ ] Verify core skill <6KB
- [ ] Verify @ references resolve correctly
- [ ] Test /begin on a phase, force /compact mid-implementation
- [ ] Verify Steps 5-9 execute without prompting after compaction
- [ ] Document any edge cases found

**Success Criteria:** /begin completes full workflow including Steps 5-9 after context compaction

---

## Out of Scope
- Hooks-based workflow persistence (requires Claude Code changes)
- Automatic model switching back after /begin completes
- Multi-phase execution in single /begin run
- GUI/TUI for /begin status

## Session Log
[Will be updated by /begin]
