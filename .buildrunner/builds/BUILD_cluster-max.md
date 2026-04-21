# Build: cluster-max

**Created:** 2026-04-12
**Last Revised:** 2026-04-20 (Phases 11+12 complete: dashboard @ :4400 + multi-model context parity)
**Status:** Phases 1-12 Complete — Phase 2 In Progress
**Deploy:** infra — cluster scripts + node services + runtime extension (no web deploy)

---

## AUTOPILOT PROTOCOL — READ FIRST (SOURCE OF TRUTH)

This section is authoritative. Everything below it is implementation reference. When anything in a later phase contradicts this section, THIS section wins. When `/autopilot go cluster max` is invoked on a fresh Claude instance, read this section first, then the "Final Decisions Override" table, then jump to the current phase.

### Fresh-Instance Bootstrap (in this order)

1. Read this file top-to-bottom through "Final Decisions Override" (≈ lines 1–400). That is the full operating contract.
2. Read `.buildrunner/decisions.log` tail (last 50 lines). Every phase appends one line — the tail tells you what actually shipped.
3. Read `.buildrunner/CLAUDE.md` for current-work snapshot.
4. Check the Status Table (All Phases) below. Locate the next `not_started` phase; verify its blockers are `completed`.
5. Read only the current phase's block in the Phases section and the AGENTS.md files it touches. Do NOT read earlier phases' details — they are noise for current work.
6. Announce to the user: "Resuming cluster-max at the next open phase — [role] work, [builder model]. OK to proceed?"
7. On approval, dispatch per the Role Matrix.

### Role Matrix (Architect / Builder / Reviewer per Phase)

Research-backed split. Opus architects the hard phases; gpt-5.4 builds the mechanical 70%; gpt-5.3-codex owns terminal-heavy work; Sonnet + gpt-5.4 co-equal review every phase; Opus arbitrates disagreement only.

| Ph  | Architect                      | Builder                  | Reviewers (parallel) | Arbiter (on disagreement) | Notes                                               |
| --- | ------------------------------ | ------------------------ | -------------------- | ------------------------- | --------------------------------------------------- |
| 0   | Opus 4.7                       | gpt-5.4 `effort:medium`  | Sonnet 4.6 + gpt-5.4 | Opus 4.7 `effort:xhigh`   | AGENTS.md human-authored, never LLM-generated       |
| 1   | Opus 4.7                       | (human hardware install) | —                    | —                         | Physical BIOS/overclock                             |
| 2   | Opus 4.7                       | gpt-5.3-codex            | Sonnet + gpt-5.4     | Opus                      | Terminal-heavy (SSH/Ollama) — COMPLETE              |
| 3   | Opus 4.7                       | gpt-5.3-codex            | Sonnet + gpt-5.4     | Opus                      | Terminal-heavy; now Jimmy memory node setup         |
| 4   | Opus 4.7                       | gpt-5.4 `effort:high`    | Sonnet + gpt-5.4     | Opus                      | 7-node priority + overflow dispatcher               |
| 5   | Opus 4.7                       | gpt-5.4 `effort:high`    | Sonnet + gpt-5.4     | Opus                      | Below skill integration                             |
| 6   | Opus 4.7                       | gpt-5.4 `effort:high`    | Sonnet + gpt-5.4     | Opus                      | OllamaRuntime — architectural                       |
| 7   | REPLACED — see Final Decisions | gpt-5.4 `effort:high`    | Sonnet + gpt-5.4     | Opus                      | RuntimeRegistry shim + pre-commit hook, NOT LiteLLM |
| 8   | Opus 4.7                       | gpt-5.4 `effort:high`    | Sonnet + gpt-5.4     | Opus                      | Cache engineering + byte-identity test — SHIP FIRST |
| 9   | Opus 4.7                       | gpt-5.4 `effort:xhigh`   | Sonnet + gpt-5.4     | Opus                      | Review pipeline itself — highest stakes             |
| 10  | Opus 4.7                       | gpt-5.4 `effort:high`    | Sonnet + gpt-5.4     | Opus                      | Auto-context + research command redesign            |
| 11  | Opus 4.7                       | gpt-5.4 `effort:high`    | Sonnet + gpt-5.4     | Opus                      | Dashboard + Jimmy cutover + overflow wake/drain     |
| 12  | Opus 4.7                       | gpt-5.4 `effort:high`    | Sonnet + gpt-5.4     | Opus                      | Multi-model context parity — architectural          |
| 13  | Opus 4.7                       | gpt-5.3-codex            | Sonnet + gpt-5.4     | Opus                      | Cutover/terminal + flag flip                        |
| 14  | Opus 4.7                       | gpt-5.3-codex            | Sonnet + gpt-5.4     | Opus                      | Self-maintenance crons                              |

Claude (this instance) acts as Opus architect + orchestrator. Claude never also builds — builds dispatch to the Builder column via the runtime registry.

### Dispatch Rules

- **Opus (this instance) authors:** the per-phase plan addendum (any decisions not already pinned in the phase block), the review prompt, the arbitration prompt if invoked.
- **Builder** executes the phase's Deliverables list under its specified `effort` level. Builder reads only: this section, the phase block, the staged AGENTS.md patches, and its own scope files.
- **Reviewers** run in parallel on the same diff. Single rebuttal round. If both pass → ship. If both flag overlapping issues → fix and re-run once. If they disagree after rebuttal → Opus arbiter terminal ruling.
- **Escalation is the exit,** not more rounds. Persistent blocker → stop, alert user with both review reports side by side.

### Context-Poisoning Detection (Alert User to Start Fresh Session)

Fresh context is required when ANY of these fire. Stop work, tell the user exactly which trigger fired, paste the resume command, wait.

| Trigger                                                                     | Why it poisons context                                                                             | Resume command                                 |
| --------------------------------------------------------------------------- | -------------------------------------------------------------------------------------------------- | ---------------------------------------------- |
| Context window >70% full (≥140K used of 200K)                               | Long-context retrieval degrades past 200K; Opus 4.7 specifically regresses 91.9% → 59.2% past 400K | `/autopilot go cluster max --resume phase-N`   |
| Conversation has touched ≥3 phases                                          | Cross-phase details bleed; builder mis-scopes                                                      | `/autopilot go cluster max --resume phase-N`   |
| After any arbiter ruling                                                    | Arbitration loads both review reports + rebuttals — heavy context residue that skews next phase    | `/autopilot go cluster max --resume phase-N+1` |
| Role switched mid-session (architect → builder, or builder → reviewer)      | Role-prompt residue causes wrong-voice output                                                      | New session per role                           |
| Build plan itself edited mid-phase                                          | The file you're reading just changed; re-read from disk in fresh context                           | `/autopilot go cluster max --resume phase-N`   |
| >2h elapsed on a single phase                                               | Drift risk; decisions earlier in session may no longer match file                                  | `/autopilot go cluster max --resume phase-N`   |
| User corrected a factual error                                              | Correction lingers as anti-example, affects unrelated decisions                                    | `/autopilot go cluster max --resume phase-N`   |
| `.buildrunner/decisions.log` tail doesn't match your memory of what shipped | You're out of sync with reality                                                                    | `/autopilot go cluster max --resume phase-N`   |

**Alert format:** "CONTEXT POISONING TRIGGER: [which one]. Start fresh session with: `/autopilot go cluster max --resume phase-N`. Current state is saved in decisions.log and the build plan is up to date."

### Self-Updating Source-of-Truth Protocol

The build plan stays current. Every phase that ships updates this file in the same commit as its code changes. No exceptions.

**On phase start:**

- Builder sets phase Status line to `in_progress` with timestamp
- Builder claims the phase lock under `.buildrunner/locks/phase-N/claim.json`

**On phase complete (blocking — phase is not "done" until all of these are satisfied):**

1. Append a single line to `.buildrunner/decisions.log`: `PHASE-N COMPLETE <timestamp> <model-used> <key-decision-summary>`
2. Update the Status Table (All Phases) below: mark the phase `completed` with timestamp + 1-line summary (e.g., "70B dual-GPU 18.01 tok/s")
3. Update the "Last Revised" date at top of file with 1-line change summary
4. If the phase changed a decision that contradicts the Final Decisions Override table → update the table inline, do NOT leave stale rows
5. If the phase added a new convention → it already updated the correct AGENTS.md (per Per-Phase AGENTS.md Mapping table); verify the line is in the right file
6. Remove the phase lock; release claim

**On any drop/replacement discovered during execution:**

- Append to the "Dropped / Replaced (post-plan)" table below with: what, why, evidence, replacement
- Update any phase block that references the dropped item with a `> **SUPERSEDED (Phase N):** see Final Decisions` line at the top

**Reviewer gate:** Sonnet + gpt-5.4 MUST verify all 6 completion steps before passing a phase. Reviewer failure on any step = phase rejected, not "fix in follow-up."

---

## Final Decisions Override (post-discussion, 2026-04-20)

These override anything written later in the file. If a phase block below says otherwise, the phase block is stale — follow this table.

### Models (Final)

| Model                   | Role                                | Where               | Proven for                                                                                                                     |
| ----------------------- | ----------------------------------- | ------------------- | ------------------------------------------------------------------------------------------------------------------------------ |
| Claude Opus 4.7         | Architect + Arbiter                 | Muddy (Claude Code) | Spec, planning, arbitration, /root, /diag                                                                                      |
| Claude Sonnet 4.6       | Primary reviewer + frontend author  | Muddy (Claude Code) | 95% vuln detection, ~5× cheaper than Opus for volume                                                                           |
| Codex gpt-5.4           | Primary builder + co-equal reviewer | Muddy/Otis (Codex)  | Default builder, cross-family review voice                                                                                     |
| Codex gpt-5.3-codex     | Terminal-only                       | Otis/Muddy          | Terminal-Bench lead; SSH/Ollama/shell phases                                                                                   |
| llama3.3:70b @ Q4_K_M   | Summarization                       | Below dual-GPU      | 18 tok/s measured, NVLink validated                                                                                            |
| qwen3:8b @ Q4           | Classification/extraction           | Below               | 131 tok/s, schema-mode only                                                                                                    |
| nomic-embed-text        | Embeddings                          | Below               | 768-dim, 8K context                                                                                                            |
| BAAI/bge-reranker-v2-m3 | Reranker (gated)                    | Jimmy CPU           | Phase 10 BLOCKING validation: ≥15% precision@5 lift on 20-query human-rate, or ship disabled with jina-v3/Cohere as named swap |

### Dropped / Replaced (post-plan)

| Item                                                      | Why dropped                                                                                                    | Replacement                                                                                                                                                 |
| --------------------------------------------------------- | -------------------------------------------------------------------------------------------------------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------------- |
| deepseek-r1:70b                                           | Research library: reasoning model, wrong tool for extraction/adversarial review                                | (none — Sonnet + gpt-5.4 do review)                                                                                                                         |
| LiteLLM gateway                                           | Stability risk + another failure surface                                                                       | `RuntimeRegistry.execute()` shim as the ONLY runtime dispatch path; pre-commit hook rejects direct `ollama`/`curl`/`requests.post` calls to local endpoints |
| 12KB summarize-before-escalate threshold                  | Arbitrary                                                                                                      | Cache-driven rule: anything reused ≥2 times in a session is cached/summarized                                                                               |
| Review round cap = 3                                      | Research says 1 is optimal; more rounds don't converge                                                         | Cap = 1 rebuttal round, then Opus arbiter or escalate                                                                                                       |
| `budget_tokens: 32000`                                    | Deprecated on Opus 4.7; throws 400                                                                             | Adaptive thinking via `effort: "high"` / `"xhigh"`                                                                                                          |
| 3-way review (adding r1 as third voice)                   | Same-family debate is mathematically null (martingale); r1 not a reviewer anyway                               | 2-way Sonnet + gpt-5.4 parallel, Opus arbiter on disagreement                                                                                               |
| "Default reviews to Below since it's the beefiest"        | 23-point quality gap (llama 72% vs Sonnet 95% vuln detection). Hardware doesn't raise model capability ceiling | Below runs qwen3:8b pre-filter + llama diff compression; paid models always do the actual review                                                            |
| Distributed test sharding across 3 nodes                  | Test suite too small; coordination risk > savings                                                              | Walter stays full suite; Lomax sharding only triggered by overflow                                                                                          |
| Continuous tsc/eslint watch on remote M2s                 | IDE already does this; remote adds sync pipeline for zero gain                                                 | Dropped entirely                                                                                                                                            |
| MLX inference pool as default                             | Speculative without measured queue depth                                                                       | MLX on Lockwood/Lomax lives ONLY as overflow (VRAM <1GB headroom or Below unreachable)                                                                      |
| Parallel research indexing as default                     | Weekly op; 4-min savings not worth complexity                                                                  | Sequential on Below; parallelize only when >20 docs queued                                                                                                  |
| Codex-warm on Lockwood/Lomax                              | Marginal cold-start win for continuous memory cost                                                             | Only Otis stays warm; overflow accepts ~5s cold-start                                                                                                       |
| Auto code comments / JSDoc / test stubs / PR title skills | Claude/Codex already produce inline; separate skills = noise                                                   | Dropped                                                                                                                                                     |

### Jimmy = New Memory/Semantic Backbone (not just staging/gateway)

Jimmy absorbs Lockwood's memory role. 64GB DDR5 + CPU is sufficient for vector DB + reranker (both CPU-friendly). Consolidation simplifies the dependency graph.

**Jimmy (always-on):** Vector DB (LanceDB), session state, build history, research library storage, bge-reranker, intel crons, dashboard WS, context parity API, cost ledger, self-health, runtime log aggregation, **central backup target for all cluster state + every ~/Projects repo**.

**Lockwood:** Freed to be true warm reserve (see Overflow Design below).

### Jimmy Storage Layout (2TB NVMe)

All paths under `/srv/jimmy/`. Single drive, directory-scoped, no partitioning — keeps free-space fungible across purposes.

| Path                                         | Purpose                                                                                      | Est. working size                        |
| -------------------------------------------- | -------------------------------------------------------------------------------------------- | ---------------------------------------- |
| `/srv/jimmy/research-library/`               | Canonical research library (Muddy rsyncs FROM here; this is authoritative)                   | ~5 GB                                    |
| `/srv/jimmy/lancedb/`                        | Vector index (embeddings + metadata)                                                         | ~20 GB                                   |
| `/srv/jimmy/memory/`                         | `memory.db`, `intel.db`, `build_history`, session summaries, research-queue                  | ~10 GB                                   |
| `/srv/jimmy/backups/projects/`               | **Nightly incremental snapshots of ALL of `~/Projects/` from Muddy** (rsync --link-dest)     | ~50 GB hot + ~200 GB across 30 snapshots |
| `/srv/jimmy/backups/buildrunner-state/`      | Nightly snapshot of `~/Projects/BuildRunner3/.buildrunner/` + decisions.log from Muddy       | ~5 GB                                    |
| `/srv/jimmy/backups/git-mirrors/`            | Hourly `git fetch --all` bare clones of every repo in `~/Projects/` (fast disaster-recovery) | ~20 GB                                   |
| `/srv/jimmy/backups/supabase/`               | Daily Supabase DB dumps from Below                                                           | ~50 GB                                   |
| `/srv/jimmy/backups/brlogger/`               | Rotated browser/supabase/device/query logs (90-day retention)                                | ~30 GB                                   |
| `/srv/jimmy/archive/adversarial-reviews/`    | Historical review JSONs (already 495, growing fast)                                          | ~10 GB                                   |
| `/srv/jimmy/archive/cost-ledger/`            | Daily cost rollups for long-term analytics                                                   | ~5 GB                                    |
| `/srv/jimmy/archive/lockwood-pre-migration/` | Frozen snapshot of old Lockwood DBs after Phase 11 cutover (keep indefinitely)               | ~10 GB                                   |

Total working set: ~415 GB. Leaves ~1.5 TB headroom for years of growth.

### Nightly Incremental Backup of ~/Projects (from Muddy to Jimmy)

**Pattern:** `rsync -aHAXv --link-dest=<previous>` snapshot. Each nightly run creates `/srv/jimmy/backups/projects/YYYY-MM-DD/` that hardlinks unchanged files to the prior night — changed files cost full disk, unchanged cost zero. Every snapshot is a complete browsable tree; restore is `cp -a` or `rsync` from any snapshot date.

- **Schedule:** 03:00 local every night via `br3-nightly-backup.timer` on Muddy (not Jimmy — source-initiated so the pull fails loudly if Muddy is offline, and Muddy's systemd is where Projects lives)
- **Source:** `~/Projects/` with excludes: `node_modules/`, `.venv/`, `dist/`, `build/`, `target/`, `.next/`, `.turbo/`, `*.sock`, and anything matched by a top-level `.backupignore` the user drops in a project
- **Destination:** `byronhudson@10.0.1.106:/srv/jimmy/backups/projects/YYYY-MM-DD/`
- **Retention:** 30 daily snapshots + 12 monthly (1st of month, promoted from that day's daily) + 3 yearly (Jan 1). Prune script runs after every nightly success.
- **Integrity:** sha256sum of snapshot root written to `manifest.sha256` at end of run; weekly job spot-checks 10 random files against their manifest hash
- **Alerting:** if a nightly backup fails (rsync exit ≠ 0, or snapshot size <80% of prior night without a corresponding `.backupignore` diff), email via local MTA + dashboard red banner
- **Off-site:** weekly `rclone sync /srv/jimmy/backups/projects/<latest>/` → cloud (B2 or Wasabi) so a whole-Jimmy failure isn't total loss

**Deliverable ownership:** Phase 3 (Jimmy activation) creates the filesystem layout + backup scripts; Phase 11 dashboard adds storage-health + last-backup tile; Phase 14 self-maintenance owns the pruning cron + off-site sync.

### Hardware Utilization (Final)

| Node                               | Role                                                                             | State           |
| ---------------------------------- | -------------------------------------------------------------------------------- | --------------- |
| Muddy (M5)                         | Claude Code workstation, dispatch orchestrator, primary dev                      | Always on       |
| Below (Win, dual 3090 NVLink 48GB) | Local inference stack (~46/48GB resident), doc writing, embedding, summarization | Always on       |
| Jimmy (64GB DDR5 CPU)              | Memory/semantic backbone (see above)                                             | Always on       |
| Walter (M2)                        | Continuous vitest + Playwright + flaky detection                                 | Always on       |
| Otis (M2)                          | Parallel Codex dispatch, warm codex-agent                                        | Always on, warm |
| Lockwood (M2)                      | Warm reserve (was memory — migrated to Jimmy in Phase 11)                        | Warm reserve    |
| Lomax (M2)                         | Warm reserve + VRT Docker + staging server                                       | Warm reserve    |

### Below VRAM Ceiling Policy (real risk — 4% headroom)

Baseline 46/48GB = 2GB margin. KV cache growth on long context can eat that.

- Dispatcher tracks live VRAM every 5s
- Headroom <1GB for >30s → new 70B requests queue; new overflow-eligible jobs route to Lockwood MLX
- Hard max context-length cap on llama3.3:70b enforced in RuntimeRegistry — force summarize-before-escalate at ceiling; no OOM possible
- qwen3:8b + embeddings evict first under pressure
- Phase 3 includes a stress test driving to 47GB, confirms queuing + capping work

### Overflow Design — Warm Reserve That Scales On Demand

Lockwood and Lomax stay idle by default. They have pre-configured overflow roles that wake instantly when real load arrives, and drain back when it clears. No forced daily work.

**Pre-configured overflow (dormant):**

- Lockwood: secondary qwen3:8b (MLX), secondary embedding (MLX), chunking + metadata extraction worker, vitest shard 2/3
- Lomax: vitest shard 3/3, Playwright overflow, third parallel Codex builder (cold-start OK); VRT+staging stay primary

**Wake triggers:**
| Trigger | Threshold | Action |
|---|---|---|
| Below VRAM headroom | <1GB for >30s | Lockwood MLX picks up classification/embedding |
| Walter test queue depth | >2 phases queued | Lomax runs shard 3/3 (+ Lockwood 2/3 if deeper) |
| Parallel worktree dispatch | >2 concurrent phases | Lomax joins as third builder |
| Bulk research ingestion | >20 docs queued | Lockwood parallelizes chunking/metadata |
| Below unreachable | Health-check fails 3× in 15s | Lockwood + Lomax absorb qwen3:8b via MLX |

**Drain:** Trigger clear for >5 min → overflow node finishes current job, reports complete, returns idle. Overflow runs at nice-level priority; primary role (VRT/staging) never preempted.

**Dispatcher (on Muddy):** Central queue with per-node VRAM/queue/latency metrics. Each job tagged `node_affinity` + `overflow_eligible`. Dispatcher only promotes overflow-eligible jobs to reserve nodes when primary saturated. All decisions logged via RuntimeRegistry.

**Dashboard:** per-node util/VRAM/queue, reserve state (`idle`/`warming`/`active`/`draining`), trigger events with cause, historical overflow frequency for threshold tuning.

### Research Command Redesign

1. Claude researches (WebFetch/WebSearch/tool calls) — gather raw sources.
2. Claude synthesizes — judgment stays with Claude (research library: llama3.3:70b not benchmarked for judgment).
3. Claude gives immediate summary to user, applies to current discussion.
4. Handoff to Below in background: llama3.3:70b reformats to library template → qwen3:8b metadata → nomic embeddings → indexed into LanceDB on Jimmy.
5. Below writes `.buildrunner/research-queue/completed.jsonl` record with doc path, chunk count, status.
6. Claude reads that record next turn and reports to user: "Research indexed at `<doc-id>`, Y chunks, available to all models."

User never talks to a local model directly. Claude is the single voice.

### Adversarial Review Pipeline (Final)

1. `/review` invoked on diff.
2. **Below qwen3:8b pre-filter** — structural/syntax/schema check. Fails obvious issues without paid tokens.
3. **Below llama3.3:70b diff compression** — if reuse ≥2× in session or diff is large, compress to structured summary.
4. **Parallel paid review** (co-equal): Sonnet 4.6 + gpt-5.4 read compressed diff + critical excerpts.
5. **Single rebuttal round** — each sees the other's findings.
6. Consensus → ship. Disagreement → **Opus 4.7 arbiter** (`effort: xhigh`, adaptive thinking) reads both reviews + rebuttals + summary. Ruling is terminal.
7. Below indexes review outcome for future reference.

### Prompt Cache Design (Final)

3 breakpoints: (1) system+tools, (2) project+skill context, (3) task payload. Cache anything reused ≥2× in a session.

**Byte-identity test (Phase 8 BLOCKING):** Send two consecutive identical requests, assert byte-identical cached prefixes up to breakpoint 3. Finds hidden dynamic sources (f-string timestamps, dict ordering, `.now()`, `uuid`, env reads, config mtime). Ships Phase 8 only when byte-identity holds. Runs in CI on every prompt-template change.

### Quality Firewall (Structurally Enforced)

- Below/Jimmy/Lockwood/Lomax NEVER own final artifacts for code, diagnoses, frontend, architecture, reviews
- All local outputs tagged `draft=true` by RuntimeRegistry
- Only `RuntimeRegistry.execute()` dispatches local model calls — ONLY path
- Pre-commit hook rejects direct `ollama`/`curl`/`requests.post` to local endpoints outside the registry module
- Silent fallback to paid models on any local failure — no user-visible error

### Status Table (All Phases — UPDATE ON EVERY PHASE COMPLETION)

| #   | Status      | Completed         | 1-line summary                                                                                                               |
| --- | ----------- | ----------------- | ---------------------------------------------------------------------------------------------------------------------------- |
| 0   | completed   | 2026-04-20T18:53Z | AGENTS.md authored — router + 5 scopes, 11907 bytes                                                                          |
| 1   | completed   | 2026-04-20T18:49Z | Below dual-3090 NVLink 4×14.062 GB/s, BIOS 2101, RM1200x, 64GB DIMM                                                          |
| 2   | completed   | 2026-04-19T18:10Z | 70B dual-GPU 18.01 tok/s, NVLink 4×14.062 GB/s, same-model residency proven                                                  |
| 3   | completed   | 2026-04-20T21:59Z | Jimmy systemd services live + enabled, /srv/jimmy/ layout + UFW provisioned, 26 git mirrors cloned, nightly backup scheduled |
| 4   | not_started | —                 | 7-node priority + overflow dispatcher                                                                                        |
| 5   | not_started | —                 | Below skill integration                                                                                                      |
| 6   | completed   | 2026-04-20T19:30Z | OllamaRuntime registered, local_ready capability live                                                                        |
| 7   | REPLACED    | —                 | Was LiteLLM; now RuntimeRegistry shim + pre-commit hook                                                                      |
| 8   | completed   | 2026-04-20T22:10Z | cache_policy (3 ephemeral breakpoints) + summarizer (qwen3:8b); cross_model_review hard-truncation removed; 31/31 tests pass |
| 9   | not_started | —                 | 2-way review + Opus arbiter (NOT 3-way, NOT r1)                                                                              |
| 10  | not_started | —                 | Auto-context hook + research redesign                                                                                        |
| 11  | not_started | —                 | Dashboard + Jimmy cutover + overflow wake/drain                                                                              |
| 12  | not_started | —                 | Multi-model context parity                                                                                                   |
| 13  | not_started | —                 | Shadow → cutover + flag flip                                                                                                 |
| 14  | not_started | —                 | Self-maintenance crons                                                                                                       |

### Recommended Ship Order (inside remaining phases)

1. **Phase 8 cache engineering** — biggest single ROI (59–70%), byte-identity test first
2. **Phase 5 Below skill integration** — unlocks ~30% paid-token reduction
3. **Phase 10 auto-context + research redesign** — daily workflow win
4. **Phase 11 Jimmy cutover + overflow dispatcher** — unlocks scalable reserve
5. **Phase 9 2-way review pipeline** — quality floor + cost (requires phases 5/8)
6. **Phase 10 reranker** — ship 80% value (vector-only) first, reranker after blocking validation
7. **Phase 13 shadow cutover** — quality gate for everything before

### Reporting Chain

Below and Jimmy report completion to Claude via `.buildrunner/*-queue/completed.jsonl`. Claude reports to user at next conversation turn. User never talks to a local model.

---

## Overview

Upgrade Below to dual RTX 3090 NVLink (48GB VRAM), add **Jimmy** (Minisforum MS-A2, 64GB DDR5, 10GbE-ready) as the new memory/semantic backbone node, reconfigure all 7 cluster nodes per the Hardware Utilization table above, and wire Below 70B inference deep into the BR3 runtime pipeline. Ollama serves all local inference — llama3.3:70b + qwen3:8b + nomic-embed-text resident simultaneously (~46GB of 48GB VRAM). **No deepseek-r1, no vLLM, no LiteLLM** (see Final Decisions Override).

**Builds on top of the completed Codex integration (BUILD_codex-full-br3-integration).** The runtime abstraction (`core/runtime/`), `RuntimeTask`/`RuntimeResult` contracts, preflight/postflight policy, `command_capabilities.json`, shadow runner, and consensus adversarial review all exist. This plan extends that abstraction with a local-inference runtime (OllamaRuntime), the RuntimeRegistry shim as the ONLY dispatch path for local models (replaces the original LiteLLM gateway idea), prompt-cache engineering, a context-injection hook, a cluster dashboard (updated to surface Jimmy as a first-class node), and multi-model context parity for Codex + Below.

**Parallel build principle.** Every new component is built alongside existing BR3 code paths without disrupting them. No existing node is removed — Jimmy is added as the memory backbone; Lockwood's memory role migrates to Jimmy in Phase 11 via shadow-mode cutover; Lockwood and Lomax become warm reserves (see Overflow Design). No existing skill loses its current behavior — new behavior is opt-in via feature flags (`BR3_CLUSTER_MAX=on`, `BR3_LOCAL_ROUTING=on`, `BR3_AUTO_CONTEXT=on`, `BR3_GATEWAY=on`, `BR3_MULTI_MODEL_CONTEXT=on`, `BR3_OVERFLOW=on`) until cutover. Current `/spec`, `/begin`, `/autopilot`, `/review`, `/commit` flows continue to work unchanged while the new paths are validated. Cutover is an explicit phase, not a side effect.

**Not BR4.** Nothing is rewritten. The Codex integration already delivered the multi-runtime architecture. This is BR3 getting a third runtime (Ollama), one hook, a dashboard, multi-model context parity, and self-maintenance, on expanded hardware. The BR3 repo, skill set, sidecar, registry, and state machine all stay.

**Quality firewall (unchanged).** Nothing Below or Jimmy generates ships without one of: a Claude pass, a Walter test pass, or user approval. Final code edits, frontend/UX, architecture decisions, `/diag`, `/root`, and the adversarial arbiter step all stay on Muddy's Claude Opus 4.7. Enforcement is structural — only `RuntimeRegistry.execute()` can dispatch a local model call, and a pre-commit hook rejects direct endpoint calls outside the registry.

---

## Codex Execution Model (applies to every phase)

**SEE AUTOPILOT PROTOCOL → Role Matrix at the top of this file for authoritative Architect/Builder/Reviewer assignment.** The table below is implementation detail; Role Matrix wins on any conflict.

Opus 4.7 architects every phase; gpt-5.4 is default builder; gpt-5.3-codex owns terminal-heavy phases; Sonnet + gpt-5.4 co-equal review every phase; Opus arbitrates disagreement only. Single rebuttal round, then escalate.

| Setting            | Default                                                                              | Override Pattern                                                                  |
| ------------------ | ------------------------------------------------------------------------------------ | --------------------------------------------------------------------------------- |
| Codex model        | `gpt-5.4`                                                                            | `gpt-5.3-codex` for terminal-heavy phases (2, 3, 13, 14)                          |
| Effort             | `high` for coding/agentic (OpenAI recommendation); `medium` for classification       | `xhigh` for Phase 9 review-pipeline wiring; `low` for boilerplate (Phase 0 parts) |
| Sandbox            | `workspace-write` + `network_access=true`                                            | Phase 2/3 require network for Ollama pulls + apt installs                         |
| Approval policy    | `on-request`                                                                         | `never` only inside Phase 13 cutover dry-run                                      |
| Plan Mode          | Skip for the easiest 25% (file-scoped MODIFYs); use for any phase with ≥4 NEW files  | —                                                                                 |
| Worktree isolation | One worktree per parallel phase wave                                                 | Required for Wave 2 (Phases 2+3+6) and Wave 3 (4+7+8)                             |
| Cache breakpoints  | 3 per Anthropic pattern (system+tools / project+skill / task payload)                | Byte-identity test ships Phase 8 as BLOCKING deliverable                          |
| Verification rule  | Every deliverable has an explicit `Verify:` command                                  | No deliverable accepted without one                                               |
| Review gate        | 2-way parallel (Sonnet 4.6 + gpt-5.4), Opus 4.7 arbiter on disagreement, cap 1 round | No phase marks complete without both reviewers passing or arbiter ruling          |
| `budget_tokens`    | **DO NOT USE** — deprecated on Opus 4.7, throws 400                                  | Use `effort: "high"`/`"xhigh"` for adaptive thinking instead                      |

**Codex behavioral guardrails (encoded in AGENTS.md, Phase 0):**

- IMPORTANT: Below (Ollama) NEVER drafts final diagnoses, final code, frontend/UX, or architecture decisions. Pre-summary and first-pass only.
- IMPORTANT: On any node-health failure, dispatcher falls back to Claude with NO user-visible error. Silent fallback is the contract.
- IMPORTANT: All five feature flags (`BR3_CLUSTER_MAX`, `BR3_LOCAL_ROUTING`, `BR3_AUTO_CONTEXT`, `BR3_GATEWAY`, `BR3_MULTI_MODEL_CONTEXT`) default OFF until Phase 13 cutover. Codex MUST NOT flip defaults outside Phase 13.
- NEVER touch files outside the per-phase `Files:` whitelist, EXCEPT the two implicit append-only artifacts every phase is expected to write:
  1. `.buildrunner/decisions.log` — APPEND-ONLY one-line entry per phase (declared in each phase's `Done When`). Never rewrite or delete prior entries.
  2. The phase's own staged AGENTS.md append snippet (see "Shared-File Merge Gate" below) — staged into `core/cluster/AGENTS.md.append-phase<N>.txt` (or the equivalent per-file path) instead of editing the AGENTS.md directly during parallel waves.
- NEVER auto-generate AGENTS.md content (ETH Zurich: −3% task success when LLM-generated).

---

## AGENTS.md Maintenance Rule (applies to every phase)

AGENTS.md is the steering wheel — Codex applies its rules every loop, automatically. Treat it as a living deliverable, not a one-time Phase 0 artifact. BR3 takes advantage of AGENTS.md in every phase that introduces new conventions.

**Per-phase requirements:**

- IMPORTANT: Every phase that introduces a new convention, contract, runtime, file pattern, port, or routing rule MUST update the affected AGENTS.md as an explicit deliverable in the same change set.
- IMPORTANT: Every Claude Review MUST verify "AGENTS.md is current for this scope" — flag any new convention not yet encoded.
- IMPORTANT: Updates stay non-inferable, scoped, and ≤8KB per file. Combined ceiling 24KB across all AGENTS.md files (8KB headroom under the 32KB silent-truncation cliff).
- NEVER let an AGENTS.md update grow beyond the new rules the phase introduces — additive lines only, EXCEPT for documented state-change phases (currently only Phase 13 cutover) where the supersede mechanism applies.
- **Supersede mechanism (state-change phases only):** When a phase changes operational state that is encoded in AGENTS.md (e.g., a feature-flag default flip), the phase MUST (a) delete the now-stale line in the same edit, (b) append the new line, AND (c) bump a single-line `Last updated: YYYY-MM-DD (Phase N)` marker at the top of the affected AGENTS.md file. No phase ships with two contradictory live instructions in the same scope.
- NEVER allow LLM-generated content (ETH Zurich: −3% task success). Codex transcribes human-provided rules; it does NOT invent them.
- NEVER ship a phase whose Claude Review flagged stale or contradictory AGENTS.md.

**Per-phase mapping (which AGENTS.md each phase touches):**

| Phase | Updates                                                                 | New rule type                                                         |
| ----- | ----------------------------------------------------------------------- | --------------------------------------------------------------------- |
| 0     | All 5 (initial authoring)                                               | Foundational                                                          |
| 2     | `core/cluster/AGENTS.md`                                                | NVLink dual-GPU detection rule                                        |
| 3     | `~/AGENTS.md` on Jimmy (deploy staged file); `core/cluster/AGENTS.md`   | Linux dispatch + systemd unit naming                                  |
| 4     | `core/cluster/AGENTS.md`                                                | 7-node priority order + overflow workers                              |
| 5     | `core/cluster/AGENTS.md`                                                | Routing table + flag-gated skill behavior                             |
| 6     | `core/runtime/AGENTS.md`                                                | OllamaRuntime + `local_ready` capability                              |
| 7     | `core/cluster/AGENTS.md`                                                | Gateway routing + cost-ledger schema                                  |
| 8     | `core/runtime/AGENTS.md`                                                | Cache breakpoint contract + summarizer rule                           |
| 9     | `core/cluster/AGENTS.md`                                                | 3-way + arbiter pattern; ultrathink budget                            |
| 10    | `core/cluster/AGENTS.md`; `~/AGENTS.md` on Jimmy                        | Auto-context hook contract + budget                                   |
| 11    | `ui/dashboard/AGENTS.md`                                                | New panel registry + WebSocket reconnect                              |
| 12    | `core/cluster/AGENTS.md`; `~/AGENTS.md` on Jimmy; `~/AGENTS.md` on Otis | `/context/{model}` endpoint + per-model budgets + read-mount contract |
| 13    | Root `AGENTS.md`; `core/cluster/AGENTS.md`                              | Default-on flags + cutover state                                      |
| 14    | `core/cluster/AGENTS.md`                                                | Self-health timers + rebalance contract                               |

Each phase's Deliverables list includes the explicit AGENTS.md update line. Each phase's Done When includes "AGENTS.md updated and reviewed for this scope".

---

## Shared-File Merge Gate (applies to every parallel wave)

Several files are touched by multiple phases inside a single wave (most notably `core/cluster/AGENTS.md` and `~/.buildrunner/scripts/adversarial-review.sh`). To eliminate guaranteed merge conflicts in parallel worktrees, every phase that would otherwise edit a shared file MUST stage its change as a deterministically-named patch file and a serialized merge step happens at wave-end before any phase in the wave is marked complete.

**Staging convention (per phase, per shared file):**

| Shared file                                    | Staging path (per phase N)                                                   |
| ---------------------------------------------- | ---------------------------------------------------------------------------- |
| `core/cluster/AGENTS.md`                       | `core/cluster/AGENTS.md.append-phase<N>.txt`                                 |
| `core/runtime/AGENTS.md`                       | `core/runtime/AGENTS.md.append-phase<N>.txt`                                 |
| `ui/dashboard/AGENTS.md`                       | `ui/dashboard/AGENTS.md.append-phase<N>.txt`                                 |
| Root `AGENTS.md`                               | `AGENTS.md.append-phase<N>.txt`                                              |
| `~/.buildrunner/scripts/adversarial-review.sh` | `~/.buildrunner/scripts/adversarial-review.sh.patch-phase<N>` (unified diff) |

**Wave-end merge step (`~/.buildrunner/scripts/wave-merge.sh <wave-N>`):**

1. Run on `main` worktree, after every phase in the wave passes its individual Claude Review.
2. Apply append snippets in ascending phase order (e.g., Wave 3 merges `phase-4` then `phase-7` then `phase-8`). Concatenate snippet content under the existing AGENTS.md scope, preserving the supersede-mechanism rule.
3. Apply `.sh.patch-phase<N>` patches in ascending phase order via `git apply --3way`. Reject and surface any conflict for human resolution.
4. Re-run the per-file size verify (`wc -c <file>`) and the supersede-mechanism check (no contradictory live instructions).
5. Open a single "wave-merge" Claude Review with target = every shared file touched in the wave + every staged snippet. Block-on: any merge skip, any size breach post-merge, any contradictory line.
6. Only after the wave-merge review passes are all phases in the wave eligible to mark complete.

**Phase-level rule:**

- IMPORTANT: Phases in the SAME wave MUST NOT edit the merged file directly during their worktree work — only the staged snippet/patch. Direct edits invalidate the wave-merge gate.
- IMPORTANT: Phases in DIFFERENT waves edit the merged file directly (no staging needed) because waves are serialized.
- The Parallelization Matrix below marks which phases use staging by listing the staged path in their `Files:` section.

---

## Review Convergence Policy (applies to EVERY review in this build)

Every review gate in this build — per-phase Claude Review, wave-merge review, Phase 9 three-way adversarial review, and any `/review` or `adversarial-review.sh` invocation — MUST follow this convergence policy. This is a response to a production failure in which a `/spec` adversarial-review session looped 7+ rounds (R17→R24→R27→R26→R29→R30→R31, 49 consecutive blocked reviews) because the reviewer always finds new findings in a sufficiently complex plan and no hard cap existed.

**Policy rules:**

1. **Hard round cap: 3.** No review gate may auto-re-run more than **3** times on the same artifact. Environment override: `BR3_MAX_REVIEW_ROUNDS=<N>`. Default stays at 3.
2. **Round counter is mandatory.** Every tracking JSON written to `.buildrunner/adversarial-reviews/phase-*-*.json` MUST include `review_round` (1-based) and `max_rebuttal_rounds`. Enforced by `~/.buildrunner/scripts/adversarial-review.sh::write_tracking_records`.
3. **Structural vs fixable classification.** Every finding emitted by any reviewer MUST include a `fix_type` field: `fixable` (plan-text edit resolves it) or `structural` (requires redesigning phase boundaries or tech-stack choice). Enforced by the adversarial prompt in `adversarial-review.sh::build_adversarial_prompt`.
4. **Structural blockers escalate immediately.** A single `fix_type: structural` blocker halts the review loop and requires user decision. The commit hook (`~/.buildrunner/hooks/require-adversarial-review.sh`) exits with code 2 (distinct from exit 1 "not clean yet") when this fires.
5. **Persistent-blocker detection.** If the same normalized blocker text appears in 2+ consecutive tracking files for the same phase, it is treated as structural regardless of its declared `fix_type`. Enforced by the commit hook.
6. **Rebuttal pass is MANDATORY on consensus.** After initial merge, the script MUST call `build_rebuttal_prompt` to ask Claude "which blockers actually survive?" and downgrade non-surviving blockers to warnings with `rebuttal_downgraded: true`. Environment override to disable (for debugging only): `BR3_REBUTTAL_DISABLED=1`.
7. **Escalation prompt is explicit.** When the cap or a structural blocker triggers, the script/hook prints:
   - Round count (`N/3`)
   - The full list of remaining blockers with `fix_type`
   - Persistent blockers separately
   - Three options: **CONTINUE** (one more round with user-supplied fix), **OVERRIDE** (`BR3_BYPASS_ADVERSARIAL_REVIEW=1`, logged to `decisions.log`), **SIMPLIFY** (reduce phase scope)
8. **No silent fallthrough.** Agents MUST NOT autonomously loop past round 3 or past the first structural blocker. `/spec` Step 3.7, Phase 9 three-way, and all wave-merge reviews carry explicit stop instructions.

**Implementation mapping (which phase enforces which rule):**

| Rule                      | Enforced by                             | Implementation location                                                                                      |
| ------------------------- | --------------------------------------- | ------------------------------------------------------------------------------------------------------------ |
| 1 (round cap 3)           | Phase 8 staged patch                    | `adversarial-review.sh` + `require-adversarial-review.sh` (already shipped pre-build as the fix for R17→R31) |
| 2 (round counter)         | Phase 8 staged patch                    | `write_tracking_records` — adds `review_round` per phase, reads `BR3_MAX_REVIEW_ROUNDS` env                  |
| 3 (fix_type)              | Phase 8 staged patch                    | `build_adversarial_prompt` — every finding includes `fix_type`                                               |
| 4 (structural escalation) | Phase 8 staged patch                    | `require-adversarial-review.sh` — exit 2 on structural                                                       |
| 5 (persistent-blocker)    | Phase 8 staged patch                    | `require-adversarial-review.sh::persistent_blockers`                                                         |
| 6 (rebuttal pass)         | Phase 8 staged patch                    | `run_consensus_mode` — calls `build_rebuttal_prompt`, filters surviving blockers                             |
| 7 (escalation prompt)     | Phase 8 staged patch + `/spec` Step 3.7 | Hook stderr + skill instruction text                                                                         |
| 8 (no silent fallthrough) | Phase 9 (3-way review)                  | `cross_model_review.py` — reuses same convergence policy; arbiter is NOT a 4th round                         |

**Phase 9 three-way review specifics:**

- 3-way is still bounded by rule 1: max 3 full review cycles across the Sonnet+Codex+R1 trio. The rebuttal pass counts as part of round 1, not a new round.
- Arbiter invocation (Opus 4.7 ultrathink) is NOT a new round — it is the tiebreaker on unresolved disagreement AFTER the rebuttal. Its ruling is terminal.
- If the arbiter ruling is contested by a subsequent review attempt on the same artifact, the agent MUST stop and escalate to the user. Agents never override an arbiter ruling autonomously.

**Wave-merge review specifics:**

- Wave-merge Claude Reviews (per Shared-File Merge Gate rule 5) run ONCE per wave. No autonomous re-run loop. If the wave-merge review blocks, the agent stops and presents findings to the user.

**Per-phase Claude Review specifics:**

- Each phase's "Claude Review (mandatory before Phase N marked complete)" section runs ONCE by default. If it returns blockers, the agent applies fixes and re-runs exactly once more (max 2 total per-phase reviews). If it still fails, the agent escalates to the user per rule 7.

**Verify:**

- `grep -c '"review_round"' .buildrunner/adversarial-reviews/phase-*-*.json` returns ≥1 for every tracking file after Phase 8.
- `grep -c '"fix_type"' .buildrunner/adversarial-reviews/phase-*-*.json` returns ≥1 for every tracking file after Phase 8.
- A test plan with a planted structural conflict (circular phase dependency) triggers exit 2 from `require-adversarial-review.sh` on first run, not after 3 rounds.
- A test plan with a planted fixable-only blocker converges within 3 rounds or exits with the escalation prompt.

---

## Parallelization Matrix

| Phase | Key Files                                                                            | Can Parallel With | Blocked By                | Codex Model    |
| ----- | ------------------------------------------------------------------------------------ | ----------------- | ------------------------- | -------------- |
| 0     | AGENTS.md (root) + 4 scoped sub-AGENTS.md                                            | 1                 | —                         | gpt-5.4 / low  |
| 1     | Hardware install guide (no code files)                                               | 0                 | —                         | N/A (physical) |
| 2     | below-verify.sh, below-benchmark.sh, ollama-below.env, node_inference.py             | 3, 6              | 0, 1 (hardware gate)      | gpt-5.3-codex  |
| 3     | jimmy-bootstrap.sh, migrate-lockwood-data.sh, jimmy-verify.sh, systemd svcs          | 2, 6              | 0, 1 (hardware gate)      | gpt-5.3-codex  |
| 4     | cluster.json, node-matrix.mjs, events.mjs, ~20 files with IP additions (additive)    | —                 | 0, 2, 3                   | gpt-5.4 / low  |
| 5     | below-route.sh, skill .md files, adversarial-review.sh (opt-in via flag)             | 7, 8              | 0, 4                      | gpt-5.4        |
| 6     | core/runtime/runtime_registry.py, core/runtime/ollama_runtime.py, SUPPORTED_RUNTIMES | 2, 3              | 0                         | gpt-5.4        |
| 7     | LiteLLM config on Jimmy, br3-gateway.service, cost-ledger.py                         | 5, 8              | 0, 3, 6                   | gpt-5.4        |
| 8     | core/cluster/cross_model_review.py (cache breakpoints + summarize step)              | 5, 7              | 0, 6                      | gpt-5.4        |
| 9     | cross_model_review.py (3-way + Opus arbiter), cross_model_review_config.json         | 10                | 0, 6, 8                   | gpt-5.4 / high |
| 10    | hooks/auto-context.sh, api/retrieve.py on Jimmy, reranker model                      | 9                 | 0, 3, 6                   | gpt-5.4        |
| 11    | ui/ dashboard panels (port 4400), WebSocket from Jimmy                               | 12                | 0, 7, 9                   | gpt-5.4        |
| 12    | context_bundle.py, /context/{model}, codex-bridge.sh, below-route.sh, read-mounts    | 11                | 0, 3, 6, 7, 10            | gpt-5.4        |
| 13    | feature-flag defaults, decisions.log, cutover checklist                              | —                 | 0, 5, 7, 8, 9, 10, 11, 12 | gpt-5.3-codex  |
| 14    | self-health monitor, auto-rebalance, model-update workflow                           | —                 | 0, 13                     | gpt-5.3-codex  |

**Optimal Execution Waves (each wave ends with the Shared-File Merge Gate before any phase in the wave is marked complete):**

- **Wave 1 (parallel):** Phase 0 (AGENTS.md authoring, 1 worktree) + Phase 1 (hardware install, physical work) — independent
- **Wave 2 (parallel, 3 worktrees):** Phase 2 (Below activation) + Phase 3 (Jimmy activation) + Phase 6 (runtime registry extension)
  - Shared-file conflicts in this wave: Phase 2 stages `core/cluster/AGENTS.md.append-phase2.txt`; Phase 3 stages `core/cluster/AGENTS.md.append-phase3.txt`. Phase 6 edits `core/runtime/AGENTS.md` directly (no other phase in this wave touches it).
- **Wave 3 (parallel, 3 worktrees):** Phase 4 (cluster recon) + Phase 7 (LiteLLM gateway) + Phase 8 (cache + summarize)
  - Shared-file conflicts: Phase 4 stages `core/cluster/AGENTS.md.append-phase4.txt`; Phase 7 stages `core/cluster/AGENTS.md.append-phase7.txt`. Phase 8 edits `core/runtime/AGENTS.md` directly (no other phase in this wave touches it).
- **Wave 4 (parallel, 3 worktrees):** Phase 5 (Below skill integration) + Phase 9 (3-way adversarial) + Phase 10 (auto-context hook)
  - Shared-file conflicts: Phase 5, 9, 10 each stage `core/cluster/AGENTS.md.append-phase<N>.txt`. Phase 5 and Phase 9 each stage `~/.buildrunner/scripts/adversarial-review.sh.patch-phase<N>` (Phase 5 adds `--local`, Phase 9 adds `--three-way`; both apply at wave-merge in phase order).
- **Wave 5 (parallel, 2 worktrees):** Phase 11 (dashboard @ 4400) + Phase 12 (multi-model context parity)
  - Shared-file conflicts: Phase 11 edits `ui/dashboard/AGENTS.md` directly; Phase 12 stages `core/cluster/AGENTS.md.append-phase12.txt`. No overlap — wave-merge gate still runs the size verify and supersede-mechanism check.
- **Wave 6:** Phase 13 (cutover + validation) — direct edits allowed (single-phase wave); state-change supersede mechanism applies for the flag-default flip
- **Wave 7:** Phase 14 (BR3 self-maintenance) — direct edits allowed (single-phase wave)

---

## Phases

### Phase 0: AGENTS.md Authoring (Codex Scoping Foundation)

**Status:** ✅ COMPLETE (2026-04-20) — 6 files authored, 11907 bytes total, all gates pass
**Codex model:** gpt-5.4
**Codex effort:** low
**Worktree:** main repo (no parallelization within phase)
**Blocked by:** None
**Can parallelize:** Phase 1 (independent — hardware vs docs)

#### Goal

Author one root `AGENTS.md` as a router (≤100 lines) plus FIVE scoped sub-AGENTS.md files (3 in-repo: `core/runtime`, `core/cluster`, `ui/dashboard`; 2 staged for remote nodes: `~/.buildrunner/agents-md/jimmy.md`, `~/.buildrunner/agents-md/otis.md`) for the directories and remote nodes Codex will modify or run on across this build. Total artifacts: SIX. Encode every non-inferable rule in this BUILD as an enforced AGENTS.md constraint so Codex applies them every loop without prompting.

#### Context

**Files (touch only these):**

- `AGENTS.md` (NEW — repo root, router pattern)
- `core/runtime/AGENTS.md` (NEW)
- `core/cluster/AGENTS.md` (NEW)
- `ui/dashboard/AGENTS.md` (NEW)
- `~/.buildrunner/agents-md/jimmy.md` (NEW — staged on Muddy; deployed to Jimmy home dir as `AGENTS.md` during Phase 3)
- `~/.buildrunner/agents-md/otis.md` (NEW — staged on Muddy; deployed to Otis home dir as `AGENTS.md` during Phase 12 — Codex runs there)

**Why this exists (non-inferable):** This BUILD adds 14 phases of context across ~6 directories and 3 remote nodes that run agents. Without scoped AGENTS.md, Codex either burns tokens re-discovering conventions or violates them. ETH Zurich data: human-curated AGENTS.md = +4% task success, LLM-generated = −3% (actively harmful). 32KB silent truncation risk if all rules live in one file. The router pattern (Harness Engineering) keeps each scope ≤8KB.

#### Constraints

- IMPORTANT: AGENTS.md content is HUMAN-AUTHORED. Codex may transcribe rules I provide, but MUST NOT invent conventions or infer new rules from code reads.
- IMPORTANT: Each AGENTS.md ≤8KB. Combined ceiling 24KB (8KB headroom below the 32KB silent-truncation cliff).
- NEVER include motivation, prose, or background — operational rules only.
- NEVER include rules the agent can infer from code (e.g., "use TypeScript", "prefer async").
- Root AGENTS.md is a router only — ≤100 lines, no implementation rules.
- Each sub-AGENTS.md scoped to one directory's non-inferable rules.

#### Deliverables

- [ ] **Root `AGENTS.md`** — sections: Build & Test (file-scoped commands), Quick Rules (≤6 bullets), Router (one bullet per scope: `For runtime work, see @core/runtime/AGENTS.md` etc.). Hard cap 100 lines.
  - Verify: `wc -l AGENTS.md` returns ≤100. `wc -c AGENTS.md` returns ≤8000.

- [ ] **`core/runtime/AGENTS.md`** — encodes: `RuntimeTask`/`RuntimeResult` shape, `BaseRuntime.execute()` contract, "fallback to Claude on Ollama 503 — no user-visible error", `SUPPORTED_RUNTIMES` ordering, capability levels (`claude_only`, `codex_workflow_only`, `codex_ready`, `local_ready`), 3-breakpoint cache contract.
  - Verify: `wc -c core/runtime/AGENTS.md` ≤8000. `grep -c "IMPORTANT\|NEVER" core/runtime/AGENTS.md` ≥3.

- [ ] **`core/cluster/AGENTS.md`** — encodes: quality firewall ("Below NEVER drafts final diagnoses, final code, frontend/UX, or architecture; pre-summary and first-pass only"), fallback contract ("on node-health failure, dispatcher reroutes silently — no user-visible error"), feature-flag discipline ("all 5 BR3\_\* flags default OFF until Phase 13"), summarize-before-escalate rule ("diff > 12KB → run summarizer first").
  - Verify: file mentions all 5 feature-flag names verbatim. `grep -c "BR3_" core/cluster/AGENTS.md` ≥5.

- [ ] **`ui/dashboard/AGENTS.md`** — vanilla HTML + JS panels, no React/no framework, port 4400 only. Per-file validation (eslint single-file). WebSocket reconnect contract (exponential backoff, cap 30s).
  - Verify: file mentions "vanilla HTML" and "no React".

- [ ] **Jimmy AGENTS.md** at `~/.buildrunner/agents-md/jimmy.md` (deployed in Phase 3) — Linux conventions, systemd unit naming (`br3-*.service`), dispatcher rsync vs tar+scp rule, port allocation (8100 semantic, 4400 dashboard, 4500 gateway).
  - Verify: file lists all 3 ports. `grep -c "br3-" ~/.buildrunner/agents-md/jimmy.md` ≥3.

- [ ] **Otis AGENTS.md** at `~/.buildrunner/agents-md/otis.md` (deployed in Phase 12) — encodes Otis as a Codex-execution worker; read-only context mounts; `/context/codex` fetch rule before any task.
  - Verify: file mentions "/context/codex" and "read-only".

- [ ] **Per-file validation commands embedded in each AGENTS.md** — Codex defaults to file-scoped runs, never full suite:
  - Python: `pytest tests/runtime/test_<file>.py -x`, `ruff check core/runtime/<file>.py`
  - JS: `npx eslint --fix ui/dashboard/panels/<file>.js`
  - Shell: `shellcheck ~/.buildrunner/scripts/<file>.sh`

- [ ] **Non-inferability audit** — read each AGENTS.md and strike any line that says "use X" or "prefer Y" where the codebase already demonstrates that pattern.

#### Claude Review (mandatory before Phase 0 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 0 --target AGENTS.md`
- Required findings: (1) every rule is non-inferable from existing code; (2) total combined size <24KB; (3) router pattern is acyclic; (4) zero LLM-generated boilerplate prose; (5) all 5 feature flags + quality firewall + fallback contract are encoded.
- Block-on: any inferable rule, any size breach, any prose without an enforcement target.

#### Done When

- [ ] All 6 AGENTS.md files exist at declared paths (4 in-repo + 2 staged in `~/.buildrunner/agents-md/`).
- [ ] Combined size verify (includes BOTH in-repo files AND staged remote files): `(find . -name AGENTS.md -not -path './node_modules/*'; ls ~/.buildrunner/agents-md/jimmy.md ~/.buildrunner/agents-md/otis.md) | xargs wc -c | tail -1` total ≤24576.
- [ ] Per-file size cap: `for f in AGENTS.md core/runtime/AGENTS.md core/cluster/AGENTS.md ui/dashboard/AGENTS.md ~/.buildrunner/agents-md/jimmy.md ~/.buildrunner/agents-md/otis.md; do test "$(wc -c < "$f")" -le 8192 || echo "OVER: $f"; done` prints nothing.
- [ ] `wc -l AGENTS.md` ≤100 (root file).
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 0: AGENTS.md authored — router + 5 scopes (6 files total, in-repo + staged) — total Nbytes`.

---

### Phase 1: Hardware Installation, BIOS & Overclocking

**Status:** ✅ COMPLETE (2026-04-20) — Below: 2× RTX 3090 + NVLink 4×14.062 GB/s verified; Jimmy: Ubuntu 24.04 at 10.0.1.106, 60GB RAM, 1.8TB NVMe
**Codex model:** N/A (physical work; verification scripts authored in Phase 2)
**Worktree:** N/A
**Blocked by:** None (parts arriving Apr 13-19)
**Can parallelize:** Phase 0

#### Goal

Both machines physically assembled, BIOS updated and optimized, GPUs overclocked, everything POST-verified before any software work begins.

#### Context

**Files:** None (physical hardware phase — output is artifacts: photos, nvidia-smi logs, BIOS screenshots).

**Why this exists (non-inferable):** Z390-E ships with a 2019 BIOS (v1302) that may not initialize Ampere GPUs or support resizable BAR. AX860 PSU is undersized for dual 3090s. NVLink P3669 must be reseated until `nvidia-smi topo -m` shows `NV#` (not `PHB`).

#### Constraints

- IMPORTANT: BIOS update on Below MUST happen BEFORE installing the 3090s.
- NEVER power off Below mid-BIOS-flash (corruption risk).
- NEVER daisy-chain a single PCIe cable to both 8-pin connectors on a 3090 — use TWO SEPARATE PSU cables per card.

#### Part A: Below — BIOS Update (DO THIS FIRST, before touching any hardware)

The Z390-E is on BIOS v1302 from September 2019. This MUST be updated before installing the 3090s.

**Deliverables:**

- [ ] Download latest Z390-E BIOS from ASUS support (https://rog.asus.com/motherboards/rog-strix/rog-strix-z390-e-gaming/helpdesk_bios/) — get the newest version available.
- [ ] Copy BIOS file to a FAT32-formatted USB drive (root directory, not in a folder).
- [ ] Boot into BIOS (Del key on POST), go to Tool > ASUS EZ Flash 3, select USB drive, flash. DO NOT power off during flash. Takes 3-5 minutes.
- [ ] After reboot, enter BIOS again and load Optimized Defaults (F5).
- [ ] Enable in BIOS:
  - **Above 4G Decoding: Enabled** — required for 48GB VRAM addressing
  - **Re-Size BAR Support: Enabled** (if available)
  - **XMP: Enabled** (Profile 1) — DDR4-3200 for all 4 DIMMs
  - **Fast Boot: Disabled**
  - **PCIEX16_1: Gen3, PCIEX16_2: Gen3** — lock to Gen3 explicitly
- [ ] Save and exit (F10). Confirm Windows boots normally with the existing 2080 Ti.
  - Verify: BIOS version display in POST screen photo.
- [ ] **Above 4G Decoding machine-readable artifact** — after Windows boot, capture `nvidia-smi --query-gpu=index,name,memory.total --format=csv` AND PowerShell `Get-PnpDevice -Class Display | Format-List Name,InstanceId | Out-File phase-1-display-pnp.txt`. Save both as Phase 1 artifacts. The `nvidia-smi` output MUST show full advertised VRAM (24GB per 3090); short reads (e.g., <12GB on a 24GB card) are the canonical signature of Above-4G-Decoding being disabled. This is the artifact the Phase 2 `below-verify.sh` references.
  - Verify: artifact files exist; `nvidia-smi` output captured shows expected per-card VRAM.

#### Part B: Below — PSU Swap (AX860 → RM1200x SHIFT)

**Deliverables:**

- [ ] Shut down Below. Flip PSU switch off. Unplug. Wait 30 seconds.
- [ ] Photograph all current cable connections.
- [ ] Remove AX860; install RM1200x SHIFT (cables connect to side panel).
- [ ] Reconnect: 24-pin ATX, 8-pin CPU (EPS12V), SATA. DO NOT connect GPU power yet.
- [ ] Test boot WITHOUT any GPU installed.
  - Verify: machine POSTs to BIOS or splash screen.

#### Part C: Below — RAM Upgrade (32GB → 64GB)

Adding 2×16GB Corsair Vengeance LPX DDR4-3200 (CMW32GX4M2C3200C16) to A1+B1.

**Deliverables:**

- [ ] Install new DIMMs into A1 and B1.
- [ ] Boot BIOS. Verify 4 DIMMs detected (64GB total).
- [ ] Re-enable XMP Profile 1. If 3200MHz fails, drop to 3000MHz.
- [ ] Memory test (mdsched.exe or MemTest86). 1 pass minimum.
  - Verify: BIOS shows 64GB; memtest reports 0 errors.

#### Part D: Below — Dual RTX 3090 FE + NVLink Bridge

**Deliverables:**

- [ ] Remove existing RTX 2080 Ti. Set aside.
- [ ] Install first RTX 3090 FE in **PCIEX16_1**. TWO SEPARATE 8-pin PCIe cables.
- [ ] Install second RTX 3090 FE in **PCIEX16_2** (3 slots below). TWO SEPARATE 8-pin cables.
- [ ] Install NVIDIA P3669 NVLink bridge — clip onto top edge of both cards.
- [ ] Cable management — keep airflow between cards clear.
- [ ] First boot. BIOS shows both GPUs.
- [ ] Boot Windows. Device Manager shows two RTX 3090 entries (DDU + clean install if not).
- [ ] `nvidia-smi` shows 24GB each. `nvidia-smi topo -m` shows `NV#` between GPU 0 and GPU 1.
- [ ] Temperature check: 5 minutes FurMark/3DMark. Both <83°C core.
  - Verify: `nvidia-smi topo -m` output saved as artifact.

#### Part E: Below — GPU Overclocking & Power Optimization

**Deliverables:**

- [ ] Install MSI Afterburner.
- [ ] Apply to BOTH GPUs (linked):
  - Power Limit: +15% / Core: +75 MHz / Memory: +300 MHz
  - Fan: 70% @65°C / 85% @75°C / 100% @80°C
  - Temp Limit: 85°C
- [ ] Save Profile 1. Enable "Start with Windows".
- [ ] Stability test: 1000 tokens × 10 runs on qwen3:8b. No garbled output.
- [ ] VRAM thermal: `nvidia-smi -q -d TEMPERATURE` Memory <100°C.
  - Verify: Afterburner profile screenshot + thermal log.

#### Part F: Jimmy Assembly

**Deliverables:**

- [ ] Open Jimmy panel. Install 64GB DDR5-5600 SODIMM kit + WD Blue SN5000 2TB NVMe (slot 1).
- [ ] Power on. BIOS verifies 64GB + 2TB. Enable XMP/EXPO.
- [ ] Install Ubuntu Server 24.04 LTS. Hostname `jimmy`. SSH server. Static IP `10.0.1.106`.
- [ ] SSH from Muddy works; `free -h` shows 64GB; `lsblk` shows 2TB.
  - Verify: `ssh byronhudson@10.0.1.106 'free -h && lsblk'` from Muddy.

#### Part G: Verification Checklist

- [ ] Below: 2× RTX 3090 detected, NVLink active, 48GB VRAM, 64GB RAM, 1200W PSU, BIOS updated, OC applied, stable.
- [ ] Jimmy: 64GB DDR5, 2TB NVMe, Ubuntu Server installed, SSH accessible, static IP.
- [ ] Old 2080 Ti: set aside.

#### Claude Review (mandatory before Phase 1 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: user uploads Part G verification artifacts → `/review --phase 1 --artifacts ./artifacts/phase-1/`
- Required findings: NVLink confirmed via `NV#`; PSU rating ≥1200W; 3090s thermally stable; Jimmy reachable; BIOS newer than v1302.
- Block-on: any artifact missing, NVLink shows `PHB`, sustained temps >83°C, or Jimmy unreachable.

#### Done When

- [ ] All 7 verification checklist items in Part G satisfied.
- [ ] Claude artifact review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 1: hardware install complete — Below dual-3090 NVLink, Jimmy online at 10.0.1.106`.

---

### Phase 2: Below Activation

**Status:** completed (2026-04-19T18:10Z) — 70B dual-GPU 18.01 tok/s, NVLink 4×14.062 GB/s, same-model residency hot-cache proven
**Codex model:** gpt-5.3-codex (terminal-heavy: SSH, Ollama config, shell scripts)
**Codex effort:** medium
**Worktree:** `worktrees/wave2-below`
**Blocked by:** Phase 0 (AGENTS.md), Phase 1 (hardware gate)
**Can parallelize:** Phase 3 + Phase 6

#### Goal

Dual 3090 NVLink operational, Ollama serving 70B models at ≥18 tok/s, existing scoring pipeline verified against upgraded hardware.

#### Context

**Files (touch only these):**

- `~/.buildrunner/scripts/below-verify.sh` (NEW)
- `~/.buildrunner/scripts/below-benchmark.sh` (NEW)
- `~/.buildrunner/config/ollama-below.env` (NEW)
- `core/cluster/node_inference.py` (MODIFY)
- `core/cluster/AGENTS.md.append-phase2.txt` (NEW — staged snippet; merged at Wave 2 end via `wave-merge.sh`)
- `~/.buildrunner/logs/below-benchmark.log` (NEW — output artifact)
- `~/.buildrunner/logs/below-activation.log` (NEW — output artifact)

**HARDWARE GATE:** Phase 1 Part G checklist passed.

#### Constraints

- IMPORTANT: Read `core/runtime/AGENTS.md` and `core/cluster/AGENTS.md` before any code edit.
- IMPORTANT: `node_inference.py` changes MUST keep existing single-GPU code path working.
- NEVER auto-pull Ollama models from `below-verify.sh`.
- NEVER hardcode Below's IP — read from `cluster.json`.

#### Deliverables

- [ ] `below-verify.sh` — SSH into Below; nvidia-smi checks: dual 3090, NVLink (`nvidia-smi topo -m` shows NV#), 48GB total VRAM. Above-4G-Decoding check is INDIRECT: confirms each GPU reports its full advertised VRAM via `nvidia-smi --query-gpu=memory.total --format=csv,noheader,nounits` (24576 MiB per card). Short reads = Above 4G Decoding off → exit 1 with explicit error. CUDA driver presence. Exit codes: 0 pass / 1 critical / 2 warning.
  - Verify: `~/.buildrunner/scripts/below-verify.sh; echo $?` returns 0. `shellcheck` passes. Output cross-references the Phase 1 `phase-1-display-pnp.txt` artifact for BIOS provenance.
- [ ] `ollama-below.env` — `OLLAMA_FLASH_ATTENTION=1`, `OLLAMA_KEEP_ALIVE=24h`, `OLLAMA_NUM_PARALLEL=4`, `OLLAMA_HOST=0.0.0.0:11434`, `CUDA_VISIBLE_DEVICES=0,1`. **`KEEP_ALIVE=24h` is mandatory** — the Overview promises `llama3.3:70b` and `qwen3:8b` co-resident with no permanent swapping. `KEEP_ALIVE=0` would unload models immediately and contradict that contract; `deepseek-r1:70b` swap-on-demand is handled explicitly via the `model-update.sh` and adversarial-review dispatch paths, not via Ollama auto-eviction.
  - Verify: `ssh below 'systemctl show ollama -p Environment'` includes all 5 vars; `KEEP_ALIVE` value is `24h` not `0`.
- [ ] Deploy Ollama with env file. Listens on 0.0.0.0:11434.
  - Verify: `curl http://10.0.1.105:11434/api/tags` returns 200.
- [ ] Pull models: `qwen3:8b`, `llama3.3:70b-instruct-q4_K_M`, `deepseek-r1:70b-q4_K_M`, `nomic-embed-text`.
  - Verify: `ssh below 'ollama list'` shows all 4 models.
- [ ] **Residency proof** — back-to-back call test: invoke `llama3.3:70b` (prompt A), then `qwen3:8b` (prompt B), then `llama3.3:70b` again (prompt C). Between calls, snapshot `nvidia-smi --query-compute-apps=pid,process_name,used_memory --format=csv` AND `curl http://10.0.1.105:11434/api/ps` (Ollama's loaded-model query). Both `llama3.3:70b` and `qwen3:8b` MUST appear in `/api/ps` after call C with `expires_at` in the future. Cold reload of llama between A and C = test fails.
  - Verify: `python scripts/test_residency.py --node below --models llama3.3:70b,qwen3:8b` returns `{"both_resident": true, "cold_reload_count": 0}`.
- [ ] `below-benchmark.sh` — tok/s benchmarks across THREE configurations to make the NVLink speedup claim measurable: (1) **single-GPU baseline** (`CUDA_VISIBLE_DEVICES=0` only, llama3.3:70b @ q4_K_M with offload to CPU for the half that does not fit — measures the no-NVLink path); (2) **dual-GPU + NVLink** (`CUDA_VISIBLE_DEVICES=0,1`, NVLink active); (3) **8B dual-GPU pipeline** (qwen3:8b). Targets: 70B dual-GPU 18-25 tok/s; 8B 80-120 tok/s; NVLink speedup = `dual_toks / single_toks` ≥ 1.30. Outputs structured JSON: `{single_gpu_70b_toks, dual_gpu_70b_toks, qwen8b_toks, nvlink_speedup}`.
  - Verify: `jq '.dual_gpu_70b_toks >= 18 and .nvlink_speedup >= 1.3' below-benchmark.log` returns `true`.
- [ ] Update `node_inference.py` — GPU 1→2, VRAM 11→48GB, NVLink flag, dual-GPU pipeline parallelism.
  - Verify: `pytest tests/cluster/test_node_inference.py -x`. `ruff check core/cluster/node_inference.py`.
- [ ] **AGENTS.md staged snippet** — write to `core/cluster/AGENTS.md.append-phase2.txt`: NVLink detection rule (require `NV#` in topo before declaring dual-GPU healthy); single-GPU code path is preserved fallback; `KEEP_ALIVE=24h` residency contract for the two co-resident models. ≤300 staged bytes. Direct edits to `core/cluster/AGENTS.md` are FORBIDDEN in this phase — Wave 2 merge gate applies the snippet.
  - Verify: `wc -c core/cluster/AGENTS.md.append-phase2.txt` ≤300; `grep -c "NVLink\|NV#\|KEEP_ALIVE" core/cluster/AGENTS.md.append-phase2.txt` ≥2.
- [ ] Smoke test — `intel_scoring.py` scores 5 deal items; results match expected JSON shape.
  - Verify: `python scripts/test_intel_scoring.py --count 5 --node below | jq 'all(.score >= 0 and .score <= 100)'` returns `true`.

#### Claude Review (mandatory before Phase 2 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 2 --target "core/cluster/node_inference.py,core/cluster/AGENTS.md.append-phase2.txt,~/.buildrunner/scripts/below-*.sh,~/.buildrunner/config/ollama-below.env"`
- Required findings: (1) `node_inference.py` preserves single-GPU path; (2) shell scripts pass `shellcheck`; (3) NVLink detection correct; (4) no hardcoded IPs; (5) 70B dual-GPU benchmark ≥18 tok/s AND NVLink speedup ≥1.30 vs single-GPU baseline; (6) residency proof shows both `llama3.3:70b` and `qwen3:8b` co-resident with `KEEP_ALIVE=24h`; (7) staged AGENTS.md snippet exists and is within budget. Wave-merge gate (NOT this phase) applies the snippet to `core/cluster/AGENTS.md`.
- Block-on: regression in single-GPU path, hardcoded IP, benchmark below threshold, missing NVLink speedup, residency cold-reload during proof, staged snippet missing or oversized, direct edit to `core/cluster/AGENTS.md` (must be staged).

#### Done When

- [ ] All deliverable verification commands pass.
- [ ] AGENTS.md updated and reviewed for this scope.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 2: Below activated — 70B at N tok/s, NVLink confirmed, AGENTS.md updated`.

---

### Phase 3: Jimmy Activation

**Status:** ✅ COMPLETE (2026-04-20T21:59Z) — 3 systemd services active+enabled on Jimmy (semantic:8100, intel:8101, staging:8200), br3-git-mirrors.timer active (hourly); /srv/jimmy/ layout fully provisioned (11 subdirs); UFW active with 22/8100/8101/8200/4400/4500 open, 11434 confirmed closed; Lockwood data migrated to /srv/jimmy/{lancedb,memory}; 26 git mirrors cloned under /srv/jimmy/backups/git-mirrors/; nightly backup LaunchAgent loaded on Muddy; AGENTS.md deployed (sha256 match); passwordless sudo configured for byronhudson.
**Codex model:** gpt-5.3-codex
**Codex effort:** medium
**Worktree:** `worktrees/wave2-msa2`
**Blocked by:** Phase 0, Phase 1
**Can parallelize:** Phase 2 + Phase 6

#### Goal

Jimmy running all Lockwood + Lomax services on systemd, data migrated, all endpoints responding identically. Jimmy AGENTS.md deployed at `~/AGENTS.md` so Codex on Jimmy has scoped rules.

#### Context

**Files (touch only these):**

- `~/.buildrunner/scripts/jimmy-bootstrap.sh` (NEW)
- `~/.buildrunner/scripts/jimmy-storage-init.sh` (NEW — provisions `/srv/jimmy/` layout)
- `~/.buildrunner/scripts/nightly-projects-backup.sh` (NEW — Muddy-side, rsync --link-dest to Jimmy)
- `~/.buildrunner/scripts/git-mirrors-sync.sh` (NEW — Jimmy-side hourly `git fetch --all` across bare clones)
- `~/.buildrunner/scripts/migrate-lockwood-data.sh` (NEW)
- `~/.buildrunner/scripts/jimmy-verify.sh` (NEW)
- `~/.buildrunner/agents-md/jimmy.md` (DEPLOY → `~/AGENTS.md` on Jimmy)
- `core/cluster/AGENTS.md.append-phase3.txt` (NEW — staged snippet; merged at Wave 2 end)
- systemd units on Jimmy: `/etc/systemd/system/br3-{semantic,intel,staging,git-mirrors}.service|.timer` (NEW)
- systemd units on Muddy: `/etc/systemd/system/br3-nightly-backup.service|.timer` (NEW — 03:00 nightly)
- `~/.buildrunner/logs/jimmy-activation.log` (NEW — output artifact)

**HARDWARE GATE:** Phase 1 Part F checklist passed.

#### Constraints

- IMPORTANT: Old Lockwood (10.0.1.101) MUST stay online during migration.
- IMPORTANT: Deploy Jimmy AGENTS.md to `~/AGENTS.md` on Jimmy BEFORE running any Codex task on that host.
- NEVER `rm` source data on Lockwood — copy only.
- NEVER expose Ollama port (11434) on Jimmy.

#### Deliverables

- [ ] `jimmy-bootstrap.sh` — apt installs (python3, python3-venv, node 22, npm, git, rsync, build-essential, sqlite3); SSH key deploy; firewall opens 8100 (semantic), 8200 (staging), 4400 (dashboard), 4500 (gateway). Port 11434 (Ollama) MUST stay closed on Jimmy (Below is the only Ollama host).
  - Verify: `ssh jimmy 'systemctl is-active ssh && command -v python3 node sqlite3 && sudo ufw status | grep -E "8100|8200|4400|4500"'` succeeds and shows all 4 ports open. `ssh jimmy 'sudo ufw status | grep 11434'` returns nothing.
- [ ] Deploy BR3 codebase to `~/repos/BuildRunner3` on Jimmy; venv + pip install.
  - Verify: `ssh jimmy 'cd ~/repos/BuildRunner3 && .venv/bin/python -c "import fastapi, lancedb, httpx"'` exits 0.
- [ ] Deploy `node_semantic.py` as `br3-semantic.service`. uvicorn port 8100. LanceDB + embedding models loaded.
  - Verify: `curl http://10.0.1.106:8100/api/search?q=test` returns 200.
- [ ] Deploy `node_intelligence.py` as `br3-intel.service`. 5 background crons. Env vars set.
  - Verify: `ssh jimmy 'systemctl is-active br3-intel'` returns `active`.
- [ ] Deploy `node_staging.py` as `br3-staging.service`. Preview deploy + build validation.
  - Verify: `curl http://10.0.1.106:8200/health` returns 200.
- [ ] `migrate-lockwood-data.sh` — rsync `~/.lockwood/` from 10.0.1.101 → Jimmy. Row counts match across LanceDB tables, `memory.db`, `intel.db`.
  - Verify: `python scripts/compare_lockwood_msa2_rows.py` returns 0 row diffs.
- [ ] **Deploy Jimmy AGENTS.md** — `scp ~/.buildrunner/agents-md/jimmy.md byronhudson@10.0.1.106:~/AGENTS.md`. Verify byte-for-byte.
  - Verify: `ssh jimmy 'sha256sum ~/AGENTS.md'` matches `sha256sum ~/.buildrunner/agents-md/jimmy.md`.
- [ ] **AGENTS.md staged snippet** — write to `core/cluster/AGENTS.md.append-phase3.txt`: Linux node dispatch rule (rsync, not tar+scp); systemd unit naming convention `br3-*.service`; Jimmy port allocation (8100/8200/4400/4500). ≤300 staged bytes. Direct edits to `core/cluster/AGENTS.md` FORBIDDEN — Wave 2 merge gate applies.
  - Verify: `wc -c core/cluster/AGENTS.md.append-phase3.txt` ≤300; `grep -c "br3-\|systemd\|rsync\|8200" core/cluster/AGENTS.md.append-phase3.txt` ≥3.
- [ ] `jimmy-storage-init.sh` — provisions `/srv/jimmy/` with all subdirectories per the Jimmy Storage Layout table above. Sets ownership (`byronhudson:byronhudson`), mode 0750, SELinux/AppArmor labels if applicable.
  - Verify: `ssh jimmy 'test -d /srv/jimmy/research-library && test -d /srv/jimmy/lancedb && test -d /srv/jimmy/memory && test -d /srv/jimmy/backups/projects && test -d /srv/jimmy/backups/buildrunner-state && test -d /srv/jimmy/backups/git-mirrors && test -d /srv/jimmy/backups/supabase && test -d /srv/jimmy/backups/brlogger && test -d /srv/jimmy/archive/adversarial-reviews && test -d /srv/jimmy/archive/cost-ledger && test -d /srv/jimmy/archive/lockwood-pre-migration'` exits 0.
- [ ] `nightly-projects-backup.sh` (on **Muddy**) — `rsync -aHAXv --delete --link-dest=../$(cat /srv/jimmy/backups/projects/LATEST 2>/dev/null || echo 0000-00-00) --exclude-from=~/.buildrunner/config/backup-excludes.list ~/Projects/ byronhudson@10.0.1.106:/srv/jimmy/backups/projects/$(date -u +%Y-%m-%d)/`. On success, update `LATEST` pointer and write `manifest.sha256`. Exit non-zero on rsync error or snapshot <80% of prior night (unless `.backupignore` diff accounts for it).
  - Verify: Dry-run `bash -x ~/.buildrunner/scripts/nightly-projects-backup.sh --dry-run` shows full tree scan and planned snapshot path; `ls /srv/jimmy/backups/projects/` shows dated directory after non-dry run; `ls /srv/jimmy/backups/projects/<date>/manifest.sha256` exists.
- [ ] `br3-nightly-backup.timer` on Muddy — `OnCalendar=*-*-* 03:00:00`, `Persistent=true`, `RandomizedDelaySec=300`. Enabled and started.
  - Verify: `systemctl is-enabled br3-nightly-backup.timer && systemctl list-timers br3-nightly-backup.timer | grep -E "03:00"` succeeds.
- [ ] `backup-excludes.list` — `node_modules/`, `.venv/`, `venv/`, `dist/`, `build/`, `target/`, `.next/`, `.turbo/`, `.cache/`, `*.sock`, `.DS_Store`, any line starting with `#` ignored.
  - Verify: `test $(wc -l < ~/.buildrunner/config/backup-excludes.list) -ge 8`.
- [ ] `git-mirrors-sync.sh` on **Jimmy** — for each dir in `~/Projects/` on Muddy (discovered via `ssh muddy 'ls -d ~/Projects/*/.git'`), maintain a bare mirror at `/srv/jimmy/backups/git-mirrors/<repo>.git`. `br3-git-mirrors.timer` fires hourly (`OnCalendar=hourly`, `Persistent=true`).
  - Verify: `ssh jimmy 'ls /srv/jimmy/backups/git-mirrors/*.git | wc -l'` ≥ number of git repos in `~/Projects/`; `ssh jimmy 'cd /srv/jimmy/backups/git-mirrors/BuildRunner3.git && git log --oneline -1'` returns the latest BR3 commit.
- [ ] `jimmy-verify.sh` — all endpoints 200; SessionStart brief structurally identical to old Lockwood; semantic search returns relevant results; intel scoring cron fires + connects to Below; reboot test passes; storage layout exists; nightly-backup timer active on Muddy; git-mirrors timer active on Jimmy.
  - Verify: `~/.buildrunner/scripts/jimmy-verify.sh; echo $?` returns 0.

#### Claude Review (mandatory before Phase 3 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 3 --target "~/.buildrunner/scripts/jimmy-*.sh,~/.buildrunner/scripts/nightly-projects-backup.sh,~/.buildrunner/scripts/git-mirrors-sync.sh,~/.buildrunner/scripts/migrate-lockwood-data.sh,~/.buildrunner/config/backup-excludes.list,~/.buildrunner/agents-md/jimmy.md,core/cluster/AGENTS.md.append-phase3.txt"`
- Required findings: (1) Jimmy AGENTS.md deployed and matches staged copy byte-for-byte; (2) old Lockwood untouched; (3) all systemd services (semantic, intel, staging, git-mirrors on Jimmy; nightly-backup on Muddy) survive reboot; (4) row-count parity post-migration; (5) firewall opens all 4 service ports (8100/8200/4400/4500) AND keeps 11434 closed; (6) `curl http://10.0.1.106:8200/health` from Muddy returns 200; (7) `/srv/jimmy/` storage layout fully provisioned; (8) `br3-nightly-backup.timer` active on Muddy with correct 03:00 schedule + Persistent=true; (9) `br3-git-mirrors.timer` active on Jimmy; (10) dry-run of nightly backup produces plausible snapshot plan and manifest; (11) staged AGENTS.md snippet within budget.
- Block-on: any service fails reboot test, row-count drift, AGENTS.md not deployed, old Lockwood data modified, port 8200 unreachable, direct edit to `core/cluster/AGENTS.md` (must be staged), storage layout incomplete, nightly-backup timer missing or misscheduled, git-mirrors timer missing, backup-excludes.list missing or empty.

#### Done When

- [ ] All deliverable verification commands pass.
- [ ] First nightly backup runs successfully; `/srv/jimmy/backups/projects/<today>/` exists with manifest.
- [ ] Git mirrors populated for every repo in `~/Projects/`.
- [ ] AGENTS.md updated and reviewed (both Jimmy deployment + `core/cluster/AGENTS.md` append).
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 3: Jimmy activated — services live, row parity, /srv/jimmy/ provisioned, nightly backup of ~/Projects scheduled, AGENTS.md deployed`.

---

### Phase 4: Cluster Reconfiguration — 7 Workers

**Status:** ✅ COMPLETE (2026-04-20) — 7 workers live: Jimmy (10.0.1.106) added as primary semantic-search/intel/staging; Below spec updated to dual 3090 NVLink 48GB; Lockwood+Lomax retained as overflow workers; node-matrix.mjs returns 7 ranked (otis>below>jimmy>lockwood>lomax>muddy>walter); is_overflow_worker() + is_linux_node() helpers in \_dispatch-core.sh; 34 remaining 10.0.1.101 refs overflow-classified; AGENTS.md.append-phase4.txt staged (379 bytes).
**Codex model:** gpt-5.4
**Codex effort:** low
**Worktree:** `worktrees/wave3-cluster`
**Blocked by:** Phase 0, Phase 2, Phase 3
**Can parallelize:** Phase 7 + Phase 8

#### Goal

All 7 nodes registered as build workers, hardcoded IPs updated, dispatch works to every node including Linux.

#### Context

**Files (touch only these — discoverable via grep, ~20 total):**

- `~/.buildrunner/cluster.json`
- `~/.buildrunner/scripts/node-matrix.mjs`
- `~/.buildrunner/scripts/dispatch-to-node.sh`, `_dispatch-core.sh`
- `~/.buildrunner/scripts/events.mjs`
- `~/.buildrunner/scripts/ssh-warmup.sh`
- `~/.buildrunner/scripts/br-token-refresh.sh`
- `core/cluster/AGENTS.md.append-phase4.txt` (NEW — staged snippet; merged at Wave 3 end)
- ~14 additional files surfaced by grep (Deliverable 1)

**Note:** All `~/.buildrunner/` files live OUTSIDE the git repo at `$HOME/.buildrunner/`.

#### Constraints

- IMPORTANT: Additive only — DO NOT remove Lockwood (10.0.1.101) or Lomax (10.0.1.104); they remain as overflow workers.
- IMPORTANT: The hardcoded-IP rewrite is **role-scoped**, not blanket. Only PRIMARY-role references (semantic-search, intel, staging) for Lockwood are rewritten to Jimmy (10.0.1.106). OVERFLOW-role and worker-pool references for Lockwood (10.0.1.101) MUST be preserved in `cluster.json`, `node-matrix.mjs`, `dispatch-to-node.sh`, `ssh-warmup.sh`, and any health/heartbeat surface. The `is_overflow_worker(node)` helper (added in Deliverable 5b) is the single classifier the rewrite respects.
- IMPORTANT: Run grep BEFORE editing — produce the full list as Deliverable 1.
- NEVER touch `cluster.json` schema fields not listed in Deliverables.

#### Deliverables

- [ ] **Discovery grep** — produce canonical hit list:
  - Verify: `grep -rl "10.0.1.101\|10.0.1.104" ~/.buildrunner/ core/cluster/ > /tmp/phase4-targets.txt && wc -l /tmp/phase4-targets.txt` returns the full count (~20).
- [ ] `cluster.json` — add Jimmy node (`roles: [semantic-search, staging-server, parallel-builder]`, `platform: "linux"`); update Below spec; mark Lockwood + Lomax as overflow.
  - Verify: `jq '.nodes | map(select(.name == "jimmy")) | length' ~/.buildrunner/cluster.json` returns 1.
- [ ] `node-matrix.mjs` — 7 workers ranked by health + load. Priority: otis, below, jimmy, lockwood, lomax, muddy, walter.
  - Verify: `node ~/.buildrunner/scripts/node-matrix.mjs --dry-run | jq 'length'` returns 7.
- [ ] `dispatch-to-node.sh` + `_dispatch-core.sh` — add `is_linux_node()` for Jimmy (rsync vs tar+scp).
  - Verify: `bash ~/.buildrunner/scripts/dispatch-to-node.sh --dry-run --node jimmy --task ping` exits 0.
- [ ] **`is_overflow_worker(node)` helper** — single classifier in `~/.buildrunner/scripts/_dispatch-core.sh` returning true for Lockwood + Lomax post-Phase-3, false for primary roles. Used by every rewrite to skip overflow paths.
  - Verify: `bash -c 'source ~/.buildrunner/scripts/_dispatch-core.sh && is_overflow_worker lockwood && is_overflow_worker lomax && ! is_overflow_worker otis'` exits 0.
- [ ] Hardcoded-IP rewrite — every file in `/tmp/phase4-targets.txt`. **Only PRIMARY-role Lockwood references** rewrite to Jimmy (semantic-search endpoints, intel cron targets, staging deploys). OVERFLOW-role + worker-pool + heartbeat references retain Lockwood's IP. Add Jimmy to node lists. The rewrite tool consults `is_overflow_worker()` for every match before substituting.
  - Verify: `grep -rn "10.0.1.101" ~/.buildrunner/ core/cluster/ > /tmp/phase4-remaining-101.txt`; every remaining reference must be in an overflow-pool / heartbeat / cluster.json context — `python scripts/audit_overflow_refs.py /tmp/phase4-remaining-101.txt` exits 0 (audits each remaining hit is overflow-classified).
- [ ] **Overflow dispatch smoke** — `bash ~/.buildrunner/scripts/dispatch-to-node.sh --dry-run --node lockwood --task echo` exits 0; `node ~/.buildrunner/scripts/node-matrix.mjs --include-overflow | jq 'map(select(.name == "lockwood")) | length'` returns 1.
- [ ] **AGENTS.md staged snippet** — write to `core/cluster/AGENTS.md.append-phase4.txt`: 7-node priority order (otis > below > jimmy > lockwood > lomax > muddy > walter); overflow workers explicitly named (lockwood, lomax) with the role-scoped rewrite rule. ≤400 staged bytes. Direct edits to `core/cluster/AGENTS.md` FORBIDDEN — Wave 3 merge gate applies.
  - Verify: `wc -c core/cluster/AGENTS.md.append-phase4.txt` ≤400; `grep -c "otis\|below\|jimmy\|lockwood\|lomax\|muddy\|walter" core/cluster/AGENTS.md.append-phase4.txt` ≥7.
- [ ] Smoke test — SessionStart brief from Jimmy; dispatch dry-run to all 7.
  - Verify: `~/.buildrunner/scripts/cluster-check.sh all --dry-run` reports all 7 reachable.

#### Claude Review (mandatory before Phase 4 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 4 --target "/tmp/phase4-targets.txt,core/cluster/AGENTS.md.append-phase4.txt,~/.buildrunner/scripts/_dispatch-core.sh"`
- Required findings: (1) every file in hit list touched OR explicitly excluded with reason; (2) Lockwood + Lomax preserved as overflow workers (overflow dispatch smoke passes); (3) `is_linux_node()` correctly branches; (4) `is_overflow_worker()` correctly classifies; (5) every remaining `10.0.1.101` reference is in overflow context (audit script passes); (6) no schema regression in `cluster.json`; (7) staged AGENTS.md snippet exists with 7-node priority + overflow rule.
- Block-on: any file missed without exclusion, schema drift, Lockwood/Lomax removed from any worker pool, primary-role rewrite that broke overflow dispatch, audit script flags non-overflow `10.0.1.101` ref, direct edit to `core/cluster/AGENTS.md`.

#### Done When

- [ ] `cluster-check.sh` returns correct URLs for all 7 nodes.
- [ ] AGENTS.md updated and reviewed for this scope.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 4: 7-worker cluster live — Jimmy added, overflow retained, AGENTS.md updated`.

---

### Phase 5: Below Skill Integration

**Status:** ✅ COMPLETE (2026-04-20) — below-route.sh live (llama3.3:70b default, qwen3:8b for summarization), BR3_LOCAL_ROUTING gate on every entry point; 8 skills routed (begin/autopilot/review/guard/diag/root/dbg/sdb) with Below firewall (never drafts final output); adversarial-review.sh.patch-phase5 staged (--local flag); AGENTS.md.append-phase5.txt 597 bytes with 5-row routing table.
**Codex model:** gpt-5.4
**Codex effort:** medium
**Worktree:** `worktrees/wave4-skills`
**Blocked by:** Phase 0, Phase 4
**Can parallelize:** Phase 9, Phase 10

#### Goal

Below 70B wired into the skill pipeline as default first choice for verified work via a hardcoded routing table. Every routing decision logged to `decisions.log`.

**Routing rule (hardcoded in below-route.sh):**

- First pass / draft / structural check → Below (`llama3.3:70b`)
- Log/diff/spec pre-summarization → Below (`qwen3:8b`)
- Implementation / final quality review / frontend / architecture → Claude (Muddy)
- Diagnosis (`/diag`, `/root`, `/dbg`, `/sdb`) → Opus 4.7 with ultrathink on `/diag`+`/root`; Below `qwen3:8b` pre-summarizes raw logs
- Greenfield code / DevOps / 2nd adversarial voice → Codex (gpt-5.4)
- Below offline → Claude (graceful fallback, NO user-visible error)

#### Context

**Files (touch only these):**

- `~/.buildrunner/scripts/below-route.sh` (NEW)
- `~/.claude/commands/begin.md` (MODIFY)
- `~/.claude/commands/autopilot.md` (MODIFY)
- `~/.claude/commands/review.md` (MODIFY)
- `~/.claude/commands/guard.md` (MODIFY)
- `~/.claude/commands/diag.md`, `root.md`, `dbg.md`, `sdb.md` (MODIFY)
- `~/.buildrunner/scripts/adversarial-review.sh.patch-phase5` (NEW — staged unified diff adding `--local`; merged at Wave 4 end)
- `core/cluster/AGENTS.md.append-phase5.txt` (NEW — staged snippet; merged at Wave 4 end)

#### Constraints

- IMPORTANT: Read `core/cluster/AGENTS.md` (quality firewall) before editing any skill .md file.
- IMPORTANT: Below NEVER drafts final diagnoses, final code, frontend, or architecture.
- IMPORTANT: All new behavior gated behind `BR3_LOCAL_ROUTING=on` (default OFF until Phase 13).
- NEVER add a separate `inference-router.mjs` — routing decision lives inline in each skill.

#### Deliverables

- [ ] `below-route.sh` — checks Below health; calls Ollama `/api/chat` with prompt + model (default `llama3.3:70b`); returns to stdout. Exit code 2 on offline/malformed. 30s timeout.
  - Verify: `~/.buildrunner/scripts/below-route.sh --model qwen3:8b "Echo OK"` returns "OK"; `shellcheck` passes.
- [ ] `/begin` update — `below-route.sh` for backend/infra plan drafts; Claude for frontend/fullstack/architecture; routing decision logged.
  - Verify: dry-run `/begin` writes a `routing:` line to `decisions.log` per phase.
- [ ] `/autopilot` update — simple phases (backend, ≤3 deliverables, no UI) → Below in `go` mode; complex → Claude.
  - Verify: `pytest tests/skills/test_autopilot_classifier.py -x`.
- [ ] `/review` update — Pass 1 structural via `below-route.sh`; Pass 2 quality via Claude. Fallback: Explore subagents.
  - Verify: end-to-end `/review` on known-good PR produces both passes.
- [ ] `/guard` update — governance via `below-route.sh`. Skip if Below offline.
  - Verify: `/guard --dry-run` on this BUILD reports rule check.
- [ ] `/diag`, `/root`, `/dbg`, `/sdb` update — Below `qwen3:8b` summarizes raw log → Opus 4.7 (ultrathink on `/diag`+`/root`) diagnoses. Below NEVER drafts diagnosis.
  - Verify: `/diag` on synthetic 50KB log produces diagnosis with ≤4KB context to Opus.
- [ ] **`adversarial-review.sh --local` (staged patch)** — write `~/.buildrunner/scripts/adversarial-review.sh.patch-phase5` as a `git diff -U3` against current `adversarial-review.sh` adding `--local` flag (routes through Below 70B; fallback: Otis if Below offline). Direct edits to `adversarial-review.sh` FORBIDDEN — Wave 4 merge gate applies the patch in phase order (Phase 5 before Phase 9).
  - Verify: `git apply --check ~/.buildrunner/scripts/adversarial-review.sh.patch-phase5` exits 0; `bash <(git apply --3way --output=- ~/.buildrunner/scripts/adversarial-review.sh.patch-phase5 < ~/.buildrunner/scripts/adversarial-review.sh) --local --target tests/fixtures/buggy.py --dry-run` returns valid findings JSON shape.
- [ ] **AGENTS.md staged snippet** — write to `core/cluster/AGENTS.md.append-phase5.txt`: full routing table (5 rows); `BR3_LOCAL_ROUTING` flag-gate rule. ≤600 staged bytes. Direct edits to `core/cluster/AGENTS.md` FORBIDDEN — Wave 4 merge gate applies.
  - Verify: `wc -c core/cluster/AGENTS.md.append-phase5.txt` ≤600; `grep -c "below-route\|llama3.3\|qwen3" core/cluster/AGENTS.md.append-phase5.txt` ≥3.

#### Claude Review (mandatory before Phase 5 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 5 --target "~/.buildrunner/scripts/below-route.sh,~/.claude/commands/{begin,autopilot,review,guard,diag,root,dbg,sdb}.md,core/cluster/AGENTS.md.append-phase5.txt,~/.buildrunner/scripts/adversarial-review.sh.patch-phase5"`
- Required findings: (1) firewall preserved — Below never produces final outputs; (2) `BR3_LOCAL_ROUTING` honored on every entry point; (3) every fallback tested; (4) routing decisions logged; (5) staged AGENTS.md snippet routing table matches code; (6) staged adversarial-review patch applies cleanly and only adds `--local`.
- Block-on: skill that lets Below produce final output, missing flag gate, untested fallback, missing log line, staged AGENTS.md drift from code, patch fails `git apply --check`, direct edits to `adversarial-review.sh` or `core/cluster/AGENTS.md`.

#### Done When

- [ ] All deliverable verification commands pass.
- [ ] AGENTS.md updated and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 5: Below skill integration — 8 skills routed, firewall enforced, AGENTS.md updated`.

---

### Phase 6: Runtime Registry Extension (OllamaRuntime)

**Status:** ✅ COMPLETE (2026-04-20) — OllamaRuntime registered, 16 tests pass, silent fallback verified, AGENTS.md updated
**Codex model:** gpt-5.4
**Codex effort:** medium
**Worktree:** `worktrees/wave2-runtime`
**Blocked by:** Phase 0
**Can parallelize:** Phase 2, Phase 3

#### Goal

Extend the existing `core/runtime/` abstraction so Below/Ollama is a first-class runtime alongside Claude and Codex.

#### Context

**Files (touch only these):**

- `core/runtime/config.py` (MODIFY — add `"ollama"` to `SUPPORTED_RUNTIMES`)
- `core/runtime/runtime_registry.py` (MODIFY — register OllamaRuntime)
- `core/runtime/ollama_runtime.py` (NEW)
- `core/runtime/command_capabilities.json` (MODIFY — add `local_ready` capability)
- `core/runtime/AGENTS.md` (MODIFY — document OllamaRuntime + `local_ready`)
- `tests/runtime/test_ollama_runtime.py` (NEW)

#### Constraints

- IMPORTANT: Read `core/runtime/AGENTS.md` first.
- IMPORTANT: Existing Claude + Codex paths MUST stay byte-identical.
- IMPORTANT: On Ollama 503, fall back to Claude SILENTLY.
- NEVER add an Ollama-specific code path outside `ollama_runtime.py` (registry pattern only).

#### Deliverables

- [ ] Add `"ollama"` to `SUPPORTED_RUNTIMES` in `core/runtime/config.py`.
  - Verify: `pytest tests/runtime/test_config.py -x`; `ruff check core/runtime/config.py`.
- [ ] Implement `OllamaRuntime(BaseRuntime)` — `execute(task) -> RuntimeResult` posts to Ollama `/api/chat` (default `llama3.3:70b`); health check via `cluster-check.sh inference`.
  - Verify: `pytest tests/runtime/test_ollama_runtime.py -x`; `ruff check core/runtime/ollama_runtime.py`.
- [ ] Register in `create_runtime_registry()`. Claude remains default.
  - Verify: `python -c "from core.runtime.runtime_registry import create_runtime_registry; print(create_runtime_registry().get('ollama').name)"` prints `ollama`.
- [ ] Extend `command_capabilities.json` with `local_ready`. Tag: `plan-draft`, `structural-review`, `governance-lint`, `intel-scoring`, `summarize`.
  - Verify: `jq '.capabilities | keys | length' core/runtime/command_capabilities.json` returns 4.
- [ ] Graceful fallback on health-check failure → Claude. No user-visible error.
  - Verify: `pytest tests/runtime/test_ollama_runtime.py::test_fallback_on_503 -x` passes.
- [ ] `tests/runtime/test_ollama_runtime.py` — construction, health, `execute()` success, fallback on 503.
  - Verify: `pytest tests/runtime/test_ollama_runtime.py -x --tb=short` all pass.
- [ ] **AGENTS.md update** — append to `core/runtime/AGENTS.md`: OllamaRuntime contract; `local_ready` capability semantics; silent-fallback rule. ≤400 added bytes.
  - Verify: `grep -c "OllamaRuntime\|local_ready" core/runtime/AGENTS.md` ≥2.

#### Claude Review (mandatory before Phase 6 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 6 --target "core/runtime/*.py,core/runtime/command_capabilities.json,core/runtime/AGENTS.md,tests/runtime/test_ollama_runtime.py"`
- Required findings: (1) `BaseRuntime` contract honored; (2) silent fallback confirmed; (3) Claude/Codex unchanged; (4) `local_ready` additive; (5) tests cover all 4 cases; (6) AGENTS.md updated.
- Block-on: contract violation, user-visible 503 error, regression, missing test cases, AGENTS.md stale.

#### Done When

- [ ] `RuntimeRegistry.get("ollama").execute(task)` returns valid `RuntimeResult` against Below.
- [ ] All tests in `tests/runtime/` pass.
- [ ] AGENTS.md updated and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 6: OllamaRuntime registered — local_ready capability live, fallback verified, AGENTS.md updated`.

---

### Phase 7: LiteLLM Gateway + Cost/Cache Observability on Jimmy

> **SUPERSEDED by Final Decisions Override (see top of file):** LiteLLM is DROPPED. Replace this phase with implementation of the `RuntimeRegistry.execute()` shim (`core/runtime/runtime_registry.py`) as the ONLY local-model dispatch path, enforced by the pre-commit hook that rejects direct `ollama`, `requests.post("http://10.0.1.*")`, and raw `curl` calls to cluster nodes. Cost/cache observability (token counts, cache-hit rate, per-model spend) is implemented inside the shim and written to `/srv/jimmy/ledger/cost.jsonl`. The Codex proxy, budget guards, and dashboard wiring below remain relevant — retarget them at the RuntimeRegistry shim instead of LiteLLM. Autopilot: skip the LiteLLM install/config steps, implement the shim + pre-commit enforcement, preserve the observability deliverables. Original content retained below for historical context only.

**Status:** ✅ COMPLETE (2026-04-20) — SUPERSEDED path shipped: RuntimeRegistry.execute() + execute_async() is sole dispatch path, cache_control passed verbatim, BR3_GATEWAY-gated cost ledger emit (best-effort, never raises); CostLedger with exact 11-field JSONL schema writing to /srv/jimmy/ledger/ with weekly rotation + local fallback; /cluster/cost (24h+7d) and /cluster/cache (hit-rate/runtime) endpoints; pre-commit cluster-guard hook rejects direct ollama/requests/curl calls to cluster IPs; BR3_GATEWAY flag default OFF (flipped Phase 13); AGENTS.md.append-phase7.txt 597 bytes with "11 fields" literal; 24 new tests pass (8 ledger + 16 shim) + 66 existing runtime tests green; LiteLLM NOT installed; gateway_client.py deliverable dropped per Phase 8 note.
**Codex model:** gpt-5.4
**Codex effort:** medium
**Worktree:** `worktrees/wave3-gateway`
**Blocked by:** Phase 0, Phase 3, Phase 6
**Can parallelize:** Phase 4, Phase 8

#### Goal

One HTTP endpoint on Jimmy fronts all LLM calls. Every call logged with model, tokens in/out, cached tokens, cost, latency.

#### Context

**Files (touch only these):**

- `~/.buildrunner/config/litellm.yaml` on Jimmy (NEW)
- `/etc/systemd/system/br3-gateway.service` on Jimmy (NEW)
- `core/cluster/gateway_client.py` (NEW)
- `core/cluster/cost_ledger.py` (NEW)
- `api/routes/cluster_metrics.py` (MODIFY)
- `core/cluster/AGENTS.md.append-phase7.txt` (NEW — staged snippet; merged at Wave 3 end)

#### Constraints

- IMPORTANT: All gateway behavior gated behind `BR3_GATEWAY=on` (default OFF until Phase 13).
- IMPORTANT: `cache_control` headers passed through verbatim.
- NEVER write secrets to `litellm.yaml` — read from env.

#### Deliverables

- [ ] Install LiteLLM on Jimmy in dedicated venv. Routes: claude (Anthropic passthrough), ollama (`http://10.0.1.105:11434`), codex (codex-bridge).
  - Verify: `ssh jimmy 'systemctl is-active br3-gateway'` returns `active`.
- [ ] `br3-gateway.service` systemd unit, port 4500, enabled on boot. `/health` returns 200.
  - Verify: `curl http://10.0.1.106:4500/health` returns 200.
- [ ] `gateway_client.py` — `call(task)` posts to Jimmy:4500 `/v1/chat/completions`. OpenAI-shape. Respects `cache_control`.
  - Verify: `pytest tests/cluster/test_gateway_client.py -x`.
- [ ] `cost_ledger.py` — JSONL: `{ts, runtime, model, input_tokens, cache_read_tokens, cache_write_tokens, output_tokens, cost_usd, latency_ms, skill, phase}`. Weekly rotation.
  - Verify: `pytest tests/cluster/test_cost_ledger.py::test_jsonl_shape -x`.
- [ ] `/cluster/cost` returns rolling 24h + 7d cost. `/cluster/cache` returns hit-rate per runtime.
  - Verify: `curl http://localhost:8000/cluster/cost` returns valid JSON with both windows.
- [ ] Feature flag `BR3_GATEWAY=on`. Default off; flipped Phase 13.
  - Verify: with flag off, no requests reach Jimmy:4500.
- [ ] **AGENTS.md staged snippet** — write to `core/cluster/AGENTS.md.append-phase7.txt`: gateway routing rule (when flag on); cost-ledger schema (**11 fields**: `ts, runtime, model, input_tokens, cache_read_tokens, cache_write_tokens, output_tokens, cost_usd, latency_ms, skill, phase`); cache_control passthrough invariant. ≤600 staged bytes. The "11 fields" count MUST match `cost_ledger.py` exactly — Claude Review block-on includes count cross-check. Direct edits to `core/cluster/AGENTS.md` FORBIDDEN — Wave 3 merge gate applies.
  - Verify: `wc -c core/cluster/AGENTS.md.append-phase7.txt` ≤600; `grep -c "gateway\|cost_ledger\|cache_control" core/cluster/AGENTS.md.append-phase7.txt` ≥3; `grep -E "11 fields" core/cluster/AGENTS.md.append-phase7.txt` matches.

#### Claude Review (mandatory before Phase 7 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 7 --target "core/cluster/gateway_client.py,core/cluster/cost_ledger.py,api/routes/cluster_metrics.py,core/cluster/AGENTS.md.append-phase7.txt"`
- Required findings: (1) `cache_control` passed verbatim; (2) flag gate honored; (3) no secrets in `litellm.yaml`; (4) ledger schema matches AGENTS.md snippet exactly (cross-check field count: AGENTS.md "11 fields" === `cost_ledger.py` field list length === schema test asserts 11); (5) direct-call path works with flag off; (6) staged AGENTS.md snippet current.
- Block-on: cache-control stripping, flag miss, secret leak, ANY field-count mismatch between code/test/AGENTS.md, direct edit to `core/cluster/AGENTS.md`.

#### Done When

- [ ] Gateway health check 200.
- [ ] Skill run with `BR3_GATEWAY=on` produces ledger line per LLM call.
- [ ] `/cluster/cost` returns non-zero totals.
- [ ] AGENTS.md updated and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 7: gateway live — cost ledger writing, AGENTS.md updated`.

---

### Phase 8: Prompt Cache Engineering + Summarize-Before-Escalate

**Status:** ✅ COMPLETE (2026-04-20T22:10Z) — cache_policy.py (3 ephemeral breakpoints) + summarizer.py (qwen3:8b via RuntimeRegistry) live; cross_model_review.py hard-truncation slices removed (grep=0); 12KB summarize-before-escalate threshold wired; AGENTS.md 3-breakpoint contract added (7 keyword hits); 31/31 tests pass; ruff clean. gateway_client.py deliverable dropped per Phase 7 REPLACED.
**Codex model:** gpt-5.4
**Codex effort:** medium
**Worktree:** `worktrees/wave3-cache`
**Blocked by:** Phase 0, Phase 6, Phase 7 (cost ledger required to measure cache hit rate)
**Can parallelize:** Phase 5 (Phase 7 already a hard predecessor)

#### Goal

Replace hard-truncation with cache-friendly 3-breakpoint prompts and an 8B summarizer. Target >70% cache hit rate on repeated reviews.

#### Context

**Files (touch only these):**

- `core/cluster/cross_model_review.py` (MODIFY)
- `core/cluster/summarizer.py` (NEW)
- `core/runtime/cache_policy.py` (NEW)
- `core/cluster/gateway_client.py` (MODIFY — wire 3-breakpoint cache policy through `BR3_GATEWAY=on` path; original ownership stays Phase 7)
- `core/runtime/AGENTS.md` (MODIFY — codify cache breakpoint contract; Phase 8 is the only Wave-3 phase touching this file, so direct edit is allowed)
- `tests/runtime/test_cache_policy.py` (NEW)
- `tests/integration/test_summarize_before_escalate.py` (NEW)

#### Constraints

- IMPORTANT: Cache-breakpoint contract documented in `core/runtime/AGENTS.md`. All call sites use `cache_policy.py` — no inline `cache_control` dicts.
- IMPORTANT: Hard truncation (`diff[:N]`) FORBIDDEN in `cross_model_review.py`.
- NEVER let `summarizer.py` produce final code or final diagnoses.

#### Deliverables

- [ ] `cache_policy.py` — 3 breakpoints: (1) system + tools, (2) project/skill, (3) task payload. Each `cache_control: {type: "ephemeral"}`.
  - Verify: `pytest tests/runtime/test_cache_policy.py -x`; `ruff check core/runtime/cache_policy.py`.
- [ ] Refactor `build_review_prompt()` — use `cache_policy` breakpoints; if diff > 12KB → `summarizer.summarize_diff(diff)` on Below `qwen3:8b`.
  - Verify: `grep -c "\\[:.*\\]" core/cluster/cross_model_review.py` returns 0.
- [ ] `summarizer.py` — `summarize_diff(diff)`, `summarize_logs(lines)`, `summarize_spec(markdown)` via `OllamaRuntime` + `qwen3:8b`. Returns `{summary, excerpts}`. Below offline → returns raw with `truncated: true`.
  - Verify: `pytest tests/integration/test_summarize_before_escalate.py::test_50kb_diff_shrinks -x` passes.
- [ ] Wire breakpoints through `gateway_client.py` (Phase 7) when `BR3_GATEWAY=on`; direct to Anthropic SDK when off.
  - Verify: integration test confirms identical prompt structure regardless of flag.
- [ ] Weekly rollup logs cache hit rate to `decisions.log`.
  - Verify: rollup script run on synthetic ledger emits expected line.
- [ ] Tests — `cache_policy` returns correct structure; summarizer shrinks 50KB → ≤5KB preserving critical change.
  - Verify: `pytest tests/runtime/test_cache_policy.py tests/integration/test_summarize_before_escalate.py -x` all pass.
- [ ] **AGENTS.md update** — append to `core/runtime/AGENTS.md`: 3-breakpoint contract (no inline cache_control); summarize-before-escalate rule (12KB threshold); summarizer is pre-summary only. ≤400 added bytes.
  - Verify: `grep -c "breakpoint\|summariz\|12KB" core/runtime/AGENTS.md` ≥3.

#### Claude Review (mandatory before Phase 8 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 8 --target "core/cluster/cross_model_review.py,core/cluster/summarizer.py,core/runtime/cache_policy.py,core/runtime/AGENTS.md"`
- Required findings: (1) zero hard-truncation slices; (2) all call sites use `cache_policy.py`; (3) summarizer never returns final-form output; (4) summary preserves critical change; (5) AGENTS.md codifies the contract.
- Block-on: any truncation slice remaining, inline `cache_control`, summarizer producing final output, AGENTS.md drift.

#### Done When

- [ ] Repeated `/review` shows >70% cache hit rate.
- [ ] Large diffs summarized via Below.
- [ ] No regression in review quality on golden test cases.
- [ ] AGENTS.md updated and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 8: cache policy + summarizer live — N% cache hit, AGENTS.md updated`.

---

### Phase 9: 3-Way Adversarial Review + Opus 4.7 Arbiter

**Status:** ✅ COMPLETE (2026-04-20) — cross_model_review_config.json flipped (below.enabled=true, deepseek-r1:70b, reviewers claude-sonnet-4-6, arbiter claude-opus-4-7); cross_model_review.py refactored — parallel gather, fix_type validation, structural short-circuit, persistent-blocker detection, mandatory rebuttal, BR3_MAX_REVIEW_ROUNDS cap, CONTINUE/OVERRIDE/SIMPLIFY escalation prompt (exit 2, byte-identical to require-adversarial-review.sh); arbiter.py with Opus 4.7 effort=xhigh (budget_tokens:32000 replaced per Final Decisions Override), terminal ruling logged to decisions.log; adversarial-review.sh.patch-phase9 staged (--three-way flag); AGENTS.md.append-phase9.txt 787 bytes; 28/28 tests pass.
**Codex model:** gpt-5.4
**Codex effort:** high
**Worktree:** `worktrees/wave4-adversarial`
**Blocked by:** Phase 0, Phase 6, Phase 8
**Can parallelize:** Phase 10

#### Goal

Adversarial loop: Sonnet 4.6 + Codex GPT-5.4 + Below deepseek-r1:70b in parallel; one rebuttal round; unresolved split → Opus 4.7 ultrathink arbiter.

**Sonnet is intentional:** Opus is reserved for the arbiter so its judgment isn't competing with itself in Round 1.

#### Context

**Files (touch only these):**

- `core/cluster/cross_model_review_config.json` (MODIFY)
- `core/cluster/cross_model_review.py` (MODIFY)
- `core/cluster/arbiter.py` (NEW)
- `~/.buildrunner/scripts/adversarial-review.sh.patch-phase9` (NEW — staged unified diff adding `--three-way`; merged at Wave 4 end after Phase 5 patch)
- `core/cluster/AGENTS.md.append-phase9.txt` (NEW — staged snippet; merged at Wave 4 end)
- `.buildrunner/decisions.log` (APPEND)
- `tests/cluster/test_three_way_review.py` (NEW)

#### Constraints

- IMPORTANT: Arbiter uses `thinking: {type: "enabled", budget_tokens: 32000}`. Do NOT downgrade.
- IMPORTANT: Arbiter ONLY when reviewers disagree post-rebuttal.
- IMPORTANT: All reviews + rebuttal + arbiter ruling logged.
- NEVER let any reviewer see the arbiter's ruling pre-finding.
- IMPORTANT: The 3-way review pipeline MUST obey the Review Convergence Policy above — round cap 3, `fix_type` classification on every finding, structural-blocker escalation, persistent-blocker detection, rebuttal pass mandatory, no silent loop past cap.
- IMPORTANT: Arbiter ruling is terminal. Agents MUST NOT re-run the 3-way review on the same artifact after an arbiter ruling; any contest escalates to the user.

#### Deliverables

- [ ] Flip `cross_model_review_config.json` → below `enabled: true`, `deepseek-r1:70b`, timeout 120s. Pin parallel Claude → `claude-sonnet-4-6`. Pin arbiter → `claude-opus-4-7`.
  - Verify: `jq '.below.enabled, .reviewers.claude_model, .arbiter.model' core/cluster/cross_model_review_config.json` returns `true "claude-sonnet-4-6" "claude-opus-4-7"`.
- [ ] Refactor `cross_model_review.py` — gather 3 reviews in parallel. Schema: `{severity, location, claim, evidence, confidence}`.
  - Verify: `pytest tests/cluster/test_three_way_review.py::test_parallel_gather -x`.
- [ ] Round 1 parallel; Round 2 rebuttal (concede or hold + rationale). Consensus → done. Split → arbiter.
  - Verify: `pytest tests/cluster/test_three_way_review.py::test_consensus_skips_arbiter -x`; `test_disagreement_invokes_arbiter -x`.
- [ ] `arbiter.py` — Opus 4.7 with ultrathink (`budget_tokens: 32000`); summarized context (Phase 8); all 3 reviews + rebuttal; specific disagreement. Logged to `decisions.log`.
  - Verify: `pytest tests/cluster/test_three_way_review.py::test_arbiter_logs_ruling -x`.
- [ ] **`adversarial-review.sh --three-way` (staged patch)** — write `~/.buildrunner/scripts/adversarial-review.sh.patch-phase9` as a `git diff -U3` against current `adversarial-review.sh` adding the `--three-way` flag dispatching to `cross_model_review.py` (parallel Sonnet+Codex+R1, then arbiter on split). Direct edits to `adversarial-review.sh` FORBIDDEN — Wave 4 merge gate applies the Phase 5 patch (`--local`) first, then this Phase 9 patch (`--three-way`) in phase order. Old single-reviewer behavior remains the default after both patches apply.
  - Verify: `git apply --check ~/.buildrunner/scripts/adversarial-review.sh.patch-phase9` exits 0 (against tip-of-Wave-4 file with Phase 5 patch already applied — verified by the wave-merge gate, not this phase). `bash <(git apply --3way --output=- ~/.buildrunner/scripts/adversarial-review.sh.patch-phase9 < /tmp/adversarial-review.sh.with-phase5) --three-way --target tests/fixtures/buggy.py` returns valid converged findings.
- [ ] **Convergence policy wiring in `cross_model_review.py`** — implement round counter (`review_round` 1-based), max-rounds env (`BR3_MAX_REVIEW_ROUNDS`, default 3), `fix_type` requirement on every finding (reject reviewer output lacking it), structural-blocker short-circuit (first structural blocker → escalate, no further rounds), persistent-blocker detection (same normalized finding across 2+ rounds → escalate), mandatory rebuttal pass before arbiter invocation.
  - Verify: `pytest tests/cluster/test_three_way_review.py::test_round_cap_enforced -x` (artifact still blocked at round 3 triggers escalation, not round 4). `pytest tests/cluster/test_three_way_review.py::test_structural_short_circuit -x` (planted structural blocker escalates on round 1). `pytest tests/cluster/test_three_way_review.py::test_persistent_blocker_detected -x`. `pytest tests/cluster/test_three_way_review.py::test_fix_type_required -x` (reviewer output without `fix_type` rejected).
- [ ] **Escalation prompt emitted by `cross_model_review.py`** — on cap hit or structural blocker, print the exact three-option prompt (CONTINUE / OVERRIDE / SIMPLIFY) to stderr and exit with code 2. Must match the prompt in `~/.buildrunner/hooks/require-adversarial-review.sh` so agents have a single consistent surface.
  - Verify: `python -m core.cluster.cross_model_review --plan tests/fixtures/structural-conflict-plan.md --three-way` exits 2 with the CONTINUE/OVERRIDE/SIMPLIFY prompt on stderr; `diff <(python -m core.cluster.cross_model_review --escalation-prompt-only) <(bash ~/.buildrunner/hooks/require-adversarial-review.sh --escalation-prompt-only)` returns empty.
- [ ] Tests — golden buggy PR converges within 3 rounds; planted disagreement triggers arbiter (no cap violation); consensus skips arbiter; structural-conflict fixture escalates on round 1; persistent-blocker fixture escalates on round 2.
  - Verify: `pytest tests/cluster/test_three_way_review.py -x --tb=short`.
- [ ] **AGENTS.md staged snippet** — write to `core/cluster/AGENTS.md.append-phase9.txt`: 3-way + arbiter pattern; ultrathink budget = 32000; arbiter invocation rule (post-rebuttal disagreement only); reviewers see no leakage of arbiter ruling; Review Convergence Policy rules 1–8 apply to every 3-way invocation; arbiter ruling is terminal. ≤800 staged bytes. Direct edits to `core/cluster/AGENTS.md` FORBIDDEN — Wave 4 merge gate applies.
  - Verify: `wc -c core/cluster/AGENTS.md.append-phase9.txt` ≤800; `grep -c "arbiter\|ultrathink\|32000\|three-way\|convergence\|structural" core/cluster/AGENTS.md.append-phase9.txt` ≥4.

#### Claude Review (mandatory before Phase 9 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 9 --target "core/cluster/cross_model_review.py,core/cluster/arbiter.py,core/cluster/cross_model_review_config.json,core/cluster/AGENTS.md.append-phase9.txt,~/.buildrunner/scripts/adversarial-review.sh.patch-phase9"`
- Required findings: (1) ultrathink budget 32000 (no downgrade); (2) arbiter only on real disagreement; (3) no leakage; (4) Sonnet R1 / Opus arbiter; (5) every ruling logged; (6) staged AGENTS.md snippet within budget; (7) staged adversarial-review patch applies cleanly atop the Phase 5 patch and only adds `--three-way` (verified at wave-merge); (8) no direct edit to `adversarial-review.sh` or `core/cluster/AGENTS.md`; (9) Review Convergence Policy rules 1–8 fully implemented in `cross_model_review.py` — round cap 3, `fix_type` required, structural short-circuit, persistent-blocker detection, mandatory rebuttal, unified escalation prompt; (10) arbiter ruling terminal (no auto re-run path).
- Block-on: budget downgrade, over-invocation, leakage, model mismatch, missing log line, staged snippet drift from code, patch fails `git apply --check` after Phase 5 patch is applied, direct edits to either Wave 4 shared file, any convergence-policy rule missing or bypassable, divergent escalation prompt text vs `require-adversarial-review.sh`.

#### Done When

- [ ] 3-way review runs end-to-end against test PR.
- [ ] Arbiter only invoked on real disagreement.
- [ ] Opus ultrathink ruling + reasoning in `decisions.log`.
- [ ] Latency: consensus <60s, arbiter <180s.
- [ ] Round cap (3) enforced; structural-blocker fixture escalates on round 1; persistent-blocker fixture escalates on round 2; `fix_type` required on every finding.
- [ ] Escalation prompt (CONTINUE/OVERRIDE/SIMPLIFY) byte-identical between `cross_model_review.py` and `require-adversarial-review.sh`.
- [ ] AGENTS.md updated and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 9: 3-way adversarial live — Sonnet+Codex+R1, Opus arbiter, convergence policy enforced, AGENTS.md updated`.

---

### Phase 10: Auto-Context Hook (PromptSubmit + PhaseStart)

**Status:** ✅ COMPLETE (2026-04-20) — reranker.py (BAAI/bge-reranker-v2-m3 CPU) + /retrieve endpoint registered on Jimmy port 8100 (two-stage vector→rerank, 4 sources); count-tokens.sh (tiktoken cl100k_base + transformers, exit-2 fail-closed, no byte fallback); auto-context.sh hook (4K tokenizer-true budget, trivial-skip <40 chars/slash commands, JSONL ledger, exclusions block secrets/logs); auto-context.yaml with token budgets + source weights; AGENTS.md.append-phase10.txt 482 bytes; jimmy.md +164 bytes; 33 tests pass + 8 skipped (Jimmy not yet synced). MANUAL: UserPromptSubmit hook registration in ~/.claude/settings.json deferred (protect-files hook; needs update-config skill or manual edit); Jimmy rsync of retrieve.py/reranker.py deferred to Phase 12/13 deploy window.
**Codex model:** gpt-5.4
**Codex effort:** medium
**Worktree:** `worktrees/wave4-context`
**Blocked by:** Phase 0, Phase 3, Phase 6
**Can parallelize:** Phase 9

#### Goal

One hook injects relevant context into every Claude prompt. Pulls from research library, Lockwood/Jimmy memory, recent `decisions.log`, active BUILD spec. Uses Jimmy cross-encoder reranker.

#### Context

**Files (touch only these):**

- `~/.buildrunner/hooks/auto-context.sh` (NEW)
- `~/.claude/settings.json` (MODIFY — register hook for PromptSubmit + PhaseStart)
- `api/routes/retrieve.py` on Jimmy (NEW)
- `core/cluster/reranker.py` on Jimmy (NEW — `BAAI/bge-reranker-v2-m3` CPU)
- `~/.buildrunner/config/auto-context.yaml` (NEW)
- `~/.buildrunner/auto-context-ledger.jsonl` (NEW — output artifact)
- `~/.buildrunner/scripts/count-tokens.sh` (NEW — wraps `tiktoken` (cl100k_base for Claude/Codex bundles) and `transformers` (`Qwen/Qwen2.5-7B`/llama tokenizer for Below) for tokenizer-true counts; single helper used by Phases 10 + 12 + 13)
- `core/cluster/AGENTS.md.append-phase10.txt` (NEW — staged snippet; merged at Wave 4 end)
- `~/.buildrunner/agents-md/jimmy.md` (MODIFY — document `/retrieve` endpoint; Jimmy is solo on this file in Wave 4 → direct edit OK)

#### Constraints

- IMPORTANT: Behavior gated behind `BR3_AUTO_CONTEXT=on` (default OFF until Phase 13).
- IMPORTANT: Trivial-prompt skip mandatory — `/help`, `/save`, `/brief`, single-word, `y`/`n`, prompts <40 chars get NO injection.
- IMPORTANT: Hard token budget (default 4K). Hook MUST refuse above budget. Budget is enforced by **tokenizer-true count** (`count-tokens.sh`), NOT byte count — `wc -c` is a misleading proxy (a 4K-byte UTF-8 payload can be 1.5K–3K tokens depending on content; bundle headroom would be silently wrong if measured in bytes).
- NEVER inject from secrets.env or `*.log` files.

#### Deliverables

- [ ] `reranker.py` on Jimmy — loads `bge-reranker-v2-m3` on CPU. `rerank(query, candidates, top_k) -> list[Scored]`.
  - Verify: `ssh jimmy 'curl http://localhost:8100/rerank/health'` returns 200.
- [ ] `/retrieve` endpoint — query + source filters (research, lockwood-code, lockwood-memory, decisions). Stage 1 vector → Stage 2 rerank. Returns top-K snippets with source URLs + line ranges.
  - Verify: `curl -X POST http://10.0.1.106:8100/retrieve -d '{"query":"runtime fallback","top_k":3}'` returns 3 results.
- [ ] **`count-tokens.sh` helper** — `count-tokens.sh --model {claude|codex|ollama} <file-or-stdin>` returns integer token count using the model-appropriate tokenizer (cl100k_base for Claude/Codex; llama tokenizer for ollama bundles). Exit 2 on missing tokenizer (NOT a fallback to byte count — the budget MUST be tokenizer-true or fail closed).
  - Verify: `echo "hello world" | ~/.buildrunner/scripts/count-tokens.sh --model claude` returns `2` ± 1; `~/.buildrunner/scripts/count-tokens.sh --model ollama tests/fixtures/sample_bundle.txt` returns an integer.
- [ ] `auto-context.sh` — reads prompt/phase, calls `/retrieve`, formats `<auto-context>` block, injects before user prompt. Hard 4K **tokenizer-true** budget enforced via `count-tokens.sh --model claude`.
  - Verify: `tokens=$(~/.buildrunner/hooks/auto-context.sh < tests/fixtures/sample_prompt.txt | ~/.buildrunner/scripts/count-tokens.sh --model claude); test "$tokens" -le 4096`.
- [ ] **Trivial-prompt skip** — no-op for prompts <40 chars OR matching simple-command pattern.
  - Verify: `echo '/save' | ~/.buildrunner/hooks/auto-context.sh` produces no `<auto-context>` block.
- [ ] **Brief visibility** — every injection writes JSONL to `~/.buildrunner/auto-context-ledger.jsonl`: `{ts, event, prompt_excerpt, sources_injected, tokens_used, top_score}`. `/brief` reads recent N entries.
  - Verify: ledger entry exists after one non-trivial test prompt.
- [ ] Register hook for both PromptSubmit and PhaseStart in `settings.json`.
  - Verify: `jq '.hooks | keys' ~/.claude/settings.json` includes both events.
- [ ] `auto-context.yaml` — token budget per event, source weights, skip patterns, exclusion patterns.
  - Verify: file passes YAML lint; contains exclusion patterns.
- [ ] Golden test — known phase pulls matching spec section + decisions entry + research doc. Trivial prompts produce zero ledger entries.
  - Verify: `pytest tests/integration/test_auto_context_golden.py -x`.
- [ ] **AGENTS.md updates** — (a) **staged snippet** at `core/cluster/AGENTS.md.append-phase10.txt`: hook contract (4 sources, 4K **tokenizer-true** budget via `count-tokens.sh`, trivial-skip patterns, ledger schema). ≤500 staged bytes. Direct edits to `core/cluster/AGENTS.md` FORBIDDEN — Wave 4 merge gate applies. (b) **direct append** to Jimmy AGENTS.md (`~/.buildrunner/agents-md/jimmy.md`, redeployed via Phase 12 sync OR ad-hoc scp): `/retrieve` endpoint shape; the Phase 10 mirror is solo on this file in Wave 4 (no other phase touches Jimmy AGENTS.md until Phase 12), so direct edit is allowed. ≤200 added bytes.
  - Verify: `wc -c core/cluster/AGENTS.md.append-phase10.txt` ≤500; `grep -c "auto-context\|retrieve\|count-tokens" core/cluster/AGENTS.md.append-phase10.txt` ≥2; `grep -c "/retrieve" ~/.buildrunner/agents-md/jimmy.md` ≥1.

#### Claude Review (mandatory before Phase 10 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 10 --target "~/.buildrunner/hooks/auto-context.sh,api/routes/retrieve.py,core/cluster/reranker.py,~/.buildrunner/scripts/count-tokens.sh,~/.buildrunner/config/auto-context.yaml,core/cluster/AGENTS.md.append-phase10.txt,~/.buildrunner/agents-md/jimmy.md"`
- Required findings: (1) trivial skip works; (2) **tokenizer-true** token budget never exceeded — `count-tokens.sh` is invoked at every emit and fails closed if tokenizer absent (no byte-count fallback); (3) exclusions block secrets/logs; (4) ledger entries written; (5) flag off → zero behavior change; (6) staged AGENTS.md snippet within budget; (7) Jimmy AGENTS.md endpoint section current; (8) no direct edit to `core/cluster/AGENTS.md`.
- Block-on: missed skip, budget breach, secret leak path, missing ledger entry, behavior change with flag off, byte-count fallback in budget enforcement, staged snippet missing/oversized, direct edit to `core/cluster/AGENTS.md`.

#### Done When

- [ ] With flag on, `/begin` shows `<auto-context>` with 3-7 snippets; ledger gains entry.
- [ ] Trivial prompts skip cleanly.
- [ ] No budget breach.
- [ ] Flag off = zero change.
- [ ] Latency <1.5s per non-skipped fire.
- [ ] AGENTS.md updated and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 10: auto-context hook live — flag-gated, AGENTS.md updated`.

---

### Phase 11: Cluster Max Dashboard @ Port 4400

**Status:** ✅ COMPLETE (2026-04-20) — 6 vanilla-JS panels (node-health 7-tile grid INCL Jimmy, overflow-reserve, storage-health, routing-ledger, cost-cache, consensus-viewer); app.js WebSocket client (500ms→30s exp backoff, 15s heartbeat, resync on reconnect); api/routes/dashboard_stream.py FastAPI WS @ ws://10.0.1.106:4400/ws with 6 collectors; ui/dashboard/AGENTS.md updated (registered panels table + endpoint contract); all panels + app.js pass `node --check`.
**Codex model:** gpt-5.4
**Codex effort:** medium
**Worktree:** `worktrees/wave5-dashboard`
**Blocked by:** Phase 0, Phase 7, Phase 9
**Can parallelize:** Phase 12

#### Goal

Upgrade the existing port-4400 dashboard with 5 new panels — including a first-class **Jimmy** node tile (the new Minisforum MS-A2 memory/semantic backbone) and an **overflow-reserve** panel showing Lockwood/Lomax wake/drain state. Vanilla HTML; WebSocket from Jimmy for live updates.

#### Context

**Files (touch only these):**

- `ui/dashboard/index.html` (MODIFY)
- `ui/dashboard/panels/node-health.js` (NEW — 7-tile grid INCLUDING Jimmy tile: CPU, RAM, LanceDB query depth, reranker queue, context-API latency)
- `ui/dashboard/panels/overflow-reserve.js` (NEW — Lockwood + Lomax reserve state `idle`/`warming`/`active`/`draining`, wake-trigger event log, historical overflow frequency)
- `ui/dashboard/panels/storage-health.js` (NEW — Jimmy `/srv/jimmy/` directory usage, last-backup timestamps per source, off-site sync status, disk-free trend)
- `ui/dashboard/panels/routing-ledger.js` (NEW)
- `ui/dashboard/panels/cost-cache.js` (NEW)
- `ui/dashboard/panels/consensus-viewer.js` (NEW)
- `api/routes/dashboard_stream.py` on Jimmy (NEW — runs as part of the existing dashboard service on port **4400** under WS path `/ws`; emits `node-health`, `overflow-reserve`, `routing`, `cost`, `consensus` events)
- `ui/dashboard/AGENTS.md` (MODIFY — register new panels + WebSocket reconnect; Phase 11 is solo on this file in Wave 5 → direct edit OK)

#### Constraints

- IMPORTANT: Read `ui/dashboard/AGENTS.md` first — vanilla HTML + JS, NO React, NO framework.
- IMPORTANT: WebSocket reconnect uses exponential backoff capped at 30s.
- IMPORTANT: Dashboard WebSocket endpoint is `ws://10.0.1.106:4400/ws` (same port as the dashboard HTTP serve). Port **4500 is reserved for `br3-gateway` (LiteLLM) and MUST NOT be reused** — colliding the WS broadcaster with the gateway would break either service silently on systemd restart order races.
- NEVER add a build step or bundler to `ui/dashboard/`.

#### Deliverables

- [ ] `node-health.js` — 7-tile grid including **Jimmy tile**. Per tile: online, CPU, RAM, GPU (Below only), VRAM headroom (Below only), active tasks, last heartbeat. Jimmy tile additionally shows: LanceDB query depth, reranker queue depth, context-API p95 latency.
  - Verify: `npx eslint ui/dashboard/panels/node-health.js`; manual visual = 7 tiles with Jimmy labelled distinctly; Below tile shows VRAM headroom gauge that turns red when <1GB for >30s.
- [ ] `overflow-reserve.js` — Lockwood + Lomax reserve panel. Shows current state (`idle`/`warming`/`active`/`draining`), last 20 wake/drain events with trigger cause (`vram_low`, `test_queue_deep`, `parallel_dispatch`, `bulk_ingest`, `below_unreachable`), and historical overflow frequency per 24h.
  - Verify: `npx eslint ui/dashboard/panels/overflow-reserve.js`; manual visual = 2 reserve tiles (Lockwood, Lomax) with live state + event log.
- [ ] `storage-health.js` — Jimmy storage panel: per-directory usage bar for each `/srv/jimmy/` subtree, last-backup timestamps per source (nightly-projects, buildrunner-state, git-mirrors, supabase, brlogger), off-site sync status (last rclone run, success/fail), 30-day disk-free trend line, **disk-guard tier badge** reading `/srv/jimmy/status/disk-guard.json` (green `OK <80%` / amber `WARN 80-92%` / red `CRIT 92-96%` / magenta `PAGE ≥96%`), last `archive-prune` + `lancedb-compact` run timestamps, `backups-paused` flag indicator (visible red pill when set). Red banner if any nightly backup is >36h old or off-site sync >8 days old. Magenta banner if `backups-paused` is present.
  - Verify: `npx eslint ui/dashboard/panels/storage-health.js`; manual visual shows all directory bars + timestamps + off-site status + disk-guard tier badge + archive/compact timestamps; force an old-backup condition and confirm red banner appears; write a fake `backups-paused` flag and confirm magenta banner appears.
- [ ] `routing-ledger.js` — last 50 routing decisions: timestamp, skill, phase, runtime, reason.
  - Verify: `npx eslint ui/dashboard/panels/routing-ledger.js`.
- [ ] `cost-cache.js` — stacked bar 24h cost + line chart cache hit rate.
  - Verify: `npx eslint ui/dashboard/panels/cost-cache.js`.
- [ ] `consensus-viewer.js` — live state of 3-way review.
  - Verify: `npx eslint ui/dashboard/panels/consensus-viewer.js`.
- [ ] WebSocket broadcaster on Jimmy at `ws://10.0.1.106:4400/ws` (sharing the dashboard service port; LiteLLM gateway on 4500 stays untouched). Dashboard subscribes via one socket.
  - Verify: `wscat -c ws://10.0.1.106:4400/ws` receives event within 5s; `ss -tnlp | grep -E ":4500\s"` on Jimmy shows ONLY `br3-gateway` bound to 4500 (no dashboard process); `curl http://10.0.1.106:4500/health` still returns 200 (LiteLLM unaffected).
- [ ] Sanity check — all 4 panels render with live data during a test `/begin`. No console errors.
  - Verify: `playwright test tests/e2e/dashboard.spec.ts` passes.
- [ ] **AGENTS.md update** — append to `ui/dashboard/AGENTS.md`: panel registry (4 new files); WebSocket reconnect contract (exp backoff cap 30s); refresh-proof rule. ≤300 added bytes.
  - Verify: `grep -c "node-health\|routing-ledger\|cost-cache\|consensus-viewer\|reconnect" ui/dashboard/AGENTS.md` ≥5.

#### Claude Review (mandatory before Phase 11 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 11 --target "ui/dashboard/index.html,ui/dashboard/panels/*.js,api/routes/dashboard_stream.py,ui/dashboard/AGENTS.md"`
- Required findings: (1) zero React/framework deps; (2) reconnect backoff implemented; (3) all 7 nodes visible INCLUDING Jimmy tile with Jimmy-specific metrics (LanceDB, reranker queue, context-API latency); (4) overflow-reserve panel renders Lockwood + Lomax with live state + wake/drain event log; (5) storage-health panel renders all `/srv/jimmy/` directories + last-backup timestamps + off-site sync status; (6) Below VRAM headroom gauge turns red when <1GB; (7) red-banner conditions (old backup, stale off-site sync) visually trigger when simulated; (8) refresh-proof; (9) eslint clean; (10) WebSocket bound to 4400 only — `dashboard_stream.py` does not import or `bind` to 4500; (11) AGENTS.md updated.
- Block-on: framework introduced, missing reconnect, panel missing a node, Jimmy tile missing its specific metrics, overflow-reserve panel missing, storage-health panel missing, red-banner not triggering on stale backups, console errors, any 4500 binding in dashboard code, AGENTS.md stale.

#### Done When

- [ ] `localhost:4400` shows routing decisions streaming, cost panel updating, node health live.
- [ ] All 7 nodes visible INCLUDING Jimmy as a first-class node tile with its specific metrics.
- [ ] Overflow-reserve panel live, showing Lockwood + Lomax state + wake/drain events.
- [ ] Storage-health panel live, showing `/srv/jimmy/` usage + last-backup timestamps + off-site sync status.
- [ ] Below VRAM headroom gauge visible and responsive to load.
- [ ] AGENTS.md updated and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 11: dashboard live — 6 panels at :4400, Jimmy + overflow-reserve + storage-health added, WebSocket from Jimmy, AGENTS.md updated`.

---

### Phase 12: Multi-Model Context Parity (Logs, Memory, Research)

**Status:** ✅ COMPLETE (2026-04-20) — context_bundle.py (5 source types, two-layer [private] filter, tokenizer-true exit-2 fail-closed no byte fallback), context_router.py (claude=32K/codex=48K/ollama=16K budgets), context_injector.py (RuntimeRegistry wrapper, BR3_MULTI_MODEL_CONTEXT flag-gated default OFF), api/routes/context.py (GET /context/{model} with budget.tokenizer field, 503 on flag-off/tokenizer-unavailable); ~/.buildrunner/ scripts filter-private-decisions.sh + sync-cluster-context.sh (rsync + chmod 444) + codex-bridge.sh + below-route.sh MODIFIED; context-sources.yaml (14 exclusion globs); deploy/jimmy/systemd/br3-context-sync.{service,timer} staged; otis.md AGENTS appended; AGENTS.md.append-phase12.txt 548 bytes (5 required keywords); 17 Phase 12 tests + 135 total cluster+runtime tests pass; canary test verifies [private] lines never leak. MANUAL DEFERRED to Phase 13 deploy window: scp otis.md to Otis, systemctl enable br3-context-sync.timer on Jimmy, live /context/{model} smoke test.
**Codex model:** gpt-5.4
**Codex effort:** medium
**Worktree:** `worktrees/wave5-parity`
**Blocked by:** Phase 0, Phase 3 (Jimmy hosts retrieve), Phase 6 (registry), Phase 7 (gateway), Phase 10 (auto-context infra)
**Can parallelize:** Phase 11

#### Goal

Bring Codex (on Otis + Muddy) and Below to **the same context surface Claude has today** — read access to all `.buildrunner/*.log` files, full Lockwood memory (`memory.db`, `intel.db`, `build_history`, `decisions.log`, `plan_outcomes`), and the entire `~/Projects/research-library/`. Every model sees the same operational reality; no model is information-starved.

This is the parity phase. After it lands, asking Codex about a recent log pattern, asking Below about a prior decision, or asking Claude about a research doc all return equivalent grounded answers.

#### Context

**Files (touch only these):**

- `core/cluster/context_bundle.py` (NEW — assembles per-model unified bundle)
- `core/cluster/context_router.py` (NEW — picks the right bundle size per model)
- `api/routes/context.py` on Jimmy (NEW — `GET /context/{model}` endpoint)
- `~/.buildrunner/scripts/codex-bridge.sh` (MODIFY — pre-prompt context fetch)
- `~/.buildrunner/scripts/below-route.sh` (MODIFY — context fetch on non-summary tasks)
- `core/runtime/context_injector.py` (NEW — registry-side injection wrapper)
- `~/.buildrunner/scripts/sync-cluster-context.sh` (NEW — read-only mirror to Otis + Below for offline-fast access; FILTERS `[private]` lines AT THE MIRROR before any bytes leave Muddy/Jimmy)
- `~/.buildrunner/scripts/filter-private-decisions.sh` (NEW — single canonical filter; reads `decisions.log`, drops every line tagged `[private]`, emits `decisions.public.log`. Used by both the mirror (Phase 12) and the extractor inside `context_bundle.py`)
- `/etc/systemd/system/br3-context-sync.timer` on Jimmy (NEW — 5-min sync cadence)
- `~/.buildrunner/config/context-sources.yaml` (NEW — source registry, per-model budgets, exclusions)
- `~/.buildrunner/agents-md/otis.md` (DEPLOY → `~/AGENTS.md` on Otis)
- `core/cluster/AGENTS.md.append-phase12.txt` (NEW — staged snippet; merged at Wave 5 end)
- `~/.buildrunner/agents-md/jimmy.md` (MODIFY — document `/context/{model}` endpoint; Phase 10 already touched this file in Wave 4 which is closed by the time Wave 5 starts, so direct edit is safe)
- `tests/cluster/test_multi_model_parity.py` (NEW)

#### Constraints

- IMPORTANT: Read access ONLY. No model — Codex, Below, or Claude — mutates Lockwood/research state through this surface. Mutation goes through the existing dispatch APIs.
- IMPORTANT: Same exclusion patterns as Phase 10 — never expose `secrets.env`, `auth.json`, `*.token`, `*.key`, or anything matching `~/.buildrunner/config/context-sources.yaml`'s exclude list.
- IMPORTANT: Per-model bundle budgets are mandatory — Claude 32K (room within 200K window), Codex 48K (room within 1.05M window), Below 16K (within 32K context). The budget is the bundle size after rerank, NOT the candidate pool size.
- IMPORTANT: `context_router.py` is the SINGLE source of truth for which sources flow to which model. Skills MUST NOT bypass it.
- IMPORTANT: Behavior gated behind `BR3_MULTI_MODEL_CONTEXT=on` (default OFF until Phase 13).
- IMPORTANT: Read-only mirrors on Otis + Below are managed by `br3-context-sync.timer` — DO NOT scp ad-hoc.
- NEVER let Below or Codex see `decisions.log` lines marked `[private]`. The filter runs **AT THE MIRROR** (`sync-cluster-context.sh` calls `filter-private-decisions.sh` before rsync; only `decisions.public.log` ever lands on Otis or Below), AND a second time at extraction inside `context_bundle.py` (defense in depth). Filtering only at extraction is INSUFFICIENT — the raw `decisions.log` would still exist on the read-mount and could be read by any process on Otis/Below outside the bundle path.
- NEVER bundle research docs older than the source `last_updated` field — staleness leaks bad guidance.

#### Deliverables

- [ ] `context_bundle.py` — assembles `{logs: [...], memory: {...}, research: [...], decisions: [...], spec: ...}` from Jimmy sources + research library + Lockwood DBs. Returns sized bundle.
  - Verify: `pytest tests/cluster/test_context_bundle.py -x`.
- [ ] `context_router.py` — given `model` (`claude` | `codex` | `ollama`), returns appropriate sources + budget. Single source of truth.
  - Verify: `pytest tests/cluster/test_context_router.py::test_per_model_budgets -x`.
- [ ] `GET /context/{model}` on Jimmy (port 4500, behind gateway) — accepts `query` + `phase` + `skill`, returns sized bundle. Reranker (Phase 10) re-orders within budget. Per-model budget enforcement is **tokenizer-true** via `count-tokens.sh` (Phase 10 helper); the response includes a `budget: {limit, used, tokenizer}` field.
  - Verify: `curl 'http://10.0.1.106:4500/context/codex?query=runtime+fallback&phase=6&skill=begin' | jq '.bundle' | ~/.buildrunner/scripts/count-tokens.sh --model codex` returns ≤48000; response `.budget.tokenizer` field equals the model-specific tokenizer name (NOT `bytes`).
- [ ] `codex-bridge.sh` — fetches `/context/codex` BEFORE each Codex dispatch; injects bundle as system-prompt prefix. If Jimmy unreachable → log warning + proceed without bundle (graceful degrade).
  - Verify: `bash ~/.buildrunner/scripts/codex-bridge.sh --dry-run --task "echo ok"` shows `<cluster-context>` block in printed prompt.
- [ ] `below-route.sh` MODIFY — for non-summary tasks (`--mode draft`, `--mode review`), fetch `/context/ollama` and prepend. Summary tasks skip (avoids context bloat on small inputs).
  - Verify: `~/.buildrunner/scripts/below-route.sh --mode draft "What was decided about runtime fallback?"` includes a memory excerpt in output reasoning.
- [ ] `context_injector.py` — registry-side wrapper used by `RuntimeRegistry`. When `BR3_MULTI_MODEL_CONTEXT=on`, every `runtime.execute(task)` call passes through the injector.
  - Verify: `pytest tests/runtime/test_context_injector.py::test_all_three_runtimes -x`.
- [ ] `filter-private-decisions.sh` — `cat decisions.log | filter-private-decisions.sh > decisions.public.log`. Drops every line containing the literal token `[private]` (case-sensitive, anchored as `\b\[private\]\b` to avoid matching e.g. `[privately]`). Idempotent. Used by both the mirror and `context_bundle.py`.
  - Verify: `printf '%s\n' '[public] foo' '[private] secret' '[public] bar' | ~/.buildrunner/scripts/filter-private-decisions.sh | wc -l` returns 2; output contains no `[private]` substring.
- [ ] `sync-cluster-context.sh` — runs every 5 min on Jimmy via `br3-context-sync.timer`. Read-only `rsync` of: `~/.buildrunner/*.log` (browser, supabase, device, query), `~/.lockwood/memory.db`, `~/.lockwood/intel.db`, `~/Projects/research-library/` to `/srv/br3-context/` mirror on Otis (10.0.1.103) and Below (10.0.1.105). For `decisions.log` specifically: pipe through `filter-private-decisions.sh` FIRST and rsync the resulting `decisions.public.log` to the mirror. The raw `decisions.log` MUST NEVER appear in `/srv/br3-context/` on either node. Read-only mount/permission (chmod 444).
  - Verify: `ssh otis 'ls /srv/br3-context/.buildrunner/'` shows `decisions.public.log` and NOT `decisions.log`; `ssh below 'ls /srv/br3-context/.buildrunner/decisions.log 2>&1'` returns "No such file or directory"; `ssh otis 'grep -c "\\[private\\]" /srv/br3-context/.buildrunner/decisions.public.log'` returns 0; mirror file permissions are `-r--r--r--`.
- [ ] `context-sources.yaml` — registry of: source paths (logs, dbs, research roots), per-model budgets, exclusion globs (secrets, auth, tokens), TTL per source (research = 30d, decisions = no TTL, logs = 7d).
  - Verify: file passes YAML lint; declares all 5 source types + 3 model budgets + ≥4 exclusion globs.
- [ ] **Deploy Otis AGENTS.md** — `scp ~/.buildrunner/agents-md/otis.md byronhudson@10.0.1.103:~/AGENTS.md`. Byte-for-byte verify.
  - Verify: `ssh otis 'sha256sum ~/AGENTS.md'` matches `sha256sum ~/.buildrunner/agents-md/otis.md`.
- [ ] **Parity test** — `tests/cluster/test_multi_model_parity.py`: send the same grounded query ("What did we decide about RLS in the last 30 days, what log evidence supports the decision, what prior session memory recalls it, and what research backs the decision?") to each model with `BR3_MULTI_MODEL_CONTEXT=on`. Each response MUST cite at least one item from EACH of the FIVE source types declared in `context-sources.yaml`: (a) `~/.buildrunner/*.log` (e.g., a `supabase.log` or `browser.log` line), (b) `decisions.public.log` (filtered), (c) `~/.lockwood/memory.db` (a prior session memory), (d) `~/.lockwood/intel.db` (an intel-scored item), (e) `~/Projects/research-library/` (a research doc). A response missing ANY source type counts as parity failure for that model. The test asserts `assert sources_cited >= {"logs","decisions","memory","intel","research"}` per model.
  - Verify: `pytest tests/cluster/test_multi_model_parity.py -x --tb=short -k all_five_sources` all 3 models pass; the test report prints per-model `sources_cited` set.
- [ ] **Private-decision leak test** — `tests/cluster/test_no_private_leak.py`: write a synthetic `decisions.log` line `[private] secret-canary-token-XYZ`, run a sync, then on each of Otis and Below run `grep -r "secret-canary-token-XYZ" /srv/br3-context/` AND fetch `/context/codex` + `/context/ollama` for a query crafted to surface the canary. Assert the canary appears NOWHERE on the mirror AND in NO bundle response.
  - Verify: `pytest tests/cluster/test_no_private_leak.py -x` passes.
- [ ] **AGENTS.md updates** — (a) **staged snippet** at `core/cluster/AGENTS.md.append-phase12.txt`: `/context/{model}` contract; `context_router.py` is single source of truth; read-mount rule; per-model token budgets enforced via `count-tokens.sh` (NOT byte count); two-layer `[private]` filter (mirror + extraction); `BR3_MULTI_MODEL_CONTEXT` default OFF until Phase 13. ≤600 staged bytes. Direct edits to `core/cluster/AGENTS.md` FORBIDDEN — Wave 5 merge gate applies. (b) **direct append** to Jimmy AGENTS.md (`~/.buildrunner/agents-md/jimmy.md`): endpoint shape + per-model token budgets; redeploy via scp + sha256 verify. ≤300 added bytes. (c) **direct append** to Otis AGENTS.md (`~/.buildrunner/agents-md/otis.md`): read-mount path `/srv/br3-context/`, sync timer cadence, `decisions.public.log` is the ONLY decisions surface visible. ≤300 added bytes.
  - Verify: `wc -c core/cluster/AGENTS.md.append-phase12.txt` ≤600; `grep -c "/context/\|context_router\|count-tokens\|filter-private\|BR3_MULTI_MODEL_CONTEXT" core/cluster/AGENTS.md.append-phase12.txt` ≥4; `grep -c "/context/" ~/.buildrunner/agents-md/jimmy.md` ≥1; `grep -c "/srv/br3-context\|decisions.public" ~/.buildrunner/agents-md/otis.md` ≥2.

#### Claude Review (mandatory before Phase 12 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 12 --target "core/cluster/context_bundle.py,core/cluster/context_router.py,api/routes/context.py,~/.buildrunner/scripts/codex-bridge.sh,~/.buildrunner/scripts/below-route.sh,~/.buildrunner/scripts/sync-cluster-context.sh,~/.buildrunner/scripts/filter-private-decisions.sh,core/runtime/context_injector.py,~/.buildrunner/config/context-sources.yaml,core/cluster/AGENTS.md.append-phase12.txt,~/.buildrunner/agents-md/jimmy.md,~/.buildrunner/agents-md/otis.md"`
- Required findings: (1) read-only contract enforced — no mutation paths; (2) exclusion globs block all secret patterns; (3) per-model budgets respected and **tokenizer-true** via `count-tokens.sh` (no byte-count fallback); (4) `context_router.py` is the only path to model-specific bundles; (5) graceful degrade when Jimmy unreachable; (6) staged AGENTS.md snippet within budget + Jimmy + Otis AGENTS.md updated; (7) read-mount permissions are 444 on Otis + Below; (8) **TWO-LAYER `[private]` filter**: (a) `sync-cluster-context.sh` calls `filter-private-decisions.sh` BEFORE rsync and the raw `decisions.log` is absent from `/srv/br3-context/` on both Otis AND Below, (b) `context_bundle.py` independently re-filters before any extraction; (9) `test_no_private_leak.py` passes (canary token nowhere); (10) parity test cites all 5 source types per model.
- Block-on: any mutation path, secret leak path, budget breach, router bypass, hard-fail on Jimmy outage, AGENTS.md stale, write permission anywhere on the mirrors, ANY private-tag leak (mirror or bundle), parity test failing on any source type, byte-count fallback in budget enforcement, direct edit to `core/cluster/AGENTS.md`.

#### Done When

- [ ] All deliverable verification commands pass.
- [ ] Parity test passes for all 3 models — each cites at least one item from EACH of the 5 source types (logs, decisions, memory, intel, research) on the same grounded query.
- [ ] Private-decision leak test passes — synthetic `[private]` canary appears nowhere on either mirror and in no bundle response.
- [ ] Read-mounts on Otis + Below show `-r--r--r--` permissions and recent mtime; `decisions.public.log` present and `decisions.log` absent.
- [ ] `BR3_MULTI_MODEL_CONTEXT=on` produces `<cluster-context>` blocks for Codex + Below; flag off = zero behavior change.
- [ ] AGENTS.md updated (staged snippet + Jimmy + Otis) and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 12: multi-model context parity live — Codex+Below see logs+memory+research, two-layer private filter, AGENTS.md updated on 3 scopes`.

---

### Phase 13: Shadow → Cutover + Validation

**Status:** not_started
**Codex model:** gpt-5.3-codex
**Codex effort:** medium
**Worktree:** main repo
**Blocked by:** Phase 0, 5, 7, 8, 9, 10, 11, 12

#### Goal

Run new paths in shadow mode for ≥7 days, compare results, then flip all 5 feature flags. Roll back in one command if quality drops.

#### Context

**Files (touch only these):**

- `core/runtime/shadow_runner.py` (MODIFY — extend to cover OllamaRuntime, context bundles, AND the shell-level dispatch surface)
- `~/.buildrunner/scripts/shadow-shell-wrapper.sh` (NEW — shadow-mode wrapper around `auto-context.sh`, `codex-bridge.sh`, `below-route.sh`; tees the produced prompt+context to `~/.buildrunner/shadow/shell-results.jsonl` for divergence diff)
- `~/.buildrunner/scripts/shadow-dashboard-tap.py` (NEW — subscribes to `ws://10.0.1.106:4400/ws` during shadow window, snapshots events to `~/.buildrunner/shadow/dashboard-events.jsonl`; verifies the streaming surface stays live across the cutover boundary)
- `~/.buildrunner/config/feature-flags.yaml` (MODIFY — flip defaults on)
- `~/.buildrunner/scripts/rollback-cluster-max.sh` (NEW)
- `core/cluster/AGENTS.md` (MODIFY — supersede mechanism applies: delete the existing "all 5 flags default OFF" line, append the new "default ON" line, bump the `Last updated:` marker; same edit set)
- `AGENTS.md` (MODIFY — root file notes cutover state via supersede mechanism: same delete-then-append-then-bump rule)
- `.buildrunner/decisions.log` (APPEND — cutover entry)

#### Constraints

- IMPORTANT: Cutover happens AFTER ≥7 days shadow with documented divergence stats.
- IMPORTANT: Rollback script MUST be tested dry-run before real cutover.
- IMPORTANT: This is the ONLY phase allowed to flip feature-flag defaults.
- IMPORTANT: Shadow coverage MUST span ALL surfaces that change behavior under the 5 flags — runtime registry (Phase 6/8), shell dispatch hooks (`auto-context.sh`, `codex-bridge.sh`, `below-route.sh`), context bundles (Phase 12), AND the dashboard streaming tap. A flag-default flip without shadow coverage of a surface is a Phase 13 ship-block.
- IMPORTANT: AGENTS.md edits use the **supersede mechanism** (defined in the AGENTS.md Maintenance Rule). Stale "default OFF" lines MUST be deleted in the same edit that appends "default ON" lines. The `Last updated: YYYY-MM-DD (Phase 13)` marker MUST be bumped at the top of every modified AGENTS.md file. Two contradictory live instructions in the same scope = ship-block.
- NEVER skip the dry-run rollback test.

#### Deliverables

- [ ] Extend `shadow_runner.py` — runs `OllamaRuntime` in parallel with Claude/Codex on read-only tasks AND validates parity bundles match between shadow and primary. Diff outputs to `~/.buildrunner/shadow/results.jsonl`.
  - Verify: `pytest tests/runtime/test_shadow_runner.py::test_ollama_shadow -x`; `test_parity_shadow -x`.
- [ ] **`shadow-shell-wrapper.sh`** — when `BR3_SHADOW=on`, wraps `auto-context.sh`, `codex-bridge.sh`, `below-route.sh` so each invocation logs `{ts, hook, input_excerpt, output_excerpt, latency_ms, would_fire_with_flag_on}` to `~/.buildrunner/shadow/shell-results.jsonl`. The wrapper is a transparent passthrough — primary behavior is unchanged; only a side-channel record is written.
  - Verify: `BR3_SHADOW=on bash -c '. ~/.buildrunner/scripts/shadow-shell-wrapper.sh && shadow_run auto-context "test prompt"'`; resulting JSONL line contains all 5 fields.
- [ ] **`shadow-dashboard-tap.py`** — runs as a 7-day systemd unit on Muddy. Subscribes to `ws://10.0.1.106:4400/ws`, writes one JSONL line per dashboard event to `~/.buildrunner/shadow/dashboard-events.jsonl`, asserts no >60s gap (heartbeat verifier). Catches dashboard streaming regressions before cutover.
  - Verify: `python scripts/shadow_dashboard_health.py --window 7d` reports `max_gap_s < 60` and `events_per_minute > 0`.
- [ ] Shadow period: 7 days minimum. Divergence goals: <15% on review findings, <5% on plan structure, <10% on parity-grounded answers, **<5% on shell-hook output** (auto-context bundle drift, codex-bridge prompt drift, below-route response drift), **zero unexplained dashboard tap gaps >60s**.
  - Verify: `python scripts/shadow_divergence_report.py --window 7d --include-shell --include-dashboard` returns within all thresholds.
- [ ] Flag cutover: flip `BR3_CLUSTER_MAX=on`, `BR3_LOCAL_ROUTING=on`, `BR3_AUTO_CONTEXT=on`, `BR3_GATEWAY=on`, `BR3_MULTI_MODEL_CONTEXT=on` in `feature-flags.yaml`.
  - Verify: `for f in BR3_CLUSTER_MAX BR3_LOCAL_ROUTING BR3_AUTO_CONTEXT BR3_GATEWAY BR3_MULTI_MODEL_CONTEXT; do yq ".flags.$f" ~/.buildrunner/config/feature-flags.yaml; done` returns `on` for all 5.
- [ ] `rollback-cluster-max.sh` — flips all 5 flags off, restarts affected services, emits `decisions.log` entry. Tested dry-run.
  - Verify: `bash ~/.buildrunner/scripts/rollback-cluster-max.sh --dry-run` exits 0; logs intended actions for all 5 flags.
- [ ] Post-cutover validation — `/begin`, `/autopilot`, `/review`, `/commit` on one real phase end-to-end. Cost ledger non-zero, cache hit rising, 3-way adversarial, dashboard live, parity bundles served.
  - Verify: `python scripts/post_cutover_smoke.py` passes all 5 checks.
- [ ] **AGENTS.md update via supersede mechanism** — for both root `AGENTS.md` AND `core/cluster/AGENTS.md`, in a SINGLE edit per file: (a) DELETE the existing line that says all 5 BR3\_\* flags default OFF (introduced in Phase 0); (b) APPEND the new line stating all 5 flags default ON post Phase 13 with the cutover date; (c) BUMP the `Last updated: YYYY-MM-DD (Phase 13)` marker at the top of each file. After the edit, NO line in either file may say the flags default OFF. ≤200 net added bytes per file (the delete partially offsets the append).
  - Verify: `grep -c "default OFF" AGENTS.md core/cluster/AGENTS.md` returns 0; `grep -c "default ON\|Phase 13" AGENTS.md core/cluster/AGENTS.md` ≥4; both files start with a `Last updated: .* (Phase 13)` line; combined size still ≤24KB.
- [ ] `decisions.log` entry documenting cutover date, shadow stats (including shell + dashboard divergence), flag state.

#### Claude Review (mandatory before Phase 13 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 13 --target "core/runtime/shadow_runner.py,~/.buildrunner/scripts/shadow-shell-wrapper.sh,~/.buildrunner/scripts/shadow-dashboard-tap.py,~/.buildrunner/config/feature-flags.yaml,~/.buildrunner/scripts/rollback-cluster-max.sh,AGENTS.md,core/cluster/AGENTS.md"`
- Required findings: (1) shadow ≥7 days documented; (2) divergence within thresholds (5 metrics: review, plan, parity, **shell-hook output, dashboard tap continuity**); (3) rollback dry-run executed; (4) all 5 flags flipped consistently; (5) post-cutover smoke passed; (6) AGENTS.md (both files) updated via supersede mechanism — **zero remaining "default OFF" lines**, `Last updated: ... (Phase 13)` marker present at top of each file, no contradictory live instructions.
- Block-on: shadow <7 days, divergence above any threshold, missing shell-wrapper or dashboard-tap coverage, rollback untested, partial flag flip, smoke failure, ANY stale "default OFF" line surviving in either AGENTS.md, missing `Last updated` marker bump.

#### Done When

- [ ] All 5 flags on in `feature-flags.yaml`.
- [ ] One full build phase executed end-to-end.
- [ ] Rollback script tested.
- [ ] No P0/P1 regressions in first 48h.
- [ ] AGENTS.md updated and reviewed.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 13: cutover complete — 5 flags on, shadow N days, rollback tested, AGENTS.md updated`.

---

### Phase 14: BR3 Self-Maintenance

**Status:** not_started
**Codex model:** gpt-5.3-codex
**Codex effort:** medium
**Worktree:** main repo
**Blocked by:** Phase 0, Phase 13

#### Goal

BR3 monitors and maintains Cluster Max itself — self-heals node-offline events, rebalances load, handles model updates, alerts on cost drift. The cluster keeps itself healthy without manual babysitting.

#### Context

**Files (touch only these):**

- `core/cluster/self_health.py` (NEW)
- `core/cluster/auto_rebalance.py` (NEW)
- `~/.buildrunner/scripts/model-update.sh` (NEW)
- `core/cluster/cost_alerts.py` (NEW)
- `~/.buildrunner/scripts/backup-prune.sh` (NEW — enforces 30 daily + 12 monthly + 3 yearly retention under `/srv/jimmy/backups/projects/`)
- `~/.buildrunner/scripts/offsite-sync.sh` (NEW — weekly `rclone sync` of `/srv/jimmy/backups/` to cloud bucket)
- `~/.buildrunner/scripts/backup-integrity-check.sh` (NEW — weekly spot-check: 10 random files per snapshot, compared to manifest.sha256)
- `~/.buildrunner/scripts/archive-prune.sh` (NEW — unified retention enforcement across all non-projects Jimmy subtrees: brlogger 90d; supabase 14d+8w+12m; git-mirrors monthly `git gc --aggressive --prune=now`; adversarial-reviews 90d raw + monthly `.tar.zst` of older; cost-ledger raw events 180d + daily rollups forever; memory session-summaries 180d)
- `~/.buildrunner/scripts/lancedb-compact.sh` (NEW — quarterly LanceDB `compact_files()` + `cleanup_old_versions()` on `/srv/jimmy/lancedb/`, with pre-run row-count check that must match post-run)
- `~/.buildrunner/scripts/disk-guard.sh` (NEW — 15-min timer, reads `df /srv/jimmy`: WARN at 80% → dashboard red banner + `decisions.log`; CRIT at 92% → emergency prune of oldest `backups/projects/` daily snapshots one at a time until ≤88%, never touching monthly/yearly; PAGE at 96% → stop accepting new backups + loud alert)
- `/etc/systemd/system/br3-self-health.service|.timer` on Jimmy (NEW — `OnUnitActiveSec=5min`, `Persistent=true`)
- `/etc/systemd/system/br3-cost-alerts.service|.timer` on Jimmy (NEW — `OnCalendar=daily`, `Persistent=true`)
- `/etc/systemd/system/br3-model-update.service|.timer` on Jimmy (NEW — `OnCalendar=weekly`, `Persistent=true`)
- `/etc/systemd/system/br3-backup-prune.service|.timer` on Jimmy (NEW — `OnCalendar=*-*-* 04:30:00`, fires 90 min after nightly backup finishes; `Persistent=true`)
- `/etc/systemd/system/br3-offsite-sync.service|.timer` on Jimmy (NEW — `OnCalendar=Sun *-*-* 05:00:00`, weekly; `Persistent=true`)
- `/etc/systemd/system/br3-backup-integrity.service|.timer` on Jimmy (NEW — `OnCalendar=Sun *-*-* 06:00:00`, weekly; `Persistent=true`)
- `/etc/systemd/system/br3-archive-prune.service|.timer` on Jimmy (NEW — `OnCalendar=*-*-* 04:45:00`, fires 15 min after backup-prune; `Persistent=true`)
- `/etc/systemd/system/br3-lancedb-compact.service|.timer` on Jimmy (NEW — `OnCalendar=*-01,04,07,10-01 03:00:00`, quarterly; `Persistent=true`)
- `/etc/systemd/system/br3-disk-guard.service|.timer` on Jimmy (NEW — `OnUnitActiveSec=15min`, `Persistent=true`)
- `core/cluster/AGENTS.md` (MODIFY — encode self-health timers + rebalance contract + full retention matrix (projects/brlogger/supabase/git-mirrors/adversarial/cost/memory/lancedb) + off-site cadence + disk-guard thresholds; Phase 14 is a single-phase wave → direct edit OK)

#### Constraints

- IMPORTANT: Auto-rebalance must NEVER drop in-flight work silently — reassign and log every move.
- IMPORTANT: Model update promotes new version ONLY if benchmark stays within 10% of prior tok/s.
- IMPORTANT: Cadences are enforced by `.timer` units (NOT `cron`, NOT `at`, NOT internal `time.sleep` loops). A `.service` without an enabled `.timer` is a Phase 14 ship-block — `Done When` requires `systemctl is-active <name>.timer` and `systemctl list-timers --all` to show the next-fire time. `Persistent=true` on every timer so a brief Jimmy outage doesn't skip a window.
- NEVER let `cost_alerts.py` page on routine variation — only >2x day-over-day spike.

#### Deliverables

- [ ] `self_health.py` — every 5 min: ping all 7 nodes, confirm services responsive, confirm disk/RAM/VRAM thresholds, confirm Ollama models loaded. Write `~/.buildrunner/health/latest.json`. On persistent failure → `decisions.log` + dashboard alert.
  - Verify: `pytest tests/cluster/test_self_health.py -x`; latest.json updated within 5 min of service start.
- [ ] `auto_rebalance.py` — unhealthy node removed from pool; in-flight work reassigned. Returns after 2-min cool-down. No silent drops.
  - Verify: `pytest tests/cluster/test_auto_rebalance.py::test_no_silent_drop -x`.
- [ ] `model-update.sh` — weekly cron pulls latest llama3.3, qwen3, deepseek-r1 tags. Quick benchmark. Promotes only if tok/s within 10% of prior.
  - Verify: `shellcheck ~/.buildrunner/scripts/model-update.sh`; dry-run with mocked benchmark exits 0.
- [ ] `cost_alerts.py` — daily reads `cost_ledger`; flags >2x DoD increase by runtime. Writes alert to `decisions.log` + dashboard banner.
  - Verify: `pytest tests/cluster/test_cost_alerts.py::test_2x_threshold -x`.
- [ ] `backup-prune.sh` — enforces retention on `/srv/jimmy/backups/projects/`: keep last 30 daily snapshots, promote 1st-of-month snapshot to `monthly/` (keep 12), promote Jan 1 snapshot to `yearly/` (keep 3). Deletes nothing until promotion completes successfully. Logs every delete to `/srv/jimmy/logs/backup-prune.log`.
  - Verify: `shellcheck ~/.buildrunner/scripts/backup-prune.sh`; dry-run on a fixture with 45 daily snapshots promotes correctly and lists exactly 15 planned deletions.
- [ ] `offsite-sync.sh` — weekly `rclone sync /srv/jimmy/backups/ <remote>:br3-jimmy-backups/ --fast-list --transfers=4 --checksum`. Writes last-success timestamp to `/srv/jimmy/status/offsite-last-success`. Exits non-zero on any rclone error.
  - Verify: `shellcheck ~/.buildrunner/scripts/offsite-sync.sh`; `--dry-run` with rclone remote configured produces plausible sync plan.
- [ ] `backup-integrity-check.sh` — weekly, picks 10 random files per snapshot in `/srv/jimmy/backups/projects/*/` (sample the 4 most recent snapshots), re-hashes them, compares to `manifest.sha256`. On mismatch, writes alert to `decisions.log` + dashboard banner.
  - Verify: `shellcheck ~/.buildrunner/scripts/backup-integrity-check.sh`; intentional corruption of one tracked file triggers alert within next run.
- [ ] `archive-prune.sh` — enforces retention across all non-projects Jimmy subtrees:
  - `backups/brlogger/` — delete files older than 90 days
  - `backups/supabase/` — keep last 14 daily dumps + 8 weekly (Sunday) + 12 monthly (1st); delete rest
  - `backups/git-mirrors/` — run `git -C <each-mirror> gc --aggressive --prune=now` monthly (first Sunday)
  - `archive/adversarial-reviews/` — keep last 90 days of raw JSON; older: bundle per-month into `YYYY-MM.tar.zst` with level 19, then delete raw
  - `archive/cost-ledger/` — daily rollups kept forever; raw per-request events deleted after 180 days
  - `memory/session-summaries/` — delete summaries older than 180 days (full builds preserved in `build_history` indefinitely)
  - Every delete/compress logged to `/srv/jimmy/logs/archive-prune.log`. Deletes nothing until the corresponding promotion/compression succeeds.
  - Verify: `shellcheck ~/.buildrunner/scripts/archive-prune.sh`; dry-run on a fixture containing one file per subtree at each boundary age prints an exact plan matching the rules above; wet-run on the fixture leaves expected survivors.
- [ ] `lancedb-compact.sh` — quarterly `compact_files()` + `cleanup_old_versions(older_than=7d)` against `/srv/jimmy/lancedb/`. Before running, captures `SELECT COUNT(*) FROM <each_table>`; after running, re-captures and aborts with alert if any count drops. Logs reclaimed bytes to `/srv/jimmy/logs/lancedb-compact.log`.
  - Verify: `shellcheck ~/.buildrunner/scripts/lancedb-compact.sh`; dry-run on a staging LanceDB copy reports rows-pre = rows-post and a non-negative reclaim figure.
- [ ] `disk-guard.sh` — every 15 min on Jimmy. Reads `df -B1 /srv/jimmy | awk 'NR==2 {print $5}'` (usage %). Thresholds:
  - **80%** (WARN): dashboard red banner + one-line `decisions.log` entry (rate-limited to 1/day).
  - **92%** (CRIT): begin **emergency prune** — delete the oldest `backups/projects/YYYY-MM-DD/` daily snapshot, re-check; repeat one-at-a-time until usage ≤ 88%. NEVER touches `monthly/`, `yearly/`, `archive/`, `lancedb/`, `memory/`, or the 7 most recent daily snapshots. Each emergency delete logs to `decisions.log` with the freed-byte count.
  - **96%** (PAGE): in addition to CRIT action, write `/srv/jimmy/status/backups-paused` (read by `nightly-projects-backup.sh` as a hard stop) and raise a dashboard PAGE banner that persists until manually cleared.
  - All state written atomically to `/srv/jimmy/status/disk-guard.json` (usage%, threshold-tier, last-action, next-fire).
  - Verify: `shellcheck ~/.buildrunner/scripts/disk-guard.sh`; simulate 82% → banner appears, no deletes; simulate 93% on a fixture → exactly one oldest-daily deleted, `monthly/` + `yearly/` untouched; simulate 97% → `backups-paused` flag written and nightly-backup refuses to run while flag present.
- [ ] `br3-archive-prune.service` (oneshot) + `br3-archive-prune.timer` (`OnCalendar=*-*-* 04:45:00`, `Persistent=true`). Enabled at boot.
  - Verify: `ssh jimmy 'systemctl is-enabled br3-archive-prune.timer && systemctl list-timers br3-archive-prune.timer | grep "04:45"'` succeeds.
- [ ] `br3-lancedb-compact.service` (oneshot) + `br3-lancedb-compact.timer` (`OnCalendar=*-01,04,07,10-01 03:00:00`, `Persistent=true`). Enabled at boot.
  - Verify: `ssh jimmy 'systemctl is-enabled br3-lancedb-compact.timer && systemctl list-timers --all | grep br3-lancedb-compact'` succeeds; `list-timers` next-fire is on a Jan/Apr/Jul/Oct 1st.
- [ ] `br3-disk-guard.service` (oneshot) + `br3-disk-guard.timer` (`OnUnitActiveSec=15min`, `Persistent=true`). Enabled at boot. Runs BEFORE nightly-backup so the `backups-paused` flag can gate it.
  - Verify: `ssh jimmy 'systemctl is-enabled br3-disk-guard.timer && systemctl is-active br3-disk-guard.timer && systemctl list-timers br3-disk-guard.timer | grep "15min\|15 min"'` succeeds; `cat /srv/jimmy/status/disk-guard.json` exists and parses.
- [ ] `br3-self-health.service` (oneshot) — runs `self_health.py` once per fire.
  - Verify: `ssh jimmy 'systemctl cat br3-self-health.service | grep -E "Type=oneshot"'` succeeds.
- [ ] `br3-self-health.timer` — `OnUnitActiveSec=5min`, `Persistent=true`, `Unit=br3-self-health.service`. Enabled at boot.
  - Verify: `ssh jimmy 'systemctl is-enabled br3-self-health.timer && systemctl is-active br3-self-health.timer && systemctl list-timers --all | grep br3-self-health'` succeeds and shows next-fire ≤5min away.
- [ ] `br3-cost-alerts.service` (oneshot) + `br3-cost-alerts.timer` (`OnCalendar=daily`, `Persistent=true`). Enabled at boot.
  - Verify: `ssh jimmy 'systemctl is-enabled br3-cost-alerts.timer && systemctl list-timers br3-cost-alerts.timer | grep "1 day"'` succeeds.
- [ ] `br3-model-update.service` (oneshot) + `br3-model-update.timer` (`OnCalendar=weekly`, `Persistent=true`). Enabled at boot.
  - Verify: `ssh jimmy 'systemctl is-enabled br3-model-update.timer && systemctl list-timers br3-model-update.timer | grep "1 week"'` succeeds.
- [ ] **Persistent recovery test** — stop Jimmy's `systemd-timesyncd` for 6 minutes (simulates clock skew), restart it, confirm the next `br3-self-health` fire happens within 1 minute (Persistent semantics catch the missed window).
  - Verify: `ssh jimmy 'sudo systemctl stop systemd-timesyncd; sleep 360; sudo systemctl start systemd-timesyncd; sleep 60; journalctl -u br3-self-health.service --since "2 minutes ago" | grep -c Started'` ≥1.
- [ ] Dry-run validation — disconnect Otis 10 min: `auto_rebalance` shifts work; `self_health` flags Otis; recovery on return.
  - Verify: structured log shows reassignment + flag + recovery.
- [ ] **AGENTS.md update** — append to `core/cluster/AGENTS.md`: self-health 5-min cadence (via `.timer`); rebalance no-silent-drop rule; model-update 10% gate (weekly `.timer`); cost-alert 2x threshold (daily `.timer`); backup retention matrix (projects 30d+12m+3y / brlogger 90d / supabase 14d+8w+12m / git-mirrors monthly gc / adversarial 90d raw + monthly `.tar.zst` / cost raw 180d + rollups ∞ / memory summaries 180d); lancedb compact quarterly; disk-guard thresholds 80/92/96%; `backups-paused` flag is the single hard-stop for nightly-backup; cadences are `.timer`-driven, never internal sleep loops. ≤900 added bytes.
  - Verify: `grep -c "self_health\|rebalance\|cost_alert\|.timer\|retention\|disk-guard\|backups-paused" core/cluster/AGENTS.md` ≥7.

#### Claude Review (mandatory before Phase 14 marked complete)

- Reviewer: `claude-opus-4-7` (Muddy)
- Trigger: `/review --phase 14 --target "core/cluster/self_health.py,core/cluster/auto_rebalance.py,~/.buildrunner/scripts/model-update.sh,core/cluster/cost_alerts.py,~/.buildrunner/scripts/{backup-prune,offsite-sync,backup-integrity-check,archive-prune,lancedb-compact,disk-guard}.sh,/etc/systemd/system/br3-{self-health,cost-alerts,model-update,backup-prune,offsite-sync,backup-integrity,archive-prune,lancedb-compact,disk-guard}.{service,timer},core/cluster/AGENTS.md"`
- Required findings: (1) zero silent work-drop; (2) model-update tok/s gate enforced; (3) cost-alert threshold correct; (4) dry-run validation log present for auto-rebalance; (5) **all 9 `.timer` units enabled, active, scheduling correctly with `Persistent=true`** (self-health 5min / cost-alerts daily / model-update weekly / backup-prune 04:30 / offsite-sync Sun 05:00 / backup-integrity Sun 06:00 / archive-prune 04:45 / lancedb-compact quarterly / disk-guard 15min); (6) zero internal `time.sleep()` cadence loops in any Phase 14 service — all are oneshot scripts driven by timers; (7) archive-prune never deletes raw before its compressed bundle is written and fsync'd; (8) disk-guard emergency prune NEVER touches `monthly/`, `yearly/`, `archive/`, `lancedb/`, `memory/`, or the 7 most recent daily snapshots; (9) `backups-paused` flag gates nightly-backup AND is cleared only by manual intervention (never self-cleared); (10) lancedb-compact aborts on any pre/post row-count drop; (11) AGENTS.md updated and cites the full retention matrix + disk-guard thresholds, not sleep loops.
- Block-on: silent drop, missing gate, threshold drift, missing dry-run, ANY of the 9 timers not enabled+active, ANY service running as a long-lived sleep loop instead of oneshot+timer, archive-prune deleting raw before compression verified, disk-guard touching protected subtrees, `backups-paused` self-clearing, lancedb row-count regression uncaught, AGENTS.md stale.

#### Done When

- [ ] Node taken offline detected within 5 min; work rerouted automatically.
- [ ] Model update runs and rolls back on regression.
- [ ] Cost alert fires on simulated spike.
- [ ] All 9 `.timer` units show `is-active=active`, `is-enabled=enabled`, and a future `next-fire` in `systemctl list-timers`.
- [ ] Archive-prune dry-run matches expected plan across all 6 non-projects subtrees; wet-run leaves only expected survivors.
- [ ] LanceDB compact dry-run reports rows-pre = rows-post and non-negative reclaim.
- [ ] Disk-guard WARN/CRIT/PAGE all verified against fixtures; emergency prune never touches protected subtrees; `backups-paused` flag gates nightly-backup.
- [ ] AGENTS.md updated and reviewed with full retention matrix + disk-guard thresholds.
- [ ] Claude review passed with zero P0/P1 findings.
- [ ] `decisions.log` entry: `Phase 14: BR3 self-maintenance live — 9 timers active, auto-rebalance + cost alerts + archive-prune + lancedb-compact + disk-guard, AGENTS.md updated with full retention matrix`.

---

## Out of Scope (Future / Roadmap)

- vLLM / SGLang / vllm-mlx — Ollama is committed. Deferred unless Ollama tok/s becomes the actual bottleneck.
- Langfuse full-stack observability on Jimmy — `cost_ledger` + dashboard panels cover v1. Revisit if detailed trace-level debugging is demanded.
- Codestral FIM / inline completion routing to Below — out of scope for this build.
- Query expansion on the auto-context hook — start with vector + reranker; add expansion only if retrieval quality is poor.
- Multi-round adversarial rebuttal (more than one) — v1 is single rebuttal then escalate.
- MCP hosting on Jimmy — skills still invoked via existing BR3 dispatch.
- Commit-message auto-drafting via Below — manual commits stay.
- Sidecar field rename (`claude_pid/pgid` → `runtime_pid/pgid`) — cosmetic.
- EXO Labs distributed inference — revisit when models exceed 48GB VRAM.
- Fine-tuning custom models on dual 3090s — potential but not in v1.
- Strix Halo node replacement for any M2 — revisit if M2s become bottlenecks.
- 10GbE switch upgrade — upgrade only if vector search latency becomes the bottleneck.
- Mac Studio M4 Max for Muddy daily driver — separate project.
- Third Claude subscription — monitor if 7 workers saturate 1-2 subscriptions.
- Proxmox/VM isolation on Jimmy — bare metal Linux is simpler for v1.
- VRT Docker stack migration from old Lomax to Jimmy — stays on Lomax for v1.
- React dashboard (ui/) full rebuild — Phase 11 adds panels to vanilla HTML; full React port is a separate project.
- Overnight automation (batch /review + /guard + /dead across projects) — build manually first.
- Auto-generated AGENTS.md — formally rejected. ETH Zurich data: −3% task success when LLM-generated. Always human-authored.
- Two-way mutation API for context surface — Phase 12 is read-only by design. Mutation goes through existing dispatch APIs, not the parity bundle.
- Federated context across multiple developer machines — single-developer cluster only for v1.

## Session Log

[Will be updated by /begin]
