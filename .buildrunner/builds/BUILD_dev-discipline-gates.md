# BUILD: Development Discipline Gates

**Build:** dev-discipline-gates
**Created:** 2026-03-23
**Total Phases:** 7
**Deploy:** N/A — global skill updates (applies to all BR3 projects)
Progress: Phases 1, 2, 5, 7 Complete; 3 of 7 phases remain

---

## Overview

Add development discipline enforcement to BR3's `/begin` workflow and supporting skills, inspired by Superpowers' strongest patterns. BR3 already leads in observability, deployment, and environment management — this build closes the gap in **pre-implementation testing, parallel execution, review rigor, and completion verification**.

All changes target global BR3 skills/docs in `~/.claude/`. No project-specific files are modified.

---

## Architecture Notes

### Design Philosophy

These gates integrate into the existing `/begin` 9-step workflow. They do NOT replace steps — they insert between existing steps or enhance them. The `/begin` skill stays under 6KB by referencing new `~/.claude/docs/` files.

### Soft Language Rule (Claude 4.6)

All new skill text uses soft guidance ("write tests for each deliverable before implementing") not force language ("CRITICAL: MUST write tests"). 4.6 overtriggers on aggressive instructions — per claude-opus-prompting-consistency.md.

### Opt-Out Convention

Phases that produce testable code get gates. Phases that are pure config, migrations, or design get a documented skip. The TDD and verification gates check the BUILD spec deliverable descriptions to determine applicability.

---

## Parallelization Matrix

| Phase | Key Files                                  | Can Parallel With              | Blocked By                                       | Status     |
| ----- | ------------------------------------------ | ------------------------------ | ------------------------------------------------ | ---------- |
| 1     | begin.md, docs/begin-tdd-gate.md (NEW)     | —                              | —                                                | ⏳ PENDING |
| 2     | begin.md, docs/begin-verification.md (NEW) | 1 (different insertion points) | —                                                | ⏳ PENDING |
| 3     | begin.md, docs/begin-review.md (NEW)       | —                              | 1, 2 (same file, must see final step numbering)  | ⏳ PENDING |
| 4     | begin.md                                   | —                              | 1, 2, 3 (depends on final step structure)        | ⏳ PENDING |
| 5     | docs/begin-health-check.md                 | 1, 2, 3                        | —                                                | ⏳ PENDING |
| 6     | begin.md, docs/begin-locks.md              | —                              | 4 (worktree option references parallel dispatch) | ⏳ PENDING |
| 7     | commands/brainstorm.md (NEW)               | 1-6                            | —                                                | ⏳ PENDING |

**Phases 1+2 can run in parallel** (insert at different points in begin.md).
**Phase 5 can run in parallel with 1-3** (different file).
**Phase 7 is fully independent** (new command, no begin.md changes).

---

## Phases

### Phase 1: TDD Gate

**Status:** ✅ COMPLETE
**Depends on:** None
**Goal:** Require failing tests before implementation code is written

Insert new Step 3.5 between Plan (Step 3) and Execute (Step 4) in `/begin`.

**Deliverables:**

- [x] **1.1** Create `~/.claude/docs/begin-tdd-gate.md` — TDD gate reference doc
  - Define RED-GREEN-REFACTOR cycle for BR3 context
  - Minimum: one test per deliverable that produces testable code
  - Skip criteria: deliverables that are pure config, SQL migrations, design assets, documentation
  - Skip detection: scan BUILD spec deliverable text for keywords (migration, config, design, docs)
  - Test file naming: match project's existing test convention (detect from `*.test.*` or `*.spec.*` patterns)
  - Gate rule: all new tests must FAIL before Step 4 begins (confirm via test runner output)
  - After Step 4 (Execute): re-run same tests, all must PASS
- [x] **1.2** Update `~/.claude/commands/begin.md` — add Step 3.5: TDD Gate
  - Insert between Step 3 (Plan) and Step 4 (Execute)
  - Reference `@~/.claude/docs/begin-tdd-gate.md`
  - Include skip logic: "If phase deliverables are non-testable (config, migrations, design), note skip reason and proceed to Step 4"
  - After Step 4 completes, add test re-run checkpoint: "Run the tests written in Step 3.5. All must pass before proceeding to Step 5."
- [x] **1.3** Update plan template in Step 3 to include a "Tests" section listing what will be tested per deliverable

**Files:**

- `~/.claude/docs/begin-tdd-gate.md` (NEW)
- `~/.claude/commands/begin.md` (MODIFY — add Step 3.5, update Step 4 with re-run)

**Success Criteria:** Running `/begin` on a phase with testable deliverables produces failing tests before any implementation. Tests pass after implementation. Non-testable phases skip cleanly with logged reason.

---

### Phase 2: Verification-Before-Completion Gate

**Status:** ✅ COMPLETE
**Depends on:** None
**Goal:** Require proof-of-function before marking a phase complete

Insert new Step 6.5 between Fixes (Step 6) and Complete Phase (Step 7).

**Deliverables:**

- [x] **2.1** Create `~/.claude/docs/begin-verification.md` — verification gate reference doc
  - Evidence types by deliverable category:
    - **UI feature:** Describe what the user sees, confirm component renders without error, or run e2e test
    - **API/data:** Show query/curl output with correct response shape
    - **Logic/algorithm:** Test output showing expected results including edge cases
    - **Config/infra:** Build succeeds, app starts, deploy preview accessible
  - Evidence format: plain text log in `.buildrunner/verification/phase-[N].md`
  - Pause rule: if evidence cannot be gathered automatically (e.g., requires physical device), pause and ask user to verify
  - Skip criteria: phases where all deliverables are already covered by passing tests from TDD gate AND no UI components (tests = sufficient evidence)
- [x] **2.2** Update `~/.claude/commands/begin.md` — add Step 6.5: Verification Gate
  - Insert between Step 6 (Fixes) and Step 7 (Complete Phase)
  - Reference `@~/.claude/docs/begin-verification.md`
  - Log evidence to `.buildrunner/verification/phase-[N].md`
  - If verification fails: loop back to Step 6 (Fixes) with specific failure details

**Files:**

- `~/.claude/docs/begin-verification.md` (NEW)
- `~/.claude/commands/begin.md` (MODIFY — add Step 6.5)

**Success Criteria:** Phase completion requires logged evidence. Verification file exists in `.buildrunner/verification/` for every completed phase. User is asked to verify when automated evidence is impossible.

---

### Phase 3: Two-Stage Review

**Status:** in_progress
**Depends on:** Phase 1, Phase 2 (need final step numbering in begin.md)
**Goal:** Split auto-review into spec compliance + code quality passes

Replace current Step 5 (Auto-Review) with two-pass review.

**Deliverables:**

- [ ] **3.1** Create `~/.claude/docs/begin-review.md` — two-stage review reference doc
  - **Pass 1 — Spec Compliance** (subagent):
    - Input: BUILD spec phase section + approved plan + git diff
    - Checks: each deliverable implemented? any missing? any unplanned additions?
    - Output: compliance report (PASS/FAIL per deliverable, list of gaps, list of unplanned additions)
  - **Pass 2 — Code Quality** (subagent):
    - Input: project CLAUDE.md + git diff + test results
    - Checks: TypeScript errors, security issues (OWASP top 10), dead code introduced, test coverage, performance concerns
    - Output: quality report (issues by severity: critical/warning/info)
  - Subagent scope constraints: each reviewer gets only its relevant context (narrow = better signal)
  - Two passes run sequentially (Pass 2 only runs if Pass 1 passes or user overrides)
- [ ] **3.2** Update `~/.claude/commands/begin.md` — replace Step 5 with two-stage review
  - Reference `@~/.claude/docs/begin-review.md`
  - Pass 1 subagent prompt: focused on BUILD spec deliverables only
  - Pass 2 subagent prompt: focused on code quality only
  - Combined output: single review report with both sections

**Files:**

- `~/.claude/docs/begin-review.md` (NEW)
- `~/.claude/commands/begin.md` (MODIFY — replace Step 5)

**Success Criteria:** Review produces two distinct reports (compliance + quality). Compliance report maps 1:1 to BUILD spec deliverables. Quality report catches TypeScript errors and security issues.

---

### Phase 4: Parallel Subagent Task Execution

**Status:** ⏳ PENDING
**Depends on:** Phase 1, 2, 3 (need final begin.md structure)
**Goal:** Dispatch independent tasks within a phase as parallel subagents

Enhance Step 4 (Execute) with dependency analysis and parallel dispatch.

**Deliverables:**

- [ ] **4.1** Add dependency analysis to Step 4 in `begin.md`
  - After plan approval, analyze task file lists for overlap
  - Tasks touching different files = independent → can parallelize
  - Tasks sharing any file = dependent → must run sequentially
  - Output: dependency graph (simple text: "Tasks A, C, D parallel | Task B after A | Task E after C, D")
- [ ] **4.2** Add parallel dispatch logic to Step 4
  - Independent tasks: dispatch as parallel subagents via Agent tool
  - Each subagent gets: task description, file list, relevant plan excerpt, project CLAUDE.md rules
  - Subagent constraint prompt: "Implement this task only. Do not modify files outside your assigned list. Do not explore beyond listed files."
  - Effort guidance: simple file creation → suggest `model: "sonnet"`, complex logic → `model: "opus"`
  - Collect results, verify no file conflicts, then proceed to review
  - Fallback: if <3 tasks in phase or all share files, execute sequentially (current behavior)
- [ ] **4.3** Update heartbeat during parallel execution — heartbeat updates after each subagent completes (not just after each commit)

**Files:**

- `~/.claude/commands/begin.md` (MODIFY — enhance Step 4)

**Success Criteria:** Phase with 4+ independent tasks dispatches them in parallel. Subagents stay within their file scope. Sequential fallback works for small/dependent phases. Heartbeat stays current during parallel work.

---

### Phase 5: Semantic Duplicate Detection

**Status:** ✅ COMPLETE
**Depends on:** None
**Goal:** Detect functions with similar logic (not just similar names) during health check

Extend `/dead` and `/begin` Step 2 health check.

**Deliverables:**

- [x] **5.1** Add semantic duplicate detection section to `~/.claude/docs/begin-health-check.md`
  - Scope: files listed in the current phase's Files section (not whole codebase)
  - What to detect: functions/methods that perform the same logical operation with different names or slightly different implementations
  - Detection approach: for each file in phase scope, read all function signatures + bodies, identify pairs with similar logic (same API calls, same data transformations, same conditional patterns)
  - Output: "Candidate duplicates" section in health check report with file:line references
  - Action: recommend consolidation opportunities, flag in plan — do not auto-refactor
- [x] **5.2** Add duplicate detection category to `~/.claude/commands/dead.md`
  - New analysis section: "Semantic Duplicates" — functions doing the same thing differently
  - Distinguish from existing "Parallel/Competing Implementations" (which finds competing features, not duplicate functions)

**Files:**

- `~/.claude/docs/begin-health-check.md` (MODIFY — add semantic duplicate section)
- `~/.claude/commands/dead.md` (MODIFY — add semantic duplicate analysis category)

**Success Criteria:** Health check flags candidate duplicate functions with file:line references. `/dead` includes semantic duplicate category in its report.

---

### Phase 6: Git Worktree Integration

**Status:** ⏳ PENDING
**Depends on:** Phase 4 (worktree option references parallel dispatch)
**Goal:** Offer worktree isolation when parallel phases are detected

Enhance `/begin` Step 1 lock detection to offer worktree creation.

**Deliverables:**

- [ ] **6.1** Update lock detection in `~/.claude/docs/begin-locks.md`
  - When lock is found AND user chooses "1" (find parallel work):
    - Current behavior: find another unlocked phase in same tree
    - New option: "3 — Create worktree for parallel phase"
    - If user picks 3: use existing `/worktree` command to create isolated worktree for the parallel phase
  - Worktree branch naming: `br3/phase-[N]-[short-desc]`
- [ ] **6.2** Add worktree merge guidance to `~/.claude/docs/begin-completion.md`
  - On phase completion in a worktree: prompt user to merge worktree branch back to main working branch
  - Provide merge command (not auto-execute — user confirms)
  - Clean up worktree after successful merge
- [ ] **6.3** Update `~/.claude/commands/begin.md` — add option 3 to lock detection output block

**Files:**

- `~/.claude/docs/begin-locks.md` (MODIFY — add worktree option)
- `~/.claude/docs/begin-completion.md` (MODIFY — add worktree merge guidance)
- `~/.claude/commands/begin.md` (MODIFY — add option 3 to lock prompt)

**Success Criteria:** Lock detection offers worktree option. Worktree creation delegates to existing `/worktree` command. Phase completion in worktree guides user through merge.

---

### Phase 7: Brainstorming Skill

**Status:** ✅ COMPLETE
**Depends on:** None
**Goal:** New `/brainstorm` command for Socratic design exploration with hard gate

Standalone new command — no changes to `/begin`.

**Deliverables:**

- [x] **7.1** Create `~/.claude/commands/brainstorm.md` — new brainstorm skill
  - Socratic questioning flow: 3-5 probing questions before proposing solutions
  - Question categories (via XML tags): scope, constraints, UX/interaction model, data model, edge cases, integration points
  - Hard gate: "Do not write code, create files, or generate BUILD specs until the user explicitly approves the design"
  - Output: design document written to `.buildrunner/brainstorm/[topic].md`
  - Incremental writing: update the file as the brainstorm progresses (not all at the end)
  - Integration with `/spec`: brainstorm output becomes input — "Run /spec to convert this design into a BUILD plan"
- [x] **7.2** Design document format
  - Sections: Problem Statement, Constraints, Proposed Architecture, Data Model, Key Decisions (with alternatives considered), Open Questions, Approval Status
  - Approval status tracks: DRAFT → APPROVED (user must explicitly approve)

**Files:**

- `~/.claude/commands/brainstorm.md` (NEW)

**Success Criteria:** `/brainstorm` produces a design document with Socratic questioning. No code is written until user approves. Document integrates with `/spec` as input.

---

## Out of Scope

- Visual brainstorming companion (WebSocket/HTML viewer) — evaluate after `/brainstorm` text version proves useful
- Multi-platform agent support (Cursor, Codex, Gemini) — not relevant, BR3 is Claude Code only
- 1% Rule meta-skill — BR3 skills already auto-invoke via frontmatter triggers
- Tmux interactive command control — BR3 workflow avoids interactive commands by design

---

## Updated `/begin` Step Map (After All Phases)

For reference — the final step sequence after all phases are implemented:

```
Step 1:   Lock (+ worktree option 3 from Phase 6)
Step 2:   Code Health Check (+ semantic duplicates from Phase 5)
Step 2.5: Phase Breadcrumb
Step 3:   Plan (+ Tests section in plan template from Phase 1)
Step 3.5: TDD Gate — write failing tests (Phase 1) [NEW]
Step 4:   Execute (+ parallel subagent dispatch from Phase 4)
Step 4.5: TDD Re-run — confirm tests pass (Phase 1) [NEW]
Step 5:   Two-Stage Review — spec compliance + code quality (Phase 3) [ENHANCED]
Step 6:   Fixes
Step 6.5: Verification Gate — proof-of-function (Phase 2) [NEW]
Step 7:   Complete Phase (+ worktree merge from Phase 6)
Step 8:   Release Lock + Build/Deploy
Step 9:   Final Report
```
