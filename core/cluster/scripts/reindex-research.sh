#!/usr/bin/env bash
# reindex-research.sh — Trigger research library reindexing on Lockwood
# Usage: ./reindex-research.sh [--wait]
#   --wait: poll until indexing completes (default: fire-and-forget)

set -euo pipefail

LOCKWOOD_URL="${LOCKWOOD_URL:-http://10.0.1.101:8100}"

echo "Triggering research reindex on Lockwood..."
RESULT=$(curl -s --max-time 10 -X POST "$LOCKWOOD_URL/api/research/reindex" 2>/dev/null)
echo "Response: $RESULT"

if [ "${1:-}" = "--wait" ]; then
    echo "Waiting for indexing to complete..."
    for i in $(seq 1 60); do
        sleep 5
        STATS=$(curl -s --max-time 5 "$LOCKWOOD_URL/api/research/stats" 2>/dev/null)
        INDEXING=$(echo "$STATS" | python3 -c "import json,sys; print(json.load(sys.stdin).get('indexing', False))" 2>/dev/null)
        if [ "$INDEXING" = "False" ]; then
            echo "Indexing complete:"
            echo "$STATS" | python3 -c "
import json, sys
d = json.load(sys.stdin)
print(f'  Files: {d.get(\"total_files\", 0)}')
print(f'  Chunks: {d.get(\"total_chunks\", 0)}')
print(f'  Duration: {d.get(\"last_duration\", 0)}s')
" 2>/dev/null
            exit 0
        fi
        echo "  Still indexing... (${i})"
    done
    echo "Timeout waiting for indexing"
    exit 1
fi
