#!/bin/bash
# Quick test logger - logs a single command to latest.log
# Usage: ./log-test.sh pytest tests/test_foo.py
#    or: ./log-test.sh npm test

LOGDIR=".buildrunner/debug-sessions"
mkdir -p "$LOGDIR"
LATEST="$LOGDIR/latest.log"

# If latest.log doesn't exist, create new session
if [ ! -f "$LATEST" ]; then
    SESSION_ID=$(date +%Y%m%d_%H%M%S)
    SESSION_FILE="$LOGDIR/session_${SESSION_ID}.log"
    {
        echo "=== DEBUG SESSION: $(date) ==="
        echo "Project: BuildRunner3"
        echo "=================================="
    } > "$SESSION_FILE"
    ln -sf "session_${SESSION_ID}.log" "$LATEST"
fi

# Log and run command
{
    echo ""
    echo "=== COMMAND: $(date +%H:%M:%S) ==="
    echo "$ $@"
    echo "--- OUTPUT ---"
} >> "$LATEST"

"$@" 2>&1 | tee -a "$LATEST"
EXIT_CODE=${PIPESTATUS[0]}

{
    echo "--- EXIT CODE: $EXIT_CODE ---"
} >> "$LATEST"

echo ""
echo "📝 Logged to: $LATEST"

exit $EXIT_CODE
