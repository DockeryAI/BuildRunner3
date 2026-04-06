# Phase 1 Plan: The Setlist Skill

## Tasks

1. **Create `~/.claude/docs/setlist-explore-lenses.md`** — Three lenses (Feature Trace, Impact Analysis, Semantic Similarity) each with output template. Concise reference doc.
2. **Create `~/.claude/docs/setlist-plan-format.md`** — Plan format: WHAT/WHY/VERIFY per task, 40-line max, single-function decomposition rules.
3. **Create `~/.claude/commands/setlist.md`** — Main skill file: 6-phase pipeline (Tune Up, Soundcheck, Rehearsal, Jam Session, Showtime), complexity classifier, graceful fallback for all cluster nodes.

## Tests

Non-testable: all deliverables are markdown instruction files (Claude skill + reference docs). No unit tests apply. TDD skipped.

## Approach

- Docs first (tasks 1-2), then skill file (task 3) which references the docs
- All research findings (Lusser's Law, TDAD, Self-Refine limits, context rot, plan granularity, producer/verifier separation) embedded as behavioral constraints, not verbose explanations
- Cluster API calls via cluster-check.sh, never hard-coded IPs
- Fallback at every cluster touchpoint
