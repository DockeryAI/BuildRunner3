# Amendment Plan: Dashboard Unification (Phase 16)

**Amendment date:** 2026-04-22
**Base build:** BUILD_cluster-max.md
**New content:** Phase 16 only. Phases 0–15 are already specified in the BUILD — stub headings below exist solely to satisfy the spec-gate plan/BUILD phase-count and title-parity check. Do not interpret the stubs as canonical descriptions.

---

### Phase 0: AGENTS.md Authoring (Codex Scoping Foundation)

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 1: Hardware Installation, BIOS & Overclocking

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 2: Below Activation

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 3: Jimmy Activation

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 4: Cluster Reconfiguration — 7 Workers

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 5: Below Skill Integration

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 6: Runtime Registry Extension (OllamaRuntime)

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 7: RuntimeRegistry Shim + Cluster Guard

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 8: Prompt Cache Engineering + Summarize-Before-Escalate

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 9: 3-Way Adversarial Review + Opus 4.7 Arbiter

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 10: Auto-Context Hook (PromptSubmit + PhaseStart)

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 11: Cluster Max Dashboard @ Port 4400

Locked — already COMPLETE in BUILD spec. Panels shipped to `ui/dashboard/` (FastAPI experiment). This amendment's Phase 16 retires that surface and relocates equivalents to `~/.buildrunner/dashboard/` (the real :4400 Node dashboard). Spec path references are corrected by Task 16.5.

---

### Phase 12: Multi-Model Context Parity (Logs, Memory, Research)

Locked — already COMPLETE in BUILD spec. No changes in this amendment.

---

### Phase 13: Direct Cutover + Post-Cutover Smoke

Pending — already specified in BUILD spec. No changes in this amendment.

---

### Phase 14: BR3 Self-Maintenance

Pending — already specified in BUILD spec. No changes in this amendment.

---

### Phase 15: Feature Observability (Passive Real-Usage Telemetry)

Pending — already specified in BUILD spec. This amendment adds `Phase 16` to Phase 15's `Blocked by` list (feature-health panel must live on :4400 before the invariant UI overlay can render). Phase 15 panel path references are corrected from `ui/dashboard/panels/feature-health.js` to `~/.buildrunner/dashboard/public/js/ws-cluster-feature-health.js` by Task 16.5. No other changes to Phase 15 scope.

---

### Phase 16: Dashboard Unification — Backport Cluster Panels to :4400

**Status:** pending
**Codex model:** gpt-5.4
**Codex effort:** medium (no security/architecture deltas warrant xhigh)
**Worktree:** main repo (touches `~/.buildrunner/dashboard/` + `api/routes/dashboard_stream.py` + two BUILD specs; disjoint from Phase 13/14 file sets)
**Blocked by:** Phase 11 (panel source code must exist — already COMPLETE), Phase 6 of BUILD_cluster-activation.md (telemetry emit sites — already COMPLETE)
**Blocks:** Phase 15 (invariant checker UI overlay requires feature-health panel on :4400)
**Can parallelize:** No — tasks are strictly sequential (readers before panels before retirement before acceptance)
**Added:** 2026-04-22 (amendment via /amend-codex)

#### Goal

Unify the cluster observability surface on the real Node dashboard at `http://localhost:4400`. Retire the FastAPI experiment at `ui/dashboard/` (whose standalone entry point is also coded to :4400 — a live collision risk) and the orphan uvicorn process on :4401. Backport the five cluster panels (feature-health, node-health detail, overflow-reserve, storage-health, consensus-viewer) onto the Node dashboard's existing SSE transport. Add Jimmy to the dashboard's node list. Execute the cluster-activation Phase 6 acceptance criterion that was never actually run against :4400.

#### Context

BUILD_cluster-activation.md Phase 6 shipped a feature-health panel into `ui/dashboard/` (FastAPI) assuming that was the dashboard. The real operator dashboard is `~/.buildrunner/dashboard/` (Node, :4400, sidebar with builds/intel/terminal/research/monitor). Phase 6 was marked COMPLETE without anyone verifying :4400 rendered the panel — it didn't. Separately, BUILD_cluster-max.md Phase 11 shipped four additional panels to the same `ui/dashboard/` directory, inheriting the same drift. The emit side (`core/runtime/runtime_registry.py`, `core/runtime/cache_policy.py`, `core/cluster/cross_model_review.py`, `scripts/codex-bridge.sh`) writes correctly to `.buildrunner/telemetry.db` — verified live, 16+ `runtime_dispatched`, 24+ `cache_hit`, 22+ `adversarial_review_ran` events within the last hour. Only the read-and-render path is on the wrong surface. Also: `NODE_NAMES` in `~/.buildrunner/dashboard/events.mjs:226` hardcodes 6 nodes and is missing Jimmy, blocking every panel that needs a 7-node baseline.

#### Tasks (Codex four-element format)

**Task 16.1: Stop :4401 orphan and remove FastAPI standalone dashboard entry**

- **Goal:** Kill the orphan uvicorn process on :4401 (PID 25376) and remove the dashboard-serving surface from `api/routes/dashboard_stream.py` — specifically the module-level `app = create_app(role="dashboard")` export and any `uvicorn` launch script that targets it — so no Python process can serve a dashboard on any port.
- **Context:** `api/routes/dashboard_stream.py` exports `app = create_app(role="dashboard")` at module scope; there is no `if __name__ == "__main__"` block, but the module-level `app` is sufficient for any `uvicorn api.routes.dashboard_stream:app` invocation to bind a port. PID 25376 is the current :4401 experiment started that way. The `_collect_*` collector functions in the same module are imported elsewhere and must remain callable as a library.
- **Constraints:** Keep every `_collect_*` function callable as a library import. Do not remove `core/telemetry/event_schemas.py` event types or the emit sites. Do not touch LaunchAgent plists for the Node dashboard on :4400. If a LaunchAgent or launch shell script exists for the FastAPI experiment, remove it. If the module needs the `app` export for other roles, gate it so `role="dashboard"` cannot be selected by a standalone uvicorn invocation.
- **Done-When:** `lsof -nP -iTCP:4401 -sTCP:LISTEN` returns empty AND `grep -n 'app = create_app(role=.dashboard.)' api/routes/dashboard_stream.py` returns no matches AND `grep -rn 'uvicorn.*dashboard_stream' ~/.buildrunner/scripts/ api/ core/ deploy/ 2>/dev/null` returns no matches AND `pytest -q tests/ -k dashboard_stream` passes (or reports "no tests ran" if none exist — the important assertion is no new failures).

**Task 16.2: Add Jimmy to Node dashboard NODE_NAMES and verify card**

- **Goal:** Extend the node-health reachability list in `~/.buildrunner/dashboard/events.mjs` to include `jimmy` so the existing card and all downstream cluster panels have a 7-node baseline.
- **Context:** `~/.buildrunner/dashboard/events.mjs:226` currently declares `NODE_NAMES = ['muddy','lockwood','walter','otis','lomax','below']`. Jimmy is the memory/semantic node at 10.0.1.106 and is reachable with the same SSH/ping pattern as the other six. `~/.buildrunner/cluster.json` already lists Jimmy.
- **Constraints:** Do not refactor the card layout in this task (the 7-tile metric grid lands in 16.4). No change to the SSH/ping check logic — just add the entry. Must not break the existing six tiles.
- **Done-When:** `curl -s localhost:4400/api/nodes | jq 'length'` returns 7 AND opening http://localhost:4400 shows a `jimmy` row in the node-health card AND `npm test --prefix ~/.buildrunner/dashboard` passes.

**Task 16.3: Build telemetry.db, Jimmy-status, and local-health readers**

- **Goal:** Add three Node.js integration modules under `~/.buildrunner/dashboard/integrations/` that produce the data shapes the five cluster panels need, swallowing errors gracefully when sources are absent.
- **Context:** Reference collectors in `api/routes/dashboard_stream.py`: `_collect_feature_health` at line 178, `_collect_node_health` at line 78, `_collect_storage_health` at line 107. Telemetry DB at `.buildrunner/telemetry.db` (SQLite, event types `runtime_dispatched`, `cache_hit`, `context_bundle_served`, `adversarial_review_ran`). Jimmy publishes `/srv/jimmy/status/nodes/*.json`, `overflow-reserve.json`, `storage-health.json`, `disk-guard.json`. Existing integration style in `integrations/lockwood.mjs` / `walter.mjs` / `lomax.mjs`.
- **Constraints:** Open telemetry.db read-only. Use `better-sqlite3` if present in the dashboard `package.json`, otherwise `sqlite3`. When DB or Jimmy filesystem is absent, return `status: "yellow"` with a human-readable `reason` field describing the missing source (matches the `_collect_feature_health` contract in `api/routes/dashboard_stream.py:178–381` which produces `yellow` with reason on missing inputs, never `unknown`). Match existing integration-module export shape. Do not add new top-level npm dependencies without checking `package.json` first. Feature-health tile outputs MUST be one of `green`, `yellow`, `red` — `unknown` is forbidden per the Phase 6 success criterion.
- **Done-When:** `node -e "import('./integrations/telemetry-reader.mjs').then(m=>m.collectFeatureHealth()).then(t=>console.log(t.length))"` prints `15` AND `node -e "import('./integrations/jimmy-status.mjs').then(m=>m.collectOverflowReserve()).then(console.log)"` prints JSON without throwing when `/srv/jimmy/status/` is missing AND new readers have matching tests under `~/.buildrunner/dashboard/tests/` that pass.

**Task 16.4: Add five SSE topics and port the five panels to :4400**

- **Goal:** Extend `events.mjs` with periodic collectors that broadcast `feature-health`, `node-health`, `overflow-reserve`, `storage-health`, and `consensus` typed SSE events, and port the five panels from `ui/dashboard/panels/` to `~/.buildrunner/dashboard/public/js/ws-cluster-*.js` rendered inside a new Cluster sidebar section.
- **Context:** Dashboard uses SSE on `/api/events/stream` — not WebSocket — for all panels except the terminal. Existing pattern in `public/js/ws-builds.js`, `ws-intel.js`, `ws-tests.js`. Panel intervals from `dashboard_stream.py:388–402`: node-health 5s, overflow-reserve 10s, feature-health 15s, consensus 20s, storage-health 60s. The 15 feature-health tile rules live in `_collect_feature_health` at `dashboard_stream.py:178–381`.
- **Constraints:** Translate the 15 tile rules verbatim — no semantic changes, thresholds identical. Follow the `ws-*.js` module pattern (no React, no new frameworks). Add a new "Cluster" sidebar entry in `public/index.html`, do not cram five panels into the existing Dashboard workspace. Reuse the readers from Task 16.3 — do not re-query SQLite or filesystem in panel JS. Add the five new event type names (`feature-health`, `node-health`, `overflow-reserve`, `storage-health`, `consensus`) to the `VALID_TYPES` set in `events.mjs` — without this, the event validator will drop every broadcast. Feature-health tiles emitted over SSE MUST use `green`, `yellow`, or `red` — never `unknown`; tile 6 is `green` ⟺ Jimmy publisher online, else `yellow` with reason.
- **Done-When:** The five new event types appear in `grep -n VALID_TYPES ~/.buildrunner/dashboard/events.mjs` output AND `curl -sN --max-time 20 http://localhost:4400/api/events/stream | awk '/^data: /{sub(/^data: /,""); print; c++; if(c>=30)exit}' | jq -s 'map(.type) | unique'` contains all five topic names within 60s AND opening http://localhost:4400 shows a Cluster sidebar entry with all five panels rendering AND every tile in the feature-health panel has `status` ∈ {`green`,`yellow`,`red`} (zero `unknown`, zero other values).

**Task 16.5: Retire ui/dashboard/ and correct two BUILD specs**

- **Goal:** Archive the FastAPI panel experiment and update both BUILD specs so their deliverable paths and acceptance URLs point at the Node dashboard on :4400.
- **Context:** `ui/dashboard/` contains `index.html`, `app.js`, `styles.css`, `AGENTS.md`, and `panels/{node-health,overflow-reserve,storage-health,consensus-viewer,feature-health}.js`. `BUILD_cluster-activation.md` Phase 6 success criterion references :4400 but panel paths point at `ui/dashboard/`. `BUILD_cluster-max.md` Phase 11 (line 219 region) and Phase 15 (lines 1686–1754) reference `ui/dashboard/panels/feature-health.js`.
- **Constraints:** Move `ui/dashboard/` to `archive/ui-dashboard-fastapi-experiment/` with a `README.md` explaining the drift and retirement — do not `rm -rf`. Keep Python collectors in `api/routes/dashboard_stream.py` as an importable library. Spec edits: change panel paths to `~/.buildrunner/dashboard/public/js/ws-cluster-*.js` + `~/.buildrunner/dashboard/integrations/*.mjs`; acceptance URLs stay `http://localhost:4400`. Do not rewrite phase structure or success criteria beyond path corrections.
- **Done-When:** `test ! -d ui/dashboard` passes AND `test -d archive/ui-dashboard-fastapi-experiment` passes AND `grep -R "ui/dashboard" .buildrunner/builds/` returns no matches AND `grep -c "~/.buildrunner/dashboard" .buildrunner/builds/BUILD_cluster-activation.md .buildrunner/builds/BUILD_cluster-max.md` both return > 0.

**Task 16.6: Walk cluster-activation Phase 6 acceptance end-to-end on :4400**

- **Goal:** Execute the Phase 6 success criterion that was never validated against :4400, confirm zero-unknown on feature-health with Jimmy publisher live, and record the verified state so this drift cannot recur silently.
- **Context:** `BUILD_cluster-activation.md` Phase 6 acceptance: run `/autopilot BUILD_cluster-max`; tiles 1/3/5 turn green within seconds; all 15 resolve to green/yellow/red with zero "unknown." Tiles 6–10 depend on Jimmy publishing `/srv/jimmy/status/nodes/*.json` — that publisher is the cluster-activation Phase 5 deliverable; if absent, tiles stay yellow.
- **Constraints:** If Jimmy's status publisher is not running, start it per cluster-activation Phase 5 documentation — do not mock data, do not lower the "zero unknown" bar. If a tile stays unknown after Jimmy is live, investigate root cause and repair before marking this task done. Record the verified snapshot as an artifact in `.buildrunner/adversarial-reviews/`, not a screenshot in a commit message.
- **Done-When:** `curl -sN --max-time 30 http://localhost:4400/api/events/stream | awk '/^data: /{sub(/^data: /,"");print}' | jq -c 'select(.type=="feature-health") | .data.tiles' | head -1 | jq 'length == 15 and (map(select(.status!="green" and .status!="yellow" and .status!="red")) | length == 0)'` returns `true` AND `.buildrunner/adversarial-reviews/phase-16-acceptance.json` exists with the full 15-tile snapshot and `pass: true` marker AND `.buildrunner/decisions.log` has a Phase-16-acceptance entry.

#### Files (whitelist)

- **Node dashboard (MODIFY):** `~/.buildrunner/dashboard/events.mjs`, `~/.buildrunner/dashboard/public/index.html`, `~/.buildrunner/dashboard/public/styles.css`
- **Node dashboard (NEW):** `~/.buildrunner/dashboard/public/js/ws-cluster-feature-health.js`, `ws-cluster-node-health.js`, `ws-cluster-overflow-reserve.js`, `ws-cluster-storage-health.js`, `ws-cluster-consensus.js`; `~/.buildrunner/dashboard/integrations/telemetry-reader.mjs`, `jimmy-status.mjs`, `cluster-health-local.mjs`
- **Python (MODIFY):** `api/routes/dashboard_stream.py` (remove standalone uvicorn entry; keep `_collect_*` as library)
- **Archive (MOVE):** `ui/dashboard/` → `archive/ui-dashboard-fastapi-experiment/` (+ README.md)
- **Spec (MODIFY):** `.buildrunner/builds/BUILD_cluster-activation.md` (Phase 6 panel paths), `.buildrunner/builds/BUILD_cluster-max.md` (Phase 11 + Phase 15 panel paths; Phase 15 Blocked-by)
- **Tests (NEW):** `~/.buildrunner/dashboard/tests/integrations-telemetry.spec.mjs`, `integrations-jimmy-status.spec.mjs`, `ws-cluster-feature-health.spec.mjs`
- **Decisions (APPEND):** `.buildrunner/decisions.log`

#### Constraints (canonical)

- No new dashboard process on a new port. One dashboard, one port (:4400), one transport (SSE on `/api/events/stream`; terminal WS stays on `/ws/terminal/:node`).
- Tile rules ported verbatim from `_collect_feature_health` — no threshold changes, no re-interpretation. If a rule needs adjustment, open a follow-up amendment; do not edit in flight.
- Readers swallow errors and return `status: "yellow"` with a `reason` field on missing sources (matching the `_collect_feature_health` fallback contract — `unknown` is forbidden). Dashboard must render even if `.buildrunner/telemetry.db` or `/srv/jimmy/status/` is absent.
- `VALID_TYPES` in `events.mjs` gates every SSE broadcast; the five new topic names must be added or the dashboard will silently drop every cluster event.
- FastAPI `_collect_*` functions remain importable — do not delete, do not reduce API surface; only the uvicorn standalone entry is removed.
- Archive, do not delete. `ui/dashboard/` moves to `archive/ui-dashboard-fastapi-experiment/` with a README explaining the drift and retirement date.
- Spec edits touch only path references and Phase 15's Blocked-by. Phase structure, success criteria, and numbering remain intact.
- Max 6 tasks per phase respected. Each task completable in a single Plan→Edit→Run→Observe→Repair→Document loop.

#### Claude Review (mandatory before Phase 16 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 16 --target "~/.buildrunner/dashboard/events.mjs,~/.buildrunner/dashboard/public/index.html,~/.buildrunner/dashboard/public/js/ws-cluster-*.js,~/.buildrunner/dashboard/integrations/telemetry-reader.mjs,~/.buildrunner/dashboard/integrations/jimmy-status.mjs,~/.buildrunner/dashboard/integrations/cluster-health-local.mjs,api/routes/dashboard_stream.py,archive/ui-dashboard-fastapi-experiment/README.md,.buildrunner/builds/BUILD_cluster-activation.md,.buildrunner/builds/BUILD_cluster-max.md"`
- Required findings: (1) feature-health tile rules match `_collect_feature_health` byte-for-byte in semantic behavior; (2) all five SSE topics emit at the FastAPI-specified cadences; (3) telemetry reader opens DB read-only; (4) error-swallowing returns unknown rather than crashing; (5) no new npm dependencies without package.json update; (6) ui/dashboard/ archived not deleted; (7) Phase 15 Blocked-by updated; (8) no new ports bound; (9) LaunchAgent for FastAPI experiment removed if present; (10) Jimmy added to `NODE_NAMES`.

#### Done When

- [ ] All 6 task verification commands pass.
- [ ] `lsof -nP -iTCP:4401 -sTCP:LISTEN` returns empty (no orphan FastAPI process).
- [ ] `curl -s localhost:4400/api/nodes | jq 'length'` returns 7 (Jimmy included).
- [ ] All five cluster panels render on `http://localhost:4400` under a "Cluster" sidebar section.
- [ ] Feature-health tile `"status":"unknown"` count = 0 with telemetry.db + Jimmy publisher live.
- [ ] `ui/dashboard/` archived to `archive/ui-dashboard-fastapi-experiment/` with README.
- [ ] BUILD_cluster-activation.md + BUILD_cluster-max.md spec path references corrected (no `ui/dashboard/` references remain in `.buildrunner/builds/`).
- [ ] Phase 15 `Blocked by` updated to include Phase 16.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `.buildrunner/decisions.log` entry: `Phase 16: dashboard unification live — 5 panels backported to :4400 Node dashboard, FastAPI experiment archived, Jimmy added to node list, cluster-activation Phase 6 acceptance walked with zero-unknown`.
