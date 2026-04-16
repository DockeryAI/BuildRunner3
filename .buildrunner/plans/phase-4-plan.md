# Phase 4 Plan: /commit Hard Walter Gate + Direct Push

## Goal

Walter is a hard requirement for all commits — no graceful degradation, no silent skips.

## Pre-work

- Standardize walter remote name to "walter" (walter-seed.sh currently uses "walter-sentinel")

## Tasks

### Task 1: commit.md Step 6.5 — Hard block on Walter offline

**Files:** `~/.claude/commands/commit.md` (lines 217-256)
**Changes:**

- Change `WALTER_GATE="SKIP"` default to `WALTER_GATE="BLOCK"`
- Replace `WARN_OFFLINE` path: set `WALTER_GATE="BLOCK"` with message "Walter is offline — commit blocked"
- Replace the `else` clause (no WALTER_URL) from SKIP to BLOCK with reason
- Remove "graceful degradation" language
- Keep `--force` override path intact

### Task 2: commit.md Step 7 — Direct push to Walter

**Files:** `~/.claude/commands/commit.md` (lines 293-300)
**Changes:**

- After `git push origin`, add walter remote setup + synchronous push
- `git remote add walter ssh://10.0.1.102/~/repos/$PROJECT` if missing
- `git push walter HEAD:refs/heads/current --force-with-lease`
- Push failure = commit aborted (unless `--force`)

### Task 3: auto-save-session.sh — Remove backgrounding, hard error

**Files:** `~/.buildrunner/scripts/auto-save-session.sh` (lines 119-148)
**Changes:**

- Line 135: Remove `&` backgrounding from walter push, remove `2>/dev/null`
- Log push result (success or failure) to WALTER_LOG
- Line 147: Change `status=skipped reason=unreachable` to `status=error reason=unreachable` + exit 1
- Add stderr message when Walter unreachable

### Task 4: receive.denyCurrentBranch in provisioning

**Files:**

- `core/cluster/node_tests.py` (`_ensure_repo`, ~line 260)
- `~/.buildrunner/scripts/walter-seed.sh` (provisioning, ~line 110)
  **Changes:**
- `_ensure_repo()`: after `git init --bare`, add `git config receive.denyCurrentBranch updateInstead`
- `walter-seed.sh`: after provision API call, ssh to Walter and set the config
- Change remote name from "walter-sentinel" to "walter"

## Tests

No unit tests — these are CLI instructions (markdown), shell scripts, and a git config addition to a Python helper. Verification at Step 6.5 covers correctness.

## Risks

- Hard Walter requirement means commits fail if Walter is down → `--force` escape hatch
- auto-save-session.sh exit 1 could affect hooks — need to scope the error to walter section only
