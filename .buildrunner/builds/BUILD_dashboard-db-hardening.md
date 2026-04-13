# Build: dashboard-db-hardening

**Created:** 2026-04-13
**Status:** Phase 1 In Progress
**Deploy:** local — infra (`~/.buildrunner/` scripts + launchd agents, no app deploy)

## Overview

Recover from the 2026-04-13 `events.db` corruption and ensure it can never recur silently. Root cause: `events.mjs` and `build-state-machine.mjs` (via `registry.mjs`) both write to `~/.buildrunner/dashboard/events.db` directly with `better-sqlite3` and don't coordinate on journal mode, busy_timeout, or checkpoint strategy. Between 09:04 and 13:21 today, one of them wrote header bytes inconsistent with the WAL, corrupting the file. The dashboard UI kept "working" because `events.mjs` (PID 86944) was serving stale mmap'd pages from its 08:58 startup snapshot.

`observability.mjs` opens **readonly** at line 17 and is not part of the race.

## Parallelization Matrix

| Phase | Key Files                                              | Can Parallel With | Blocked By        |
| ----- | ------------------------------------------------------ | ----------------- | ----------------- |
| 1     | events.db (REPLACE), launchd control                   | -                 | -                 |
| 2     | db-open.mjs (NEW), events.mjs, build-state-machine.mjs | 3                 | 1                 |
| 3     | backup-events-db.sh (NEW), launchd plist (NEW)         | 2, 4              | -                 |
| 4     | db-watchdog.mjs (NEW), launchd plist (NEW)             | 3                 | 2                 |
| 5     | events.mjs, build-state-machine.mjs, registry.mjs      | -                 | 2 (file conflict) |

## Phases

### Phase 1: Recovery + Safe Restart

**Status:** in_progress
**Goal:** Fresh readable `events.db`, broken file preserved for forensics, `BUILD_cross-model-review` + `BUILD_cluster-max` + `BUILD_geo-v2` all visible in the dashboard.

**Files:**

- `~/.buildrunner/dashboard/events.db` (REPLACE)
- `~/.buildrunner/dashboard/events.db-wal` (DELETE)
- `~/.buildrunner/dashboard/events.db-shm` (DELETE)
- `~/.buildrunner/dashboard/events.db.broken-2026-04-13.*` (NEW — forensic copies)

**Blocked by:** None

**Deliverables:**

- [ ] Stop dashboard server PID 86944 (`events.mjs`) cleanly via launchd (`launchctl unload` the plist, or SIGTERM)
- [ ] Move `events.db`, `events.db-wal`, `events.db-shm` to `events.db.broken-2026-04-13.*` (preserve, do NOT delete)
- [ ] Restart dashboard via launchd; verify it recreates an empty `events.db` on startup
- [ ] Confirm `sqlite3 events.db "SELECT 1"` returns successfully on the fresh file
- [ ] Re-register `BuildRunner3:BUILD_cross-model-review` (5 phases — the amendment from this session is in the spec but not in the registry)
- [ ] Re-register `BuildRunner3:BUILD_cluster-max` from `~/Projects/BuildRunner3/.buildrunner/builds/BUILD_cluster-max.md`
- [ ] Re-register `geo-command-center:BUILD_geo-v2` from `~/Projects/geo-command-center/.buildrunner/builds/BUILD_geo-v2.md` — cross-project, must use `--path ~/Projects/geo-command-center --project geo-command-center`
- [ ] Verify dashboard UI lists all three named builds before declaring Phase 1 complete

**Success Criteria:** Dashboard UI lists `BUILD_cross-model-review` (5 phases), `BUILD_cluster-max`, and `BUILD_geo-v2`. Fresh `events.db` opens cleanly from both `sqlite3` CLI and a standalone `new Database()` call. Broken file preserved under `.broken-2026-04-13` for later inspection.

**Note:** Do NOT call `registry.mjs --register-all` — that flag does not exist (verified via grep). All restoration in Phase 1 is explicit per-build.

---

### Phase 2: Shared DB-Open Helper

**Status:** not_started
**Goal:** Every db open uses one shared helper with identical pragmas. No raw `new Database(DB_PATH)` survives outside the helper.

**Files:**

- `~/.buildrunner/lib/db-open.mjs` (NEW)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY)
- `~/.buildrunner/lib/build-state-machine.mjs` (MODIFY)
- `~/.buildrunner/dashboard/observability.mjs` (MODIFY — readonly path)

**Blocked by:** Phase 1 (need a readable db to test against)

**Deliverables:**

- [ ] Create `db-open.mjs` exporting `openEventsDb({ readonly })` that sets: `journal_mode=WAL`, `busy_timeout=5000`, `synchronous=NORMAL`, `foreign_keys=ON`
- [ ] Replace `new Database(DB_PATH)` in `events.mjs`, `build-state-machine.mjs`, and `observability.mjs` (readonly path) with `openEventsDb()`
- [ ] Grep `~/.buildrunner/` (excluding `node_modules/`) for `new Database(` — must return zero outside `db-open.mjs`
- [ ] Add startup-time assertion in `events.mjs`: refuse to start if `PRAGMA journal_mode` ≠ `wal`
- [ ] Smoke test: concurrent `events.mjs` write + `registry.mjs add` succeed without lock errors

**Success Criteria:** All db opens go through `db-open.mjs`. Grep for `new Database(` outside the helper and `node_modules/` returns zero matches. Concurrent writes from `events.mjs` and `registry.mjs` coexist without errors.

---

### Phase 3: Hourly Backups + Rotation

**Status:** not_started
**Goal:** Recovery from corruption is one `mv` away.

**Files:**

- `~/.buildrunner/scripts/backup-events-db.sh` (NEW)
- `~/Library/LaunchAgents/com.buildrunner.db-backup.plist` (NEW)
- `~/.buildrunner/dashboard/backups/` (NEW directory, auto-created)
- `~/.buildrunner/logs/db-backup.log` (NEW, auto-created)

**Blocked by:** None — all new files, runs parallel to Phase 2

**Deliverables:**

- [ ] `backup-events-db.sh` uses `sqlite3 events.db ".backup <dest>"` (online safe method, NOT `cp`)
- [ ] launchd plist fires the script hourly, survives reboot
- [ ] Rotation: keep last 24 hourly + last 7 daily backups in `dashboard/backups/`
- [ ] Script exits non-zero on `.backup` failure and logs to `~/.buildrunner/logs/db-backup.log`
- [ ] `--restore <backup-file>` flag stops the dashboard, swaps the backup in, and restarts
- [ ] Manual test: run once, confirm a readable `.bak` lands in `backups/` and the dashboard keeps running

**Success Criteria:** 24 rolling hourly + 7 daily backups present after one day of uptime. Running `--restore` swaps cleanly without leaving the dashboard in a broken state.

---

### Phase 4: Health Watchdog

**Status:** not_started
**Goal:** Corruption events alert within 5 minutes, not 4 hours.

**Files:**

- `~/.buildrunner/scripts/db-watchdog.mjs` (NEW)
- `~/Library/LaunchAgents/com.buildrunner.db-watchdog.plist` (NEW)
- `~/.buildrunner/logs/db-watchdog.log` (NEW, auto-created)

**Blocked by:** Phase 2 (uses `openEventsDb()` from the shared helper)

**Deliverables:**

- [ ] `db-watchdog.mjs` opens `events.db` via the shared helper every 5 min, runs `PRAGMA integrity_check`, asserts result === `ok`
- [ ] Also runs a real `SELECT COUNT(*) FROM builds` to catch mmap-vs-disk drift (the failure mode that masked today's corruption)
- [ ] On failure: write loud entry to `db-watchdog.log`, post dashboard SSE alert (`db_health_alert`), auto-trigger a `.backup` snapshot before state degrades further
- [ ] launchd plist runs the script every 300s
- [ ] Dashboard UI shows a red banner when last watchdog entry is a failure
- [ ] Test: deliberately corrupt a copy of the db in a sandbox, point watchdog at it, confirm alert fires within one cycle

**Success Criteria:** Watchdog runs on schedule, logs ok every cycle. Simulated corruption triggers the red banner within 5 minutes.

---

### Phase 5: Single-Writer Architecture

**Status:** not_started
**Goal:** Only `events.mjs` ever holds a writable handle on `events.db`. All other processes post HTTP. Multi-writer race becomes architecturally impossible.

**Files:**

- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add write endpoints)
- `~/.buildrunner/lib/build-state-machine.mjs` (MODIFY — split read/write paths)
- `~/.buildrunner/scripts/registry.mjs` (MODIFY — use HTTP client)
- `~/.buildrunner/lib/db-client.mjs` (NEW — thin HTTP client)

**Blocked by:** Phase 2 (same files — file conflict, cannot parallelize)

**Deliverables:**

- [ ] Add POST endpoints on dashboard server for registry add/update/remove and phase state transitions
- [ ] Create `db-client.mjs` mirroring the `build-state-machine.mjs` writer API but talking HTTP to localhost
- [ ] Split `build-state-machine.mjs`: reads stay local (open via helper, readonly), writes delegate to `db-client.mjs`
- [ ] Refactor `registry.mjs` to use `db-client.mjs` exclusively for writes
- [ ] Retire all non-server `new Database()` writer calls — grep must return zero
- [ ] Stress test: 100 concurrent `registry.mjs add` calls during dashboard serving, confirm no lock errors and all writes land

**Success Criteria:** Only `events.mjs` holds a writable `better-sqlite3` handle. All other BR3 scripts talk to it via HTTP. Concurrent stress test passes. The race condition that caused 2026-04-13 is architecturally eliminated.

---

## Out of Scope (Future)

- Dashboard schema migrations or event model redesign
- Multi-machine replication of `events.db`
- Switching from SQLite to Postgres (not warranted — SQLite is correct for a single-host dashboard)
- Encryption at rest
- Historical event recovery from the broken file (preserved for forensics, not restored)
- Cross-node registry sync
- Implementing `--register-all` in `registry.mjs` (small separate task if Byron wants bulk restore)

## Session Log

[Will be updated by /begin]
