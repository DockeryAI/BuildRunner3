# Phase 1: SQLite Single Writer — Verification

## All 16 Deliverables: PASS

1. builds table created with all columns + SUSPECT status
2. build_events audit log table created
3. heartbeats table created with sequence tracking
4. 30 builds migrated from cluster-builds.json (in-flight get fresh baseline)
5. build-state-machine.mjs rewritten as SQLite accessor
6. Scanner routes through updateBuild()
7. Heartbeat handler routes through appendEvent(HEARTBEAT)
8. Dispatch completion routes through appendEvent(EXIT/STALLED)
9. registry.mjs reads/writes via SQLite state machine
10. /api/builds/snapshot endpoint added
11. registry.mjs lock path fixed (.registry-lock -> cluster-builds.json.lock)
12. Dead imports removed from events.mjs
13. migrate-to-events.mjs archived to lib/archive/
14. NODE_MATRIX extracted to lib/node-matrix.mjs
15. readRegistry() consolidated to single source
16. browser.old.log + pending-alerts.jsonl deleted

## Functional Tests: 7/7 PASS
