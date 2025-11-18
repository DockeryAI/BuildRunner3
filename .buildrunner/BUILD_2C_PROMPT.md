# BuildRunner 3.0 - Build 2C: Integration + PRD Wizard System

**Status:** Ready to Execute
**Context:** Builds 2A (CLI) and 2B (API) are merged into main branch
**Location:** `/Users/byronhudson/Projects/BuildRunner3` (main branch)
**Duration:** 3-4 hours

---

## TASK REFERENCE

Execute all tasks from BUILD_PLAN.md Build 2C (lines 716-826):
- **File:** `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN.md`
- **Section:** "Build 2C - Week 2 Integration + PRD Wizard System [MAIN BRANCH]"
- **Task Count:** 11 tasks covering PRD wizard, design intelligence, and integration testing

---

## KEY DELIVERABLES

### 1. PRD Wizard System with Design Intelligence
- `core/prd_wizard.py` - Interactive wizard with auto-detection and Opus pre-fill
- `core/design_profiler.py` - Industry + use case profile merger
- `core/design_researcher.py` - Web research integration for design patterns
- `core/prd_parser.py` - PROJECT_SPEC.md parser and validator
- `core/prd_mapper.py` - Sync PROJECT_SPEC → features.json → build plans
- `core/opus_handoff.py` - Opus → Sonnet protocol

### 2. Planning Mode Detection
- `core/planning_mode.py` - Detect strategic keywords, suggest model switching

### 3. Template Directory Structure
```
templates/
├── industries/
│   ├── healthcare.yaml
│   ├── fintech.yaml
│   ├── ecommerce.yaml
│   ├── education.yaml
│   └── saas.yaml
├── use_cases/
│   ├── dashboard.yaml
│   ├── marketplace.yaml
│   ├── crm.yaml
│   └── analytics.yaml
└── tech_stacks/
    ├── mern.yaml
    ├── django-react.yaml
    └── fastapi-vue.yaml
```

### 4. CLI Commands
- `br spec wizard` - Start interactive PROJECT_SPEC creation
- `br spec edit <section>` - Edit specific section
- `br spec sync` - Sync spec → features.json → build plans
- `br spec validate` - Check spec completeness
- `br spec review` - Section-by-section review mode
- `br spec confirm` - Lock spec and generate build plans
- `br spec unlock` - Unlock for changes (triggers rebuild)
- `br design profile <industry> <use-case>` - Preview design profile

### 5. Integration Tests
- `tests/test_integration_cli_api.py`
- `tests/test_integration_prd_sync.py`
- `tests/test_integration_config.py`
- `tests/test_prd_wizard.py`
- `tests/test_opus_handoff.py`

### 6. Documentation
- `docs/PRD_WIZARD.md`
- `docs/PRD_SYSTEM.md`
- `docs/examples/PRD-example.md`

---

## ACCEPTANCE CRITERIA

- ✅ Builds 2A and 2B merged successfully (DONE)
- [ ] CLI + API work together
- [ ] PRD wizard flow works (first-time and existing)
- [ ] Opus pre-fills PRD from app idea
- [ ] Interactive suggestions work per section
- [ ] Skip/defer functionality works
- [ ] Section-by-section review works
- [ ] Tech stack wizard completes
- [ ] Opus → Sonnet handoff protocol works
- [ ] PRD state machine functional
- [ ] PROJECT_SPEC.md syncs to features.json correctly
- [ ] Planning mode detection works
- [ ] Config hierarchy functional across CLI and API
- [ ] Auto-piping captures outputs
- [ ] Integration tests pass
- [ ] Alpha 2 tagged (v3.0.0-alpha.2)

---

## EXECUTION NOTES

**Dependencies Already Installed:**
- Python 3.14+, FastAPI, Typer, Rich, watchdog, pyyaml, pytest, pytest-cov

**Current State:**
- CLI implementation complete (Build 2A merged)
- API implementation complete (Build 2B merged)
- Both systems tested independently

**Focus Areas:**
1. **First:** Implement core PRD wizard system (wizard, parser, mapper)
2. **Second:** Add design intelligence (profiler, researcher)
3. **Third:** Create template files (start with 3 industries, 3 use cases, 2 tech stacks)
4. **Fourth:** Integration testing between CLI and API
5. **Fifth:** Documentation and examples

**Test Coverage Target:** 85%+

---

## COMMIT MESSAGE TEMPLATE

```bash
git add .
git commit -m "feat: Implement PROJECT_SPEC wizard with design intelligence (Build 2C)

- Add interactive PRD wizard with Opus pre-fill
- Implement design profiler (industry + use case merger)
- Add design researcher with web integration
- Create PROJECT_SPEC → features.json sync pipeline
- Add planning mode detection
- Create initial template library (industries, use cases, tech stacks)
- Implement Opus → Sonnet handoff protocol
- Add 8 new CLI commands (br spec, br design)
- Integration testing for CLI + API
- Test coverage: 85%+

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude <noreply@anthropic.com>"

git tag -a v3.0.0-alpha.2 -m "Week 2 Complete: CLI + API + PRD System"
```

---

## NEXT STEPS AFTER COMPLETION

After Build 2C is complete and tagged:
1. Generate Week 3 parallel build prompts (Builds 3A and 3B)
2. Execute Week 3 builds in parallel worktrees
3. Week 3 integration (Build 3C)
