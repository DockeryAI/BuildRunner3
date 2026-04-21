# Plan: cluster-activation

**Created:** 2026-04-21
**Purpose:** Close the 10 post-cutover orchestration gaps in BUILD_cluster-max. Wire `/begin` and `/autopilot` into the infrastructure cluster-max shipped (RuntimeRegistry, codex-bridge, feature flags, dashboard).
**Scope:** 6 phases. Framework internals only — no user-facing deploy.

---

## Gap Inventory (from 2026-04-21 post-cutover audit)

1. Role Matrix is prose-only in cluster-max — unparseable by orchestration code.
2. `/context/codex` APIRouter exists but is not mounted on Jimmy `:4500`.
3. Dual dispatch paths: bash `below-route.sh` curls Ollama directly; Python `RuntimeRegistry` is isolated.
4. Dead adversarial/cache flags: `BR3_ADVERSARIAL_3WAY` and `BR3_CACHE_BREAKPOINTS` not read anywhere.
5. `cluster-daemon.mjs` idle — never dispatches.
6. `node-matrix.mjs` orphaned — `/autopilot` hardcodes node names.
7. Walter sentinel LaunchDaemon plist missing from deploy.
8. Lomax overflow trigger missing — build-status ambiguity in `/begin`.
9. Zero dispatch telemetry — no `runtime_dispatched` / `cache_hit` / `context_bundle_served` / `adversarial_review_ran` events.
10. Stale `runtime-shadow-metrics.md` artifact references deleted `shadow_runner.py`.

---

## Phase Titles (binding — must match BUILD spec)

### Phase 1: Foundation — Role Matrix schema + context router extraction + :4500 mount

Define the `role_matrix` YAML schema; migrate cluster-max prose Role Matrix to YAML; extract `context.py` APIRouter from its module-level `create_app()` call; mount the router in `api/node_semantic.py` so `:4500/context/codex` resolves live.

### Phase 2: Unified dispatcher — bash/Python bridge + flag cleanup

Ship `scripts/runtime-dispatch.sh` as the sole bash-side dispatch entry; add a `python -m core.runtime.runtime_registry execute` CLI; refactor `below-route.sh` to call the bridge instead of direct Ollama curl; canonicalize `BR3_LOCAL_ROUTING`; delete dead `$BELOW_URL/api/summarize` call in `autopilot.md`.

### Phase 3: Orchestrator wiring — /begin + /autopilot dispatch per phase

Ship `load-role-matrix.sh` and `load-cluster-flags.sh`; wire role-matrix lookup into `/begin` and `/autopilot` at the top of each phase loop; branch on `builder != claude` to call `runtime-dispatch.sh`; wire `codex-bridge.sh` invocation inside the bridge when builder==codex; add phase-complete assertion that `builder_in_matrix == builder_that_ran`.

### Phase 4: Flag enforcement at skill entry

Add `BR3_ADVERSARIAL_3WAY` branch in `cross_model_review.py`; gate `cache_policy.py` on `BR3_CACHE_BREAKPOINTS`; source `load-cluster-flags.sh` at the top of `/begin` and `/autopilot` phase loops; prove flag toggles change behavior via unit tests.

### Phase 5: Cluster node activation — Otis + Walter + Lomax

Flip `cluster-daemon-config.json` to `auto_dispatch: true`; deploy LaunchAgent plist for `cluster-daemon.mjs`; deploy LaunchDaemon plist for `walter-sentinel`; make `/autopilot` consult `node-matrix.mjs` (remove hardcoded path); add Walter `/api/coverage` gate to `/autopilot`; ship `overflow-shard-watcher.sh` with 30s poll + 60s cooldown + 3/hr cap; resolve Lomax build-status non-blocking→blocking.

### Phase 6: Dispatch telemetry + feature-health dashboard

Add 4 event types (`runtime_dispatched`, `cache_hit`, `context_bundle_served`, `adversarial_review_ran`) to `event_schemas.py`; emit from `runtime_registry.py`, `cache_policy.py`, `codex-bridge.sh`, `cross_model_review.py`; add `feature-health` WS topic to `dashboard_stream.py`; ship `ui/dashboard/panels/feature-health.js` with 15 tiles; delete orphaned `runtime-shadow-metrics.md`.

---

## Parallelization

- Phase 1 ∥ Phase 2 (file-independent).
- Phase 3, 4, 5 serial (all contend on `/begin.md` and `/autopilot.md`).
- Phase 6 serial after 3, 4, 5 (needs emit sites).

## Dependencies

Consumed as-is from cluster-max: `runtime_registry.py`, `codex-bridge.sh`, `feature-flags.yaml`, `cluster-daemon.mjs`, `node-matrix.mjs`, `walter-setup.sh`, `event_collector.py`, `dashboard_stream.py`.

Cluster services required online: Jimmy, Lockwood, Below, Otis, Walter, Lomax. Falls back gracefully when any node offline per `cluster-check.sh` contract.

## Out of Scope

Auto-triage via Below summarize, checkpoint-resume for mid-phase Walter outages, mid-run recovery for cluster-daemon crashes, >3-way adversarial review, new dashboard panels beyond feature-health, replacing deleted cost ledger, cross-project orchestration.
