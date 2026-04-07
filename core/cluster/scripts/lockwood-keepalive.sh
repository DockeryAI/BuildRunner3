#!/bin/bash
# Lockwood uvicorn keepalive watchdog
# Checks port 8100, restarts uvicorn if down
# Install: launchctl load ~/Library/LaunchAgents/com.br3.lockwood-keepalive.plist

LOCKWOOD_DIR="$HOME/repos/BuildRunner3"
PYTHON="/opt/homebrew/Cellar/python@3.11/3.11.15/Frameworks/Python.framework/Versions/3.11/Resources/Python.app/Contents/MacOS/Python"
PORT=8100
LOG="$HOME/.buildrunner/keepalive.log"
MODULE="core.cluster.node_semantic"

check_and_restart() {
  # Check if process exists — don't use HTTP (GIL contention during model loading kills health checks)
  if pgrep -f "uvicorn.*node_semantic" >/dev/null 2>&1; then
    return 0
  fi

  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Process not found — restarting uvicorn" >> "$LOG"

  # Start uvicorn from project root (module path requires it)
  cd "$LOCKWOOD_DIR"
  DISABLE_SOURCER=true nohup "$PYTHON" -m uvicorn "$MODULE:app" --host 0.0.0.0 --port $PORT >> "$LOG" 2>&1 &
  echo "[$(date -u +%Y-%m-%dT%H:%M:%SZ)] Restarted uvicorn (PID $!)" >> "$LOG"
}

check_and_restart
