# Verify Report — burnin-queue-v2

**Date:** 2026-04-25
**Runner:** Codex
**Build:** `.buildrunner/builds/BUILD_burnin-queue-v2.md`

## Summary

Scenarios A-F were exercised end-to-end against isolated verification databases.
Scenarios A-D used a disposable temp harness rooted at `/tmp/br3-burnin-phase7`.
Scenario E used the required production snapshot at
`~/.buildrunner/burnin/snapshots/events.db.20260425`.
Scenario F used a fresh synthetic snapshot with two valid `needs_human` rows to
verify `burnin recover --all` independently of unrelated production data issues.

Two clarifications from the run:

- Scenario D re-entered the queue only after a second canonical failure trigger
  (`burnin run phase7-d`) following claim reaping. This matches the contract's
  trigger inventory: reaping releases claims, it does not enqueue new work.
- The live 2026-04-25 production snapshot contains `38` `needs_human` rows, but
  only `36` are the stranded cohort. The other two are explicit non-stranded
  controls: `walter-trigger-logs` (budget exhausted) and `fix-loop-exhaust`
  (missing plugin YAML).

## Scenario A — Autoheal ON Failure

Command sequence:

```bash
cd /tmp/br3-burnin-phase7/repo
env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    BR3_BURNIN_AUTOHEAL=on \
    ~/.buildrunner/scripts/burnin/burnin.sh run phase7-a

sqlite3 /tmp/br3-burnin-phase7/events.db \
  "SELECT COUNT(*) FROM fix_requests WHERE case_id='phase7-a' AND status='requested';"

env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    BR3_BURNIN_AUTOAPPLY=1 \
    BR3_BURNIN_FIX_CLAUDE_CMD=/tmp/br3-burnin-phase7/repo/bin/fake-claude-success.sh \
    BR3_BURNIN_WORKER_PROJECT_ROOT=/tmp/br3-burnin-phase7/repo \
    ~/.buildrunner/scripts/burnin/lib/worker.sh
```

Expected SQL state:

- Immediately after the failing run:
  `burnin_cases.state='untested'`
  and one open row in `fix_requests.status='requested'`.
- After worker drain:
  no open queue rows remain.
  The case ends either `probation` after a successful green rerun or
  `needs_human` after budget exhaustion.

Observed:

- `requested_rows=1`
- `pre_worker_case_state=untested`
- `final_case_state=needs_human`
- request history: `failed,applied,applied,applied`

## Scenario B — Autoheal OFF Then Resume

Command sequence:

```bash
cd /tmp/br3-burnin-phase7/repo
printf 'PASS\n' > fixtures/phase7-b.txt
env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    ~/.buildrunner/scripts/burnin/burnin.sh run phase7-b

printf 'FAIL\n' > fixtures/phase7-b.txt
env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    BR3_BURNIN_AUTOHEAL=off \
    ~/.buildrunner/scripts/burnin/burnin.sh run phase7-b

env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    BR3_BURNIN_AUTOHEAL=on \
    ~/.buildrunner/scripts/burnin/burnin.sh resume
```

Expected SQL state:

- After the failing run with autoheal off:
  `burnin_cases.state='probation'`,
  `burnin_cases.deferred_reason IS NOT NULL`,
  and one open row in `fix_requests.status='deferred'`.
- After `burnin resume` with autoheal on:
  the same open row becomes `status='requested'`.
- After worker drain:
  the row is terminal and no open queue rows remain.

Observed:

- `deferred_rows=1`
- `case_state_and_deferred_reason=probation|1`
- `requested_after_resume=1`
- `claimed_and_released_rows=1`

## Scenario C — Five Concurrent Failures

Command sequence:

```bash
cd /tmp/br3-burnin-phase7/repo
printf '%s\n' phase7-c1 phase7-c2 phase7-c3 phase7-c4 phase7-c5 \
| xargs -I{} -P 5 sh -c '
    cd /tmp/br3-burnin-phase7/repo &&
    env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
        BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
        BR3_BURNIN_AUTOHEAL=on \
        ~/.buildrunner/scripts/burnin/burnin.sh run "$1" >/tmp/"$1".out 2>/tmp/"$1".err || true
  ' sh {}

sqlite3 /tmp/br3-burnin-phase7/events.db \
  "SELECT COUNT(*) FROM fix_requests
    WHERE case_id IN ('phase7-c1','phase7-c2','phase7-c3','phase7-c4','phase7-c5')
      AND status='requested';"
```

Expected SQL state:

- After injection:
  exactly five open `requested` rows, one per case.
- After worker drain:
  no open rows remain,
  `claim_at` values are strictly ordered,
  and each `claim_at` is greater than or equal to the previous row's
  `resolved_at` (no overlap).

Observed:

- `requested_rows=5`
- `seriality=serial`
- `claimed_rows_after_drain=0`

## Scenario D — Worker Crash Mid-Loop

Command sequence:

```bash
cd /tmp/br3-burnin-phase7/repo
env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    BR3_BURNIN_AUTOHEAL=on \
    ~/.buildrunner/scripts/burnin/burnin.sh run phase7-d

env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    BR3_BURNIN_FIX_CLAUDE_CMD=/tmp/br3-burnin-phase7/repo/bin/fake-claude-sleep.sh \
    BR3_BURNIN_WORKER_PROJECT_ROOT=/tmp/br3-burnin-phase7/repo \
    ~/.buildrunner/scripts/burnin/lib/worker.sh &

kill -9 <worker-pid>
sqlite3 /tmp/br3-burnin-phase7/events.db \
  "UPDATE fix_requests
     SET lease_expires_at = strftime('%Y-%m-%dT%H:%M:%fZ','now','-1 minute')
   WHERE case_id='phase7-d' AND status='claimed';"

# Restart worker to trigger db_reap_expired_claims on claim polling.
env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    BR3_BURNIN_FIX_CLAUDE_CMD=/tmp/br3-burnin-phase7/repo/bin/fake-claude-needs-human.sh \
    BR3_BURNIN_WORKER_PROJECT_ROOT=/tmp/br3-burnin-phase7/repo \
    ~/.buildrunner/scripts/burnin/lib/worker.sh

# Re-trigger through a canonical enqueue path after reaping.
env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7/events.db \
    BR3_BURNIN_AUTOHEAL=on \
    ~/.buildrunner/scripts/burnin/burnin.sh run phase7-d
```

Expected SQL state:

- After the crash:
  the row remains `status='claimed'` until lease expiry.
- After worker restart/reap:
  the first row becomes `status='aborted'`,
  `resolver='timeout'`,
  and `burnin_cases.state` returns to the original pre-claim state.
- After the second canonical failure trigger:
  a new `requested` row appears and drains to a terminal state.

Observed:

- `post_reap_case_and_first_status=untested|aborted`
- `requested_after_retrigger=1`
- `final_case_state=needs_human`

## Scenario E — Production Snapshot Cohort Recovery

Command sequence:

```bash
sqlite3 ~/.buildrunner/dashboard/events.db \
  ".backup ~/.buildrunner/burnin/snapshots/events.db.20260425"

BR3_BURNIN_DB=~/.buildrunner/burnin/snapshots/events.db.20260425 \
  ~/.buildrunner/burnin/migrate-v1-to-v2.sh

env BR3_EVENTS_DB=~/.buildrunner/burnin/snapshots/events.db.20260425 \
    BR3_BURNIN_ROOT=~/.buildrunner/burnin \
    ~/.buildrunner/scripts/burnin/recover-stranded.sh

env BR3_EVENTS_DB=~/.buildrunner/burnin/snapshots/events.db.20260425 \
    BR3_BURNIN_ROOT=~/.buildrunner/burnin \
    BR3_BURNIN_FIX_CLAUDE_CMD=/tmp/br3-burnin-phase7/repo/bin/fake-claude-needs-human.sh \
    BR3_BURNIN_WORKER_PROJECT_ROOT=/Users/byronhudson/Projects/BuildRunner3 \
    ~/.buildrunner/scripts/burnin/lib/worker.sh
```

Expected SQL state:

- Snapshot is v2 after migrate.
- `recover-stranded.sh` enqueues one `requested` recovery row per stranded case.
- Worker drains all of those `recovery` rows serially.
- No `claimed` recovery rows remain at the end.

Observed:

- `recover_requested=36`
- `open_after_drain=0`
- `resolved=36`
- `seriality=serial`
- first recover line: `Recovering 36 stranded case(s)`

The snapshot has `38` total `needs_human` rows; `36` are stranded reaper
victims and `2` are legitimate non-stranded controls (excluded by design):

- `walter-trigger-logs` — `fix_attempts=3`, `last_failure='fix budget exhausted after 3 attempts'`
- `fix-loop-exhaust` — `fix_attempts=4`, plugin YAML missing

The stranded-cohort signature, validated against the snapshot:

```sql
SELECT COUNT(*) FROM burnin_cases
WHERE state = 'needs_human'
  AND fix_attempts < 3
  AND (last_failure IS NULL OR last_failure NOT LIKE '%budget exhausted%');
-- Returns 36
```

This is the WHERE clause used by `recover-stranded.sh`. It rests on the
contract guarantee that `needs_human` is reserved for budget exhaustion or
explicit operator action — anything else in `needs_human` is, by definition,
a stranded reaper victim from the pre-Phase-5 stale-fixing path.

Reviewer-flagged correction: an earlier draft of `recover-stranded.sh` used
`last_failure LIKE '%reaped from stale fixing%' OR (fix_attempts=0 AND
EXISTS aborted+resolver='timeout')`, which only matched 20 of the 36
stranded cases. The 16 `below-*` cases have `fix_attempts=1` and a final
`aborted` row with `resolver=NULL` — neither branch caught them. The
fix_attempts/budget-text signature above matches all 36 against the live
snapshot.

## Scenario F — `burnin recover --all`

Command sequence:

```bash
# Fresh synthetic snapshot with two valid needs_human cases.
env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7-f-synth.db \
    ~/.buildrunner/scripts/burnin/burnin.sh register

sqlite3 /tmp/br3-burnin-phase7-f-synth.db \
  "UPDATE burnin_cases
      SET state='needs_human', last_result='fail', last_failure='synthetic recover-all target'
    WHERE id IN ('phase7-f1','phase7-f2');
   DELETE FROM fix_requests;"

env BR3_BURNIN_ROOT=/tmp/br3-burnin-phase7/burnin-root \
    BR3_EVENTS_DB=/tmp/br3-burnin-phase7-f-synth.db \
    ~/.buildrunner/scripts/burnin/burnin.sh recover --all
```

Expected SQL state:

- `recover --all` enqueues exactly one `requested` recovery row per
  `needs_human` case in the fresh snapshot.
- Worker drains those rows serially.
- No `claimed` rows remain at the end.

Observed:

- `recover_all_requested=2`
- `open_after_drain=0`
- `resolved=2`
- `seriality=serial`
- output:
  `Recovered: phase7-f1 ...`
  `Recovered: phase7-f2 ...`

## Invariants

Final invariant checks on the verification harness:

- `fixing_without_claim=0`
- `live_claimed_rows=0`
