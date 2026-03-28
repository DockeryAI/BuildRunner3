# Phase 1: Research Artifacts — Implementation Plan

## Tasks

1. **Create font-personality-pool.md** — ~35 curated fonts in machine-parseable tables, Aaker bridge table, pairing rules, fluid type scale, loading strategy. Merge relevant Impeccable typography/color guidance not already in BR3.
2. **Create dashboard-chart-design.md** — Colorblind-safe palette, sequential/diverging palettes, Recharts dark theme config, KPI card anatomy, dashboard grid, Tufte rules, empty state/skeleton patterns. Merge relevant Impeccable motion/spatial guidance.
3. **Update index.md** — Add entries for both new docs in appropriate section.
4. **Update schema.md** — Add new subjects: font-personality, aaker-brand-personality, kpi-cards, recharts, colorblind-safe, tufte, fluid-typography, font-loading, variable-fonts.

## Impeccable Evaluation Summary

7 reference files fetched. Useful NEW content to merge:
- **OKLCH color**: tinted neutrals formula oklch(15% 0.01 hue), chroma reduction rule — goes into font-personality-pool.md color section
- **Vertical rhythm**: line-height as base spacing unit, 24px rhythm — goes into font-personality-pool.md
- **Motion choreography**: 4-tier timing (100-800ms), cubic-bezier values, exit=75% of enter — goes into dashboard-chart-design.md
- **Stagger patterns**: calc(var(--i) * 50ms), cap at 500ms total — goes into dashboard-chart-design.md
- Already covered by BR3: GPU-safe whitelist, focus indicators, container queries, prefers-reduced-motion

## Tests

Non-testable (docs only). TDD skipped.

## Files Modified

- ~/Projects/research-library/docs/techniques/font-personality-pool.md (NEW)
- ~/Projects/research-library/docs/techniques/dashboard-chart-design.md (NEW)
- ~/Projects/research-library/index.md (MODIFY)
- ~/Projects/research-library/schema.md (MODIFY)
