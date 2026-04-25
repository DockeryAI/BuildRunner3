# Plan — burnin-queue-v2

## Purpose

Repair the burn-in harness so fix dispatch is genuinely serialized through a real queue, the state machine has a single canonical implementation, and stranded cases have explicit recovery flows. Folds in the round-3 cross-model review that surfaced the contract bug, schema gaps, and ordering inversion left behind by `BUILD_burnin-harness-reliability`.

## Prior-State Survey

**File:** `.buildrunner/plans/survey-burnin-queue-v2.md`

Prior BUILD `burnin-harness-reliability` (6 phases COMPLETE) added the reaper, fix-loop timeout, and watchd LaunchAgent but left three load-bearing problems in place: (1) `fixing` means "needs fix" rather than "worker-owned," (2) the queue table has no `worker_id`/`claim_at`/heartbeat/uniqueness, (3) `_run_one` still dispatches in-process. This build supersedes those decisions in the same files.

## Contract Change

`fixing` = "a worker has claimed this case and is actively running the fix loop."
A failure that is not yet claimed sits in a new `deferred` status on the queue, NOT in the `fixing` case-state.
`needs_human` is reserved for cases that have exhausted the fix budget OR have been explicitly marked by the operator. Autoheal-off failures land in `deferred`, not `needs_human`.

## Phases

### Phase 1: Schema migration + contract definition

**Bucket:** terminal-build · **Node:** muddy
**Files:**

- `~/.buildrunner/burnin/schema.sql` (MODIFY — additive only)
- `~/.buildrunner/burnin/CONTRACT.md` (NEW)
- `~/.buildrunner/dashboard/events.db` (MODIFY — apply migration)

**Blocked by:** None
**Deliverables:**

- [ ] Add columns to `fix_requests`: `worker_id TEXT`, `claim_at TEXT`, `heartbeat_at TEXT`, `lease_expires_at TEXT`, `enqueue_reason TEXT`. Use `ALTER TABLE ADD COLUMN`; idempotent.
- [ ] Extend `status` CHECK constraint to include `deferred` and `claimed`. Sqlite requires table rebuild for CHECK changes — script must do `BEGIN; CREATE TABLE …_new …; INSERT INTO …_new SELECT …; DROP …; ALTER TABLE …_new RENAME …; COMMIT;` preserving FKs and indexes.
- [ ] Add unique partial index: `CREATE UNIQUE INDEX idx_fix_requests_open_one_per_case ON fix_requests(case_id) WHERE status IN ('requested','deferred','claimed');` — enforces one open request per case.
- [ ] Add a `deferred_reason TEXT` column to `burnin_cases` for operator-visible reason text on cases linked to a deferred queue entry.
- [ ] Write `CONTRACT.md`: state-machine table, queue-status table, the three invariants (one open request per case; fixing ⇔ active worker holds a claim; deferred ⇒ no worker, can be drained on resume).
- [ ] Smoke: re-running migration is a no-op; existing rows preserved; dashboard read queries still return.

**Success Criteria:**

- `PRAGMA table_info(fix_requests)` shows the five new columns.
- `SELECT sql FROM sqlite_master WHERE name='idx_fix_requests_open_one_per_case'` returns the unique partial index.
- Inserting two `requested` rows for the same `case_id` raises a UNIQUE constraint failure.

### Phase 2: Atomic failure-transition + enqueue; canonicalize state machine

**Bucket:** backend-build · **Node:** muddy
**Files:**

- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/runner.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/state.sh` (MODIFY — delete dead code)

**Blocked by:** Phase 1
**Deliverables:**

- [ ] Replace the two-call sequence in `runner.sh:185-204` with a single new `db_failure_transition_and_enqueue` (distinct function name; the existing `db_advance_and_transition` becomes worker-only in Phase 5) that does state transition + queue insert in one `BEGIN IMMEDIATE … COMMIT` block.
- [ ] On failure with autoheal ON: case stays `untested`/`probation` (no `fixing` flip), queue gets a `requested` row.
- [ ] On failure with autoheal OFF: case stays `untested`/`probation`, queue gets a `deferred` row with `enqueue_reason='autoheal_off'`, case's `deferred_reason` populated.
- [ ] Delete `state_advance_after_run` and the dead `state.sh:64-127` body. Update the one snapshot import path. State machine has exactly one implementation.
- [ ] Delete the `db_record_fix_skip` function from `db.sh` entirely (call sites are removed in Phase 4 — see `_run_one` SIGINT trap and the autoheal-off branch). The function and its callers leave the codebase in this build, in two phases for sequencing safety: Phase 2 removes the function definition and all non-SIGINT callers; Phase 4 removes the SIGINT trap that was the last remaining caller in `_run_one`.
- [ ] Smoke: forced failure with autoheal=on writes one `requested` row; with autoheal=off writes one `deferred` row; both leave case in pre-failure state (not `fixing`).

**Success Criteria:**

- `grep -n state_advance_after_run ~/.buildrunner/scripts/burnin/lib/` returns nothing outside snapshots.
- Crash-injected test (kill between the two old calls' positions) leaves no orphan stub or unmatched state.

### Phase 3: Worker daemon (separate LaunchAgent, lease-based, single-flight)

**Bucket:** terminal-build · **Node:** muddy
**Files:**

- `~/.buildrunner/scripts/burnin/lib/worker.sh` (NEW)
- `~/Library/LaunchAgents/com.buildrunner.burnin-fix-worker.plist` (NEW)
- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY — add claim/heartbeat/release helpers)

**Blocked by:** Phase 1, Phase 2
**Deliverables:**

- [ ] `db_claim_next_request`: `BEGIN IMMEDIATE; SELECT fix_id FROM fix_requests WHERE status='requested' ORDER BY created_at LIMIT 1; UPDATE fix_requests SET status='claimed', worker_id=:wid, claim_at=:now, heartbeat_at=:now, lease_expires_at=datetime(:now,'+15 minutes') WHERE fix_id=:fix_id AND status='requested'; COMMIT;` — explicit `WHERE fix_id=? AND status='requested'` predicate is the check-and-set guard; returns the claimed row only if the UPDATE affected one row.
- [ ] `db_heartbeat_request`: bump `heartbeat_at` and extend `lease_expires_at` while attempt is running.
- [ ] `db_release_request`: terminal status set on completion (applied/rejected/failed/aborted) plus `resolved_at`.
- [ ] `worker.sh` main loop: poll for claim every 5s; on claim → flip case to `fixing` → run `fix_loop_run` → on success flip `fixing → probation` → on exhaustion flip `fixing → needs_human` → release request.
- [ ] Single-flight enforced by the partial unique index from Phase 1, NOT by an OS file lock. One worker process per host enforced by LaunchAgent KeepAlive=true + the worker_id being the PID.
- [ ] Plist: `KeepAlive=true`, `RunAtLoad=true`, env `BR3_BURNIN_WORKER_ID=$(hostname)-fix`, stdout/stderr to `~/.buildrunner/burnin/fix-worker.log`.
- [ ] Smoke: enqueue 3 cases simultaneously; verify worker processes them strictly serially; verify a killed worker mid-attempt has its claim reaped (Phase 5).

**Success Criteria:**

- `ps -ef | grep burnin-fix-worker` shows exactly one process under launchd.
- Concurrent `db_claim_next_request` calls (two shells) only one wins; the other gets empty.
- Heartbeat updates visible in `fix_requests.heartbeat_at` while a fix is running.

### Phase 4: Route every trigger through the queue

**Bucket:** backend-build · **Node:** muddy
**Files:**

- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/watchd.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/canary.sh` (MODIFY)

**Blocked by:** Phase 3
**Deliverables:**

- [ ] Remove the in-process `fix_loop_run` call from `_run_one` (burnin.sh:271-288). Failure path simply enqueues via Phase 2's atomic helper.
- [ ] `cmd_fix <id>` enqueues a `requested` row with `enqueue_reason='operator'` and exits. Add `cmd_fix --wait <id>` flag that polls the request to terminal status (default behavior remains async to match the new contract; `--wait` is explicit).
- [ ] `watchd.sh` fswatch-driven retry: on case file change, enqueue if no open request exists; never call `fix_loop_run` directly.
- [ ] `canary.sh` failure: enqueue with `enqueue_reason='canary'`.
- [ ] Remove the SIGINT trap in `_run_one` that wrote `db_record_fix_skip`; no longer needed since dispatch isn't in-process.
- [ ] Smoke: trigger a failure via each path (manual run, watchd file event, canary); verify exactly one row appears per case in `fix_requests` and the worker picks them up serially.

**Success Criteria:**

- `grep -n 'fix_loop_run' ~/.buildrunner/scripts/burnin/{burnin.sh,lib/watchd.sh,lib/canary.sh}` returns no callers — only `worker.sh` invokes the fix loop.
- Two simultaneous failure events for two different cases produce two queue entries; worker processes them one at a time.

### Phase 5: State-machine fix + cleanup migration of existing data

**Bucket:** backend-build · **Node:** muddy
**Files:**

- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY — `db_advance_and_transition` final form)
- `~/.buildrunner/scripts/burnin/lib/state.sh` (MODIFY — supervisor functions)
- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY — remove reap from cmd_status)

**Blocked by:** Phase 4
**Deliverables:**

- [ ] In `db_advance_and_transition` (now only ever called by `worker.sh`): when src=`fixing` and passed=1 → target=`probation`. When src=`probation` and passed=1 and `consecutive_greens+1 >= promote_after` → target=`promoted`. Add explicit case for src=`needs_human` (worker should never see this; assert and abort).
- [ ] Add `db_reap_expired_claims`: `UPDATE fix_requests SET status='aborted', resolver='timeout' WHERE status='claimed' AND datetime(lease_expires_at) < datetime('now')`. Cases linked to those expired claims flip back to their pre-claim state (recorded in a new `claim_origin_state` column added in Phase 1 — add it there, not here).
- [ ] Wire `db_reap_expired_claims` into the worker's main loop (every claim attempt also reaps first) and into watchd's reaper sidecar (fallback if worker is dead).
- [ ] Remove `state_reap_stale_fixing` call from `cmd_status` (burnin.sh:81-119). `cmd_status` becomes pure read.
- [ ] Smoke: kill worker mid-attempt; confirm next worker startup or watchd reaper tick releases the claim and case is re-queueable.

**Success Criteria:**

- A green re-run from `fixing` provably advances the case to `probation` (verified by SQL snapshot before/after).
- `cmd_status` produces zero writes (verified by sqlite trace).
- Killed mid-attempt → claim released within 15min lease window.

### Phase 6: Operator flows + cost-cap accounting + emergency cohort recovery

**Bucket:** backend-build · **Node:** muddy
**Files:**

- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY — add `recover` and `resume` subcommands)
- `~/.buildrunner/scripts/burnin/lib/cost.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/recover-stranded.sh` (NEW — one-shot for the existing 38-case cohort)

**Blocked by:** Phase 5
**Deliverables:**

- [ ] `burnin recover [--all | <id>...]`: explicitly transitions selected `needs_human` cases → `untested` (transition allowed by table) and enqueues a `requested` row with `enqueue_reason='recovery'`.
- [ ] `burnin resume`: scans for `deferred` rows with `enqueue_reason='autoheal_off'` and flips them to `requested` if autoheal is currently ON. No-op if autoheal is still off.
- [ ] `cost_check_daily_cap`: change query from `COUNT(*) FROM fix_requests WHERE DATE(created_at)=DATE('now')` to `COUNT(*) FROM fix_requests WHERE DATE(claim_at)=DATE('now') AND status IN ('claimed','applied','rejected','failed')` — counts real Claude invocations, not enqueue volume. (Use `DATE('now')`, not the literal string `'today'`.)
- [ ] `recover-stranded.sh`: one-shot script that selects existing `needs_human` cases via `SELECT id FROM burnin_cases WHERE state='needs_human' AND last_failure LIKE '%reaped from stale fixing%'` (the `last_failure` column is pre-existing on `burnin_cases`; verified in current schema) and runs `burnin recover` on them. Operator runs once after Phase 6 lands.
- [ ] Smoke: run `recover-stranded.sh` against a snapshot DB; confirm cases enter the queue and the worker drains them one by one.

**Success Criteria:**

- `burnin recover sharding-process-detector-mac` enqueues exactly one `requested` row for that case and the worker picks it up.
- `cost_check_daily_cap` returns 0 invocations when the only fix_requests rows are `deferred` (i.e. enqueue ≠ spend).
- After running `recover-stranded.sh`, the 38-case cohort drains over time without operator intervention.

### Phase 7: E2E verification

**Bucket:** qa · **Node:** walter
**Files:**

- `.buildrunner/verify/burnin-queue-v2.md` (NEW — project-relative; lives at the repo root, not in `~/.buildrunner/`)
- `~/.buildrunner/burnin/logs/` (writes during verification)
- `~/.buildrunner/burnin/snapshots/events.db.20260425` (NEW — production snapshot for Scenario E)

**Blocked by:** Phase 6
**Deliverables:**

- [ ] Scenario A (autoheal ON, failure): inject failure → confirm one `requested` row → confirm worker claims, runs, releases → confirm case ends `probation` (after one green) or `needs_human` (after budget exhaustion).
- [ ] Scenario B (autoheal OFF, failure): inject failure → confirm `deferred` row → confirm case stays `probation` with `deferred_reason` populated → flip autoheal ON, run `burnin resume` → confirm row promotes to `requested` and worker picks up.
- [ ] Scenario C (concurrent failures): trigger 5 simultaneous failures across 5 different cases → confirm exactly 5 queue rows → confirm worker processes them strictly serially (claim_at timestamps strictly ascending, no overlap of `claimed` status).
- [ ] Scenario D (worker crash): start a fix attempt → kill -9 the worker mid-loop → confirm next watchd reaper tick or worker restart releases the claim → confirm case re-enters the queue and completes.
- [ ] Scenario E (cohort recovery): take an online snapshot via `sqlite3 ~/.buildrunner/dashboard/events.db ".backup ~/.buildrunner/burnin/snapshots/events.db.20260425"` → apply migration against the snapshot copy (use `BR3_BURNIN_DB=~/.buildrunner/burnin/snapshots/events.db.20260425` env override on the harness) → run `recover-stranded.sh` against the snapshot → confirm all 38 cases drain through the worker.
- [ ] Scenario F (`burnin recover --all`): point harness at a fresh snapshot containing ≥2 `needs_human` cases → run `burnin recover --all` → confirm every matching case enqueues exactly one `requested` row and the worker drains them serially.
- [ ] Document each scenario's command sequence + expected SQL state in `verify/burnin-queue-v2.md`.

**Success Criteria:**

- All six scenarios (A–F) pass without operator intervention beyond the documented steps.
- No case lands in `fixing` without an active worker claim during any scenario.
- No two `claimed` rows ever exist simultaneously across the run.

## Out of Scope (Future)

- Multi-host fix workers (worker stays single-host; the unique partial index would let us add this later).
- Adaptive fix budgets per case (still global `BR3_BURNIN_MAX_ATTEMPTS=3`).
- Dashboard UI for queue depth (read-only API exposure only; UI is a follow-up).
- Migrating existing snapshot DBs older than 7 days (one-shot recovery script handles current cohort only).

## Parallelization Matrix

| Phase | Key Files                                                     | Can Parallel With | Blocked By |
| ----- | ------------------------------------------------------------- | ----------------- | ---------- |
| 1     | schema.sql, CONTRACT.md, events.db migration                  | —                 | —          |
| 2     | lib/db.sh, lib/runner.sh, lib/state.sh                        | —                 | 1          |
| 3     | lib/worker.sh (NEW), burnin-fix-worker.plist (NEW), lib/db.sh | —                 | 1, 2       |
| 4     | burnin.sh, lib/watchd.sh, lib/canary.sh                       | —                 | 3          |
| 5     | lib/db.sh, lib/state.sh, burnin.sh                            | —                 | 4          |
| 6     | burnin.sh, lib/cost.sh, recover-stranded.sh (NEW)             | —                 | 5          |
| 7     | verify/burnin-queue-v2.md (NEW)                               | —                 | 6          |

Mostly serial — schema → atomic-ops → worker → routing → bug-fix → operator-flows → verify. This is intentional: every phase corrects a real prerequisite for the next, per Codex round-3 ordering guidance.
