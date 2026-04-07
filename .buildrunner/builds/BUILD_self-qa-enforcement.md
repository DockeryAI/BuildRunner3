# Build: Self-QA Enforcement Layer

**Created:** 2026-04-06
**Status:** ✅ COMPLETE
**Deploy:** web — global skill updates (applies to all BR3 projects)

## Overview

Make it impossible for Claude to mark work done without visually verifying it in a browser. Closes the gap between "tests pass" and "the app actually works" by adding enforcement hooks, autonomous browser exploration, visual regression baselines, and a mandatory self-QA verification step to /begin.

## Parallelization Matrix

| Phase | Key Files                                       | Can Parallel With | Blocked By          |
| ----- | ----------------------------------------------- | ----------------- | ------------------- |
| 1     | ~/.claude/settings.json                         | —                 | —                   |
| 2     | ~/.claude/commands/explore-qa.md (NEW)          | 1                 | —                   |
| 3     | begin.md, begin-self-qa.md (NEW)                | 1, 2              | —                   |
| 4     | playwright.config.ts, tests/e2e/visual/\* (NEW) | 1, 2, 3           | —                   |
| 5     | Lomax remote, deploy script (NEW)               | 1, 2, 3           | 4 (needs baselines) |

## Phases

### Phase 1: Enforcement Hooks

**Status:** ✅ COMPLETE
**Files:**

- ~/.claude/settings.json (MODIFY)
  **Blocked by:** None
  **Deliverables:**
- [x] Add Stop hook (type: agent) that spawns a subagent to run `npm test` and verify results — blocks completion on failure
- [x] Add Stop hook (type: agent) for Playwright MCP visual verification — opens localhost, navigates main pages, checks rendering
- [x] Add `stop_hook_active` guard in both hooks to prevent infinite loops
- [x] Add PreCompact hook that re-injects a condensed 30-line testing/verification reminder into context
- [x] Add SessionStart compact-matcher hook for post-compaction test status injection
- [x] Audit existing hooks in settings.json to confirm nothing from PLAYWRIGHT_INTEGRATION Phase 3 was lost

**Success Criteria:** Start a conversation, write some code, try to stop — Claude is forced to run tests and open the browser first. Trigger compaction — testing rules survive. The `stop_hook_active` guard prevents infinite blocking.

---

### Phase 2: Explore-QA Command

**Status:** ✅ COMPLETE
**Files:**

- ~/.claude/commands/explore-qa.md (NEW)
  **Blocked by:** None
  **After:** Phase 1 (logical sequence, CAN parallelize)
  **Deliverables:**
- [x] Create `/explore-qa` slash command with Playwright MCP exploration prompt
- [x] Crawl logic: discover navigation, visit every reachable page, interact with all elements
- [x] Console error detection after every action via `browser_console_messages`
- [x] Mobile viewport test (375x667 resize + re-crawl)
- [x] Dead link detection (click every link, check for 404/error pages)
- [x] Form filling with valid and invalid data
- [x] Output: structured `qa-report.md` with pages visited, errors found, screenshots of issues

**Success Criteria:** Run `/explore-qa` on a live app — it visits every page, finds console errors and broken layouts, produces a report without human guidance.

---

### Phase 3: Self-QA Step in /begin

**Status:** ✅ COMPLETE
**Files:**

- ~/.claude/commands/begin.md (MODIFY)
- ~/.claude/docs/begin-self-qa.md (NEW)
  **Blocked by:** None (different insertion point in begin.md than Phase 1's hooks)
  **After:** Phase 1
  **Deliverables:**
- [x] Create `begin-self-qa.md` reference doc defining the visual verification procedure
- [x] Insert Step 4.7 "Visual Browser Verification" in begin.md between Step 4.5 (TDD Re-run) and Step 5 (Review)
- [x] Step logic: identify all pages/routes touched by this phase's deliverables, open each via Playwright MCP, take snapshots, check for rendering issues and console errors
- [x] Fix loop: if visual issues found, fix and re-verify (max 3 attempts)
- [x] Block phase on persistent visual failures
- [x] Skip criteria: phases with no UI deliverables (backend-only, migrations, config)
- [x] Track result as `visual_qa: PASS|FAIL|SKIP` in progress output

**Success Criteria:** Run `/begin` on a UI phase — after tests pass, Claude opens the browser and visually verifies before proceeding to review. Backend phases skip cleanly.

---

### Phase 4: Visual Regression Baselines

**Status:** ✅ COMPLETE
**Files:**

- playwright.config.ts (MODIFY)
- tests/e2e/visual/dashboard.visual.spec.ts (NEW)
- tests/e2e/visual/login.visual.spec.ts (NEW)
- tests/e2e/visual/analytics.visual.spec.ts (NEW)
- tests/e2e/visual/screenshot.css (NEW)
- Dockerfile.playwright (NEW)
- package.json (MODIFY — add visual test scripts)
  **Blocked by:** None (test files are independent)
  **After:** Phase 3
  **Deliverables:**
- [x] Add `toHaveScreenshot()` config to playwright.config.ts with maxDiffPixelRatio, animation disabling, caret hiding
- [x] Install and configure `playwright-odiff` for 6.6x faster comparison than default pixelmatch
- [x] Create screenshot.css with animation/transition disabling rules
- [x] Create visual spec files for each major page (dashboard, login, analytics) with dynamic content masking
- [x] Create Dockerfile.playwright for consistent baseline generation (font rendering parity)
- [x] Add `test:visual`, `test:visual:docker`, `test:visual:update` npm scripts
- [x] Generate initial baselines inside Docker
- [x] Tag visual tests with `@visual` and exclude from normal `test:e2e:ui` runs

**Success Criteria:** Change a CSS property that breaks layout — `npm run test:visual:docker` catches it automatically. Baselines generated in Docker are consistent across machines.

---

### Phase 5: Visual Regression Tracker on Lomax

**Status:** ✅ COMPLETE
**Files:**

- ~/.buildrunner/scripts/deploy-vrt-lomax.sh (NEW)
- Cluster remote files on Lomax (10.0.1.104)
  **Blocked by:** Phase 4 (need baselines first)
  **After:** Phase 4
  **Deliverables:**
- [x] Write deployment script for VRT Docker Compose on Lomax
- [x] Configure VRT with odiff comparison provider
- [x] Wire `@visual-regression-tracker/agent-playwright` integration into BR3 projects
- [x] Configure branch-based baselines (separate per git branch)
- [x] Add VRT dashboard URL to BR3 cluster dashboard
- [ ] Test end-to-end: code change on Muddy → visual test runs → diff appears in VRT on Lomax

**Success Criteria:** Push a CSS change — VRT dashboard on Lomax shows the visual diff with approve/reject buttons. Branch baselines are isolated.

---

## Out of Scope

- Vercel agent-browser integration (wait for maturity, Playwright MCP is sufficient now)
- AI-powered visual comparison via VLM (VRT supports it but needs a local vision model on Below)
- Full Ralph Loop state machine (overkill for per-phase verification — Stop hooks + begin step are sufficient)
- Automated PR-gated QA (Quinn pattern) — no GitHub Actions CI for BR3 framework itself
- Stagehand/browser-use integration — Playwright MCP covers the use case

## Session Log

[Will be updated by /begin]
