# BuildRunner Architecture Shift: Self-Orchestration

## The Paradigm Change

### Before: Human-Orchestrated
```
Human writes task lists → Human directs Claude → Human verifies → Repeat
```
**Problem:** Slow, error-prone, cognitive overload, missing components

### After: Self-Orchestrated
```
PROJECT_SPEC.md → BR generates tasks → BR directs Claude → BR verifies → Auto-continues
```
**Solution:** Fast, reliable, complete, human only handles exceptions

---

## Implementation Timeline

### Phase 1: Current Week 1 (In Progress)
**Traditional Approach (Last Time)**
- Build 1A: PRD Wizard (manual task list)
- Build 1B: Design System (manual task list)
- Build 1C: Integration
- Result: v3.1.0-alpha.1

### Phase 2: Week 2 - Build the Orchestrator
**Transitional Phase**
- Build 2A: Task Generation System
- Build 2B: Orchestration Runtime
- Build 2C: Integration
- Result: v3.1.0-alpha.3 with orchestration capability

### Phase 3: Week 3-12 - Orchestrated Development
**New Paradigm**
- BuildRunner orchestrates its own development
- Parallel execution with optimal batching
- Real-time verification and recovery
- Result: Complete BuildRunner 3.4 in 12 weeks (vs 20)

---

## Key Architectural Components

### 1. Task Generation System
**Purpose:** Convert specs into executable tasks

**Components:**
- `spec_parser.py` - Parse PROJECT_SPEC.md
- `task_decomposer.py` - Break features into 1-2 hour tasks
- `dependency_graph.py` - Build execution DAG

**Output:** Prioritized queue of atomic tasks

### 2. Batch Optimizer
**Purpose:** Group tasks for optimal Claude performance

**Rules:**
- Max 2-3 tasks per batch (not 3-5)
- Never mix domains (frontend/backend/database)
- Adjust by complexity (complex = 1 task)
- Validate coherence

**Output:** Optimized task batches

### 3. Prompt Builder
**Purpose:** Generate focused Claude prompts

**Features:**
- Clear task descriptions
- Relevant context only (max 4000 tokens)
- Explicit acceptance criteria
- Stop points

**Output:** Ready-to-execute Claude prompts

### 4. Execution Engine
**Purpose:** Run the orchestration loop

**Process:**
```python
while tasks_remaining:
    batch = optimizer.get_next_batch()
    prompt = builder.build_prompt(batch)
    claude.execute(prompt)
    monitor.watch_files()
    verifier.run_tests()
    if success:
        state.mark_complete(batch)
    else:
        recovery.fix_issues()
```

### 5. Verification System
**Purpose:** Ensure quality and completeness

**Checks:**
- Files created as expected
- Tests passing
- Coverage targets met
- No missing components
- Performance acceptable

---

## Benefits Analysis

### Speed: 60% Faster
- **Old:** 20 weeks (manual orchestration)
- **New:** 12 weeks (auto-orchestration)
- **Why:** No human bottleneck, optimal batching, parallel execution

### Quality: 99% Completion Rate
- **Old:** 70% completion (cognitive overload)
- **New:** 99% completion (automated tracking)
- **Why:** Real-time monitoring, auto-recovery, nothing forgotten

### Consistency: Predictable Output
- **Old:** Variable quality based on human state
- **New:** Consistent quality from systematic approach
- **Why:** Same process every time, verification gates

---

## Migration Strategy

### For Current BuildRunner Users

**No Breaking Changes Initially:**
- Existing commands still work
- Manual mode still available
- Gradual adoption possible

**New Commands Available:**
```bash
# Automated orchestration
br run --auto

# Semi-automated (prompts for approval)
br run --interactive

# View task queue
br task list

# Manual fallback
br task execute --manual
```

### For BuildRunner Development

**Week 1:** Continue current approach (already started)
**Week 2:** Build orchestrator
**Week 3+:** Use orchestrator for everything

---

## Example: How It Works

### Input: PROJECT_SPEC.md
```markdown
## Features
- User Authentication
  - JWT-based auth
  - Social login (Google, GitHub)
  - Password reset
  - 2FA support
```

### BuildRunner Processing
```bash
$ br spec analyze
Extracted 1 feature: User Authentication
Generated 12 tasks:
  - Create User model (90 min)
  - Add password hashing (60 min)
  - Create auth endpoints (90 min)
  - Add JWT generation (60 min)
  - Implement social login (120 min)
  - Add password reset (90 min)
  - Implement 2FA (120 min)
  - Create auth middleware (60 min)
  - Write unit tests (90 min)
  - Write integration tests (90 min)
  - Update documentation (60 min)
  - Add examples (60 min)

$ br run --auto
Starting orchestrated execution...
Batch 1: Database layer (2 tasks)
  ✓ User model created
  ✓ Password hashing added
  ✓ Tests passing
Batch 2: API layer (2 tasks)
  ✓ Auth endpoints created
  ✓ JWT generation added
  ✓ Tests passing
[Continues automatically...]
```

---

## Critical Success Factors

### 1. Optimal Batch Size
- **2-3 tasks maximum** (not 5+)
- Proven to maintain 95% accuracy
- Prevents context pollution

### 2. Domain Isolation
- Never mix frontend/backend in same batch
- Maintains focus
- Reduces errors

### 3. Real-Time Verification
- Test after every batch
- Catch errors immediately
- Auto-recovery for missing components

### 4. State Persistence
- Track everything
- Enable recovery from any point
- No lost work

---

## Risks and Mitigations

### Risk: Orchestrator Complexity
**Mitigation:** Build incrementally, test thoroughly, keep manual fallback

### Risk: Claude API Changes
**Mitigation:** Abstract prompt generation, version prompts

### Risk: Spec Parsing Errors
**Mitigation:** Validate specs, provide templates, manual override

---

## Next Immediate Steps

1. **Let Week 1 builds complete** (PRD Wizard + Design System)
2. **Execute Build 2** (Task Orchestrator) using ORCHESTRATOR_PROMPTS.md
3. **Test orchestrator** on a simple feature
4. **Use orchestrator** for all remaining BuildRunner development

---

## Success Metrics

### Week 2 Success (Orchestrator Built)
- [ ] Parses PROJECT_SPEC.md correctly
- [ ] Generates valid task queues
- [ ] Creates optimal batches (2-3 tasks)
- [ ] Produces focused Claude prompts
- [ ] Monitors execution successfully
- [ ] 90%+ test coverage

### Week 12 Success (BuildRunner Complete)
- [ ] All features implemented
- [ ] 99% completion rate
- [ ] 60% time reduction achieved
- [ ] Self-orchestration proven
- [ ] Ready for production use

---

## The Vision

BuildRunner becomes an **intelligent development orchestrator** that:
1. Understands project requirements (from specs)
2. Plans optimal execution (task generation)
3. Directs AI assistants (Claude orchestration)
4. Ensures quality (real-time verification)
5. Completes projects reliably (99% completion)

**This is the future of AI-assisted development: Not humans directing AI, but systems orchestrating AI for predictable, high-quality outcomes.**