# Build: burnin-harness-reliability

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

**Created:** 2026-04-24
**Status:** Phases 1-5 Complete — Phase 6 In Progress
**Deploy:** operator-tooling — no user-facing deploy; changes live under `~/.buildrunner/scripts/` and `~/Library/LaunchAgents/`.
**Source Plan File:** .buildrunner/plans/plan-burnin-harness-reliability.md
**Source Plan SHA:** 8a21d0305b34701f0657e578e3b64405ede6ab9026e84b03ceb5d76ef6df1d50
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-24T14:24:17Z
**Prior-State Survey:** .buildrunner/plans/survey-burnin-harness-reliability.md
**Owner:** byronhudson
**Builder posture:** Codex for Phases 1–4 and 6. Claude runs exactly one review round plus final arbitration in Phase 5. On BLOCK, Codex gets one targeted revision pass; Claude arbitrates once more; no further review rounds.

## Overview

Fix the burn-in harness so it is actually autonomous. The `sharding-cluster-check-passthrough` case has been stuck in `fixing` for 18+ hours because (a) `cluster-check.sh --health-json muddy` violates the Phase 2 passthrough contract the case was guarding, and (b) the harness has no recovery path once a case lands in `fixing` if the in-process autoheal doesn't dispatch. This build repairs `cluster-check.sh`, adds a stale-`fixing` reaper + fix-loop timeout + transactional state updates, installs the watchd LaunchAgent, and adds a first-run sweep for `untested` cases. Codex does all the edits; Claude runs one review round with final arbitration.

## Parallelization Matrix

| Phase | Key Files                                                                                                                                                    | Can Parallel With | Blocked By |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------- | ---------- |
| 1     | `~/.buildrunner/dashboard/events.db`, `~/.buildrunner/burnin/state.db` (delete), `~/.buildrunner/burnin/README.md` (NEW)                                     | 2, 3              | —          |
| 2     | `~/.buildrunner/scripts/cluster-check.sh`                                                                                                                    | 1, 3              | —          |
| 3     | `~/.buildrunner/scripts/burnin/lib/{runner,fix-loop,state,db}.sh`                                                                                            | 1, 2              | —          |
| 4     | `~/.buildrunner/scripts/burnin/burnin.sh`, `~/.buildrunner/scripts/burnin/lib/watchd.sh`, `~/Library/LaunchAgents/com.buildrunner.burnin-watchd.plist` (NEW) | —                 | 3          |
| 5     | `.buildrunner/adversarial-reviews/burnin-harness-fix-review.md` (NEW)                                                                                        | —                 | 1, 2, 3, 4 |
| 6     | `~/.buildrunner/burnin/logs/` (writes), `.buildrunner/verify/burnin-harness-reliability.md` (NEW)                                                            | —                 | 5          |

## Phases

### Phase 1: Unstick the stuck case + remove orphan state file

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/events.db` (MODIFY — one SQL)
- `~/.buildrunner/burnin/state.db` (DELETE)
- `~/.buildrunner/burnin/README.md` (NEW)

**Blocked by:** None
**Deliverables:**

- [x] `UPDATE fix_requests SET status='aborted', resolver='human', resolved_at=strftime('%Y-%m-%dT%H:%M:%fZ','now') WHERE fix_id=13` in `events.db`.
- [x] `~/.buildrunner/scripts/burnin/burnin.sh reset sharding-cluster-check-passthrough` executed.
- [x] `rm ~/.buildrunner/burnin/state.db` (confirmed 0 bytes before removal).
- [x] One-line README at `~/.buildrunner/burnin/README.md`: "Canonical DB: `~/.buildrunner/dashboard/events.db`. Do not create `state.db` here."

**Success Criteria:**

- `SELECT state, fix_attempts FROM burnin_cases WHERE id='sharding-cluster-check-passthrough'` returns `untested|0`.
- `SELECT COUNT(*) FROM fix_requests WHERE status='requested' AND datetime(created_at) < datetime('now','-1 hour')` returns 0.

### Phase 2: `cluster-check.sh --health-json muddy` honors the passthrough contract

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/cluster-check.sh` (MODIFY)

**Blocked by:** None
**Deliverables:**

- [x] Replace `ipconfig getifaddr en0` LOCAL_IP detection with an authoritative cluster-identity check: lowercased `$NODE_NAME` compared to lowercased `cluster.json master.name`. IP equality is a secondary fallback, not the primary signal.
- [x] Local-muddy path: first attempt `curl --max-time 3 http://127.0.0.1:8100/health`. If it returns `"status":"healthy"`, proxy the payload verbatim with `node`, `ip`, `online: true`, `via: "local+http"` added.
- [x] Synthesis fallback when local `/health` is unavailable: construct a schema-compatible JSON locally from `uptime` (load_1m), `sysctl -n hw.ncpu` + `top -l 1 -n 0` (cpu_pct), `vm_stat` (mem), plus `busy_state` derived from load thresholds and an empty `workloads: []` array. Output MUST include the keys `busy_state`, `workloads`, `cpu_pct`, `load_1m`, `mem`.
- [x] Keep the existing `online:false` fallthrough path as the last resort for truly offline nodes.
- [x] Inline smoke in the final change: `~/.buildrunner/scripts/cluster-check.sh --health-json muddy | jq -e '.busy_state and (.workloads|type=="array") and .cpu_pct'` must exit 0.

**Success Criteria:**

- The smoke command above exits 0.
- Manual re-run of `sharding-cluster-check-passthrough` and `sharding-dashboard-chip` after Phase 2 yields PASS on all assertions.

### Phase 3: State-machine escape + fix-loop timeout

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/lib/runner.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/fix-loop.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/state.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY)

**Blocked by:** None
**After:** 1 (so the smoke tests in this phase don't trip over the stuck case)
**Deliverables:**

- [x] `db.sh`: new `db_record_fix_request_stub <case_id> <artifact>` that INSERTs a `status='requested'` row without bumping `fix_attempts`. `runner.sh` switches from `db_record_fix_request "…" "requested"` to the stub. Existing `db_record_fix_request` retains the attempt-counter bump for real attempts.
- [x] `fix-loop.sh`: wrap `$CLAUDE_CMD < "$prompt_file"` in `timeout "${BR3_BURNIN_FIX_TIMEOUT_S:-300}"`. On timeout exit status, record `status='failed'`, `resolver='timeout'`, continue to the next attempt. (Implemented via `_fix_loop_timed_exec` helper that prefers `gtimeout`/`timeout` when present and falls back to a pure-bash watcher — stock macOS ships neither binary.)
- [x] `state.sh`: new `state_reap_stale_fixing [max_age_minutes]` (default 30). Flips `fixing` → `needs_human` for cases whose `updated_at` is older than threshold AND have no active `fix_requests` row (`status IN ('requested','proposed')` with `created_at` newer than threshold). Stamps those pending rows `status='aborted', resolver='timeout', resolved_at=now`.
- [x] `fix-loop.sh`: on budget exhaustion, also `UPDATE burnin_cases SET last_failure='fix budget exhausted after N attempts' WHERE id=…` so `/burnin status` shows the reason.
- [x] `db.sh`: wrap `db_advance_case` + `state_advance_after_run` in a single `BEGIN IMMEDIATE; … COMMIT;`. Introduce `db_advance_and_transition <case_id> <passed> <summary>`; `runner.sh` switches to the new helper.

**Success Criteria:**

- Unit smoke A: seeded failing case + `BR3_BURNIN_FIX_CLAUDE_CMD='sleep 600'` + `BR3_BURNIN_FIX_TIMEOUT_S=10` → fix-loop exits within ~15s with `status='failed', resolver='timeout'` rows for each attempt.
- Unit smoke B: `state_reap_stale_fixing 0` on a seeded `fixing` case immediately transitions it to `needs_human` and aborts its pending fix_request.
- `SELECT fix_attempts FROM burnin_cases WHERE id=<fresh fail>` returns 0 before the fix loop starts.

### Phase 4: Dispatcher hygiene, watchd install, untested sweep

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/watchd.sh` (MODIFY)
- `~/.buildrunner/scripts/burnin/lib/db.sh` (MODIFY — new `db_record_fix_skip` helper)
- `~/Library/LaunchAgents/com.buildrunner.burnin-watchd.plist` (NEW — installed via `watchd-install`)

**Blocked by:** 3 (consumes `state_reap_stale_fixing`)
**After:** 1, 2
**Deliverables:**

- [x] `burnin.sh`: new `burnin run --untested` handler — iterates every `burnin_cases WHERE state='untested' AND tombstoned_at IS NULL` row and runs it once in warm condition. Honors existing autoheal settings. Iteration uses an array loaded up-front (not a herestring while-read) to survive stdin consumption by `fswatch`/`yq`/`runner.sh` children that previously truncated sweeps mid-run.
- [x] `burnin.sh`: when the autoheal branch in `_run_one` decides not to dispatch (daily cost cap / `BR3_BURNIN_AUTOHEAL=off` / operator interrupt), write a `fix_requests` row with `status='aborted', resolver='skipped'` and a one-line reason in `failure_artifact` so the decision is visible in the DB. (Implemented via new `db_record_fix_skip` helper. Operator-interrupt path installs a transient `SIGINT` trap so Ctrl-C during a fix-loop dispatch also records a skip row.)
- [x] `burnin.sh`: top of `cmd_status` and `cmd_run` calls `state_reap_stale_fixing 30` (wrapped `2>/dev/null || true` so a sqlite blip never blocks status output).
- [x] `watchd.sh`: add a 5-minute reaper tick in `watchd_start` that calls `state_reap_stale_fixing 30` alongside the fswatch loop (background sidecar subshell; fswatch stays primary). Tick interval is `BR3_BURNIN_REAPER_TICK_S` (default 300); threshold is `BR3_BURNIN_REAPER_THRESHOLD_MIN` (default 30).
- [x] Run `~/.buildrunner/scripts/burnin/burnin.sh watchd-install`. Verify `launchctl list com.buildrunner.burnin-watchd` prints the label.

**Success Criteria:**

- `launchctl list com.buildrunner.burnin-watchd` prints the label with a non-negative PID.
- `burnin run --untested` moves all 11 currently-untested sharding cases out of `untested` state (they land in `probation`, `fixing`, or `needs_human` depending on run result).
- `watchd.log` shows the startup line and at least one reaper tick within 5 minutes of LaunchAgent load.

### Phase 5: Claude review + final arbitration (ONE round)

**Status:** ✅ COMPLETE
**Files:**

- `.buildrunner/adversarial-reviews/burnin-harness-fix-review.md` (NEW)

**Blocked by:** 1, 2, 3, 4
**Deliverables:**

- [x] Collect the union diff of Phases 1–4 vs the pre-change SHA. `~/.buildrunner` lives outside the git repo — snapshot the touched files before Phase 1 and diff against the post-Phase-4 state.
- [x] Claude issues a single verdict — **PASS** or **BLOCK** — with file:line findings and one-line rationale each. No second review round under any circumstance.
- [x] On BLOCK: Codex applies exactly one targeted revision pass scoped strictly to Claude's findings (no new scope). Claude then arbitrates once: **APPROVE** or **ESCALATE** to human. No further rounds.
- [x] Write the artifact at `.buildrunner/adversarial-reviews/burnin-harness-fix-review.md` with sections: `## Verdict`, `## Findings`, `## Revision Pass (if any)`, `## Arbitration`, `## Final State`.

**Success Criteria:**

- Artifact exists with a final verdict of `APPROVED` or `ESCALATED`.
- No `fix_requests` rows remain against the code under review with `status IN ('requested','proposed')`.

### Phase 6: End-to-end verification

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/burnin/logs/` (writes only)
- `.buildrunner/verify/burnin-harness-reliability.md` (NEW — summary report)

**Blocked by:** 5
**Deliverables:**

- [x] `~/.buildrunner/scripts/burnin/burnin.sh run sharding-cluster-check-passthrough` → PASS on all assertions.
- [x] `~/.buildrunner/scripts/burnin/burnin.sh run sharding-dashboard-chip` → PASS.
- [x] `~/.buildrunner/scripts/burnin/burnin.sh run --untested` → all 11 untested sharding cases get a first run. Record pass/fail counts in the verify report.
- [x] Hang-simulation smoke: seed a failing case and run `BR3_BURNIN_FIX_CLAUDE_CMD='sleep 600' BR3_BURNIN_FIX_TIMEOUT_S=10 ~/.buildrunner/scripts/burnin/burnin.sh fix <case>` → exits within ~15s with the case in `needs_human` and three `fix_requests` rows whose `resolver='timeout'`.
- [x] `~/.buildrunner/scripts/burnin/burnin.sh status` shows zero cases in `fixing` older than 30 minutes.

**Success Criteria:**

- All five checks green.
- `.buildrunner/verify/burnin-harness-reliability.md` written with pass/fail table and any residual `needs_human` cases surfaced for operator follow-up.

## Out of Scope

- Promoting the three sharding cases to `promoted` (natural canary progression, not this build).
- Rewriting autoheal as a queued DB-poller (bigger redesign).
- Enabling `cold`/`loaded` condition staging for sharding plugins.
- Dashboard UI changes.
- Rebuilding `state.db` as a separate store.

## Session Log

(Will be updated by `/begin` / `/autopilot`)
