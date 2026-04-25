# Build: research-pipeline-triple-failure-fix

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: backend-build, assigned_node: muddy }
      phase_2: { bucket: backend-build, assigned_node: muddy }
      phase_3: { bucket: backend-build, assigned_node: muddy }
      phase_4: { bucket: backend-build, assigned_node: muddy }
      phase_5: { bucket: backend-build, assigned_node: muddy }
```

**Created:** 2026-04-25
**Status:** PENDING — phases unstarted
**Deploy:** Muddy → Jimmy via existing rsync path for `core/cluster/node_semantic.py`. Below worker (`core/cluster/below/research_worker.py`) reloads on next launchd cycle. `~/.claude/commands/research.md`, `~/.buildrunner/scripts/llm-dispatch.sh`, and `~/.buildrunner/scripts/llm-clients/perplexity.py` live in user-global trees and take effect on next `/research` invocation.
**Source Plan File:** .buildrunner/plans/plan-research-pipeline-triple-failure-fix.md
**Source Plan SHA:** 0ece7c77ec07c69a0384368d032cad18b277c7d4034285316575ba4f1a805a09
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-25T14:58:05Z
**Prior-State Survey:** .buildrunner/plans/survey-research-pipeline-triple-failure-fix.md
**Owner:** byronhudson
**Builder posture:** Backend-build bucket on Muddy for all five phases. Phase 1 + Phase 3 run in parallel (no shared files). Phase 2 follows Phase 1 (research.md collision). Phase 4 follows Phase 3, Phase 5 follows Phase 4 (research_worker.py collision chain).

## Overview

The `/research` multi-LLM pipeline ships docs to Jimmy git but does not verify they become searchable. Three independent failure modes confirmed against production runs of the Neolithic henges topic: (1) reviewer call site is broken — dispatcher and skill use incompatible APIs and the envelope parser expects the wrong shape, so Gemini and Perplexity reviewers cascade silently to `degraded_no_review`; (2) the Claude sub-agent prompt template ships `<output_format>`, `<thinking>`, `WebSearch`/`WebFetch`, and literal `{…}` placeholders to non-Claude providers, biasing Perplexity sonar-pro's grounded search to off-topic content; (3) the reindex contract is uncorrelated — `_wait_for_reindex` polls global state, treats `last_index` advancement as proof (false-positives on no-change scans), silently sets `status: ok` on timeout, and never verifies the doc is actually retrievable. A fourth, separate Ollama retry-exhaustion path produces hard `status: error` and is not currently instrumented.

End-to-end success means: doc committed → specific reindex job complete → `/retrieve` with `sources:["research"]` returns the doc by intended_path with non-noise score. Anything less is `indexing_pending` or `error`, never `ok`.

## Parallelization Matrix

| Phase | Key Files                            | Can Parallel With | Blocked By                       |
| ----- | ------------------------------------ | ----------------- | -------------------------------- |
| 1     | research.md, llm-dispatch.sh         | 3                 | —                                |
| 2     | research.md, perplexity.py           | —                 | 1 (research.md collision)        |
| 3     | node_semantic.py, research_worker.py | 1                 | —                                |
| 4     | research_worker.py                   | —                 | 3 (research_worker.py collision) |
| 5     | research_worker.py                   | —                 | 4 (research_worker.py collision) |

First wave: Phase 1 || Phase 3.
Second wave: Phase 2 (after Phase 1) || Phase 4 (after Phase 3).
Third wave: Phase 5 (after Phase 4).

## Phases

### Phase 1: Reviewer Path Repair

**Status:** PENDING
**Files:**

- `~/.claude/commands/research.md` (MODIFY — Step 4.5 `run_reviewer()` call site, envelope parser at `research.md:703-704`)
- `~/.buildrunner/scripts/llm-dispatch.sh` (MODIFY — wildcard handler at `llm-dispatch.sh:93-97` exits nonzero with structured JSON)
- `tests/research/test_dispatcher_contract.py` (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Rewrite `run_reviewer()` to use existing positional dispatcher API (`llm-dispatch.sh codex --prompt-file <path>`); drop `--provider`, `--role`, `--body-file`.
- [ ] Compose reviewer prompt file with body content inlined (`cat reviewer-prompt-template.txt body.md > reviewer-prompt.txt`).
- [ ] Update reviewer envelope parser to expect `{ok: bool, content: string}` shape; parse critique JSON from inside `content`.
- [ ] Make `llm-dispatch.sh` wildcard handler exit nonzero with `{"ok":false,"provider":"<p>","error":"unknown_flag:<flag>"}` instead of silent `shift`.
- [ ] Contract test asserts: every flag the skill passes appears in dispatcher `--help`; envelope shape returned by `llm-dispatch.sh codex --prompt-file <fixture>` matches what reviewer parser expects.
- [ ] Backward-compat sweep: confirm `core/cluster/cross_model_review.py` and `~/.buildrunner/scripts/adversarial-review.sh --consensus` calls to `llm-dispatch.sh` still pass. The `adversarial-review.sh` script lives outside the project tree at `$HOME/.buildrunner/scripts/adversarial-review.sh`; the contract test must locate it by absolute path and FAIL (not silently skip) if missing.

**Success Criteria:** `/research` adversarial review returns parseable JSON for all three reviewer providers; no `[llm-dispatch] Unknown flag:` lines in any `.err` file across one full `/research` invocation; contract test passes.

### Phase 2: Perplexity Prompt Hardening

**Status:** PENDING
**Files:**

- `~/.claude/commands/research.md` (MODIFY — `<non_claude_dispatch>` strip step at `research.md:660`, `<sub_agent_prompt_template>` `<output_format>` placeholder rename)
- `~/.buildrunner/scripts/llm-clients/perplexity.py` (MODIFY — `build_request_body()` at lines 66-76)
- `tests/research/test_perplexity_prompt.py` (NEW)

**Blocked by:** Phase 1 (research.md collision)

**Deliverables:**

- [ ] Add prompt-strip step to `<non_claude_dispatch>` that removes `<output_format>`, `<thinking>`, `WebSearch`, `WebFetch`, and literal `{…}` placeholder lines before writing the per-provider prompt file.
- [ ] Replace literal text "common misconceptions" in `<sub_agent_prompt_template>` `<output_format>` Gotchas section with neutral "evidence gaps and caveats".
- [ ] Add optional `--search-domain-filter` and `--search-recency-filter` argparse args to `perplexity.py`; pass through to `build_request_body()`.
- [ ] Add per-sub-topic filter config in skill's `<non_claude_dispatch>` (e.g. archaeology sub-topic gets `--search-domain-filter "academic"`); design TBD per topic family.
- [ ] Test: stripped-prompt smoke run on a known-trick topic ("common misconceptions about X") returns at least one on-topic citation.

**Success Criteria:** Re-running the Neolithic henges query against Perplexity returns archaeology citations with no credit-union sources.

### Phase 3: Reindex Job Correlation

**Status:** PENDING
**Files:**

- `core/cluster/node_semantic.py` on Jimmy (MODIFY — `/api/research/reindex` handler at `node_semantic.py:1268-1278`, new `/api/research/reindex/<job_id>` endpoint)
- `core/cluster/below/research_worker.py` (MODIFY — `_post_reindex` at `research_worker.py:663`, `_wait_for_reindex` at `research_worker.py:666-693`)
- `tests/research/test_reindex_correlation.py` (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] `/api/research/reindex` returns `{status: started|already_indexing, job_id: <uuid>}` and tracks per-job state in a process-local dict (rows added, completion time, error).
- [ ] New `/api/research/reindex/<job_id>` endpoint reports `{state: running|done|failed, rows_added: int, error?: string}`.
- [ ] Worker `_post_reindex` captures `job_id` from response and returns it.
- [ ] Replace `_wait_for_reindex` polling with per-job status polling against new endpoint.
- [ ] Remove `last_index > commit_time_epoch` fallback (false-positives on no-change scans per `node_semantic.py:273-276`).
- [ ] On `already_indexing` response, wait on the returned in-flight `job_id` instead of timing out.

**Success Criteria:** Reindex POST during an active background cycle returns the in-flight `job_id`; worker correctly waits on it; per-job status returns `done` with `rows_added > 0` for newly committed docs.

### Phase 4: Post-Commit Searchability Verification + Status States

**Status:** PENDING
**Files:**

- `core/cluster/below/research_worker.py` (MODIFY — `process_record` at `research_worker.py:787-850`, `CompletedRecord` schema)
- `tests/research/test_worker_verification.py` (NEW)

**Blocked by:** Phase 3 (research_worker.py collision)

**Deliverables:**

- [ ] After successful job-correlated reindex, issue `/retrieve` with `sources:["research"]` constraint and query string built using this priority order: (1) doc frontmatter `title` field if present and non-empty; (2) first H1 (`# `) heading if present; (3) first non-empty paragraph (truncated to 200 chars). Record which source was used in the verification log for reproducibility.
- [ ] Match returned hits by `intended_path`; require non-noise score above a fixed threshold. **Hardcode `RETRIEVAL_VERIFY_THRESHOLD = 0.5`** in `core/cluster/below/research_worker.py` as a module constant. (Spec-trim 2026-04-25: dropped the 100-pair σ-calibration script — the original `max(0.4, mean+2σ)` formula was overengineering for a single retrieval gate; 0.5 sits well above the BUILD's prior `max(0.4, …)` floor and the live "neolithic-britain-trade-economics" hit at 0.87. If false-negatives appear in production, revisit then.) One-line comment citing rationale.
- [ ] Add `status: indexing_pending` to `CompletedRecord` schema (third state, distinct from ok/error).
- [ ] Reformat-fallback, metadata-fallback, reindex-timeout, and verification-failure paths all set `indexing_pending` (not ok).
- [ ] Worker re-enqueues `indexing_pending` records once for verification retry; on second failure flip to `error` with surfaced reason.
- [ ] Step 0 of `/research` skill in `research.md` recognizes `indexing_pending` and reports `Research from turn N still indexing — re-verifying`.

**Success Criteria:** Re-process the existing `c976014e` (currently `ok` with hidden warning) and `65e59b1d` (currently `error: timed out`) records — both either land `ok` (with verified retrieval) or `error` (with specific reason); no more silent `ok` + warning.

### Phase 5: Ollama Reformat/Metadata Failure Investigation

**Status:** PENDING
**Files:**

- `core/cluster/below/research_worker.py` (MODIFY — `_retry_ollama` at `research_worker.py:771`, instrumentation around reformat/metadata calls)
- `tests/research/test_ollama_retry.py` (NEW)

**Blocked by:** Phase 4 (research_worker.py collision)

**Deliverables:**

**(Spec-trim 2026-04-25: root cause already known.** Another Claude session confirmed the failure mode is `socket.timeout`/`TimeoutError` raised inside `process_record`'s reformat retry — the bare-`except OllamaError` clause does not catch socket exceptions, so the deterministic-frontmatter fallback never fires on big bodies (47KB+). The flock-with-PID-forensics lock and the `/api/tags` health check were originally listed as "pick one of three remediations" — both are dropped here as YAGNI. If post-fix reproduction still shows contention or cold-instance failures, file a follow-up.)

- [ ] **Catch `socket.timeout` and `TimeoutError` (in addition to `OllamaError`) in `process_record`'s reformat-retry path** so the deterministic-frontmatter fallback fires on socket-level timeouts. This is the root-cause one-line fix.
- [ ] Record per-attempt: which operation (reformat/metadata), elapsed time, error class, retry index — write structured JSON to `.buildrunner/research-queue/ollama-attempts.jsonl`. (Diagnostic instrumentation; keeps future failures cheap to triage.)
- [ ] Run reproduction of original `65e59b1d` failure with the timeout catch in place; confirm it now lands in the deterministic fallback path. Produce `decisions.log` entry citing the fix and the reproduction outcome.
- [ ] **Out of scope (deferred):** `/api/tags` health-check pre-flight, `fcntl.flock` per-host serializing lock with PID forensics. Reopen only if instrumentation data after the timeout-catch ships shows a remaining failure mode that warrants either.

**Success Criteria:** Re-queue `neolithic-henges-uk.md` (the failed run) and confirm it completes with `status: ok` and verified retrieval, OR surfaces a specific Ollama failure reason in the new instrumentation log (not just the opaque "timed out").

## Out of Scope

- Multi-model search domain configuration UI on the dashboard
- Cross-provider citation deduplication
- Exponential backoff retry policy for Perplexity 429s (existing single-retry is sufficient short-term)
- Bulk re-verification migration of all existing committed-but-unindexed docs (Phase 4 reverification on re-queue is sufficient for the two known-bad records)
- Replacing the launchd worker with a different process model
- Changing the embedding model (`sentence-transformers/all-MiniLM-L6-v2` stays)

## Verification

After all five phases complete:

1. `/research <test topic>` end-to-end returns `status: ok` with verified `/retrieve` match.
2. Re-queue `c976014e` and `65e59b1d` records — both resolve to either `ok` (with verified retrieval) or `error` (with specific reason).
3. Contract test from Phase 1 passes (no flag drift).
4. Perplexity smoke test from Phase 2 passes (no off-topic citations).
5. Reindex correlation test from Phase 3 passes (`job_id` roundtrip).
6. Worker verification test from Phase 4 passes (sources-filtered retrieve match).
7. Ollama retry test from Phase 5 passes (instrumentation logs are structured).
