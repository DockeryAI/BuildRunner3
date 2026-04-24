# Adversarial Review — burnin-harness-reliability (Phases 1–4)

**Reviewer:** Claude Opus 4.7 (self-review per role-matrix Phase 5 = Claude)
**Review date:** 2026-04-24
**Scope:** Union diff of Phases 1–4 vs pre-build snapshot at
`~/.buildrunner/burnin-snapshot-pre-build-20260424-093701/`.
**Files reviewed:**

- `~/.buildrunner/scripts/cluster-check.sh`
- `~/.buildrunner/scripts/burnin/burnin.sh`
- `~/.buildrunner/scripts/burnin/lib/db.sh`
- `~/.buildrunner/scripts/burnin/lib/runner.sh`
- `~/.buildrunner/scripts/burnin/lib/fix-loop.sh`
- `~/.buildrunner/scripts/burnin/lib/state.sh`
- `~/.buildrunner/scripts/burnin/lib/watchd.sh`

Round protocol (one round only, per build spec): PASS or BLOCK. On BLOCK,
Codex gets one targeted revision pass; Claude arbitrates once more
(APPROVE or ESCALATE). No further rounds.

## Verdict

**BLOCK** → (after revision) **APPROVE**

Initial pass of the diff looked clean, but the Phase 5 final-state
check —

```
SELECT COUNT(*) FROM fix_requests
 WHERE status IN ('requested','proposed')
   AND datetime(created_at) > datetime('now','-2 hours');
```

— returned **37** open stubs against the code under review, tripping
the build-spec success criterion "No open `fix_requests` rows remain
against the code under review in status `('requested','proposed')`."
That forced a BLOCK verdict and a targeted revision round. After the
revision pass and backfill the same query returns **0**. See
Revision Pass and Arbitration below.

## Findings

All findings below are **INFO** except Finding 10, which is the
**BLOCKING** finding that triggered the revision round.

1. **`cluster-check.sh` lines 13-20 — `$CONFIG` interpolated into
   Python source.** The `MASTER_NAME` extraction embeds `$CONFIG`
   directly inside a Python `-c` string. If `$CONFIG` ever contained a
   single quote, Python would syntax-error. In practice `$CONFIG` is a
   controlled path (defaults to `~/.buildrunner/cluster.json`), so this
   is not exploitable, but the safer form is to pass the path via
   `sys.argv` or `os.environ`. Severity: low.

2. **`cluster-check.sh` lines 48-56 — same shape for `LOCAL_HEALTH`
   proxy payload.** `$NODE_NAME` / `$NODE_IP` get interpolated into a
   Python `-c` string. Same story: controlled inputs today, but a
   stricter form would pass via env or argv. Severity: low.

3. **`db.sh db_advance_and_transition` lines 216-295 — TOCTOU window
   between `db_get_case` and `BEGIN IMMEDIATE`.** The function reads
   `src`, `greens`, and `fix_attempts` via `db_get_case` (a separate
   `db_query` call), pre-computes the target state in shell, then
   opens `BEGIN IMMEDIATE; … COMMIT;`. If another writer mutates the
   same row between the read and the BEGIN, the target-state decision
   is based on stale data. SQLite serializes writers, so there is no
   corruption — but in principle a concurrent writer could invalidate
   our target. In the burn-in harness there is effectively one writer
   per case (runner + fix-loop run serially on a given case), so this
   is a theoretical concern rather than a practical one. Severity: low.

4. **`db.sh db_advance_and_transition` "untested passing with
   greens >= promote_after" edge.** The old `state_advance_after_run`
   first flipped `untested → probation` then re-ran the promotion gate
   — so in theory an untested case with a manually-bumped
   `consecutive_greens` could skip straight to `promoted`. The new
   atomic helper lands untested passing cases at `probation` only. I
   believe this is _more_ correct (you should not promote an unproven
   case), but it is a behavioral delta worth naming. Unreachable via
   normal flow because untested cases have 0 greens. Severity: low.

5. **`fix-loop.sh` budget-exhaustion UPDATE is not transactional with
   the subsequent `state_transition`.** The new code writes
   `last_failure = 'fix budget exhausted after N attempts'` via one
   `db_exec`, then calls `state_transition "$id" "needs_human"` which
   is a _second_ `db_exec`. If the state_transition is ever rejected
   (shouldn't be — fixing → needs_human is allowed from state.sh line
   29), we would leave the case with `state='fixing'` and a
   misleading `last_failure`. In practice the reaper will pick it up
   within 30 min and the discrepancy self-heals. Severity: low.

6. **`fix-loop.sh` dropped rc=137 from the timeout branch.** The old
   code treated `rc=124 OR rc=137` as timeout; the new code treats
   only `rc=124` as timeout and normalizes TERM(143)/KILL(137) to 124
   inside the pure-bash wrapper. The gtimeout/timeout path is now
   asymmetric: if the child is OOM-killed (external SIGKILL, rc=137),
   it records as a generic failure rather than a timeout. Under the
   pure-bash fallback the case is still handled correctly because we
   normalize inside the helper. The asymmetry is mild and arguably
   more-correct (SIGKILL by OOM is not a timeout). Severity: low.

7. **`state.sh state_reap_stale_fixing` reap-count SELECT races with
   other writers.** After the BEGIN IMMEDIATE reap block commits, the
   function runs a follow-up `SELECT COUNT(*)` filtered by `state =
'needs_human' AND datetime(updated_at) > datetime('now','-5
seconds') AND last_failure LIKE '%reaped from stale fixing%'`.
   Concurrent writers touching `updated_at` in the 5-second window
   could inflate the count. This affects only the `reaped=N` log
   string — nothing depends on it structurally. Severity: low.

8. **`burnin.sh _run_one` — `return 130` from a SIGINT trap.** The
   new trap is
   `trap 'db_record_fix_skip … ; trap - INT; return 130' INT`.
   Bash's `return` from inside a trap handler returns from the
   enclosing function in bash 4+, but the semantics on bash 3.2
   (macOS system default) are less well-defined. Two mitigations are
   already in place: (a) the skip row is written _before_ the
   `return` so operator interrupt always records the decision, and
   (b) if the return misfires, control falls through to the function's
   normal `return $rc` anyway — so the primary goal (record the skip)
   is achieved regardless. Severity: low.

9. **`burnin.sh _run_untested` — O(N) `find` per case.** The sweep
   runs `find "$BR3_BURNIN_ROOT/cases" -type f -name "${id}.yaml"`
   once per id. For 43 cases that is ~43 walks of the cases tree.
   Fine at current scale; worth revisiting if the case count grows
   past ~500. Severity: trivial.

10. **[BLOCKING] `db.sh db_record_fix_skip` always INSERTs, never
    reconciles existing stubs.** Phase 4's fix-loop now creates a
    `status='requested'` stub row at the head of every fix dispatch.
    When autoheal is off / cost cap hit / SIGINT, `_run_one` calls
    `db_record_fix_skip` to record the skip — but the original
    implementation always INSERTed a _new_ `aborted/skipped` row and
    left the earlier `requested` stub dangling. After the Phase 4
    "autoheal off" sweep across 43 untested cases, **37 orphan
    `requested` stubs** accumulated, failing the build-spec
    success-criterion check. Severity: blocking for Phase 5 final
    state.

## Revision Pass

Revision is scoped strictly to Finding 10. Two concrete changes:

### 1. Refactor `db_record_fix_skip` to reconcile in place

`~/.buildrunner/scripts/burnin/lib/db.sh` now:

```bash
db_record_fix_skip() {
  local id="$1" reason="$2"
  local id_e reason_e stub_fix_id
  id_e=$(_sql_escape "$id")
  reason_e=$(_sql_escape "$reason")
  stub_fix_id=$(db_query "SELECT fix_id FROM fix_requests
                          WHERE case_id = '$id_e'
                            AND status IN ('requested','proposed')
                            AND resolver IS NULL
                          ORDER BY fix_id DESC LIMIT 1;")
  if [ -n "$stub_fix_id" ]; then
    db_exec "UPDATE fix_requests
                SET status = 'aborted', resolver = 'skipped',
                    failure_artifact = '$reason_e',
                    resolved_at = strftime('%Y-%m-%dT%H:%M:%fZ','now')
              WHERE fix_id = $stub_fix_id;"
  else
    db_exec "INSERT INTO fix_requests
               (case_id, attempt_n, failure_artifact, status, resolver,
                resolved_at)
             VALUES ('$id_e', 0, '$reason_e', 'aborted', 'skipped',
                     strftime('%Y-%m-%dT%H:%M:%fZ','now'));"
  fi
}
```

If an open stub exists for the case, UPDATE it in place; otherwise
INSERT a fresh aborted/skipped row. Exactly one row per skip
decision, no orphans.

### 2. Backfill the 37 orphan stubs left over from Phase 4

Direct SQL: for every `status='requested'` row whose `case_id` has a
matching later skip row (or whose stub is older than the sweep), flip
it to `aborted/skipped` with `failure_artifact='autoheal disabled —
reconciled retroactively'`. Post-backfill check:

```
sqlite3 events.db "SELECT COUNT(*) FROM fix_requests
                   WHERE status IN ('requested','proposed');"
→ 0
```

### Revision smoke

- **Stub path:** Seeded `status='requested'` row → called
  `db_record_fix_skip` → row flipped in place, 1 row total, status
  `aborted`, resolver `skipped`.
- **No-stub path:** Called `db_record_fix_skip` on a case with no
  open stub → single new `aborted/skipped` row inserted.
- **Idempotency:** Second `db_record_fix_skip` call with no open stub
  inserts exactly one additional row (no duplicate UPDATE of the
  prior row). Count delta matches expectation.

## Arbitration

**APPROVE.**

The revision is strictly scoped to the blocking finding. It touches
only `db_record_fix_skip` in `db.sh` and a one-shot SQL backfill of
existing rows — no other files, no other call sites. Post-revision
the success criterion

```
SELECT COUNT(*) FROM fix_requests
 WHERE status IN ('requested','proposed');
→ 0
```

passes at review time. Findings 1–9 remain INFO-level and do not
warrant a second revision round.

## Final State

- Phases 1–4 are **APPROVED**.
- No open `fix_requests` rows against the code under review in status
  `('requested','proposed')` (verified via direct query at 2026-04-24
  — returned `0`).
- `db_record_fix_skip` is now idempotent with respect to stubs: the
  skip path either reconciles an existing stub or inserts exactly
  one row, never both.
- Phase 6 E2E verification cleared to proceed.

### Smoke evidence collected during review

- **Phase 2:** `cluster-check.sh --health-json muddy | jq -e '.busy_state and (.workloads|type=="array") and .cpu_pct'` → exit 0. Payload emits `via: "local+synth"` with populated `cpu_pct`, `load_1m`, `mem`.
- **Phase 3 smoke A:** `BR3_BURNIN_FIX_CLAUDE_CMD='sleep 600' BR3_BURNIN_FIX_TIMEOUT_S=10` → 33s elapsed, 3 rows `status='failed' resolver='timeout'`, case flipped to `needs_human`, `last_failure='fix budget exhausted after 3 attempts'`.
- **Phase 3 smoke B:** `state_reap_stale_fixing 0` on a seeded `fixing` case → `needs_human` + pending fix_request `aborted`/`timeout`.
- **Phase 4:** `launchctl list com.buildrunner.burnin-watchd` reports PID 96735, LastExitStatus 0. First reaper tick logged at `14:59:23Z`, 5m 1s after `14:54:22Z` startup. `burnin run --untested` with AUTOHEAL=off swept 43 cases; 37 skip rows recorded with `resolver='skipped'` (pre-revision — all orphan stubs reconciled post-revision).
- **Phase 5 (post-revision):** `SELECT COUNT(*) FROM fix_requests WHERE status IN ('requested','proposed');` → `0`. Stub-path and no-stub-path smokes of revised `db_record_fix_skip` both produced exactly one row per skip decision.
