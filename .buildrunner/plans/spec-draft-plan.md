# Build: Research Library Vectorization

**Created:** 2026-04-07
**Status:** Draft
**Deploy:** cluster — Lockwood (10.0.1.101) service restart

## Overview

Vectorize the 182-doc research library (~10.2 MB) on Lockwood so research context surfaces automatically during work — no manual skill invocation needed. Extends existing LanceDB + FastAPI infrastructure with a new `research_library` table, markdown-aware chunking, and integration into the recall hook + developer brief + skills.

## What Changes

**The core shift:** Research goes from "pull" (user invokes /learn, /opus, /chet, etc.) to "push" (Lockwood auto-surfaces relevant chunks when you edit files, start sessions, or begin build phases).

**Skills that need updating:**

- `/learn` — semantic search becomes primary, synonym table becomes fallback, chunk-level retrieval replaces whole-file loading
- `/begin` — phase starts query Lockwood for research relevant to phase deliverables
- `/opus`, `/chet`, `/geo`, `/social`, `/prompt`, `/llm`, `/recraft`, `/perplexity`, `/appdesign` — still work as manual deep-dive overrides, but gain cross-domain discovery (e.g., /opus also surfaces related hallucination-prevention and claude-automation chunks)
- `/research` — new research output auto-indexes into Lockwood immediately
- `/br3-frontend-design`, `/design`, `/website-build` — auto-pull relevant design research from Lockwood

**Hooks that need updating:**

- `recall-on-tool.sh` — add research query as 4th parallel source (5 lines of bash)
- `developer-brief.sh` — add research context section at session start

**New infrastructure:**

- Markdown section chunker (splits on H2/H3, preserves frontmatter metadata)
- Text embedding model (nomic-embed-text-v1.5 alongside existing CodeRankEmbed)
- LanceDB `research_library` table (~1,800 vectors)
- Batch + incremental indexer for ~/Projects/research-library/
- API endpoints: /api/research/search, /api/research/reindex, /api/research/stats
- Dashboard workspace for research index health

## Parallelization Matrix

| Phase | Key Files                                                      | Can Parallel With | Blocked By    |
| ----- | -------------------------------------------------------------- | ----------------- | ------------- |
| 1     | core/cluster/node_semantic.py, research_chunker.py (NEW)       | -                 | -             |
| 2     | ~/.buildrunner/scripts/recall-on-tool.sh, developer-brief.sh   | 3                 | 1 (needs API) |
| 3     | ~/.claude/commands/learn.md, begin.md, opus.md, etc.           | 2                 | 1 (needs API) |
| 4     | ~/.claude/commands/research.md, dashboard ws-research.js (NEW) | -                 | 1 (needs API) |

---

## Phases

### Phase 1: Vectorization Engine (Lockwood)

**Goal:** Research library indexed in LanceDB with semantic search API working on Lockwood.

**Files:**

- core/cluster/node_semantic.py (MODIFY) — add research table, text embedder, search/reindex endpoints
- core/cluster/memory_store.py (MODIFY) — add research metadata SQLite table
- core/cluster/research_chunker.py (NEW) — markdown section chunker with frontmatter extraction
- core/cluster/scripts/reindex-research.sh (NEW) — CLI trigger for batch reindexing

**Blocked by:** None
**Deliverables:**

- [ ] Markdown-aware chunker: splits docs on H2/H3 headers, each chunk gets doc title + section header + content + frontmatter metadata (domain, subjects, priority)
- [ ] Text embedding model: load nomic-embed-text-v1.5 as second SentenceTransformer (text-optimized, ~275MB RAM), keep CodeRankEmbed for code table
- [ ] LanceDB `research_library` table: schema with id, title, section, domain, subjects, priority, source_file, content, vector
- [ ] Batch indexer: discover all .md files in ~/Projects/research-library/docs/, chunk, embed, insert. Hash-based change detection for incremental updates
- [ ] API endpoint POST /api/research/search: semantic query with top-k chunks with source file, section, score
- [ ] API endpoint POST /api/research/reindex: trigger manual reindexing
- [ ] API endpoint GET /api/research/stats: table size, last indexed, file count, chunk count
- [ ] Background indexer thread: reindex research library on configurable interval (default: 300s, research changes rarely)
- [ ] Deploy to Lockwood, restart service, verify with curl test

**Success Criteria:** `curl -s "http://10.0.1.101:8100/api/research/search?query=prompting+best+practices&limit=5"` returns relevant chunks from opus/prompting research docs with scores > 0.5.

---

### Phase 2: Ambient Research (Hooks)

**Goal:** Research automatically surfaces during editing and session starts without any skill invocation.

**Files:**

- ~/.buildrunner/scripts/recall-on-tool.sh (MODIFY) — add 4th parallel curl to /api/research/search
- ~/.buildrunner/scripts/developer-brief.sh (MODIFY) — add research context section

**Blocked by:** Phase 1 (needs /api/research/search endpoint)
**After:** Phase 1
**Deliverables:**

- [ ] recall-on-tool.sh: add parallel curl to /api/research/search using file basename + project context as query. Parse top 2 chunks, inject as "Research Context" section. Same 2s timeout pattern as existing queries.
- [ ] developer-brief.sh: at session start, query Lockwood with current BUILD phase description (if active build exists) to surface relevant research. Add "## Relevant Research" section to brief output.
- [ ] Test: edit a React component file, verify design research chunks appear in recall. Start a new session on a project with an active build, verify relevant research shows in brief.

**Success Criteria:** Editing `src/components/Hero.tsx` auto-surfaces chunks from agency-website-design, residential-real-estate-broker-website-design, or relevant design research without invoking any skill.

---

### Phase 3: Skill Enhancement

**Goal:** Research-loading skills become semantic-aware with chunk-level retrieval and cross-domain discovery.

**Files:**

- ~/.claude/commands/learn.md (MODIFY) — semantic search primary, synonym table fallback
- ~/.claude/commands/begin.md (MODIFY) — add research query at phase start
- ~/.claude/commands/opus.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/commands/geo.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/commands/social.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/commands/prompt.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/commands/llm.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/commands/appdesign.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/commands/recraft.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/commands/perplexity.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/skills/chet/SKILL.md (MODIFY) — add cross-domain chunk discovery
- ~/.claude/skills/br3-frontend-design/SKILL.md (MODIFY) — add cross-domain chunk discovery

**Blocked by:** Phase 1 (needs /api/research/search endpoint)
**After:** Phase 1 (can run in parallel with Phase 2 — different files)
**Deliverables:**

- [ ] /learn overhaul: Step 0 queries Lockwood research table (not code table). Returns chunk-level results with source file + section + score. Loads only the relevant sections, not whole files. Synonym table kept as fallback when Lockwood is offline.
- [ ] /begin enhancement: at phase start, extract phase deliverable text, query Lockwood for relevant research, inject top 3-5 chunks as context before building. Adds ~2s to phase start.
- [ ] Research skill pattern: add a standard "Lockwood Research Query" block to each research-loading skill (/opus, /chet, /geo, etc.) that queries the research table with the skill's domain + the user's current context. Skills still load their primary docs as before, but also surface cross-domain chunks.
- [ ] Test: invoke /learn "website hero copy" and verify it returns chunks from multiple docs (agency design, buyer psychology, content strategy) instead of just keyword matches.

**Success Criteria:** /learn returns semantically relevant chunks from across domains. /begin loads research context automatically. Research skills discover cross-domain content.

---

### Phase 4: Research Pipeline + Dashboard

**Goal:** New research auto-indexes into Lockwood. Dashboard shows research index health.

**Files:**

- ~/.claude/commands/research.md (MODIFY) — auto-index output into Lockwood
- ~/.buildrunner/dashboard/js/ws-research.js (NEW) — dashboard workspace for research index

**Blocked by:** Phase 1 (needs /api/research/reindex and /api/research/stats endpoints)
**After:** Phases 2, 3
**Deliverables:**

- [ ] /research skill: after writing a new research doc to ~/Projects/research-library/, auto-trigger /api/research/reindex on Lockwood so the new doc is immediately searchable
- [ ] Dashboard workspace: show research index stats (total docs, total chunks, last indexed, top domains by chunk count), recent search queries, and index health. Follows existing ws-\*.js modular pattern.
- [ ] Test: run /research on a new topic and verify the output doc appears in Lockwood search results within 30 seconds

**Success Criteria:** New research is searchable immediately after creation. Dashboard shows live index stats.

---

## Out of Scope (Future)

- Relevance feedback loop (tracking which surfaced research is actually useful)
- Research deduplication (some GEO content spans 29 files — could consolidate)
- Cross-project research sharing (other BR3 projects accessing the same research index)
- Research versioning (tracking how docs evolve over time)
- Embedding model fine-tuning on the research corpus
- Natural language research queries via dashboard (search UI)

---

## Technical Notes

### Embedding Model Decision

Start with nomic-embed-text-v1.5 (text-optimized, same Nomic family as CodeRankEmbed). ~275MB RAM on Lockwood M2 8GB — headroom alongside CodeRankEmbed. 768-dim embeddings. If prose recall is poor, evaluate: all-MiniLM-L6-v2 (fastest), bge-base-en-v1.5 (balanced). Decision point: after Phase 1 indexing, run 10 test queries and verify relevance.

### Chunking Strategy

Split on H2 headers as primary boundaries. If a section exceeds 2000 chars, split on H3 sub-headers. Each chunk inherits doc title + frontmatter fields (domain, subjects, priority, techniques). Frontmatter metadata prepended to chunk text before embedding. Chunks under 100 chars merged with next section.

### Recall Hook Query Design

The recall hook fires on Edit/Write/NotebookEdit with a file path. The research query uses: file basename + project name + any active BUILD phase description. This gives enough semantic signal to surface relevant research without reading file contents (which would add latency). Example: editing "HeroSection.tsx" in project "synapse" with Phase 3 "Sales landing page" → query captures design + sales + landing page context.
