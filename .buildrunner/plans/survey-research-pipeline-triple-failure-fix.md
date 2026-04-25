# Prior-State Survey: research-pipeline-triple-failure-fix

## Prior BUILDs

- `BUILD_research-multi-llm.md` — **COMPLETE (7 phases)**. Built `~/.buildrunner/scripts/llm-dispatch.sh`, `~/.buildrunner/scripts/llm-clients/perplexity.py`, and the `/research` skill at `~/.claude/commands/research.md`. **All five files this fix touches were originally created or last modified by this build.** Phases 4 (adversarial review wiring) and 6 (queue/worker) are the most directly relevant.
- `BUILD_research-vectorization.md` — **COMPLETE**. Built the LanceDB indexing path on Jimmy. Established the `_research_stats` / `total_chunks` shape that `_extract_chunk_count` falls back on. Reindex job-id contract being added in Phase 3 of this fix did not exist when this build shipped.
- `BUILD_cluster-max-research-library.md` — **COMPLETE (7 phases)**. Built `node_semantic.py` `/api/research/*` endpoints on Jimmy. `/api/research/reindex` and `/api/research/stats` were established here as async/global-state respectively. Phase 3 of this fix changes that contract.

## Shared-Surface Impact

- `~/.claude/commands/research.md` — used only by `/research`; no other callers. Phase 1 + Phase 2 modifications are scoped to this consumer. Safe.
- `~/.buildrunner/scripts/llm-dispatch.sh` — also called by `core/cluster/cross_model_review.py` and `~/.buildrunner/scripts/adversarial-review.sh` (consensus path). Phase 1's wildcard-handler change (silent → loud failure) MAY surface latent bad calls from those callers. Verify both still pass their existing test paths.
- `~/.buildrunner/scripts/llm-clients/perplexity.py` — used by `llm-dispatch.sh perplexity` only. New optional args (`search_domain_filter`, `search_recency_filter`) are additive and backward-compatible. Safe.
- `core/cluster/below/research_worker.py` — only consumer is the launchd agent `com.buildrunner.below-worker.plist`. New `indexing_pending` state requires `CompletedRecord` schema acceptance — confirm `~/.claude/sessions/research-pending.json` sidecar reader and Step 0 of the `/research` skill tolerate the new value.
- `core/cluster/node_semantic.py` on Jimmy — `/api/research/reindex` is called by the worker AND by the `/research` skill's manual-reindex fallback message. Adding `job_id` to the response is additive (existing callers ignore unknown fields). The new `/api/research/reindex/<job_id>` endpoint is purely additive. Safe.

## Governance Drift

- No `.buildrunner/governance.yaml` exists in this repo.
- `~/.buildrunner/config/default-role-matrix.yaml` — verify `backend-build` bucket default matches expected codex effort/model for this fix's complexity.
- `core/cluster/AGENTS.md` rule: "Below NEVER drafts final diagnoses, final code, frontend/UX, or architecture decisions." — Phase 5's instrumentation is observability code; safe. Phase 3's API contract change is architecture — must be done by Claude/Codex on Muddy, not Below.
- `core/cluster/AGENTS.md` rule: "Muddy → Jimmy: rsync." — Phase 3 deploys `node_semantic.py` changes to Jimmy via existing rsync path. No new deploy mechanism required.

## Completed-Phase Blast Radius

- `BUILD_research-multi-llm.md` Phase 4 (adversarial review wiring) — **directly re-modified by Phase 1 of this fix**. Phase 4 introduced the broken `--body-file` flag pattern and the broken envelope parser. This fix corrects those. Locked completed phase being touched, but the touch is a bug fix to that exact phase's deliverables.
- `BUILD_research-multi-llm.md` Phase 6 (queue/worker) — **re-modified by Phases 3, 4, 5 of this fix**. Phase 6 introduced `_wait_for_reindex` and the silent `status: ok` on timeout. This fix corrects those.
- `BUILD_cluster-max-research-library.md` Phase N (Jimmy reindex API) — **re-modified by Phase 3 of this fix**. The async-fire-and-forget contract from that phase becomes job-id-correlated.

**Net assessment:** This fix is a remediation of three known-buggy completed phases. Completed-phase locks are intentionally being broken to fix bugs the original phases shipped. Decision logged: surfaced, not blocking.
