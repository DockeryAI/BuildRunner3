# Phase 1 Plan — Walter Service Hardening

## Tasks

1. Thread safety locks — Add threading.Lock for _running, _file_hashes, _last_results, _db_lock
2. Queue-based execution — Replace dual trigger with queue.Queue, single consumer, dedup by project+SHA
3. Git SHA change detection — Replace mtime with git diff --name-only, track last_tested_sha
4. Extended /health endpoint — uptime, last_test_run, repo HEADs, memory, queue depth, version
5. Unique temp files — UUID-based paths
6. Queue-based /api/run — Returns queued status with run_id, add polling endpoint
7. Remove dead code — /api/history, /api/running, /api/testmap/baseline, _push_to_lockwood()
8. walter-setup.sh — LaunchAgent plist, deploy, verify
