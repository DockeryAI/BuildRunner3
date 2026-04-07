# Build: Dashboard Build Liveness Detection

**Created:** 2026-04-07
**Status:** BUILD COMPLETE — All 2 Phases Done
**Deploy:** local — dashboard event server restart (`kill $(pgrep -f "node events.mjs"); cd ~/.buildrunner/dashboard && node events.mjs &`)

## Overview

The dashboard's BUILD spec scanner reads markdown status lines every 30s and marks builds as `running` when any phase says `in_progress`. If the agent process dies, the spec stays `in_progress` forever and the dashboard lies. The session detection system already polls `ps aux` every 15s on all cluster nodes and knows which Claude processes are alive. These two systems are not connected.

This build connects them: the scanner cross-references sessions with builds, introduces a `stalled` status for builds with no live process, and updates the frontend to show accurate state and dispatch buttons.

**Builds On:** Existing dashboard event server, session polling, BUILD spec scanner

**DO NOT:**

- Add new polling loops
- Modify sessions.mjs
- Add new files
- Change registry.mjs

**Adversarial Review:** Completed 2026-04-07 via local subagent. 4 blockers found and resolved (re-entrancy guard, remote heartbeat skip, project_path matching, empty assigned_node). 9 warnings incorporated (grace period, both KPIs, ad-hoc stale removal, workfloDock paths).

## Parallelization Matrix

| Phase | Key Files                       | Can Parallel With | Blocked By                         |
| ----- | ------------------------------- | ----------------- | ---------------------------------- |
| 1     | `events.mjs` (scanner function) | -                 | -                                  |
| 2     | `index.html`, `ws-builds.js`    | -                 | 1 (needs stalled status to render) |

**Optimal execution:** Sequential — Phase 2 needs Phase 1's `stalled` status to exist in the registry.

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

## Out of Scope (Future)

- PID tracking in registry (would eliminate fuzzy matching)
- `progress.json` consumption (step-level detail in dashboard)
- Auto-dispatch on stall detection (user should decide)
- Spec revert (writing `pending` back into BUILD spec markdown — feedback loop risk)
- `agents.json` consumption (agent-level detail in dashboard)
- workfloDock path matching fix in sessions.mjs

## Prereqs

- [x] Session polling operational (sessions.mjs already running)
- [x] Scanner operational (events.mjs already running)
- [x] `getActiveSessions` already imported in events.mjs (line 12)

## Session Log

- 2026-04-07: Root cause found — `claude -p` (single-turn) kills orchestrator after first response, orphaning background agents. Scanner trusts BUILD spec `in_progress` status without checking process liveness. Adversarial review found 4 blockers (re-entrancy, remote heartbeats, session matching ambiguity, empty assigned_node) — all resolved. Fixed dispatch-all to use interactive mode, fixed individual dispatch status mismatch.
