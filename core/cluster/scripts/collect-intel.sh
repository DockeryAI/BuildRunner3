#!/bin/bash
# BR3 Nightly Intel Collector + Opus Review
# Two-phase: (1) collect real tech intel, (2) write BR3-specific analysis + improvements
# Cron: 3 4 * * * ~/Projects/BuildRunner3/core/cluster/scripts/collect-intel.sh
set -euo pipefail

LOG_DIR="$HOME/.buildrunner/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/intel-collect-$(date +%Y-%m-%d).log"

# ---- Phase 1: Collect ----
echo "[$(date)] Phase 1: Collecting intel..." >> "$LOG_FILE"

claude -p 'You are the BR3 nightly intel collector. Search for REAL, current tech updates (last 7 days) and post each one to Lockwood.

Categories to search: Claude/Anthropic (models, API, SDK, Claude Code), Supabase (edge functions, auth, realtime, CLI), Tailwind CSS (v4.x), Vite, Playwright, React, TypeScript, security advisories (npm/PyPI), hardware deals (NVIDIA 3090, Mac Mini M4, NVMe 4TB, PSUs 1000W+).

For each verified finding, run:
curl -s -X POST http://10.0.1.101:8100/api/intel/items -H "Content-Type: application/json" -d "{\"title\":\"...\",\"source\":\"...\",\"url\":\"REAL_URL\",\"summary\":\"1-2 sentences\",\"source_type\":\"official\",\"category\":\"ecosystem-news\",\"priority\":\"medium\"}"

category values: model-release, api-change, community-tool, ecosystem-news, security, general-news
priority values: critical (security/breaking), high (new releases), medium (updates), low (blog)
source_type values: official, community, blog

RULES: Every item MUST have a real URL. Do NOT fabricate versions, CVEs, or URLs. Only report verified findings. After posting, output a count summary.' \
  --max-turns 30 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 1 complete." >> "$LOG_FILE"

# ---- Phase 2: Opus Review ----
echo "[$(date)] Phase 2: BR3 analysis + improvements..." >> "$LOG_FILE"

claude -p 'Review all unreviewed intel items on Lockwood and write BR3-specific analysis for each.

BR3 context: 6-node Mac Mini cluster (Muddy=dev, Lockwood=memory/vector, Walter=testing, Otis=parallel builder, Lomax=staging, Below=Windows inference planning dual 3090 NVLink). Stack: React + Vite + Tailwind v4 + Supabase + Playwright + Claude Code CLI. Deploys to Netlify. BRLogger for observability.

Step 1: Get unreviewed items:
curl -s "http://10.0.1.101:8100/api/intel/items" | python3 -c "import sys,json; items=json.load(sys.stdin)[\"items\"]; [print(f\"{i[\"id\"]}: {i[\"title\"]}\") for i in items if not i.get(\"opus_reviewed\")]"

Step 2: For EACH unreviewed item, write a 2-4 sentence plain-English explanation of what it means and how it specifically affects BR3 (name nodes, tools, workflows). Then POST:
curl -s -X POST http://10.0.1.101:8100/api/intel/items/{ID}/opus-review -H "Content-Type: application/json" -d "{\"opus_synthesis\": \"...\", \"br3_improvement\": true_or_false}"

Step 3: For items where br3_improvement is true, create an improvement:
curl -s -X POST http://10.0.1.101:8100/api/intel/improvements -H "Content-Type: application/json" -d "{\"title\": \"...\", \"rationale\": \"...\", \"complexity\": \"simple|medium|complex\", \"setlist_prompt\": \"what to build/change\", \"source_intel_id\": ID}"

Only create improvements for clearly actionable items. Write like explaining to a senior dev who knows the system but hasnt read the news.' \
  --max-turns 30 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 2 complete. Nightly intel done." >> "$LOG_FILE"
