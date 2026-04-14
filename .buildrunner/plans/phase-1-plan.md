# Phase 1 Plan: Cursor IDE Setup + Auto-Focus Script

## Assessment

All Phase 1 code already exists from a prior build. Verification only.

## Existing Code

- `~/.buildrunner/scripts/cursor-review-focus.sh` — complete, 69 lines
- `~/.buildrunner/cursor-workspace.code-workspace` — complete, 41 lines
- Hook wired in `auto-save-session.sh` lines 83-84

## Tasks

### Task 1: Verify cursor-review-focus.sh

Run the script with a test commit range to confirm it resolves files correctly and invokes Cursor CLI.

### Task 2: Verify workspace loads

Confirm workspace file is valid JSON and references correct paths.

### Task 3: Mark deliverables complete

Update BUILD spec with all checkboxes checked.

## Tests

- Script exits 0 with valid commit range
- Script exits 0 (no-op) on nodes that aren't Muddy
- Workspace JSON is valid
