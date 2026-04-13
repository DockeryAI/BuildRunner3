# Draft Plan: Dashboard DB Hardening

**Purpose:** Prevent recurrence of the 2026-04-13 `events.db` corruption and recover from the current broken state. Root cause: multiple independent writers (`events.mjs`, `build-state-machine.mjs`, `observability.mjs`, and any `registry.mjs` subprocess) open `~/.buildrunner/dashboard/events.db` directly with `better-sqlite3` and do not coordinate on journal mode, busy_timeout, or checkpoint strategy. One of them wrote header bytes inconsistent with the WAL between 09:04 and 13:21 today, corrupting the file. The dashboard UI appears healthy only because `events.mjs` (PID 86944) is serving stale mmap'd pages from its startup snapshot.

**Target Users:** Byron (solo builder) — the dashboard is his primary source of truth for build state, and it must not silently lie to him.

**Tech Stack:** `better-sqlite3` (Node), launchd (scheduling), bash (scripts).

**Scope:** Recovery + hardening of `~/.buildrunner/dashboard/events.db`. Does NOT include dashboard feature work, schema changes, or migrations beyond what recovery requires.

---

## Current DB Openers (confirmed via grep for `new Database(`)

1. `~/.buildrunner/dashboard/events.mjs` — dashboard server, **WRITER**, holds mmap
2. `~/.buildrunner/lib/build-state-machine.mjs` — **WRITER**, used by `registry.mjs`, `cluster-health.mjs`, `node-matrix.mjs`, `next-ready-build.mjs`, `recommender.mjs`
3. `~/.buildrunner/dashboard/observability.mjs` — **READONLY** (opens with `{ readonly: true }` at line 17). Not a writer. Still routes through the helper in Phase 2 for pragma consistency, but does not contribute to the multi-writer race.

The race is between `events.mjs` and any process spawned via `build-state-machine.mjs` (notably `registry.mjs add/update`). Two real writers, not three.

---

## Phase 1: Recovery + Safe Restart

**Goal:** Dashboard is running on a fresh, readable `events.db`. Broken file preserved for forensics. The `BUILD_cross-model-review` amendment from this session is re-registered.

**Files:**

- `~/.buildrunner/dashboard/events.db` (REPLACE — move broken aside, fresh created by server on boot)
- `~/.buildrunner/dashboard/events.db-wal`, `events.db-shm` (DELETE)
- `~/.buildrunner/dashboard/events.db.broken-2026-04-13` (NEW — forensic copy)

**Blocked by:** None

**Deliverables:**

- [ ] Kill dashboard server PID 86944 (`events.mjs`) cleanly via launchd (`launchctl unload` the plist, or SIGTERM)
- [ ] Move `events.db`, `events.db-wal`, `events.db-shm` to `events.db.broken-2026-04-13.*` (preserve for forensics — do NOT delete)
- [ ] Restart dashboard server via launchd; confirm it recreates an empty `events.db` on startup
- [ ] Verify with `sqlite3 events.db "SELECT 1"` that the fresh file is readable
- [ ] Re-register `BuildRunner3:BUILD_cross-model-review` via `registry.mjs add` (the amendment from earlier this session is in the spec file but not in the registry)
- [ ] Re-register `BuildRunner3:BUILD_cluster-max` from `~/Projects/BuildRunner3/.buildrunner/builds/BUILD_cluster-max.md` — explicitly required, must be present in the dashboard after Phase 1 completes
- [ ] Re-register `geo-command-center:BUILD_geo-v2` from `~/Projects/geo-command-center/.buildrunner/builds/BUILD_geo-v2.md` — explicitly required, must be present in the dashboard after Phase 1 completes. Note: cross-project registration, so `registry.mjs add` must be run with `--path ~/Projects/geo-command-center` and `--project geo-command-center`
- [ ] For any **other** builds Byron wants restored beyond the three above, run `registry.mjs add` per-build manually. (Note: `--register-all` is referenced in the `/spec` skill template but does NOT exist in `registry.mjs` — confirmed via grep. Do not call it. If we want bulk restore, that's a separate small task: implement `--register-all` first, then use it.)
- [ ] Verify dashboard UI lists (at minimum): `BUILD_cross-model-review`, `BUILD_cluster-max`, `BUILD_geo-v2` — Phase 1 is not complete until all three are visible

**Success Criteria:** Dashboard UI lists `BUILD_cross-model-review` (5 phases), `BUILD_cluster-max`, and `BUILD_geo-v2`. Fresh `events.db` opens cleanly from both `sqlite3` CLI and a standalone `new Database()` call. Broken file preserved under `.broken-2026-04-13` for later inspection.

---

## Phase 2: Shared DB-Open Helper + Writer Audit

**Goal:** Every process that opens `events.db` does so through one helper with identical pragmas. No direct `new Database(DB_PATH)` calls survive outside the helper.

**Files:**

- `~/.buildrunner/lib/db-open.mjs` (NEW)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — route through helper)
- `~/.buildrunner/lib/build-state-machine.mjs` (MODIFY — route through helper)
- `~/.buildrunner/dashboard/observability.mjs` (MODIFY — route through helper)

**Blocked by:** Phase 1 (need a readable db to test against)

**Deliverables:**

- [ ] Create `db-open.mjs` exporting `openEventsDb()` that sets: `journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`, `foreign_keys=ON`
- [ ] Replace `new Database(DB_PATH)` in `events.mjs`, `build-state-machine.mjs`, `observability.mjs` with `openEventsDb()`
- [ ] Grep the full `~/.buildrunner/` tree for any remaining `new Database(` or `better-sqlite3` direct imports — fix or delete
- [ ] Add a startup-time assertion in `events.mjs` that PRAGMA reports `journal_mode=wal` (refuse to start otherwise)
- [ ] Smoke test: run `registry.mjs list`, `registry.mjs add`, and a dashboard write simultaneously; confirm no lock errors

**Success Criteria:** All DB opens go through `db-open.mjs`. A grep for `new Database(` outside `db-open.mjs` and `node_modules/` returns zero matches. Concurrent writes from `events.mjs` and `registry.mjs` coexist without errors.

---

## Phase 3: Hourly Backups + Rotation

**Goal:** If the db breaks again, recovery is a `mv` away.

**Files:**

- `~/.buildrunner/scripts/backup-events-db.sh` (NEW)
- `~/Library/LaunchAgents/com.buildrunner.db-backup.plist` (NEW)
- `~/.buildrunner/dashboard/backups/` (NEW directory, auto-created)

**Blocked by:** None (all new files — can run parallel to Phase 2)

**Deliverables:**

- [ ] `backup-events-db.sh`: uses `sqlite3 events.db ".backup <dest>"` (the online safe method, NOT `cp`) to write `backups/events.db.<HH>.bak`. Rotates: keep last 24 hourly + last 7 daily.
- [ ] launchd plist: fires the script hourly. Loaded on demand, survives reboot.
- [ ] Backup script exits non-zero on `.backup` failure and logs to `~/.buildrunner/logs/db-backup.log`
- [ ] Add a `--restore <backup-file>` flag to the script that stops the dashboard, swaps the backup in, and restarts
- [ ] Manual test: run once, confirm a readable `.bak` file lands in `backups/` and the dashboard keeps running

**Success Criteria:** 24 rolling hourly + 7 daily backups present after one day of uptime. Running `--restore` on today's broken file (as a dry test) swaps cleanly.

---

## Phase 4: Health Watchdog

**Goal:** A corruption event pages the user within 5 minutes, not 4 hours.

**Files:**

- `~/.buildrunner/scripts/db-watchdog.mjs` (NEW)
- `~/Library/LaunchAgents/com.buildrunner.db-watchdog.plist` (NEW)
- `~/.buildrunner/logs/db-watchdog.log` (NEW, auto-created)

**Blocked by:** Phase 2 (uses `openEventsDb()` from the shared helper)

**Deliverables:**

- [ ] `db-watchdog.mjs`: every 5 min, opens events.db via the shared helper, runs `PRAGMA integrity_check`, asserts result === `ok`. Also runs a real `SELECT COUNT(*) FROM builds` to catch mmap-vs-disk drift.
- [ ] On failure: write a loud entry to `db-watchdog.log`, post a dashboard SSE alert (`db_health_alert`), and optionally trigger an automatic `.backup` snapshot before the state degrades further
- [ ] launchd plist runs the script every 300s
- [ ] Dashboard UI shows a red banner when the last watchdog entry is a failure
- [ ] Test: deliberately corrupt a copy of the db in a sandbox, point the watchdog at it, confirm alert fires within one interval

**Success Criteria:** Watchdog runs on schedule, logs ok every cycle. Simulated corruption triggers the red banner within 5 minutes.

---

## Phase 5: Single-Writer Architecture (the real fix)

**Goal:** Only `events.mjs` ever writes to `events.db`. All other processes post to an HTTP endpoint. The multi-writer race becomes architecturally impossible.

**Files:**

- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add write endpoints)
- `~/.buildrunner/lib/build-state-machine.mjs` (MODIFY — split into read-only and HTTP-client write paths)
- `~/.buildrunner/scripts/registry.mjs` (MODIFY — use HTTP client, not direct db)
- `~/.buildrunner/dashboard/observability.mjs` (MODIFY — writes go through endpoint)
- `~/.buildrunner/lib/db-client.mjs` (NEW — thin HTTP client used by all non-server callers)

**Blocked by:** Phase 2 (same files — cannot parallelize with Phase 2)

**Deliverables:**

- [ ] Add POST endpoints on dashboard server for registry operations (add/update/remove), phase state transitions, and event inserts
- [ ] Create `db-client.mjs` exposing the same API surface as current `build-state-machine.mjs` writer functions, but talking HTTP to localhost
- [ ] Split `build-state-machine.mjs`: reads stay local (open via helper, read-only), writes delegate to `db-client.mjs`
- [ ] Refactor `registry.mjs` to use `db-client.mjs` for all writes
- [ ] Retire all non-server `new Database()` writer calls — grep must return zero
- [ ] Integration test: spam 100 concurrent `registry.mjs add` calls while dashboard is serving, confirm no lock errors, no corruption, all writes land

**Success Criteria:** Only `events.mjs` holds a writable `better-sqlite3` handle. All other BR3 scripts talk to it via HTTP. Concurrent write stress test passes. The race condition that caused 2026-04-13 is architecturally eliminated.

---

## Parallelization Matrix

| Phase | Key Files                                              | Can Parallel With | Blocked By                    |
| ----- | ------------------------------------------------------ | ----------------- | ----------------------------- |
| 1     | events.db (REPLACE), launchd control                   | -                 | -                             |
| 2     | db-open.mjs (NEW), events.mjs, build-state-machine.mjs | 3                 | 1                             |
| 3     | backup-events-db.sh (NEW), launchd plist (NEW)         | 2, 4              | -                             |
| 4     | db-watchdog.mjs (NEW), launchd plist (NEW)             | 3                 | 2 (uses shared helper)        |
| 5     | events.mjs, build-state-machine.mjs, registry.mjs      | -                 | 2 (same files, file conflict) |

---

## Out of Scope (Future)

- Dashboard schema migrations or event model redesign
- Multi-machine replication of `events.db`
- Switching from SQLite to Postgres (not warranted — SQLite is correct for a single-host dashboard)
- Encryption at rest for the db
- Historical event recovery from the broken file (preserved for forensics, not restored)
- Cross-node registry sync (separate concern)

---

**Total Phases:** 5
**Parallelizable:** Phase 3 runs alongside Phase 2. Phase 4 runs alongside Phase 3. Phase 5 is serial after Phase 2.
