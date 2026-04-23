#!/usr/bin/env bash
# developer-brief.sh — Generates a context brief for Claude sessions.
# Aggregates: git state, recent commits, failing tests, BR3 phase, TODOs.
# When cluster is online, also pulls node data.
#
# Usage: ~/.buildrunner/scripts/developer-brief.sh [project_path]
# Output: stdout (meant to be captured by SessionStart hook)

# Portable timeout (works on macOS without coreutils)
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
# shellcheck disable=SC1091
source "$SCRIPT_DIR/_portable-timeout.sh"

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

  # Runtime alerts (pushed by log analyzer)
  WALTER_ALERTS=$(curl -s --max-time 3 "$WALTER_URL/api/alerts?limit=5" 2>/dev/null)
  if [ -n "$WALTER_ALERTS" ] && [ "$WALTER_ALERTS" != '{"alerts":[]}' ]; then
    echo ""
    echo "## Runtime Alerts"
    echo "$WALTER_ALERTS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
for a in d.get('alerts', []):
    sev = a.get('severity', '?')
    icon = '🔴' if sev == 'critical' else '🟠' if sev == 'high' else '⚠'
    print(f'  {icon} {a[\"pattern_type\"]}: {a[\"description\"][:100]} ({a.get(\"received_at\", \"?\")[:16]})')
" 2>/dev/null
  fi
fi
echo ""

# --- Open TODOs (fast — 3 second cap) ---
echo "## TODOs in Recent Changes"
portable_timeout 3 bash -c '
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

# --- Below Log Summarization (optional, instant, zero API cost) ---
BELOW_URL=$("$CLUSTER_CHECK" inference 2>/dev/null)

# --- Log Analysis (runs locally on Muddy) ---
ANALYSIS_URL="http://127.0.0.1:8200"
ANALYSIS=$(curl -s --max-time 2 "$ANALYSIS_URL/api/logs/analyze" 2>/dev/null)
if [ -n "$ANALYSIS" ] && [ "$ANALYSIS" != "null" ] && [ "$ANALYSIS" != '{"summary":"No active patterns","patterns":[],"total_patterns":0,"last_analysis":0.0}' ]; then
  echo "## Log Analysis"
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

# --- Relevant Research (if Lockwood + BUILD spec available) ---
if [ "${BR3_CLUSTER:-}" != "off" ]; then
  RESEARCH_LOCKWOOD=$("$CLUSTER_CHECK" semantic-search 2>/dev/null)
  if [ -n "$RESEARCH_LOCKWOOD" ] && [ -n "${LATEST_BUILD:-}" ]; then
    # Extract current phase description from BUILD spec
    PHASE_DESC=$(python3 -c "
import re, sys
with open('$LATEST_BUILD') as f:
    text = f.read()
# Find the first IN_PROGRESS or next PLANNED phase
phases = re.findall(r'### Phase \d+[^\n]*\n(.*?)(?=### Phase|\Z)', text, re.DOTALL)
for p in phases:
    if 'IN_PROGRESS' in p or 'PLANNED' in p:
        # Get first meaningful line
        for line in p.strip().split('\n'):
            line = line.strip()
            if line and not line.startswith('**Status') and not line.startswith('---'):
                print(line[:200])
                break
        break
" 2>/dev/null || true)

    if [ -n "$PHASE_DESC" ]; then
      ENCODED_QUERY=$(python3 -c "import urllib.parse; print(urllib.parse.quote('$PHASE_DESC'))" 2>/dev/null || echo "$PHASE_DESC")
      RESEARCH_DATA=$(curl -s --max-time 3 "$RESEARCH_LOCKWOOD/api/research/search?query=$ENCODED_QUERY&limit=3" 2>/dev/null)
      if [ -n "$RESEARCH_DATA" ] && [ "$RESEARCH_DATA" != "null" ]; then
        DEDUP_FILE="${TMPDIR:-/tmp}/br3-research-seen-$$.txt"
        RESEARCH_OUTPUT=$(python3 -c "
import json, sys, os
try:
    data = json.loads('''$RESEARCH_DATA''')
    results = data.get('results', [])[:3]
    dedup_file = '$DEDUP_FILE'
    new_ids = []
    for r in results:
        rid = r.get('id', '')
        title = r.get('title', '')
        section = r.get('section', '')
        score = r.get('score', 0)
        print(f'  [{score:.2f}] {title}')
        if section:
            print(f'    Section: {section}')
        if rid:
            new_ids.append(rid)
    if new_ids:
        with open(dedup_file, 'a') as f:
            for nid in new_ids:
                f.write(nid + '\n')
except: pass
" 2>/dev/null || true)

        if [ -n "$RESEARCH_OUTPUT" ]; then
          echo "## Relevant Research"
          echo "$RESEARCH_OUTPUT"
          echo ""
        fi
      fi
    fi
  fi
fi

# --- Cluster Status (if available) ---
if [ -x "$CLUSTER_CHECK" ]; then
  # Only check Lockwood (semantic-search) — it's the memory node.
  # Other nodes are checked only when their roles are needed by skills.
  # This keeps startup fast (1 ping instead of 5).
  SEMANTIC_URL=$("$CLUSTER_CHECK" semantic-search 2>/dev/null)

  TOTAL=$(cd "$PROJECT_PATH" && python3 -m core.cluster.cluster_config get-node-count 2>/dev/null || python3 -c "import json; print(len(json.load(open('$HOME/.buildrunner/cluster.json')).get('nodes', {})))" 2>/dev/null || echo "0")
  ONLINE=0
  ONLINE_LIST=""
  for ROLE in semantic-search test-runner parallel-builder staging-server inference; do
    RURL=$("$CLUSTER_CHECK" "$ROLE" 2>/dev/null)
    if [ -n "$RURL" ]; then
      ONLINE=$((ONLINE + 1))
      ONLINE_LIST="$ONLINE_LIST $ROLE"
    fi
  done

  if [ "$TOTAL" -gt 0 ]; then
    echo "## Cluster"
    echo "  Nodes online: $ONLINE/$TOTAL ($ONLINE_LIST )"

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
    import urllib.parse
    raw = urllib.parse.unquote(s.get('working_on', 'unknown'))
    when = s.get('when', '?')
    # Parse structured narrative: WORKING_ON: x | NEXT: y | BLOCKERS: z | INTERRUPTED_AT: w
    if ' | ' in raw and 'WORKING_ON:' in raw:
        parts = {}
        for seg in raw.split(' | '):
            if ':' in seg:
                k, _, v = seg.partition(':')
                parts[k.strip()] = v.strip()
        print(f'  Last session ({when}):')
        if parts.get('WORKING_ON'):
            print(f'    Was doing: {parts[\"WORKING_ON\"]}')
        if parts.get('INTERRUPTED_AT') and parts['INTERRUPTED_AT'].lower() not in ('', 'none', 'n/a'):
            print(f'    Interrupted at: {parts[\"INTERRUPTED_AT\"]}')
        if parts.get('NEXT'):
            print(f'  ▶ NEXT STEP: {parts[\"NEXT\"]}')
        if parts.get('BLOCKERS') and parts['BLOCKERS'].lower() not in ('', 'none'):
            print(f'    Blockers: {parts[\"BLOCKERS\"]}')
    else:
        print(f'  Last session: {raw} ({when})')
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
    for n in d['architecture_notes'][:5]:
        topic = n.get('topic', '?')
        content = n.get('content', '')[:120]
        print(f'    • {topic}: {content}')
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

    # Lomax (staging) — fast 2s check for last build status of current project
    STAGING_URL=$("$CLUSTER_CHECK" staging-server 2>/dev/null)
    if [ -n "$STAGING_URL" ]; then
      PROJECT_LC=$(basename "$PROJECT_PATH" | tr '[:upper:]' '[:lower:]')
      BUILD_STATUS=$(curl -s --max-time 2 "$STAGING_URL/api/projects/$PROJECT_LC/build/status" 2>/dev/null)
      if [ -n "$BUILD_STATUS" ] && echo "$BUILD_STATUS" | grep -q '"passed"'; then
        echo ""
        echo "## Lomax (staging)"
        echo "$BUILD_STATUS" | python3 -c "
import json, sys, time
d = json.load(sys.stdin)
icon = '✓' if d.get('passed') else '✗'
ts = d.get('timestamp', 0)
age = int((time.time() - ts) / 60) if ts else 0
print(f'  Last build: {icon} {\"passed\" if d.get(\"passed\") else \"FAILED\"} ({age}m ago, {d.get(\"duration_sec\",0)}s)')
if not d.get('tsc_ok'):
    print(f'    ✗ tsc --noEmit failed')
if not d.get('vite_ok'):
    print(f'    ✗ vite build failed')
" 2>/dev/null
      fi
    fi
    echo ""
  fi
fi

# --- Below Log Summary (if active patterns exist and Below is online) ---
if [ -n "$BELOW_URL" ] && [ -n "$ANALYSIS" ] && [ "$ANALYSIS" != "null" ]; then
  LOG_PATTERNS=$(echo "$ANALYSIS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
s = d.get('summary', '')
if s and s != 'No active patterns':
    print(s[:500])
" 2>/dev/null)
  if [ -n "$LOG_PATTERNS" ]; then
    SUMMARY=$(curl -s --max-time 10 -X POST "$BELOW_URL/api/summarize" \
      -H "Content-Type: application/json" \
      -d "{\"text\":\"$LOG_PATTERNS\"}" 2>/dev/null)
    if [ -n "$SUMMARY" ] && [ "$SUMMARY" != "null" ]; then
      echo "## Below Analysis"
      echo "$SUMMARY" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  {d.get(\"summary\", d) if isinstance(d, dict) else d}')
" 2>/dev/null
      echo ""
    fi
  fi
fi

# --- Intelligence & Deals Alerts (if intel-digest.sh exists) ---
INTEL_DIGEST="$HOME/.buildrunner/scripts/intel-digest.sh"
if [ -x "$INTEL_DIGEST" ]; then
  INTEL_OUTPUT=$("$INTEL_DIGEST" 2>/dev/null)
  if [ -n "$INTEL_OUTPUT" ]; then
    echo "$INTEL_OUTPUT"
    echo ""
  fi
fi

echo "═══════════════════════════════════════════"
