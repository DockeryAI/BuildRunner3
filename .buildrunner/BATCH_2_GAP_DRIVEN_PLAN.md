# Batch 2: Gap-Driven Implementation Plan

**Created:** 2025-11-17
**Approach:** Adaptive orchestration based on gap analysis findings
**Estimated Time:** 3-4 hours
**Focus:** High-impact user-facing features + validation layer

---

## Philosophy: Intelligent Adaptation

Instead of blindly executing the original task queue, we're **adapting based on gap analysis**:

- ✅ **Gap Analysis Identified:** Missing CLI layer, validation components, configuration
- ✅ **Original Plan Had:** 6 feature-level tasks (too coarse)
- ✅ **Adjusted Approach:** Build what's actually missing (gap-driven)

**This demonstrates BuildRunner's intelligence:** Analyze → Learn → Adapt → Execute

---

## Batch 2 Scope

### Priority 0: Critical User-Facing Features

#### 1. cli/build_commands.py
**Purpose:** Unlock checkpoint/rollback/resume functionality
**Commands:**
- `br build checkpoint <name>` - Create named checkpoint
- `br build rollback <checkpoint-id>` - Rollback to checkpoint
- `br build resume [checkpoint-id]` - Resume from checkpoint
- `br build list-checkpoints` - List all checkpoints
- `br build status` - Show current build state

**Why Critical:** Core orchestration exists but users can't access it

#### 2. cli/gaps_commands.py
**Purpose:** Enable gap analysis from CLI
**Commands:**
- `br gaps analyze [--spec FILE]` - Analyze gaps between spec and implementation
- `br gaps report` - Generate gap analysis report
- `br gaps list` - List all detected gaps
- `br gaps fix <gap-id>` - Generate fix prompt for specific gap

**Why Critical:** Gap analyzer exists but no user interface

#### 3. cli/quality_commands.py
**Purpose:** Run quality checks from CLI
**Commands:**
- `br quality check [--strict]` - Run quality gates
- `br quality report` - Generate quality report
- `br quality score` - Show overall quality score
- `br quality fix` - Auto-fix formatting issues

**Why Critical:** Quality analyzer exists but inaccessible

### Priority 1: Validation Layer

#### 4. core/completeness_validator.py
**Purpose:** Programmatically verify 100% completion
**Features:**
- Compare PROJECT_SPEC against implemented files
- Verify all acceptance criteria met
- Check test coverage >= 85%
- Generate completion report
- Exit codes for CI/CD integration

**Why Critical:** Cannot verify we're actually done without this

#### 5. .buildrunner/quality-standards.yaml
**Purpose:** Configurable quality thresholds
**Contents:**
```yaml
quality_gates:
  min_overall_score: 7.0
  min_test_coverage: 85
  max_complexity: 10

format:
  python:
    - black
    - ruff

security:
  enabled: true
  scanners:
    - bandit
    - safety

thresholds:
  structure_score: 6.5
  security_score: 8.0
  testing_score: 8.5
  docs_score: 7.0
```

**Why Important:** Makes quality standards transparent and configurable

### Priority 2: Test Coverage Improvement

#### 6. Improve checkpoint_manager.py coverage
**Current:** 83% (103 statements, 17 missed)
**Target:** 85%+
**Approach:** Add tests for error paths and edge cases

**Missing Coverage:**
- Error handling in `_load_checkpoints()`
- Invalid checkpoint file handling
- Corrupted JSON handling
- Delete checkpoint edge cases

---

## Implementation Order

**Phase 1: CLI Layer (2 hours)**
1. `cli/build_commands.py` (30 min)
2. `cli/gaps_commands.py` (45 min)
3. `cli/quality_commands.py` (45 min)

**Phase 2: Validation (1 hour)**
4. `core/completeness_validator.py` (45 min)
5. `.buildrunner/quality-standards.yaml` (15 min)

**Phase 3: Testing & Validation (1 hour)**
6. Improve checkpoint test coverage (30 min)
7. Test all CLI commands (20 min)
8. Run completeness validator (10 min)

---

## Expected Outcomes

### Metrics
- **Functional Completion:** 55% → 85%
- **User-Facing CLI:** 0% → 80%
- **Validation Layer:** 0% → 100%
- **Test Coverage:** 88% → 90%+

### User Impact
**Before Batch 2:**
- Core orchestration exists but hidden
- Gap analysis exists but no CLI
- Quality system exists but no interface
- Cannot verify completion

**After Batch 2:**
- ✅ `br build checkpoint/rollback/resume` - Full build control
- ✅ `br gaps analyze` - Run gap analysis on demand
- ✅ `br quality check` - Validate code quality
- ✅ Completeness validator - Verify 100% done
- ✅ Quality standards - Configurable thresholds

### Validation
Can run these commands to verify Build 3A:
```bash
br gaps analyze --spec .buildrunner/PROJECT_SPEC_BUILD_3A.md
br quality check --strict
br build status
```

---

## Comparison to Original Plan

### Original Task Queue (Blind Execution)
- Task 2: "Implement API endpoints" (gap analyzer)
- Task 3: "Create UI components" (gap analyzer)
- Task 4: "Write tests" (gap analyzer)
- Task 5: "Implement Code Quality System"
- Task 6: "Implement Architecture Drift Prevention"

**Problem:** Tasks 5-6 already exist from Build 1A/1B!

### Gap-Driven Plan (Intelligent Execution)
- Build missing CLI layer (3 commands files)
- Add validation component (completeness_validator)
- Create configuration (quality-standards.yaml)
- Improve test coverage

**Advantage:** Builds what's actually missing, not redundant work

---

## Success Criteria

**Batch 2 Complete When:**
1. ✅ All 3 CLI command files created and tested
2. ✅ Completeness validator functional
3. ✅ Quality standards YAML created
4. ✅ Test coverage >= 85% on all new code
5. ✅ Can run `br gaps analyze` and verify Build 3A completion
6. ✅ Can run `br quality check` and pass quality gates
7. ✅ All commands have help text and examples
8. ✅ Integration tests pass for CLI workflows

**Validation:**
```bash
# These should all work:
br build checkpoint batch2_complete
br gaps analyze
br quality check
br build list-checkpoints
```

---

## Risk Mitigation

**Risk:** CLI integration with existing core modules
**Mitigation:** Use existing patterns from run_commands.py and tasks_commands.py

**Risk:** Completeness validator complexity
**Mitigation:** Start simple (file existence), iterate to full validation

**Risk:** Time overrun
**Mitigation:** Implement in priority order, can stop after P0 if needed

---

## Meta: This Demonstrates Intelligence

**Key Insight:** This batch proves BuildRunner can:
1. Execute a plan (Batch 1)
2. Analyze results (gap analysis)
3. Learn what's missing (55% complete, why?)
4. Adapt the plan (adjust Batch 2)
5. Execute smarter (gap-driven not blind)
6. Validate results (completeness validator)

**This is the full self-improvement loop!**

---

**Plan Created By:** Claude Code
**Based On:** GAP_ANALYSIS_BUILD_3A.md findings
**Next Step:** Execute Phase 1 (CLI Layer)
