# Phase 1 Plan: Data Layer — Schema + Tier + Types

## Health Check Result

All 10 deliverables are already implemented in the codebase. This phase was previously built (likely during the initial intel-innovation-engine development before the BUILD spec was formalized).

## Deliverable Verification

| #   | Deliverable                                                | Status | File                                  |
| --- | ---------------------------------------------------------- | ------ | ------------------------------------- |
| 1   | `type`, `auto_acted`, `auto_act_log` columns in schema     | DONE   | intel_schema.sql:121-123              |
| 2   | ALTER TABLE migration fallback in `_ensure_intel_tables()` | DONE   | intel_collector.py:81-93              |
| 3   | `ImprovementCreate` Pydantic model with `type` field       | DONE   | node_intelligence.py:52               |
| 4   | `create_improvement()` with `type` passthrough             | DONE   | intel_collector.py:829-851            |
| 5   | `compute_tier()` helper                                    | DONE   | intel_collector.py:789-824            |
| 6   | Computed `tier` in GET responses                           | DONE   | node_intelligence.py:162-168, 213-217 |
| 7   | `GET /api/intel/brief` endpoint                            | DONE   | node_intelligence.py:248-293          |
| 8   | `POST /api/intel/improvements/{id}/auto-act` endpoint      | DONE   | node_intelligence.py:296-303          |
| 9   | Nightly Phase 2: Innovation discovery                      | DONE   | collect-intel.sh:30-48                |
| 10  | Nightly Phase 3: Opus type classification                  | DONE   | collect-intel.sh:50-73                |
| 11  | Nightly Phase 4: Auto-act with safety guardrails           | DONE   | collect-intel.sh:75-108               |

## Tier Logic Verification

Item tiers match spec:

- Tier 1: priority=critical AND category=security
- Tier 2: br3_improvement=true AND priority in (critical, high)
- Tier 3: category=new_capability OR type=community-tool
- Tier 4: else

Improvement tiers match spec:

- Tier 1: complexity=simple AND (src_priority=critical OR has_deadline)
- Tier 2: complexity in (simple, medium) AND src_priority in (critical, high)
- Tier 3: type in (new_capability, new_skill, research)
- Tier 4: else

## Tasks

No implementation tasks needed — all deliverables are complete.
