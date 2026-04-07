# CLAUDE.md - Persistent AI Memory

This file maintains context across AI sessions for BuildRunner 3.0 development.

## Current Work

**Status:** Initial setup - Build 1A in progress
**Active Branch:** build/week1-feature-registry
**Focus:** Feature Registry System + AI Context Management

## Architecture Decisions

### Feature Registry
- **Storage:** JSON-based (.buildrunner/features.json)
- **Operations:** CRUD via FeatureRegistry class
- **Progress Tracking:** Auto-calculated metrics (complete/in_progress/planned)
- **Status Generation:** Auto-generated STATUS.md from features data

### AI Context Management
- **CLAUDE.md:** This file - persistent memory across sessions
- **context/:** Segmented context files for specific concerns
  - architecture.md - Design decisions and patterns
  - current-work.md - Active tasks and WIP
  - blockers.md - Known issues and blockers
  - test-results.md - Latest test outputs

## Lessons Learned

- Python 3.14 requires venv for package installation (system packages protected)
- Git worktrees enable parallel development without branch switching
- Segmented context prevents AI context overload

## Next Steps

1. Complete AIContextManager implementation
2. Write comprehensive tests (90%+ coverage target)
3. Create example features.json
4. Merge Build 1A when complete

---

*Last Updated: {datetime}*
*This file is read/written by AI assistants to maintain project context*
