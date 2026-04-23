# Build: Cluster Dashboard — Prometheus Surfacing

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: backend-build, assigned_node: muddy }
      phase_2: { bucket: ui-build, assigned_node: muddy }
      phase_3: { bucket: ui-build, assigned_node: muddy }
      phase_4: { bucket: ui-build, assigned_node: otis }
      phase_5: { bucket: ui-build, assigned_node: muddy }
      phase_6: { bucket: qa, assigned_node: walter }
```

**Created:** 2026-04-22
**Status:** Phases 1-3 Complete — Phase 4 In Progress
**Deploy:** web — dashboard auto-reloads on file change; Node server auto-restarts via launchd
**Source Plan File:** .buildrunner/plans/plan-cluster-dashboard-prometheus-surfacing.md
**Source Plan SHA:** 52ecdd4f675a339f3ce968cdea8a960532439739638a73503b7bc76852bf051a
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-22T22:09:17Z

## Overview

Replace the dashboard's raw SSE event log as the centerpiece with three state-shaped panels (Node Health cards, Storage Health table, Overflow Reserve panel) that surface every Prometheus datapoint from the recent cluster-prometheus-integration build. Adds a right-side drill-down drawer for per-node CPU/memory/disk/network history, a BR3-native jobs list per node, and temperature chips where hardware/OS supports it (Jimmy Linux real now, Below Windows CPU/GPU real now, Macs deferred to a macmon-exporter follow-up build).

Schema bumps to v3 (additive only — all v2 fields preserved). New `/api/prometheus/range` passthrough endpoint with strict metric+selector allowlist powers drawer sparklines. Event log demoted to a collapsed bottom drawer. Phase 2 ships behind a `?prom_v3=1` query flag; flag removed in Phase 6.

**Mockup (design source of truth):** `http://localhost:4400/mockup-prometheus.html`
**Dashboard code location:** `~/.buildrunner/dashboard/` (user home, outside this git repo; spec artifacts stay in this repo's `.buildrunner/`).

## Parallelization Matrix

| Phase | Key Files                                                                            | Can Parallel With | Blocked By            |
| ----- | ------------------------------------------------------------------------------------ | ----------------- | --------------------- |
| 1     | `integrations/prometheus-metrics.mjs`, `events.mjs`                                  | —                 | —                     |
| 2     | `public/index.html`, `public/styles.css`, `events.mjs` (panel-registry one-liner)    | —                 | 1 (shared events.mjs) |
| 3     | `public/js/ws-cluster-node-health.js`, `public/js/jobs-aggregator.js` (NEW)          | 4                 | 1, 2                  |
| 4     | `public/js/ws-cluster-storage-health.js`, `public/js/ws-cluster-overflow-reserve.js` | 3                 | 1, 2                  |
| 5     | `public/js/ws-cluster-drawer.js` (NEW), `public/styles.css` (additive)               | —                 | 1, 2, 3               |
| 6     | `tests/dashboard-prometheus-panels.spec.mjs`, `tests/smoke/prometheus-schema.sh`     | —                 | 1–5                   |

## Phases

### Phase 1: Schema v3 backend — expand collectors, add range endpoint, fix off-spec query

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/integrations/prometheus-metrics.mjs` (MODIFY)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY)

**Blocked by:** None

**Deliverables:**

- [ ] `collectNodeHealthHardware` expands to emit per node: v2 fields + `cpu_per_core[]`, `load_1m`, `load_5m`, `load_15m`, `mem_used_bytes`, `mem_cached_bytes`, `mem_buffered_bytes`, `mem_free_bytes`, `swap_used_bytes`, `swap_total_bytes`, `proc_count`, `fd_count`, `temp_c`, `gpu_temp_c` (nullable), `temp_source`, `interfaces[{name, rx_bytes_sec, tx_bytes_sec}]`.
- [ ] `collectStorageHealthHardware` expands with `mounts[{mountpoint, total_bytes, free_bytes, read_bytes_sec, write_bytes_sec}]` + `disk_delta_24h_bytes`.
- [ ] Per-OS temperature PromQL: Linux `node_hwmon_temp_celsius` (Jimmy); Windows `windows_thermalzone_temperature_celsius` CPU + `nvidia_smi_temperature_gpu` GPU (Below); Macs null with `temp_source: "macmon (not installed)"`.
- [ ] Delete off-spec `MACOS_RAM_PCT_PROMQL` branch at prometheus-metrics.mjs:25-26 (non-existent metrics; canonical MemAvailable/MemTotal already covers all OSes). Stops rate-limited "fetch failed" log noise.
- [ ] `events.mjs` merge stamps `schema_version: 3` additively; v2 fields preserved at root.
- [ ] Collectors emit `status: 'yellow'` + `reason` + `stale_since` at event root on Prometheus offline; merge layer caches last-good snapshot per event type in memory.
- [ ] New endpoint `GET /api/prometheus/range` with params `metric`, `node`, `start`, `end`, `step`, optional selectors `mount`, `interface`, `cpu_mode` (user|sys|iowait|idle), `core`. Server-side allowlist maps `{metric, selectors}` → canonical PromQL; non-allowlisted → 400.
- [ ] Endpoint returns `{ data: [{t,v}], source, generated_at }`; `{ error, status: "yellow" }` + 503 on Prometheus offline; same rate-limit as instant queries.
- [ ] Unit smoke: `metric=cpu_mode&cpu_mode=user&node=muddy` non-empty; `metric=disk_read&mount=/` non-empty; `metric=net_in&interface=en0&node=muddy` non-empty; 400 on missing required selector; 503+yellow when Prometheus down.

### Phase 2: DOM + token refactor — layout slots for new panels, event log demotion

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — remove node-health entry from panel registry at line 594)

**Blocked by:** Phase 1 (shared `events.mjs` edit — serialize)

**Deliverables:**

- [ ] Replace `<div class="cluster-strip" id="node-grid">` with `<div class="node-health-grid" id="node-grid"></div>`.
- [ ] Delete text-only `#node-health` panel from `index.html:309` AND remove `{ type: 'node-health', title: 'Node Health' }` from `events.mjs:594` registry (both required).
- [ ] Add `#storage-health` and `#overflow-reserve` `.panel` elements to `panel-grid` with empty bodies.
- [ ] Add hidden `<aside id="node-drawer">` + `<div id="drawer-scrim">` at end of `<body>`.
- [ ] Move `#event-log` panel out of `panel-grid` into fixed-position `<details id="event-log-drawer">` at bottom. Default collapsed.
- [ ] Extend `styles.css` with `.node-health-grid`, `.node-card`, `.mbar`, `.jobs`, `.storage-table`, `.overflow-row`, `.drawer`, `.drawer-scrim`, `.event-log-drawer` — all from existing color tokens only.
- [ ] Gate new layout behind `?prom_v3=1` until Phase 3 ships.

### Phase 3: Node Health cards + Jobs list

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/public/js/ws-cluster-node-health.js` (MODIFY — full rewrite)
- `~/.buildrunner/dashboard/public/js/jobs-aggregator.js` (NEW)

**Blocked by:** Phase 1, Phase 2
**After:** Phase 2

**Deliverables:**

- [ ] SSE `node-health` consumer renders one `.node-card` per node with status dot (CPU+RAM+reachability combined).
- [ ] CPU bar + % with cyan→yellow→red at 60/85%. RAM bar same thresholds.
- [ ] Load avg row: `1m · 5m · 15m`. Hidden on Below (Windows — no load).
- [ ] Temperature row: color-coded chip (<65 cyan, 65–80 yellow, >80 red); em-dash with tooltip `temp_source` when null; GPU chip when `gpu_temp_c` present.
- [ ] Uptime humanized (`16d 3h`), IP, hardware class.
- [ ] Jobs list per card: build/session/test/infra/idle chips, max 3 + `+N more`.
- [ ] `jobs-aggregator.js` subscribes to existing SSE topics (`session.update`, build scanner, `consensus`, `feature-health`) and maintains per-node job map. No new infra.
- [ ] Card click dispatches `cluster:node-drawer-open` with `{nodeId}`.
- [ ] Graceful degradation: schema_version < 3 → renders v2 fields only, hides load/temp/jobs rows.

### Phase 4: Storage Health + Overflow Reserve panels

**Status:** 🚧 in_progress
**Files:**

- `~/.buildrunner/dashboard/public/js/ws-cluster-storage-health.js` (MODIFY — full rewrite)
- `~/.buildrunner/dashboard/public/js/ws-cluster-overflow-reserve.js` (MODIFY — full rewrite)

**Blocked by:** Phase 1, Phase 2
**After:** Phase 2

**Deliverables:**

- [ ] Storage table: node, mount, used/total bar, free, 24h Δ (▼ red / ▲ green / · neutral). Thresholds at 80% and 90%.
- [ ] Row expand-on-click: reveals all `mounts[]` with read/write sparklines (calls Phase 1 range endpoint with `mount=` selector).
- [ ] Storage row click dispatches `cluster:node-drawer-open` with `{nodeId, focus: 'disk'}`.
- [ ] Overflow panel: 2 rows (lockwood + lomax). State pill, `since` timestamp, free-disk bar with 50% threshold tick.
- [ ] 24-cell activity strip (1h per cell) driven by existing `events[]` in overflow-reserve payload.
- [ ] ⚠ chip on row when free < 50%.
- [ ] Yellow-banner fallback: consumes `status: 'yellow'` + `stale_since` from Phase 1 cache; panel shows banner + last-good values.

### Phase 5: Drill-down drawer

**Status:** 🚧 in_progress
**Files:**

- `~/.buildrunner/dashboard/public/js/ws-cluster-drawer.js` (NEW)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — additive, wrapped in `/* === Phase 5: drawer === */` block)

**Blocked by:** Phase 1, Phase 2, Phase 3
**After:** Phase 3

**Deliverables:**

- [ ] Listens for `cluster:node-drawer-open`; hydrates drawer from last SSE snapshot + fetches 60m history.
- [ ] CPU stacked-area chart (~160px, vanilla canvas/SVG) — 4 parallel fetches `metric=cpu_mode&cpu_mode={user|sys|iowait|idle}`.
- [ ] Per-core grid: N mini-bars via `metric=cpu_per_core&core=<i>` (batched).
- [ ] Memory breakdown: `used · cached · buffered · free · swap` stacked bar + numeric readout (from SSE snapshot, no range fetch).
- [ ] Disk section: one row per mount with read/write sparklines using `metric={disk_read|disk_write}&mount=<mountpoint>`.
- [ ] Network section: one row per interface from `interfaces[]` using `metric={net_in|net_out}&interface=<iface>`. Skip if `interfaces[]` empty.
- [ ] Process/jobs table: BR3 jobs inline; process section shows stub hint "install process-exporter to see OS processes" when absent.
- [ ] Action row: `[copy PromQL]`, `[open Prometheus ↗]` (deep-link), `[×]`.
- [ ] Close handlers: Esc keydown, scrim click, × button. Focus trap while open; focus returns to triggering element on close.

### Phase 6: Verification — smoke + Playwright E2E + regression scan

**Status:** not_started
**Files:**

- `~/.buildrunner/dashboard/tests/dashboard-prometheus-panels.spec.mjs` (NEW — flat tree alongside existing `tests/e2e-prometheus-panels.spec.mjs`, runs under `~/.buildrunner/dashboard/playwright.config.mjs`)
- `~/.buildrunner/dashboard/tests/smoke/prometheus-schema.sh` (NEW)

**Blocked by:** Phase 1, Phase 2, Phase 3, Phase 4, Phase 5
**After:** All previous phases

**Deliverables:**

- [ ] Smoke: curl `/api/events/stream` 10s, assert `schema_version: 3` on every node-health + storage-health sample; assert every node in `up` vector has all v3 fields populated at least once in the window.
- [ ] Smoke: curl `/api/prometheus/range` with `metric=cpu_mode&cpu_mode=user`, `metric=disk_read&mount=/`, `metric=net_in&interface=en0&node=muddy` — assert non-empty `data[]`; 400 on missing selector; yellow when Prometheus stubbed offline.
- [ ] Playwright: load `/`, wait for SSE populate, assert 7 `.node-card`, 7 storage rows, 2 overflow rows.
- [ ] Playwright: click first node card → drawer opens with CPU chart + memory breakdown. Esc closes. Focus returns to card.
- [ ] Playwright: other 6 workspaces (Intelligence, Terminal, Builds, Research, Monitor, Cluster) still reachable via sidebar; zero console errors.
- [ ] Playwright: event-log drawer collapsed by default, expands on click.
- [ ] Remove `?prom_v3=1` rollout flag once all assertions green (last deliverable in phase).

## Session Log

_(Populated by /begin)_
