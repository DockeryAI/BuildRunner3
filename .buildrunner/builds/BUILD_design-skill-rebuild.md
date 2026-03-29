# Build: Design Skill Rebuild

**Created:** 2026-03-28
**Status:** Phases 1-10 Complete, Phase 10.5 + Phases 11-14 pending
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

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 3)
  **Blocked by:** Phase 2, Phase 3
  **Deliverables:**
- [x] 10-axis definition with 4+ positions per axis (narrative, typography, color temp, density, layout, interaction, tone, visual weight, imagery, content hierarchy)
- [x] Expanded layout archetype pool: 12 per project type (add broken grid, maximalist, brutalist, data-dense, card cascade, single-column scroll)
- [x] Direction assembly logic: pick 3 combinations maximally distant (≥3 axes different), within brand-appropriate ranges, outside competitor territory
- [x] Direction 4 (baseline): placed where competitors cluster on axis map
- [x] Random concept injection: curated word pool, one random stimulus per direction
- [x] Cross-domain analogy prompt per direction
- [x] Constraint sheet output per direction: all 10 axis positions + derived color + rationale
- [x] Multishot examples: 2-3 complete direction constraint sheets as examples
- [x] Reflection checkpoint: "Do A, B, C differ on at least 3 axes? Could you tell them apart in grayscale? If not, reassign."
- [x] INSTEAD pattern: pair every prohibition with a positive alternative

**Success Criteria:** Three directions distinguishable in grayscale, using different archetypes, density tiers, navigation, typography, and components

---

### Phase 5: CSS Enforcement + Mockup Validation

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 4)
  **Blocked by:** Phase 4
  **Deliverables:**
- [x] Must-use CSS patterns table: 12 archetypes → required CSS structures
- [x] Must-not-use CSS patterns table: 12 archetypes → banned convergent patterns
- [x] Component variety enforcement: Direction A's components ban from Direction B
- [x] Navigation variety: each direction uses different nav pattern
- [x] Density profile enforcement: each direction locked to different spacing tier
- [x] Structural validation gate: grep mockup files for required CSS patterns, fail if two directions share display strategy
- [x] Grayscale validation: explicit hard gate in divergence check
- [x] Reflection checkpoint: "Inspect HTML — does Direction A's bento grid contain grid with span? Or did you default to flex-col?"

**Success Criteria:** Mockup HTML structurally matches constraint sheet — validated programmatically

---

### Phase 6: Direction Report

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 4.5)
  **Blocked by:** Phase 5
  **Deliverables:**
- [x] Direction report template: Brand Scores, Color Derivation, Axis Positions, Competitive Rationale, Audience Alignment
- [x] Brand personality scores displayed per direction
- [x] Color derivation chain: dimension → hue range → saturation → competitive gap → specific accent
- [x] All 10 axis positions with one-line justification each
- [x] "Not like" trace: which Q3 exclusions influenced this direction
- [x] Competitor distance: how direction differs from closest competitor on axis map
- [x] Report presented alongside each mockup
- [x] Reflection checkpoint: "Read each report — does the rationale make sense? If it contradicts the brand profile, something broke."

**Success Criteria:** User reads report and understands why every choice was made, traceable to discovery answers

---

### Phase 7: Content Structure Redesign

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Step 6)
  **Blocked by:** None (independent section)
  **After:** Phase 6 (logical sequence, CAN parallelize)
  **Deliverables:**
- [x] Content audit step (new Step 6.1): scan for text walls, identical cards, flat hierarchy, insufficient padding, missing breaks
- [x] Content restructure step (new Step 6.2): break walls, vary cards, establish 4 font sizes, alternate content types, add spacing
- [x] Component variety enforcement for redesigns: map sections to different BR3 component types
- [x] Reflection checkpoint: "Before visual application — does every page now have clear hierarchy, varied components, proper spacing?"
- [x] Visual application step (Step 6.3): apply palette/typography/components AFTER structure fixed
- [x] Before/after structure comparison in presentation

**Success Criteria:** Redesigned pages have fixed content structure before visual styling applied

---

### Phase 8: Integration + Smoke Test

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/appdesign.md` (MODIFY — verify research doc #7)
- `~/.claude/commands/design.md` (MODIFY — final cleanup)
  **Blocked by:** Phases 1-7
  **Deliverables:**
- [x] Verify /appdesign loads design-direction-differentiation.md
- [x] End-to-end walkthrough on test project: discovery → research → colors → axes → mockups → reports → redesign
- [x] Remove deprecated code: old 3-axis remnants, old quadrant-only color system
- [x] Soften overtriggering language per /opus (CRITICAL/MUST → softer for 4.6)
- [x] Final reflection checkpoint review: verify all 6 checkpoints worded as genuine self-checks

**Success Criteria:** Full /design run produces 3 genuinely different directions with reports, on any BR3 project type

---

### Phase 9: Discovery Upgrade + Audit Fixes _(added: 2026-03-28)_

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Steps 1.5a, 1.5b, 1.5c, 4.3, 4.3b)
  **Blocked by:** Phase 8
  **Deliverables:**
- [x] Replace 5-question block with 13-question block in 5 XML-tagged categories (`<business>`, `<goals>`, `<audience>`, `<personality>`, `<landscape>`, `<constraints>`)
- [x] Add `<example_response>` multishot block showing one completed discovery for a sample project (food app or B2B SaaS)
- [x] Soften Aaker scoring table from fixed lookup to guided derivation with ranges ("derive considering these associations")
- [x] Add personality slider anchor examples (Nike, law firm) so users calibrate placements
- [x] Add scope constraint: "These answers feed visual direction only — not technical architecture or content strategy"
- [x] Rewrite Step 1.5c brand profile output to reflect all 13-question categories (business summary, goal, audience type, 4 slider positions, personality words, emotional target, competitor map, references, exclusions, constraints)
- [x] Expand convergence_guards table in Step 4.3b to include INSTEAD-pattern rows for all 24 dashboard + app archetypes
- [x] Add build rule to Step 4.3: all 4 mockups use Tailwind for layout/spacing/typography, inline styles only for palette hex values
- [x] Verify and update user_gates step references after Step 1.5a expansion
- [x] Commit all changes to `~/.claude` git repo

**Success Criteria:** `/design` prompts 13 questions, Aaker scores derive from slider inputs via soft derivation (not rigid table), brand profile shows all new categories, convergence guards cover all 36 archetypes, all mockups use Tailwind

---

### Phase 10: External Website Redesign Mode _(added: 2026-03-28)_

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Steps -1, 0, 0.5, 1, 1.5a, 3.5, 4.0b, 4.2, 4.3)
  **Blocked by:** Phase 9
  **Deliverables:**
- [x] Add URL detection at top of file: if argument matches URL pattern → external redesign mode, skip project detection + redesign gate
- [x] New Step 0.5 (Site Audit): WebFetch up to 6 pages (home + 5 nav links), extract palette, typography, layout structure, component inventory, content inventory, logo URL
- [x] SPA detection + Playwright fallback: if WebFetch body < 500 chars real content or mostly `<script>` tags, launch Playwright to render and extract DOM + screenshots
- [x] Map crawled site onto 10 axes as "current state" baseline, run content audit (text walls, flat hierarchy, etc.)
- [x] Modified Step 1.5a: pre-fill inferable questions from crawl (Q1 business, Q2 stage, Q5-Q6 audience, Q12 competitors), user confirms/corrects
- [x] Modified Step 3.5 + 4.2: Direction D = current site's actual design (from audit), mockups use site's exact content + logo
- [x] Output scaffolding: create `~/Projects/Websites/Mockups/<domain>/` as project root, scaffold Vite+React+Tailwind if no project exists
- [x] _(bonus)_ Mockup output to `~/Projects/Websites/Mockups/` for ALL modes (not just external)
- [x] _(bonus)_ Logo + favicon on all mockups (rule 16)
- [x] _(bonus)_ Auto-open mockups in browser after build (rule 17)

**Success Criteria:** `/design stripe.com` crawls the site, presents pre-filled discovery, generates 3 redesign directions + current-site baseline using exact content, outputs working mockups to `~/Projects/Websites/Mockups/stripe/`

---

### Phase 10.5: Validation & Enforcement Fixes _(added: 2026-03-29)_

**Status:** pending
**Blocked by:** Phase 10
**Files:**

- `~/.claude/commands/design.md` (MODIFY — Steps 3, 4.3, 4.4, 4.4e, 4.4f, 4.4g)

**Deliverables:**

- [ ] Rewrite Step 4.4 validation to mandate Read tool on each mockup file — extract actual font-family, nav JSX, accent hex, img src; compare against constraint sheet (not plan memory) _(added: 2026-03-29)_
- [ ] Add build-contract.json artifact after Step 3 constraint sheets — JSON with exact font*heading, font_body, nav_pattern, accent_hex, logo_touchpoints per direction; validation diffs this against actual files *(added: 2026-03-29)\_
- [ ] Add logo enforcement multishot example to Step 4.3 — concrete JSX example showing all 5 touchpoints (hero mark, atmospheric bg, card watermark, section divider, nav icon) _(added: 2026-03-29)_
- [ ] Soften validation language from "Hard Gate"/"ENFORCED"/"CRITICAL" to outcome-focused 4.6 phrasing per /opus anti-laziness research _(added: 2026-03-29)_
- [ ] Add content variety build rule to Step 4.3 rule 6 — each direction uses different trending items, featured topic, and pull quote _(added: 2026-03-29)_
- [ ] Add 60-degree minimum hue distance check to Step 3 color derivation — pairwise check on A/B/C accents, shift into nearest unoccupied quadrant if too close _(added: 2026-03-29)_
- [ ] Add validation multishot example showing concrete PASS (actual extracted values match contract) vs FAIL (values differ, triggers rebuild) _(added: 2026-03-29)_

**Build constraints (per /opus 4.6 alignment):**

- Use outcome-focused language, not emphasis markers (MUST/CRITICAL/ENFORCED)
- Multishot examples for validation and logo, not more instruction paragraphs
- build-contract.json is a simple flat JSON, not a schema or complex structure

**Success Criteria:** Run `/design` — validation.md contains actual hex values and font strings read from mockup files (not echoed from plan). All 4 mockups have flame logo in 5 touchpoints. No two creative direction accents within 60 degrees hue. Each direction has different sample content.

---

### Phase 11: Interactive Discovery Wizard App _(added: 2026-03-29)_

**Status:** pending
**Blocked by:** Phase 10.5
**Files:**

- `~/.claude/tools/design-wizard/` (NEW — React app)
- `~/.claude/commands/design.md` (MODIFY — Step 1.5a to launch wizard)

**Deliverables:**

- [ ] Scaffold Vite + React + TypeScript + Tailwind + Framer Motion app at `~/.claude/tools/design-wizard/`
- [ ] 14-screen wizard flow (Q1-Q13 + constraints) with smooth transitions, progress bar, one question per screen
- [ ] 4 interactive sliders (Q7-Q10) with live-morphing preview panel: each slider maps to CSS custom properties that update on drag (border-radius, spacing scale, hue rotation, font-weight/family). The browser interpolates via CSS transitions — not JS state machines. One lookup object per slider, CSS does the rest. A sample card + hero + nav section morph live as the slider moves.
- [ ] Visual examples per question: stage cards with illustrations (Q2), goal/emotion pills (Q3-Q4), discovery channel cards with icons (Q6), competitor URL inputs with favicon fetch (Q12), "not like" with brand reference card (Q13), constraint toggle chips (final)
- [ ] File-based handoff: Submit writes `discovery.json` to the target project's `.buildrunner/design/` directory. "Continue in Claude Code" toast on submit.
- [ ] Update design.md Step 1.5a: Claude Code generates the wizard with project context, opens browser, reads `discovery.json` on return

**Build constraints (per /opus 4.6 alignment):**

- Keep it simple. One component per screen, no premature abstractions, no wrapper utilities for things used once.
- CSS custom properties + transitions for all live previews. No JS animation libraries for slider morphing — Framer Motion is for page transitions only.
- No charting libraries. The color wheel and axis grid are custom SVG/canvas — they're interactive visualizations, not data charts.

**Success Criteria:** Running `/design` opens a visual wizard in the browser. Dragging the Warm↔Cool slider visibly shifts the preview between warm amber tones and cool steel tones. Submitting writes discovery.json. Claude Code reads it and continues.

---

### Phase 12: Interactive Research Dashboard _(added: 2026-03-29)_

**Status:** pending
**Blocked by:** Phase 10.5, Phase 11
**Files:**

- `~/.claude/tools/design-wizard/` (MODIFY — add research views)
- `~/.claude/commands/design.md` (MODIFY — Steps 2b, 2d, 3.7, 4.4)

**Deliverables:**

- [ ] Visual axis grid: 10 rows of position circles, competitor dots color-coded, gap positions glowing (green=safe, amber=risky, red=excluded). Click any position for tooltip with explanation.
- [ ] Interactive OKLCH color wheel: click to explore hues, drag direction accent dots to adjust, live swatch preview updates, competitor accents plotted, brand-appropriate arc highlighted
- [ ] Direction comparison cards: 4 side-by-side cards with live accent swatch, rendered font samples (actual fonts loaded), archetype mini-diagram, nav pattern icon, axis position pills. Click "Swap archetype" to cycle alternatives.
- [ ] File-based handoff: Confirm writes `research-decisions.json` (adjusted colors, swapped archetypes, final axis positions). Claude Code reads and builds mockups.
- [ ] Mockup gallery page: after all 4 mockups are built, open a gallery landing page with 4 extra-large thumbnail cards (screenshot or live iframe preview of each direction). Each card shows direction letter, archetype name, accent swatch, and font name. Click a card → full-screen mockup loads. Persistent nav bar at top for switching between mockups and returning to gallery. "Pick this one" button on each mockup page writes selection to `selection.json`.
- [ ] Validation badge per mockup in gallery — read validation.md and display pass/fail indicators for logo (5 touchpoints), color (hue distance), font (matches contract), nav (matches contract) on each gallery card _(added: 2026-03-29)_
- [ ] Update design.md Steps 2b, 2d, 3.7, 4.6: Claude Code generates dashboard with research data embedded, opens browser, reads decisions on return. Step 4.6 opens gallery instead of 4 separate tabs.

**Build constraints (per /opus 4.6 alignment):**

- No charting libraries (D3, Chart.js, Recharts). The color wheel and axis grid are custom SVG — these are interactive design tools, not data charts. Keep dependencies minimal.
- Each interactive component is self-contained. No shared state management library — React state + context is sufficient for 4 views.
- Gallery uses iframe previews of the mockup apps, not screenshots. Live previews, zero extra build steps.

**Success Criteria:** Research dashboard opens showing competitor clustering visually. You click the color wheel to explore, drag accent dots, swap archetypes on direction cards. Confirming saves decisions. Claude Code builds mockups. Gallery page opens with 4 large preview cards — click to browse each mockup, nav to switch between them, pick button to choose.

---

### Phase 13: Brand Profile Document Generator _(added: 2026-03-29)_

**Status:** pending
**Blocked by:** Phase 12
**Files:**

- `~/.claude/tools/design-wizard/` (MODIFY — add brand profile view)
- `~/.claude/commands/design.md` (MODIFY — Step 5 to generate profile)

**Deliverables:**

- [ ] Designed HTML brand profile page: dark theme, print-friendly, sections from research library (purpose, audience JTBD, positioning Dunford formula, archetype + personality, voice + tone, messaging hierarchy, competitive context, visual identity direction)
- [ ] Combine all /design outputs: discovery answers, Aaker scores (visual bars), competitive axis map (visual grid), color derivation (swatches + wheel), typography pairing (rendered samples), chosen direction constraint sheet
- [ ] Conditional Synapse section: if WebsiteIntelligenceBrief exists, include pain vocabulary, voice gap, psychology profile, competitive voice analysis. Omit cleanly if not available.
- [ ] Conditional workfloDock section: if business plan data exists, include value proposition, target market, service tiers, financial context. Omit cleanly if not available.
- [ ] Save to `.buildrunner/design/brand-profile.html` and auto-open in browser
- [ ] Update design.md Step 5: after DESIGN_SPEC.md generation, also generate brand profile document

**Success Criteria:** After picking a direction, a polished brand profile document opens in the browser. It looks like a $100k agency deliverable. It includes visual Aaker bars, color swatches, font samples, axis positioning, and any available Synapse/workfloDock intelligence. Printable.

---

### Phase 14: Design the Wizard with /design (Dockery Brand) _(added: 2026-03-29)_

**Status:** pending
**Blocked by:** Phase 13
**Files:**

- `~/.claude/tools/design-wizard/` (MODIFY — apply DESIGN_SPEC)

**Deliverables:**

- [ ] Run `/design` on the wizard app itself — full discovery, research, 4 directions, mockups, selection
- [ ] Apply winning DESIGN_SPEC.md as a theme layer: update CSS custom properties, swap font imports, adjust accent colors, add motion tokens. Do not restructure components or change the wizard flow — the app works, this phase only changes how it looks.
- [ ] Premium polish pass: micro-interactions on every interactive element (slider thumb spring, color wheel glow on hover, card flip on archetype swap, progress bar shimmer), 60fps transitions, smooth page transitions between wizard steps
- [ ] Responsive: works on desktop (primary) and tablet. Not mobile — this is a design tool.

**Build constraints (per /opus 4.6 alignment):**

- This is a theming phase, not a rebuild. Apply DESIGN_SPEC.md to existing components via CSS custom properties and font swaps. Do not refactor, restructure, or add features.
- 4.6 will want to "improve" the wizard during design application — resist. If something needs improving, note it for a future phase.

**Success Criteria:** The wizard looks and feels like a premium product — Dockery-branded, smooth animations, every interaction delightful. Not a developer tool form. A $100k design experience.

---

### Out of Scope (Future)

- Persistent color history database across all projects
- User-facing design system token export from chosen direction
- A/B testing integration for chosen designs

## Session Log

[Will be updated by /begin]
