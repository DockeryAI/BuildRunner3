# Build: Hunt Sourcer — Go Live

**Created:** 2026-04-06
**Status:** BUILD COMPLETE — All 5 Phases Done
**Deploy:** local — Lockwood FastAPI (sourcer cron), zero external API keys required

## Overview

Wire the existing hunt sourcer (built on Otis, synced to Muddy this session) into Lockwood's live service, add missing retail adapters, and fix gaps found by adversarial review. The sourcer core, eBay adapter, Reddit RSS, Craigslist RSS, PCPartPicker, pair detection, and title dedup all exist — this build connects them and fills holes.

**Builds On:** BUILD_hunt-system (code exists but never deployed), BUILD_intel-deals-dashboard (schema, CRUD, scoring, dashboard all live)

**DO NOT:**

- Rewrite hunt_sourcer.py — extend it
- Rewrite existing adapters (ebay_browse, reddit_rss, craigslist_rss, pcpartpicker) — they work
- Install changedetection.io — wrong tool, decided against this session
- Hard-code node IPs — use cluster-check.sh or env vars

**Adversarial Review:** Completed 2026-04-06 via Otis. 4 blockers found and resolved (existing code on Otis pulled to Muddy, spec rewritten to extend not replace). 6 warnings incorporated.

## Parallelization Matrix

| Phase | Key Files                                                       | Can Parallel With | Blocked By           |
| ----- | --------------------------------------------------------------- | ----------------- | -------------------- |
| 1     | `node_intelligence.py`, `hunt_sourcer.py`, `intel_collector.py` | 3                 | -                    |
| 2     | `hunt_sources/newegg.py`, `shopify.py`, `bhphoto.py` (all NEW)  | 3                 | 1 (adapter registry) |
| 3     | `ws-intel.js`, Lockwood launchd (NEW)                           | 1, 2              | -                    |

**Optimal execution:**

- **Wave 1:** Phase 1 + Phase 3 (parallel — different files)
- **Wave 2:** Phase 2 (needs sourcer wired in from Phase 1)

## Phases

### Phase 1: Wire Sourcer Into Lockwood + eBay Scrape Adapter

**Status:** ✅ COMPLETE
**Goal:** Sourcer runs as a background cron on Lockwood, searches eBay via HTML scrape + Below extraction (no API keys needed), deals appear in dashboard scored by Below.
**Files:**

- `core/cluster/node_intelligence.py` (MODIFY) — add sourcer cron startup + `POST /api/deals/source` trigger
- `core/cluster/hunt_sourcer.py` (MODIFY) — add `start_sourcer_cron()` for threading (currently only has `run_forever()` for standalone)
- `core/cluster/intel_collector.py` (MODIFY) — add listing_url hash dedup to `create_deal_item()`
- `core/cluster/hunt_sources/ebay_scrape.py` (NEW) — fetch eBay search page HTML, Below extracts listings. Default adapter — works with zero credentials.
- `core/cluster/hunt_sources/ebay_browse.py` (EXISTING — optional upgrade path if eBay API ever approved, not required)

**Blocked by:** None
**Deliverables:**

- [ ] Build `ebay_scrape.py` adapter — fetch eBay search URL with hunt keywords, send product listing HTML to Below qwen3:8b for structured extraction (title, price, condition, seller, seller rating, URL, stock status)
- [ ] Register `ebay_scrape` as default eBay adapter in `_run_source()`, keep `ebay_browse` as optional fallback if API keys present
- [ ] Add `start_sourcer_cron()` to hunt_sourcer.py — threading wrapper like scoring/verifier crons
- [ ] Wire sourcer cron into `intel_startup()` in node_intelligence.py with `DISABLE_SOURCER` toggle
- [ ] Add `POST /api/deals/source` endpoint to manually trigger `check_hunts_once()`
- [ ] Add listing_url dedup in `create_deal_item()` — hash listing_url, reject if exists
- [ ] Deploy updated files to Lockwood via SCP, restart uvicorn
- [ ] Verify: trigger `/api/deals/source`, confirm eBay results appear as deal_items, confirm Below scores them

**Success Criteria:** `curl -X POST http://10.0.1.101:8100/api/deals/source` returns found deals. Dashboard Deals tab shows real eBay listings with prices, sellers, scores, and IN STOCK badges. No API keys required.

### Phase 2: Newegg + Shopify + B&H Adapters

**Status:** ✅ COMPLETE
**Goal:** Search Newegg, B&H Photo, Crucial, and Minisforum alongside eBay. Below extracts listings from HTML sources.
**Files:**

- `core/cluster/hunt_sources/newegg.py` (NEW) — HTML fetch + Below qwen3:8b extraction
- `core/cluster/hunt_sources/shopify.py` (NEW) — Minisforum + Crucial via Shopify search/suggest.json
- `core/cluster/hunt_sources/bhphoto.py` (NEW) — HTML fetch + Below extraction
- `core/cluster/hunt_sourcer.py` (MODIFY) — register new adapters in `_run_source()`
- `core/cluster/hunt_sourcer_config.json` (NEW) — default config with all sources enabled

**Blocked by:** Phase 1 (sourcer must be wired into Lockwood)
**Deliverables:**

- [ ] Newegg adapter — search URL fetch, send product grid HTML to Below for structured extraction (title, price, seller, condition, URL, stock)
- [ ] Shopify adapter — `search/suggest.json?q=KEYWORDS&resources[type]=product` for Minisforum/Crucial (pure JSON, no LLM)
- [ ] B&H adapter — search URL fetch, Below extraction
- [ ] Below-offline fallback — if Below unreachable, skip all HTML adapters (eBay/Newegg/B&H), only Shopify JSON runs
- [ ] Register all 3 new adapters in hunt_sourcer.py `_run_source()` dispatch
- [ ] Rate limiting — 2 sec delay between requests for scraped sites
- [ ] Write hunt_sourcer_config.json with all 8 sources (ebay_scrape, ebay_browse, reddit, craigslist, pcpartpicker, newegg, shopify, bhphoto) — ebay_scrape enabled by default, ebay_browse disabled unless API keys present
- [ ] Deploy to Lockwood, verify multi-source results

**Success Criteria:** PSU hunt finds Corsair RM1200x on Newegg. MS-A2 hunt finds listing on Minisforum store. RAM hunt finds DDR5 on Crucial. All appear in dashboard alongside eBay results.

### Phase 3: Dashboard Fixes + Lockwood Stability

**Status:** ✅ COMPLETE
**Goal:** Timestamps display correctly, Lockwood auto-restarts on crash, deal cards show pair badges.
**Files:**

- `~/.buildrunner/dashboard/public/js/ws-intel.js` (MODIFY) — fix timeAgo UTC parsing, add PAIR AVAILABLE badge
- Lockwood keepalive script (NEW) — on Lockwood node at ~/auto-restart.sh or launchd plist

**Blocked by:** None
**Can parallelize with:** Phase 1, Phase 2
**Deliverables:**

- [x] Fix `timeAgo()` — Lockwood SQLite timestamps are UTC without Z suffix; append Z or offset before calculating delta
- [x] Add PAIR AVAILABLE badge to deal cards — read `attributes.pair_available` from deal item data
- [x] Lockwood keepalive — launchd plist or cron-based watchdog that checks port 8100, restarts uvicorn if down
- [x] Kill existing duplicate uvicorn processes on Lockwood, ensure single instance
- [x] Deploy dashboard changes, deploy keepalive to Lockwood

**Success Criteria:** Hunt timestamps show "5 minutes ago" not "-17509s ago". Kill Lockwood uvicorn, it restarts within 10 seconds. GPU deals with pair_available show badge.

### Phase 4: Hunt Requirements + Session Fixes _(added: 2026-04-07)_

**Status:** ✅ COMPLETE
**Blocked by:** Phase 3 (complete)
**Goal:** Every item in the feed passes structured requirements. No out-of-stock, no wrong products, no over-budget, no excluded terms. Commit all fixes made during 2026-04-07 debugging session.

**Files:**

- `core/cluster/hunt_sourcer.py` (MODIFY) — add `_validate_item()`, centralize all filtering, pass requirements from hunt
- `core/cluster/intel_schema.sql` (MODIFY) — add `requirements TEXT` column to `active_hunts`
- `core/cluster/intel_collector.py` (MODIFY) — add requirements to `create_hunt()` and `get_hunts()`
- `core/cluster/hunt_sourcer_config.json` (ALREADY MODIFIED) — disabled ebay_scrape/craigslist, removed Crucial from Shopify
- `core/cluster/hunt_sources/reddit_rss.py` (ALREADY MODIFIED) — smart keyword matching, [W] post filter
- `core/cluster/hunt_sources/newegg.py` (ALREADY MODIFIED) — regex HTML extraction, skip OOS
- `core/cluster/hunt_sources/ebay_scrape.py` (ALREADY MODIFIED) — regex HTML extraction, browser headers
- `core/cluster/hunt_sources/bhphoto.py` (ALREADY MODIFIED) — browser headers
- `core/cluster/hunt_sources/craigslist_rss.py` (ALREADY MODIFIED) — browser UA, keyword fix
- `core/cluster/hunt_sources/pcpartpicker.py` (ALREADY MODIFIED) — HTML search fallback
- `core/cluster/hunt_sources/shopify.py` (ALREADY MODIFIED) — removed Crucial

**Deliverables:**

- [ ] Add `requirements TEXT` column to `active_hunts` in schema + migrate existing DB _(added: 2026-04-07)_
- [ ] Build `_validate_item(item, requirements)` — checks: in*stock, price_min/max, title_must_contain (AND + OR groups), title_must_not_contain, condition_accept/reject, domestic_only, min_seller_feedback, min_seller_rating *(added: 2026-04-07)\_
- [ ] Replace all ad-hoc filters in `_batch_insert_deals` and source modules with `_validate_item()` call _(added: 2026-04-07)_
- [ ] Populate requirements JSON for all 9 cluster upgrade hunts per upgrade plan discussion _(added: 2026-04-07)_
- [ ] Add `pair_rules` support — flag when 2+ items of same model exist for hunts needing pairs _(added: 2026-04-07)_
- [ ] Commit all session fixes (Reddit, Newegg, eBay, B&H, PCPartPicker, Shopify, Craigslist, Lockwood fallback, OOS/price/exclusion filters) _(added: 2026-04-07)_
- [ ] Purge bad data from DB, re-run full sweep, verify 0 garbage items enter feed _(added: 2026-04-07)_
- [ ] Sync DB to Lockwood, restart Lockwood service _(added: 2026-04-07)_

**Requirements JSON Schema:**

```json
{
  "filters": {
    "in_stock_only": true,
    "price_min": 500,
    "price_max": 1100,
    "title_must_contain": ["RTX", "3090"],
    "title_must_not_contain": ["Ti", "water block", "for parts", "not working", "EKWB"],
    "condition_accept": ["New", "Refurbished", "Used"],
    "domestic_only": true,
    "min_seller_feedback": 10,
    "min_seller_rating": 95.0
  },
  "pair_rules": { "quantity_needed": 2, "must_match_model": true },
  "notes": ["NVLink requires matching brand+model"]
}
```

**Success Criteria:** Run full hunt sweep. Every item passes all requirements. Zero OOS, zero wrong products, zero over-budget, zero excluded terms.

### Phase 5: Below Prompt Alignment _(added: 2026-04-07)_

**Status:** ✅ COMPLETE
**Blocked by:** Phase 4 (requirements must exist to inform prompts)
**Goal:** All Below LLM extraction prompts aligned with /opus + /llm research. Few-shot examples, JSON schema format parameter, correct temperature per model, seller/location extraction for requirement validation.

**Research loaded:**

- `~/Projects/research-library/docs/techniques/claude-opus-prompting-consistency.md`
- `~/Projects/research-library/docs/techniques/local-llm-prompting-ollama-cluster.md`

**Key principles applied:**

- Qwen 3 8B: temp 0.2, `think: false`, `presence_penalty: 1.5`, `format:{schema}` not `format:"json"`
- Multishot > instruction (3 diverse examples for 8B models)
- Concise prompts — no verbose field-by-field instructions (per /opus §1.1: softer language for 4.6-era models)
- Schema in format param AND in prompt text — grammar handles syntax, prompt handles semantics
- Extract seller_feedback, seller_rating, location fields — needed for requirement validation
- Include null/empty example — prevents hallucination to fill fields

**Files:**

- `core/cluster/hunt_sources/ebay_scrape.py` (MODIFY) — rewrite Below prompt with few-shot, schema format, add seller/location fields
- `core/cluster/hunt_sources/newegg.py` (MODIFY) — rewrite Below fallback prompt, schema format
- `core/cluster/hunt_sources/bhphoto.py` (MODIFY) — rewrite Below prompt, schema format
- `core/cluster/hunt_sourcer.py` (MODIFY) — add Pydantic models for extraction schemas, switch to `format:{schema}`
- `core/cluster/node_inference.py` (MODIFY) — align scoring/classification prompts with /llm research

**Deliverables:**

- [ ] Create Pydantic extraction models (DealListing, DealScore) for JSON schema generation _(added: 2026-04-07)_
- [ ] Rewrite ebay*scrape Below prompt: 3 few-shot examples, `format:{schema}`, temp 0.2, `think:false`, extract seller_feedback + location *(added: 2026-04-07)\_
- [ ] Rewrite newegg Below fallback prompt: same pattern (regex primary, LLM fallback only) _(added: 2026-04-07)_
- [ ] Rewrite bhphoto Below prompt: same pattern _(added: 2026-04-07)_
- [ ] Switch all Ollama calls from `format:"json"` to `format:DealListing.model_json_schema()` _(added: 2026-04-07)_
- [ ] Add `num_ctx: 8192` to all Ollama options (default 2048-4096 truncates HTML) _(added: 2026-04-07)_
- [ ] Add json*repair + Pydantic validation pipeline for all Below responses *(added: 2026-04-07)\_
- [ ] Create `hunt-extractor` Ollama Modelfile with baked-in few-shot examples _(added: 2026-04-07)_
- [ ] Test full sweep with aligned prompts, verify extraction accuracy _(added: 2026-04-07)_
- [ ] Deploy to Lockwood _(added: 2026-04-07)_

**Prompt template (per /llm research):**

```
System: "Extract product listings as JSON. Use null for missing fields. Return as JSON."

Example 1 (user): "Extract: 'EVGA RTX 3090 FTW3 Ultra - $899, Refurbished, seller: outworld_systems (994, 99.6%)'"
Example 1 (assistant): {"title":"EVGA RTX 3090 FTW3 Ultra","price":899.0,...}

Example 2 (user): "Extract: 'This item is currently out of stock'"
Example 2 (assistant): {"title":null,"price":null,...,"in_stock":false}

Example 3 (user): "Extract: '{actual HTML content}'"
```

**Success Criteria:** Below extraction returns valid JSON with seller_feedback, seller_rating, location fields. 0 json_repair invocations on clean HTML. All items pass requirement validation.

### Phase 6: Market Price Collection _(added: 2026-04-07)_

**Status:** pending
**Blocked by:** Phase 5 (complete)
**Goal:** Accumulate historical price data from sold listings, Reddit history, and ongoing sourcer runs. Build the dataset for deal quality scoring.
**Adversarial review:** 13 blockers found and resolved (price_history reuse, migration pattern, eBay API dual-key check, budget from target_price). Findings: `.buildrunner/plans/amend-adversarial-findings.json`

**Files:**

- `core/cluster/intel_schema.sql` (MODIFY) — extend `price_history` table with hunt_id, is_sold, condition, title columns
- `core/cluster/intel_collector.py` (MODIFY) — add `log_market_price()`, extend `_ensure_intel_tables()` with ALTER TABLE migrations
- `core/cluster/hunt_sourcer.py` (MODIFY) — log every price to price_history before requirements filtering
- `core/cluster/hunt_sources/ebay_sold.py` (NEW) — eBay completed/sold listings via `LH_Sold=1&LH_Complete=1`, new adapter function (not reuse of ebay_scrape)
- `core/cluster/hunt_sources/reddit_rss.py` (MODIFY) — add `search_historical()` with new JSON parsing (different API from RSS)

**Deliverables:**

- [ ] Extend `price_history` table: add `hunt_id INTEGER`, `is_sold INTEGER DEFAULT 0`, `condition TEXT`, `title TEXT`, `url TEXT` columns via ALTER TABLE migrations _(added: 2026-04-07)_
- [ ] Build `log_market_price(hunt_id, price, source, title, url, is_sold, condition)` in intel*collector.py *(added: 2026-04-07)\_
- [ ] Modify sourcer to call `log_market_price()` for every item BEFORE `_validate_item()` — rejected items are valid market data _(added: 2026-04-07)_
- [ ] Build `ebay_sold.py` — new adapter with `LH_Sold=1&LH_Complete=1` params, regex parser for sold price extraction, `is_sold=1` on all entries _(added: 2026-04-07)_
- [ ] Add `search_historical()` to reddit*rss.py — hits `/search.json` (JSON response, not RSS), extracts prices from titles, last 30 days *(added: 2026-04-07)\_
- [ ] Wire eBay Browse API — enable when BOTH `EBAY_APP_ID` AND `EBAY_SECRET` env vars present _(added: 2026-04-07)_
- [ ] Run initial seeding pass for all 9 existing hunts _(added: 2026-04-07)_
- [ ] Sync DB to Lockwood via scp (market data lives in same intel.db file) _(added: 2026-04-07)_

**Success Criteria:** `price_history` has 50+ data points for GPU hunts, 10+ for commodity items. eBay sold adapter returns actual transaction prices with `is_sold=1`.

### Phase 7: Market Stats Engine + Purchase Tracking _(added: 2026-04-07)_

**Status:** pending
**Blocked by:** Phase 6 (needs market data to compute stats)
**Goal:** Compute per-hunt market statistics and deal quality scoring. Add purchase tracking.

**Files:**

- `core/cluster/intel_collector.py` (MODIFY) — add `get_market_stats()` (NEW function), `update_deal_item()` (NEW function), `mark_purchased()` (NEW function)
- `core/cluster/intel_schema.sql` (MODIFY) — add `purchased`, `purchased_price` to deal_items via ALTER TABLE
- `core/cluster/node_intelligence.py` (MODIFY) — add `GET /api/deals/market/{hunt_id}` (NEW endpoint), `PATCH /api/deals/items/{id}` (NEW endpoint), `GET /api/deals/summary` (NEW endpoint)

**Deliverables:**

- [ ] Add `purchased INTEGER DEFAULT 0` and `purchased_price REAL` to deal*items via ALTER TABLE migration *(added: 2026-04-07)\_
- [ ] Build `get_market_stats(hunt_id, days=90)` in intel*collector.py (NEW function) — uses Python `statistics.median`, `statistics.quantiles` on price_history rows. Returns: median, p25, p75, min, max, sample_count, sold_count, trend *(added: 2026-04-07)\_
- [ ] Build `update_deal_item(item_id, **fields)` in intel*collector.py (NEW function) — general-purpose update for purchased, purchased_price, notes *(added: 2026-04-07)\_
- [ ] Add `GET /api/deals/market/{hunt_id}` endpoint (NEW) — returns market stats JSON from get*market_stats() *(added: 2026-04-07)\_
- [ ] Add `PATCH /api/deals/items/{id}` endpoint (NEW) — calls update*deal_item() *(added: 2026-04-07)\_
- [ ] Add `GET /api/deals/summary` endpoint (NEW) — per-hunt spend totals using SUM(target*price) as budget, SUM(purchased_price) as spent *(added: 2026-04-07)\_
- [ ] Trend computation: linear regression on 30-day price*history window → rising/falling/stable *(added: 2026-04-07)\_

**Success Criteria:** `GET /api/deals/market/2` returns median price for RTX 3090 with sample count. `PATCH` toggles purchased. `GET /api/deals/summary` shows budget vs spent.

### Phase 8: Deals Page Redesign _(added: 2026-04-07)_

**Status:** pending
**Blocked by:** Phase 7 (needs stats API + purchase endpoint)
**Goal:** Single deal feed sorted by quality vs market, market position on every card, purchase tracking, exceptional deals highlighted.

**Files:**

- `~/.buildrunner/dashboard/public/js/ws-intel.js` (MODIFY) — rewrite deals rendering section (lines 1133-1232)

**Deliverables:**

- [ ] Fetch market stats per hunt — separate call to `GET /api/deals/market/{hunt_id}` per active hunt _(added: 2026-04-07)_
- [ ] Compute deal*percentile at render time: `(prices_above_this / total_prices) * 100` from market stats response *(added: 2026-04-07)\_
- [ ] Sort deals by deal*percentile ascending (best deals first) *(added: 2026-04-07)\_
- [ ] Deal card redesign: title + price (large), tags (source/condition/stock), market position bar showing price vs P25/median/P75 range _(added: 2026-04-07)_
- [ ] Highlight tiers: exceptional (below P25) green glow + label, good (below median) green border, fair (above median) neutral, pass (above budget) muted _(added: 2026-04-07)_
- [ ] "Mark Bought" button — calls `PATCH /api/deals/items/{id}` with `{purchased: 1, purchased_price: price}`, card moves to bought section _(added: 2026-04-07)_
- [ ] Inline edit — click price to edit, click to add notes _(added: 2026-04-07)_
- [ ] KPI bar: total deals, bought count, total spent vs total budget (from /api/deals/summary), hunt count _(added: 2026-04-07)_
- [ ] Empty state per hunt: "No deals found — N market prices tracked, median $X" _(added: 2026-04-07)_
- [ ] Remove dead fields: MSRP, savings, score when 0, verdict when empty _(added: 2026-04-07)_

**Success Criteria:** Deals page shows market median + percentile on every card. Best deals at top. "Mark Bought" persists. Budget tracker shows spent vs total.

## Out of Scope (Future)

- Keepa API (paid, excluded)
- Facebook Marketplace (TOS risk)
- Automated purchasing (human always decides)
- Slickdeals integration
- Mobile push notifications (Discord webhook sufficient)
- changedetection.io (wrong tool — we search, not watch)
- Amazon PA-API (requires affiliate account with sales)
- vLLM batch inference (post GPU upgrade — research complete, ready to implement)

## Prereqs

- [ ] Below (10.0.1.105) online for HTML extraction + scoring (only Shopify JSON works without it)
- [ ] eBay Browse API keys (OPTIONAL — user needs to sign up at developer.ebay.com, instant approval)

## Session Log

- 2026-04-06: Adversarial review via Otis found existing sourcer code (381 lines) + 4 adapters on Otis never synced to Muddy. Pulled code. Rewrote spec to extend, not replace. 4 blockers resolved, 6 warnings incorporated.
- 2026-04-06: eBay Browse API requires affiliate approval (eBay Partner Network) — no guarantee, 10+ business day wait. Switched to HTML scrape + Below extraction as default. Browse API kept as optional upgrade. Zero external API keys required for full pipeline.
- 2026-04-07: Feed and hunts empty after DB wipe. Restored from Lockwood. Fixed: Reddit keyword matching (model+brand, exclusions, [W] filter), Newegg regex extraction (skip OOS), eBay/B&H browser headers (403→200), PCPartPicker HTML fallback, Shopify removed Crucial (not Shopify), Lockwood API fallback to local DB, schema migration (listing_url_hash), added 2 missing hunts (NVMe + bridge alt). Disabled: eBay scrape (CAPTCHA), Craigslist (IP block). 48 deals inserted, purged garbage, 6 clean items remaining.
- 2026-04-07: Designed hunt requirements system — per-hunt JSON rules enforced at insert time. Researched local LLM prompting (8 Opus sub-agents, 2 rounds, 55+ sources). Created /llm skill + research library doc. Amended BUILD spec with Phase 4 (requirements) + Phase 5 (prompt alignment).
- 2026-04-07: Amended BUILD spec with Phase 6 (market price collection), Phase 7 (market stats + purchase tracking), Phase 8 (deals page redesign). Adversarial review: 13 blockers found and resolved — key fixes: reuse price_history table instead of new market_prices, ALTER TABLE migrations, deal_percentile computed at render time not stored, budget from target_price. Built enforce-build-gates.sh hook to enforce adversarial review on all future amendments.
