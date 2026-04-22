# Adversarial Review Bypass — Phase 16 of BUILD_cluster-max

**Date:** 2026-04-22
**Build:** BUILD_cluster-max.md
**Phase:** 16 (Dashboard Unification — Backport Cluster Panels to :4400)
**Plan:** `.buildrunner/plans/phase-16-plan.md` (sha `5aadadb2075eb38191a84f443bf6008fe924a4c4ed148bd897fce5dd15369f71`)
**Verdict artifact:** `.buildrunner/adversarial-reviews/phase-16-20260422T140951Z.json`

## Context

Adversarial review ran once per the `/amend-codex` one-review rule
(`BR3_MAX_REVIEW_ROUNDS=1`). Verdict: BLOCKED with 5 distinct upheld blockers,
all marked `fix_type: fixable` by the arbiter. All five were local, obvious
fixes applied inline to `phase-16-plan.md` before this commit. Plan SHA was
recomputed and stamped in the BUILD spec header. The skill forbids re-running
the review on the same plan in the same invocation.

## Waivers (each finding addressed inline — not actually "waived," but

the hook requires this format for any bypass)

finding_id: phase-16-task-16.1-grep-pattern
waived_by: Byron Hudson (via /amend-codex skill)
reason: The `uvicorn|if __name__` grep pattern in the original Done-When would match nothing because `api/routes/dashboard_stream.py` has no `__main__` block — it exports `app = create_app(role="dashboard")` at module level. Fixed inline: Done-When now greps for the actual `app = create_app(role=...)` export AND searches for any uvicorn launch script targeting the module across `~/.buildrunner/scripts/`, `api/`, `core/`, `deploy/`.

finding_id: phase-16-valid-types-gate
waived_by: Byron Hudson (via /amend-codex skill)
reason: `VALID_TYPES` in `events.mjs` gates every SSE broadcast; the five new cluster topic names weren't listed. Fixed inline: Task 16.4 Constraints now explicitly require adding `feature-health`, `node-health`, `overflow-reserve`, `storage-health`, `consensus` to `VALID_TYPES`, and Task 16.4 Done-When verifies their presence via `grep -n VALID_TYPES`.

finding_id: phase-16-unknown-status-contract
waived_by: Byron Hudson (via /amend-codex skill)
reason: Original plan said readers return `status: "unknown"` on missing sources; the feature-health contract (Phase 6 success criterion — "zero unknown") forbids `unknown`. Fixed inline in Task 16.3 Constraints and Task 16.4 Done-When: readers return `status: "yellow"` with a `reason` field, matching the existing `_collect_feature_health` fallback in `api/routes/dashboard_stream.py:178–381`.

finding_id: phase-16-task-16.1-test-path
waived_by: Byron Hudson (via /amend-codex skill)
reason: Original Done-When referenced `pytest tests/api/` which does not exist in the repo. Fixed inline: Done-When now uses `pytest -q tests/ -k dashboard_stream` with tolerance for "no tests ran" (the assertion is no new failures, not that tests must exist).

finding_id: phase-16-task-16.6-jq-pipeline
waived_by: Byron Hudson (via /amend-codex skill)
reason: Original jq pipeline didn't strip the SSE `data: ` prefix before parsing, and referenced `.tiles[]` at top level when the actual payload envelope wraps tiles under `.data.tiles`. Fixed inline: new pipeline strips the prefix with `awk`, selects the first `feature-health` event, parses the `.data.tiles` array, and asserts `length == 15 AND all statuses ∈ {green,yellow,red}`.

## One-review rule

Per `/amend-codex` Step 3.5: "Never re-run the adversarial review on the same
plan in the same invocation... one review, one fix pass, then commit."
All five blockers were fixable and local. No structural rewrite needed. No
product decisions required.
