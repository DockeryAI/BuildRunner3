# DRAFT: BR3 Universal Test Plan System

## Purpose

Every BR3 build gets a TEST_PLAN.md — a plain English testing document that lives alongside the BUILD spec. Tests are verified in a real browser via Playwright. No test passes without browser confirmation. The dashboard shows all tests per project, editable inline, with changes flowing bidirectionally to the filesystem. Mandatory after every single build phase — no exceptions.

## Problem Being Solved

Claude marks tests as "passing" without opening a browser. Rate limits, guards, and middleware block user flows but go undiscovered because nobody tested the full flow end-to-end. New Claude instances don't know what was tested vs assumed. The TEST_PLAN.md + dashboard system fixes all of this.

## Tech Stack

- Node.js (dashboard workspace, file watcher, WebSocket server)
- Playwright MCP (browser verification)
- SQLite (Walter test results)
- Chokidar v4 (file watching for dashboard sync)
- SSE/WebSocket (real-time dashboard updates)
- Markdown (TEST_PLAN.md format)

## Existing Infrastructure to Build On

- Dashboard workspace pattern: ws-\*.js files in ~/.buildrunner/dashboard/public/js/
- Registry: ~/.buildrunner/scripts/registry.mjs (build tracking)
- Events: ~/.buildrunner/dashboard/events.mjs (SSE + WebSocket)
- Walter: core/cluster/node_tests.py (test_file_map, SHA tracking)
- Walter integration: ~/.buildrunner/dashboard/integrations/walter.mjs
- Stop hooks: ~/.claude/settings.json (test + visual verification)
- Begin skill: ~/.claude/commands/begin.md (Steps 3, 3.5, 4.5, 6.5, 7)
- File watchers: core/build/file_watcher.py (watchdog pattern)
- Governance: ~/.buildrunner/governance/governance.yaml

---

## Phase 1: TEST_PLAN.md Format + Creation in /begin

**Goal:** Every build creates a TEST_PLAN.md during planning. Format is standardized with preconditions, user actions, expected results, status, and per-row content hashes.

**Files:**

- ~/.claude/docs/begin-test-plan.md (NEW)
- ~/.claude/commands/begin.md (MODIFY)
- ~/.claude/docs/begin-tdd-gate.md (MODIFY)

**Deliverables:**

- [ ] TEST_PLAN.md format specification with rules header, feature sections, precondition/action/result/status columns, per-row content hash, version tracking
- [ ] begin-test-plan.md reference doc with format template, generation rules, status management, healing protocol, rate-limit bypass rule, false-pass prevention checklist, XML enforcement tags
- [ ] begin.md Step 3: create TEST_PLAN.md alongside phase plan, every deliverable gets user-flow rows from UX perspective
- [ ] begin.md Step 3.5: generate .spec.ts Playwright files from TEST_PLAN.md browser scenarios, commit alongside unit tests
- [ ] begin.md Step 4: after each commit, update TEST_PLAN.md statuses, FAILED blocks next task
- [ ] begin.md Step 4.5: run all Playwright specs, update statuses, heal before failing (2 attempts), block if FAILED after healing

**Success Criteria:** /begin creates TEST_PLAN.md with user-perspective test rows for every deliverable.

---

## Phase 2: Mandatory Post-Build Browser Verification Gate

**Goal:** Every phase completion requires full TEST_PLAN.md browser verification. No skip criteria. No exceptions. Any change can break user flows.

**Files:**

- ~/.claude/commands/begin.md (MODIFY)
- ~/.claude/docs/begin-verification.md (MODIFY)
- ~/.claude/settings.json (MODIFY)
- ~/.claude/commands/autopilot.md (MODIFY)

**Deliverables:**

- [ ] Step 6.5 rewrite: parse TEST_PLAN.md, run every non-PASS test in Playwright, update statuses, block if any FAILED
- [ ] Remove ALL skip criteria from browser verification
- [ ] XML absolute completion rule: PASS = browser-confirmed only
- [ ] Rate limit/guard bypass rule: limiters must have TEST_MODE bypass
- [ ] Healing protocol: re-snapshot, update selectors, re-run (2 attempts) before FAILED
- [ ] False pass prevention: 5-question checklist before any PASS
- [ ] Stop hook: check TEST_PLAN.md, block if non-PASS rows exist
- [ ] Autopilot: full regression between every phase

**Success Criteria:** Claude cannot complete any phase or stop until every row is PASS via Playwright.

---

## Phase 3: Dashboard Test Workspace

**Goal:** New "Tests" workspace in the BR3 dashboard. Testpad-style checklist UX — all tests visible at once, editable inline, keyboard-driven. Real-time status updates.

**Files:**

- ~/.buildrunner/dashboard/public/js/ws-tests.js (NEW)
- ~/.buildrunner/dashboard/public/index.html (MODIFY)
- ~/.buildrunner/dashboard/events.mjs (MODIFY)
- ~/.buildrunner/dashboard/emit-event.mjs (MODIFY)

**Deliverables:**

- [ ] ws-tests.js: project selector, progress bar (pass/fail/untested), collapsible feature sections, checklist rows with status badges
- [ ] Inline editing: click row to edit precondition/action/result, auto-save on blur/Enter, arrow keys + Tab navigation
- [ ] Add Flow button (new test group per feature), Add Test button (new row per flow), Delete row with confirmation
- [ ] Non-dismissable rules banner showing 6 verification rules
- [ ] Real-time SSE updates when Claude/Walter updates test statuses
- [ ] Test run history per row (last 5 results on badge click)
- [ ] Project summary: total tests, pass rate, last tested, last tester
- [ ] index.html: tests workspace div + sidebar icon + switcher

**Success Criteria:** User opens dashboard, clicks project, sees all tests in plain English, edits inline, sees real-time updates.

---

## Phase 4: Bidirectional Dashboard-File Sync

**Goal:** Dashboard edits write to TEST_PLAN.md. External edits update dashboard. Chokidar watcher with self-edit suppression and hash-based change detection.

**Files:**

- ~/.buildrunner/dashboard/watchers/test-plan-watcher.mjs (NEW)
- ~/.buildrunner/dashboard/lib/test-plan-parser.mjs (NEW)
- ~/.buildrunner/dashboard/lib/test-plan-sync.mjs (NEW)
- ~/.buildrunner/dashboard/events.mjs (MODIFY)

**Deliverables:**

- [ ] test-plan-parser.mjs: parse TEST_PLAN.md to JSON, serialize JSON to markdown, preserve formatting
- [ ] test-plan-watcher.mjs: chokidar watching TEST_PLAN.md files, 150ms debounce, self-edit suppression via content hash
- [ ] test-plan-sync.mjs: external change → parse → broadcast via WebSocket; dashboard edit → serialize → write → suppress echo
- [ ] Per-row content hash in markdown (HTML comment), status resets to UNTESTED on hash change
- [ ] Conflict notification: "File changed externally — merge or discard?"
- [ ] WebSocket messages: file:changed, file:save, file:status-update
- [ ] Auto-discovery: scan registered projects for TEST_PLAN.md on startup

**Success Criteria:** Dashboard edit → file updates in 100ms. External edit → dashboard updates in 200ms. No echo loops.

---

## Phase 5: Walter TEST_PLAN.md Integration

**Goal:** Walter parses TEST_PLAN.md, generates Playwright tests from UNTESTED rows, executes, updates statuses. Continuous on every push.

**Files:**

- core/cluster/node_tests.py (MODIFY)
- core/cluster/test_plan_parser.py (NEW)
- core/cluster/test_generator.py (NEW)

**Deliverables:**

- [ ] test_plan_parser.py: parse TEST_PLAN.md to Python dicts
- [ ] test_generator.py: generate .spec.ts from parsed rows, getByRole/getByText locators, precondition setup, row number references
- [ ] node_tests.py: on run, check TEST_PLAN.md, parse, generate tests for UNTESTED rows, execute via Playwright, update statuses, push to Lockwood
- [ ] Healing: re-snapshot DOM, selector repair, re-run before FAILED
- [ ] Incremental generation: only regenerate for changed/UNTESTED rows
- [ ] Dashboard events: emit test.plan.updated with per-row results

**Success Criteria:** Push to Walter → reads TEST_PLAN.md → generates tests → runs in browser → updates statuses → dashboard shows results.

---

## Phase 6: Governance + Enforcement

**Goal:** TEST_PLAN.md mandatory for all builds. Enforced via hooks, governance, skill gates.

**Files:**

- ~/.buildrunner/governance/governance.yaml (MODIFY)
- ~/.claude/settings.json (MODIFY)
- ~/.claude/commands/spec.md (MODIFY)
- ~/.claude/commands/begin.md (MODIFY)

**Deliverables:**

- [ ] governance.yaml: test_plan_required, browser_verification_required, no_skip_criteria
- [ ] PreToolUse hook: on phase completion commit, verify TEST_PLAN.md exists and all rows PASS
- [ ] Stop hook: parse TEST_PLAN.md, block if any non-PASS
- [ ] /spec: prompt for TEST_PLAN.md section in BUILD spec template
- [ ] Post-build event: emit test.plan.gate to dashboard
- [ ] Backfill guide for existing builds

**Success Criteria:** No build without TEST_PLAN.md. No phase completion without all-PASS. No Claude stop with incomplete tests.

---

## Parallelization Matrix

| Phase | Key Files                                                       | Can Parallel With | Blocked By               |
| ----- | --------------------------------------------------------------- | ----------------- | ------------------------ |
| 1     | begin.md, begin-test-plan.md, begin-tdd-gate.md                 | -                 | -                        |
| 2     | begin.md, begin-verification.md, settings.json, autopilot.md    | -                 | 1 (shares begin.md)      |
| 3     | ws-tests.js, index.html, events.mjs                             | 1, 2              | - (different files)      |
| 4     | test-plan-watcher.mjs, test-plan-parser.mjs, test-plan-sync.mjs | 1, 2              | 3 (dashboard must exist) |
| 5     | node_tests.py, test_plan_parser.py, test_generator.py           | 1, 2, 3           | 1 (needs format spec)    |
| 6     | governance.yaml, settings.json, spec.md                         | -                 | 1, 2, 3, 4, 5            |

## Out of Scope (Future)

- Mobile viewport testing in dashboard
- CRDT-based collaborative editing
- AI-generated test specs without human review
- Visual regression screenshot comparison
- Test coverage percentage tracking
- Gherkin/Cucumber/BDD framework integration
