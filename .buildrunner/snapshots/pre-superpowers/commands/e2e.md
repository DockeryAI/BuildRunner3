---
description: Run Playwright E2E tests for the most recent work — auto-detects what to test
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent
model: opus
---

# E2E Test Runner

Test the most recently built feature or fix end-to-end using Playwright. Automatically detect what was built, write/update tests if needed, run them, fix failures, and re-run until green.

**Arguments:** $ARGUMENTS

---

## Step 0: Detect What Was Recently Built

Determine the scope of what needs E2E testing:

1. **Check git for recent changes:**
   ```bash
   git log --oneline -5
   git diff --name-only HEAD~3..HEAD
   git status --short
   ```

2. **Identify the feature/fix** — Look at commit messages, changed files, and any BUILD spec lock:
   ```bash
   cat .buildrunner/current-phase.json 2>/dev/null || echo "No active phase"
   ```

3. **Summarize what needs testing** — State clearly: "Testing [feature X] which touches [these files/flows]."

If the user provided arguments (`$ARGUMENTS`), use that as the scope instead of auto-detecting.

---

## Step 1: Verify Prerequisites

```bash
# Dev server must be running (check the project's configured port)
lsof -iTCP:3000 -sTCP:LISTEN -P 2>/dev/null | head -3
```

If not running, start it:
```bash
npm run dev &
sleep 5
```

Check if Playwright is installed:
```bash
npx playwright --version 2>/dev/null || npm install -D @playwright/test
```

---

## Step 2: Check Existing Tests

```bash
# Find existing E2E test files
find e2e/ tests/ test/ -name "*.spec.ts" -o -name "*.e2e.ts" -o -name "*.test.ts" 2>/dev/null
```

Read the existing tests and the Playwright config to understand the test infrastructure.

**Determine if existing tests cover the recent work:**
- If YES → run them as-is
- If NO → write new tests for the feature (see Step 2b)
- If PARTIAL → extend existing tests

---

## Step 2b: Write Tests (if needed)

When writing new E2E tests for the recently built feature:

1. **Read the source code** of the feature being tested
2. **Follow existing test patterns** — match the style, helpers, and conventions already in the test directory
3. **Test the critical path** — the main user flow, not every edge case
4. **Include setup/teardown** — clean up any test data created
5. **Use data-testid selectors** where they exist, fall back to role/text selectors
6. **Set appropriate timeouts** — longer for API/pipeline tests, shorter for UI-only

---

## Step 3: Run E2E Tests

```bash
npx playwright test --reporter=list 2>&1
```

To run only the tests relevant to the recent work:
```bash
npx playwright test --grep "feature name" --reporter=list 2>&1
```

---

## Step 4: Fix Loop

If ANY test fails:

1. **Read the failure output** — understand what failed and why
2. **Check if it's a test bug or an app bug:**
   - Test bug (wrong selector, timing issue, stale assumption) → fix the test
   - App bug (component broken, missing prop, runtime error) → fix the app code
3. **Read the relevant source files** before making changes
4. **Fix the issue**
5. **Re-run the failing test** to confirm the fix:
   ```bash
   npx playwright test --grep "test name" --reporter=list 2>&1
   ```
6. **Repeat** until that test passes
7. **Run the full suite again** to confirm no regressions:
   ```bash
   npx playwright test --reporter=list 2>&1
   ```
8. **Loop back to step 4** if any test still fails

**Do NOT skip or delete failing tests.** Fix the root cause.

**Do NOT add `.skip()` to make tests pass.** That's not fixing.

**Max iterations: 5.** If still failing after 5 fix attempts on the same test, report the blocker.

---

## Step 5: Report

When all tests pass, output:

```markdown
## E2E Results

**Feature tested:** [what was tested]
**Status:** PASS | FAIL
**Tests:** X passed, Y failed, Z skipped
**Duration:** Xs

| Test | Result | Notes |
|------|--------|-------|
| [test name] | PASS/FAIL | [fix applied if any] |

**Tests written this run:**
- [file] — [what it tests]

**Fixes applied this run:**
- [file:line] — [what was fixed and why]

**Remaining issues:**
- [any blockers or skipped tests that need attention]
```

---

## Rules

1. **Auto-detect scope** — figure out what was recently built and test THAT
2. **Write tests if missing** — don't just run existing tests if they don't cover the new work
3. **Fix, don't skip** — every failure gets investigated and fixed
4. **App bugs > test bugs** — if the app is wrong, fix the app, not the test
5. **Re-run after every fix** — confirm the fix actually works
6. **Full suite at the end** — no regressions allowed
7. **Report everything** — what passed, what was fixed, what's still broken
8. **Follow existing patterns** — match the test infrastructure already in the project
