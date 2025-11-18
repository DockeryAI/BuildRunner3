# Week 1 Quick Start Guide

**Goal:** Close critical gaps, get to 72% completion
**Time:** 3 days (Mon-Wed)
**Builds:** 4 parallel builds using git worktrees

---

## Step 1: Initial Setup (5 minutes)

Run these commands once:

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# Create all 4 worktrees
git worktree add /Users/byronhudson/Projects/br3-integration build/integration-layer
git worktree add /Users/byronhudson/Projects/br3-persistence build/persistence-layer
git worktree add /Users/byronhudson/Projects/br3-ai-layer build/ai-integration
git worktree add /Users/byronhudson/Projects/br3-docs-tests build/docs-and-tests

# Install dependencies in each
for tree in br3-integration br3-persistence br3-ai-layer br3-docs-tests; do
    cd /Users/byronhudson/Projects/$tree
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -e /Users/byronhudson/Projects/BuildRunner3
done

# Install additional deps
cd /Users/byronhudson/Projects/br3-persistence && source .venv/bin/activate && pip install sqlalchemy alembic
cd /Users/byronhudson/Projects/br3-ai-layer && source .venv/bin/activate && pip install anthropic python-dotenv
```

---

## Step 2: Kick Off Builds (Day 1)

### Open 4 terminal windows:

**Terminal 1 - Build A (Integration):**
```bash
cd /Users/byronhudson/Projects/br3-integration
code .
```
Then paste **Prompt A** from `.buildrunner/WEEK1_PROMPTS.md`

**Terminal 2 - Build B (Persistence):**
```bash
cd /Users/byronhudson/Projects/br3-persistence
code .
```
Then paste **Prompt B** from `.buildrunner/WEEK1_PROMPTS.md`

**Terminal 3 - Build C (AI Integration):**
```bash
cd /Users/byronhudson/Projects/br3-ai-layer
code .
```
Then paste **Prompt C** from `.buildrunner/WEEK1_PROMPTS.md`

**Terminal 4 - Build D (Documentation):**
```bash
cd /Users/byronhudson/Projects/br3-docs-tests
code .
```
Then paste **Prompt D** from `.buildrunner/WEEK1_PROMPTS.md`

---

## Step 3: Monitor Progress

Run this script to check build status:

```bash
# From main project directory
cd /Users/byronhudson/Projects/BuildRunner3

# Check each build
for tree in br3-integration br3-persistence br3-ai-layer br3-docs-tests; do
    echo "=== $tree ==="
    cd /Users/byronhudson/Projects/$tree
    git status --short
    echo ""
done
```

---

## Step 4: Verify Builds (As They Complete)

When Claude reports a build is complete:

### Build A Verification:
```bash
cd /Users/byronhudson/Projects/br3-integration
source .venv/bin/activate
pytest tests/integration/ -v --cov=core/integrations
# Expected: 20+ tests passing, 90%+ coverage
```

### Build B Verification:
```bash
cd /Users/byronhudson/Projects/br3-persistence
source .venv/bin/activate
pytest tests/test_persistence.py tests/test_event_storage.py tests/test_metrics_db.py -v
# Expected: 18+ tests passing
```

### Build C Verification:
```bash
cd /Users/byronhudson/Projects/br3-ai-layer
source .venv/bin/activate
pytest tests/test_claude_client.py tests/test_ai_complexity.py tests/test_fallback.py tests/test_key_manager.py -v
# Expected: 15+ tests passing
```

### Build D Verification:
```bash
cd /Users/byronhudson/Projects/br3-docs-tests
source .venv/bin/activate
pytest tests/e2e/ -v
# Expected: 5+ tests passing
```

---

## Step 5: Merge (Day 3)

**IMPORTANT:** Merge in this exact order:

```bash
cd /Users/byronhudson/Projects/BuildRunner3

# 1. Documentation (no conflicts)
git merge build/docs-and-tests
pytest tests/e2e/ -v
git commit -m "docs: Update documentation accuracy and add E2E tests"

# 2. Persistence (adds new files)
git merge build/persistence-layer
pytest tests/test_persistence.py tests/test_event_storage.py tests/test_metrics_db.py -v
git commit -m "feat: Add persistence layer with SQLite and event rotation"

# 3. AI Integration (modifies routing)
git merge build/ai-integration
pytest tests/test_claude_client.py tests/test_ai_complexity.py -v
git commit -m "feat: Add Claude API integration and AI-powered complexity estimation"

# 4. Integration (modifies orchestrator)
git merge build/integration-layer
pytest tests/integration/ -v
git commit -m "feat: Wire telemetry, routing, and parallel into orchestrator"

# 5. Full verification
pytest tests/ -v --cov=core --cov-report=html
# Expected: 220+ tests passing

# 6. Push to GitHub
git push origin main

# 7. Tag release
git tag -a v3.1.0-alpha.4 -m "Week 1: Critical gaps closed - 49% → 72% completion"
git push origin v3.1.0-alpha.4

# 8. Cleanup
git worktree remove /Users/byronhudson/Projects/br3-integration
git worktree remove /Users/byronhudson/Projects/br3-persistence
git worktree remove /Users/byronhudson/Projects/br3-ai-layer
git worktree remove /Users/byronhudson/Projects/br3-docs-tests
```

---

## What Gets Built

### Build A: Integration Layer
- ✅ Telemetry events in orchestrator (task start/complete/fail)
- ✅ Model selection via routing in orchestrator
- ✅ Parallel coordination for task execution
- ✅ 20+ integration tests

### Build B: Persistence Layer
- ✅ SQLite database for cost tracking
- ✅ Event rotation and compression (1MB files)
- ✅ Metrics aggregation (hourly/daily/weekly)
- ✅ Database migration system

### Build C: AI Integration
- ✅ Claude API client for complexity estimation
- ✅ Real AI-powered task analysis
- ✅ Model fallback strategies (rate limit, timeout, context)
- ✅ Secure API key management

### Build D: Documentation
- ✅ Fixed all false claims in docs
- ✅ Added ⚠️ warnings for partial features
- ✅ Created user guides (QUICKSTART, INTEGRATION, API)
- ✅ 5 end-to-end test scenarios

---

## Success Criteria

After Week 1:
- ✅ 220+ tests passing (up from 165)
- ✅ 72% overall completion (up from 49%)
- ✅ All integrations working
- ✅ Persistence layer functional
- ✅ AI integration optional but available
- ✅ Documentation accurate

---

## Troubleshooting

### Issue: Worktree creation fails
```bash
# Clean up existing worktrees first
git worktree prune
# Then try again
```

### Issue: Tests fail in worktree
```bash
# Ensure you're in the right directory and venv is activated
cd /Users/byronhudson/Projects/br3-[name]
source .venv/bin/activate
pip install -e /Users/byronhudson/Projects/BuildRunner3
```

### Issue: Merge conflicts
```bash
# Abort merge
git merge --abort

# Check what changed
git diff main build/[branch-name]

# Merge with strategy
git merge -X ours build/[branch-name]  # Prefer current branch
# or
git merge -X theirs build/[branch-name]  # Prefer incoming branch
```

### Issue: Build seems stuck
```bash
# Check Claude Code session
# Look for errors or blockers
# If needed, provide additional context or fix issues manually
```

---

## Quick Reference

**Full docs:**
- Build Plan: `.buildrunner/WEEK1_BUILD_PLAN.md`
- All Prompts: `.buildrunner/WEEK1_PROMPTS.md`
- Gap Analysis: `.buildrunner/GAP_ANALYSIS_V3.md`
- Fixes Summary: `.buildrunner/GAP_FIXES_SUMMARY.md`

**Worktree locations:**
- Build A: `/Users/byronhudson/Projects/br3-integration`
- Build B: `/Users/byronhudson/Projects/br3-persistence`
- Build C: `/Users/byronhudson/Projects/br3-ai-layer`
- Build D: `/Users/byronhudson/Projects/br3-docs-tests`

**Commands:**
- Setup: See Step 1 above
- Verify: See Step 4 above
- Merge: See Step 5 above

---

**Ready to start? Run the commands in Step 1, then Step 2.**
