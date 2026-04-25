# Adversarial Review Bypass Justification

**Plan:** `.buildrunner/plans/plan-role-matrix-codex-arbiter.md`
**Build slug:** `role-matrix-codex-arbiter`
**Reviewed:** 2026-04-25 15:11:38 UTC
**Verdict:** BLOCKED (arbiter circuit_open)
**Actual blocker findings:** 1 (Phase 4 referenced nonexistent `cross-model-review.sh` script)
**Warning findings:** 8 (all addressed inline before bypass)
**Note findings:** 5 (all addressed inline before bypass)

## Why bypass is appropriate

Per the `/spec` skill 1-review rule: "On BLOCKED → Fix the surfaced blockers inline in the draft plan, auto-bypass 3.7, proceed to 3.8. Do NOT re-run the review." The consensus pipeline returned BLOCKED with the Opus arbiter circuit open ("circuit_open" — committed BLOCK until human reset). The substantive blocker plus all warnings and notes were fixed inline in the plan; the BLOCKED verdict is therefore being honored as informational rather than re-run, in compliance with the skill's hard cap of exactly one review per spec.

## Blocker fixed inline

**Phase 4 nonexistent script.** Original plan invoked `cross-model-review.sh --mode phase`; no such wrapper exists in the tree. Replaced with direct `python3 -m core.cluster.cross_model_review --mode phase` invocation in Phase 4 Step A, with explicit instruction not to introduce a wrapper.

## Warnings addressed inline

1. **Phase 2 Rule 22 locator.** Added 4-step fallback chain (grep strings → git log → override-emit grep → introduce policy file). Removed `core/cluster/context_router.py` reference (wrong abstraction layer per pre-spec review).
2. **Phase 3 codex effort posture.** Added rationale that `medium` is correct codex default per fixit skill; CLAUDE.md's `xhigh` mandate applies to claude side only; codex `xhigh` is documented anti-pattern.
3. **Phase 4 phase-loop driver locator.** Added 3-step fallback chain (grep / `build-sidecar.sh` / `runtime-dispatch.sh` exit fallback).
4. **Phase 5 idempotency key clarification.** Made canonical key explicit as the triple `(build_id, phase_n, revision_count)`; `diff_sha256` now scoped to tracking-file naming only, not idempotency.
5. **Phase 5 codex version gate.** Added deliverable to update `SUPPORTED_CODEX_VERSION_MAX` to accommodate installed codex 0.124.0 (currently rejects with strict 0.49.0 upper bound).
6. **Phase 6 rollback procedure.** Added explicit rollback deliverable: `br runtime set claude` reverts atomically; no migrations or stateful side-effects to undo.
7. **Phase 6 spec-codex skill path.** Added locator strategy (`find ~/.claude/skills -name SKILL.md -exec grep -l ...`) before claiming MODIFY; spec-codex may live as a branch of `/spec` rather than its own skill directory.
8. **Phase 8 node assignment.** Changed `assigned_node: lomax` → `muddy`. Burnin retest paths and `/tmp/codex-flow-test/` are Muddy-relative; lomax filesystem cannot satisfy them.

## Notes addressed inline

1. **Phase 1 regression artifact.** Added `tests/runtime/test_codex_sandbox_loader.sh` as persistent CI smoke artifact (not just a one-shot smoke test).
2. **Phase 8 verify directory.** Added explicit `mkdir -p .buildrunner/verify` deliverable so Write doesn't race the directory creation.
3. **Phase 8 automated assertion.** Replaced manual log inspection with `tests/verify/assert-role-matrix-flow.sh` grep-assertion script.
4. **Out-of-scope clarity.** Added explicit note that home-dir cluster scripts not under git is an accepted BR3 constraint (cluster-wide infra shared across projects on this machine).
5. **Phase 7 emit-site verification.** Added explicit deliverable to confirm/refute codex's claim about `core/runtime/postflight.py:303` already handling missing files; the original guess (`check-runtime-alerts.sh`) is unverified.

## Tracking

Reviews stored under `.buildrunner/adversarial-reviews/`. Plan source SHA: `88eca53a794970bf765a55d445811cd9466e3858e403e9021d1614707cdf0d97`. Survey: `.buildrunner/plans/survey-role-matrix-codex-arbiter.md`.
