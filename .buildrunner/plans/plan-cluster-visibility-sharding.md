# Plan: Cluster Visibility & Test Sharding

**Source:** Derived from root-cause investigation of dashboard "idle" display vs actual Walter load (2026-04-23 session).

## Problem Statement

The BR3 cluster dashboard has two independent idle/busy signals, neither of which reflects ground truth:

1. **"Idle/busy" chip** — driven purely by the SSE event bus in `~/.buildrunner/dashboard/public/js/jobs-aggregator.js:165-184`. Only sees work started via `session.update` / `build.started` / `build.heartbeat` / `build.complete` / `consensus` / `feature-health`. User-initiated SSH workloads (e.g. `npx vitest` run by hand against a repo on Walter) never emit these events, so the chip shows `idle` even when the node is at 83% CPU.
2. **`running_builds` counter** — populated by `~/.buildrunner/scripts/cluster-check.sh:136-145` reading `cluster-builds.json`. Only counts BR3-dispatched builds.

Walter is currently pinned running vitest against `/Users/byronhudson/repos/Synapse` (PID 75065, 85.7% CPU; 4 tinypool workers 35–67% CPU; load avg 3.25). Dashboard shows it as idle.

Downstream consequences:

- **Router is blind.** `~/.buildrunner/scripts/resolve-dispatch-node.py:309-312` reads saturation from `active_builds` in `cluster-builds.json`. Out-of-band load never trips the threshold, so overflow to Lockwood / Lomax is never triggered.
- **Overflow nodes sit idle.** Lockwood (`is_overflow_worker: true`, vitest shard 2/3 role) and Lomax (vitest shard 3/3, Playwright overflow) are warm reserves that never activate because the saturation signal is broken.
- **Otis sits idle.** `parallel-builder` role only receives work when a BUILD spec's role-matrix explicitly assigns a phase to it. Between builds, no speculative work; no pull-based work-stealing.
- **No capacity fan-out for tests.** A single-machine vitest run pins Walter instead of sharding 3-way across the M2 fleet.

## Goals

1. Every node's `/health` endpoint reports ground truth: CPU%, load, memory, tracked workloads, a `busy_state` enum.
2. Dashboard's idle/busy chip reads `busy_state` + CPU% fallback, not just the SSE event bus. Workload label row on each card ("vitest · Synapse · 4 workers").
3. Router's saturation check consumes `busy_state`, so overflow triggers on real load regardless of how the work was started.
4. `br test <project>` dispatcher shards vitest across Walter / Lockwood / Lomax by default, registers entries in `cluster-builds.json`.
5. Per-project `.buildrunner/cluster-test-config.yaml` declares shard count and assigned nodes; `/test` and `/e2e` commands route through the dispatcher when the config is present.
6. Otis runs a permanent `tsc --watch` baseline across registered BR3 projects, reports workload via the Phase 1 schema.

## Non-Goals

- Replacing Prometheus. Keep the existing stack; consume more of its data.
- Cross-node test result caching (separate Jimmy-owned work).
- Using Below as a test shard (GPU box; different cost model; inference-reserved).
- Dynamic shard rebalancing mid-run (static split is sufficient for v1).
- A web UI to edit `cluster-test-config.yaml`.
- Authentication on node `/health` endpoints (LAN-only; deferred until a cluster exits LAN).
- Back-porting visibility to Supabase edge function logs.

## Phases

### Phase 1: Node ground-truth API

**Bucket:** backend-build · **Assigned node:** muddy

**Files:**

- `core/cluster/base_service.py` (MODIFY) — enrich `/health` payload with `cpu_pct`, `load_1m`, `mem_avail_pct`, `busy_state`, `workloads[]`.
- `core/cluster/node_tests.py` (MODIFY) — wire process detector into `/api/health`; keep existing `running` / `queue_depth` fields; add `workloads[]` parity.
- `core/cluster/process_detector.py` (NEW) — shared process detector module. Platform branches: macOS uses `psutil` + named matchers (vitest/playwright/tsc); Windows uses `psutil` with identical matchers. Returns list of `{name, pid, cpu_pct, started_at, project}`.
- `core/cluster/below_service.py` (MODIFY if present) — hook the detector on Below's Windows runtime.

**Deliverables:**

- [ ] Process detector module with macOS + Windows branches, unit tested on Muddy.
- [ ] Both endpoints enriched with the same ground-truth fields. `base_service.py` `/health` returns the canonical `{cpu_pct, load_1m, mem_avail_pct, busy_state, workloads[]}` payload; `node_tests.py` `/api/health` extends that same shape with existing `running` / `queue_depth` fields (superset, not divergent schema). Both must stay in sync — no silent skew.
- [ ] `busy_state` thresholds: `idle` (<30% CPU, no tracked workloads), `active` (30–75% or ≥1 workload), `saturated` (>75% or load > cores).
- [ ] `psutil` installation contract: pin to `psutil>=5.9.8` in `pyproject.toml`; for Below, add a `pip install psutil` step to its worker bootstrap (Below runs `research_worker.py` with its own deps, not the BR3 poetry env). Document in Phase 1 ops notes.
- [ ] First-call warmup: `psutil.cpu_percent(interval=None)` returns 0.0 on first call on all platforms (documented psutil behavior) — the service must call it once at startup and discard the result, else `busy_state` will misfire to `idle` immediately after a node restart.
- [ ] Rsync + service restart on all 7 nodes (Muddy, Lockwood, Walter, Otis, Lomax, Below, Jimmy) with smoke curl against both `/health` and `/api/health`.
- [ ] Decision log entry recording schema version bump.

**Success criteria:** `curl http://10.0.1.102:8100/health` (not just `/api/health`) while Walter is running vitest returns `busy_state: active` with a workloads entry for each of the 4 processes. Ditto for Below running ollama (`busy_state: active` with an `ollama` workload).

### Phase 2: Dashboard renders ground truth

**Bucket:** ui-build · **Assigned node:** muddy

**Files:**

- `~/.buildrunner/scripts/cluster-check.sh` (MODIFY) — `--health-json` currently hand-constructs JSON (`cluster-check.sh:147` SSH branch, `cluster-check.sh:118` HTTP branch) and drops unknown fields. Rewrite to proxy the node's `/health` response verbatim plus the existing synthesized fields (`running_builds` etc.). Without this, the new Phase 1 fields never reach the dashboard.
- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — this is the actual dashboard server (no `server.mjs` exists). `refreshNodeHealth()` currently polls on a 30s interval (`events.mjs:361`). Extend it to (a) read `busy_state` / `workloads[]` / `cpu_pct` from the enriched `cluster-check.sh --health-json` output, (b) reduce interval to 10s guarded by a config knob `BR3_NODE_HEALTH_POLL_MS` defaulting to 10000, (c) emit a new SSE event `node.workload` whenever a node's workload list changes.
- `~/.buildrunner/dashboard/public/js/jobs-aggregator.js` (MODIFY) — add a seventh listener for `node.workload` events alongside the existing six (`jobs-aggregator.js:160-184`). Workload-sourced entries carry an explicit `origin: "node-health"` tag; SSE build entries carry `origin: "sse"`. Dedupe by `build_id` when both exist (SSE wins — it has phase info). Expose via existing `window.getJobsForNode` accessor unchanged.
- `~/.buildrunner/dashboard/public/js/ws-cluster-node-health.js` (MODIFY) — rewrite chip logic: primary=`busy_state` from node-health cache, fallback=CPU% threshold, tertiary=SSE event bus. Render workload label row under CPU bar.
- `~/.buildrunner/dashboard/public/js/node-card.js` (MODIFY if present; otherwise inline in ws-cluster-node-health.js) — workload label row.

**Deliverables:**

- [ ] `cluster-check.sh --health-json` proxies the full `/health` payload including `busy_state` and `workloads[]`; verified by diffing raw `curl /health` vs `cluster-check.sh --health-json <node>` for each of the 7 nodes.
- [ ] Poll interval knob `BR3_NODE_HEALTH_POLL_MS` with 10s default; existing 30s behavior restored when set to `30000`.
- [ ] `node.workload` SSE event emitted from `events.mjs` whenever a node's `workloads[]` delta changes. Event payload: `{node, workloads, busy_state, ts}`.
- [ ] `jobs-aggregator.js` handles the new event type with dedupe semantics (SSE build entry wins over node-health entry for the same `build_id`).
- [ ] Chip logic: `busy_state` first, CPU% fallback (>30% → active, >75% → saturated), SSE events only as a label source.
- [ ] Workload label row renders "vitest · Synapse · 4 workers" (or "idle · 3% CPU") under the CPU bar.
- [ ] SSE-driven BR3 phase info is preserved: `autopilot phase 3 · BUILD_foo` still surfaces when present.
- [ ] No regression on existing dashboard tabs (overflow panel, cluster-builds list, Prometheus CPU bars).

**Success criteria:** SSH-started vitest on Walter appears as `active · vitest · N workers` within one poll cycle (≤10s at default `BR3_NODE_HEALTH_POLL_MS`).

### Phase 3: Router sees ground truth

**Bucket:** backend-build · **Assigned node:** muddy

**Files:**

- `~/.buildrunner/scripts/resolve-dispatch-node.py` (MODIFY) — saturation check reads `busy_state` + `cpu_pct` from each node's `/health`, not just `cluster-builds.json` active_builds.
- `~/.buildrunner/scripts/cluster-check.sh` (MODIFY if saturation logic lives there) — expose the new health fields via `--health-json`.

**Deliverables:**

- [ ] Saturation check weights: `busy_state=saturated` → force overflow; `busy_state=active` + CPU>75% → force overflow; else retain active_builds threshold.
- [ ] `cluster-builds.json` count remains a secondary input, not the primary.
- [ ] Manual test case: spike Walter with vitest out-of-band, dispatch a new build, verify it routes to Lockwood or Lomax.
- [ ] Decision log entry recording old vs new threshold behavior.
- [ ] **Rollback env var `BR3_ROUTER_LEGACY_SATURATION=1` must be coded as part of this phase** (not assumed). When set, `resolve-dispatch-node.py` skips the `busy_state` check and falls back to the pre-existing Prometheus + `agents.json` logic at `resolve-dispatch-node.py:330-376`. Same name in `cluster-check.sh` if saturation logic migrates there. Covered by a smoke test that toggles the env var and confirms dispatch behavior returns to the prior baseline.
- [ ] **Fail-open timeout:** new env `BR3_NODE_HEALTH_TIMEOUT_MS` (default 500ms). If any node's `/health` call exceeds this, the router falls open to the Prometheus-based check rather than stalling the dispatch critical path. Model after existing `load_query_timeout_ms` pattern (`resolve-dispatch-node.py:313`). Logged as `"source": "fail-open-health-timeout"` in the router decision record.

**Success criteria:** User-initiated SSH load on a primary node triggers overflow routing on the next dispatch, confirmed in router logs. Toggling `BR3_ROUTER_LEGACY_SATURATION=1` reverts to pre-Phase-3 behavior, verified by the smoke test.

### Phase 4: Parallel-shard test dispatcher

**Bucket:** terminal-build · **Assigned node:** muddy

**Files:**

- `~/.buildrunner/scripts/dispatch-test.sh` (NEW) — entry point. Reads `.buildrunner/cluster-test-config.yaml` from target project, rsyncs, runs shards, collects, merges. Invoked directly; there is no unified `br` CLI today (only per-feature scripts like `br-swap-accounts.sh`).
- `~/.buildrunner/scripts/collect-test-shards.sh` (NEW) — merge JUnit XML and vitest JSON reports from N nodes into a single report.
- `~/.buildrunner/docs/sharded-testing.md` (NEW) — architecture + ops notes, including the SSH username map and shard strategy rationale.
- `~/.buildrunner/scripts/br-test.sh` (NEW) — optional thin wrapper that matches the `br-*.sh` naming convention of existing scripts; delegates to `dispatch-test.sh`. Kept separate so `dispatch-test.sh` can also be called directly from `/test` and `/e2e`.

**Shard strategy:** Use vitest's built-in `--shard=N/M` flag, not a custom file-count split. Vitest splits by test-count internally and handles unbalanced durations reasonably. Projects that don't use vitest (rare in BR3) fall back to a simpler "single-node local" path — no custom splitter to maintain. This also avoids the Playwright/vitest mixed-suite duration-skew trap a file-count split would hit.

**Write contract for `cluster-builds.json`:** Multiple writers exist today (`events.mjs:62-86` with a `.lock` flag, `registry.mjs:25-28` unlocked, `registry-sync.mjs:107` unlocked). Phase 4 MUST route all dispatcher writes through the SQLite-backed state machine at `~/.buildrunner/dashboard/build-state-machine.mjs` — that module is explicitly the single writer per its header comment. Direct `writeFileSync` from `dispatch-test.sh` is forbidden. Three shards completing near-simultaneously must not race on the JSON file.

**SSH username map:** `resolve-dispatch-node.py:419-430` already hardcodes `ssh_user = "byronhudson"` with `below` overridden to `"byron"`. `dispatch-test.sh` must reuse this map (either by shelling out to a shared helper or by duplicating the constant with a DRY note). Document any future drift in `sharded-testing.md`.

**Deliverables:**

- [ ] Dispatcher uses `vitest --shard=N/M` (or project-declared equivalent). No custom splitter.
- [ ] Rsync target repo to each node under `/tmp/br-test-<build_id>/`; clean on exit or timeout.
- [ ] Run shards in parallel via SSH; stream stdout back tagged with shard ID.
- [ ] Merge results (JUnit XML + vitest JSON) into a single report under `/tmp/br-test-<build_id>-merged.{xml,json}`.
- [ ] Register `cluster-builds.json` entries per shard **through `build-state-machine.mjs`** (single-writer contract) — `status: running` on start, `complete` / `failed` on exit.
- [ ] Per-shard failure isolation: one shard failing does not kill others; aggregate pass/fail at the end.
- [ ] SSH reachability handling: exit code 255 (host unreachable) is treated as infrastructure failure, not test failure. The shard is requeued once on a remaining node before giving up.
- [ ] Per-node SSH username respected (byronhudson for Apple nodes, byron for Below).
- [ ] Timeout policy: per-shard hard cap from config; kill + mark failed on expiry.

**Success criteria:** `br test synapse` against a 3-node split runs Synapse's vitest suite in meaningfully less wall-time than single-node (target ≥2× speedup; skew from vitest's built-in splitter is acceptable), returns merged pass/fail, shows 3 shard entries on the dashboard.

### Phase 5: Per-project shard config + command wiring

**Bucket:** terminal-build · **Assigned node:** muddy

**Files:**

- `~/.buildrunner/templates/cluster-test-config.yaml.template` (NEW) — canonical template with commented fields.
- `.buildrunner/cluster-test-config.yaml` (NEW, in BuildRunner3) — installed reference config.
- `~/.claude/commands/test.md` (MODIFY) — detect config, route through dispatcher if present.
- `~/.claude/commands/e2e.md` (MODIFY) — detect config, route Playwright specs to Lomax when config lists it as Playwright target.

**Deliverables:**

- [ ] Template fields: `test_command`, `shard_count`, `assigned_nodes[]`, `timeout_sec`, `playwright: { enabled, assigned_node }`.
- [ ] Config installed in BuildRunner3 and validated with `dispatch-test.sh --dry-run`.
- [ ] `/test` skill: when `.buildrunner/cluster-test-config.yaml` exists → dispatcher; else → local behavior.
- [ ] `/e2e` skill: same routing contract for Playwright.
- [ ] Docs under `~/.buildrunner/docs/sharded-testing.md` on how to install config in other BR3 projects.

**Success criteria:** Invoking `/test` in a configured project runs sharded and dashboard-visible; invoking in an unconfigured project runs locally with no breakage.

### Phase 6: Otis type-check loop

**Bucket:** backend-build · **Assigned node:** otis

**Files:**

- `core/cluster/otis_typecheck.py` (NEW) — service that scans registered BR3 project paths, launches `tsc --noEmit --watch` per project, publishes error counts.
- `core/cluster/otis_service.py` (MODIFY or NEW) — compose the typecheck service with existing Otis uvicorn app.
- `~/.buildrunner/units/otis-typecheck.plist` (NEW) — launchd unit to start on Otis boot.
- `~/.buildrunner/docs/otis-secondary-role.md` (NEW) — ops notes: pause/resume contract, project discovery, troubleshooting.

**Deliverables:**

- [ ] Project discovery reads a file list (e.g. `~/.buildrunner/otis-projects.txt`) or `cluster-builds.json` active-project list.
- [ ] One `tsc --noEmit --watch` per project; workload reported via Phase 1 schema (`workloads[].name = "tsc"`, `project = <repo>`, `error_count = N`).
- [ ] Dashboard label shows "tsc-watch · N projects · M errors".
- [ ] **Pause/resume via kill-and-relaunch, not SIGSTOP.** On dispatch arrival, typecheck processes are terminated (SIGTERM, SIGKILL after 3s) and their compilation cache is freed. On dispatch exit, they cold-start again (~8s per project). Rationale: SIGSTOP on a tsc process blocked on FSEvents frees almost no CPU (it's already ~0%) and retains the full compilation cache in RAM — the intended "free resources for autopilot" goal is not achieved. Kill-and-relaunch is simpler, actually frees memory, and avoids the stuck-process failure mode.
- [ ] launchd plist starts the service on Otis boot; survives reboot.

**Success criteria:** Otis reports `busy_state: active` with a `tsc-watch` workload label at rest; typecheck terminates cleanly on parallel-builder dispatch arrival and resumes (cold-start) on dispatch exit.

## Parallelization Matrix

| Phase | Key Files                                                                         | Parallel With | Blocked By |
| ----- | --------------------------------------------------------------------------------- | ------------- | ---------- |
| 1     | base_service.py, node_tests.py, process_detector.py (NEW)                         | 4, 6          | -          |
| 2     | dashboard/events.mjs, dashboard/public/js/\*.js, cluster-check.sh                 | 4, 6          | 1          |
| 3     | resolve-dispatch-node.py                                                          | 2, 4, 6       | 1          |
| 4     | dispatch-test.sh (NEW), collect-test-shards.sh (NEW), br, build-state-machine.mjs | 1, 6          | -          |
| 5     | cluster-test-config template, /test + /e2e skills                                 | 6             | 4          |
| 6     | otis_typecheck.py (NEW), otis_service.py, launchd plist                           | 1, 2, 3, 4, 5 | -          |

**Note:** Phase 2 and Phase 3 both touch `cluster-check.sh` (Phase 2 for `--health-json` passthrough, Phase 3 only if saturation logic migrates). They are serialized in the matrix to avoid merge conflicts — Phase 2 lands first, then Phase 3 rebases.

**Waves:**

- Wave 1 (parallel): Phase 1, Phase 4, Phase 6
- Wave 2: Phase 2 (after Phase 1)
- Wave 3: Phase 3 (after Phase 1 and Phase 2 — both touch `cluster-check.sh`)
- Wave 4: Phase 5 (after Phase 4)

## Risks & Mitigations

- **Schema bump on `/health`** could break legacy consumers. Mitigation: additive-only; all existing fields retained. Explicit audit in Phase 1 deliverables of every caller of `/health` and `/api/health` before rollout.
- **`cluster-check.sh --health-json` hand-constructs its JSON and drops unknown fields** (`cluster-check.sh:118,147`). Mitigation: Phase 2 deliverable explicitly rewrites both branches to proxy the node `/health` payload. Without this, Phase 1 fields never reach the dashboard.
- **Router behavior change** could misroute during the transition. Mitigation: `BR3_ROUTER_LEGACY_SATURATION=1` rollback env var coded as a Phase 3 deliverable (not assumed to exist). Plus `BR3_NODE_HEALTH_TIMEOUT_MS` fail-open at 500ms default to prevent the new health check from stalling dispatch on a slow node.
- **Concurrent writers on `cluster-builds.json`** (`events.mjs:62-86` locked, `registry.mjs:25-28` and `registry-sync.mjs:107` unlocked). Mitigation: Phase 4 dispatcher routes all writes through `build-state-machine.mjs` as the single writer.
- **Rsync + SSH shard dispatch** amplifies network chatter. Mitigation: LAN-only; rsync hardlinks against prior shard dir when possible.
- **File-count shard skew.** Mitigation: use `vitest --shard=N/M` built-in (not a custom splitter).
- **SSH reachability during sharded runs.** Mitigation: SSH exit 255 is treated as infra failure, shard is requeued once on a remaining node; otherwise partial results aggregate with the failing shard flagged.
- **Otis typecheck pause/resume.** Mitigation: kill-and-relaunch (not SIGSTOP) — simpler, frees memory, avoids stuck-process risk.
- **Below Windows branch** of the process detector is less tested. Mitigation: explicit psutil install step documented; `psutil.cpu_percent` first-call warmup at boot; ollama smoke test on Below before marking Phase 1 complete.
- **`server.mjs` does not exist** in the dashboard tree — the actual file is `events.mjs`. Plan corrected accordingly; baseline poll interval is 30s (`events.mjs:361`) with a new knob `BR3_NODE_HEALTH_POLL_MS` defaulting to 10s.
- **`jobs-aggregator.js` is SSE-only today** (`jobs-aggregator.js:160-184`). Mitigation: Phase 2 adds a seventh SSE event type `node.workload` emitted from `events.mjs` rather than mutating aggregator state from outside. Dedupe by `build_id` with SSE origin winning.

## Governance

- Respects the "no unauthorized destructive ops" rule: no `git push --force`, no database drops, no secret commits.
- RLS not touched. LLM model selection not touched.
- BRLogger not affected; this is cluster infra, not app-layer.
- `/ship` gates run as usual on merge to main.
