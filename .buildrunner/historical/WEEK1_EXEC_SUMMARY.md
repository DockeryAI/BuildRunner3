# Week 1 Executive Summary & Prompts

**Status:** Ready to execute
**Duration:** 3 days (16-20 hours total, 5-6 hours wall-clock with parallel execution)
**Goal:** 49% → 72% completion (+23%)

---

## What We're Building

### 4 Parallel Builds (Using Git Worktrees)

1. **Build A: Integration Layer** → Wire telemetry/routing/parallel into orchestrator
2. **Build B: Persistence Layer** → SQLite for costs, event rotation, metrics aggregation
3. **Build C: AI Integration** → Claude API for real complexity estimation
4. **Build D: Documentation** → Fix false claims, add E2E tests

### Expected Results

- **Tests:** 165 → 220+ tests (+55 tests, +33%)
- **Overall Completion:** 49% → 72% (+23%)
- **New Capabilities:**
  - Integrated telemetry (automatic event tracking)
  - Persistent cost tracking (SQLite database)
  - AI-powered complexity estimation (optional)
  - 5 end-to-end test scenarios
  - Accurate documentation

---

## Your Prompts (Copy & Paste These)

### Setup (Run Once)

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Create worktrees
git worktree add /Users/byronhudson/Projects/br3-integration build/integration-layer
git worktree add /Users/byronhudson/Projects/br3-persistence build/persistence-layer
git worktree add /Users/byronhudson/Projects/br3-ai-layer build/ai-integration
git worktree add /Users/byronhudson/Projects/br3-docs-tests build/docs-and-tests

# Install dependencies
for tree in br3-integration br3-persistence br3-ai-layer br3-docs-tests; do
    cd /Users/byronhudson/Projects/$tree
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e /Users/byronhudson/Projects/BuildRunner3
done

# Additional deps
cd /Users/byronhudson/Projects/br3-persistence && source .venv/bin/activate && pip install sqlalchemy alembic
cd /Users/byronhudson/Projects/br3-ai-layer && source .venv/bin/activate && pip install anthropic python-dotenv
```

---

### Prompt A: Integration Layer

**Open:** `cd /Users/byronhudson/Projects/br3-integration && code .`

**Paste this into Claude Code:**

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

### Prompt B: Persistence Layer

**Open:** `cd /Users/byronhudson/Projects/br3-persistence && code .`

**Paste this into Claude Code:**

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

DELIVERABLES:
1. Create core/persistence/ directory with database, models, migrations
2. Modify core/routing/cost_tracker.py to use SQLite
3. Modify core/telemetry/event_collector.py for rotation
4. Create 3 test files: test_persistence.py, test_event_storage.py, test_metrics_db.py
5. Ensure 18+ tests passing

VERIFICATION:
Run: pytest tests/test_persistence.py tests/test_event_storage.py tests/test_metrics_db.py -v
Expected: 18+ tests passing

When complete, report: database schema created, test results, and migration commands.
```

---

### Prompt C: AI Integration

**Open:** `cd /Users/byronhudson/Projects/br3-ai-layer && code .`

**Paste this into Claude Code:**

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

DELIVERABLES:
1. Create core/ai/ directory with claude_client.py, api_config.py, key_manager.py
2. Modify core/routing/complexity_estimator.py to add AI mode
3. Implement core/routing/fallback_handler.py strategies
4. Create .env.example template
5. Create 4 test files with 15+ tests (all mocked, no real API calls)

IMPORTANT: All tests must use mocks - do NOT make real API calls during testing.

VERIFICATION:
Run: pytest tests/test_claude_client.py tests/test_ai_complexity.py tests/test_fallback.py tests/test_key_manager.py -v
Expected: 15+ tests passing (all mocked)

When complete, report: test results, API integration approach, and security measures.
```

---

### Prompt D: Documentation & E2E

**Open:** `cd /Users/byronhudson/Projects/br3-docs-tests && code .`

**Paste this into Claude Code:**

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

DELIVERABLES:
1. Fix SECURITY.md, ROUTING.md, TELEMETRY.md, PARALLEL.md, BUILD_4E_COMPLETE.md
   - Remove "production-ready" claims
   - Remove specific numbers (21.4ms, 85% accuracy, 1000+ events)
   - Add ⚠️ warnings for UI-only features
2. Create docs/QUICKSTART.md, docs/INTEGRATION_GUIDE.md, docs/API_REFERENCE.md
3. Create tests/e2e/test_full_workflow.py with 5 scenarios
4. Update README.md status section

VERIFICATION:
Run: pytest tests/e2e/ -v
Expected: 5+ E2E tests passing

When complete, report: documentation changes summary and E2E test scenarios.
```

---

## Verification Commands (After Each Build)

### Build A Done?
```bash
cd /Users/byronhudson/Projects/br3-integration
source .venv/bin/activate
pytest tests/integration/ -v --cov=core/integrations
# Expected: 20+ tests, 90%+ coverage
```

### Build B Done?
```bash
cd /Users/byronhudson/Projects/br3-persistence
source .venv/bin/activate
pytest tests/test_persistence.py tests/test_event_storage.py tests/test_metrics_db.py -v
# Expected: 18+ tests
```

### Build C Done?
```bash
cd /Users/byronhudson/Projects/br3-ai-layer
source .venv/bin/activate
pytest tests/test_claude_client.py tests/test_ai_complexity.py tests/test_fallback.py tests/test_key_manager.py -v
# Expected: 15+ tests
```

### Build D Done?
```bash
cd /Users/byronhudson/Projects/br3-docs-tests
source .venv/bin/activate
pytest tests/e2e/ -v
# Expected: 5+ tests
```

---

## Merge & Finish (When All Builds Complete)

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Merge in order (IMPORTANT!)
git merge build/docs-and-tests && git commit -m "docs: Update documentation accuracy and add E2E tests"
git merge build/persistence-layer && git commit -m "feat: Add persistence layer"
git merge build/ai-integration && git commit -m "feat: Add Claude API integration"
git merge build/integration-layer && git commit -m "feat: Wire integrations into orchestrator"

# Full test
pytest tests/ -v --cov=core --cov-report=html
# Expected: 220+ tests passing

# Push
git push origin main

# Tag
git tag -a v3.1.0-alpha.4 -m "Week 1: Critical gaps closed - 49% → 72%"
git push origin v3.1.0-alpha.4

# Cleanup
git worktree remove /Users/byronhudson/Projects/br3-integration
git worktree remove /Users/byronhudson/Projects/br3-persistence
git worktree remove /Users/byronhudson/Projects/br3-ai-layer
git worktree remove /Users/byronhudson/Projects/br3-docs-tests
```

---

## Success Criteria Checklist

After Week 1, you should have:

- [ ] 220+ tests passing (up from 165)
- [ ] 72% overall completion (up from 49%)
- [ ] Orchestrator emits telemetry events automatically
- [ ] Cost tracking persisted to SQLite
- [ ] Events rotated and compressed (1MB files)
- [ ] AI complexity estimation available (optional)
- [ ] Documentation accurate (no false claims)
- [ ] 5 E2E test scenarios passing
- [ ] Tagged v3.1.0-alpha.4
- [ ] All worktrees cleaned up

---

## Timeline

- **Day 1 Morning:** Run setup commands (30 min)
- **Day 1 Afternoon:** Kick off Builds A & B (paste prompts)
- **Day 2 Morning:** Kick off Builds C & D (paste prompts)
- **Day 2 Afternoon:** Monitor, verify as builds complete
- **Day 3 Morning:** Verify all builds, fix any issues
- **Day 3 Afternoon:** Merge in order, test, push, tag, cleanup

---

## Next Steps (After Week 1)

Week 2 will focus on:
- Production polish (error handling, logging, performance)
- Original roadmap features (PRD Wizard, Design System)
- Advanced integrations (Git workflows, CLI improvements)
- Performance optimization (caching, async operations)

Target: 72% → 90% completion

---

**READY TO START:**

1. Copy setup commands above
2. Run in terminal
3. Open 4 VS Code windows (one per worktree)
4. Paste prompts A, B, C, D into respective Claude Code sessions
5. Let builds run in parallel
6. Verify as each completes
7. Merge when all done

**Good luck! 🚀**
