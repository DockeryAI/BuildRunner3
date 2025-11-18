# BuildRunner Atomic Task Workflow Principles

**Version:** 1.0
**For:** Week-by-week build execution

---

## Core Philosophy

**Claude performs best with focused, bounded tasks with clear success criteria.**

Think "surgical strikes" not "carpet bombing."

---

## PRD → Task List → Execution Flow

### 1. PRD Creation
Natural language requirements → structured `PROJECT_SPEC.md`

### 2. Task Extraction
AI parses spec into **atomic, testable tasks** (~1-2 hour chunks each)

### 3. Dependency Mapping
Tasks ordered by dependencies:
- Database before API
- API before UI
- Core before features

### 4. Progressive Execution
One task (or small batch) at a time with validation gates

---

## Directing Claude Code

### Explicit Commands
- Each task becomes a **single, focused prompt**
- Clear acceptance criteria
- Expected files to create/modify
- Expected test coverage
- Explicit "done" signal

### Context Injection
Include for each task:
- Relevant `PROJECT_SPEC.md` sections
- Previously completed code
- Dependency files
- Current state (from CLAUDE.md)

### Checkpoint System
After each task/batch:
1. Verify output matches requirements
2. Run tests
3. Update state tracking
4. Commit
5. Get explicit confirmation before next task

### State Management
Maintain running state in:
- **CLAUDE.md** - Completed components, current state, next steps
- **TodoWrite** - Real-time task tracking
- **Git commits** - Version history

---

## Preventing Missing Components

### Problem
Cognitive overload when processing 20+ tasks simultaneously leads to **dropped items**

### Solutions

#### 1. Batch Size Limits ⚠️
- **Max 3-5 related tasks per prompt**
- Group by domain (all auth tasks, all database tasks)
- **Never mix frontend/backend in same batch**
- Never "build everything" in one go

#### 2. Verification Gates ✅
After each batch:
- List what was built vs what was requested
- Run automated checks:
  - Files exist
  - Imports resolve
  - Tests pass
  - Coverage meets target
- **Explicit confirmation before next batch**

#### 3. Task Decomposition 🔨
Break large tasks into atomic units.

**Bad:**
```
Task: Create user authentication
```

**Good:**
```
Batch 1 (Data Layer):
- Task 1.1: Create user model (20 min)
- Task 1.2: Add password hashing (15 min)
- Task 1.3: Write user model tests (25 min)

✅ Verification Gate: User model complete, tests pass

Batch 2 (API Layer):
- Task 2.1: Create login endpoint (30 min)
- Task 2.2: Add JWT generation (20 min)
- Task 2.3: Write endpoint tests (30 min)

✅ Verification Gate: API endpoints complete, tests pass

Batch 3 (Middleware):
- Task 3.1: Write auth middleware (30 min)
- Task 3.2: Add middleware tests (25 min)
- Task 3.3: Integration tests (25 min)

✅ Verification Gate: Full auth flow working
```

#### 4. Progressive Enhancement 📈
- Build **minimal working version first**
- Add features incrementally
- Each addition must pass tests
- No "gold plating" until core works

#### 5. Memory Management 🧠
- Use **TodoWrite** to track completion status
- Update **CLAUDE.md** with completed items
- Reference previous completions in next prompt
- Keep context window clean

---

## Optimal Execution Patterns

### 1. Single Task Mode (Highest Accuracy, Slowest)
```
Task → Verify → Commit → Next Task
```
- One atomic task per prompt
- Best for: Critical components, complex logic
- Accuracy: ~95%

### 2. Domain Batch Mode (Balanced) ⭐ **RECOMMENDED**
```
3-5 Related Tasks → Verify → Commit → Next Batch
```
- 3-5 related tasks in same domain
- All in same file/module
- Shared context
- Best for: Standard features, related components
- Accuracy: ~85-90%

### 3. Never "Build Everything" Mode ❌
```
20+ tasks in one prompt → 70% completion → missing components
```
- Brain dumps fail at ~70% completion
- Context window pollution
- Lost track of requirements
- **Never use this pattern**

---

## Task List Structure

Each atomic task must include:

```markdown
### Task X.Y: [Clear, Specific Title]

**Domain:** [Backend/Frontend/Database/Testing]
**Duration:** [Estimated time: 15-60 min]
**Dependencies:** [Task IDs this depends on]

**Objective:**
Single sentence describing what this task accomplishes.

**Files to Create/Modify:**
- path/to/file1.py (CREATE - 150 lines)
- path/to/file2.py (UPDATE - add function X)

**Implementation Details:**
[Specific code structure, function signatures, key algorithms]

**Acceptance Criteria:**
- [ ] File(s) created/modified
- [ ] Function X returns expected output
- [ ] Tests pass (X tests, Y% coverage)
- [ ] No linting errors
- [ ] Imports resolve

**Testing Commands:**
```bash
pytest path/to/test.py -v
```

**Verification Gate:**
Before proceeding, verify:
1. All acceptance criteria met
2. Tests passing
3. No errors in console
```

---

## Batch Grouping Rules

### ✅ Good Batches (Same Domain)
```
Batch: Database Models
- Create User model
- Create Post model
- Create Comment model
(All database, all models, shared ORM knowledge)
```

### ❌ Bad Batches (Mixed Domains)
```
Batch: User Feature
- Create User model (database)
- Create login API (backend)
- Create login form (frontend)
(Too much context switching, different technologies)
```

---

## PRD Change Management

### Version Control
- `PROJECT_SPEC.md` versions with diffs
- Track changes in git
- Tag major revisions

### Impact Analysis
- AI identifies which code affected by spec changes
- Generate list of files to update
- Estimate effort

### Targeted Updates
- Only rebuild affected components
- Avoid unnecessary rewrites
- Maintain working state

### Regression Prevention
- Run **full test suite** after changes
- Check integration points
- Verify dependent features still work

---

## State Tracking: CLAUDE.md

Every build should maintain a `CLAUDE.md` file:

```markdown
# Claude State Tracker

## Project: BuildRunner 3.1 - PRD Wizard

## Current Status
**Last Updated:** 2025-01-24 14:30
**Branch:** build/v3.1-prd-wizard
**Phase:** Implementation

## Completed Components
- [x] OpusClient (core/opus_client.py) - 387 lines, 90% coverage
- [x] ModelSwitcher (core/model_switcher.py) - 284 lines, 88% coverage
- [x] Planning mode detection (core/planning_mode.py) - 156 lines added

## In Progress
- [ ] PRD Wizard full flow (core/prd_wizard.py)
  - Status: 60% complete
  - Remaining: Error handling, edge cases

## Pending
- [ ] Tests for wizard flow
- [ ] Documentation updates

## Blockers
None

## Next Steps
1. Complete wizard error handling
2. Write integration tests
3. Update documentation
4. Push branch for review

## Notes
- Real Opus API integration working
- Model switching protocol tested
- Coverage target: 85%+
```

---

## Week-by-Week Planning

### Week N Preparation
1. Read PROJECT_SPEC.md sections for week N features
2. Extract all required components
3. Map dependencies
4. Break into batches (3-5 tasks each)
5. Define verification gates
6. Create atomic task list

### During Week N
1. Execute Batch 1 → Verify → Commit
2. Update CLAUDE.md and TodoWrite
3. Execute Batch 2 → Verify → Commit
4. Continue until all batches complete
5. Integration testing
6. Final verification
7. Push branch

### Week N+1 Preparation
1. Review Week N outcomes
2. Adjust estimates based on actual time
3. Refine task decomposition strategy
4. Plan Week N+1 with lessons learned

---

## Key Metrics

Track these for each week:

- **Task Completion Rate:** Completed / Total tasks
- **Accuracy Rate:** Tasks completed correctly first time
- **Rework Rate:** Tasks requiring fixes after verification
- **Coverage Achievement:** Actual vs target test coverage
- **Time Estimation Accuracy:** Estimated vs actual time

**Target:**
- Completion: 95%+
- Accuracy: 90%+
- Rework: <10%
- Coverage: 85%+
- Time Accuracy: ±20%

---

## Anti-Patterns to Avoid

### ❌ The "Big Bang" Approach
```
Prompt: "Build the entire authentication system"
Result: 70% complete, missing edge cases, poor tests
```

### ❌ The "Context Salad"
```
Prompt: "Add user auth, fix the CSS bug, update docs, and refactor the DB"
Result: Confusion, none done well
```

### ❌ The "Assumption Trap"
```
Prompt: "Add login" (without specifying JWT vs session, OAuth, etc.)
Result: Wrong implementation, wasted time
```

### ❌ The "No Verification" Pattern
```
Prompt → Prompt → Prompt (no testing between)
Result: Compounding errors, broken code
```

---

## Success Patterns

### ✅ The "Surgical Strike"
```
Prompt: "Create User model with email, password_hash, created_at fields.
         Use SQLAlchemy. Include __repr__ and validate_email method.
         Target: 80 lines, 90% test coverage."
Result: Perfect implementation
```

### ✅ The "Batch and Verify"
```
Batch 1: Database models → Verify → ✅
Batch 2: API endpoints → Verify → ✅
Batch 3: Frontend components → Verify → ✅
Result: Complete feature, high quality
```

### ✅ The "Progressive Enhancement"
```
V1: Basic login (username/password) → Verify → ✅
V2: Add JWT tokens → Verify → ✅
V3: Add OAuth → Verify → ✅
Result: Robust auth system, built incrementally
```

---

## Summary

**Do:**
- Break tasks into 1-2 hour chunks
- Batch 3-5 related tasks
- Verify after each batch
- Track state (CLAUDE.md, TodoWrite)
- Use explicit acceptance criteria

**Don't:**
- Build everything at once
- Mix domains in one batch
- Skip verification gates
- Assume implicit requirements
- Proceed without checking tests

**Remember:** Claude is a focused specialist, not a multitasking generalist. Give it clear, bounded work and it will excel.
