#!/bin/bash
# Extract errors from debug session for Claude
# Usage: ./extract-errors.sh [session_file]
# If no file specified, uses latest.log

LOGDIR=".buildrunner/debug-sessions"
LOGFILE="${1:-$LOGDIR/latest.log}"

if [ ! -f "$LOGFILE" ]; then
    echo "❌ No log file found at: $LOGFILE"
    echo "Run a test with log-test.sh first"
    exit 1
fi

echo "📋 ERROR SUMMARY FROM: $LOGFILE"
echo "=================================="
echo ""

# Extract failed commands
echo "🔴 FAILED COMMANDS:"
grep -B 2 "EXIT CODE: [1-9]" "$LOGFILE" | grep "COMMAND:" | sed 's/=== COMMAND: /  • /'
echo ""

# Extract error messages (common patterns)
echo "❌ ERROR MESSAGES:"
grep -E "(ERROR|Error|error:|FAILED|Failed|failed|Exception|Traceback|AssertionError)" "$LOGFILE" | \
    head -30 | \
    sed 's/^/  /'
echo ""

# Show last command with context
echo "📍 LAST COMMAND:"
tail -50 "$LOGFILE" | grep -A 20 "=== COMMAND:"
echo ""

echo "=================================="
echo "📄 Full log: $LOGFILE"
echo ""
echo "💡 To share with Claude:"
echo "   1. Copy the output above"
echo "   2. Or: cat $LOGFILE"
echo "   3. Or: Tell Claude to check this file path"
