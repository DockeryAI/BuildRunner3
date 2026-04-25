# Prior-State Survey — burnin-harness-reliability

## Prior BUILDs

- `BUILD_burnin-harness.md` — **complete** (all 12 phases, 2026-04-23). Owns every file this reliability pass modifies under `~/.buildrunner/scripts/burnin/**` and `~/.buildrunner/scripts/cluster-check.sh` (Phase 2 of parent build). Completed phases are normally locked; surfacing the collision here explicitly — this reliability pass is a **follow-up bug-fix build** against the same files, not a re-implementation, and must not reverse contracts the parent build established.

## Shared-Surface Impact

- `~/.buildrunner/scripts/cluster-check.sh` — called by:
  - `sharding-cluster-check-passthrough.yaml` (plugin under test, Phase 2 contract guard)
  - `sharding-dashboard-chip.yaml` (reads `busy_state`)
  - Operator shell prompts, `cluster-check.sh semantic-search` in `/spec` and `/impact`
  - Dashboard jobs-aggregator poller
  - Any code that does `NODE_URL=$(cluster-check.sh <role>)` — the plain URL-return mode is untouched by this build.
- `~/.buildrunner/scripts/burnin/burnin.sh`, `lib/*.sh` — called only by `/burnin` skill, the parent build's canary + reconcile, and the LaunchAgent (being installed here).
- `~/.buildrunner/dashboard/events.db` — shared by dashboard live views. SQL in Phase 1 is a single-row UPDATE; no schema change.

## Governance Drift

- `.buildrunner/governance.yaml` (not present at repo root) — no project-level constraints.
- `~/.buildrunner/config/default-role-matrix.yaml` — buckets used (`terminal-build`, `backend-build`, `review`, `qa`) are all standard. No drift.

## Completed-Phase Blast Radius

- Parent `BUILD_burnin-harness.md` completed phases touching the same files:
  - Phase 2 (cluster-check passthrough): this reliability build re-modifies `cluster-check.sh`. Intentional — fixing a real-world violation of the contract that phase established. Phase-2 assertions stay identical; we are strengthening the implementation, not changing the contract.
  - Phase 3 (fix-loop): this reliability build adds a timeout to `fix_loop_run`. Wraps existing code, does not remove attempts/budget semantics.
  - Phase 7 (watchd): this reliability build installs the LaunchAgent that was authored there. No code change to `watchd.sh` beyond adding the 5-minute reaper tick.
  - Phase 11 (state/db): this reliability build wraps `db_advance_case` + `state_advance_after_run` in a transaction and adds `reap_stale_fixing`. Additive; no removal.

None of the modifications break the parent build's success criteria when re-run.
