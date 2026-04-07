#!/usr/bin/env bash
# One-time backfill: query Walter's SQLite test_runs history, bulk POST to Lockwood
# Usage: ssh walter 'bash ~/repos/BuildRunner3/core/cluster/scripts/backfill-lockwood-tests.sh'
#   or:  bash backfill-lockwood-tests.sh  (if run from Walter directly)

set -euo pipefail

WALTER_DB="${TEST_DB:-$HOME/.walter/test_results.db}"
LOCKWOOD_URL="${LOCKWOOD_URL:-http://10.0.1.101:8100}"

if [ ! -f "$WALTER_DB" ]; then
    echo "Walter DB not found at $WALTER_DB"
    exit 1
fi

echo "Backfilling test history from $WALTER_DB to $LOCKWOOD_URL/api/memory/tests..."

# Export test_runs as JSON lines
sqlite3 -json "$WALTER_DB" "
    SELECT runner, project, git_sha, git_branch, duration_ms,
           total, passed, failed, skipped, trigger, last_tested_sha, timestamp
    FROM test_runs
    ORDER BY timestamp ASC
" | python3 -c "
import sys, json, urllib.request, urllib.error, time

LOCKWOOD = '${LOCKWOOD_URL}'
rows = json.load(sys.stdin)
ok = 0
fail = 0

for r in rows:
    total = r.get('total', 0)
    passed_count = r.get('passed', 0)
    pass_rate = round((passed_count / total * 100), 1) if total > 0 else 0.0

    payload = json.dumps({
        'project': r.get('project', 'unknown'),
        'sha': r.get('git_sha', ''),
        'branch': r.get('git_branch', ''),
        'pass_rate': pass_rate,
        'total': total,
        'passed': passed_count,
        'failed': r.get('failed', 0),
        'skipped': r.get('skipped', 0),
        'failures': [],
        'duration_ms': r.get('duration_ms'),
        'runner': r.get('runner', 'vitest'),
        'trigger': r.get('trigger', 'watch'),
    }).encode('utf-8')

    req = urllib.request.Request(
        f'{LOCKWOOD}/api/memory/tests',
        data=payload,
        method='POST',
        headers={'Content-Type': 'application/json'}
    )
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            ok += 1
    except Exception as e:
        fail += 1
        print(f'  FAIL: {r.get(\"project\")} {r.get(\"git_sha\")} -> {e}', file=sys.stderr)

    # Rate limit to avoid overwhelming Lockwood
    if ok % 50 == 0:
        time.sleep(0.5)

print(f'Backfill complete: {ok} OK, {fail} failed, {ok + fail} total')
"
