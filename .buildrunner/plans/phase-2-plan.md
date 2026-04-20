# Phase 2: Heartbeat Redesign — Implementation Plan

## Tasks

### Task 2.1: Create lib/cluster-health.mjs
Extract getNodeHealth() from registry.mjs and recommender.mjs into shared module.
- Export getNodeHealth(nodeName) function
- Uses cluster-check.sh --health-json for health data
- Returns { node, online, cpu_load, memory_pct, ... }

### Task 2.2: Update build-sidecar.sh heartbeat format
Change heartbeat loop to write JSON with monotonic sequence counter.
- Write JSON format: {"ts":"ISO8601","seq":N,"pid":CLAUDE_PID,"phase":CURRENT_PHASE}
- Increment sequence counter on each heartbeat cycle
- Include current phase and progress in heartbeat payload

### Task 2.3: Update sidecar dashboard reporting with sequence
Add sequence number to POST /api/events heartbeat payload.
- Add seq field to report_to_dashboard JSON
- Increment sequence counter in background loop

### Task 2.4: Add heartbeat fencing to events.mjs
Server rejects heartbeats with sequence <= last recorded.
- Check heartbeat_seq column against incoming sequence
- Reject stale heartbeats (log warning, don't update state)
- Reset heartbeat_seq to 0 on DISPATCHED event (already done in state machine)

### Task 2.5: Implement graduated reaper in events.mjs
Replace 15-minute stale check with graduated response.
- <45s: active (no action)
- 45-90s: suspect (set status=SUSPECT)
- >180s: stalled (set status=STALLED, terminal)
- Run reaper every 30s in scanner interval

### Task 2.6: Demote heartbeat-relay.sh to read-only fallback
Only poll nodes with no sidecar heartbeat > 60s.
- Remove all JSON writes from relay
- Only send API heartbeat events for builds missing sidecar heartbeat > 60s
- Tag events as source: poll (lower authority than source: sidecar)

### Task 2.7: Update registry.mjs to import cluster-health.mjs
Replace inline getNodeHealth with import from shared module.

### Task 2.8: Update recommender.mjs to import cluster-health.mjs
Replace inline checkNodeHealth with import from shared module.

### Task 2.9: Add process group isolation to sidecar
Use _setsid-exec.sh wrapper for Claude process to enable clean process group kills.
- Track PGID not just PID
- Update sidecar.json to include pgid field

## Tests

Testing is integrated via heartbeat verification:
- Heartbeat sequence increments correctly
- Stale heartbeats rejected by server
- Graduated reaper correctly sets SUSPECT then STALLED
- Relay only activates for builds without sidecar heartbeat

## File Summary

| File | Action |
|------|--------|
| ~/.buildrunner/lib/cluster-health.mjs | CREATE |
| ~/.buildrunner/scripts/build-sidecar.sh | MODIFY |
| ~/.buildrunner/scripts/heartbeat-relay.sh | MODIFY |
| ~/.buildrunner/dashboard/events.mjs | MODIFY |
| ~/.buildrunner/scripts/registry.mjs | MODIFY |
| ~/.buildrunner/dashboard/recommender.mjs | MODIFY |
