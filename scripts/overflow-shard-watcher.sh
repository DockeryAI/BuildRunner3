#!/usr/bin/env bash
# overflow-shard-watcher.sh — Monitor Walter queue depth; dispatch overflow shards to Lomax
#
# Behavior:
#   - Poll every 30 seconds
#   - When Walter queue depth > 2, dispatch one shard to Lomax via dispatch-to-node.sh
#   - 60-second cooldown after each dispatch (prevents thrashing)
#   - Hard cap: 3 shards per hour — persisted to file, survives daemon restart
#
# Cap persistence file: ~/.buildrunner/overflow-shard-cap.json
#   Format: {"dispatches": [<ISO8601_timestamp>, ...]}  (last hour only)
#
# Usage: Launched by com.br3.overflow-shard-watcher LaunchAgent (RunAtLoad + KeepAlive)
# Manual run: scripts/overflow-shard-watcher.sh [--once] [--dry-run]

set -euo pipefail

# --- Config ---
POLL_INTERVAL=30          # seconds between queue-depth checks
COOLDOWN=60               # seconds after a dispatch before re-checking
HOURLY_CAP=3              # max shards dispatched in any rolling 60-minute window
CAP_FILE="$HOME/.buildrunner/overflow-shard-cap.json"
LOG_FILE="$HOME/.buildrunner/logs/overflow-shard-watcher.log"
DISPATCH_SCRIPT="$HOME/.buildrunner/scripts/dispatch-to-node.sh"
CLUSTER_CHECK="$HOME/.buildrunner/scripts/cluster-check.sh"
WALTER_QUEUE_THRESHOLD=2  # dispatch when queue depth exceeds this

# --- Flags ---
DRY_RUN=false
ONCE=false
for arg in "$@"; do
  [ "$arg" = "--dry-run" ] && DRY_RUN=true
  [ "$arg" = "--once" ]    && ONCE=true
done

# --- Logging ---
log() {
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) [overflow-shard-watcher] $*" | tee -a "$LOG_FILE"
}

# --- Cap management (persisted across restarts) ---

# Returns number of dispatches in the last 60 minutes from the cap file
count_recent_dispatches() {
  [ -f "$CAP_FILE" ] || echo '{"dispatches":[]}' > "$CAP_FILE"
  local CUTOFF
  CUTOFF=$(date -u -v-1H +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u -d "-1 hour" +%Y-%m-%dT%H:%M:%SZ 2>/dev/null \
    || date -u +%Y-%m-%dT%H:%M:%SZ)
  python3 - <<PYEOF
import json, sys
from datetime import datetime, timezone
cap = json.load(open('$CAP_FILE'))
cutoff = datetime.fromisoformat('$CUTOFF'.replace('Z','+00:00'))
recent = [ts for ts in cap.get('dispatches', [])
          if datetime.fromisoformat(ts.replace('Z','+00:00')) >= cutoff]
print(len(recent))
PYEOF
}

# Append a dispatch timestamp to the cap file (prune entries > 2 hours old)
record_dispatch() {
  [ -f "$CAP_FILE" ] || echo '{"dispatches":[]}' > "$CAP_FILE"
  python3 - <<PYEOF
import json
from datetime import datetime, timezone, timedelta
now = datetime.now(timezone.utc)
cutoff = now - timedelta(hours=2)
path = '$CAP_FILE'
cap = json.load(open(path))
dispatches = [ts for ts in cap.get('dispatches', [])
              if datetime.fromisoformat(ts.replace('Z','+00:00')) >= cutoff]
dispatches.append(now.strftime('%Y-%m-%dT%H:%M:%SZ'))
cap['dispatches'] = dispatches
json.dump(cap, open(path, 'w'))
PYEOF
  log "Recorded dispatch. Cap file updated: $CAP_FILE"
}

# --- Query Walter queue depth ---
get_walter_queue_depth() {
  local WALTER_URL
  WALTER_URL=$("$CLUSTER_CHECK" test-runner 2>/dev/null || echo "")
  if [ -z "$WALTER_URL" ]; then
    echo "0"
    return
  fi
  local QUEUE_RESP
  QUEUE_RESP=$(curl -s --max-time 5 "$WALTER_URL/api/queue" 2>/dev/null || echo "{}")
  python3 -c "
import sys, json
try:
    d = json.loads('$QUEUE_RESP' if '$QUEUE_RESP' else '{}')
    print(d.get('depth', d.get('queue_depth', d.get('pending', 0))))
except:
    print(0)
" 2>/dev/null || echo "0"
}

# --- Dispatch one shard to Lomax ---
dispatch_shard_to_lomax() {
  local PROJECT_PATH="$1"
  local BUILD_ID="$2"
  local SESSION_NAME="lomax-overflow-${BUILD_ID}-$(date +%s)"

  log "Dispatching overflow shard to Lomax: project=$PROJECT_PATH build=$BUILD_ID session=$SESSION_NAME"

  if [ "$DRY_RUN" = "true" ]; then
    log "DRY RUN — would dispatch: $DISPATCH_SCRIPT lomax $PROJECT_PATH 'cd $PROJECT_PATH && claude -p /autopilot go' $SESSION_NAME"
    return 0
  fi

  if [ ! -x "$DISPATCH_SCRIPT" ]; then
    log "ERROR: dispatch-to-node.sh not found or not executable: $DISPATCH_SCRIPT"
    return 1
  fi

  "$DISPATCH_SCRIPT" lomax "$PROJECT_PATH" \
    "cd $PROJECT_PATH && claude -p '/autopilot go'" \
    "$SESSION_NAME" 2>&1 | tee -a "$LOG_FILE"
}

# --- Find the next ready build to shard ---
get_next_ready_build() {
  node "$HOME/.buildrunner/scripts/next-ready-build.mjs" 2>/dev/null \
    | python3 -c "
import sys, json
try:
    d = json.load(sys.stdin)
    if d.get('build_id'):
        print(d.get('project_path', ''), d.get('build_id', ''))
except: pass
" 2>/dev/null || echo ""
}

# --- Main loop ---
mkdir -p "$(dirname "$LOG_FILE")"
log "overflow-shard-watcher started (poll=${POLL_INTERVAL}s cooldown=${COOLDOWN}s cap=${HOURLY_CAP}/hr dry_run=$DRY_RUN)"

while true; do
  QUEUE_DEPTH=$(get_walter_queue_depth)
  log "Walter queue depth: $QUEUE_DEPTH (threshold: $WALTER_QUEUE_THRESHOLD)"

  if [ "$QUEUE_DEPTH" -gt "$WALTER_QUEUE_THRESHOLD" ] 2>/dev/null; then
    # Check cap
    RECENT=$(count_recent_dispatches)
    log "Overflow detected. Recent dispatches (1h): $RECENT / $HOURLY_CAP"

    if [ "$RECENT" -ge "$HOURLY_CAP" ]; then
      log "CAP HIT: $RECENT dispatches in last hour >= cap of $HOURLY_CAP. Skipping shard."
    else
      # Find a ready build to dispatch
      BUILD_INFO=$(get_next_ready_build)
      PROJECT_PATH=$(echo "$BUILD_INFO" | awk '{print $1}')
      BUILD_ID=$(echo "$BUILD_INFO" | awk '{print $2}')

      if [ -n "$PROJECT_PATH" ] && [ -n "$BUILD_ID" ]; then
        log "Dispatching shard: project=$PROJECT_PATH build=$BUILD_ID"
        if dispatch_shard_to_lomax "$PROJECT_PATH" "$BUILD_ID"; then
          record_dispatch
          log "Shard dispatched. Entering ${COOLDOWN}s cooldown."
          sleep "$COOLDOWN"
          [ "$ONCE" = "true" ] && exit 0
          continue
        else
          log "ERROR: Shard dispatch failed."
        fi
      else
        log "No ready build found to shard."
      fi
    fi
  fi

  [ "$ONCE" = "true" ] && exit 0
  sleep "$POLL_INTERVAL"
done
