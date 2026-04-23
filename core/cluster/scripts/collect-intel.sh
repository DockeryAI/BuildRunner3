#!/bin/bash
# BR3 Intel Collector + Opus Review
# Four-phase pipeline: (1) collect tech intel, (2) innovation scout, (2.5) Below
# pre-filter [below-offload-v1 Phase 3], (3) Opus BR3 analysis, (4) Tier 1 auto-act.
#
# Invocation moved from nightly cron to ad-hoc /intel-run (below-offload-v1 Phase 2).
# Supported flags (forwarded from intel-run.sh):
#   --dry-run           Phases 1, 2, 2.5 only (no Opus synthesis / auto-act)
#   --phase=N           Run a single phase (1, 2, 2.5, 3, or 4)
#   --skip-prefilter    Skip Phase 2.5 Below pre-filter (escape hatch)
#
# Tunables (env vars, read below):
#   BR3_INTEL_MIN_SCORE=6                           composite score cut-off for Phase 3
#   BR3_INTEL_PRIORITY_OVERRIDE=critical,high       always pass these priorities
#   BR3_SKIP_PREFILTER=1                            same as --skip-prefilter
set -euo pipefail

# ---- Arg parsing ------------------------------------------------------------
DRY_RUN=0
SINGLE_PHASE=""
for arg in "$@"; do
    case "$arg" in
        --dry-run)        DRY_RUN=1 ;;
        --phase=*)        SINGLE_PHASE="${arg#--phase=}" ;;
        --skip-prefilter) export BR3_SKIP_PREFILTER=1 ;;
        *) echo "Unknown flag: $arg" >&2; exit 1 ;;
    esac
done

should_run_phase() {
    local p="$1"
    # Single-phase mode: only the matching phase runs.
    if [ -n "$SINGLE_PHASE" ]; then
        [ "$SINGLE_PHASE" = "$p" ] && return 0 || return 1
    fi
    # Dry-run: Phases 1, 2, 2.5 only.
    if [ "$DRY_RUN" -eq 1 ]; then
        case "$p" in 1|2|2.5) return 0 ;; *) return 1 ;; esac
    fi
    return 0
}

LOG_DIR="$HOME/.buildrunner/logs"
mkdir -p "$LOG_DIR"
LOG_FILE="$LOG_DIR/intel-collect-$(date +%Y-%m-%d).log"

# ---- Phase 1: Collect -------------------------------------------------------
if should_run_phase 1; then
echo "[$(date)] Phase 1: Collecting intel..." >> "$LOG_FILE"

claude -p 'You are the BR3 nightly intel collector. Search for REAL, current tech updates (last 7 days) and post each one to Lockwood.

Categories to search: Claude/Anthropic (models, API, SDK, Claude Code), Supabase (edge functions, auth, realtime, CLI), Tailwind CSS (v4.x), Vite, Playwright, React, TypeScript, security advisories (npm/PyPI), hardware deals (NVIDIA 3090, Mac Mini M4, NVMe 4TB, PSUs 1000W+).

For each verified finding, run:
curl -s -X POST http://10.0.1.106:8101/api/intel/items -H "Content-Type: application/json" -d "{\"title\":\"...\",\"source\":\"...\",\"url\":\"REAL_URL\",\"summary\":\"1-2 sentences\",\"source_type\":\"official\",\"category\":\"ecosystem-news\",\"priority\":\"medium\"}"

category values: model-release, api-change, community-tool, ecosystem-news, security, general-news
priority values: critical (security/breaking), high (new releases), medium (updates), low (blog)
source_type values: official, community, blog

RULES: Every item MUST have a real URL. Do NOT fabricate versions, CVEs, or URLs. Only report verified findings. After posting, output a count summary.' \
  --max-turns 30 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 1 complete." >> "$LOG_FILE"
fi

# ---- Phase 1.5: Below structured extraction from Phase 1 log ---------------
# Sends the Phase 1 log tail to Below qwen3:8b for structured re-extraction.
# Supplements (does not replace) Claude's Phase 1 postings.
# Rollback: BR3_BELOW_INTEL=off skips this block.
if should_run_phase 1 && [ "${BR3_BELOW_INTEL:-on}" != "off" ]; then
    echo "[$(date)] Phase 1.5: Below structured extraction from Phase 1 log..." >> "$LOG_FILE"
    REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
    PHASE1_LOG_TAIL=$(tail -c 12000 "$LOG_FILE" 2>/dev/null || true)
    if [ -n "$PHASE1_LOG_TAIL" ]; then
        EXTRACTED=$(python3 -c "
import sys, json
sys.path.insert(0, '$REPO_ROOT')
from core.cluster.scripts.intel_below_extractor import extract_intel_items
items = extract_intel_items('''$PHASE1_LOG_TAIL''', context='tech news ecosystem')
for item in items:
    print(json.dumps(item))
" 2>>"$LOG_FILE" || true)
        if [ -n "$EXTRACTED" ]; then
            echo "$EXTRACTED" | while IFS= read -r line; do
                [ -z "$line" ] && continue
                TITLE=$(echo "$line" | python3 -c "import sys,json; d=json.loads(sys.stdin.read()); print(d.get('title',''))" 2>/dev/null)
                echo "[$(date)] Below extracted item: $TITLE" >> "$LOG_FILE"
                curl -s -X POST http://10.0.1.106:8101/api/intel/items \
                    -H "Content-Type: application/json" \
                    -d "$line" >> "$LOG_FILE" 2>&1 || true
            done
        fi
    fi
    echo "[$(date)] Phase 1.5 complete." >> "$LOG_FILE"
fi

# ---- Phase 2: Discover — Innovation Search ----------------------------------
if should_run_phase 2; then
echo "[$(date)] Phase 2: Innovation discovery..." >> "$LOG_FILE"

claude -p 'You are the BR3 innovation scout. Search for NEW capabilities, tools, and patterns BR3 does not use yet. Focus on discoveries, not version bumps.

Search targets:
- New MCP servers (Model Context Protocol) — check awesome-mcp-servers, GitHub trending
- Claude Code patterns — new workflows, slash commands, hooks, agent patterns
- SDK capabilities — new Anthropic SDK features, tool_use patterns, streaming improvements
- AI dev patterns — cursor rules, copilot techniques, agentic workflows, code review automation
- Infrastructure tools — new Supabase features, Vite plugins, Playwright capabilities, Tailwind v4 utilities

For each verified finding, POST to Lockwood:
curl -s -X POST http://10.0.1.106:8101/api/intel/items -H "Content-Type: application/json" -d "{\"title\":\"...\",\"source\":\"...\",\"url\":\"REAL_URL\",\"summary\":\"1-2 sentences\",\"source_type\":\"community\",\"category\":\"community-tool\",\"priority\":\"medium\"}"

RULES: Every item MUST have a real, verifiable URL. Do NOT fabricate. Only report things BR3 could actually adopt. After posting, output a count summary.' \
  --max-turns 30 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 2 complete." >> "$LOG_FILE"
fi

# ---- Phase 2.25: Below categorization of unclassified items ----------------
# Runs After Phase 2; sends uncategorized items to Below qwen3:8b for
# category/priority/source_type classification before Opus Phase 3 review.
# Rollback: BR3_BELOW_INTEL=off skips this block.
if should_run_phase 2 && [ "${BR3_BELOW_INTEL:-on}" != "off" ]; then
    echo "[$(date)] Phase 2.25: Below categorization of unreviewed items..." >> "$LOG_FILE"
    REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
    UNCATEGORIZED=$(curl -s "http://10.0.1.106:8101/api/intel/items" 2>/dev/null \
        | python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    items = data.get('items', [])
    # Items without opus_reviewed and without a source_type are candidates
    candidates = [{'id': i['id'], 'title': i.get('title',''), 'summary': i.get('summary','')}
                  for i in items if not i.get('opus_reviewed') and not i.get('source_type')]
    print(json.dumps(candidates))
except Exception:
    print('[]')
" 2>/dev/null || echo "[]")
    if [ "$UNCATEGORIZED" != "[]" ] && [ -n "$UNCATEGORIZED" ]; then
        CLASSIFIED=$(python3 -c "
import sys, json
sys.path.insert(0, '$REPO_ROOT')
from core.cluster.scripts.intel_below_extractor import categorize_intel_items
items = json.loads('''$UNCATEGORIZED''')
result = categorize_intel_items(items)
print(json.dumps(result))
" 2>>"$LOG_FILE" || echo "[]")
        if [ "$CLASSIFIED" != "[]" ] && [ -n "$CLASSIFIED" ]; then
            echo "$CLASSIFIED" | python3 -c "
import sys, json, urllib.request
classified = json.loads(sys.stdin.read())
for c in classified:
    item_id = c.get('id')
    if not item_id:
        continue
    patch = {k: v for k, v in c.items() if k != 'id'}
    try:
        req = urllib.request.Request(
            f'http://10.0.1.106:8101/api/intel/items/{item_id}',
            data=json.dumps(patch).encode(),
            headers={'Content-Type': 'application/json'},
            method='PATCH',
        )
        urllib.request.urlopen(req, timeout=5)
        print(f'classified item {item_id}')
    except Exception as e:
        print(f'failed to patch item {item_id}: {e}', file=sys.stderr)
" >> "$LOG_FILE" 2>&1 || true
        fi
    fi
    echo "[$(date)] Phase 2.25 complete." >> "$LOG_FILE"
fi

# ---- Phase 2.5: Below pre-filter --------------------------------------------
# Scores unreviewed items via Below qwen3:8b, flagging any it can't score for
# Opus review (fail-open — intel_scoring.py handles Below-offline gracefully).
# Defaults:
#   BR3_INTEL_MIN_SCORE=6                     composite score cut-off for Phase 3 filter
#   BR3_INTEL_PRIORITY_OVERRIDE=critical,high  always pass these priorities regardless of score
#   BR3_SKIP_PREFILTER=1                      escape hatch
if should_run_phase 2.5; then
    if [ "${BR3_SKIP_PREFILTER:-0}" = "1" ]; then
        echo "[$(date)] Phase 2.5: skipped (BR3_SKIP_PREFILTER=1 / --skip-prefilter)" >> "$LOG_FILE"
    else
        echo "[$(date)] Phase 2.5: Below pre-filter (qwen3:8b scoring)..." >> "$LOG_FILE"
        REPO_ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"
        if (cd "$REPO_ROOT" && python3 -m core.cluster.scripts.intel_prefilter) >> "$LOG_FILE" 2>&1; then
            echo "[$(date)] Phase 2.5 complete." >> "$LOG_FILE"
        else
            echo "[$(date)] Phase 2.5: prefilter exited non-zero — proceeding (fail-open)" >> "$LOG_FILE"
        fi
    fi
fi

# ---- Phase 3: Review — Opus Classification (score-filtered) -----------------
# Uses BR3_INTEL_MIN_SCORE and BR3_INTEL_PRIORITY_OVERRIDE from env.
if should_run_phase 3; then
echo "[$(date)] Phase 3: BR3 analysis + type classification..." >> "$LOG_FILE"

MIN_SCORE="${BR3_INTEL_MIN_SCORE:-6}"
OVERRIDE="${BR3_INTEL_PRIORITY_OVERRIDE:-critical,high}"
export BR3_INTEL_MIN_SCORE="$MIN_SCORE"
export BR3_INTEL_PRIORITY_OVERRIDE="$OVERRIDE"

claude -p 'Review unreviewed intel items on Lockwood (pre-filtered by Below score / priority override / flags). Write BR3-specific analysis and classify improvement types.

BR3 context: 6-node Mac Mini cluster (Muddy=dev, Lockwood=memory/vector, Walter=testing, Otis=parallel builder, Lomax=staging, Below=Windows inference planning dual 3090 NVLink). Stack: React + Vite + Tailwind v4 + Supabase + Playwright + Claude Code CLI. Deploys to Netlify. BRLogger for observability.

Step 1: Get unreviewed items AND apply the Below pre-filter (defaults: BR3_INTEL_MIN_SCORE=6, BR3_INTEL_PRIORITY_OVERRIDE=critical,high).
curl -s "http://10.0.1.106:8101/api/intel/items" | python3 -c "
import sys, json, os
items = json.load(sys.stdin)[\"items\"]
min_score = int(os.environ.get(\"BR3_INTEL_MIN_SCORE\", \"6\"))
override = set(os.environ.get(\"BR3_INTEL_PRIORITY_OVERRIDE\", \"critical,high\").split(\",\"))
def keep(i):
    if i.get(\"opus_reviewed\"):
        return False
    return ((i.get(\"score\") or 0) >= min_score
            or i.get(\"priority\") in override
            or i.get(\"needs_opus_review\") == 1
            or i.get(\"scored\") == 0)
for i in items:
    if keep(i):
        print(str(i[\"id\"]) + \": \" + i[\"title\"])
"

Step 2: For EACH filtered item, write a 2-4 sentence plain-English explanation of what it means and how it specifically affects BR3 (name nodes, tools, workflows). Then POST:
curl -s -X POST http://10.0.1.106:8101/api/intel/items/{ID}/opus-review -H "Content-Type: application/json" -d "{\"opus_synthesis\": \"...\", \"br3_improvement\": true_or_false}"

Step 3: For items where br3_improvement is true, classify the improvement type and create it:
Types: fix (security patches, CVEs, breaking changes), upgrade (better version of something we use), new_capability (something BR3 cant do today but could), new_skill (a new slash command or automation), research (worth investigating, no clear action yet)

For discovery items (new_capability, new_skill, research), write an innovation-style synthesis: what it enables, why it matters for BR3, concrete next steps.

curl -s -X POST http://10.0.1.106:8101/api/intel/improvements -H "Content-Type: application/json" -d "{\"title\": \"...\", \"rationale\": \"...\", \"complexity\": \"simple|medium|complex\", \"setlist_prompt\": \"what to build/change\", \"source_intel_id\": ID, \"type\": \"fix|upgrade|new_capability|new_skill|research\"}"

Only create improvements for clearly actionable items. Write like explaining to a senior dev who knows the system but hasnt read the news.' \
  --max-turns 30 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 3 complete." >> "$LOG_FILE"
fi

# ---- Phase 4: Auto-Act — Tier 1 Fixes Only ----------------------------------
if should_run_phase 4; then
echo "[$(date)] Phase 4: Auto-act on Tier 1 fixes..." >> "$LOG_FILE"

claude -p 'You are the BR3 auto-act agent. Execute ONLY Tier 1 fixes — simple security patches and deadline-critical items.

Step 1: Get pending improvements that are Tier 1 candidates (type=fix, complexity=simple):
curl -s "http://10.0.1.106:8101/api/intel/improvements?status=pending" | python3 -c "
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
curl -s -X POST http://10.0.1.106:8101/api/intel/improvements/{ID}/auto-act -H "Content-Type: application/json" -d "{\"log\": \"Audit: [what was checked]. Result: [what was done or why skipped].\"}"

If no Tier 1 items found, output "No Tier 1 auto-act candidates" and exit.' \
  --max-turns 15 >> "$LOG_FILE" 2>&1

echo "[$(date)] Phase 4 complete. Nightly intel done." >> "$LOG_FILE"
fi
