# Plan: Below Offload Program

**Purpose:** Move every Claude/paid-API workload that Below can handle at parity to Below, reducing token spend and latency without touching quality. Bundle the five previously committed items (commit messages, reranker enablement, semantic cache, log clustering, JSON-schema classifier migration) with eight newly-validated proven offload patterns from multi-model research.

**Target users:** BR3 autopilot harness, /commit, /ship, /dbg, /sdb, /diag, /root, /begin, /auto-remediate, intel collection pipeline, ai_code_review, cross_model_review.

**Tech stack:** Ollama on Below (qwen2.5-coder:7b, qwen2.5:14b, qwen3:8b, llama3.3:70b, nomic-embed-text), LLMLingua-2 (Python package), Semgrep, sqlite-vec, LanceDB (Jimmy), BAAI/bge-reranker-v2-m3 (Jimmy, already deployed).

**Path conventions used in this plan:**

- Repo-relative paths (e.g. `core/ai_code_review.py`) are inside `~/Projects/BuildRunner3`.
- `$HOME/.buildrunner/scripts/*` and `$HOME/.claude/skills/*.md` paths are **user-global** assets. They are not in the project tree but are absolutely required targets — BR3 is the framework, the scripts and skills are its user-level surface. Each phase that touches them lists them with the `$HOME/` prefix.

---

## Scope

Thirteen consumer offload opportunities plus four shared-infrastructure phases.

**Infrastructure (build once, consume many):**

- Shared embedding client (`core/cluster/below/embed.py`) used by clustering, spec-drift, and semantic cache
- Schema-constrained classifier library with fallback harness
- Embedding + DBSCAN clustering library (exposes outlier labels)
- Semantic answer cache (sqlite-vec, keyed by `{model, method, prompt_embedding, prompt_hash}`)

**Consumers (committed five):** reranker enable; commit messages; JSON-schema classifier migration; log clustering; semantic cache integration.

**Consumers (new additions):** intel collect stage 1/2; CI classifier hybrid; test failure clustering; dep update triage; PR body gen; static analysis prefilter; LLMLingua compression; spec-drift detection.

---

## Phase Plan

### Phase 0: Shared embedding client + dependency manifests

**Files:** `core/cluster/below/__init__.py` (NEW), `core/cluster/below/embed.py` (NEW), `requirements-api.txt` (MODIFY), `pyproject.toml` (MODIFY if present), `tests/cluster/test_below_embed.py` (NEW)
**Blocked by:** None
**Deliverables:**

- Reusable `embed_batch(texts: list[str]) -> list[list[float]]` wrapper on Below `/api/embed` with nomic-embed-text
- Timeout, retry, and circuit breaker
- Pin new runtime deps in `requirements-api.txt`: `scikit-learn>=1.4` (for DBSCAN), `sqlite-vec>=0.1`, `llmlingua>=0.2.2`, `semgrep` as a dev/runtime target via system package (not pip — documented in README)
- Unit tests covering happy path, Below-offline fallback, malformed response
  **Success:** `embed_batch` returns consistent 768-d vectors; dep install succeeds in a fresh venv.

### Phase 1: Enable bge-reranker (service env + metrics)

**Files:** `api/routes/retrieve.py` (MODIFY if uses reranker), `core/cluster/reranker.py` (MODIFY), `core/cluster/context_bundle.py` (MODIFY), `scripts/service-env.sh` (NEW or MODIFY), `docs/reranker-ops.md` (NEW)
**Blocked by:** None
**Deliverables:**

- Set `BR3_AUTO_CONTEXT=on` in the service launch env (`scripts/service-env.sh` sourced by the Jimmy retrieval service and by the local context-bundle caller). `.claude/settings.json` is NOT a valid location — `AUTO_CONTEXT_ENABLED` is read from process env at import.
- Verify reranker fires for both `/retrieve` and context-bundle paths (the context bundle reranks only when a non-empty query is passed — confirm callers supply one).
- Add metric logging for rerank invocations, `top_k` distribution, and latency
- Document `top_k` tuning (reranker has no similarity threshold; tuning is top_k only)
- Smoke test on recorded `/retrieve` fixtures
  **Success:** Reranker fires on every context bundle call with a query; metrics emit to lockwood-metrics.

### Phase 2: Schema-constrained classifier library on Below

**Files:** `core/cluster/below/schema_classifier.py` (NEW), `tests/cluster/test_schema_classifier.py` (NEW)
**Blocked by:** Phase 0
**Deliverables:**

- Reusable helper that calls Ollama `/api/chat` with `format: <json_schema>`
- Pydantic schema validation on output
- Fallback-to-Claude harness on validation failure or timeout (caller injects Claude fn; library stays decoupled)
- Configurable retry budget (default 2) before fallback
- Validate at both model sizes used downstream: **qwen2.5:14b** AND **qwen3:8b** — separate success metrics per model
  **Success:** `<2%` fallback rate on synthetic load at qwen2.5:14b; `<5%` at qwen3:8b.

### Phase 3: Embedding + DBSCAN clustering library on Below

**Files:** `core/cluster/below/log_cluster.py` (NEW), `tests/cluster/test_log_cluster.py` (NEW), `tests/fixtures/cluster_benchmark.jsonl` (NEW)
**Blocked by:** Phase 0
**Deliverables:**

- Use `core/cluster/below/embed.py` for batch embeddings (no duplicate embed path)
- DBSCAN with tuned `eps` and `min_samples` defaults
- Returned structure exposes: `clusters: list[{representative, frequency, member_indices}]` AND `outliers: list[{index, text}]` (DBSCAN label -1) — consumers rely on outlier visibility
- Clear cluster-to-representative selection (longest shared prefix or most-central member)
- Build project-local benchmark fixture (`tests/fixtures/cluster_benchmark.jsonl`) with labeled ground truth; replace undefined "LogSage-style" reference
  **Success:** Precision ≥95% on project benchmark; outliers surfaced correctly for 100% of singletons.

### Phase 4: Semantic answer cache infrastructure

**Files:** `core/cluster/below/semantic_cache.py` (NEW), `tests/cluster/test_semantic_cache.py` (NEW), `.gitignore` (MODIFY)
**Blocked by:** Phase 0
**Deliverables:**

- sqlite-vec table keyed by `(model, method_name, prompt_embedding, normalized_prompt_hash)` — NOT prompt-only (avoids mixing responses across models/methods)
- DB file lives at runtime path (`$HOME/.buildrunner/state/answer_cache.db`), NOT in repo; add the runtime dir pattern to `.gitignore`
- `lookup(model, method, prompt) -> Optional[answer]` with configurable similarity threshold (default 0.95)
- `store(model, method, prompt, answer)` with TTL eviction
- Admin CLI: `below-cache inspect`, `below-cache clear`, `below-cache stats`
- Cache-warming mode (log hit candidates for N runs before serving)
  **Success:** 0 false-positive hits at 0.95 threshold on curated test set; no cross-model bleed.

### Phase 5: Commit message generation → qwen2.5-coder

**Files:** `$HOME/.buildrunner/scripts/commit-br3-housekeeping.sh` (MODIFY), `$HOME/.buildrunner/scripts/lib/below-commit-msg.sh` (NEW)
**Blocked by:** None (freeform generation + regex validation; no schema library needed)
**Deliverables:**

- Tier 1: Below qwen2.5-coder with conventional-commit prompt
- Tier 2: Claude fallback on empty/malformed
- Tier 3: Static template fallback when both Below AND Claude unreachable (commit hook must not hang offline)
- Output shape validation (`<type>(<scope>): <subject>` regex)
- Emit fallback-tier metric; integration test on 10 BR3 diffs
  **Success:** ≥85% commits accepted at tier 1 on typical workload; 0 commits hang.

### Phase 6: JSON-schema classifier migration (real existing call sites only)

**Files:** `$HOME/.buildrunner/scripts/auto-remediate.mjs` (MODIFY), `$HOME/.buildrunner/scripts/adversarial-review.sh` (MODIFY — classifier sections only), `$HOME/.buildrunner/scripts/cross-model-review.sh` (MODIFY — routing decisions only)
**Blocked by:** Phase 2
**Deliverables:**

- Convert auto-remediate yes/no classifier calls to Below schema classifier
- Convert adversarial-review yes/no verdict router to Below schema classifier
- Convert cross-model-review routing decisions to Below schema classifier
- Measure per-site fallback rate and record in decisions.log
- **Dropped:** governance_enforcer classifier — the file has no Claude classifier call to convert (confirmed by review)
  **Success:** Fallback rate <5% per call site on a 100-run sample.

### Phase 7: Log clustering in /dbg, /sdb, /diag, /device, /query

**Files:** `$HOME/.buildrunner/scripts/developer-brief.sh` (MODIFY), `core/cluster/node_analysis.py` (MODIFY), `$HOME/.claude/commands/dbg.md` (MODIFY), `$HOME/.claude/commands/sdb.md` (MODIFY), `$HOME/.claude/commands/diag.md` (MODIFY), `$HOME/.claude/commands/device.md` (MODIFY), `$HOME/.claude/commands/query.md` (MODIFY)
**Blocked by:** Phase 3
**Deliverables:**

- Add baseline-capture step: run each skill on fixture log with clustering OFF, record token count; then with clustering ON, compute delta
- Pre-cluster log tail before qwen3:8b summary step
- Wire clustering library into five skills above
- Preserve cluster representative + frequency + full outlier list
- **Automatic fail-open**: if Below/embed call fails, skip clustering and fall through to the current pipeline (no user-visible error)
- Rollback flag (`BR3_LOG_CLUSTER=off`)
  **Success:** ≥30% token reduction on representative logs vs baseline; no cluster collapses a unique critical error; 0 outages from Below-offline.

### Phase 8: Test failure clustering before /root analysis

**Files:** `$HOME/.buildrunner/scripts/ship/ci/ci-classifier.sh` (MODIFY — cluster integration only), `$HOME/.claude/commands/root.md` (MODIFY), `core/cluster/below/test_failure_cluster.py` (NEW), `tests/cluster/test_test_failure_cluster.py` (NEW)
**Blocked by:** Phase 3, Phase 9 (both modify ci-classifier.sh — serialized)
**Deliverables:**

- Baseline capture: /root on multi-failure run with clustering OFF; record tokens. Then ON; compute delta
- Cluster CI test failures via library (uses Phase 3 outlier exposure)
- Preserve outliers (cluster size 1) as-is — never dropped
- Pass cluster representative + frequency + outlier list to /root
- **Automatic fail-open** on Below/embed failure
- Rollback flag (`BR3_TEST_CLUSTER=off`)
- Production module file lives under `core/` (NOT the test file); the test file is under `tests/`
  **Success:** /root context tokens reduced ≥25% on multi-failure runs vs baseline; 0 outages from Below-offline.

### Phase 9: CI classifier → qwen3:8b hybrid

**Files:** `$HOME/.buildrunner/scripts/ship/ci/ci-classifier.sh` (MODIFY — regex fallback path)
**Blocked by:** Phase 2
**Deliverables:**

- Keep regex path as first check (speed)
- Fall back to Below qwen3:8b via schema classifier when regex returns no match
- Emit novel-pattern hits to decisions.log for regex expansion
- Rollback flag (`BR3_CI_CLASSIFY=regex-only`)
- Accuracy regression test vs. recorded CI failures
  **Success:** Novel-pattern detection rate ≥80%; accuracy ≥90% on labeled test set.

### Phase 10: Semantic cache integration across Claude call sites

**Files:** `core/opus_client.py` (MODIFY), `core/ai_code_review.py` (MODIFY — route through shared wrapper), `core/cluster/below/claude_cache_wrapper.py` (NEW), `tests/test_claude_cache_wrapper.py` (NEW)
**Blocked by:** Phase 4
**Deliverables:**

- Introduce a thin `claude_cache_wrapper.call(model, method, messages, *, skip_cache=False)` wrapper that all Anthropic SDK call sites go through
- Migrate `opus_client` internal call path to use the wrapper
- Migrate `ai_code_review.py` (which instantiates `AsyncAnthropic` directly) to use the wrapper — critical: ai_code_review is an excluded caller, so it passes `skip_cache=True`
- Exclusion list enforced by `skip_cache=True`: ai_code_review, adversarial-review, arbiter, any call with user-specific context
- 7-day warm-up period (log-only, no serve) before trusting hits
- Metric logging (hit rate, similarity distribution, false-positive reports)
  **Success:** Hit rate ≥15% on steady-state autopilot workload; 0 false positives reported during warm-up; ai_code_review bypasses cache 100%.

### Phase 11: Intel collect stage 1/2 → Below

**Files:** `core/cluster/scripts/collect-intel.sh` (MODIFY — stages 1 and 2 only)
**Blocked by:** Phase 2, Phase 13 (both modify collect-intel.sh — serialized)
**Deliverables:**

- Replace `claude -p` calls at **intel pipeline stage 1 (sources)** and **intel pipeline stage 2 (categorize)** with below-route qwen3:8b. (Labels "stage 1/2" used throughout this phase to avoid collision with build-plan Phase 1/2.)
- Structured extraction schema mirrors `hunt_sources/bhphoto.py` / `newegg.py` patterns
- Keep Opus for intel pipeline stage 3 (BR3-specific implications narrative)
- Snapshot-based regression test: capture 7 days of intel items into `tests/fixtures/intel_snapshot.jsonl`; replay through new pipeline; diff categorization accuracy
- **Dropped:** `intel_scoring.py` modifications — confirmed by review already routes to Below; only `collect-intel.sh` has remaining Claude calls
- Metric: Claude call count reduction vs. prior week
  **Success:** ≥80% Claude token reduction in intel pipeline; categorization accuracy parity with Opus baseline ±5%.

### Phase 12: Dependency update triage → qwen2.5:14b

**Files:** `$HOME/.buildrunner/scripts/auto-remediate.mjs` (MODIFY — dep triage section only), `$HOME/.buildrunner/scripts/lib/below-dep-triage.sh` (NEW)
**Blocked by:** Phase 2, Phase 6 (both modify auto-remediate.mjs — serialized)
**Deliverables:**

- Changelog diff parsing helper
- qwen2.5:14b schema classifier: `{action: auto-merge | stage-review | escalate, reasoning: string}`
- Route major version bumps to Claude; patch/minor to local classifier
- Route decision logged to decisions.log
- Integration test on 20 representative dep updates
  **Success:** Classification accuracy ≥90% on labeled set; ≥70% of updates handled locally.

### Phase 13: LLMLingua-2 prompt compression on dispatch

**Files:** `core/cluster/below/llmlingua_compress.py` (NEW), `$HOME/.buildrunner/scripts/autopilot-dispatch-prefix.sh` (MODIFY), `core/cluster/scripts/collect-intel.sh` (MODIFY — dispatch prefix only), `requirements-api.txt` (MODIFY — already in Phase 0)
**Blocked by:** None (serialized after Phase 11 due to shared collect-intel.sh file)
**Deliverables:**

- Install LLMLingua-2 via the `llmlingua` PyPI package (not GGUF; LLMLingua-2 is BERT-family, runs on CPU/CUDA via HF transformers)
- Compression helper with configurable ratio (default 0.5)
- Wire into autopilot dispatch prefix and intel-collect dispatch prefix
- Explicit exclusion list enforced in the wrapper: adversarial-review, arbiter, ai_code_review, cross-model-review, any reviewer dispatch
- Measure compression ratio + downstream quality delta on autopilot phase success rate
  **Success:** Mean compression ratio ≥3x on eligible prompts; autopilot phase success rate delta <3%.

### Phase 14: Static analysis prefilter for ai_code_review (downgrade, never skip)

**Files:** `core/ai_code_review.py` (MODIFY), `core/cluster/below/semgrep_triage.py` (NEW), `tests/test_semgrep_triage.py` (NEW)
**Blocked by:** Phase 2
**Deliverables:**

- Semgrep run on diff before Opus call (use public registry rulesets: p/ci, p/security-audit, p/owasp-top-ten, plus project-local rules)
- qwen2.5-coder:7b reads Semgrep output, classifies `{severity: clean | minor | flagged}`
- **clean** → downgrade Opus call to a single quick-pass prompt (NOT skip entirely) — preserves reviewer's broader mandate (bugs, performance, test coverage, best practices)
- **minor | flagged** → full Opus review proceeds unchanged
- Red-team test: deliberately inject a non-static-issue defect (e.g., an off-by-one in a new function) into a diff that Semgrep scores clean; verify the downgraded review still catches it
- Rule-coverage validation: assert Semgrep ruleset covers OWASP Top 10 categories
- Metric: Opus token savings per 100 diffs
  **Success:** ≥30% token reduction on clean diffs via downgrade; 100% red-team defects caught by downgraded review; 0 OWASP categories missing from ruleset.

### Phase 15: PR body generation → qwen2.5-coder

**Files:** `$HOME/.buildrunner/scripts/ship/ci/pr-body-gen.sh` (CREATE or MODIFY — verify existence at phase start), `core/cluster/below/pr_body.py` (NEW)
**Blocked by:** None
**Deliverables:**

- Confirm file exists at `$HOME/.buildrunner/scripts/ship/ci/pr-body-gen.sh`; if absent, create it and wire into /ship's PR creation step
- Replace static template with qwen2.5-coder diff-to-PR-body
- Architectural-keyword router (schema migration, interface change, auth, RLS, deploy config) → escalate to Claude
- Unflagged PRs stay on Below
- Fallback to static template on empty/malformed Below output
- 10-PR integration test
  **Success:** ≥70% of PRs handled by Below; human-acceptability rate ≥90%.

### Phase 16: Spec-drift detection at /begin step 0

**Files:** `$HOME/.claude/commands/begin.md` (MODIFY — add project-scoping guard), `core/runtime/workflows/begin_workflow.py` (MODIFY), `core/cluster/below/spec_drift.py` (NEW), `tests/test_spec_drift.py` (NEW)
**Blocked by:** Phase 0 (uses shared embedding client)
**Deliverables:**

- `spec_drift.py` uses `core/cluster/below/embed.py` for embeddings (no coupling to log_cluster internals)
- Embedding comparison between BUILD spec requirements and current codebase function signatures / module names
- Integrate into `core/runtime/workflows/begin_workflow.py` step 0 (not governance_enforcer — confirmed correct subsystem)
- Update `begin.md` with a project-scoping guard: only run drift check when a BUILD spec exists at `.buildrunner/builds/BUILD_*.md`; skip in projects without one
- Surface drift candidates (spec item → no implementation; implementation → no spec) to user
- Advisory only; no auto-fix
- Integration test on a BUILD with injected drift
  **Success:** Detects injected drift in test case; zero false positives on clean baseline; skipped silently in projects with no BUILD spec.

---

## Parallelization Matrix

File-conflict check confirmed: phases that share a file are marked `Blocked by` each other (serialized), not parallel.

| Phase | Key Files                                                             | Can Parallel With     | Blocked By |
| ----- | --------------------------------------------------------------------- | --------------------- | ---------- |
| 0     | requirements-api.txt, embed.py                                        | 1, 5, 15              | -          |
| 1     | retrieve.py, reranker.py, context_bundle.py, service-env.sh           | 0, 2, 3, 4, 5, 13, 15 | -          |
| 2     | schema_classifier.py                                                  | 0, 1, 3, 4, 5, 13, 15 | 0          |
| 3     | log_cluster.py                                                        | 0, 1, 2, 4, 5, 13, 15 | 0          |
| 4     | semantic_cache.py                                                     | 0, 1, 2, 3, 5, 13, 15 | 0          |
| 5     | commit-br3-housekeeping.sh                                            | 0, 1, 2, 3, 4, 13, 15 | -          |
| 6     | auto-remediate.mjs, adversarial-review.sh, cross-model-review.sh      | 9, 10, 14             | 2          |
| 7     | skills, developer-brief.sh, node_analysis.py                          | 8, 10, 14             | 3          |
| 8     | ci-classifier.sh, root.md, test_failure_cluster.py                    | 7, 10, 14             | 3, 9       |
| 9     | ci-classifier.sh                                                      | 6, 10, 11, 14         | 2          |
| 10    | opus_client.py, ai_code_review.py, claude_cache_wrapper.py            | 6, 7, 8, 9, 14        | 4          |
| 11    | collect-intel.sh                                                      | 6, 9, 10, 14          | 2          |
| 12    | auto-remediate.mjs (dep section)                                      | 9, 10, 11, 14         | 2, 6       |
| 13    | autopilot-dispatch-prefix.sh, collect-intel.sh, llmlingua_compress.py | 1, 2, 3, 4            | 11         |
| 14    | ai_code_review.py (prefilter section), semgrep_triage.py              | 6, 7, 8, 9, 11, 12    | 2, 10      |
| 15    | pr-body-gen.sh, pr_body.py                                            | 0, 1, 2, 3, 4, 5, 13  | -          |
| 16    | begin.md, begin_workflow.py, spec_drift.py                            | 7, 10                 | 0          |

**Wave structure:**

- **Wave A (parallel):** Phases 0, 1, 5, 15 — no infrastructure dependencies
- **Wave B (parallel, after 0):** Phases 2, 3, 4, 13 — foundation
- **Wave C (parallel, after 2):** Phases 6, 9, 11, 14 (14 also needs Phase 10, see Wave D)
- **Wave C (parallel, after 3):** Phases 7, 16
- **Wave D (parallel, after 4):** Phase 10
- **Wave E (after 3 and 9):** Phase 8
- **Wave E (after 2 and 6):** Phase 12

---

## Out of Scope

- Migrating adversarial-review, arbiter, ai_code_review reasoning itself to Below (quality-sensitive, reserved for Claude)
- Replacing Opus 4.7 in stage 3 of intel collect (BR3-specific narrative needs reasoning model)
- Draft-model speculative decoding via Anthropic API (not supported in public API as of 2026-04)
- Multi-provider cache sharing across projects (scoped to BR3 for now)
- LLMLingua on ai_code_review / adversarial / arbiter / cross-model-review / reviewer dispatch paths (explicit exclusion due to quality sensitivity)
- Fixing the pre-existing `_RESEARCH_LIBRARY = HOME / 'Projects' / 'research-library'` violation in `context_bundle.py` (separate remediation track)
