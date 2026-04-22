# Plan: Cluster Hardening v1

**Purpose:** Wire the seven solid-tier Claude-Code safety items onto BR3's existing cluster infrastructure. Items 1–4 are wire-ups on code that already exists (preflight patterns, Walter baseline, cost_tracker budgets, Walter flaky detection). Item 5 fills an empty PreToolUse hook. Item 6 is net-new eval corpus on Jimmy. Item 7 reframed: architect/builder/verifier already exists in cross_model_review.py — delete the superseded single-model reviewer and add a scope-drift judge pass.

**Target users:** Single operator (Byron) running BR3 against the 7-node Blues Cluster.

**Tech stack:** Python 3.11, FastAPI (api/routes/\*, core/cluster/base_service.py), SQLite (`.buildrunner/data.db` for CostTracker cost_entries + Walter's ~/.walter/test_results.db for test baselines; `.buildrunner/telemetry.db` only for runtime event telemetry), LanceDB (Jimmy), bash hooks (~/.claude/settings.json PreToolUse chain). Syntax validation tools per language: Python → `py_compile`, shell → `bash -n`, JS/MJS → `node --check`. **TypeScript/TSX excluded** from Phase 5 — BR3 core is Python-dominant and BR3 lacks a root tsconfig.json; bare `tsc` on single .tsx files rejects valid JSX. Project-level TSX validation is owned by each project's own vite/tsc pipeline, not by this hook.

**Paths outside the repo tree that this spec modifies:**

- `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` — emitted at every autopilot dispatch; owned by the operator's home-dir BuildRunner install. Not in the project git tree.
- `~/.buildrunner/scripts/runtime-dispatch.sh` — paid-call dispatcher; same location.
- `.claude/hooks/protect-files.sh` and `.claude/hooks/bash-guard.sh` — present in the project-level `.claude/hooks/` directory (verified — currently passthrough stubs).
- `~/.claude/settings.json` — 12-entry PreToolUse chain registration; only appended to, never rewritten.
- `/srv/jimmy/eval-corpus/**` on Jimmy (10.0.1.106); not in the Muddy repo tree.
- `~/.walter/test_results.db` on Walter; read-only from Muddy; Walter owns writes.

Reviewers that only see the Muddy repo tree will mis-flag these as missing; the files exist in the home dir or on other nodes.

**Deploy target:** web (local cluster only). No app artifact — all changes ship as Python module edits, hook scripts, BUILD spec header keys, and Jimmy-side corpus storage.

**Source context:**

- Audit completed by 5 parallel Explore agents (prior turn): test-protection, regression-gating, cost-enforcement, flaky/ACI, eval/gen-verifier, role matrix.
- Items 1–4 are one-line-to-one-file wire-ups. Items 5–6 are net-new but small. Item 7 is mostly delete.
- core/runtime/preflight.py:25-33 — PROTECTED_PATH_PATTERNS (5 lines to add tests/\*).
- core/dashboard_views.py:465-487 — get_test_baseline_data() already reads Walter's pass/fail snapshot.
- core/routing/cost_tracker.py:297-310 — \_check_budgets() currently warns; flip to raise.
- core/cluster/node_tests.py:659-715, :1172-1199 — Walter flaky detection + /api/flaky endpoint already live.
- core/cluster/cross_model_review.py (1621 lines) + arbiter.py + config — architect/builder/verifier already built.
- core/ai_code_review.py — superseded single-model reviewer, no longer wired into pre-commit hook. DELETE candidate.
- 495+ artifacts in .buildrunner/adversarial-reviews/ — corpus seed material.

**Related builds:**

- BUILD_cluster-max.md — will receive a small doc amendment under Phase 9 (role matrix gains architect/builder/verifier pattern).
- BUILD_cluster-prometheus-integration.md — independent; no overlap.
- BUILD_cluster-activation.md — independent; no overlap.

---

## Decisions to Confirm

Surfaced before writing the BUILD spec so the user can override defaults:

1. **Default cost ceiling per phase:** $4.00 USD. Override via `cost_ceiling_usd: N` key in BUILD phase header.
2. **`tests_writable` header key default:** `false` (safer). Phases that author or modify tests must opt-in explicitly (e.g. eval-harness phase, test-refactor phase).
3. **Scope-drift veto posture:** warn-only in Phase 9 (logs veto intent, does not block). Flip to hard-block after 2 weeks of clean telemetry.
4. **Eval harness trigger scope:** opt-in per-change initially (`make eval` after prompt/skill/hook edits). Gate later once corpus stabilizes.
5. **Flaky registry 3-of-3 gate:** require 3 consecutive passes across 3 distinct Walter runs before a fresh test is promoted from `quarantine:new` → `trusted`.

User can override any of these at "go" time before the BUILD spec is written.

---

## Phase 1 — Test file lockdown

**Goal:** Claude Code cannot edit, delete, or weaken tests during a phase unless the phase explicitly declares `tests_writable: true`. Reward-hacking the test suite is mechanically prevented.

**Files:**

- core/runtime/preflight.py (MODIFY — extend PROTECTED_PATH_PATTERNS + exemption logic)
- core/runtime/**init**.py (MODIFY if helper re-export needed)
- tests/runtime/test_preflight_test_lockdown.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] `PROTECTED_PATH_PATTERNS` is string-matched via `fnmatch`, which does NOT support `**` as recursive glob. Implement a new helper `is_test_path(normalized_path: str) -> bool` that returns True when the normalized path contains a `tests/` segment (`"/tests/" in normalized_path or normalized_path.startswith("tests/")`) OR matches project-local naming (`*_test.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`). Do NOT add `**` globs to PROTECTED_PATH_PATTERNS — they will silently not match.
- [ ] `is_protected_file()` (preflight.py:177) delegates to `is_test_path()` in addition to the fnmatch check on secret patterns.
- [ ] Read active-phase `tests_writable` flag from the BUILD spec header. `autopilot-dispatch-prefix.sh` already has the phase header in scope at dispatch; export `BR3_TESTS_WRITABLE=1` when the phase declares it. Default unset = blocked.
- [ ] Exemption: when `BR3_TESTS_WRITABLE=1`, `is_test_path()` returns False (test edits allowed). Secret patterns always block regardless of the flag.
- [ ] Log every test-edit attempt (block + pass) to `.buildrunner/logs/test-lockdown.log` with `{timestamp, path, decision, reason, phase_id}` for audit.
- [ ] Unit tests: blocked edit on tests/foo.py, blocked edit on pkg/tests/sub/bar_test.py, allowed edit under exemption, secrets still blocked under exemption, basename `*_test.py` blocked without exemption.

**Success criteria:** Edit/Write attempts on any path under `tests/` or matching test-naming patterns return a structured rejection to Claude when exemption is absent; the existing secrets-protection path is unchanged; all preflight unit tests pass.

**Parallelizable:** Yes — only touches preflight.py + a new test file.

---

## Phase 2 — Regression gate on every iteration

**Goal:** The inner-loop pass rule becomes "failing test now passes AND no previously-passing test now fails." Iterations that introduce a green→red regression are rejected and retried.

**Files:**

- core/dashboard_views.py (MODIFY — add compare_baseline())
- core/runtime/regression_gate.py (NEW — pure helper)
- ~/.buildrunner/scripts/autopilot-dispatch-prefix.sh (MODIFY — emit per-iteration gate hook)
- tests/runtime/test_regression_gate.py (NEW)

**Blocked by:** None (different files than Phase 1)

**Deliverables:**

- [ ] `compare_baseline(prev_snapshot, new_snapshot) -> RegressionReport` reading Walter's ~/.walter/test_results.db via existing get_test_baseline_data().
- [ ] Report shape: `{ new_pass: [...], new_fail: [...], regressed: [...], cleared: [...] }`.
- [ ] Autopilot inner loop invokes compare_baseline after each iteration. `regressed != []` → iteration rejected, retry instructed.
- [ ] Structured rejection message to Claude: names regressed tests + suggests revert-or-fix.
- [ ] Unit tests: regression detected, no-change no-op, flaky-quarantined tests excluded from the regressed set.

**Success criteria:** A fabricated diff that breaks a previously-green test is rejected; a diff that only makes a red test green passes; regressed tests already on the flaky quarantine list are excluded from the gate.

**Parallelizable:** Yes with Phases 1, 3, 4, 5.

---

## Phase 3 — Hard cost ceiling per phase

**Goal:** Each phase carries a USD ceiling. CostTracker's warn becomes a raised exception. Paid calls are preflighted against the ceiling; bust → phase halts and escalates, no matter the iteration count.

**Database note:** CostTracker persists to `.buildrunner/data.db` (table `cost_entries`) per core/routing/cost_tracker.py:93. `telemetry.db` holds unrelated event telemetry. All schema changes in this phase apply to `data.db`, not `telemetry.db`.

**Files:**

- core/routing/cost_tracker.py (MODIFY — convert warn to BudgetCeilingExceeded raise; add ceiling-lookup helper; add a new `phase_budgets` table migration in data.db)
- core/opus_client.py (MODIFY — preflight check before paid call)
- ~/.buildrunner/scripts/runtime-dispatch.sh (MODIFY — read ceiling, enforce)
- scripts/migrate-data-db-add-phase-budgets.py (NEW — idempotent migration runs inline via CostTracker's existing run_migration path)
- tests/routing/test_cost_ceiling.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Add `BudgetCeilingExceeded` exception class in `core/routing/cost_tracker.py`.
- [ ] Add table `phase_budgets { phase_id TEXT PRIMARY KEY, ceiling_usd REAL NOT NULL, set_at TIMESTAMP }` to `.buildrunner/data.db` via the existing `run_migration` path (same mechanism cost_entries uses at cost_tracker.py:286-294). Writes are upserts per phase_id at dispatch time.
- [ ] `_check_budgets()` (cost_tracker.py:297) now joins per-phase spend (SUM of cost_entries.cost_usd WHERE build_phase = current_phase) against `phase_budgets.ceiling_usd`. Raises `BudgetCeilingExceeded` when `spent_usd >= ceiling_usd`.
- [ ] Ceiling resolution: phase-header `cost_ceiling_usd: N` → `phase_budgets` row → env `BR3_COST_CEILING_USD` → default `4.00`. First non-null wins.
- [ ] `opus_client.py` preflights each call by calling CostTracker.would_exceed(phase_id, projected_usd) where projected = model_pricing \* max_output_tokens. Refuses the call on True.
- [ ] `runtime-dispatch.sh` writes ceiling to process env and upserts `phase_budgets` row before dispatch.
- [ ] Unit tests: bust triggers raise, warn threshold still logs but does not raise, missing `phase_budgets` row falls back to default, concurrent upsert safe.

**Success criteria:** A phase configured with ceiling=$0.01 halts before a second paid call; `phase_budgets` table exists after first run; cost_entries path is unchanged for existing reads.

**Parallelizable:** Yes with Phases 1, 2, 4, 5.

---

## Phase 4 — Flaky-test quarantine registry

**Goal:** Promote Walter's implicit flaky-detection to an explicit registry. Claude is told to skip (not "fix") quarantined tests. Fresh tests must pass 3-of-3 consecutive runs before they count as trusted.

**Files:**

- core/cluster/node_tests.py (MODIFY — add registry writer + `GET /api/flaky/registry` route + 3-of-3 promotion filter to the existing LAG() query in /api/flaky)
- core/cluster/flaky_registry_client.py (NEW — Muddy-side HTTP pull + snapshot writer with 60s TTL cache)
- .buildrunner/flaky-quarantine.json (NEW — Muddy-side snapshot file, written by the pull client)
- core/cluster/jimmy_flaky_sync.py (NEW — Walter-side Jimmy LanceDB push with outbox retry)
- ~/.buildrunner/scripts/autopilot-dispatch-prefix.sh (MODIFY — call flaky_registry_client, inject quarantine list into dispatched prompt context)
- tests/cluster/test_flaky_registry.py (NEW)

**Blocked by:** Phase 2 preferred (compare_baseline reader takes the quarantine list as input — acceptable to ship Phase 4 first and update Phase 2 reader in the same PR).

**Deliverables:**

- [ ] Registry writer on Walter: after each Walter run, upsert `{ test_id, flaky_score, first_seen, last_flip, status: trusted|quarantined|new }` into Walter's local `~/.walter/flaky-quarantine.json`.
- [ ] **Walter → Muddy sync:** Walter exposes the registry via a new FastAPI route `GET /api/flaky/registry` on its existing node_tests.py service. Muddy-side helper `core/cluster/flaky_registry_client.py` (NEW) pulls it at autopilot-dispatch time, writes a snapshot to `.buildrunner/flaky-quarantine.json` in the active repo, and caches with a 60s TTL. No shared mount, no scp, no git sync — pure HTTP pull over the cluster network.
- [ ] 3-of-3 filter added to LAG() query: `status: new` tests require 3 consecutive green runs (across distinct walter_run_id) before flipping to `trusted`.
- [ ] Jimmy push: after the registry is updated on Walter, Walter POSTs delta entries to Jimmy (`POST http://10.0.1.106:8100/api/flaky/upsert`) for LanceDB table `flaky_registry` cross-session persistence. On Jimmy-unreachable, Walter buffers to a local outbox and retries on next run.
- [ ] Autopilot prompt prefix reads the cached `.buildrunner/flaky-quarantine.json` and includes the current quarantine list under a "do-not-fix, log-and-move-on" heading.
- [ ] Phase 2's `compare_baseline()` reader takes `quarantined_ids: set[str]` parameter and excludes them from `regressed[]`.
- [ ] Unit tests: 3-of-3 gate math, Muddy pull + snapshot write, Jimmy push stub + outbox-retry path, prompt-prefix injection, compare_baseline exclusion.

**Success criteria:** Walter-side `~/.walter/flaky-quarantine.json` exists after first run; Muddy-side `.buildrunner/flaky-quarantine.json` is produced by the pull client on autopilot dispatch; Jimmy LanceDB has matching rows; a quarantined test does not appear in regressed[]; a new test does not get trusted status until it has 3 consecutive green runs.

**Parallelizable:** Yes with Phases 1, 3, 5.

---

## Phase 5 — ACI syntax guardrail on edits

**Goal:** Before any Edit/Write lands on disk, a fast parse check runs on the resulting file. Invalid syntax → rejection returned to Claude before the write. Prevents cascading edits on top of broken code.

**Files:**

- .claude/hooks/protect-files.sh (MODIFY — currently passthrough stub; add syntax gate)
- .claude/hooks/syntax-check.py (NEW — fast parser dispatch by extension)
- tests/hooks/test_syntax_check.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Dispatch by file extension: `.py` → `python3 -m py_compile`, `.js` / `.mjs` / `.cjs` → `node --check`, `.sh` / `.bash` → `bash -n`, `.json` → `python3 -c 'json.load(open(sys.argv[1]))'`, `.yaml` / `.yml` → `python3 -c 'yaml.safe_load(open(sys.argv[1]))'`.
- [ ] **TypeScript and JSX/TSX are explicitly excluded.** BR3 core has no root tsconfig.json and bare `tsc` on individual .tsx files rejects valid React. Project-level TSX is validated by each project's own pipeline (vite/tsc) on build — not by this hook. If a future BR3 project lands with a root tsconfig.json, add an extension-branch that shells out to `npx tsc --noEmit -p <nearest-tsconfig> <file>` with the project's config.
- [ ] Parse only — no lint, no type-check on the broader project. Time budget: 1.5s per file; timeout → pass-through (fail-open).
- [ ] Unknown extensions (including .ts/.tsx) → pass-through silently.
- [ ] Rejection format: `SYNTAX_REJECTED: <file> (<parser>): <first error line>`; Claude sees this string and re-plans.
- [ ] Write to `.buildrunner/logs/aci-guardrail.log` every pass/reject with duration.
- [ ] Unit tests: valid py/js/sh/json/yaml pass; invalid each rejected; .ts and .tsx pass-through without running any parser; unknown extension passes through; timeout passes through.

**Success criteria:** Writing a syntactically invalid .py file is rejected with a one-line error and Claude re-plans; writing a valid .py file lands in <1.5s overhead; .tsx files are not blocked by this hook; unknown file types are not blocked.

**Parallelizable:** Yes with Phases 1–4.

---

## Phase 6 — Eval corpus: storage + seeding on Jimmy

**Goal:** Establish the project-local eval corpus layout and seed it from existing adversarial-review artifacts + bug-fix commits. 30% holdout enforced at creation time.

**Files:** (Jimmy-side at /srv/jimmy + Muddy-side API route + loader)

- /srv/jimmy/eval-corpus/manifest.jsonl (NEW — one row per bug, on Jimmy)
- /srv/jimmy/eval-corpus/bugs/<id>/ (NEW — per-bug directory: `task.md`, `failing_test.patch`, `fix.patch`, `labels.json`)
- /srv/jimmy/eval-corpus/README.md (NEW — schema + contribution flow)
- Jimmy FastAPI route (new, appended to Jimmy's existing service): `GET /api/eval/corpus?split=train|holdout|all` returns JSONL of manifest rows filtered by split.
- core/eval/\_\_init\_\_.py (NEW, Muddy-side)
- core/eval/corpus_loader.py (NEW, Muddy-side — HTTP client that hits Jimmy's new endpoint)
- api/routes/eval.py (NEW, Muddy-side — local Muddy route that proxies to Jimmy and is what the dashboard/CLI call)
- api/server.py (MODIFY — register `eval.router` alongside the existing route registrations)
- scripts/seed-eval-corpus.py (NEW — runs on Jimmy over SSH; mines .buildrunner/adversarial-reviews/ from Muddy + git log; writes manifest.jsonl)
- tests/eval/test_corpus_loader.py (NEW)
- tests/api/test_eval_routes.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Corpus schema: `{ id, title, task, failing_test_path, failing_test_content, fix_diff, category, labels[], split: "train"|"holdout", seeded_from }`.
- [ ] Seed script mines 495+ adversarial-review JSONs; each `blocker`-verdict artifact becomes a candidate bug.
- [ ] Seed script also mines git log for commits with "fix:" prefix + test change; extracts failing→passing test as task.
- [ ] 30% holdout: deterministic hash(id) % 10 < 3 → split="holdout"; tagged at creation, never rewritten.
- [ ] **Jimmy route (new):** append `GET /api/eval/corpus?split=...` to Jimmy's existing FastAPI service; returns JSONL stream of manifest rows filtered by split; 200 OK on empty.
- [ ] **Muddy route (new):** `api/routes/eval.py` with `GET /api/eval/corpus` that proxies to Jimmy (and caches for 60s). Registered in `api/server.py`.
- [ ] corpus_loader.py exposes `iter_bugs(split: str) -> Iterator[Bug]` reading over the Muddy proxy route.
- [ ] LanceDB index `eval_corpus_embeddings` (256-dim, same embedder as research-library) for analog-bug retrieval; built by seed script after manifest write.
- [ ] Unit tests: schema round-trip, 30% holdout count tolerance ±3, loader returns only requested split, Jimmy route returns filtered JSONL, Muddy proxy route echoes Jimmy with cache.
- [ ] Target ≥ 40 bugs seeded before Phase 7 begins.

**Success criteria:** manifest.jsonl has ≥40 rows; holdout count is 28–36% of total; corpus_loader.py returns correct row counts per split; LanceDB index reachable from Muddy.

**Parallelizable:** Yes with Phases 1–5, 9.

---

## Phase 7 — Eval execution harness

**Goal:** Given a corpus + a config (prompt/skill/hook/model), run every bug and record pass rate, regression rate, cost, tool-call count. Below executes inference; Muddy orchestrates.

**Database note:** eval results live in `.buildrunner/data.db` (same DB as cost_entries) table `eval_runs`. `telemetry.db` is not used. Cost per bug is joined from `cost_entries` by `build_phase = '<run_id>/<bug_id>'` — each bug dispatch sets that phase scope so CostTracker attributes spend correctly.

**Files:**

- core/eval/runner.py (NEW — orchestrator, sets build_phase scope per bug)
- core/eval/below_executor.py (NEW — dispatches inference to Below via existing `/api/gpu` health + `/api/inference` endpoints in node_inference.py)
- core/eval/metrics.py (NEW — joins eval_runs + cost_entries, computes per-run aggregates)
- scripts/run-eval.sh (NEW — CLI wrapper)
- scripts/migrate-data-db-add-eval-runs.py (NEW — adds `eval_runs` table to `.buildrunner/data.db`)
- tests/eval/test_runner.py (NEW)

**Blocked by:** Phase 6 (needs corpus) AND Phase 3 (Phase 3 owns the data.db migration infra this phase reuses; serialize 3 → 7)

**Deliverables:**

- [ ] `eval_runs` table in `.buildrunner/data.db` via CostTracker-style run_migration: columns `run_id TEXT, config_hash TEXT, split TEXT, bug_id TEXT, passed INTEGER, regressed INTEGER, tool_calls INTEGER, duration_ms INTEGER, started_at TIMESTAMP, PRIMARY KEY (run_id, bug_id)`.
- [ ] `runner.run_config(config, split) -> EvalRun` iterates corpus, dispatches each bug to a fresh Claude Code session. Sets `BR3_BUILD_PHASE="<run_id>/<bug_id>"` so cost_entries rows pin to the bug. Writes one eval_runs row per bug. Cost_usd is joined on demand from cost_entries, not stored redundantly.
- [ ] below_executor VRAM preflight uses `GET http://<below_host>:<port>/api/gpu` (exists at node_inference.py:289). Response is `{gpu_count, vram_total_mb, dual_gpu_ready, mode, ...}`. Abort if gpu_count == 0 OR vram_total_mb < 2048; fallback to Muddy orchestrator with a log line.
- [ ] Per-bug metrics: passed (target test flipped red→green per Walter snapshot diff), regressed (≥1 previously-green test flipped red per the Phase 2 compare_baseline), tool_calls (from Claude session transcript), duration_ms.
- [ ] CLI: `scripts/run-eval.sh --config <hash> --split train|holdout|all [--workers 2]`.
- [ ] Concurrency: 2 concurrent bugs by default; each runs in its own transient git worktree so parallel bugs can't collide on edits.
- [ ] Unit tests: mock corpus, mock session, runner tallies correctly; `/api/gpu` abort path; cost join returns correct sums; worktree cleanup on error.

**Success criteria:** `run-eval.sh --split train` produces an eval_runs row per train bug; `SELECT COUNT(*) FROM eval_runs WHERE run_id=?` equals corpus train count; Below `/api/gpu` is queried at dispatch; Muddy fallback path is logged when Below VRAM is insufficient.

**Parallelizable:** No with Phase 6; yes with Phases 1–5, 8, 9.

---

## Phase 8 — Eval comparison + holdout enforcement

**Goal:** Turn eval runs into a comparison report. Given two config hashes, produce a diff of pass-rate / regression-rate / cost / tool-calls. Holdout split is never used for tuning — only for sanity-check reports.

**Files:**

- core/eval/compare.py (NEW — diff two runs)
- core/eval/holdout_guard.py (NEW — enforces holdout isolation)
- scripts/eval-compare.sh (NEW — CLI wrapper)
- api/routes/eval.py (MODIFY — extend the route file created in Phase 6; add `GET /api/eval/compare`)
- tests/eval/test_compare.py (NEW)
- tests/eval/test_holdout_guard.py (NEW)
- tests/api/test_eval_compare_route.py (NEW)

**Blocked by:** Phase 7

**Deliverables:**

- [ ] `compare.diff(run_a, run_b) -> ComparisonReport`: pass_rate delta, regression_rate delta, cost delta (via cost_entries join), tool-call delta, per-bug flip list.
- [ ] `holdout_guard.assert_clean(config_hash: str, commit_sha: str, changed_files: list[str]) -> GuardReport`. Changed_files is the source of truth (tool caller extracts via `git diff --name-only <commit>^!`); commit_sha is for logging; config_hash is what the eval used. Rejects if any changed_file matches a path listed in holdout bug metadata (failing_test_path, files-under-fix-diff). Soft-gate (warning only in report) by default; `BR3_HOLDOUT_GUARD_MODE=block` flips to hard reject.
- [ ] CLI: `scripts/eval-compare.sh <baseline-hash> <candidate-hash>` — wraps compare.diff; prints table; invokes holdout_guard with `git diff --name-only <baseline-hash>..<candidate-hash>` for changed_files.
- [ ] Route `GET /api/eval/compare?baseline=...&candidate=...` returns the JSON ComparisonReport. Lives in api/routes/eval.py (the same module Phase 6 adds).
- [ ] Unit tests: diff math, holdout_guard.assert_clean with clean / contaminated / empty changes, report renders on empty runs, route returns 400 on unknown hash.

**Success criteria:** `eval-compare.sh A B` emits a readable diff table; the same comparison is reachable via `GET /api/eval/compare`; holdout_guard flags a contrived commit that touches a holdout failing_test_path.

**Parallelizable:** No with Phase 7; yes with Phase 9.

---

## Phase 9 — Architect/builder/verifier cleanup + scope-drift judge

**Goal:** Delete the superseded single-model reviewer (core/ai_code_review.py). Add a scope-drift judge as a 4th pass inside cross_model_review.py. Document the architect/builder/verifier pattern in BUILD_cluster-max.md so future phases know the split already exists.

**Files:**

- core/ai_code_review.py (DELETE)
- tests/test_ai_code_review.py (DELETE — finalize; partial state in working tree per git status)
- core/cluster/cross_model_review.py (MODIFY — add scope_drift_judge() pass after the three existing passes)
- core/cluster/cross_model_review_config.json (MODIFY — config knob `scope_drift_enabled: bool`, `scope_drift_mode: warn|block`)
- .buildrunner/builds/BUILD_cluster-max.md (MODIFY — add architect/builder/verifier section to role matrix narrative)
- tests/cluster/test_scope_drift_judge.py (NEW)
- grep the repo for other `ai_code_review` imports and remove them.

**Blocked by:** None (no file conflicts with Phases 1–8; independent)

**Deliverables:**

- [ ] Delete core/ai_code_review.py and any references (search tree; remove imports; adjust pre-commit hook if still wired).
- [ ] Delete tests/test_ai_code_review.py (record in PR).
- [ ] scope_drift_judge() receives: diff, phase "Success Criteria" text from BUILD spec, phase "Files:" list. Returns `{ verdict: pass|drift, out_of_scope_files: [...], out_of_scope_changes: [...] }`.
- [ ] Judge runs as 4th pass after arbiter verdict. If `mode: warn` → log and annotate review artifact; if `mode: block` → verdict flipped to BLOCKED.
- [ ] Config default: `scope_drift_enabled: true, scope_drift_mode: warn` (per decision 3 above).
- [ ] BUILD_cluster-max.md: add "Architect / builder / verifier pattern" subsection under the role matrix narrative; cross-link to cross_model_review.py.
- [ ] Unit tests: in-scope diff passes, out-of-scope-file rejected, warn-mode doesn't flip verdict, block-mode flips it.

**Success criteria:** ai_code_review.py removed + tree builds green; scope_drift_judge produces a verdict on at least 3 real review artifacts from .buildrunner/adversarial-reviews/; BUILD_cluster-max.md has the new subsection; judge warnings visible in review artifact JSON.

**Parallelizable:** Yes with Phases 1–8.

---

## Out of Scope (Future)

- **Replacing `/predict` skill stub with real phase-difficulty predictor.** Flagged in audit as a dead stub but is independent work. Deferred to a future spec (predictor needs eval-harness data from Phase 7 as training signal, so sequencing it after Phase 8 is rational).
- **Deleting project-level .claude/hooks/bash-guard.sh** (passthrough stub). Leave in place — harmless, and a separate security-hook spec may fill it.
- **Generator/verifier split for "plain" phases.** The split exists for review; wiring it into every phase's builder path is a larger architectural change, not a hardening item. Separate spec if wanted.
- **Dashboard UI for eval-harness results.** Phase 8 adds the JSON endpoint; a full dashboard panel is follow-up UI work.
- **Cross-project corpus sharing** (corpus read by non-BR3 projects). Corpus lives under /srv/jimmy/eval-corpus/ which is BR3-scoped; cross-project reads need an auth layer we don't want to design yet.

---

## Parallelization Matrix

| Phase | Key Files                                                                                                                                       | Can Parallel With      | Blocked By                                                   |
| ----- | ----------------------------------------------------------------------------------------------------------------------------------------------- | ---------------------- | ------------------------------------------------------------ |
| 1     | core/runtime/preflight.py (MODIFY); tests/runtime/test_preflight_test_lockdown.py (NEW)                                                         | 2, 3, 4, 5, 6, 9       | None                                                         |
| 2     | core/dashboard_views.py (MODIFY); core/runtime/regression_gate.py (NEW); autopilot-dispatch-prefix.sh (MODIFY)                                  | 1, 3, 5, 6, 9          | None (Phase 4 updates reader in same PR)                     |
| 3     | core/routing/cost_tracker.py (MODIFY); core/opus_client.py (MODIFY); runtime-dispatch.sh (MODIFY); telemetry.db schema (MIGRATE)                | 1, 2, 4, 5, 6, 9       | None                                                         |
| 4     | core/cluster/node_tests.py (MODIFY); .buildrunner/flaky-quarantine.json (NEW); jimmy_flaky_sync.py (NEW); autopilot-dispatch-prefix.sh (MODIFY) | 1, 3, 5, 6, 9          | After Phase 2 preferred (updates compare_baseline exclusion) |
| 5     | .claude/hooks/protect-files.sh (MODIFY); .claude/hooks/syntax-check.py (NEW)                                                                    | 1, 2, 3, 4, 6, 9       | None                                                         |
| 6     | /srv/jimmy/eval-corpus/\*\* (NEW, Jimmy-side); core/eval/corpus_loader.py (NEW); scripts/seed-eval-corpus.py (NEW)                              | 1, 2, 3, 4, 5, 9       | None                                                         |
| 7     | core/eval/runner.py (NEW); core/eval/below_executor.py (NEW); telemetry.db schema (MIGRATE eval_runs)                                           | 1, 2, 3, 4, 5, 8, 9    | 6 (needs corpus)                                             |
| 8     | core/eval/compare.py (NEW); core/eval/holdout_guard.py (NEW); core/dashboard_views.py (MODIFY)                                                  | 1, 2, 3, 4, 5, 9       | 7 (needs eval runs)                                          |
| 9     | core/ai_code_review.py (DELETE); core/cluster/cross_model_review.py (MODIFY); BUILD_cluster-max.md (MODIFY)                                     | 1, 2, 3, 4, 5, 6, 7, 8 | None                                                         |

**Shared-file watch:** Phases 2 and 4 both touch autopilot-dispatch-prefix.sh. Sequence 2 → 4 OR merge their edits in a single PR. Phases 3 and 7 both MIGRATE telemetry.db; run migrations in order (3 first since it adds a column to an existing table).

---

## Role Matrix (draft — finalized in Step 4.5 before BUILD write)

| Phase | bucket         | assigned_node | rationale                                                                                           |
| ----- | -------------- | ------------- | --------------------------------------------------------------------------------------------------- |
| 1     | backend-build  | muddy         | preflight.py is Muddy-side; tests live here                                                         |
| 2     | backend-build  | muddy         | dashboard_views.py + autopilot dispatch prefix live on Muddy                                        |
| 3     | backend-build  | muddy         | cost_tracker + opus_client + telemetry.db on Muddy                                                  |
| 4     | backend-build  | walter        | Walter owns test_results.db and /api/flaky; writes registry from here, Jimmy push is a network call |
| 5     | terminal-build | muddy         | .claude/hooks/ shell + small Python parser dispatch                                                 |
| 6     | backend-build  | jimmy         | corpus is /srv/jimmy/eval-corpus/, loader/seed scripts run from Jimmy                               |
| 7     | backend-build  | muddy         | orchestrator runs on Muddy; Below called as inference worker (not "assigned" — just dispatched to)  |
| 8     | backend-build  | muddy         | compare + holdout on Muddy; dashboard view addition                                                 |
| 9     | review         | muddy         | cross_model_review.py lives on Muddy; doc edit + deletes local                                      |

No phase lands on Lockwood or Otis as primary. Walter gains one phase (4). Jimmy gains one phase (6). Below is inference-dispatched-to (Phase 7), not phase-assigned.

---

## Sequencing Recommendation

1. Phases 1, 2, 3, 5, 9 in parallel (hardening wire-ups + cleanup). Cheap, high-leverage, different files.
2. Phase 4 after Phase 2 lands (Phase 4 calls into Phase 2's compare_baseline exclusion).
3. Phase 6 in parallel with any of the above (Jimmy-side work, no Muddy file conflicts).
4. Phase 7 after Phase 6.
5. Phase 8 after Phase 7.

Roll-up: Phases 1+2+3+5+9 → parallel. Phase 4 → after 2. Phase 6 → parallel with anything. Phases 7 → 8 → serial on corpus availability.
