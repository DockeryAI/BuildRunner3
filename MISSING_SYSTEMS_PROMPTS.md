# BuildRunner 3.0 - Missing Systems Execution Prompts

**Instructions:** Copy and paste each prompt below into a new Claude Code session. Each prompt is self-contained and references the complete build plan.

---

## Week 1: Core Enhancement Systems

### Prompt 1A: Code Quality + Gap Analysis (Parallel)

```
Execute Build 1A (Code Quality System + Gap Analysis System) from /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md lines 8-160.

Setup git worktree:
cd /Users/byronhudson/Projects/BuildRunner3 && git worktree add ../br3-quality-gaps -b build/quality-gaps && cd ../br3-quality-gaps

Implement both systems with 85%+ test coverage. All implementation tasks, file structures, tests, and acceptance criteria are in BUILD_PLAN_MISSING_SYSTEMS.md.

Signal when complete for review before merging.
```

### Prompt 1B: Architecture Guard + Self-Service (Parallel)

```
Execute Build 1B (Architecture Guard System + Self-Service Execution System) from /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md lines 162-314.

Setup git worktree:
cd /Users/byronhudson/Projects/BuildRunner3 && git worktree add ../br3-arch-service -b build/arch-service && cd ../br3-arch-service

Implement both systems with 85%+ test coverage. All implementation tasks, file structures, tests, and acceptance criteria are in BUILD_PLAN_MISSING_SYSTEMS.md.

Signal when complete for review before merging.
```

### Prompt 1C: Week 1 Integration (After 1A and 1B)

```
Execute Build 1C (Week 1 Integration) from /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md lines 316-357.

Prerequisites: Builds 1A and 1B complete and reviewed.

Tasks:
1. Merge build/quality-gaps branch to main
2. Merge build/arch-service branch to main
3. Run full test suite (expect 300+ tests passing)
4. Verify all 4 new CLI commands work
5. Tag v3.0.0-rc.1
6. Clean up worktrees

All integration steps in BUILD_PLAN_MISSING_SYSTEMS.md.

Signal when complete for review.
```

---

## Week 2: Complete Documentation

### Prompt 2A: Core Documentation (Parallel)

```
Execute Build 2A (Missing Core Documentation) from /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md lines 359-510.

Setup git worktree:
cd /Users/byronhudson/Projects/BuildRunner3 && git worktree add ../br3-core-docs -b build/core-docs && cd ../br3-core-docs

Create 9 documentation files:
- CODE_QUALITY.md, GAP_ANALYSIS.md, ARCHITECTURE_GUARD.md, SELF_SERVICE.md
- DESIGN_SYSTEM.md, INDUSTRY_PROFILES.md, INSTALLATION.md
- LICENSE, CODE_OF_CONDUCT.md

All doc specifications and required sections in BUILD_PLAN_MISSING_SYSTEMS.md.

Signal when complete for review before merging.
```

### Prompt 2B: Tutorial Guides (Parallel)

```
Execute Build 2B (Tutorial Guides) from /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md lines 512-660.

Setup git worktree:
cd /Users/byronhudson/Projects/BuildRunner3 && git worktree add ../br3-tutorials -b build/tutorials && cd ../br3-tutorials

Create 5 tutorial guides in docs/tutorials/:
- FIRST_PROJECT.md (complete walkthrough)
- DESIGN_SYSTEM_GUIDE.md (industry profiles usage)
- QUALITY_GATES.md (code standards setup)
- PARALLEL_BUILDS.md (multi-feature orchestration)
- COMPLETION_ASSURANCE.md (gap analyzer usage)

All tutorial specifications in BUILD_PLAN_MISSING_SYSTEMS.md.

Signal when complete for review before merging.
```

### Prompt 2C: Week 2 Integration (After 2A and 2B)

```
Execute Build 2C (Week 2 Integration) from /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md lines 662-697.

Prerequisites: Builds 2A and 2B complete and reviewed.

Tasks:
1. Merge build/core-docs branch to main
2. Merge build/tutorials branch to main
3. Verify all README/QUICKSTART links work (no 404s)
4. Verify all 8 enhancement systems documented
5. Tag v3.0.0-rc.2
6. Clean up worktrees

All integration steps in BUILD_PLAN_MISSING_SYSTEMS.md.

Signal when complete for review.
```

---

## Week 3: Final Polish & Release

### Prompt 3A: Test Fixes + Final Validation (Sequential)

```
Execute Build 3A (Test Fixes + Final Validation) from /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md lines 699-769.

Working directory: /Users/byronhudson/Projects/BuildRunner3 (main branch)

Tasks:
1. Fix 6 test collection errors (test_api.py, test_api_config.py, etc.)
2. Run pytest with coverage measurement
3. Ensure 500+ tests passing
4. Ensure 85%+ code coverage
5. Verify all 8 enhancement systems work end-to-end
6. Verify all CLI commands work

All fix specifications and validation steps in BUILD_PLAN_MISSING_SYSTEMS.md.

Signal when complete for review.
```

### Prompt 3B: Release v3.0.0 (Sequential, after 3A)

```
Execute Build 3B (Release v3.0.0) from /Users/byronhudson/Projects/BuildRunner3/.buildrunner/BUILD_PLAN_MISSING_SYSTEMS.md lines 771-834.

Prerequisites: Build 3A complete with all tests passing and 85%+ coverage.

Working directory: /Users/byronhudson/Projects/BuildRunner3 (main branch)

Tasks:
1. Update all version markers to v3.0.0 (remove beta/rc tags)
2. Verify pyproject.toml: version="3.0.0", status="Production/Stable"
3. Create RELEASE_NOTES_v3.0.0_FINAL.md
4. Run final acceptance tests
5. Tag v3.0.0 (final production release)

All release steps and acceptance criteria in BUILD_PLAN_MISSING_SYSTEMS.md.

Signal when complete for review. DO NOT publish to PyPI until approved.
```

---

## Quick Reference

### Execution Order

**Week 1:**
1. Execute Prompt 1A (in session A)
2. Execute Prompt 1B (in session B, parallel)
3. Review both branches
4. Execute Prompt 1C (merge and integrate)

**Week 2:**
5. Execute Prompt 2A (in session A)
6. Execute Prompt 2B (in session B, parallel)
7. Review both branches
8. Execute Prompt 2C (merge and integrate)

**Week 3:**
9. Execute Prompt 3A (test fixes)
10. Review results
11. Execute Prompt 3B (final release)

### Expected Timeline

- Week 1: 8-12 hours (2 parallel builds)
- Week 2: 6-8 hours (2 parallel builds)
- Week 3: 4-6 hours (sequential)

**Total:** ~18-26 hours to v3.0.0 production

### Success Metrics

- ✅ All 8 enhancement systems working
- ✅ 500+ tests passing
- ✅ 85%+ code coverage
- ✅ All documentation complete
- ✅ All CLI commands functional
- ✅ No test collection errors
- ✅ Production/Stable status justified

---

## Support Files

- **BUILD_PLAN_MISSING_SYSTEMS.md** - Complete implementation specifications
- **MISSING_SYSTEMS_SUMMARY.md** - Executive summary and rationale
- **GAP_ANALYSIS_REALITY_CHECK.md** - Current state assessment
- **README.md** - Will be accurate after completion
- **QUICKSTART.md** - Will have working commands after completion

---

## Notes

- Each prompt is designed for copy-paste into Claude Code
- All implementation details are in BUILD_PLAN_MISSING_SYSTEMS.md
- Git worktrees enable parallel development without conflicts
- Signal "complete for review" before any merging
- DO NOT publish to PyPI until final approval after 3B

---

**Ready to start?** Begin with Prompts 1A and 1B in parallel sessions.
