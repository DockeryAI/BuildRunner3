#!/bin/bash
# Lockwood uvicorn keepalive watchdog
# Checks process, restarts uvicorn if down with startup grace period
# Install: launchctl load ~/Library/LaunchAgents/com.br3.lockwood-keepalive.plist

LOCKWOOD_DIR="$HOME/repos/BuildRunner3"
PYTHON="/opt/homebrew/Cellar/python@3.11/3.11.15/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python"
PORT=8100
LOG="$HOME/.buildrunner/keepalive.log"
MODULE="core.cluster.node_semantic"
PIDFILE="$HOME/.buildrunner/lockwood-uvicorn.pid"
GRACE_SECONDS=90  # Don't restart during model loading window

check_and_restart() {
  # Check if process exists
  if pgrep -f "uvicorn.*node_semantic" >/dev/null 2>&1; then
    return 0
  fi

  # Startup grace period — don't rapid-restart during model loading
  if [ -f "$PIDFILE" ]; then
    STARTED_AT=$(stat -f %m "$PIDFILE" 2>/dev/null || echo 0)
    NOW=$(date +%s)
    ELAPSED=$((NOW - STARTED_AT))
    if [ "$ELAPSED" -lt "$GRACE_SECONDS" ]; then
      return 0  # Still within grace period, don't restart yet
    fi
  fi

  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Process not found — restarting uvicorn" >> "$LOG"

  # Kill any zombie processes holding the port
  lsof -ti :$PORT 2>/dev/null | xargs kill -9 2>/dev/null || true

  # Start uvicorn from project root (module path requires it)
  # Code indexer enabled — uses ~275MB for embedding model
  # DISABLE_SOURCER=true: skip hunt sourcer (runs separately via launchd)
  # APIFY_API_KEY: seller verification for Reddit/eBay deals
  cd "$LOCKWOOD_DIR"
  source "$HOME/.buildrunner/.env" 2>/dev/null || true
  DISABLE_SOURCER=true APIFY_API_KEY="${APIFY_API_KEY:-}" nohup "$PYTHON" -m uvicorn "$MODULE:app" --host 0.0.0.0 --port $PORT >> "$LOG" 2>&1 &
  NEWPID=$!
  echo "$NEWPID" > "$PIDFILE"
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Restarted uvicorn (PID $NEWPID) [indexer=ON, grace=${GRACE_SECONDS}s]" >> "$LOG"
}

check_and_restart
