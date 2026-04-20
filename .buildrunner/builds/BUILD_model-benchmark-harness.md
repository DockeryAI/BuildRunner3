# Build: model-benchmark-harness

**Created:** 2026-04-16
**Status:** Phase 1 Not Started
**Deploy:** web — `npm run build`

## Overview

Scientifically compare Codex 5.4 vs Claude Opus 4.7 on BuildRunner3 phase work. Produce a trustworthy default-runtime recommendation backed by ~300 task-level observations across 30 phases, with context-poisoning defenses, a neutral third-party judge, dual sub-studies (native vs neutral prompting), and statistically rigorous analysis (Bradley-Terry pairwise ratings + mixed-effects regression + clustered bootstrap + Benjamini-Hochberg correction + training-cutoff stratification).

**Design invariants:**

1. N ≈ 300 checklist items across 30 phases (nested mixed-effects analysis)
2. Third-party judge (GPT-5 or Gemini via OpenRouter) — never Claude or Codex
3. Training-cutoff stratification — pre-cutoff vs post-cutoff reported separately
4. Spec paraphrasing + recognition probe defeat token-level memorization
5. Dual sub-study — native prompts (each model's skill) + neutral (shared minimal)
6. Double-pass judging with A/B swap; unstable pairs excluded from primary analysis
7. Format normalization via Prettier/Black erases model-identity style tells
8. Judge-human calibration — Byron scores 60 items to validate agreement
9. Bradley-Terry pairwise ratings + BH correction on all reported p-values
10. Clustered bootstrap CIs — resample phases not items
11. Chen 2021 pass@k unbiased estimator for test-pass across 3 replications
12. Single-harness caveat disclosed in report header

## Parallelization Matrix

| Phase | Key Files                                           | Can Parallel With | Blocked By |
| ----- | --------------------------------------------------- | ----------------- | ---------- |
| 1     | core/benchmark/models.py, cli.py, pyproject.toml    | -                 | -          |
| 2     | core/benchmark/selector.py, training_cutoffs.py     | 3                 | 1          |
| 3     | core/benchmark/runner.py, prompts.py                | 2                 | 1          |
| 4     | core/benchmark/paraphraser.py, recognition_probe.py | 5, 6              | 3          |
| 5     | core/benchmark/scorer.py, pass_at_k.py              | 4, 6              | 3          |
| 6     | core/benchmark/judge.py, formatter.py               | 4, 5              | 3          |
| 7     | core/benchmark/aggregator.py, stats.py              | -                 | 5, 6       |
| 8     | core/benchmark/human_validator.py, reporter.py      | -                 | 7          |
| 9     | .buildrunner/benchmarks/results/pilot/              | -                 | 8          |
| 10    | .buildrunner/benchmarks/results/full-n30/           | -                 | 9          |

**Parallelizable groups:** (2, 3), (4, 5, 6). Phases 7–10 are strictly sequential.

## Phases

### Phase 1: Foundation + Data Models

**Status:** not_started
**Goal:** `br benchmark --help` prints usage. All dataclasses defined. Config schema locked.
**Files:**

- core/benchmark/**init**.py (NEW)
- core/benchmark/models.py (NEW)
- core/benchmark/cli.py (NEW)
- core/benchmark/prompts.py (NEW)
- .buildrunner/benchmarks/config.yaml (NEW)
- pyproject.toml (MODIFY)

**Blocked by:** None

**Deliverables:**

- [ ] PhaseSpec, RunResult, ObjectiveMetrics, AdherenceMetrics, JudgeVerdict, BenchmarkConfig dataclasses
- [ ] Click/Typer CLI skeleton with run/select/score/judge/report/resume subcommands
- [ ] config.yaml schema documented with every field and example values
- [ ] pyproject.toml wires `br benchmark` as CLI entry point
- [ ] `python -m core.benchmark.cli --help` returns without error
- [ ] Minimal unit test confirming dataclasses serialize round-trip to JSON

**Success Criteria:** CLI prints usage. Dataclasses round-trip to JSON cleanly. No logic yet.

---

### Phase 2: Phase Selector + Contamination Stratification

**Status:** not_started
**Goal:** `br benchmark select --count 30` returns a stratified, filtered list of candidate phases with training-cutoff tags.
**Files:**

- core/benchmark/selector.py (NEW)
- core/benchmark/training_cutoffs.py (NEW)
- tests/benchmark/test_selector.py (NEW)

**Blocked by:** Phase 1
**After:** Phase 1 (can parallelize with Phase 3)

**Deliverables:**

- [ ] BUILD spec markdown parser extracting phase number, files, checklist, lock: commit SHA
- [ ] Candidate scoring formula (checklist count + files + verify + layer diversity)
- [ ] Self-containment filter (excludes phases referencing deliverables from later phases)
- [ ] External-only-files filter (excludes phases with zero in-repo file changes)
- [ ] Training-cutoff stratification (tags each phase pre-cutoff or post-cutoff per model)
- [ ] Exclusion of phases already in benchmark_registry.jsonl
- [ ] `br benchmark select` outputs ranked candidates with strata balance

**Success Criteria:** Returns 30 candidates balanced across layers and cutoff strata.

---

### Phase 3: Execution Engine — Worktree + Dispatch

**Status:** not_started
**Goal:** Runner sets up isolated worktree at pre-phase commit, dispatches to either model via cluster, captures all outputs.
**Files:**

- core/benchmark/runner.py (NEW)
- core/benchmark/prompts.py (MODIFY)
- tests/benchmark/test_runner.py (NEW)

**Blocked by:** Phase 1
**After:** Phase 1 (can parallelize with Phase 2)

**Deliverables:**

- [ ] setup_worktree() resolves lock: commit and creates /tmp/br3-bench-<uuid>/
- [ ] teardown_worktree() captures diff and removes worktree cleanly
- [ ] dispatch_codex_run() invokes dispatch-to-node.sh --runtime codex otis
- [ ] dispatch_claude_run() invokes dispatch-to-node.sh --runtime claude lomax
- [ ] Token + wall-clock + exit code captured for every run
- [ ] Fresh OS process per run (no session reuse, no residual state)
- [ ] Native sub-study loads /codex or /opus skill preamble symmetrically
- [ ] Neutral sub-study uses identical minimal prompt for both models

**Success Criteria:** A single test run executes end-to-end on a real past phase: worktree created, model dispatched, diff captured, worktree cleaned up.

---

### Phase 4: Contamination Defenses — Paraphrasing + Recognition Probe

**Status:** not_started
**Goal:** Spec is semantically paraphrased before being shown to model. Recognition probe measures per-phase contamination risk.
**Files:**

- core/benchmark/paraphraser.py (NEW)
- core/benchmark/recognition_probe.py (NEW)
- tests/benchmark/test_paraphraser.py (NEW)
- tests/benchmark/test_recognition_probe.py (NEW)

**Blocked by:** Phase 3
**After:** Phase 3 (can parallelize with Phase 5 and Phase 6)

**Deliverables:**

- [ ] Paraphraser rewrites BUILD spec checklist without changing semantics (neutral LLM call)
- [ ] Paraphrase preserves file paths and identifier names (only prose rewritten)
- [ ] Original spec retained for scorer ground truth
- [ ] Recognition probe sends spec to each contestant pre-run, asks if seen before
- [ ] Recognition score logged as covariate in run_meta.json
- [ ] Paraphrase quality check — semantic-equivalence validator via cluster semantic-search
- [ ] Fallback: if paraphraser fails, log and use original (flag the run)

**Success Criteria:** Paraphrased specs pass semantic-equivalence check. Probe returns scalar score per (phase, model).

---

### Phase 5: Objective Scoring + Plan Adherence

**Status:** not_started
**Goal:** Scorer produces ObjectiveMetrics and AdherenceMetrics for any completed run.
**Files:**

- core/benchmark/scorer.py (NEW)
- core/benchmark/pass_at_k.py (NEW)
- tests/benchmark/test_scorer.py (NEW)

**Blocked by:** Phase 3
**After:** Phase 3 (can parallelize with Phase 4 and Phase 6)

**Deliverables:**

- [ ] Chen 2021 pass@k unbiased estimator implemented and unit-tested
- [ ] Test-pass rate computed from Walter API across 3 replications per task
- [ ] tsc, eslint, ruff, jscpd, lizard integrations (subprocess + JSON parse)
- [ ] Walter verdict + Lomax build verdict pulled via HTTP
- [ ] File precision/recall vs phase_spec.declared_files
- [ ] Checklist item keyword-match counter (keyword extraction from each item)
- [ ] Scope-creep LOC (diff lines outside declared files)
- [ ] Per-checklist-item binary score (delivered / partial / missed)

**Success Criteria:** Scorer handles a real past-phase diff and agrees with Walter's verdict.

---

### Phase 6: Third-Party Judge + Blinding Protocol

**Status:** not_started
**Goal:** Blind pairwise judge dispatched to non-contestant model. Double-pass with swap. Position-stability detection.
**Files:**

- core/benchmark/judge.py (NEW)
- core/benchmark/formatter.py (NEW)
- core/benchmark/prompts.py (MODIFY)
- tests/benchmark/test_judge_blinding.py (NEW)
- tests/benchmark/test_formatter.py (NEW)

**Blocked by:** Phase 3
**After:** Phase 3 (can parallelize with Phase 4 and Phase 5)

**Deliverables:**

- [ ] OpenRouter integration for GPT-5 (primary) + Gemini 2.5 (secondary)
- [ ] Format normalization via Prettier (TS/JS) and Black (Python) before judge sees diff
- [ ] Metadata stripping: no commit messages, no git log, no model identifiers
- [ ] Deterministic A/B label assignment using sha256(run_id + blind_salt)
- [ ] Double-pass: each pair judged twice with positions swapped
- [ ] Position-unstable pairs flagged and excluded from primary analysis
- [ ] JudgeVerdict parsed into structured JSON (5 dimensions + overall winner)
- [ ] Inter-judge agreement logged when both judges run

**Success Criteria:** Pair judged end-to-end, blinded correctly. De-blinding classifier on anonymized diffs fails above chance.

---

### Phase 7: Statistical Analysis Engine

**Status:** not_started
**Goal:** Aggregator produces Bradley-Terry ratings, mixed-effects coefficients, clustered bootstrap CIs, BH-corrected p-values, pre/post-cutoff strata.
**Files:**

- core/benchmark/aggregator.py (NEW)
- core/benchmark/stats.py (NEW)
- tests/benchmark/test_stats.py (NEW)
- tests/benchmark/test_aggregator.py (NEW)

**Blocked by:** Phase 5, Phase 6

**Deliverables:**

- [ ] Bradley-Terry pairwise rating with bootstrap CI
- [ ] Mixed-effects logistic regression (binary outcomes, phase as random intercept)
- [ ] Linear mixed model for continuous scores (item nested in phase)
- [ ] Clustered bootstrap — resample phases not items, 10k iterations
- [ ] Benjamini-Hochberg correction applied across all reported p-values
- [ ] Hodges-Lehmann effect size estimator
- [ ] Pre-cutoff vs post-cutoff stratified fits with coefficient comparison
- [ ] Power analysis report for the achieved sample size

**Success Criteria:** Given synthetic input with a known effect, aggregator recovers the effect within the reported CI.

---

### Phase 8: Human Validation + Report Generator

**Status:** not_started
**Goal:** CLI workflow for Byron's 20% human spot-check. Final markdown report with mandatory caveat section.
**Files:**

- core/benchmark/human_validator.py (NEW)
- core/benchmark/reporter.py (NEW)
- core/benchmark/prompts.py (MODIFY)
- tests/benchmark/test_reporter.py (NEW)

**Blocked by:** Phase 7

**Deliverables:**

- [ ] `br benchmark validate` presents 60 random items to Byron for scoring
- [ ] Judge-human agreement rate computed per dimension
- [ ] Agreement threshold check (abort report if agreement < 70%)
- [ ] Report generator produces markdown with fixed structure (caveats first)
- [ ] Per-sub-study breakdown (native vs neutral prompt)
- [ ] Per-cutoff-stratum breakdown (pre vs post training cutoff)
- [ ] Cost table (tokens, wall-clock, $USD per model per sub-study)
- [ ] Raw data JSONL export with every (phase, model, run, item, score) tuple

**Success Criteria:** Running on a completed pilot produces a full report with all sections populated, ready to share.

---

### Phase 9: Pilot Run (N=7 smoke test)

**Status:** not_started
**Goal:** Execute a 7-phase dry run to shake out harness bugs, profile performance, confirm API costs are in the expected range.
**Files:**

- .buildrunner/benchmarks/results/pilot/ (NEW)
- .buildrunner/benchmarks/reports/pilot_report.md (NEW)

**Blocked by:** Phase 8

**Deliverables:**

- [ ] `br benchmark run --phases 7 --runs 3 --pilot` completes without crash
- [ ] All 42 runs (7 × 2 models × 3 runs) produce valid RunResults
- [ ] Scorer produces complete metrics for every run
- [ ] Judge produces verdicts for every pair
- [ ] Human validation step produces agreement rate
- [ ] Pilot report generated end-to-end
- [ ] Any harness bugs discovered are logged and fixed before Phase 10
- [ ] Runtime + cost measurements update the N=30 budget estimate

**Success Criteria:** Pilot report complete, judge-human agreement above 70%, no unresolved harness bugs. If agreement is below threshold, rubric revision is required before Phase 10.

---

### Phase 10: Full Benchmark Run (N=30) + Public Report

**Status:** not_started
**Goal:** Execute the full 30-phase study and publish the trustworthy result.
**Files:**

- .buildrunner/benchmarks/results/full-n30/ (NEW)
- .buildrunner/benchmarks/reports/full-n30_report.md (NEW)
- .buildrunner/benchmarks/reports/full-n30_data.jsonl (NEW)
- .buildrunner/runtime.json (MODIFY)

**Blocked by:** Phase 9

**Deliverables:**

- [ ] `br benchmark run --phases 30 --runs 3 --sub-studies native,neutral` completes
- [ ] All objective, adherence, and judge metrics collected across both sub-studies
- [ ] Byron completes 60-item human validation
- [ ] Final report with caveats section prominent
- [ ] Bradley-Terry ratings with CIs published
- [ ] Pre/post-cutoff stratification reported
- [ ] Raw JSONL archived for future re-analysis
- [ ] Default-runtime recommendation committed to runtime.json if warranted

**Success Criteria:** Report passes internal review (three-tier agreement documented, judge-human calibration reported, no analysis decisions made after seeing results). Result changes or deliberately preserves the BR3 default runtime.

---

## Out of Scope (Future)

- Harness-diversity study (aider, Cursor, Cline) — single harness now, multiple later
- Third model comparison (Gemini, Qwen, local models) — two-model focus first
- Continuous re-benchmarking on every model release — manual re-run
- Public leaderboard publication — internal use first
- Held-out test set expansion beyond 10 reserved phases
- Languages beyond Python + TypeScript — BR3-specific for v1
- UI dashboard for benchmark results — markdown reports only
- Automated per-task runtime routing based on predicted winner — manual toggle

## Risks

| Risk                                                 | Mitigation                                                                               |
| ---------------------------------------------------- | ---------------------------------------------------------------------------------------- |
| OpenRouter access to GPT-5/Gemini lapses mid-run     | Fall back to Llama 3.1 405B via OpenRouter or local Qwen on Below                        |
| Walter flakes inflate test-pass variance             | pass@k averages across replications; flakes logged and reported separately               |
| Paraphraser changes semantic difficulty accidentally | Semantic-equivalence validator via cluster semantic-search before acceptance             |
| Judge-human agreement below 70% on pilot             | Rubric revision required before N=30                                                     |
| Cluster contention during 15–20 hour full run        | Schedule overnight; Otis + Lomax dedicated during window                                 |
| Byron doesn't have time for 60-item validation       | Minimum 30 items yields useful agreement estimate; abort below 30                        |
| Two sub-studies disagree on winner                   | That is the finding — report both, recommend based on practical ergonomics               |
| Result is "no clear winner"                          | Valid outcome — default stays, report produces cost/speed breakdown for per-task routing |

## Session Log

_Will be updated by /begin_
