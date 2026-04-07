# Build: Hunt System

**Created:** 2026-04-06
**Status:** 5/5 Phases Complete — ALL COMPLETE
**Deploy:** local — Lockwood FastAPI + Walter sourcing service + Muddy dashboard (deploy nodes via SSH after each phase)

## Overview

/hunt skill + automated sourcing pipeline + dashboard hunt management. Conversational strategy sessions with Claude, automated deal monitoring on the cluster, Opus reasoning on exceptional finds. Zero API cost — eBay Browse API free tier, RSS free, Below inference free.

**Builds On:** BUILD_intel-deals-dashboard (ALL 6 PHASES COMPLETE) — schema, CRUD, scoring, dashboard Deals tab, Opus review, changedetection.io all exist.

**DO NOT:**

- Rebuild existing infrastructure (active_hunts, deal_items, price_history tables, CRUD, scoring, dashboard tab)
- Use Keepa API (paid, excluded by design)
- Scrape Facebook Marketplace (TOS violation)
- Add automated purchasing (human always decides)
- Hard-code node IPs (use cluster-check.sh)

**Research:**

- `~/Projects/research-library/docs/techniques/deal-finding-price-tracking.md` (50+ sources)
- `~/.claude/projects/-Users-byronhudson-Projects-BuildRunner3/memory/project_cluster_upgrade.md` (buy list + compatibility)

## Parallelization Matrix

| Phase | Key Files                                                              | Can Parallel With | Blocked By |
| ----- | ---------------------------------------------------------------------- | ----------------- | ---------- |
| 1     | `~/.claude/commands/hunt.md`                                           | 2, 3              | -          |
| 2     | `core/cluster/hunt_sourcer.py`, `core/cluster/hunt_sources/*`          | 1, 3 (build)      | 1 (deploy) |
| 3     | `~/.buildrunner/dashboard/public/index.html`                           | 1, 2              | -          |
| 4     | `core/cluster/node_intelligence.py`, `core/cluster/intel_collector.py` | -                 | 1 or 3     |
| 5     | `core/cluster/intel_scoring.py`, `core/cluster/intel_collector.py`     | -                 | 2, 4       |

**Optimal execution:**

- **Wave 1:** Phases 1, 2, 3 (all parallel — zero file conflicts)
- **Wave 2:** Phase 4 (needs hunts creatable)
- **Wave 3:** Phase 5 (needs sourcer + auto-watch)

## Phases

### Phase 1: /hunt Skill (Claude Code Command)

**Status:** COMPLETE
**Goal:** Type /hunt and have a strategy conversation — research a buy list, see fair prices, create hunts, review exceptional deals.
**Files:**

- `~/.claude/commands/hunt.md` (NEW)
  **Blocked by:** None
  **Deliverables:**
- [ ] `/hunt` (no args) — list active hunts with deal counts and top scores
- [ ] `/hunt research <topic>` — reads memory/specs, researches current market via WebSearch, recommends fair price per item, compares to target
- [ ] `/hunt add <name> <category> <target_price> <keywords> [sources]` — creates hunt via Lockwood API
- [ ] `/hunt deals [hunt_id]` — show exceptional deals (80+) with Opus verdicts
- [ ] `/hunt review` — trigger Opus reasoning on unreviewed 80+ deals (like /intel-review Step 4)
- [ ] `/hunt archive <hunt_id>` — archive a completed hunt
- [ ] Connects to Lockwood dynamically via `cluster-check.sh semantic-search`
- [ ] Graceful fallback if Lockwood offline

**Success Criteria:** `/hunt research "cluster upgrade"` reads upgrade memory, searches eBay sold listings, tells you what each item should cost today.

### Phase 2: Automated Sourcing Service (Walter)

**Status:** COMPLETE
**Goal:** Background service polls deal sources on a schedule, feeds results into Lockwood, Below scores automatically. Wake up to scored deals in the dashboard.
**Files:**

- `core/cluster/hunt_sourcer.py` (NEW)
- `core/cluster/hunt_sourcer_config.json` (NEW)
- `core/cluster/hunt_sources/__init__.py` (NEW)
- `core/cluster/hunt_sources/ebay_browse.py` (NEW)
- `core/cluster/hunt_sources/reddit_rss.py` (NEW)
- `core/cluster/hunt_sources/craigslist_rss.py` (NEW)
- `core/cluster/hunt_sources/pcpartpicker.py` (NEW)
  **Blocked by:** None (different files than Phase 1)
  **After:** Phase 1 (hunts need to exist for sourcer to poll)
  **Deliverables:**
- [ ] eBay Browse API client — search active listings + sold/completed for fair price baseline (free, 5K/day)
- [ ] Reddit RSS parser — r/buildapcsales + r/hardwareswap, extract product/price/condition via Below
- [ ] Craigslist RSS parser — configurable city, keyword matching
- [ ] PCPartPicker Playwright scraper — price comparison across retailers
- [ ] APScheduler (Python) or systemd timer scheduling respecting each hunt's `check_interval_minutes`
- [ ] Results POST to Lockwood `POST /api/deals/items` or batch endpoint
- [ ] Pair detection — flag when 2+ matching items from same seller (NVLink requirement)
- [ ] Dedup against existing deal_items (URL hash + title similarity via Below)
- [ ] Deploy to Walter via SCP + systemd service

**Success Criteria:** Create an RTX 3090 hunt, sourcer finds active eBay listings within one check interval, deals appear in dashboard scored by Below.

### Phase 3: Dashboard Hunt Management

**Status:** COMPLETE
**Goal:** Create, edit, filter, and visualize hunts directly from the dashboard.
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY)
  **Blocked by:** None (different files than Phase 1-2)
  **Deliverables:**
- [ ] "Create Hunt" button + modal form (name, category dropdown, keywords, target_price, check_interval, source_urls)
- [ ] Edit hunt (inline edit on hunt cards)
- [ ] Hunt filter dropdown — show deals for selected hunt only
- [ ] Price history sparkline per deal card (Chart.js or inline SVG, data from `GET /api/deals/price-history/{id}`)
- [ ] "Pair Available" badge on deals where sourcer detected matching pair

**Success Criteria:** Create a new hunt from dashboard, see it in hunt list, filter deals by that hunt.

### Phase 4: changedetection.io Auto-Watch

**Status:** COMPLETE
**Goal:** Creating a hunt with source URLs automatically starts watching those pages. Archiving removes watches.
**Files:**

- `core/cluster/node_intelligence.py` (MODIFY)
- `core/cluster/intel_collector.py` (MODIFY)
  **Blocked by:** Phase 1 or 3 (hunts must be creatable)
  **Deliverables:**
- [ ] On hunt create: POST to changedetection.io API (Lockwood :5000) for each source_url
- [ ] Configure CSS selectors per source type (eBay: `.s-item`, Newegg: `.item-cell`, etc.)
- [ ] Set webhook to `POST /api/deals/webhook/changedetection` with hunt_id context
- [ ] On hunt archive: DELETE watches from changedetection.io
- [ ] Selector config extends `hunt_sourcer_config.json` created in Phase 2 (add `selectors` key, preserve existing schema)

**Success Criteria:** Create hunt with eBay URL, changedetection.io shows new watch, page change triggers webhook and creates deal_item.

### Phase 5: Intelligence Layer

**Status:** COMPLETE
**Goal:** Smarter scoring — pair awareness, timing advice, total cost of ownership, alternative suggestions.
**Files:**

- `core/cluster/intel_scoring.py` (MODIFY)
- `core/cluster/intel_collector.py` (MODIFY)
  **Blocked by:** Phase 2 (needs sourcer feeding data), Phase 4 (same files)
  **Deliverables:**
- [ ] Pair scoring boost — deals part of an available pair score higher (NVLink critical)
- [ ] Timing intelligence — seasonal patterns (Prime Day July, Black Friday Nov), GPU generation launches
- [ ] Total cost of ownership — add known accessory costs (blower +$80 cooler, Canada +$400 import)
- [ ] Alternative suggestions — different product at similar value for less (benchmark-per-dollar from PCPartPicker data)
- [ ] "Buy now or wait" verdict — Opus reasoning combining price trend, timing, pair availability, TCO
- [ ] Update `/hunt review` output to include timing + TCO context

**Success Criteria:** Blower 3090 at $900 scores lower than FTW3 at $900 (TCO includes cooler). Deal in June gets "wait for Prime Day" note.

## Out of Scope (Future)

- Keepa API (paid, excluded)
- Facebook Marketplace (TOS risk)
- Automated purchasing
- Mobile push notifications (Discord webhook sufficient)
- Multi-user hunt sharing
- International marketplace monitoring

## Session Log

[Will be updated by /begin]
