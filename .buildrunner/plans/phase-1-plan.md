# Phase 1 Plan: Wire Tests into Build Workflow

## Tasks

### Task 1.1: Add E2E execution block to /begin Step 4.5b
- In `begin.md`, update Step 4.5 to reference the enhanced tdd-gate doc
- Add e2e_tier1 tracking to progress output mentions

### Task 1.2: Enhance begin-tdd-gate.md Step 4.5b with real execution logic
- Add Playwright config detection
- Add UI deliverable detection
- Add npm run test:e2e:ui execution with fallback
- Add fix loop (3 attempts max), block on failure
- Add "do not hard-code values to pass assertions" constraint
- Use soft 4.6 prompt language throughout
- Track e2e_tier1 result (PASS|FAIL|SKIP)

### Task 1.3: Update /e2e to accept phase_number argument
- Add phase_number argument handling in Step 0
- When phase_number provided, scope detection to that phase's deliverables
- Look up BUILD spec for that phase

### Task 1.4: Ensure e2e_tier1 result tracked in progress output
- Add e2e_tier1: PASS|FAIL|SKIP to 4.5c report template

## Tests

- All deliverables are skill/command markdown files - TDD gate: SKIP
