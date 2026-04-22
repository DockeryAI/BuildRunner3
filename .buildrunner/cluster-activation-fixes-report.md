# cluster-activation fixes report

## Summary

This pass fixed the verified repo-side gaps from `BUILD_cluster-activation` and validated them with file-scoped tests. Two live-machine fixes were also investigated and confirmed broken, but could not be deployed from this session because the current sandbox forbids writes outside the repo workspace.

## Fixed in repo

### Phase 4 — adversarial telemetry emits only when enabled

- Updated `core/cluster/cross_model_review.py` so `adversarial_review_ran` emits only when `BR3_ADVERSARIAL_3WAY=on`.
- Added regression coverage in `tests/cluster/test_adversarial_3way_flag.py` for both states:
  - flag OFF leaves the `adversarial_review_ran` row count unchanged
  - flag ON inserts one row

### Phase 6 — `context_bundle_served` metadata no longer double-encodes

- Updated `scripts/br-emit-event.sh` to unwrap double-encoded JSON strings before writing telemetry.
- Added regression coverage in `tests/telemetry/test_new_event_types.py`.
- Cleaned bad local rows from `.buildrunner/telemetry.db` with:

  ```sql
  DELETE FROM events
  WHERE event_type='context_bundle_served'
    AND (metadata LIKE '%"raw"%' OR metadata LIKE '%xxxxxxxx%');
  ```

- Emitted a fresh local verification event and confirmed the newest row shape is:

  ```json
  { "phase": "2", "task": "dispatch" }
  ```

### Phase 6 — `runtime_dispatched.success` now reflects failures

- Updated `core/runtime/runtime_registry.py` so `runtime_dispatched.success` is derived from the dispatch return code instead of being hardcoded to `1`.
- Runtime execution paths now emit `success=0` when the runtime result is not successful.
- CLI validation failures (including malformed spec / missing spec → exit `3`) now also emit a failure event.
- Added regression coverage in `tests/cluster/test_runtime_dispatch_cli.py` asserting malformed spec emits `success=0` and `metadata.returncode == 3`.

### Phase 1 — live context test now asserts real behavior

- Split `tests/integration/test_context_codex_live.py` into:
  - flag ON → assert HTTP `200`, `bundle.phase`, `bundle.model`, and `budget.{limit,used,tokenizer}`
  - flag OFF → assert HTTP `503` and explicit flag-off response content
- Updated `api/routes/context.py` to echo the requested `phase` in the returned bundle so the live test can assert it directly.

### Docs / spec / governance

- Updated `core/runtime/AGENTS.md` and `core/cluster/AGENTS.md` to use `BR3_LOCAL_ROUTING` as the canonical flag and note `BR3_RUNTIME_OLLAMA` as a deprecated alias shim.
- Corrected stale BUILD spec paths in `.buildrunner/builds/BUILD_cluster-activation.md` to match the shipped tree:
  - `api/node_semantic.py` → `core/cluster/node_semantic.py`
  - `core/review/cross_model_review.py` → `core/cluster/cross_model_review.py`
  - `core/cache/cache_policy.py` → `core/runtime/cache_policy.py`
- Renamed `.buildrunner/bypass-justification.md` to `.buildrunner/bypass-justification-4-7-optimization.md`.
- Added `.buildrunner/bypass-justification-cluster-activation.md` summarizing the cluster-activation override.

## Verified

- `tests/cluster/test_adversarial_3way_flag.py` — passed (`13 passed`)
- `tests/telemetry/test_new_event_types.py` — passed (`14 passed`)
- `tests/cluster/test_runtime_dispatch_cli.py` — passed (`10 passed`)
- `tests/integration/test_context_codex_live.py` — source assertion passed; live-network tests skipped when Jimmy was unreachable from this environment

## Investigated but not deployed from this session

### Critical Fix 1 — cluster-daemon LaunchAgent — RESOLVED

Applied post-codex by the orchestrator:

- Edited `~/Library/LaunchAgents/com.br3.cluster-daemon.plist`:
  - `ProgramArguments[0]`: `/usr/local/bin/node` → `/opt/homebrew/bin/node`
  - `EnvironmentVariables.PATH`: prepended `/opt/homebrew/bin` so future `node`/`npm` invocations resolve on Apple Silicon
- `launchctl bootout gui/$(id -u)/com.br3.cluster-daemon` → "No such process" (old process already dead)
- `launchctl bootstrap gui/$(id -u) ~/Library/LaunchAgents/com.br3.cluster-daemon.plist`
- `launchctl print gui/$(id -u)/com.br3.cluster-daemon` now shows: `state = running`, `active count = 1`, `runs = 1`, `last exit code = (never exited)`

### Critical Fix 2 — live dashboard feature-health deployment — ARCHITECTURAL GAP

Inspection revealed the two dashboards are **different applications**, not two copies of the same one:

- `~/.buildrunner/dashboard/` — Node app (`events.mjs` + `public/js/ws-*.js`) currently serving :4400
- `ui/dashboard/` — FastAPI app (`api/routes/dashboard_stream.py` + `panels/*.js`) built by Phase 11/Phase 6 but never started

Deploying the `feature-health` panel into the Node dashboard is not a copy-paste — the data paths, panel registration, and WS topic contract all differ. Treating this as a simple deploy would silently ship broken glue.

Correct path forward (requires user decision):

1. **Option A — cutover:** stop the Node dashboard supervisor, start `uvicorn api.routes.dashboard_stream:app --port 4400`. Phase 6 feature-health panel works immediately. Loses the Node dashboard's feature set unless ported.
2. **Option B — coexist:** run the new FastAPI dashboard on a different port (e.g. 4401) alongside the Node one for validation, then cut over.
3. **Option C — backport panel:** port `feature-health.js` into the Node dashboard's WS architecture (`js/ws-*.js` pattern).

Manual validation command for Option B right now:

```bash
uvicorn api.routes.dashboard_stream:app --host 0.0.0.0 --port 4401
# visit http://localhost:4401/ — feature-health panel should render 15 tiles
```

Until a decision is made, Phase 6's success criterion ("15 tiles on :4400") does not hold on the live server. Logged as an open gap in `.buildrunner/decisions.log`.

## Skipped by instruction

- Jimmy Context API `:4500` service start on Jimmy — requires SSH to `10.0.1.106`
- Walter node offline remediation — requires Walter hardware

Both were logged in `.buildrunner/decisions.log` per instruction.
