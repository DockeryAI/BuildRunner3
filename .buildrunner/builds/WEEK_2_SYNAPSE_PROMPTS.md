# Week 2 Build Prompts - AI Review + Synapse Integration

**IMPORTANT UPDATE:** Build 2B now integrates Synapse's 147 industry profiles database

---

## Prompt 2A: AI Code Review System

```
You are building the AI Code Review System for BuildRunner 3.1.

CONTEXT:
BuildRunner needs an AI-powered code review system that analyzes code before commits, detects patterns, identifies performance issues, and suggests improvements using Claude API.

CRITICAL RULES:
1. Work in batches of 2-3 tasks maximum
2. Update CLAUDE.md after each task
3. Test each component before moving on
4. STOP at verification gates

EXECUTION:
1. Setup worktree: git worktree add ../br3-ai-review -b build/v3.1-ai-review
2. Navigate: cd ../br3-ai-review
3. Initialize CLAUDE.md for state tracking
4. Work on these task batches:

BATCH 1: Core Review Engine (3 tasks, 4 hours)
- Task 1: Create core/ai_code_review.py
  - CodeReviewer class with async methods
  - review_diff() to review git diffs
  - analyze_architecture() to check against PROJECT_SPEC.md
  - Uses Claude API (Sonnet) for analysis
  - Include tests in tests/test_ai_code_review.py

- Task 2: Create core/pattern_analyzer.py
  - Detect MVC, repository, factory patterns
  - Check layer violations
  - Verify separation of concerns
  - Include tests

- Task 3: Create core/performance_analyzer.py
  - Analyze cyclomatic complexity (use radon)
  - Detect N+1 queries, memory leaks
  - Big-O analysis
  - Include tests

VERIFICATION GATE: After Batch 1, verify all tests pass, 90% coverage

BATCH 2: Detection & Integration (3 tasks, 4 hours)
- Task 4: Create core/code_smell_detector.py
- Task 5: Create core/security_scanner.py
- Task 6: Create pre-commit hook and CLI commands

Dependencies to install:
pip install anthropic>=0.18.0 radon astroid pylint bandit pytest pytest-asyncio pytest-cov -q

Report completion after each batch. DO NOT proceed past verification gates without approval.

Begin execution now.
```

---

## Prompt 2B: Synapse Profile Integration

```
You are integrating the Synapse industry profile database into BuildRunner 3.1.

CONTEXT:
BuildRunner needs to import Synapse's complete industry database of 147 profiles, along with its industry discovery and research system. This replaces the limited 8-profile system with a comprehensive industry knowledge base.

CRITICAL RULES:
1. Work in batches of 2-3 tasks maximum
2. Update CLAUDE.md after each task
3. Import EXACT Synapse structure and methodology
4. STOP at verification gates

EXECUTION:
1. Setup worktree: git worktree add ../br3-synapse-profiles -b build/v3.1-synapse-profiles
2. Navigate: cd ../br3-synapse-profiles
3. Initialize CLAUDE.md for state tracking
4. Work on these task batches:

BATCH 1: Import Synapse Database (2 tasks, 3 hours)
- Task 1: Create core/synapse_profile_manager.py
  - SynapseProfileManager class
  - load_industry_database() for all 147 profiles
  - get_industry_profile() to retrieve specific profiles
  - list_available_industries() to show all
  - Import exact Synapse database structure
  - Include tests in tests/test_synapse_integration.py

- Task 2: Copy Synapse profile templates
  - Create templates/industries/ with 147 industry subdirectories
  - Copy all profile YAML files from Synapse format
  - Create templates/use_cases/ with all Synapse patterns
  - Structure must match Synapse exactly:
    templates/industries/healthcare/
    templates/industries/fintech/
    ... (145 more)

VERIFICATION GATE: Verify 147 profiles imported, tests pass

BATCH 2: Discovery & Migration (3 tasks, 4 hours)
- Task 3: Create core/industry_discovery.py
  - IndustryDiscovery class (same as Synapse)
  - discover_new_industry() for unknown industries
  - generate_profile_from_research()
  - validate_with_opus() using Opus API
  - Use same research methodology as Synapse

- Task 4: Create core/profile_migrator.py
  - Migrate existing BR3 profiles to Synapse format
  - preserve_custom_fields() for BR3 data
  - merge_with_synapse_profile()

- Task 5: Update core/design_profiler.py
  - Use SynapseProfileManager instead of local YAML
  - Support full Synapse schema
  - Handle industry categories/subcategories

BATCH 3: CLI & Documentation (2 tasks, 2 hours)
- Task 6: Update CLI commands
  - br design list-industries (show all 147)
  - br design discover <industry>
  - br design migrate

- Task 7: Create docs/SYNAPSE_INTEGRATION.md

Dependencies to install:
pip install anthropic>=0.18.0 pyyaml httpx pytest pytest-asyncio pytest-cov -q

Key requirement: The system must be 100% compatible with Synapse's existing infrastructure and methodology.

Report completion after each batch. DO NOT proceed past verification gates without approval.

Begin execution now.
```

---

## Execution Instructions

### Parallel Execution (Recommended)

**Terminal 1:**
```bash
cd /Users/byronhudson/Projects/BuildRunner3
# Paste Prompt 2A (AI Code Review)
```

**Terminal 2:**
```bash
cd /Users/byronhudson/Projects/BuildRunner3
# Paste Prompt 2B (Synapse Profiles)
```

### Key Changes from Original Plan

1. **Build 2B completely replaced** - Now imports 147 Synapse industry profiles (not refactoring engine)
2. **Much larger scope** - 147 profiles vs 8 originally planned
3. **Industry discovery system** - Research capability for unknown industries
4. **Full Synapse compatibility** - Must match exact structure and methodology

### Expected Outcomes

**Build 2A (AI Review):**
- AI-powered code review before commits
- Pattern detection and analysis
- Performance bottleneck identification
- Security scanning
- Pre-commit hook integration

**Build 2B (Synapse Integration):**
- All 147 industry profiles imported
- Industry discovery for new industries
- Full compatibility with Synapse
- Migration path for existing BR3 profiles
- Research and validation using Opus

### Monitoring

```bash
# Check AI Review progress
cd ../br3-ai-review && cat CLAUDE.md

# Check Synapse progress
cd ../br3-synapse-profiles && cat CLAUDE.md
```

---

## Integration (Build 2C)

After both complete:
1. Merge both branches to main
2. Test integration (AI review should use Synapse profiles for design validation)
3. Tag v3.1.0-alpha.2
4. Result: BuildRunner with comprehensive industry knowledge + AI review

---

## Why This Change Is Important

**Original plan:** 8 industry profiles (limited coverage)
**New plan:** 147 industry profiles from Synapse (comprehensive coverage)

This gives BuildRunner:
- Complete industry coverage
- Proven profile database from Synapse
- Industry discovery for emerging sectors
- Research-based profile generation
- Full compatibility with existing Synapse infrastructure

The AI Review system can now validate code against 147 industry-specific patterns instead of just 8!