# Plan: Cluster Hardening v1

**Purpose:** Wire the seven solid-tier Claude-Code safety items onto BR3's existing cluster infrastructure. Items 1–4 are wire-ups on code that already exists (preflight patterns, Walter baseline, cost_tracker budgets, Walter flaky detection). Item 5 fills an empty PreToolUse hook. Item 6 is net-new eval corpus on Jimmy. Item 7 reframed: architect/builder/verifier already exists in cross_model_review.py — delete the superseded single-model reviewer and add a scope-drift judge pass.

**Target users:** Single operator (Byron) running BR3 against the 7-node Blues Cluster.

**Tech stack:** Python 3.11, FastAPI (core/cluster/base_service.py), SQLite (telemetry.db + Walter's ~/.walter/test_results.db), LanceDB (Jimmy), bash hooks (~/.claude/settings.json PreToolUse chain), ruff/py_compile/tsc/node --check for syntax validation.

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

- [ ] Add `"tests/*"`, `"tests/**"`, `"**/tests/*"`, `"**/tests/**"` to PROTECTED_PATH_PATTERNS.
- [ ] Read active-phase `tests_writable` flag from the BUILD spec header (Muddy already loads phase context via autopilot-dispatch-prefix.sh; expose flag via env `BR3_TESTS_WRITABLE=1`).
- [ ] Exemption: when `BR3_TESTS_WRITABLE=1`, test patterns pass through normally. Secret patterns always block.
- [ ] Log every test-edit attempt (block + pass) to `.buildrunner/logs/test-lockdown.log` for audit.
- [ ] Unit tests: blocked edit on tests/foo.py, allowed edit under exemption, secrets still blocked under exemption.

**Success criteria:** Edit/Write attempts on `tests/**` return a structured rejection to Claude when exemption is absent; the existing secrets-protection path is unchanged; all preflight unit tests pass.

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

**Goal:** Each phase carries a USD ceiling. cost_tracker's warn becomes a raised exception. Paid calls are preflighted against the ceiling; bust → phase halts and escalates, no matter the iteration count.

**Files:**

- core/routing/cost_tracker.py (MODIFY — convert warn to BudgetCeilingExceeded raise)
- core/opus_client.py (MODIFY — preflight check before paid call)
- ~/.buildrunner/scripts/runtime-dispatch.sh (MODIFY — read ceiling, enforce)
- .buildrunner/telemetry.db schema (MIGRATE — add `phase_cost_ceiling_usd REAL` column)
- scripts/migrate-telemetry-add-ceiling.sh (NEW)
- tests/routing/test_cost_ceiling.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Add `BudgetCeilingExceeded` exception class.
- [ ] `_check_budgets()` raises instead of warns when `spent_usd >= ceiling_usd`.
- [ ] Read ceiling from BUILD phase header key `cost_ceiling_usd` (default 4.00).
- [ ] opus_client.py preflights before each call; sums already-spent + worst-case next call (model pricing table + max_output_tokens).
- [ ] runtime-dispatch.sh writes ceiling to process env before dispatch.
- [ ] telemetry.db migration: add column; backfill existing rows with NULL (treated as default).
- [ ] Unit tests: bust triggers raise, warn threshold still logs but does not raise, missing column treated as default.

**Success criteria:** A phase configured with ceiling=$0.01 halts before a second paid call; telemetry.db column exists on fresh installs; existing reads unchanged.

**Parallelizable:** Yes with Phases 1, 2, 4, 5.

---

## Phase 4 — Flaky-test quarantine registry

**Goal:** Promote Walter's implicit flaky-detection to an explicit registry. Claude is told to skip (not "fix") quarantined tests. Fresh tests must pass 3-of-3 consecutive runs before they count as trusted.

**Files:**

- core/cluster/node_tests.py (MODIFY — add registry writer + 3-of-3 promotion filter to the existing LAG() query in /api/flaky)
- .buildrunner/flaky-quarantine.json (NEW — registry file, Muddy-readable)
- core/cluster/jimmy_flaky_sync.py (NEW — Jimmy LanceDB push)
- ~/.buildrunner/scripts/autopilot-dispatch-prefix.sh (MODIFY — inject quarantine list into dispatched prompt context)
- tests/cluster/test_flaky_registry.py (NEW)

**Blocked by:** Phase 2 preferred (compare_baseline reader takes the quarantine list as input — acceptable to ship Phase 4 first and update Phase 2 reader in the same PR).

**Deliverables:**

- [ ] Registry writer: after each Walter run, upsert `{ test_id, flaky_score, first_seen, last_flip, status: trusted|quarantined|new }` into .buildrunner/flaky-quarantine.json.
- [ ] 3-of-3 filter added to LAG() query: `status: new` tests require 3 consecutive green runs (across distinct walter_run_id) before flipping to `trusted`.
- [ ] Jimmy push: new entries replicated to LanceDB table `flaky_registry` for cross-session persistence.
- [ ] Autopilot prompt prefix includes current quarantine list under a "do-not-fix, log-and-move-on" heading.
- [ ] Phase 2's compare_baseline excludes quarantined tests from regressed[].
- [ ] Unit tests: 3-of-3 gate math, Jimmy push stub, prompt-prefix injection.

**Success criteria:** flaky-quarantine.json exists after first Walter run; Jimmy LanceDB has a matching row; a test marked quarantined does not appear in regressed[]; a new test does not get trusted status until it has 3 consecutive green runs.

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

- [ ] Dispatch by file extension: `.py` → `python3 -m py_compile`, `.ts/.tsx` → `npx tsc --noEmit --skipLibCheck --allowJs --target es2020 <file>`, `.js/.mjs/.jsx` → `node --check`, `.sh` → `bash -n`.
- [ ] Parse only — no lint, no type-check on the broader project. Time budget: 1.5s per file; timeout → pass-through (fail-open).
- [ ] Unknown extensions → pass-through.
- [ ] Rejection format: `SYNTAX_REJECTED: <file> (<parser>): <first error line>`; Claude sees this string and re-plans.
- [ ] Write to `.buildrunner/logs/aci-guardrail.log` every pass/reject with duration.
- [ ] Unit tests: valid py/ts/js/sh pass; invalid each rejected; unknown extension passes through; timeout passes through.

**Success criteria:** Writing a syntactically invalid .py file is rejected with a one-line error and Claude re-plans; writing a valid .py file lands in <1.5s overhead; unknown file types are not blocked.

**Parallelizable:** Yes with Phases 1–4.

---

## Phase 6 — Eval corpus: storage + seeding on Jimmy

**Goal:** Establish the project-local eval corpus layout and seed it from existing adversarial-review artifacts + bug-fix commits. 30% holdout enforced at creation time.

**Files:** (Jimmy-side — SSH to 10.0.1.106, commit/push from Jimmy repo)

- /srv/jimmy/eval-corpus/manifest.jsonl (NEW — one row per bug)
- /srv/jimmy/eval-corpus/bugs/<id>/ (NEW — per-bug directory: `task.md`, `failing_test.patch`, `fix.patch`, `labels.json`)
- /srv/jimmy/eval-corpus/README.md (NEW — schema + contribution flow)
- core/eval/**init**.py (NEW)
- core/eval/corpus_loader.py (NEW — reads corpus from Jimmy via existing FastAPI)
- scripts/seed-eval-corpus.py (NEW — mines .buildrunner/adversarial-reviews/ + git log)
- tests/eval/test_corpus_loader.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Corpus schema: `{ id, title, task, failing_test_path, failing_test_content, fix_diff, category, labels[], split: "train"|"holdout", seeded_from }`.
- [ ] Seed script mines 495+ adversarial-review JSONs; each `blocker`-verdict artifact becomes a candidate bug.
- [ ] Seed script also mines git log for commits with "fix:" prefix + test change; extracts failing→passing test as task.
- [ ] 30% holdout: deterministic hash(id) % 10 < 3 → split="holdout"; tagged at creation, never rewritten.
- [ ] corpus_loader.py exposes `iter_bugs(split: str) -> Iterator[Bug]` reading over FastAPI GET `/api/eval/corpus?split=train`.
- [ ] LanceDB index `eval_corpus_embeddings` (256-dim, same embedder as research-library) for analog-bug retrieval.
- [ ] Unit tests: schema round-trip, 30% holdout count tolerance ±3, loader returns only requested split.
- [ ] Target ≥ 40 bugs seeded before Phase 7 begins.

**Success criteria:** manifest.jsonl has ≥40 rows; holdout count is 28–36% of total; corpus_loader.py returns correct row counts per split; LanceDB index reachable from Muddy.

**Parallelizable:** Yes with Phases 1–5, 9.

---

## Phase 7 — Eval execution harness

**Goal:** Given a corpus + a config (prompt/skill/hook/model), run every bug and record pass rate, regression rate, cost, tool-call count to telemetry.db. Below executes inference; Muddy orchestrates.

**Files:**

- core/eval/runner.py (NEW — orchestrator)
- core/eval/below_executor.py (NEW — dispatches inference to Below, handles VRAM monitoring)
- core/eval/metrics.py (NEW — computes pass/regression/cost/tool-calls per run)
- scripts/run-eval.sh (NEW — CLI wrapper)
- telemetry.db schema (MIGRATE — new table `eval_runs`: `run_id, config_hash, split, bug_id, passed, regressed, cost_usd, tool_calls, duration_ms, started_at`)
- scripts/migrate-telemetry-add-eval-runs.sh (NEW)
- tests/eval/test_runner.py (NEW)

**Blocked by:** Phase 6 (needs corpus)

**Deliverables:**

- [ ] `runner.run_config(config, split) -> EvalRun` iterates corpus, dispatches each bug to a fresh Claude Code session, records metrics.
- [ ] below_executor respects VRAM headroom: pre-call check via `curl $BELOW/api/health`; abort if VRAM_free < 2GB; escalate to Muddy.
- [ ] Per-bug metrics: passed (target test flipped red→green), regressed (≥1 other test flipped green→red), cost_usd (from cost_tracker), tool_calls (from session log), duration_ms.
- [ ] eval_runs table + migration.
- [ ] CLI: `scripts/run-eval.sh --config <hash> --split train|holdout|all`.
- [ ] Concurrency: 2 concurrent bugs by default (tunable via `--workers`); corpus size / workers dictates runtime.
- [ ] Unit tests: mock corpus, mock session, runner tallies correctly; VRAM-abort path exits clean.

**Success criteria:** `run-eval.sh --split train` produces an eval_runs row per train bug; telemetry.db query `SELECT COUNT(*) FROM eval_runs WHERE run_id=?` equals corpus train count; Below VRAM never drops below 2GB during runs.

**Parallelizable:** No with Phase 6; yes with Phases 1–5, 8, 9.

---

## Phase 8 — Eval comparison + holdout enforcement

**Goal:** Turn eval runs into a comparison report. Given two config hashes, produce a diff of pass-rate / regression-rate / cost / tool-calls. Holdout split is never used for tuning — only for sanity-check reports.

**Files:**

- core/eval/compare.py (NEW — diff two runs)
- core/eval/holdout_guard.py (NEW — enforces holdout isolation)
- scripts/eval-compare.sh (NEW — CLI wrapper)
- core/dashboard_views.py (MODIFY — add `/api/eval/compare` view for dashboard)
- tests/eval/test_compare.py (NEW)
- tests/eval/test_holdout_guard.py (NEW)

**Blocked by:** Phase 7

**Deliverables:**

- [ ] `compare.diff(run_a, run_b) -> ComparisonReport`: pass_rate delta, regression_rate delta, cost delta, tool-call delta, per-bug flip list.
- [ ] `holdout_guard.assert_not_tuned_on(config_hash)`: rejects if a tuning commit touches files mentioned in holdout bug metadata. Soft-gate (warning) by default; flippable to hard-gate via env var.
- [ ] CLI: `scripts/eval-compare.sh <baseline-hash> <candidate-hash>`.
- [ ] Dashboard view at /api/eval/compare returns JSON for UI consumption.
- [ ] Unit tests: diff math, holdout guard flags tuning commit, report renders on empty runs.

**Success criteria:** `eval-compare.sh A B` emits a readable diff table; the same comparison is visible on the dashboard; holdout-guard flags a contrived "tuned on holdout" commit.

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
