#!/bin/bash
# Lockwood hunt sourcer — standalone cron (separate from uvicorn)
# Runs one sweep cycle, exits. Launched every 5 min by launchd.
# Avoids blocking uvicorn's event loop.

LOCKWOOD_DIR="$HOME/repos/BuildRunner3"
PYTHON="/opt/homebrew/Cellar/python@3.11/3.11.15/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python"
LOG="$HOME/.buildrunner/sourcer.log"

# --- Flock guard: prevent double-fire if launchd overlaps invocations ---
# 'flock -n' acquires a non-blocking exclusive lock; exits 1 immediately if
# another instance holds it, which causes this invocation to skip gracefully.
LOCK_FILE="/tmp/br3-sourcer.lock"
exec 9>"$LOCK_FILE"
if ! flock -n 9; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] sourcer already running — skipping" >> "$LOG"
    exit 0
fi

# Only run if uvicorn is healthy (sourcer needs Lockwood API for hunt list)
if ! curl -sf --max-time 5 "http://127.0.0.1:8100/health" >/dev/null 2>&1; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Lockwood API not ready — skipping sweep" >> "$LOG"
    exit 0
fi

cd "$LOCKWOOD_DIR"
"$PYTHON" -c '
import asyncio
from core.cluster.hunt_sourcer import check_hunts_once
asyncio.run(check_hunts_once())
' >> "$LOG" 2>&1
