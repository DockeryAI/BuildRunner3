# Prior-State Survey — role-matrix-codex-arbiter

**Build:** role-matrix-codex-arbiter
**Survey date:** 2026-04-25
**Trigger:** SHARED_SURFACE_TOUCHED=1 (5 surfaces) + PRIOR_BUILDS=56

## Prior BUILDs

- **BUILD_burnin-queue-v2** (in progress, phases 1-2 complete) — modifies `~/.buildrunner/scripts/burnin/lib/*.sh`. No file overlap with this spec, but it is currently active and uses `runtime-dispatch.sh` on every phase. **Risk:** modifying `runtime-dispatch.sh` (Phase 1) while burnin-queue-v2 is mid-build will affect every subsequent burnin-queue-v2 phase dispatch. **Mitigation:** Phase 1 changes are additive (read optional config, append flags only when present); existing dispatches without `codex-sandbox.toml` see standard behavior.
- **BUILD_cluster-role-matrix-router** (complete) — created `~/.buildrunner/scripts/load-role-matrix*.sh`, `default-role-matrix.yaml`. This spec's Phase 2 (Rule 22) lives in adjacent code; phase 2 must not regress role-matrix loader contract.
- **BUILD_codex-full-br3-integration** (complete) — installed codex CLI integration, likely the source of current `--sandbox workspace-write --cd $PROJECT_PATH` invocation in `runtime-dispatch.sh:62-68`. Phases 1, 3 of this spec evolve that integration without contradicting it.
- **BUILD_universal-role-routing** (complete) — defined the role-matrix routing model. Phase 2's Rule 22 patch must conform to its bucket/node abstraction.
- **BUILD_cross-model-review** (complete) — created `core/cluster/cross_model_review.py`. Phase 5 extends it with phase-scoped revision tracking; must preserve plan-mode review contract still relied on by `/spec` gate 3.7.
- **BUILD_dev-discipline-gates** (complete) — installed `enforce-spec-gates.sh` which gates this very spec. No conflict.

## Shared-Surface Impact

- `~/.buildrunner/scripts/runtime-dispatch.sh` — Phase 1, 3 modify. Used by EVERY dispatch from autopilot, /begin, /spec gates, /2nd, ship pipeline. **Constraint:** changes must be backward-compatible — empty/missing `codex-sandbox.toml` must not change behavior for projects that never created one.
- `core/cluster/cross_model_review.py` — Phase 5 modifies. Used by `/spec` (plan mode), `/2nd` (cross-model second opinion), `cross-model-review.sh`, and the adversarial-review pipeline. **Constraint:** existing `--mode plan` invocation contract preserved verbatim; Phase 5 only adds `--mode phase` as a NEW path with NEW hash key shape.
- `core/runtime/postflight.py` — Phase 7 may modify. Used by runtime resolution alerting. **Constraint:** existing `evaluate_runtime_alerts` and the `POLICY_ACTION_*` contract preserved.
- `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` — Phase 3 leaves untouched (creates a new sibling `autopilot-dispatch-prefix-codex.sh` instead). **Constraint:** claude prefix path remains the only producer of claude posture headers.
- `~/.claude/CLAUDE.md` and `~/Projects/BuildRunner3/CLAUDE.md` — informational. No edits planned. Operator-facing docs may need updates after Phase 6 default flip (handled by Phase 8 verification report, not as a phase deliverable).
- `~/.buildrunner/config/default-role-matrix.yaml` — read-only for this build. Phase 2's Rule 22 changes consult this but do not modify it.

## Governance Drift

- No `.buildrunner/governance.yaml` present in BR3 project root (verified: file absent). No project-level governance constraints to honor beyond CLAUDE.md.
- `~/.claude/CLAUDE.md` "Verify before acting" rule (load files, no guesses) — Phase 7 explicitly investigates source before patching, conforms.
- `~/.claude/CLAUDE.md` 4.7 effort default of `xhigh` for coding/agentic work — bootstrap phases 1-7 run on claude with this default. Phase 8 codex run inherits codex's `medium` default per fixit skill's documented anti-pattern guard.
- Project CLAUDE.md "Auto-Continue: ENABLED" — applies to /begin, not to /spec gating. Gates 3.7/3.8 still run.

## Completed-Phase Blast Radius

- BUILD_burnin-queue-v2 Phase 1, 2 (complete) wrote schema + state-machine code in `~/.buildrunner/scripts/burnin/`. **No file overlap** with this build — different scripts entirely. Listed for reference only.
- BUILD_codex-full-br3-integration phases that established `runtime-dispatch.sh` codex branch — Phase 1 of this build modifies the codex branch additively (preserves the existing `--sandbox workspace-write --cd "$PROJECT_PATH"` invocation, prepends `--add-dir` flags only when config present). Completed-phase contract honored.
- BUILD_cross-model-review completed phases — Phase 5 extends, does not rewrite. Existing plan-mode artifact tracking under `.buildrunner/cluster-reviews/` remains in place; phase-mode adds a sibling subdirectory.

## Net Risk Verdict

LOW for backward compat (every change is additive or a sibling). MEDIUM for bootstrap correctness (this build modifies the very dispatch path it depends on; Phase 1 must not break in-flight burnin-queue-v2). Phase ordering (1 before 2 before 6) plus claude-as-bootstrap-builder neutralizes the bootstrap risk.
