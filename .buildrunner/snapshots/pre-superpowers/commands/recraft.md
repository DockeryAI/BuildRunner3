---
description: Load Recraft image generation best practices, prompting techniques, and creative guidance
allowed-tools: Read, Glob, Grep
model: opus
---

# Recraft Image Creation Context: /recraft

**PURPOSE: Load everything about how to create the best images with Recraft — prompting techniques, style controls, template-friendly composition, brand consistency, promotional prompt library, and anti-patterns. No API integration, no code architecture. Creative knowledge only.**

---

## Step 1: Load Recraft Research

Read the following document from the research library. Extract ONLY the creative/prompting/image-quality sections listed below — skip API endpoints, SDK code, provider comparisons, pricing tables, and integration architecture.

```
~/Projects/research-library/docs/techniques/ai-image-generation-integration.md
```

### Sections to Load (read these fully):

1. **Recraft V4 Update** — Model variants, V4 vs V3 feature matrix, what V4 improves (design taste, composition, typography)
2. **Recraft Prompting Guide** — The prompt formula, structure best practices, lighting keywords, template-friendly techniques (negative space, bokeh hack, solid backgrounds, split composition), promotional template prompt library (flash sale, new arrival, BTS, seasonal, testimonial, before/after), artistic_level guide, `no_text` importance, color enforcement behavior, `text_layout` creative uses, anti-patterns
3. **Recraft V3 Technical Reference** — Styles available (realistic_image, digital_illustration, vector_illustration + substyles), color parameter behavior
4. **Brand-Matched Image Generation** — Why style training fails, what works (brand colors, style presets, voice→style mapping, industry negative prompts), best-in-class company patterns (Canva, Adobe, Jasper)
5. **Template-Aligned Image Generation** — Text-safe zone strategies (prompt composition, bokeh/DoF, scrim overlay, inpainting), Recraft size mapping for social platforms
6. **Image Purpose & Content Structure Alignment** — Hook/body/CTA image roles, visual hierarchy
7. **SMB Render Styles** — Business-type-specific prompt templates (professional services, local retail, e-commerce, fitness, creative)
8. **Ready-to-Use Prompt Library** — Quick-start formulas, UGC-style, product, people, lifestyle prompts
9. **Recraft API Gotchas** — Creative-relevant gotchas only (text_layout limits, color enforcement behavior, V4 style gap, dimension warping near humans, vector cleanup needs)
10. **Industry Negative Prompts** — Per-industry cliche avoidance lists (spa, wellness, tech, restaurant, etc.)

### Also Search For Updates:

```bash
grep -rl "subjects:.*recraft" ~/Projects/research-library/docs/
```

Read any new Recraft-specific docs not already loaded.

---

## Step 2: Synthesize Key Principles

After reading, build a mental model grouped into these categories:

1. **Prompt Formula** — The [Image Type] + [Subject] + [Style/Mood] + [Composition] + [Technical] + [Negative Constraints] structure
2. **Style Selection** — When to use realistic_image vs digital_illustration vs vector_illustration, substyles, artistic_level 0-5
3. **Brand Consistency** — Color enforcement (suggestive not absolute, works best with illustration styles), style presets, voice→style mapping
4. **Template Composition** — How to prompt for images that work behind text overlays (negative space directives, bokeh hack, split composition, solid/gradient backgrounds)
5. **Promotional Prompts** — Flash sale, product launch, seasonal, testimonial, before/after — ready-to-use patterns
6. **Industry-Specific** — Negative prompts per vertical to avoid AI cliches, SMB render styles per business type
7. **Anti-Patterns** — Don't ask for text you'll overlay, don't specify pixel positions, don't rely on prompt-only composition for production
8. **V3 vs V4 Creative Differences** — V4 has "design taste" (better composition/lighting/negative space) but no custom styles or text_layout. V3 required for brand style_id and positioned text.

---

## Step 3: Check Session Context

Look at the current conversation for:

1. **Image generation task** — Is the user building or debugging image generation prompts?
2. **Template work** — Are they working on Quick Create templates that need AI backgrounds?
3. **Brand-specific context** — Is there a specific brand/industry/aesthetic being targeted?
4. **Edge function prompts** — Are they writing Recraft prompts inside edge functions or services?

---

## Step 4: Present Results

### If an image generation task exists in the session:

```
## Recraft Best Practices — Applied to Current Task

**Research loaded:** Recraft prompting guide, brand matching, template alignment, SMB styles, prompt library

### Most Relevant Techniques for This Task

{List 3-7 specific techniques from the research that directly apply. Be specific — cite the technique name and which section.}

### Recommended Prompt

{Write the actual prompt applying all relevant principles — formula structure, composition for template, brand colors, negative prompts, style selection.}

### Style & Parameter Recommendations

| Parameter | Recommended Value | Why |
|-----------|-------------------|-----|
| style | {value} | {reason} |
| artistic_level | {0-5} | {reason} |
| colors | {brand colors} | {reason} |
| no_text | {true/false} | {reason} |

### Watch Out For

{2-3 anti-patterns or gotchas relevant to this specific task}

---

*Recraft creative context retained for remainder of session.*
```

### If NO specific task exists in the session:

```
## Recraft Image Creation — Loaded into Context

**Research loaded:** Recraft prompting guide, brand matching, template alignment, SMB styles, prompt library, industry negatives

### The Recraft Prompt Formula

[Image Type] + [Subject] + [Style/Mood] + [Composition Directive] + [Technical Parameters] + [Negative Constraints]

### Core Principles Now Active

**Prompt Structure:** Lead with image type, be specific on subject, control mood via lighting keywords, 2-3 sentences max, always include "no text, no watermarks, no logos"
**Style Selection:** realistic_image (photographic), digital_illustration (marketing graphics), vector_illustration (icons/logos). artistic_level 2-3 for most promotional work.
**Brand Consistency:** Pass brand colors as RGB (suggestive, most reliable with illustration styles). Style presets > style training. Map brand voice → visual preset (Sophisticated→Elegant, Friendly→Warm, Professional→Corporate).
**Template Composition:** Bokeh/DoF hack is most reliable for text-safe zones. Explicit negative space directives work ~60-70%. Always use scrim overlay as backup. Generate at closest Recraft size, scale up 5.5%.
**Anti-Patterns:** Don't prompt for text you'll overlay. Don't specify pixel positions. Don't ask for complete promotional layouts — generate background only.

### Quick Reference: Promotional Prompts

- **Flash Sale:** Vibrant flat lay, bold surface, dramatic top-down lighting, high contrast, breathing room
- **Product Launch:** Single hero shot, minimalist surface, soft studio lighting, premium feel, negative space
- **Seasonal:** Lifestyle vignette, season-appropriate lighting, cozy atmosphere, brand tones
- **Behind-the-Scenes:** Candid workplace, warm natural light, genuine moment, environmental portrait
- **Testimonial:** Warm portrait, genuine smile, natural expression, soft diffused light, background blur

### Industry Negative Prompts (Cliche Avoidance)

Spa: no leaves, botanical, lotus, zen stones, bamboo | Tech: no floating screens, blue hexagons, circuits | Restaurant: no floating ingredients, steam, overhead flat lay | Finance: no pie charts, upward arrows, gold coins | Healthcare: no stethoscopes, medical crosses | Fitness: no extreme muscles, generic gym equipment

### V3 vs V4 Decision

- **Use V3:** When you need custom brand style_id, text_layout positioning, or artistic_level control
- **Use V4:** When composition quality matters most (better "design taste," lighting, negative space) and brand style isn't needed

---

*Recraft creative context retained for remainder of session. All image prompts will apply these principles automatically.*
```

---

## Rules

1. **NO API/INTEGRATION** — Do not discuss endpoints, SDKs, authentication, rate limits, or pipeline architecture
2. **NO CODE** — Do not output implementation code. Creative principles and prompt examples only.
3. **CONCISE** — Synthesize, don't dump. The user wants actionable creative guidance, not raw document contents.
4. **CONTEXT RETENTION** — After presenting, keep all Recraft knowledge active for the rest of the session. Apply it to any subsequent image prompt work without being asked again.
5. **PROMPT-READY** — When applying to a task, output actual usable Recraft prompts, not abstract advice.
6. **BRAND-AWARE** — If brand context is available in the session (colors, industry, voice), incorporate it into all prompt recommendations.
