# Hunt Sourcer — Draft Spec

## What Already Exists

- 7 active hunts in Lockwood SQLite (keywords, target prices, source URLs)
- Deal pipeline: create_deal_item → Below scoring (qwen3:8b) → verifier (HTTP in-stock check) → dashboard display
- intel_verifier.py — background cron re-checks deal links every 5 min
- Dashboard Intelligence workspace — Hunts tab (7 hunts visible), Deals tab ready
- intel_scoring.py — Below scores 0-100 with verdict (exceptional/good/fair/pass)
- /hunt skill — research, add, deals, review, archive
- node_intelligence.py — FastAPI endpoints for all CRUD + webhooks
- intel_collector.py — deal/hunt CRUD, webhook parsers
- intel_schema.sql — deal_items with verified/link_status/in_stock/last_checked columns

## What's Missing

The sourcer — nothing searches for products. Hunts exist, scoring exists, dashboard exists, but the pipe between "search the internet" and "create deal items" doesn't.

## Phase 1: eBay Search Adapter + Sourcer Core

**Goal:** Sourcer searches eBay for each hunt's keywords, creates deal items with in-stock confirmation. Deals appear in dashboard, scored by Below.

**Files:**

- core/cluster/hunt_sourcer.py (NEW) — cron loop, hunt iteration, adapter dispatch, dedup
- core/cluster/hunt_sources/**init**.py (NEW)
- core/cluster/hunt_sources/ebay_browse.py (NEW) — eBay Browse API OAuth2 + search
- core/cluster/node_intelligence.py (MODIFY) — add sourcer cron startup + manual trigger endpoint
- core/cluster/intel_collector.py (MODIFY) — add listing_url dedup to create_deal_item

**Deliverables:**

- eBay Browse API OAuth2 client credentials flow (app token, no user login)
- Search by hunt keywords with price filter (under target_price \* 1.2)
- Extract: title, price, condition, seller, seller rating, listing URL, availability status
- Filter out junk: "for parts", water blocks, Ti models, zero-feedback sellers
- Dedup against existing deal_items by listing_url hash
- In-stock confirmation from eBay API response (itemAvailabilityStatus)
- Sourcer cron respects each hunt's check_interval_minutes
- POST /api/deals/source manual trigger endpoint
- DISABLE_SOURCER env toggle, startup in node_intelligence.py

## Phase 2: Multi-Source Adapters

**Goal:** Search beyond eBay — Newegg, B&H, Crucial, Minisforum, Reddit deal subs.

**Files:**

- core/cluster/hunt_sources/newegg.py (NEW) — HTML fetch + Below extraction
- core/cluster/hunt_sources/shopify.py (NEW) — Minisforum/Crucial JSON search
- core/cluster/hunt_sources/bhphoto.py (NEW) — HTML fetch + Below extraction
- core/cluster/hunt_sources/reddit_deals.py (NEW) — r/buildapcsales + r/hardwareswap RSS
- core/cluster/hunt_sourcer.py (MODIFY) — register new adapters

**Deliverables:**

- Newegg adapter — fetch search page, Below qwen3:8b extracts listings
- Shopify JSON adapter — search/suggest.json for Minisforum/Crucial
- B&H Photo adapter — fetch search page, Below extraction
- Reddit RSS adapter — r/buildapcsales + r/hardwareswap, Below parses posts
- Below-offline fallback — skip HTML adapters, eBay/Shopify JSON still run
- Rate limiting per source (1-2 req/sec scraped, respect eBay API limits)

## Phase 3: Pair Detection + Smart Filtering

**Goal:** Identify matching GPU pairs (NVLink), apply hunt-specific filters.

**Files:**

- core/cluster/hunt_sourcer.py (MODIFY) — pair detection logic
- core/cluster/intel_scoring.py (MODIFY) — pair scoring boost
- ~/.buildrunner/dashboard/public/js/ws-intel.js (MODIFY) — pair badge on deal cards

**Deliverables:**

- Pair detection — flag 2+ identical model from same seller or concurrent listings
- NVLink compatibility check — reject 3090 Ti, flag water blocks, flag mismatched brands
- Scoring boost for pair-available deals (+15 points)
- PAIR AVAILABLE badge in dashboard
- Hunt-specific exclude rules from keyword patterns (-Ti -water -block -parts)

## Phase 4: Lockwood Process Management + Timestamp Fix

**Goal:** Lockwood stays up reliably, timestamps display correctly.

**Files:**

- Lockwood launchd plist or keepalive script (NEW) — on Lockwood node
- ~/.buildrunner/dashboard/public/js/ws-intel.js (MODIFY) — fix timeAgo UTC parsing

**Deliverables:**

- Launchd plist or keepalive on Lockwood — single uvicorn, auto-restart on crash
- Fix timeAgo() UTC timestamp handling
- Clean up duplicate uvicorn processes

## Dependencies

- Phase 1: no blockers
- Phase 2: blocked by Phase 1 (needs sourcer core)
- Phase 3: blocked by Phase 1 (needs deals to detect pairs)
- Phase 4: no blockers, can parallel with anything

## Prereqs

- eBay developer account + OAuth2 credentials
- Below (10.0.1.105) online for HTML extraction and scoring
