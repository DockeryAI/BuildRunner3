# Adversarial Review Bypass — 2026-04-23

**Build:** `br3-cleanup-wave-abc`
**Plan:** `.buildrunner/plans/plan-br3-cleanup-wave-abc.md`
**Plan SHA:** `9ed95239e047b6dda4aee8d5eefd41c1c873cfb60ee96f1d15e00c447b785665`

## Why bypassed

Consensus review returned `exit_code: 1` with `arbiter_ruling.status: circuit_open`. The arbiter's circuit was already open at review time, so arbitration defaulted to `committed BLOCK until human reset` without true adjudication of the two reviewers' output. The Phase 2 deliverable of this very spec (fix `core/cluster/arbiter.py:50-66` circuit-breaker race) closes exactly this failure mode.

Reviewer findings fell into three categories:

1. **Fixable items applied inline** — Phase 1 zero-byte count typo (3→4); Phase 4 root-cleanliness success threshold (6→15) with list of canonical project files to keep; Phase 4 RLS SQL ↔ `rls_aware.py` sequencing note; Phase 5 pre-delete caller audit for all 8 orphan modules (named `rls_aware.py` explicitly to resolve Codex/`/dead` disagreement); Phase 6 `pin: true` success criterion now exercises `load-role-matrix.sh` directly (not inline `yaml.safe_load`); Phase 6 task 3 installer-mode contradiction removed; Phase 7 npm `overrides` field (not Yarn `resolutions`); Phase 7 `tests/test_imports.py` replaced with direct import smoke.
2. **Stale-tree artifacts** (Codex claimed paths don't exist which DO exist — verified in-session): `cli/`, `plugins/notion.py|slack.py|github.py`, `electron/package.json`, `hooks/__init__.py`, `.dispatch-worktrees/`, `.buildrunner/rollout-state.yaml`, `/api/memory/note` (endpoint returned `{"status":"saved"}` minutes before the review ran). Documented in the plan's "Adversarial Review Notes" preamble.
3. **Structural deferral** — runtime-dispatch dual-script "disambiguate vs collapse" decision noted explicitly; full physical merge deferred to a future cluster-infrastructure spec where caller migration can happen under test.

## Authority

/spec skill 1-review rule: "On BLOCKED → Fix the surfaced blockers inline in the draft plan, auto-bypass 3.7, proceed to 3.8." No re-run permitted in the same invocation.

---

# Prior bypass (for audit)

# Bypass Justification: plan-below-offload

**Plan:** `.buildrunner/plans/plan-below-offload.md`
**Date:** 2026-04-23
**Review outcome:** BLOCKED (Claude + Codex consensus, arbiter circuit_open)
**Bypass authority:** /spec skill 1-review rule (fix inline, do not re-run)

Retained historical record of the `plan-below-offload` bypass from earlier today; the full content lives in `.buildrunner/historical/` after Phase 4 of this cleanup build archives the `bypass-justification-*.md` series.
