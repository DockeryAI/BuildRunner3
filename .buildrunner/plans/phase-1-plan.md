# Phase 1: SQLite Single Writer — Implementation Plan

## Tasks

1. Create SQLite tables (builds, build_events, heartbeats) in events.db
2. Migrate cluster-builds.json into builds table
3. Rewrite build-state-machine.mjs as SQLite accessor with SUSPECT state
4. Extract NODE_MATRIX to lib/node-matrix.mjs
5. Update registry.mjs — SQLite via state machine, fix lock path
6. Update next-ready-build.mjs — shared imports
7. Route heartbeat handler through state machine (events.mjs)
8. Route dispatch completion through state machine (events.mjs)
9. Route scanner updates through state machine (events.mjs)
10. Add /api/builds/snapshot endpoint (events.mjs)
11. Update recommender.mjs — read from SQLite
12. Remove dead imports from events.mjs
13. Archive migrate-to-events.mjs
14. Delete stale files (browser.old.log, pending-alerts.jsonl)
15. Consolidate readRegistry() duplicates

## Tests

- State machine CRUD + transitions + SUSPECT state
- Migration correctness
- /api/builds/snapshot response shape
