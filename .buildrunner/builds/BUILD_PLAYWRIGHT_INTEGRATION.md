# Build: Playwright Full Integration

**Created:** 2026-03-30
**Status:** Batch 1 Complete, Batch 2 Pending (Phase 5)
**Deploy:** web — existing BR3 skill system (no deploy step, skill files are live on save)

## Overview

Wire Playwright into every stage of the BR3 build pipeline so tests run automatically, failures block progress, and Claude can browse the live app to self-check its work. Fixes the critical gap where /begin documents E2E testing (Step 4.5b) but never executes it.

## Parallelization Matrix

| Phase | Key Files                                              | Can Parallel With | Blocked By             |
| ----- | ------------------------------------------------------ | ----------------- | ---------------------- |
| 1     | begin.md, begin-tdd-gate.md, e2e.md                    | -                 | -                      |
| 2     | autopilot.md, autopilot-executor-prompt.md             | 1                 | -                      |
| 3     | .mcp.json (NEW), settings.local.json, pw-test.md (NEW) | 1, 2              | -                      |
| 4     | tests/e2e/\*.ts, playwright.config.ts                  | 1, 2, 3           | -                      |
| 5     | .github/workflows/ci.yml                               | 1, 2, 3           | 4 (tests stable first) |
| 6     | guard.md, review.md, design.md                         | 1, 2, 3, 4        | -                      |

## Phases

### Phase 1: Wire Tests into Build Workflow

**Status:** ✅ COMPLETE
**Files:**

- ~/.claude/commands/begin.md (MODIFY)
- ~/.claude/docs/begin-tdd-gate.md (MODIFY)
- ~/.claude/commands/e2e.md (MODIFY)
  **Blocked by:** None
  **Deliverables:**
- [x] Add E2E execution block to /begin Step 4.5b — detect playwright config, check for UI deliverables, run `npm run test:e2e:ui`, fix loop (3 attempts), block phase on failure
- [x] Update /e2e skill to accept `phase_number` argument for scoped test detection
- [x] Use soft 4.6 prompt language ("run tests when phase includes UI deliverables" not "MUST run tests")
- [x] Add "do not hard-code values to pass assertions" constraint per 4.6 anti-pattern
- [x] Track E2E result in progress output (e2e_tier1: PASS|FAIL|SKIP)

**Success Criteria:** /begin on a UI phase runs Playwright and blocks on failure. Backend-only phases skip cleanly.

---

### Phase 2: Autopilot E2E Gates

**Status:** ✅ COMPLETE
**Files:**

- ~/.claude/commands/autopilot.md (MODIFY)
- ~/.claude/docs/autopilot-executor-prompt.md (MODIFY)
  **Blocked by:** None (different files than Phase 1)
  **After:** Phase 1 (logical sequence, CAN parallelize)
  **Deliverables:**
- [x] Add E2E result aggregation to batch gate (Step 5)
- [x] Fail batch if any phase's E2E failed
- [x] Add full regression run (npm run test:e2e) after batch passes individually
- [x] Add "run tests directly, do not delegate to subagents" constraint in executor prompt (prevents 4.6 subagent spawning)
- [x] Report E2E status in batch gate summary

**Success Criteria:** Autopilot refuses to advance past a batch when E2E tests are failing. Batch summary shows E2E pass/fail per phase.

---

### Phase 3: Playwright MCP + Claude Code Hooks

**Status:** ✅ COMPLETE
**Files:**

- ~/Projects/BuildRunner3/.mcp.json (NEW)
- ~/Projects/BuildRunner3/.claude/settings.local.json (MODIFY)
- ~/.claude/commands/pw-test.md (NEW)
  **Blocked by:** None (all new files or different files)
  **After:** Phase 1
  **Deliverables:**
- [x] Create .mcp.json with Playwright MCP server config (stdio transport, npx @playwright/mcp@latest)
- [x] Add MCP tool permissions to settings — restrict to 8 core tools (navigate, click, type, fill, screenshot, snapshot, evaluate, close)
- [x] Add Stop hook (type: agent, low effort, terse prompt) that runs npm run test:e2e before Claude finishes tasks
- [x] Add stop_hook_active guard to prevent infinite loops
- [x] Create /pw-test slash command — explore-then-write pattern with XML structure and 2-3 multishot examples
- [x] Add compact-matcher SessionStart hook to re-inject test status after context compaction

**Success Criteria:** Claude can browse localhost:5173 via MCP tools. Tasks can't complete until tests pass. /pw-test produces tests grounded in observed behavior.

---

### Phase 4: Test Infrastructure Upgrade

**Status:** ✅ COMPLETE
**Files:**

- tests/e2e/pages/LoginPage.ts (NEW)
- tests/e2e/pages/DashboardPage.ts (NEW)
- tests/e2e/pages/AnalyticsPage.ts (NEW)
- tests/e2e/fixtures.ts (NEW)
- tests/e2e/auth.setup.ts (NEW)
- tests/e2e/authentication.spec.ts (MODIFY)
- tests/e2e/dashboard.spec.ts (MODIFY)
- tests/e2e/analytics.spec.ts (MODIFY)
- tests/e2e/websocket.spec.ts (MODIFY)
- tests/e2e/api-health.spec.ts (MODIFY)
- playwright.config.ts (MODIFY)
  **Blocked by:** None (test files independent of skill files)
  **After:** Phase 1
  **Deliverables:**
- [x] Create Page Object Models for Login, Dashboard, Analytics pages with role-based locators
- [x] Create shared fixtures (authenticatedPage, dashboardPage, apiContext)
- [x] Create auth setup project with storageState reuse
- [x] Update playwright.config.ts with setup project dependency and auth state path
- [x] Migrate all 5 spec files from CSS selectors to POM + getByRole/getByTestId locators
- [x] Add playwright/.auth/ to .gitignore

**Success Criteria:** All 25+ existing tests pass using POMs. Login happens once per worker, not once per test. No CSS selectors remain in spec files.

---

### Phase 5: GitHub Actions CI

**Status:** not_started
**Files:**

- .github/workflows/ci.yml (MODIFY)
  **Blocked by:** Phase 4 (tests should be stable before CI runs them)
  **After:** Phase 4
  **Deliverables:**
- [ ] Add e2e-tests job after integration-tests
- [ ] Install browsers with npx playwright install --with-deps
- [ ] Start frontend + backend servers
- [ ] Run npx playwright test
- [ ] Upload HTML report as artifact
- [ ] Upload traces as artifact (on failure only)

**Success Criteria:** CI pipeline includes Playwright step. Failed tests show traces in downloadable artifacts.

---

### Phase 6: Skill Cross-Integration

**Status:** ✅ COMPLETE
**Files:**

- ~/.claude/commands/guard.md (MODIFY)
- ~/.claude/commands/review.md (MODIFY)
- ~/.claude/commands/design.md (MODIFY)
  **Blocked by:** None
  **After:** Phase 1 (skills need /begin integration working first to be meaningful)
  **Deliverables:**
- [x] /guard — add check: "Phase has UI deliverables but no E2E tests" → flag as gap
- [x] /review — after auto-fixing issues, explicitly run npm run test:e2e to verify no regressions
- [x] /design — when producing DESIGN_SPEC.md, add "E2E Test Requirements" section documenting which flows need testing

**Success Criteria:** Guard catches missing test coverage. Review verifies fixes don't break E2E. Design specs include test planning.

---

## Out of Scope

- Visual regression testing with screenshot diffs (BUILD_4D plan)
- E2E test recording and replay
- Screenshot gallery generation
- Network traffic monitoring during tests
- Accessibility testing with @axe-core/playwright
- E2E Tier 2 (API/AI specs) — implement separately
- Sharding in CI (wait until test count exceeds 30)

## Prompting Notes (4.6-specific)

These principles from /opus research apply to all skill modifications in this build:

- Use soft trigger language ("run tests when phase includes UI deliverables") — 4.6 overtriggers on aggressive prompts
- Constrain subagent spawning for test execution — "run tests directly, do not delegate"
- Add "do not hard-code values to pass assertions" — 4.6 tendency
- Stop hooks use low effort, terse prompts — test running is mechanical
- /pw-test uses multishot examples over lengthy instructions
- Compact-matcher hooks re-inject test context after compaction

## Session Log

[Will be updated by /begin]
