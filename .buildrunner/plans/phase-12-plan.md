# Phase 12: Integration Rewire — Implementation Plan

## Tasks

1. **appdesign.md Step 1.5** — Replace 7-step inline Design Discovery with /design delegation. Check DESIGN_SPEC.md → load. Check .design-declined → skip. Neither → suggest /design or skip.
2. **begin.md Step 1.5** — Add .design-declined gate. If frontend detected + no spec + no declined → ask user about /design. Yes → invoke /design. No → write .design-declined.
3. **autopilot note** — Add design gate note to begin.md rules or Step 1.5 noting /autopilot respects same gate.

## Tests
Non-testable (skill/doc modifications only). TDD skipped.

## Files Modified
- ~/.claude/commands/appdesign.md (MODIFY)
- ~/.claude/commands/begin.md (MODIFY)
