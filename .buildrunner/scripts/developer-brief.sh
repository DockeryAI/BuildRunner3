#!/usr/bin/env bash
# developer-brief.sh — Generates a context brief for Claude sessions.
# Aggregates: git state, recent commits, failing tests, BR3 phase, TODOs.
# When cluster is online, also pulls node data.
#
# Usage: ~/.buildrunner/scripts/developer-brief.sh [project_path]
# Output: stdout (meant to be captured by SessionStart hook)

PROJECT_PATH="${1:-$(git rev-parse --show-toplevel 2>/dev/null || pwd)}"
CLUSTER_CHECK="$HOME/.buildrunner/scripts/cluster-check.sh"

echo "DEVELOPER BRIEF — USE THIS CONTEXT. Do not ask the user to re-explain what they were working on."
echo "This data was loaded automatically from Lockwood (persistent memory node) and local git."
echo "═══════════════════════════════════════════"
echo "  $(date '+%Y-%m-%d %H:%M')"
echo "═══════════════════════════════════════════"
echo ""

# --- Git State ---
echo "## Git State"
cd "$PROJECT_PATH" 2>/dev/null || exit 0
BRANCH=$(git branch --show-current 2>/dev/null)
echo "Branch: $BRANCH"
echo "Status:"
git status --short 2>/dev/null | head -20
UNCOMMITTED=$(git status --short 2>/dev/null | wc -l | tr -d ' ')
if [ "$UNCOMMITTED" -gt 0 ]; then
  echo "  ($UNCOMMITTED uncommitted changes)"
fi
echo ""

# --- Recent Commits ---
echo "## Recent Commits (last 5)"
git log --oneline -5 2>/dev/null
echo ""

# --- BR3 Phase ---
if [ -d "$PROJECT_PATH/.buildrunner/builds" ]; then
  echo "## Active Build"
  # Find most recent BUILD file
  LATEST_BUILD=$(ls -t "$PROJECT_PATH/.buildrunner/builds"/BUILD_*.md 2>/dev/null | head -1)
  if [ -n "$LATEST_BUILD" ]; then
    BUILD_NAME=$(basename "$LATEST_BUILD" .md)
    echo "Build: $BUILD_NAME"
    # Extract current status line
    grep -m1 "^**Status:**" "$LATEST_BUILD" 2>/dev/null || echo "Status: unknown"
    # Show phases with status
    grep "^### Phase" "$LATEST_BUILD" 2>/dev/null | while read -r line; do
      PHASE_NUM=$(echo "$line" | grep -oE 'Phase [0-9]+')
      # Get the status line after this phase header
      STATUS=$(grep -A2 "$line" "$LATEST_BUILD" 2>/dev/null | grep "Status:" | head -1 | sed 's/.*Status:\*\* //')
      echo "  $PHASE_NUM: ${STATUS:-unknown}"
    done
  fi
  echo ""
fi

# --- Failing Tests ---
echo "## Test Status"
if [ -f "$PROJECT_PATH/package.json" ]; then
  # Check for recent test results
  if [ -f "$PROJECT_PATH/.buildrunner/test-results.json" ]; then
    python3 -c "
import json, os
f = '$PROJECT_PATH/.buildrunner/test-results.json'
if os.path.exists(f):
    data = json.load(open(f))
    passed = data.get('passed', 0)
    failed = data.get('failed', 0)
    total = passed + failed
    print(f'Last run: {passed}/{total} passed')
    if failed > 0:
        for fail in data.get('failures', [])[:5]:
            print(f'  FAIL: {fail}')
" 2>/dev/null
  else
    echo "No cached test results. Run tests to populate."
  fi
else
  echo "No package.json found."
fi

# Check Walter for continuous test results
WALTER_URL=$("$CLUSTER_CHECK" test-runner 2>/dev/null)
if [ -n "$WALTER_URL" ]; then
  PROJECT_NAME=$(basename "$PROJECT_PATH")
  WALTER_DATA=$(curl -s --max-time 3 "$WALTER_URL/api/results?project=$PROJECT_NAME&latest=true" 2>/dev/null)
  if [ -n "$WALTER_DATA" ] && [ "$WALTER_DATA" != '{"results":[]}' ]; then
    echo ""
    echo "## Walter (Continuous Tests)"
    echo "$WALTER_DATA" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for r in d.get('results', []):
    icon = '✓' if r['failed'] == 0 else '✗'
    print(f'  {icon} {r[\"runner\"]}: {r[\"passed\"]}/{r[\"total\"]} passed ({r.get(\"timestamp\", \"?\")})')
    for f in r.get('failures', [])[:3]:
        print(f'    FAIL: {f[\"full_name\"]}: {f.get(\"failure_message\", \"\")[:80]}')
" 2>/dev/null
  fi
fi
echo ""

# --- Open TODOs (fast — 3 second cap) ---
echo "## TODOs in Recent Changes"
timeout 3 bash -c '
  git diff HEAD~5 --name-only 2>/dev/null | head -10 | while read -r file; do
    if [ -f "'"$PROJECT_PATH"'/$file" ] && [ "$(stat -f%z "'"$PROJECT_PATH"'/$file" 2>/dev/null || echo 999999)" -lt 50000 ]; then
      TODOS=$(grep -rnI "TODO\|FIXME\|HACK\|XXX" "'"$PROJECT_PATH"'/$file" 2>/dev/null | head -2)
      if [ -n "$TODOS" ]; then
        echo "  $file:"
        echo "$TODOS" | sed "s/^/    /"
      fi
    fi
  done
' 2>/dev/null
echo ""

# --- Log Analysis ---
# Check Crawford first for pre-analyzed patterns, fall back to raw log stats
CRAWFORD_URL=$("$CLUSTER_CHECK" log-analysis 2>/dev/null)
if [ -n "$CRAWFORD_URL" ]; then
  ANALYSIS=$(curl -s --max-time 3 "$CRAWFORD_URL/api/logs/analyze" 2>/dev/null)
  if [ -n "$ANALYSIS" ] && [ "$ANALYSIS" != "null" ]; then
    echo "## Crawford (Log Analysis)"
    echo "$ANALYSIS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
summary = d.get('summary', 'No patterns')
if summary and summary != 'No active patterns':
    for line in summary.split('\n'):
        print(f'  {line}')
else:
    print('  No active patterns')
" 2>/dev/null
    echo ""
  fi
else
  # Fallback: raw log file stats
  if [ -d "$PROJECT_PATH/.buildrunner" ]; then
    echo "## Log Status (local)"
    for LOG in browser.log supabase.log device.log query.log; do
      LOGFILE="$PROJECT_PATH/.buildrunner/$LOG"
      if [ -f "$LOGFILE" ]; then
        LINES=$(wc -l < "$LOGFILE" | tr -d ' ')
        ERRORS=$(grep -ci "error\|fail\|denied\|401\|403\|500" "$LOGFILE" 2>/dev/null)
        LAST_MOD=$(stat -f "%Sm" -t "%H:%M" "$LOGFILE" 2>/dev/null || stat -c "%y" "$LOGFILE" 2>/dev/null | cut -d' ' -f2 | cut -d. -f1)
        echo "  $LOG: ${LINES} lines, ${ERRORS} errors (last update: $LAST_MOD)"
      fi
    done
    echo ""
  fi
fi

# --- Cluster Status (if available) ---
if [ -x "$CLUSTER_CHECK" ]; then
  # Only check Lockwood (semantic-search) — it's the memory node.
  # Other nodes are checked only when their roles are needed by skills.
  # This keeps startup fast (1 ping instead of 5).
  SEMANTIC_URL=$("$CLUSTER_CHECK" semantic-search 2>/dev/null)

  TOTAL=$(python3 -c "import json; print(len(json.load(open('$HOME/.buildrunner/cluster.json')).get('nodes', {})))" 2>/dev/null || echo "0")
  ONLINE=0
  [ -n "$SEMANTIC_URL" ] && ONLINE=1

  if [ "$TOTAL" -gt 0 ]; then
    echo "## Cluster"
    echo "  Nodes online: $ONLINE/$TOTAL"

    # Pull Lockwood's persistent memory
    if [ -n "$SEMANTIC_URL" ]; then
      PROJECT_NAME=$(basename "$PROJECT_PATH")
      BRIEF=$(curl -s --max-time 3 "$SEMANTIC_URL/api/brief/$PROJECT_NAME" 2>/dev/null)
      if [ -n "$BRIEF" ] && [ "$BRIEF" != "null" ] && [ "$BRIEF" != "{}" ]; then
        echo ""
        echo "## Lockwood Memory"
        echo "$BRIEF" | python3 -c "
import json, sys
d = json.load(sys.stdin)

if 'last_session' in d and d['last_session']:
    s = d['last_session']
    print(f'  Last session: {s.get(\"working_on\", \"unknown\")} ({s.get(\"when\", \"?\")})')
    if s.get('todos'):
        for t in s['todos'][:3]:
            print(f'    TODO: {t}')

if 'recent_builds' in d and d['recent_builds']:
    print(f'  Build history: {len(d[\"recent_builds\"])} phases recorded')
    fails = [b for b in d['recent_builds'] if b['status'] == 'failed']
    if fails:
        print(f'    ⚠ {len(fails)} failures in recent history')
        for f in fails[:2]:
            print(f'      {f[\"phase\"]}: {f.get(\"failure\", \"unknown\")}')

if 'test_results' in d and d['test_results']:
    t = d['test_results']
    icon = '✓' if t['failed'] == 0 else '✗'
    print(f'  Tests: {icon} {t[\"passed\"]} passed, {t[\"failed\"]} failed')

if 'log_patterns' in d and d['log_patterns']:
    print(f'  Active log patterns:')
    for p in d['log_patterns'][:3]:
        print(f'    ⚠ {p[\"type\"]}: {p[\"count\"]}x in {p[\"file\"]}')

if 'architecture_notes' in d and d['architecture_notes']:
    print(f'  Architecture notes: {len(d[\"architecture_notes\"])} stored')
" 2>/dev/null
      fi

      # Also show index stats
      STATS=$(curl -s --max-time 2 "$SEMANTIC_URL/api/stats" 2>/dev/null)
      if [ -n "$STATS" ] && [ "$STATS" != "null" ]; then
        echo "$STATS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  Index: {d.get(\"total_files\", 0)} files, {d.get(\"total_chunks\", 0)} chunks')
" 2>/dev/null
      fi
    fi

    # Other nodes (Walter, Crawford, Lomax, Below) are checked by individual skills
    # when they need them, not at startup. Keeps the brief fast.
    echo ""
  fi
fi

echo "═══════════════════════════════════════════"
