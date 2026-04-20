# Adversarial Review — model-benchmark-harness

**Reviewer:** Codex (GPT-5.4) dispatched to Otis
**Plan:** `.buildrunner/plans/spec-draft-plan.md`
**Date:** 2026-04-16
**Findings:** 4 blockers, 8 warnings, 3 notes

## Blockers (must resolve before build)

1. **Missing `dispatch-to-node.sh` verification** — Phase 3 depends on it but it's absent from project tree/cited excerpts. (Action: confirm path + include explicit dependency in Phase 1.)
2. **`benchmark_registry.jsonl` writer not declared** — Phase 2 excludes phases already in it, but no phase creates/writes it. (Action: Phase 1 deliverable must create/initialize registry.)
3. **Walter/Lomax HTTP API contracts unspecified** — Phase 5 pulls verdicts from them without endpoint, schema, or auth. (Action: Phase 1 or 2 deliverable to document exact endpoints consumed.)
4. **Semantic-equivalence validator source undefined** — Phase 4 requires "cluster semantic-search" for paraphrase validation, but that service/module isn't cited or verified. (Action: specify concrete validator module or replace with NLI/judge call.)

## Warnings

5. OpenRouter integration has no existing client/config/auth in the project — external-API risk unaccounted.
6. Prettier/Black declared but never added as project dependencies.
7. tsc/eslint/ruff/jscpd/lizard called but availability/install never verified.
8. `br benchmark validate` introduced in Phase 8 but Phase 1 CLI skeleton doesn't list it — contract drift across phases.
9. Phase 9 success says "no unresolved harness bugs" while deliverables say "bugs logged and fixed" — internally conflicting with no exit condition.
10. Phase 10 requires 60-item validation; risks table says "abort below 30" — acceptance vs fallback inconsistent.
11. Training-cutoff stratification declared "per model" but no authoritative cutoff metadata source for either model.
12. Phase 4 fallback to use original spec when paraphraser fails directly violates the contamination-defense invariant.

## Notes

13. Partial-credit scoring rule undefined for empty/ambiguous/no-keyword checklist items.
14. Token-count capture method from shell dispatches not specified — missing-data edge case.
15. Atomic-write and resume semantics for partial artifact files not defined.

---

## Also surfaced by local Claude review (relevant, not duplicates)

A. **Model-to-node pairing confound (BLOCKER)** — Phase 3 fixes Codex→Otis and Claude→Lomax. Hardware/node state now confounded with model. Either randomize node per run, or run both models on the same node.

B. **Paraphraser leakage risk (BLOCKER)** — Phase 4's paraphraser uses unspecified LLM. If dispatched to GPT-5/Gemini, the judge sees output derived from a spec it paraphrased. If to Claude or Codex, a contestant sees the spec pre-run. Invariant 2 must extend to the paraphraser.

C. **Recognition probe primes contestant (BLOCKER)** — Sending spec to the contestant pre-run makes the probe call part of its context for the scored run. Probe must use a non-retained process or run after scoring.

D. **pyproject.toml vs cli/main.py (BLOCKER)** — Project already registers `br` as `cli.main:app`. New subcommands are added via `app.add_typer(...)` in `cli/main.py`, which Phase 1 doesn't list.

E. **Phase 10 run count is 360, not 180** — 30 × 2 × 3 × 2 sub-studies = 360. The 15–20h budget derived from single-sub-study math must be doubled.

F. **Phase 3 success criterion is too ambitious pre-Phase-4/5** — Narrow it to a single dispatch + worktree + diff capture to avoid rework.

G. **Phase 5 pass@k requires 3 replications but Phase 3 doesn't list replication-loop support** — Add explicit `replications: int` input and per-replication RunResult emission to Phase 3.

H. **Diff format-normalization is not a Prettier/Black operation** — Must format pre/post source files and regenerate the diff; plan misstates this.

I. **BH correction without pre-registered hypothesis list** — Plan must enumerate comparisons that feed BH before running, not after.

J. **`lock:` commit SHA parsed from BUILD markdown, but SHA lives in git log** — Change source to `git log --grep='^lock: claim Phase N'`.

K. **"Warranted" update to runtime.json is undefined** — Codify decision rule (e.g., lower bound of Bradley-Terry 95% CI favors challenger) before running.

---

## Consolidated Blocker List (must fix before writing Phase 1 code)

1. Verify dispatch-to-node.sh path + declare as Phase 1 dependency
2. Phase 1 creates benchmark_registry.jsonl; declare path + writer contract
3. Phase 1 or 2 documents Walter + Lomax HTTP endpoints, auth, response schema
4. Replace "semantic-search" validator with a concrete NLI/judge call; declare source
5. Randomize or equalize node assignment to avoid model×node confound
6. Constrain paraphraser to a model outside the judge + contestant set; document it
7. Move recognition probe to a separate fresh process or run post-scoring
8. Phase 1 edits cli/main.py via `app.add_typer(...)`, not pyproject.toml alone
9. Rewrite Phase 10 budget with 360-run math (double the original)
10. Phase 3 adds `replications: int` + per-replication RunResult emission
11. Define the `runtime.json` update decision rule pre-run (e.g., BT 95% CI lower bound)
