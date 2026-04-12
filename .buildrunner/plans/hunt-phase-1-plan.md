# Phase 1: Schema + API Extensions — Plan

## Tasks

1. Add lifecycle columns to `deal_items` in schema + migrations
2. Add completion columns to `active_hunts` in schema + migrations
3. Extend `DealItemUpdate` model with new fields, rename `notes` → `user_notes`
4. Extend `update_deal_item()` allowed fields
5. Add `DELETE /api/deals/items/{item_id}` endpoint
6. Add `POST /api/deals/hunts/{hunt_id}/complete` endpoint
7. Add `GET /api/deals/hunts/archived` endpoint
8. Add `revive_hunt()` and `revive_item()` in intel_collector.py
9. Add `POST /api/deals/hunts/{hunt_id}/revive` endpoint
10. Add `POST /api/deals/items/{item_id}/revive` endpoint
11. Verify all endpoints via curl against Lockwood
