# Phase 2 Plan: SKILL.md Enhancement

## Budget: 416 current lines → 600 max = 184 lines available for additions

## Tasks

### T1: Add Accessibility section (new) — ~25 lines
- Contrast table, target size, focus spec, semantic bans, chart a11y, ARIA live rule
- All tables, no prose

### T2: Add Responsive section (new) — ~22 lines
- Decision hierarchy table, Tailwind v4 container query syntax, dashboard responsive strategy, data table patterns, desktop-first note

### T3: Add Performance section (new) — ~22 lines
- GPU-safe animation whitelist, backdrop-filter cap, LazyMotion, image rules, route splitting, CLS prevention

### T4: Add Dashboard component mapping (extend existing tables) — ~18 lines
- KPI card, chart container, empty state, skeleton loader, sparkline

### T5: Add Chart theme reference (new subsection) — ~15 lines
- Palette array, Recharts dark defaults, area gradient pattern

### T6: Modify Glassmorphism Recipes — +1 line
- Add performance warning comment

### T7: Modify Framer Motion Patterns — +2 lines
- Add LazyMotion note

### T8: Modify Avoid section — +5 lines
- Add 5 new items

### T9: Modify 8pt Spacing System — +2 lines
- Add fluid spacing with container query units

## Tests: N/A (docs-only phase, non-testable)

## Total estimated addition: ~112 lines → well within budget
