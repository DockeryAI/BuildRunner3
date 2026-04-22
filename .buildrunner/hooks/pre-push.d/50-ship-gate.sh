#!/usr/bin/env bash
# 50-ship-gate.sh — BR3 /ship pre-push gate fragment
# Blocks push if sentinel missing, stale, head_sha mismatch, or required gates not passed.
# Slots into the BR3 composed-hook chain at lexical position 50.
# Exit 0 = allow push. Non-zero = block push.
#
# Install via: .buildrunner/hooks/install-hooks.sh
# Bypass (emergency): BR3_SHIP_BYPASS_PREPUSH=1 git push  (logged to autoheal-overrides.log)
#
set -euo pipefail

SENTINEL_SH="${HOME}/.buildrunner/scripts/ship/ship-sentinel.sh"

# Bypass escape hatch — logged, audited
if [[ "${BR3_SHIP_BYPASS_PREPUSH:-0}" == "1" ]]; then
  PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  OVERRIDE_LOG="${PROJECT_ROOT}/.buildrunner/ship/autoheal-overrides.log"
  mkdir -p "$(dirname "$OVERRIDE_LOG")"
  echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) PREPUSH_BYPASS branch=$(git rev-parse --abbrev-ref HEAD 2>/dev/null) head=$(git rev-parse HEAD 2>/dev/null | head -c 12) user=${USER}" >> "$OVERRIDE_LOG"
  echo "ship: pre-push gate bypassed (BR3_SHIP_BYPASS_PREPUSH=1) — logged"
  exit 0
fi

# Skip if ship sentinel script is not installed (fresh install scenario)
if [ ! -f "$SENTINEL_SH" ]; then
  echo "ship: pre-push gate skipped (ship-sentinel.sh not installed at $SENTINEL_SH)"
  exit 0
fi

# Run sentinel validation
if bash "$SENTINEL_SH" validate 2>&1; then
  # Valid — allow push
  exit 0
else
  SENTINEL_EXIT=$?
  PROJECT_ROOT="$(git rev-parse --show-toplevel 2>/dev/null || pwd)"
  SENTINEL="${PROJECT_ROOT}/.buildrunner/ship/last-ship.json"
  BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo unknown)"
  HEAD="$(git rev-parse HEAD 2>/dev/null | head -c 12 || echo unknown)"

  echo ""
  echo "================================================================"
  echo "PUSH BLOCKED: /ship gate not satisfied"
  echo "================================================================"
  echo "Branch: ${BRANCH}   HEAD: ${HEAD}"
  echo ""

  if [ ! -f "$SENTINEL" ]; then
    echo "Reason: No ship sentinel found."
    echo ""
    echo "Run /ship to gate this branch before pushing."
  else
    echo "Reason: Sentinel is stale, head_sha mismatch, or required gates not passed."
    echo ""
    # Show current sentinel state
    python3 -c "
import json, sys
try:
    d = json.load(open('$SENTINEL'))
    print('  Sentinel head:    ' + d.get('head_sha','?')[:12])
    print('  gates_required:   ' + str(d.get('gates_required',[])))
    print('  gates_passed:     ' + str(d.get('gates_passed',[])))
    missing = set(d.get('gates_required',[])) - set(d.get('gates_passed',[]))
    if missing:
        print('  gates missing:    ' + str(sorted(missing)))
except Exception as e:
    print('  (could not parse sentinel: ' + str(e) + ')')
" 2>/dev/null || true
    echo ""
    echo "Run /ship (or /ship --fast for non-critical branches) to satisfy the gate."
    echo ""
    echo "Emergency bypass (logged and audited):"
    echo "  BR3_SHIP_BYPASS_PREPUSH=1 git push"
  fi

  echo "================================================================"
  echo ""
  exit 1
fi
