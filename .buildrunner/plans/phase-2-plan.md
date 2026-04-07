# Phase 2 Plan: Push-Based Repo Sync + Dispatch Logging

## Tasks

### T1: auto-save-session.sh — Walter git remote auto-setup

Add `walter` remote if missing before push.

### T2: auto-save-session.sh — Push code before /api/run

`git push walter HEAD:refs/heads/current --force-with-lease` before the curl to /api/run

### T3: auto-save-session.sh — Dispatch logging

Log every dispatch to `~/.buildrunner/logs/walter-dispatch.log`

### T4: auto-save-session.sh — Health check before dispatch

Verify Walter /health freshness before dispatching; skip with log if degraded

### T5: dispatch-to-node.sh — Lock files for dispatch exclusivity

`/tmp/dispatch-lock-${NODE}-${PROJECT}` with PID check, EXIT trap cleanup

### T6: dispatch-to-node.sh — Remove dead code

Remove keychain unlock lines. Fix DISPATCH_USER -> SSH_USER in rsync.

### T7: dispatch-to-node.sh — Unique prompt file paths

Use unique pattern for temp prompt files

## Tests

Shell scripts — non-testable with vitest. TDD skipped.
