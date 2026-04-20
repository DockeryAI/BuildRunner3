# Phase 5 Verification: Adversarial Dispatch Hardening

## Deliverable Checklist

| # | Deliverable | Status | Evidence |
|---|------------|--------|----------|
| 1 | Create `_setsid-exec.sh` | PASS | File exists at `~/.buildrunner/scripts/_setsid-exec.sh`, executable, uses `perl POSIX::setsid` |
| 2 | Replace perl alarm with setsid + pgid timeout | PASS | adversarial-review.sh lines 223-238: remote setsid + watchdog replaces `perl -e 'alarm ...'` |
| 3 | Add `--bare` flag to claude --print | PASS | Line 226: `claude --print --bare` |
| 4 | Add NODE_OPTIONS max-old-space-size=3584 | PASS | Line 223: `export NODE_OPTIONS='--max-old-space-size=3584'` |
| 5 | Increase TIMEOUT_SECONDS to 360 | PASS | Line 28: `TIMEOUT_SECONDS=360` |
| 6 | Orphan cleanup between retries | PASS | Lines 209-212: `pkill -f "claude.*print"` before retry |
| 7 | Fix timeout detection exit codes | PASS | Lines 274, 291: only checks `$EXIT_CODE -eq 124`, removed 142 check |

## Syntax Validation
- `bash -n adversarial-review.sh` — PASS
- `bash -n _setsid-exec.sh` — PASS
- `bash -n _portable-timeout.sh` — PASS

## Shell Quoting Verification
- `$REMOTE_DIR` in SSH command: correctly breaks out of single quotes for local expansion
- `$TIMEOUT_SECONDS` in SSH command: correctly breaks out of single quotes for local expansion
- Remote-side variables (`$CHILD_PID`, `$WATCHDOG_PID`, etc.) stay inside single quotes — correct
