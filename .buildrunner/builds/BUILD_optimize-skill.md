# Build: optimize-skill

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: architecture, assigned_node: muddy }
      phase_2: { bucket: backend-build, assigned_node: muddy }
      phase_3: { bucket: backend-build, assigned_node: muddy }
      phase_4: { bucket: architecture, assigned_node: muddy }
      phase_5: { bucket: backend-build, assigned_node: muddy }
      phase_6: { bucket: qa, assigned_node: walter }
```

**Created:** 2026-04-23
**Status:** 🚧 in_progress
**Deploy:** local-skill — no deploy target (Claude Code skill, lives under `~/.claude/commands/`)
**Source Plan File:** .buildrunner/plans/plan-optimize-skill.md
**Source Plan SHA:** 9450c8eeb649cf9b69d4d1bfa202c5c2d5616f6ca43a9d23f237c0b1fb976ad1
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-23T15:28:18Z

## Overview

Build `/optimize-skill`, a universal Claude Code command that automates prompt optimization for other skills using the production-proven methodology validated in Jimmy's research library (`docs/techniques/llm-skill-prompt-optimization-loops.md`, commit SHA `697c21352b`). Implements: 4-axis rubric (binary criteria + cost + diversity + length), train/holdout split (14/6 from 20 varied inputs), cross-family judge panel (Sonnet + Codex + Gemini) with swap-order averaging + CoT-judge + majority vote, Opus 4.7 rewriter that prefers shorter equivalent prompts (GEPA insight), strict decision gate (score ≥5% AND diversity ≥-20% AND cost ≤+30% AND length ≤+50%), max-3 iterations OR plateau stop, mandatory human spot-check. Internal prompts follow per-LLM research-library conventions: XML tags for Claude, verification-first for Codex, step-by-step markdown for Gemini. First validation target: `/website-build`.

## Parallelization Matrix

| Phase | Key Files                                                                                                       | Can Parallel With | Blocked By    |
| ----- | --------------------------------------------------------------------------------------------------------------- | ----------------- | ------------- |
| 1     | `~/.claude/commands/optimize-skill.md` (NEW), `.buildrunner/skill-evals/_README.md` (NEW), `_schema.yaml` (NEW) | —                 | —             |
| 2     | `~/.claude/commands/optimize-skill.md` (EXTEND)                                                                 | 4                 | 1             |
| 3     | `~/.claude/commands/optimize-skill.md` (EXTEND)                                                                 | 4                 | 2             |
| 4     | `.buildrunner/skill-evals/website-build.yaml` (NEW)                                                             | 2, 3              | 1             |
| 5     | `~/.claude/commands/optimize-skill.md` (EXTEND)                                                                 | —                 | 2, 3          |
| 6     | `.buildrunner/skill-evals/runs/` (NEW), `decisions.log` (MODIFY)                                                | —                 | 1, 2, 3, 4, 5 |

## Phases

### Phase 1: Foundation — skill file + rubric schema + scaffolding

**Status:** 🚧 in_progress
**Bucket:** architecture
**Node:** muddy
**Files:**

- `~/.claude/commands/optimize-skill.md` (NEW)
- `.buildrunner/skill-evals/_README.md` (NEW)
- `.buildrunner/skill-evals/_schema.yaml` (NEW)
- `.buildrunner/skill-evals/runs/.gitkeep` (NEW)
- `tests/cluster/test_optimize_skill_schema.py` (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Skill `.md` frontmatter: `effort: xhigh`, `thinking: {type: adaptive, display: summarized}`, `allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent`
- [ ] Skill parses `<skill-name>` arg and `--dry-run` / `--n <int>` / `--max-iter <int>` / `--resume <timestamp>` flags
- [ ] Loads `.buildrunner/skill-evals/<skill-name>.yaml`, validates against `_schema.yaml`
- [ ] Schema keys: binary criteria (3–5), inputs (20), train/holdout split (14/6), pass_threshold, plateau_threshold (5%), max_iterations (3), budget_usd (2.00)
- [ ] Dry-run mode prints: loaded inputs, rubric, judge panel, budget estimate — no execution
- [ ] Boot-time Jimmy accessibility check (POST to `http://10.0.1.106:8100/retrieve`) with actionable failure message
- [ ] Per-LLM prompt conventions documented inside the skill (XML for Claude, verification-first for Codex, step-by-step for Gemini)
- [ ] Test file: schema parse tests (valid rubric passes, missing keys reject, invalid thresholds reject)

**Success Criteria:** `/optimize-skill foo --dry-run` with missing rubric exits cleanly; with valid rubric prints full plan in <5s; all schema tests pass.

### Phase 2: Runner dispatch + cross-family judge panel

**Status:** 🚧 in_progress
**Bucket:** backend-build
**Node:** muddy
**Files:**

- `~/.claude/commands/optimize-skill.md` (EXTEND — built on Phase 1)
- `tests/cluster/test_optimize_skill_judge.py` (NEW)
- `tests/cluster/test_optimize_skill_diversity.py` (NEW)

**Blocked by:** Phase 1 (same file)

**Deliverables:**

- [ ] Train-set dispatch: 10 parallel Agent subagents run target skill with XML-tagged prompts
- [ ] Sonnet judge: `<criteria>`-tagged prompt + json_schema structured output + `medium` effort
- [ ] Codex judge: verification-first prompt + fenced-JSON output contract + stdin input
- [ ] Gemini judge: step-by-step markdown + UNKNOWN-on-uncertain anti-hallucination rule
- [ ] Swap-order averaging: each pair scored twice (v1-first, v2-first), per-judge scores averaged
- [ ] Majority vote per criterion (2-of-3)
- [ ] Three-way disagreement → human-flag (no auto-resolve)
- [ ] Diversity metric: token-shingle overlap + Shannon entropy on embeddings
- [ ] Per-run cost + length tracking
- [ ] Test files: swap-order symmetry, majority-vote logic, diversity-metric stability (identical→0, distinct→~1)

**Success Criteria:** N=10 runs complete; per-criterion per-judge scores stored in `runs/<ts>/baseline.json`; all judge/diversity tests pass.

### Phase 3: Rewriter + decision gate + iteration control

**Status:** 🚧 in_progress
**Bucket:** backend-build
**Node:** muddy
**Files:**

- `~/.claude/commands/optimize-skill.md` (EXTEND — built on Phase 1)
- `tests/cluster/test_optimize_skill_gate.py` (NEW)

**Blocked by:** Phase 2 (same file)

**Deliverables:**

- [ ] Rewriter prompt uses XML tags (`<role>`, `<baseline>`, `<failures>`, `<constraints>`, `<output_format>`), Opus 4.7 xhigh
- [ ] Rewriter constraint explicitly: "prefer shorter equivalent rewrites" (GEPA 9.2× insight)
- [ ] A/B run: v1 + v2 on holdout (6 inputs × 5 runs = 30 outputs), judged
- [ ] Decision gate (ALL four must hold): score_gain ≥5%, diversity_delta ≥-20%, cost_delta ≤+30%, length_delta ≤+50%
- [ ] Plateau detection: two consecutive <5% gains → stop
- [ ] Hard cap: 3 iterations (`--max-iter` configurable)
- [ ] Human spot-check: 3 random holdout outputs, block on user confirm (`--no-spot-check` override, not default)
- [ ] Test file: 16-case truth table on decision gate, plateau trigger, hard-cap trigger

**Success Criteria:** baseline → rewrite → A/B → decision → (optional iter2) → final winner with rationale logged; gate tests pass.

### Phase 4: Starter rubric for /website-build + budget guard

**Status:** 🚧 in_progress
**Bucket:** architecture
**Node:** muddy
**Files:**

- `.buildrunner/skill-evals/website-build.yaml` (NEW)
- `~/.claude/commands/optimize-skill.md` (EXTEND — built on Phase 1)

**Blocked by:** Phase 1 (schema must exist). Can parallelize with Phase 2 and 3.

**Deliverables:**

- [ ] 5 binary criteria: no banned libs (chakra/mui/antd/etc), dark theme default, Tailwind `@layer components`, section padding tokens, `/audit-site` pass
- [ ] Cost axis (total tokens), diversity axis (embedding variance via Jimmy), length axis (mean char count)
- [ ] 20 inputs referenced by path from `.buildrunner/context/`, `.buildrunner/artifacts/`, or project `post-synapse.json` files
- [ ] Budget guard: $2.00 default cap, `BR3_OPTIMIZE_SKILL_BUDGET` override, reuse `~/.buildrunner/scripts/research-budget-guard.sh` pattern
- [ ] Stop-on-cap: let in-flight finish, no new dispatch, flag `BUDGET_CAP_HIT`
- [ ] Rubric validates against `_schema.yaml`

**Success Criteria:** `/optimize-skill website-build --dry-run` prints budget estimate <$15 for N=10; rubric validates clean.

### Phase 5: Run logging + /2nd tiebreaker + summary

**Status:** 🚧 in_progress
**Bucket:** backend-build
**Node:** muddy
**Files:**

- `~/.claude/commands/optimize-skill.md` (EXTEND — built on Phase 1)
- `tests/cluster/test_optimize_skill_runlog.py` (NEW)

**Blocked by:** Phase 2 and 3 (same file)

**Deliverables:**

- [ ] Run logs at `.buildrunner/skill-evals/runs/<skill>-<ISO-timestamp>/`:
  - `baseline.json` — inputs, outputs, per-criterion scores, diversity/cost/length, total cost
  - `iter-N.json` — same shape plus `v2_prompt` and `decision_gate_outcome`
  - `winner.md` — final prompt + unified diff from baseline
  - `failures.md` — failed criteria + offending outputs
  - `rubric-retro.md` (optional) — rubric-revision notes if winner rejected
- [ ] `/2nd` tiebreaker: when A/B tie (score gain within ±1%), dispatch to `/2nd` for Opus arbitration
- [ ] Summary output: score table, diversity/cost/length deltas, iterations, winner kept/rejected, next-step guidance
- [ ] `--resume <timestamp>` flag reloads cached baseline, skips baseline dispatch
- [ ] Test file: directory creation, JSON structure invariants, winner.md diff, `--resume` skips baseline

**Success Criteria:** Complete audit trail after any run; summary prints <20 lines; run-log tests pass.

### Phase 6: E2E validation on /website-build

**Status:** 🚧 in_progress
**Bucket:** qa
**Node:** walter
**Files:**

- `.buildrunner/skill-evals/runs/website-build-<timestamp>/*` (NEW — generated)
- `.buildrunner/decisions.log` (MODIFY)

**Blocked by:** Phases 1, 2, 3, 4, 5 (runtime)

**Deliverables:**

- [ ] Run `/optimize-skill website-build --dry-run` — verify plan, budget ≤$15, all per-LLM prompts render correctly against research-library conventions
- [ ] Run `/optimize-skill website-build` with N=10 for real
- [ ] Verify post-run: 3-family judging in log, swap-order applied, decision gate fired correctly, human spot-check blocked, run directory complete
- [ ] Log results to `.buildrunner/decisions.log`: baseline score, iter-1 score, gain %, duration, cost, winner kept/rejected, diversity/cost/length deltas
- [ ] If winner rejected or flat: write `rubric-retro.md` — failure here is rubric-side, not method-side

**Success Criteria:** EITHER (a) holdout score improved ≥10% with diversity stable, cost ≤$15, human-confirmed quality, OR (b) `rubric-retro.md` documents why the rubric needs sharpening. Both are valid outcomes.

## Session Log

_(Will be updated by /begin)_
