# Build: BR3 Universal Test Plan System

**Created:** 2026-04-09
**Status:** Phase 1 In Progress
**Deploy:** framework — skill files + dashboard workspace + cluster integration

## Overview

Every BR3 build gets a TEST_PLAN.md — a plain English testing document that lives alongside the BUILD spec. Tests are verified in a real browser via Playwright. No test passes without browser confirmation. The dashboard shows all tests per project, editable inline, with changes flowing bidirectionally to the filesystem. Mandatory after every single build phase — no exceptions, no shortcuts, no assumptions.

**Research basis:** Playwright Test Agents (Planner/Generator/Healer), Gauge markdown specs (ThoughtWorks/Microsoft), Testpad checklist UX, Testomat.io sync patterns, Octomind "AI at authoring not runtime" principle, QA Wolf flakiness data (28% selectors / 72% state+timing).

**The absolute rule:** PASS means a real browser confirmed it. Not code reading, not unit tests, not API calls. If Claude hasn't opened a browser and observed the expected result, the test is NOT PASS.

---

## READ FIRST

1. `/Users/byronhudson/.claude/commands/begin.md` — current /begin skill (Steps 3, 3.5, 4, 4.5, 6.5)
2. `/Users/byronhudson/.claude/docs/begin-tdd-gate.md` — current TDD gate reference
3. `/Users/byronhudson/.claude/docs/begin-verification.md` — current verification gate
4. `/Users/byronhudson/.claude/commands/autopilot.md` — current autopilot skill
5. `/Users/byronhudson/.buildrunner/dashboard/public/js/ws-builds.js` — dashboard workspace pattern
6. `/Users/byronhudson/.buildrunner/dashboard/events.mjs` — SSE/WebSocket event server
7. `/Users/byronhudson/.buildrunner/scripts/registry.mjs` — build registry
8. `/Users/byronhudson/Projects/BuildRunner3/core/cluster/node_tests.py` — Walter test runner
9. Research: `~/Projects/research-library/docs/techniques/playwright-claude-code-testing.md`
10. Research: `~/Projects/research-library/docs/techniques/continuous-testing-infrastructure.md`

---

## Parallelization Matrix

| Phase | Key Files                                                                                  | Can Parallel With | Blocked By |
| ----- | ------------------------------------------------------------------------------------------ | ----------------- | ---------- |
| 1     | begin.md (Steps 3,3.5,4,4.5), begin-test-plan.md, begin-test-healing.md, begin-tdd-gate.md | -                 | -          |
| 2     | begin.md (Step 6.5), begin-verification.md, settings.json, autopilot.md                    | -                 | 1          |
| 3     | ws-tests.js, index.html, events.mjs                                                        | 2                 | 1          |
| 4     | test-plan-watcher.mjs, test-plan-parser.mjs, test-plan-sync.mjs, dashboard package.json    | 2, 5              | 3          |
| 5     | node_tests.py, test_plan_parser.py, test_generator.py                                      | 3, 4              | 1          |
| 6     | governance.yaml, settings.json, spec.md                                                    | -                 | 1,2,3,4,5  |

---

## Phases

### Phase 1: TEST_PLAN.md Format + /begin Integration

**Status:** not_started
**Goal:** Standardized test document format with creation built into /begin. Every deliverable gets user-perspective test rows. Browser, terminal, and API test types all supported.

**Files:**

- /Users/byronhudson/.claude/docs/begin-test-plan.md (NEW)
- /Users/byronhudson/.claude/docs/begin-test-healing.md (NEW)
- /Users/byronhudson/.claude/commands/begin.md (MODIFY — Steps 3, 3.5, 4, 4.5 ONLY)
- /Users/byronhudson/.claude/docs/begin-tdd-gate.md (MODIFY)

**Blocked by:** None

**Deliverables:**

- [ ] **1.1 TEST_PLAN.md format specification** — begin-test-plan.md reference doc defining:
  - Rules header (6 rules, non-negotiable, read before any test work)
  - Feature sections with collapsible flow groups
  - 4-column rows: Precondition | User Action | Expected Result | Status
  - Per-row content hash stored as HTML comment `<!-- hash:abc123 -->` after each row
  - Status values: UNTESTED, PASS ✅, FAILED ❌, BLOCKED 🚫
  - Version tracking: Last Updated timestamp, Tested By session ID
  - Test type per row: Browser (Playwright) | Terminal (Vitest+exec) | API (Vitest+fetch)
  - Golden-file examples: 3 sample TEST_PLAN.md files (web app, CLI tool, API-only) for parser validation

- [ ] **1.2 XML enforcement rules** — In begin-test-plan.md, the following XML-tagged rules for Claude 4.6:

  ```
  <test_verification_rule> — PASS requires real browser/terminal confirmation
  <false_pass_prevention> — 5-question checklist before any PASS
  <rate_limit_and_guard_rule> — limiters must have TEST_MODE bypass
  <absolute_completion_rule> — do not stop until every row is PASS
  ```

- [ ] **1.3 Shared healing protocol** — begin-test-healing.md:
  - On test failure: re-snapshot DOM (browser) or re-run with debug output (terminal)
  - Attempt selector repair using getByRole/getByText fallbacks
  - Re-run test (attempt 1 of 2)
  - If still failing: deeper fix (check preconditions, state, data)
  - Re-run test (attempt 2 of 2)
  - If still failing after 2 healing attempts: mark FAILED, fix underlying code
  - If code fix fails 3 times: STOP and report — only acceptable stop condition

- [ ] **1.4 begin.md Step 3 modification** — After writing phase plan, create TEST_PLAN.md in `.buildrunner/builds/TEST_PLAN.md` (or append if exists). Every deliverable gets:
  - At least one user flow with specific interactions
  - Preconditions for each row (logged in, data exists, on correct page)
  - Expected results observable in browser/terminal
  - Test type assignment (browser/terminal/API)

- [ ] **1.5 begin.md Step 3.5 modification** — After writing failing unit tests, also:
  - Generate .spec.ts Playwright files from TEST_PLAN.md browser rows
  - Generate .test.ts Vitest files from TEST_PLAN.md terminal/API rows
  - Include TEST_PLAN.md row reference in comments: `// TEST_PLAN row: Feature.Flow.3`
  - Commit generated test files alongside unit tests

- [ ] **1.6 begin.md Step 4 modification** — After each commit during execution:
  - Run tests for features just built
  - Update TEST_PLAN.md statuses (UNTESTED → PASS or FAILED)
  - If any test is FAILED: invoke healing protocol before next task
  - Do not proceed to next task until FAILED is resolved

- [ ] **1.7 begin.md Step 4.5 modification** — Full test re-run:
  - Run ALL Playwright specs from TEST_PLAN.md
  - Run ALL Vitest specs from TEST_PLAN.md
  - Update all statuses
  - Heal before failing (shared protocol from 1.3)
  - Block phase if any FAILED after healing
  - Report: `TEST_PLAN: X/Y PASS, Z FAILED, W UNTESTED`

**Success Criteria:** Running /begin on any project creates TEST_PLAN.md with user-perspective test rows. All three test types supported. Healing protocol prevents premature FAILED status.

---

### Phase 2: Mandatory Post-Build Browser Verification Gate

**Status:** not_started
**Goal:** Every phase completion requires full TEST_PLAN.md verification. No skip criteria. No exceptions. Runs after every single build.

**Files:**

- /Users/byronhudson/.claude/commands/begin.md (MODIFY — Step 6.5 ONLY)
- /Users/byronhudson/.claude/docs/begin-verification.md (MODIFY)
- /Users/byronhudson/.claude/settings.json (MODIFY — Stop hook section only)
- /Users/byronhudson/.claude/commands/autopilot.md (MODIFY)

**Blocked by:** Phase 1 (needs format spec and Step 3/4 changes committed)

**Deliverables:**

- [ ] **2.1 Step 6.5 rewrite** — Replace current verification gate with TEST_PLAN.md-driven gate:
  - Parse TEST_PLAN.md from project's `.buildrunner/builds/`
  - Count statuses: PASS, FAILED, UNTESTED, BLOCKED
  - Run every non-PASS test via appropriate runner (Playwright for browser, Vitest for terminal/API)
  - Update statuses in TEST_PLAN.md after each run
  - If any remain FAILED after healing: BLOCK phase completion
  - If any remain UNTESTED: run them, then re-evaluate
  - Walter gate still applies on top (existing behavior preserved)
  - **NO SKIP CRITERIA** — removed entirely. Backend phases, config phases, migration phases ALL run browser verification because any change can break user flows.

- [ ] **2.2 Stop hook update** — Modify existing test verification Stop hook in settings.json:
  - Parse TEST_PLAN.md if it exists in the project
  - Count non-PASS rows
  - If any non-PASS: `BLOCK: TEST_PLAN.md has X incomplete tests` with list of failing/untested items
  - If TEST_PLAN.md doesn't exist: graceful degradation (warn, don't block — until Phase 6 activates full enforcement)

- [ ] **2.3 Autopilot regression gate** — Add to autopilot.md between-phase logic:
  - After completing phase N, before starting phase N+1:
  - Run full TEST_PLAN.md verification (all rows, all phases, not just current)
  - If any prior-phase test now fails (regression): block, report which phase broke
  - Fix regression before starting next phase

- [ ] **2.4 begin-verification.md update** — Remove skip criteria language, add TEST_PLAN.md as primary evidence source, document the "runs after every build" rule with no exceptions

**Success Criteria:** Claude cannot complete any phase or stop working until every TEST_PLAN.md row shows PASS. Autopilot catches regressions between phases.

---

### Phase 3: Dashboard Test Workspace

**Status:** not_started
**Goal:** New "Tests" workspace in the BR3 dashboard. Testpad-style checklist UX — all tests visible at once, editable inline, keyboard-driven. Real-time status updates from Claude and Walter.

**Files:**

- /Users/byronhudson/.buildrunner/dashboard/public/js/ws-tests.js (NEW)
- /Users/byronhudson/.buildrunner/dashboard/public/index.html (MODIFY)
- /Users/byronhudson/.buildrunner/dashboard/events.mjs (MODIFY)

**Blocked by:** Phase 1 (needs format spec for data structure)

**Deliverables:**

- [ ] **3.1 ws-tests.js workspace** — Self-contained workspace following ws-builds.js pattern:
  - Project selector dropdown populated from registry (existing `registry` global)
  - Progress bar: green/red/grey segments showing PASS/FAILED/UNTESTED ratio
  - Feature sections as collapsible accordion groups
  - Flow groups within features as indented sub-sections
  - Test rows as checklist items: `[status badge] Precondition → Action → Expected Result`
  - Status badges: green checkmark (PASS), red X (FAILED), grey dot (UNTESTED), orange block (BLOCKED)
  - Injected CSS following existing workspace pattern (style.textContent)

- [ ] **3.2 Inline editing** — Testpad-style editing, no forms:
  - Click any cell (precondition, action, result) to edit in-place
  - Auto-save on blur or Enter (no save button)
  - Keyboard navigation: arrow keys between rows, Tab between columns
  - Escape to cancel edit
  - Visual indicator when field is being edited (subtle border/highlight)

- [ ] **3.3 Add/Delete controls** —
  - "Add Flow" button at bottom of each feature section (creates new flow group)
  - "Add Test" button at bottom of each flow (creates new row, defaults to UNTESTED)
  - Delete row: click X icon → confirmation toast → remove
  - "Add Feature" button at top level

- [ ] **3.4 Rules banner** — Non-dismissable banner at top of workspace:

  ```
  TEST RULES: 1. PASS = browser confirmed  2. No code reading  3. No unit-test-only
  4. Full flow end-to-end  5. Rate limits need TEST_MODE bypass  6. Don't stop until all PASS
  ```

  Compact single-line, always visible, styled as warning bar

- [ ] **3.5 Real-time updates** — SSE integration:
  - Listen for test.plan.row.updated events
  - Animate status badge changes (brief flash on update)
  - Update progress bar in real-time
  - Show "Testing in progress..." indicator when Claude/Walter actively running tests
  - New event types in events.mjs: test.plan.loaded, test.plan.row.updated, test.plan.row.added, test.plan.row.deleted, test.plan.run.started, test.plan.run.complete

- [ ] **3.6 Run history** — Click status badge to expand:
  - Last 5 test runs: timestamp, result, tester (Claude session / Walter), duration
  - Failure messages for FAILED runs
  - Collapsible, doesn't disrupt row layout

- [ ] **3.7 Project summary header** —
  - Project name, build name
  - Total tests | Pass rate (X/Y = Z%)
  - Last tested: relative timestamp (timeAgo())
  - Last tester: Claude session ID or "Walter"

- [ ] **3.8 index.html integration** —
  - Add `<div class="workspace" id="ws-tests">` container
  - Add sidebar icon (clipboard with checkmark) with data-ws="tests"
  - Wire into existing switchWorkspace() function

**Success Criteria:** User opens dashboard, clicks Tests, selects project, sees all tests in plain English, edits any test inline with keyboard, sees status badges update in real-time as Claude/Walter run tests. Add and delete test rows. Progress bar reflects current state.

---

### Phase 4: Bidirectional Dashboard-File Sync

**Status:** not_started
**Goal:** Dashboard edits write to TEST_PLAN.md on disk. External edits (Claude/Walter) update dashboard in real-time. No echo loops, no data loss.

**Files:**

- /Users/byronhudson/.buildrunner/dashboard/watchers/test-plan-watcher.mjs (NEW — create `watchers/` directory)
- /Users/byronhudson/.buildrunner/dashboard/lib/test-plan-parser.mjs (NEW — create `lib/` directory)
- /Users/byronhudson/.buildrunner/dashboard/lib/test-plan-sync.mjs (NEW)
- /Users/byronhudson/.buildrunner/dashboard/events.mjs (MODIFY — WebSocket handlers)
- /Users/byronhudson/.buildrunner/dashboard/package.json (MODIFY — add chokidar)

**Blocked by:** Phase 3 (dashboard workspace must exist to receive updates)

**Deliverables:**

- [ ] **4.1 Install chokidar** — Add chokidar v4 to dashboard package.json dependencies, npm install

- [ ] **4.2 test-plan-parser.mjs** — Markdown ↔ JSON parser:
  - Parse TEST_PLAN.md into: `{ rules: string[], features: [{ name, flows: [{ name, rows: [{ precondition, action, result, status, hash, testType }] }] }] }`
  - Serialize JSON back to TEST_PLAN.md markdown preserving formatting
  - Handle malformed markdown gracefully: log warning, return partial parse, never crash
  - Validate against golden-file fixtures from Phase 1
  - Hash generation: SHA-256 of `precondition|action|result` truncated to 8 chars

- [ ] **4.3 test-plan-watcher.mjs** — File watcher service:
  - On dashboard server start: scan registry for all registered projects
  - For each project: check for `.buildrunner/builds/TEST_PLAN.md`
  - Watch found files with chokidar, 150ms debounce
  - Self-edit suppression: track `lastWriteHash` per file, skip broadcast when hash matches
  - On external change: parse file, broadcast `file:changed` via WebSocket with parsed JSON
  - On new project registered: add its TEST_PLAN.md to watch list dynamically

- [ ] **4.4 test-plan-sync.mjs** — Bidirectional sync coordinator:
  - Dashboard → File: receive `file:save` WebSocket message, serialize to markdown, write to disk, set lastWriteHash
  - File → Dashboard: receive chokidar event, parse markdown, check hash, broadcast if external edit
  - Status update path: receive `file:status-update` message (from Claude/Walter), update specific rows in file without full rewrite
  - Conflict detection: if dashboard has unsaved changes when external edit arrives, emit `file:conflict` with both versions

- [ ] **4.5 Per-row change detection** —
  - On dashboard save: compute hash of each row's content
  - Compare against stored hash in HTML comment
  - If hash changed: reset status to UNTESTED, flag row for re-testing
  - Emit `test.plan.row.updated` event with `{ rowId, oldHash, newHash, statusReset: true }`

- [ ] **4.6 events.mjs WebSocket handlers** —
  - Add WebSocket message handlers: `file:save`, `file:status-update`
  - Add WebSocket broadcast types: `file:changed`, `file:conflict`
  - Route test plan messages through existing WebSocket infrastructure

**Success Criteria:** Edit in dashboard → TEST_PLAN.md updates on disk. Claude/Walter edit TEST_PLAN.md → dashboard updates. Edited rows reset to UNTESTED. No echo loops.

---

### Phase 5: Walter TEST_PLAN.md Integration

**Status:** not_started
**Goal:** Walter reads TEST_PLAN.md, generates Playwright/Vitest tests from UNTESTED rows, executes, updates statuses. Continuous verification on every push.

**Files:**

- /Users/byronhudson/Projects/BuildRunner3/core/cluster/test_plan_parser.py (NEW)
- /Users/byronhudson/Projects/BuildRunner3/core/cluster/test_generator.py (NEW)
- /Users/byronhudson/Projects/BuildRunner3/core/cluster/node_tests.py (MODIFY)

**Blocked by:** Phase 1 (needs format spec and golden-file fixtures)
**Can parallelize with:** Phases 3, 4 (completely different files)

**Deliverables:**

- [ ] **5.1 test_plan_parser.py** — Python TEST_PLAN.md parser:
  - Parse TEST_PLAN.md → dict structure matching JS parser output
  - Validate against golden-file fixtures from Phase 1 (same fixtures, different language)
  - Handle malformed markdown: log, partial parse, never crash
  - Unit tests: parse each golden-file fixture, compare output

- [ ] **5.2 test_generator.py** — Test file generator:
  - Browser rows → `.spec.ts` Playwright files:
    - Use getByRole, getByText, getByLabel locators (resilience order)
    - Include precondition setup (navigate, login, seed data)
    - Reference TEST_PLAN.md row: `// TEST_PLAN: Feature.Flow.RowN`
    - Proper auto-waiting (expect().toBeVisible() not isVisible())
  - Terminal rows → `.test.ts` Vitest files with child_process/exec
  - API rows → `.test.ts` Vitest files with fetch assertions
  - Incremental: only generate for rows where hash changed or status is UNTESTED
  - Generated files go to `tests/test-plan/` directory in the project

- [ ] **5.3 node_tests.py integration** — Add TEST_PLAN.md to the test run pipeline:
  - In `_run_tests()`: after existing test detection, check for `.buildrunner/builds/TEST_PLAN.md`
  - If found: parse → generate tests for UNTESTED/FAILED rows → execute via subprocess
  - For Playwright: `npx playwright test tests/test-plan/ --reporter=json`
  - For Vitest: `npx vitest run tests/test-plan/ --reporter=json`
  - Parse results JSON, map back to TEST_PLAN.md rows
  - Update TEST_PLAN.md statuses on disk
  - Apply healing protocol on failures (re-snapshot, selector repair, re-run)
  - Push git commit with updated statuses: `test(walter): TEST_PLAN verification — X/Y pass`

- [ ] **5.4 Lockwood reporting** — Per-row results to cluster memory:
  - POST to `/api/memory/tests` with test_plan_results structure
  - Include: project, build, phase, row_id, status, duration_ms, failure_message
  - Enables cross-project test health tracking

- [ ] **5.5 Dashboard event emission** — Via existing walter.mjs integration:
  - Emit `test.plan.run.started` when TEST_PLAN.md verification begins
  - Emit `test.plan.row.updated` for each row as it completes
  - Emit `test.plan.run.complete` with summary when all rows done
  - Dashboard receives via SSE, updates badges in real-time

- [ ] **5.6 Non-web project support** —
  - If project has no `playwright.config.*`: skip browser test generation, use Vitest only
  - Terminal test rows: generate subprocess tests (run command, assert output)
  - API test rows: generate fetch tests (HTTP request, assert status + body)
  - Python projects: generate pytest files instead of Vitest

**Success Criteria:** Push to Walter → reads TEST_PLAN.md → generates appropriate tests → runs in browser/terminal → updates statuses → pushes commit → dashboard shows real-time results.

---

### Phase 6: Governance + Enforcement Activation

**Status:** not_started
**Goal:** Make TEST_PLAN.md mandatory for ALL builds. Activate all enforcement gates. This phase activates LAST — all tooling must exist and be tested first.

**Files:**

- /Users/byronhudson/.buildrunner/governance/governance.yaml (MODIFY)
- /Users/byronhudson/.claude/settings.json (MODIFY — PreToolUse hook)
- /Users/byronhudson/.claude/commands/spec.md (MODIFY)

**Blocked by:** Phases 1, 2, 3, 4, 5 (all tooling must be complete and tested)

**Deliverables:**

- [ ] **6.1 governance.yaml testing rules** — Add new section:

  ```yaml
  testing_rules:
    test_plan:
      required: true
      browser_verification: mandatory
      skip_criteria: none
      enforcement: block_on_violation
    post_build_verification:
      required: true
      runs_after: every_phase
      runner: playwright_or_vitest
      no_exceptions: true
  ```

- [ ] **6.2 PreToolUse hook** — Add to settings.json:
  - Trigger: on `git commit` containing "complete: Phase" in message
  - Check: TEST_PLAN.md exists in project's `.buildrunner/builds/`
  - Check: parse TEST_PLAN.md, verify all rows show PASS
  - Block with exit code 2 if either check fails: `BLOCK: TEST_PLAN.md incomplete — X rows not PASS`

- [ ] **6.3 /spec template update** — Modify spec.md Step 4 output template:
  - Add "Testing" section to each phase: "TEST_PLAN.md rows will be created for these deliverables"
  - Add reminder: "Every phase requires browser-verified TEST_PLAN.md before completion"
  - Prompt user to think about testable user flows during spec creation

- [ ] **6.4 Remove graceful degradation** — Update Phase 2's Stop hook:
  - Remove the "if TEST_PLAN.md doesn't exist, warn but don't block" fallback
  - Now: if TEST_PLAN.md doesn't exist, BLOCK with `BLOCK: No TEST_PLAN.md found — create one before proceeding`

- [ ] **6.5 Backfill guide** — Document in begin-test-plan.md:
  - How to add TEST_PLAN.md to an in-progress build
  - How to retroactively write test rows for completed phases
  - How to mark completed phases as verified (if they were browser-tested before this system existed)

- [ ] **6.6 Post-build dashboard event** — Emit `test.plan.gate` event on every phase completion:
  - Includes: project, build, phase, total_tests, passed, failed, untested, gate_result (pass/block)
  - Dashboard shows gate results in build timeline

**Success Criteria:** No build without TEST_PLAN.md. No phase completion without all-PASS browser verification. No Claude stop with incomplete tests. All enforced mechanically, not by honor system.

---

## Session Log

[Will be updated by /begin]
