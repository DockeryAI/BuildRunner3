---
description: Load LLM & Claude prompting best practices, apply to current session plans
allowed-tools: Read, Glob, Grep
model: opus
---

# Prompt Engineering Context: /prompt

**PURPOSE: Load all LLM/Claude prompting best practices from the research library into context. If a fix plan or implementation plan exists in the current session, apply prompting principles to improve it and present the updated plan. No action taken, no code written.**

---

## Step 1: Load Core Prompting Research

Read ALL of the following documents from the research library. These are the primary prompting knowledge base:

### Required Documents (read in full — TL;DR + all sections)

1. **Claude Opus & Sonnet Prompting (4.5 + 4.6)** — Model-specific behaviors, adaptive thinking, effort parameter, structured output, temperature, multishot, agentic system patterns, prefill migration, subagent orchestration, system prompt architecture
   ```
   ~/Projects/research-library/docs/techniques/claude-opus-prompting-consistency.md
   ```

2. **LLM Content Prompting Mastery** — AI slop prevention, humanization, brand voice engineering, persona prompting, tone calibration, advanced techniques
   ```
   ~/Projects/research-library/docs/techniques/llm-content-prompting-mastery.md
   ```

3. **Perplexity Prompt Engineering** — RAG-optimized prompting, fail-fast clauses, citation-forcing, scope constraints, schema hinting, decomposed prompts
   ```
   ~/Projects/research-library/docs/techniques/perplexity-prompt-engineering.md
   ```

4. **Claude Automation & Context Management** — Context windows, XML tags, extended thinking, subagents, governance, self-healing patterns
   ```
   ~/Projects/research-library/docs/concepts/claude-automation.md
   ```

5. **LLM Content Safety Guardrails** — System prompt engineering, prompt injection defense, input/output filtering, multi-layer defense patterns
   ```
   ~/Projects/research-library/docs/techniques/llm-content-safety-guardrails.md
   ```

6. **Hallucination Prevention** — Factual grounding, RAG patterns, source verification, semantic entropy
   ```
   ~/Projects/research-library/docs/concepts/hallucination-prevention.md
   ```

### Optional: Check for New Prompting Research

Search for any additional prompting-related docs that may have been added since this command was created:

```bash
grep -rl "techniques:.*llm-prompting\|subjects:.*prompt-engineering\|subjects:.*system-prompts\|subjects:.*adaptive-thinking\|subjects:.*effort-parameter" ~/Projects/research-library/docs/
```

Read any new matches not already in the list above.

---

## Step 2: Synthesize Key Principles

After reading all documents, build a mental model of the core principles. Group them into categories:

### Categories to Extract

1. **Structural Patterns** — XML tags, structured outputs API (`output_config.format`), format specification, schema hinting, decomposed prompts
2. **Consistency Techniques** — Temperature settings, multishot examples, format matching, personality anchoring
3. **Quality Guards** — Fail-fast clauses, hallucination prevention, citation-forcing, scope constraints
4. **Voice & Tone** — Brand voice profiles, AI slop avoidance, humanization framework, persona prompting
5. **System Architecture** — System vs user prompt roles, fixed vs adaptive elements, context management
6. **Safety & Defense** — Multi-layer defense, input validation, output filtering, prompt injection resistance
7. **4.5-Specific** — Instruction sensitivity, word choice ("think" avoidance with thinking disabled), concise style
8. **4.6-Specific** — Adaptive thinking + effort parameter, prefill removal (use structured outputs), overly agentic behavior (add safety guardrails), overthinking prevention, subagent orchestration control, LaTeX defaults, anti-laziness over-prompting causes overtriggering

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
## Prompting Best Practices — Applied to Current Plan

**Research loaded:** {count} documents, {total_size} of prompting knowledge

### Principles Most Relevant to This Plan

{List 3-7 specific principles from the research that directly apply to the current plan. Be specific — cite the technique name and which document it comes from.}

### Updated Plan

{Restate the plan with prompting improvements integrated. Keep the same structure but annotate where prompting principles improve it. Be concise — bullet points, not paragraphs.}

### Key Prompting Improvements

| Original | Improved | Principle Applied |
|----------|----------|-------------------|
| {what was there} | {what it should be} | {which technique} |

---

*Prompting context retained for remainder of session. All subsequent LLM prompt work will apply these principles.*
```

### If NO plan exists in the session:

```
## Prompting Best Practices — Loaded into Context

**Research loaded:** {count} documents, {total_size} of prompting knowledge

### Core Principles Now Active

**Structural:** {2-3 key structural patterns}
**Consistency:** {2-3 key consistency techniques}
**Quality:** {2-3 key quality guards}
**Opus-Specific:** {2-3 key Opus behaviors to leverage}
**Anti-Patterns:** {2-3 things to avoid}

### Quick Reference

- **XML tags** for structured sections (Claude responds well to explicit structure)
- **Multishot > instructions** for format consistency
- **Fail-fast clauses** before generation to prevent hallucination
- **Temperature 0.3-0.5** for factual, 0.7-0.9 for creative
- **Structured outputs API** (`output_config.format`) to enforce output format (prefill removed in 4.6)
- **Adaptive thinking** + **effort parameter** (low/medium/high/max) to control thinking depth and token spend
- **Dial back anti-laziness prompting** — 4.6 overtriggers on aggressive tool-use instructions
- **Add safety guardrails** for agentic 4.6 behavior (destructive actions, shared systems)
- **Scope constraints** to prevent scope creep in responses

---

*Prompting context retained for remainder of session. When we work on LLM prompts, these principles will be applied automatically.*
```

---

## Rules

1. **NO ACTION** — Do not modify any files, run any commands, or make any changes
2. **NO CODE** — Do not output code blocks with implementation. Principles only.
3. **CONCISE** — Synthesize, don't dump. The user wants actionable principles, not raw document contents
4. **CONTEXT RETENTION** — After presenting, keep all prompting knowledge active for the rest of the session. Apply it to any subsequent LLM prompt work without being asked again.
5. **PLAN IMPROVEMENT** — When applying to a plan, focus on the LLM-facing parts (prompts, system messages, output parsing). Don't restructure non-LLM parts of the plan.
