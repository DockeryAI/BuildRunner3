# Plan: Burn-in Harness Reliability Pass

**Slug:** burnin-harness-reliability
**Parent build completed:** BUILD_burnin-harness.md (all 12 phases, 2026-04-23)
**Trigger:** `sharding-cluster-check-passthrough` stuck in `fixing` for 18+ hours. Dashboard shows three sharding cases (`sharding-br-test-fanout`, `sharding-cluster-check-passthrough`, `sharding-dashboard-chip`) as broken or never-run.

## Root-cause summary

1. **Legitimate test failure:** `~/.buildrunner/scripts/cluster-check.sh --health-json muddy` returned `{"node":"muddy","ip":"10.0.1.100","online":false}` — no `busy_state`, `workloads`, or `cpu_pct`. Two bugs in that script:
   - `IS_LOCAL` detection relies on `ipconfig getifaddr en0`, which returns empty if the primary interface isn't wifi, so the local fast-path is skipped and the fallthrough `online:false` path is taken.
   - Even when the local fast-path fires, it returns a stripped `{online, status, via, role}` JSON that drops the contract fields. The plugin (Phase 2 passthrough guard) is designed to catch exactly this.

2. **State-machine trap:** `runner.sh` transitions the case to `fixing` and writes a `fix_requests` row with `status='requested'`. `_run_one` in `burnin.sh` is supposed to dispatch `fix_loop_run` when autoheal is on — but nothing processes pending `status='requested'` rows if that in-process dispatch is skipped or interrupted. Evidence: only one `fix_requests` row exists for the stuck case, none of the attempt-level rows `fix_loop_run` would have written.

3. **Ancillary issues** surfaced during investigation:
   - `runner.sh`'s "requested" stub increments `fix_attempts`, silently shrinking the 3-attempt budget to 2.
   - `fix-loop.sh` has no timeout on `claude -p`; a hung subprocess blocks the whole harness.
   - `watchd` LaunchAgent is not installed (`launchctl list` returns nothing; `watchd.log` empty) — the event-driven auto-heal is dark.
   - 11 of 17 sharding cases are still `untested` — no "first-run sweep" exists for newly-added cases.
   - Empty `~/.buildrunner/burnin/state.db` (0 bytes) — a schema-split leftover. Real store is `dashboard/events.db`.
   - `db_advance_case` and `state_advance_after_run` are two separate transactions.

## Scope

Fix only the burn-in harness and the `cluster-check.sh --health-json` passthrough contract. No dashboard UI changes, no canary changes, no rewrite of the harness architecture.

## Builder posture

**Codex is the sole builder/fixer for Phases 1–4 and Phase 6.** **Claude runs exactly one review round + final arbitration in Phase 5.** If Claude blocks, Codex gets one targeted revision pass and Claude arbitrates once more. No further review rounds.

## Phases

### Phase 1: Unstick the stuck case + remove orphan state file

**Files:**

- `~/.buildrunner/dashboard/events.db` (MODIFY — one SQL)
- `~/.buildrunner/burnin/state.db` (DELETE)
- `~/.buildrunner/burnin/README.md` (NEW)

**Deliverables:**

- `UPDATE fix_requests SET status='aborted', resolver='human', resolved_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE fix_id=13` in `events.db`.
- `~/.buildrunner/scripts/burnin/burnin.sh reset sharding-cluster-check-passthrough`.
- `rm ~/.buildrunner/burnin/state.db` (confirmed 0 bytes).
- One-line README at `~/.buildrunner/burnin/README.md`: "Canonical DB: `~/.buildrunner/dashboard/events.db`. Do not create `state.db` here."

**Success:** `SELECT state, fix_attempts FROM burnin_cases WHERE id='sharding-cluster-check-passthrough'` returns `untested|0`; no `fix_requests` row with `status='requested'` older than 1 hour.
**Blocked by:** None.

### Phase 2: `cluster-check.sh --health-json muddy` honors the passthrough contract

**Files:**

- `~/.buildrunner/scripts/cluster-check.sh` (MODIFY)

**Deliverables:**

- Replace `ipconfig getifaddr en0` LOCAL_IP detection with a cluster-identity check: compare lowercased `$NODE_NAME` to `cluster.json master.name` (lowercased). IP comparison is a secondary fallback.
- Local-muddy path: first try `curl --max-time 3 http://127.0.0.1:8100/health`. If that returns `"status":"healthy"`, proxy it verbatim (with `node`/`ip`/`online`/`via="local+http"` added).
- Fallback: synthesize a schema-compatible JSON locally from `uptime` (load_1m), `sysctl -n hw.ncpu` + `top -l 1 -n 0` (cpu_pct), `vm_stat` (mem), plus `busy_state` derived from load thresholds and an empty `workloads: []` array. Output must include `busy_state`, `workloads`, `cpu_pct`, `load_1m`, `mem`.
- The existing `online:false` fallthrough path stays as the last resort for truly offline nodes only.

**Success:**

- `~/.buildrunner/scripts/cluster-check.sh --health-json muddy | jq -e '.busy_state and (.workloads|type=="array") and .cpu_pct'` exits 0.
- Re-running `sharding-cluster-check-passthrough` and `sharding-dashboard-chip` after Phase 2 yields PASS on all assertions.

**Blocked by:** None.

### Phase 3: State-machine escape + fix-loop timeout

**Files:**

- `~/.buildrunner/scripts/burnin/lib/runner.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/fix-loop.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/state.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY)

**Deliverables:**

- `db.sh`: add `db_record_fix_request_stub <case_id> <artifact>` — INSERT only, does not bump `fix_attempts`. `runner.sh` switches from `db_record_fix_request "…" "requested"` to the stub. Existing `db_record_fix_request` keeps the attempt-counter increment for real attempts.
- `fix-loop.sh`: wrap `$CLAUDE_CMD < "$prompt_file"` in `timeout "${BR3_BURNIN_FIX_TIMEOUT_S:-300}"`. On timeout, record `status='failed'`, `resolver='timeout'`, continue to next attempt.
- `state.sh`: new `reap_stale_fixing [max_age_minutes]` (default 30). Flips `fixing` → `needs_human` for cases whose `updated_at` is older than threshold AND no `fix_requests` row with `status IN ('requested','proposed')` and `created_at` newer than threshold. Stamps those pending fix_requests `status='aborted', resolver='timeout', resolved_at=now`.
- `fix-loop.sh`: on budget exhaustion, also `UPDATE burnin_cases SET last_failure='fix budget exhausted after N attempts' WHERE id=…`.
- `db.sh`: wrap `db_advance_case` + `state_advance_after_run` in a single `BEGIN IMMEDIATE; … COMMIT;`. Introduce `db_advance_and_transition <case_id> <passed> <summary>` helper; `runner.sh` uses it.

**Success:**

- Unit smoke: seeded failing case + `BR3_BURNIN_FIX_CLAUDE_CMD='sleep 600'` → `fix-loop` exits within `300s + 10s` with one `status='failed', resolver='timeout'` row per attempt.
- Unit smoke: `reap_stale_fixing 0` on a case with `state='fixing'` immediately transitions it to `needs_human`.
- `fix_attempts=0` immediately after a failing run (before the fix loop starts).

**Blocked by:** None.

### Phase 4: Dispatcher hygiene, watchd install, untested sweep

**Files:**

- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/watchd.sh` (MODIFY)
- `~/Library/LaunchAgents/com.buildrunner.burnin-watchd.plist` (NEW — via `watchd-install`)

**Deliverables:**

- `burnin.sh`: new `burnin run --untested` handler — iterates every `burnin_cases WHERE state='untested' AND tombstoned_at IS NULL` row and runs it once in warm condition. Honors existing autoheal settings.
- `burnin.sh`: when the autoheal branch in `_run_one` decides not to dispatch (cost cap / `BR3_BURNIN_AUTOHEAL=off`), write a `fix_requests` row with `status='aborted', resolver='skipped'` and a one-line reason in `failure_artifact`.
- `burnin.sh`: top of `cmd_status` and `cmd_run` calls `state_reap_stale_fixing 30` (wrapped in `2>/dev/null || true` so a sqlite blip never blocks status).
- `watchd.sh`: add a periodic tick in `watchd_start` (every 300s) that calls `state_reap_stale_fixing 30` alongside the fswatch event loop. Implement via a background sidecar subshell; do not move away from fswatch.
- Run `~/.buildrunner/scripts/burnin/burnin.sh watchd-install`. Verify `launchctl list com.buildrunner.burnin-watchd` prints the label.

**Success:**

- `launchctl list com.buildrunner.burnin-watchd` prints the label with a non-negative PID.
- `burnin run --untested` moves all 11 currently-untested sharding cases out of `untested` (they become `probation` or `fixing`/`needs_human` depending on run result).
- `watchd.log` shows a reaper tick within 5 minutes of startup.

**Blocked by:** Phase 3 (consumes `reap_stale_fixing`).
**After:** 1, 2.

### Phase 5: Claude review + final arbitration (ONE round)

**Files:**

- `.buildrunner/adversarial-reviews/burnin-harness-fix-review.md` (NEW)

**Deliverables:**

- Collect the union diff of Phases 1–4 vs pre-change SHA (`git diff` on the repo + local snapshots of `~/.buildrunner` changes captured during Phases 1–4).
- Claude issues a single verdict — **PASS** or **BLOCK** — with file:line findings and a short rationale each.
- On BLOCK: Codex applies exactly one targeted revision scoped to the findings (no new scope). Claude then arbitrates: **APPROVE** or **ESCALATE**. No further rounds.
- Final artifact at `.buildrunner/adversarial-reviews/burnin-harness-fix-review.md` with sections: `## Verdict`, `## Findings`, `## Revision Pass (if any)`, `## Arbitration`.

**Success:** Artifact exists with a final verdict of `APPROVED` or `ESCALATED`. No pending `fix_requests` rows remain against the code under review.
**Blocked by:** 1, 2, 3, 4.

### Phase 6: End-to-end verification

**Files:** none (writes logs to `~/.buildrunner/burnin/logs/` and a summary at `.buildrunner/verify/burnin-harness-reliability.md`).

**Deliverables:**

- `burnin run sharding-cluster-check-passthrough` → PASS.
- `burnin run sharding-dashboard-chip` → PASS.
- `burnin run --untested` → all 11 untested sharding cases get a first run. Record pass/fail counts in the verify report.
- Hang-simulation smoke: seeded failing case + `BR3_BURNIN_FIX_CLAUDE_CMD='sleep 600' BR3_BURNIN_FIX_TIMEOUT_S=10 burnin fix <case>` → exits within ~15s with the case in `needs_human` and three `fix_requests` rows with `resolver='timeout'`.
- `burnin status` shows zero cases in `fixing` older than 30 minutes.

**Success:** All five checks green, verify report written.
**Blocked by:** 5.

## Out of scope

- Promoting the three sharding cases (natural canary progression).
- Rewriting autoheal as a queued DB-poller.
- Enabling `cold`/`loaded` conditions for sharding plugins.
- Dashboard UI changes.
- Rebuilding `state.db` as a separate store.

## Parallelization matrix

| Phase | Files                                                                                          | Parallel with | Blocked by |
| ----- | ---------------------------------------------------------------------------------------------- | ------------- | ---------- |
| 1     | `events.db`, `state.db` (delete), `burnin/README.md`                                           | 2, 3          | —          |
| 2     | `cluster-check.sh`                                                                             | 1, 3          | —          |
| 3     | `burnin/lib/{runner,fix-loop,state,db}.sh`                                                     | 1, 2          | —          |
| 4     | `burnin/burnin.sh`, `burnin/lib/watchd.sh`, `LaunchAgents/com.buildrunner.burnin-watchd.plist` | —             | 3          |
| 5     | review artifact                                                                                | —             | 1, 2, 3, 4 |
| 6     | logs + verify report                                                                           | —             | 5          |

## Role matrix

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: terminal-build, assigned_node: muddy, builder: codex }
      phase_2: { bucket: terminal-build, assigned_node: muddy, builder: codex }
      phase_3: { bucket: backend-build, assigned_node: muddy, builder: codex }
      phase_4: { bucket: terminal-build, assigned_node: muddy, builder: codex }
      phase_5: { bucket: review, assigned_node: muddy, builder: claude }
      phase_6: { bucket: qa, assigned_node: muddy, builder: codex }
```

## Prior-State Survey

**File:** `.buildrunner/plans/survey-burnin-harness-reliability.md`

Survey summary: the parent `BUILD_burnin-harness.md` is complete, so its phases are locked. This reliability pass only modifies files already owned by that build (same script paths under `~/.buildrunner/scripts/burnin/`) — collisions are expected and intentional. No overlap with any other in-progress BUILD spec.
