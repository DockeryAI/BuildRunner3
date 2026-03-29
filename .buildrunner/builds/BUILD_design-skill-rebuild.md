# Build: Design Skill Rebuild

**Created:** 2026-03-28
**Status:** Phases 1-3 Complete
**Deploy:** N/A — skill file (no deployment, changes are live on save)

## Overview

Rebuild `/design` to produce genuinely different, brand-derived design directions with enforced structural variety, full decision reports, internal reflection checkpoints, and content-aware redesigns. Single file rebuild (~/.claude/commands/design.md) with /appdesign integration.

## Parallelization Matrix

| Phase | Key Files                  | Can Parallel With | Blocked By |
| ----- | -------------------------- | ----------------- | ---------- |
| 1     | design.md (Steps 0-2a)     | —                 | —          |
| 2     | design.md (Steps 2b-2d)    | —                 | 1          |
| 3     | design.md (color sections) | —                 | 1, 2       |
| 4     | design.md (Step 3)         | —                 | 2, 3       |
| 5     | design.md (Step 4)         | —                 | 4          |
| 6     | design.md (Step 4.5)       | —                 | 5          |
| 7     | design.md (Step 6)         | 1-6               | —          |
| 8     | design.md + appdesign.md   | —                 | 1-7        |

## Phases

### Phase 1: Discovery Q&A + Brand Scoring

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Steps 0-2a)
  **Blocked by:** None
  **Deliverables:**
- [x] New Step 1.5: Discovery Q&A prompt (5 questions — personality, competitors, "not like", density, dealbreakers)
- [x] Structured brand profile output format (Aaker scores 0-1 across 5 dimensions, competitor list, exclusions, density preference)
- [x] Aaker scoring logic: map user's personality pick + tone keywords → numerical scores across Sincerity/Excitement/Competence/Sophistication/Ruggedness
- [x] Reflection checkpoint after scoring: "Review scores — does Excitement at 0.8 match what the user described? Would someone who knows this brand agree?"
- [x] User gate: wait for discovery answers before proceeding to research

**Success Criteria:** Running `/design` prompts 5 questions, user answers in one response, brand profile with numerical scores is produced

---

### Phase 2: Upgraded Research Pipeline

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 2b-2d)
  **Blocked by:** Phase 1
  **Deliverables:**
- [x] Competitor visual scan: map each competitor onto 10 axes (layout, color temp, density, typography, interaction, tone, weight, imagery, hierarchy, narrative)
- [x] Gap map output: which axis combinations are unoccupied in competitive landscape
- [x] Audience constraint mapping: which axis positions are appropriate vs wrong for this audience type
- [x] "Not like" exclusion processing: user's Q3 answer eliminates specific axis positions
- [x] Reflection checkpoint after research: "Check gap map — are these genuine gaps or did you miss a competitor? Does the audience constraint make sense for this user base?"
- [x] Updated research presentation format showing structured maps, not just prose bullets

**Success Criteria:** Research outputs structured gap map and competitor axis positions that mechanically feed direction generation

---

### Phase 3: Color Derivation Pipeline

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 2d color sections, hue_diversity_rule)
  **Blocked by:** Phase 1, Phase 2
  **Deliverables:**
- [x] Brand-to-hue mapping: Aaker dimension scores → hue range (excitement=warm, competence=cool, etc.)
- [x] Saturation derivation: brand positioning (heritage vs innovation) → saturation level (15-90%)
- [x] Lightness derivation: personality dimensions → lightness level
- [x] Competitive gap integration: narrow hue to specific 20° window within derived range, offset by largest competitor gap
- [x] Per-direction saturation/lightness profiles: one vibrant, one muted, one soft
- [x] Random offset per session: 20° hue windows shift randomly each run
- [x] Color rationale template with derivation chain
- [x] Reflection checkpoint: "Does this accent genuinely differ from last 3 projects? Does saturation match heritage/innovation positioning?"
- [x] Replace current 90° quadrant system with new derivation pipeline

**Success Criteria:** Each direction's color has written rationale connecting hue, saturation, lightness to specific brand scores and competitive gaps

---

### Phase 4: 10-Axis Direction System

**Status:** not_started
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 3)
  **Blocked by:** Phase 2, Phase 3
  **Deliverables:**
- [ ] 10-axis definition with 4+ positions per axis (narrative, typography, color temp, density, layout, interaction, tone, visual weight, imagery, content hierarchy)
- [ ] Expanded layout archetype pool: 12 per project type (add broken grid, maximalist, brutalist, data-dense, card cascade, single-column scroll)
- [ ] Direction assembly logic: pick 3 combinations maximally distant (≥3 axes different), within brand-appropriate ranges, outside competitor territory
- [ ] Direction 4 (baseline): placed where competitors cluster on axis map
- [ ] Random concept injection: curated word pool, one random stimulus per direction
- [ ] Cross-domain analogy prompt per direction
- [ ] Constraint sheet output per direction: all 10 axis positions + derived color + rationale
- [ ] Multishot examples: 2-3 complete direction constraint sheets as examples
- [ ] Reflection checkpoint: "Do A, B, C differ on at least 3 axes? Could you tell them apart in grayscale? If not, reassign."
- [ ] INSTEAD pattern: pair every prohibition with a positive alternative

**Success Criteria:** Three directions distinguishable in grayscale, using different archetypes, density tiers, navigation, typography, and components

---

### Phase 5: CSS Enforcement + Mockup Validation

**Status:** not_started
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 4)
  **Blocked by:** Phase 4
  **Deliverables:**
- [ ] Must-use CSS patterns table: 12 archetypes → required CSS structures
- [ ] Must-not-use CSS patterns table: 12 archetypes → banned convergent patterns
- [ ] Component variety enforcement: Direction A's components ban from Direction B
- [ ] Navigation variety: each direction uses different nav pattern
- [ ] Density profile enforcement: each direction locked to different spacing tier
- [ ] Structural validation gate: grep mockup files for required CSS patterns, fail if two directions share display strategy
- [ ] Grayscale validation: explicit hard gate in divergence check
- [ ] Reflection checkpoint: "Inspect HTML — does Direction A's bento grid contain grid with span? Or did you default to flex-col?"

**Success Criteria:** Mockup HTML structurally matches constraint sheet — validated programmatically

---

### Phase 6: Direction Report

**Status:** not_started
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 4.5)
  **Blocked by:** Phase 5
  **Deliverables:**
- [ ] Direction report template: Brand Scores, Color Derivation, Axis Positions, Competitive Rationale, Audience Alignment
- [ ] Brand personality scores displayed per direction
- [ ] Color derivation chain: dimension → hue range → saturation → competitive gap → specific accent
- [ ] All 10 axis positions with one-line justification each
- [ ] "Not like" trace: which Q3 exclusions influenced this direction
- [ ] Competitor distance: how direction differs from closest competitor on axis map
- [ ] Report presented alongside each mockup
- [ ] Reflection checkpoint: "Read each report — does the rationale make sense? If it contradicts the brand profile, something broke."

**Success Criteria:** User reads report and understands why every choice was made, traceable to discovery answers

---

### Phase 7: Content Structure Redesign

**Status:** not_started
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 6)
  **Blocked by:** None (independent section)
  **After:** Phase 6 (logical sequence, CAN parallelize)
  **Deliverables:**
- [ ] Content audit step (new Step 6.1): scan for text walls, identical cards, flat hierarchy, insufficient padding, missing breaks
- [ ] Content restructure step (new Step 6.2): break walls, vary cards, establish 4 font sizes, alternate content types, add spacing
- [ ] Component variety enforcement for redesigns: map sections to different BR3 component types
- [ ] Reflection checkpoint: "Before visual application — does every page now have clear hierarchy, varied components, proper spacing?"
- [ ] Visual application step (Step 6.3): apply palette/typography/components AFTER structure fixed
- [ ] Before/after structure comparison in presentation

**Success Criteria:** Redesigned pages have fixed content structure before visual styling applied

---

### Phase 8: Integration + Smoke Test

**Status:** not_started
**Files:**

- `~/.claude/commands/appdesign.md` (MODIFY — verify research doc #7)
- `~/.claude/commands/design.md` (MODIFY — final cleanup)
  **Blocked by:** Phases 1-7
  **Deliverables:**
- [ ] Verify /appdesign loads design-direction-differentiation.md
- [ ] End-to-end walkthrough on test project: discovery → research → colors → axes → mockups → reports → redesign
- [ ] Remove deprecated code: old 3-axis remnants, old quadrant-only color system
- [ ] Soften overtriggering language per /opus (CRITICAL/MUST → softer for 4.6)
- [ ] Final reflection checkpoint review: verify all 6 checkpoints worded as genuine self-checks

**Success Criteria:** Full /design run produces 3 genuinely different directions with reports, on any BR3 project type

---

### Out of Scope (Future)

- Automated competitor screenshot capture (headless browser)
- Persistent color history database across all projects
- User-facing design system token export from chosen direction
- A/B testing integration for chosen designs
- /design working outside BR3 projects

## Session Log

[Will be updated by /begin]
