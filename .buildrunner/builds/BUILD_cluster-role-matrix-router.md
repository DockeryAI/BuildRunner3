# Build: Cluster Role-Matrix Router

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: backend-build, assigned_node: muddy } # config edits, Muddy-local
      phase_2: { bucket: backend-build, assigned_node: muddy } # ~/.buildrunner/scripts/
      phase_3: { bucket: backend-build, assigned_node: muddy } # new router scripts
      phase_4: { bucket: backend-build, assigned_node: muddy } # /autopilot + /begin edits
      phase_5: { bucket: backend-build, assigned_node: muddy } # dispatch-to-node.sh
      phase_6: { bucket: qa, assigned_node: muddy } # tests exercise cross-node but run here
```

**Created:** 2026-04-22
**Status:** pending
**Deploy:** web — no runtime deploy; scripts take effect on next skill invocation
**Source Plan File:** .buildrunner/plans/spec-draft-plan.md
**Source Plan SHA:** 77a3305d5b1ccccfc2ce4278cbe9d6a0c48ebe13cd7473470c8ddd5df9aba0c4
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-22T22:48:50Z

## Overview

Make `/autopilot` and `/begin` honor every BUILD spec's `role-matrix.overrides.phases` by default — no `--cluster` flag required. Invert `node-matrix.mjs` priority so Muddy (M5), Below (Windows workhorse), and Jimmy (MS-A2 Ryzen) are tier 1, with the four M2s as tier 2 overflow. Add a load-aware router (`resolve-dispatch-node.sh`) that walks a documented precedence: `pin` → path-locality → spec-preference → load-reroute → tier-fallback-up → tier-fallback-down → local. Fix `dispatch-to-node.sh`'s hard limitation on out-of-project writes by adding `sync_on_dispatch` rsync prefixes (pre/post, SHA-verified) so BUILDs that edit `~/.buildrunner/dashboard/` can actually dispatch to Otis/Walter.

All routing policy lives in the existing `~/.buildrunner/config/default-role-matrix.yaml` — every BUILD spec already inherits from it. No parallel system. Every routing decision is written to `.buildrunner/decisions.log` with the reason chain.

Every phase in this build edits files under `~/.buildrunner/` (scripts, config) — path-locality pins everything to Muddy. The Otis/Walter/Below dispatch paths ship in this build but are exercised by _other_ builds after it ships. Phase 6 includes a live round-trip sync test to Otis as verification.

## Parallelization Matrix

| Phase | Key Files                                                                | Can Parallel With | Blocked By    |
| ----- | ------------------------------------------------------------------------ | ----------------- | ------------- |
| 1     | `default-role-matrix.yaml`, `role-matrix.schema.json`, `cluster.json`    | —                 | —             |
| 2     | `node-matrix.mjs`                                                        | —                 | 1             |
| 3     | `resolve-dispatch-node.sh`, `resolve-dispatch-node.py`                   | —                 | 1, 2          |
| 4     | `populate-agent-registry.sh`, `autopilot.md`, `begin.md`                 | 5                 | 3             |
| 5     | `dispatch-to-node.sh`, `_dispatch-core.sh`                               | 4                 | 3             |
| 6     | `tests/router-resolution.sh`, `tests/dispatch-sync.sh`, `docs/router.md` | —                 | 1, 2, 3, 4, 5 |

## Phases

### Phase 1: Extend global matrix schema and defaults

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/config/default-role-matrix.yaml` (MODIFY)
- `~/.buildrunner/config/role-matrix.schema.json` (MODIFY)
- `~/.buildrunner/cluster.json` (MODIFY)

**Blocked by:** None

**Deliverables:**

- [x] Add `nodes:` top-level block to `default-role-matrix.yaml` with `speed_tier` (1 or 2) and `local_paths` array for all seven workers plus `master`.
- [x] `local_paths` populated: `muddy` → `~/.buildrunner/`, `~/.claude/`, `~/Projects/`; `jimmy` → `/srv/jimmy/`; `below` → `C:/Users/byron/br3-sandbox/`.
- [x] Add `preferred_nodes` array (tier 1 first) to every bucket in `default-role-matrix.yaml`: `backend-build: [muddy, below, jimmy, otis, lomax]`; `ui-build: [muddy, below, otis, lomax]`; `qa: [walter, otis, lomax]`; same pattern for `terminal-build`, `review`, `classification`, `retrieval`, `planning`, `architecture`.
- [x] Add `routing:` block at top level: `overload_thresholds: { cpu_pct: 75, mem_avail_pct: 20, active_builds: 2, window_seconds: 60 }`, `sync_on_dispatch: [~/.buildrunner/dashboard/]`, `load_query_timeout_ms: 2000`.
- [x] Extend `role-matrix.schema.json` to accept the new `nodes.*`, `buckets.*.preferred_nodes`, `buckets.*.allow_tier_fallback` (bool, default true), `routing.*`, and per-phase `pin: bool` keys. Continue to reject unknown bucket/node names.
- [x] Add `speed_tier: 1|2` integer to every node in `cluster.json` (muddy/below/jimmy → 1; otis/walter/lomax/lockwood → 2) and on `master`. Additive only — existing consumers unaffected.
- [x] Verify `~/.buildrunner/scripts/load-role-matrix.sh` resolves cleanly against the new schema and writes the enriched `.resolved-role-matrix.json` cache. All existing BUILD specs in `.buildrunner/builds/` and `~/.buildrunner/builds/` still resolve without error.

### Phase 2: Invert `node-matrix.mjs` priority + add load query

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/node-matrix.mjs` (MODIFY)

**Blocked by:** Phase 1

**Deliverables:**

- [x] Replace the hardcoded `PRIORITY_ORDER` constant with dynamic tier-derived ordering: read `speed_tier` from `cluster.json`, sort ascending. Within a tier, preserve existing stable ordering. Remove the "last resort — dev workstation" comment on Muddy.
- [x] Add exported function `listCandidates(bucket)` — returns tier-sorted healthy nodes filtered by the bucket's `preferred_nodes` list from the resolved matrix cache.
- [x] Add exported function `nodeLoad(node)` — returns `{ cpu_pct, mem_avail_pct, active_builds, overloaded: bool, source: "prometheus" | "fail-open" }`. Pull CPU/mem from the existing Prometheus instant-query host; pull `active_builds` by scanning `.buildrunner/agents.json` for `status=running` entries matching this node. Respect `routing.load_query_timeout_ms`; return `fail-open` on timeout (overloaded=false, logged).
- [x] `--json` stdout retains backwards compatibility: existing fields unchanged; new fields `speed_tier` and `overloaded` added to each node object.
- [x] Smoke: `node ~/.buildrunner/scripts/node-matrix.mjs --json --dry-run | jq '.[0].key'` returns `muddy`.

### Phase 3: `resolve-dispatch-node.sh` — the router

**Status:** not_started
**Files:**

- `~/.buildrunner/scripts/resolve-dispatch-node.sh` (NEW)
- `~/.buildrunner/scripts/resolve-dispatch-node.py` (NEW)
- `~/.buildrunner/scripts/tests/resolve-dispatch-node-tests.sh` (NEW)

**Blocked by:** Phase 1, Phase 2

**Deliverables:**

- [ ] CLI: `resolve-dispatch-node.sh <build-spec> <phase-num> [--exclude-node <name>]...` prints JSON `{ node, bucket, reason, overrides_applied[], load_snapshot }` to stdout. `--exclude-node` is repeatable; excluded nodes are removed from every step of the precedence walk, including path-locality (path-locality-excluded → fall through to tier routing). Exit codes: 0 success, 1 unresolvable hard pin, 2 schema/parse error, 4 all candidates excluded.
- [ ] Resolution walks precedence exactly: pin (hard) → path-locality → spec-preference healthy+not-overloaded → load-reroute same-tier alternate → tier-fallback-up (tier 1 if tier 2 saturated) → tier-fallback-down (tier 2 if tier 1 saturated AND `bucket.allow_tier_fallback`) → local Muddy.
- [ ] Reads `.resolved-role-matrix.json` cache. Re-resolves via `load-role-matrix.sh` if cache is missing or older than existing TTL.
- [ ] Parses phase `Files:` list: matches each file path against `routing.sync_on_dispatch` prefixes (marks phase for sync, does not pin) AND `nodes.*.local_paths` prefixes (pins to matching node). Multiple `local_paths` matches → pin to first in evaluation order, log conflict.
- [ ] Every resolution writes one line to `.buildrunner/decisions.log` in the project root: ISO timestamp + `router: build=<id> phase=<N> node=<chosen> reason=<code> overrides=<comma-list>`. Reason codes: `pin`, `path-locality`, `path-locality-excluded`, `spec-preference`, `load-rerouted`, `tier-fallback-up`, `tier-fallback-down`, `saturation-fallback-local`, `load-unknown-fail-open`.
- [ ] Hard pin on unhealthy node returns exit 1 and a structured error JSON — does NOT silently reroute. `reason: pin-failed`.
- [ ] `resolve-dispatch-node.py` handles YAML/JSON parsing and prefix matching; the shell script handles CLI glue, stdout formatting, and decisions.log write.
- [ ] `tests/resolve-dispatch-node-tests.sh` covers: spec-preference pass, load-reroute within tier, tier-fallback-up, path-locality pin, path-locality-excluded after `--exclude-node`, hard-pin-fails-loud, unknown-bucket schema error.

### Phase 4: Bridge into `/autopilot` and `/begin` (no-flag default)

**Status:** not_started
**Files:**

- `~/.buildrunner/scripts/populate-agent-registry.sh` (NEW)
- `~/.claude/commands/autopilot.md` (MODIFY)
- `~/.claude/commands/begin.md` (MODIFY)

**Blocked by:** Phase 3

**Deliverables:**

- [ ] `populate-agent-registry.sh <build-spec>` iterates every pending phase, calls `resolve-dispatch-node.sh`, writes `{ phase: N, assigned_node: X, bucket: Y, reason: Z }` into `.buildrunner/agents.json` under a new `routing:` key. Idempotent — replaces prior `routing:` block on each invocation. Does NOT touch the existing `agents:` key used by `/dash`.
- [ ] **Ordering (explicit):** helper runs AFTER `load-role-matrix.sh` populates `.resolved-role-matrix.json`, never before. Both skills updated to enforce this order.
- [ ] **Concurrency safety:** writes to `.buildrunner/agents.json` are guarded by `flock -x -w 5` on `.buildrunner/locks/agents.json.lock`. Read-modify-write the entire file under the lock, then atomic `mv` from same-directory temp file. Lockfile path added to `.gitignore`. Prevents corruption when `/autopilot` and `/begin` (or two autopilots) run concurrently against the same project.
- [ ] `/autopilot` Step 1 reordered to: BUILD/plan binding check (Step 1.0a) → `load-role-matrix.sh "$BUILD_FILE"` → `populate-agent-registry.sh "$BUILD_FILE"` → existing Step 1.5 dispatch check. Step 1.5 semantics unchanged — reads `assigned_node` from `agents.json.routing.phases[phase_N]`, falls through to local when absent (back-compat).
- [ ] `/begin` reordered: BUILD spec located → existing `load-role-matrix.sh` call at begin.md:142 → NEW `populate-agent-registry.sh` call inserted immediately after → existing dispatch check.
- [ ] Both skills gain a documented precedence table in-line: pin > path-locality > spec-preference > load > tier-fallback.
- [ ] `--cluster` behavior unchanged. Skill docs updated to state explicitly: per-phase routing is no longer gated on `--cluster`; the flag keeps its multi-build-parallelism meaning only.

### Phase 5: Path-sync in `dispatch-to-node.sh`

**Status:** not_started
**Files:**

- `~/.buildrunner/scripts/dispatch-to-node.sh` (MODIFY)
- `~/.buildrunner/scripts/_dispatch-core.sh` (MODIFY)

**Blocked by:** Phase 3

**Deliverables:**

- [ ] Before dispatch, script reads the phase's resolved routing entry (from `agents.json.routing` or a `--phase <N>` arg). Any Files matching a `routing.sync_on_dispatch` prefix triggers a pre-dispatch rsync of the full prefix directory to the target node's equivalent path.
- [ ] After execution, a post-dispatch rsync pulls changes back. SHA256 of each file pre/post is recorded in `.buildrunner/decisions.log` under `sync_result:` lines. Drift without an expected change → WARN.
- [ ] **Sync failure handling (standalone):** on rsync failure (network drop, permissions, target path missing), `dispatch-to-node.sh` aborts with exit code 3 (`sync-failed`) WITHOUT executing the phase. The orchestrator (autopilot) detects exit 3 and invokes `resolve-dispatch-node.sh --exclude-node <failed-node> <build> <phase>` to re-resolve, then re-dispatches. `dispatch-to-node.sh` does NOT call the resolver itself — resolver stays a pure CLI.
- [ ] Replace the current "LIMITATION" comment block at the top of `dispatch-to-node.sh` with accurate behavior documentation: files inside project_path sync via the existing flow; files under `routing.sync_on_dispatch` prefixes additionally sync in and out; other external paths still pin the phase via the router's path-locality step.
- [ ] `_dispatch-core.sh` gains `sync_prefix_to_node(node, prefix)` and `sync_prefix_from_node(node, prefix)` helpers (using existing rsync/tar/scp selection logic based on target OS).
- [ ] Feature flag `BR3_ROUTER_PREFIX_SYNC=on|off`. Default `off` through Phase 6 verification; flipped to `on` in Phase 6 last deliverable. Rollback is one env var.

### Phase 6: Live verification + rollout

**Status:** not_started
**Files:**

- `~/.buildrunner/scripts/tests/router-resolution.sh` (NEW)
- `~/.buildrunner/scripts/tests/dispatch-sync.sh` (NEW)
- `~/.buildrunner/docs/router.md` (NEW)

**Blocked by:** Phase 1, Phase 2, Phase 3, Phase 4, Phase 5

**Deliverables:**

- [ ] `router-resolution.sh` calls `resolve-dispatch-node.sh` against `.buildrunner/builds/BUILD_cluster-dashboard-prometheus-surfacing.md` for every phase. Asserts Phase 1/2/3/5 → muddy (path-locality on `~/.buildrunner/dashboard/`), Phase 4 → muddy (path-locality overrides spec's otis assignment, `reason: path-locality`), Phase 6 → muddy (same).
- [ ] `router-resolution.sh` synthetic scenario: constructs a throwaway BUILD spec with in-repo Files only (no path-locality triggers). Asserts Phase 4 resolves to otis per spec. Injects fake Prometheus load payload for otis at 90% CPU → asserts fallback to lomax (tier 2 alternate). Injects load on lomax too → asserts fallback up to muddy (tier 1).
- [ ] `dispatch-sync.sh` end-to-end live run: sets `BR3_ROUTER_PREFIX_SYNC=on`, dispatches a no-op touch of `~/.buildrunner/dashboard/.router-sync-test` to otis, confirms file appears on otis, confirms return-sync produces identical SHA256 on muddy, cleans up the test file on both ends.
- [ ] `docs/router.md` documents: precedence table, overload thresholds with defaults, `pin: true` semantics (hard fail on unhealthy), `sync_on_dispatch` behavior, `BR3_ROUTER_PREFIX_SYNC` rollout flag, `--exclude-node` re-entry contract, how to inspect `.buildrunner/decisions.log` for `router:` and `sync_result:` lines.
- [ ] Live `/autopilot` invocation on `.buildrunner/builds/BUILD_cluster-dashboard-prometheus-surfacing.md` with NO flags runs through Phase 1 (smoke only — do not execute the build). Verifies `.buildrunner/agents.json.routing` is populated with one entry per phase, each carrying the correct `reason` code, with decisions logged.
- [ ] Flip `BR3_ROUTER_PREFIX_SYNC` default from `off` to `on` in `_dispatch-core.sh` as the final deliverable, only after all previous assertions pass. Rollback is one env var or one-line revert.

## Session Log

_(Populated by /begin)_
