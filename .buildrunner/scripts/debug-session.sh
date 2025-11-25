#!/bin/bash
# BuildRunner Debug Session Logger
# Automatically captures all command output for Claude debugging

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Setup paths
LOGDIR=".buildrunner/debug-sessions"
mkdir -p "$LOGDIR"
SESSION_ID=$(date +%Y%m%d_%H%M%S)
SESSION_FILE="$LOGDIR/session_${SESSION_ID}.log"
LATEST_LINK="$LOGDIR/latest.log"

echo -e "${GREEN}🔴 Debug Session Started${NC}"
echo -e "${BLUE}Session ID: ${SESSION_ID}${NC}"
echo -e "${YELLOW}Logs: ${SESSION_FILE}${NC}"
echo ""
echo -e "${GREEN}All commands will be logged automatically${NC}"
echo -e "${YELLOW}Type 'exit' to end session and get Claude-ready summary${NC}"
echo ""

# Start logging
{
    echo "=== DEBUG SESSION STARTED: $(date) ==="
    echo "Project: BuildRunner3"
    echo "Directory: $(pwd)"
    echo "=================================="
    echo ""
} > "$SESSION_FILE"

# Create symlink to latest session
ln -sf "session_${SESSION_ID}.log" "$LATEST_LINK"

# Function to log commands
log_command() {
    echo -e "\n${BLUE}$ $@${NC}"
    {
        echo ""
        echo "=== COMMAND: $(date +%H:%M:%S) ==="
        echo "$ $@"
        echo "--- OUTPUT ---"
    } >> "$SESSION_FILE"

    # Run command and capture output
    "$@" 2>&1 | tee -a "$SESSION_FILE"
    local exit_code=${PIPESTATUS[0]}

    {
        echo "--- EXIT CODE: $exit_code ---"
        echo ""
    } >> "$SESSION_FILE"

    return $exit_code
}

# Wrapper functions for common test commands
test() {
    if [ "$1" == "pytest" ] || [ "$1" == "py" ]; then
        shift
        log_command pytest "$@"
    elif [ "$1" == "npm" ] || [ "$1" == "node" ]; then
        shift
        log_command npm test "$@"
    elif [ "$1" == "jest" ]; then
        shift
        log_command npx jest "$@"
    else
        log_command "$@"
    fi
}

run() {
    log_command "$@"
}

# Start interactive shell with logging
export PS1="${YELLOW}[debug]${NC} $ "
export -f log_command
export -f test
export -f run

echo -e "${GREEN}Quick commands:${NC}"
echo "  test pytest <args>  - Run pytest with logging"
echo "  test npm <args>     - Run npm test with logging"
echo "  run <command>       - Run any command with logging"
echo "  br autodebug run    - Run BuildRunner's auto-debug"
echo ""

# Start subshell
bash --rcfile <(
    echo "source ~/.bashrc 2>/dev/null || source ~/.zshrc 2>/dev/null"
    echo "alias test='test'"
    echo "alias run='run'"
    echo "export PS1='${YELLOW}[debug]${NC} $ '"
)

# On exit, create summary
echo ""
echo -e "${GREEN}=== Session Ended ===${NC}"
echo ""
echo -e "${BLUE}Full log saved to:${NC}"
echo "  $SESSION_FILE"
echo ""
echo -e "${YELLOW}To share with Claude, use one of:${NC}"
echo "  cat $LATEST_LINK        # Show full session"
echo "  tail -100 $LATEST_LINK  # Show last 100 lines"
echo "  grep ERROR $LATEST_LINK # Show only errors"
echo ""
echo -e "${GREEN}Or reference in Claude:${NC}"
echo "  'Check debug session at: $SESSION_FILE'"