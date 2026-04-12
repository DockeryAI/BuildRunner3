# Phase 5: Adversarial Dispatch Hardening — Implementation Plan

## Tasks

### T1: Create `_setsid-exec.sh`
New shared utility. Perl POSIX setsid wrapper that runs a command in its own process group. Returns the child's exit code. Enables clean `kill -- -$PGID` on timeout.

### T2: Update `_portable-timeout.sh` with setsid integration
Add a `portable_timeout_pgid` function that uses `_setsid-exec.sh` to run the command in its own process group, then kills the entire group on timeout. Keep original `portable_timeout` for backward compat.

### T3: Increase TIMEOUT_SECONDS from 180 to 360
Simple constant change in adversarial-review.sh line 28.

### T4: Add NODE_OPTIONS and --bare flag
Before claude invocation: `export NODE_OPTIONS="--max-old-space-size=3584"`. Add `--bare` flag to `claude --print` invocation.

### T5: Replace perl alarm with setsid + process-group timeout
Replace the remote `perl -e 'alarm ...'` with a remote-side setsid + timeout approach. The remote runs the command via setsid in its own PGID, with a watchdog that kills the entire group on timeout.

### T6: Add orphan cleanup between retries
Before retry attempt: `ssh $NODE 'pkill -f "claude.*print"'` to kill any orphaned claude processes.

### T7: Fix timeout detection exit codes
Replace `exit 124/142` checks with process-group-aware detection. The setsid approach returns 124 on timeout consistently.

## Tests
Shell scripts — non-testable with vitest. Will verify via review + manual inspection. TDD step skipped.
