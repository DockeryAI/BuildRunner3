# Build: Hunt Lifecycle Management

**Created:** 2026-04-12
**Status:** Phase 1 In Progress
**Deploy:** local — Lockwood FastAPI + Muddy dashboard (deploy nodes via SSH after each phase)

## Overview

Full item lifecycle tracking for the hunt/deals system. Items flow through found → purchased → received with notes, editable URLs, delivery tracking via 17track, and delete. Hunts can be completed, archived, and revived. Single items can be revived from archived hunts.

**Builds On:** BUILD_hunt-system (ALL 5 PHASES COMPLETE) — hunts, deals, sourcer, scoring, dashboard all exist.

**DO NOT:**

- Rebuild existing hunt/deal infrastructure (tables, CRUD, scoring, dashboard tab all exist)
- Break existing sourcer pipeline or scoring flow
- Remove the existing purchased toggle (extend it)
- Change the intel_items or intel_improvements tables
- Add automated purchasing

**Research:**

- 17track API key stored in `.env` as `TRACK17_API_KEY`
- 17track docs: https://api.17track.net/track/v2.2
- Free tier: 100 queries/day, auto-detects carrier from tracking number

## Parallelization Matrix

| Phase | Key Files                                                                                               | Can Parallel With | Blocked By       |
| ----- | ------------------------------------------------------------------------------------------------------- | ----------------- | ---------------- |
| 1     | `core/cluster/intel_schema.sql`, `core/cluster/intel_collector.py`, `core/cluster/node_intelligence.py` | -                 | -                |
| 2     | `~/.buildrunner/dashboard/public/js/ws-intel.js`, `~/.buildrunner/dashboard/events.mjs`                 | 3                 | 1 (needs API)    |
| 3     | `core/cluster/delivery_tracker.py` (NEW)                                                                | 2                 | 1 (needs schema) |

**Optimal execution:**

- **Wave 1:** Phase 1 (schema + API — everything depends on this)
- **Wave 2:** Phases 2 + 3 (parallel — dashboard vs tracker service, zero file overlap)

## Phases

### Phase 1: Schema + API Extensions

**Status:** not_started
**Goal:** Database supports full item lifecycle (purchased/received/notes/URL/tracking/delete) and hunt completion/archive/revival. All new API endpoints working.
**Files:**

- `core/cluster/intel_schema.sql` (MODIFY)
- `core/cluster/intel_collector.py` (MODIFY)
- `core/cluster/node_intelligence.py` (MODIFY)

**Blocked by:** None
**Pre-flight:** Verify Lockwood's `~/.lockwood/intel.db` has existing BUILD_hunt-system columns (purchased, purchased_price, seller_verified, etc.) — if missing, run full schema init first
**Deliverables:**

- [ ] Add columns to `deal_items`: `received INTEGER DEFAULT 0`, `received_at TEXT`, `user_notes TEXT`, `actual_url TEXT`, `tracking_number TEXT`, `carrier TEXT`, `delivery_status TEXT DEFAULT 'none'`, `delivery_updated_at TEXT`
- [ ] Add columns to `active_hunts`: `completed_at TEXT`, `completion_notes TEXT`
- [ ] Run ALTER TABLE migration on Lockwood's `~/.lockwood/intel.db` (SQLite ALTER ADD COLUMN for each new column)
- [ ] Extend `DealItemUpdate` model with: `received`, `received_at`, `user_notes`, `actual_url`, `tracking_number`, `carrier`, `delivery_status`
- [ ] Rename existing `DealItemUpdate.notes` → `user_notes` for consistency with new schema column (existing `notes` field has no backing column — was writing to void)
- [ ] Extend `update_deal_item()` allowed fields set to include all new columns
- [ ] Add `DELETE /api/deals/items/{item_id}` endpoint — deletes price_history rows FIRST (no FK cascade configured), then deletes the deal_item
- [ ] Add `POST /api/deals/hunts/{hunt_id}/complete` endpoint — sets `active=0`, `completed_at=now()`, accepts optional `completion_notes`. This is the new canonical endpoint; existing `/archive` endpoint remains for backward compat but doesn't set `completed_at`
- [ ] Add `GET /api/deals/hunts/archived` endpoint — returns hunts where `active=0` with item counts and total spent
- [ ] Add `revive_hunt()` and `revive_item()` functions in `intel_collector.py` (no existing revive logic exists — archive_hunt only sets active=0)
- [ ] Add `POST /api/deals/hunts/{hunt_id}/revive` endpoint — calls revive_hunt(), sets `active=1`, clears `completed_at`
- [ ] Add `POST /api/deals/items/{item_id}/revive` endpoint — accepts optional `target_hunt_id` or `new_hunt_name`; if neither provided, creates new hunt named "Revived: {original_hunt_name}". Calls revive_item(), clones item, resets purchased/received to 0

**Success Criteria:** All endpoints testable via curl against Lockwood. Delete removes items. Complete/archive/revive cycle works round-trip.

### Phase 2: Dashboard UI

**Status:** not_started
**Goal:** Dashboard supports the full item lifecycle — multi-state buttons, notes, URL editing, tracking display, delete, hunt completion, archived hunts view, revival.
**Files:**

- `~/.buildrunner/dashboard/public/js/ws-intel.js` (MODIFY)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY)

**Blocked by:** Phase 1 (needs API endpoints)
**Deliverables:**

- [ ] Deal card action buttons: three-state toggle — "Mark Bought" → "Bought ✓ / Mark Received" → "Received ✓✓" (with appropriate styling per state)
- [ ] Deal card inline notes editing — textarea that saves to `user_notes` (separate from AI assessments)
- [ ] Deal card URL editing — click to edit actual_url, prefilled with listing_url, saves to `actual_url` field
- [ ] Deal card tracking display — show carrier + tracking number badge, delivery status badge (color-coded: ordered=yellow, shipped=blue, in_transit=blue, delivered=green)
- [ ] Delete button on every deal card — red ✕ with confirmation modal ("Delete this deal? This cannot be undone.")
- [ ] Hunt card "Complete Hunt" button — confirmation modal, moves hunt to archived state
- [ ] Archived Hunts panel — collapsible section below active hunt cards showing completed hunts with date, item count, total spent
- [ ] "Revive Hunt" button on archived hunt cards — brings hunt back to active
- [ ] "Revive Item" action on items within archived hunts — modal to pick target hunt or create new one
- [ ] Dashboard proxy in events.mjs: add DELETE method forwarding for `/api/proxy/deals/items/{id}`. Also update existing DELETE `/api/proxy/deals/hunts/:id` mapping (line ~1961) to call `/complete` instead of `/archive` for new hunts

**Success Criteria:** Full lifecycle walkthrough in browser — buy item, add note, add tracking, mark received, complete hunt, view in archive, revive.

### Phase 3: 17track Delivery Tracker

**Status:** not_started
**Goal:** Automatic delivery status updates for items with tracking numbers. Walter runs periodic checks via 17track API.
**Files:**

- `core/cluster/delivery_tracker.py` (NEW)
- `core/cluster/hunt_sourcer_config.json` (MODIFY — add tracking section)

**Blocked by:** Phase 1 (needs schema columns)
**After:** Phase 1 (different files than Phase 2, CAN run in parallel with Phase 2)
**Deliverables:**

- [ ] `delivery_tracker.py` — standalone service that queries 17track for items where `tracking_number IS NOT NULL AND delivery_status != 'delivered'`
- [ ] 17track API integration — batch register tracking numbers via POST `/track/v2.2/register` (up to 40 per request), batch query status via POST `/track/v2.2/gettrackinfo`
- [ ] Auto-detect carrier from tracking number (17track does this natively in batch response)
- [ ] Map 17track status codes to our states: `none` → `ordered` → `shipped` → `in_transit` → `out_for_delivery` → `delivered`
- [ ] Update `deal_items` via Lockwood API: PATCH with `delivery_status`, `carrier` (auto-detected), `delivery_updated_at`
- [ ] Rate limiting — 100 API calls/day limit applies to batch endpoints (each call handles up to 40 items). With 4-hour check interval = 6 calls/day = 240 items max. Check only items not yet delivered.
- [ ] Config in `hunt_sourcer_config.json`: add `delivery_tracking` section with `enabled`, `check_interval_hours`, `api_key_env`
- [ ] Deploy to Walter as systemd timer or integrate into existing hunt_sourcer scheduling

**Success Criteria:** Add tracking number to a purchased item, within 4 hours dashboard shows carrier + delivery status automatically.

## Out of Scope (Future)

- Push notifications on delivery status change (Discord webhook later)
- Bulk operations (mark all items in a hunt as received)
- Cost analytics / spending reports across hunts
- Export hunt data to CSV/spreadsheet
- Multi-user hunt sharing
- Automated tracking number extraction from email
- eBay order API integration (not available for buyers)

## Session Log

[Will be updated by /begin]
