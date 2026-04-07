# Phase 6 Plan: Cluster Health Monitor

## Tasks

1. **cluster-health-monitor.mjs** — Main monitor script
   - Read cluster.json for node list (master + 5 nodes)
   - Poll each node every 60s: ping + /health endpoint
   - Track consecutive failures per node (2 = offline alert)
   - Detect: down, degraded (CPU>90%/mem>85%), service crashed, repo drift
   - Log structured JSON lines to ~/.buildrunner/logs/cluster-health.log
   - Write alert JSON files to ~/.buildrunner/alerts/

2. **LaunchAgent plist** — com.br3.cluster-monitor.plist
   - KeepAlive, RunAtLoad, ThrottleInterval 60
   - stdout/stderr to log files

3. **Alert file format** — JSON with type, node, severity, message, timestamp, alert_id

## Non-testable
Config + monitoring scripts — TDD gate will be skipped.
