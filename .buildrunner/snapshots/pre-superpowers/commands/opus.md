---
description: Load Claude Opus/Sonnet prompting best practices (4.5-4.6), apply to current session plans
allowed-tools: Read, Glob, Grep
model: opus
---

# Claude Prompting Context: /opus

**PURPOSE: Load Claude-specific prompting best practices (Opus & Sonnet 4.5-4.6) into context. If a fix plan or implementation plan exists in the current session, apply prompting principles to improve it and present the updated plan. No action taken, no code written.**

---

## Step 1: Load Claude Prompting Research

Read the following document from the research library in full (TL;DR + all sections):

**Claude Opus & Sonnet Prompting (4.5 + 4.6)** — Model-specific behaviors, adaptive thinking, effort parameter, structured output, temperature, multishot, agentic system patterns, prefill migration, subagent orchestration, system prompt architecture
```
~/Projects/research-library/docs/techniques/claude-opus-prompting-consistency.md
```

### Optional: Check for New Claude-Specific Research

Search for any additional Claude-specific prompting docs added since this command was created:

```bash
grep -rl "subjects:.*adaptive-thinking\|subjects:.*effort-parameter\|subjects:.*prefill-migration\|subjects:.*interleaved-thinking\|subjects:.*claude.*prompting" ~/Projects/research-library/docs/
```

Read any new matches not already loaded.

---

## Step 2: Synthesize Key Principles

After reading, build a mental model grouped into these categories:

1. **4.5-Specific** — Instruction sensitivity, word choice ("think" avoidance with thinking disabled), concise style
2. **4.6-Specific** — Adaptive thinking + effort parameter, prefill removal (use structured outputs), overly agentic behavior (add safety guardrails), overthinking prevention, subagent orchestration control, LaTeX defaults, anti-laziness over-prompting causes overtriggering
3. **Structural Patterns** — XML tags, structured outputs API (`output_config.format`), format specification, schema hinting
4. **Consistency Techniques** — Temperature settings, multishot examples, format matching, personality anchoring
5. **Agentic Patterns** — Safety guardrails, subagent constraints, parallel tool calls, long-horizon state tracking
6. **System Architecture** — System vs user prompt roles, fixed vs adaptive elements, chat agent design

---

## Step 3: Check Session Context

Look at the current conversation for:

1. **Active fix plan** — Has a `/fixplan`, `/begin`, or manual plan been discussed?
2. **Active implementation plan** — Any plan mode output or step-by-step approach?
3. **LLM prompts being written or modified** — Edge functions, generators, or services that contain LLM prompts?
4. **Debugging session** — Is the user debugging prompt-related issues (hallucinations, inconsistent output, wrong format)?

---

## Step 4: Present Results

### If a plan or fix exists in the session:

```
## Claude Prompting Best Practices — Applied to Current Plan

**Research loaded:** claude-opus-prompting-consistency.md (850 lines, 4.5-4.6 coverage)

### Principles Most Relevant to This Plan

{List 3-7 specific principles from the research that directly apply to the current plan. Be specific — cite the technique name and which section it comes from.}

### Updated Plan

{Restate the plan with prompting improvements integrated. Keep the same structure but annotate where prompting principles improve it. Be concise — bullet points, not paragraphs.}

### Key Prompting Improvements

| Original | Improved | Principle Applied |
|----------|----------|-------------------|
| {what was there} | {what it should be} | {which technique} |

---

*Claude prompting context retained for remainder of session. All subsequent LLM prompt work will apply these principles.*
```

### If NO plan exists in the session:

```
## Claude Prompting Best Practices — Loaded into Context

**Research loaded:** claude-opus-prompting-consistency.md (850 lines, 4.5-4.6 coverage)

### Core Principles Now Active

**4.6 Behavioral:** {2-3 key 4.6 behaviors}
**Adaptive Thinking:** {2-3 key thinking/effort patterns}
**Structural:** {2-3 key structural patterns}
**Consistency:** {2-3 key consistency techniques}
**Anti-Patterns:** {2-3 things to avoid}

### Quick Reference

- **Adaptive thinking** + **effort parameter** (low/medium/high/max) to control thinking depth and token spend
- **Structured outputs API** (`output_config.format`) to enforce output format (prefill removed in 4.6)
- **Multishot > instructions** for format consistency (3-5 diverse examples)
- **XML tags** for structured sections (Claude responds well to explicit structure)
- **Dial back anti-laziness prompting** — 4.6 overtriggers on aggressive tool-use instructions
- **Add safety guardrails** for agentic 4.6 behavior (destructive actions, shared systems)
- **Temperature 0.3-0.5** for factual, 0.7-0.9 for creative
- **Scope constraints** to prevent scope creep in responses

---

*Claude prompting context retained for remainder of session. When we work on LLM prompts, these principles will be applied automatically.*
```

---

## Rules

1. **NO ACTION** — Do not modify any files, run any commands, or make any changes
2. **NO CODE** — Do not output code blocks with implementation. Principles only.
3. **CONCISE** — Synthesize, don't dump. The user wants actionable principles, not raw document contents
4. **CONTEXT RETENTION** — After presenting, keep all prompting knowledge active for the rest of the session. Apply it to any subsequent LLM prompt work without being asked again.
5. **PLAN IMPROVEMENT** — When applying to a plan, focus on the LLM-facing parts (prompts, system messages, output parsing). Don't restructure non-LLM parts of the plan.
