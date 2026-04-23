# Plan: /optimize-skill

**Purpose:** Automate prompt optimization for Claude Code skills using the production-proven methodology validated in `research-library/docs/techniques/llm-skill-prompt-optimization-loops.md`. First target: `/website-build`.

**Source research doc SHA (Jimmy):** `697c21352bec5e75e495f4b83f3416449ff7cb4d` (committed 2026-04-23, indexed in Jimmy LanceDB).

**Note on cited documents:** `research-library/docs/techniques/llm-skill-prompt-optimization-loops.md`, `claude-opus-prompting-consistency.md`, `perplexity-prompt-engineering.md`, and `openai-codex-optimization.md` live on Jimmy at `/srv/jimmy/research-library/` (not in this repo). They are accessible via Jimmy's `/retrieve` endpoint (`http://10.0.1.106:8100/retrieve`) and via direct SSH cat for full-document reads. Phase 1 adds a boot-time accessibility check to fail fast if Jimmy is unreachable.

## Methodology Anchor Points (from research)

1. **DSPy patterns without the framework** — teacher/student split, train/val/holdout discipline, metric-driven optimizer — implemented in Bash + subagents inside the skill, not as a Python dependency.
2. **4-axis rubric**: 3–5 binary correctness criteria + cost axis + output diversity + output length. Multi-axis is the anti-Goodhart hedge.
3. **Train/holdout split**: 14/6 from 20 varied real inputs (larger than the 8-example baseline flagged as statistically thin by adversarial review).
4. **Cross-family judge panel**: Sonnet + Codex + Gemini. Majority vote per criterion. Three-way disagreement → human spot-check flag.
5. **Swap-order averaging**: each pairwise comparison run twice with order flipped. Addresses position bias (0.04–0.82 consistency range by model).
6. **CoT-judge**: judges reason before scoring. Documented 5–15% reliability gain.
7. **Rewriter optimizes for brevity**: GEPA's 9.2× shorter prompts with equivalent performance. Rewriter prefers shorter equivalent rewrites.
8. **Decision gate (keep v2 only if ALL hold)**: score gain ≥5%, diversity didn't drop >20%, cost didn't grow >30%, length didn't grow >50%.
9. **Stop conditions**: 3 iterations max OR two consecutive <5% gains (plateau).
10. **Human spot-check**: 3 random holdout outputs per iteration, non-negotiable per Anthropic's published practice.
11. **Skip retrieval-heavy skills**: `/research`, `/learn`, `/cluster-research` are 4.6-pinned with subjective outputs — won't converge on binary rubrics.
12. **Highest leverage on cheap models**: Tessl 880-eval study — prioritize Sonnet/Haiku-backed skills over Opus-backed ones.

## Per-LLM Prompt Optimization (research-library best-practices baked into the skill)

All internal prompt templates emitted by the skill must follow the per-LLM conventions below. These are derived from `claude-opus-prompting-consistency.md`, `perplexity-prompt-engineering.md`, and `openai-codex-optimization.md` on Jimmy.

### Claude (Opus 4.7 rewriter, Sonnet judge, Haiku embeddings if ever used)

- **XML-tagged structure**: `<role>`, `<task>`, `<criteria>`, `<output_format>`, `<examples>` — every internal Claude call uses this.
- Adaptive thinking: `type: adaptive, display: summarized`. Never `budget_tokens` (hard error on 4.7).
- Effort: `xhigh` for rewriter, `medium` for judge scoring (classification-style task).
- Structured Outputs API for judge: `json_schema` (NOT `json_object`).
- `max_tokens`: 64K for rewriter, 2K for judge.
- Separate structure from content — XML template is fixed, content/examples vary.
- No XML close-tag omission — always close every tag.

### Codex (GPT-5.4 judge)

- **Verification-first prompting**: every task includes the verification mechanism ("how will you know your scoring is correct?").
- Explicit expected output shape: JSON in a fenced code block with field comments.
- Short system prompt; long structured user prompt with `## sections`.
- Effort via `-c model_reasoning_effort=medium` for scoring tasks.
- No `--prompt-file` flag (deprecated) — pass via stdin.

### Gemini (2.5 Pro judge)

- Structured markdown with explicit step-by-step ordering (`## Step 1 …`, `## Step 2 …`).
- Output contract stated twice — once in system prompt, once at end of user prompt.
- Anti-hallucination: "if you cannot score a criterion, respond 'UNKNOWN' — do not guess."
- `max_tokens`: 4K for judge, 8K if thinking mode.

### Perplexity (not in judge panel; present in rubric-validator sub-check if used)

- User prompt: 2–8 keyword-rich tokens, NOT prose. The search component uses user prompt only.
- System prompt holds all formatting rules (user prompt doesn't affect search).
- Structured output: `response_format: json_schema` (`json_object` is silently unreliable).
- Explicit failure instruction: "state 'not found' if evidence is missing."

## Phases

### Phase 1: Foundation — skill file + rubric schema + scaffolding

**Bucket:** architecture · **Node:** muddy

**Files:**

- `~/.claude/commands/optimize-skill.md` (NEW) — skill file with 4.7 frontmatter
- `.buildrunner/skill-evals/_README.md` (NEW) — rubric format documentation
- `.buildrunner/skill-evals/_schema.yaml` (NEW) — authoritative rubric schema
- `.buildrunner/skill-evals/runs/.gitkeep` (NEW)

**Blocked by:** None

**Deliverables:**

- [ ] Skill `.md` frontmatter: `effort: xhigh`, `thinking: {type: adaptive, display: summarized}`, `allowed-tools: Read, Write, Edit, Bash, Grep, Glob, Agent`
- [ ] Skill parses `<skill-name>` arg and `--dry-run` / `--n <int>` / `--max-iter <int>` flags
- [ ] Loads `.buildrunner/skill-evals/<skill-name>.yaml` and validates against `_schema.yaml`
- [ ] Schema documents: binary criteria (3–5), inputs (20), train/holdout split (14/6), pass_threshold, plateau_threshold (5%), max_iterations (3), budget_usd (2.00)
- [ ] Dry-run mode prints: loaded inputs, rubric, judge panel composition, budget estimate — no execution
- [ ] Documents per-LLM prompt optimization rules from this plan as a skill-internal reference
- [ ] **Boot-time Jimmy accessibility check** — skill POSTs to `http://10.0.1.106:8100/retrieve` at entry, fails fast with actionable message if unreachable (research docs live on Jimmy, not in repo)
- [ ] **Test file: `tests/cluster/test_optimize_skill_schema.py`** — unit tests for schema parsing: valid rubric parses, missing required keys reject, invalid threshold values reject, out-of-range N/max-iter reject

**Success Criteria:** `/optimize-skill foo --dry-run` with missing rubric exits with helpful message; with valid rubric prints full dry-run plan in <5s.

### Phase 2: Runner dispatch + cross-family judge panel

**Bucket:** backend-build · **Node:** muddy

**Files:**

- `~/.claude/commands/optimize-skill.md` (EXTEND — built on Phase 1)

**Blocked by:** Phase 1 (same file)

**Deliverables:**

- [ ] Train-set dispatch: 10 parallel `Agent` subagents run target skill with varied inputs (subagent prompt in XML tags)
- [ ] Judge panel dispatch via `~/.buildrunner/scripts/llm-dispatch.sh`:
  - Sonnet judge: XML-tagged `<criteria>`, structured outputs `json_schema`, `medium` effort
  - Codex judge: verification-first, fenced-JSON output contract, stdin input
  - Gemini judge: step-by-step markdown, UNKNOWN-on-uncertain
- [ ] Each judge scores N outputs against 3–5 binary criteria + reasoning
- [ ] **Swap-order averaging**: every pairwise comparison run twice with order flipped, per-judge scores averaged
- [ ] **Majority vote** per criterion: 2-of-3 across judges
- [ ] Three-way disagreement → flag for human spot-check (don't auto-resolve)
- [ ] Diversity measurement: token-shingle overlap across N outputs, Shannon entropy on embeddings if available
- [ ] Per-run length + cost tracking
- [ ] All judge prompts must validate against research-library conventions (fail fast if template violates XML/CoT/verification rules)
- [ ] **Test file: `tests/cluster/test_optimize_skill_judge.py`** — unit tests for: swap-order averaging (same pair scored twice with flipped order → average is symmetric), majority-vote logic (2-of-3 with 3-way split triggers human-flag), per-criterion scoring parse, CoT reasoning extraction
- [ ] **Test file: `tests/cluster/test_optimize_skill_diversity.py`** — diversity metric stability: identical outputs → 0.0, fully-distinct outputs → close to 1.0, known-distance pairs match expected cosine

**Success Criteria:** N=10 parallel runs complete; per-criterion per-judge scores stored in `.buildrunner/skill-evals/runs/<ts>/baseline.json`; swap-order averaging verified via unit inspection AND passing tests.

### Phase 3: Rewriter + decision gate + iteration control

**Bucket:** backend-build · **Node:** muddy

**Files:**

- `~/.claude/commands/optimize-skill.md` (EXTEND — built on Phase 1)

**Blocked by:** Phase 2 (same file)

**Deliverables:**

- [ ] Rewriter prompt uses XML tags: `<role>Prompt optimizer</role>`, `<baseline>`, `<failures>`, `<constraints>` (brevity preferred), `<output_format>`
- [ ] Rewriter input: baseline skill prompt + top-3 failure clusters + rubric criteria that failed
- [ ] Rewriter constraint: "prefer shorter equivalent rewrites" — GEPA 9.2× finding
- [ ] A/B run: v1 (baseline) and v2 (rewrite) both executed on holdout (6 inputs × 5 runs = 30 outputs), scored
- [ ] Decision gate implementation (ALL four must hold to keep v2): score_gain ≥5%, diversity_delta ≥-20%, cost_delta ≤+30%, length_delta ≤+50%
- [ ] Plateau detection: two consecutive <5% gains → stop
- [ ] Hard cap: 3 iterations (configurable via `--max-iter`)
- [ ] Human spot-check: present 3 random holdout outputs, block on user confirm (unless `--no-spot-check` flag, not recommended)
- [ ] **Test file: `tests/cluster/test_optimize_skill_gate.py`** — decision gate truth table: exhaustive 16 combinations of (gain, diversity, cost, length) above/below thresholds → assert keep-v2 only when all four pass; plateau detection trigger after 2 consecutive <5% gains; hard-cap trigger at iter 3

**Success Criteria:** Given a baseline prompt and a failing rubric, the skill executes baseline → rewrite → A/B → decision → (optional iter2) → final winner with full rationale logged. Gate tests pass.

### Phase 4: Starter rubric for /website-build + budget guard

**Bucket:** architecture · **Node:** muddy
**Can parallelize with:** Phases 2 and 3 (different file)

**Files:**

- `.buildrunner/skill-evals/website-build.yaml` (NEW)
- `~/.claude/commands/optimize-skill.md` (MODIFY — budget guard integration)

**Blocked by:** Phase 1 (schema must exist)

**Deliverables:**

- [ ] `website-build.yaml` with 5 binary criteria: no banned libs (chakra/mui/antd/etc), dark theme default, Tailwind v4 `@layer components` respected, section padding tokens present, passes `/audit-site`
- [ ] Cost axis: total token count across all N runs
- [ ] Diversity axis: semantic embedding variance via Jimmy `/retrieve` embeddings or local cosine similarity
- [ ] Length axis: mean output char count
- [ ] 20 real inputs referenced by path: past intake artifacts from `.buildrunner/context/`, `.buildrunner/artifacts/`, or existing project `post-synapse.json` files
- [ ] Budget guard: default cap $2.00, override via `BR3_OPTIMIZE_SKILL_BUDGET`, uses `~/.buildrunner/scripts/research-budget-guard.sh` pattern
- [ ] Stop-on-cap: let in-flight runs complete, no new dispatches, flag `BUDGET_CAP_HIT` in run log
- [ ] Rubric validates against `_schema.yaml`

**Success Criteria:** `/optimize-skill website-build --dry-run` prints budget estimate <$15 for N=10; rubric validates clean.

### Phase 5: Run logging + /2nd tiebreaker + summary

**Bucket:** backend-build · **Node:** muddy

**Files:**

- `~/.claude/commands/optimize-skill.md` (EXTEND — built on Phase 1)

**Blocked by:** Phases 2 and 3 (same file)

**Deliverables:**

- [ ] Run logs at `.buildrunner/skill-evals/runs/<skill>-<ISO-timestamp>/` per run:
  - `baseline.json` — inputs, outputs, per-criterion scores, diversity/cost/length, total cost
  - `iter-1.json`, `iter-2.json` — same shape, plus `v2_prompt` and `decision_gate_outcome`
  - `winner.md` — final prompt + unified diff from baseline
  - `failures.md` — failed criteria + offending outputs with annotations
  - `rubric-retro.md` (optional) — rubric-revision notes if winner rejected
- [ ] `/2nd` tiebreaker integration: when holdout A/B ties (score gain within ±1%), dispatch to `/2nd` for Opus 4.7 arbitration
- [ ] Final summary format (printed to stdout):
  - Score table: baseline vs winner per criterion
  - Diversity/cost/length deltas
  - Iterations run, stop reason
  - Winner kept/rejected
  - Next-step guidance ("sharpen criterion X" or "ready to commit")
- [ ] `--resume <timestamp>` flag to continue from an interrupted run using cached baseline scores
- [ ] **Test file: `tests/cluster/test_optimize_skill_runlog.py`** — run log directory creation, JSON structure invariants (baseline.json has N entries, scores sum correctly, diversity/cost/length present), winner.md unified diff renders, `--resume` reloads baseline without re-running

**Success Criteria:** After any run completes, `.buildrunner/skill-evals/runs/<name>/` contains complete audit trail; summary prints in <20 lines; run-log tests pass.

### Phase 6: E2E validation on /website-build

**Bucket:** qa · **Node:** walter (sentinel node for E2E)

**Files:**

- `.buildrunner/skill-evals/runs/website-build-<timestamp>/*` (NEW — generated by run)
- `.buildrunner/decisions.log` (MODIFY)

**Blocked by:** Phases 1, 2, 3, 4, 5 (runtime)

**Deliverables:**

- [ ] Run `/optimize-skill website-build --dry-run` — verify plan, budget ≤$15, all per-LLM prompts render correctly
- [ ] Run `/optimize-skill website-build` with N=10 for real
- [ ] Verify post-run: 3-family judging ran (check log), swap-order applied (check log), decision gate logic fired correctly, human spot-check blocked on user confirm, run directory complete
- [ ] Document results in `.buildrunner/decisions.log`: baseline score, iter-1 score, gain %, duration, cost, winner kept/rejected, diversity/cost/length deltas
- [ ] If winner rejected or score flat: write `rubric-retro.md` with specific criterion-sharpening recommendations — failure here is rubric-side, not method-side

**Success Criteria:** EITHER (a) holdout score improved ≥10% with diversity stable and cost ≤$15 AND human spot-check confirmed quality, OR (b) `rubric-retro.md` clearly documents why the rubric (not the skill) needs sharpening. Both are valid outcomes — both prove the method works.

## Out of Scope

- Auto-commit of winner prompts (always human-confirm)
- Optimizing `/research`, `/learn`, `/cluster-research` (4.6-pinned, subjective, won't converge)
- Multi-skill batch optimization in one run (v2 feature)
- Autonomous re-optimization on model upgrade
- DSPy framework adoption (explicitly rejected — patterns yes, framework no)
- Metadata step auto-fix (qwen3:8b → qwen2.5:14b for research pipeline; separate unrelated issue)

## Parallelization Matrix

| Phase | Key Files                                                     | Can Parallel With  | Blocked By              |
| ----- | ------------------------------------------------------------- | ------------------ | ----------------------- |
| 1     | `optimize-skill.md` NEW, `_README.md` NEW, `_schema.yaml` NEW | —                  | —                       |
| 2     | `optimize-skill.md` MODIFY                                    | 4 (different file) | 1                       |
| 3     | `optimize-skill.md` MODIFY                                    | 4 (different file) | 2                       |
| 4     | `website-build.yaml` NEW                                      | 2, 3               | 1 (schema)              |
| 5     | `optimize-skill.md` MODIFY                                    | —                  | 2, 3                    |
| 6     | `runs/` NEW, `decisions.log` MODIFY                           | —                  | 1, 2, 3, 4, 5 (runtime) |

## Risk Register

- **Judge disagreement rate may be high** — if 3-way disagreement fires on >30% of comparisons, rubric criteria aren't binary enough. Surface this in Phase 6 retro.
- **Budget cap fires mid-iteration** — in-flight runs complete but no decision-gate evaluation. Log state and exit cleanly; resumable via `--resume`.
- **Human spot-check fatigue** — 3 outputs × 3 iterations = 9 manual reviews per run. Mitigation: `--auto-after-iter-1` flag (not default).
- **Diversity metric overfitting** — if we optimize for diversity we may degrade correctness. Diversity is a brake, not a target — decision gate rejects only catastrophic collapse (>20%).
- **N=10 may be too small to detect real improvements** — research shows 50–100 rollouts for DSPy convergence on full pipelines. We're optimizing ONE skill prompt, not a pipeline; 10 is adequate for per-skill tuning but may need bumping for high-variance skills.
