#!/bin/bash
# BR3 Intel Collector — runs Claude Code to gather tech intel and post to Lockwood
# Schedule: daily at 4am via cron on Muddy
# Usage: ./collect-intel.sh

set -euo pipefail

LOCKWOOD="http://10.0.1.101:8100"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
LOG_FILE="$HOME/.buildrunner/logs/intel-collect-$(date +%Y-%m-%d).log"
mkdir -p "$(dirname "$LOG_FILE")"

echo "[$(date)] Starting intel collection..." | tee -a "$LOG_FILE"

# Run Claude Code with the collector prompt
claude -p "$(cat <<'PROMPT'
You are the BR3 nightly intel collector. Search for REAL, current tech updates and post each one to the Lockwood API. Be thorough but only report verified findings with real URLs.

## Search these categories (last 7 days):
1. Claude / Anthropic — new models, API changes, SDK releases, Claude Code CLI updates
2. Supabase — edge functions, auth, realtime, new features, CLI
3. Tailwind CSS — v4.x releases, plugins, breaking changes
4. Vite — new versions, Rolldown progress, ecosystem
5. Playwright — test runner updates, new browser APIs
6. React / TypeScript — releases, RFCs, ecosystem
7. Security — npm/PyPI advisories affecting common packages

## For each finding, run this curl command:
```
curl -s -X POST http://10.0.1.101:8100/api/intel/items \
  -H "Content-Type: application/json" \
  -d '{"title":"...","source":"...","url":"https://...","summary":"...","source_type":"official","category":"ecosystem-news","priority":"medium"}'
```

Categories: model-release, api-change, community-tool, ecosystem-news, security, general-news
Priorities: critical (security/breaking), high (new releases), medium (updates), low (blog)
Source types: official, community, blog

## Rules:
- WebSearch each category, then WebFetch the most relevant pages for details
- Every item MUST have a real, working URL
- Write a 1-2 sentence summary for each item
- Skip anything older than 7 days unless security
- After posting all items, output a summary count of what you collected

Do NOT fabricate URLs or make up version numbers. Only report what you can verify.
PROMPT
)" --max-turns 30 2>&1 | tee -a "$LOG_FILE"

echo "[$(date)] Collection complete." | tee -a "$LOG_FILE"
