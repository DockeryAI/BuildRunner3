# Research Skill Diff

## Before

- Step 0B read `~/Projects/research-library/` directly with `grep` and `find`.
- Step 8.5 SSHed to Jimmy and ran `~/.buildrunner/scripts/reindex-research.sh`.
- The skill had no documented next-turn completion reader and no session-local pending-ID sidecar.

## After

- Step 0 now checks `.buildrunner/research-queue/completed.jsonl` plus `~/.claude/sessions/research-pending.json` and reports completed, errored, or stalled queue work on the next invocation.
- Step 0B now calls `POST http://10.0.1.106:8100/retrieve` for existing-library context and degrades gracefully with `Jimmy unreachable — proceeding without library context`.
- Step 8.5 now appends a `PendingRecord` JSON line to `.buildrunner/research-queue/pending.jsonl`, writes the session sidecar, and leaves commit/ingest/reindex work to Below.
- The skill now documents the three required user-visible failure modes: Jimmy unreachable, Below offline, and queue stale for more than 24 hours.

## Risk/Rollback

- Pre-change git blob backup: `81926ea487786c484e682fc053d864f10d3bfb55`
- Restore from the stored blob: `git cat-file -p 81926ea487786c484e682fc053d864f10d3bfb55 > ~/.claude/commands/research.md`
- If git objects are unavailable, copy the fenced pre-change snapshot below back into `~/.claude/commands/research.md`.

## Pre-change `research.md`

```markdown
---
description: Deep research on any subject - exhaustive multi-source analysis with unique angles
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Agent
model: claude-sonnet-4-6
# Pinned to 4.6: web fetch + long-context synthesis across many sources.
# Research library Part 11 — long-context regression 91.9→59.2%, BrowseComp 83.7→79.3%.
# `model: opus` alias resolves to 4.7 at runtime; explicit 4.6 pin required here.
---

# Deep Research: /research

<purpose>
Exhaustive, comprehensive research on any subject. Auto-indexes to research library, checks for existing research first. Uses sub-agents for all research — each major sub-topic gets its own Agent running independently in parallel.
</purpose>

---

## Step 0A: Parse Thinking Mode

**Input:** $ARGUMENTS

<thinking_modes>

| First Arg       | Thinking Mode    | Token Budget |
| --------------- | ---------------- | ------------ |
| `ultrathink`    | Maximum thinking | ~32K tokens  |
| `thinkharder`   | Maximum thinking | ~32K tokens  |
| `megathink`     | Deep thinking    | ~10K tokens  |
| `thinkhard`     | Deep thinking    | ~10K tokens  |
| (none of above) | Standard         | Default      |

</thinking_modes>

**Parse and set variables:**

1. If first word matches a trigger: `THINKING_MODE` = that trigger, `RESEARCH_TOPIC` = remaining args
2. If no trigger match: `THINKING_MODE` = "standard", `RESEARCH_TOPIC` = all of $ARGUMENTS

If `ultrathink` or `thinkharder` mode:

- Think harder about this research
- Run 2x more searches (20 instead of 10)
- Verify each major claim with at least 2 independent sources
- Explore at least 3 alternative approaches beyond the mainstream
- Spend extra time on edge cases and failure modes

**Use `RESEARCH_TOPIC` (not $ARGUMENTS) for all subsequent steps.**

---

## Step 0B: Check Existing Research

<rule>Before any new research, check what already exists. Use RESEARCH_TOPIC, not raw $ARGUMENTS.</rule>

```bash
RESEARCH_LIB=~/Projects/research-library

# Search for existing research on this topic
grep -rilF "$RESEARCH_TOPIC" $RESEARCH_LIB/docs/ 2>/dev/null | head -10

# Check index for related entries
grep -iF "$RESEARCH_TOPIC" $RESEARCH_LIB/index.md 2>/dev/null

# List all docs to find semantic matches
find $RESEARCH_LIB/docs -name "*.md" -exec basename {} \; | sort
```

### If Existing Research Found:

Present options to user:

```
## Existing Research Found

I found existing research that may cover this topic:

| Document | Domain | Last Updated |
|----------|--------|--------------|
| [doc-name](path) | {domain} | {date} |

**What would you like to do?**

1. **Enrich existing** - Add new angles not already covered to the existing doc
2. **New research** - Create separate doc (if topic is different enough)
3. **Review first** - Let me show you what's already there before deciding

Which option? (or just tell me what you want)
```

Wait for user response before proceeding.

### If Enriching Existing Doc:

1. Read the existing document fully
2. Identify sections and topics already covered
3. Check the Research Log for documented gaps and failed approaches — prioritize filling these
4. Research ONLY new angles, techniques, or sources not present
5. Append new findings to appropriate sections
6. Add any new subjects to the `subjects:` array (don't remove existing ones)
7. Update the Research Log with new session
8. Update `last_updated` in frontmatter

### If No Existing Research:

Proceed to Step 1.

---

## Step 1: Parse Input & Determine Category

**Arguments provided:** $ARGUMENTS

### Determine Subject

1. **If arguments provided:** Use as the research topic
2. **If NO arguments:** Infer topic from current conversation context

### Auto-Categorize

| Topic Type              | Category      | Examples                                            |
| ----------------------- | ------------- | --------------------------------------------------- |
| Platform-specific       | `domains/`    | twitter scraping, reddit mining, SEC filings        |
| Industry/vertical       | `domains/`    | buyer psychology, sales triggers, competitive intel |
| How-to guides           | `techniques/` | sentiment analysis, data enrichment, error handling |
| Theoretical foundations | `concepts/`   | hallucination prevention, context management        |
| Bug patterns            | `debugging/`  | react crashes, loading issues, error patterns       |

**Filename:** Slugify the topic (lowercase, hyphens, no special chars)

---

## Step 2: Research Strategy

<source_types>
Each sub-agent should cover these source types for its sub-topic:

1. **Official Documentation** — Official docs, GitHub repos, release notes, changelogs
2. **Authoritative Sources** — Academic papers, conference talks, books, maintainer blog posts
3. **Community Knowledge** — Stack Overflow, Reddit, Hacker News, Dev.to, Medium
4. **Real-World Implementations** — Open source projects, company case studies, postmortems, benchmarks
5. **Full Spectrum** — Mainstream solutions, alternative approaches, edge cases/gotchas, anti-patterns

Every approach should be proven in real-world production use, backed by evidence, and tested at scale. Avoid theoretical or untested ideas.
</source_types>

---

## Step 2.5: Frame the Research Question (SCQA)

<scqa_framing>
Before decomposing into sub-topics, frame the research question precisely. This prevents researching broadly when a precise question would yield better results.

**Situation:** What is the current state? What do we already know?
**Complication:** What challenge, gap, or contradiction demands investigation?
**Question:** What specific, answerable question should this research address?

Write a 2-3 sentence SCQA frame. This becomes the north star for sub-topic selection — every sub-topic should advance the answer to this question.

If the topic is broad and exploratory (e.g., "all things research"), the Question becomes: "What are the most impactful approaches, and how do they compare?" In this case SCQA serves as orientation, not constraint.
</scqa_framing>

---

## Step 3: Decompose Topic into Sub-Topics

Break the RESEARCH_TOPIC into 3-6 major sub-topics using the SCQA frame from Step 2.5.

### Decomposition Framework

Use this 6-lens framework. Select the 3-6 most relevant lenses:

| Lens                    | What It Covers                                             | Example (for "redis caching")                                   |
| ----------------------- | ---------------------------------------------------------- | --------------------------------------------------------------- |
| **Foundations**         | Core concepts, how it works, mental models                 | Cache patterns (write-through, write-behind, cache-aside)       |
| **Implementation**      | Production setup, configuration, scaling, deployment       | Cluster mode, sentinel, memory management, persistence          |
| **Alternatives**        | Competing solutions, comparisons, trade-offs               | Memcached vs Dragonfly vs KeyDB vs Valkey                       |
| **Failure Modes**       | Anti-patterns, gotchas, what breaks at scale               | Thundering herd, cache stampede, hot keys, memory fragmentation |
| **Real-World Evidence** | Case studies, benchmarks, production postmortems           | How Discord/Twitter/Instagram use Redis at scale                |
| **Cutting Edge**        | Emerging techniques, recent developments, future direction | Redis 8 features, serverless Redis, WASM modules                |

Simple topics may need 3 lenses. Complex topics should use all 6.

Every sub-topic gets its own dedicated sub-agent. Do not research sub-topics in the main context.

---

## Step 3.5: Execute Research via Sub-Agents

Launch one Agent per sub-topic. All sub-agents run in parallel using a single message with multiple Agent tool calls.

For each sub-topic, call the Agent tool with:

- `subagent_type`: `"general-purpose"`
- `model`: `"opus"`
- `description`: Short label like "Research: {sub-topic name}"

<sub_agent_prompt_template>
Use this template EXACTLY, filling in the variables:

```
<role>
You are a research sub-agent. Your job is to produce thorough, well-sourced research on ONE sub-topic. The parent agent will synthesize your output — focus on gathering quality findings with strong evidence.
</role>

<sub_topic>
{sub-topic name and description}
</sub_topic>

<parent_topic>
{RESEARCH_TOPIC}
</parent_topic>

<scqa_frame>
{The SCQA frame from Step 2.5 — gives sub-agent the research question context}
</scqa_frame>

<instructions>
Before searching, state 2-3 hypotheses about what you expect to find for this sub-topic. These hypotheses guide your search strategy and help identify surprising findings.

1. Run at minimum 5 WebSearch queries covering:
   - Official documentation and specs
   - Production implementations and case studies
   - Community discussions (Reddit, HN, Stack Overflow)
   - Benchmarks and comparisons
   - Edge cases, gotchas, and failure modes

2. For every promising search result, use WebFetch to read the full content. Do not skip sources.

3. Cross-reference findings across multiple sources. When sources contradict each other, report BOTH positions with their sources — do not silently pick one.

4. If you find a sub-sub-topic that deserves deeper investigation, dig into it.

5. Include raw data, direct quotes, specific version numbers, and concrete examples where available.

6. Prefer authoritative sources (official docs, academic papers, maintainer posts) over SEO-optimized content farms and listicles. When a blog restates official docs, cite the original.
</instructions>

<output_format>
Structure your output using this template:

## Hypotheses

### H1: {hypothesis}
**Verdict:** CONFIRMED | PARTIAL | REFUTED | UNKNOWN
**Surprise level:** Expected | Somewhat Surprising | Very Surprising

### H2: {hypothesis}
...

## Key Findings

### Finding 1: {title}
- **Detail:** {thorough explanation with evidence}
- **Source:** [{source title}]({URL})
- **Credibility:** [Official] | [Peer-Reviewed] | [Community] | [Blog] | [Unverified]
- **Confidence:** HIGH | MEDIUM | LOW (based on source count and credibility)

### Finding 2: {title}
...

## Code Examples (if applicable)
{Real production patterns only — no toy examples. Include the source where you found each.}

## Metrics & Benchmarks
{Specific numbers only — percentages, latencies, throughput, scale. No vague claims.}

## Gotchas & Edge Cases
{What breaks in production. Include the context where each was discovered.}

## Contradictions Found
{Where sources disagreed. Present both sides with URLs. Do NOT resolve — the parent agent will judge.}

## All Sources
| # | Title | URL | Credibility | Key Contribution |
|---|-------|-----|-------------|-----------------|
| 1 | {title} | {url} | [Official]/[Peer-Reviewed]/[Community]/[Blog]/[Unverified] | {what this source contributed} |
</output_format>
```

</sub_agent_prompt_template>

**If `ultrathink` or `thinkharder` mode:** Add inside `<instructions>` for each sub-agent:

```
<ultra_mode>
ULTRA MODE ACTIVE:
- Run at least 10 searches (not 5)
- Verify every major claim with 2+ independent sources
- Explore at least 2 alternative viewpoints per finding
- Spend extra time on edge cases and failure modes
</ultra_mode>
```

After all sub-agents return, collect all results and proceed to Step 3.7.

---

## Step 3.7: Evaluate Sub-Agent Results & Fill Gaps

Review each result for quality before synthesizing.

### Quality Check (per sub-agent)

| Signal                 | Thin Result                                         | Acceptable Result                        |
| ---------------------- | --------------------------------------------------- | ---------------------------------------- |
| Sources found          | 0-2 sources                                         | 3+ sources                               |
| Credibility mix        | All [Blog] or [Unverified]                          | At least 1 [Official] or [Peer-Reviewed] |
| Specificity            | Vague claims, no numbers                            | Concrete metrics, version numbers, dates |
| Contradictions section | Empty (suspicious — means only one viewpoint found) | At least noted "no contradictions found" |
| Hypotheses             | All CONFIRMED (suspicious — no surprises found)     | At least one PARTIAL or REFUTED          |

### If a sub-agent returned thin results:

1. Spawn a follow-up Agent with refined queries:
   - Use different search terms (synonyms, related concepts, specific tool names)
   - Target specific source types that were missing (e.g., "site:reddit.com", "benchmark", "postmortem")
   - Add: "Previous research on this sub-topic found limited results. Try alternative search terms and dig deeper into adjacent topics."

2. If the follow-up also returns thin: Accept it — note in the final document: "Limited public research available on this sub-topic as of {date}."

### Contradiction Aggregation

Collect all `## Contradictions Found` sections across sub-agents. If multiple sub-agents found the same contradiction, it's likely a genuine debate — promote it to the Debated Topics section.

---

## Step 4: Determine Frontmatter Values

<schema_reference>
Read the compact schema for valid values:

```bash
cat ~/Projects/research-library/schema-quick.md
```

If schema-quick.md doesn't exist, fall back to:

```bash
cat ~/Projects/research-library/schema.md
```

</schema_reference>

**Select appropriate values:**

| Field            | How to Determine                                           |
| ---------------- | ---------------------------------------------------------- |
| `title`          | Clear, descriptive title for the research                  |
| `domain`         | Match to schema domains                                    |
| `techniques`     | What methods are used                                      |
| `concepts`       | What concepts are covered                                  |
| `subjects`       | Extract granular technical topics (see below)              |
| `priority`       | high = frequently needed, medium = occasional, low = niche |
| `source_project` | Auto-detect from current working directory (see below)     |
| `created`        | Today's date YYYY-MM-DD                                    |
| `last_updated`   | Today's date YYYY-MM-DD                                    |

### Dynamic source_project Detection

```bash
# Detect project name from current working directory
basename "$(pwd)" 2>/dev/null || echo "general"
```

If the detected name doesn't match a known project, use it anyway — source_project is freeform, not an enum. Common values: synapse, geo-command-center, sales-assistant, buildrunner3, valuedock, general.

### Subject Extraction

As you research, identify specific technical subjects discussed in detail (not just mentioned):

1. **Algorithms & ML:** sbert, cosine-similarity, cross-encoder, bertopic, faiss, tf-idf, etc.
2. **Tools & APIs:** apify, semrush, buzzsumo, perplexity, serpapi, etc.
3. **Techniques:** semantic-search, reranking, intent-classification, rate-limiting, etc.
4. **Business concepts:** buying-signals, switching-signals, trigger-events, etc.
5. **UI/Frontend:** shadcn, radix-ui, tailwind, framer-motion, zustand, etc.
6. **LLM/AI:** rag, semantic-entropy, chain-of-verification, graphrag, etc.

**Format:** lowercase, hyphenated (kebab-case).

---

## Step 5: Synthesize Sub-Agent Results & Write Document

Collect all sub-agent results and synthesize into a single cohesive document.

### Synthesis Protocol

1. **De-duplicate:** Multiple sub-agents may cover the same finding. Merge into one entry, combining source URLs from all agents that found it.

2. **Cross-reference:** When finding X from Agent A is supported by finding Y from Agent B, note this — cross-validated findings are higher confidence.

3. **Hypothesis rollup:** Aggregate hypothesis verdicts across agents. Findings where hypotheses were REFUTED or marked "Very Surprising" deserve prominent placement — these are the discoveries the reader didn't know to look for.

4. **Resolve contradictions:** Check the `## Contradictions Found` sections from all agents.
   - If sources on both sides are credible: Present both positions in the **Debated Topics** section.
   - If one side has stronger credibility: Lead with the stronger position, note the weaker one.
   - Never silently drop a contradicted finding.

5. **Source credibility rollup:** Organize final sources by tier:
   - `[Official]` — Official docs, maintainer posts
   - `[Peer-Reviewed]` — Academic papers, conference proceedings
   - `[Community]` — Stack Overflow, Reddit, HN (high-signal)
   - `[Blog]` — Dev.to, Medium, company blogs
   - `[Unverified]` — Single-source claims, no corroboration

6. **Gap detection:** If a lens from the decomposition framework has thin coverage even after retries, note it: "Gap: Limited public research on {lens} as of {date}."

### Document Template

Use this structure with YAML frontmatter:

```markdown
---
title: { Subject Title }
domain: { domain from schema }
techniques: [{ techniques used }]
concepts: [{ concepts covered }]
subjects: [{ granular technical topics extracted during research }]
priority: high | medium | low
source_project: { auto-detected or "general" }
created: { YYYY-MM-DD }
last_updated: { YYYY-MM-DD }
---

# Research: {Subject}

> **Last Updated:** {ISO Date}
> **Research Sessions:** {count}

## TL;DR

{3-5 bullet executive summary of key findings}

---

## Problem Statement

{Clear definition of what we're solving. Include the SCQA frame.}

---

## Common Solutions

### Solution 1: {Name}

- **What:** {Description}
- **Pros:** {Benefits}
- **Cons:** {Drawbacks}
- **When to use:** {Use cases}
- **Sources:** {URLs}

### Solution 2: {Name}

...

---

## Alternative Approaches

{Other valid solutions beyond the mainstream}

### Approach 1: {Name}

- **What:** {Description}
- **Why it's overlooked:** {Reason}
- **Evidence it works:** {Proof points}
- **Sources:** {URLs}

---

## Real-World Implementations

### {Company/Project 1}

- **Scale:** {Size/scope}
- **Approach:** {What they did}
- **Results:** {Outcomes}
- **Source:** {URL}

---

## Trade-offs & Considerations

| Approach | Complexity     | Performance | Maintainability | Cost |
| -------- | -------------- | ----------- | --------------- | ---- |
| {A}      | {Low/Med/High} | {metrics}   | {rating}        | {$}  |

---

## Anti-Patterns (What NOT To Do)

1. **{Anti-pattern 1}:** {Why it fails}
2. **{Anti-pattern 2}:** {Why it fails}

---

## Debated Topics

{Genuine debates where credible sources disagree. Present both sides with evidence.}

### {Topic 1}: {Position A} vs. {Position B}

- **Position A:** {argument with sources}
- **Position B:** {argument with sources}
- **Current evidence leans:** {A/B/Neither — explain why}

---

## Recommendations

{Based on research, what should we actually do?}

### For Our Use Case:

1. {Recommendation 1}
2. {Recommendation 2}

---

## Sources

### [Official] Official Documentation

- [{Title}]({URL})

### [Peer-Reviewed] Academic & Research

- [{Title}]({URL})

### [Community] Community Discussions

- [{Title}]({URL})

### [Blog] Practitioner Insights

- [{Title}]({URL})

---

## Research Log

### Session {N} - {Date}

- **SCQA Frame:** {The research question}
- **Searched:** {queries}
- **Found:** {key findings}
- **Surprises:** {hypotheses that were refuted or findings that were unexpected}
- **Gaps identified:** {areas where research was thin — these become starting points for future sessions}
- **Failed approaches:** {search terms or angles that produced no useful results}
- **Added:** {sections updated}
```

---

## Step 6: Write Document to Library

Save to the correct category folder:

```bash
RESEARCH_LIB=~/Projects/research-library/docs

CATEGORY={determined category}
FILENAME={slugified topic}.md

# Write the document
# Path: $RESEARCH_LIB/$CATEGORY/$FILENAME
```

---

## Step 6.5: Validate & Expand Subjects

After writing the document, validate subjects against schema:

### 1. Extract subjects from your new/updated doc

```bash
grep "subjects:" ~/Projects/research-library/docs/{category}/{filename}.md
```

### 2. Check each subject against schema

```bash
grep "{subject}" ~/Projects/research-library/schema-quick.md 2>/dev/null || grep "{subject}" ~/Projects/research-library/schema.md
```

### 3. Handle NEW subjects not in schema

If you find subjects that don't exist in schema.md:

a) Categorize the new subject:

- Algorithms & ML: embeddings, models, similarity measures, clustering
- Tools & APIs: external services, platforms, SDKs
- Techniques & Patterns: methods, approaches, workflows
- Business Concepts: sales, marketing, buyer behavior terms
- UI/Frontend: component libraries, state management, styling
- LLM & AI: prompting, RAG, hallucination, context

b) Confirm with user before adding:

```
I found new subjects not in schema.md:

| Subject | Category | Description |
|---------|----------|-------------|
| `{new-subject}` | {category} | {one-line description} |

Add to schema.md? [Y/n]
```

c) If user confirms: Update schema.md with kebab-case entries.
d) If user declines: Still include subjects in the document frontmatter. Log in Research Log.

---

## Step 7: Update Index

After creating/updating the document, update the master index:

```bash
cat ~/Projects/research-library/index.md
```

Add entry to the appropriate section in index.md:

1. Find the correct category section (domains, techniques, concepts, debugging)
2. Add a new row to the table with: document name, description, priority
3. If it's a new domain/technique/concept, add to cross-references section

---

## Step 8: Summary Report

After completing all research:

```
## Research Complete: {Subject}

**Document saved:** ~/Projects/research-library/docs/{category}/{filename}.md
**Indexed:** Added to index.md under {category}

**What I learned:**

{3-5 sentences summarizing the most important insights discovered}

**Surprising findings:**

{Hypotheses that were refuted, or findings no one would have predicted}

**Recommendation for this project:**

{1-2 sentences on what approach best fits THIS project's context}

**Sources:** {number} sources consulted across {categories covered}

**Gaps for future research:**
- {gap 1 — from Research Log}
- {gap 2}

**Related research you might also want:**
- {related doc 1}
- {related doc 2}
```

---

## Step 8.5: Reindex the research library on Jimmy (automatic, silent)

After the document is saved, rebuild the LanceDB `research_library` table
so the new doc becomes retrievable via `/retrieve` and the context bundle.

Canonical host per Phase 1: **Jimmy (`10.0.1.106`)** — Muddy authors, Jimmy
mirrors. The reindex script is idempotent (drops + rebuilds).

```bash
# Preferred: run on Jimmy so the table lands on the canonical mirror.
ssh byronhudson@10.0.1.106 'bash -lc "~/.buildrunner/scripts/reindex-research.sh"' \
  >/dev/null 2>&1 \
  || ~/.buildrunner/scripts/reindex-research.sh --dry-run >/dev/null 2>&1 || true
```

Skip silently if Jimmy is unreachable — the next scheduled sync will
catch up.

### What this command actually does (and does not)

- **Runs:** Claude researches (sub-agents), synthesizes findings, writes
  the doc to `~/Projects/research-library/`, updates `index.md`, and
  kicks `reindex-research.sh` on Jimmy.
- **Does not run:** there is no separate "retrieve → rerank → inject"
  pipeline stage inside `/research`. Retrieval happens later, on demand,
  via `POST /retrieve` on Jimmy (`core.cluster.context_bundle` +
  `api/routes/retrieve.py`). `/research` is end-to-end write-and-index.
- **Verify retrieve host:** `~/.buildrunner/scripts/verify-retrieve-host.sh`
  confirms `/retrieve` resolves to Jimmy.

---

## Rules

<rules>
1. **CHECK FIRST** - Always check for existing research before starting
2. **ASK BEFORE DUPLICATING** - If related research exists, confirm with user
3. **FRAME FIRST** - Use SCQA to define the question before decomposing
4. **EXHAUSTIVE** - Don't stop at first answer, keep digging
5. **MULTI-SOURCE** - Verify findings across multiple sources
6. **PROVEN ONLY** - Every approach should have real-world evidence
7. **HYPOTHESIZE** - State expectations before searching, track surprises
8. **TRACK GAPS** - Document what was thin or missing for future sessions
9. **AUTO-CATEGORIZE** - Put docs in the right folder automatically
10. **AUTO-INDEX** - Always update index.md after creating/updating docs
11. **ENRICH DON'T DUPLICATE** - Add to existing docs when topic overlaps
12. **PREFER AUTHORITATIVE SOURCES** - Official docs and papers over SEO content farms
</rules>

---

## Deduplication Logic

Before creating a new doc, check for semantic overlap:

| New Topic           | Existing Doc                | Action                            |
| ------------------- | --------------------------- | --------------------------------- |
| "twitter API"       | twitter-voc-mining.md       | Enrich existing                   |
| "twitter ads API"   | twitter-voc-mining.md       | Ask user - could be new or enrich |
| "facebook scraping" | (none)                      | Create new                        |
| "react errors"      | react-debugging-patterns.md | Enrich existing                   |
| "vue errors"        | react-debugging-patterns.md | Create new (different framework)  |

When in doubt, ask the user.

---

## What This Command Does

- Frames the research question with SCQA before investigating
- Checks existing research before starting
- Offers to enrich rather than duplicate
- Tracks hypotheses and highlights surprises
- Auto-categorizes into correct folder
- Auto-updates index.md
- Creates proper YAML frontmatter
- Exhaustive multi-source research
- Documents gaps and failed approaches for future research momentum

## What This Command Does NOT Do

- Create duplicate research without asking
- Skip the existing research check
- Leave index.md out of date
- Create docs without frontmatter
- Accept findings without evidence
```
