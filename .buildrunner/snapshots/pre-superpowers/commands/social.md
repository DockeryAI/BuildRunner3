---
description: Load social media marketing best practices, apply to current session plans
allowed-tools: Read, Glob, Grep
model: opus
---

# Social Media Marketing Context: /social

**PURPOSE: Load all social media marketing best practices from the research library into context. If a fix plan or implementation plan exists in the current session, apply social media principles to improve it and present the updated plan. No action taken, no code written.**

---

## Step 1: Load Social Media Research

Read ALL of the following documents from the research library. These are the social media marketing knowledge base:

### Required Documents (read in full)

1. **SMB Content Best Practices** — Platform selection, content cadence, content mix ratio, posting frequency, hooks, storytelling, educational content, SMB voice, visual-first, image hooks, caption strategy, 80/20 rule, hashtag strategy, engagement benchmarks
   ```
   ~/Projects/research-library/docs/domains/smb-content-best-practices.md
   ```

2. **SMB Campaign Best Practices** — Video-first, social commerce, Instagram Shopping, TikTok, Reels, Shorts, UGC, micro-influencers, campaign duration, platform selection, community building, batch content creation, video hooks, AI content tools
   ```
   ~/Projects/research-library/docs/domains/smb-campaign-best-practices.md
   ```

3. **Platform x Content Type Performance Matrix** — Content type performance by platform, industry content ratios, educate/trust/engage/convert/celebrate mix, carousel engagement, platform-specific benchmarks, industry-specific strategies
   ```
   ~/Projects/research-library/docs/domains/platform-content-type-matrix.md
   ```

4. **SMB Persona Social Content** — Buyer personas, persona-to-content mapping, content pillars, psychographic/behavioral segmentation, persona content matrix, platform selection
   ```
   ~/Projects/research-library/docs/domains/smb-persona-social-content.md
   ```

5. **Seasonal Cadence Framework** — Seasonal marketing, holiday marketing, content cadence, posting frequency benchmarks, Q4 marketing, holiday calendar, seasonal engagement patterns, diminishing returns
   ```
   ~/Projects/research-library/docs/domains/seasonal-cadence-framework.md
   ```

6. **Video Production Optimization** — Video hooks, AIDA for video, UGC, viral engineering, engagement benchmarks, content repurposing, psychological triggers for video
   ```
   ~/Projects/research-library/docs/domains/video-production-optimization.md
   ```

7. **Promotional Link Placement** — Platform-specific caption link best practices, CTA optimization, link-in-bio, social commerce
   ```
   ~/Projects/research-library/docs/domains/promotional-link-placement.md
   ```

8. **EQ Scoring Framework** — Emotional resonance, psychological triggers, neuromarketing, identity alignment, urgency
   ```
   ~/Projects/research-library/docs/domains/eq-scoring-framework.md
   ```

9. **Threads Platform Strategy** — Threads algorithm, engagement, posting frequency, demographics, conversational marketing, text-first platform
   ```
   ~/Projects/research-library/docs/domains/threads-platform-strategy.md
   ```

10. **YouTube SMB Cadence & Content Strategy** — YouTube Shorts, community posts, algorithm, SEO, long-form vs short-form, channel growth, evergreen content
    ```
    ~/Projects/research-library/docs/domains/youtube-smb-cadence.md
    ```

11. **Google Business Profile Content Strategy** — Local SEO, near-me searches, local pack, GMB posts/offers/events, posting frequency, review management, geo-tagging
    ```
    ~/Projects/research-library/docs/domains/gmb-content-strategy.md
    ```

12. **SMB Template Audit 2026** — Content pillars, Quick Create template gaps, engagement/promotional/celebration formats, 4 Es framework, content mix ratios
    ```
    ~/Projects/research-library/docs/domains/smb-template-audit-2026.md
    ```

### Optional: Check for New Social Media Research

Search for any additional social-media-related docs that may have been added since this command was created:

```bash
grep -rl "subjects:.*social-media\|subjects:.*instagram\|subjects:.*tiktok\|subjects:.*posting-frequency\|subjects:.*content-cadence\|domain:.*social" ~/Projects/research-library/docs/
```

Read any new matches not already in the list above.

---

## Step 2: Synthesize Key Principles

After reading all documents, build a mental model of the core principles. Group them into categories:

### Categories to Extract

1. **Content Mix** — Content pillars, mix ratios (80/20 rule), educate/trust/engage/convert/celebrate balance, industry-specific ratios
2. **Platform Mastery** — Instagram, TikTok, LinkedIn, Facebook, YouTube, Threads, GMB — algorithm behaviors, optimal formats, posting frequency, engagement benchmarks
3. **Cadence & Timing** — Posting frequency by platform, seasonal peaks, holiday calendar, batch creation, diminishing returns
4. **Video & Visual** — Video hooks (first 3 seconds), thumbnail psychology, Reels/Shorts/TikTok formats, UGC, carousel engagement
5. **Audience Targeting** — Persona-to-content mapping, psychographic segmentation, platform selection by persona, content pillars per audience
6. **Engagement & CTAs** — Hook formulas, caption strategy, hashtag strategy, link placement, social commerce, link-in-bio
7. **EQ & Psychology** — Emotional resonance scoring, identity alignment, urgency triggers, neuromarketing for social
8. **SMB-Specific** — Resource constraints, batch creation, content repurposing, community building, micro-influencer partnerships

---

## Step 3: Check Session Context

Look at the current conversation for:

1. **Active content plan** — Is content being generated, campaigns being designed, or templates being built?
2. **Active implementation plan** — Any plan mode output or step-by-step approach involving social media features?
3. **LLM prompts for content generation** — Edge functions or services that generate captions, posts, campaigns?
4. **UI/UX for social features** — Calendar, campaign builder, content preview, template editor?
5. **Debugging session** — Is the user debugging content quality, scheduling, or generation issues?

---

## Step 4: Present Results

### If a plan or social media context exists in the session:

```
## Social Media Best Practices — Applied to Current Plan

**Research loaded:** {count} documents, {total_size} of social media knowledge

### Principles Most Relevant to This Plan

{List 3-7 specific principles from the research that directly apply to the current plan. Be specific — cite the technique name and which document it comes from.}

### Updated Plan

{Restate the plan with social media improvements integrated. Keep the same structure but annotate where social media principles improve it. Be concise — bullet points, not paragraphs.}

### Key Social Media Improvements

| Original | Improved | Principle Applied |
|----------|----------|-------------------|
| {what was there} | {what it should be} | {which technique} |

---

*Social media context retained for remainder of session. All subsequent content and campaign work will apply these principles.*
```

### If NO plan exists in the session:

```
## Social Media Best Practices — Loaded into Context

**Research loaded:** {count} documents, {total_size} of social media knowledge

### Core Principles Now Active

**Content Mix:** {2-3 key content mix patterns}
**Platforms:** {2-3 key platform insights}
**Cadence:** {2-3 key timing/frequency patterns}
**Video:** {2-3 key video/visual principles}
**Audience:** {2-3 key persona/targeting insights}
**Engagement:** {2-3 key hook/CTA patterns}
**SMB-Specific:** {2-3 key SMB constraints and strategies}

### Quick Reference

- **80/20 rule** — 80% value content (educate, entertain, inspire), 20% promotional
- **Platform-native content** — don't cross-post identical content; adapt format per platform
- **Video hooks in first 3 seconds** — pattern interrupt, bold claim, or curiosity gap
- **Posting cadence** — consistency > frequency; each platform has a sweet spot
- **Seasonal planning** — plan 4-6 weeks ahead, increase frequency during peak seasons
- **Content repurposing** — 1 long-form piece = 8-12 platform-specific pieces
- **EQ scoring** — emotional resonance > feature lists for SMB content
- **Industry-specific ratios** — each vertical has different optimal content mix (see matrix)
- **Batch creation** — SMBs should batch 2-4 weeks of content in one session
- **Carousel > single image** — 2-3x engagement on Instagram, LinkedIn

---

*Social media context retained for remainder of session. When we work on content, campaigns, or social features, these principles will be applied automatically.*
```

---

## Rules

1. **NO ACTION** — Do not modify any files, run any commands, or make any changes
2. **NO CODE** — Do not output code blocks with implementation. Principles only.
3. **CONCISE** — Synthesize, don't dump. The user wants actionable principles, not raw document contents
4. **CONTEXT RETENTION** — After presenting, keep all social media knowledge active for the rest of the session. Apply it to any subsequent social media, content, or campaign work without being asked again.
5. **PLAN IMPROVEMENT** — When applying to a plan, focus on the social-media-facing parts (content generation, platform strategy, posting cadence, caption quality). Don't restructure non-social parts of the plan.
