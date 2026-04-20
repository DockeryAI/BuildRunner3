# A/B Benchmark: Codex 5.4 vs Claude Opus 4.7 — Implementation Plan

**Document path:** `.buildrunner/benchmarks/PLAN.md`
**Created:** 2026-04-16
**Author:** Byron Hudson
**Scope:** Post-phase coding task benchmark. Codex 5.4 vs Claude Opus 4.7. Statistical rigor. Repeatable harness. Otis as blind judge.

---

## Orientation

**What this is not:** A one-off experiment. The harness is a permanent BR3 module (`core/benchmark/`) with a CLI entry point, reusable across future model comparisons.

**What this is not touching:** `cross_model_review.py` is extended, not rewritten. The live dispatch chain is not modified. No new cluster nodes.

**The key insight from exploring the codebase:** BR3 already has everything needed — `lock:` and `complete:` commits mark exact phase boundaries in git history, `dispatch-to-node.sh --runtime` already supports both runtimes, `core/runtime/` has the `RuntimeResult` envelope, `quality-standards.yaml` already declares the objective thresholds, and Walter + Lomax already emit pass/fail verdicts. The benchmark is a thin orchestration layer on top of existing infrastructure.

---

## Phase Selection Rubric

Before any code is written, Byron selects 7–9 benchmark phases from completed BUILD specs using these criteria.

**Required coverage:**

| Dimension                       | Target     | Example candidates                                                                                                                    |
| ------------------------------- | ---------- | ------------------------------------------------------------------------------------------------------------------------------------- |
| Backend/Python (no UI)          | 2–3 phases | codex-integration Phase 4 (runtime contract), walter-auto-provision Phase 1 (server-side API)                                         |
| Infra/Shell (scripts + config)  | 1–2 phases | walter-auto-provision Phase 2 (dispatch shell), rock-solid-build-tracking Phase 5 (adversarial dispatch hardening)                    |
| UI/Frontend (dashboard panels)  | 1–2 phases | dashboard-intelligence-layer Phase 3 (token stats panel), dashboard-intelligence-layer Phase 5 (auto-review integration)              |
| Mixed (Python + shell + config) | 1–2 phases | cross-model-review Phase 2 (the review engine itself — a pure Python module), codex-integration Phase 6 (preflight/postflight policy) |
| Large scope (≥8 files)          | 1 phase    | codex-integration Phase 9 (command compiler + skill translation)                                                                      |
| Small scope (≤3 files)          | 1 phase    | walter-auto-provision Phase 3 (bulk seed script)                                                                                      |

**Scoring formula (use to rank candidates):**

```
candidate_score = (checklist_items_count * 0.4)      # more items = harder = better signal
                + (files_declared * 0.3)              # wider file scope = harder
                + (has_verify_command * 0.2)           # explicit verify = measurable ground truth
                + (layer_diversity_bonus * 0.1)        # prefer underrepresented layers
```

**Elimination criteria:**

- Phases whose `lock:` commit is less than 3 commits before `complete:` (too trivial — model produced almost nothing)
- Phases where the BUILD spec `Files:` list contains external-only paths (`~/.buildrunner/`, `~/.claude/`) with zero in-repo files (can't diff)
- Hardware phases (cluster-max Phase 1 — no code)
- Phases already used in a prior benchmark run (tracked in `benchmark_registry.jsonl`)

**Recommended starting set (Byron confirms before running):**

1. `BUILD_codex-full-br3-integration` Phase 4 — Runtime contract, edit normalization (backend, medium, 6 files)
2. `BUILD_cross-model-review` Phase 2 — Cross-model review engine (backend Python, medium, 4 files)
3. `BUILD_walter-auto-provision` Phase 1 — Server-side auto-provision (backend Python, small, 1 file)
4. `BUILD_rock-solid-build-tracking` Phase 1 — SQLite single writer (mixed, large, 7 files)
5. `BUILD_dashboard-intelligence-layer` Phase 3 — Token stats panel (UI/JS, small, 2 files)
6. `BUILD_walter-sentinel-hardening` Phase 1 — Race condition hardening (backend Python, medium, 2 files)
7. `BUILD_cluster-build-orchestration` Phase 1 — Commit-triggered validation (shell/infra, micro, 1 file)

Seven phases × 2 models × 3 runs = **42 total executions.** At ~15 min average execution time, total wall-clock is ~10 hours. With parallel dispatch to Otis + Lomax this collapses to ~3–4 hours.

---

## Architecture

### Directory Layout

```
core/benchmark/
    __init__.py
    selector.py          # Phase candidate scoring + selection logic
    driver.py            # Top-level orchestration: reads benchmark config, emits run plan
    runner.py            # Per-run execution: worktree setup, model dispatch, capture
    scorer.py            # Metrics collection per completed run
    judge.py             # Blind pairwise judge dispatch to Otis
    aggregator.py        # Statistical analysis, report generation
    models.py            # Dataclasses: BenchmarkConfig, PhaseRun, RunResult, JudgeVerdict
    prompts.py           # All judge + runner prompt templates (no prompts buried in logic)
    cli.py               # Click/Typer CLI: `br benchmark run`, `br benchmark score`, `br benchmark report`

.buildrunner/benchmarks/
    PLAN.md              # This document
    benchmark_registry.jsonl  # Append-only log of every run ever attempted
    config.yaml          # Active benchmark configuration (phases, N, models, seed)
    results/
        <run_id>/
            meta.json
            phase_runs/
                <phase_id>_<model>_<run_n>/
                    run_meta.json       # timing, tokens, cost estimate, exit code
                    diff.patch          # git diff vs pre-phase commit
                    stdout.log
                    stderr.log
                    checklist_match.json
                    objective_metrics.json
                    judge_input_A.md    # blinded, randomized label assignment
                    judge_input_B.md
                    judge_verdict.json
    reports/
        <run_id>_report.md
        <run_id>_data.jsonl
```

### Module Responsibilities

**`models.py`** — All dataclasses. Nothing else imports from nowhere — everything imports from here. Key types:

```python
@dataclass
class PhaseSpec:
    build_spec: str          # e.g. "BUILD_codex-full-br3-integration"
    phase_number: int
    phase_name: str
    pre_phase_commit: str    # git SHA of the lock: commit immediately before this phase
    declared_files: list[str]
    checklist_items: list[str]
    difficulty_score: float
    layer: str               # backend | infra | ui | mixed

@dataclass
class RunResult:
    run_id: str
    phase_spec: PhaseSpec
    model: str               # "codex-5.4" | "claude-opus-4.7"
    run_index: int           # 0, 1, 2
    wall_seconds: float
    input_tokens: int
    output_tokens: int
    cost_usd_estimate: float
    diff_patch: str
    stdout: str
    stderr: str
    exit_code: int
    worktree_path: str
    label: str               # "A" or "B" — randomly assigned, used for blinding

@dataclass
class ObjectiveMetrics:
    test_pass_rate: float         # vitest/pytest pass % from Walter verdict
    new_tests_added: int
    tsc_errors: int
    eslint_errors: int
    ruff_errors: int
    jscpd_duplication_pct: float
    cyclomatic_delta: float       # vs pre-phase baseline
    walter_verdict: str           # PASS | FAIL | FLAKE | TIMEOUT
    lomax_verdict: str            # PASS | FAIL | SKIP

@dataclass
class AdherenceMetrics:
    files_declared: int
    files_touched: int
    files_touched_in_scope: int
    precision: float              # files_touched_in_scope / files_touched
    recall: float                 # files_touched_in_scope / files_declared
    checklist_matched: int
    checklist_total: int
    checklist_rate: float
    scope_creep_loc: int          # LOC outside declared files

@dataclass
class JudgeVerdict:
    run_id: str
    phase_id: str
    winner_label: str             # "A" or "B" — judge never knows model identity
    winner_model: str             # resolved after unblinding
    scores: dict                  # {"correctness": (A, B), "readability": (A, B), ...}
    rationale: str
    judge_model: str              # "claude-opus-4.7" running on Otis
    judge_node: str               # "otis"
```

**`selector.py`** — Reads all BUILD specs from `.buildrunner/builds/`, scores candidates, returns ranked list. Reads `benchmark_registry.jsonl` to exclude already-benchmarked phases.

**`driver.py`** — Reads `benchmark_registry.jsonl` to get a random seed, generates the execution plan as an ordered list of `(phase, model, run_n)` tuples randomized via Fisher-Yates shuffle (seed logged for reproducibility). Emits `plan.jsonl` before any execution begins. Handles `--dry-run` flag.

**`runner.py`** — The core execution loop. For each `(phase, model, run_n)` tuple:

1. Calls `/worktree` skill to create isolated worktree at the pre-phase commit
2. Loads the model's skill file (either `/codex` or `/opus`) — **this is the symmetric prompting guarantee**
3. Dispatches to Otis (for Codex runs) or runs locally/Lomax (for Claude runs) via `dispatch-to-node.sh`
4. Captures diff, stdout, stderr, timing, token counts
5. Cleans up worktree

**`scorer.py`** — Given a completed `RunResult`, computes `ObjectiveMetrics` and `AdherenceMetrics`. Calls Walter API for test verdict. Calls `tsc`, `eslint`, `ruff`, `jscpd`. Parses spec checklist against diff.

**`judge.py`** — Assembles blinded judge inputs, dispatches to Otis via `dispatch-to-node.sh --runtime claude`, parses `JudgeVerdict`. Never exposes model names.

**`aggregator.py`** — Runs Wilcoxon signed-rank tests, computes bootstrap CIs, generates markdown report.

**`cli.py`** — Single entry point. `br benchmark run --phases 7 --runs 3 --seed 42`.

---

## Milestone Breakdown

### Milestone 0 — Foundation (effort: ~3h)

**Goal:** Skeleton compiles, `br benchmark --help` works, config schema is locked.

**Files to CREATE:**

- `core/benchmark/__init__.py`
- `core/benchmark/models.py` — all dataclasses defined
- `core/benchmark/cli.py` — Click/Typer skeleton, no logic yet
- `.buildrunner/benchmarks/PLAN.md` — this document
- `.buildrunner/benchmarks/config.yaml` — schema + example populated

**Files to MODIFY:**

- `pyproject.toml` — register `br benchmark` as a CLI entry point under `[project.scripts]`

**Architecture decision:** Use `dataclasses` + `json` for all persistence (not SQLite). Rationale: runs are write-once, read occasionally. The append-only JSONL pattern already used in BR3 for `decisions.log`, `runtime-shadow.log`, etc. is the right fit. No schema migrations to manage. SQLite adds complexity with zero benefit for this workload.

**Done when:** `python -m core.benchmark.cli --help` prints usage without error.

---

### Milestone 1 — Phase Selector (effort: ~2h)

**Goal:** `br benchmark select --count 7` prints a scored, ranked candidate list.

**Files to CREATE:**

- `core/benchmark/selector.py`
- `tests/benchmark/test_selector.py`

**Key logic in `selector.py`:**

- Parses every `.buildrunner/builds/BUILD_*.md` with a `phase_spec_parser()` function that extracts: phase number, phase name, `Files:` block (declared files), checklist items (`- [x]` lines), and the `lock:` commit SHA (obtained via `git log --grep="lock.*<phase_name>" --oneline -1`)
- Scores candidates with the formula above
- Reads `benchmark_registry.jsonl` to exclude previously benchmarked phases
- Returns a `list[PhaseSpec]` sorted by score descending

**Architecture decision:** Parse BUILD spec markdown with regex, not a markdown library. The spec format is consistent (established patterns: `### Phase N:`, `**Files:**`, `- [x]`). A markdown parser adds a dependency and the format is simple enough. This mirrors how `spec_parser.py` already works in `core/`.

**Done when:** `br benchmark select --count 7` returns 7 candidates with scores, and `tests/benchmark/test_selector.py` passes.

---

### Milestone 2 — Worktree Orchestration (effort: ~3h)

**Goal:** Runner can reset a worktree to any pre-phase commit and clean it up reliably.

**Files to CREATE:**

- `core/benchmark/runner.py` — worktree setup/teardown only (no dispatch yet)
- `tests/benchmark/test_runner_worktree.py`

**Worktree protocol (per run):**

```python
def setup_worktree(phase_spec: PhaseSpec, run_id: str) -> Path:
    """
    1. Determine worktree path: /tmp/br3-bench-<run_id>/
    2. Run: git worktree add <path> <pre_phase_commit>
    3. Verify: git -C <path> log -1 --oneline matches pre_phase_commit
    4. Copy .buildrunner/benchmarks/config.yaml into worktree (read-only)
    5. Return worktree_path
    """

def teardown_worktree(worktree_path: Path, run_id: str) -> None:
    """
    1. git diff HEAD > <results_dir>/<run_id>/diff.patch
    2. git worktree remove --force <worktree_path>
    3. Log cleanup to benchmark_registry.jsonl
    """
```

**Critical detail:** The `lock:` commit is the correct pre-phase anchor. The pattern in git history is `lock: claim Phase N - <name>` appearing immediately before the `complete:` commit. The runner must resolve this: `git log --all --oneline --grep="lock.*<phase_name>" | head -1`. This is tested explicitly.

**Confound control:** Worktrees are in `/tmp/br3-bench-*/` — outside the main repo. This prevents run artifacts from contaminating each other or polluting git status on Muddy.

**Done when:** `test_runner_worktree.py` verifies a worktree is created at the correct commit, the diff is captured, and the worktree is cleaned up. Test uses a real BR3 commit from git history.

---

### Milestone 3 — Model Dispatch + Capture (effort: ~4h)

**Goal:** Runner can execute both models on a phase task and capture all outputs.

**Files to MODIFY:**

- `core/benchmark/runner.py` — add `dispatch_model_run()`

**Dispatch protocol:**

For **Codex 5.4** runs:

```bash
~/.buildrunner/scripts/dispatch-to-node.sh \
    --runtime codex \
    otis \
    <worktree_path> \
    "<phase_prompt_with_codex_skill_preamble>" \
    "bench-<run_id>"
```

For **Claude Opus 4.7** runs (dispatched to Lomax to keep Muddy free):

```bash
~/.buildrunner/scripts/dispatch-to-node.sh \
    --runtime claude \
    lomax \
    <worktree_path> \
    "<phase_prompt_with_opus_skill_preamble>" \
    "bench-<run_id>"
```

**Symmetric prompting guarantee:** `core/benchmark/prompts.py` holds two functions: `build_codex_prompt(phase_spec, skill_text)` and `build_claude_prompt(phase_spec, skill_text)`. Before each dispatch, the runner loads the relevant skill from disk:

- Codex: `~/.claude/skills/codex` (the existing `/codex` skill)
- Claude: `~/.claude/skills/opus` (the existing `/opus` skill)

Both prompts are logged verbatim to `run_meta.json`. This is the audit trail for the symmetry check.

**Token capture:** `dispatch-to-node.sh` already captures stdout/stderr. Token counts are extracted from:

- Codex: the `turn.completed` event's `usage` field (already parsed in `extract_codex_message_and_usage()` in `cross_model_review.py`)
- Claude: parse `claude --output-format json` usage field from stdout

**Timing:** `time.perf_counter()` around the full dispatch call — wall-clock includes SSH overhead, which is fair since it's symmetric (both dispatched to remote nodes).

**Architecture decision on randomization:** The execution order is randomized once at `driver.py` startup using `random.shuffle()` with a logged seed. The full plan is written to `plan.jsonl` before execution begins. This means Byron can inspect the plan before running and re-run with `--seed <N>` to reproduce the exact order. Time-of-day confound is addressed by distributing all models/phases across the run window rather than doing all Codex first.

---

### Milestone 4 — Objective Metrics + Plan Adherence (effort: ~4h)

**Goal:** `scorer.py` produces fully populated `ObjectiveMetrics` and `AdherenceMetrics` for every run.

**Files to CREATE:**

- `core/benchmark/scorer.py`
- `tests/benchmark/test_scorer.py`

**Objective quality checks (run inside the worktree after dispatch):**

| Check                 | Command                                                           | Parsed field                               |
| --------------------- | ----------------------------------------------------------------- | ------------------------------------------ |
| TypeScript types      | `npx tsc --noEmit 2>&1 \| wc -l`                                  | `tsc_errors`                               |
| ESLint                | `npx eslint --format json <changed_files>`                        | `eslint_errors`                            |
| Python lint           | `.venv/bin/ruff check <changed_files> --output-format json`       | `ruff_errors`                              |
| Code duplication      | `npx jscpd --min-tokens 30 --reporters json <worktree_path>`      | `jscpd_duplication_pct`                    |
| Cyclomatic complexity | `lizard <changed_files> --CCN 1 --csv`                            | `cyclomatic_delta` (vs pre-phase baseline) |
| Walter verdict        | `curl -s http://10.0.1.102:8100/api/results?project=BuildRunner3` | `walter_verdict`                           |
| Lomax build           | `curl -s http://10.0.1.104:8100/api/projects/BuildRunner3/build`  | `lomax_verdict`                            |

**Plan adherence computation:**

```python
def compute_adherence(phase_spec: PhaseSpec, diff_patch: str) -> AdherenceMetrics:
    touched = extract_touched_files(diff_patch)  # parse unified diff headers
    declared = set(phase_spec.declared_files)
    in_scope = touched & declared

    # Checklist matching: for each checklist item, check if at least one
    # touched file's diff contains a keyword derived from the item description
    matched = sum(1 for item in phase_spec.checklist_items
                  if any(keyword_from_item(item) in diff_patch for ...))

    # Scope creep: count LOC in diff outside declared files
    scope_creep_loc = sum(count_diff_loc(path, diff_patch)
                          for path in touched - declared)
    ...
```

**Important:** checklist matching is keyword-based, not semantic. This is intentional — it avoids having the scoring step itself require a model call, which would add cost and model-in-the-loop confounds to the objective metrics. Semantic matching is the judge's job.

**Walter/Lomax integration note:** Walter runs vitest+Playwright continuously. After dispatch completes, scorer waits up to 120 seconds for Walter's `last_run` timestamp to advance past the dispatch completion time. If it does not advance (Walter flake), the run is marked `walter_verdict: TIMEOUT` and excluded from the test-pass-rate dimension — but NOT from other dimensions. This prevents Walter flakes from invalidating otherwise-complete runs.

---

### Milestone 5 — Blind Judge Protocol (effort: ~3h)

**Goal:** `judge.py` dispatches blinded pairwise comparison to Otis and returns `JudgeVerdict`.

**Files to CREATE:**

- `core/benchmark/judge.py`
- `core/benchmark/prompts.py` — judge prompt template

**Blinding protocol:**

1. At run time, `driver.py` assigns label "A" or "B" to each (phase, model, run) combination using a deterministic but non-obvious mapping: `label = "A" if sha256(run_id + phase_id + "blind_salt") % 2 == 0 else "B"`. The salt is a random string generated once per benchmark session and stored in `config.yaml`. Neither label maps reliably to a specific model.
2. Judge inputs are written to `judge_input_A.md` and `judge_input_B.md`. These files contain only: the diff, the objective metric summary, and the original spec checklist. They contain no model names, no `codex exec` references, no Claude API references, no commit messages (commit messages include model name by BR3 convention — stripped before judge sees them).
3. The judge prompt is dispatched via `dispatch-to-node.sh --runtime claude otis`.
4. After judge returns, `aggregator.py` resolves labels to model names using the same deterministic mapping.

**Judge prompt (verbatim — this is load-bearing):**

```
You are a neutral code quality judge. You are comparing two implementations of the same task.
You do NOT know which AI model produced which implementation. Your job is to evaluate them
on merit alone.

## Task Specification
<phase_spec_checklist>

## Implementation A
<diff_A>

Objective metrics for A:
- Test pass rate: {walter_pass_rate_A}%
- TSC errors: {tsc_A}
- ESLint errors: {eslint_A}
- Ruff errors: {ruff_A}
- Checklist items matched: {checklist_A}/{checklist_total}

## Implementation B
<diff_B>

Objective metrics for B:
- Test pass rate: {walter_pass_rate_B}%
- TSC errors: {tsc_B}
- ESLint errors: {eslint_B}
- Ruff errors: {ruff_B}
- Checklist items matched: {checklist_B}/{checklist_total}

## Your scoring task

Score each implementation on a 1–5 scale for each dimension. Then pick an overall winner.
If scores are within 0.5 points on all dimensions AND objective metrics are within 5%, call it a TIE.

Dimensions:
1. CORRECTNESS — Does the diff deliver the specified checklist items? Are there logic errors?
2. READABILITY — Is the code clear? Good naming? Appropriate comments?
3. IDIOMATIC STYLE — Does it follow the patterns already in this codebase?
4. OVER-ENGINEERING — Does it add unnecessary abstraction, complexity, or scope?
   (Higher score = LESS over-engineering = better)
5. COMPLETENESS — Are all spec deliverables present?

Output ONLY valid JSON matching this schema:
{
  "scores_A": {"correctness": N, "readability": N, "idiomatic": N, "over_engineering": N, "completeness": N},
  "scores_B": {"correctness": N, "readability": N, "idiomatic": N, "over_engineering": N, "completeness": N},
  "overall_winner": "A" | "B" | "TIE",
  "rationale": "<2-3 sentences explaining the decision>",
  "key_differentiator": "<one sentence on the single most important difference>"
}
```

**Why Otis for judging:** Otis is the parallel-builder node. It is already wired for `dispatch-to-node.sh` dispatch. Running the judge on Otis means the judge model (Claude Opus 4.7) is physically separate from Muddy, reducing the risk of any context leakage from the benchmark session running on Muddy. Otis sees only the blinded judge input files, never the raw run logs.

**Extension point:** `cross_model_review.py` already has `run_review_spike_async()` which runs two runtimes in parallel. `judge.py` extends this by adding a new `run_judge_task()` function that reuses the `review_via_codex()` / `review_via_openrouter()` pattern but with the judge prompt. This is an additive change — `cross_model_review.py` is not modified, `judge.py` imports the probe/auth utilities from it.

---

### Milestone 6 — Statistical Aggregator + Report (effort: ~3h)

**Goal:** `br benchmark report` generates a complete markdown analysis.

**Files to CREATE:**

- `core/benchmark/aggregator.py`
- `tests/benchmark/test_aggregator.py`

**Statistical plan:**

N = 3 runs per (phase, model) is the minimum viable sample for variance estimation but too small for parametric tests. The correct choice is a **non-parametric paired comparison**:

- **Primary test:** Wilcoxon signed-rank test on the paired per-phase scores (each phase contributes one pair: Codex score vs Claude score, averaged across the 3 runs). With 7 phases that gives 7 pairs — marginal for the signed-rank test (minimum recommended N=6, and power will be low), but sufficient for a pre-registered directional claim.
- **Effect size:** Report **Hodges-Lehmann estimator** (the pseudo-median of pairwise differences) rather than just p-value. If the p-value cannot reach significance at N=7, the effect size still characterizes the practical gap.
- **Bootstrap CI:** For each metric, compute a 95% bootstrap CI (N=10,000 resamples) over the 7 phase pairs. This is the primary confidence interval reported to Byron — it does not require distributional assumptions and is meaningful at N=7.
- **Per-dimension breakdown:** Report the full matrix: (phase × model × metric). Do not collapse to a single score until the report narrative.
- **Significance threshold:** α=0.05 two-tailed. If p ≥ 0.05, report "no statistically significant difference" with the effect size and CI — do not inflate claims.

**`aggregator.py` structure:**

```python
def run_wilcoxon(pairs: list[tuple[float, float]]) -> dict:
    # scipy.stats.wilcoxon if available, else manual rank computation
    ...

def bootstrap_ci(values: list[float], n_resamples=10_000) -> tuple[float, float]:
    ...

def hodges_lehmann(diffs: list[float]) -> float:
    # median of all pairwise averages
    ...

def generate_report(run_id: str, results_dir: Path) -> str:
    # Produces the markdown string
    ...
```

**Report template (fixed structure):**

```markdown
# Benchmark Report: Codex 5.4 vs Claude Opus 4.7

Run ID: {run_id}
Date: {date}
Phases: {N} Runs per phase per model: {R} Total executions: {N*R*2}
Random seed: {seed}

## Executive Summary

Winner on objective quality: {model} (p={p}, HL={hl}, 95% CI [{lo}, {hi}])
Winner on plan adherence: {model} (p={p}, HL={hl}, 95% CI [{lo}, {hi}])
Winner on subjective quality (judge): {model} ({win_count}/{N} phases)
Cost delta: Codex ${codex_total} vs Claude ${claude_total} (wall: {codex_wall}m vs {claude_wall}m)

## Per-Phase Results

| Phase | Codex Obj | Claude Obj | Codex Adh | Claude Adh | Judge Winner | Key Differentiator |
...

## Statistical Details

### Wilcoxon Signed-Rank: Objective Quality

...

## Confound Log

- Walter flakes excluded: {N}
- Runs excluded (non-zero exit): {N}
- Runs with judge TIE: {N}

## Raw Data

See {results_dir}/data.jsonl
```

---

### Milestone 7 — CLI Wiring + End-to-End Test (effort: ~2h)

**Goal:** `br benchmark run --phases 7 --runs 3` executes the full pipeline.

**Files to MODIFY:**

- `core/benchmark/cli.py` — wire all commands to real implementations
- `core/benchmark/driver.py` — top-level orchestration loop

**CLI commands:**

```bash
# Full benchmark run
br benchmark run \
    --phases 7 \
    --runs 3 \
    --seed 42 \
    --node-codex otis \
    --node-claude lomax \
    --dry-run          # print plan without executing

# Score completed runs (if dispatch already done externally)
br benchmark score --run-id <id>

# Judge a completed run
br benchmark judge --run-id <id> --judge-node otis

# Aggregate and report
br benchmark report --run-id <id>

# Select candidate phases (inspection helper)
br benchmark select --count 10

# Resume an interrupted run
br benchmark resume --run-id <id>
```

**Resume logic:** `driver.py` reads `benchmark_registry.jsonl` to find which `(phase, model, run_n)` tuples already have `status: complete` for the given `run_id`, and skips them. This makes the harness idempotent against interruptions.

---

## Confound Controls — Complete Protocol

| Confound                           | Control mechanism                                                                                                                                                                                                                                                                          |
| ---------------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ |
| Temperature non-determinism        | Both models run at temperature=0 (or lowest supported). Codex: no temperature flag needed for `codex exec`. Claude: `--temperature 0` passed via dispatch prompt. Logged in `run_meta.json`.                                                                                               |
| Time-of-day / cluster load         | Fisher-Yates shuffle distributes all (phase, model, run) combos randomly. Codex and Claude runs for the same phase are NOT adjacent in the schedule.                                                                                                                                       |
| Prompt asymmetry                   | Both models receive their own best-practices skill preamble. The skill text is logged verbatim in `run_meta.json`. Diff between the two preambles is included in the report appendix.                                                                                                      |
| Tool permission differences        | Both models run with identical `--sandbox workspace-write` permissions. No tool is granted to one model but not the other. Enforced in `runner.py` via a `BENCHMARK_CODEX_FLAGS` and `BENCHMARK_CLAUDE_FLAGS` constant pair with an assertion that they are equivalent in capability tier. |
| Model attribution leakage in diffs | Commit messages in worktrees are stripped before judge sees them. Specifically: `git log` is never included in judge input. Diff headers (`diff --git a/... b/...`) are kept (they identify files, not models).                                                                            |
| Checklist pre-knowledge            | The phase is reset to the `lock:` commit, which exists in history before any implementation commits. The checklist items are read from the BUILD spec, which was present at the `lock:` commit. Models have access to the spec at execution time (fair — that is the actual work context). |
| Walter flake pollution             | Walter flakes are detected and excluded from test-pass-rate only. Other metrics are unaffected. Flake detection: a run is classified as `FLAKE` if Walter returns the same result (same test names, same pass/fail) as the pre-phase baseline, suggesting it did not re-run.               |
| Scope creep measurement bias       | LOC is counted in the diff, not in the final file. This means model-added boilerplate that exactly offsets deleted code cancels out. Net LOC outside declared files is the scope creep signal.                                                                                             |
| Judge recency bias                 | Judge receives Implementation A and Implementation B in random order. The A/B label randomization is independent of the temporal order of runs.                                                                                                                                            |

---

## Execution Flow — How Byron Runs This

**Step 0: Preflight (once)**

```bash
# Verify both runtimes are authenticated
python3 core/cluster/cross_model_review.py --runtime-preflight codex --json-output
python3 core/cluster/cross_model_review.py --runtime-preflight claude --json-output

# Verify cluster nodes are online
~/.buildrunner/scripts/cluster-check.sh --health-json otis
~/.buildrunner/scripts/cluster-check.sh --health-json lomax
~/.buildrunner/scripts/cluster-check.sh --health-json walter
```

**Step 1: Inspect phase candidates**

```bash
br benchmark select --count 10
# Review output, optionally edit .buildrunner/benchmarks/config.yaml
# to pin specific phases or exclude candidates
```

**Step 2: Dry run to inspect execution plan**

```bash
br benchmark run --phases 7 --runs 3 --seed 42 --dry-run
# Prints the full randomized execution schedule
# Prints estimated wall-clock time (phases × runs × 2 models × avg_minutes)
# Prints estimated API cost
```

**Step 3: Execute**

```bash
br benchmark run --phases 7 --runs 3 --seed 42
# Progress bar per run
# Logs to benchmark_registry.jsonl in real-time
# Resumable: Ctrl-C and re-run same command to resume
```

**Step 4: Score + judge (can run in parallel with step 3 as runs complete)**

```bash
br benchmark score --run-id <id>   # compute objective + adherence metrics
br benchmark judge --run-id <id>   # dispatch blind judge to Otis
```

**Step 5: Report**

```bash
br benchmark report --run-id <id>
# Writes .buildrunner/benchmarks/reports/<id>_report.md
# Writes .buildrunner/benchmarks/reports/<id>_data.jsonl
```

Total time from `br benchmark run` to final report: approximately 4–6 hours (3–4 hours execution, 1–2 hours scoring + judgment).

---

## Risks and Mitigations

| Risk                                                                                            | Likelihood | Impact | Mitigation                                                                                                                                                                                                                                                                                                                                     |
| ----------------------------------------------------------------------------------------------- | ---------- | ------ | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- |
| Walter flakes pollute test-pass-rate                                                            | Medium     | Medium | Flake detection via baseline comparison. Flaked runs excluded from that dimension only. Report flake count explicitly.                                                                                                                                                                                                                         |
| Codex times out on large phases (Phase 4 of codex-integration, 6 files)                         | Medium     | Medium | 120s timeout in runner. Timed-out runs are marked `exit_code: TIMEOUT` and excluded from all metrics (not just test pass). If >1 run per phase times out, phase is dropped from the analysis with a note.                                                                                                                                      |
| One model's skill preamble is substantially longer/richer                                       | Low        | Medium | Skill texts are logged and their lengths compared in the report. If one preamble is >2× longer, flag as a confound. Byron can equalize by providing a trimmed version.                                                                                                                                                                         |
| Judge model (Claude Opus 4.7 on Otis) has seen the BR3 codebase and may prefer its own patterns | Medium     | Medium | The judge prompt instructs it to score against the spec checklist, not against idiosyncratic preferences. The `idiomatic_style` dimension is scored against the codebase's demonstrated patterns, not the judge's own style. This is partially mitigated — a fully independent judge would require a third-party model, which is out of scope. |
| Cluster node contention (Otis serving both Codex runs and judge requests simultaneously)        | Medium     | Low    | `driver.py` serializes: all execution runs complete before judge requests begin. Judge requests are single-file, fast (<30s each).                                                                                                                                                                                                             |
| Non-determinism in model outputs inflates variance                                              | High       | Low    | N=3 runs is specifically designed to measure this variance. High variance in a model is itself a signal. Report per-model variance explicitly alongside the comparison.                                                                                                                                                                        |
| git worktree isolation failure (path collision, stale lock)                                     | Low        | High   | `setup_worktree()` uses unique `run_id` UUIDs. `teardown_worktree()` uses `--force`. If a worktree fails to clean up, `runner.py` logs to `benchmark_registry.jsonl` and skips the run rather than corrupting the next one.                                                                                                                    |
| commit messages in diffs leak model identity to judge                                           | Medium     | High   | Judge inputs are built by `judge.py` which strips commit log output. Only `git diff --stat` and `git diff` content (not `git log`) are included. Tested explicitly in `tests/benchmark/test_judge_blinding.py`.                                                                                                                                |
| Phase selection bias (cherry-picking easy phases for one model)                                 | Low        | High   | Selection is done once, upfront, logged in `config.yaml`, and not changed after runs begin. The selector scoring formula is deterministic and logged. Byron reviews the selection before running.                                                                                                                                              |

---

## Files Created vs Modified

### Created (new files)

```
core/benchmark/__init__.py
core/benchmark/models.py
core/benchmark/cli.py
core/benchmark/driver.py
core/benchmark/runner.py
core/benchmark/scorer.py
core/benchmark/judge.py
core/benchmark/aggregator.py
core/benchmark/prompts.py
core/benchmark/selector.py
tests/benchmark/__init__.py
tests/benchmark/test_selector.py
tests/benchmark/test_runner_worktree.py
tests/benchmark/test_scorer.py
tests/benchmark/test_aggregator.py
tests/benchmark/test_judge_blinding.py
.buildrunner/benchmarks/PLAN.md   (this document)
.buildrunner/benchmarks/config.yaml
.buildrunner/benchmarks/benchmark_registry.jsonl  (empty, created on first run)
```

### Modified (existing files)

```
pyproject.toml                         — add `br = "core.benchmark.cli:app"` entry point
core/cluster/cross_model_review.py     — no modification; judge.py imports auth utilities from it
```

That is the full scope. No existing command, skill, hook, or dispatch script is modified.

---

## Effort Estimates

| Milestone               | Description                           | Estimated effort            |
| ----------------------- | ------------------------------------- | --------------------------- |
| 0                       | Foundation + models.py + CLI skeleton | 3h                          |
| 1                       | Phase selector + spec parser          | 2h                          |
| 2                       | Worktree orchestration                | 3h                          |
| 3                       | Model dispatch + capture              | 4h                          |
| 4                       | Objective metrics + adherence         | 4h                          |
| 5                       | Blind judge protocol                  | 3h                          |
| 6                       | Statistical aggregator + report       | 3h                          |
| 7                       | CLI wiring + end-to-end smoke test    | 2h                          |
| **Total build**         |                                       | **~24h (3 developer-days)** |
| **Benchmark execution** | (runtime, not build)                  | ~4–6h per full run          |

---

## Pre-Run Checklist

Before executing the first real benchmark run:

- [ ] Both models authenticated: `codex --version` returns supported range, `claude --version` works
- [ ] Otis online: `cluster-check.sh --health-json otis` returns `online: true`
- [ ] Lomax online: same check
- [ ] Walter online and last_run timestamp advancing on commits
- [ ] `br benchmark select --count 10` returns ≥7 scoreable candidates
- [ ] `br benchmark run --dry-run --phases 7 --runs 3` completes without error
- [ ] `config.yaml` reviewed and `blind_salt` generated (first run generates it automatically)
- [ ] `.buildrunner/benchmarks/benchmark_registry.jsonl` initialized (empty file)
