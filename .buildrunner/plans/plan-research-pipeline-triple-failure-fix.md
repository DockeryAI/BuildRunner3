# Plan: research-pipeline-triple-failure-fix

## Prior-State Survey

**File:** `.buildrunner/plans/survey-research-pipeline-triple-failure-fix.md`

Three completed BUILDs (`BUILD_research-multi-llm`, `BUILD_research-vectorization`, `BUILD_cluster-max-research-library`) shipped the code surfaces this fix re-modifies. The `--body-file`/parser mismatch in Phase 1, the silent reindex timeout in Phase 4, and the async-fire-and-forget reindex contract in Phase 3 are all bugs from those original completed phases. Surfaced, not blocking.

Latent callers of `llm-dispatch.sh` outside `/research` (`cross_model_review.py`, `adversarial-review.sh --consensus`) MAY surface as failures when Phase 1 changes the wildcard handler from silent-shift to loud-exit. Phase 1 deliverables include a contract test that asserts those callers' invocations parse cleanly.

## Purpose

The /research multi-LLM pipeline ships docs to Jimmy git but does not verify they become searchable. Three independent failure modes were confirmed:

1. **Reviewer call site is broken** — dispatcher and skill use incompatible APIs; envelope parser expects the wrong shape. Codex got lucky in some runs; Gemini and Perplexity reviewers cascade silently to `degraded_no_review`.
2. **Perplexity prompt is non-portable** — the Claude sub-agent template ships `<output_format>`, `<thinking>`, `WebSearch`/`WebFetch`, and literal `{…}` placeholders to non-Claude providers, biasing sonar-pro's grounded search to off-topic content.
3. **Reindex contract is uncorrelated** — `_wait_for_reindex` polls global state, never ties success back to the POST it issued, treats `last_index` advancement as proof (false-positives on no-change scans), silently sets `status: ok` on timeout, and never verifies the doc is actually retrievable. A separate Ollama retry-exhaustion path produces hard `status: error` and is not currently instrumented.

## Goal

End-to-end success means: doc committed → specific reindex job complete → `/retrieve` with `sources:["research"]` returns the doc by intended_path with non-noise score. Anything less is `indexing_pending` or `error`, never `ok`.

## Phases

### Phase 1: Reviewer Path Repair

**Goal:** Adversarial review actually runs and parses for Codex, Gemini, Perplexity.

**Files:**

- `~/.claude/commands/research.md` (MODIFY — Step 4.5 `run_reviewer()` call site, envelope parser at `research.md:703-704`)
- `~/.buildrunner/scripts/llm-dispatch.sh` (MODIFY — wildcard handler at `llm-dispatch.sh:93-97` exits nonzero with structured JSON)
- `tests/research/test_dispatcher_contract.py` (NEW)

**Blocked by:** None.

**Deliverables:**

- [ ] Rewrite `run_reviewer()` to use existing positional dispatcher API (`llm-dispatch.sh codex --prompt-file <path>`); drop `--provider`, `--role`, `--body-file`
- [ ] Compose reviewer prompt file with body content inlined (`cat reviewer-prompt-template.txt body.md > reviewer-prompt.txt`)
- [ ] Update reviewer envelope parser to expect `{ok: bool, content: string}` shape; parse critique JSON from inside `content`
- [ ] Make `llm-dispatch.sh` wildcard handler exit nonzero with `{"ok":false,"provider":"<p>","error":"unknown_flag:<flag>"}` instead of silent `shift`
- [ ] Contract test asserts: every flag the skill passes appears in dispatcher --help; envelope shape returned by `llm-dispatch.sh codex --prompt-file <fixture>` matches what reviewer parser expects
- [ ] Backward-compat sweep: confirm `core/cluster/cross_model_review.py` and `~/.buildrunner/scripts/adversarial-review.sh --consensus` calls to `llm-dispatch.sh` still pass. The adversarial-review.sh script lives outside the project tree at `$HOME/.buildrunner/scripts/adversarial-review.sh`; the contract test must locate it by absolute path and FAIL (not silently skip) if missing

**Success Criteria:** /research adversarial review returns parseable JSON for all three reviewer providers; no `[llm-dispatch] Unknown flag:` lines in any `.err` file across one full /research invocation; contract test passes.

### Phase 2: Perplexity Prompt Hardening

**Goal:** Non-Claude providers receive a portable prompt; Perplexity returns on-topic citations.

**Files:**

- `~/.claude/commands/research.md` (MODIFY — `<non_claude_dispatch>` strip step at `research.md:660`, `<sub_agent_prompt_template>` `<output_format>` placeholder rename)
- `~/.buildrunner/scripts/llm-clients/perplexity.py` (MODIFY — `build_request_body()` at lines 66-76)
- `tests/research/test_perplexity_prompt.py` (NEW)

**Blocked by:** Phase 1 (research.md collision).

**Deliverables:**

- [ ] Add prompt-strip step to `<non_claude_dispatch>` that removes `<output_format>`, `<thinking>`, `WebSearch`, `WebFetch`, and literal `{…}` placeholder lines before writing the per-provider prompt file
- [ ] Replace literal text "common misconceptions" in `<sub_agent_prompt_template>` `<output_format>` Gotchas section with neutral "evidence gaps and caveats"
- [ ] Add optional `--search-domain-filter` and `--search-recency-filter` argparse args to `perplexity.py`; pass through to `build_request_body()`
- [ ] Add per-sub-topic filter config in skill's `<non_claude_dispatch>` (e.g. archaeology sub-topic gets `--search-domain-filter "academic"`); design TBD per topic family
- [ ] Test: stripped-prompt smoke run on a known-trick topic ("common misconceptions about X") returns at least one on-topic citation

**Success Criteria:** Re-running the Neolithic henges query against Perplexity returns archaeology citations with no credit-union sources.

### Phase 3: Reindex Job Correlation

**Goal:** Worker waits for the specific reindex job it triggered, not for global state.

**Files:**

- `core/cluster/node_semantic.py` on Jimmy (MODIFY — `/api/research/reindex` handler at `node_semantic.py:1268-1278`, new `/api/research/reindex/<job_id>` endpoint)
- `core/cluster/below/research_worker.py` (MODIFY — `_post_reindex` at `research_worker.py:663`, `_wait_for_reindex` at `research_worker.py:666-693`)
- `tests/research/test_reindex_correlation.py` (NEW)

**Blocked by:** None.

**Deliverables:**

- [ ] `/api/research/reindex` returns `{status: started|already_indexing, job_id: <uuid>}` and tracks per-job state in a process-local dict (rows added, completion time, error)
- [ ] New `/api/research/reindex/<job_id>` endpoint reports `{state: running|done|failed, rows_added: int, error?: string}`
- [ ] Worker `_post_reindex` captures `job_id` from response and returns it
- [ ] Replace `_wait_for_reindex` polling with per-job status polling against new endpoint
- [ ] Remove `last_index > commit_time_epoch` fallback (false-positives on no-change scans per `node_semantic.py:273-276`)
- [ ] On `already_indexing` response, wait on the returned in-flight `job_id` instead of timing out

**Success Criteria:** Reindex POST during an active background cycle returns the in-flight job_id; worker correctly waits on it; per-job status returns `done` with `rows_added > 0` for newly committed docs.

### Phase 4: Post-Commit Searchability Verification + Status States

**Goal:** A queue record is `status: ok` only when /retrieve actually returns the new doc.

**Files:**

- `core/cluster/below/research_worker.py` (MODIFY — `process_record` at `research_worker.py:787-850`, `CompletedRecord` schema)
- `tests/research/test_worker_verification.py` (NEW)

**Blocked by:** Phase 3 (research_worker.py collision).

**Deliverables:**

- [ ] After successful job-correlated reindex, issue `/retrieve` with `sources:["research"]` constraint and query string built using this priority order: (1) doc frontmatter `title` field if present and non-empty; (2) first H1 (`# `) heading if present; (3) first non-empty paragraph (truncated to 200 chars). Record which source was used in the verification log for reproducibility
- [ ] Match returned hits by `intended_path`; require non-noise score above a calibrated threshold. Calibration: in this phase, run a one-time script that computes mean cosine similarity for 100 random title-vs-unrelated-doc pairs against the live `sentence-transformers/all-MiniLM-L6-v2` index; set threshold = max(0.4, calibrated_noise_mean + 2σ). Store the calibrated value in `core/cluster/below/research_worker.py` as a module constant `RETRIEVAL_VERIFY_THRESHOLD` with a one-line comment citing the calibration date and noise mean
- [ ] Add `status: indexing_pending` to `CompletedRecord` schema (third state, distinct from ok/error)
- [ ] Reformat-fallback, metadata-fallback, reindex-timeout, and verification-failure paths all set `indexing_pending` (not ok)
- [ ] Worker re-enqueues `indexing_pending` records once for verification retry; on second failure flip to `error` with surfaced reason
- [ ] Step 0 of `/research` skill in `research.md` recognizes `indexing_pending` and reports `Research from turn N still indexing — re-verifying`

**Success Criteria:** Re-process the existing `c976014e` (currently `ok` with hidden warning) and `65e59b1d` (currently `error: timed out`) records — both either land `ok` (with verified retrieval) or `error` (with specific reason); no more silent `ok` + warning.

### Phase 5: Ollama Reformat/Metadata Failure Investigation

**Goal:** Identify why `65e59b1d` hard-timed-out and decide remediation.

**Files:**

- `core/cluster/below/research_worker.py` (MODIFY — `_retry_ollama` at `research_worker.py:771`, instrumentation around reformat/metadata calls)
- `tests/research/test_ollama_retry.py` (NEW)

**Blocked by:** Phase 4 (research_worker.py collision).

**Deliverables:**

- [ ] Record per-attempt: which operation (reformat/metadata), elapsed time, error class, retry index — write structured JSON to `.buildrunner/research-queue/ollama-attempts.jsonl`
- [ ] Add Ollama health check call (`/api/tags` ping with 2s timeout) before reformat dispatch; fail fast on cold/dead instance with specific error
- [ ] Implement per-host serializing lock (file-based at `.buildrunner/research-queue/.ollama-host-<host>.lock`) so two parallel /research runs don't contend on one Below Ollama instance. Locking primitive: `fcntl.flock(fd, LOCK_EX | LOCK_NB)` on an open file handle; the kernel releases the advisory lock automatically on process exit (clean or crash), so no manual TTL is needed. Lock-file contents = `{pid, hostname, acquired_at_iso}` for forensics. On `flock` EWOULDBLOCK, read the lock file and: if the recorded PID is not running on this host, log a stale-lock warning and proceed to re-acquire (kernel already released it); else wait with exponential backoff up to 60s, then surface `ollama_lock_contention` error
- [ ] Run reproduction of original `65e59b1d` failure with new instrumentation; produce `decisions.log` entry naming the specific failure path
- [ ] Apply remediation chosen from instrumentation data: longer timeouts, health-gated dispatch, or serializing lock — only ONE remediation, not all three

**Success Criteria:** Re-queue `neolithic-henges-uk.md` (the failed run) and confirm it completes with `status: ok` and verified retrieval, OR surfaces a specific Ollama failure reason in the new instrumentation log (not just the opaque "timed out").

## Parallelization Matrix

| Phase | Key Files                            | Can Parallel With | Blocked By                       |
| ----- | ------------------------------------ | ----------------- | -------------------------------- |
| 1     | research.md, llm-dispatch.sh         | 3                 | -                                |
| 2     | research.md, perplexity.py           | -                 | 1 (research.md collision)        |
| 3     | node_semantic.py, research_worker.py | 1                 | -                                |
| 4     | research_worker.py                   | -                 | 3 (research_worker.py collision) |
| 5     | research_worker.py                   | -                 | 4 (research_worker.py collision) |

First wave: Phase 1 || Phase 3 in parallel.
Second wave: Phase 2 (after Phase 1) || Phase 4 (after Phase 3).
Third wave: Phase 5 (after Phase 4).

## Out of Scope

- Multi-model search domain configuration UI on the dashboard
- Cross-provider citation deduplication
- Exponential backoff retry policy for Perplexity 429s (existing single-retry is sufficient short-term)
- Bulk re-verification migration of all existing committed-but-unindexed docs (Phase 4 reverification on re-queue is sufficient for the two known-bad records)
- Replacing the launchd worker with a different process model
- Changing the embedding model (`sentence-transformers/all-MiniLM-L6-v2` stays)

## Verification

After all five phases complete:

1. `/research <test topic>` end-to-end returns `status: ok` with verified `/retrieve` match
2. Re-queue `c976014e` and `65e59b1d` records — both resolve to either `ok` (with verified retrieval) or `error` (with specific reason)
3. Contract test from Phase 1 passes (no flag drift)
4. Perplexity smoke test from Phase 2 passes (no off-topic citations)
5. Reindex correlation test from Phase 3 passes (job_id roundtrip)
6. Worker verification test from Phase 4 passes (sources-filtered retrieve match)
7. Ollama retry test from Phase 5 passes (instrumentation logs are structured)
