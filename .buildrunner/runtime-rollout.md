# Runtime Rollout

Phase 13 rollout posture is intentionally conservative.

## Current Posture

- Claude remains the default runtime when runtime is omitted.
- Codex remains execution/build only after plan approval.
- Codex `/spec` remains BR3-workflow-only.
- Codex `/begin` remains BR3-workflow-only, sequential, and bounded.
- Shadow mode remains advisory-only.
- Remote Codex is not promoted or enabled by policy.

## Operator Checklist

1. Confirm `/api/runtime/health` reports expected status before investigating workflow failures.
2. Confirm `command_capabilities.json` still matches the intended support posture before changing any runtime routing.
3. Confirm `runtime-shadow.log` does not show unintended mutation or repeated blocker mismatches before discussing promotion.
4. Confirm remote-node auth/version/probe criteria separately before any remote Codex policy change.

## Rollout Boundaries

- Phase 13 does not enable live cutover.
- Phase 13 does not broaden command support beyond the audited capability map.
- Phase 13 does not treat review-spend budget tracking as a promotion signal.

## Next Safe Step After Phase 13

Proceed to Phase 14 consensus/adversarial review enforcement while preserving the same runtime posture.
