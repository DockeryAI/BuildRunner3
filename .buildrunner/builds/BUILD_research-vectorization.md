# Build: Research Library Vectorization

**Created:** 2026-04-07
**Status:** Phases 1-1 Complete — Phase 2 In Progress
**Deploy:** cluster — Lockwood (10.0.1.101) service restart

## Overview

Vectorize the 182-doc research library (~10.2 MB) on Lockwood so research context surfaces automatically during work — no manual skill invocation needed. Extends existing LanceDB + FastAPI infrastructure with a new `research_library` table, markdown-aware chunking, and integration into the recall hook + developer brief + skills.

## Parallelization Matrix

| Phase | Key Files                                                      | Can Parallel With | Blocked By    |
| ----- | -------------------------------------------------------------- | ----------------- | ------------- |
| 1     | core/cluster/node_semantic.py, research_chunker.py (NEW)       | -                 | -             |
| 2     | ~/.buildrunner/scripts/recall-on-tool.sh, developer-brief.sh   | 3                 | 1 (needs API) |
| 3     | ~/.claude/commands/learn.md, begin.md, opus.md, etc.           | 2                 | 1 (needs API) |
| 4     | ~/.claude/commands/research.md, public/js/ws-research.js (NEW) | -                 | 1 (needs API) |

## Phases

### Phase 1: Vectorization Engine (Lockwood)

**Status:** ✅ COMPLETE
**Goal:** Research library indexed in LanceDB with semantic search API working on Lockwood.

**Files:**

- core/cluster/node_semantic.py (MODIFY) — add research table, text embedder, search/reindex endpoints
- core/cluster/memory_store.py (MODIFY) — add research metadata SQLite table
- core/cluster/research_chunker.py (NEW) — markdown section chunker with frontmatter extraction
- core/cluster/scripts/reindex-research.sh (NEW) — CLI trigger for batch reindexing

**Blocked by:** None
**Deliverables:**

- [x] Markdown-aware chunker: splits docs on H2/H3 headers, each chunk gets doc title + section header + content + frontmatter metadata (domain, subjects, priority)
- [x] Text embedding model (switched to all-MiniLM-L6-v2 — nomic too heavy for M2 8GB): load nomic-embed-text-v1.5 as second SentenceTransformer (text-optimized, ~275MB RAM, lazy-loaded), keep CodeRankEmbed for code table
- [x] LanceDB `research_library` table: schema with id, title, section, domain, subjects, priority, source_file, content, vector
- [x] Batch indexer: discover .md files in ~/repos/research-library/docs/ (Lockwood's synced copy). Directory mtime check before file scan — skip entirely when unchanged. File-level hash detection for incremental updates
- [x] API endpoint GET /api/research/search?query=X&limit=N: semantic query returning top-k chunks with source file, section, score (GET with query params, consistent with existing Lockwood endpoints)
- [x] API endpoint POST /api/research/reindex: trigger manual reindexing
- [x] API endpoint GET /api/research/stats: table size, last indexed, file count, chunk count
- [x] Background indexer thread: reindex research library on configurable interval (default: 300s, research changes rarely)
- [x] Deploy to Lockwood (initial index built on Muddy in 22.7s, synced to Lockwood), restart service, verify with curl test

**Success Criteria:** `curl -s "http://10.0.1.101:8100/api/research/search?query=prompting+best+practices&limit=5"` returns relevant chunks from opus/prompting research docs with scores > 0.3 (nomic-embed-text typical relevant range is 0.3-0.6).

---

### Phase 2: Ambient Research (Hooks)

**Status:** not_started
**Goal:** Research automatically surfaces during editing and session starts without any skill invocation.

**Files:**

- ~/.buildrunner/scripts/recall-on-tool.sh (MODIFY) — add 4th parallel curl to /api/research/search
- ~/.buildrunner/scripts/developer-brief.sh (MODIFY) — add research context section

**Blocked by:** Phase 1 (needs /api/research/search endpoint)
**After:** Phase 1 (can run in parallel with Phase 3 — different files)
**Deliverables:**

- [ ] recall-on-tool.sh: add parallel curl to /api/research/search using file basename + project context as query (~20 lines: temp file, trap update, curl, PID wait, Python parse). Parse top 2 chunks, inject as "Research Context" section. Same 2s timeout pattern as existing queries.
- [ ] developer-brief.sh: at session start, query Lockwood with current BUILD phase description (if active build exists) to surface relevant research. Add "## Relevant Research" section to brief output.
- [ ] Dedup mechanism: session-scoped temp file (`$TMPDIR/br3-research-seen-$$.txt`) tracks injected chunk IDs. Brief writes first, recall hook and /begin filter against it. Auto-cleans on shell exit.
- [ ] Test: edit a React component file, verify design research chunks appear in recall. Start a new session on a project with an active build, verify relevant research shows in brief. Verify same chunk doesn't appear twice across brief + recall.

**Success Criteria:** Editing `src/components/Hero.tsx` auto-surfaces chunks from agency-website-design, residential-real-estate-broker-website-design, or relevant design research without invoking any skill. No duplicate chunks across injection points.

---

### Phase 3: Skill Enhancement

**Status:** not_started
**Goal:** Research-loading skills become semantic-aware with chunk-level retrieval and cross-domain discovery.

**Files:**

- ~/.claude/commands/learn.md (MODIFY) — semantic search primary, existing guidance as fallback
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

- [ ] /learn overhaul: Step 0 queries Lockwood research table (not code table). Returns chunk-level results with source file + section + score. Loads only the relevant sections, not whole files. Existing semantic guidance section (lines 39-122) kept as fallback interpretation logic when Lockwood is offline.
- [ ] /begin enhancement: at phase start, extract phase deliverable text, query Lockwood for relevant research, inject top 3-5 chunks as context before building. Adds ~2s to phase start. Uses dedup temp file from Phase 2.
- [ ] Research skill pattern: define a standard "Lockwood Research Query" template block (curl GET to /api/research/search with skill domain as query context, parse JSON results, present top 3 chunks with source + section). Copy this identical block into each skill (/opus, /chet, /geo, etc.) with only the domain parameter changed. Skills still load their primary docs as before, but also surface cross-domain chunks.
- [ ] Test: invoke /learn "website hero copy" and verify it returns chunks from multiple docs (agency design, buyer psychology, content strategy) instead of just keyword matches.

**Success Criteria:** /learn returns semantically relevant chunks from across domains. /begin loads research context automatically. Research skills discover cross-domain content.

---

### Phase 4: Research Pipeline + Dashboard

**Status:** not_started
**Goal:** New research auto-indexes into Lockwood. Dashboard shows research index health.

**Files:**

- ~/.claude/commands/research.md (MODIFY) — auto-index output into Lockwood
- ~/.buildrunner/dashboard/public/js/ws-research.js (NEW) — dashboard workspace for research index

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
- Research content consolidation (some GEO content spans 29 files — could merge into fewer docs)
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

### Memory Budget (Lockwood M2 8GB)

Estimated concurrent RAM: macOS baseline (~2GB) + Python/FastAPI (~200MB) + CodeRankEmbed (~275MB) + nomic-embed-text-v1.5 (~275MB) + LanceDB tables (~100MB) = ~2.85GB application. Leaves ~3GB for OS file cache and headroom. Mitigation: lazy-load text model on first research query, not at startup. If OOM occurs under concurrent search+reindex, add a lock to prevent simultaneous embedding operations.

### Recall Hook Query Design

The recall hook fires on Edit/Write/NotebookEdit with a file path. The research query uses: file basename + project name + any active BUILD phase description. This gives enough semantic signal to surface relevant research without reading file contents (which would add latency). Example: editing "HeroSection.tsx" in project "synapse" with Phase 3 "Sales landing page" → query captures design + sales + landing page context.

### Research Injection Deduplication

Three injection points (brief, recall hook, /begin) can surface the same chunks in one session. Dedup via a session-scoped temp file: `$TMPDIR/br3-research-seen-$$.txt` lists chunk IDs already injected. Each injection point appends chunk IDs after surfacing them. Before injecting, check the file and skip already-seen IDs. File is per-PID so it auto-cleans when the shell session ends. The brief (session start) always writes first, recall hook and /begin filter against it.

## Session Log

[Will be updated by /begin]
