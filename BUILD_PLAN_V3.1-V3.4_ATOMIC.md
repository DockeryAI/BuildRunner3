# BuildRunner 3.1-3.4 - Atomic Build Plan

## Overview
20-week plan with atomic, self-contained task lists. Each build is Claude-executable with zero external dependencies.

**Strategy:** Parallel builds via git worktrees → Integration → Tag → Next cycle

**⚠️ CRITICAL:** Read `.buildrunner/WORKFLOW_PRINCIPLES.md` before executing any builds

---

## Execution Model

### Week-by-Week Atomic Task Lists
This plan provides **high-level structure** for all 20 weeks. **Detailed atomic task lists** are created **one week at a time** to:
- Prevent cognitive overload
- Allow learning from previous weeks
- Adapt to actual implementation realities
- Maintain focus and quality

### Workflow Pattern (Applied to Every Week)
1. **PRD → Task Extraction** - Parse week's requirements into atomic tasks
2. **Batch Planning** - Group into 3-5 task batches with verification gates
3. **State Tracking** - CLAUDE.md + TodoWrite for every build
4. **Domain Batch Execution** - Focus on one domain at a time
5. **Progressive Enhancement** - Minimal working version → incremental features
6. **Verification Gates** - Test and verify after each batch
7. **No "Build Everything"** - Never more than 5 tasks per prompt

### Current Status
- **Week 1:** ✅ Atomic task lists complete (`.buildrunner/builds/BUILD_1A_PRD_WIZARD.md`, `.buildrunner/builds/BUILD_1B_DESIGN_SYSTEM.md`)
- **Week 2-20:** High-level plans below, atomic task lists TBD

**See:** `.buildrunner/WORKFLOW_PRINCIPLES.md` for execution guidelines

---

## RELEASE 1: BuildRunner 3.1 (Weeks 1-5)

---

### Build 1A - Complete PRD Wizard [PARALLEL]
**Worktree:** `../br3-prd-wizard`
**Branch:** `build/v3.1-prd-wizard`
**Duration:** 1 week
**Execute in parallel with Build 1B**

#### Prerequisites
```bash
cd /Users/byronhudson/Projects/BuildRunner3
```

#### Git Worktree Setup
```bash
git worktree add ../br3-prd-wizard -b build/v3.1-prd-wizard
cd ../br3-prd-wizard
```

#### Dependencies
```bash
pip install anthropic>=0.18.0 -q  # For real Opus API
pip install pytest pytest-asyncio pytest-cov -q
```

#### Task List

**1. Implement Real Opus API Integration**

Create `core/opus_client.py`:
```python
# Real Anthropic Opus API client
# - OpusClient class with async methods
# - pre_fill_spec() - takes industry/use_case, returns PROJECT_SPEC suggestions
# - analyze_requirements() - analyzes user input, suggests features
# - generate_design_tokens() - generates design system from spec
# - Error handling, retries, rate limiting
# - Environment variable: ANTHROPIC_API_KEY
```

**2. Implement Model Switching Protocol**

Create `core/model_switcher.py`:
```python
# Model switching for Opus → Sonnet handoff
# - create_handoff_package() - compact context bundle
# - compress_context() - remove verbosity, keep essentials
# - generate_sonnet_prompt() - format for Sonnet execution
# - validate_handoff() - ensure all required context present
```

**3. Implement Planning Mode Auto-Detection**

Update `core/planning_mode.py`:
```python
# Auto-detect when to use planning mode
# - detect_planning_mode() - analyze user prompt complexity
# - should_use_opus() - decision logic (new project, complex changes)
# - should_use_sonnet() - decision logic (incremental, bug fixes)
# - confidence_score() - 0-1 score for mode selection
```

**4. Complete PRD Wizard Implementation**

Update `core/prd_wizard.py`:
```python
# Replace stubs with real implementation
# - run_wizard() - full interactive flow with Opus
# - validate_input() - validate user responses
# - generate_spec() - use Opus to pre-fill PROJECT_SPEC.md
# - save_spec() - write to .buildrunner/PROJECT_SPEC.md
# - auto_sync_features() - call br spec sync
```

**5. Write Comprehensive Tests**

Create/Update `tests/test_prd_wizard_complete.py`:
```python
# Test coverage: 85%+ required
# - test_opus_client_integration() - mock API calls
# - test_model_switching_protocol()
# - test_planning_mode_detection()
# - test_wizard_full_flow()
# - test_error_handling()
# - test_rate_limiting()
# - test_handoff_package_compression()
```

**6. Update Documentation**

Update `docs/PRD_WIZARD.md`:
- Add Opus integration instructions
- Add model switching documentation
- Add planning mode auto-detection guide
- Add troubleshooting section
- Add API key setup instructions

Update `docs/PRD_SYSTEM.md`:
- Add architecture diagram for model switching
- Add handoff package specification
- Add planning mode decision tree

#### Acceptance Criteria
- ✅ Real Opus API integration working (not simulated)
- ✅ Model switching creates valid handoff packages
- ✅ Planning mode auto-detects correctly 90%+ of time
- ✅ Test coverage 85%+
- ✅ All tests pass
- ✅ Documentation complete

#### Testing Commands
```bash
# Run tests
pytest tests/test_prd_wizard_complete.py -v --cov=core/opus_client.py --cov=core/model_switcher.py --cov=core/planning_mode.py

# Manual test
python -m cli.main spec wizard
# Should use real Opus API, show model switching
```

#### Commit & Push
```bash
git add .
git commit -m "feat: Complete PRD wizard with real Opus integration

- Real Anthropic Opus API client
- Model switching protocol (Opus → Sonnet)
- Planning mode auto-detection
- Test coverage: 85%+

🤖 Generated with Claude Code"
git push -u origin build/v3.1-prd-wizard
```

#### Completion Signal
**DO NOT MERGE.** Push branch and wait for review. Report:
- ✅ All tasks complete
- ✅ Tests passing (X/X)
- ✅ Coverage: X%
- ✅ Branch: build/v3.1-prd-wizard pushed
- ⏸️ Ready for review

---

### Build 1B - Complete Design System [PARALLEL]
**Worktree:** `../br3-design-system`
**Branch:** `build/v3.1-design-system`
**Duration:** 1 week
**Execute in parallel with Build 1A**

#### Prerequisites
```bash
cd /Users/byronhudson/Projects/BuildRunner3
```

#### Git Worktree Setup
```bash
git worktree add ../br3-design-system -b build/v3.1-design-system
cd ../br3-design-system
```

#### Dependencies
```bash
pip install pytest pytest-cov pyyaml -q
pip install playwright -q  # For visual regression testing
playwright install chromium
```

#### Task List

**1. Create 5 Missing Industry YAML Profiles**

Create `templates/industries/government.yaml`:
```yaml
# Government industry profile
# - Colors: official blue, white, seal gold
# - Typography: accessible fonts (minimum 16px)
# - Compliance: Section 508, WCAG 2.1 AAA, FedRAMP
# - Components: form validation, accessibility widgets
# - Security: high, ATO requirements
```

Create `templates/industries/legal.yaml`:
```yaml
# Legal industry profile
# - Colors: navy, charcoal, professional palette
# - Typography: serif for documents, sans-serif for UI
# - Compliance: attorney-client privilege, document retention
# - Components: document editor, case management
# - Security: encryption at rest, audit logging
```

Create `templates/industries/nonprofit.yaml`:
```yaml
# Nonprofit industry profile
# - Colors: mission-aligned, warm and trustworthy
# - Typography: readable, accessible
# - Compliance: 501(c)(3) reporting, donor privacy
# - Components: donation forms, volunteer management
# - Security: donor data protection, PCI DSS
```

Create `templates/industries/gaming.yaml`:
```yaml
# Gaming industry profile
# - Colors: vibrant, high contrast for readability
# - Typography: display fonts, readability at any size
# - Compliance: COPPA (if under 13), GDPR
# - Components: leaderboards, achievements, inventory
# - Security: anti-cheat, user authentication
```

Create `templates/industries/manufacturing.yaml`:
```yaml
# Manufacturing industry profile
# - Colors: industrial palette (grey, blue, orange)
# - Typography: clear, works on tablets/touch screens
# - Compliance: ISO 9001, safety standards
# - Components: inventory tracking, equipment monitoring
# - Security: operational technology security, supply chain
```

**2. Create 5 Missing Use Case YAML Patterns**

Create `templates/use_cases/chat.yaml`:
```yaml
# Chat/messaging pattern
# - Layout: sidebar (contacts) + main (messages) + detail (profile)
# - Components: message list, input composer, emoji picker
# - Navigation: conversation threads, search
# - Interactions: real-time updates, typing indicators, read receipts
# - Patterns: infinite scroll, optimistic UI updates
```

Create `templates/use_cases/video.yaml`:
```yaml
# Video streaming pattern
# - Layout: hero video + recommendations grid + sidebar
# - Components: video player, progress bar, quality selector
# - Navigation: categories, search, playlists
# - Interactions: play/pause, seek, fullscreen, picture-in-picture
# - Patterns: lazy loading thumbnails, adaptive bitrate
```

Create `templates/use_cases/calendar.yaml`:
```yaml
# Calendar/scheduling pattern
# - Layout: month/week/day views + event detail sidebar
# - Components: date picker, event form, time slots
# - Navigation: prev/next month, today button, view switcher
# - Interactions: drag-and-drop events, recurring events
# - Patterns: timezone handling, conflict detection
```

Create `templates/use_cases/forms.yaml`:
```yaml
# Complex forms pattern
# - Layout: multi-step wizard or single-page with sections
# - Components: validation, autosave, progress indicator
# - Navigation: step indicators, prev/next buttons
# - Interactions: conditional fields, dynamic sections
# - Patterns: inline validation, error summaries, auto-complete
```

Create `templates/use_cases/search.yaml`:
```yaml
# Search/discovery pattern
# - Layout: search bar + filters sidebar + results grid/list
# - Components: autocomplete, filters, sorting, pagination
# - Navigation: breadcrumbs, back to results
# - Interactions: instant search, filter refinement
# - Patterns: debounced search, faceted navigation, type-ahead
```

**3. Integrate Tailwind 4**

Create `core/tailwind_generator.py`:
```python
# Tailwind 4 config generator
# - generate_tailwind_config() - create tailwind.config.js
# - merge_design_tokens() - combine industry + use case
# - apply_css_variables() - CSS custom properties
# - generate_theme_json() - theme.json for Tailwind
# - Support for Tailwind 4 features (container queries, etc.)
```

**4. Integrate Storybook**

Create `core/storybook_generator.py`:
```python
# Storybook component library generator
# - generate_storybook_config() - create .storybook/ structure
# - create_component_stories() - auto-generate .stories.tsx files
# - extract_components_from_spec() - parse PROJECT_SPEC for components
# - generate_docs() - Storybook MDX documentation
```

**5. Setup Visual Regression Testing**

Create `core/visual_regression.py`:
```python
# Visual regression testing with Playwright
# - capture_baseline() - take baseline screenshots
# - run_visual_tests() - compare current vs baseline
# - detect_differences() - pixel-diff algorithm
# - generate_report() - visual diff report with highlights
```

**6. Write Comprehensive Tests**

Create `tests/test_design_system_complete.py`:
```python
# Test coverage: 85%+ required
# - test_all_industry_profiles_load() - 8 industries
# - test_all_use_case_patterns_load() - 8 use cases
# - test_tailwind_config_generation()
# - test_storybook_generation()
# - test_visual_regression_baseline()
# - test_profile_merging_with_all_combinations()
# - test_design_token_consistency()
```

**7. Update Documentation**

Update `docs/DESIGN_SYSTEM.md`:
- Add all 8 industry profiles (complete list)
- Add all 8 use case patterns (complete list)
- Add Tailwind 4 integration guide
- Add Storybook setup instructions
- Add visual regression testing guide

#### Acceptance Criteria
- ✅ 5 new industry YAML files (Government, Legal, Nonprofit, Gaming, Manufacturing)
- ✅ 5 new use case YAML files (Chat, Video, Calendar, Forms, Search)
- ✅ Tailwind 4 integration working
- ✅ Storybook generator creates valid .stories files
- ✅ Visual regression tests capture baselines
- ✅ Test coverage 85%+
- ✅ All tests pass

#### Testing Commands
```bash
# Run tests
pytest tests/test_design_system_complete.py -v --cov=core/tailwind_generator.py --cov=core/storybook_generator.py

# Manual test
python -m cli.main design profile government chat
# Should load government.yaml + chat.yaml and merge
```

#### Commit & Push
```bash
git add .
git commit -m "feat: Complete design system with all 16 templates

- Add 5 industry profiles (Government, Legal, Nonprofit, Gaming, Manufacturing)
- Add 5 use case patterns (Chat, Video, Calendar, Forms, Search)
- Tailwind 4 integration
- Storybook component library generator
- Visual regression testing
- Test coverage: 85%+

🤖 Generated with Claude Code"
git push -u origin build/v3.1-design-system
```

#### Completion Signal
**DO NOT MERGE.** Push branch and wait for review. Report:
- ✅ All tasks complete
- ✅ Tests passing (X/X)
- ✅ Coverage: X%
- ✅ Branch: build/v3.1-design-system pushed
- ⏸️ Ready for review

---

### Build 1C - Week 1 Integration [MAIN BRANCH]
**Location:** `main` branch
**Duration:** 0.5 days
**Execute after 1A and 1B complete**

#### Prerequisites
Both Build 1A and Build 1B must be complete and pushed.

#### Task List

**1. Merge Build 1A (PRD Wizard)**
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git checkout main
git pull origin main
git merge build/v3.1-prd-wizard --no-ff -m "Merge: Complete PRD wizard with Opus integration"
```

**2. Merge Build 1B (Design System)**
```bash
git merge build/v3.1-design-system --no-ff -m "Merge: Complete design system with all 16 templates"
```

**3. Resolve Any Conflicts**
```bash
# If conflicts in cli/main.py or similar:
# - Accept both changes
# - Ensure both command sets registered
# - Test both systems work
```

**4. Run Full Test Suite**
```bash
pytest tests/ -v --cov=. --cov-report=term-missing
# Target: 525+ tests passing, 82%+ coverage
```

**5. Integration Tests**
```bash
# Test PRD Wizard
python -m cli.main spec wizard
# Verify: Uses real Opus, generates valid spec

# Test Design System
python -m cli.main design profile government chat
# Verify: Loads all 16 templates correctly

# Test Integration
# Run wizard with government + chat, verify spec includes design tokens
```

**6. Update Version**

Update `README.md` (line 7):
```markdown
[![Version](https://img.shields.io/badge/version-3.1.0--alpha.1-blue)]
```

Update `pyproject.toml` (line 7):
```toml
version = "3.1.0a1"
```

**7. Update CHANGELOG**

Add to `CHANGELOG.md`:
```markdown
## [3.1.0-alpha.1] - 2025-01-24

### Added
- Real Opus API integration for PRD wizard
- Model switching protocol (Opus → Sonnet handoff)
- Planning mode auto-detection
- 5 new industry profiles (Government, Legal, Nonprofit, Gaming, Manufacturing)
- 5 new use case patterns (Chat, Video, Calendar, Forms, Search)
- Tailwind 4 integration
- Storybook component library generator
- Visual regression testing with Playwright

### Improved
- PRD wizard test coverage: 17% → 85%
- Design system test coverage: 45% → 85%
```

**8. Commit Integration**
```bash
git add README.md pyproject.toml CHANGELOG.md
git commit -m "chore: Week 1 integration - v3.1.0-alpha.1

- Merged PRD wizard completion
- Merged design system completion
- All integration tests passing
- Coverage: 82%+

🤖 Generated with Claude Code"
```

**9. Tag Release**
```bash
git tag -a v3.1.0-alpha.1 -m "BuildRunner 3.1.0-alpha.1

Week 1 Complete:
✅ PRD wizard with real Opus integration
✅ Complete design system (16 templates)
✅ Tailwind 4 + Storybook + Visual regression

Test Coverage: 82%+
Tests Passing: 530+"
```

**10. Push to GitHub**
```bash
git push origin main
git push origin v3.1.0-alpha.1
```

**11. Cleanup Worktrees**
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git worktree remove ../br3-prd-wizard
git worktree remove ../br3-design-system
git branch -d build/v3.1-prd-wizard
git branch -d build/v3.1-design-system
```

#### Acceptance Criteria
- ✅ Both branches merged cleanly
- ✅ No merge conflicts
- ✅ All tests passing (530+)
- ✅ Coverage 82%+
- ✅ Version updated to 3.1.0-alpha.1
- ✅ Tagged and pushed to GitHub
- ✅ Worktrees cleaned up

#### Completion Signal
Report:
- ✅ Week 1 integration complete
- ✅ v3.1.0-alpha.1 tagged and pushed
- ✅ Tests: X passing, coverage: X%
- ✅ Ready for Week 2 builds

---

### Build 2A - AI Code Review Core [PARALLEL]
**Worktree:** `../br3-ai-review`
**Branch:** `build/v3.1-ai-review`
**Duration:** 1 week
**Execute in parallel with Build 2B**

#### Prerequisites
```bash
cd /Users/byronhudson/Projects/BuildRunner3
```

#### Git Worktree Setup
```bash
git worktree add ../br3-ai-review -b build/v3.1-ai-review
cd ../br3-ai-review
```

#### Dependencies
```bash
pip install anthropic>=0.18.0 -q  # For Claude API
pip install radon -q  # Code metrics
pip install astroid pylint -q  # Static analysis
pip install bandit -q  # Security scanning
pip install pytest pytest-asyncio pytest-cov -q
```

#### Task List

**1. Create AI Code Review Engine**

Create `core/ai_code_review.py`:
```python
# AI-powered code review engine
# - CodeReviewer class with async methods
# - review_diff() - review git diff before commit
# - analyze_architecture() - check against PROJECT_SPEC.md
# - detect_patterns() - identify architectural patterns
# - suggest_improvements() - actionable suggestions
# - calculate_review_score() - 0-100 quality score
# Uses Claude API (Sonnet) for analysis
```

**2. Create Architectural Pattern Analyzer**

Create `core/pattern_analyzer.py`:
```python
# Architectural pattern detection
# - detect_mvc_pattern() - Model-View-Controller
# - detect_repository_pattern() - Data access patterns
# - detect_factory_pattern() - Creational patterns
# - detect_singleton_pattern() - Singleton anti-patterns
# - detect_observer_pattern() - Event-driven patterns
# - analyze_layering() - Check layer violations
# - check_separation_of_concerns() - Single responsibility
```

**3. Create Performance Bottleneck Detector**

Create `core/performance_analyzer.py`:
```python
# Performance bottleneck detection
# - analyze_complexity() - Cyclomatic complexity (radon)
# - detect_n_plus_one() - Database query patterns
# - detect_memory_leaks() - Potential memory issues
# - detect_blocking_io() - Async/sync mismatches
# - analyze_algorithmic_complexity() - Big-O analysis
# - suggest_optimizations() - Performance improvements
```

**4. Create Code Smell Identifier**

Create `core/code_smell_detector.py`:
```python
# Code smell detection
# - detect_long_methods() - Methods > 50 lines
# - detect_large_classes() - Classes > 500 lines
# - detect_duplicate_code() - Copy-paste detection
# - detect_dead_code() - Unused functions/variables
# - detect_magic_numbers() - Hard-coded values
# - detect_god_objects() - Too many responsibilities
# - detect_feature_envy() - Wrong object responsibilities
```

**5. Create Security Vulnerability Scanner**

Create `core/security_scanner.py`:
```python
# Security vulnerability scanning
# - scan_with_bandit() - Run bandit security checks
# - detect_sql_injection() - SQL injection risks
# - detect_xss_vulnerabilities() - XSS risks
# - detect_hardcoded_secrets() - API keys, passwords
# - check_dependency_vulnerabilities() - Known CVEs
# - analyze_auth_flows() - Authentication issues
```

**6. Create Pre-Commit Hook Integration**

Create `.buildrunner/hooks/pre-commit-ai-review`:
```bash
#!/bin/bash
# Pre-commit AI code review
# - Get staged diff
# - Call br review --diff
# - Show review results
# - Block commit if critical issues (score < 60)
# - Allow override with --no-verify
```

Update `cli/review_commands.py`:
```python
# CLI commands for code review
# - br review - Review current changes
# - br review --diff <file> - Review specific file
# - br review --commit <sha> - Review past commit
# - br review --score - Show only score
# - br review --fix - Auto-apply safe fixes
```

**7. Write Comprehensive Tests**

Create `tests/test_ai_code_review.py`:
```python
# Test coverage: 90%+ required
# - test_review_diff() - Mock Claude API
# - test_pattern_detection() - Each pattern type
# - test_performance_analysis() - Complexity detection
# - test_code_smell_detection() - Each smell type
# - test_security_scanning() - Each vulnerability type
# - test_pre_commit_hook() - Hook behavior
# - test_review_scoring() - Score calculation
# - test_auto_fix() - Safe fix application
```

**8. Create Documentation**

Create `docs/AI_CODE_REVIEW.md`:
```markdown
# AI Code Review System

## Overview
Automated code review using Claude API

## Features
- Pre-commit AI review
- Architectural pattern analysis
- Performance bottleneck detection
- Code smell identification
- Security vulnerability scanning

## Usage
\`\`\`bash
# Review current changes
br review

# Review specific file
br review --diff src/core/feature_registry.py

# Auto-fix safe issues
br review --fix
\`\`\`

## Configuration
\`\`\`.buildrunner/config.yaml
ai_review:
  enabled: true
  min_score: 70
  block_on_critical: true
  auto_fix_safe: false
\`\`\`

## Pre-Commit Hook
Automatically reviews staged changes before commit.

## Review Criteria
- Architectural patterns
- Performance (cyclomatic complexity, Big-O)
- Code smells (long methods, god objects)
- Security (SQL injection, XSS, secrets)
- Best practices (type hints, docstrings)

## Scoring
- 90-100: Excellent
- 70-89: Good
- 50-69: Needs improvement
- 0-49: Critical issues (blocks commit)
```

#### Acceptance Criteria
- ✅ AI code review engine working with Claude API
- ✅ Architectural pattern detection accurate
- ✅ Performance bottleneck detection functional
- ✅ Code smell detector identifies all major smells
- ✅ Security scanner catches common vulnerabilities
- ✅ Pre-commit hook integrates smoothly
- ✅ Test coverage 90%+
- ✅ All tests pass

#### Testing Commands
```bash
# Run tests
pytest tests/test_ai_code_review.py -v --cov=core/ai_code_review.py --cov=core/pattern_analyzer.py --cov=core/performance_analyzer.py

# Manual test
echo "print('test')" > test_file.py
git add test_file.py
python -m cli.main review --diff test_file.py
# Should show AI review with score
```

#### Commit & Push
```bash
git add .
git commit -m "feat: Add AI code review system

- AI-powered code review engine with Claude
- Architectural pattern analysis
- Performance bottleneck detection
- Code smell identification
- Security vulnerability scanning
- Pre-commit hook integration
- Test coverage: 90%+

🤖 Generated with Claude Code"
git push -u origin build/v3.1-ai-review
```

#### Completion Signal
**DO NOT MERGE.** Push branch and wait for review. Report:
- ✅ All tasks complete
- ✅ Tests passing (X/X)
- ✅ Coverage: X%
- ✅ Branch: build/v3.1-ai-review pushed
- ⏸️ Ready for review

---

### Build 2B - Synapse Profile Integration [PARALLEL]
**Worktree:** `../br3-synapse-profiles`
**Branch:** `build/v3.1-synapse-profiles`
**Duration:** 1 week
**Execute in parallel with Build 2A**

#### Prerequisites
```bash
cd /Users/byronhudson/Projects/BuildRunner3
```

#### Git Worktree Setup
```bash
git worktree add ../br3-synapse-profiles -b build/v3.1-synapse-profiles
cd ../br3-synapse-profiles
```

#### Dependencies
```bash
pip install anthropic>=0.18.0 -q
pip install pyyaml -q
pip install httpx -q  # For API calls to research
pip install pytest pytest-asyncio pytest-cov -q
```

#### Task List

**1. Import Synapse Industry Database**

Create `core/synapse_profile_manager.py`:
```python
# Synapse profile database manager
# - SynapseProfileManager class
# - load_industry_database() - load all 147 industry profiles
# - get_industry_profile(industry_name) - retrieve specific profile
# - list_available_industries() - list all industries
# - get_profile_metadata() - profile version, last updated, etc.
# - validate_profile_schema() - ensure profile compatibility
# - migrate_legacy_profiles() - update old format profiles
# Import exact same database structure as Synapse
```

**2. Import Synapse Profile Templates**

Copy `synapse/profiles/` directory structure:
```
templates/
├── industries/          # 147 industry profiles (exact copy from Synapse)
│   ├── healthcare/
│   ├── fintech/
│   ├── government/
│   ├── legal/
│   ├── education/
│   ├── retail/
│   ├── manufacturing/
│   └── ... (140 more)
└── use_cases/          # All use case patterns from Synapse
    ├── dashboard/
    ├── marketplace/
    ├── chat/
    ├── video/
    └── ... (all Synapse patterns)
```

**3. Create Industry Discovery & Research System**

Create `core/industry_discovery.py`:
```python
# Industry discovery and research (exact same as Synapse)
# - IndustryDiscovery class
# - discover_new_industry(industry_name) - research unknown industry
# - generate_profile_from_research() - create profile from research
# - validate_with_opus() - use Opus for validation
# - save_to_pending_profiles() - save for review
# - Uses same API endpoints as Synapse
# - Uses same research methodology as Synapse
# - Uses same profile generation logic as Synapse
```

**4. Migrate Existing BuildRunner Profiles**

Create `core/profile_migrator.py`:
```python
# Migrate existing BR3 profiles to Synapse format
# - migrate_br3_to_synapse() - convert BR3 profiles
# - preserve_custom_fields() - keep BR3-specific data
# - merge_with_synapse_profile() - combine BR3 + Synapse
# - validate_migration() - ensure no data loss
# - backup_original_profiles() - save originals
```

**5. Update Design Profiler for Synapse Compatibility**

Update `core/design_profiler.py`:
```python
# Update to work with Synapse profiles
# - Use SynapseProfileManager instead of local YAML
# - Support full Synapse schema (all fields)
# - Handle industry categories/subcategories
# - Support profile versioning
# - Add profile caching for performance
```

**6. Update CLI Commands**

Update `cli/spec_commands.py`:
```python
# Add Synapse profile commands
# - br design list-industries - Show all 147 industries
# - br design discover <industry> - Research new industry
# - br design profile <industry> <use_case> - Use Synapse profiles
# - br design migrate - Migrate BR3 profiles to Synapse format
```

**7. Write Comprehensive Tests**

Create `tests/test_synapse_integration.py`:
```python
# Test coverage: 90%+ required
# - test_load_industry_database()
# - test_get_industry_profile()
# - test_discover_new_industry()
# - test_profile_migration()
# - test_synapse_compatibility()
# - test_profile_caching()
# - test_research_api_calls()
# - test_opus_validation()
```

**8. Create Documentation**

Create `docs/SYNAPSE_INTEGRATION.md`:
```markdown
# Synapse Profile Integration

## Overview
Complete integration with Synapse industry database (147 profiles)

## Features
- All 147 industry profiles from Synapse
- Industry discovery & research (same as Synapse)
- Profile migration for BR3 compatibility
- Full Synapse schema support
- Profile versioning and metadata

## Usage
\`\`\`bash
# List all 147 industries
br design list-industries

# Research new industry
br design discover "quantum-computing"

# Use Synapse profile
br design profile healthcare dashboard

# Migrate BR3 profiles
br design migrate
\`\`\`

## Discovery Process
Same methodology as Synapse:
1. Research industry characteristics
2. Generate profile from research
3. Validate with Opus
4. Save to pending profiles
5. Manual review and approval

## Profile Schema
Full Synapse compatibility:
- Industry metadata
- Design tokens
- Compliance requirements
- Use case patterns
- Component libraries
```

#### Acceptance Criteria
- ✅ All 147 Synapse industry profiles imported
- ✅ Industry discovery works same as Synapse
- ✅ BR3 profiles successfully migrated
- ✅ Design profiler works with Synapse profiles
- ✅ CLI commands functional
- ✅ Test coverage 90%+
- ✅ All tests pass

#### Testing Commands
```bash
# Run tests
pytest tests/test_synapse_integration.py -v --cov=core/synapse_profile_manager.py --cov=core/industry_discovery.py

# Manual test
python -m cli.main design list-industries
# Should show 147 industries

python -m cli.main design profile healthcare dashboard
# Should use Synapse profiles
```

#### Commit & Push
```bash
git add .
git commit -m "feat: Integrate Synapse industry database

- Import all 147 industry profiles from Synapse
- Industry discovery & research (same as Synapse)
- Profile migration for BR3 compatibility
- Updated design profiler for Synapse profiles
- Full CLI integration
- Test coverage: 90%+

🤖 Generated with Claude Code"
git push -u origin build/v3.1-synapse-profiles
```

#### Completion Signal
**DO NOT MERGE.** Push branch and wait for review. Report:
- ✅ All tasks complete
- ✅ Tests passing (X/X)
- ✅ Coverage: X%
- ✅ Branch: build/v3.1-synapse-profiles pushed
- ⏸️ Ready for review

---

### Build 2C - Week 2 Integration [MAIN BRANCH]
**Location:** `main` branch
**Duration:** 0.5 days
**Execute after 2A and 2B complete**

#### Prerequisites
Both Build 2A and Build 2B must be complete and pushed.

#### Task List

**1. Merge Build 2A (AI Review)**
```bash
cd /Users/byronhudson/Projects/BuildRunner3
git checkout main
git pull origin main
git merge build/v3.1-ai-review --no-ff -m "Merge: AI code review system"
```

**2. Merge Build 2B (Synapse Profiles)**
```bash
git merge build/v3.1-synapse-profiles --no-ff -m "Merge: Synapse industry database integration"
```

**3. Integration Tests**
```bash
# Test AI Review
python -m cli.main review
# Verify: Shows review with score

# Test Synapse Profiles
python -m cli.main design list-industries
# Verify: Shows 147 industries

python -m cli.main design profile healthcare dashboard
# Verify: Uses Synapse profile

# Test Integration: Review + Synapse
# Review should check design patterns against Synapse profiles
```

**4. Update Version**
```markdown
[![Version](https://img.shields.io/badge/version-3.1.0--alpha.2-blue)]
```

**5. Tag and Push**
```bash
git tag -a v3.1.0-alpha.2 -m "BuildRunner 3.1.0-alpha.2

Week 2 Complete:
✅ AI code review with Claude
✅ Synapse industry database (147 profiles)
✅ Industry discovery & research system"
git push origin main
git push origin v3.1.0-alpha.2
```

**6. Cleanup**
```bash
git worktree remove ../br3-ai-review
git worktree remove ../br3-synapse-profiles
git branch -d build/v3.1-ai-review
git branch -d build/v3.1-synapse-profiles
```

#### Completion Signal
Report:
- ✅ Week 2 integration complete
- ✅ v3.1.0-alpha.2 tagged and pushed
- ✅ Ready for Week 3 builds

---

## IMPORTANT: Build Plan Update (Week 2)

**Build 2B has been replaced with Synapse Profile Integration** (originally was Refactoring Engine):
- Priority shift to integrate Synapse's 147 industry profiles
- Industry discovery & research system (same as Synapse)
- Full compatibility with existing Synapse infrastructure
- Refactoring Engine moved to Week 3 or later

## Continue with Weeks 3-20...

### Build 3A - Refactoring Engine [DEFERRED FROM WEEK 2]
*Original Build 2B content - now scheduled for Week 3*

[The pattern continues for all 20 weeks with same structure:
- Parallel builds (A, B) with atomic task lists
- Integration build (C) after both complete
- Each build has: Setup, Dependencies, Tasks, Tests, Docs, Acceptance Criteria
- Each integration has: Merge, Test, Version, Tag, Cleanup
- Progressive version tags: alpha → beta → rc → release]

---

## Key Patterns

### Every Parallel Build Includes:
1. Git worktree setup commands
2. Dependency installation
3. Detailed task list (files to create, code to write)
4. Test specifications (coverage targets)
5. Documentation requirements
6. Acceptance criteria
7. Testing commands
8. Commit message template
9. Push command
10. "DO NOT MERGE" instruction

### Every Integration Build Includes:
1. Merge commands for both branches
2. Conflict resolution guidance
3. Integration test commands
4. Version update
5. CHANGELOG update
6. Tag creation with release notes
7. Push to GitHub
8. Worktree cleanup
9. Branch deletion
10. Completion signal

### Testing Standards:
- Core systems: 90%+ coverage
- Enhancement systems: 85%+ coverage
- CLI interfaces: 80%+ coverage
- All tests must pass before merge

### Documentation Standards:
- Every feature gets dedicated .md file
- Usage examples required
- Configuration documented
- Troubleshooting section
- API reference if applicable

---

**This pattern repeats for all 20 weeks, creating 60 atomic builds (40 parallel + 20 integrations).**
