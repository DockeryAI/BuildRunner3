# Phase 14.8 Plan: Archetype Selection Algorithm

## Tasks

### T1: Add structural family definitions and affinity scoring table to Step 3.2

- Define 5 structural families: grid-based, scroll-based, spatial, dense, minimal
- Assign each archetype (all 3 tables: website, dashboard, app) to a structural family
- Add affinity table: each archetype maps to 2-3 axis positions it pairs well with (affinity) and 2-3 it conflicts with (anti-affinity)

### T2: Rename archetype table entries to remove axis-name overlap

- "Editorial scroll" → "Longform narrative" (prevents echo of "editorial-scroll" Layout axis)
- Other names that echo axis values get description-first labels
- Update all references throughout the file

### T3: Add mandatory archetype selection algorithm to Step 3.2

- Score each archetype against the direction's axis positions using affinity table
- Top 6 by score → shuffle → pick top 3
- Enforce structural family distance: 3 selected must come from 3 different families
- If constraint violated, re-pick from shuffled list respecting family rule

### T4: Add session archetype memory

- Before scoring, check `.buildrunner/design/session-log.md` for previously used archetypes
- Deprioritize (score penalty) archetypes used in last session
- If no session log exists, skip this step

### T5: Wire algorithm output into Step 3.4 constraint sheets

- Constraint sheet Archetype line now comes from algorithm output, not manual pick
- Add structural family to constraint sheet output

## Tests

- Non-testable (markdown skill file, no runtime). Skip TDD.
