# Build: Dashboard Build Liveness Detection

**Created:** 2026-04-07
**Status:** Phases 1-6 Complete — Phase 6 In Progress
**Deploy:** local — dashboard event server restart (`kill $(pgrep -f "node events.mjs"); cd ~/.buildrunner/dashboard && node events.mjs &`)

## Overview

The dashboard's BUILD spec scanner reads markdown status lines every 30s and marks builds as `running` when any phase says `in_progress`. If the agent process dies, the spec stays `in_progress` forever and the dashboard lies. The session detection system already polls `ps aux` every 15s on all cluster nodes and knows which Claude processes are alive. These two systems are not connected.

This build connects them: the scanner cross-references sessions with builds, introduces a `stalled` status for builds with no live process, and updates the frontend to show accurate state and dispatch buttons.

**Builds On:** Existing dashboard event server, session polling, BUILD spec scanner

**DO NOT (Phases 1-3):**

- Add new polling loops
- Modify sessions.mjs

**RELAXED for Phases 4-9:**

- New files allowed: `build-sidecar.sh`, `test-sidecar.sh`
- `registry.mjs` already modified in Phase 3
- `_dispatch-core.sh` cleanup allowed

**Adversarial Review:** Completed 2026-04-07 via local subagent. 4 blockers found and resolved (re-entrancy guard, remote heartbeat skip, project_path matching, empty assigned_node). 9 warnings incorporated (grace period, both KPIs, ad-hoc stale removal, workfloDock paths).

## Parallelization Matrix

| Phase | Key Files                                                           | Can Parallel With | Blocked By                         |
| ----- | ------------------------------------------------------------------- | ----------------- | ---------------------------------- |
| 1     | `events.mjs` (scanner function)                                     | -                 | -                                  |
| 2     | `index.html`, `ws-builds.js`                                        | -                 | 1 (needs stalled status to render) |
| 3     | `events.mjs`, `registry.mjs`                                        | -                 | 2                                  |
| 4     | `build-sidecar.sh` (NEW)                                            | 8                 | 3                                  |
| 5     | `events.mjs` (scanner), `integrations/*`                            | -                 | 4                                  |
| 6     | `dispatch-to-node.sh`, `_dispatch-core.sh`, `events.mjs` (dispatch) | 7                 | 5                                  |
| 7     | `autopilot-executor-prompt.md`                                      | 6                 | 4                                  |
| 8     | `index.html`, `ws-builds.js`, `styles.css`                          | 4                 | 3                                  |
| 9     | `test-sidecar.sh` (NEW)                                             | -                 | 6, 7                               |

**Optimal execution (Phases 4-9):**

- Batch 1: Phase 4 (backend → agent) + Phase 8 (frontend → inline)
- Batch 2: Phase 5 (scanner PID rewrite)
- Batch 3: Phase 6 (dispatch) + Phase 7 (resume) — parallel, different files
- Batch 4: Phase 9 (integration test)

## Phases

### Phase 1: Scanner Liveness Check + Stalled Status

**Status:** ✅ COMPLETE
**Goal:** Scanner detects dead builds and marks them `stalled` in the registry. Self-corrects when processes return.
**Files:**

- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — scanner function, VALID_TYPES

**Blocked by:** None
**Deliverables:**

- [ ] Add `'build.stalled'` to VALID_TYPES set (line 156, adjacent to other build.\* entries)
- [ ] Make `scan()` function async with re-entrancy guard (`let scanning = false; if (scanning) return;`)
- [ ] After `newStatus = 'running'`, add liveness check:
  - Call `getActiveSessions(false)` (cached, no SSH overhead)
  - Match sessions to builds by `project_path` (not project name) — compare session CWD path against `build.project_path`
  - Also match by `assigned_node` if set — session node must match build node
  - Skip liveness check entirely if `build.assigned_node` is empty (never dispatched)
  - If no live session: increment a `_stall_count` counter on the build object
  - If `_stall_count >= 2`: set `newStatus = 'stalled'` (grace period prevents flapping)
  - If live session found: reset `_stall_count = 0` (self-correction)
- [ ] For local builds only: check heartbeat staleness as secondary signal — read `.buildrunner/locks/phase-*/heartbeat`, if >5 min old treat as confirming stalled (skip for remote nodes)
- [ ] Emit `build.stalled` event when transitioning from `running` to `stalled`
- [ ] Ensure liveness check only runs when `newStatus === 'running'` — never override `complete` with `stalled`

**Success Criteria:** Kill a Claude process working on a build. Within 60s (2 scanner cycles), registry shows `stalled` instead of `running`. Redispatch the build, within 30s registry shows `running` again.

### Phase 2: Frontend Stalled State

**Status:** ✅ COMPLETE
**Goal:** Dashboard renders `stalled` builds with distinct styling and correct action buttons in both views.
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY) — badge CSS, actions column, badge class mapping, KPI
- `~/.buildrunner/dashboard/public/js/ws-builds.js` (MODIFY) — card CSS, statusColor, badgeClass, canDispatch, KPI

**Blocked by:** Phase 1 (needs `stalled` status in registry)
**Deliverables:**

index.html:

- [ ] Add `.badge-stalled` CSS (orange/amber to distinguish from pending)
- [ ] Add `stalled` to badge class mapping in renderBuilds()
- [ ] Update actions column (~line 1330): add `'stalled'` to list that shows Dispatch button
- [ ] Remove ad-hoc `stale` detection (`const stale = status === 'running' && !hasSession`) — backend handles this now
- [ ] KPI (~line 1277): add stalled count display (separate from active, like failed)

ws-builds.js:

- [ ] Add `.bws-build-card.status-stalled` CSS (orange border)
- [ ] `statusColor()`: stalled returns `var(--orange)`
- [ ] `badgeClass()`: stalled returns `'badge-stalled'`
- [ ] Add `'stalled'` to `canDispatch` status list (keep `'running'` — intentional for re-dispatch)
- [ ] Add `'stalled'` to status filter dropdown options
- [ ] KPI (`renderKPI()`): add stalled count

**Success Criteria:** Stalled build shows orange badge, Dispatch button (not Pause), and has separate stalled count in KPI. Running build shows blue badge with Pause button. No more ad-hoc stale detection in frontend.

### Phase 3: Auto-Redispatch Watchdog _(added: 2026-04-07)_

**Status:** ✅ COMPLETE
**Blocked by:** Phase 2 (complete)
**Goal:** When the scanner marks a build `stalled`, automatically re-dispatch it if the build opts in. Prevents dead builds sitting idle on cluster nodes.
**Adversarial review:** 3 blockers resolved (race condition, registry field whitelist, dispatch method). 3 warnings incorporated (no count reset on auto-running, exact invocation, cooldown).
**Files:**

- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — auto-redispatch in scanner
- `~/.buildrunner/scripts/registry.mjs` (MODIFY) — add `auto-redispatch` flag to cmdUpdate whitelist

**Deliverables:**

- [x] Add `auto-redispatch` flag to registry.mjs cmdUpdate whitelist _(added: 2026-04-07)_
- [x] Add `redispatching` Set + `redispatchCounts` map in scanner closure for in-flight tracking _(added: 2026-04-07)_
- [x] On stalled + `auto_redispatch === true`: add to `redispatching` Set, dispatch using `exec('bash DISPATCH_SCRIPT ... &')` for remote nodes or `spawn('claude', [...], {detached:true, stdio:['pipe','ignore','ignore']})` for local _(added: 2026-04-07)_
- [x] Remove from `redispatching` Set when status changes to `running` or after 5min timeout _(added: 2026-04-07)_
- [x] Max 3 redispatches — only reset count on manual dispatch or `complete`, NOT on auto-`running` transition _(added: 2026-04-07)_
- [x] After 3 failures, set status to `failed` with event `build.failed` _(added: 2026-04-07)_
- [x] Add `'build.redispatched'` to VALID*TYPES, emit on each auto-redispatch *(added: 2026-04-07)\_
- [x] Dashboard Dispatch All sets `auto_redispatch: true` on dispatched builds via registry update _(added: 2026-04-07)_

**Success Criteria:** Dispatch a build with auto_redispatch, kill the Claude process. Within 90s, a new session appears. After 3 kills, build shows `failed`.

### Phase 4: Build Sidecar Script _(added: 2026-04-07)_

**Status:** ✅ COMPLETE
**Blocked by:** Phase 3 (complete)
**Goal:** Wrapper script for every Claude dispatch. Writes PID file, heartbeats every 15s, `git stash create` snapshots, exit status on death. Maximum work loss: 15 seconds.
**Files:**

- `~/.buildrunner/scripts/build-sidecar.sh` (NEW)

**Deliverables:**

- [x] Accept args: `BUILD_ID`, `PHASE_NUM`, `PROJECT_PATH`, plus the Claude command to wrap _(added: 2026-04-07)_
- [x] Start Claude as child process, capture its PID _(added: 2026-04-07)_
- [x] Write `sidecar.json` to `.buildrunner/locks/phase-N/`: `{ sidecar_pid, claude_pid, build_id, node, started_at }` _(added: 2026-04-07)_
- [x] Background loop every 15s: write heartbeat, verify Claude PID alive via `kill -0`, run `git stash create` and tag as `wip-rescue-${BUILD_ID}` (overwrite each cycle) _(added: 2026-04-07)_
- [x] Skip tagging if `git stash create` returns empty (clean working tree) _(added: 2026-04-07)_
- [x] Handle `git stash create` failure gracefully (skip, don't crash) — guards against concurrent git ops _(added: 2026-04-07)_
- [x] EXIT trap: final `git stash create` + tag, write `exit-status.json` with `{ exit_code, rescue_tag, timestamp }` _(added: 2026-04-07)_
- [x] If background loop detects Claude PID dead: final snapshot, write exit-status, exit sidecar _(added: 2026-04-07)_
- [x] Cross-platform: macOS (Muddy/Otis/Lomax) and Linux/WSL (Below) _(added: 2026-04-07)_

**Success Criteria:** Wrap `sleep 60` in sidecar. Verify `sidecar.json` written with correct PIDs. Kill sleep. Within 15s, `exit-status.json` appears. `wip-rescue-*` tag exists if working tree was dirty.

### Phase 5: Scanner PID-Based Liveness + Dead Code Cleanup _(added: 2026-04-07)_

**Status:** ✅ COMPLETE
**Blocked by:** Phase 4
**Goal:** Replace fuzzy session-path matching with exact PID verification via sidecar.json. Clean dead code from integrations/. Falls back to existing behavior for non-sidecar builds.
**Adversarial review:** Findings from 6-agent analysis (2026-04-07): scanner lines 1694-1743 contain fuzzy matching, heartbeat check, grace period — all demoted to fallback. below.mjs entirely dead. reviews.mjs and decisions.mjs have unused exports.
**Files:**

- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — scanner liveness rewrite
- `~/.buildrunner/dashboard/integrations/below.mjs` (DELETE) — entirely dead, never imported
- `~/.buildrunner/dashboard/integrations/reviews.mjs` (MODIFY) — remove unused exports
- `~/.buildrunner/dashboard/integrations/decisions.mjs` (MODIFY) — remove unused exports

**Deliverables:**

Scanner liveness (events.mjs):

- [x] Before session matching: check for `sidecar.json` in build's lock dir (`build.project_path + /.buildrunner/locks/phase-N/sidecar.json`) _(added: 2026-04-07)_
- [x] If sidecar.json exists + local node: `process.kill(claude_pid, 0)` in try/catch — alive=running, dead=stalled (no grace period) _(added: 2026-04-07)_
- [x] If sidecar.json exists + remote node: `execSync('ssh ... kill -0 PID')` with 5s timeout _(added: 2026-04-07)_
- [x] If sidecar.json missing: fall back to existing `getActiveSessions` fuzzy matching (backward compat) _(added: 2026-04-07)_
- [x] Check `exit-status.json` — if present, include exit code in stalled event data _(added: 2026-04-07)_
- [x] Add file locking around registry write at end of scan (prevent race with registry.mjs CLI) _(added: 2026-04-07)_

Dead code cleanup:

- [x] Delete `integrations/below.mjs` — all 4 exports unused, never imported _(added: 2026-04-07)_
- [x] Remove `getReviewFindings()` and `retriggerAutoReview()` from `reviews.mjs` — exported but never called _(added: 2026-04-07)_
- [x] Remove `getAllDecisions()` and `watchDecisionFiles` export from `decisions.mjs` — never called externally _(added: 2026-04-07)_

**Success Criteria:** Sidecar-wrapped build detected via PID in one scan cycle (30s). Kill Claude — stalled in 30s not 60s. Non-sidecar builds still work via fallback. Dead integrations removed without breaking imports.

### Phase 6: Dispatch Integration + Infrastructure Hardening _(added: 2026-04-07)_

**Status:** 🚧 in_progress
**Blocked by:** Phase 5 (both touch events.mjs)
**Goal:** All Claude dispatch paths wrap in sidecar. Fix crash cleanup in dispatch script. Prevent double-dispatch via PID guard.
**Adversarial review:** 6-agent analysis found 4 Claude invocations in dispatch-to-node.sh (lines 155, 166, 220, 229), 3 local spawn points in events.mjs, no EXIT trap, no double-dispatch prevention.
**Files:**

- `~/.buildrunner/scripts/dispatch-to-node.sh` (MODIFY) — wrap Claude, add EXIT trap
- `~/.buildrunner/scripts/_dispatch-core.sh` (MODIFY) — remove dead functions
- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — wrap local spawns, dispatch guard, pre-redispatch cleanup

**Deliverables:**

dispatch-to-node.sh:

- [ ] Add EXIT trap at top: clean up worktree + branch + temp files on any exit _(added: 2026-04-07)_
- [ ] Rsync `build-sidecar.sh` to remote node before dispatch _(added: 2026-04-07)_
- [ ] Replace `claude -p` with `build-sidecar.sh $BUILD_ID $PHASE_NUM $PROJECT_PATH claude -p --dangerously-skip-permissions '$PROMPT'` (all 4 invocation points: lines 155, 166, 220, 229) _(added: 2026-04-07)_
- [ ] Verify return rsync includes `.buildrunner/locks/` (add explicit `--include` for clarity) _(added: 2026-04-07)_

\_dispatch-core.sh:

- [ ] Remove `dispatch_gui_claude()` (lines 229-237) — dead, never called _(added: 2026-04-07)_
- [ ] Remove `wait_for_completion()` (lines 192-225) — dead, never called _(added: 2026-04-07)_

events.mjs dispatch:

- [ ] `/api/builds/:id/dispatch`: wrap spawn in sidecar. Guard: if `sidecar.json` exists and PID alive, reject with 409 (double-dispatch prevention) _(added: 2026-04-07)_
- [ ] `/api/builds/dispatch-all`: same sidecar wrapping _(added: 2026-04-07)_
- [ ] Auto-redispatch: wrap both remote `exec()` and local `spawn()` in sidecar _(added: 2026-04-07)_
- [ ] Pre-redispatch: clean stale `sidecar.json` + `exit-status.json`, preserve rescue tags _(added: 2026-04-07)_

**Success Criteria:** Every dispatch path produces `sidecar.json`. No unwrapped Claude runs. Double-dispatch returns 409. Crashed dispatch cleans up worktree via trap.

### Phase 7: Resume Logic _(added: 2026-04-07)_

**Status:** 🚧 in_progress
**Blocked by:** Phase 4
**Goal:** Recover uncommitted work from dead sessions on resume. New executor Step 0.5 detects rescue tags and applies stashed work.
**Files:**

- `~/.claude/docs/autopilot-executor-prompt.md` (MODIFY) — add rescue Step 0.5 before Step 1

**Deliverables:**

- [ ] Add Step 0.5 before Step 1: check for `wip-rescue-${BUILD_ID}` git tag _(added: 2026-04-07)_
- [ ] If tag found: `git stash apply $(git rev-parse wip-rescue-${BUILD_ID})` to restore working tree _(added: 2026-04-07)_
- [ ] Log recovered files, write progress step 0.5 "rescue" _(added: 2026-04-07)_
- [ ] If stash apply fails (conflicts): `git checkout -- .`, log warning, start fresh _(added: 2026-04-07)_
- [ ] On phase completion (Step 7): `git tag -d wip-rescue-${BUILD_ID}` to clean up _(added: 2026-04-07)_

**Success Criteria:** Kill a build mid-work. Redispatch. New session finds rescue tag, applies it, continues with previously-written code. No manual intervention.

### Phase 8: Frontend Status Consistency _(added: 2026-04-07)_

**Status:** ✅ COMPLETE
**Blocked by:** Phase 3 (complete)
**Goal:** Fix Phase 2 gaps found by code analysis: incomplete badge mapping, inconsistent dispatch buttons, missing CSS across both dashboard views.
**Adversarial review:** 6-agent analysis found stalled missing from 2 dispatch paths, modal badge only handles 4/9 statuses, 5 CSS classes missing, paused incorrectly in dispatch list.
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY) — modal, context menu, inline dispatch, badges
- `~/.buildrunner/dashboard/public/js/ws-builds.js` (MODIFY) — badgeClass, dead code
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY) — missing badge/card CSS

**Deliverables:**

index.html:

- [x] Modal dispatch (line 837): add `'stalled'` to `canDispatch` list _(added: 2026-04-07)_
- [x] Context menu dispatch (line 2590): add `'stalled'` to dispatch check _(added: 2026-04-07)_
- [x] Modal badge (line 816): extend to handle all 9 statuses (running, complete, failed, stalled, pending, paused, blocked, registered, queued) _(added: 2026-04-07)_
- [x] Inline dispatch (line 1334): remove `'paused'` (paused should show Resume, not Dispatch) _(added: 2026-04-07)_

ws-builds.js:

- [x] `badgeClass()` (line 375): extend to map all 9 statuses to CSS classes _(added: 2026-04-07)_
- [x] `statusColor()` consolidated into lookup table alongside `badgeClass()` _(added: 2026-04-07)_

styles.css:

- [x] Add `.badge-paused` (yellow), `.badge-blocked` (orange), `.badge-registered` (gray), `.badge-queued` (gray) _(added: 2026-04-07)_
- [x] Add `.bws-build-card.status-registered`, `.status-queued`, `.status-pending` card border styles _(added: 2026-04-07)_

**Success Criteria:** Every build status renders correct badge and action buttons in all 4 UI locations (table, modal, card view, context menu). No status falls through to wrong default.

### Phase 9: Integration Test _(added: 2026-04-07)_

**Status:** pending
**Blocked by:** Phases 6, 7
**Goal:** End-to-end validation of full sidecar lifecycle: PID detection, stall marking, rescue tag recovery.
**Files:**

- `~/.buildrunner/scripts/test-sidecar.sh` (NEW)

**Deliverables:**

- [ ] Create dummy BUILD, dispatch locally with sidecar, verify sidecar.json + heartbeat + rescue tag _(added: 2026-04-07)_
- [ ] Kill Claude process, verify exit-status.json within 15s _(added: 2026-04-07)_
- [ ] Verify scanner detects stalled via PID within one scan cycle _(added: 2026-04-07)_
- [ ] Verify rescue tag contains uncommitted changes _(added: 2026-04-07)_
- [ ] Simulate redispatch, verify stash applied and code recovered _(added: 2026-04-07)_
- [ ] Clean up: remove test build, tags, locks _(added: 2026-04-07)_

**Success Criteria:** `test-sidecar.sh` exits 0. All assertions pass.

## Out of Scope (Future)

- PID tracking in registry (sidecar.json in lock dir is sufficient; registry field is redundant)
- `progress.json` consumption (step-level detail in dashboard)
- Spec revert (writing `pending` back into BUILD spec markdown — feedback loop risk)
- `agents.json` consumption (agent-level detail in dashboard)
- workfloDock path matching fix in sessions.mjs
- Session polling frequency reduction (15s → 60s once sidecar handles liveness)

## Prereqs

- [x] Session polling operational (sessions.mjs already running)
- [x] Scanner operational (events.mjs already running)
- [x] `getActiveSessions` already imported in events.mjs (line 12)

## Session Log

- 2026-04-07: Root cause found — `claude -p` (single-turn) kills orchestrator after first response, orphaning background agents. Scanner trusts BUILD spec `in_progress` status without checking process liveness. Adversarial review found 4 blockers (re-entrancy, remote heartbeats, session matching ambiguity, empty assigned_node) — all resolved. Fixed dispatch-all to use interactive mode, fixed individual dispatch status mismatch.
- 2026-04-07: Phases 1-3 complete. Amended with Phases 4-9: PID-accurate sidecar liveness + zero-work-loss resume. 6-agent deep analysis found dead code (below.mjs, \_dispatch-core.sh functions), Phase 2 frontend gaps (stalled missing from modal/context menu dispatch, incomplete badge mapping for 5 statuses), infrastructure gaps (no EXIT trap in dispatch script, no double-dispatch prevention, scanner registry write race). All findings incorporated into phases.
