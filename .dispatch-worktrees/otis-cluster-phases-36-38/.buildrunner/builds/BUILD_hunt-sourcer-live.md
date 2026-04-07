# Build: Hunt Sourcer — Go Live

**Created:** 2026-04-06
**Status:** 🚧 in_progress
**Deploy:** local — Lockwood FastAPI (sourcer cron) + env config (eBay keys)

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

### Phase 1: Wire Sourcer Into Lockwood + Fix Gaps

**Status:** not_started
**Goal:** Sourcer runs as a background cron on Lockwood, eBay searches execute on schedule, deals appear in dashboard scored by Below.
**Files:**

- `core/cluster/node_intelligence.py` (MODIFY) — add sourcer cron startup + `POST /api/deals/source` trigger
- `core/cluster/hunt_sourcer.py` (MODIFY) — add `start_sourcer_cron()` for threading (currently only has `run_forever()` for standalone), add `POST /api/deals/items` endpoint call for deal creation
- `core/cluster/intel_collector.py` (MODIFY) — add listing_url hash dedup to `create_deal_item()`
- `core/cluster/hunt_sources/ebay_browse.py` (EXISTING — no changes, needs EBAY_APP_ID + EBAY_SECRET env vars)

**Blocked by:** None
**Deliverables:**

- [ ] Add `start_sourcer_cron()` to hunt_sourcer.py — threading wrapper like scoring/verifier crons
- [ ] Wire sourcer cron into `intel_startup()` in node_intelligence.py with `DISABLE_SOURCER` toggle
- [ ] Add `POST /api/deals/source` endpoint to manually trigger `check_hunts_once()`
- [ ] Add `POST /api/deals/items` endpoint for sourcer to POST new deals (sourcer uses this when not on Lockwood)
- [ ] Add listing_url dedup in `create_deal_item()` — hash listing_url, reject if exists
- [ ] Configure EBAY_APP_ID + EBAY_SECRET on Lockwood (user must register eBay developer account first)
- [ ] Deploy updated files to Lockwood via SCP, restart uvicorn
- [ ] Verify: trigger `/api/deals/source`, confirm eBay results appear as deal_items, confirm Below scores them

**Success Criteria:** `curl -X POST http://10.0.1.101:8100/api/deals/source` returns found deals. Dashboard Deals tab shows real eBay listings with prices, sellers, scores, and IN STOCK badges.

### Phase 2: Newegg + Shopify + B&H Adapters

**Status:** not_started
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
- [ ] Below-offline fallback — if Below unreachable, skip HTML adapters (Newegg/B&H), eBay + Shopify JSON sources still run
- [ ] Register all 3 new adapters in hunt_sourcer.py `_run_source()` dispatch
- [ ] Rate limiting — 2 sec delay between requests for scraped sites
- [ ] Write hunt_sourcer_config.json with all 7 sources (ebay, reddit, craigslist, pcpartpicker, newegg, shopify, bhphoto) and default settings
- [ ] Deploy to Lockwood, verify multi-source results

**Success Criteria:** PSU hunt finds Corsair RM1200x on Newegg. MS-A2 hunt finds listing on Minisforum store. RAM hunt finds DDR5 on Crucial. All appear in dashboard alongside eBay results.

### Phase 3: Dashboard Fixes + Lockwood Stability

**Status:** not_started
**Goal:** Timestamps display correctly, Lockwood auto-restarts on crash, deal cards show pair badges.
**Files:**

- `~/.buildrunner/dashboard/public/js/ws-intel.js` (MODIFY) — fix timeAgo UTC parsing, add PAIR AVAILABLE badge
- Lockwood keepalive script (NEW) — on Lockwood node at ~/auto-restart.sh or launchd plist

**Blocked by:** None
**Can parallelize with:** Phase 1, Phase 2
**Deliverables:**

- [ ] Fix `timeAgo()` — Lockwood SQLite timestamps are UTC without Z suffix; append Z or offset before calculating delta
- [ ] Add PAIR AVAILABLE badge to deal cards — read `attributes.pair_available` from deal item data
- [ ] Lockwood keepalive — launchd plist or cron-based watchdog that checks port 8100, restarts uvicorn if down
- [ ] Kill existing duplicate uvicorn processes on Lockwood, ensure single instance
- [ ] Deploy dashboard changes, deploy keepalive to Lockwood

**Success Criteria:** Hunt timestamps show "5 minutes ago" not "-17509s ago". Kill Lockwood uvicorn, it restarts within 10 seconds. GPU deals with pair_available show badge.

## Out of Scope (Future)

- Keepa API (paid, excluded)
- Facebook Marketplace (TOS risk)
- Automated purchasing (human always decides)
- Slickdeals integration
- Mobile push notifications (Discord webhook sufficient)
- changedetection.io (wrong tool — we search, not watch)
- New source adapters beyond Phase 2 (Amazon PA-API requires affiliate account)

## Prereqs

- [ ] eBay developer account registered at developer.ebay.com (user action)
- [ ] EBAY_APP_ID + EBAY_SECRET configured in Lockwood environment
- [ ] Below (10.0.1.105) online for HTML extraction + scoring (eBay/Shopify work without it)

## Session Log

- 2026-04-06: Adversarial review via Otis found existing sourcer code (381 lines) + 4 adapters on Otis never synced to Muddy. Pulled code. Rewrote spec to extend, not replace. 4 blockers resolved, 6 warnings incorporated.
