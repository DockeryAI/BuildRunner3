# Build: Below Offload Program

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_0: { bucket: backend-build, assigned_node: muddy }
      phase_1: { bucket: terminal-build, assigned_node: muddy }
      phase_2: { bucket: backend-build, assigned_node: below }
      phase_3: { bucket: backend-build, assigned_node: below }
      phase_4: { bucket: backend-build, assigned_node: below }
      phase_5: { bucket: terminal-build, assigned_node: below }
      phase_6: { bucket: terminal-build, assigned_node: muddy }
      phase_7: { bucket: terminal-build, assigned_node: muddy }
      phase_8: { bucket: terminal-build, assigned_node: muddy }
      phase_9: { bucket: terminal-build, assigned_node: muddy }
      phase_10: { bucket: backend-build, assigned_node: muddy }
      phase_11: { bucket: terminal-build, assigned_node: muddy }
      phase_12: { bucket: terminal-build, assigned_node: muddy }
      phase_13: { bucket: backend-build, assigned_node: below }
      phase_14: { bucket: review, assigned_node: muddy }
      phase_15: { bucket: terminal-build, assigned_node: muddy }
      phase_16: { bucket: backend-build, assigned_node: muddy }
```

**Created:** 2026-04-23
**Status:** Phases 1-11 Complete — Phase 5 In Progress
**Deploy:** web — `npm run build && deploy`
**Source Plan File:** .buildrunner/plans/plan-below-offload.md
**Source Plan SHA:** 4fe80ce08f49a668d634f82cfe01721cde65c042ace4c24de78c1117abd0f1d4
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-23T16:30:54Z

## Overview

Move every Claude/paid-API workload that Below can handle at parity to Below, reducing token spend and latency without touching quality. Bundles the five previously committed items (commit messages, reranker enable, semantic cache, log clustering, JSON-schema classifier migration) with eight newly-validated proven offload patterns from multi-model research.

Shared infrastructure (Phases 0–4) builds an embedding client, schema-constrained classifier library, clustering library, and semantic cache. Consumer phases (5–16) adopt these libraries across /commit, /ship, intel collect, CI classifier, /root, /dbg, /sdb, /diag, /device, /query, auto-remediate, dependency triage, autopilot dispatch, ai_code_review, PR body generation, and /begin spec-drift detection.

## Parallelization Matrix

| Phase | Key Files                                                                                                | Can Parallel With     | Blocked By |
| ----- | -------------------------------------------------------------------------------------------------------- | --------------------- | ---------- |
| 0     | requirements-api.txt, core/cluster/below/embed.py                                                        | 1, 5, 15              | -          |
| 1     | api/routes/retrieve.py, core/cluster/reranker.py, core/cluster/context_bundle.py, scripts/service-env.sh | 0, 2, 3, 4, 5, 13, 15 | -          |
| 2     | core/cluster/below/schema_classifier.py                                                                  | 0, 1, 3, 4, 5, 13, 15 | 0          |
| 3     | core/cluster/below/log_cluster.py                                                                        | 0, 1, 2, 4, 5, 13, 15 | 0          |
| 4     | core/cluster/below/semantic_cache.py                                                                     | 0, 1, 2, 3, 5, 13, 15 | 0          |
| 5     | $HOME/.buildrunner/scripts/commit-br3-housekeeping.sh                                                    | 0, 1, 2, 3, 4, 13, 15 | -          |
| 6     | $HOME/.buildrunner/scripts/auto-remediate.mjs, adversarial-review.sh, cross-model-review.sh              | 9, 10, 14             | 2          |
| 7     | $HOME/.claude/commands/{dbg,sdb,diag,device,query}.md, developer-brief.sh, node_analysis.py              | 8, 10, 14             | 3          |
| 8     | $HOME/.buildrunner/scripts/ship/ci/ci-classifier.sh, commands/root.md, test_failure_cluster.py           | 7, 10, 14             | 3, 9       |
| 9     | $HOME/.buildrunner/scripts/ship/ci/ci-classifier.sh                                                      | 6, 10, 11, 14         | 2          |
| 10    | core/opus_client.py, core/ai_code_review.py, claude_cache_wrapper.py                                     | 6, 7, 8, 9, 14        | 4          |
| 11    | core/cluster/scripts/collect-intel.sh                                                                    | 6, 9, 10, 14          | 2          |
| 12    | $HOME/.buildrunner/scripts/auto-remediate.mjs (dep section)                                              | 9, 10, 11, 14         | 2, 6       |
| 13    | $HOME/.buildrunner/scripts/autopilot-dispatch-prefix.sh, collect-intel.sh, llmlingua_compress.py         | 1, 2, 3, 4            | 11         |
| 14    | core/ai_code_review.py (prefilter), semgrep_triage.py                                                    | 6, 7, 8, 9, 11, 12    | 2, 10      |
| 15    | $HOME/.buildrunner/scripts/ship/ci/pr-body-gen.sh, pr_body.py                                            | 0, 1, 2, 3, 4, 5, 13  | -          |
| 16    | $HOME/.claude/commands/begin.md, core/runtime/workflows/begin_workflow.py, spec_drift.py                 | 7, 10                 | 0          |

**Wave structure:**

- **Wave A (parallel):** 0, 1, 5, 15
- **Wave B (parallel, after 0):** 2, 3, 4, 13
- **Wave C (parallel, after 2 and/or 3):** 6, 7, 9, 11, 16
- **Wave D (after 4):** 10
- **Wave E (after 3 + 9):** 8
- **Wave F (after 2 + 6):** 12
- **Wave G (after 2 + 10):** 14

## Phases

### Phase 0: Shared embedding client + dependency manifests

**Status:** ✅ COMPLETE
**Files:**

- core/cluster/below/**init**.py (NEW)
- core/cluster/below/embed.py (NEW)
- requirements-api.txt (MODIFY)
- pyproject.toml (MODIFY if present)
- tests/cluster/test_below_embed.py (NEW)

**Blocked by:** None
**Deliverables:**

- [x] Reusable `embed_batch(texts: list[str]) -> list[list[float]]` wrapper on Below `/api/embed` with nomic-embed-text
- [x] Timeout, retry, and circuit breaker
- [x] Pin scikit-learn>=1.4, sqlite-vec>=0.1, llmlingua>=0.2.2 in requirements-api.txt
- [x] Document semgrep as a system/dev dep in README
- [x] Unit tests: happy path, Below-offline fallback, malformed response

**Success Criteria:** `embed_batch` returns consistent 768-d vectors; dep install succeeds in a fresh venv.

### Phase 1: Enable bge-reranker (service env + metrics)

**Status:** ✅ COMPLETE
**Files:**

- api/routes/retrieve.py (MODIFY if uses reranker)
- core/cluster/reranker.py (MODIFY)
- core/cluster/context_bundle.py (MODIFY)
- scripts/service-env.sh (NEW or MODIFY)
- docs/reranker-ops.md (NEW)

**Blocked by:** None
**Deliverables:**

- [x] Set BR3_AUTO_CONTEXT=on in service launch env; NOT in .claude/settings.json
- [x] Verify reranker fires for /retrieve and context-bundle paths
- [x] Confirm context-bundle callers supply non-empty query
- [x] Add metrics: rerank invocations, top_k distribution, latency
- [x] Document top_k tuning (no similarity threshold exists)
- [x] Smoke test on recorded /retrieve fixtures

**Success Criteria:** Reranker fires on every context bundle call with a query; metrics emit to lockwood-metrics.

### Phase 2: Schema-constrained classifier library on Below

**Status:** ✅ COMPLETE
**Files:**

- core/cluster/below/schema_classifier.py (NEW)
- tests/cluster/test_schema_classifier.py (NEW)

**Blocked by:** Phase 0
**Deliverables:**

- [x] Ollama `/api/chat` wrapper with `format: <json_schema>`
- [x] Pydantic schema validation on output
- [x] Fallback-to-Claude harness (caller injects Claude fn)
- [x] Configurable retry budget (default 2) before fallback
- [x] Success metrics measured separately at qwen2.5:14b AND qwen3:8b

**Success Criteria:** `<2%` fallback rate at qwen2.5:14b; `<5%` at qwen3:8b on synthetic load.

### Phase 3: Embedding + DBSCAN clustering library on Below

**Status:** ✅ COMPLETE
**Files:**

- core/cluster/below/log_cluster.py (NEW)
- tests/cluster/test_log_cluster.py (NEW)
- tests/fixtures/cluster_benchmark.jsonl (NEW)

**Blocked by:** Phase 0
**Deliverables:**

- [x] Use core/cluster/below/embed.py for batch embeddings
- [x] DBSCAN with tuned eps and min_samples defaults
- [x] Return shape exposes `clusters` AND `outliers` (DBSCAN label -1)
- [x] Representative selection (longest shared prefix or most-central)
- [x] Build project-local benchmark fixture with labeled ground truth

**Success Criteria:** Precision ≥95% on project benchmark; outliers surfaced correctly for 100% of singletons.

### Phase 4: Semantic answer cache infrastructure

**Status:** ✅ COMPLETE
**Files:**

- core/cluster/below/semantic_cache.py (NEW)
- tests/cluster/test_semantic_cache.py (NEW)
- .gitignore (MODIFY)

**Blocked by:** Phase 0
**Deliverables:**

- [x] sqlite-vec table keyed by `(model, method_name, prompt_embedding, normalized_prompt_hash)`
- [x] DB file at $HOME/.buildrunner/state/answer_cache.db (NOT in repo)
- [x] `lookup(model, method, prompt)` with configurable threshold (default 0.95)
- [x] `store(model, method, prompt, answer)` with TTL eviction
- [x] Admin CLI: `below-cache inspect | clear | stats`
- [x] Cache-warming mode (log-only for N runs before serving)

**Success Criteria:** 0 false-positive hits at 0.95 threshold; no cross-model bleed.

### Phase 5: Commit message generation → qwen2.5-coder

**Status:** ✅ COMPLETE
**Files:**

- $HOME/.buildrunner/scripts/commit-br3-housekeeping.sh (MODIFY)
- $HOME/.buildrunner/scripts/lib/below-commit-msg.sh (NEW)

**Blocked by:** None
**Deliverables:**

- [x] Tier 1: Below qwen2.5-coder with conventional-commit prompt
- [x] Tier 2: Claude fallback on empty/malformed
- [x] Tier 3: Static template fallback when both unreachable
- [x] Output shape validation (`<type>(<scope>): <subject>` regex)
- [x] Fallback-tier metric; integration test on 10 BR3 diffs

**Success Criteria:** ≥85% commits accepted at tier 1; 0 commits hang when offline.

### Phase 6: JSON-schema classifier migration (existing call sites)

**Status:** ✅ COMPLETE
**Files:**

- $HOME/.buildrunner/scripts/auto-remediate.mjs (MODIFY)
- core/cluster/cross_model_review.py (MODIFY — below_prescreen routing)

**Blocked by:** Phase 2
**Deliverables:**

- [x] Convert auto-remediate novel-type routing to Below qwen3:8b schema classifier
- [x] Convert cross-model-review routing: Below qwen3:8b obvious-PASS pre-screen before full review
- [x] Fallback rate metric logged to schema-classifier-metrics.jsonl per site
- [x] BR3_BELOW_PRESCREEN=off rollback flag; security keyword guard; 8KB size cap
- [x] (governance_enforcer dropped — no classifier call exists; adversarial-review.sh delegates to Python, no inline classifier)

**Success Criteria:** Fallback rate <5% per call site on a 100-run sample.

### Phase 7: Log clustering in /dbg, /sdb, /diag, /device, /query

**Status:** ✅ COMPLETE
**Files:**

- $HOME/.buildrunner/scripts/developer-brief.sh (MODIFY)
- core/cluster/node_analysis.py (MODIFY)
- $HOME/.buildrunner/scripts/lib/log-cluster.py (NEW)
- $HOME/.claude/commands/dbg.md (MODIFY)
- $HOME/.claude/commands/sdb.md (MODIFY)
- $HOME/.claude/commands/diag.md (MODIFY)
- $HOME/.claude/commands/device.md (MODIFY)
- $HOME/.claude/commands/query.md (MODIFY)

**Blocked by:** Phase 3
**Deliverables:**

- [x] log-cluster.py stdin helper: reads log lines, calls cluster_lines(), outputs format_cluster_summary()
- [x] Wire clustering (Step 2.5) into /dbg, /sdb, /device, /query; Step 1.75 into /diag
- [x] Preserve cluster representative + frequency + outlier list in summary
- [x] Automatic fail-open on Below/embed failure (exit code 1, no output = use raw log)
- [x] Rollback flag BR3_LOG_CLUSTER=off (both helper and library)
- [x] developer-brief.sh: pre-cluster browser.log + supabase.log into brief log section
- [x] node_analysis.py: /api/logs/clusters endpoint for programmatic access

**Success Criteria:** ≥30% token reduction vs baseline; 0 outages from Below-offline.

### Phase 8: Test failure clustering before /root analysis

**Status:** not_started
**Files:**

- $HOME/.buildrunner/scripts/ship/ci/ci-classifier.sh (MODIFY — cluster integration only)
- $HOME/.claude/commands/root.md (MODIFY)
- core/cluster/below/test_failure_cluster.py (NEW)
- tests/cluster/test_test_failure_cluster.py (NEW)

**Blocked by:** Phase 3, Phase 9
**Deliverables:**

- [ ] Baseline: /root on multi-failure run with clustering OFF; record tokens
- [ ] Cluster CI failures via library (uses Phase 3 outlier exposure)
- [ ] Preserve outliers (cluster size 1) — never drop
- [ ] Pass representative + frequency + outlier list to /root
- [ ] Automatic fail-open on Below/embed failure
- [ ] Rollback flag BR3_TEST_CLUSTER=off

**Success Criteria:** /root context tokens reduced ≥25% vs baseline; 0 outages from Below-offline.

### Phase 9: CI classifier → qwen3:8b hybrid

**Status:** ✅ COMPLETE
**Files:**

- $HOME/.buildrunner/scripts/ship/ci/ci-classifier.sh (MODIFY)
- tests/fixtures/ci_failures.jsonl (NEW — 21 labeled CI failure records)
- tests/test_ci_classifier.py (NEW — 12 tests, 100% pass)

**Blocked by:** Phase 2
**Deliverables:**

- [x] Regex path first (speed) — expanded patterns for ESLint, Prettier, ruff, black, isort, Playwright
- [x] Below qwen3:8b via schema classifier on regex miss (BR3_CI_CLASSIFY=hybrid)
- [x] Emit novel-pattern hits to decisions.log + schema-classifier-metrics.jsonl
- [x] Rollback flag BR3_CI_CLASSIFY=regex-only
- [x] Accuracy regression test: 21 labeled records, 100% accuracy on regex path

**Success Criteria:** Novel-pattern detection ≥80%; accuracy ≥90% on labeled set.

### Phase 10: Semantic cache integration across Claude call sites

**Status:** ✅ COMPLETE
**Files:**

- core/opus_client.py (MODIFY — _cached_call() helper, all methods routed through wrapper)
- core/ai_code_review.py (MODIFY — cache bypass comment added, direct client retained per exclusion)
- core/cluster/below/claude_cache_wrapper.py (NEW)
- tests/test_claude_cache_wrapper.py (NEW — 17 tests, 100% pass)

**Blocked by:** Phase 4
**Deliverables:**

- [x] ClaudeCacheWrapper.call(model, method, messages, *, skip_cache=False) → str
- [x] opus_client._cached_call() routes pre_fill_spec, analyze_requirements, generate_design_tokens, validate_spec through cache
- [x] ai_code_review bypasses cache per exclusion list (review_diff, analyze_architecture)
- [x] Exclusion list: ai_code_review, adversarial_review, arbiter, reviewer, review_diff, analyze_architecture
- [x] 7-day warm-up period (log-only, configurable via warmup_days=0 in tests)
- [x] Metrics: hit rate, skip reasons, latency to cache-wrapper-metrics.jsonl
- [x] get_wrapper() singleton; BR3_SEMANTIC_CACHE=off rollback

**Success Criteria:** Hit rate ≥15% on autopilot; 0 false positives in warm-up; ai_code_review bypasses cache 100%.

### Phase 11: Intel collect stage 1/2 → Below

**Status:** not_started
**Files:**

- core/cluster/scripts/collect-intel.sh (MODIFY — stages 1 and 2 only)

**Blocked by:** Phase 2, Phase 13
**Deliverables:**

- [ ] Replace `claude -p` at intel pipeline stage 1 (sources) and stage 2 (categorize) with below-route qwen3:8b
- [ ] Structured extraction schema mirrors hunt_sources/bhphoto.py, newegg.py
- [ ] Keep Opus for intel pipeline stage 3 (BR3-specific narrative)
- [ ] Snapshot regression test: tests/fixtures/intel_snapshot.jsonl
- [ ] Metric: Claude call count reduction vs prior week

**Success Criteria:** ≥80% Claude token reduction in intel pipeline; categorization accuracy parity ±5%.

### Phase 12: Dependency update triage → qwen2.5:14b

**Status:** not_started
**Files:**

- $HOME/.buildrunner/scripts/auto-remediate.mjs (MODIFY — dep triage section only)
- $HOME/.buildrunner/scripts/lib/below-dep-triage.sh (NEW)

**Blocked by:** Phase 2, Phase 6
**Deliverables:**

- [ ] Changelog diff parsing helper
- [ ] qwen2.5:14b schema classifier: `{action, reasoning}`
- [ ] Route major bumps to Claude; patch/minor to local classifier
- [ ] Route decision logged
- [ ] Integration test on 20 representative dep updates

**Success Criteria:** Classification accuracy ≥90%; ≥70% handled locally.

### Phase 13: LLMLingua-2 prompt compression on dispatch

**Status:** not_started
**Files:**

- core/cluster/below/llmlingua_compress.py (NEW)
- $HOME/.buildrunner/scripts/autopilot-dispatch-prefix.sh (MODIFY)
- core/cluster/scripts/collect-intel.sh (MODIFY — dispatch prefix only)

**Blocked by:** Phase 11
**Deliverables:**

- [ ] Install llmlingua PyPI package (not GGUF; CPU/CUDA via HF transformers)
- [ ] Compression helper with configurable ratio (default 0.5)
- [ ] Wire into autopilot dispatch prefix and intel-collect dispatch prefix
- [ ] Exclusion list in wrapper: adversarial-review, arbiter, ai_code_review, cross-model-review, reviewer dispatches
- [ ] Measure compression ratio + autopilot phase success delta

**Success Criteria:** Mean compression ≥3x on eligible prompts; autopilot success delta <3%.

### Phase 14: Static analysis prefilter for ai_code_review (downgrade, never skip)

**Status:** not_started
**Files:**

- core/ai_code_review.py (MODIFY)
- core/cluster/below/semgrep_triage.py (NEW)
- tests/test_semgrep_triage.py (NEW)

**Blocked by:** Phase 2, Phase 10
**Deliverables:**

- [ ] Semgrep on diff (p/ci, p/security-audit, p/owasp-top-ten + project-local rules)
- [ ] qwen2.5-coder:7b classifies `{severity: clean | minor | flagged}`
- [ ] clean → downgrade Opus call to quick-pass (not skip)
- [ ] minor | flagged → full Opus review unchanged
- [ ] Red-team test: inject non-static defect; verify downgraded review catches it
- [ ] Rule-coverage validation against OWASP Top 10 categories

**Success Criteria:** ≥30% token reduction on clean diffs; 100% red-team defects caught; 0 OWASP categories missing.

### Phase 15: PR body generation → qwen2.5-coder

**Status:** ✅ COMPLETE
**Files:**

- $HOME/.buildrunner/scripts/ship/ci/pr-body-gen.sh (CREATE or MODIFY — verify at phase start)
- core/cluster/below/pr_body.py (NEW)

**Blocked by:** None
**Deliverables:**

- [x] Confirm pr-body-gen.sh exists; create + wire into /ship if absent
- [x] Replace static template with qwen2.5-coder diff-to-PR-body
- [x] Architectural-keyword router escalates to Claude
- [x] Fallback to static template on empty/malformed
- [x] 10-PR integration test

**Success Criteria:** ≥70% of PRs handled by Below; human-acceptability ≥90%.

### Phase 16: Spec-drift detection at /begin step 0

**Status:** ✅ COMPLETE
**Files:**

- $HOME/.claude/commands/begin.md (MODIFY — project-scoping guard)
- core/runtime/workflows/begin_workflow.py (MODIFY)
- core/cluster/below/spec_drift.py (NEW)
- tests/test_spec_drift.py (NEW)

**Blocked by:** Phase 0
**Deliverables:**

- [x] spec_drift.py uses core/cluster/below/embed.py (no coupling to log_cluster internals)
- [x] Embedding comparison between BUILD spec and current codebase
- [x] Integrate into begin_workflow.py step 0 (not governance_enforcer)
- [x] Project-scoping guard in begin.md: skip when no BUILD spec exists
- [x] Surface drift candidates; advisory only, no auto-fix
- [x] Integration test on BUILD with injected drift

**Success Criteria:** Detects injected drift; zero false positives on clean baseline; silent skip in non-BR3 projects.

## Out of Scope

- Migrating adversarial-review, arbiter, ai_code_review reasoning to Below (quality-sensitive)
- Replacing Opus 4.7 in intel collect stage 3 (BR3-specific narrative)
- Draft-model speculative decoding via Anthropic API (not in public API as of 2026-04)
- Multi-provider cache sharing across projects
- LLMLingua on ai_code_review / adversarial / arbiter / cross-model-review / reviewer dispatch paths
- Fixing pre-existing `_RESEARCH_LIBRARY` path violation in context_bundle.py (separate remediation)

## Session Log

Will be updated by /begin.
