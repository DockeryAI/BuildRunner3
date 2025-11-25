#!/bin/bash
# Debug Session Aliases for BuildRunner
# Source this file in your shell: source .buildrunner/scripts/debug-aliases.sh

# Start full debug session
alias debug-start='.buildrunner/scripts/debug-session.sh'

# Quick test with logging
alias tlog='.buildrunner/scripts/log-test.sh'

# Extract errors for Claude
alias show-errors='.buildrunner/scripts/extract-errors.sh'

# Show latest log
alias show-log='cat .buildrunner/debug-sessions/latest.log'

# Show last 50 lines
alias show-last='tail -50 .buildrunner/debug-sessions/latest.log'

# Copy latest log to clipboard (macOS)
alias copy-log='cat .buildrunner/debug-sessions/latest.log | pbcopy && echo "✅ Log copied to clipboard"'

# Clear debug sessions
alias clear-logs='rm -rf .buildrunner/debug-sessions/* && echo "✅ Debug sessions cleared"'

echo "✅ Debug aliases loaded:"
echo "  debug-start   - Start full debug session"
echo "  tlog <cmd>    - Run test with logging (e.g., tlog pytest tests/)"
echo "  show-errors   - Extract errors for Claude"
echo "  show-log      - Show full latest log"
echo "  show-last     - Show last 50 lines"
echo "  copy-log      - Copy log to clipboard"
echo "  clear-logs    - Clear all debug logs"
