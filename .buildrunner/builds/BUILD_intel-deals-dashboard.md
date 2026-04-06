# Build: Intelligence & Deals Dashboard

**Created:** 2026-04-06
**Status:** Phase 1 Not Started
**Deploy:** local — Lockwood FastAPI + Muddy dashboard + Below inference (deploy nodes via SSH after each phase)

## Overview

Two new dashboard tabs powered by Below (grunt work) and Claude Code Opus (reasoning). Intelligence tab: live radar for Claude/Anthropic capabilities, community innovations, and cluster-relevant tools. Deals tab: universal price tracker starting with RTX 3090 GPUs for the Below upgrade, switchable to any product category. When Intelligence finds a BR3 improvement, it feeds into /setlist for instant evidence-based planning.

**Zero Anthropic API cost.** Below's local model handles all classification, extraction, and scoring. Claude Code scheduled tasks (Opus, already paid for) handle synthesis and reasoning.

**Research:**

- `~/Projects/research-library/docs/techniques/claude-capability-monitoring-integration.md` (70+ sources, 5 sub-agents)
- `~/Projects/research-library/docs/techniques/deal-finding-price-tracking.md` (50+ sources, 3 sub-agents)

**READ FIRST:**

1. `core/cluster/node_semantic.py` — Lockwood's existing FastAPI
2. `core/cluster/node_inference.py` — Below's existing FastAPI (classify/draft/summarize/gpu)
3. `ui/src/components/Dashboard.tsx` — existing dashboard with 3 tabs (Tasks, Agent Pool, Telemetry)
4. `ui/src/components/AgentPool.tsx` — template for new tab components
5. `ui/src/services/api.ts` — existing API client
6. `~/.buildrunner/builds/BUILD_setlist.md` — setlist planning system (Phase 6 connects here)
7. `~/.buildrunner/scripts/developer-brief.sh` — SessionStart context injection

**DO NOT:**

- Break existing dashboard tabs or APIs
- Call Anthropic API for scoring/classification (Below handles this)
- Hard-code node IPs (all reads from cluster.json via cluster-check.sh)
- Require any node to be online (graceful fallback everywhere)
- Scrape Facebook Marketplace (TOS violation, account ban risk)
- Add automated purchasing (just alert, human decides)

---

## Parallelization Matrix

| Phase | Key Files                                                          | Can Parallel With | Blocked By                   |
| ----- | ------------------------------------------------------------------ | ----------------- | ---------------------------- |
| 1     | `node_intelligence.py`, `intel_collector.py`, `intel_schema.sql`   | 3, 4              | -                            |
| 2     | `intel_scoring.py`, `node_intelligence.py` (modify)                | 3, 4              | - (after 1 logically)        |
| 3     | `intel-review.md`, `intel-digest.sh`                               | 1, 2, 4           | -                            |
| 4     | `IntelligenceTab.tsx`, `Dashboard.tsx`, `api.ts`, `types/index.ts` | 1, 2, 3           | -                            |
| 5     | `DealsTab.tsx`, `Dashboard.tsx`, `api.ts`, `types/index.ts`        | -                 | 4 (same Dashboard.tsx)       |
| 6     | `intel-review.md`, `node_intelligence.py`, `IntelligenceTab.tsx`   | -                 | 4 (same IntelligenceTab.tsx) |

**Optimal execution:**

- **Wave 1:** Phases 1, 3, 4 (all parallel — zero file conflicts)
- **Wave 2:** Phase 2 (scoring, needs collection from Phase 1)
- **Wave 3:** Phases 5, 6 (sequential, both touch Dashboard.tsx/IntelligenceTab.tsx)

---

## Phases

### Phase 1: Collection Infrastructure (Lockwood)

**Status:** not_started
**Files:**

- `core/cluster/node_intelligence.py` (NEW) — FastAPI endpoints on Lockwood for intelligence + deals
- `core/cluster/intel_collector.py` (NEW) — cron-driven collection scripts
- `core/cluster/intel_schema.sql` (NEW) — SQLite schema for both tabs

**Blocked by:** None

**Deliverables:**

- [ ] SQLite schema with tables: `intel_items` (id, title, source, url, raw_content, source_type, category, collected_at, scored BOOL, score INT, priority TEXT, summary TEXT, opus_synthesis TEXT, br3_improvement BOOL, read BOOL, dismissed BOOL), `deal_items` (id, hunt_id, name, category, attributes JSON, source_url, price DECIMAL, condition TEXT, seller TEXT, seller_rating REAL, deal_score INT, verdict TEXT, opus_assessment TEXT, listing_url TEXT, collected_at, read BOOL, dismissed BOOL), `price_history` (id, deal_item_id FK, price DECIMAL, source TEXT, recorded_at), `model_snapshots` (id, snapshot JSON, diff_summary TEXT, created_at), `active_hunts` (id, name TEXT, category TEXT, keywords TEXT, target_price DECIMAL, check_interval_minutes INT, source_urls JSON, active BOOL, created_at)
- [ ] Miniflux install on Lockwood (Docker one-liner + existing Postgres): subscribe to 12 feeds — GitHub releases.atom for anthropics/claude-code, anthropic-sdk-python, anthropic-sdk-typescript, claude-agent-sdk-python, claude-agent-sdk-typescript; status.claude.com/history.atom; conoro/anthropic-engineering-rss-feed XML; Google News RSS for "Anthropic OR Claude AI OR Claude Code"; Reddit RSS for r/ClaudeAI and r/ClaudeCode (reddit.com/r/subreddit/.rss format)
- [ ] Miniflux webhook config: fires POST to `lockwood.local:8100/api/intel/webhook/miniflux` on new entries with HMAC-SHA256 signature verification
- [ ] Models API poller (`intel_collector.py`): cron every 6h, calls `GET /v1/models?limit=1000` using ANTHROPIC_API_KEY from Lockwood env, compares against last model_snapshot, generates intel_items for new models, new capabilities, deprecations, new beta headers
- [ ] Package version poller (`intel_collector.py`): cron every 2h, hits `registry.npmjs.org/@anthropic-ai/{pkg}/latest` + `pypi.org/pypi/anthropic/json` (zero auth), compares against stored versions, creates intel_item on version bump
- [ ] NewReleases.io webhook endpoint: `POST /api/intel/webhook/newreleases` — parses payload, creates intel_item
- [ ] F5Bot webhook endpoint: `POST /api/intel/webhook/f5bot` — parses keyword alert payload, creates intel_item
- [ ] changedetection.io install on Lockwood (Docker: dgtlmoon/changedetection.io + dgtlmoon/sockpuppetbrowser, ~200MB combined). Initial watches: Outworld Systems store page (ebay.com/str/outworld) at 15-min interval with restock detection mode. Webhook fires to `POST /api/deals/webhook/changedetection`
- [ ] Deal webhook handler: parses changedetection.io payload, extracts listing data (title, price, seller, condition, URL) using CSS selectors (.s-item, .s-item**title, .s-item**price, .s-item\_\_link), creates deal_item + price_history entry
- [ ] FastAPI endpoints on Lockwood (:8100): `GET /api/intel/items?priority=&category=&source_type=&read=&limit=`, `GET /api/intel/alerts` (unread critical+high count), `POST /api/intel/items/{id}/read`, `POST /api/intel/items/{id}/dismiss`, `GET /api/deals/items?hunt_id=&min_score=&limit=`, `GET /api/deals/hunts`, `POST /api/deals/hunts` (create hunt), `POST /api/deals/hunts/{id}/archive`, `GET /api/deals/price-history/{deal_item_id}`, all webhook endpoints above

**Success Criteria:** `curl lockwood.local:8100/api/intel/items` returns items from at least 3 sources within 24h of deploy. `curl lockwood.local:8100/api/deals/items` returns eBay listings from Outworld Systems. changedetection.io at lockwood.local:5000 shows Outworld store watch with 15-min interval.

---

### Phase 2: Below Scoring Pipeline

**Status:** not_started
**Files:**

- `core/cluster/intel_scoring.py` (NEW) — scoring logic calling Below's Ollama
- `core/cluster/node_intelligence.py` (MODIFY) — add scoring cron trigger

**Blocked by:** None
**After:** Phase 1 (needs collected items to score)

**Deliverables:**

- [ ] Intel scoring function: for each unscored intel_item, POST to `below.local:11434/api/generate` with model=qwen3:8b (or upgraded model), prompt instructs: classify relevance 1-10, urgency 1-10, actionability 1-10, assign category (api-change/model-release/community-tool/ecosystem-news/cluster-relevant/general-news), assign priority (critical/high/medium/low), write one-line summary. Parse JSON response, update intel_item
- [ ] Deal scoring function: for each unscored deal_item, POST to Below with prompt: score 0-100 using weighted formula (price vs hunt target_price 0.30, seller_rating 0.20, condition quality 0.20, market context 0.15, scarcity/urgency 0.15), assign verdict (exceptional/good/fair/pass), write one-line assessment. Parse JSON response, update deal_item
- [ ] Deduplication before scoring: URL hash check against last 48h. Title similarity check via Below embeddings (`POST below.local:11434/api/embeddings`) with cosine similarity > 0.92 = duplicate
- [ ] Confidence flagging: if Below's JSON response fails to parse or returns malformed scores, flag item as `needs_opus_review=true`
- [ ] Scoring cron: runs every 30 minutes on Lockwood. Queries `intel_items WHERE scored=false` and `deal_items WHERE deal_score IS NULL`, sends to Below. Fire-and-forget if Below offline — items stay unscored
- [ ] Below offline fallback: if Below unreachable after 3s timeout, log warning, skip scoring cycle. Items accumulate and score on next successful cycle
- [ ] Exceptional deal alert: when a deal_item scores 80+, immediately fire Discord webhook notification (configurable URL in env)

**Success Criteria:** Items have non-null scores within 30 minutes of collection. Below handles 200+ items/day at 82 tok/s without backlog. Outworld FTW3 restock listing scores 85+ with verdict "exceptional" and fires Discord alert.

---

### Phase 3: Claude Code Reasoning Layer

**Status:** not_started
**Files:**

- `~/.claude/commands/intel-review.md` (NEW) — skill for Opus reasoning pass
- `~/.buildrunner/scripts/intel-digest.sh` (NEW) — brief injection helper

**Blocked by:** None

**Deliverables:**

- [ ] `/intel-review` skill: reads top 10 unreviewed high-scoring items from Lockwood (`GET /api/intel/items?priority=critical,high&opus_reviewed=false&limit=10`). For each item, Opus writes synthesis: what it is, why it matters to BR3 specifically, what action to take. Writes opus_synthesis back via `POST /api/intel/items/{id}/opus-review`
- [ ] BR3 improvement detection: when Opus identifies an actionable BR3 improvement, marks `br3_improvement=true` and writes improvement record via `POST /api/intel/improvements` with fields: title, rationale, complexity (simple/medium/complex), setlist_prompt (the exact /setlist command to generate the plan), affected_files (if known)
- [ ] Deal review: also reads exceptional deals (score 80+, `opus_reviewed=false`), writes assessment specific to cluster upgrade requirements — NVLink matching, PCB height compatibility, seller warranty, whether to buy now or wait. Writes via `POST /api/deals/items/{id}/opus-review`
- [ ] Scheduled execution: Claude Code desktop scheduled task, runs every 12 hours. Runs `/intel-review` non-interactively
- [ ] Brief injection script (`intel-digest.sh`): queries Lockwood `GET /api/intel/alerts` + `GET /api/deals/items?min_score=80&read=false&limit=3`. Formats as:
  ```
  ## Intelligence Alerts (N new)
    ! [CRITICAL] summary...
    [HIGH] summary...
  ## Deal Alerts (N new)
    ! [92] EVGA RTX 3090 FTW3 — BACK IN STOCK at Outworld...
  ```
  Integrated into existing `developer-brief.sh` via source/call
- [ ] Graceful degradation: if Lockwood offline, skip intel section in brief. If no unreviewed items, skip entirely (zero noise)

**Success Criteria:** `/intel-review` produces Opus-level synthesis on top items. BR3 improvements appear with /setlist prompts. Developer brief shows Intelligence + Deal Alerts sections. Runs unattended every 12 hours.

---

### Phase 4: Dashboard — Intelligence Tab

**Status:** not_started
**Files:**

- `ui/src/components/IntelligenceTab.tsx` (NEW)
- `ui/src/components/IntelligenceTab.css` (NEW)
- `ui/src/components/Dashboard.tsx` (MODIFY) — add 4th tab
- `ui/src/services/api.ts` (MODIFY) — add intel API methods
- `ui/src/types/index.ts` (MODIFY) — add intel types

**Blocked by:** None
**After:** Phases 1, 2 (needs data to display)

**Deliverables:**

- [ ] TypeScript interfaces: `IntelItem` (id, title, source, url, source_type, category, priority, score, summary, opus_synthesis, br3_improvement, read, dismissed, collected_at), `IntelAlerts` (critical_count, high_count), `IntelImprovement` (id, title, rationale, complexity, setlist_prompt)
- [ ] `IntelligenceTab` component: priority-sorted feed with critical items pinned at top (red left border), high items below (amber border), medium/low scrollable. Each item: priority dot, title, one-line summary from Below, source badge (Official/Community/Blog), category badge, relative timestamp. Click to expand: full Opus synthesis (if available), raw content preview, link to source
- [ ] Filter bar: dropdown for source_type (All/Official/Community/Blog), category (All/api-change/model-release/community-tool/ecosystem-news/cluster-relevant), priority (All/Critical/High/Medium), time range (24h/7d/30d/All)
- [ ] Alert badge on tab header: red circle with count of unread critical+high items. Updates via 30-second polling
- [ ] Item actions: Dismiss button (grays out, removes from active feed), Mark Read (removes from alert count), "Save to Library" button (POST to Lockwood, which writes research doc stub)
- [ ] BR3 Improvement items: green "Build This" badge, expandable section showing /setlist prompt, complexity estimate, "Copy Command" button that copies `/setlist [prompt]` to clipboard
- [ ] Improvement counter in tab header: "N improvements pending" next to alert badge
- [ ] API methods in api.ts: `getIntelItems(filters)`, `getIntelAlerts()`, `dismissIntelItem(id)`, `markIntelRead(id)`, `getIntelImprovements()`
- [ ] Follow existing Dashboard.css color palette (blue primary, green/amber/red status colors). Dark theme. Cards with generous internal padding per CLAUDE.md rules
- [ ] Auto-refresh: poll `/api/intel/items` every 30 seconds, `/api/intel/alerts` every 15 seconds (badge only)

**Success Criteria:** Intelligence tab renders items from multiple sources sorted by priority. Alert badge shows correct unread count. Filtering by category and source works. BR3 improvement items display "Build This" with copyable /setlist command.

---

### Phase 5: Dashboard — Deals Tab

**Status:** not_started
**Files:**

- `ui/src/components/DealsTab.tsx` (NEW)
- `ui/src/components/DealsTab.css` (NEW)
- `ui/src/components/Dashboard.tsx` (MODIFY) — add 5th tab
- `ui/src/services/api.ts` (MODIFY) — add deals API methods
- `ui/src/types/index.ts` (MODIFY) — add deals types

**Blocked by:** Phase 4 (same Dashboard.tsx — must sequence tab additions)
**After:** Phases 1, 2 (needs data)

**Deliverables:**

- [ ] TypeScript interfaces: `DealItem` (id, hunt_id, name, category, attributes, source_url, price, condition, seller, seller_rating, deal_score, verdict, opus_assessment, listing_url, collected_at, read, dismissed), `Hunt` (id, name, category, keywords, target_price, check_interval_minutes, source_urls, active, created_at), `PriceHistoryPoint` (price, source, recorded_at)
- [ ] Hunt management panel (top section): list active hunts as cards, each showing name, category, target price, items found count, last checked time. "Add Hunt" button opens modal with fields: name, category (dropdown: gpu/guitar/lumber/electronics/food/other), keywords, target price, check interval (15min/30min/1hr/6hr/24hr), source URLs (optional, for changedetection.io watches). "Archive" button on each hunt
- [ ] Deal feed (main section): filtered by selected hunt. Sorted by deal_score descending. Color-coded cards: green border for exceptional (80+), amber for good (60-79), default for fair/pass. Each card: product name, price (large), deal score badge, source badge, seller + rating, condition, one-line Below assessment, Opus assessment (if available, expandable), "Open Listing" external link button
- [ ] Price history chart: per-product mini sparkline (Recharts AreaChart) showing price over time. Appears when clicking a deal card's "History" button. Follow existing dashboard chart patterns from `dashboard-chart-design.md` research (transparent bg, grid rgba(148,163,184,0.06), #0f1520 tooltip)
- [ ] Alert badge on Deals tab: count of unread exceptional deals (score 80+)
- [ ] Quick actions per deal: Dismiss, Mark Read, Open Listing (new tab)
- [ ] Pre-populated GPU hunt: on first load, if no hunts exist, auto-create: name="RTX 3090 FTW3 for Below Upgrade", category="gpu", keywords="EVGA RTX 3090 FTW3 Ultra 24GB -Ti", target_price=900, check_interval=15, source_urls=["https://www.ebay.com/str/outworld"]
- [ ] API methods: `getDealItems(huntId, filters)`, `getHunts()`, `createHunt(hunt)`, `archiveHunt(id)`, `getPriceHistory(dealItemId)`, `dismissDeal(id)`, `markDealRead(id)`
- [ ] Dark theme, generous card padding, same aesthetic as Intelligence tab

**Success Criteria:** Deals tab shows Outworld Systems listings with deal scores. Adding a "Fender Telecaster" hunt starts watching for guitars. Price history sparklines render. Exceptional deals show alert badge.

---

### Phase 6: Setlist Integration — Auto-Plan from Intelligence

**Status:** not_started
**Files:**

- `~/.claude/commands/intel-review.md` (MODIFY) — enhance improvement detection with setlist prompt generation
- `core/cluster/node_intelligence.py` (MODIFY) — add improvement CRUD endpoints
- `ui/src/components/IntelligenceTab.tsx` (MODIFY) — add "Plan This" workflow

**Blocked by:** Phase 4 (modifies IntelligenceTab.tsx)
**After:** Phase 3 (needs Opus improvement detection working)

**Deliverables:**

- [ ] Improvement CRUD endpoints on Lockwood: `GET /api/intel/improvements?status=pending`, `POST /api/intel/improvements` (from intel-review skill), `POST /api/intel/improvements/{id}/status` (pending→planned→built→archived)
- [ ] Enhanced `/intel-review` improvement detection: when Opus identifies actionable BR3 improvement, generates a complete /setlist prompt incorporating: what the improvement is, which existing BR3 systems it affects (reference BUILD specs), what the expected outcome is, and complexity estimate. Stores as improvement record
- [ ] Overlap detection: when improvement relates to existing BR3 functionality, Opus notes the overlap and recommends adopt (replace ours), adapt (merge best of both), or ignore (ours is better) with reasoning
- [ ] "Plan This" button on improvement items in IntelligenceTab: opens modal showing improvement title, Opus rationale, /setlist prompt, complexity badge, affected systems. "Copy /setlist Command" button copies ready-to-paste command
- [ ] Improvement lifecycle tracking: status badge on each improvement (pending/planned/built/archived). When user marks "planned", prompts for BUILD spec name to link. Dashboard shows improvement count by status
- [ ] Improvement history: `GET /api/intel/improvements?status=built` shows past improvements that were successfully integrated, creating a record of how Intelligence → Plan → Build pipeline works over time

**Success Criteria:** Intelligence finds "Agent Teams left experimental", Opus marks BR3 improvement with rationale + /setlist prompt. Dashboard shows "Plan This" with copyable `/setlist integrate Agent Teams GA...` command. Marking as "planned" links to BUILD spec. Full lifecycle from discovery to build tracked.

---

## Session Log

[Will be updated by /begin]
