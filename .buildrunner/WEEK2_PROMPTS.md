# Week 2 Build Prompts - Execute in Parallel

## Setup Commands

Run these first to create worktrees:

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Create worktrees for parallel builds
git worktree add ../br3-cli -b build/week2-cli
git worktree add ../br3-api -b build/week2-api
```

---

## Build 2A Prompt - Python CLI Commands

**Worktree:** `/Users/byronhudson/Projects/br3-cli`
**Branch:** `build/week2-cli`
**Duration:** 4-5 hours

### Execution Prompt:

```
You are executing Build 2A of BuildRunner 3.0 in a git worktree.

CONTEXT:
- Working directory: /Users/byronhudson/Projects/br3-cli
- Branch: build/week2-cli
- This is a parallel build; other builds are happening simultaneously
- Week 1 is complete with FeatureRegistry, StatusGenerator, AIContext, and Governance systems

OBJECTIVE:
Implement the Python CLI with automated debugging and behavior configuration features.

CORE TASKS:
1. Setup CLI framework using typer in cli/main.py
2. Implement core commands: init, feature (add/complete/list), status, generate, sync
3. Implement automated debugging commands:
   - `br debug` - diagnostics with auto-retry suggestions
   - `br pipe <command>` - run and auto-pipe output to context
   - `br watch` - start error watcher daemon
4. Implement behavior config system:
   - `br config` commands (init/set/get/list)
   - Create cli/config_manager.py for hierarchy (project > global > defaults)
   - Load from ~/.buildrunner/global-behavior.yaml and .buildrunner/behavior.yaml
5. Create cli/auto_pipe.py - capture stdout/stderr, write to .buildrunner/context/command-outputs.md
6. Create cli/error_watcher.py - daemon to monitor logs, auto-update blockers.md
7. Implement auto-retry logic with exponential backoff (1s, 2s, 4s, 8s, max 3 retries)
8. Add rich formatting for professional output
9. Write comprehensive tests (85%+ coverage):
   - tests/test_cli.py
   - tests/test_config_manager.py
   - tests/test_auto_pipe.py
   - tests/test_error_watcher.py
10. Create documentation:
    - docs/CLI.md
    - docs/AUTOMATED_DEBUGGING.md
    - docs/BEHAVIOR_CONFIG.md
11. Create example configs:
    - docs/examples/global-behavior.yaml
    - docs/examples/project-behavior.yaml

DEPENDENCIES:
- typer
- rich
- watchdog
- pytest
- pyyaml

ACCEPTANCE CRITERIA:
- All commands work end-to-end
- Auto-piping captures outputs correctly to context
- Error watcher detects and logs errors automatically
- Config hierarchy works (project overrides global overrides defaults)
- Auto-retry works for transient failures
- 85%+ test coverage
- All tests pass

COMPLETION SIGNAL:
When all tests pass, commit your work with message:
"feat: Implement CLI with automated debugging and behavior config (Build 2A)"

DO NOT merge to main - this will be done in Build 2C integration.
```

---

## Build 2B Prompt - FastAPI Backend

**Worktree:** `/Users/byronhudson/Projects/br3-api`
**Branch:** `build/week2-api`
**Duration:** 4-5 hours

### Execution Prompt:

```
You are executing Build 2B of BuildRunner 3.0 in a git worktree.

CONTEXT:
- Working directory: /Users/byronhudson/Projects/br3-api
- Branch: build/week2-api
- This is a parallel build; other builds are happening simultaneously
- Week 1 is complete with FeatureRegistry, StatusGenerator, AIContext, and Governance systems

OBJECTIVE:
Implement the FastAPI backend with background test runner, error watcher API, and config management.

CORE TASKS:
1. Setup FastAPI app in api/main.py with CORS and environment config
2. Implement core endpoints:
   - GET /health, GET /features, POST /features, PATCH /features/{id}, DELETE /features/{id}
   - POST /sync, GET /governance, GET /metrics
3. Implement behavior config endpoints:
   - GET /config - merged config (global + project)
   - PATCH /config - update project config
   - GET /config/schema - behavior.yaml schema
4. Implement debugging endpoints:
   - GET /debug/status, GET /debug/blockers, POST /debug/test
   - GET /debug/errors, POST /debug/retry/{command_id}
5. Implement background test runner (api/test_runner.py):
   - POST /test/start, POST /test/stop, GET /test/results
   - WebSocket /test/stream - stream test results live
   - Periodic pytest execution with auto-reporting
6. Implement error watcher API (api/error_watcher.py):
   - Monitor .buildrunner/context/ for errors
   - Auto-categorize (syntax, runtime, test, etc.)
   - Suggest fixes based on error patterns
7. Create Pydantic models (api/models.py):
   - FeatureModel, ConfigModel, ErrorModel, TestResultModel, MetricsModel
8. Create api/config_service.py - load/merge/validate configs
9. Create api/supabase_client.py for Supabase connection
10. Add middleware for request logging to context
11. Write comprehensive tests (85%+ coverage):
    - tests/test_api.py (core endpoints)
    - tests/test_api_config.py
    - tests/test_api_debug.py
    - tests/test_test_runner.py
    - tests/test_error_watcher.py
12. Create documentation:
    - docs/API.md (with OpenAPI schema)
    - docs/API_DEBUGGING.md

DEPENDENCIES:
- fastapi
- uvicorn
- pytest
- httpx
- python-dotenv
- pytest-asyncio
- aiofiles

ACCEPTANCE CRITERIA:
- All endpoints functional
- Background test runner works and streams results
- Error watcher detects and categorizes errors
- Config endpoints return correct merged hierarchy
- OpenAPI docs auto-generated
- WebSocket streaming works
- 85%+ test coverage
- All tests pass

COMPLETION SIGNAL:
When all tests pass, commit your work with message:
"feat: Implement FastAPI backend with test runner and error detection (Build 2B)"

DO NOT merge to main - this will be done in Build 2C integration.
```

---

## Build 2C Prompt - Week 2 Integration + PRD System

**Location:** `/Users/byronhudson/Projects/BuildRunner3` (main branch)
**Duration:** 2-3 hours

### Execution Prompt:

```
You are executing Build 2C of BuildRunner 3.0 - the Week 2 integration build.

CONTEXT:
- Working directory: /Users/byronhudson/Projects/BuildRunner3
- Branch: main
- Builds 2A (CLI) and 2B (API) are complete in parallel worktrees
- You will merge both branches and implement the PRD system

OBJECTIVE:
Merge CLI and API branches, implement PRD system for planning mode, and ensure full integration.

CORE TASKS:
1. Review both branches:
   - `git log build/week2-cli --oneline -10`
   - `git log build/week2-api --oneline -10`
   - `git diff build/week2-cli`
   - `git diff build/week2-api`
2. Merge Build 2A (CLI):
   - `git merge --no-ff build/week2-cli -m "Merge Build 2A: CLI with automated debugging"`
   - Resolve any conflicts
3. Merge Build 2B (API):
   - `git merge --no-ff build/week2-api -m "Merge Build 2B: FastAPI backend with test runner"`
   - Resolve any conflicts
4. Implement PRD System:
   - Create .buildrunner/PRD.md template with 8 sections:
     * Executive Summary, Problem Statement, User Stories
     * Technical Architecture, Success Metrics, Implementation Phases
     * Risk Analysis, Dependencies
   - Create core/prd_parser.py:
     * Parse PRD.md structure, extract features/phases/dependencies
     * Validate completeness
   - Create core/prd_mapper.py:
     * Map PRD sections to features.json
     * Auto-generate feature entries from PRD
     * Bidirectional sync (PRD ↔ features.json)
     * Generate atomic task lists from phases
   - Create CLI commands in cli/prd.py:
     * `br prd init`, `br prd sync`, `br prd validate`, `br prd tasks <phase>`
5. Add planning mode detection (core/planning_mode.py):
   - Detect strategic keywords (architecture, design, approach, strategy)
   - Log planning sessions to .buildrunner/context/planning-notes.md
   - Suggest model switching (Opus for planning, Sonnet for execution)
6. Run integration tests:
   - CLI calls API endpoints end-to-end
   - Test `br init` → API creates project
   - Test PRD sync: PRD.md → features.json
   - Test config hierarchy: global overrides work
   - Test auto-piping: commands write to context
7. Write integration test suite:
   - tests/test_integration_cli_api.py
   - tests/test_integration_prd_sync.py
   - tests/test_integration_config.py
   - tests/test_prd_parser.py
   - tests/test_prd_mapper.py
8. Create documentation:
   - docs/PRD_SYSTEM.md
   - docs/examples/PRD-example.md
9. Run full test suite and verify all pass
10. Tag release: `git tag -a v3.0.0-alpha.2 -m "Week 2 Complete: CLI + API + PRD System"`

ACCEPTANCE CRITERIA:
- Both builds merged cleanly
- No merge conflicts or all conflicts resolved
- PRD.md syncs to features.json correctly
- Planning mode detection works
- Config hierarchy functional across CLI and API
- Auto-piping captures outputs
- All integration tests pass
- Alpha 2 tagged

COMPLETION SIGNAL:
When all tests pass and tag is created, commit with message:
"feat: Complete Week 2 Integration with PRD System (Build 2C)"
```

---

## Execution Instructions

### 1. Create Worktrees
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree add ../br3-cli -b build/week2-cli
git worktree add ../br3-api -b build/week2-api
```

### 2. Execute Builds in Parallel

Open 3 separate Claude Code sessions:

**Session A (Build 2A):**
```bash
cd /Users/byronhudson/Projects/br3-cli
# Paste Build 2A prompt from above
```

**Session B (Build 2B):**
```bash
cd /Users/byronhudson/Projects/br3-api
# Paste Build 2B prompt from above
```

**Session C (Build 2C) - WAIT until 2A and 2B are complete:**
```bash
cd /Users/byronhudson/Projects/BuildRunner3
# Paste Build 2C prompt from above
```

### 3. Cleanup (after successful merge)
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree remove ../br3-cli
git worktree remove ../br3-api
git branch -d build/week2-cli
git branch -d build/week2-api
```

---

## Notes

- Builds 2A and 2B are independent and can run truly in parallel
- Build 2C depends on 2A and 2B completing
- Each build should create comprehensive tests before committing
- Do not push to remote unless explicitly requested
- All builds should reference Week 1 code (FeatureRegistry, Governance, AIContext)
