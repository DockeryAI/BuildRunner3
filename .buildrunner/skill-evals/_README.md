# Skill Evaluation Rubrics

This directory holds rubrics consumed by `/optimize-skill`. Each rubric is a YAML file at `.buildrunner/skill-evals/<skill-name>.yaml` and is validated against `_schema.yaml` at skill entry.

## File layout

```
.buildrunner/skill-evals/
├── _README.md            ← this file
├── _schema.yaml          ← authoritative schema (every rubric is validated against it)
├── <skill-name>.yaml     ← one rubric per target skill
└── runs/                 ← run artifacts written here per invocation
    └── <skill>-<ISO-timestamp>/
        ├── baseline.json
        ├── iter-1.json
        ├── winner.md
        ├── failures.md
        ├── rubric-retro.md   ← optional, only if winner rejected
        └── budget.json
```

## Rubric structure

Every rubric YAML has these top-level keys (see `_schema.yaml` for authoritative types and constraints):

| Key                 | Type   | Notes                                                                                       |
| ------------------- | ------ | ------------------------------------------------------------------------------------------- |
| `skill`             | string | Target skill name (e.g. `website-build`). Must match the filename.                          |
| `description`       | string | One-sentence description of what this rubric evaluates.                                     |
| `criteria`          | list   | 3–5 binary (yes/no) criteria. Each has `name`, `question`, optional `weight` (default 1.0). |
| `inputs`            | list   | 20 input references (path-based or inline). Train/holdout split is 14/6.                    |
| `train_split`       | int    | Default 14. Must equal `len(inputs) - holdout_split`.                                       |
| `holdout_split`     | int    | Default 6.                                                                                  |
| `pass_threshold`    | float  | Default 0.80. Min fraction of criteria that must pass.                                      |
| `plateau_threshold` | float  | Default 0.05. Two consecutive gains below this → stop.                                      |
| `max_iterations`    | int    | Default 3. Hard cap.                                                                        |
| `budget_usd`        | float  | Default 2.00. Per-run hard cap. Override env: `BR3_OPTIMIZE_SKILL_BUDGET`.                  |
| `judges`            | list   | Default `[sonnet, codex, gemini]`. Ordering is irrelevant (swap-order averages anyway).     |
| `cost_axis`         | bool   | Default true.                                                                               |
| `diversity_axis`    | bool   | Default true.                                                                               |
| `length_axis`       | bool   | Default true.                                                                               |

## Binary criteria (key invariant)

Criteria MUST be yes/no decidable. "Is the output well-written?" is NOT binary. "Does the output reference at least one banned library (chakra-ui / mui / antd)?" IS binary.

If 3-way judge disagreement fires on >30% of comparisons during a run, the rubric is not binary enough. The skill writes `rubric-retro.md` flagging this. That is a valid run outcome — it surfaces a rubric defect.

## Inputs

20 inputs is the floor. Below 14/6 split, statistical noise dominates. Inputs may be:

- File paths relative to project root: `path: ".buildrunner/context/intake.json"`
- Inline strings (only for short fixtures): `text: "Build a landing page for a dental clinic."`

Use real intake artifacts where possible — synthetic inputs hide tokenization/length distributions that real inputs expose.

## Decision gate (enforced by `/optimize-skill`)

A rewrite is kept ONLY if ALL four hold:

| Axis      | Constraint                 |
| --------- | -------------------------- |
| score     | gain ≥ +5%                 |
| diversity | delta ≥ -20% (no collapse) |
| cost      | delta ≤ +30%               |
| length    | delta ≤ +50%               |

This is intentionally strict — diversity and cost are guard-rails against optimizing the wrong axis (Goodhart).

## Adding a rubric

1. Copy `website-build.yaml` as a template.
2. Set `skill:` to your target skill name.
3. Replace `criteria:` with 3–5 yes/no questions.
4. Reference 20 inputs (mix of `.buildrunner/context/`, `.buildrunner/artifacts/`, project `post-synapse.json`).
5. `python3 -c "import yaml; yaml.safe_load(open('your-skill.yaml'))"` to lint.
6. Run `/optimize-skill <your-skill> --dry-run` — verifies schema + prints budget.

## Skip list (refuse to optimize)

`/optimize-skill` refuses to run on `/research`, `/learn`, `/cluster-research`. They are 4.6-pinned, retrieval-heavy, and produce subjective outputs that will not converge on binary rubrics. See `.buildrunner/plans/plan-optimize-skill.md` "Out of Scope" for the full reasoning.
