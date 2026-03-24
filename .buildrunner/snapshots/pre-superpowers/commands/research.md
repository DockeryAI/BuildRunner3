---
description: Deep research on any subject - exhaustive multi-source analysis with unique angles
allowed-tools: Read, Write, Edit, Bash, Grep, Glob, WebSearch, WebFetch, Agent
model: opus
---

# Deep Research: /research

**PURPOSE: Exhaustive, comprehensive research on any subject. Auto-indexes to research library, checks for existing research first.**

**ARCHITECTURE: This skill uses SUB-AGENTS for all research. Each major sub-topic gets its own Agent (subagent_type="general-purpose") that runs independently and is instructed to be maximally thorough. Sub-agents run in parallel when possible.**

---

## Step 0A: Parse Thinking Mode (CHECK FIRST)

**Input:** $ARGUMENTS

**Check if first argument is a thinking mode trigger:**

| First Arg | Thinking Mode | Token Budget |
|-----------|---------------|--------------|
| `ultrathink` | Maximum thinking | ~32K tokens |
| `thinkharder` | Maximum thinking | ~32K tokens |
| `megathink` | Deep thinking | ~10K tokens |
| `thinkhard` | Deep thinking | ~10K tokens |
| (none of above) | Standard | Default |

**Parse and set variables:**
1. If first word matches a trigger: `THINKING_MODE` = that trigger, `RESEARCH_TOPIC` = remaining args
2. If no trigger match: `THINKING_MODE` = "standard", `RESEARCH_TOPIC` = all of $ARGUMENTS

**Examples:**
- `/research ultrathink react hydration` → `THINKING_MODE=ultrathink`, `RESEARCH_TOPIC="react hydration"`
- `/research thinkharder API rate limiting` → `THINKING_MODE=ultrathink`, `RESEARCH_TOPIC="API rate limiting"`
- `/research megathink caching strategies` → `THINKING_MODE=megathink`, `RESEARCH_TOPIC="caching strategies"`
- `/research redis patterns` → `THINKING_MODE=standard`, `RESEARCH_TOPIC="redis patterns"`

**CRITICAL:** If `ultrathink` or `thinkharder` mode:
- You MUST think harder and think very hard about this research
- Run 2x more searches (20 instead of 10)
- Verify each major claim with at least 2 independent sources
- Explore at least 3 alternative approaches beyond the mainstream
- Spend extra time on edge cases and failure modes

**Use `RESEARCH_TOPIC` (not $ARGUMENTS) for all subsequent steps.**

---

## Step 0B: Check Existing Research (ALWAYS DO THIS FIRST)

**Before ANY new research, check what already exists.**

**IMPORTANT:** Use `RESEARCH_TOPIC` variable (the stripped topic), NOT raw $ARGUMENTS.

```bash
RESEARCH_LIB=~/Projects/research-library

# Search for existing research on this topic (use -F for literal string matching)
grep -rilF "$RESEARCH_TOPIC" $RESEARCH_LIB/docs/ 2>/dev/null | head -10

# Check index for related entries (use -F for literal matching)
grep -iF "$RESEARCH_TOPIC" $RESEARCH_LIB/index.md 2>/dev/null

# List all docs to find semantic matches
find $RESEARCH_LIB/docs -name "*.md" -exec basename {} \; | sort
```

**Note:** Using `-F` flag for fixed-string matching prevents issues with special characters like `()`, `*`, `+` in topic names.

### If Existing Research Found:

**STOP and present options to user:**

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

**Wait for user response before proceeding.**

### If Enriching Existing Doc:

1. Read the existing document fully
2. Identify sections and topics already covered
3. Research ONLY new angles, techniques, or sources not present
4. Append new findings to appropriate sections
5. **Add any new subjects to the `subjects:` array** (don't remove existing ones)
6. Update the Research Log with new session
7. Update `last_updated` in frontmatter

### If No Existing Research:

Proceed to Step 1.

---

## Step 1: Parse Input & Determine Category

**Input format:** `/research [topic]`

**Arguments provided:** $ARGUMENTS

### Determine Subject

1. **If arguments provided:** Use as the research topic
2. **If NO arguments:** Infer topic from current conversation context

### Auto-Categorize

Determine the correct category based on the topic:

| Topic Type | Category | Examples |
|------------|----------|----------|
| Platform-specific | `domains/` | twitter scraping, reddit mining, SEC filings |
| Industry/vertical | `domains/` | buyer psychology, sales triggers, competitive intel |
| How-to guides | `techniques/` | sentiment analysis, data enrichment, error handling |
| Theoretical foundations | `concepts/` | hallucination prevention, context management |
| Bug patterns | `debugging/` | react crashes, loading issues, error patterns |

**Filename:** Slugify the topic (lowercase, hyphens, no special chars)
- "Twitter API rate limits" → `twitter-api-rate-limits.md`
- "How to handle React hydration" → `react-hydration.md`

---

## Step 2: Research Strategy

**Research MUST be exhaustive. Each sub-agent (Step 3.5) should cover these source types for its sub-topic:**

### Source Types (sub-agents must cover ALL relevant ones)
1. **Official Documentation** — Official docs, GitHub repos, release notes, changelogs
2. **Authoritative Sources** — Academic papers, conference talks, books, maintainer blog posts
3. **Community Knowledge** — Stack Overflow, Reddit, Hacker News, Dev.to, Medium
4. **Real-World Implementations** — Open source projects, company case studies, postmortems, benchmarks
5. **Full Spectrum** — Mainstream solutions, alternative approaches, edge cases/gotchas, anti-patterns

**CRITICAL: Every approach MUST be:**
- Proven in real-world production use
- Backed by evidence (case studies, benchmarks, testimonials)
- Tested at scale by actual teams
- NOT theoretical or untested ideas

---

## Step 3: Decompose Topic into Sub-Topics

**Before executing research, break the RESEARCH_TOPIC into 3-6 major sub-topics.**

### Decomposition Framework

Use this 6-lens framework to generate sub-topics. Not all lenses apply to every topic — select the 3-6 most relevant:

| Lens | What It Covers | Example (for "redis caching") |
|------|---------------|-------------------------------|
| **Foundations** | Core concepts, how it works, mental models | Cache patterns (write-through, write-behind, cache-aside) |
| **Implementation** | Production setup, configuration, scaling, deployment | Cluster mode, sentinel, memory management, persistence |
| **Alternatives** | Competing solutions, comparisons, trade-offs | Memcached vs Dragonfly vs KeyDB vs Valkey |
| **Failure Modes** | Anti-patterns, gotchas, what breaks at scale | Thundering herd, cache stampede, hot keys, memory fragmentation |
| **Real-World Evidence** | Case studies, benchmarks, production postmortems | How Discord/Twitter/Instagram use Redis at scale |
| **Cutting Edge** | Emerging techniques, recent developments, future direction | Redis 8 features, serverless Redis, WASM modules |

**Select 3-6 lenses based on topic complexity.** Simple topics (debugging patterns) may need 3. Complex topics (distributed systems) should use all 6.

**CRITICAL: Every sub-topic MUST get its own dedicated sub-agent. Do NOT research sub-topics yourself in the main context.**

---

## Step 3.5: Execute Research via Sub-Agents (MANDATORY)

**Launch one Agent per sub-topic. ALL sub-agents MUST run in parallel using a single message with multiple Agent tool calls.**

For each sub-topic, call the Agent tool with:
- `subagent_type`: `"general-purpose"`
- `model`: `"opus"`
- `description`: Short label like "Research: {sub-topic name}"

**Sub-agent prompt template (use this EXACTLY, filling in the variables):**

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

<instructions>
1. Run at MINIMUM 5 WebSearch queries covering:
   - Official documentation and specs
   - Production implementations and case studies
   - Community discussions (Reddit, HN, Stack Overflow)
   - Benchmarks and comparisons
   - Edge cases, gotchas, and failure modes

2. For EVERY promising search result, use WebFetch to read the FULL content. Do not skip sources.

3. Cross-reference findings across multiple sources. When sources CONTRADICT each other, report BOTH positions with their sources — do not silently pick one.

4. If you find a sub-sub-topic that deserves deeper investigation, dig into it. Do not leave stones unturned.

5. Include raw data, direct quotes, specific version numbers, and concrete examples where available.
</instructions>

<output_format>
Structure your output using EXACTLY this template:

## Key Findings

### Finding 1: {title}
- **Detail:** {thorough explanation with evidence}
- **Source:** [{source title}]({URL})
- **Credibility:** [Official] | [Peer-Reviewed] | [Community] | [Blog] | [Unverified]

### Finding 2: {title}
...

## Code Examples (if applicable)
{Real production patterns only — no toy examples. Include the source where you found each.}

## Metrics & Benchmarks
{Specific numbers only — percentages, latencies, throughput, scale. No vague claims like "fast" or "scalable".}

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

**If `ultrathink` or `thinkharder` mode:** Add inside `<instructions>` for each sub-agent:
```
<ultra_mode>
ULTRA MODE ACTIVE:
- Run at least 10 searches (not 5)
- Verify every major claim with 2+ independent sources
- Explore at least 2 alternative viewpoints per finding
- Spend extra time on edge cases and failure modes
- Be maximally thorough — explore all angles before concluding
</ultra_mode>
```

**After all sub-agents return:** Collect all results. Proceed to Step 3.7 before synthesizing.

---

## Step 3.7: Evaluate Sub-Agent Results & Fill Gaps

**After all sub-agents return, review each result for quality before synthesizing.**

### Quality Check (per sub-agent)

| Signal | Thin Result | Acceptable Result |
|--------|-------------|-------------------|
| Sources found | 0-2 sources | 3+ sources |
| Credibility mix | All [Blog] or [Unverified] | At least 1 [Official] or [Peer-Reviewed] |
| Specificity | Vague claims, no numbers | Concrete metrics, version numbers, dates |
| Contradictions section | Empty (suspicious — means only one viewpoint found) | At least noted "no contradictions found" |

### If a sub-agent returned thin results:

1. **Do NOT just accept it.** Spawn a follow-up Agent for that sub-topic with refined queries:
   - Use different search terms (synonyms, related concepts, specific tool names)
   - Target specific source types that were missing (e.g., "site:reddit.com", "benchmark", "postmortem")
   - Add: `"Previous research on this sub-topic found limited results. Try alternative search terms and dig deeper into adjacent topics."`

2. **If the follow-up ALSO returns thin:** Accept it — the topic genuinely has limited coverage. Note this in the final document: `"Limited public research available on this sub-topic as of {date}."`

### Contradiction Aggregation

Collect all `## Contradictions Found` sections across sub-agents. If multiple sub-agents found the same contradiction, it's likely a genuine debate in the field — highlight it prominently in the final document.

---

## Step 4: Determine Frontmatter Values

**Read the schema for valid values:**
```bash
cat ~/Projects/research-library/schema.md
```

**Select appropriate values:**

| Field | How to Determine |
|-------|------------------|
| `title` | Clear, descriptive title for the research |
| `domain` | Match to schema domains (social-voc-mining, buyer-psychology, etc.) |
| `techniques` | What methods are used (scraping, sentiment-analysis, api-integration, etc.) |
| `concepts` | What concepts are covered (voc, pain-points, buyer-journey, etc.) |
| `subjects` | **REQUIRED** - Extract granular technical topics (see below) |
| `priority` | high = frequently needed, medium = occasional, low = niche |
| `source_project` | Current project name or "general" |
| `created` | Today's date YYYY-MM-DD |
| `last_updated` | Today's date YYYY-MM-DD |

### Subject Extraction (REQUIRED)

**As you research, identify specific technical subjects that appear in the content:**

1. **Algorithms & ML:** sbert, cosine-similarity, cross-encoder, bertopic, faiss, tf-idf, lda, umap, hdbscan, lstm, bm25, colbert
2. **Tools & APIs:** apify, semrush, buzzsumo, zoominfo, clearbit, gong, clari, g2, capterra, sec-api, companies-house
3. **Techniques:** semantic-search, reranking, intent-classification, rate-limiting, weak-supervision, hybrid-retrieval
4. **Business concepts:** buying-signals, switching-signals, trigger-events, meddpicc, challenger-sale, battlecards
5. **UI/Frontend:** shadcn, radix-ui, tailwind, framer-motion, zustand, react-hook-form, zod, error-boundaries
6. **LLM/AI:** rag, semantic-entropy, chain-of-verification, graphrag, guardrails, context-windows

**Format:** lowercase, hyphenated (kebab-case). Example: `subjects: [sbert, cosine-similarity, apify, pain-points]`

**Extraction rule:** If a specific tool, algorithm, technique, or concept is discussed in detail (not just mentioned), add it to subjects.

---

## Step 5: Synthesize Sub-Agent Results & Write Document

**Collect ALL sub-agent results and synthesize into a single cohesive document.**

### Synthesis Protocol

1. **De-duplicate:** Multiple sub-agents may cover the same finding. Merge into one entry, combining source URLs from all agents that found it.

2. **Cross-reference:** When finding X from Agent A is supported by finding Y from Agent B, note this — cross-validated findings are higher confidence.

3. **Resolve contradictions:** Check the `## Contradictions Found` sections from all agents.
   - If sources on both sides are credible ([Official] or [Peer-Reviewed]): Present both positions in the final doc under a **"Debated Topics"** subsection with evidence for each side.
   - If one side has stronger credibility: Lead with the stronger position, note the weaker one as a counterpoint.
   - NEVER silently drop a contradicted finding. The reader decides.

4. **Source credibility rollup:** Aggregate the source tables from all agents. The final document's Sources section should be organized by credibility tier:
   - `[Official]` — Official docs, maintainer posts
   - `[Peer-Reviewed]` — Academic papers, conference proceedings
   - `[Community]` — Stack Overflow, Reddit, HN (high-signal)
   - `[Blog]` — Dev.to, Medium, company blogs
   - `[Unverified]` — Single-source claims, no corroboration

5. **Gap detection:** If a lens from the decomposition framework (Step 3) has thin coverage even after Step 3.7 retries, note it explicitly: `"Gap: Limited public research on {lens} as of {date}."`

**Always use this structure with YAML frontmatter:**

```markdown
---
title: {Subject Title}
domain: {domain from schema}
techniques: [{techniques used}]
concepts: [{concepts covered}]
subjects: [{granular technical topics extracted during research}]
priority: high | medium | low
source_project: {current project name}
created: {YYYY-MM-DD}
last_updated: {YYYY-MM-DD}
---

# Research: {Subject}

> **Last Updated:** {ISO Date}
> **Research Sessions:** {count}

## TL;DR

{3-5 bullet executive summary of key findings}

---

## Problem Statement

{Clear definition of what we're solving}

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

| Approach | Complexity | Performance | Maintainability | Cost |
|----------|------------|-------------|-----------------|------|
| {A} | {Low/Med/High} | {metrics} | {rating} | {$} |

---

## Anti-Patterns (What NOT To Do)

1. **{Anti-pattern 1}:** {Why it fails}
2. **{Anti-pattern 2}:** {Why it fails}

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

### [Community] Community Discussions
- [{Title}]({URL})

### [Research] Studies & Benchmarks
- [{Title}]({URL})

---

## Research Log

### Session {N} - {Date}
- Searched: {queries}
- Found: {key findings}
- Added: {sections updated}
```

---

## Step 6: Write Document to Library

**Save to the correct category folder:**

```bash
RESEARCH_LIB=~/Projects/research-library/docs

# Based on auto-categorization from Step 1:
# - domains/ for topic-specific research
# - techniques/ for how-to guides
# - concepts/ for theoretical foundations
# - debugging/ for bug fix patterns

CATEGORY={determined category}
FILENAME={slugified topic}.md

# Write the document
# Path: $RESEARCH_LIB/$CATEGORY/$FILENAME
```

---

## Step 6.5: Validate & Expand Subjects (REQUIRED)

**After writing the document, validate subjects against schema:**

### 1. Extract subjects from your new/updated doc

```bash
# Get subjects array from the document you just wrote
grep "subjects:" ~/Projects/research-library/docs/{category}/{filename}.md
```

### 2. Check each subject against schema.md

```bash
# For each subject in your doc, verify it exists in schema
grep "{subject}" ~/Projects/research-library/schema.md
```

### 3. Handle NEW subjects not in schema

**If you find subjects that don't exist in schema.md:**

a) **Categorize the new subject:**
   - Algorithms & ML: embeddings, models, similarity measures, clustering
   - Tools & APIs: external services, platforms, SDKs
   - Techniques & Patterns: methods, approaches, workflows
   - Business Concepts: sales, marketing, buyer behavior terms
   - UI/Frontend: component libraries, state management, styling
   - LLM & AI: prompting, RAG, hallucination, context

b) **If no category fits:** Propose a new category with 3+ related subjects

c) **Confirm with user before adding:**
   ```
   I found new subjects not in schema.md:

   | Subject | Category | Description |
   |---------|----------|-------------|
   | `{new-subject}` | {category} | {one-line description} |

   Add to schema.md? [Y/n]
   ```

d) **If user confirms (y/Y/yes):** Update schema.md:
   - Add to appropriate category table in Valid Subjects section
   - Use kebab-case, lowercase
   - Include brief description

e) **If user declines (n/N/no or any other response):**
   - Do NOT add new subjects to schema.md
   - Still include subjects in the research document's frontmatter
   - Log in Research Log: "New subjects proposed but not added to schema: [list]"
   - Continue with research - this is not a blocker

### 4. Log subject additions

If you added new subjects to schema, include in the Research Log:
```
- New subjects added to schema: {list}
```

---

## Step 7: Update Index (REQUIRED)

**After creating/updating the document, update the master index:**

```bash
# Read current index
cat ~/Projects/research-library/index.md
```

**Add entry to the appropriate section in index.md:**

1. Find the correct category section (domains, techniques, concepts, debugging)
2. Add a new row to the table with: document name, description, priority
3. If it's a new domain/technique/concept, add to cross-references section

**Use Edit tool to add the new entry to index.md**

---

## Step 8: Summary Report

**After completing all research:**

```
## Research Complete: {Subject}

**Document saved:** ~/Projects/research-library/docs/{category}/{filename}.md
**Indexed:** Added to index.md under {category}

**What I learned:**

{3-5 sentences summarizing the most important insights discovered}

**Recommendation for this project:**

{1-2 sentences on what approach best fits THIS project's context}

**Sources:** {number} sources consulted across {categories covered}

**Related research you might also want:**
- {related doc 1}
- {related doc 2}
```

---

## Rules

1. **CHECK FIRST** - Always check for existing research before starting
2. **ASK BEFORE DUPLICATING** - If related research exists, confirm with user
3. **EXHAUSTIVE** - Don't stop at first answer, keep digging
4. **MULTI-SOURCE** - Verify findings across multiple sources
5. **PROVEN ONLY** - Every approach must have real-world evidence
6. **AUTO-CATEGORIZE** - Put docs in the right folder automatically
7. **AUTO-INDEX** - Always update index.md after creating/updating docs
8. **ENRICH DON'T DUPLICATE** - Add to existing docs when topic overlaps

---

## Deduplication Logic

**Before creating a new doc, check for semantic overlap:**

| New Topic | Existing Doc | Action |
|-----------|--------------|--------|
| "twitter API" | twitter-voc-mining.md | Enrich existing |
| "twitter ads API" | twitter-voc-mining.md | Ask user - could be new or enrich |
| "facebook scraping" | (none) | Create new |
| "react errors" | react-debugging-patterns.md | Enrich existing |
| "vue errors" | react-debugging-patterns.md | Create new (different framework) |

**When in doubt, ask the user.**

---

## What This Command Does

- Checks existing research before starting
- Offers to enrich rather than duplicate
- Auto-categorizes into correct folder
- Auto-updates index.md
- Creates proper YAML frontmatter
- Exhaustive multi-source research

## What This Command Does NOT Do

- Create duplicate research without asking
- Skip the existing research check
- Leave index.md out of date
- Create docs without frontmatter
