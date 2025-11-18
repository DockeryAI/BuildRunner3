# Architecture Decisions

## Feature Registry System

**Pattern:** Repository pattern with JSON persistence

**Rationale:**
- JSON is human-readable and git-friendly
- No database dependency for local development
- Easy to version control and diff
- Supabase sync optional (Week 2)

**Key Classes:**
- `FeatureRegistry`: CRUD operations for features
- `StatusGenerator`: Auto-generates STATUS.md
- `AIContextManager`: Manages AI memory and context

## File Structure

```
.buildrunner/
├── features.json       # Source of truth for features
├── STATUS.md          # Auto-generated status report
├── CLAUDE.md          # Persistent AI memory
├── context/
│   ├── architecture.md
│   ├── current-work.md
│   ├── blockers.md
│   └── test-results.md
├── governance/
│   └── governance.yaml
├── standards/
│   └── CODING_STANDARDS.md
└── commands/
    └── *.md (slash commands)
```

## Design Principles

1. **Git as Source of Truth:** All governance data in git
2. **Auto-Generated Artifacts:** STATUS.md generated from features.json
3. **AI-Native:** CLAUDE.md and context files for AI memory
4. **Progressive Enhancement:** Core works offline, Supabase optional
5. **Test-Driven:** 90%+ coverage requirement

---

*Updated during Build 1A*
