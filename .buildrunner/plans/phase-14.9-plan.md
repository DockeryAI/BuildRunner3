# Phase 14.9 Plan: Axis Alignment + Variety Enforcement

## Context

The design.md spec drifted to hyphenated-technical axis labels while types.ts has the correct research-backed Title Case labels. This phase aligns the spec to the UI, adds missing positions, adds a 5th slider, project-type archetype pools, empty states, and post-assembly validation.

## Tasks

### Task 1: Update types.ts axis positions

**Layout** — add 4 positions to reach 12 total:

- Current 8: Swiss grid, Broken grid, Bento grid, Editorial, Split-screen, Cinematic, Brutalist, Single-column
- Add: Full-bleed, Card cascade, Hub-spoke, Data-dense

**Hierarchy** — replace Z-pattern/F-pattern:

- Current: Hero-driven, Distributed equal, Progressive reveal, Z-pattern, F-pattern
- New: Hero-driven, Distributed equal, Progressive reveal, Hub-spoke, Flat-uniform

**Color Temp** — add monochrome as 6th:

- Add: Monochrome

**Sliders type** — add `rugged` property:

- DiscoveryData.sliders: add `rugged: number`
- EMPTY_DISCOVERY.sliders: add `rugged: 5`
- FirstDesignDiscoveryOutput.sliders: add `rugged: number`

### Task 2: Update design.md axis tables (Steps 2b + 3.0)

Replace both axis tables with Title Case labels matching types.ts:

- Narrative: Trusted guide, Friendly helper, Expert authority, Rebellious disruptor, Elegant curator
- Typography: Serif authority, Sans modern, Display creative, Mono technical, Mixed editorial
- Color Temp: Warm stimulating, Neutral balanced, Cool calming, Neon energetic, Earth organic, Monochrome
- Density: Sparse minimal, Light airy, Medium balanced, Dense editorial, Maximum data
- Layout: Swiss grid, Broken grid, Bento grid, Editorial, Split-screen, Cinematic, Brutalist, Single-column, Full-bleed, Card cascade, Hub-spoke, Data-dense
- Interaction: Conventional scroll, Horizontal scroll, Drag/explore, Command-first, Parallax reveal
- Tone: Formal serious, Professional warm, Casual friendly, Playful fun, Irreverent bold
- Visual Weight: Heavy dramatic, Medium balanced, Light airy, Ultra-light minimal
- Imagery: Photography, Illustration, Abstract geometric, Data visualization, Icon-driven
- Hierarchy: Hero-driven, Distributed equal, Progressive reveal, Hub-spoke, Flat-uniform

### Task 3: Add 5th slider to App.tsx (Ruggedness↔Sophistication)

Add `RuggedSophisticatedPreview` component following existing pattern:

- Value 1 = Patagonia (rugged, outdoorsy, textured)
- Value 10 = Chanel (refined, elegant, delicate)
- 10 art-directed states morphing between rugged textures/earthy/bold to sophisticated/refined/elegant
- CSS custom properties + transitions (same as other 4 sliders)

Add 5th SliderRow in both paths:

- First-design: insert after classic slider (new screen 9, bumps brand feel to 10, gut test to 11, density to 12)
- Legacy path: add to slider screens
- Update `canContinue` switch cases for shifted indices
- Update `SliderPreviewType` to include 'rugged'
- Update StepLabel text ("Personality — X of 5" instead of "4")

### Task 4: Add PROJECT_ARCHETYPES to DirectionCards.tsx

Add a `PROJECT_ARCHETYPES` record keyed by project type (website/dashboard/app) with 12 archetypes each, matching the archetype tables already in design.md Step 3.2.

Accept `projectType` as optional prop. When provided, filter the swap pool to that project type's archetypes. Default to website pool.

### Task 5: Add post-assembly validation to design.md

After Step 3 constraint sheets, add a validation section instructing Claude to run 3 programmatic checks:

1. Minimum 3-axis pairwise difference between A/B/C
2. Minimum 60-degree pairwise hue distance
3. All 3 archetypes from different structural families

If any check fails, regenerate the failing direction.

### Task 6: Add empty/waiting states

**Gallery.tsx** — when `data.mockups` is empty, show a contextual message: "Your mockups are being built. They'll appear here when ready."

**ResearchDashboard.tsx** — already has loading/error states; add a specific empty-data state when data loads but has no competitors/directions.

### Tests

- types.ts: Layout has 12 positions, Hierarchy has Hub-spoke/Flat-uniform, Color Temp has 6 positions including Monochrome, sliders type includes `rugged`
- App.tsx: 5 slider screens render, 5th has preview
- DirectionCards: PROJECT_ARCHETYPES has 3 keys with 12 archetypes each
- Gallery: empty mockups array renders waiting message
- design.md: both axis tables match types.ts labels exactly
