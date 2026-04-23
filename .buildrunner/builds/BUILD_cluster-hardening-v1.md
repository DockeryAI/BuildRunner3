# Build: Cluster Hardening v1

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: backend-build, assigned_node: muddy }
      phase_2: { bucket: backend-build, assigned_node: muddy }
      phase_3: { bucket: backend-build, assigned_node: muddy }
      phase_4: { bucket: backend-build, assigned_node: walter }
      phase_5: { bucket: terminal-build, assigned_node: muddy }
      phase_6: { bucket: backend-build, assigned_node: jimmy }
      phase_7: { bucket: backend-build, assigned_node: muddy }
      phase_8: { bucket: backend-build, assigned_node: muddy }
      phase_9: { bucket: review, assigned_node: muddy }
```

**Source Plan SHA:** 0de207af41ccb6a402369b936f293c3f3e0edf1ad973983593ffc5d891718880
**Source Plan File:** .buildrunner/plans/plan-cluster-hardening-v1.md
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-22T19:13:58Z
**Deploy:** web

**Purpose:** Wire the seven solid-tier Claude-Code safety items onto BR3's existing cluster infrastructure. Items 1–4 are wire-ups on code that already exists. Item 5 fills an empty PreToolUse hook. Item 6 adds an eval corpus on Jimmy. Item 7 deletes the superseded single-model reviewer and adds a scope-drift judge.

**Target users:** Single operator (Byron) running BR3 against the 7-node Blues Cluster.

**Tech stack:** Python 3.11, FastAPI, SQLite (`.buildrunner/data.db` for CostTracker cost_entries + the new phase_budgets and eval_runs tables; `~/.walter/test_results.db` on Walter for test baselines), LanceDB (Jimmy), bash hooks under `~/.claude/settings.json` PreToolUse chain.

**Paths outside the Muddy repo tree that this spec modifies:**

- `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh`, `~/.buildrunner/scripts/runtime-dispatch.sh` — operator home-dir BuildRunner install.
- `.claude/hooks/protect-files.sh`, `.claude/hooks/bash-guard.sh` — project-level hooks (currently passthrough stubs).
- `~/.claude/settings.json` — PreToolUse chain registration; appended only.
- `/srv/jimmy/eval-corpus/**` on Jimmy (10.0.1.106).
- `~/.walter/test_results.db` on Walter (read-only from Muddy).

---

## Decisions (confirmed at "go" time)

1. **Default cost ceiling per phase:** $4.00 USD. Override via `cost_ceiling_usd: N` in the phase header.
2. **`tests_writable` default:** `false`. Phases that author or modify tests must opt in.
3. **Scope-drift veto posture:** `warn` in Phase 9 initially. Flip to `block` after 2 weeks of clean telemetry.
4. **Eval harness trigger scope:** opt-in per-change (`make eval` after prompt/skill/hook edits).
5. **Flaky 3-of-3 gate:** require 3 consecutive passes across 3 distinct Walter runs before `quarantine:new` → `trusted`.

---

### Phase 1: Test file lockdown

**Goal:** Claude Code cannot edit, delete, or weaken tests during a phase unless the phase declares `tests_writable: true`. Reward-hacking the test suite is mechanically prevented.

**Files:**

- core/runtime/preflight.py (MODIFY)
- core/runtime/**init**.py (MODIFY — helper re-export if needed)
- tests/runtime/test_preflight_test_lockdown.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Add helper `is_test_path(normalized_path: str) -> bool` in preflight.py that returns True when the path contains a `tests/` segment (`"/tests/" in path or path.startswith("tests/")`) OR matches `*_test.py`, `*.test.ts`, `*.test.tsx`, `*.spec.ts`, `*.spec.tsx`. Do NOT add `**` globs to `PROTECTED_PATH_PATTERNS` — `fnmatch` does not support recursive `**`.
- [ ] `is_protected_file()` (preflight.py:177) delegates to `is_test_path()` in addition to the existing fnmatch secrets check.
- [ ] Exemption: when env `BR3_TESTS_WRITABLE=1`, `is_test_path()` returns False. Secret patterns still block regardless.
- [ ] `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` exports `BR3_TESTS_WRITABLE=1` only when the active phase header declares `tests_writable: true`.
- [ ] Log every test-edit attempt (block + pass) to `.buildrunner/logs/test-lockdown.log` with `{timestamp, path, decision, reason, phase_id}`.
- [ ] Unit tests: blocked edit on tests/foo.py; blocked edit on pkg/tests/sub/bar_test.py; allowed edit under exemption; secrets still blocked under exemption; basename `*_test.py` blocked without exemption.

**Success Criteria:** Edit/Write attempts on any path under `tests/` or matching test naming return a structured rejection when the exemption is absent; existing secrets protection unchanged; all preflight unit tests pass.

**Parallelizable:** Yes — only touches preflight.py + a new test file.

---

### Phase 2: Regression gate on every iteration

**Goal:** The inner-loop pass rule becomes "the failing test now passes AND no previously-passing test now fails." Iterations that introduce a green→red regression are rejected and retried.

**Files:**

- core/dashboard_views.py (MODIFY — add `compare_baseline()`)
- core/runtime/regression_gate.py (NEW)
- ~/.buildrunner/scripts/autopilot-dispatch-prefix.sh (MODIFY — emit per-iteration gate hook)
- tests/runtime/test_regression_gate.py (NEW)

**Blocked by:** None (different files than Phase 1)

**Deliverables:**

- [ ] `compare_baseline(prev_snapshot, new_snapshot, quarantined_ids: set[str]) -> RegressionReport` reading Walter's `~/.walter/test_results.db` via existing `get_test_baseline_data()`.
- [ ] Report shape `{ new_pass, new_fail, regressed, cleared }`. Quarantined IDs are excluded from `regressed`.
- [ ] Autopilot inner loop invokes `compare_baseline` after each iteration. `regressed != []` → iteration rejected, retry instructed.
- [ ] Rejection message to Claude names regressed tests and suggests revert-or-fix.
- [ ] Unit tests: regression detected; no-change no-op; flaky-quarantined tests excluded from regressed set.

**Success Criteria:** A fabricated diff that breaks a previously-green test is rejected; a diff that only makes a red test green passes; regressed tests on the quarantine list are excluded from the gate.

**Parallelizable:** Yes with Phases 1, 3, 5.

---

### Phase 3: Hard cost ceiling per phase

**Goal:** Each phase carries a USD ceiling. `CostTracker`'s warn becomes a raised exception. Paid calls preflight against the ceiling; bust → phase halts and escalates.

**Database note:** `CostTracker` persists to `.buildrunner/data.db` (table `cost_entries`) per core/routing/cost_tracker.py:93. All schema changes in this phase apply to `data.db`, not `telemetry.db`.

**Files:**

- core/routing/cost_tracker.py (MODIFY — add `BudgetCeilingExceeded`, convert warn→raise, ceiling resolver, migration for `phase_budgets`)
- core/opus_client.py (MODIFY — preflight each paid call)
- ~/.buildrunner/scripts/runtime-dispatch.sh (MODIFY — upsert `phase_budgets` row and export ceiling)
- scripts/migrate-data-db-add-phase-budgets.py (NEW — idempotent, invoked via CostTracker `run_migration`)
- tests/routing/test_cost_ceiling.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Add `BudgetCeilingExceeded` exception in cost_tracker.py.
- [ ] New table `phase_budgets { phase_id TEXT PRIMARY KEY, ceiling_usd REAL NOT NULL, set_at TIMESTAMP }` in `.buildrunner/data.db` via the existing `run_migration` path (same mechanism `cost_entries` uses at cost_tracker.py:286-294). Upsert per phase at dispatch.
- [ ] `_check_budgets()` (cost_tracker.py:297) joins per-phase spend `(SUM(cost_entries.cost_usd) WHERE build_phase = current_phase)` against `phase_budgets.ceiling_usd` and raises `BudgetCeilingExceeded` when spent ≥ ceiling.
- [ ] Ceiling resolution precedence: phase header `cost_ceiling_usd: N` → `phase_budgets` row → env `BR3_COST_CEILING_USD` → default `4.00`.
- [ ] `opus_client.py` preflights each call via `CostTracker.would_exceed(phase_id, projected_usd)` (projected = `model_pricing * max_output_tokens`).
- [ ] `runtime-dispatch.sh` writes the ceiling to env and upserts `phase_budgets` before dispatch.
- [ ] Unit tests: bust raises; warn threshold logs but does not raise; missing row falls back to default; concurrent upsert safe.

**Success Criteria:** A phase configured with `ceiling=0.01` halts before a second paid call; `phase_budgets` exists after first run; existing `cost_entries` reads are unaffected.

**Parallelizable:** Yes with Phases 1, 2, 4, 5.

---

### Phase 4: Flaky-test quarantine registry

**Goal:** Promote Walter's implicit flaky detection to an explicit registry. Claude is told to skip (not "fix") quarantined tests. Fresh tests must pass 3-of-3 consecutive runs before counting as trusted.

**Files:**

- core/cluster/node_tests.py (MODIFY — registry writer + `GET /api/flaky/registry` + 3-of-3 filter on LAG())
- core/cluster/flaky_registry_client.py (NEW — Muddy-side HTTP pull with 60s TTL)
- .buildrunner/flaky-quarantine.json (NEW — Muddy-side snapshot)
- core/cluster/jimmy_flaky_sync.py (NEW — Walter-side Jimmy push with outbox retry)
- ~/.buildrunner/scripts/autopilot-dispatch-prefix.sh (MODIFY — inject quarantine list into prompt)
- tests/cluster/test_flaky_registry.py (NEW)

**Blocked by:** Phase 2 preferred — Phase 2's `compare_baseline` reader takes the quarantine set as input. Shipping 4 first is acceptable if Phase 2's reader is updated in the same PR.

**Deliverables:**

- [ ] Walter-side registry: after each run, upsert `{test_id, flaky_score, first_seen, last_flip, status: trusted|quarantined|new}` into `~/.walter/flaky-quarantine.json`.
- [ ] **Walter → Muddy sync over HTTP:** Walter exposes registry via new FastAPI route `GET /api/flaky/registry` on its existing node_tests.py service. Muddy-side `flaky_registry_client.py` pulls at autopilot dispatch time, writes `.buildrunner/flaky-quarantine.json`, caches 60s. No shared mount, no scp, no git sync.
- [ ] 3-of-3 filter on the existing LAG() query: `status: new` requires 3 consecutive green runs across distinct `walter_run_id` before flipping to `trusted`.
- [ ] Jimmy push: Walter POSTs delta entries to `http://10.0.1.106:8100/api/flaky/upsert` for LanceDB table `flaky_registry`. On unreachable Jimmy, buffer to local outbox and retry on next run.
- [ ] Autopilot prompt prefix reads `.buildrunner/flaky-quarantine.json` and injects the current quarantine list under a "do-not-fix, log-and-move-on" heading.
- [ ] Unit tests: 3-of-3 math; Muddy pull + snapshot write; Jimmy push stub + outbox retry; prompt-prefix injection; `compare_baseline` exclusion integration.

**Success Criteria:** Walter-side registry file exists after first run; Muddy-side snapshot is produced by the pull client on autopilot dispatch; Jimmy LanceDB has matching rows; a quarantined test does not appear in `regressed[]`; a new test stays `new` until 3 consecutive greens.

**Parallelizable:** Yes with Phases 1, 3, 5.

---

### Phase 5: ACI syntax guardrail on edits

**Goal:** Before any Edit/Write lands on disk, a fast parse check runs on the resulting file. Invalid syntax → rejection returned to Claude before the write.

**Files:**

- .claude/hooks/protect-files.sh (MODIFY — currently passthrough stub)
- .claude/hooks/syntax-check.py (NEW — fast parser dispatch by extension)
- tests/hooks/test_syntax_check.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Dispatch by extension: `.py` → `python3 -m py_compile`; `.js`/`.mjs`/`.cjs` → `node --check`; `.sh`/`.bash` → `bash -n`; `.json` → `python3 -c 'json.load(...)'`; `.yaml`/`.yml` → `yaml.safe_load`.
- [ ] **TypeScript and JSX/TSX are excluded.** BR3 has no root tsconfig.json and bare `tsc` on single .tsx files rejects valid JSX. Project-level TSX is validated by each project's own vite/tsc pipeline.
- [ ] Parse only — no lint, no type-check. Time budget 1.5s per file; timeout → fail-open pass-through.
- [ ] Unknown extensions (including `.ts`/`.tsx`) pass through silently.
- [ ] Rejection format `SYNTAX_REJECTED: <file> (<parser>): <first error line>`; Claude sees the string and re-plans.
- [ ] Write every pass/reject to `.buildrunner/logs/aci-guardrail.log` with duration.
- [ ] Unit tests: valid py/js/sh/json/yaml pass; invalid each rejected; `.ts`/`.tsx` pass through; unknown extension passes through; timeout passes through.

**Success Criteria:** Writing a syntactically invalid `.py` file is rejected with a one-line error and Claude re-plans; valid writes land in <1.5s overhead; TSX files are not blocked by this hook.

**Parallelizable:** Yes with Phases 1–4.

---

### Phase 6: Eval corpus storage and seeding on Jimmy

**Goal:** Establish the project-local eval corpus layout and seed it from existing adversarial-review artifacts + bug-fix commits. 30% holdout enforced at creation time.

**Files:**

- /srv/jimmy/eval-corpus/manifest.jsonl (NEW — on Jimmy)
- /srv/jimmy/eval-corpus/bugs/<id>/ (NEW — `task.md`, `failing_test.patch`, `fix.patch`, `labels.json`)
- /srv/jimmy/eval-corpus/README.md (NEW — schema + contribution flow)
- Jimmy FastAPI route `GET /api/eval/corpus?split=train|holdout|all` (NEW — appended to Jimmy's existing service)
- core/eval/**init**.py (NEW, Muddy)
- core/eval/corpus_loader.py (NEW, Muddy — HTTP client to Jimmy)
- api/routes/eval.py (NEW, Muddy — proxy/cache of Jimmy's route)
- api/server.py (MODIFY — register `eval.router`)
- scripts/seed-eval-corpus.py (NEW — mines `.buildrunner/adversarial-reviews/` and git log; runs on Jimmy)
- tests/eval/test_corpus_loader.py (NEW)
- tests/api/test_eval_routes.py (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Schema: `{id, title, task, failing_test_path, failing_test_content, fix_diff, category, labels[], split, seeded_from}`.
- [ ] Seed script mines 495+ adversarial-review JSONs (each `blocker` verdict → candidate bug) and git log commits with `fix:` prefix + test change.
- [ ] Deterministic holdout: `hash(id) % 10 < 3` → `split="holdout"`, tagged at creation, never rewritten.
- [ ] Jimmy route returns JSONL stream of manifest rows filtered by split; 200 OK on empty.
- [ ] Muddy route `GET /api/eval/corpus` proxies Jimmy with 60s cache.
- [ ] `corpus_loader.iter_bugs(split) -> Iterator[Bug]` reads via the Muddy proxy.
- [ ] LanceDB index `eval_corpus_embeddings` (256-dim, same embedder as research-library) built by seed script.
- [ ] Target ≥40 bugs seeded before Phase 7 begins.
- [ ] Unit tests: schema round-trip; 30% holdout tolerance ±3; split filtering; Jimmy route JSONL shape; Muddy proxy echoes with cache.

**Success Criteria:** `manifest.jsonl` has ≥40 rows; holdout count is 28–36% of total; `corpus_loader.py` returns correct per-split counts; LanceDB index reachable from Muddy.

**Parallelizable:** Yes with Phases 1–5, 9.

---

### Phase 7: Eval execution harness

**Goal:** Given a corpus + a config (prompt/skill/hook/model), run every bug and record pass rate, regression rate, cost, tool-call count. Below executes inference; Muddy orchestrates.

**Database note:** Eval results live in `.buildrunner/data.db` (same DB as `cost_entries`), new table `eval_runs`. Cost per bug is joined from `cost_entries` by `build_phase = '<run_id>/<bug_id>'` — each bug dispatch sets that phase scope so `CostTracker` attributes spend correctly.

**Files:**

- core/eval/runner.py (NEW — orchestrator; sets `build_phase` scope per bug)
- core/eval/below_executor.py (NEW — dispatches inference to Below via `/api/gpu` + `/api/inference` in node_inference.py)
- core/eval/metrics.py (NEW — joins `eval_runs` + `cost_entries`)
- scripts/run-eval.sh (NEW — CLI wrapper)
- scripts/migrate-data-db-add-eval-runs.py (NEW — adds `eval_runs` to `.buildrunner/data.db`)
- tests/eval/test_runner.py (NEW)

**Blocked by:** Phase 6 (needs corpus) AND Phase 3 (owns the `data.db` migration infra this phase reuses; serialize 3 → 7).

**Deliverables:**

- [ ] `eval_runs` table in `.buildrunner/data.db` via `CostTracker`-style `run_migration` — columns `run_id TEXT, config_hash TEXT, split TEXT, bug_id TEXT, passed INTEGER, regressed INTEGER, tool_calls INTEGER, duration_ms INTEGER, started_at TIMESTAMP, PRIMARY KEY (run_id, bug_id)`.
- [ ] `runner.run_config(config, split) -> EvalRun` iterates corpus, dispatches each bug to a fresh Claude Code session, sets `BR3_BUILD_PHASE="<run_id>/<bug_id>"`, writes one `eval_runs` row per bug. Cost is joined on demand from `cost_entries`.
- [ ] VRAM preflight: `GET http://<below_host>:<port>/api/gpu` (exists at node_inference.py:289); response is `{gpu_count, vram_total_mb, dual_gpu_ready, mode, ...}`. Abort if `gpu_count == 0` OR `vram_total_mb < 2048`; fallback to Muddy orchestrator with a log line.
- [ ] Per-bug metrics: `passed` (target test flipped red→green per Walter snapshot diff); `regressed` (≥1 previously-green test flipped red per Phase 2 `compare_baseline`); `tool_calls`; `duration_ms`.
- [ ] CLI `scripts/run-eval.sh --config <hash> --split train|holdout|all [--workers 2]`.
- [ ] Concurrency: 2 concurrent bugs; each runs in a transient git worktree so edits cannot collide.
- [ ] Unit tests: mock corpus + session; `/api/gpu` abort path; cost join; worktree cleanup on error.

**Success Criteria:** `run-eval.sh --split train` produces an `eval_runs` row per train bug; `SELECT COUNT(*) FROM eval_runs WHERE run_id=?` equals corpus train count; `/api/gpu` is queried at dispatch; Muddy fallback path is logged on insufficient VRAM.

**Parallelizable:** No with Phase 6; yes with Phases 1–5, 8, 9.

---

### Phase 8: Eval comparison and holdout enforcement

**Goal:** Turn eval runs into a comparison report. Given two config hashes, produce a diff of pass-rate / regression-rate / cost / tool-calls. Holdout is never used for tuning — only for sanity-check reports.

**Files:**

- core/eval/compare.py (NEW — diff two runs)
- core/eval/holdout_guard.py (NEW — enforces holdout isolation)
- scripts/eval-compare.sh (NEW — CLI wrapper)
- api/routes/eval.py (MODIFY — extend the route file created in Phase 6; add `GET /api/eval/compare`)
- tests/eval/test_compare.py (NEW)
- tests/eval/test_holdout_guard.py (NEW)
- tests/api/test_eval_compare_route.py (NEW)

**Blocked by:** Phase 7 (needs `eval_runs` data).

**Deliverables:**

- [ ] `compare.diff(run_a, run_b) -> ComparisonReport`: pass-rate delta, regression-rate delta, cost delta (via `cost_entries` join), tool-call delta, per-bug flip list.
- [ ] `holdout_guard.assert_clean(config_hash: str, commit_sha: str, changed_files: list[str]) -> GuardReport`. Changed files are the source of truth (caller extracts via `git diff --name-only <base>..<candidate>`); `commit_sha` is for logging; `config_hash` is what the eval used. Rejects if any changed file matches a path listed in holdout bug metadata (`failing_test_path` or files under `fix_diff`). Soft-gate (warn in report) by default; `BR3_HOLDOUT_GUARD_MODE=block` flips to hard reject.
- [ ] CLI `scripts/eval-compare.sh <baseline-hash> <candidate-hash>` — wraps `compare.diff`, prints table, invokes `holdout_guard` with `git diff --name-only <baseline>..<candidate>` for `changed_files`.
- [ ] Route `GET /api/eval/compare?baseline=...&candidate=...` returns JSON `ComparisonReport` — lives in `api/routes/eval.py` (same module as Phase 6).
- [ ] Unit tests: diff math; `holdout_guard` clean/contaminated/empty; empty-run rendering; route 400 on unknown hash.

**Success Criteria:** `eval-compare.sh A B` emits a readable diff table; the same comparison is reachable via `GET /api/eval/compare`; `holdout_guard` flags a contrived commit that touches a holdout `failing_test_path`.

**Parallelizable:** No with Phase 7; yes with Phase 9.

---

### Phase 9: Architect/builder/verifier cleanup and scope-drift judge

**Goal:** Delete the superseded single-model reviewer (core/ai_code_review.py). Add a scope-drift judge as a 4th pass inside cross_model_review.py. Document the architect/builder/verifier pattern in BUILD_cluster-max.md so future phases know the split already exists.

**Phase header flags:** `tests_writable: true` (required to delete `tests/test_ai_code_review.py` under Phase 1 lockdown).

**Files:**

- core/ai_code_review.py (DELETE)
- tests/test_ai_code_review.py (DELETE — finalize; partial-state per git status)
- core/cluster/cross_model_review.py (MODIFY — add `scope_drift_judge()` pass)
- core/cluster/cross_model_review_config.json (MODIFY — add `scope_drift_enabled`, `scope_drift_mode`)
- .buildrunner/builds/BUILD_cluster-max.md (MODIFY — architect/builder/verifier subsection)
- tests/cluster/test_scope_drift_judge.py (NEW)

**Blocked by:** None (independent of Phases 1–8)

**Deliverables:**

- [ ] Declare `tests_writable: true` in this phase's header so Phase 1 lockdown permits deleting the ai_code_review test file. Without this, the deletion is mechanically blocked.
- [ ] Delete core/ai_code_review.py; grep the repo for remaining `ai_code_review` imports and remove them; adjust any pre-commit hook still wired to it.
- [ ] Delete tests/test_ai_code_review.py (record in PR) under this phase's test-writable exemption.
- [ ] `scope_drift_judge()` receives: diff, phase "Success Criteria" text, phase "Files:" list. Returns `{verdict: pass|drift, out_of_scope_files: [...], out_of_scope_changes: [...]}`.
- [ ] Judge runs as the 4th pass after arbiter verdict. `mode: warn` → log + annotate artifact; `mode: block` → verdict flipped to BLOCKED.
- [ ] Config defaults: `scope_drift_enabled: true, scope_drift_mode: warn` (per Decision 3).
- [ ] BUILD_cluster-max.md: add "Architect / builder / verifier pattern" subsection under the role-matrix narrative; cross-link to cross_model_review.py.
- [ ] Unit tests: in-scope diff passes; out-of-scope file rejected; warn-mode does not flip verdict; block-mode flips it.

**Success Criteria:** `ai_code_review.py` removed + tree builds green; `scope_drift_judge` produces a verdict on at least 3 real review artifacts from `.buildrunner/adversarial-reviews/`; BUILD_cluster-max.md has the new subsection; judge warnings visible in review artifact JSON.

**Parallelizable:** Yes with Phases 1–8.

---

### Out of Scope (Future)

- Replacing `/predict` skill stub with a real phase-difficulty predictor (deferred — needs Phase 7/8 data as training signal).
- Deleting the project-level `.claude/hooks/bash-guard.sh` stub — leave in place; a separate security-hook spec may fill it.
- Generator/verifier split for "plain" phases (not just review) — separate spec if wanted.
- Dashboard UI panel for eval-harness results (Phase 8 adds the JSON endpoint; a full panel is follow-up UI work).
- Cross-project corpus sharing — corpus is BR3-scoped under `/srv/jimmy/eval-corpus/`; cross-project reads need an auth layer we don't want to design yet.

---

## Parallelization Matrix

| Phase | Key Files                                                                                                                             | Can Parallel With   | Blocked By                                |
| ----- | ------------------------------------------------------------------------------------------------------------------------------------- | ------------------- | ----------------------------------------- |
| 1     | core/runtime/preflight.py (MODIFY); tests/runtime/test_preflight_test_lockdown.py (NEW)                                               | 2, 3, 4, 5, 6, 9    | None                                      |
| 2     | core/dashboard_views.py (MODIFY); core/runtime/regression_gate.py (NEW); autopilot-dispatch-prefix.sh (MODIFY)                        | 1, 3, 5, 6, 9       | None                                      |
| 3     | core/routing/cost_tracker.py (MODIFY); core/opus_client.py (MODIFY); runtime-dispatch.sh (MODIFY); `data.db` (MIGRATE)                | 1, 2, 4, 5, 6, 9    | None                                      |
| 4     | core/cluster/node_tests.py (MODIFY); flaky_registry_client.py (NEW); jimmy_flaky_sync.py (NEW); autopilot-dispatch-prefix.sh (MODIFY) | 1, 3, 5, 6, 9       | 2 (quarantine set feeds compare_baseline) |
| 5     | .claude/hooks/protect-files.sh (MODIFY); .claude/hooks/syntax-check.py (NEW)                                                          | 1, 2, 3, 4, 6, 9    | None                                      |
| 6     | /srv/jimmy/eval-corpus/\*\* (NEW); Jimmy route; api/routes/eval.py (NEW); api/server.py (MODIFY); corpus_loader.py (NEW)              | 1, 2, 3, 4, 5, 9    | None                                      |
| 7     | core/eval/runner.py (NEW); below_executor.py (NEW); `data.db` (MIGRATE eval_runs)                                                     | 1, 2, 4, 5, 9       | 3 (data.db migration infra), 6 (corpus)   |
| 8     | core/eval/compare.py (NEW); holdout_guard.py (NEW); api/routes/eval.py (MODIFY)                                                       | 1, 2, 3, 4, 5, 6, 9 | 7 (needs eval_runs data)                  |
| 9     | core/ai_code_review.py (DELETE); cross_model_review.py (MODIFY); BUILD_cluster-max.md (MODIFY)                                        | 1, 2, 3, 4, 5, 6, 8 | None                                      |

**Shared-file watch:**

- Phases 2 and 4 both touch `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` → sequence 2 → 4 or merge edits in one PR.
- Phases 3 and 7 both migrate `.buildrunner/data.db` (disjoint schemas but serialize to avoid CI lock contention).
- Phases 6 and 8 both touch `api/routes/eval.py` (6 creates, 8 extends). Phase 8 is already blocked by 7 so 6 → 7 → 8 is natural.

---

## Sequencing Recommendation

1. Phases 1, 2, 3, 5, 9 in parallel (hardening wire-ups + cleanup).
2. Phase 4 after Phase 2 lands (quarantine set feeds `compare_baseline`).
3. Phase 6 in parallel with the above (Jimmy-side + small Muddy route registration).
4. Phase 7 after Phase 6 (corpus) AND Phase 3 (`data.db` migration infra).
5. Phase 8 after Phase 7 (`eval_runs` rows).

**Total Phases:** 9
