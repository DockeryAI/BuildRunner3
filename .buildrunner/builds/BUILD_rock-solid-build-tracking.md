# Build: Rock-Solid Build Tracking

**Created:** 2026-04-12
**Status:** Phases 1-4 Complete — Phase 3 In Progress
**Deploy:** infra — restart dashboard server (`node ~/.buildrunner/dashboard/events.mjs`)

## Overview

Replace the unreliable multi-writer JSON build registry with a single-writer SQLite-backed state system. Fix heartbeat races, add reliable exit status delivery, and harden the dashboard UI. Every production CI/CD system converged on these patterns — this build adopts them for The Band.

## Parallelization Matrix

| Phase | Key Files                                                            | Can Parallel With | Blocked By                                          |
| ----- | -------------------------------------------------------------------- | ----------------- | --------------------------------------------------- |
| 1     | build-state-machine.mjs, events.mjs, registry.mjs, recommender.mjs   | 5                 | -                                                   |
| 2     | events.mjs (heartbeat section), build-sidecar.sh, heartbeat-relay.sh | 4, 5              | 1 (events.mjs, state machine), 5 (\_setsid-exec.sh) |
| 3     | events.mjs (scanner section), build-sidecar.sh, registry.mjs         | 4, 5              | 1 (events.mjs), 2 (build-sidecar.sh)                |
| 4     | index.html, ws-builds.js, styles.css                                 | 2, 3, 5           | 1 (needs /api/builds/snapshot)                      |
| 5     | adversarial-review.sh, \_setsid-exec.sh, \_portable-timeout.sh       | 1, 2, 3, 4        | -                                                   |

**Critical path:** Phase 1 → Phase 2 → Phase 3
**Parallel track:** Phase 4 starts after Phase 1, runs alongside Phases 2-3
**Independent track:** Phase 5 runs anytime (unblocked), provides \_setsid-exec.sh for Phase 2

## Phases

### Phase 1: SQLite Single Writer

**Status:** ✅ COMPLETE
**Goal:** All build state lives in SQLite. One process (dashboard server) owns all writes. cluster-builds.json and build-events.jsonl eliminated as state stores.

**Files:**

- ~/.buildrunner/lib/build-state-machine.mjs (REWRITE)
- ~/.buildrunner/dashboard/events.mjs (MODIFY — scanner, heartbeat handler, dispatch handler sections)
- ~/.buildrunner/scripts/registry.mjs (MODIFY)
- ~/.buildrunner/scripts/next-ready-build.mjs (MODIFY — use shared imports) _(added: 2026-04-12)_
- ~/.buildrunner/lib/node-matrix.mjs (CREATE — shared module) _(added: 2026-04-12)_
- ~/.buildrunner/cluster-builds.json (MIGRATE then DEPRECATE)
- ~/.buildrunner/build-events.jsonl (DELETE)
- ~/.buildrunner/dashboard/recommender.mjs (MODIFY — read from SQLite)

**Blocked by:** None
**Deliverables:**

- [ ] Create `builds` table in events.db (id, project, status, branch, phase_current, phases_total, phases_complete, assigned_node, last_heartbeat_at, heartbeat_seq, spec_path, created_at, updated_at) — status enum includes: registered, queued, dispatched, running, suspect, stalled, complete, failed, cancelled, paused, blocked
- [ ] Create `build_events` table in events.db (id, build_id, event_type, payload, created_at) — audit log only, never replayed for state
- [ ] Create `heartbeats` table in events.db (id, build_id, node, pid, phase, sequence, received_at)
- [ ] Migrate all builds from cluster-builds.json into `builds` table. In-flight builds (running/dispatched) get status preserved + last_heartbeat_at set to migration time (gives reaper fresh baseline instead of immediately marking them stale)
- [ ] Rewrite build-state-machine.mjs as thin SQLite accessor (getCurrentState reads SQL, transition validates + updates SQL). Add SUSPECT to STATES enum (graduated liveness — set only by reaper, not user). STALLED remains the terminal dead state.
- [ ] Route scanner state updates through state machine (remove direct JSON mutations in events.mjs scanner section ~lines 2519-2548)
- [ ] Route heartbeat handler through state machine (remove dual-write in events.mjs ~lines 478-552)
- [ ] Route dispatch completion through state machine (remove direct writes in events.mjs ~lines 987-1036)
- [ ] Update registry.mjs to write to SQLite via state machine instead of cluster-builds.json
- [ ] Add /api/builds/snapshot endpoint that returns full builds table as JSON (replaces reading cluster-builds.json)
- [ ] **CRITICAL:** Fix registry.mjs lock path divergence — change line 14 from `.registry-lock` to `cluster-builds.json.lock` (currently uses different lock file than events.mjs and build-state-machine.mjs, causing write races) _(added: 2026-04-12, source: /dead analysis)_
- [ ] Remove unused imports from events.mjs: STATES (line 20), checkStaleHeartbeats (line 22), readRegistryFromEvents (line 23) — grep confirms zero usage _(added: 2026-04-12, source: /dead analysis)_
- [ ] Archive migrate-to-events.mjs to `lib/archive/` — already executed (171 events exist), guard clause prevents re-run _(added: 2026-04-12, source: /dead analysis)_
- [ ] Extract NODE*MATRIX to `lib/node-matrix.mjs` — currently duplicated identically in registry.mjs:18-24 and next-ready-build.mjs:15-21 *(added: 2026-04-12, source: /dead analysis)\_
- [ ] Consolidate readRegistry() — delete duplicate definitions in registry.mjs:61 and next-ready-build.mjs:37, import from build-state-machine.mjs instead _(added: 2026-04-12, source: /dead analysis)_
- [ ] Delete stale files: `browser.old.log`, `pending-alerts.jsonl` (0 bytes) _(added: 2026-04-12, source: /dead analysis)_

**Success Criteria:** Dashboard shows correct build states sourced entirely from SQLite. cluster-builds.json is not read by any running code. Zero dual-writes. No duplicate lock files, no dead imports, no triplicate function definitions.

---

### Phase 2: Heartbeat Redesign

**Status:** ✅ COMPLETE
**Goal:** Single heartbeat source per build with graduated liveness detection. No more dual heartbeat race between sidecar and relay.

**Files:**

- ~/.buildrunner/dashboard/events.mjs (MODIFY — heartbeat handler + reaper)
- ~/.buildrunner/scripts/build-sidecar.sh (MODIFY)
- ~/.buildrunner/scripts/heartbeat-relay.sh (MODIFY)
- ~/.buildrunner/lib/cluster-health.mjs (CREATE — shared module) _(added: 2026-04-12)_

**Blocked by:** Phase 1 (events.mjs, state machine)
**Deliverables:**

- [ ] Add monotonic sequence number (fencing token) to sidecar heartbeat payload
- [ ] Sidecar heartbeat includes: PID, current phase, phase progress, sequence number, timestamp
- [ ] Update build-sidecar.sh heartbeat loop to include sequence counter in heartbeat file (JSON format: `{"ts":"...","seq":N}`) _(added: 2026-04-12, source: skill analysis)_
- [ ] Server rejects heartbeats with sequence <= last recorded sequence (fencing). Server resets sequence to 0 on DISPATCHED event so sidecar restarts are accepted after redispatch.
- [ ] Demote relay to read-only fallback — only checks nodes with no sidecar heartbeat > 60s
- [ ] Relay reports tagged `source: poll` (lower authority than `source: sidecar`)
- [ ] Server-side reaper every 30s with graduated response: active (<45s) → suspect (45-90s, status=SUSPECT) → stalled (>180s, status=STALLED). Suspect is a liveness warning, stalled is terminal requiring manual intervention or redispatch.
- [ ] Process group isolation — sidecar uses shared `_setsid-exec.sh` utility (from Phase 5), tracks PGID not just PID
- [ ] Extract getNodeHealth() to shared `lib/cluster-health.mjs` — currently duplicated identically in registry.mjs:26-33 and recommender.mjs:55-66 _(added: 2026-04-12, source: /dead analysis)_

**Success Criteria:** Only one heartbeat source active per build at any time. Stale builds detected and marked within 3 minutes. No phantom liveness from relay keeping dead builds alive. No duplicate health check functions. Sidecar heartbeats include monotonic sequence for fencing.

---

### Phase 3: Exit Status Outbox + Branch-Aware Scanner

**Status:** 🚧 in_progress
**Goal:** Build exit status survives network drops. Scanner reads specs from correct branch.

**Files:**

- ~/.buildrunner/scripts/build-sidecar.sh (MODIFY — exit handling)
- ~/.buildrunner/dashboard/events.mjs (MODIFY — scanner section, poll handler)
- ~/.buildrunner/scripts/registry.mjs (MODIFY — branch recording)

**Blocked by:** Phase 1 (events.mjs, registry.mjs), Phase 2 (build-sidecar.sh)
**Deliverables:**

- [ ] Sidecar writes exit-status.json atomically (temp file + rename) on build completion
- [ ] Sidecar retries exit POST with exponential backoff (5s, 15s, 45s, 2min) if dashboard unreachable
- [ ] Server polls remote nodes for exit-status.json on builds in stale/stalled state
- [ ] Exit status delivery idempotent — server ignores if build already marked complete/failed
- [ ] Record git branch at dispatch time (not registration — branch may change between registration and dispatch) in events.mjs dispatch handler
- [ ] Scanner reads BUILD specs via `git show {branch}:{spec_path}` instead of working tree
- [ ] Handle missing branch gracefully (branch deleted → mark spec as unresolvable, don't overwrite state)

**Success Criteria:** Exit status delivered even after dashboard restart or SSH drop. Scanner never overwrites state with data from wrong branch.

---

### Phase 4: Dashboard Resilience + Status Display

**Status:** ✅ COMPLETE
**Goal:** Dashboard UI handles disconnection gracefully, shows heartbeat health in real-time, uses accessible status indicators.

**Files:**

- ~/.buildrunner/dashboard/public/index.html (MODIFY — SSE connection logic)
- ~/.buildrunner/dashboard/public/js/ws-builds.js (MODIFY)
- ~/.buildrunner/dashboard/public/styles.css (MODIFY)

**Blocked by:** Phase 1 (needs /api/builds/snapshot)
**After:** Phase 2 (suspect/stalled states exist to display — can build UI first, test after P2)
**Deliverables:**

- [ ] SSE reconnection with exponential backoff + jitter (replace fixed 3s retry in index.html)
- [ ] Page visibility handler — on tab active: reconnect SSE, fetch /api/builds/snapshot for full state sync
- [ ] Connection health indicator in topbar (green dot = connected, red = disconnected, with time since last event)
- [ ] Add suspect/stalled to status filter dropdown and card rendering
- [ ] Accessible status indicators: color + icon + text for all states (min 3 of 4 channels — color, shape, icon, text)
- [ ] Heartbeat freshness counter per build card — "last heartbeat Xs ago" with aging color (white → yellow → orange → red)
- [ ] Progressive disclosure — active/suspect/stalled builds prominent as cards, completed builds in collapsible accordion section
- [ ] Toast notifications on status transitions (build started, completed, stalled) with 4-8s duration

**Success Criteria:** Dashboard recovers within 5 seconds of tab becoming active after any disconnection period. Heartbeat age visible at a glance for every running build. Status readable without relying on color alone.

---

### Phase 5: Adversarial Dispatch Hardening _(added: 2026-04-12)_

**Status:** ✅ COMPLETE
**Goal:** Fix adversarial-review.sh so remote Claude dispatch to Otis completes reliably instead of failing 100% of the time. Extract setsid process group utility for reuse in Phase 2.

**Files:**

- ~/.buildrunner/scripts/adversarial-review.sh (MODIFY)
- ~/.buildrunner/scripts/\_setsid-exec.sh (CREATE — shared utility)
- ~/.buildrunner/scripts/\_portable-timeout.sh (MODIFY — integrate setsid)

**Blocked by:** None (independent of all other phases)
**Deliverables:**

- [ ] Create `_setsid-exec.sh` shared utility: `perl -e 'use POSIX qw(setsid); setsid(); exec @ARGV'` wrapper that runs a command in its own process group, enabling clean `kill -- -$PGID` on timeout _(added: 2026-04-12)_
- [ ] Replace `perl -e 'alarm 180; exec @ARGV'` in adversarial-review.sh with setsid + process-group-aware timeout that kills the entire group (claude --print included, not just sh) _(added: 2026-04-12)_
- [ ] Add `--bare` flag to remote `claude --print` invocation (line 215) — skip hooks, CLAUDE.md, LSP, MCP on headless review _(added: 2026-04-12)_
- [ ] Add `export NODE_OPTIONS="--max-old-space-size=3584"` before claude invocation on remote 8GB nodes _(added: 2026-04-12)_
- [ ] Increase TIMEOUT*SECONDS from 180 to 360 — adversarial reviews on M2 8GB take 4-6 minutes *(added: 2026-04-12)\_
- [ ] Add orphan cleanup between retries: `ssh $NODE 'pkill -f "claude.*print"'` before second attempt _(added: 2026-04-12)_
- [ ] Fix timeout detection: replace exit code 124/142 check with process-group-aware detection (setsid + waitpid returns correct signal code, not SSH's 255 wrapper) _(added: 2026-04-12)_

**Success Criteria:** Adversarial review dispatched to Otis completes successfully with valid JSON output. No orphaned claude processes on retry. Timeout kills the entire process tree.

---

## Out of Scope (Future)

- Log streaming in build cards (terminal workspace exists)
- Automatic redispatch of stalled builds (manual reassign until foundation solid)
- Multi-coordinator / multi-dashboard (single writer sufficient for 6-node cluster)
- Mobile/touch dashboard patterns
- Build notifications outside dashboard (Slack, email)
- Virtual scrolling for build list (28 builds, not needed yet)

## Adversarial Review Notes

**Gate 3.7 passed** — 3 blockers found and fixed:

1. `setsid` doesn't exist on macOS → perl POSIX workaround
2. SUSPECT state missing from Phase 1 state machine → added to STATES enum
3. Heartbeat fencing breaks on sidecar restart → server resets sequence on DISPATCHED

**Gate 3.8 passed** — architecture validation clean

**Warnings addressed:**

- "Stale" semantic conflict resolved: SUSPECT = liveness warning, STALLED = terminal state
- Branch capture moved from registration to dispatch time
- In-flight builds get heartbeat baseline reset during migration
- "Dead" maps to STALLED (existing state), not a new state

## Session Log

[Will be updated by /begin]
