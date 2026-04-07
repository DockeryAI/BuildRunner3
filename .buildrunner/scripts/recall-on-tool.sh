#!/usr/bin/env bash
# recall-on-tool.sh — PreToolUse hook that surfaces relevant Lockwood memory
# when Claude touches a file. Four sources, queried in parallel:
#   1. Local decisions.log (fast grep, always available)
#   2. Lockwood architecture notes (semantic match on filename + project)
#   3. Lockwood log patterns (if active anomalies exist for this project)
#   4. Research library (semantic search on filename)
#
# Input: JSON on stdin with tool_name + tool_input.file_path
# Output: stdout injected as system-reminder context (or nothing if no matches)
# Budget: must complete in <3s (timeout on Lockwood calls is 2s)
#
# Only fires for Edit|Write|NotebookEdit tools (not Read — too noisy).

set -uo pipefail
# Never block a tool call — always exit 0
trap 'exit 0' ERR

INPUT=$(cat)
TOOL=$(echo "$INPUT" | python3 -c "import json,sys; print(json.load(sys.stdin).get('tool_name',''))" 2>/dev/null || echo "")
FILE=$(echo "$INPUT" | python3 -c "import json,sys; d=json.load(sys.stdin); print(d.get('tool_input',{}).get('file_path',''))" 2>/dev/null || echo "")

# Only run on write-targeted tools (Read is too noisy — fires constantly)
case "$TOOL" in
  Edit|Write|NotebookEdit) ;;
  *) exit 0 ;;
esac

[ -z "$FILE" ] && exit 0

BASE=$(basename "$FILE")

# Resolve project root
PROJECT_DIR=""
if [ -n "${CLAUDE_PROJECT_DIR:-}" ] && [ -d "$CLAUDE_PROJECT_DIR/.buildrunner" ]; then
  PROJECT_DIR="$CLAUDE_PROJECT_DIR"
else
  DIR=$(dirname "$FILE")
  while [ "$DIR" != "/" ] && [ "$DIR" != "." ]; do
    if [ -d "$DIR/.buildrunner" ] && [ "$DIR" != "$HOME" ]; then
      PROJECT_DIR="$DIR"
      break
    fi
    DIR=$(dirname "$DIR")
  done
fi

[ -z "$PROJECT_DIR" ] && exit 0

PROJECT=$(basename "$PROJECT_DIR")
OUTPUT=""

# --- Source 1: Local decisions.log (always, <50ms) ---
LOG="$PROJECT_DIR/.buildrunner/decisions.log"
if [ -f "$LOG" ]; then
  MATCHES=$(grep -B0 -A2 -F -e "$BASE" "$LOG" 2>/dev/null | tail -n 30 | head -c 1500 || true)
  if [ -n "$MATCHES" ] && [ "$(echo "$MATCHES" | wc -l | tr -d ' ')" -gt 0 ]; then
    OUTPUT+="── Past Decisions ──
$MATCHES
"
  fi
fi

# --- Source 2 + 3: Lockwood (parallel, 2s timeout) ---
if [ "${BR3_CLUSTER:-}" != "off" ]; then
  LOCKWOOD_URL=$("$HOME/.buildrunner/scripts/cluster-check.sh" semantic-search 2>/dev/null || echo "")
  if [ -n "$LOCKWOOD_URL" ]; then
    # Temp files for parallel curl results
    NOTES_TMP=$(mktemp /tmp/recall-notes.XXXXXX)
    PATTERNS_TMP=$(mktemp /tmp/recall-patterns.XXXXXX)
    RESEARCH_TMP=$(mktemp /tmp/recall-research.XXXXXX)
    trap 'rm -f "$NOTES_TMP" "$PATTERNS_TMP" "$RESEARCH_TMP"; exit 0' ERR EXIT

    # Fire all queries in parallel
    curl -s --max-time 2 "$LOCKWOOD_URL/api/memory/notes?query=$BASE&project=$PROJECT" \
      -o "$NOTES_TMP" 2>/dev/null &
    PID_NOTES=$!

    curl -s --max-time 2 "$LOCKWOOD_URL/api/memory/patterns" \
      -o "$PATTERNS_TMP" 2>/dev/null &
    PID_PATTERNS=$!

    curl -s --max-time 2 "$LOCKWOOD_URL/api/research/search?query=$BASE&limit=2" \
      -o "$RESEARCH_TMP" 2>/dev/null &
    PID_RESEARCH=$!

    # Wait for all (they'll timeout at 2s max)
    wait $PID_NOTES 2>/dev/null || true
    wait $PID_PATTERNS 2>/dev/null || true
    wait $PID_RESEARCH 2>/dev/null || true

    # Parse architecture notes
    NOTES=$(python3 -c "
import json, sys
try:
    data = json.load(open('$NOTES_TMP'))
    notes = data.get('notes', [])[:3]
    for n in notes:
        topic = n.get('topic','')
        content = n.get('content','')[:200]
        source = n.get('source','')
        ts = n.get('timestamp','')[:10]
        print(f'• [{ts}] {topic} ({source})')
        if content:
            print(f'  {content}')
except: pass
" 2>/dev/null || true)

    if [ -n "$NOTES" ]; then
      OUTPUT+="── Lockwood Notes for $BASE ──
$NOTES
"
    fi

    # Parse active log patterns (only show unresolved ones)
    PATTERNS=$(python3 -c "
import json, sys
try:
    data = json.load(open('$PATTERNS_TMP'))
    patterns = [p for p in data.get('patterns', []) if not p.get('resolved', False)][:3]
    for p in patterns:
        desc = p.get('description','')
        count = p.get('count', 0)
        ptype = p.get('pattern_type','')
        print(f'⚠ {ptype}: {desc} ({count}x)')
except: pass
" 2>/dev/null || true)

    if [ -n "$PATTERNS" ]; then
      OUTPUT+="── Active Log Patterns ──
$PATTERNS
"
    fi

    # Parse research results (with dedup)
    DEDUP_FILE="${TMPDIR:-/tmp}/br3-research-seen-$$.txt"
    RESEARCH=$(python3 -c "
import json, sys, os
try:
    data = json.load(open('$RESEARCH_TMP'))
    results = data.get('results', [])[:2]
    dedup_file = '$DEDUP_FILE'
    seen = set()
    if os.path.exists(dedup_file):
        seen = set(open(dedup_file).read().strip().split('\n'))
    new_ids = []
    for r in results:
        rid = r.get('id', '')
        if rid and rid in seen:
            continue
        title = r.get('title', '')
        section = r.get('section', '')
        score = r.get('score', 0)
        print(f'• [{score:.2f}] {title}')
        if section:
            print(f'  Section: {section}')
        if rid:
            new_ids.append(rid)
    if new_ids:
        with open(dedup_file, 'a') as f:
            for nid in new_ids:
                f.write(nid + '\n')
except: pass
" 2>/dev/null || true)

    if [ -n "$RESEARCH" ]; then
      OUTPUT+="── Research Context ──
$RESEARCH
"
    fi

    rm -f "$NOTES_TMP" "$PATTERNS_TMP" "$RESEARCH_TMP"
  fi
fi

# Only output if we found something
if [ -n "$OUTPUT" ]; then
  echo "═══ LOCKWOOD RECALL for $BASE ═══"
  echo "$OUTPUT"
  echo "═══ end recall ═══"
fi

exit 0
