# Bypass Justification: plan-below-offload

**Plan:** `.buildrunner/plans/plan-below-offload.md`
**Date:** 2026-04-23
**Review outcome:** BLOCKED (Claude + Codex consensus, arbiter circuit_open)
**Bypass authority:** /spec skill 1-review rule (fix inline, do not re-run)

## Blockers addressed inline

1. Phase 13 LLMLingua install path: corrected from "GGUF on Ollama" (incompatible — LLMLingua-2 is BERT-family) to PyPI `llmlingua` package on CPU/CUDA via HF transformers.
2. Phase 1 `BR3_AUTO_CONTEXT` location: moved from `.claude/settings.json` to `scripts/service-env.sh` — the reranker reads the flag from process env at import.
3. Phase 1 scope: added `api/routes/retrieve.py` to covered files and noted the context-bundle reranker only fires when a non-empty query is supplied.
4. Phase 0 added: shared embedding client (`core/cluster/below/embed.py`) + dependency manifest updates (scikit-learn, sqlite-vec, llmlingua pinned in requirements-api.txt) — unblocks phases 3, 4, 13, 14, 16.
5. Path convention clarified: `$HOME/.buildrunner/scripts/*` and `$HOME/.claude/skills/*.md` are user-global assets, not repo-relative. Every phase touching them uses the `$HOME/` prefix.
6. Phase 6 governance_enforcer deliverable dropped — file has no Claude classifier call to convert (confirmed by review).
7. Phase 10 expanded: added `claude_cache_wrapper.py`; both `opus_client.py` and `ai_code_review.py` route through it; `skip_cache` parameter enforces the exclusion list.
8. Phase 16 target fixed: moved from `governance_enforcer.py` to `core/runtime/workflows/begin_workflow.py` (correct subsystem for /begin).
9. Phase 11 scope corrected: dropped `intel_scoring.py` (already on Below); kept only `collect-intel.sh` stages 1/2. Renamed intel pipeline stages to avoid collision with build-plan phase numbering.
10. Parallelization matrix: file-conflict violations fixed — phases 8/9 (ci-classifier.sh), 6/12 (auto-remediate.mjs), 11/13 (collect-intel.sh) serialized via `Blocked by`.
11. Phase 4 `answer_cache.db` removed from source-controlled files; relocated to runtime state path under `$HOME/.buildrunner/state/` with `.gitignore` entry. Cache key expanded to include `(model, method_name)` to prevent cross-model response bleed.
12. Phase 5 commit-hook offline path: added tier-3 static template fallback so commits never hang when both Below and Claude are unreachable.
13. Phase 7, 8 fail-open: clustering steps fall through to current pipeline on Below/embed failure; no user-visible outage.
14. Phase 14 changed from "auto-dismiss clean diffs" to "downgrade to a single quick-pass prompt" — preserves reviewer's broader mandate (bugs, performance, test coverage). Added red-team test for non-static defects and OWASP coverage validation.
15. Phase 3 API: now exposes DBSCAN outlier labels (cluster -1) so Phase 8's outlier-preservation guarantee is implementable. Replaced undefined "LogSage-style test set" with project-local benchmark fixture.
16. Phase 2 validation extended: success metrics now measured separately at qwen2.5:14b AND qwen3:8b (Phase 9's model).
17. Phase 7, 8 baseline capture added as explicit deliverable so `≥30%`/`≥25%` token-reduction success criteria are measurable.
18. Phase 8 test file relocated from `core/routing/` to `tests/cluster/`, matching project convention.
19. Phase 1 reranker `top_k` tuning replaces nonexistent "similarity threshold" deliverable.
20. Phase 16 `begin.md` project-scoping guard added — drift check only runs when a BUILD spec exists; silent skip otherwise (prevents breaking /begin in non-BR3 projects).

## Blockers NOT addressed

- Pre-existing `_RESEARCH_LIBRARY = HOME / 'Projects' / 'research-library'` violation in `context_bundle.py`: moved to Out of Scope. Not introduced by this plan; separate remediation track.
- Arbiter circuit_open state: runtime infra issue; does not affect the plan's technical validity.

## Decision

Per skill's explicit 1-review + inline-fix rule, proceeding to Step 3.8 without re-running adversarial review.
