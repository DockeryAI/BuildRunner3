# Phase 4 Plan: Pre-Commit Cluster Gate

## Tasks

### Task 4.1: Add Walter + Lomax pre-push checks to commit.md

- Add a new Step 6.5 between Step 6 (Stage & Commit) and Step 7 (Push)
- Check Walter for test failures via `cluster-check.sh test-runner` + `/api/coverage`
- Check Lomax for build status via `cluster-check.sh staging-server` + `/api/projects/$PROJECT_LC/build/status`
- Warnings only — never blocks the push
- Graceful skip if nodes are offline

### Task 4.2: Add Lomax build check + Walter test trigger to begin.md Step 6.5

- In the Verification Gate section, add cluster checks
- Trigger Walter test run via `POST /api/run` and wait for result
- Check Lomax build status
- Warnings only — informational, user decides
- Graceful skip if nodes are offline

## Tests

- Non-testable: these are markdown command files (documentation/config), not executable code
- Verification will be structural — confirm the sections exist with correct content
