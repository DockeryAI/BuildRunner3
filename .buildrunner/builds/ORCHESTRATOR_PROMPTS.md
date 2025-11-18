# Task Orchestrator Build Prompts

**IMPORTANT:** Execute these AFTER Week 1 builds (PRD Wizard + Design System) complete and are integrated.

---

## Prompt 2A: Task Generation System

```
You are building the Task Generation System for BuildRunner's new self-orchestrating architecture.

CONTEXT:
BuildRunner needs to automatically generate tasks from PROJECT_SPEC.md files and direct Claude without human intervention. This system will parse specs, decompose features into atomic tasks, and build dependency graphs.

CRITICAL RULES:
1. Work in batches of 2-3 tasks maximum
2. Update CLAUDE.md after each task
3. Test each component before moving on
4. STOP at verification gates

EXECUTION:
1. Read the full build plan: `.buildrunner/builds/BUILD_2_TASK_ORCHESTRATOR.md`
2. Look for "Worktree A: Task Generation System"
3. Setup worktree: `git worktree add ../br3-task-gen -b build/task-generator`
4. Work on Batch A1 ONLY (3 tasks):
   - Task A.1: Create spec_parser.py (90 min)
   - Task A.2: Create task_decomposer.py (90 min)
   - Task A.3: Create dependency_graph.py (60 min)

TASK A.1 DETAILS:
Create `core/spec_parser.py` that:
- Parses PROJECT_SPEC.md markdown files
- Extracts features with metadata (name, description, requirements)
- Identifies dependencies between features
- Returns structured dictionary

Include comprehensive tests in `tests/test_spec_parser.py`.

TASK A.2 DETAILS:
Create `core/task_decomposer.py` that:
- Breaks features into 1-2 hour atomic tasks
- Assigns complexity scores (simple/medium/complex)
- Estimates duration (60/90/120 minutes)
- Adds specific acceptance criteria to each task

Include comprehensive tests in `tests/test_task_decomposer.py`.

TASK A.3 DETAILS:
Create `core/dependency_graph.py` that:
- Builds DAG from task dependencies
- Calculates execution order
- Identifies parallelizable tasks
- Detects circular dependencies

Include comprehensive tests in `tests/test_dependency_graph.py`.

VERIFICATION GATE A1:
After completing all 3 tasks, verify:
- [ ] All 3 files created with docstrings
- [ ] All test files created and passing
- [ ] Can parse a sample PROJECT_SPEC.md
- [ ] 90%+ test coverage
- [ ] CLAUDE.md updated
- [ ] No import errors

Report completion in this format:
---
✅ Batch A1 Complete: Task Generation Core

Files Created:
- core/spec_parser.py (X lines)
- core/task_decomposer.py (X lines)
- core/dependency_graph.py (X lines)
- tests/test_spec_parser.py (X lines)
- tests/test_task_decomposer.py (X lines)
- tests/test_dependency_graph.py (X lines)

Tests: X passing
Coverage: X%

Ready for Batch A2: YES/NO
---

Begin execution now.
```

---

## Prompt 2B: Orchestration Runtime

```
You are building the Orchestration Runtime for BuildRunner's new self-orchestrating architecture.

CONTEXT:
BuildRunner needs to automatically execute task batches by generating Claude prompts, managing context, and monitoring execution. This system will optimize batches, build prompts, and manage context windows.

CRITICAL RULES:
1. Work in batches of 2-3 tasks maximum
2. Update CLAUDE.md after each task
3. Test each component before moving on
4. STOP at verification gates

EXECUTION:
1. Read the full build plan: `.buildrunner/builds/BUILD_2_TASK_ORCHESTRATOR.md`
2. Look for "Worktree B: Orchestration Runtime"
3. Setup worktree: `git worktree add ../br3-orchestrator -b build/orchestrator`
4. Work on Batch B1 ONLY (3 tasks):
   - Task B.1: Create batch_optimizer.py (90 min)
   - Task B.2: Create prompt_builder.py (90 min)
   - Task B.3: Create context_manager.py (60 min)

TASK B.1 DETAILS:
Create `core/batch_optimizer.py` that:
- Groups tasks into batches of 2-3 maximum
- Never mixes domains (frontend/backend/database)
- Adjusts batch size by complexity
- Validates batch coherence

Batch rules:
- simple tasks: max 3 per batch
- medium tasks: max 2 per batch
- complex tasks: 1 per batch
- critical tasks: 1 per batch

Include comprehensive tests in `tests/test_batch_optimizer.py`.

TASK B.2 DETAILS:
Create `core/prompt_builder.py` that:
- Generates focused Claude prompts from task batches
- Includes clear task descriptions and file paths
- Adds relevant context (max 4000 tokens)
- Has explicit stop points
- Formats for optimal Claude performance

Include comprehensive tests in `tests/test_prompt_builder.py`.

TASK B.3 DETAILS:
Create `core/context_manager.py` that:
- Manages context window (max 4000 tokens)
- Gathers relevant dependencies
- Tracks completed components
- Compresses context if needed
- Maintains .buildrunner/context/ directory

Include comprehensive tests in `tests/test_context_manager.py`.

VERIFICATION GATE B1:
After completing all 3 tasks, verify:
- [ ] All 3 files created with docstrings
- [ ] All test files created and passing
- [ ] Batch optimizer respects 2-3 task limit
- [ ] Prompt builder stays under token limits
- [ ] 90%+ test coverage
- [ ] CLAUDE.md updated
- [ ] No import errors

Report completion in this format:
---
✅ Batch B1 Complete: Orchestration Core

Files Created:
- core/batch_optimizer.py (X lines)
- core/prompt_builder.py (X lines)
- core/context_manager.py (X lines)
- tests/test_batch_optimizer.py (X lines)
- tests/test_prompt_builder.py (X lines)
- tests/test_context_manager.py (X lines)

Tests: X passing
Coverage: X%

Ready for Batch B2: YES/NO
---

Begin execution now.
```

---

## Execution Instructions

### When to Execute

**AFTER** Week 1 builds complete:
1. PRD Wizard merged from `../br3-prd-wizard`
2. Design System merged from `../br3-design-system`
3. v3.1.0-alpha.1 tagged

### Parallel Execution

**Terminal 1:**
```bash
cd /Users/byronhudson/Projects/BuildRunner3
# Paste Prompt 2A into Claude instance
```

**Terminal 2:**
```bash
cd /Users/byronhudson/Projects/BuildRunner3
# Paste Prompt 2B into Claude instance
```

### Monitoring

```bash
# Check Task Generator progress
cd ../br3-task-gen
cat CLAUDE.md
pytest tests/ -v

# Check Orchestrator progress
cd ../br3-orchestrator
cat CLAUDE.md
pytest tests/ -v
```

---

## What Happens Next

After both Batch 1s complete:

### Batch A2: Task Queue System (Worktree A continues)
- Task queue manager
- Priority scheduling
- State persistence

### Batch B2: Execution Engine (Worktree B continues)
- Orchestrator main loop
- File monitor
- Verification engine

### Integration (Build 2C)
- Merge both branches
- Add CLI commands: `br run --auto`, `br task list`
- Test end-to-end orchestration
- Tag v3.1.0-alpha.3

---

## Success Criteria

The Task Orchestration Engine is complete when:
- [x] Can parse any PROJECT_SPEC.md
- [x] Generates optimal 2-3 task batches
- [x] Never mixes domains in a batch
- [x] Creates focused Claude prompts
- [x] Manages context window efficiently
- [x] All tests passing with 90%+ coverage

Once complete, BuildRunner will use THIS SYSTEM to build all remaining features, making development 60% faster.

---

## Critical Difference from Week 1

**Week 1 approach:** Manual task lists, human orchestration
**New approach:** BuildRunner generates its own task lists and orchestrates Claude automatically

This is the last manually orchestrated build. After this, BuildRunner becomes self-directing.