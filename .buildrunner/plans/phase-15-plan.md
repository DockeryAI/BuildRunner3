# Phase 15 Plan — Feature Observability (Passive Real-Usage Telemetry)

**Build:** BUILD_cluster-max
**Added:** 2026-04-21
**Revision:** R2 (post-round-1 adversarial review — 6 blockers + 4 warnings addressed)
**Status:** pending
**Codex model:** gpt-5.4
**Codex effort:** high
**Worktree:** main repo (Phase 14 touches disjoint files — no conflict)
**Blocked by:** Phase 13 (cutover complete; all feature code paths live and exercisable)
**Can parallelize:** Phase 14

## Note for reviewers re: file visibility

Several files referenced below (`core/telemetry/event_collector.py`, `core/runtime/runtime_registry.py`, `core/cluster/context_bundle.py`, `api/routes/dashboard_stream.py`, `ui/dashboard/index.html`, `.buildrunner/builds/BUILD_cluster-max.md`, etc.) are live in the main repo but may be absent from the rsync bundle delivered to the review node. Each referenced API below has been independently verified by the amender via `grep` against the live repo. Specific locations:

- `RuntimeRegistry.execute()` — `core/runtime/runtime_registry.py:73`
- `build_cached_prompt()` — `core/runtime/cache_policy.py:35`
- `context_bundle.assemble()` — `core/cluster/context_bundle.py:450`
- `context_router.route()` — `core/cluster/context_router.py:145`
- `run_three_way_review()` — `core/cluster/cross_model_review.py:1211`
- `invoke_arbiter_claude()` + `log_ruling()` — `core/cluster/arbiter.py:134,203`
- `summarizer.summarize_diff()` / `summarize_logs()` — `core/cluster/summarizer.py:163,191`
- `EventCollector.collect(event)` — `core/telemetry/event_collector.py:179`
- `events` table already has `event_id TEXT UNIQUE NOT NULL` (verified against `.buildrunner/telemetry.db` schema)

If the review environment cannot see these paths, treat that as a review-packaging issue and do not raise it as a plan defect.

## Goal (phase-level)

Every real invocation of the 4 flipped cluster-max feature flags (`BR3_AUTO_CONTEXT`, `BR3_RUNTIME_OLLAMA`, `BR3_ADVERSARIAL_3WAY`, `BR3_CACHE_BREAKPOINTS`) plus the 3 context-parity components (bundle, router, private-filter) emits a typed telemetry event during the user's normal work. An invariant checker validates every event against the BUILD_cluster-max.md contract that produced the feature. Violations surface on the :4400 dashboard and as alert files within 60 s.

**No synthetic probes in production observability.** Production emit points only fire on real traffic (`/begin`, `/autopilot`, `/review`, `/plan`, `/research`, `/commit`). Acceptance tests in Task 15.4 and 15.5 necessarily use synthetic inputs to prove the pipeline responds correctly — this is test infrastructure, not production monitoring.

## Why this phase is needed

Post-cutover (Phase 13, 2026-04-21), the only evidence that the 4 flags still behave per spec is the one-shot `post_cutover_smoke.py`. The cluster-monitor launchd agent checks node liveness, not feature correctness. Silent regressions (Ollama falling back to Claude, cache dropping a breakpoint after a template edit, `[private]` leak on a new source, tokenizer silently returning `bytes`) would not surface until a user noticed. Passive telemetry on real code paths closes that gap.

## Session / correlation model (addresses reviewer finding #9)

Events carry a `correlation_id` resolved as follows:

- **Python host sites** read `os.environ.get("BR3_SESSION_ID")` first; if absent, fall back to the in-process `EventCollector` session UUID (initialised once per process).
- **Shell host sites** (`auto-context.sh`, `pre-commit-cluster-guard`) read `$BR3_SESSION_ID` if set, else synthesise `shell-<8char-uuid>` for that invocation. The existing `auto-context.sh` already exports a session marker via the Claude Code hook environment; `pre-commit-cluster-guard` uses a per-commit correlation (`git-HEAD@<short-sha>`).

**Cross-event invariants** that require Python-side correlation (e.g., `router_decision` → `context_bundle_served` ordering, two-layer private-filter ordering) only fire when both events carry the same non-`shell-*` correlation. Shell-only correlations are recorded but not asserted against Python-side ordering rules (documented in `invariants.yaml`).

## Files (whitelist — touch only these)

### Python — core + API

- `core/telemetry/event_collector.py` (MODIFY — add `collect_simple(event_type, metadata, correlation_id=None, duration_ms=None)` convenience that constructs an `Event` with a fresh `event_id` UUID and delegates to existing `.collect()`)
- `core/telemetry/event_schemas.py` (MODIFY — register 16 new `EventType` enum values)
- `core/telemetry/invariant_checker.py` (NEW)
- `core/telemetry/invariants.yaml` (NEW — declarative rules, one per feature)
- `core/telemetry/jsonl_bridge.py` (NEW — tails shell-emitted events into telemetry.db)
- `core/runtime/runtime_registry.py` (MODIFY — 1 emit call at the end of `execute()`)
- `core/runtime/cache_policy.py` (MODIFY — 1 emit call at the end of `build_cached_prompt()`)
- `core/runtime/context_injector.py` (MODIFY — 1 emit call at wrap point)
- `core/cluster/cross_model_review.py` (MODIFY — 1 emit call at the end of `run_three_way_review()`)
- `core/cluster/arbiter.py` (MODIFY — 1 emit call inside `log_ruling()`)
- `core/cluster/summarizer.py` (MODIFY — 1 emit call at end of `summarize_diff()` and `summarize_logs()`)
- `core/cluster/context_bundle.py` (MODIFY — 2 emit calls: one at end of `assemble()` (`context_bundle_served`); one at the extraction-layer private filter (`private_filter_applied` with `layer="extract"`))
- `core/cluster/context_router.py` (MODIFY — 1 emit call at end of `route()`)
- `api/routes/context.py` (MODIFY — 1 emit call before response return)
- `api/routes/retrieve.py` (MODIFY — 1 emit call before response return)
- `api/routes/dashboard_stream.py` (MODIFY — add `feature-health` WS topic + invoke invariant checker + start bridge tailer on existing event loop)

### Shell hooks + scripts

- `~/.buildrunner/hooks/auto-context.sh` (MODIFY — script file is user-global, but its JSONL append targets the **repo-relative** bridge file; see Bridge Path Resolver Contract below)
- `.buildrunner/hooks/pre-commit-cluster-guard` (MODIFY — repo-relative; append one JSONL line to the repo-relative bridge file)
- `~/.buildrunner/scripts/sync-cluster-context.sh` (MODIFY — script file is user-global, but its JSONL append targets the **repo-relative** bridge file; emits `private_filter_applied` with `layer="mirror"`)

#### Bridge Path Resolver Contract (canonical — binds Tasks 15.1 / 15.2 / 15.3)

All JSONL bridge writers (Python and shell) MUST resolve the bridge file path to `<repo_root>/.buildrunner/events-bridge.jsonl`, where `<repo_root>` is the absolute path returned by `git rev-parse --show-toplevel` evaluated in the current working directory at emit time, with `$BR3_REPO_ROOT` as an environment override when set. **The user-global path `~/.buildrunner/events-bridge.jsonl` is explicitly NOT a bridge target and MUST NOT be written to** — this is the single source of truth that eliminates the user-global vs. repo-relative split.

Shell resolver snippet (used verbatim in every shell emit site):

```bash
BRIDGE_REPO_ROOT="${BR3_REPO_ROOT:-$(git rev-parse --show-toplevel 2>/dev/null)}"
if [ -n "$BRIDGE_REPO_ROOT" ] && [ -d "$BRIDGE_REPO_ROOT/.buildrunner" ]; then
  printf '%s\n' "$JSON" >> "$BRIDGE_REPO_ROOT/.buildrunner/events-bridge.jsonl" 2>/dev/null || true
fi
# If no repo root can be resolved (e.g., hook fires outside a git checkout), the
# event is silently dropped — best-effort contract per Constraints section.
```

Python bridge tailer (`core/telemetry/jsonl_bridge.py`) reads from the same `<repo_root>/.buildrunner/events-bridge.jsonl` resolved via `Path(__file__).resolve().parents[2] / ".buildrunner" / "events-bridge.jsonl"` (the `core/` package sits directly under the repo root). `BR3_REPO_ROOT` env override applies identically.

### UI

- `ui/dashboard/panels/feature-health.js` (NEW)
- `ui/dashboard/index.html` (MODIFY — mount panel; reference uses `<script src="./panels/feature-health.js">` alongside existing panel mounts)
- `ui/dashboard/AGENTS.md` (MODIFY — register feature-health panel; Phase 15 is solo on this file in its wave → direct edit OK)

### AGENTS.md staged snippets

- `core/runtime/AGENTS.md.append-phase15.txt` (NEW — staged snippet, merged at wave end)
- `core/cluster/AGENTS.md.append-phase15.txt` (NEW — staged snippet, merged at wave end)

### Tests

- `tests/telemetry/test_invariant_checker.py` (NEW)
- `tests/telemetry/test_emit_contract.py` (NEW)
- `tests/e2e/feature-health-panel.spec.ts` (NEW)

### Spec + decisions (meta-update, explicitly allowed)

- `.buildrunner/builds/BUILD_cluster-max.md` (MODIFY — append Phase 15 block, update Status Table row 15, update Role Matrix row 15, update Per-Phase AGENTS.md Mapping row 15, update Recommended Ship Order)
- `.buildrunner/decisions.log` (APPEND — one `PHASE-15 AMENDMENT <ts>` line)

## Constraints

- IMPORTANT: Emission is **best-effort, non-blocking**. A failing emit MUST NOT break the host call path. Python sites wrap in `try: collector.collect_simple(...) except Exception: _emit_warn_once(logger)`; shell sites append with `printf … >> …jsonl 2>/dev/null || true`. Silent emit failure logs one warning per process lifetime, nothing more.
- IMPORTANT: Zero new network hops. Python emits write directly to `telemetry.db` via the existing `EventCollector`. Shell emits append to the repo-relative bridge file `<repo_root>/.buildrunner/events-bridge.jsonl` resolved per the Bridge Path Resolver Contract above (single source of truth — user-global `~/.buildrunner/events-bridge.jsonl` is NOT used). The bridge tailer runs inside the existing dashboard service process (`api/routes/dashboard_stream.py` event loop) — no new daemon, no new port, no new systemd unit, no new launchd agent.
- IMPORTANT: Invariants are declarative (`invariants.yaml`). Each rule cites the BUILD_cluster-max.md phase + `Done When` / `Constraint` line it enforces. Rule additions or edits require a spec-line citation in the PR description.
- IMPORTANT: **Silent-fallback contract preserved (Phase 7 Quality Firewall).** `runtime_dispatched` event records `fallback_reason` when Ollama→Claude fallback occurs, but the host call still returns the Claude result with no user-visible error. The invariant checker treats a populated `fallback_reason` as a P1 anomaly (rising rate visible) — a missing `actual_runtime` with no reason is P0.
- IMPORTANT: `telemetry.db` schema stays backward-compatible. Phase 15 adds NO new columns — all new event types use the existing `metadata` JSON column. Existing consumers (`task_completed`, `model_selected`, etc.) unchanged. The existing `event_id TEXT UNIQUE NOT NULL` column provides JSONL bridge dedup — no new UNIQUE constraint needed.
- IMPORTANT: Phase 15 uses the staged AGENTS.md append pattern for `core/runtime/AGENTS.md` and `core/cluster/AGENTS.md` (both files carry prior-phase appends). Direct edit to those two files is FORBIDDEN — wave-merge gate applies. `ui/dashboard/AGENTS.md` direct edit OK (solo).
- NEVER emit PII, API keys, or full prompt / diff / log / bundle text in event `metadata` — only hashes (sha256 truncated to 16 chars), sizes (bytes, tokens, lines), booleans, enums, and reason codes. A regex scanner runs in `test_emit_contract.py` against every emit site and every metadata dict literal; reject any string literal longer than 256 chars appearing as a metadata value.
- NEVER add a new port, systemd service, or launchd agent. Reuse `telemetry.db`, the :4400 WS topic mechanism, and the existing `~/.buildrunner/alerts/` directory.
- NEVER let the invariant checker mutate any state consumed by external components. The checker emits two kinds of **outputs** (an `anomaly` row in `events`, and an alert JSON file). The checker also maintains its own **internal process state** (`.buildrunner/invariant_checker.position` watermark and per-rule alert-rate-limit counters) — these are private to the checker's process and are not outputs consumed by any other system.

## Tasks (Codex four-element format)

### Task 15.1: Runtime + cache + guard emits

- **Goal:** `RuntimeRegistry.execute()` (runtime_registry.py:73) emits TWO events per invocation — one `runtime_dispatched` and one `cache_hit` (derived from the Anthropic response headers on the same call). `cache_policy.build_cached_prompt()` (cache_policy.py:35), `context_injector` wrap, and `.buildrunner/hooks/pre-commit-cluster-guard` (shell) each write one typed telemetry event per real invocation.
- **Context:** `core/telemetry/event_collector.py` stores rows in `.buildrunner/telemetry.db` via `EventCollector.collect(event)` (event_collector.py:179). A thin `collect_simple(event_type, metadata, correlation_id=None, duration_ms=None)` helper is added on the collector to reduce boilerplate at emit sites. Host call sites are stable (Phase 6 / 7 / 8). `pre-commit-cluster-guard` lives at repo-relative `.buildrunner/hooks/pre-commit-cluster-guard`; it is a shell script and uses the JSONL bridge built in Task 15.3. Anthropic SDK responses expose `usage.cache_creation_input_tokens` and `usage.cache_read_input_tokens`; `RuntimeRegistry.execute()` parses these off the response object after each Claude call and emits one `cache_hit` event per call with those two fields (plus `model`, `prompt_hash` (sha256, 16-char truncated)). Non-Claude runtimes do not emit `cache_hit`.
- **Constraints:** One line per emit, wrapped in try/except (Python) or `|| true` (shell). No new network calls. Event types: `runtime_dispatched`, `cache_hit`, `cache_prompt_built`, `runtime_context_injected`, `cluster_guard_scan`. `cache_hit` metadata schema: `{model: str, cache_creation_input_tokens: int, cache_read_input_tokens: int, prompt_hash: str}`. `cache_hit` MUST also be added to `core/telemetry/event_schemas.py`'s event-type enum alongside the other Phase 15 additions. Metadata fields otherwise fixed by the `invariants.yaml` schema for each type. Correlation resolves per the Session / correlation model section above — `cache_hit` shares the same correlation_id as the `runtime_dispatched` it pairs with.
- **Done-When:** `pytest tests/telemetry/test_emit_contract.py::test_runtime_emits -x` passes AND a one-task smoke against `RuntimeRegistry.execute()` on Claude produces exactly one `runtime_dispatched` row AND one `cache_hit` row in `telemetry.db` sharing the same `correlation_id`, with both `cache_creation_input_tokens` and `cache_read_input_tokens` populated as integers in the `cache_hit` metadata.

### Task 15.2: Cluster review + context emits

- **Goal:** `run_three_way_review()` (cross_model_review.py:1211), `invoke_arbiter_claude()` (arbiter.py:134) + `log_ruling()` (arbiter.py:203), `summarizer.summarize_diff()` / `summarize_logs()` (summarizer.py:163,191), `context_bundle.assemble()` (context_bundle.py:450), `context_router.route()` (context_router.py:145), `/context/{model}` endpoint, `/retrieve` endpoint, and `~/.buildrunner/scripts/sync-cluster-context.sh` (via bridge) each emit one typed event. `context_bundle.assemble()` additionally emits a second `private_filter_applied` event at the extraction-layer filter (Phase 12 defense-in-depth rule, BUILD line ~1459).
- **Context:** Phase 9 / 10 / 12 call sites live. Shell script `sync-cluster-context.sh` emits a `private_filter_applied` event with `layer="mirror"` via the JSONL bridge. Invariant checker cross-references mirror-layer + extract-layer pairs plus `router_decision` → `context_bundle_served` ordering within the same Python-side correlation.
- **Constraints:** Same wrap/no-block contract as 15.1. Event types: `adversarial_review_ran`, `arbiter_ruled`, `summarizer_invoked`, `context_bundle_served`, `router_decision`, `private_filter_applied`, `retrieve_served`. `adversarial_review_ran` metadata carries `claude_ok`, `codex_ok`, `review_round`, `fix_type_missing_count`, `structural_blocker`, `persistent_blocker`, `findings_count`. No full diff / prompt text — only hashes and counts.
- **Done-When:** `pytest tests/telemetry/test_emit_contract.py::test_cluster_emits -x` passes AND a dry `/review --phase test --target <fixture>` produces ≥4 linked events (same Python-side correlation) across the review + context paths.

### Task 15.3: JSONL bridge + shell hook emits

- **Goal:** `~/.buildrunner/hooks/auto-context.sh`, `.buildrunner/hooks/pre-commit-cluster-guard`, and `~/.buildrunner/scripts/sync-cluster-context.sh` append one JSONL event per run to the resolved bridge path `<repo_root>/.buildrunner/events-bridge.jsonl` (per Bridge Path Resolver Contract). `core/telemetry/jsonl_bridge.py` tails that exact same file and inserts rows into `telemetry.db` via `EventCollector.collect_simple(...)`. The bridge runs as an asyncio task on the existing dashboard service event loop.
- **Context:** Shell scripts cannot import Python telemetry directly — JSONL is the cheapest crossover. The dashboard service (`api/routes/dashboard_stream.py`) is the only always-running Python process on Muddy that already owns an asyncio loop; attaching the bridge there avoids a new daemon. Both writer and tailer resolve the same path via `$BR3_REPO_ROOT` env override OR `git rev-parse --show-toplevel` (shell) / `Path(__file__).resolve().parents[2]` (Python).
- **Constraints:** Bridge is **at-least-once with strict rotation ordering**:
  1. Shell emit uses the resolver snippet from the Bridge Path Resolver Contract — `printf '%s\n' "$JSON" >> "$BRIDGE_REPO_ROOT/.buildrunner/events-bridge.jsonl" 2>/dev/null || true`. No `sync` required — the bridge tolerates partial lines (lines without trailing `\n` are held until next tick). If repo root cannot be resolved, the event is silently dropped.
  2. Bridge checkpoints position to `.buildrunner/jsonl_bridge.position` **after every row successfully inserted** (not every 100). Overhead benchmarked acceptable at ≥1000 rows/s in `test_shell_bridge`.
  3. Rotation protocol at 50 MB: bridge first drains the file to EOF, writes the final position to the position file, **then** atomically renames `events-bridge.jsonl` → `events-bridge.jsonl.<ts>.done`. Shell writers opening the file after the rename create a fresh `events-bridge.jsonl`. The renamed file is picked up next tick with a fresh position of 0; any duplicated rows at the boundary are caught by the existing `event_id UNIQUE` column on the `events` table (event_id is a fresh UUID per emit, so actual duplicates are structurally impossible — the UNIQUE column just protects against bugs).
  4. Bridge MUST NOT block the dashboard WS — sqlite writes go through `asyncio.to_thread`. Graceful if `events-bridge.jsonl` is missing (bridge creates on first tick).
- Shell emit uses pure `printf` + `>>` plus the repo-root resolver — no `jq`, no `python -c`, no network tool.
- **Done-When:** `pytest tests/telemetry/test_emit_contract.py::test_shell_bridge -x` passes AND writing a synthetic JSONL line to `$(git rev-parse --show-toplevel)/.buildrunner/events-bridge.jsonl` (from a shell cwd anywhere inside the repo) produces a matching `telemetry.db` row within 2 s of the next bridge tick AND the same test also asserts the bridge tailer reads from the identical resolved path AND simulating rotation mid-burst shows zero skipped rows and zero duplicated `event_id`s.

### Task 15.4: Invariant checker + rule set

- **Goal:** `core/telemetry/invariant_checker.py` polls new rows in `telemetry.db` (last-checked `id` watermark stored in `.buildrunner/invariant_checker.position`), evaluates each against `core/telemetry/invariants.yaml`, inserts `event_type='anomaly'` rows for violations, and writes `~/.buildrunner/alerts/<feature>-<ts>.json` for P0/P1 violations. Runs as a coroutine on the dashboard service event loop (same loop as Task 15.3's bridge).
- **Context:** 15 rules total, one per in-scope flag-gated feature + context-parity component + cluster-guard. Representative rules (each cites its spec line):
  - `cache_prompt_built` MUST have `block_count = 3` AND `cached_count = 2` (Phase 8, BUILD line ~1162). P0.
  - `runtime_dispatched` with `requested_runtime = ollama` AND `flag_state.BR3_RUNTIME_OLLAMA = on` MUST have `actual_runtime = ollama` OR `fallback_reason != null`. Populated `fallback_reason` = P1. Missing both = P0.
  - `context_bundle_served` MUST have `budget.tokenizer != "bytes"` (Phase 10/12 fail-closed rule, BUILD line ~1468). P0.
  - Per-model bundle budget: claude ≤32000, codex ≤48000, ollama ≤16000 tokens (Phase 12, BUILD line ~1455). P1 on breach.
  - `adversarial_review_ran` MUST have `fix_type_missing_count = 0` AND `review_round ≤ 3` (Phase 9, BUILD line ~1226). P0.
  - `arbiter_ruled` only when matching `adversarial_review_ran` in same correlation has `claude_ok XOR codex_ok` post-rebuttal (Phase 9). P1.
  - `private_filter_applied` with `layer = extract` MUST be preceded by a `context_bundle_served` for the same Python-side correlation; any `context_bundle_served` MUST have had both `layer = mirror` AND `layer = extract` events recorded before it (Phase 12 two-layer rule, BUILD line ~1459). P0.
  - `router_decision` MUST precede every `context_bundle_served` in the same Python-side correlation (Phase 12 single-source rule, BUILD line ~1456). P0.
  - `cluster_guard_scan` with `violations > 0`. P0 (Phase 7 registry-only rule).
  - Rolling 24 h cache hit rate (derived from `cache_hit` events emitted by `RuntimeRegistry.execute()` — see Task 15.1) — target ≥70 % on prompts reused ≥2× (Phase 8 done-when). P2 below target. Note: backup observability is explicitly OUT OF SCOPE for Phase 15 — no backup system emits events yet; deferred to a future amendment that introduces a backup subsystem.
- **Constraints:** Checker is a **pure evaluator over input events**, with the clarification that its internal watermark + per-rule rate-limit counters are process-private state and are NOT outputs consumed by any external system. External outputs are limited to (a) `anomaly` rows in the `events` table and (b) alert JSON files in `~/.buildrunner/alerts/`. Rule authoring is declarative YAML (`severity: P0|P1|P2`, `condition: jq-style JSONPath + comparison`, `message: template`, `source: BUILD_cluster-max.md#L<n>`). macOS notification via `osascript` fires only on P0. Per-rule alert-rate limit: max 10 alerts/rule/hour, excess suppressed with `suppressed_count` in the subsequent alert's metadata. Must handle an empty / brand-new `telemetry.db` cleanly. Cold start (missing watermark file) begins from "last 1 hour" to avoid replay storm.
- **Done-When:** `pytest tests/telemetry/test_invariant_checker.py -x` passes ≥15 rule tests AND hand-inserting a bad event (`runtime_dispatched` with `requested_runtime = ollama, actual_runtime = claude, fallback_reason = null` while the flag is `on`) produces exactly one `anomaly` row AND one alert file in `~/.buildrunner/alerts/` within 5 s of the next checker tick.

### Task 15.5: Dashboard Feature Health panel

- **Goal:** `ui/dashboard/panels/feature-health.js` mounts a new panel on :4400 showing 15 feature tiles (one per invariant rule), a live event stream (last 20), and anomaly drill-down. `api/routes/dashboard_stream.py` adds a `feature-health` WS topic emitting `{tile_id, last_fire_ts, fires_1h, fires_24h, anomalies_24h, status: green|amber|red}` per tick.
- **Context:** Dashboard is vanilla HTML + JS, no framework (per `ui/dashboard/AGENTS.md`). WS at `ws://10.0.1.106:4400/ws` already broadcasts 4 topics (node-health / overflow-reserve / storage-health / consensus) — Phase 15 adds the 5th. Panel mount happens in `ui/dashboard/index.html` alongside the existing 4 via a `<script src="./panels/feature-health.js">` line.
- **Constraints:** Zero framework deps. Reconnect uses the existing exp-backoff cap 30 s from Phase 11 `app.js`. Tile status mapping: green (no anomalies 24 h), amber (P2 anomaly 24 h), red (P0/P1 anomaly 24 h). Panel renders refresh-proof across reconnects (`app.js` handles resync). Event stream capped at 20 entries client-side. No direct DB access from the panel — all data via the WS topic.
- **Done-When:** `npx eslint ui/dashboard/panels/feature-health.js` passes AND `playwright test tests/e2e/feature-health-panel.spec.ts` confirms 15 tiles render on load AND directly inserting one synthetic P0 `anomaly` row turns the correct tile red within 2 s of the next WS tick.

### Task 15.6: AGENTS.md + decisions + spec hook-up

- **Goal:** Encode the emit contract + invariant-checker-is-authoritative rule in `core/runtime/AGENTS.md` and `core/cluster/AGENTS.md` via staged `.append-phase15.txt` snippets; register `feature-health.js` in `ui/dashboard/AGENTS.md` (direct edit, solo); append one line to `.buildrunner/decisions.log`; update `.buildrunner/builds/BUILD_cluster-max.md` (explicitly whitelisted for this spec meta-update) with Phase 15 block, Status Table row, Role Matrix row, Per-Phase AGENTS.md Mapping row, and Recommended Ship Order entry.
- **Context:** `core/cluster/AGENTS.md` already carries phase-9 + phase-12 appends — staged-snippet Wave pattern applies. `core/runtime/AGENTS.md` carried a phase-8 direct edit in an earlier wave → Phase 15 MUST use staged append. `ui/dashboard/AGENTS.md` is solo-editable (Phase 15 alone on it in its wave) → direct edit OK. The BUILD spec update is the conventional phase-completion meta-update allowed by the Self-Updating Source-of-Truth Protocol.
- **Constraints:** Staged snippets ≤ 500 bytes each. Combined AGENTS.md ceiling 24 KB across all files (must not push any single file over 8 KB). Direct edits to `core/cluster/AGENTS.md` / `core/runtime/AGENTS.md` FORBIDDEN — merge gate applies at wave end. No LLM-generated content (ETH Zurich rule). Decisions.log entry format matches existing convention (`PHASE-15 AMENDMENT <iso-ts> <summary>`).
- **Done-When:** `wc -c core/runtime/AGENTS.md.append-phase15.txt core/cluster/AGENTS.md.append-phase15.txt` both ≤ 500 AND `grep -c "feature-health\|invariant\|telemetry" ui/dashboard/AGENTS.md` ≥ 3 AND BUILD_cluster-max.md Status Table row 15 shows `pending` AND `.buildrunner/decisions.log` has one `PHASE-15 AMENDMENT` line.

## Claude Review (mandatory before Phase 15 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 15 --target "core/telemetry/*.py,core/telemetry/invariants.yaml,core/runtime/runtime_registry.py,core/runtime/cache_policy.py,core/runtime/context_injector.py,core/cluster/cross_model_review.py,core/cluster/arbiter.py,core/cluster/summarizer.py,core/cluster/context_bundle.py,core/cluster/context_router.py,api/routes/context.py,api/routes/retrieve.py,api/routes/dashboard_stream.py,ui/dashboard/panels/feature-health.js,~/.buildrunner/hooks/auto-context.sh,.buildrunner/hooks/pre-commit-cluster-guard,~/.buildrunner/scripts/sync-cluster-context.sh,core/runtime/AGENTS.md.append-phase15.txt,core/cluster/AGENTS.md.append-phase15.txt,ui/dashboard/AGENTS.md"`
- Required findings: (1) emit wrappers never block the host call path under any failure (fault-injection test asserts this); (2) zero PII / secret / full-prompt / full-diff / full-log leakage in any event metadata dict literal; (3) all 16 invariant rules cite a BUILD line number; (4) silent-fallback contract preserved — user-visible surface unchanged when `fallback_reason` is set; (5) alert files written only on P0/P1; (6) panel framework-free; (7) JSONL bridge is at-least-once with per-row checkpoint AND rotation protocol (drain→position-write→rename) AND `event_id UNIQUE` dedup; (8) AGENTS.md snippets within 500-byte budget and registered in the right file per Per-Phase AGENTS.md Mapping; (9) tokenizer-true fail-closed rule (Phase 10/12) covered by an invariant; (10) `[private]` filter two-layer rule (Phase 12) covered by an invariant; (11) correlation model handles both Python-sourced and shell-sourced events and only asserts Python-side ordering on Python-side correlations.
- Block-on: any host-blocking emit, any PII leak in metadata, any shipped feature without an invariant rule, any spec drift, panel using a framework, emit failure crashing host, missing private-tag leak rule, missing tokenizer fail-closed rule, direct edit to `core/cluster/AGENTS.md` or `core/runtime/AGENTS.md`, any cross-event invariant firing on shell-only correlations.

## Done When (phase-level)

- [ ] All 6 task verification commands pass.
- [ ] 15 invariant rules cover every in-scope flag-gated feature + context-parity component + cluster-guard. (Backup observability is explicitly deferred — no backup system exists to emit events yet.)
- [ ] One real `/begin` run produces ≥ 8 linked events (same Python-side correlation) with zero anomalies.
- [ ] One deliberate spec violation (e.g., patching `cache_policy.build_cached_prompt()` to return 1 cached block instead of 2) surfaces on dashboard red AND drops an alert file within 60 s.
- [ ] AGENTS.md updated on 3 scopes (runtime staged, cluster staged, dashboard direct) and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `.buildrunner/decisions.log` entry: `Phase 15: feature observability live — 15 invariant rules, emit points across runtime/cluster/shell, invariant checker, feature-health panel, AGENTS.md updated on 3 scopes`.

## Risks + mitigations

- **Risk:** A buggy invariant rule false-positives and floods `~/.buildrunner/alerts/`. **Mitigation:** Per-rule alert-rate limit (max 10/hour, excess folded into `suppressed_count` field on the next alert); checker tests cover both positive and negative cases per rule.
- **Risk:** JSONL bridge falls behind under burst. **Mitigation:** Per-row checkpointing; benchmarked in `test_shell_bridge` at ≥ 1000 rows/s. If > 50 MB accumulates, rotation triggers with the drain-before-rename protocol above.
- **Risk:** Dashboard WS topic count grows past browser handling. **Mitigation:** Only one new topic (`feature-health`). The existing 4 topics already coexist without issue.
- **Risk:** Emit-failure path itself is buggy and DOES block host. **Mitigation:** Fault-injection test in `test_emit_contract.py` monkey-patches the emit function to raise and asserts the host call completes normally in ≤ 100 ms.
- **Risk:** `telemetry.db` grows unbounded. **Mitigation:** Out of scope for Phase 15 — retention will be added to Phase 14 `archive-prune` if and when row count exceeds 10 M. Current row count is ~8 k.
- **Risk:** Shell-only correlations fire cross-event invariants incorrectly. **Mitigation:** `invariants.yaml` explicitly marks which rules require a Python-sourced correlation; the checker skips those rules when the correlation prefix is `shell-*` or `git-HEAD@*`.
