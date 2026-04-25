# Prior-State Survey — burnin-queue-v2

## Prior BUILDs

- `BUILD_burnin-harness-reliability` (2026-04-24, all 6 phases COMPLETE) — touched the exact files this build re-modifies: `burnin/lib/{runner,fix-loop,state,db}.sh`, `burnin/burnin.sh`, `burnin/lib/watchd.sh`, `~/Library/LaunchAgents/com.buildrunner.burnin-watchd.plist`. That build added the reaper, fix-loop timeout, and watchd LaunchAgent — but left the contract bug (`fixing` = "needs fix" rather than "worker-owned"), the schema gaps (no claim_at/worker_id/heartbeat/uniqueness), and the in-process dispatcher in place. This build supersedes those decisions.
- `BUILD_burnin-harness` (2026-04-23) — created the harness skeleton; lower-level than this build.

## Shared-Surface Impact

- `~/.buildrunner/scripts/burnin/lib/db.sh` — also called by `canary.sh` and `reconcile.sh`. Adding worker_id/claim_at fields and the atomic transition+enqueue path must keep both readers' queries valid (canary writes its own runs; reconcile reads aggregates).
- `~/.buildrunner/burnin/schema.sql` — applied by harness startup; idempotent migration must use `ALTER TABLE` for new columns and `CREATE UNIQUE INDEX IF NOT EXISTS` for the open-request constraint, not destructive recreation.
- `~/.buildrunner/dashboard/events.db` — shared with the live dashboard (`com.buildrunner.dashboard.plist` reads burnin_cases/fix_requests). Schema additions must be backwards-readable; the dashboard must not blow up if it sees new columns or statuses.
- `~/Library/LaunchAgents/` — adding `com.buildrunner.burnin-fix-worker.plist` as a NEW agent. Must not collide with existing `com.buildrunner.burnin-watchd.plist` or `com.buildrunner.burnin-canary.plist` (they cooperate, they don't dispatch fixes themselves anymore).

## Governance Drift

- `.buildrunner/governance.yaml` — not present at project root; no rule conflicts.
- `~/.buildrunner/config/default-role-matrix.yaml` — terminal-build / backend-build buckets are appropriate for bash + sqlite + LaunchAgent work; no override needed.

## Completed-Phase Blast Radius

- `BUILD_burnin-harness-reliability` Phase 3 (state-machine escape + fix-loop timeout) and Phase 4 (dispatcher hygiene + watchd install) modified the same files this build re-modifies. Those phases are LOCKED per BR3 convention; this build must explicitly acknowledge it is correcting decisions made there. Plan must call out: (a) the `state_advance_after_run` path being deleted (Phase 3 left two divergent implementations), (b) the in-process `fix_loop_run` call in `_run_one` being removed (Phase 4 added the autoheal-off skip but did not move dispatch off the runner), (c) the `state_reap_stale_fixing` call in `cmd_status` being removed (Phase 4 wired it into status read).
- `BUILD_burnin-harness-reliability` Phase 5 produced an adversarial review record; this build's review will reference that prior verdict and explain why the contract change is now warranted.
