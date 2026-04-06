# Phase 3 Plan: Test Map (Walter)

## Tasks

### 3.1 — Add test_file_map table to _ensure_tables
Add CREATE TABLE for test_file_map (id, project, test_file, source_file, confidence, last_verified) and index idx_testmap_project_source.

### 3.2 — Implement build_test_map(project) function
Scan repo test files for import statements referencing source files and naming conventions (foo.test.ts -> foo.ts). Build source->test mapping, store in test_file_map table.

### 3.3 — Implement get_test_map(files, project) function
Given list of source files and project, query test_file_map and return {source_file: [{test_file, confidence}]} mapping.

### 3.4 — Add GET /api/testmap endpoint
Accept files (comma-separated) and project params. Call get_test_map, return JSON mapping.

### 3.5 — Add POST /api/testmap/baseline endpoint
Accept project and files params. Get test map, run mapped tests, return {test_file: status, duration_ms} baseline.

### 3.6 — Add auto-rebuild on file hash change
During existing poll cycle, invalidate and rebuild affected test_file_map entries when file hashes change.

## Tests
- test_file_map table creation
- build_test_map correctly maps imports and conventions
- get_test_map returns correct mappings
- API endpoints return expected responses
- Auto-rebuild invalidates stale entries
