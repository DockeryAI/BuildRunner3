# Build: cluster-activation

**Created:** 2026-04-21
**Last Revised:** 2026-04-21 (Revision 3 — cluster-max authoring-contract conformance)
**Status:** Phases 1-4 Complete — Phase 5 In Progress
**Deploy:** local — BR3 framework internals; no user-facing deploy target.
**Supersedes:** closes the 10 post-cutover gaps in `BUILD_cluster-max`. Consumes the infrastructure cluster-max shipped (RuntimeRegistry, codex-bridge, feature flags, dashboard) and makes `/begin` + `/autopilot` actually use it.
**Source Plan File:** .buildrunner/plans/cluster-activation-plan.md
**Source Plan SHA:** a976080ea7cab7af7db658fa5944245b81239f6ca0f11c4461adeb51a88f42b3
**Adversarial Review Verdict:** BYPASSED:.buildrunner/adversarial-reviews/cluster-activation-R3-user-override.json

## Overview

Close the orchestration gaps found in the post-cluster-max-cutover audit. Make every BR3 build, fix, and planning session automatically dispatch to the correct LLM/node across the cluster (Claude, Codex, Below/Ollama, Otis, Walter, Lomax, Jimmy) without manual invocation. Closes 10 identified gaps: Role Matrix is prose-only (unparseable), `/context/codex` router not mounted, dual bash/Python dispatch paths, dead adversarial/cache flags, idle cluster-daemon, orphaned node-matrix, missing Walter plist deploy, missing Lomax overflow trigger, zero dispatch telemetry, stale shadow-metrics artifact.

Revision 2 addresses adversarial review from `phase-0-20260421T204226Z.json` (1-round cap, BLOCKED → user OVERRIDE authorized). Structural blocker (Phase 1 context.py double-init) fixed via router extraction into `api/services/context_api_standalone.py`. All 7 notes resolved.

Revision 3 (2026-04-21) corrects authoring-contract drift: the Revision 2 review citation pointed at `spec-draft-plan.md` (research-library remediation), not this spec — cluster-activation was never reviewed against the BUILD_cluster-max authoring contract. R3 adds per-phase `Codex model` / `Codex effort` / builder / reviewer / arbiter lines, an inline `role_matrix` YAML block, the `Codex Model` column in the Parallelization Matrix, and a mandatory `Claude Review` trigger per phase — matching the format used by cluster-max Phases 0–15. No deliverables, files, or phase boundaries changed.

## Role Matrix (inline YAML — consumed by Phase 3 load-role-matrix.sh)

```yaml
role_matrix:
  spec: BUILD_cluster-activation
  default_architect: opus-4-7
  default_reviewers: [sonnet-4-6, codex-gpt-5.4]
  default_arbiter: opus-4-7
  phases:
    phase_1:
      builder: codex
      codex_model: gpt-5.4
      codex_effort: medium
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: muddy
      context: [core/cluster, api/routes, core/runtime]
    phase_2:
      builder: codex
      codex_model: gpt-5.3-codex
      codex_effort: medium
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: otis
      context: [core/runtime, core/cluster]
    phase_3:
      builder: codex
      codex_model: gpt-5.3-codex
      codex_effort: medium
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: otis
      context: [core/cluster, core/runtime]
    phase_4:
      builder: codex
      codex_model: gpt-5.4
      codex_effort: low
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: muddy
      context: [core/cluster, core/runtime]
    phase_5:
      builder: codex
      codex_model: gpt-5.3-codex
      codex_effort: high
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: otis
      context: [core/cluster]
    phase_6:
      builder: codex
      codex_model: gpt-5.4
      codex_effort: high
      reviewers: [sonnet-4-6, codex-gpt-5.4]
      arbiter: opus-4-7
      assigned_node: muddy
      context: [core/cluster, core/runtime, ui/dashboard]
```

## Parallelization Matrix

| Phase | Key Files                                                                                                                                            | Can Parallel With | Blocked By                 | Codex Model   |
| ----- | ---------------------------------------------------------------------------------------------------------------------------------------------------- | ----------------- | -------------------------- | ------------- |
| 1     | schemas/role-matrix.schema.yaml, api/routes/context.py, api/services/context_api_standalone.py, api/node_semantic.py, scripts/migrate-role-matrix.py | 2                 | —                          | gpt-5.4       |
| 2     | scripts/runtime-dispatch.sh, below-route.sh, runtime_registry.py, autopilot.md (api/summarize delete only)                                           | 1                 | —                          | gpt-5.3-codex |
| 3     | begin.md, autopilot.md, load-role-matrix.sh, load-cluster-flags.sh                                                                                   | —                 | 1, 2                       | gpt-5.3-codex |
| 4     | cross_model_review.py, cache_policy.py, begin.md, autopilot.md                                                                                       | —                 | 3 (same skill files)       | gpt-5.4       |
| 5     | cluster-daemon-config.json, LaunchAgent plists, autopilot.md, overflow-shard-watcher.sh, cluster-check.sh                                            | —                 | 4 (same autopilot.md)      | gpt-5.3-codex |
| 6     | event_schemas.py, runtime_registry.py, cache_policy.py, cross_model_review.py, codex-bridge.sh, dashboard panels                                     | —                 | 3, 4, 5 (needs emit sites) | gpt-5.4       |

**Parallelizable groupings:**

- Phases 1 and 2 run in parallel.
- Phases 3, 4, 5 are strictly serial (all contend on `/begin.md` and `/autopilot.md`).
- Phase 6 serial after 5.

## Phases

### Phase 1: Foundation — Role Matrix schema + context router extraction + :4500 mount

**Status:** ✅ COMPLETE
**Codex model:** gpt-5.4
**Codex effort:** medium
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.4
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** Muddy
**Files:**

- `.buildrunner/schemas/role-matrix.schema.yaml` (NEW)
- `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY — append `role_matrix` YAML block)
- `scripts/migrate-role-matrix.py` (NEW)
- `api/routes/context.py` (MODIFY — remove module-level `app = create_app(...)`. Keep ONLY APIRouter.)
- `api/services/context_api_standalone.py` (NEW — standalone entrypoint)
- `api/node_semantic.py` (MODIFY — mount `context_router`)
- `tests/cluster/test_role_matrix_schema.py` (NEW)
- `tests/cluster/test_context_router_no_side_effects.py` (NEW)
- `tests/integration/test_context_codex_live.py` (NEW)

**Blocked by:** None

**Deliverables:**

- [x] Define role_matrix YAML schema (phase_N: builder, reviewers, context, assigned_node)
- [x] Migration script converts prose Role Matrix in `BUILD_cluster-max.md` to YAML block
- [x] Append `role_matrix` YAML block to `BUILD_cluster-max.md`
- [x] Extract APIRouter: remove module-level `app = create_app(role='context-api')` from `api/routes/context.py`
- [x] Move standalone app bootstrap to `api/services/context_api_standalone.py` with `if __name__ == "__main__"` guard
- [x] Import and mount `context_router` in `api/node_semantic.py`
- [x] Unit test asserts `import api.routes.context` does not instantiate FastAPI app
- [x] Smoke test: `curl http://10.0.1.106:4500/context/codex?phase=2` returns HTTP 200
- [x] Document role_matrix schema in `core/cluster/AGENTS.md`

**Success Criteria:** YAML parser extracts `builder=codex` for phase_2. `curl :4500/context/codex` returns HTTP 200 with JSON payload. No duplicate FastAPI app detectable via `importlib` introspection.

**Claude Review (mandatory before Phase 1 marked complete):**

- Reviewer: `claude-opus-4-7` (Muddy) + `codex-gpt-5.4` (secondary)
- Trigger: `/review --phase 1 --target ".buildrunner/schemas/role-matrix.schema.yaml,scripts/migrate-role-matrix.py,api/routes/context.py,api/services/context_api_standalone.py,api/node_semantic.py,core/cluster/AGENTS.md"`
- Required findings: (1) `import api.routes.context` has zero side effects; (2) YAML schema validates against all cluster-max phases 0–15; (3) standalone bootstrap behaves byte-identically to prior module-level app; (4) no duplicate FastAPI app registered on `:4500`; (5) AGENTS.md documents the schema within 500-byte staged-append budget.

---

### Phase 2: Unified dispatcher — bash/Python bridge + flag cleanup

**Status:** ✅ COMPLETE
**Codex model:** gpt-5.3-codex
**Codex effort:** medium
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.3-codex (terminal-heavy: shell scripts, CLI entry, flag alias shim)
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** Otis
**Files:**

- `scripts/runtime-dispatch.sh` (NEW)
- `core/runtime/runtime_registry.py` (MODIFY — add `if __name__ == "__main__"` CLI entry)
- `~/.buildrunner/scripts/below-route.sh` (MODIFY — thin wrapper around runtime-dispatch.sh)
- `AGENTS.md` (MODIFY — canonical flag name)
- `~/.claude/commands/autopilot.md` (MODIFY — delete dead `$BELOW_URL/api/summarize` call at line 755)
- `tests/cluster/test_runtime_dispatch_cli.py` (NEW)
- `tests/integration/test_bash_to_python_dispatch.py` (NEW)

**Blocked by:** None (file-independent of Phase 1)

**Deliverables:**

- [x] Add CLI entry to `runtime_registry.py`: `python -m core.runtime.runtime_registry execute <builder> <spec_path>`
- [x] Ship `scripts/runtime-dispatch.sh` that shells into CLI entry
- [x] Refactor `below-route.sh` to call `runtime-dispatch.sh` instead of direct Ollama curl
- [x] Canonicalize flag: `BR3_LOCAL_ROUTING` canonical; `BR3_RUNTIME_OLLAMA` aliased one release, then removed. Document in `AGENTS.md`.
- [x] Delete dead `$BELOW_URL/api/summarize` call at `autopilot.md:755`. Auto-triage out of scope.
- [x] Unit tests for CLI entry (success + unknown builder + malformed spec)
- [x] Integration test: bash `runtime-dispatch.sh claude test-spec.md` returns Claude output

**Success Criteria:** `below-route.sh` contains no direct Ollama curl. Bash dispatch and Python workflows produce identical outputs for the same spec. Grep for `api/summarize` in `autopilot.md` returns zero hits.

**Claude Review (mandatory before Phase 2 marked complete):**

- Reviewer: `claude-opus-4-7` (Muddy) + `codex-gpt-5.4` (secondary)
- Trigger: `/review --phase 2 --target "scripts/runtime-dispatch.sh,core/runtime/runtime_registry.py,~/.buildrunner/scripts/below-route.sh,AGENTS.md,~/.claude/commands/autopilot.md"`
- Required findings: (1) bash + Python dispatch paths produce byte-identical outputs for the same spec; (2) `BR3_RUNTIME_OLLAMA` alias shim documented with removal release; (3) zero direct Ollama curl in any shell entrypoint; (4) autopilot dead code fully removed (no orphaned refs); (5) CLI exit codes match runtime contract (0 success, 2 unknown builder, 3 malformed spec).

---

### Phase 3: Orchestrator wiring — /begin + /autopilot dispatch per phase

**Status:** ✅ COMPLETE
**Codex model:** gpt-5.3-codex
**Codex effort:** medium
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.3-codex (terminal-heavy: skill prose + bash load scripts + dispatch bridge wiring)
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** Otis
**Files:**

- `~/.claude/commands/begin.md` (MODIFY)
- `~/.claude/commands/autopilot.md` (MODIFY)
- `scripts/load-role-matrix.sh` (NEW)
- `scripts/load-cluster-flags.sh` (NEW)
- `~/.buildrunner/scripts/runtime-dispatch.sh` (MODIFY — call `codex-bridge.sh` when builder==codex)
- `tests/e2e/orchestrator-dispatch.spec.ts` (NEW)

**Blocked by:** Phase 1 (role_matrix schema), Phase 2 (runtime-dispatch.sh)

**Deliverables:**

- [x] Ship `load-role-matrix.sh` — args: `<spec_path> <phase_num>` → prints `builder=codex` etc.
- [x] Ship `load-cluster-flags.sh` — sources `feature-flags.yaml`, exports all cluster flags
- [x] Add role_matrix lookup to `/begin` at start of each phase loop
- [x] Add role_matrix lookup to `/autopilot` at start of each phase loop
- [x] Dispatch branch: if `builder != claude`, call `runtime-dispatch.sh $builder $spec`
- [x] Wire `codex-bridge.sh` invocation inside `runtime-dispatch.sh` when builder==codex
- [x] Phase-complete assertion: `builder_in_matrix == builder_that_ran`; fail phase if mismatch
- [x] E2E smoke test: `/begin` on throwaway spec with `phase_2.builder: codex`, assert Codex ran

**Success Criteria:** `/begin BUILD_cluster-max` and `/autopilot BUILD_cluster-max` dispatch Phase 2 to Codex automatically. No manual `/codex-do`.

**Claude Review (mandatory before Phase 3 marked complete):**

- Reviewer: `claude-opus-4-7` (Muddy) + `codex-gpt-5.4` (secondary)
- Trigger: `/review --phase 3 --target "~/.claude/commands/begin.md,~/.claude/commands/autopilot.md,scripts/load-role-matrix.sh,scripts/load-cluster-flags.sh,~/.buildrunner/scripts/runtime-dispatch.sh"`
- Required findings: (1) role-matrix lookup fires exactly once per phase loop (no duplicate dispatch); (2) `builder_in_matrix == builder_that_ran` assertion cannot be skipped; (3) codex-bridge.sh called BEFORE any Codex dispatch (context injected); (4) flag load is idempotent and safe to re-source; (5) E2E smoke exercises both `/begin` and `/autopilot` paths.

---

### Phase 4: Flag enforcement at skill entry

**Status:** ✅ COMPLETE
**Codex model:** gpt-5.4
**Codex effort:** low
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.4
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** Muddy
**Files:**

- `core/review/cross_model_review.py` (MODIFY — read `BR3_ADVERSARIAL_3WAY`)
- `core/cache/cache_policy.py` (MODIFY — gate on `BR3_CACHE_BREAKPOINTS`)
- `~/.claude/commands/begin.md` (MODIFY — source `load-cluster-flags.sh` at top of phase loop)
- `~/.claude/commands/autopilot.md` (MODIFY — same)
- `tests/cluster/test_adversarial_3way_flag.py` (NEW)
- `tests/cluster/test_cache_breakpoints_flag.py` (NEW)

**Blocked by:** Phase 3 (same `/begin`, `/autopilot` files)

**Deliverables:**

- [x] Add `BR3_ADVERSARIAL_3WAY` branch to `cross_model_review.py`; flag on → `run_three_way_review()`
- [x] Add `BR3_CACHE_BREAKPOINTS` gate to `cache_policy.py`; flag on → emit breakpoints
- [x] Call `load-cluster-flags.sh` at top of `/begin` phase loop
- [x] Call `load-cluster-flags.sh` at top of `/autopilot` phase loop
- [x] Unit test: `BR3_ADVERSARIAL_3WAY=on` runs 3-way with Claude+Codex+Below
- [x] Unit test: `BR3_CACHE_BREAKPOINTS=off` emits zero breakpoints
- [x] Smoke test: flag toggle actually changes review round composition

**Success Criteria:** Flipping `BR3_ADVERSARIAL_3WAY` in `feature-flags.yaml` measurably changes review behavior. Same for `BR3_CACHE_BREAKPOINTS`.

**Claude Review (mandatory before Phase 4 marked complete):**

- Reviewer: `claude-opus-4-7` (Muddy) + `codex-gpt-5.4` (secondary)
- Trigger: `/review --phase 4 --target "core/review/cross_model_review.py,core/cache/cache_policy.py,~/.claude/commands/begin.md,~/.claude/commands/autopilot.md"`
- Required findings: (1) flag read occurs exactly once per entry point; (2) flag off = zero behavior change from pre-Phase-4; (3) 3-way branch respects `BR3_MAX_REVIEW_ROUNDS=1` cap; (4) cache_policy.py breakpoint emission honors 3-breakpoint contract from cluster-max Phase 8; (5) flag names match `feature-flags.yaml` canonical keys exactly.

---

### Phase 5: Cluster node activation — Otis + Walter + Lomax

**Status:** ✅ COMPLETE
**Codex model:** gpt-5.3-codex
**Codex effort:** high
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.3-codex (terminal-heavy: LaunchAgent/LaunchDaemon plists, launchctl, shell watchers, cluster health probes)
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** Otis
**Files:**

- `~/.buildrunner/cluster-daemon-config.json` (MODIFY — `auto_dispatch: true`)
- `~/Library/LaunchAgents/com.br3.cluster-daemon.plist` (NEW)
- `~/Library/LaunchDaemons/com.br3.walter-sentinel.plist` (NEW)
- `~/.claude/commands/autopilot.md` (MODIFY — Walter `/api/coverage` gate)
- `scripts/overflow-shard-watcher.sh` (NEW)
- `~/Library/LaunchAgents/com.br3.overflow-shard-watcher.plist` (NEW)
- `~/.buildrunner/scripts/cluster-check.sh` (MODIFY — `walter-sentinel` health)
- `tests/e2e/cluster-daemon-autodispatch.spec.ts` (NEW)
- `tests/e2e/overflow-shard.spec.ts` (NEW)

**Blocked by:** Phase 4 (same `/autopilot.md` file)

**Deliverables:**

- [x] Flip `cluster-daemon-config.json` → `auto_dispatch: true`
- [x] Ship LaunchAgent plist for `cluster-daemon.mjs`; `launchctl load`; verify runs at boot
- [x] Add `assigned_node` field to role_matrix YAML schema
- [x] Make `/autopilot` consult `node-matrix.mjs` (remove inline hardcode at autopilot.md:126)
- [x] Add Walter `/api/coverage` gate to `/autopilot`. Gate blocks at phase start only. Mid-phase outages continue with stale coverage. Checkpoint-resume out of scope.
- [x] Unconditionally deploy `com.br3.walter-sentinel.plist` LaunchDaemon via `launchctl load`. Separately verify with `launchctl list | grep walter-sentinel`.
- [x] Add `walter-sentinel` health check to `cluster-check.sh`
- [x] Ship `overflow-shard-watcher.sh`: 30s poll, 60s cooldown after dispatch, 3 shards/hour cap
- [x] Resolve Lomax build-status ambiguity at `/begin:454-465`: change non-blocking warn to blocking error
- [x] E2E test: daemon auto-dispatches ready build to Otis
- [x] E2E test: Walter queue depth >2 triggers Lomax shard within 60s; cooldown prevents re-dispatch for 60s

**Success Criteria:** Boot Mac. `cluster-daemon` starts, polls, dispatches next ready build to Otis. `launchctl list | grep walter-sentinel` returns loaded. `/autopilot` run with Walter offline blocks with same message as `/begin`. 30s/60s/3-per-hour enforced by test harness.

**Claude Review (mandatory before Phase 5 marked complete):**

- Reviewer: `claude-opus-4-7` (Muddy) + `codex-gpt-5.4` (secondary)
- Trigger: `/review --phase 5 --target "~/.buildrunner/cluster-daemon-config.json,~/Library/LaunchAgents/com.br3.cluster-daemon.plist,~/Library/LaunchDaemons/com.br3.walter-sentinel.plist,~/.claude/commands/autopilot.md,scripts/overflow-shard-watcher.sh,~/Library/LaunchAgents/com.br3.overflow-shard-watcher.plist,~/.buildrunner/scripts/cluster-check.sh"`
- Required findings: (1) LaunchAgent vs LaunchDaemon scope correct (user vs system); (2) `KeepAlive` and `RunAtLoad` plist keys set correctly for boot persistence; (3) overflow-shard-watcher cooldown + cap enforceable (not trivially bypassable via manual restart); (4) Lomax blocking change documented in `core/cluster/AGENTS.md`; (5) Walter gate does NOT block mid-phase (checkpoint-resume out of scope); (6) hardcoded node path at autopilot.md:126 fully removed.

---

### Phase 6: Dispatch telemetry + feature-health dashboard

**Status:** not_started
**Codex model:** gpt-5.4
**Codex effort:** high
**Architect:** Opus 4.7
**Builder:** Codex gpt-5.4
**Reviewers (parallel):** Sonnet 4.6 + Codex gpt-5.4
**Arbiter (on disagreement):** Opus 4.7 `effort:xhigh`
**Assigned node:** Muddy
**Files:**

- `core/telemetry/event_schemas.py` (MODIFY — add 4 new event types)
- `core/runtime/runtime_registry.py` (MODIFY — emit `runtime_dispatched`)
- `core/cache/cache_policy.py` (MODIFY — emit `cache_hit`)
- `core/review/cross_model_review.py` (MODIFY — emit `adversarial_review_ran`)
- `scripts/br-emit-event.sh` (NEW)
- `~/.buildrunner/scripts/codex-bridge.sh` (MODIFY — emit `context_bundle_served`)
- `api/routes/dashboard_stream.py` (MODIFY — add `feature-health` WS topic)
- `ui/dashboard/panels/feature-health.js` (NEW — 15 tiles)
- `ui/dashboard/index.html` (MODIFY)
- `ui/dashboard/app.js` (MODIFY)
- `.buildrunner/runtime-shadow-metrics.md` (DELETE — orphaned)
- `tests/telemetry/test_new_event_types.py` (NEW)
- `tests/e2e/feature-health-panel.spec.ts` (NEW)

**Blocked by:** Phases 3, 4, 5

**Feature-health 15 tiles:**

1. Role Matrix dispatch (green if any dispatch in last hour)
2. RuntimeRegistry health (red if <90% success in 24h)
3. 3-way adversarial review (yellow if flag off; green if on+firing)
4. Cache breakpoints (red if flag on but zero hits in 24h)
5. Codex bridge (red if any Codex dispatch lacks preceding bundle)
6. Auto-context Jimmy /retrieve (green if healthy)
7. Local routing Below (yellow if zero dispatches in 24h)
8. Otis dispatch (green if daemon loaded+dispatching)
9. Walter gate (red if stale >5min)
10. Lomax shard (green if shards firing when needed)
11. Cluster daemon (binary loaded/not-loaded)
12. Node matrix consulted (yellow if hardcoded path still used)
13. Dispatch log writer (red if >24h stale)
14. Context bundle parity (green if Claude+Codex+Below within 10%)
15. Adversarial review cap (red if any build exceeds 1 round)

**Deliverables:**

- [ ] Add event types: `runtime_dispatched`, `cache_hit`, `context_bundle_served`, `adversarial_review_ran` (reuse metadata JSON column)
- [ ] Emit `runtime_dispatched` from `runtime_registry.py` on every `execute()`
- [ ] Ship `br-emit-event.sh` CLI wrapper
- [ ] Emit `context_bundle_served` from `codex-bridge.sh`
- [ ] Emit `adversarial_review_ran` from `cross_model_review.py`
- [ ] Emit `cache_hit` from `cache_policy.py`
- [ ] Add `feature-health` WS topic to `dashboard_stream.py`
- [ ] Ship `ui/dashboard/panels/feature-health.js` with 15 tiles
- [ ] Delete `.buildrunner/runtime-shadow-metrics.md`
- [ ] E2E: run phase, verify `runtime_dispatched` lands in panel within 5s

**Success Criteria:** Open dashboard at :4400, run `/autopilot BUILD_cluster-max`. Within seconds, panel shows Phase 2 dispatched to Codex (tile 1 green), context_bundle_served (tile 5 green), adversarial_review_ran (tile 3 green, mode=3-way, pass). All 15 tiles resolve to green/yellow/red — no "unknown".

**Claude Review (mandatory before Phase 6 marked complete):**

- Reviewer: `claude-opus-4-7` (Muddy) + `codex-gpt-5.4` (secondary)
- Trigger: `/review --phase 6 --target "core/telemetry/event_schemas.py,core/runtime/runtime_registry.py,core/cache/cache_policy.py,core/review/cross_model_review.py,scripts/br-emit-event.sh,~/.buildrunner/scripts/codex-bridge.sh,api/routes/dashboard_stream.py,ui/dashboard/panels/feature-health.js,ui/dashboard/index.html,ui/dashboard/app.js"`
- Required findings: (1) emit wrappers never block host code path; (2) zero PII / full-prompt / full-diff leakage in metadata (string-literal scan <256 chars); (3) `telemetry.db` schema backward-compatible (no new columns, metadata JSON only); (4) all 15 tiles resolve to green/yellow/red — no "unknown" state; (5) WS topic respects existing `dashboard_stream.py` subscription contract; (6) `runtime-shadow-metrics.md` deletion does not break any documented workflow; (7) overlap with Phase 15 (cluster-max) observability is additive only — no duplicate emit sites.

---

## Out of Scope

- Supporting >3-way adversarial review
- New dashboard panels beyond `feature-health`
- Migrating `telemetry.db` schema away from Python DDL
- Replacing deleted cost ledger
- Supporting additional cluster nodes beyond current 7
- Re-enabling `shadow_runner.py`
- Cross-project orchestration
- Auto-triage via Below summarize (deleted call)
- Checkpoint-resume for mid-phase Walter outages
- Mid-run recovery for `cluster-daemon` / `overflow-shard-watcher` crashes

---

## Risks & Mitigations

1. **Router extraction temporary broken state** — create `api/services/context_api_standalone.py` first, verify it boots, THEN remove module-level app from `context.py`.
2. **CLI entry to RuntimeRegistry** — needs argparse + asyncio event loop. Reference `core.orchestrator` pattern.
3. **Flag rename migration** — alias `BR3_RUNTIME_OLLAMA` for one release via shim in `load-cluster-flags.sh`, then remove.
4. **LaunchAgent vs LaunchDaemon scope** — `cluster-daemon` + `overflow-shard-watcher` = LaunchAgent (user). `walter-sentinel` = LaunchDaemon (system).
5. **Telemetry event volume** — est. 50–500/day. `telemetry.db` growth <1MB/month.
6. **Dashboard panel load** — 15 tiles + 4 existing = 19 WS subscriptions. Verify no drops.
7. **overflow-shard-watcher thrashing** — 3/hr cap is safety net. Emit `shard_cap_hit` event + yellow tile 10.
8. **Lomax blocking change** — flipping warn→error means red Lomax stops builds. Document in `core/cluster/AGENTS.md`.

---

## Gate Status

- **Step 3.7 (Adversarial Review):** OVERRIDE (user-authorized via `BR3_BYPASS_ADVERSARIAL_REVIEW=1` after SIMPLIFY iteration; R3 format-only delta covered by `cluster-activation-R3-user-override.json`)
- **Step 3.8 (Architecture Validation):** PASS (INFO-level external paths only, no blockers)

---

## Dependencies on Existing Infrastructure

This build does not create a new orchestration layer — it wires `/begin` and `/autopilot` into the infrastructure that `BUILD_cluster-max` already shipped. Each phase consumes one or more of the following:

**Consumed as-is (no modification):**

- `core/runtime/runtime_registry.py` — Python dispatch registry (Phases 2, 3, 6)
- `~/.buildrunner/scripts/codex-bridge.sh` — pre-dispatch Codex context injection (Phases 3, 6)
- `~/.buildrunner/feature-flags.yaml` — canonical cluster flag source (Phases 2, 4)
- `~/.buildrunner/scripts/cluster-daemon.mjs` — ready-build dispatcher (Phase 5)
- `~/.buildrunner/scripts/node-matrix.mjs` — node-role mapping (Phase 5)
- `~/.buildrunner/scripts/walter-setup.sh` — Walter sentinel bootstrap (Phase 5)
- `core/telemetry/event_collector.py` — SQLite event sink (Phase 6)
- `api/routes/dashboard_stream.py` — WS dashboard stream (Phase 6 adds topic)

**Modified (additive, no breaking changes):**

- `core/review/cross_model_review.py` — gated on `BR3_ADVERSARIAL_3WAY` (Phase 4), emits event (Phase 6)
- `core/cache/cache_policy.py` — gated on `BR3_CACHE_BREAKPOINTS` (Phase 4), emits event (Phase 6)
- `core/telemetry/event_schemas.py` — 4 new event types appended (Phase 6)
- `api/routes/context.py` — APIRouter extraction, standalone bootstrap moved out (Phase 1)
- `api/node_semantic.py` — mounts `context_router` (Phase 1)

**Cluster services required online:**

- **Jimmy** (10.0.1.106:4500) — context bundle + `/context/codex` endpoint
- **Lockwood** (10.0.1.101) — semantic search + memory for role_matrix lookups
- **Below** (10.0.1.105) — Ollama runtime for local dispatch
- **Otis** (10.0.1.103) — parallel Claude builder for cluster-daemon dispatch
- **Walter** (10.0.1.102) — sentinel coverage gate for `/autopilot`
- **Lomax** (10.0.1.104) — overflow shard 3/3 target

Falls back gracefully when any node offline: `cluster-check.sh <role>` returns empty, skill continues with local behavior. `BR3_CLUSTER=off` disables all cluster access.

---

## Session Log

_Will be updated by /begin_
