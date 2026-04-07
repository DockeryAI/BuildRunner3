# Build: Walter Sentinel Hardening + Cluster Monitoring

**Created:** 2026-04-07
**Status:** BUILD COMPLETE — All 8 Phases Done
**Deploy:** cluster — Walter (10.0.1.102), Lockwood (10.0.1.101), Muddy (local)

## Overview

Walter has never successfully tested a single build despite being wired into 39 phases of cluster infrastructure. Root cause: 5 compounding failures (no auto-restart, stale repos, silent dispatch, non-blocking gates, incomplete Phase 37) plus 22 race conditions across the codebase. This build fixes Walter permanently, adds cluster-wide monitoring agents, and makes the test pipeline bulletproof from commit to gate.

## Root Cause Analysis

1. **Walter crashes and never restarts** — no LaunchAgent, empty PID file, no auto-recovery
2. **Repos on Walter are stale** — git pull silently fails, mtime-based change detection misses everything
3. **Trigger fires into the void** — auto-save-session.sh curls Walter in background to /dev/null, no logging
4. **Results never block anything** — governance says "block on test failure" but all gates are warnings-only
5. **Phase 37 marked complete but unbuilt** — no Lockwood reporting, no sparklines

## Race Conditions Found (22 total, 7 critical)

| ID   | File                          | Issue                                                                   | Severity |
| ---- | ----------------------------- | ----------------------------------------------------------------------- | -------- |
| RC1  | node_tests.py:34,638,840      | Unprotected `_running` flag — two test runs can execute simultaneously  | CRITICAL |
| RC2  | node_tests.py:37,151          | `_file_hashes` dict accessed from multiple threads without lock         | HIGH     |
| RC3  | node_tests.py:35-36,673-685   | `_last_results` written during test run, read by API — torn updates     | HIGH     |
| RC4  | node_tests.py:626-689,837-875 | `_test_loop()` and `/api/run` both run tests — can overlap              | CRITICAL |
| RC5  | node_tests.py:584-619,268-308 | SQLite concurrent writes from multiple threads without serialization    | CRITICAL |
| RC6  | node_tests.py:366,447         | Same temp file path for concurrent runs — results belong to wrong run   | HIGH     |
| RC7  | auto-save-session.sh:33-39    | Multiple background curls from rapid commits — duplicate session writes | MEDIUM   |
| RC10 | walter.mjs:16,89-140          | setInterval stacking — poll can overlap if response >30s                | MEDIUM   |
| RC11 | walter.mjs:125-139            | Coverage delta calculation races with assignment                        | MEDIUM   |
| RC12 | dispatch-to-node.sh:497-514   | Two dispatches to same node simultaneously — repo corruption            | CRITICAL |
| RC13 | dispatch-to-node.sh:82-88     | Dispatch branch creation race — git error                               | CRITICAL |
| RC14 | dispatch-to-node.sh:121-132   | Rsync write conflicts on remote — file corruption                       | CRITICAL |
| RC17 | events.mjs:604-653            | Registry read-modify-write race — state partially lost                  | CRITICAL |
| RC18 | events.mjs:539-541            | Prompt file collision — wrong prompt executed                           | CRITICAL |
| RC21 | events.mjs:241-252,330-338    | SSE broadcast during client add/remove — iterator crash                 | HIGH     |

## Dead Code Found (8 blocks)

| Code                       | File                | Lines    | Reason                                       |
| -------------------------- | ------------------- | -------- | -------------------------------------------- |
| `/api/history/{test_name}` | node_tests.py       | 816-834  | Zero callers                                 |
| `/api/running`             | node_tests.py       | 939-941  | Zero callers                                 |
| `/api/testmap/baseline`    | node_tests.py       | 887-936  | Zero callers, DoS risk (1.67hr baseline run) |
| `_push_to_lockwood()`      | node_tests.py       | 548-574  | Pushes to non-existent Lockwood endpoint     |
| Keychain unlock code       | dispatch-to-node.sh | 200, 263 | DISPATCH_KEYCHAIN_PW never set               |
| DISPATCH_USER refs         | dispatch-to-node.sh | 132, 143 | Variable never defined                       |
| Windows extraction paths   | dispatch-to-node.sh | 106-116  | No Windows dispatch nodes                    |
| `/api/alert` receiver      | node_tests.py       | 957-973  | Alert sender never connected                 |

## Parallelization Matrix

| Phase | Key Files                                    | Can Parallel With | Blocked By |
| ----- | -------------------------------------------- | ----------------- | ---------- |
| 1     | node_tests.py, walter-setup.sh               | 3, 6              | -          |
| 2     | auto-save-session.sh, dispatch-to-node.sh    | 3, 6              | 1          |
| 3     | events.mjs, walter.mjs                       | 1, 2, 6           | -          |
| 4     | begin.md, commit.md                          | 3, 5              | 1, 2       |
| 5     | node_semantic.py, node_tests.py              | 4                 | 1          |
| 6     | cluster-health-monitor.mjs                   | 1, 2, 3           | -          |
| 7     | build-monitor.mjs, test-pipeline-monitor.mjs | -                 | 2, 6       |
| 8     | auto-remediate.mjs, ws-monitor.js            | -                 | 6, 7       |

## Phases

### PHASE 1: Walter Service Hardening

**Status:** ✅ COMPLETE
**Goal:** Walter's test service is crash-proof, thread-safe, and uses git SHAs instead of mtimes for change detection.

**Files:**

- `core/cluster/node_tests.py` (MODIFY)
- `~/.buildrunner/scripts/walter-setup.sh` (NEW)

**Blocked by:** None
**Deliverables:**

- [x] Add `threading.Lock` for `_running`, `_file_hashes`, `_last_results`, `_db_lock` — wraps all shared state access (fixes RC1-RC5)
- [x] Replace dual trigger paths (loop + /api/run) with `queue.Queue` — single consumer thread pulls from queue, deduplicates by project+SHA, runs tests serially
- [x] Add `last_tested_sha` column to SQLite `test_runs` table. Replace `_detect_changes()` mtime logic with `git diff --name-only $last_tested_sha..HEAD`. Update `last_tested_sha` after each test run.
- [x] Add `GET /health` endpoint returning: uptime, last_test_run timestamp, repo HEADs per project, memory usage, queue depth, service version
- [x] Unique temp files: `/tmp/walter-{runner}-{project}-{uuid}.json` — prevents RC6
- [x] `/api/run` returns `{"status":"queued","run_id":"..."}`. Add `GET /api/run/{run_id}/status` for polling.
- [x] Remove dead code: `/api/history` endpoint (lines 816-834), `/api/running` endpoint (lines 939-941), `/api/testmap/baseline` endpoint (lines 887-936), dead `_push_to_lockwood()` (lines 548-574 — will be rewritten in Phase 5)
- [x] Create `walter-setup.sh`: SSH to Walter, deploy updated node_tests.py, create `~/Library/LaunchAgents/com.br3.walter-sentinel.plist` with KeepAlive+RunAtLoad, load LaunchAgent, verify via /health curl

**Success Criteria:** Walter restarts automatically after `kill -9`. `/health` shows fresh data. Queue prevents concurrent test runs. Git-SHA detection catches every commit.

---

### PHASE 2: Push-Based Repo Sync + Dispatch Logging

**Status:** ✅ COMPLETE
**Goal:** Walter always has the exact code that was just committed. Every dispatch is logged and verifiable.

**Files:**

- `~/.buildrunner/scripts/auto-save-session.sh` (MODIFY)
- `~/.buildrunner/scripts/dispatch-to-node.sh` (MODIFY)

**Blocked by:** Phase 1 (Walter must be running with /health endpoint)
**Deliverables:**

- [x] auto-save-session.sh: add git remote `walter` auto-setup (create if missing: `git remote add walter ssh://10.0.1.102/~/repos/$PROJECT`)
- [x] auto-save-session.sh: before /api/run curl, push code: `git push walter HEAD:refs/heads/current --force-with-lease 2>/dev/null`
- [x] auto-save-session.sh: log every dispatch to `~/.buildrunner/logs/walter-dispatch.log` — timestamp, project, SHA, Walter response code, run_id
- [x] auto-save-session.sh: verify /health freshness before dispatching (check last_test_run is not null), skip with log entry if Walter degraded
- [x] dispatch-to-node.sh: add lock files `/tmp/dispatch-lock-${NODE}-${PROJECT}` with PID — check before dispatch, clean on EXIT trap (fixes RC12-RC15)
- [x] dispatch-to-node.sh: remove dead `DISPATCH_KEYCHAIN_PW` references (lines 200, 263) and undefined `DISPATCH_USER` references
- [x] dispatch-to-node.sh: unique prompt file paths `/tmp/dispatch-prompt-${buildId}-${Date.now()}.txt` (fixes RC18)

**Success Criteria:** `git commit` on Muddy → Walter has the commit within 5s → dispatch logged with response code. No two dispatches to same node+project can overlap.

---

### PHASE 3: Race Condition Fixes (Dashboard Layer)

**Status:** ✅ COMPLETE
**Goal:** Dashboard and integrations are race-free.

**Files:**

- `~/.buildrunner/dashboard/events.mjs` (MODIFY)
- `~/.buildrunner/dashboard/integrations/walter.mjs` (MODIFY)

**Blocked by:** None (independent of Phases 1-2)
**Deliverables:**

- [x] events.mjs: registry read-modify-write atomicity — write to temp file, then `fs.renameSync()` to `cluster-builds.json` (fixes RC17)
- [x] events.mjs: SSE broadcast safety — `const clients = [...sseClients]` before iterating (fixes RC21)
- [x] walter.mjs: replace `setInterval(poll, 30000)` with sequential `poll().then(() => setTimeout(poll, 30000))` — prevents stacking (fixes RC10)
- [x] walter.mjs: lock `lastCoverage` updates — read+compute+assign in single synchronous block (fixes RC11)

**Success Criteria:** Parallel API calls to events.mjs don't corrupt registry. SSE broadcast doesn't crash on client disconnect. Walter polling never stacks.

---

### PHASE 4: Blocking Test Gates

**Status:** ✅ COMPLETE
**Goal:** Failing tests actually block phase completion and pushes. Governance is enforced, not advisory.

**Files:**

- `~/.claude/commands/begin.md` (MODIFY)
- `~/.claude/commands/commit.md` (MODIFY)

**Blocked by:** Phase 1 (Walter must return accurate results), Phase 2 (dispatch must be reliable)
**Deliverables:**

- [x] begin.md Step 6.5: query Walter `/api/coverage?project=$PROJECT`. If `pass_rate < 1.0` → output `BLOCK: Walter reports N failing tests` with failure list. Require explicit user confirmation to override.
- [x] commit.md: query Walter `/api/coverage?project=$PROJECT` before push. If `pass_rate < 1.0` → block push with failure details. Allow `--force` flag for emergency override.
- [x] Both gates: if Walter offline → WARN but don't block (graceful degradation). Log gate result to `~/.buildrunner/logs/test-pipeline.log`.

**Success Criteria:** Phase completion with failing tests requires explicit user override. Push with failing tests blocked unless --force.

---

### PHASE 5: Lockwood Test Reporting (Phase 37 Completion)

**Status:** ✅ COMPLETE
**Goal:** Walter's test results flow to Lockwood for cross-project health tracking. Actually completes the unfinished Phase 37 from cluster-build-orchestration.

**Files:**

- `core/cluster/node_semantic.py` (MODIFY)
- `core/cluster/node_tests.py` (MODIFY)

**Blocked by:** Phase 1 (Walter must store results correctly)
**Deliverables:**

- [x] Lockwood: add `POST /api/memory/tests` endpoint — accepts `{project, sha, branch, pass_rate, failures[], duration_ms, runner, trigger}`, stores in `test_health` SQLite table
- [x] Lockwood: add `GET /api/memory/tests?project=X` — returns recent test health for dashboard sparklines
- [x] Walter: rewrite `_push_to_lockwood()` targeting correct endpoint `POST /api/memory/tests`, add 1 retry on failure, log both attempts
- [x] Walter: mark trigger correctly per source: `'watch'` (background loop), `'manual'` (/api/run), `'hook'` (auto-save dispatch)
- [x] One-time backfill script: query Walter's SQLite history, bulk-POST to Lockwood to seed sparkline data

**Success Criteria:** Test results appear on Lockwood within 30s of test completion. `GET /api/memory/tests?project=buildrunner3` returns real data.

---

### PHASE 6: Cluster Health Monitor

**Status:** ✅ COMPLETE
**Goal:** Every node is watched 24/7. Failures detected within 120 seconds.

**Files:**

- `~/.buildrunner/scripts/cluster-health-monitor.mjs` (NEW)
- `~/Library/LaunchAgents/com.br3.cluster-monitor.plist` (NEW)

**Blocked by:** None (reads cluster.json, hits /health endpoints)
**Deliverables:**

- [x] Poll all 6 nodes every 60s: ping + /health endpoint (where available). Read node list from `~/.buildrunner/cluster.json`.
- [x] Log to `~/.buildrunner/logs/cluster-health.log`: structured JSON lines — timestamp, node, status (online/degraded/offline), CPU, memory, last_activity
- [x] Detect conditions: node down (2 consecutive fails), degraded (CPU>90% or memory>85%), service crashed (ping OK but /health fails), repo drift (HEAD behind Muddy)
- [x] Alert mechanism: write to `~/.buildrunner/alerts/` directory — one JSON file per alert with type, node, severity, message, timestamp. Dashboard events.mjs scans this directory.
- [x] LaunchAgent plist: KeepAlive, RunAtLoad, stdout/stderr to log file, ThrottleInterval 60

**Success Criteria:** Kill Walter's service → alert file within 120s. Node goes offline → alert within 120s. Logs show continuous 60s polling.

---

### PHASE 7: Build Monitor + Test Pipeline Monitor

**Status:** ✅ COMPLETE
**Goal:** Every active build is watched. The full test pipeline is traced end-to-end.

**Files:**

- `~/.buildrunner/scripts/build-monitor.mjs` (NEW)
- `~/.buildrunner/scripts/test-pipeline-monitor.mjs` (NEW)

**Blocked by:** Phase 2 (needs walter-dispatch.log), Phase 6 (needs health data)
**Deliverables:**

- [x] Build monitor: read `cluster-builds.json` every 30s. For each active build: SSH to assigned node, check Claude process running, check `git log --oneline -1`, check sidecar.json status.
- [x] Stall detection: no new commit in 10 min on active build → write alert. Node offline mid-build → write alert + log which build is orphaned.
- [x] Test pipeline monitor: parse `~/.buildrunner/logs/walter-dispatch.log`, trace chain: commit_timestamp → dispatch_timestamp → run_id → /api/run/{id}/status complete → Lockwood POST.
- [x] Gap detection: any pipeline step >2 min or missing from chain → write alert with gap details.
- [x] Logs: `~/.buildrunner/logs/monitor.log` (build monitor) and `~/.buildrunner/logs/test-pipeline.log` (pipeline tracer). Same structured JSON line format as health monitor.

**Success Criteria:** Active build stalls 10 min → alert fires. Commit-to-results pipeline gap >2 min → flagged in pipeline log.

---

### PHASE 8: Auto-Remediation + Dashboard Workspace

**Status:** ✅ COMPLETE
**Goal:** Common failures auto-fix. All monitoring visible in dashboard.

**Files:**

- `~/.buildrunner/scripts/auto-remediate.mjs` (NEW)
- `~/.buildrunner/dashboard/public/js/ws-monitor.js` (NEW)
- `~/.buildrunner/monitor-config.json` (NEW)

**Blocked by:** Phase 6, Phase 7 (needs monitor alerts to respond to)
**Deliverables:**

- [x] Auto-remediate: watch `~/.buildrunner/alerts/` for new alert files. Actions: node service down → SSH restart. Repo drift → `git push` from Muddy. Walter stale → trigger `/api/run`. Build stalled + node dead → flag for re-dispatch to next available node.
- [x] All remediation actions logged with full audit trail in `~/.buildrunner/logs/remediation.log`: timestamp, alert_id, action_taken, result (success/fail), duration.
- [x] Config: `~/.buildrunner/monitor-config.json` controls which auto-fixes are enabled per action type. Default: service restart ON, repo sync ON, build re-dispatch OFF (requires manual).
- [x] Dashboard workspace `ws-monitor.js`: cluster topology view (green/yellow/red per node), active build progress bars, test pipeline waterfall visualization, alert history with remediation actions. Follows existing `ws-*.js` modular pattern.
- [x] New event types in events.mjs: `monitor.health`, `monitor.build`, `monitor.pipeline`, `monitor.fix` — workspace subscribes to these via SSE.

**Success Criteria:** Walter service killed → auto-restarted within 2 minutes without human intervention. Dashboard shows live cluster topology with correct status colors. Alert → remediation → resolution visible in dashboard.

---

## Session Log

[Will be updated by /begin]
