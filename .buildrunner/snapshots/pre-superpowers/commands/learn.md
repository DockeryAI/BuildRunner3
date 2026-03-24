---
description: Load research context from library - understands natural language queries
allowed-tools: Read, Glob, Grep
model: opus
---

# Learn from Research Library: /learn

**PURPOSE: Load existing research into context using natural language.**

---

## Step 1: Understand the Query

**Input:** `/learn $ARGUMENTS`

**You are an intelligent query interpreter.** The user will ask in plain English. Your job is to understand their INTENT and find the most relevant research documents.

### Interpretation Rules

**Understand synonyms and related terms:**
- "social media" → social-voc-mining domain (YouTube, Twitter, Instagram, TikTok, Reddit)
- "twitter", "x", "tweets" → twitter-voc-mining.md
- "instagram", "insta", "IG" → instagram-voc-mining.md
- "youtube", "YT", "video comments" → youtube-voc-mining.md
- "tiktok", "TT", "short video" → tiktok-voc-mining.md
- "reddit", "subreddits" → reddit-voc-mining.md
- "reviews", "yelp", "google reviews" → review-mining.md
- "customer voice", "VOC", "what customers say" → social-voc-mining domain + ALL docs with concepts:.*voc (includes: customer-vocabulary.md, smb-persona-social-content.md, purchase-context-foundations.md, video-production-optimization.md, buzzsumo-content-intelligence.md, semrush-api-integration.md, generative-engine-optimization.md, voc-query-learning.md)
- "personas", "buyer personas", "customer personas" → smb-persona-social-content.md + b2b-buyer-psychology.md + customer-vocabulary.md
- "buyer", "buying", "purchase decisions" → buyer-psychology domain
- "competitors", "competition", "battlecards" → competitor-identification.md
- "triggers", "buying signals", "intent signals" → sales-triggers.md
- "hallucination", "making stuff up", "accuracy" → hallucination-prevention.md
- "debugging", "errors", "crashes", "freezes" → debugging category
- "SEC", "filings", "10-K", "financial" → sec-filings-research.md
- "weather", "seasonal" → weather-insights.md
- "trends", "market trends" → trend-analysis.md
- "local", "geographic", "location-based" → local-insights.md
- "proof", "testimonials", "case studies" → proof-points-social-proof.md
- "meeting prep", "sales calls" → meeting-prep.md
- "customer profiles", "enrichment" → customer-profile-intelligence.md
- "UI", "components", "design system" → ui-library-selection.md
- "documentation", "docs" → documentation-best-practices.md
- "Claude", "automation", "context" → claude-automation.md
- "PRD", "product requirements" → prd-visualization.md
- "api costs", "API cost tracking", "API spend", "cost tracking", "usage metering", "billing metering" → api-cost-tracking.md
- "mail assistant", "email task manager", "email tasks", "email automation tools", "email AI", "AI email assistant", "missive", "shortwave", "lindy", "alias ai", "newmail", "superhuman email", "copilot outlook", "trailing documentation", "email task extraction" → email-task-management-ai.md
- "task management", "task management ui", "task manager", "task views", "task sorting", "task prioritization", "kanban", "eisenhower matrix", "GTD", "getting things done", "inbox triage", "focus mode", "command palette", "saved views", "smart views", "daily planning", "weekly review", "WIP limits", "fractional indexing", "drag and drop reorder", "Linear app", "Things 3", "Todoist filters", "Amazing Marvin", "Sunsama", "Reclaim.ai", "TickTick" → task-management-ui-design-architecture.md

**Technical subjects (search `subjects:` field):**
- "cosine similarity", "vector similarity" → subjects: cosine-similarity
- "SBERT", "sentence embeddings" → subjects: sbert
- "BERTopic", "topic modeling" → subjects: bertopic
- "FAISS", "vector search" → subjects: faiss
- "cross-encoder", "reranking" → subjects: cross-encoder, reranking
- "Apify", "web scraping" → subjects: apify
- "SEMrush", "keyword research" → subjects: semrush
- "BuzzSumo", "content analysis" → subjects: buzzsumo
- "ZoomInfo", "Clearbit", "enrichment" → subjects: zoominfo, clearbit
- "Gong", "conversation intelligence" → subjects: gong
- "MEDDPICC", "sales methodology" → subjects: meddpicc
- "RAG", "retrieval" → subjects: rag, hybrid-retrieval
- "hallucination detection", "semantic entropy" → subjects: semantic-entropy, guardrails
- "shadcn", "Radix", "Tailwind" → subjects: shadcn, radix-ui, tailwind
- "error boundaries", "React errors" → subjects: error-boundaries
- "useEffect loops", "infinite loops" → subjects: useeffect-infinite-loops
- "OpenMeter", "usage metering" → subjects: usage-metering
- "LiteLLM", "LLM proxy" → subjects: proxy-gateway, llm-cost-tracking
- "Helicone", "LLM gateway" → subjects: llm-cost-tracking, proxy-gateway
- "Langfuse", "LLM observability" → subjects: llm-cost-tracking, token-counting
- "token counting", "token costs" → subjects: token-counting, llm-cost-tracking
- "semantic caching", "LLM caching" → subjects: semantic-caching
- "Kafka", "event streaming" → subjects: event-streaming, kafka
- "ClickHouse", "analytics DB" → subjects: clickhouse
- "budget enforcement", "API budgets" → subjects: budget-enforcement
- "idempotency", "deduplication" → subjects: idempotency
- "async logging", "non-blocking logging" → subjects: async-logging
- "kanban board", "WIP limits" → subjects: kanban, wip-limits
- "eisenhower matrix", "urgent important" → subjects: eisenhower-matrix
- "focus mode", "single task view" → subjects: focus-mode
- "command palette", "cmd+k", "cmd k" → subjects: command-palette
- "fractional indexing", "sort order" → subjects: fractional-indexing
- "saved views", "custom views" → subjects: saved-views
- "filter query", "filter DSL" → subjects: filter-query-language
- "smart views", "today view", "inbox view" → subjects: smart-views
- "daily planning", "morning planning" → subjects: daily-planning
- "weekly review", "GTD review" → subjects: weekly-review
- "Linear", "Linear app" → subjects: linear-app
- "Things 3", "Things app" → subjects: things-3
- "Todoist", "Todoist filters" → subjects: todoist
- "Amazing Marvin", "Marvin app" → subjects: amazing-marvin
- "Sunsama" → subjects: sunsama
- "Reclaim", "Reclaim.ai" → subjects: reclaim-ai
- "TickTick" → subjects: ticktick
- "swipe gestures", "swipe to complete" → subjects: swipe-gestures
- "dark mode", "dark theme design" → subjects: dark-mode-design
- "dnd-kit", "drag and drop" → subjects: dnd-kit
- "time blocking", "time blocks" → subjects: time-blocking
- "inbox triage", "GTD inbox" → subjects: inbox-triage
- "optimistic updates", "optimistic UI" → subjects: optimistic-updates
- "local first", "local-first sync" → subjects: local-first-sync

**Understand intent phrases:**
- "how to scrape X" → find docs with scraping technique for X platform
- "techniques for X" → find technique docs related to X
- "what do we know about X" → find all docs mentioning X
- "help me understand X" → find conceptual docs about X
- "I need to build X" → find implementation-focused docs for X
- "debugging X" → find debugging docs related to X
- "best practices for X" → find high-priority docs about X
- "all the important stuff" → priority:high docs
- "everything from synapse" → source_project: synapse docs

**Handle compound queries:**
- "social media mining techniques" → social-voc-mining domain + technique docs
- "how to extract pain points from reddit" → reddit-voc-mining.md (has pain point extraction)
- "buyer psychology and triggers" → b2b-buyer-psychology.md + sales-triggers.md
- "all the VoC research" or just "VoC" → ALL docs with concepts:.*voc (grep -l "concepts:.*voc") — this catches social-voc-mining domain docs AND cross-domain docs like personas, customer-vocabulary, purchase-context, GEO, video-production, etc.
- "VoC and personas" → all social-voc-mining docs + smb-persona-social-content.md + customer-vocabulary.md + purchase-context-foundations.md

---

## Step 2: Locate Research Library

```
RESEARCH_LIB = ~/Projects/research-library
```

**Read the index first to understand what's available:**
```bash
cat ~/Projects/research-library/index.md
```

**List all available docs:**
```bash
find ~/Projects/research-library/docs -name "*.md" | sort
```

---

## Step 3: Find Matching Documents

Based on your interpretation of the query, find relevant documents using:

1. **Subjects search (HIGHEST PRIORITY)** - Search `subjects:` field for granular topics
2. **Semantic matching** - Match user intent to document purposes
3. **Frontmatter search** - Search domain, techniques, concepts, priority, source_project
4. **Full-text search** - Search document content for keywords
5. **Filename matching** - Match against document names

**Use Grep to search frontmatter and content:**
```bash
# FIRST: Search by subjects (granular topics like algorithms, tools, techniques)
grep -l "subjects:.*cosine-similarity" ~/Projects/research-library/docs/**/*.md
grep -l "subjects:.*sbert" ~/Projects/research-library/docs/**/*.md
grep -l "subjects:.*apify" ~/Projects/research-library/docs/**/*.md

# Search by interpreted domain
grep -l "domain: social-voc-mining" ~/Projects/research-library/docs/**/*.md

# Search by concepts (CRITICAL for VoC — catches cross-domain docs)
grep -l "concepts:.*voc" ~/Projects/research-library/docs/**/*.md

# Search by technique
grep -l "techniques:.*scraping" ~/Projects/research-library/docs/**/*.md

# Full-text search for keywords
grep -ril "pain point" ~/Projects/research-library/docs/
```

**IMPORTANT: For VoC queries, ALWAYS search concepts:.*voc in addition to domain: social-voc-mining.** The concepts search catches cross-domain VoC docs (personas, purchase psychology, GEO, video production, etc.) that are NOT in the social-voc-mining domain but contain critical VoC content.

**Prioritize matches:**
1. Exact subject matches (highest relevance - specific technical topics)
2. Exact domain/concept matches
3. Technique matches
4. Full-text keyword matches
5. Related documents (lower relevance)

**Subject Search Examples:**
- "cosine similarity" → Search `subjects:.*cosine-similarity` → Finds: reddit-voc-mining, instagram-voc-mining, twitter-voc-mining
- "SBERT" → Search `subjects:.*sbert` → Finds: reddit-voc-mining, twitter-voc-mining, voc-query-learning
- "Apify" → Search `subjects:.*apify` → Finds: All social platform mining docs
- "hallucination prevention" → Search `subjects:.*semantic-entropy` + `subjects:.*rag-hat` → Finds: hallucination-prevention.md
- "MEDDPICC" → Search `subjects:.*meddpicc` → Finds: meeting-prep.md

---

## Step 4: Load Matched Documents

For each matched document:

1. **Read the file** using the Read tool
2. **Extract key sections:**
   - YAML frontmatter (for metadata)
   - TL;DR section
   - Recommendations section
   - Key findings/solutions

**For large documents (>50KB):** Focus on TL;DR and Recommendations
**For smaller documents:** Read more content as needed

---

## Step 5: Present Context

**Format your response:**

```
## Research Context: {interpreted query meaning}

**Your query:** "{original query}"
**I found:** {count} relevant documents

### Key Insights

{Synthesize the most important findings from matched docs that answer the user's question. Be specific and actionable.}

### Documents Loaded

| Document | What It Covers | Priority |
|----------|----------------|----------|
| [name](path) | {brief description} | {priority} |

### TL;DR from Sources

{Combined key points from the TL;DR sections of matched docs}

### Want More Detail?

- Read full doc: `~/Projects/research-library/docs/{path}`
- Related: {suggest related docs they might also want}
```

---

## Examples of Natural Language Understanding

| User Says | You Understand | Documents to Load |
|-----------|----------------|-------------------|
| "social media mining" | VoC extraction from social platforms | All social-voc-mining domain docs |
| "how do I scrape twitter" | Twitter data extraction techniques | twitter-voc-mining.md |
| "techniques to mine reddit" | Reddit scraping and analysis | reddit-voc-mining.md |
| "what makes buyers decide" | B2B/B2C purchase psychology | b2b-buyer-psychology.md, sales-triggers.md |
| "help with react crashes" | React debugging patterns | react-debugging-patterns.md |
| "the important research" | High priority documents | All priority:high docs |
| "everything about customers" | Customer intelligence | customer-vocabulary.md, customer-profile-intelligence.md, b2b-buyer-psychology.md |
| "VoC" or "voc" | Voice of Customer (all) | ALL docs with concepts:.*voc (15 docs: youtube/reddit/twitter/instagram/tiktok/amazon-review/review-mining + customer-vocabulary + smb-persona-social-content + purchase-context-foundations + video-production + buzzsumo + semrush + GEO + voc-query-learning) |
| "personas" | Customer persona research | smb-persona-social-content.md, b2b-buyer-psychology.md, customer-vocabulary.md |
| "mail assistant" | AI email task management tools | email-task-management-ai.md |
| "email tasks" | Email task extraction and management | email-task-management-ai.md |
| "missive", "shortwave", "lindy" | Specific email tool research | email-task-management-ai.md |
| "trailing documentation" | Auto-updating project docs from email | email-task-management-ai.md |
| "LLM accuracy issues" | Hallucination prevention | hallucination-prevention.md |
| "competitor intel" | Competitive analysis | competitor-identification.md |
| "all synapse research" | Synapse project docs | All source_project:synapse docs |
| "api costs" | API cost tracking without overhead | api-cost-tracking.md |
| "LLM costs", "token tracking" | LLM cost tracking and budget enforcement | api-cost-tracking.md |
| "usage metering", "billing" | Usage-based metering architecture | api-cost-tracking.md |
| "task management" | Task management UI design patterns | task-management-ui-design-architecture.md |
| "task management ui" | Task views, sorting, prioritization, architecture | task-management-ui-design-architecture.md |
| "kanban", "eisenhower", "GTD" | Specific productivity methodology | task-management-ui-design-architecture.md |
| "Linear app", "Things 3", "Todoist" | Specific task manager patterns | task-management-ui-design-architecture.md |
| "focus mode", "command palette" | Specific UI patterns for productivity | task-management-ui-design-architecture.md |
| "task sorting", "task views" | Task list sorting and view patterns | task-management-ui-design-architecture.md |

---

## No Arguments: `/learn`

If the user just types `/learn` with no arguments:

1. Show the research library index
2. List available categories
3. Suggest example queries:
   - "Try: `/learn social media mining`"
   - "Try: `/learn how to extract customer pain points`"
   - "Try: `/learn priority:high` for critical research"

---

## What This Command Does

- Understands natural language queries
- Finds semantically relevant research documents
- Loads context for informed decision-making
- Synthesizes key findings from multiple sources

## What This Command Does NOT Do

- Does NOT conduct new research (use `/research` for that)
- Does NOT modify any documents
- Does NOT make up information not in the documents
