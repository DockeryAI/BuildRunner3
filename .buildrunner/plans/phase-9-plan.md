# Phase 9 Plan: Discovery Upgrade + Audit Fixes

## Overview

Expand the /design discovery from 5 questions to 13 questions across structured categories, soften the Aaker scoring from rigid lookup to guided derivation, expand convergence guards for all archetypes, and add Tailwind build rule.

## Tasks

### Task 1: Replace 5-question block with 13-question block (Step 1.5a)

Replace lines 66-92 (current 5-question block) with 13 questions organized in XML-tagged categories: `<business>`, `<goals>`, `<audience>`, `<personality>`, `<landscape>`, `<constraints>`. Questions cover business context, design goals, audience details, brand personality sliders, competitor landscape, and hard constraints.

### Task 2: Add multishot example block

Add an `<example_response>` block after the 13 questions showing a completed discovery response for a sample project (food delivery app or B2B SaaS). Helps users understand expected answer depth and format.

### Task 3: Soften Aaker scoring (Step 1.5b)

Replace the fixed lookup table at lines 97-118 with a guided derivation approach using ranges. Instead of "answer a → Sincerity 0.8", use "derive considering these associations" with slider inputs from Q7-Q10. Add personality slider anchor examples (Nike = high Excitement, law firm = high Competence) so users calibrate placements.

### Task 4: Add scope constraint

Add a note before the questions: "These answers feed visual direction only — not technical architecture or content strategy." Sets user expectations.

### Task 5: Rewrite Step 1.5c brand profile output

Update the brand profile template to reflect all 13-question categories: business summary, goal, audience type, 4 slider positions, personality words, emotional target, competitor map, references, exclusions, constraints.

### Task 6: Expand convergence_guards table (Step 4.3b)

Add INSTEAD-pattern rows for all remaining dashboard + app archetypes (currently only has 15 rows covering mostly website archetypes). Need rows for: Dense data grid, KPI editorial, Kanban/workflow, Map/spatial, Activity stream, Notebook/report, Command dashboard, Split-pane, Tile mosaic, Status wall, Inbox zero, Conversational, Search-first, Visual feed, Magazine editorial, Tab sections, Drawer navigation, Timeline/stories, Card stack, Map-centric, Radial/gesture, Split-view tablet, Onboarding flow, Dashboard widget.

### Task 7: Add Tailwind build rule (Step 4.3)

Add rule: "All 4 mockups use Tailwind for layout/spacing/typography, inline styles only for palette hex values."

### Task 8: Update user_gates step references

After the Step 1.5a expansion, verify the user_gates list at lines 1305-1310 still references correct steps. The new 13-question block doesn't change step numbers, but verify all gate references are accurate.

### Task 9: Commit to ~/.claude git repo

Commit all changes to the ~/.claude git repository.

## Tests

- Non-testable (skill file modification, no code to unit test). Skip TDD gate.

## Execution Order

Sequential: Tasks 1-8 are all edits to the same file, then Task 9 commits.
