# Build: Cluster Prometheus Integration

role-matrix:
inherit: default-role-matrix
overrides: {}

**Created:** 2026-04-22
**Status:** pending
**Deploy:** web — per-node install scripts; Prometheus via launchd on Lockwood; dashboard auto-deploys via existing Node runtime on port 4400
**Source Plan File:** .buildrunner/plans/spec-cluster-prometheus-integration-plan.md
**Source Plan SHA:** c7041f015d8cd7f8e251c56b21d51208ae42ca6b4be2ebf9abf1df8952b0dc97
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification-cluster-prometheus-integration.md
**Adversarial Review Timestamp:** 2026-04-22T17:33:08Z

## Overview

Replace broken cross-host filesystem reads (`/srv/jimmy/status/*` from Muddy) with a real metrics transport. Host Prometheus on Lockwood (warm reserve — explicitly not the Memory SPOF now that Jimmy owns primary memory/semantic-search). Dashboard UI and panel JS unchanged; only hardware-metric server-side readers swap to Prometheus HTTP queries. BR3-domain data (consensus, adversarial reviews, feature-health domain meaning, build phases, overflow state, backup timestamps) stays on Jimmy's FastAPI.

This spec supersedes the hardware-metric portion of BUILD_cluster-max Phase 14 (self_health.py node-ping loop + `/srv/jimmy/status/nodes/*.json` writers) and provides the real data transport for the hardware-metric panels in BUILD_cluster-max Phase 16. Phase 14's BR3-domain operations (disk-guard, archive-prune, backup-prune, offsite-sync, lancedb-compact, backup-integrity-check) remain in that build's scope.

## Role Matrix (inline YAML — consumed by load-role-matrix.sh at dispatch)

```yaml
role_matrix:
  spec: BUILD_cluster-prometheus-integration
  default_architect: opus-4-7
  default_reviewers: [sonnet-4-6, codex-gpt-5.4]
  default_arbiter: opus-4-7
  phases:
    phase_1:
      bucket: terminal-build
      builder: codex
      codex_model: gpt-5.3-codex
      codex_effort: medium
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: muddy
      context: [~/.buildrunner/scripts, ~/.buildrunner/config, ~/.buildrunner/AGENTS.md]
    phase_2:
      bucket: terminal-build
      builder: codex
      codex_model: gpt-5.3-codex
      codex_effort: medium
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: muddy
      context: [~/.buildrunner/scripts, ~/.buildrunner/config]
    phase_3:
      bucket: backend-build
      builder: codex
      codex_model: gpt-5.4
      codex_effort: medium
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: otis
      context: [~/.buildrunner/dashboard/integrations, ~/.buildrunner/dashboard/tests]
    phase_4:
      bucket: backend-build
      builder: codex
      codex_model: gpt-5.4
      codex_effort: high
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: muddy
      context:
        [
          ~/.buildrunner/dashboard/integrations,
          ~/.buildrunner/dashboard/events.mjs,
          ~/.buildrunner/dashboard/tests,
        ]
      rationale: 'PromQL correctness + merge logic is load-bearing; muddy + high effort for tighter human oversight.'
    phase_5:
      bucket: architecture
      builder: opus-4-7
      codex_model: null
      codex_effort: null
      primary_effort: xhigh
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: muddy
      context:
        [
          .buildrunner/builds/BUILD_cluster-max.md,
          api/routes/dashboard_stream.py,
          core/cluster,
          .buildrunner/decisions.log,
        ]
      rationale: 'Cross-build spec amendment (Phase 14 scope reduction) requires architectural judgment — Opus primary, not Codex.'
    phase_6:
      bucket: qa
      builder: codex
      codex_model: gpt-5.4
      codex_effort: medium
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: otis
      context: [~/.buildrunner/dashboard/tests, ~/.buildrunner/docs, ~/.buildrunner/config]
```

## Parallelization Matrix

| Phase | Key Files                                                                                                                                         | Can Parallel With | Blocked By                                        |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | ------------------------------------------------- |
| 1     | `~/.buildrunner/scripts/install-node-exporter-*.sh`, `install-windows-exporter.ps1`, launchd/systemd templates                                    | 2                 | None                                              |
| 2     | `~/.buildrunner/config/prometheus.yml`, `install-prometheus-lockwood.sh`, `com.br3.prometheus.plist`                                              | 1                 | None                                              |
| 3     | `~/.buildrunner/dashboard/integrations/prometheus-client.mjs` (NEW), `dashboard/tests/integrations-prometheus.spec.mjs` (NEW)                     | —                 | Phase 2; **external: BUILD_cluster-max Phase 16** |
| 4     | `~/.buildrunner/dashboard/integrations/prometheus-metrics.mjs` (NEW), `jimmy-status.mjs` (MODIFY), `events.mjs` (MODIFY), `events-merge.spec.mjs` | —                 | Phase 3                                           |
| 5     | `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY), `api/routes/dashboard_stream.py` (MODIFY), `.buildrunner/decisions.log`                      | —                 | Phase 4                                           |
| 6     | `~/.buildrunner/dashboard/tests/e2e-prometheus-panels.spec.mjs`, `alertmanager.yml.example`, `prometheus-operations.md`, `config/AGENTS.md`       | —                 | Phase 5                                           |

## Phases

### Phase 1: node_exporter Rollout (7 nodes)

**Status:** ✅ COMPLETE
**Bucket:** terminal-build
**Codex model:** gpt-5.3-codex
**Codex effort:** medium
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.3-codex
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** muddy
**Files:**

- `~/.buildrunner/scripts/install-node-exporter-macos.sh` (NEW) — Muddy, Lockwood, Walter, Otis, Lomax
- `~/.buildrunner/scripts/install-node-exporter-linux.sh` (NEW) — Jimmy
- `~/.buildrunner/scripts/install-windows-exporter.ps1` (NEW) — Below
- `~/.buildrunner/config/com.br3.node-exporter.plist.template` (NEW) — launchd template
- `~/.buildrunner/config/br3-node-exporter.service` (NEW) — systemd unit for Jimmy

**Blocked by:** None. Can run in parallel with Phase 2.

**Deliverables:**

- [ ] Install node_exporter on 5 macOS nodes (Muddy, Lockwood, Walter, Otis, Lomax) via pinned release tarball (preferred over Homebrew — user-owned paths); launchd plist enables at boot; bind to `:9100`.
- [ ] Install node_exporter on Jimmy (Ubuntu 24.04) via `apt install prometheus-node-exporter` (upstream package; ships systemd unit `prometheus-node-exporter.service`); bind to `:9100`. If apt version is too old for needed collectors, fall back to pinned binary download.
- [ ] Install windows_exporter on Below via pinned MSI; Windows service auto-start; bind to `:9182`; enable collectors: `cpu, memory, logical_disk, net, os, system, cs` (cs provides `physical_memory_bytes`).
- [ ] Install scripts are idempotent — re-running succeeds without error if already installed.
- [ ] Firewall: allow inbound `:9100` on all 6 nodes (macOS Application Firewall + Ubuntu `ufw`); allow inbound `:9182` on Below (Windows Defender Firewall) — restrict source to LAN subnet `10.0.1.0/24`.
- [ ] Verify: `curl http://10.0.1.{100..104,106}:9100/metrics` and `curl http://10.0.1.105:9182/metrics` all return 200 from Muddy.
- [ ] Document port matrix in `~/.buildrunner/AGENTS.md` or `~/.buildrunner/scripts/AGENTS.md`.

**Success criteria:** All 7 exporters return valid Prometheus exposition format. `node_memory_*`, `node_cpu_*`, `node_filesystem_*` (or `windows_*` equivalents on Below) present.

---

### Phase 2: Prometheus on Lockwood

**Status:** ✅ COMPLETE
**Bucket:** terminal-build
**Codex model:** gpt-5.3-codex
**Codex effort:** medium
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.3-codex
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** muddy
**Files:**

- `~/.buildrunner/scripts/install-prometheus-lockwood.sh` (NEW)
- `~/.buildrunner/config/prometheus.yml` (NEW) — scrape config
- `~/.buildrunner/config/com.br3.prometheus.plist` (NEW) — launchd plist for Lockwood

**Blocked by:** None. Can run in parallel with Phase 1.

**Deliverables:**

- [ ] Install Prometheus 2.x on Lockwood. Prefer pinned release tarball over Homebrew to keep storage/config paths user-owned rather than Homebrew-prefix-dependent. Install to `/Users/byronhudson/.buildrunner/prometheus/` (binary + tsdb + config).
- [ ] launchd plist specifies `ProgramArguments` array with absolute paths (launchd does not expand `~`): `["/Users/byronhudson/.buildrunner/prometheus/prometheus", "--config.file=/Users/byronhudson/.buildrunner/config/prometheus.yml", "--storage.tsdb.path=/Users/byronhudson/.buildrunner/prometheus/data", "--storage.tsdb.retention.time=30d", "--web.listen-address=0.0.0.0:9090"]`.
- [ ] `prometheus.yml` defines job `br3-cluster` using `static_configs` with 7 separate target blocks, each with its own `labels:` map carrying `node: <friendly-name>` (e.g., `{ targets: ["10.0.1.101:9100"], labels: { node: "lockwood" } }`). The default `instance` label (`host:port`) remains for uniqueness; the `node` label is what the dashboard reads.
- [ ] Targets: muddy/lockwood/walter/otis/lomax/jimmy on `:9100`, below on `:9182`.
- [ ] Scrape interval: 15s. Scrape timeout: 10s.
- [ ] launchd plist enabled; survives Lockwood reboot.
- [ ] Query API reachable from Muddy: `curl http://10.0.1.101:9090/api/v1/query?query=up` returns 200.
- [ ] `up{job="br3-cluster"}` returns 1 for all 7 targets (captured in verification log).

**Success criteria:** `up == 1` for 7/7 targets. Retention flag confirmed in running process.

---

### Phase 3: Dashboard Prometheus Client Module

**Status:** not_started
**Bucket:** backend-build
**Codex model:** gpt-5.4
**Codex effort:** medium
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.4
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** otis
**Files:**

- `~/.buildrunner/dashboard/integrations/prometheus-client.mjs` (NEW)
- `~/.buildrunner/dashboard/tests/integrations-prometheus.spec.mjs` (NEW)

**Blocked by:** Phase 2. External: BUILD_cluster-max Phase 16 complete (`~/.buildrunner/dashboard/integrations/` directory must exist).

**Deliverables:**

- [ ] `prometheus-client.mjs` exports `queryInstant(promql)` returning `[{node, value, timestamp}]`.
- [ ] `prometheus-client.mjs` exports `queryRange(promql, {startSec, endSec, stepSec})` returning `[{node, samples: [{t, v}]}]`.
- [ ] Node-label extraction: prefer the `node` label from the scrape config. If absent, fall back to looking up the `instance` against `~/.buildrunner/cluster.json`. If neither maps, pass through the raw `instance` string as the node identifier.
- [ ] `cluster.json` schema dependency: reader walks `.nodes.*.host` to build an `ip → friendly` map. If `cluster.json` is missing or unreadable, fall back to identity mapping and log once at startup.
- [ ] HTTP timeout: 5s. On timeout or non-200: return empty array.
- [ ] Rate-limited warning log: an in-module counter suppresses duplicate `[prometheus-client] unreachable` warnings to one emission per 60s window. Tested by firing 100 synthetic failures → exactly 1 `console.warn` call.
- [ ] Prometheus host resolved from env `BR3_PROMETHEUS_URL` with fallback `http://10.0.1.101:9090` (IP, not hostname).
- [ ] Response shape: `{internal_schema_version: 1, data: [...], collected_at: ISO8601, source: "prometheus"}`. Named `internal_schema_version` to avoid conflation with SSE event `schema_version` used by `events.mjs` in Phase 4.
- [ ] Test: mocked Prometheus instant response → correct normalization.
- [ ] Test: mocked Prometheus range response → correct normalization + `node`-label preferred over `instance`.
- [ ] Test: `instance` present but no `node` label and no `cluster.json` match → raw `instance` passes through.
- [ ] Test: `cluster.json` missing → identity-mapped labels and single startup warning.
- [ ] Test: Prometheus unreachable → returns empty array; no exception propagates.
- [ ] Test: 100 consecutive unreachable responses emit exactly one `console.warn`.

**Success criteria:** `node --test` passes. Live smoke from Muddy against Lockwood returns non-empty data for `up` query.

---

### Phase 4: Panel Data-Source Rewrites (Hybrid: Prometheus + Jimmy FastAPI)

**Status:** not_started
**Bucket:** backend-build
**Codex model:** gpt-5.4
**Codex effort:** high
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.4
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** muddy
**Rationale:** PromQL correctness and SSE event-merge logic are load-bearing — adversarial review flagged 4 PromQL blockers on this phase during spec review. High effort + muddy (command node) for tighter oversight.
**Files:**

- `~/.buildrunner/dashboard/integrations/prometheus-metrics.mjs` (NEW)
- `~/.buildrunner/dashboard/integrations/jimmy-status.mjs` (MODIFY — created by BUILD_cluster-max Phase 16)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — created/modified by BUILD_cluster-max Phase 16)
- `~/.buildrunner/dashboard/tests/events-merge.spec.mjs` (NEW)

**Blocked by:** Phase 3.

**Deliverables:**

- [ ] `prometheus-metrics.mjs` emits `node-health` hardware fields per node using these exact PromQL expressions:
  - `cpu_pct`: `100 - (avg by (node) (rate(node_cpu_seconds_total{mode="idle"}[1m])) * 100)` — averages across cores, converts idle→used, returns 0–100.
  - `ram_pct`: `(1 - node_memory_MemAvailable_bytes / node_memory_MemTotal_bytes) * 100` — used-memory percentage.
  - `uptime_sec`: `node_time_seconds - node_boot_time_seconds`.
  - Below (windows_exporter) equivalents:
    - `cpu_pct`: `100 - (avg by (node) (rate(windows_cpu_time_total{mode="idle"}[1m])) * 100)`
    - `ram_pct`: `(1 - windows_os_physical_memory_free_bytes / windows_cs_physical_memory_bytes) * 100`
    - `uptime_sec`: `windows_system_system_up_time` (verify unit at install time).
- [ ] `prometheus-metrics.mjs` emits `storage-health` hardware fields: `disk_total_bytes` from `node_filesystem_size_bytes{mountpoint=~"^/srv/jimmy$|^/$",fstype!~"tmpfs|overlay"}`, `disk_free_bytes` from `node_filesystem_avail_bytes` with same selector. Regex is **anchored** (`^...$`) and excludes transient filesystems.
- [ ] `prometheus-metrics.mjs` emits `overflow-reserve` hardware field: 30-day `disk_free_bytes` trend for Lockwood and Lomax via `queryRange` with `stepSec=3600` (~720 samples per series; no post-query downsampling). For first 300s after process start, `disk_free_trend` = `null` — panels treat null as "collecting" and show a skeleton.
- [ ] Cadence + dual-rate caching mechanism:
  - `node-health`: fresh query every 5s.
  - `storage-health`: fresh query every 60s.
  - `overflow-reserve`: instant-state emitted every 10s using a **cached** `disk_free_trend` value that refreshes via `queryRange` on a separate 300s `setInterval`. First-run safety: `cachedTrend = null` until first refresh completes.
- [ ] Fields explicitly NOT emitted by `prometheus-metrics.mjs` (stay on Jimmy FastAPI via `jimmy-status.mjs`): Jimmy extras (`lancedb_query_depth`, `reranker_queue`, `context_api_p95_ms`), Below GPU/VRAM fields (from Ollama daemon), `dirs.*` per-directory sizes, `backup_timestamps`, `offsite_sync`, `cron_timestamps`, `backups_paused`, `disk_guard.pct`, overflow `nodes.*.state`, overflow `events`, overflow `freq`.
- [ ] `jimmy-status.mjs` modified to stop emitting the hardware fields listed above — returns only its BR3-domain slice.
- [ ] `events.mjs` merges emissions from both integrations per topic before SSE broadcast; emitted events carry `schema_version: 2` and preserve existing field shapes so panel JS is unchanged.
- [ ] Graceful degradation: if Prometheus unreachable, hardware fields absent from the merged event; panel renders BR3-domain fields green and hardware tiles as yellow with reason `"Prometheus offline"`.
- [ ] Tests: merge with both sources present; merge with Prometheus missing; merge with jimmy-status missing.

**Success criteria:** Dashboard at http://localhost:4400 renders with live CPU/RAM/uptime/disk data from Prometheus. Stopping Prometheus on Lockwood degrades hardware tiles to yellow without crashing panels; FastAPI-backed tiles remain green.

---

### Phase 5: Delete Superseded Writers + Amend BUILD_cluster-max Phase 14

**Status:** not_started
**Bucket:** architecture
**Primary effort:** xhigh
**Architect:** Opus 4.7
**Builder:** Opus 4.7 `effort:xhigh` (NOT Codex — cross-build spec amendment requires architectural judgment)
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh` (self-arbitrate pattern for architecture bucket; matches default-role-matrix)
**Assigned node:** muddy
**Rationale:** Amending BUILD_cluster-max Phase 14 scope + deleting Python collector functions is architectural cleanup, not mechanical coding.
**Files:**

- `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY — Phase 14 deliverables reduced)
- `api/routes/dashboard_stream.py` (MODIFY — remove `_collect_node_health` + `_collect_storage_health`)
- `.buildrunner/decisions.log` (APPEND)
- Any `core/cluster/self_health.py` that exists (DELETE — confirmed absent in current repo)

**Blocked by:** Phase 4.

**Deliverables:**

- [ ] Amend `BUILD_cluster-max.md` Phase 14: remove deliverables for `self_health.py` (node-ping loop + `~/.buildrunner/health/latest.json`), remove `/srv/jimmy/status/nodes/*.json` write path, remove `/srv/jimmy/status/storage-health.json` write path.
- [ ] Phase 14 retained deliverables (explicitly unchanged): `disk-guard.sh`, `archive-prune.sh`, `backup-prune.sh`, `offsite-sync.sh`, `lancedb-compact.sh`, `backup-integrity-check.sh`, `model-update.sh`, `auto_rebalance.py`, all related `.service|.timer` units, retention matrix in AGENTS.md.
- [ ] Add note to Phase 14 header: "Hardware metrics served by Prometheus — see BUILD_cluster-prometheus-integration. Phase 14 scope is BR3-domain operations + backup/retention only."
- [ ] **Delete** the `_collect_node_health` function and the `_collect_storage_health` function in `api/routes/dashboard_stream.py` in their entirety — both functions' sole purpose is reading hardware-metric JSON files and they have no BR3-domain branches to preserve. Remove their callers and any now-unreferenced imports.
- [ ] Append `.buildrunner/decisions.log`: `Phase 14 hardware-metric writers superseded by Prometheus on Lockwood; Phase 14 scope reduced; see BUILD_cluster-prometheus-integration.`
- [ ] Verify grep cleanup using `git grep` with pathspec exclusions:
  - `git grep -n "/srv/jimmy/status/nodes/" -- ':!.buildrunner/plans/' ':!.buildrunner/builds/' ':!.buildrunner/adversarial-reviews/' ':!.buildrunner/decisions.log'` returns zero.
  - `git grep -n "/srv/jimmy/status/storage-health.json" -- ':!.buildrunner/plans/' ':!.buildrunner/builds/' ':!.buildrunner/adversarial-reviews/' ':!.buildrunner/decisions.log'` returns zero.

**Success criteria:** Repo grep proof as above. Phase 14 reads as a coherent reduced-scope phase. `dashboard_stream.py` no longer references hardware-metric file paths.

---

### Phase 6: Verification + Alertmanager Placeholder + Runbook

**Status:** not_started
**Bucket:** qa
**Codex model:** gpt-5.4
**Codex effort:** medium
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.4
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** otis
**Files:**

- `~/.buildrunner/dashboard/tests/e2e-prometheus-panels.spec.mjs` (NEW)
- `~/.buildrunner/config/alertmanager.yml.example` (NEW — not active)
- `~/.buildrunner/docs/prometheus-operations.md` (NEW)
- `~/.buildrunner/config/AGENTS.md` (NEW if absent, else MODIFY)

**Blocked by:** Phase 5.

**Deliverables:**

- [ ] E2E test: boot dashboard via its existing entrypoint; open SSE connection; assert `node-health` event received within 15s carrying `schema_version: 2` and at least `cpu_pct` populated for all 7 nodes.
- [ ] E2E test: stop Prometheus on Lockwood via `ssh byronhudson@10.0.1.101 "launchctl bootout gui/$(id -u) /Users/byronhudson/Library/LaunchAgents/com.br3.prometheus.plist"`; within 60s, assert `node-health` event carries hardware tiles with `status: "yellow"` and `reason: "Prometheus offline"` while non-hardware tiles remain green. Test teardown re-loads the plist via `launchctl bootstrap` to leave Lockwood clean.
- [ ] E2E test: wait at least 305s after Prometheus is up, then assert `overflow-reserve` event carries `disk_free_trend` for Lockwood and Lomax with ≥1 sample each.
- [ ] Runbook sections: "add a new scrape target", "inspect 30d retention", "query from CLI with `curl`", "restart Prometheus on Lockwood", "what to do if `up` is 0".
- [ ] Alertmanager example config: 3 commented rules (disk-free <15%, `up == 0` >5m, memory >90% sustained 10m). Installation steps in runbook as "future work — not installed".
- [ ] Update `~/.buildrunner/config/AGENTS.md` with Prometheus operational notes: file paths, launchd labels, retention config, upgrade procedure.
- [ ] Post-completion smoke: `curl -s http://10.0.1.101:9090/api/v1/query?query=up | jq '.data.result | length'` returns `7`.

**Success criteria:** All three E2E tests pass. Runbook covers the 5 listed scenarios. `alertmanager.yml.example` exists but no Alertmanager process runs.

---

## Out of Scope (explicit)

- Alertmanager deployment (placeholder config only; follow-up build)
- Grafana (explicitly rejected — BR3 dashboard is the UI)
- Jimmy-domain data HTTP transport (non-hardware BR3-domain fields still flow via `jimmy-status.mjs` reading `/srv/jimmy/status/*.json` which Phase 16 degrades gracefully; separate follow-up)
- Prometheus HA / federation (single Lockwood instance; acceptable at homelab scale)
- Custom BR3 metrics exposure via `/metrics` on Jimmy FastAPI (future)
- pushgateway (rejected; pull-only scrape model)
- Schema-version rollout across all status files
- launchd hardening (restart-on-failure policy, structured log rotation)
- Reverse proxy / auth in front of Prometheus

## Key Design Decisions

1. **Prometheus on Lockwood, not Jimmy.** Lockwood is warm reserve overflow (per cluster.json 2026-04-22). Hosting Prometheus there means (a) if Jimmy dies, Prometheus still sees it go down; (b) we don't further load the Memory/research/FastAPI SPOF.
2. **Hybrid data sources per panel, not two dashboards.** Each reader combines Prometheus hardware data with Jimmy FastAPI BR3-domain data server-side, then SSE-broadcasts a single unified event shape. Panel JS unchanged.
3. **Prometheus owns only numeric hardware metrics.** The BR3 domain stays on Jimmy FastAPI.
4. **No Alertmanager yet.** Placeholder config + runbook mention is the right amount now.
5. **Phase 14 scope reduction is codified in this spec, not assumed.**
6. **node_exporter for Linux/macOS, windows_exporter for Below.** No custom collectors in scope.
7. **Phase 16 contingency.** Phases 1 and 2 have no Phase 16 dependency — they can merge to main and run in production with zero consumers until Phase 3 kicks off.
8. **PromQL correctness is load-bearing.** The spec-review blockers were all PromQL/exporter-config correctness issues. Future panel additions should follow the same patterns.

## Session Log

(Updated by `/begin` as phases execute.)
