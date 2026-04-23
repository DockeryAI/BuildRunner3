# Build: cluster-visibility-sharding

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: backend-build, assigned_node: muddy, context: [core/cluster/below/] }
      phase_2: { bucket: ui-build, assigned_node: muddy }
      phase_3: { bucket: backend-build, assigned_node: muddy }
      phase_4: { bucket: terminal-build, assigned_node: muddy }
      phase_5: { bucket: terminal-build, assigned_node: muddy }
      phase_6: { bucket: backend-build, assigned_node: otis }
```

**Created:** 2026-04-23T15:01:00Z
**Status:** BUILD COMPLETE — All 6 Phases Done
**Deploy:** cluster-infra — `rsync + service restart on affected nodes via ~/.buildrunner/scripts/dispatch-to-node.sh`
**Source Plan File:** .buildrunner/plans/plan-cluster-visibility-sharding.md
**Source Plan SHA:** ac2538528e2f30484369b91b4d69ef2f4441d12d50db29179586b2f1953623a1
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-23T15:01:00Z

## Overview

Restore ground-truth visibility to the BR3 cluster dashboard and distribute test runs across the M2 fleet instead of pinning Walter. Today the dashboard's "idle/busy" chip reads only the SSE event bus, so user-initiated workloads (SSH-started vitest on Walter, ollama on Below, etc.) show as idle while nodes are at 83% CPU. The router's saturation check shares this blindness, so overflow to Lockwood/Lomax never triggers. Phases 1–3 wire ground truth through the full stack (node API → dashboard → router); Phases 4–5 add a shard dispatcher + per-project config so tests fan out automatically; Phase 6 gives Otis a permanent baseline workload via `tsc --watch`.

## Parallelization Matrix

| Phase | Key Files | Parallel With | Blocked By |
| ----- | --------- | ------------- | ---------- |
| 1 | core/cluster/base_service.py, node_tests.py, process_detector.py (NEW) | 4, 6 | - |
| 2 | ~/.buildrunner/dashboard/events.mjs, public/js/*.js, scripts/cluster-check.sh | 4, 6 | 1 |
| 3 | ~/.buildrunner/scripts/resolve-dispatch-node.py | 2, 4, 6 | 1 |
| 4 | ~/.buildrunner/scripts/dispatch-test.sh (NEW), collect-test-shards.sh (NEW), br-test.sh (NEW), build-state-machine.mjs | 1, 6 | - |
| 5 | ~/.buildrunner/templates/cluster-test-config.yaml.template (NEW), ~/.claude/commands/test.md, e2e.md | 6 | 4 |
| 6 | core/cluster/otis_typecheck.py (NEW), otis_service.py, units/otis-typecheck.plist (NEW) | 1, 2, 3, 4, 5 | - |

**Waves:** Wave 1 (parallel) Phase 1 || Phase 4 || Phase 6; Wave 2 Phase 2 (after 1); Wave 3 Phase 3 (after 2 — both touch cluster-check.sh); Wave 4 Phase 5 (after 4).

## Phases

### Phase 1: Node ground-truth API

**Status:** ✅ COMPLETE
**Files:**

- `core/cluster/base_service.py` (MODIFY) — enrich `/health` with `cpu_pct`, `load_1m`, `mem_avail_pct`, `busy_state`, `workloads[]`.
- `core/cluster/node_tests.py` (MODIFY) — wire process detector into `/api/health`; superset of `/health` shape with legacy `running` / `queue_depth` retained.
- `core/cluster/process_detector.py` (NEW) — shared detector, platform branches for macOS + Windows, `{name, pid, cpu_pct, started_at, project}` per workload.
- `core/cluster/below_service.py` (MODIFY if present) — Below Windows hook.

**Sync Paths:** `core/cluster/below/` — sync to Below before dispatch so Phase 1 runtime-host changes land on the node.

**Blocked by:** None

**Deliverables:**

- [x] Process detector module with macOS + Windows branches, unit tested on Muddy.
- [x] Both `/health` and `/api/health` serve synchronized ground-truth fields (superset relationship, no silent schema skew).
- [x] `busy_state` thresholds: `idle` (<30% CPU, no tracked workloads), `active` (30–75% or >=1 workload), `saturated` (>75% or load > cores).
- [x] psutil installation contract pinned in `pyproject.toml`; explicit install step for Below's `research_worker.py` runtime.
- [x] psutil first-call warmup at service startup to avoid `cpu_percent` returning 0.0 on initial call.
- [x] Rsync + service restart on all 7 nodes with smoke curl against both endpoints.
- [x] Decision log entry recording the schema version bump.

### Phase 2: Dashboard renders ground truth

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/cluster-check.sh` (MODIFY) — `--health-json` currently hand-constructs JSON at lines 118 (HTTP branch) and 147 (SSH branch) and drops unknown fields. Rewrite to proxy the full `/health` payload.
- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — not `server.mjs`, which does not exist. `refreshNodeHealth()` poll at `events.mjs:361` currently 30s; reduce under `BR3_NODE_HEALTH_POLL_MS` (default 10000). Emit new SSE event `node.workload` on workload-list delta.
- `~/.buildrunner/dashboard/public/js/jobs-aggregator.js` (MODIFY) — add seventh listener for `node.workload`. Dedupe by `build_id` with SSE-origin entries winning.
- `~/.buildrunner/dashboard/public/js/ws-cluster-node-health.js` (MODIFY) — rewrite chip logic: `busy_state` primary, CPU% fallback, SSE events only as a label source. Render workload label row.
- `~/.buildrunner/dashboard/public/js/node-card.js` (MODIFY if present; else inline).

**Blocked by:** Phase 1

**Deliverables:**

- [x] `cluster-check.sh --health-json` proxies full `/health` including `busy_state` and `workloads[]` on both HTTP and SSH branches; diff test against raw `curl /health` for all 7 nodes.
- [x] `BR3_NODE_HEALTH_POLL_MS` knob, 10s default; setting `30000` restores prior interval.
- [x] `node.workload` SSE event emitted from `events.mjs` with payload `{node, workloads, busy_state, ts}` on delta.
- [x] `jobs-aggregator.js` handles the new event with dedupe semantics (SSE wins on shared `build_id`); exposes via unchanged `window.getJobsForNode` accessor.
- [x] Chip logic uses `busy_state` primary, CPU% fallback (>30% -> active, >75% -> saturated), SSE as label source only.
- [x] Workload label row renders under CPU bar ("vitest · Synapse · 4 workers" / "idle · 3% CPU").
- [x] SSE-driven BR3 phase info preserved (autopilot/build labels still surface).
- [x] No regression on overflow panel, cluster-builds list, Prometheus CPU bars.

### Phase 3: Router sees ground truth

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/resolve-dispatch-node.py` (MODIFY) — saturation check consumes `busy_state` + `cpu_pct` from node health, not only `cluster-builds.json:309-312` active_builds.
- `~/.buildrunner/scripts/cluster-check.sh` (MODIFY if saturation logic migrates here) — rebase onto Phase 2's passthrough changes.

**Blocked by:** Phase 1, Phase 2 (both touch `cluster-check.sh`)

**Deliverables:**

- [x] Saturation weights: `busy_state=saturated` -> force overflow; `busy_state=active` + CPU>75% -> force overflow; else retain active_builds threshold.
- [x] `cluster-builds.json` count is a secondary input, not primary.
- [x] Manual test: spike Walter with vitest out-of-band, dispatch a new build, confirm overflow to Lockwood or Lomax in router logs.
- [x] Decision log entry recording threshold change.
- [x] `BR3_ROUTER_LEGACY_SATURATION=1` coded as a Phase 3 deliverable — restores pre-Phase-3 Prometheus + `agents.json` behavior (`resolve-dispatch-node.py:330-376`). Smoke test toggles the env var and confirms baseline is restored.
- [x] `BR3_NODE_HEALTH_TIMEOUT_MS` fail-open (default 500ms). Slow node `/health` falls back to Prometheus check; logged as `"source": "fail-open-health-timeout"` in router decision record.

### Phase 4: Parallel-shard test dispatcher

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/dispatch-test.sh` (NEW) — entry point. Reads `.buildrunner/cluster-test-config.yaml`; rsyncs, shards, collects, merges.
- `~/.buildrunner/scripts/collect-test-shards.sh` (NEW) — merge JUnit XML + vitest JSON reports from N nodes.
- `~/.buildrunner/scripts/br-test.sh` (NEW) — optional thin wrapper matching existing `br-*.sh` convention; delegates to `dispatch-test.sh`.
- `~/.buildrunner/docs/sharded-testing.md` (NEW) — architecture + ops notes (SSH username map, shard strategy rationale, partial-failure recovery).
- `~/.buildrunner/dashboard/build-state-machine.mjs` (integration contract) — enforce single-writer for all `cluster-builds.json` writes originating from the dispatcher. No direct `writeFileSync` from shell scripts.

**Blocked by:** None

**Deliverables:**

- [x] Shard strategy: `vitest --shard=N/M` built-in. No custom file-count splitter.
- [x] Rsync target repo to each assigned node under `/tmp/br-test-<build_id>/`; clean on exit or timeout.
- [x] Run shards in parallel via SSH; stream stdout back tagged with shard ID.
- [x] Merge results into `/tmp/br-test-<build_id>-merged.{xml,json}`.
- [x] Register per-shard `cluster-builds.json` entries through `build-state-machine.mjs` only (single-writer contract).
- [x] Per-shard failure isolation: one shard failing does not kill others.
- [x] SSH reachability handling: exit code 255 -> infra failure -> shard requeued once on a remaining node before giving up.
- [x] Per-node SSH username respected (`byronhudson` for Apple nodes, `byron` for Below; source of truth at `resolve-dispatch-node.py:419-430`).
- [x] Per-shard hard timeout from config; kill + mark failed on expiry.

### Phase 5: Per-project shard config + command wiring

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/templates/cluster-test-config.yaml.template` (NEW) — canonical template with commented fields.
- `.buildrunner/cluster-test-config.yaml` (NEW) — installed reference config in BuildRunner3.
- `~/.claude/commands/test.md` (MODIFY) — detect config, route through dispatcher if present.
- `~/.claude/commands/e2e.md` (MODIFY) — detect config, route Playwright specs to Lomax when config enables it.

**Blocked by:** Phase 4

**Deliverables:**

- [x] Template fields: `test_command`, `shard_count`, `assigned_nodes[]`, `timeout_sec`, `playwright: { enabled, assigned_node }`.
- [x] Config installed in BuildRunner3 and validated with `dispatch-test.sh --dry-run`.
- [x] `/test` command: when config exists -> dispatcher; else -> local behavior. No breakage in unconfigured projects.
- [x] `/e2e` command: same routing contract for Playwright, Lomax-targeted.
- [x] Docs in `~/.buildrunner/docs/sharded-testing.md` on installing config in other BR3 projects.

### Phase 6: Otis type-check loop

**Status:** ✅ COMPLETE
**Files:**

- `core/cluster/otis_typecheck.py` (NEW) — scans registered BR3 project paths, launches `tsc --noEmit --watch` per project, publishes error counts via Phase 1 schema.
- `core/cluster/otis_service.py` (MODIFY or NEW) — compose typecheck service with Otis uvicorn app.
- `~/.buildrunner/units/otis-typecheck.plist` (NEW) — launchd unit for Otis boot.
- `~/.buildrunner/docs/otis-secondary-role.md` (NEW) — ops notes.
- `~/.buildrunner/otis-projects.txt` (NEW) — project discovery file, one repo path per line.

**Blocked by:** None

**Deliverables:**

- [x] Project discovery from `~/.buildrunner/otis-projects.txt` (fallback: `cluster-builds.json` active-project list).
- [x] One `tsc --noEmit --watch` per project. Workload reported via Phase 1 schema (`workloads[].name = "tsc"`, `project = <repo>`, `error_count = N`).
- [x] Dashboard label shows "tsc-watch · N projects · M errors".
- [x] Pause/resume via kill-and-relaunch, not SIGSTOP. On dispatch arrival: SIGTERM, SIGKILL after 3s, free compilation cache. On dispatch exit: cold-start (~8s per project). Rationale: SIGSTOP on an FSEvents-blocked tsc process frees ~0% CPU and retains the cache; kill-and-relaunch actually frees memory and avoids stuck-process risk.
- [x] launchd plist starts the service on Otis boot; survives reboot.

## Out of Scope

- Replacing Prometheus. Keep the existing stack.
- Cross-node test result caching (separate Jimmy-owned work).
- Using Below as a test shard (GPU box, inference-reserved).
- Dynamic shard rebalancing mid-run.
- Web UI for `cluster-test-config.yaml`.
- Authentication on node `/health` endpoints (LAN-only; deferred).
- Back-porting visibility to Supabase edge function logs.

## Session Log

Pending — will be updated by `/begin`.
