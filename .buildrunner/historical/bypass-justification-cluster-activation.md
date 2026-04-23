# Adversarial Review Bypass — Build: cluster-activation

**Date:** 2026-04-21
**BUILD spec:** `.buildrunner/builds/BUILD_cluster-activation.md`
**Plan file:** `.buildrunner/plans/cluster-activation-plan.md`
**Override artifact:** `.buildrunner/adversarial-reviews/cluster-activation-R3-user-override.json`
**Verdict:** `USER_OVERRIDE`
**Authorization:** `BR3_BYPASS_ADVERSARIAL_REVIEW=1` by `byron@dockeryai.com` at `2026-04-21T22:00:00Z`

## Why the override was used

Revision 2 of the BUILD cited adversarial reviews that were for a different artifact: `.buildrunner/plans/spec-draft-plan.md`, not `BUILD_cluster-activation.md`. The R2 reference was a cross-wiring error.

Revision 3 corrected authoring-contract drift only. It added:

- per-phase `builder`, `codex_model`, `codex_effort`, `reviewers`, and `arbiter` lines
- the inline `role_matrix` YAML block
- the `Codex Model` column in the Parallelization Matrix
- a mandatory Claude Review trigger per phase

No deliverables, file lists, phase titles, or phase boundaries changed.

## Invariants preserved

- All 6 phase titles remained unchanged
- Phase file whitelists remained unchanged
- Deliverables and success criteria remained unchanged
- The out-of-scope list remained unchanged
- Parallelization semantics remained unchanged; the new column was additive only

## Conditions attached to the override

- A proper `/review` pass still must run before Phase 6 is marked complete
- If any phase deliverable changes after the format-only R3 update, that phase must run its own review gate

## Risk assessment

- The override covered a format-only BUILD correction, not new executable scope
- The change introduced no new runtime, API, DB, or deployment surface
- Re-running a full 3-way review for formatting-only drift was considered disproportionate relative to the risk

Override accepted for the R3 authoring-contract correction only.
