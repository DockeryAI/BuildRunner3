#!/bin/bash
# Lockwood uvicorn keepalive watchdog
# Checks port 8100, restarts uvicorn if down
# Install: launchctl load ~/Library/LaunchAgents/com.br3.lockwood-keepalive.plist

LOCKWOOD_DIR="$HOME/repos/BuildRunner3"
PYTHON="/opt/homebrew/Cellar/python@3.11/3.11.15/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python"
PORT=8100
LOG="$HOME/.buildrunner/keepalive.log"
MODULE="core.cluster.node_semantic"

GRACE_FILE="/tmp/lockwood-restart-grace"

check_and_restart() {
  if curl -sf --max-time 5 "http://127.0.0.1:${PORT}/health" >/dev/null 2>&1; then
    return 0
  fi

  # Health check failed — but if process exists and is within grace period, skip (still starting)
  if [ -f "$GRACE_FILE" ]; then
    GRACE_AGE=$(( $(date +%s) - $(stat -f %m "$GRACE_FILE" 2>/dev/null || echo 0) ))
    if [ "$GRACE_AGE" -lt 60 ] && pgrep -f "uvicorn.*node_semantic" >/dev/null 2>&1; then
      return 0  # process exists and still starting up
    fi
    rm -f "$GRACE_FILE"
  fi

  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Port $PORT not responding — restarting uvicorn" >> "$LOG"

  # Kill any existing uvicorn processes
  pkill -f "uvicorn.*node_semantic" 2>/dev/null
  sleep 1

  # Ensure only one instance
  PIDS=$(pgrep -f "uvicorn.*node_semantic" 2>/dev/null)
  if [ -n "$PIDS" ]; then
    echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Force killing stale uvicorn: $PIDS" >> "$LOG"
    kill -9 $PIDS 2>/dev/null
    sleep 1
  fi

  # Start uvicorn from project root (module path requires it)
  cd "$LOCKWOOD_DIR"
  nohup "$PYTHON" -m uvicorn "$MODULE:app" --host 0.0.0.0 --port $PORT >> "$LOG" 2>&1 &
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Restarted uvicorn (PID $!)" >> "$LOG"
  touch "$GRACE_FILE"  # 30s grace period before next health check
}

check_and_restart
