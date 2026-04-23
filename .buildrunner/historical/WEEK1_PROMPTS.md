# Week 1 Build Prompts

**How to use:** Copy each prompt and paste it into a new Claude Code session in the respective worktree.

---

## Build A: Integration Layer

**Worktree:** `/Users/byronhudson/Projects/br3-integration`

### Prompt A

```
You are working on BuildRunner v3.1 Week 1, Build A: Integration Layer.

TASK: Wire telemetry, routing, and parallel systems into the orchestrator.

BUILD PLAN: /Users/byronhudson/Projects/BuildRunner3/.buildrunner/WEEK1_BUILD_PLAN.md
SECTION: Build A (lines 34-169)

EXECUTE TASKS:
1. A.1: Wire Telemetry into Orchestrator (90 min)
2. A.2: Wire Routing into Orchestrator (90 min)
3. A.3: Wire Parallel Coordinator (60 min)
4. A.4: Integration Tests (30 min)

SETUP:
- You're in the br3-integration worktree on branch build/integration-layer
- Virtual environment already created at .venv
- Dependencies installed

DELIVERABLES:
1. Modify core/orchestrator.py to integrate all 3 systems
2. Create core/integrations/ directory with 3 integration modules
3. Create tests/integration/ directory with 4 test files
4. Ensure 20+ integration tests passing
5. No circular imports or errors

VERIFICATION:
Run: pytest tests/integration/ -v --cov=core/integrations
Expected: 20+ tests passing, 90%+ coverage

When complete, report: test results, files created/modified, and any issues encountered.
```

---

## Build B: Persistence Layer

**Worktree:** `/Users/byronhudson/Projects/br3-persistence`

### Prompt B

```
You are working on BuildRunner v3.1 Week 1, Build B: Persistence Layer.

TASK: Add SQLite database for costs, event rotation, and metrics aggregation.

BUILD PLAN: /Users/byronhudson/Projects/BuildRunner3/.buildrunner/WEEK1_BUILD_PLAN.md
SECTION: Build B (lines 171-336)

EXECUTE TASKS:
1. B.1: Cost Tracking Database (90 min) - SQLite + migrations
2. B.2: Event Storage Optimization (90 min) - rotation + compression
3. B.3: Metrics Aggregation (60 min) - pre-aggregate to SQLite
4. B.4: Database Migrations (30 min) - migration system

SETUP:
- You're in the br3-persistence worktree on branch build/persistence-layer
- Virtual environment already created at .venv
- Dependencies installed

DELIVERABLES:
1. Create core/persistence/ directory with database, models, migrations
2. Modify core/routing/cost_tracker.py to use SQLite
3. Modify core/telemetry/event_collector.py for rotation
4. Create 3 test files: test_persistence.py, test_event_storage.py, test_metrics_db.py
5. Ensure 18+ tests passing

DEPENDENCIES TO INSTALL:
pip install sqlalchemy alembic

VERIFICATION:
Run: pytest tests/test_persistence.py tests/test_event_storage.py tests/test_metrics_db.py -v
Expected: 18+ tests passing

When complete, report: database schema created, test results, and migration commands.
```

---

## Build C: AI Integration Layer

**Worktree:** `/Users/byronhudson/Projects/br3-ai-layer`

### Prompt C

```
You are working on BuildRunner v3.1 Week 1, Build C: AI Integration Layer.

TASK: Add Claude API integration for real complexity estimation and model selection.

BUILD PLAN: /Users/byronhudson/Projects/BuildRunner3/.buildrunner/WEEK1_BUILD_PLAN.md
SECTION: Build C (lines 338-502)

EXECUTE TASKS:
1. C.1: Claude API Client (90 min) - core/ai/claude_client.py
2. C.2: Real Complexity Estimation (90 min) - integrate with ComplexityEstimator
3. C.3: Model Fallback Handler (60 min) - implement all strategies
4. C.4: API Key Management (30 min) - secure key loading

SETUP:
- You're in the br3-ai-layer worktree on branch build/ai-integration
- Virtual environment already created at .venv
- Dependencies installed

DELIVERABLES:
1. Create core/ai/ directory with claude_client.py, api_config.py, key_manager.py
2. Modify core/routing/complexity_estimator.py to add AI mode
3. Implement core/routing/fallback_handler.py strategies
4. Create .env.example template
5. Create 4 test files with 15+ tests (all mocked, no real API calls)
6. Ensure all tests passing

DEPENDENCIES TO INSTALL:
pip install anthropic python-dotenv

IMPORTANT: All tests must use mocks - do NOT make real API calls during testing.

VERIFICATION:
Run: pytest tests/test_claude_client.py tests/test_ai_complexity.py tests/test_fallback.py tests/test_key_manager.py -v
Expected: 15+ tests passing (all mocked)

When complete, report: test results, API integration approach, and security measures.
```

---

## Build D: Documentation & E2E Tests

**Worktree:** `/Users/byronhudson/Projects/br3-docs-tests`

### Prompt D

```
You are working on BuildRunner v3.1 Week 1, Build D: Documentation & E2E Tests.

TASK: Fix documentation accuracy and create end-to-end tests.

BUILD PLAN: /Users/byronhudson/Projects/BuildRunner3/.buildrunner/WEEK1_BUILD_PLAN.md
SECTION: Build D (lines 504-652)

EXECUTE TASKS:
1. D.1: Fix Documentation Accuracy (90 min) - remove false claims
2. D.2: Create User Guides (60 min) - QUICKSTART, INTEGRATION_GUIDE, API_REFERENCE
3. D.3: End-to-End Tests (90 min) - 5 comprehensive scenarios
4. D.4: README Updates (30 min) - update status badges

SETUP:
- You're in the br3-docs-tests worktree on branch build/docs-and-tests
- Virtual environment already created at .venv
- Dependencies installed

DELIVERABLES:
1. Fix SECURITY.md, ROUTING.md, TELEMETRY.md, PARALLEL.md, BUILD_4E_COMPLETE.md
   - Remove "production-ready" claims for partial systems
   - Remove specific performance claims (21.4ms, 85% accuracy, 1000+ events)
   - Add ⚠️ warnings for UI-only features
2. Create docs/QUICKSTART.md, docs/INTEGRATION_GUIDE.md, docs/API_REFERENCE.md
3. Create tests/e2e/test_full_workflow.py with 5 scenarios
4. Update README.md status section

DOCUMENTATION FIXES REQUIRED:
- SECURITY.md: Remove "21.4ms" claim, note pattern improvements
- ROUTING.md: Remove "85% accuracy", add "AI optional"
- TELEMETRY.md: Remove "1000+ events", note file-based storage
- PARALLEL.md: Note unit-tested, not production-tested
- BUILD_4E_COMPLETE.md: Update all completion percentages

VERIFICATION:
Run: pytest tests/e2e/ -v
Expected: 5+ E2E tests passing

When complete, report: documentation changes summary and E2E test scenarios.
```

---

## Execution Order

### Day 1 Morning: Setup
```bash
# Run ONCE to create all worktrees
cd /Users/byronhudson/Projects/BuildRunner3
git worktree add /Users/byronhudson/Projects/br3-integration build/integration-layer
git worktree add /Users/byronhudson/Projects/br3-persistence build/persistence-layer
git worktree add /Users/byronhudson/Projects/br3-ai-layer build/ai-integration
git worktree add /Users/byronhudson/Projects/br3-docs-tests build/docs-and-tests

# Install dependencies in each worktree
for tree in br3-integration br3-persistence br3-ai-layer br3-docs-tests; do
    cd /Users/byronhudson/Projects/$tree
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e /Users/byronhudson/Projects/BuildRunner3
done
```

### Day 1 Afternoon: Kick Off Builds A & B (Parallel)

**Terminal 1 - Build A:**
```bash
cd /Users/byronhudson/Projects/br3-integration
code .
# Paste Prompt A into Claude Code
```

**Terminal 2 - Build B:**
```bash
cd /Users/byronhudson/Projects/br3-persistence
code .
# Paste Prompt B into Claude Code
```

### Day 2 Morning: Kick Off Builds C & D (Parallel)

**Terminal 3 - Build C:**
```bash
cd /Users/byronhudson/Projects/br3-ai-layer
code .
# Paste Prompt C into Claude Code
```

**Terminal 4 - Build D:**
```bash
cd /Users/byronhudson/Projects/br3-docs-tests
code .
# Paste Prompt D into Claude Code
```

---

## After Each Build Completes

### Verification Script
```bash
#!/bin/bash
# verify_build.sh

BUILD=$1  # A, B, C, or D
WORKTREE_PATH=$2

cd $WORKTREE_PATH
source .venv/bin/activate

case $BUILD in
    A)
        pytest tests/integration/ -v --cov=core/integrations
        ;;
    B)
        pytest tests/test_persistence.py tests/test_event_storage.py tests/test_metrics_db.py -v
        ;;
    C)
        pytest tests/test_claude_client.py tests/test_ai_complexity.py tests/test_fallback.py tests/test_key_manager.py -v
        ;;
    D)
        pytest tests/e2e/ -v
        ;;
esac
```

### Merge Order (IMPORTANT)
Merge in this specific order to avoid conflicts:

1. **First:** Build D (Documentation - no code conflicts)
2. **Second:** Build B (Persistence - adds new files)
3. **Third:** Build C (AI Integration - modifies routing)
4. **Fourth:** Build A (Integration - modifies orchestrator)

### Merge Commands
```bash
cd /Users/byronhudson/Projects/BuildRunner3

# 1. Merge Build D
git merge build/docs-and-tests
pytest tests/e2e/ -v  # Verify
git push origin main

# 2. Merge Build B
git merge build/persistence-layer
pytest tests/test_persistence.py tests/test_event_storage.py tests/test_metrics_db.py -v
git push origin main

# 3. Merge Build C
git merge build/ai-integration
pytest tests/test_claude_client.py tests/test_ai_complexity.py -v
git push origin main

# 4. Merge Build A
git merge build/integration-layer
pytest tests/integration/ -v
git push origin main

# 5. Final verification
pytest tests/ -v --cov=core
# Expected: 220+ tests passing

# 6. Tag release
git tag -a v3.1.0-alpha.4 -m "Week 1: Critical gaps closed, integrations wired"
git push origin v3.1.0-alpha.4

# 7. Cleanup worktrees
git worktree remove /Users/byronhudson/Projects/br3-integration
git worktree remove /Users/byronhudson/Projects/br3-persistence
git worktree remove /Users/byronhudson/Projects/br3-ai-layer
git worktree remove /Users/byronhudson/Projects/br3-docs-tests
```

---

## Monitoring Script

Save this as `monitor_builds.sh`:

```bash
#!/bin/bash
# monitor_builds.sh - Check build progress

echo "=== Build Status Monitor ==="
echo ""

for BUILD in "A:br3-integration" "B:br3-persistence" "C:br3-ai-layer" "D:br3-docs-tests"; do
    NAME=$(echo $BUILD | cut -d: -f1)
    TREE=$(echo $BUILD | cut -d: -f2)
    PATH="/Users/byronhudson/Projects/$TREE"

    if [ -d "$PATH" ]; then
        echo "Build $NAME ($TREE):"

        cd $PATH
        source .venv/bin/activate 2>/dev/null

        # Count files created
        FILES=$(git diff --name-only main | wc -l)
        echo "  Files modified: $FILES"

        # Count tests
        if [ -d "tests" ]; then
            TESTS=$(grep -r "def test_" tests/ | wc -l)
            echo "  Tests found: $TESTS"
        fi

        # Check if tests pass
        if [ -f "pytest.ini" ] || [ -f "pyproject.toml" ]; then
            pytest --collect-only 2>/dev/null | grep "test session starts" > /dev/null
            if [ $? -eq 0 ]; then
                echo "  Status: ✅ Tests can run"
            else
                echo "  Status: ⏳ In progress"
            fi
        fi

        echo ""
    else
        echo "Build $NAME: ❌ Not started"
        echo ""
    fi
done
```

Run: `bash monitor_builds.sh`

---

**All prompts ready. Follow execution order for parallel development.**
