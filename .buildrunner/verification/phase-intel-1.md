# Phase 1 Verification: Data Layer — Schema + Tier + Types

## Deliverable Status: ALL COMPLETE (pre-existing)

All 10 deliverables were already implemented before this phase execution began.

### Schema (intel_schema.sql)

- [x] `type TEXT NOT NULL DEFAULT 'fix'` on intel_improvements (line 121)
- [x] `auto_acted INTEGER NOT NULL DEFAULT 0` on intel_improvements (line 122)
- [x] `auto_act_log TEXT` on intel_improvements (line 123)

### Migration (intel_collector.py)

- [x] ALTER TABLE fallback for `type`, `auto_acted`, `auto_act_log` in `_ensure_intel_tables()` (lines 81-93)
- [x] Wrapped in try/except for already-exists safety

### Pydantic Model (node_intelligence.py)

- [x] `ImprovementCreate.type: str = "fix"` (line 52)
- [x] `AutoActLog` model with `log: str` (lines 55-56)

### CRUD (intel_collector.py)

- [x] `create_improvement()` accepts and validates `type` param (lines 829-851)
- [x] `VALID_IMPROVEMENT_TYPES` validation set (line 786)
- [x] `mark_improvement_auto_acted()` function (lines 882-890)

### Tier Classification (intel_collector.py)

- [x] `compute_tier()` implements spec's exact tier logic (lines 789-824)
- [x] Item tiers: security+critical=T1, br3_improvement+high=T2, new_capability=T3, else=T4
- [x] Improvement tiers: simple+critical=T1, simple/medium+high=T2, innovation types=T3, else=T4

### API Endpoints (node_intelligence.py)

- [x] GET `/api/intel/items` adds computed `tier` field (lines 162-168)
- [x] GET `/api/intel/improvements` adds computed `tier` field (lines 213-217)
- [x] GET `/api/intel/brief` returns morning summary with all required fields (lines 248-293)
- [x] POST `/api/intel/improvements/{id}/auto-act` with 404 handling (lines 296-303)

### Nightly Script (collect-intel.sh)

- [x] Phase 1: Collect (existing, lines 13-28)
- [x] Phase 2: Discover — innovation search (lines 30-48)
- [x] Phase 3: Review — Opus type classification (lines 50-73)
- [x] Phase 4: Auto-Act with safety guardrails (lines 75-108)
- [x] Safety: --max-turns 15, read-only audit, no deploys/deletions

## Success Criteria

- [x] `curl /api/intel/brief` returns tier counts
- [x] Improvements have type field
- [x] Existing intel.db migration without data loss (ALTER TABLE fallback)
- [x] Nightly script has 4 phases
