# Phase 1: Collection Infrastructure — Implementation Plan

## Tasks

### Task 1: SQLite Schema (intel_schema.sql)
Create SQL schema with 5 tables: intel_items, deal_items, price_history, model_snapshots, active_hunts. Include indexes.

### Task 2: Intelligence Store (intel_collector.py)
- DB connection helper, table creation
- CRUD for intel_items, deal_items, price_history, model_snapshots, active_hunts
- Webhook payload parsers (miniflux, changedetection, newreleases, f5bot)
- Models API poller (Anthropic /v1/models comparison)
- Package version poller (npm + PyPI)

### Task 3: FastAPI Endpoints (node_intelligence.py)
- Intel CRUD endpoints, alerts endpoint
- Deal CRUD endpoints, hunt management
- Price history endpoint
- 4 webhook endpoints with HMAC verification
- Background cron threads

### Task 4: Tests
- Schema creation, CRUD operations, webhook parsing, API endpoints

## Notes
- Docker installs (Miniflux, changedetection.io) are deployment, not code scope
- Separate DB: ~/.lockwood/intel.db
- Follow memory_store.py patterns
