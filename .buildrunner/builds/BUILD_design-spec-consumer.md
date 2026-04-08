# BUILD: BR3 /design + /website-build — Synapse Spec Consumer

**Project:** BuildRunner3 (BR3)
**Created:** 2026-04-05
**Shared Contract:** `/Users/byronhudson/workfloDock/docs/contracts/SYNAPSE_INTEGRATION_CONTRACT.md`
**Paired Specs:**

- `workfloDock/.buildrunner/builds/BUILD_synapse-integration.md` (upstream producer)
- `Synapse/.buildrunner/builds/BUILD_workflodock-intake.md` (intermediate generator)

---

## 0. Purpose (For a New Claude)

**What this spec does:** Patches two Claude-based skills — `/design` and `/website-build` — so they consume Synapse-generated artifacts (DESIGN_SPEC.md front-matter + voice_package) directly, skipping interactive discovery when a pre-built spec arrives.

**Specifically:**

1. **`/design`** gets a new "synapse-generated" detection path at Step 1 that skips the 13-question discovery wizard, reads Aaker 5 scores from spec front-matter, and uses Synapse's recommended layout archetypes as the 4 mockup directions.
2. **`/website-build`** gets voice_package fetching (HTTP call to Synapse) at Step 2, uses voice_package copy verbatim for every page at Step 5, and enforces GEO + a11y + CWV compliance gates before deploy.

**Why this spec exists:** Today `/design` always runs full 13-question wizard; `/website-build` generates its own copy. The chain workfloDock → Synapse → /design → /website-build has upstream authorities (strategy, voice, visual derivation) that downstream tools must obey. These patches make the skills obey.

**READ FIRST:**

1. `/Users/byronhudson/workfloDock/docs/contracts/SYNAPSE_INTEGRATION_CONTRACT.md` — full schema + front-matter format
2. `/Users/byronhudson/.claude/commands/design.md` — existing /design skill (2460 lines)
3. `/Users/byronhudson/.claude/commands/website-build.md` — existing /website-build skill (199 lines)
4. `/Users/byronhudson/.claude/skills/br3-frontend-design/SKILL.md` — BR3 design system rules
5. Research files listed per phase

**CRITICAL RULES:**

- Do NOT rewrite the entire skill files — surgical patches only
- Preserve all existing flows (first-design, redesign-external, redesign-local must continue working)
- The user has invested heavily in the /design UI; treat it as tested and stable
- All changes must be backward compatible: legacy DESIGN_SPEC.md without front-matter continues to work

---

## 1. Existing Code Map (What Already Exists)

### /design Skill Definition

**File:** `/Users/byronhudson/.claude/commands/design.md` (2460 lines)

**Steps in the skill:**

- Step -1: Mode Detection (redesign-external | redesign-local | first-design)
- Step 0: Project Detection
- Step 0.5: Site Audit (redesign modes)
- Step 0.7: Audit Presentation
- **Step 1: Redesign Gate (lines 294-316)** ← PATCH TARGET
- **Step 1.5: Discovery Q&A + Brand Scoring (lines 321-550)** ← PATCH TARGET (add skip path)
- Step 2: Research + Differentiation Vectors (2a-2d)
- Step 3: Four Directions (10-Axis System)
- Step 4: Build Mockups (4.0-4.6)
- Step 5: Selection + Spec Generation (lines 2205-2280) ← PATCH TARGET (add front-matter on write)
- Step 6: Redesign Existing UI

**Existing Synapse integration block:** Lines 748-785 (`<synapse_integration>`) — **already documents the pipeline workfloDock → Synapse → DAIS**, defines which brief fields populate which DaisBusinessSignals. This block is ASPIRATIONAL today (no code detection yet).

**Existing discovery questions:** Lines 425-550 (Q1-Q10 for first-design, Q1-Q3 for redesign).

**Existing personality sliders:** 4 sliders (Playful-Serious, Minimal-Maximal, Warm-Cool, Classic-Cutting-edge) at lines 493-515. These generate **4-sum not 5-sum Aaker scores**. MUST BE EXPANDED to 5 sliders matching contract.

**DaisBusinessSignals type (lines 733-746):** Inputs to Step 2a. Currently no `aaker_scores_5d` field — uses 4-slider derivation.

### /website-build Skill Definition

**File:** `/Users/byronhudson/.claude/commands/website-build.md` (199 lines)

**Steps:**

- **Step 1: Load Research Context (lines 11-40)** — loads 5 research files in parallel
- **Step 2: Load Intelligence Brief (lines 42-90)** ← PATCH TARGET (add voice_package fetch)
- Step 3: Scaffold BR3 Project (lines 92-93)
- **Step 4: Generate Design System via DAIS (lines 93-117)** ← PATCH TARGET (detect synapse spec, skip discovery)
- **Step 5: Build Pages (lines 119-167)** ← PATCH TARGET (use voice_package copy)
- **Step 6: Verify Build (lines 169-199)** ← PATCH TARGET (add GEO + CWV gates)

**Brief path:** `.buildrunner/data/website-intelligence-brief.json` (line 46)
**Spec path:** `.buildrunner/design/DESIGN_SPEC.md` (line 95)

### BR3 Underlying Code

**Files to inspect (do NOT modify unless necessary):**

- `/Users/byronhudson/Projects/BuildRunner3/cli/design_commands.py`
- `/Users/byronhudson/Projects/BuildRunner3/core/design_researcher.py`
- `/Users/byronhudson/Projects/BuildRunner3/core/design_profiler.py`
- `/Users/byronhudson/Projects/BuildRunner3/core/design_extractor.py`

**Note:** `designResearch()`, `designDerive()`, `designSpec()` are primarily **Claude skill steps** — inline LLM prompts inside the skill definition, not Python functions. They may have Python CLI wrappers but the authoritative logic lives in `design.md`.

### DESIGN_SPEC.md Format (Current, no front-matter)

**Sections written today:**

1. `# {ProjectName} — Design Spec`
2. `**Direction:** {title}` + `**Approved:** {date}` + `**Reference mockup:** {path}`
3. `## Design Thesis`
4. `## Color Palette` (Primary/Secondary Accent, Surfaces, Text, Borders, Semantic, Usage Rules)
5. `## Typography` (Heading, Body, Rules)
6. Optional: Components, Spacing/density, Motion, E2E Test Requirements

**NO existing `source:` or `metadata:` front-matter.** The new front-matter gets ADDED at top of file.

### Skip-the-Wizard Mechanism (Current)

**Today at Step 1 (line 303-316):**

```
IF .buildrunner/design/DESIGN_SPEC.md exists:
  - Output: "Existing DESIGN_SPEC.md found. Redesign? (y/n)"
  - On YES → Step 2 (research)
  - On NO → write .design-declined marker
```

**No detection of spec source (synapse vs manual).** No `--spec-path` flag. No skip-wizard-for-synapse path.

### BR3 Design System Rules

**File:** `/Users/byronhudson/.claude/skills/br3-frontend-design/SKILL.md`

**Component library matrix (must preserve):**

- shadcn → base components
- aceternity → hero effects
- magic-ui → particles, beams, animations
- catalyst-ui → layouts, complex forms
- radix → accessible primitives

**Rules:** Dark theme default, Tailwind v4 with @layer components, 8pt spacing, content never touches borders, GPU-safe motion only.

**DO NOT:**

- Install new UI libraries
- Bypass component library matrix
- Disable reduced-motion checks
- Remove accessibility enforcement

---

## 2. Research Context

These frameworks already govern the skills — this spec enforces them more strictly + adds GEO/CWV gates.

| Framework                                                      | File(s)                                                                                                                     |
| -------------------------------------------------------------- | --------------------------------------------------------------------------------------------------------------------------- |
| **Aaker 5 Dimensions** (expanding from 4 sliders to 5)         | `brand-profile-smb-midmarket.md`, `/techniques/design-direction-differentiation.md`, `/techniques/font-personality-pool.md` |
| **10 Variation Axes + 12 Layout Archetypes**                   | `/techniques/design-direction-differentiation.md`                                                                           |
| **Color Derivation Pipeline** (Aaker → hue → gap → saturation) | `/techniques/design-direction-differentiation.md` lines 141-183                                                             |
| **Font Personality Pool** (Aaker-to-font bridge)               | `/techniques/font-personality-pool.md`                                                                                      |
| **OKLCH Tinted Neutrals**                                      | `/techniques/font-personality-pool.md` lines 198-214                                                                        |
| **Dark/Light Mode Hierarchies**                                | `saas-dark-mode-color-systems.md`, `premium-light-mode-design.md`                                                           |
| **Services Page 10-section Architecture**                      | `services-page-conversion-optimization.md`                                                                                  |
| **GEO Ranking Factors**                                        | `geo-citation-optimization-2026.md`, `geo-anti-patterns-dangers.md`                                                         |
| **Schema Markup Rules** (attribute-rich or skip)               | `geo-page-type-optimization.md`                                                                                             |
| **Core Web Vitals + A11y**                                     | BR3 frontend-design SKILL.md                                                                                                |
| **StoryBrand/PAS/FAB/AIDA/PASTOR frameworks**                  | consumed from voice_package (no re-generation)                                                                              |

---

## 3. Phases (12 phases total)

### PHASE 1: DESIGN_SPEC.md Front-Matter Detection (/design Step 1) ✅ COMPLETE

**Goal:** At Step 1 (Redesign Gate), parse front-matter YAML and detect `source: synapse-generated`.

**File touched:** `/Users/byronhudson/.claude/commands/design.md`

**Patch target:** Lines 294-316 (Step 1: Redesign Gate block)

**New logic (replaces existing block):**

````
### Step 1: Redesign Gate

**PRECONDITION:** Project detection complete (Step 0).

1. **Check for existing spec:** Read `.buildrunner/design/DESIGN_SPEC.md` if present.

2. **Parse front-matter** (YAML between `---` markers at top):
   ```yaml
   ---
   source: synapse-generated | manual-discovery
   brand_id: {uuid}
   brief_version: {number}
   aaker_scores: { sincerity, excitement, competence, sophistication, ruggedness }
   heritage_innovation: {float}
   density_preference: spacious|balanced|dense
   dominant_dimension: {name}
   recommended_layout_archetypes: [list of 4]
   voice_package_available: {bool}
   ---
````

3. **Decision tree:**
   - IF front-matter parsed AND `source: synapse-generated` AND all 5 Aaker scores present AND ≥4 layout archetypes listed:
     → **SKIP Step 1.5 (Discovery Q&A entirely)**
     → Load Aaker scores + archetypes + density from front-matter into DaisBusinessSignals
     → Output: "Synapse-generated spec detected. Skipping discovery — using pre-computed brand profile."
     → Jump to Step 2 (research + differentiation vectors)
   - IF front-matter present but `source: manual-discovery` OR incomplete:
     → Output: "Existing DESIGN_SPEC.md found (manual). Redesign? (y/n)"
     → (Existing behavior)
   - IF no front-matter (legacy spec):
     → Output: "Existing DESIGN_SPEC.md found (legacy format). Redesign? (y/n)"
     → (Existing behavior)
   - IF no spec exists:
     → (Existing first-design path)

4. **Stash parsed front-matter** in session context for downstream steps.

```

**Acceptance:**
- Given a synapse-generated spec file, skill skips wizard and outputs detection message
- Given manual-discovery spec, skill prompts redesign as today
- Given malformed front-matter, skill gracefully falls back to legacy behavior
- Given no spec, skill runs discovery as today

---

### PHASE 2: [REMOVED] Expand Discovery from 4-Slider to 5-Slider Aaker

**Status:** 🗑️ REMOVED 2026-04-05 — already delivered by `BUILD_design-skill-rebuild.md` Phase 1 + Phase 14 (both COMPLETE). /design wizard already captures all 5 Aaker dimensions.

---

### PHASE 3: [REMOVED] Use Synapse Layout Archetypes as 4 Directions

**Status:** 🗑️ REMOVED 2026-04-05 — archetype routing is already delivered by `BUILD_design-skill-rebuild.md` Phase 14.8 (Archetype Selection Algorithm, COMPLETE) and Phase 14.9 (Axis Alignment + Variety Enforcement, COMPLETE). The existing archetype engine will consume `recommended_layout_archetypes` from front-matter automatically once Phase 1 of this spec stashes it in session context — no separate phase needed.

---

### PHASE 4: Write Front-Matter When /design Writes DESIGN_SPEC.md ✅ COMPLETE

**Goal:** At Step 5 (Selection + Spec Generation), prepend front-matter YAML to DESIGN_SPEC.md when skill writes it.

**File touched:** `/Users/byronhudson/.claude/commands/design.md`

**Patch target:** Lines 2205-2280 (Step 5 write logic)

**New requirement:**
```

When `designSpec()` writes DESIGN_SPEC.md, ALWAYS prepend this YAML front-matter:

---

source: {if came from synapse spec: synapse-generated-approved; else: manual-discovery}
brand_id: {from stash if synapse; else null}
brief_version: {from stash if synapse; else null}
aaker_scores:
sincerity: {score}
excitement: {score}
competence: {score}
sophistication: {score}
ruggedness: {score}
heritage_innovation: {value}
density_preference: {spacious|balanced|dense}
dominant_dimension: {name}
selected_direction: {A|B|C|D}
layout_archetype: {chosen archetype name}
voice_package_available: {true if synapse; else false}
generated_at: {iso8601}
generated_by: claude-design-skill

---

{existing spec content}

```

**Acceptance:**
- Every new DESIGN_SPEC.md has valid YAML front-matter
- Synapse-approved specs carry `source: synapse-generated-approved` after /design merges user's direction choice
- Manual runs carry `source: manual-discovery`

---

### PHASE 5: /website-build — Voice Package Fetch ✅ COMPLETE

**Goal:** At Step 2, after loading brief, fetch voice_package from Synapse by brand_id.

**File touched:** `/Users/byronhudson/.claude/commands/website-build.md`

**Patch target:** Step 2 (Load Intelligence Brief), around lines 42-90.

**Add after brief is loaded:**
```

### Step 2.5: Load Voice Package (Synapse-generated copy)

After loading the brief, attempt to hydrate voice_package:

1. **Check local file:** Read `.buildrunner/data/voice_package.json` if it exists. If present, use it.

2. **Fetch from Synapse (if not local):**
   - Extract `brand_id` from DESIGN_SPEC.md front-matter (if synapse-generated) OR from brief.meta if present
   - Extract `brief_version` from same
   - If brand_id available:
     - Call: `GET {SYNAPSE_URL}/functions/v1/get-voice-package?brand_id={id}&brief_version={v}`
     - Authorization header: Bearer {SYNAPSE_SERVICE_TOKEN} from env
     - On 200: parse WebsiteCopyPackage, save to `.buildrunner/data/voice_package.json`
     - On 404: log warning "No voice_package available; falling back to pain_vocabulary generation"
     - On 500: retry once; then fallback
   - If brand_id unavailable: skip fetch, use brief.pain_vocabulary only

3. **Decision:**
   - IF voice_package hydrated:
     → Set mode `USE_VOICE_PACKAGE` for Step 5
   - ELSE:
     → Set mode `GENERATE_INLINE_COPY` for Step 5 (existing behavior with pain_vocabulary)

```

**Acceptance:**
- With brand_id + working Synapse: voice_package fetched + persisted
- Without Synapse: falls back silently to existing pain_vocabulary path
- 404 logged; no hard failure

---

### PHASE 6: /website-build — Use Voice Package Copy at Step 5 ✅ COMPLETE

**Goal:** When voice_package is available, use its per-page copy verbatim instead of LLM-generating copy.

**File touched:** `/Users/byronhudson/.claude/commands/website-build.md`

**Patch target:** Step 5 (Build Pages), lines 119-167.

**Add at top of Step 5:**
```

### Step 5: Build Pages

**IF mode is USE_VOICE_PACKAGE:**
For each page in voice_package.pages:

1. Read the page's sections[] — each has section_name, copy (markdown), framework_role, voc_phrases_used, cialdini_lever
2. Build the page component using DESIGN_SPEC's layout archetype + component mapping
3. Inject voice_package copy VERBATIM into section slots (do NOT rewrite)
4. Use voice_package.pages[slug].hero_variants[0] as primary hero; hold others for A/B test setup
5. Use voice_package.pages[slug].primary_cta_text for CTA button
6. Inject voice_package.pages[slug].faq as FAQ block (40-60 word answers, visible HTML for GEO)
7. Place voice_package.pages[slug].objection_response_pairs as FAQ extensions or sidebar
8. Apply social_proof from brief NEAR the primary CTA (+68% conversion rule)

**ELSE mode is GENERATE_INLINE_COPY:**
(Existing behavior: apply copy filters table at lines 119-129 — pain-first, loss/gain framed, FOMU, etc.)

```

**Acceptance:**
- Voice-package path uses copy verbatim, no LLM rewrites
- Fallback path unchanged
- Framework enforcement respected (StoryBrand sections in correct order, etc.)

---

### PHASE 7: /website-build — GEO + Schema Compliance Gates at Step 6 ✅ COMPLETE

**Goal:** Enforce GEO/schema/a11y/CWV gates before build is considered complete.

**File touched:** `/Users/byronhudson/.claude/commands/website-build.md`

**Patch target:** Step 6 (Verify Build), lines 169-199.

**Add new sub-steps:**
```

### Step 6: Verify Build

**6.1 Build Check:** (existing) `npm run build` passes

**6.2 GEO Compliance Gates:**

- Every page has attribute-rich schema markup (Organization OR LocalBusiness + Service + FAQPage + BreadcrumbList + WebPage.dateModified)
- Generic schema penalty check: if schema fields incomplete, REMOVE schema (generic = -18 point penalty per research)
- FAQPage schema answers are 40-60 words AND visible in HTML (not accordion-hidden)
- First 100 words of each content-heavy page contain a 120-150 char BLUF answer capsule
- H2/H3 hierarchy present (no flat structure)
- Statistics cadence: 1 stat per 150-200 words on pillar pages

**6.3 Accessibility Gates:**

- Contrast ≥ 4.5:1 for all body text (WCAG AA)
- Focus indicators visible (outline: 2px solid accent + offset 2px)
- Target size ≥ 24px (WCAG 2.2 SC 2.5.8)
- No `outline: none` without replacement
- Semantic HTML (no `<div onClick>`)
- Motion respects `prefers-reduced-motion`

**6.4 Core Web Vitals Gates:**

- LCP < 2.5s
- Page load < 2s
- Hero media < 200kb
- GPU-safe animations only (transform + opacity)

**6.5 Framework Compliance Gates (if voice_package used):**

- Home page has 8 StoryBrand sections in order
- Service pages have PAS structure + 1,000-1,500 words
- Pricing page is HTML table (not gated "Contact Sales")
- Primary CTA singular per page (multiple = -266% conversion violation)
- Social proof placed near primary CTA (+68% rule)

**If any gate fails:** Report to user with specific remediation + research source; DO NOT ship.

```

**Acceptance:**
- Playwright E2E test verifies all gates on a sample build
- Failure modes report the gate + research source

---

### PHASE 8: /website-build — E2E Test Suite Generation ✅ COMPLETE

**Goal:** Auto-generate Playwright tests matching DESIGN_SPEC's E2E Test Requirements + the compliance gates.

**File touched:** `/Users/byronhudson/.claude/commands/website-build.md`

**Patch target:** After Step 6.

**Add Step 6.6:**
```

**6.6 Generate Playwright E2E Tests:**
Create `e2e/` directory with tests for:

- Every page loads (200 status)
- Primary CTA visible above fold
- Social proof logo bar present (3-6 logos)
- FAQ schema validates
- Contrast check on all text
- Focus indicators appear on Tab navigation
- Mobile viewport: load < 3s, CTA tappable 24px+

Run `npx playwright test` — blocks ship on failure.

```

---

### PHASE 9: /design — Legacy Spec Graceful Fallbacks ✅ COMPLETE

**Goal:** Ensure skill doesn't crash on specs without expected fields.

**File touched:** `/Users/byronhudson/.claude/commands/design.md`

**Patch target:** Front-matter parsing (added in Phase 1).

**Add defaults:**
```

If synapse-generated spec is missing:

- aaker_scores → fallback to manual wizard (all 5 sliders)
- recommended_layout_archetypes → fallback to 10-axis vectoring (existing path)
- density_preference → default to 'balanced'
- heritage_innovation → default to 0.5
- dominant_dimension → recompute from Aaker scores

Log each fallback as warning. Never hard-fail on missing fields.

```

**Acceptance:**
- Partial synapse spec still works (with fallbacks + warnings)
- Malformed YAML logs + falls back to legacy

---

### PHASE 10: Documentation — Update Synapse Integration Block ✅ COMPLETE

**Goal:** Update `<synapse_integration>` block in design.md to reflect implemented behavior.

**File touched:** `/Users/byronhudson/.claude/commands/design.md` lines 748-785.

**Update content:**
- Document that `/design` NOW auto-detects synapse-generated specs
- Document the front-matter schema
- Document fallback behavior
- Link to contract doc

Similar update for website-build.md — document voice_package fetching.

---

### PHASE 11: Environment Configuration ✅ COMPLETE

**Goal:** Define env vars for Synapse API access.

**Files touched:**
- CREATE `/Users/byronhudson/.claude/commands/_env.example` (if not exists) — document required vars
- UPDATE skill docs with env var references

**Required env vars:**
```

SYNAPSE_URL=https://{project}.supabase.co
SYNAPSE_SERVICE_TOKEN=<supabase service role key or user-scoped token>

```

---

### PHASE 12: Cross-Skill Integration Test ✅ COMPLETE

**Goal:** End-to-end test of workfloDock → Synapse → /design → /website-build.

**Files touched:**
- CREATE `/Users/byronhudson/Projects/BuildRunner3/tests/integration/full_chain.test.sh`

**Test flow:**
1. Mock workfloDock brief JSON fixture
2. POST to local Synapse `intake-strategic-spine`
3. Wait for voice_package + design_spec generation (poll pipeline_status)
4. Copy DESIGN_SPEC.md to test project `.buildrunner/design/`
5. Copy voice_package.json to `.buildrunner/data/`
6. Run `/design` skill — assert it skips wizard + produces 4 mockups
7. User picks direction A (simulate)
8. Run `/website-build` skill — assert it fetches voice_package + uses copy verbatim
9. Assert all compliance gates pass
10. Assert Playwright E2E tests generated + pass

---

## 4. Out of Scope

- Changes to workfloDock (separate spec)
- Changes to Synapse edge functions (separate spec)
- Rewriting `/design` discovery wizard UX (keep existing; just add skip path)
- Rewriting `/website-build` page-building logic (keep existing; add voice_package path)
- Changes to BR3 frontend-design SKILL rules
- New Python/CLI functions in BR3 core/

---

## 5. Acceptance Criteria Summary

- [x] `/design` detects `source: synapse-generated` front-matter and skips discovery wizard
- [x] `/design` uses Aaker 5 scores + layout archetypes from spec directly
- [x] `/design` still runs grayscale distinctness check on 4 directions
- [x] `/design` expanded from 4 sliders to 5 Aaker dimensions (backward compat)
- [x] `/design` writes front-matter on every DESIGN_SPEC.md it produces
- [x] `/website-build` fetches voice_package from Synapse API when brand_id available
- [x] `/website-build` uses voice_package copy verbatim when available
- [x] `/website-build` falls back to existing pain_vocabulary path silently on miss
- [x] `/website-build` enforces GEO + a11y + CWV + framework compliance gates
- [x] All legacy flows (first-design, redesign, no-Synapse website-build) continue working
- [x] Cross-skill integration test passes end-to-end

---

## 6. Risk Register

| Risk | Mitigation |
|---|---|
| Synapse spec arrives malformed | YAML parser + graceful fallback to manual wizard |
| voice_package fetch fails | Falls back to inline copy generation (existing path) |
| Expanded 5-slider Aaker confuses existing users | Pre-fill defaults from 4-slider derivation; allow skip |
| 4 recommended archetypes fail distinctness | Swap one with compatible alternative; log warning |
| BR3 Python CLI diverges from skill definition | Cross-skill integration test catches drift |
| Users have outdated DESIGN_SPEC.md | Legacy-format branch unchanged |
| GEO gates too strict, block builds | Escape hatch env var for dev (GEO_GATES_WARN_ONLY=1) |

---

## 7. Build Order

Phases 1 → 9 → 2 → 3 → 4 → 10 (all /design edits) → 5 → 6 → 7 → 8 (all /website-build edits) → 11 → 12

Rationale: /design detection + fallbacks first (Phases 1, 9). Expand Aaker (2), archetype routing (3), front-matter write (4), docs (10). Then /website-build: fetch (5), consume (6), gates (7), tests (8). Env vars (11) last, before integration test (12).

---

**End of Spec**
```
