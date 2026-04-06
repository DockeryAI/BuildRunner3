# Phase 2: Plan Memory — Implementation Plan

## Tasks

### T1: Add plan_outcomes table to memory_store.py
- Add CREATE TABLE in `_ensure_tables()` with all specified columns
- Add `CREATE INDEX idx_plans_project ON plan_outcomes(project)`
- **VERIFY**: Table schema matches spec (all 11 columns)

### T2: Add record_plan_outcome() to memory_store.py
- Insert plan record with all fields, JSON-serialize files_planned/files_actual
- **VERIFY**: Function inserts and retrieves a round-trip record

### T3: Add get_recent_plan_outcomes() to memory_store.py
- Query by project, order by timestamp DESC, configurable limit
- **VERIFY**: Returns recent plans filtered by project

### T4: Add search_similar_plans() to node_semantic.py
- Embed query text using existing CodeRankEmbed model via `_get_embedder()`
- Search a new `plan_outcomes` LanceDB table for similar vectors
- Return top N with outcome, accuracy_pct, drift_notes
- **VERIFY**: Semantic search returns ranked results by similarity

### T5: Add plan embedding pipeline to node_semantic.py
- On plan record, embed plan_text and store in LanceDB `plan_outcomes` table
- Reuse existing `_get_embedder()` for embedding
- **VERIFY**: Embedded plans are retrievable via vector search

### T6: Add API endpoints to node_semantic.py
- `POST /api/plans/record` — accepts plan data, stores in SQLite + embeds in LanceDB
- `GET /api/plans/similar` — query param search, returns top 3 similar plans
- **VERIFY**: Both endpoints respond correctly

## Tests
- Unit tests for record_plan_outcome, get_recent_plan_outcomes
- Integration test for embed + search_similar_plans round-trip
- API endpoint tests for /api/plans/record and /api/plans/similar
