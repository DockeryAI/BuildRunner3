# Week 2 Executable Prompts - Copy/Paste Ready

Each prompt is fully self-contained with all setup steps included.

---

## PROMPT 1: Build 2A - CLI (4-5 hours)

**Copy/paste this entire prompt into Claude Code:**

```
BUILDRUNNER 3.0 - BUILD 2A: CLI WITH AUTOMATED DEBUGGING

═══════════════════════════════════════════════════════════════════

CONTEXT:
- This is Build 2A of Week 2 (parallel with Build 2B)
- Week 1 is complete: FeatureRegistry, StatusGenerator, AIContext, Governance
- Main project: /Users/byronhudson/Projects/BuildRunner3
- You will work in a separate worktree: /Users/byronhudson/Projects/br3-cli
- Branch: build/week2-cli

═══════════════════════════════════════════════════════════════════

STEP 1: CREATE WORKTREE AND SETUP

Run these commands:

```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree add ../br3-cli -b build/week2-cli
cd ../br3-cli

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install typer rich watchdog pytest pyyaml pytest-cov
```

═══════════════════════════════════════════════════════════════════

STEP 2: IMPLEMENT CLI CORE

Create the following structure and files:

**cli/__init__.py**
```python
"""BuildRunner 3.0 CLI Module"""
```

**cli/main.py**
- Setup typer app with rich formatting
- Implement commands:
  * `br init <project>` - Initialize new BuildRunner project
  * `br feature add <name> --priority <priority> --week <week>` - Add feature
  * `br feature complete <id>` - Mark feature complete
  * `br feature list` - List all features with status
  * `br status` - Show project progress summary
  * `br generate` - Generate STATUS.md from features.json
  * `br sync` - Trigger Supabase sync (stub for now)

Each command should:
- Use FeatureRegistry from core/feature_registry.py
- Use StatusGenerator from core/status_generator.py
- Use AIContextManager from core/ai_context.py
- Handle errors gracefully with rich error formatting
- Return proper exit codes

═══════════════════════════════════════════════════════════════════

STEP 3: IMPLEMENT AUTOMATED DEBUGGING SYSTEM

**cli/auto_pipe.py**
Create CommandPiper class:
- `run_and_pipe(command: str) -> Tuple[int, str, str]`
  * Execute shell command
  * Capture stdout and stderr
  * Write to .buildrunner/context/command-outputs.md with timestamp
  * Format: `## [TIMESTAMP] command\n### stdout\n...\n### stderr\n...`
  * Return exit code, stdout, stderr

**cli/error_watcher.py**
Create ErrorWatcher daemon:
- `start()` - Start background monitoring
- `stop()` - Stop daemon
- `check_for_errors()` - Scan recent command outputs
- Monitor patterns:
  * Python tracebacks (Traceback, File, line, Error)
  * Test failures (FAILED, ERROR, AssertionError)
  * Git errors (fatal:, error:)
  * File not found (No such file)
- Auto-update .buildrunner/context/blockers.md when errors detected
- Categorize errors: syntax, runtime, test, git, file

**cli/retry_logic.py**
Create RetryHandler class:
- `should_retry(error_msg: str) -> bool` - Detect transient errors
  * Network errors (Connection refused, timeout)
  * File locks (Resource temporarily unavailable)
  * Temporary failures (Try again)
- `retry_with_backoff(func, max_retries=3)` - Exponential backoff
  * Wait times: 1s, 2s, 4s, 8s
  * Log each attempt to context
  * Return success or final failure

**cli/debug_commands.py**
Add debug commands to typer app:
- `br debug` - Run full diagnostics:
  * Check Python version, dependencies
  * Check git status, branch
  * Scan recent errors from context
  * Suggest fixes based on error patterns
  * Offer to auto-retry failed commands
- `br pipe <command>` - Run command with auto-piping
  * Execute using CommandPiper
  * Display output with rich formatting
  * Confirm output saved to context
- `br watch` - Start/stop error watcher
  * `br watch start` - Start daemon
  * `br watch stop` - Stop daemon
  * `br watch status` - Show daemon status

═══════════════════════════════════════════════════════════════════

STEP 4: IMPLEMENT BEHAVIOR CONFIG SYSTEM

**cli/config_manager.py**
Create ConfigManager class:
- Load hierarchy: Project > Global > Defaults
- `load_config() -> Dict` - Merge configs:
  * Defaults (hardcoded)
  * Global (~/.buildrunner/global-behavior.yaml)
  * Project (.buildrunner/behavior.yaml)
- `set_config(key: str, value: Any, scope: str)` - Update config
- `get_config(key: str) -> Any` - Get merged value
- `validate_config(config: Dict) -> bool` - Schema validation

Config schema:
```yaml
behavior:
  response_style: "concise" | "detailed" | "technical"
  code_display: "full" | "snippets" | "diffs-only"
  personality: "helpful" | "professional" | "snarky"

context:
  auto_load: true | false
  max_context_size: 50000

automation:
  auto_pipe: true | false
  auto_retry: true | false
  error_watch: true | false
  background_tests: true | false
```

**cli/config_commands.py**
Add config commands:
- `br config init [--global]` - Create config file
  * Global: ~/.buildrunner/global-behavior.yaml
  * Project: .buildrunner/behavior.yaml
  * Use template with defaults
- `br config set <key> <value> [--global]` - Update config
  * Validate key exists in schema
  * Update appropriate file
- `br config get <key>` - Show config value
  * Show merged value
  * Indicate source (default/global/project)
- `br config list` - Show all config
  * Display merged config
  * Highlight overrides

═══════════════════════════════════════════════════════════════════

STEP 5: WRITE COMPREHENSIVE TESTS

Create test files with 85%+ coverage:

**tests/test_cli.py**
Test all core commands:
- test_init_project
- test_feature_add
- test_feature_complete
- test_feature_list
- test_status_display
- test_generate_status
- test_command_help_text

**tests/test_config_manager.py**
Test config hierarchy:
- test_load_default_config
- test_load_global_config
- test_load_project_config
- test_config_hierarchy_override
- test_set_config_global
- test_set_config_project
- test_validate_config_schema

**tests/test_auto_pipe.py**
Test command piping:
- test_run_and_pipe_success
- test_run_and_pipe_failure
- test_output_saved_to_context
- test_timestamp_format
- test_stderr_capture

**tests/test_error_watcher.py**
Test error detection:
- test_detect_python_traceback
- test_detect_test_failure
- test_detect_git_error
- test_categorize_errors
- test_update_blockers_md
- test_daemon_start_stop

**tests/test_retry_logic.py**
Test auto-retry:
- test_should_retry_network_error
- test_should_not_retry_syntax_error
- test_exponential_backoff
- test_max_retries_exceeded
- test_retry_success_on_second_attempt

Run tests:
```bash
pytest tests/ -v --cov=cli --cov-report=term-missing
```

═══════════════════════════════════════════════════════════════════

STEP 6: CREATE DOCUMENTATION

**docs/CLI.md**
Document all commands with examples:
- Installation instructions
- Command reference (all commands with options)
- Usage examples
- Exit codes

**docs/AUTOMATED_DEBUGGING.md**
Document debugging features:
- Auto-piping workflow
- Error watcher setup
- Debug command usage
- Retry logic explanation
- Common error patterns and fixes

**docs/BEHAVIOR_CONFIG.md**
Document config system:
- Config hierarchy explanation
- All config keys and values
- Examples for global and project configs
- Use cases (when to use global vs project)

**docs/examples/global-behavior.yaml**
Example global config:
```yaml
behavior:
  response_style: "concise"
  code_display: "snippets"
  personality: "professional"

context:
  auto_load: true
  max_context_size: 50000

automation:
  auto_pipe: true
  auto_retry: true
  error_watch: true
  background_tests: false
```

**docs/examples/project-behavior.yaml**
Example project override:
```yaml
behavior:
  response_style: "detailed"
  code_display: "full"

automation:
  background_tests: true
```

═══════════════════════════════════════════════════════════════════

STEP 7: FINAL TESTING AND COMMIT

1. Run full test suite:
```bash
pytest tests/ -v --cov=cli --cov-report=term-missing
```

2. Verify 85%+ coverage

3. Test commands manually:
```bash
python -m cli.main --help
python -m cli.main config init
python -m cli.main config list
python -m cli.main pipe "echo test"
```

4. Commit:
```bash
git add .
git commit -m "feat: Implement CLI with automated debugging and behavior config (Build 2A)

Features:
- Core CLI commands: init, feature (add/complete/list), status, generate, sync
- Automated debugging: br debug, br pipe, br watch
- Behavior config system with global/project hierarchy
- Auto-piping command outputs to context
- Error watcher daemon with auto-blocker updates
- Auto-retry logic with exponential backoff
- Rich formatting for professional output

Tests:
- 85%+ coverage across all CLI modules
- Comprehensive test suite for commands, config, piping, errors, retry

Documentation:
- CLI command reference
- Automated debugging guide
- Behavior config guide
- Example configs (global and project)"
```

═══════════════════════════════════════════════════════════════════

ACCEPTANCE CRITERIA CHECKLIST:

□ All core commands work end-to-end
□ Auto-piping captures outputs correctly to context
□ Error watcher detects and logs errors automatically
□ Config hierarchy works (project > global > defaults)
□ Auto-retry works for transient failures
□ Rich formatting looks professional
□ 85%+ test coverage
□ All tests pass
□ Documentation complete
□ Example configs created

═══════════════════════════════════════════════════════════════════

DO NOT MERGE TO MAIN - Wait for Build 2C integration.

When complete, notify that Build 2A is ready for integration.
```

---

## PROMPT 2: Build 2B - FastAPI Backend (4-5 hours)

**Copy/paste this entire prompt into Claude Code:**

```
BUILDRUNNER 3.0 - BUILD 2B: FASTAPI BACKEND WITH TEST RUNNER

═══════════════════════════════════════════════════════════════════

CONTEXT:
- This is Build 2B of Week 2 (parallel with Build 2A)
- Week 1 is complete: FeatureRegistry, StatusGenerator, AIContext, Governance
- Main project: /Users/byronhudson/Projects/BuildRunner3
- You will work in a separate worktree: /Users/byronhudson/Projects/br3-api
- Branch: build/week2-api

═══════════════════════════════════════════════════════════════════

STEP 1: CREATE WORKTREE AND SETUP

Run these commands:

```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree add ../br3-api -b build/week2-api
cd ../br3-api

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install fastapi uvicorn pytest httpx python-dotenv pytest-asyncio aiofiles pyyaml websockets
```

═══════════════════════════════════════════════════════════════════

STEP 2: IMPLEMENT FASTAPI CORE

Create the following structure and files:

**api/__init__.py**
```python
"""BuildRunner 3.0 API Module"""
```

**api/main.py**
Setup FastAPI application:
- Create FastAPI app with metadata (title, version, description)
- Setup CORS middleware (allow all origins for dev)
- Add request logging middleware
- Add error handling middleware
- Include routers for features, config, debug, test

**api/models.py**
Create Pydantic models:

```python
from pydantic import BaseModel
from typing import Optional, List, Dict, Any
from datetime import datetime

class FeatureModel(BaseModel):
    id: str
    name: str
    status: str  # planned, in_progress, complete
    version: str
    priority: str  # critical, high, medium, low
    week: Optional[int]
    build: Optional[str]
    description: str

class ConfigModel(BaseModel):
    source: str  # default, global, project
    config: Dict[str, Any]

class ErrorModel(BaseModel):
    id: str
    timestamp: datetime
    category: str  # syntax, runtime, test, git, file
    message: str
    source: str  # file or command that generated error
    suggested_fix: Optional[str]

class TestResultModel(BaseModel):
    timestamp: datetime
    total: int
    passed: int
    failed: int
    errors: int
    duration: float
    failures: List[Dict[str, str]]

class MetricsModel(BaseModel):
    features_complete: int
    features_in_progress: int
    features_planned: int
    completion_percentage: int
    total_tests: int
    test_pass_rate: float
    active_blockers: int
```

═══════════════════════════════════════════════════════════════════

STEP 3: IMPLEMENT CORE ENDPOINTS

**api/routes/features.py**
Create feature management endpoints:

- `GET /health` - Health check (return status, version, uptime)
- `GET /features` - List all features with optional filter by status
- `GET /features/{id}` - Get single feature by ID
- `POST /features` - Create new feature (accepts FeatureModel)
- `PATCH /features/{id}` - Update feature (status, priority, etc.)
- `DELETE /features/{id}` - Delete feature
- `POST /sync` - Trigger Supabase sync (stub for now)

**api/routes/governance.py**
- `GET /governance` - Get governance rules from governance.yaml
- `GET /governance/dependencies` - Get feature dependencies
- `POST /governance/validate` - Validate feature against rules

**api/routes/metrics.py**
- `GET /metrics` - Get project metrics (features, tests, blockers)
- `GET /metrics/history` - Get historical metrics (stub for now)

All endpoints should:
- Use FeatureRegistry from core/feature_registry.py
- Use GovernanceManager from core/governance.py
- Handle errors with proper HTTP status codes
- Return consistent JSON responses
- Log requests to .buildrunner/context/api-requests.log

═══════════════════════════════════════════════════════════════════

STEP 4: IMPLEMENT CONFIG ENDPOINTS

**api/routes/config.py**
- `GET /config` - Get merged config (global + project)
  * Load both configs
  * Merge with hierarchy
  * Return with source annotations
- `GET /config/global` - Get global config only
- `GET /config/project` - Get project config only
- `PATCH /config/project` - Update project config
  * Validate against schema
  * Write to .buildrunner/behavior.yaml
  * Return updated merged config
- `GET /config/schema` - Get behavior.yaml JSON schema

**api/config_service.py**
Create ConfigService class:
- `load_global_config() -> Dict`
- `load_project_config() -> Dict`
- `merge_configs() -> Dict` - Apply hierarchy
- `validate_config(config: Dict) -> Tuple[bool, List[str]]`
- `save_project_config(config: Dict)`

═══════════════════════════════════════════════════════════════════

STEP 5: IMPLEMENT DEBUGGING ENDPOINTS

**api/routes/debug.py**
- `GET /debug/status` - System health and diagnostics
  * Python version
  * Dependencies installed
  * Git branch and status
  * Disk space
  * .buildrunner/ structure exists
- `GET /debug/blockers` - Current blockers from context/blockers.md
- `POST /debug/test` - Run test suite and return results
  * Execute pytest
  * Parse output
  * Return TestResultModel
- `GET /debug/errors` - Recent errors from error watcher
  * Read from context/
  * Categorize errors
  * Return ErrorModel list
- `POST /debug/retry/{command_id}` - Retry failed command
  * Look up command from context
  * Re-execute with retry logic
  * Return result

**api/error_watcher.py**
Create ErrorWatcherAPI class:
- `scan_context() -> List[ErrorModel]` - Scan context/ for errors
- `categorize_error(error_msg: str) -> str` - Determine category
- `suggest_fix(error: ErrorModel) -> Optional[str]` - Pattern-based suggestions
- Error patterns:
  * ModuleNotFoundError → "Run: pip install <module>"
  * FAILED tests → "Check test file: <file>"
  * Git conflicts → "Run: git status and resolve conflicts"
  * Permission denied → "Run: chmod +x <file>"

═══════════════════════════════════════════════════════════════════

STEP 6: IMPLEMENT BACKGROUND TEST RUNNER

**api/test_runner.py**
Create TestRunner class:

```python
import asyncio
import subprocess
from datetime import datetime
from typing import Optional

class TestRunner:
    def __init__(self):
        self.running = False
        self.task: Optional[asyncio.Task] = None
        self.latest_result: Optional[TestResultModel] = None
        self.interval = 300  # 5 minutes

    async def start(self):
        """Start background testing"""
        if self.running:
            return
        self.running = True
        self.task = asyncio.create_task(self._run_loop())

    async def stop(self):
        """Stop background testing"""
        self.running = False
        if self.task:
            self.task.cancel()

    async def _run_loop(self):
        """Run tests periodically"""
        while self.running:
            self.latest_result = await self.run_tests()
            await asyncio.sleep(self.interval)

    async def run_tests(self) -> TestResultModel:
        """Execute pytest and parse results"""
        # Run: pytest tests/ --json-report
        # Parse output
        # Create TestResultModel
        # Save to .buildrunner/context/test-results.md
        pass
```

**api/routes/test.py**
WebSocket and test endpoints:
- `POST /test/start` - Start background test runner
- `POST /test/stop` - Stop background test runner
- `GET /test/status` - Get runner status (running/stopped)
- `GET /test/results` - Get latest test results
- `POST /test/run` - Run tests immediately (don't wait for interval)
- `WebSocket /test/stream` - Stream test results live
  * Connect to get real-time test output
  * Send JSON messages when tests complete
  * Disconnect to stop streaming

═══════════════════════════════════════════════════════════════════

STEP 7: ADD REQUEST LOGGING MIDDLEWARE

**api/middleware.py**
Create logging middleware:

```python
from fastapi import Request
import time
from datetime import datetime

async def log_requests(request: Request, call_next):
    """Log all requests to context"""
    start_time = time.time()

    response = await call_next(request)

    duration = time.time() - start_time

    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "method": request.method,
        "path": request.url.path,
        "status_code": response.status_code,
        "duration_ms": round(duration * 1000, 2)
    }

    # Append to .buildrunner/context/api-requests.log
    # Flag slow requests (> 1 second)

    return response
```

═══════════════════════════════════════════════════════════════════

STEP 8: CREATE SUPABASE CLIENT STUB

**api/supabase_client.py**
Create Supabase client stub (for future):

```python
from typing import Optional
import os

class SupabaseClient:
    def __init__(self):
        self.url = os.getenv("SUPABASE_URL")
        self.key = os.getenv("SUPABASE_KEY")
        self.connected = False

    async def connect(self):
        """Connect to Supabase (stub)"""
        if not self.url or not self.key:
            raise ValueError("Supabase credentials not configured")
        # TODO: Implement actual connection
        self.connected = True

    async def sync_features(self, features: list):
        """Sync features to Supabase (stub)"""
        if not self.connected:
            await self.connect()
        # TODO: Implement sync
        pass
```

═══════════════════════════════════════════════════════════════════

STEP 9: WRITE COMPREHENSIVE TESTS

Create test files with 85%+ coverage:

**tests/test_api.py**
Test core endpoints:
- test_health_endpoint
- test_get_features
- test_get_feature_by_id
- test_create_feature
- test_update_feature
- test_delete_feature
- test_get_metrics
- test_get_governance

**tests/test_api_config.py**
Test config endpoints:
- test_get_merged_config
- test_get_global_config
- test_get_project_config
- test_update_project_config
- test_config_validation

**tests/test_api_debug.py**
Test debug endpoints:
- test_debug_status
- test_get_blockers
- test_run_tests_endpoint
- test_get_errors
- test_retry_command

**tests/test_test_runner.py**
Test background runner:
- test_start_runner
- test_stop_runner
- test_run_tests
- test_parse_test_output
- test_test_result_model

**tests/test_error_watcher.py**
Test error detection:
- test_scan_context
- test_categorize_error
- test_suggest_fix
- test_error_patterns

**tests/test_config_service.py**
Test config service:
- test_load_configs
- test_merge_hierarchy
- test_validate_config
- test_save_project_config

Run tests:
```bash
pytest tests/ -v --cov=api --cov-report=term-missing
```

═══════════════════════════════════════════════════════════════════

STEP 10: CREATE DOCUMENTATION

**docs/API.md**
Complete API documentation:
- Installation and setup
- Running the server (uvicorn)
- All endpoints with examples (curl and Python)
- Request/response schemas
- Error codes
- OpenAPI schema URL (/docs)

**docs/API_DEBUGGING.md**
Document debugging features:
- Debug endpoints usage
- Background test runner setup
- Error watcher functionality
- WebSocket streaming
- Common error patterns and fixes

═══════════════════════════════════════════════════════════════════

STEP 11: FINAL TESTING AND COMMIT

1. Run full test suite:
```bash
pytest tests/ -v --cov=api --cov-report=term-missing
```

2. Verify 85%+ coverage

3. Start server and test manually:
```bash
uvicorn api.main:app --reload
```

Visit http://localhost:8000/docs for OpenAPI UI

4. Test key endpoints:
```bash
curl http://localhost:8000/health
curl http://localhost:8000/features
curl http://localhost:8000/config
curl http://localhost:8000/debug/status
```

5. Commit:
```bash
git add .
git commit -m "feat: Implement FastAPI backend with test runner and error detection (Build 2B)

Features:
- Core endpoints: features, governance, metrics
- Config endpoints with hierarchy (global/project)
- Debug endpoints: status, blockers, errors, retry
- Background test runner with WebSocket streaming
- Error watcher API with categorization and fix suggestions
- Request logging middleware
- Supabase client stub

Tests:
- 85%+ coverage across all API modules
- Comprehensive test suite for endpoints, config, debug, test runner, errors

Documentation:
- Complete API reference with examples
- API debugging guide
- OpenAPI schema auto-generated"
```

═══════════════════════════════════════════════════════════════════

ACCEPTANCE CRITERIA CHECKLIST:

□ All core endpoints functional
□ Background test runner works and streams results
□ Error watcher detects and categorizes errors
□ Config endpoints return correct merged hierarchy
□ OpenAPI docs auto-generated at /docs
□ WebSocket streaming works
□ Request logging captures all API calls
□ 85%+ test coverage
□ All tests pass
□ Documentation complete

═══════════════════════════════════════════════════════════════════

DO NOT MERGE TO MAIN - Wait for Build 2C integration.

When complete, notify that Build 2B is ready for integration.
```

---

## PROMPT 3: Build 2C - Integration + PRD System (2-3 hours)

**WAIT FOR BUILDS 2A AND 2B TO COMPLETE BEFORE RUNNING THIS**

**Copy/paste this entire prompt into Claude Code:**

```
BUILDRUNNER 3.0 - BUILD 2C: WEEK 2 INTEGRATION + PRD SYSTEM

═══════════════════════════════════════════════════════════════════

CONTEXT:
- This is Build 2C - the Week 2 integration build
- Builds 2A (CLI) and 2B (API) are COMPLETE in their worktrees
- You will work in the main branch
- You will merge both branches and implement the PRD system
- Main project: /Users/byronhudson/Projects/BuildRunner3

═══════════════════════════════════════════════════════════════════

STEP 1: VERIFY BUILDS 2A AND 2B ARE COMPLETE

Run these commands:

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Check worktrees exist
git worktree list

# Check both branches have commits
git log build/week2-cli --oneline -5
git log build/week2-api --oneline -5

# If either branch has no commits, STOP and complete that build first
```

═══════════════════════════════════════════════════════════════════

STEP 2: REVIEW CHANGES FROM BOTH BRANCHES

Review what will be merged:

```bash
# Review CLI changes
echo "=== BUILD 2A (CLI) CHANGES ==="
git diff main...build/week2-cli --stat
git log main..build/week2-cli --oneline

# Review API changes
echo "=== BUILD 2B (API) CHANGES ==="
git diff main...build/week2-api --stat
git log main..build/week2-api --oneline

# Check for potential conflicts
git merge-tree $(git merge-base main build/week2-cli) main build/week2-cli
git merge-tree $(git merge-base main build/week2-api) main build/week2-api
```

═══════════════════════════════════════════════════════════════════

STEP 3: MERGE BUILD 2A (CLI)

```bash
git merge --no-ff build/week2-cli -m "Merge Build 2A: CLI with automated debugging and behavior config

Features:
- Core CLI commands (init, feature, status, generate, sync)
- Automated debugging (debug, pipe, watch)
- Behavior config system with global/project hierarchy
- Auto-piping, error watcher, auto-retry
- Rich formatting
- 85%+ test coverage"
```

If conflicts occur:
1. Review conflict files: `git status`
2. Resolve conflicts manually
3. Stage resolved files: `git add <file>`
4. Complete merge: `git commit`

═══════════════════════════════════════════════════════════════════

STEP 4: MERGE BUILD 2B (API)

```bash
git merge --no-ff build/week2-api -m "Merge Build 2B: FastAPI backend with test runner and error detection

Features:
- Core API endpoints (features, governance, metrics)
- Config endpoints with hierarchy
- Debug endpoints (status, blockers, errors, retry)
- Background test runner with WebSocket streaming
- Error watcher API
- Request logging middleware
- 85%+ test coverage"
```

If conflicts occur:
1. Review conflict files (likely in core/__init__.py, tests/)
2. Resolve by combining imports and exports from both builds
3. Stage and commit

═══════════════════════════════════════════════════════════════════

STEP 5: RUN INTEGRATION TESTS

Test that CLI and API work together:

```bash
# Install any missing dependencies
source .venv/bin/activate
pip install typer rich watchdog fastapi uvicorn websockets

# Run all tests
pytest tests/ -v --cov=core --cov=cli --cov=api --cov-report=term-missing

# Expected: All previous tests pass (from Week 1 + 2A + 2B)
```

If tests fail:
1. Review failures
2. Fix integration issues (imports, paths, etc.)
3. Re-run tests
4. Commit fixes

═══════════════════════════════════════════════════════════════════

STEP 6: IMPLEMENT PRD SYSTEM

**Create .buildrunner/PRD.md template:**

```markdown
# Product Requirements Document

## Executive Summary
Brief overview of the project goals and vision.

## Problem Statement
What problem does this project solve?

## User Stories
- As a [user type], I want [goal] so that [benefit]
- ...

## Technical Architecture
High-level architecture design, tech stack, and key components.

## Success Metrics
How will we measure success?
- Metric 1: [description]
- Metric 2: [description]

## Implementation Phases
### Phase 1: [Name]
**Duration:** X weeks
**Features:**
- Feature 1
- Feature 2

### Phase 2: [Name]
...

## Risk Analysis
| Risk | Impact | Mitigation |
|------|--------|------------|
| Risk 1 | High | Mitigation strategy |

## Dependencies
- External dependency 1
- External dependency 2
```

**core/prd_parser.py**
Create PRDParser class:

```python
from typing import Dict, List, Optional
import re
from pathlib import Path

class PRDParser:
    def __init__(self, prd_path: str = ".buildrunner/PRD.md"):
        self.prd_path = Path(prd_path)

    def parse(self) -> Dict:
        """Parse PRD.md and extract structured data"""
        if not self.prd_path.exists():
            raise FileNotFoundError(f"PRD not found: {self.prd_path}")

        content = self.prd_path.read_text()

        return {
            "executive_summary": self._extract_section(content, "Executive Summary"),
            "problem_statement": self._extract_section(content, "Problem Statement"),
            "user_stories": self._extract_user_stories(content),
            "technical_architecture": self._extract_section(content, "Technical Architecture"),
            "success_metrics": self._extract_metrics(content),
            "phases": self._extract_phases(content),
            "risks": self._extract_risks(content),
            "dependencies": self._extract_dependencies(content)
        }

    def validate(self) -> Tuple[bool, List[str]]:
        """Validate PRD completeness"""
        # Check all required sections exist
        # Return (is_valid, [list of missing sections])
        pass

    def _extract_section(self, content: str, section_name: str) -> str:
        """Extract content between section headers"""
        pass

    def _extract_user_stories(self, content: str) -> List[str]:
        """Extract user stories (lines starting with "- As a")"""
        pass

    def _extract_phases(self, content: str) -> List[Dict]:
        """Extract implementation phases with features"""
        pass

    def _extract_metrics(self, content: str) -> List[Dict]:
        """Extract success metrics"""
        pass

    def _extract_risks(self, content: str) -> List[Dict]:
        """Extract risk analysis table"""
        pass

    def _extract_dependencies(self, content: str) -> List[str]:
        """Extract external dependencies"""
        pass
```

**core/prd_mapper.py**
Create PRDMapper class:

```python
from core.prd_parser import PRDParser
from core.feature_registry import FeatureRegistry
from typing import Dict, List

class PRDMapper:
    def __init__(self):
        self.parser = PRDParser()
        self.registry = FeatureRegistry()

    def sync_prd_to_features(self) -> Dict:
        """Sync PRD.md to features.json"""
        prd_data = self.parser.parse()

        # For each phase in PRD
        for phase in prd_data["phases"]:
            # For each feature in phase
            for feature in phase["features"]:
                # Check if feature exists in registry
                # If not, create it
                # If exists, update it
                feature_id = self._generate_feature_id(feature)

                if not self.registry.get_feature(feature_id):
                    self.registry.add_feature(
                        feature_id=feature_id,
                        name=feature,
                        description=f"From PRD Phase: {phase['name']}",
                        priority="medium",
                        week=phase.get("week"),
                        build=phase.get("build")
                    )

        self.registry.save()
        return {"synced": True, "features_updated": len(features)}

    def sync_features_to_prd(self):
        """Sync features.json back to PRD.md (bidirectional)"""
        # Read current features
        # Update PRD phases to match features.json
        # Preserve PRD narrative content
        pass

    def generate_task_list(self, phase_name: str) -> List[str]:
        """Generate atomic task list from phase"""
        prd_data = self.parser.parse()

        phase = next((p for p in prd_data["phases"] if p["name"] == phase_name), None)
        if not phase:
            raise ValueError(f"Phase not found: {phase_name}")

        tasks = []
        for feature in phase["features"]:
            # Break down feature into atomic tasks
            tasks.extend([
                f"Implement {feature}",
                f"Write tests for {feature}",
                f"Document {feature}",
                f"Review {feature}"
            ])

        return tasks

    def _generate_feature_id(self, feature_name: str) -> str:
        """Generate feature ID from name"""
        return feature_name.lower().replace(" ", "-")
```

**Create CLI commands (cli/prd_commands.py):**

```python
import typer
from core.prd_parser import PRDParser
from core.prd_mapper import PRDMapper
from pathlib import Path
from rich.console import Console

app = typer.Typer()
console = Console()

@app.command()
def init():
    """Create PRD.md from template"""
    # Copy template to .buildrunner/PRD.md
    # Prompt for project name, update template
    pass

@app.command()
def sync():
    """Sync PRD.md to features.json"""
    mapper = PRDMapper()
    result = mapper.sync_prd_to_features()
    console.print(f"[green]✓ Synced {result['features_updated']} features")

@app.command()
def validate():
    """Validate PRD completeness"""
    parser = PRDParser()
    is_valid, missing = parser.validate()
    if is_valid:
        console.print("[green]✓ PRD is complete")
    else:
        console.print("[red]✗ PRD incomplete. Missing:")
        for section in missing:
            console.print(f"  - {section}")

@app.command()
def tasks(phase: str):
    """Generate atomic task list for phase"""
    mapper = PRDMapper()
    tasks = mapper.generate_task_list(phase)
    console.print(f"[bold]Tasks for {phase}:[/bold]")
    for i, task in enumerate(tasks, 1):
        console.print(f"{i}. {task}")
```

Add to main CLI (cli/main.py):
```python
from cli.prd_commands import app as prd_app
app.add_typer(prd_app, name="prd")
```

═══════════════════════════════════════════════════════════════════

STEP 7: IMPLEMENT PLANNING MODE DETECTION (EXPERIMENTAL)

**core/planning_mode.py**

```python
from typing import List, Tuple
from datetime import datetime
from pathlib import Path

class PlanningModeDetector:
    """Detect when user enters planning/strategy mode"""

    STRATEGIC_KEYWORDS = [
        "architecture", "design", "approach", "strategy",
        "plan", "planning", "should we", "what if",
        "brainstorm", "alternatives", "pros and cons",
        "trade-offs", "which is better"
    ]

    def __init__(self):
        self.planning_notes_file = Path(".buildrunner/context/planning-notes.md")

    def detect(self, user_input: str) -> Tuple[bool, float]:
        """
        Detect if input suggests planning mode
        Returns: (is_planning, confidence_score)
        """
        user_lower = user_input.lower()

        keyword_count = sum(1 for kw in self.STRATEGIC_KEYWORDS if kw in user_lower)
        confidence = min(keyword_count / 3.0, 1.0)  # Cap at 1.0

        is_planning = confidence > 0.3

        return (is_planning, confidence)

    def suggest_model_switch(self, confidence: float) -> str:
        """Suggest model based on confidence"""
        if confidence > 0.7:
            return "opus"  # Complex planning
        elif confidence > 0.4:
            return "sonnet"  # Moderate planning
        else:
            return "haiku"  # Execution

    def log_planning_session(self, topic: str, notes: str):
        """Log planning session to context"""
        self.planning_notes_file.parent.mkdir(parents=True, exist_ok=True)

        with open(self.planning_notes_file, "a") as f:
            f.write(f"\n## {datetime.now().isoformat()} - {topic}\n\n")
            f.write(notes)
            f.write("\n\n---\n")
```

Note: Actual model switching will be implemented in Week 3 with MCP integration.

═══════════════════════════════════════════════════════════════════

STEP 8: WRITE INTEGRATION TESTS

**tests/test_integration_cli_api.py**
Test CLI calling API:
- test_cli_calls_api_health
- test_cli_feature_add_creates_via_api
- test_cli_status_fetches_from_api
- test_cli_config_syncs_with_api

**tests/test_integration_prd_sync.py**
Test PRD sync:
- test_prd_to_features_sync
- test_features_to_prd_sync
- test_task_generation_from_phase
- test_prd_validation

**tests/test_integration_config.py**
Test config hierarchy:
- test_global_config_loads
- test_project_overrides_global
- test_cli_and_api_see_same_config

**tests/test_prd_parser.py**
Test PRD parsing:
- test_parse_prd_sections
- test_extract_user_stories
- test_extract_phases
- test_validate_completeness

**tests/test_prd_mapper.py**
Test PRD mapping:
- test_generate_features_from_prd
- test_generate_task_list
- test_feature_id_generation

**tests/test_planning_mode.py**
Test planning detection:
- test_detect_planning_keywords
- test_confidence_scoring
- test_model_suggestion
- test_log_planning_session

Run tests:
```bash
pytest tests/ -v --cov --cov-report=term-missing
```

═══════════════════════════════════════════════════════════════════

STEP 9: CREATE DOCUMENTATION

**docs/PRD_SYSTEM.md**
Document PRD system:
- What is the PRD system
- How to create a PRD (br prd init)
- How to sync PRD ↔ features.json
- Task generation from phases
- Best practices for writing PRDs
- Example workflow

**docs/examples/PRD-example.md**
Complete example PRD for a sample project

═══════════════════════════════════════════════════════════════════

STEP 10: FINAL TESTING AND TAGGING

1. Run complete test suite:
```bash
pytest tests/ -v --cov --cov-report=term-missing --cov-report=html
```

2. Manually test CLI:
```bash
python -m cli.main prd init
python -m cli.main prd validate
python -m cli.main prd sync
python -m cli.main config list
python -m cli.main feature list
```

3. Manually test API:
```bash
# In one terminal
uvicorn api.main:app --reload

# In another
curl http://localhost:8000/health
curl http://localhost:8000/features
curl http://localhost:8000/config
```

4. Commit integration work:
```bash
git add .
git commit -m "feat: Complete Week 2 Integration with PRD System (Build 2C)

Integration:
- Merged Build 2A (CLI) successfully
- Merged Build 2B (API) successfully
- All integration tests passing

PRD System:
- PRD.md template with 8 sections
- PRD parser for extracting structured data
- PRD mapper for bidirectional sync with features.json
- Atomic task list generation from phases
- CLI commands: prd init, sync, validate, tasks

Planning Mode (Experimental):
- Keyword-based planning mode detection
- Model switching suggestions
- Planning session logging to context

Tests:
- Integration test suite (CLI ↔ API)
- PRD system tests
- Planning mode tests
- All 99+ tests passing

Documentation:
- PRD system guide
- Example PRD
- Updated API and CLI docs"
```

5. Tag release:
```bash
git tag -a v3.0.0-alpha.2 -m "BuildRunner 3.0 Alpha 2 Release

Week 2 Complete: CLI + API + PRD System

New Features:
- Python CLI with automated debugging
  * Auto-piping command outputs to context
  * Error watcher daemon
  * Auto-retry logic with exponential backoff
  * Behavior config system (global/project hierarchy)
- FastAPI backend with real-time features
  * Background test runner
  * Error detection and categorization
  * WebSocket streaming
  * Config management API
- PRD System
  * PRD ↔ features.json bidirectional sync
  * Atomic task generation
  * Planning mode detection

Stats:
- 150+ tests passing
- 85%+ coverage across CLI and API
- 20+ new commands
- 15+ API endpoints

Ready for Week 3: Git hooks, MCP integration, slash commands"
```

═══════════════════════════════════════════════════════════════════

STEP 11: CLEANUP WORKTREES

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Remove worktrees
git worktree remove ../br3-cli
git worktree remove ../br3-api

# Delete branches (they're merged)
git branch -d build/week2-cli
git branch -d build/week2-api

# Verify clean state
git worktree list
git branch -a
```

═══════════════════════════════════════════════════════════════════

ACCEPTANCE CRITERIA CHECKLIST:

□ Build 2A merged successfully (no conflicts)
□ Build 2B merged successfully (no conflicts)
□ All previous tests still pass
□ PRD.md template created
□ PRD parser extracts all sections
□ PRD mapper syncs to features.json
□ CLI prd commands work (init, sync, validate, tasks)
□ Planning mode detection works
□ Integration tests pass
□ All documentation complete
□ v3.0.0-alpha.2 tagged
□ Worktrees cleaned up

═══════════════════════════════════════════════════════════════════

When complete, Week 2 is DONE. Ready for Week 3: Git hooks and MCP.
```

---

## Execution Summary

**These prompts are 100% self-contained. Copy/paste and go.**

1. **Prompt 1** - Creates worktree, installs deps, implements CLI (4-5 hours)
2. **Prompt 2** - Creates worktree, installs deps, implements API (4-5 hours)
3. **Prompt 3** - Merges both, implements PRD system, tags release (2-3 hours)

Each prompt includes:
- All setup commands (worktrees, venv, pip installs)
- Complete implementation instructions
- Test requirements
- Documentation requirements
- Commit messages
- Acceptance criteria checklists

No external context needed. Just paste and execute.
