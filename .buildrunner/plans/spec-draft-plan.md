# Draft Plan: Walter Sentinel Hardening + Cluster Monitoring

## Problem Statement

Walter (test-runner sentinel, 10.0.1.102) has never successfully tested a single build despite being "wired in" across 39 phases of cluster-build-orchestration. Root cause analysis found 5 compounding failures:

1. **Walter crashes and never restarts** — no LaunchAgent, empty PID file, no auto-recovery
2. **Repos on Walter are stale** — git pull silently fails, mtime-based change detection misses everything
3. **Trigger fires into the void** — auto-save-session.sh curls Walter in background with output to /dev/null, no logging, no verification
4. **Results never block anything** — governance says "block on test failure" but all gates are warnings-only
5. **Phase 37 marked complete but unbuilt** — no post-receive hook, no Lockwood reporting, no sparklines

Additionally, deep code scan found:

- **22 race conditions** (7 critical) in node_tests.py, events.mjs, dispatch-to-node.sh, walter.mjs
- **8 dead code blocks** including endpoints nobody calls and functions pushing to non-existent Lockwood endpoints
- **3 duplicate test dispatch paths** that can race against each other

## Scope

Fix Walter permanently. Add cluster-wide monitoring. Make the test pipeline bulletproof from commit to gate.

### In Scope

- Walter service hardening (LaunchAgent, health, auto-restart)
- Race condition fixes in node_tests.py (threading locks, queue-based dispatch)
- Race condition fixes in events.mjs (registry atomicity, SSE safety, dispatch locking)
- Push-based repo sync replacing broken pull-based polling
- Git SHA-based change detection replacing fragile mtime detection
- Dispatch logging and verification (walter-dispatch.log)
- Blocking test gates in /begin and /commit
- Phase 37 completion (Lockwood reporting endpoint + Walter push)
- Dead code removal from node_tests.py and dispatch-to-node.sh
- Cluster health monitor (LaunchAgent, all 6 nodes, 60s interval)
- Build monitor (active builds, stall detection, 30s interval)
- Test pipeline monitor (end-to-end tracing: commit → dispatch → run → results)
- Auto-remediation agent (restart services, fix repo drift, re-dispatch stalled builds)
- Dashboard monitoring workspace (ws-monitor.js)

### Out of Scope

- Rewriting the entire dashboard
- Changing the cluster topology
- Adding new cluster nodes
- Rewriting /autopilot or /begin from scratch
- Intel pipeline (Phase 36 — separate build)

## Technical Approach

### Walter Service (node_tests.py)

- Add `threading.Lock` for `_running`, `_file_hashes`, `_last_results`
- Replace dual trigger paths (loop + /api/run) with single queue consumer
- Unique temp files per run (include run_id in path)
- SQLite write serialization via `_db_lock`
- Git SHA-based change detection: `git diff --name-only $last_tested_sha..HEAD`
- Store `last_tested_sha` per repo in SQLite
- Remove dead endpoints: /api/history, /api/running, /api/testmap/baseline
- Fix `_push_to_lockwood()` to target correct Lockwood endpoint

### Cluster Infrastructure

- Push-based sync: git remote `walter` on Muddy, push before /api/run trigger
- Enhanced auto-save-session.sh: log dispatches, verify health, capture response
- LaunchAgent on Walter: KeepAlive, RunAtLoad, log rotation
- Enhanced /health endpoint: uptime, last_test_run, repo HEADs, memory

### Events & Dispatch (events.mjs, dispatch-to-node.sh)

- Registry read-modify-write atomicity (temp-file-then-rename)
- Dispatch lock files per node+project
- SSE broadcast: copy Set before iterating
- Unique prompt file paths (include buildId + timestamp)
- Walter.mjs: sequential polling (prevents stacking)

### Gates

- /begin Step 6.5: BLOCK on pass_rate < 1.0 (not just warn)
- /commit: BLOCK on test failures (allow --force override)

### Monitoring (NEW)

- cluster-health-monitor.mjs — LaunchAgent, 60s, all nodes, logs to .buildrunner/logs/cluster-health.log
- build-monitor.mjs — LaunchAgent, 30s, active builds, logs to .buildrunner/logs/monitor.log
- test-pipeline-monitor.mjs — hooks into dispatch log, traces full chain
- auto-remediate.mjs — triggered by alerts, restarts/syncs/re-dispatches
- ws-monitor.js — dashboard workspace for all monitoring data

## Files

### MODIFY

- `core/cluster/node_tests.py` — race fixes, queue, git-SHA detection, dead code removal, /health enhancement
- `~/.buildrunner/scripts/auto-save-session.sh` — push-based sync, logging, health verification
- `~/.buildrunner/dashboard/integrations/walter.mjs` — sequential polling, coverage delta fix
- `~/.buildrunner/dashboard/events.mjs` — registry atomicity, SSE safety, dispatch locking, prompt uniqueness
- `~/.buildrunner/scripts/dispatch-to-node.sh` — dispatch lock files, remove dead keychain code
- `~/.claude/commands/begin.md` — blocking test gate at Step 6.5
- `~/.claude/commands/commit.md` — blocking pre-push test gate
- `core/cluster/node_semantic.py` — add /api/memory/tests endpoint on Lockwood

### CREATE (NEW)

- `~/.buildrunner/scripts/cluster-health-monitor.mjs` — node health polling
- `~/.buildrunner/scripts/build-monitor.mjs` — active build monitoring
- `~/.buildrunner/scripts/test-pipeline-monitor.mjs` — end-to-end test tracing
- `~/.buildrunner/scripts/auto-remediate.mjs` — auto-fix detected issues
- `~/.buildrunner/dashboard/public/js/ws-monitor.js` — monitoring dashboard workspace
- `~/Library/LaunchAgents/com.br3.walter-sentinel.plist` — Walter auto-restart (deployed to Walter)
- `~/Library/LaunchAgents/com.br3.cluster-monitor.plist` — monitoring LaunchAgent on Muddy
- `~/.buildrunner/scripts/walter-setup.sh` — one-shot Walter deployment script

## Risk Assessment

| Risk                                                  | Mitigation                                               |
| ----------------------------------------------------- | -------------------------------------------------------- |
| Walter offline during deployment                      | Deploy via SSH script, verify with health check          |
| Race fix breaks existing API consumers                | Run existing tests before/after, maintain API contract   |
| Blocking gates too aggressive                         | --force override on /commit, user confirmation on /begin |
| Monitor LaunchAgents add CPU overhead                 | Lightweight polling (curl + jq), <1% CPU                 |
| Registry atomicity change breaks concurrent dashboard | Test with parallel API calls                             |
| Dead code removal breaks undiscovered callers         | Grep entire codebase before removing                     |
