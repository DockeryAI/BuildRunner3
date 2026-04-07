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

# ---- Phase 2: Discover — Innovation Search ----
echo "[$(date)] Phase 2: Innovation discovery..." >> "$LOG_FILE"

claude -p 'You are the BR3 innovation scout. Search for NEW capabilities, tools, and patterns BR3 does not use yet. Focus on discoveries, not version bumps.

Search targets:
- New MCP servers (Model Context Protocol) — check awesome-mcp-servers, GitHub trending
- Claude Code patterns — new workflows, slash commands, hooks, agent patterns
- SDK capabilities — new Anthropic SDK features, tool_use patterns, streaming improvements
- AI dev patterns — cursor rules, copilot techniques, agentic workflows, code review automation
- Infrastructure tools — new Supabase features, Vite plugins, Playwright capabilities, Tailwind v4 utilities

For each verified finding, POST to Lockwood:
curl -s -X POST http://10.0.1.101:8100/api/intel/items -H "Content-Type: application/json" -d "{\"title\":\"...\",\"source\":\"...\",\"url\":\"REAL_URL\",\"summary\":\"1-2 sentences\",\"source_type\":\"community\",\"category\":\"community-tool\",\"priority\":\"medium\"}"

RULES: Every item MUST have a real, verifiable URL. Do NOT fabricate. Only report things BR3 could actually adopt. After posting, output a count summary.' \
  --max-turns 30 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 2 complete." >> "$LOG_FILE"

# ---- Phase 3: Review — Opus Classification ----
echo "[$(date)] Phase 3: BR3 analysis + type classification..." >> "$LOG_FILE"

claude -p 'Review all unreviewed intel items on Lockwood. Write BR3-specific analysis and classify improvement types.

BR3 context: 6-node Mac Mini cluster (Muddy=dev, Lockwood=memory/vector, Walter=testing, Otis=parallel builder, Lomax=staging, Below=Windows inference planning dual 3090 NVLink). Stack: React + Vite + Tailwind v4 + Supabase + Playwright + Claude Code CLI. Deploys to Netlify. BRLogger for observability.

Step 1: Get unreviewed items:
curl -s "http://10.0.1.101:8100/api/intel/items" | python3 -c "import sys,json; items=json.load(sys.stdin)[\"items\"]; [print(f\"{i[\"id\"]}: {i[\"title\"]}\") for i in items if not i.get(\"opus_reviewed\")]"

Step 2: For EACH unreviewed item, write a 2-4 sentence plain-English explanation of what it means and how it specifically affects BR3 (name nodes, tools, workflows). Then POST:
curl -s -X POST http://10.0.1.101:8100/api/intel/items/{ID}/opus-review -H "Content-Type: application/json" -d "{\"opus_synthesis\": \"...\", \"br3_improvement\": true_or_false}"

Step 3: For items where br3_improvement is true, classify the improvement type and create it:
Types: fix (security patches, CVEs, breaking changes), upgrade (better version of something we use), new_capability (something BR3 cant do today but could), new_skill (a new slash command or automation), research (worth investigating, no clear action yet)

For discovery items (new_capability, new_skill, research), write an innovation-style synthesis: what it enables, why it matters for BR3, concrete next steps.

curl -s -X POST http://10.0.1.101:8100/api/intel/improvements -H "Content-Type: application/json" -d "{\"title\": \"...\", \"rationale\": \"...\", \"complexity\": \"simple|medium|complex\", \"setlist_prompt\": \"what to build/change\", \"source_intel_id\": ID, \"type\": \"fix|upgrade|new_capability|new_skill|research\"}"

Only create improvements for clearly actionable items. Write like explaining to a senior dev who knows the system but hasnt read the news.' \
  --max-turns 30 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 3 complete." >> "$LOG_FILE"

# ---- Phase 4: Auto-Act — Tier 1 Fixes Only ----
echo "[$(date)] Phase 4: Auto-act on Tier 1 fixes..." >> "$LOG_FILE"

claude -p 'You are the BR3 auto-act agent. Execute ONLY Tier 1 fixes — simple security patches and deadline-critical items.

Step 1: Get pending improvements that are Tier 1 candidates (type=fix, complexity=simple):
curl -s "http://10.0.1.101:8100/api/intel/improvements?status=pending" | python3 -c "
import sys, json
imps = json.load(sys.stdin)[\"improvements\"]
for i in imps:
    if i.get(\"type\") == \"fix\" and i.get(\"complexity\") == \"simple\" and not i.get(\"auto_acted\"):
        print(json.dumps({\"id\": i[\"id\"], \"title\": i[\"title\"], \"prompt\": i[\"setlist_prompt\"]}))"

Step 2: For each Tier 1 item, run a READ-ONLY audit first:
- Check current state: npm ls, pip list, grep for affected patterns
- Verify the issue actually exists in BR3 codebase
- If the issue is NOT present, log "Already resolved" and skip

Step 3: If the issue IS confirmed, apply the fix:
- ONLY: pin versions, update configs, apply patches
- NEVER: deploy to production, delete files, modify BUILD specs, run migrations
- NEVER: modify more than 3 files per fix

SAFETY GUARDRAILS:
- Maximum 15 turns total for ALL auto-acts combined
- Read-only audit before any changes
- No deploys, no deletions, no database changes
- Log every action taken

Step 4: After each fix (or skip), log the result:
curl -s -X POST http://10.0.1.101:8100/api/intel/improvements/{ID}/auto-act -H "Content-Type: application/json" -d "{\"log\": \"Audit: [what was checked]. Result: [what was done or why skipped].\"}"

If no Tier 1 items found, output "No Tier 1 auto-act candidates" and exit.' \
  --max-turns 15 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 4 complete. Nightly intel done." >> "$LOG_FILE"
