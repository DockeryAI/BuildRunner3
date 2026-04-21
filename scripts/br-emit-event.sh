#!/usr/bin/env bash
# br-emit-event.sh — CLI wrapper: write telemetry event to telemetry.db
#
# Usage:
#   br-emit-event.sh <event_type> '<json_metadata>'
#
# Examples:
#   br-emit-event.sh context_bundle_served '{"phase":"2","task":"dispatch"}'
#   br-emit-event.sh cache_hit '{"breakpoint":1}'
#
# Exit: always 0 — non-blocking, swallows all errors
#
# Requirements: python3 on PATH, .buildrunner/telemetry.db must exist

set -uo pipefail

EVENT_TYPE="${1:-}"
METADATA="${2:--}"
if [[ "$METADATA" == "-" ]]; then METADATA="{}"; fi

if [[ -z "$EVENT_TYPE" ]]; then
  echo "Usage: br-emit-event.sh <event_type> '<json_metadata>'" >&2
  exit 0
fi

# Pass event_type and metadata via env vars to avoid heredoc quoting issues
export _BR_EMIT_EVENT_TYPE="$EVENT_TYPE"
export _BR_EMIT_METADATA="$METADATA"

# Truncate metadata values > 256 chars — Python handles full truncation
python3 - <<'PYEOF' 2>/dev/null || true
import sys, json, sqlite3, uuid, os
from datetime import datetime
from pathlib import Path

event_type = os.environ.get("_BR_EMIT_EVENT_TYPE", "")
raw_meta = os.environ.get("_BR_EMIT_METADATA", "{}")

# Find telemetry.db — BR3_PROJECT_ROOT takes priority over cwd
db_candidates = [
    Path(os.environ.get("BR3_PROJECT_ROOT", "")) / ".buildrunner" / "telemetry.db",
    Path.cwd() / ".buildrunner" / "telemetry.db",
    Path.home() / "Projects" / "BuildRunner3" / ".buildrunner" / "telemetry.db",
]
db_path = next((p for p in db_candidates if p.exists()), None)
if db_path is None:
    sys.exit(0)

try:
    meta = json.loads(raw_meta)
except Exception:
    meta = {"raw": str(raw_meta)[:256]}

# Truncate all string values to 256 chars to prevent PII/prompt leakage
sanitized = {}
for k, v in meta.items():
    if isinstance(v, str) and len(v) > 256:
        sanitized[str(k)[:64]] = v[:256]
    else:
        sanitized[str(k)[:64]] = v

row_id = str(uuid.uuid4())
ts = datetime.utcnow().isoformat()

conn = sqlite3.connect(str(db_path))
try:
    conn.execute(
        "INSERT INTO events (event_id, event_type, timestamp, metadata, success) VALUES (?, ?, ?, ?, ?)",
        (row_id, event_type, ts, json.dumps(sanitized), 1),
    )
    conn.commit()
except Exception:
    pass
finally:
    conn.close()
PYEOF

exit 0
