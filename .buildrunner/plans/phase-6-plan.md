# Phase 6: Skill Cross-Integration — Plan

## Tasks

### Task 6.1: /guard — Add E2E test coverage gap check
Add a new validation section (3.6) that checks if the current phase has UI deliverables but no E2E tests. Flag as a gap with WARNING severity.

### Task 6.2: /review — Add E2E regression run after auto-fixes
In Step 3 (Auto-Fix), after running tests, explicitly run `npm run test:e2e` when Playwright is configured to verify no E2E regressions.

### Task 6.3: /design — Add E2E Test Requirements section to DESIGN_SPEC.md
In Step 5 (Selection + Spec Generation), add instruction to include an "E2E Test Requirements" section in DESIGN_SPEC.md documenting which user flows need testing.

## Tests
Non-testable (markdown skill files). Skip TDD.
