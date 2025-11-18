# BuildRunner v3.1 - Week 1: Critical Gap Closure

**Week:** 1 of 4
**Goal:** Close critical gaps, wire integrations, add persistence, reach 80%+ completion
**Strategy:** 4 parallel builds using git worktrees
**Estimated Time:** 16-20 hours (4-5 hours per build)

---

## Overview

### Current State
- Task Orchestration: 95% ✅
- Security: 35% (fixed patterns, tests added)
- Routing: 45% (tests added)
- Telemetry: 40% (tests added)
- Parallel: 30% (tests exist)
- **Overall: 49% complete**

### Week 1 Target
- Task Orchestration: 95% ✅ (no change needed)
- Security: 60% (wire to orchestrator)
- Routing: 75% (wire to orchestrator + persistence + AI)
- Telemetry: 70% (wire to orchestrator + persistence)
- Parallel: 60% (wire to orchestrator + real execution)
- **Overall Target: 72% complete**

---

## Build Strategy

### Parallel Builds (4 worktrees)

```
Build A: Integration Layer     (br3-integration)   → 4-5 hours
Build B: Persistence Layer     (br3-persistence)   → 4-5 hours
Build C: AI Integration        (br3-ai-layer)      → 4-5 hours
Build D: Documentation + Tests (br3-docs-tests)    → 3-4 hours
```

**Why Parallel:**
- Builds A, B, C are independent (different files)
- Build D can run after others or in parallel (documentation)
- Total wall-clock time: 5-6 hours (vs 17-19 sequential)

---

## Build A: Integration Layer

**Branch:** `build/integration-layer`
**Worktree:** `/Users/byronhudson/Projects/br3-integration`
**Time:** 4-5 hours
**Status:** ⬜ NOT STARTED

### Goals
1. Wire telemetry collector into orchestrator
2. Wire routing estimator into orchestrator
3. Wire parallel coordinator into orchestrator
4. Add integration tests

### Success Criteria
- [ ] Orchestrator emits telemetry events on task start/complete/fail
- [ ] Orchestrator uses routing for model selection
- [ ] Orchestrator can execute tasks in parallel sessions
- [ ] 15+ integration tests passing
- [ ] No import errors, no circular dependencies

### Tasks

#### A.1: Wire Telemetry into Orchestrator (90 min)
**Files to modify:**
- `core/orchestrator.py` (add EventCollector, emit events)
- `core/batch_optimizer.py` (emit batch events)
- `core/verification_engine.py` (emit verification events)

**Files to create:**
- `core/integrations/__init__.py`
- `core/integrations/telemetry_integration.py` (helper functions)

**Changes:**
```python
# core/orchestrator.py
from core.telemetry import EventCollector, TaskEvent, EventType

class Orchestrator:
    def __init__(...):
        self.event_collector = EventCollector()

    def execute_task(self, task):
        # Emit task started
        self.event_collector.collect(TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id=task.id,
            ...
        ))

        try:
            result = self._run_task(task)
            # Emit task completed
            self.event_collector.collect(TaskEvent(
                event_type=EventType.TASK_COMPLETED,
                success=True,
                ...
            ))
        except Exception as e:
            # Emit task failed
            self.event_collector.collect(TaskEvent(
                event_type=EventType.TASK_FAILED,
                success=False,
                error_message=str(e),
            ))
```

**Tests to create:**
- `tests/integration/test_telemetry_integration.py` (8 tests)

**Verification:**
```bash
pytest tests/integration/test_telemetry_integration.py -v
# Expected: 8/8 passing
```

#### A.2: Wire Routing into Orchestrator (90 min)
**Files to modify:**
- `core/orchestrator.py` (add ComplexityEstimator, ModelSelector)
- `core/task_decomposer.py` (add complexity hints)

**Files to create:**
- `core/integrations/routing_integration.py`

**Changes:**
```python
# core/orchestrator.py
from core.routing import ComplexityEstimator, ModelSelector

class Orchestrator:
    def __init__(...):
        self.estimator = ComplexityEstimator()
        self.selector = ModelSelector()

    def select_model_for_task(self, task):
        complexity = self.estimator.estimate(
            task_description=task.description,
            files=task.files,
        )

        selection = self.selector.select(complexity)
        return selection.model
```

**Tests to create:**
- `tests/integration/test_routing_integration.py` (5 tests)

**Verification:**
```bash
pytest tests/integration/test_routing_integration.py -v
# Expected: 5/5 passing
```

#### A.3: Wire Parallel Coordinator (60 min)
**Files to modify:**
- `core/orchestrator.py` (add session coordination)

**Files to create:**
- `core/integrations/parallel_integration.py`

**Changes:**
```python
# core/orchestrator.py
from core.parallel import SessionManager, WorkerCoordinator

class Orchestrator:
    def __init__(...):
        self.session_manager = SessionManager()
        self.worker_coordinator = WorkerCoordinator()

    def execute_parallel(self, tasks):
        session_id = self.session_manager.create_session(...)
        for task in tasks:
            self.worker_coordinator.assign_task(task.id, task.data, session_id)
```

**Tests to create:**
- `tests/integration/test_parallel_integration.py` (4 tests)

**Verification:**
```bash
pytest tests/integration/test_parallel_integration.py -v
# Expected: 4/4 passing
```

#### A.4: Integration Tests (30 min)
**Files to create:**
- `tests/integration/__init__.py`
- `tests/integration/test_end_to_end.py` (full workflow)

**Tests:** 3 end-to-end scenarios

**Verification:**
```bash
pytest tests/integration/ -v
# Expected: 20+ tests passing
```

### Deliverables
- [ ] 3 integration modules created
- [ ] 4 test files created (20+ tests)
- [ ] All integration tests passing
- [ ] No circular imports
- [ ] Documentation updated

---

## Build B: Persistence Layer

**Branch:** `build/persistence-layer`
**Worktree:** `/Users/byronhudson/Projects/br3-persistence`
**Time:** 4-5 hours
**Status:** ⬜ NOT STARTED

### Goals
1. Add SQLite database for cost tracking
2. Add JSON file persistence for events
3. Add metrics database
4. Add migration system

### Success Criteria
- [ ] Cost entries persisted to SQLite
- [ ] Events persisted to JSON (with rotation)
- [ ] Metrics aggregated and stored
- [ ] Database migrations working
- [ ] 12+ persistence tests passing

### Tasks

#### B.1: Cost Tracking Database (90 min)
**Files to modify:**
- `core/routing/cost_tracker.py` (add SQLite backend)

**Files to create:**
- `core/persistence/__init__.py`
- `core/persistence/database.py` (SQLite wrapper)
- `core/persistence/models.py` (SQLAlchemy models)
- `core/persistence/migrations/001_initial.sql`

**Schema:**
```sql
CREATE TABLE cost_entries (
    id INTEGER PRIMARY KEY,
    timestamp TEXT NOT NULL,
    task_id TEXT,
    model_name TEXT NOT NULL,
    input_tokens INTEGER,
    output_tokens INTEGER,
    cost_usd REAL NOT NULL,
    session_id TEXT
);

CREATE INDEX idx_timestamp ON cost_entries(timestamp);
CREATE INDEX idx_task_id ON cost_entries(task_id);
```

**Changes:**
```python
# core/routing/cost_tracker.py
class CostTracker:
    def __init__(self, db_path=None):
        self.db = Database(db_path or ".buildrunner/costs.db")

    def record_cost(self, entry: CostEntry):
        self.db.insert("cost_entries", entry.to_dict())

    def get_summary(self, start_time=None, end_time=None):
        return self.db.query(
            "SELECT SUM(cost_usd), COUNT(*) FROM cost_entries WHERE ..."
        )
```

**Tests to create:**
- `tests/test_persistence.py` (8 tests)

**Verification:**
```bash
pytest tests/test_persistence.py::TestCostTracking -v
# Expected: 8/8 passing
```

#### B.2: Event Storage Optimization (90 min)
**Files to modify:**
- `core/telemetry/event_collector.py` (add rotation, compression)

**Files to create:**
- `core/persistence/event_storage.py`
- `core/persistence/rotation.py` (log rotation)

**Features:**
- JSON file rotation (1MB max per file)
- Compression of old files (gzip)
- Automatic cleanup (30 days retention)

**Changes:**
```python
# core/telemetry/event_collector.py
class EventCollector:
    def _save(self):
        if self.storage_path.stat().st_size > 1_000_000:  # 1MB
            self._rotate_file()

        with open(self.storage_path, 'w') as f:
            json.dump([e.to_dict() for e in self.events], f)

    def _rotate_file(self):
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        rotated = self.storage_path.with_suffix(f".{timestamp}.json")
        self.storage_path.rename(rotated)

        # Compress old file
        with gzip.open(f"{rotated}.gz", 'wt') as gz:
            with open(rotated) as f:
                gz.write(f.read())
        rotated.unlink()
```

**Tests to create:**
- `tests/test_event_storage.py` (6 tests)

**Verification:**
```bash
pytest tests/test_event_storage.py -v
# Expected: 6/6 passing
```

#### B.3: Metrics Aggregation (60 min)
**Files to create:**
- `core/persistence/metrics_db.py`

**Features:**
- Pre-aggregate metrics (hourly, daily, weekly)
- Store in SQLite for fast queries

**Schema:**
```sql
CREATE TABLE metrics_hourly (
    timestamp TEXT PRIMARY KEY,
    total_tasks INTEGER,
    successful_tasks INTEGER,
    failed_tasks INTEGER,
    total_cost_usd REAL,
    total_tokens INTEGER,
    avg_duration_ms REAL
);
```

**Tests to create:**
- `tests/test_metrics_db.py` (4 tests)

**Verification:**
```bash
pytest tests/test_metrics_db.py -v
# Expected: 4/4 passing
```

#### B.4: Database Migrations (30 min)
**Files to create:**
- `core/persistence/migrate.py`
- `core/persistence/migrations/002_add_indices.sql`

**CLI command:**
```bash
br db migrate  # Run pending migrations
br db rollback # Rollback last migration
```

**Tests:** Schema version tracking

### Deliverables
- [ ] SQLite database for costs
- [ ] Event rotation and compression
- [ ] Metrics aggregation
- [ ] Migration system
- [ ] 18+ tests passing

---

## Build C: AI Integration Layer

**Branch:** `build/ai-integration`
**Worktree:** `/Users/byronhudson/Projects/br3-ai-layer`
**Time:** 4-5 hours
**Status:** ⬜ NOT STARTED

### Goals
1. Add Claude API integration
2. Implement real complexity estimation
3. Add model switching (Haiku → Sonnet → Opus)
4. Add fallback handling

### Success Criteria
- [ ] Complexity estimation uses Claude API
- [ ] Model selection based on real analysis
- [ ] Automatic fallback on errors
- [ ] API key management secure
- [ ] 10+ AI integration tests passing

### Tasks

#### C.1: Claude API Client (90 min)
**Files to create:**
- `core/ai/__init__.py`
- `core/ai/claude_client.py`
- `core/ai/api_config.py`

**Features:**
```python
# core/ai/claude_client.py
class ClaudeClient:
    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.client = Anthropic(api_key=self.api_key)

    def estimate_complexity(
        self,
        task_description: str,
        files: List[Path] = None,
    ) -> ComplexityEstimate:
        """Use Claude to estimate task complexity."""

        prompt = f"""Analyze this task and estimate complexity:

Task: {task_description}
Files: {len(files or [])} files

Provide:
1. Complexity level (simple/moderate/complex/critical)
2. Estimated time (minutes)
3. Recommended model (haiku/sonnet/opus)
4. Reasoning

Format: JSON"""

        response = self.client.messages.create(
            model="claude-haiku-3-5-20241022",
            max_tokens=500,
            messages=[{"role": "user", "content": prompt}]
        )

        return self._parse_response(response.content[0].text)
```

**Tests to create:**
- `tests/test_claude_client.py` (6 tests, mocked)

**Verification:**
```bash
pytest tests/test_claude_client.py -v
# Expected: 6/6 passing (with mocks)
```

#### C.2: Real Complexity Estimation (90 min)
**Files to modify:**
- `core/routing/complexity_estimator.py` (add AI mode)

**Changes:**
```python
# core/routing/complexity_estimator.py
class ComplexityEstimator:
    def __init__(self, use_ai: bool = False):
        self.use_ai = use_ai
        if use_ai:
            self.ai_client = ClaudeClient()

    def estimate(self, task_description: str, files=None) -> TaskComplexity:
        if self.use_ai:
            return self._ai_estimate(task_description, files)
        else:
            return self._heuristic_estimate(task_description, files)

    def _ai_estimate(self, description, files):
        result = self.ai_client.estimate_complexity(description, files)

        return TaskComplexity(
            level=result.level,
            score=result.score,
            reasons=[result.reasoning],
            recommended_model=result.model,
            ...
        )
```

**Tests to create:**
- `tests/test_ai_complexity.py` (5 tests)

**Verification:**
```bash
# With mocks
pytest tests/test_ai_complexity.py -v
# Expected: 5/5 passing

# Real API (optional, requires key)
ANTHROPIC_API_KEY=sk-... pytest tests/test_ai_complexity.py --live -v
```

#### C.3: Model Fallback Handler (60 min)
**Files to modify:**
- `core/routing/fallback_handler.py` (implement strategies)

**Strategies:**
```python
# core/routing/fallback_handler.py
class FallbackHandler:
    def handle_failure(
        self,
        failure: FailureEvent,
        original_model: str,
    ) -> str:
        """Return fallback model based on failure type."""

        if failure.reason == FailureReason.RATE_LIMIT:
            # Wait and retry same model
            time.sleep(failure.retry_after or 60)
            return original_model

        elif failure.reason == FailureReason.CONTEXT_LENGTH:
            # Upgrade to larger context model
            return self._upgrade_model(original_model)

        elif failure.reason == FailureReason.TIMEOUT:
            # Downgrade to faster model
            return self._downgrade_model(original_model)

        else:
            # Generic fallback
            return self._next_available_model(original_model)
```

**Tests to create:**
- `tests/test_fallback.py` (4 tests)

**Verification:**
```bash
pytest tests/test_fallback.py -v
# Expected: 4/4 passing
```

#### C.4: API Key Management (30 min)
**Files to create:**
- `core/ai/key_manager.py`
- `.env.example` (template)

**Features:**
- Load from environment
- Load from `.env` file
- Validate key format
- Mask in logs

**Security:**
```python
# core/ai/key_manager.py
class KeyManager:
    @staticmethod
    def load_api_key() -> str:
        # Try environment first
        key = os.getenv("ANTHROPIC_API_KEY")

        # Try .env file
        if not key and Path(".env").exists():
            from dotenv import load_dotenv
            load_dotenv()
            key = os.getenv("ANTHROPIC_API_KEY")

        # Validate format
        if key and not key.startswith("sk-ant-"):
            raise ValueError("Invalid API key format")

        return key
```

**Tests to create:**
- `tests/test_key_manager.py` (3 tests)

### Deliverables
- [ ] Claude API client
- [ ] AI-powered complexity estimation
- [ ] Fallback strategies
- [ ] Secure key management
- [ ] 18+ tests passing

---

## Build D: Documentation & E2E Tests

**Branch:** `build/docs-and-tests`
**Worktree:** `/Users/byronhudson/Projects/br3-docs-tests`
**Time:** 3-4 hours
**Status:** ⬜ NOT STARTED

### Goals
1. Update documentation accuracy
2. Remove false claims
3. Add end-to-end tests
4. Create user guides

### Success Criteria
- [ ] All documentation reflects reality
- [ ] No false "production-ready" claims
- [ ] 5+ end-to-end tests passing
- [ ] User guides complete

### Tasks

#### D.1: Fix Documentation Accuracy (90 min)
**Files to modify:**
- `SECURITY.md` - Remove "21.4ms" claim, update pattern info
- `ROUTING.md` - Remove "85% accuracy" claim, add "AI optional"
- `TELEMETRY.md` - Remove "1000+ events" claim, note persistence
- `PARALLEL.md` - Note unit-tested only, not production-tested
- `BUILD_4E_COMPLETE.md` - Update completion percentages

**Changes:**
```markdown
# BEFORE:
✅ Production-ready secret detection in 21.4ms
✅ 85%+ accuracy in complexity estimation
✅ Handles 1000+ events efficiently

# AFTER:
✅ Secret detection with realistic pattern matching
⚠️ Complexity estimation (heuristic-based, AI mode optional)
✅ Event collection with file-based storage (rotation available)
```

**Checklist:**
- [ ] Remove all "production-ready" for partial systems
- [ ] Add ⚠️ warnings for UI-only features
- [ ] Update test coverage numbers
- [ ] Add "NOT IMPLEMENTED" sections

#### D.2: Create User Guides (60 min)
**Files to create:**
- `docs/QUICKSTART.md`
- `docs/INTEGRATION_GUIDE.md`
- `docs/API_REFERENCE.md`

**Content:**
```markdown
# QUICKSTART.md
## Installation
pip install -e .

## Basic Usage
from core.orchestrator import Orchestrator

orchestrator = Orchestrator()
orchestrator.run()

## With Telemetry
from core.telemetry import EventCollector

collector = EventCollector()
orchestrator = Orchestrator(event_collector=collector)
```

#### D.3: End-to-End Tests (90 min)
**Files to create:**
- `tests/e2e/__init__.py`
- `tests/e2e/test_full_workflow.py`

**Scenarios:**
1. Spec → Tasks → Execution → Metrics
2. Secret detection in git commit
3. Parallel task execution
4. Cost tracking across session
5. Error recovery and fallback

**Example:**
```python
# tests/e2e/test_full_workflow.py
def test_complete_build_workflow(tmp_path):
    """Test: Spec → Tasks → Execute → Verify → Metrics"""

    # 1. Create spec
    spec_path = tmp_path / "PROJECT_SPEC.md"
    spec_path.write_text("""
    # Feature: User Authentication
    Add login/logout functionality
    """)

    # 2. Parse and decompose
    parser = SpecParser()
    features = parser.parse(spec_path)

    decomposer = TaskDecomposer()
    tasks = decomposer.decompose(features[0])

    # 3. Execute tasks
    orchestrator = Orchestrator()
    results = orchestrator.execute_batch(tasks[:3])

    # 4. Verify results
    assert len(results) == 3
    assert all(r.success for r in results)

    # 5. Check metrics
    assert orchestrator.event_collector.count() > 0
    summary = orchestrator.get_summary()
    assert summary.total_tasks == 3
```

**Tests:** 5 comprehensive scenarios

#### D.4: README Updates (30 min)
**Files to modify:**
- `README.md` - Update status, add warnings

**Changes:**
```markdown
## Status

✅ **Stable** (>90% complete, production-ready)
- Task Orchestration (Build 2A/2B)

⚠️ **Beta** (60-80% complete, functional but needs polish)
- Routing System (75% - AI integration optional)
- Telemetry System (70% - persistence working)

🚧 **Alpha** (40-60% complete, use with caution)
- Security System (60% - patterns working, hooks need testing)
- Parallel System (60% - coordination working, execution needs testing)
```

### Deliverables
- [ ] All docs updated for accuracy
- [ ] User guides created
- [ ] 5+ E2E tests passing
- [ ] README reflects reality

---

## Execution Plan

### Day 1 (Monday) - Setup & Kick Off

**Morning (2 hours):**
```bash
# Create all worktrees
git worktree add /Users/byronhudson/Projects/br3-integration build/integration-layer
git worktree add /Users/byronhudson/Projects/br3-persistence build/persistence-layer
git worktree add /Users/byronhudson/Projects/br3-ai-layer build/ai-integration
git worktree add /Users/byronhudson/Projects/br3-docs-tests build/docs-and-tests

# Install dependencies in each
for tree in br3-integration br3-persistence br3-ai-layer br3-docs-tests; do
    cd /Users/byronhudson/Projects/$tree
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e .
done
```

**Afternoon (4 hours):**
- Kick off Build A (Integration Layer)
- Kick off Build B (Persistence Layer)
- Let Claude work in parallel

### Day 2 (Tuesday) - Build & Test

**Morning (3 hours):**
- Kick off Build C (AI Integration)
- Monitor Builds A & B

**Afternoon (3 hours):**
- Kick off Build D (Documentation)
- Test completed builds
- Fix any issues

### Day 3 (Wednesday) - Review & Merge

**Morning (2 hours):**
- Review all PRs
- Run full test suite
- Check documentation

**Afternoon (2 hours):**
- Merge all builds to main
- Tag v3.1.0-alpha.4
- Clean up worktrees

---

## Testing Strategy

### Per-Build Testing
Each build must pass its own tests before merging:

```bash
# Build A
cd /Users/byronhudson/Projects/br3-integration
pytest tests/integration/ -v --cov=core/integrations
# Expected: 20+ tests, 90%+ coverage

# Build B
cd /Users/byronhudson/Projects/br3-persistence
pytest tests/test_persistence.py tests/test_event_storage.py tests/test_metrics_db.py -v
# Expected: 18+ tests passing

# Build C
cd /Users/byronhudson/Projects/br3-ai-layer
pytest tests/test_claude_client.py tests/test_ai_complexity.py tests/test_fallback.py -v
# Expected: 15+ tests passing

# Build D
cd /Users/byronhudson/Projects/br3-docs-tests
pytest tests/e2e/ -v
# Expected: 5+ tests passing
```

### Integration Testing
After merging, run full suite:

```bash
cd /Users/byronhudson/Projects/BuildRunner3
source .venv/bin/activate
pytest tests/ -v --cov=core --cov-report=html
# Expected: 220+ tests passing (165 current + 55 new)
```

---

## Success Metrics

### Code Metrics
- **Tests:** 165 → 220+ (+55 tests)
- **Coverage:** 95% → 95%+ (maintain)
- **Files Created:** ~25 new files
- **Lines of Code:** +2,500-3,000 lines

### Functionality Metrics
- **Security:** 35% → 60% (+25%)
- **Routing:** 45% → 75% (+30%)
- **Telemetry:** 40% → 70% (+30%)
- **Parallel:** 30% → 60% (+30%)
- **Overall:** 49% → 72% (+23%)

### Quality Metrics
- **Integration:** 0% → 80% (new!)
- **Persistence:** 0% → 75% (new!)
- **AI Integration:** 0% → 70% (new!)
- **Documentation Accuracy:** 40% → 90% (+50%)

---

## Risk Mitigation

### Risk 1: Circular Dependencies
**Mitigation:**
- Import only from lower layers
- Use dependency injection
- Test imports in isolation

### Risk 2: API Key Security
**Mitigation:**
- Never commit .env
- Use .gitignore
- Validate key format
- Mask in logs

### Risk 3: Database Migrations Fail
**Mitigation:**
- Test migrations in tmp directory first
- Keep rollback scripts
- Backup before migrate

### Risk 4: Merge Conflicts
**Mitigation:**
- Each build touches different files
- Merge order: D → B → C → A
- Test after each merge

---

## Completion Checklist

### Build A: Integration Layer
- [ ] Telemetry wired into orchestrator
- [ ] Routing wired into orchestrator
- [ ] Parallel wired into orchestrator
- [ ] 20+ integration tests passing
- [ ] No circular imports
- [ ] PR created and reviewed

### Build B: Persistence Layer
- [ ] SQLite database for costs
- [ ] Event storage with rotation
- [ ] Metrics aggregation
- [ ] Migration system working
- [ ] 18+ tests passing
- [ ] PR created and reviewed

### Build C: AI Integration
- [ ] Claude API client working
- [ ] Real complexity estimation
- [ ] Fallback strategies implemented
- [ ] API key management secure
- [ ] 15+ tests passing
- [ ] PR created and reviewed

### Build D: Documentation
- [ ] All docs updated for accuracy
- [ ] User guides created
- [ ] 5+ E2E tests passing
- [ ] README reflects reality
- [ ] PR created and reviewed

### Final Integration
- [ ] All builds merged to main
- [ ] 220+ tests passing
- [ ] No regressions
- [ ] Coverage ≥95%
- [ ] Tagged v3.1.0-alpha.4
- [ ] Worktrees cleaned up

---

**End of Week 1 Plan**

*Next: Week 2 will focus on production polish, performance optimization, and original roadmap features (PRD Wizard, Design System).*
