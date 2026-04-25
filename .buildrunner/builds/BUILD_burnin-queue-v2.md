# Build: burnin-queue-v2

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: terminal-build, assigned_node: muddy }
      phase_2: { bucket: backend-build, assigned_node: muddy }
      phase_3: { bucket: terminal-build, assigned_node: muddy }
      phase_4: { bucket: backend-build, assigned_node: muddy }
      phase_5: { bucket: backend-build, assigned_node: muddy }
      phase_6: { bucket: backend-build, assigned_node: muddy }
      phase_7: { bucket: qa, assigned_node: walter }
```

**Created:** 2026-04-25
**Status:** BUILD COMPLETE — All 7 Phases Done
**Deploy:** operator-tooling — no user-facing deploy; changes live under `~/.buildrunner/scripts/burnin/` and `~/Library/LaunchAgents/`.
**Source Plan File:** .buildrunner/plans/plan-burnin-queue-v2.md
**Source Plan SHA:** 830e493397dc97f8e71253c2f34f6344a4917274e03a18d5f1e1bf1fbed5d2af
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-25T13:40:14Z
**Prior-State Survey:** .buildrunner/plans/survey-burnin-queue-v2.md
**Owner:** byronhudson

## Overview

Repair the burn-in harness so fix dispatch is genuinely serialized through a real queue, the state machine has a single canonical implementation, and stranded cases have explicit recovery flows. Supersedes decisions made in `BUILD_burnin-harness-reliability` Phases 3 and 4 in the same files. Contract change: `fixing` means "worker has claimed this case," not "needs fix"; pre-claim failures sit in queue status `requested` (autoheal on) or `deferred` (autoheal off), not in case-state `fixing`. `needs_human` is reserved for budget exhaustion or explicit operator action.

## Parallelization Matrix

| Phase | Key Files                                                                                                                                         | Can Parallel With | Blocked By |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ---------- |
| 1     | `~/.buildrunner/burnin/schema.sql`, `~/.buildrunner/burnin/CONTRACT.md` (NEW), `~/.buildrunner/dashboard/events.db`                               | —                 | —          |
| 2     | `~/.buildrunner/scripts/burnin/lib/{db,runner,state}.sh`                                                                                          | —                 | 1          |
| 3     | `~/.buildrunner/scripts/burnin/lib/worker.sh` (NEW), `~/Library/LaunchAgents/com.buildrunner.burnin-fix-worker.plist` (NEW), `lib/db.sh`          | —                 | 1, 2       |
| 4     | `~/.buildrunner/scripts/burnin/burnin.sh`, `~/.buildrunner/scripts/burnin/lib/{watchd,canary}.sh`                                                 | —                 | 3          |
| 5     | `~/.buildrunner/scripts/burnin/lib/{db,state}.sh`, `~/.buildrunner/scripts/burnin/burnin.sh`                                                      | —                 | 4          |
| 6     | `~/.buildrunner/scripts/burnin/burnin.sh`, `~/.buildrunner/scripts/burnin/lib/cost.sh`, `~/.buildrunner/scripts/burnin/recover-stranded.sh` (NEW) | —                 | 5          |
| 7     | `.buildrunner/verify/burnin-queue-v2.md` (NEW), `~/.buildrunner/burnin/snapshots/events.db.20260425` (NEW)                                        | —                 | 6          |

## Phases

### Phase 1: Schema migration + contract definition

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/burnin/schema.sql` (MODIFY — additive only)
- `~/.buildrunner/burnin/CONTRACT.md` (NEW)
- `~/.buildrunner/dashboard/events.db` (MODIFY — apply migration)

**Blocked by:** None
**Deliverables:**

- [x] Add columns to `fix_requests`: `worker_id TEXT`, `claim_at TEXT`, `heartbeat_at TEXT`, `lease_expires_at TEXT`, `enqueue_reason TEXT`, `claim_origin_state TEXT`. Use `ALTER TABLE ADD COLUMN`; idempotent.
- [x] Extend `status` CHECK constraint to include `deferred` and `claimed`. SQLite requires table rebuild for CHECK changes — do `BEGIN; CREATE TABLE …_new …; INSERT INTO …_new SELECT …; DROP …; ALTER TABLE …_new RENAME …; COMMIT;` preserving FKs and indexes.
- [x] Add unique partial index `idx_fix_requests_open_one_per_case ON fix_requests(case_id) WHERE status IN ('requested','deferred','claimed')` — enforces one open request per case.
- [x] Add `deferred_reason TEXT` column to `burnin_cases` for operator-visible reason text.
- [x] Write `CONTRACT.md`: state-machine table, queue-status table, the three invariants (one open request per case; fixing ⇔ active worker holds a claim; deferred ⇒ no worker, drainable on resume).
- [x] Smoke: re-running migration is a no-op; existing rows preserved; dashboard read queries still return.

**Success Criteria:**

- `PRAGMA table_info(fix_requests)` shows the six new columns.
- `SELECT sql FROM sqlite_master WHERE name='idx_fix_requests_open_one_per_case'` returns the unique partial index.
- Inserting two `requested` rows for the same `case_id` raises a UNIQUE constraint failure.

### Phase 2: Atomic failure-transition + enqueue; canonicalize state machine

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/runner.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/state.sh` (MODIFY — delete dead code)

**Blocked by:** Phase 1
**Deliverables:**

- [x] Replace the two-call sequence in `runner.sh:185-204` with a new `db_failure_transition_and_enqueue` (distinct from the worker-side `db_advance_and_transition`, which becomes worker-only in Phase 5) that does state transition + queue insert in one `BEGIN IMMEDIATE … COMMIT` block.
- [x] On failure with autoheal ON: case stays `untested`/`probation` (no `fixing` flip), queue gets a `requested` row.
- [x] On failure with autoheal OFF: case stays `untested`/`probation`, queue gets a `deferred` row with `enqueue_reason='autoheal_off'`, case's `deferred_reason` populated.
- [x] Delete `state_advance_after_run` and the dead `state.sh:64-127` body. Update the one snapshot import path. State machine has exactly one implementation.
- [x] Delete the `db_record_fix_skip` function from `db.sh` entirely; remove all non-SIGINT call sites. (The SIGINT trap caller in `_run_one` is removed in Phase 4 — sequencing is intentional.)
- [x] Smoke: forced failure with autoheal=on writes one `requested` row; with autoheal=off writes one `deferred` row; both leave case in pre-failure state (not `fixing`).

**Success Criteria:**

- `grep -n state_advance_after_run ~/.buildrunner/scripts/burnin/lib/` returns nothing outside snapshots.
- Crash-injected test (kill between the two old calls' positions) leaves no orphan stub or unmatched state.

### Phase 3: Worker daemon (separate LaunchAgent, lease-based, single-flight)

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/lib/worker.sh` (NEW)
- `~/Library/LaunchAgents/com.buildrunner.burnin-fix-worker.plist` (NEW)
- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY — add claim/heartbeat/release helpers)

**Blocked by:** Phase 1, Phase 2
**Deliverables:**

- [x] `db_claim_next_request`: `BEGIN IMMEDIATE; SELECT fix_id FROM fix_requests WHERE status='requested' ORDER BY created_at LIMIT 1; UPDATE fix_requests SET status='claimed', worker_id=:wid, claim_at=:now, heartbeat_at=:now, lease_expires_at=datetime(:now,'+15 minutes') WHERE fix_id=:fix_id AND status='requested'; COMMIT;` — explicit check-and-set guard; returns row only if the UPDATE affected one row.
- [x] `db_heartbeat_request`: bump `heartbeat_at` and extend `lease_expires_at` while attempt is running.
- [x] `db_release_request`: terminal status set on completion (applied/rejected/failed/aborted) + `resolved_at`.
- [x] `worker.sh` main loop: poll for claim every 5s; on claim → flip case to `fixing` → run `fix_loop_run` → on success flip `fixing → probation` → on exhaustion flip `fixing → needs_human` → release request. Lease-loss SIGTERM aborts the running fix and re-polls.
- [x] Single-flight enforced by the partial unique index from Phase 1, NOT by an OS file lock. One worker process per host enforced by LaunchAgent KeepAlive=true + `worker_id=$(hostname)-fix-$$`.
- [x] Plist: `KeepAlive=true`, `RunAtLoad=true`, env `BR3_BURNIN_WORKER_ID=$(hostname)-fix`, stdout/stderr to `~/.buildrunner/burnin/fix-worker.log`.
- [x] Smoke: enqueue 3 cases simultaneously; verify worker processes them strictly serially; lease-lost smoke confirms running fix is terminated and worker re-polls.

**Success Criteria:**

- `ps -ef | grep burnin-fix-worker` shows exactly one process under launchd.
- Concurrent `db_claim_next_request` calls (two shells) only one wins; the other gets empty.
- Heartbeat updates visible in `fix_requests.heartbeat_at` while a fix is running.

### Phase 4: Route every trigger through the queue

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/watchd.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/canary.sh` (MODIFY)

**Blocked by:** Phase 3
**Deliverables:**

- [x] Remove the in-process `fix_loop_run` call from `_run_one` (burnin.sh:271-288). Failure path simply enqueues via Phase 2's atomic helper.
- [x] `cmd_fix <id>` enqueues a `requested` row with `enqueue_reason='operator'` and exits. `cmd_fix --wait <id>` polls to terminal status with a `BR3_BURNIN_FIX_WAIT_TIMEOUT`-bounded deadline (default 300s).
- [x] `watchd.sh` fswatch-driven retry: on case file change, `watchd_enqueue_case` does INSERT OR IGNORE on red cases only; never calls `fix_loop_run` directly.
- [x] `canary.sh` failure: enqueue with `enqueue_reason='canary'`. Promotion is `deferred → requested` only — claimed and requested rows are left untouched to preserve audit trail.
- [x] Remove the SIGINT trap in `_run_one` that wrote `db_record_fix_skip` — last remaining caller of the function deleted in Phase 2.
- [x] Smoke: trigger a failure via each path (manual run, watchd file event, canary); verify exactly one row appears per case in `fix_requests` and the worker picks them up serially.

**Success Criteria:**

- `grep -n 'fix_loop_run' ~/.buildrunner/scripts/burnin/{burnin.sh,lib/watchd.sh,lib/canary.sh}` returns no callers — only `worker.sh` invokes the fix loop.
- Two simultaneous failure events for two different cases produce two queue entries; worker processes them one at a time.

### Phase 5: State-machine fix + lease-expiry reaper + read-only status

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY — `db_advance_and_transition` final form)
- `~/.buildrunner/scripts/burnin/lib/state.sh` (MODIFY — supervisor functions)
- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY — remove reap from `cmd_status`)

**Blocked by:** Phase 4
**Deliverables:**

- [x] In `db_advance_and_transition` (now only ever called by `worker.sh`): when src=`fixing` and passed=1 → target=`probation`. When src=`probation` and passed=1 and `consecutive_greens+1 >= promote_after` → target=`promoted`. Add explicit case for src=`needs_human` (worker should never see this; assert and abort).
- [x] Add `db_reap_expired_claims`: `UPDATE fix_requests SET status='aborted', resolver='timeout' WHERE status='claimed' AND datetime(lease_expires_at) < datetime('now')`. Cases linked to those expired claims flip back to `COALESCE(claim_origin_state, 'probation')` (column added in Phase 1; NULL safely defaults to probation).
- [x] Wire `db_reap_expired_claims` into the worker's main loop (every claim attempt also reaps first) and into watchd's reaper sidecar (fallback if worker is dead).
- [x] Remove `state_reap_stale_fixing` call from `cmd_status` (burnin.sh:81-119). `cmd_status` becomes pure read.
- [x] Smoke: kill worker mid-attempt; confirm next worker startup or watchd reaper tick releases the claim and case is re-queueable.

**Success Criteria:**

- A green re-run from `fixing` provably advances the case to `probation` (verified by SQL snapshot before/after).
- `cmd_status` produces zero writes (verified by sqlite trace).
- Killed mid-attempt → claim released within 15min lease window.

### Phase 6: Operator flows + cost-cap accounting + emergency cohort recovery

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY — add `recover` and `resume` subcommands)
- `~/.buildrunner/scripts/burnin/lib/cost.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/recover-stranded.sh` (NEW — one-shot)

**Blocked by:** Phase 5
**Deliverables:**

- [x] `burnin recover [--all | <id>...]`: explicitly transitions selected `needs_human` cases → `untested` (transition allowed by table) and enqueues a `requested` row with `enqueue_reason='recovery'`. Atomic CTE gates on no existing open request, preserving I-1.
- [x] `burnin resume`: scans for `deferred` rows with `enqueue_reason='autoheal_off'` and flips them to `requested` if autoheal is currently ON. No-op if autoheal still off. Canary-deferred rows untouched.
- [x] `cost_check_daily_cap`: query is `COUNT(*) FROM fix_requests WHERE DATE(claim_at)=DATE('now') AND status IN ('claimed','applied','rejected','failed')` — counts real Claude invocations, not enqueue volume. Uses `DATE('now')`, not literal `'today'`.
- [x] `recover-stranded.sh`: one-shot script `SELECT id FROM burnin_cases WHERE state='needs_human' AND last_failure LIKE '%reaped from stale fixing%'` and `exec`s `burnin recover` on them (propagates exit code).
- [x] Smoke: snapshot cohort of 36 stranded cases drained — `recover_stranded_count=36`, worker processed them with `claims:36|releases:36|max_inflight:1`.

**Success Criteria:**

- `burnin recover sharding-process-detector-mac` enqueues exactly one `requested` row for that case and the worker picks it up.
- `cost_check_daily_cap` returns 0 invocations when the only fix_requests rows are `deferred` (i.e. enqueue ≠ spend).
- After running `recover-stranded.sh`, the 38-case cohort drains without operator intervention.

### Phase 7: E2E verification

**Status:** ✅ COMPLETE
**Files:**

- `.buildrunner/verify/burnin-queue-v2.md` (NEW — project-relative; lives at the repo root, not in `~/.buildrunner/`)
- `~/.buildrunner/burnin/logs/` (writes during verification)
- `~/.buildrunner/burnin/snapshots/events.db.20260425` (NEW — production snapshot for Scenario E)

**Blocked by:** Phase 6
**Deliverables:**

- [x] Scenario A (autoheal ON, failure): 1 `requested` row, worker drained, case ended `needs_human` after budget exhaustion (history `failed,applied,applied,applied`).
- [x] Scenario B (autoheal OFF, failure): 1 `deferred` row, `case_state_and_deferred_reason=probation|1`; `burnin resume` promoted to `requested`; worker drained.
- [x] Scenario C (concurrent failures): 5 simultaneous `burnin run` produced exactly 5 `requested` rows; worker processed strictly serially (`claimed_rows_after_drain=0`).
- [x] Scenario D (worker crash): `kill -9` mid-loop → forced lease expiry → worker restart reaped claim (`status=aborted`, case → `untested`); second canonical trigger re-entered queue.
- [x] Scenario E (cohort recovery): snapshot captured (2.2GB), migrated to v2; `recover-stranded.sh` (after CF-1 fix to use `fix_attempts<3 AND NOT LIKE '%budget exhausted%'`) matches all 36 stranded cases. The 38-case cohort = 36 stranded + 2 controls (`walter-trigger-logs` budget-exhausted, `fix-loop-exhaust` missing plugin).
- [x] Scenario F (`burnin recover --all`): fresh synthetic 2-row snapshot enqueued exactly 2 `requested` rows; worker drained serially; `open_after_drain=0`.
- [x] Each scenario documented with command sequence + expected SQL state in `.buildrunner/verify/burnin-queue-v2.md`.

**Success Criteria:**

- All six scenarios (A–F) pass without operator intervention beyond the documented steps.
- No case lands in `fixing` without an active worker claim during any scenario.
- No two `claimed` rows ever exist simultaneously across the run.

## Out of Scope (Future)

- Multi-host fix workers (worker stays single-host; the unique partial index would let us add this later).
- Adaptive fix budgets per case (still global `BR3_BURNIN_MAX_ATTEMPTS=3`).
- Dashboard UI for queue depth (read-only API exposure only; UI is a follow-up).
- Migrating snapshot DBs older than 7 days (one-shot recovery script handles current cohort only).

## Session Log

[Will be updated by /begin]
