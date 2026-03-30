# Phase 2 Plan: Autopilot E2E Gates

## Tasks

### Task 2.1: Add E2E result aggregation to batch gate (Step 5.5) in autopilot.md

- In Step 5.5 gate report, add E2E status per phase row
- Aggregate e2e_tier1 from each phase's AUTOPILOT_PHASE_RESULT

### Task 2.2: Fail batch if any phase's E2E failed in autopilot.md

- Before merge in Step 5.1, check e2e_tier1 results
- Treat E2E failure same as phase failure — don't merge, surface to user

### Task 2.3: Add full regression run after batch passes in autopilot.md

- After individual phases pass and merge, run `npm run test:e2e`
- Add between Step 5.4 and 5.5
- Log result in gate report

### Task 2.4: Add "run tests directly, do not delegate" constraint in executor prompt

- Add to scope_constraints section
- Add to do_not section
- Prevents 4.6 subagent spawning for test execution

### Task 2.5: Report E2E status in batch gate summary in autopilot.md

- Add E2E regression line to gate report template in Step 5.5

## Tests

Non-testable (prompt template / skill files). Skip TDD.
