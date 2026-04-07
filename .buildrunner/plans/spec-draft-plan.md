# Intel Innovation Engine — Draft Plan

## Phase 1: Data Layer
- Add `type` column to intel_improvements (fix/upgrade/new_capability/new_skill/research)
- Add `auto_acted` + `auto_act_log` columns to intel_improvements
- Computed `tier` in API responses (1-4 based on priority+complexity+category)
- GET /api/intel/brief endpoint — morning summary
- POST /api/intel/improvements accepts type field
- POST /api/intel/improvements/{id}/auto-act — records auto-action
- Update nightly script: 4 phases (collect, discover, review, auto-act)
- Files: core/cluster/intel_schema.sql, core/cluster/intel_collector.py, core/cluster/node_intelligence.py, core/cluster/scripts/collect-intel.sh

## Phase 2: Feed Redesign
- Morning brief banner (fetches /api/intel/brief)
- Feed grouped into 5 category sections
- Tier badges on cards
- Auto-action results shown on Tier 1 cards
- Visual polish (alpha borders, tinted elevation, scaled radius)
- Files: .buildrunner/dashboard/public/js/ws-intel.js

## Phase 3: Improvements Redesign
- Improvements grouped by type (5 sections)
- Click card → detail modal with rationale, complexity, "what it enables"
- Action buttons per type: Fix Now, Act on This, Explore, Build, Deep Dive
- Explore/Build dispatch to Muddy terminal via claude -p
- Files: .buildrunner/dashboard/public/js/ws-intel.js

## Phase 4: Deals Polish
- Visual consistency pass across deals + hunts tabs
- Same card system as feed/improvements
- Files: .buildrunner/dashboard/public/js/ws-intel.js
