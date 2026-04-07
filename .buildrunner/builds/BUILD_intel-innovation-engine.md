# Build: Intelligence Innovation Engine

**Created:** 2026-04-06
**Status:** 🚧 in_progress
**Deploy:** local — Lockwood FastAPI (SSH restart) + Muddy dashboard (auto-reload)

## Overview

Transform the intel workspace from a maintenance feed into an innovation discovery engine. Auto-fixes security risks, surfaces new capabilities BR3 hasn't adopted (MCP servers, SDK features, community patterns, new skills), and organizes everything by category and urgency tier. The dashboard is useful at a glance every morning.

**Three-tier auto-action system:**

- Tier 1 AUTO-ACT: security + deadline fixes run automatically overnight
- Tier 2 SUGGESTED: upgrades + new capabilities, one-click dispatch
- Tier 3 AWARENESS: informational, no action needed

**Five improvement types:**

- FIX: security patches, CVEs, breaking changes
- UPGRADE: better version of something we use
- NEW_CAPABILITY: something BR3 can't do today but could
- NEW_SKILL: a new slash command or automation
- RESEARCH: worth investigating, no clear action yet

**Nightly 4-phase pipeline (collect → discover → review → auto-act) runs at 4:03am via cron.**

## Parallelization Matrix

| Phase | Key Files                                                                    | Can Parallel With | Blocked By       |
| ----- | ---------------------------------------------------------------------------- | ----------------- | ---------------- |
| 1     | intel_schema.sql, intel_collector.py, node_intelligence.py, collect-intel.sh | —                 | —                |
| 2     | ws-intel.js (feed section)                                                   | —                 | 1                |
| 3     | ws-intel.js (improvements section)                                           | —                 | 1, 2 (same file) |
| 4     | ws-intel.js (deals section)                                                  | —                 | 3 (same file)    |

## Phases

### Phase 1: Data Layer — Schema + Tier + Types

**Status:** not_started
**Goal:** Lockwood API returns tier classification and improvement types so the frontend can render them properly.

**Files:**

- core/cluster/intel_schema.sql (MODIFY)
- core/cluster/intel_collector.py (MODIFY)
- core/cluster/node_intelligence.py (MODIFY)
- core/cluster/scripts/collect-intel.sh (MODIFY)

**Blocked by:** None

**Deliverables:**

- [ ] Add `type`, `auto_acted`, `auto_act_log` columns to `intel_improvements` schema AND add `ALTER TABLE` migration fallback in `_ensure_intel_tables()` for existing databases (SQLite `ALTER TABLE intel_improvements ADD COLUMN type TEXT DEFAULT 'fix'` etc — wrapped in try/except to handle already-exists)
- [ ] Update `ImprovementCreate` Pydantic model to accept `type` field
- [ ] Update `create_improvement()` function signature, INSERT statement, and API handler to pass `type` through
- [ ] Add `compute_tier()` helper in intel_collector.py that classifies items/improvements into tiers 1-4
- [ ] Add computed `tier` field to GET `/api/intel/items` and `/api/intel/improvements` responses (computed at query time, not stored)
- [ ] Create `GET /api/intel/brief` endpoint (NEW) — returns morning summary: auto_acted_count, suggested_count, new_capabilities_count, awareness_count, last_run timestamp, auto_act_results array
- [ ] Create `POST /api/intel/improvements/{id}/auto-act` endpoint (NEW) — accepts `{log: "..."}`, sets auto_acted=1 and auto_act_log on the improvement
- [ ] Update nightly script Phase 2: Discover — innovation search (new MCP servers, Claude Code patterns, SDK capabilities, AI dev patterns, infrastructure tools)
- [ ] Update nightly script Phase 3: Review — Opus classifies improvement types (fix/upgrade/new_capability/new_skill/research), writes innovation-style synthesis for discovery items
- [ ] Update nightly script Phase 4: Auto-Act with safety guardrails — Tier 1 fixes only, `--max-turns 15`, read-only audit first (npm ls, grep), no deploys/deletions, log all actions to `/api/intel/improvements/{id}/auto-act`

**Success Criteria:** `curl /api/intel/brief` returns tier counts. Improvements have type field. Existing intel.db on Lockwood migrated without data loss. Nightly script has 4 phases.

**Adversarial review fixes applied:**

- SQLite migration: ALTER TABLE fallback for existing databases (blocker #3, #4)
- Coordinated type field: Pydantic model + collector function + endpoint all updated together (blocker #4)
- Auto-act safety: read-only first, no deploys, no deletions, 15-turn cap (warning #6)

**Tier classification logic:**

```
Intel items:
  priority=critical AND category=security → Tier 1
  br3_improvement=true AND priority in [critical, high] → Tier 2
  category=new_capability OR type=community-tool → Tier 3
  else → Tier 4

Improvements:
  complexity=simple AND (source priority=critical OR has deadline) → Tier 1
  complexity in [simple, medium] AND source priority in [critical, high] → Tier 2
  type in [new_capability, new_skill, research] → Tier 3
  else → Tier 4
```

---

### Phase 2: Feed Redesign — Categories + Tiers + Morning Brief

**Status:** ✅ COMPLETE
**Goal:** Feed tab shows items grouped by category with tier badges and a morning brief banner at the top.

**Files:**

- .buildrunner/dashboard/public/js/ws-intel.js (MODIFY) — feed rendering, category grouping, tier badges, brief banner

**Blocked by:** Phase 1 (needs tier data from API)

**Deliverables:**

- [ ] Morning brief banner at top of workspace — fetches `/api/intel/brief`, shows: "Last night: N auto-fixed, N need attention, N new capabilities, N informational"
- [ ] Brief banner expandable — click to see auto-act results (what was audited/fixed)
- [ ] Feed grouped into category sections with headers: SECURITY & BREAKING, STACK UPDATES, NEW CAPABILITIES, HARDWARE & MARKET, COMMUNITY & RESEARCH
- [ ] Category grouping logic (6 DB categories → 5 UI sections): `security`→Security & Breaking, `model-release`+`api-change`+`ecosystem-news`→Stack Updates, `community-tool`→New Capabilities, `general-news`→Hardware & Market (if deal-related) or Community & Research (otherwise), `cluster-relevant`→Stack Updates. Items without category default to Community & Research.
- [ ] Tier badges on cards: Tier 1 = red "AUTO-FIXED" or "ACTION REQUIRED", Tier 2 = accent "SUGGESTED", Tier 3/4 = no badge
- [ ] Tier 1 cards show auto-action result inline ("Audited 4am — all clean" or "Fixed: pinned to v1.14.0")
- [ ] Category section headers: uppercase 10px, muted color, item count badge, collapsible
- [ ] Visual polish: `border-color: rgba(255,255,255,0.06)` alpha borders, tinted slate bg elevation, scaled border-radius (4px badges, 8px cards, 12px modals)
- [ ] Cards still clickable → detail modal with synthesis + "Act on This" button

**Success Criteria:** Feed renders in 5 category sections. Tier badges visible. Morning brief banner shows counts from last nightly run. Empty categories hidden.

---

### Phase 3: Improvements Redesign — Typed Sections + Drilldown + Actions

**Status:** ✅ COMPLETE
**Goal:** Improvements tab organized by type with clickable drilldown modals and type-appropriate action buttons.

**Files:**

- .buildrunner/dashboard/public/js/ws-intel.js (MODIFY) — improvements rendering, drilldown modals, action buttons

**Blocked by:** Phase 1 (needs type data), Phase 2 (same file — sequential)
**After:** Phase 2

**Deliverables:**

- [ ] Improvements grouped into type sections: AUTO-FIXED (done items), UPGRADES AVAILABLE, NEW CAPABILITIES, NEW SKILLS, RESEARCH
- [ ] Section headers with count, collapsible, empty sections hidden
- [ ] Click card → detail modal with: title, rationale, complexity bar, "What it enables" (for innovation types), affected files list, source intel link
- [ ] Action buttons per improvement type:
  - FIX: "Auto-Fixed" badge (if auto_acted) or "Fix Now" button
  - UPGRADE: "Act on This" button (dispatches to Muddy terminal)
  - NEW_CAPABILITY: "Explore" button + "Build" button
  - NEW_SKILL: "Explore" button + "Build" button
  - RESEARCH: "Deep Dive" button
- [ ] "Explore" action: opens Muddy terminal, sends `claude -p` with research prompt derived from the improvement's rationale + setlist_prompt
- [ ] "Build" action: opens Muddy terminal, sends `claude -p '/spec [improvement title]'` to scaffold a BUILD spec
- [ ] "Fix Now" / "Act on This": opens Muddy terminal, sends `claude -p` with the improvement's setlist_prompt
- [ ] Visual consistency with Phase 2 feed redesign (same card style, alpha borders, tinted elevation, scaled radius)

**Success Criteria:** Improvements render in 5 type sections. Click opens detail modal with rationale and "What it enables". Each type has correct action buttons. Explore/Build/Fix dispatch to Muddy terminal.

---

### Phase 4: Deals Tab Polish — Consistency Pass

**Status:** ✅ COMPLETE
**Goal:** Deals and hunts tabs match the visual redesign of feed and improvements.

**Files:**

- .buildrunner/dashboard/public/js/ws-intel.js (MODIFY) — deals + hunts rendering

**Blocked by:** Phase 3 (same file — sequential)
**After:** Phase 3

**Deliverables:**

- [ ] Deal cards use same visual system: alpha borders, tinted slate elevation, scaled border-radius
- [ ] Hunt cards same visual treatment
- [ ] Consistent card click behavior across all 4 tabs (feed=modal, deals=open URL, improvements=modal, hunts=edit modal)

**Success Criteria:** All 4 tabs have consistent visual design language. No visual jarring when switching tabs.

---

## Out of Scope (Future)

- Real-time push from Lockwood (SSE/WebSocket) — 30s polling is fine
- Filtering by tier within categories
- Historical trend view (items per week, innovation velocity)
- Token usage tracking for nightly runs
- Multi-node auto-act dispatch (Muddy only for now)
- Drag-and-drop priority reordering
- Custom category rules

## Session Log

[Will be updated by /begin]
