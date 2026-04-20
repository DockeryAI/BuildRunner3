# Codex Full BR3 Integration Plan

## Objective

Integrate Codex into BR3 as a first-class coding agent without disrupting the current Claude-based workflow.

The end state is:

- One BR3 orchestration system
- One dashboard
- One build/state model
- Two selectable runtimes: Claude and Codex
- Claude remains fully usable during the migration
- The current Claude-driven BR3 path stays live and undisrupted until an explicit switch-over phase

## Core Decision

Do not build two separate systems.

Build one shared BR3 control plane with a runtime abstraction layer:

- `ClaudeRuntime`
- `CodexRuntime`

BR3 should own:

- build specs
- plans
- locks
- approvals
- dashboard events
- registry/state
- cluster dispatch decisions
- policy enforcement
- shared context assembly

The runtime layer should only own:

- task execution
- model-specific prompt/session handling
- model-specific tool/capability shims
- returning output, edits, findings, and status

## Migration Guardrails

- This migration runs in parallel with the current BR3 implementation; it must not disrupt the live Claude path.
- Claude remains the default runtime for research, planning, spec generation, and architecture work.
- Codex is introduced first as an execution/build runtime after a build plan is completed and approved.
- Expanding Codex beyond execution/build requires an explicit later amendment, not drift during implementation.

## Required Phase Closeout Protocol

Every completed phase must end with the same closeout loop so the next session inherits a complete and accurate checkpoint.

Required closeout steps:

1. Update both source-of-truth plan documents:
   - `.buildrunner/builds/BUILD_codex-full-br3-integration.md`
   - `.buildrunner/Codex Full BR3 Integration Plan.md`
2. Record the real checkpoint rather than the intended one:
   - actual phase status
   - actual gate result
   - constraints still in force
   - next safe build step
   - verification commands and results
   - probe/runtime measurements when relevant
3. Update any phase artifacts that serve as direct handoff context for the next session.
4. Run a cumulative Claude review over all completed work through the current phase, not just the latest edits.
5. Claude is the final review authority for that cumulative pass:
   - implement required fixes
   - re-run focused verification
   - send the updated cumulative scope back to Claude
   - if the review cycle is completed and the remaining findings are documented rather than blocking implementation work, the user may mark the phase complete without requiring a terminal `NO_FINDINGS`
6. Write the cumulative review result back into both source-of-truth documents before ending the session.

## Current Checkpoint

- BUILD document phase numbering is authoritative for implementation status from this point forward; the lower plan section names are historical and should not override the BUILD-defined Phase 9/10 scope.
- Phase 0 is complete with a `CONDITIONAL_GO` result, not an unconditional pass.
- The original repo-scoped review baseline was a `NO-GO`.
- The fix pass proved Codex can handle representative BR3 review workloads only when execution is isolated from the repo workspace, BUILD context is narrowed, multi-file diffs are batched, and oversized new-file diffs are chunked.
- The active live BR3 review helper was restored after validation so current infrastructure remains unchanged until explicit cutover.
- Phase 1 completed as a parallel-only shadow scaffold with no live runtime routing or default behavior changes.
- Phase 2 command inventory is complete and formalized a long-term hybrid strategy rather than near-term full parity.
- Phase 3 dispatch/auth architecture work is complete with a local-only Gate B result.
- Muddy/local passed Codex preflight and direct probe on `codex-cli 0.48.0`.
- Lomax is the only remote node currently exposing Codex, but it failed the validated version gate on `codex-cli 0.47.0` and its direct probe ended with `401 Unauthorized` after repeated reconnect attempts.
- Otis currently exposes Claude only, and Lockwood currently exposes neither Claude nor Codex.
- Remote Codex remains disabled until a remote node matches the validated version, auth, and probe baseline.
- Phase 4 is complete and locks the BR3 runtime contract around versioned task/result schemas, capability profiles, checkpoint records, canonical edit normalization, observed-change tracking, and fail-closed same-file proposal conflicts.
- Phase 5 is complete and adds runtime config resolution plus explicit CLI/API runtime selection without changing the default Claude path when runtime is omitted.
- Runtime config precedence now exists exactly as planned: explicit selection, project config, user config, then default Claude.
- Phase 5 added `.buildrunner/runtime.json` as the schema example fixture and runtime-resolution smoke coverage in `tests/runtime/test_config_resolution.py`.
- Phase 6 implementation work is landed for shared preflight/postflight policy extraction, and the phase is complete under the amended closeout rule.
- Phase 6 focused verification command: `python3 -m py_compile core/runtime/policy_result.py core/runtime/preflight.py core/runtime/postflight.py core/runtime/shadow_runner.py`
- Phase 6 focused verification result: success (`exit 0`, no output).
- Phase 6 focused verification command: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py -q`
- Phase 6 focused verification result: `47 passed, 2 warnings in 1.18s`
- Phase 6 targeted UI verification command: `cd ui && npx vitest run src/stores/buildStore.test.ts`
- Phase 6 targeted UI verification result: `1 passed`
- Phase 6 actual gate result is `COMPLETE_BY_USER_OVERRIDE_AFTER_REVIEW_CYCLE`.
- Phase 6 still keeps all existing migration constraints in force: no live routing/cutover, no remote Codex enablement, omitted runtime behavior unchanged, Claude default preserved for research/planning/spec/architecture, Codex execution/build only after plan approval.
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun multiple times for the Phase 6 scope after additional hardening fixes.
- Those reruns completed but still returned `FINDING:` output rather than the required exact terminal result `NO_FINDINGS`.
- On 2026-04-16, the user amended the closeout rule: if the review cycle is complete, the phase may be marked complete without a final `NO_FINDINGS`.
- Phase 6 is therefore complete under the amended closeout rule, and the cumulative review checkpoint is advanced through Phase 6.
- On 2026-04-16, the BUILD source-of-truth Phase 7 dashboard-runtime-awareness implementation landed across the dashboard registry filter, build-session API serialization, runtime metadata websocket/session updates, and dashboard/store hydration slice.
- On 2026-04-16, the BUILD source-of-truth Phase 8 shadow-mode hardening landed across `core/runtime/shadow_runner.py`, `tests/integration/test_shadow_mode.py`, and `.buildrunner/runtime-shadow-metrics.md`, including timeout isolation so shadow failures do not contaminate the primary result.
- Phase 7 and Phase 8 focused verification command: `python3 -m py_compile core/build_session.py api/routes/build.py core/runtime/shadow_runner.py`
- Phase 7 and Phase 8 focused verification result: success (`exit 0`, no output).
- Phase 7 and Phase 8 focused verification command: `.venv/bin/python -m pytest tests/runtime/test_review_spike.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py -q`
- Phase 7 and Phase 8 focused verification result: `33 passed, 2 warnings in 0.85s`
- Phase 7 targeted UI verification command: `cd ui && npx vitest run src/stores/buildStore.test.ts`
- Phase 7 targeted UI verification result: `4 passed`
- Touched-file TypeScript verification for `ui/src/stores/buildStore.ts`, `ui/src/pages/BuildMonitor.tsx`, `ui/src/components/CommandCenter.tsx`, and `ui/src/utils/websocketClient.ts` returned no diagnostics.
- Repo-wide `cd ui && npx tsc --noEmit` still fails on pre-existing unrelated diagnostics outside the Phase 7/8 slice, so no clean repo-wide TypeScript gate was established here.
- All migration constraints remain in force: no live routing/cutover, no remote Codex enablement, omitted runtime behavior unchanged, Claude remains default for research/planning/spec/architecture, Codex remains execution/build only after plan approval.
- A targeted Claude review rerun over the Phase 7/8 diff was completed multiple times on 2026-04-16 and the actionable findings were fixed before the cumulative pass.
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun through the completed Phase 8 scope and returned `NO_FINDINGS`.
- The cumulative review checkpoint is now advanced through Phase 8.
- Cumulative focused verification command for the reviewed 0 through 8 scope: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py -q`
- Cumulative focused verification result for the reviewed 0 through 8 scope: `55 passed, 2 warnings in 1.90s`
- Phase 7 actual gate result: `COMPLETE_RUNTIME_AWARE_DASHBOARD`
- Phase 8 actual gate result: `COMPLETE_ADVISORY_SHADOW_NOT_PROMOTED`
- On 2026-04-16, the BUILD-authoritative Phase 9 implementation landed across `core/runtime/command_compiler.py`, `core/runtime/command_capabilities.json`, `core/runtime/context_compiler.py`, `core/runtime/preflight.py`, `.buildrunner/runtime-skill-mapping.md`, and the installed Codex skill wrappers under `~/.codex/skills/`.
- Phase 9 actual gate result: `COMPLETE_COMMAND_COMPILER_CONTEXT_TRANSLATION`.
- On 2026-04-16, the BUILD-authoritative Phase 10 implementation landed across `core/runtime/workflows/spec_workflow.py`, `core/runtime/workflows/__init__.py`, `core/runtime/codex_runtime.py`, `core/runtime/base.py`, `api/routes/execute.py`, and `tests/integration/test_codex_spec_workflow.py`.
- Phase 10 actual gate result: `COMPLETE_CODEX_SPEC_GATED_WORKFLOW`.
- Phase 9/10 focused verification command: `python3 -m py_compile core/runtime/command_compiler.py core/runtime/context_compiler.py core/runtime/preflight.py core/runtime/codex_runtime.py core/runtime/workflows/spec_workflow.py api/routes/execute.py tests/runtime/test_command_compiler.py tests/integration/test_codex_spec_workflow.py`
- Phase 9/10 focused verification result: success (`exit 0`, no output).
- Cumulative focused verification command for the reviewed 0 through 10 scope: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/runtime/test_command_compiler.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py tests/integration/test_codex_spec_workflow.py -q`
- Cumulative focused verification result for the reviewed 0 through 10 scope: `61 passed, 2 warnings in 1.51s`
- All migration constraints remain in force: no live routing/cutover, no remote Codex enablement, omitted runtime behavior unchanged, Claude remains default for research/planning/spec/architecture, Codex remains execution/build only after plan approval, and Phase 8 shadow mode remains advisory-only and not promoted.
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun through the completed Phase 10 scope and returned `NO_FINDINGS`.
- The cumulative review checkpoint is now advanced through Phase 10.
- On 2026-04-16, the BUILD-authoritative Phase 11 implementation landed across `core/runtime/capability_gate.py`, `core/runtime/workflows/begin_workflow.py`, `core/runtime/base.py`, `core/runtime/codex_runtime.py`, `core/runtime/command_capabilities.json`, `api/routes/execute.py`, and `tests/integration/test_codex_begin_workflow.py`.
- Phase 11 actual gate result: `COMPLETE_BEGIN_BOUNDED_SEQUENTIAL_GATE`.
- Phase 11 focused verification command: `python3 -m py_compile core/runtime/capability_gate.py core/runtime/workflows/begin_workflow.py core/runtime/base.py core/runtime/codex_runtime.py api/routes/execute.py tests/integration/test_codex_begin_workflow.py tests/runtime/test_command_compiler.py`
- Phase 11 focused verification result: success (`exit 0`, no output).
- On 2026-04-16, the BUILD-authoritative Phase 12 implementation landed across `~/.buildrunner/scripts/runtime-dispatch.sh`, `~/.buildrunner/scripts/dispatch-to-node.sh`, `~/.buildrunner/scripts/_dispatch-core.sh`, `~/.buildrunner/scripts/build-sidecar.sh`, `~/.buildrunner/dashboard/events.mjs`, `~/.buildrunner/lib/build-state-machine.mjs`, and `tests/integration/test_codex_remote_dispatch.py`.
- Phase 12 actual gate result: `COMPLETE_RUNTIME_AWARE_DISPATCH_CONTRACT_NO_REMOTE_PROMOTION`.
- Phase 12 focused verification command: `bash -n /Users/byronhudson/.buildrunner/scripts/runtime-dispatch.sh /Users/byronhudson/.buildrunner/scripts/build-sidecar.sh /Users/byronhudson/.buildrunner/scripts/dispatch-to-node.sh /Users/byronhudson/.buildrunner/scripts/_dispatch-core.sh`
- Phase 12 focused verification result: success (`exit 0`, no output).
- Phase 12 focused verification command: `node --check /Users/byronhudson/.buildrunner/dashboard/events.mjs`
- Phase 12 focused verification result: success (`exit 0`, no output).
- Phase 12 post-review focused verification command: `.venv/bin/python -m pytest tests/integration/test_codex_begin_workflow.py tests/integration/test_codex_remote_dispatch.py tests/integration/test_runtime_build_monitor.py tests/runtime/test_command_compiler.py tests/integration/test_policy_parity.py tests/integration/test_shadow_mode.py -q`
- Phase 12 post-review focused verification result: `37 passed, 2 warnings in 7.54s`
- Cumulative focused verification command for the reviewed 0 through 12 scope: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/runtime/test_command_compiler.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py tests/integration/test_codex_spec_workflow.py tests/integration/test_codex_begin_workflow.py tests/integration/test_codex_remote_dispatch.py -q`
- Cumulative focused verification result for the reviewed 0 through 12 scope: `69 passed, 2 warnings in 10.90s`
- All migration constraints remain in force: no live routing/cutover, omitted runtime behavior unchanged, Claude remains default for research/planning/spec/architecture, Codex remains execution/build only after plan approval, Phase 8 shadow mode remains advisory-only and not promoted, Phase 10 `/spec` remains BR3-workflow-only, and remote Codex remains disabled because live node readiness was not re-verified in this session.
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun through the completed Phase 12 scope and returned `NO_FINDINGS`.
- The cumulative review checkpoint is now advanced through Phase 12.
- The next safe build step is to begin BUILD-authoritative Phase 13 hardening/rollout work; any future remote Codex promotion still requires a fresh live node version/auth/probe validation pass before policy changes.
- On 2026-04-16, the BUILD-authoritative Phase 13 implementation landed across `tests/runtime/test_capabilities.py`, `tests/integration/test_runtime_selection.py`, `tests/integration/test_claude_regression_smoke.py`, `.buildrunner/runtime-observability.md`, `.buildrunner/runtime-rollout.md`, `.buildrunner/runtime-runbook.md`, `ui/src/components/CommandCenter.tsx`, `~/.buildrunner/dashboard/events.mjs`, and `~/.buildrunner/scripts/developer-brief.sh`.
- Phase 13 actual gate result: `COMPLETE_HARDENING_OBSERVABILITY_ROLLOUT_NO_REMOTE_PROMOTION`.
- Phase 13 focused verification command: `.venv/bin/python -m pytest /Users/byronhudson/Projects/BuildRunner3/tests/runtime/test_capabilities.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_runtime_selection.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_claude_regression_smoke.py -q`
- Phase 13 focused verification result: `9 passed, 2 warnings in 0.65s`
- On 2026-04-16, the BUILD-authoritative Phase 14 implementation landed across `.buildrunner/adversarial-reviews/README.md`, `~/.buildrunner/hooks/require-adversarial-review.sh`, `~/.buildrunner/scripts/adversarial-review.sh`, `.buildrunner/hooks/pre-commit`, `~/.claude/commands/spec.md`, `~/.claude/commands/amend.md`, `core/runtime/workflows/spec_workflow.py`, `core/runtime/preflight.py`, and `tests/integration/test_adversarial_review_enforcement.py`.
- Phase 14 actual gate result: `COMPLETE_CONSENSUS_ADVERSARIAL_REVIEW_ENFORCEMENT`.
- Phase 14 focused verification command: `.venv/bin/python -m pytest /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_adversarial_review_enforcement.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_codex_spec_workflow.py -q`
- Phase 14 focused verification result: `5 passed in 1.67s`
- Cumulative focused verification command for the reviewed 0 through 14 scope: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/runtime/test_command_compiler.py tests/runtime/test_capabilities.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py tests/integration/test_codex_spec_workflow.py tests/integration/test_codex_begin_workflow.py tests/integration/test_codex_remote_dispatch.py tests/integration/test_runtime_selection.py tests/integration/test_claude_regression_smoke.py tests/integration/test_adversarial_review_enforcement.py -q`
- Cumulative focused verification result for the reviewed 0 through 14 scope: `81 passed, 2 warnings in 9.53s`
- All migration constraints remain in force: no live routing/cutover, omitted runtime behavior unchanged, Claude remains default for research/planning/spec/architecture and when runtime is omitted, Codex remains execution/build only after plan approval, Phase 8 shadow mode remains advisory-only, Phase 10 `/spec` remains BR3-workflow-only, Phase 11 `/begin` remains sequential and bounded, unsupported flows fail closed or hand off explicitly, blocker disagreements remain explicit and blocking, and remote Codex remains disabled because live node readiness was not re-verified in this session.
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun through the completed Phase 14 scope and returned `NO_FINDINGS`.
- The cumulative review checkpoint is now advanced through Phase 14.
- The next safe build step is to stop at the completed BUILD-authoritative Phase 14 checkpoint. Any future remote Codex promotion or post-Phase-14 behavior requires a new BUILD amendment plus fresh live node version/auth/probe validation before policy changes.
- On 2026-04-16, a cumulative Claude final-authority review was completed for Phases 0 through 3, including the runtime boundary, tests, dispatch scripts, inventory, baseline artifacts, and source-of-truth docs.
- The cumulative review initially found bugs in runtime result serialization, diff-path sanitization, Codex isolation/compatibility handling, machine-specific tests, and Phase 9 spec drift; those were fixed before closeout.
- Focused verification command: `.venv/bin/python -m pytest tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/runtime/test_review_spike.py -q`
- Focused verification result: `18 passed, 2 warnings`
- Final cumulative Claude authority result for Phases 0 through 3: `NO_FINDINGS`
- Phase 4 and Phase 5 focused verification command: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py -q`
- Phase 4 and Phase 5 focused verification result: `30 passed, 2 warnings`
- On 2026-04-16, the mandatory cumulative Claude final-authority review was re-run across the full completed Phase 0 through Phase 5 scope after the Phase 4 and Phase 5 contract/config changes landed.
- Final cumulative Claude authority result for Phases 0 through 5: `NO_FINDINGS`

## Success Criteria

This project is complete when all of the following are true:

1. BR3 can run either Claude or Codex by explicit runtime selection.
2. Claude remains the default and existing Claude flows still work.
3. The dashboard shows both runtimes through the same event/state pipeline.
4. Critical policy enforcement no longer depends only on Claude hooks.
5. Codex can successfully handle review, analysis, planning, and selected execution workflows through BR3.
6. `/spec` and `/begin` work through Codex in production-safe mode.
7. Cluster-dispatched Codex runs report heartbeats, logs, progress, and exit state the same way Claude runs do.

## Non-Goals

This plan does not try to:

- replace Claude immediately
- recreate every Claude-specific feature inside Codex on day one
- rewrite all 65 slash commands before shipping any value
- split BR3 into a second product

## Architecture Target

### Shared BR3 Layer

The shared BR3 layer should become the source of truth for:

- command intent
- build progression
- approvals
- policy checks
- state transitions
- dashboard telemetry
- cluster execution contracts

### Runtime Adapters

Each runtime adapter should implement the same BR3-facing contract:

- `prepare_context()`
- `run_analysis()`
- `run_review()`
- `run_plan()`
- `run_phase_execution()`
- `stream_events()` when supported, or buffered progress when not
- `cancel()`
- `save_orchestration_checkpoint()`
- `resume_orchestration_task()`
- `run_postflight()`

The Claude adapter should initially wrap existing behavior.

The Codex adapter should be introduced as a new peer backend rather than a Claude imitation layer.

### Consensus Review Model

BR3 reviews should not stop at one-pass disagreement when more than one reviewer is involved. The default multi-review pattern should be a bounded Claude + Codex consensus loop, with BUILD phase creation, `/spec`, `/amend`, and promoted architecture reviews making that loop mandatory.

The V1 review loop should work like this:

1. Claude and Codex review the same artifact independently in parallel.
2. BR3 merges findings into one review artifact with source attribution.
3. If disagreements remain, BR3 runs up to two rebuttal rounds where each reviewer sees the merged findings.
4. BR3 marks consensus blockers, one-sided warnings, and unresolved disagreements explicitly.
5. If blocker disagreement remains after the bounded loop, the system escalates to the user instead of pretending consensus exists.

The session boundary for this logic should be one BR3 `task_id`. One runtime may be the authoritative writer for that task. Secondary or shadow reviewers remain advisory-only in V1.

## Workstreams

### 1. Runtime Abstraction

Create a new internal runtime layer so BR3 stops hardcoding Claude in CLI, dashboard, and dispatch logic.

Initial module targets:

- `core/runtime/base.py`
- `core/runtime/claude_runtime.py`
- `core/runtime/codex_runtime.py`
- `core/runtime/context_compiler.py`
- `core/runtime/runtime_registry.py`

### 2. Policy Extraction

Move critical checks out of Claude-only hooks and into BR3-managed preflight/postflight stages.

Policy areas to extract:

- protected file rules
- BUILD/spec gates
- prompt-writing rules
- formatting
- runtime alerts
- session persistence
- memory/research injection

### 3. Dashboard and State Integration

Extend the current event/state system to become runtime-aware instead of Claude-specific.

New build metadata should include:

- `runtime`
- `backend`
- `session_id`
- `capabilities`
- `dispatch_mode`

### 4. Command Migration

Port BR3 command families in a safe order:

- context-loading commands
- review and analysis commands
- planning commands
- primary execution flows
- long-running orchestration flows

### 5. Cluster and Sidecar Support

Generalize dispatch and sidecar logic so both Claude and Codex can run through the same heartbeat, progress, and exit reporting pipeline.

Current status on 2026-04-15:

- `dispatch-to-node.sh` now performs runtime preflight before launch, with direct failure for Codex, advisory-only behavior for Claude during migration, and advisory-only behavior for shadow runtime checks.
- `check-runtime-auth.sh` uses the shared BR3 helper logic from `core/cluster/cross_model_review.py` and ships the current helper to remote nodes before preflight so stale remote checkouts do not control the decision.
- V1 Codex process ownership is still `codex exec` wrapped by the existing BR3 sidecar.
- Codex remains local-only after Phase 3 because remote readiness is node-specific and not yet reliable.

### 6. Shadow Mode and Rollout

Run Codex in parallel with Claude on selected workflows before giving Codex ownership of those workflows.

### Phase 2: Command Inventory

Status: complete.

The command inventory now exists as `.buildrunner/runtime-command-inventory.md` and `.buildrunner/runtime-command-inventory.json`, generated by `tools/runtime/audit_commands.py`.

Inventory result:

- 65 commands cataloged from `~/.claude/commands`
- 12 skills cataloged from `~/.claude/skills`
- Migration buckets: 10 trivial, 11 moderate, 9 hard, 35 keep-Claude-first
- Core command decision gate: 14 of 16 core commands are low-portability or Claude-first

Outcome:

- BR3 should not pursue near-term parity across the full command surface.
- Claude remains the long-term default for research, planning, architecture, and browser-heavy orchestration commands.
- Codex migration should stay focused on execution-centric commands first.

### 7. Consensus Review and Enforcement

Add a BR3-owned consensus review system so new BUILD phases and other high-stakes planning artifacts carry an audit trail showing Claude + Codex review happened before commit or promotion.

## Phased Build Plan

Historical note: the phase names below were drafted before the BUILD document’s later renumbering. Use `.buildrunner/builds/BUILD_codex-full-br3-integration.md` as the authoritative phase numbering and completion source for Phases 7 and beyond.

### Phase 0: Baseline and Safety Rails

#### Goal

Create the migration scaffolding without changing current Claude behavior.

#### Status

Conditionally complete. The safety baseline exists, but the validated Codex path is limited to isolated review execution patterns rather than the original repo-scoped path.

#### Deliverables

- Add runtime selection config with default `claude`
- Add feature flags for Codex shadow mode and Codex execution mode
- Define shared runtime interface and response schema
- Add runtime metadata fields to build/session records
- Document rollback path for every new runtime feature
- Run a Codex capability audit before adapter work starts
- Pin an acceptable Codex CLI version range and add compatibility checks
- Define explicit auth failure policy before cluster rollout
- Add cost and observability baselines from the first spike onward

#### Key Files to Touch

- `/Users/byronhudson/Projects/BuildRunner3/cli/main.py`
- `/Users/byronhudson/Projects/BuildRunner3/cli/alias_commands.py`
- `/Users/byronhudson/.buildrunner/dashboard/events.mjs`
- `/Users/byronhudson/.buildrunner/lib/build-state-machine.mjs`

#### Exit Criteria

- Claude remains the default everywhere
- No current Claude command behavior changes
- BR3 can represent runtime choice in config/state even if only Claude executes

### Phase 1: Runtime Abstraction Layer

#### Goal

Introduce a clean runtime boundary inside BR3.

#### Status

Complete in parallel-shadow form. The runtime boundary, review context compiler, runtime registry, and explicit shadow `/review` spike path are in place without changing the live BR3 route.

#### Next-Session Constraint

Begin with a parallel-only scaffold. Do not wire Codex into the live BR3 routing path or change the default Claude behavior in this phase.

#### Deliverables

- Shared runtime base class or interface
- `ClaudeRuntime` adapter that wraps current Claude behavior
- `CodexRuntime` adapter stub with minimal invocation path
- Context compiler that assembles shared BR3 context independently of runtime
- Structured runtime result object for findings, edits, logs, and failures

#### Design Rules

- BR3 owns workflow state
- Runtime adapters do not own build state transitions
- Runtime adapters do not write directly to dashboard storage

#### Exit Criteria

- BR3 can call a runtime adapter instead of shelling Claude directly in at least one non-critical path
- Existing Claude path still works through the adapter

#### Outcome

- BR3 can execute a shadow `/review` spike through `ClaudeRuntime` and `CodexRuntime` under one shared `RuntimeTask`.
- The API exposes one normalized response envelope for both runtimes through the explicit shadow route.
- A real synthetic spike completed successfully in both runtimes while keeping live BR3 behavior untouched.

### Phase 2: Shared Preflight and Postflight Policy

#### Goal

Make critical governance runtime-neutral.

#### Deliverables

- BR3 preflight pipeline
- BR3 postflight pipeline
- Reuse existing Claude hook scripts where possible, but call them from BR3
- Central policy result format: pass, warn, block

#### Policy to Centralize First

- protected files
- BUILD/spec gating
- formatting
- runtime alerts
- auto-save/session persistence

#### Exit Criteria

- A Codex run and a Claude run hit the same BR3-managed safety checks
- Claude hooks can remain enabled, but BR3 is no longer dependent on them for correctness

### Phase 3: Dashboard Runtime Awareness

#### Goal

Make the existing dashboard support both runtimes without splitting the UI or event server.

#### Deliverables

- Add runtime metadata to event payloads
- Add runtime fields to build registry/state machine
- Update dashboard views to show Claude vs Codex
- Preserve one build lifecycle model for both

#### Key Files to Touch

- `/Users/byronhudson/.buildrunner/dashboard/events.mjs`
- `/Users/byronhudson/.buildrunner/lib/build-state-machine.mjs`
- `/Users/byronhudson/Projects/BuildRunner3/ui/src/components/CommandCenter.tsx`
- `/Users/byronhudson/Projects/BuildRunner3/ui/src/pages/BuildMonitor.tsx`

#### Exit Criteria

- A build can be registered and displayed with `runtime=claude` or `runtime=codex`
- Heartbeats, suspect/stalled states, and exit behavior remain unified

### Phase 4: Codex Shadow Mode for Analysis and Review

#### Goal

Start using Codex through BR3 where risk is low and value is immediate.

#### First Workflows

- `/review`
- `/root`
- `/dead`
- `/guard`
- `/gaps`
- `/why`
- `/diag`
- plan critique and adversarial review

#### Deliverables

- BR3 command routing for review and analysis workloads
- Codex outputs stored alongside Claude outputs for comparison
- Side-by-side quality tracking for findings, latency, and failure modes
- Advisory-only shadow mode with no edit application
- Kill switch, timeout, and resource limits for shadow runs
- Bounded consensus review loop on promoted review surfaces

#### Existing Assets to Reuse

- `/Users/byronhudson/Projects/BuildRunner3/core/cluster/cross_model_review.py`
- `/Users/byronhudson/.buildrunner/scripts/adversarial-review.sh`
- `/Users/byronhudson/.claude/skills/2nd/SKILL.md`
- `/Users/byronhudson/.claude/skills/codex-do/SKILL.md`

#### Exit Criteria

- Codex can run these workflows through BR3 without affecting Claude users
- Review results appear in the same BR3 system

### Phase 5: Command and Skill Translation

#### Goal

Port the easy command classes and shared knowledge first.

#### First Command Families

- context loaders
- research/context skills
- static analysis commands
- review/reporting commands

#### Skills to Port Early

- `br3-frontend-design`
- `br3-planning`
- `chet`
- `prodlog`
- `business`
- `geo`
- `sales`
- `security-rules`

#### Deliverables

- Codex-compatible skill/context package
- BR3 command compiler that can assemble command docs plus local context for Codex
- Shared command metadata describing which runtime supports which command modes

#### Exit Criteria

- Codex has equivalent domain context for planning, design, and analysis
- BR3 can invoke selected commands through either runtime

### Phase 6: Codex Planning Ownership

#### Goal

Let Codex own planning and spec generation workflows before full execution workflows.

#### First Targets

- `/spec`
- plan drafting
- plan critique
- setlist-style planning support

#### Deliverables

- Codex-generated BR3 plan outputs in the expected file formats
- Shared approval gate handling owned by BR3, not hidden inside the model runtime
- Structured blocker/warning feedback loop

#### Exit Criteria

- `/spec` works through Codex under BR3
- The same BUILD/spec gating logic applies to Claude and Codex

### Phase 7: Codex `/begin` Support

#### Goal

Make Codex capable of driving the primary day-to-day BR3 workflow.

#### Deliverables

- BR3-managed lock handling
- BR3-managed approval gates
- shared design gate handling
- heartbeat updates during execution
- Codex phase execution using the shared runtime interface

#### Important Scope Control

Do not start with parallel subagents or full autopilot behavior.
Start with sequential `/begin` execution on bounded phases.

#### Exit Criteria

- Codex can complete `/begin` on selected projects/phases safely
- Claude `/begin` remains unchanged and production-default

### Phase 8: Cluster Dispatch Generalization

#### Goal

Generalize the current cluster execution path so either runtime can be dispatched and monitored the same way.

#### Deliverables

- Runtime-aware dispatch contract
- Runtime-aware sidecar wrapper
- Shared heartbeat and exit reporting for Claude and Codex
- Runtime-specific command assembly at dispatch time

#### Key Files to Touch

- `/Users/byronhudson/.buildrunner/scripts/dispatch-to-node.sh`
- `/Users/byronhudson/.buildrunner/scripts/build-sidecar.sh`
- `/Users/byronhudson/.buildrunner/scripts/_dispatch-core.sh`
- `/Users/byronhudson/.buildrunner/dashboard/events.mjs`

#### Exit Criteria

- A cluster job can run with `runtime=codex`
- Dashboard liveness behavior works the same as Claude jobs

### Phase 9: Long-Running Orchestration and Autopilot

#### Goal

Evaluate whether Codex should support the most complex orchestration flows.

#### Targets

- `/autopilot`
- complex multi-phase execution
- optional parallel task decomposition
- long-running background workflows

#### Recommendation

Do this last. It has the highest risk and the weakest business value early in the migration.

#### Exit Criteria

- Codex long-running flows are stable enough to use by choice
- Claude remains available for workflows that still fit it better

### Phase 10: Consensus Review Enforcement

#### Goal

Make bounded Claude + Codex consensus review mandatory for new BUILD phases and other high-stakes planning artifacts.

#### Targets

- `/spec`
- `/amend`
- new BUILD phase creation
- promoted architecture and planning reviews

#### Deliverables

- Parallel adversarial review runner
- Tracking files under `.buildrunner/adversarial-reviews/`
- Merged findings with source attribution, consensus blockers, and unresolved disagreements
- Pre-commit or equivalent enforcement that blocks new BUILD phases without tracking files
- Emergency bypass with loud audit logging

#### Exit Criteria

- New BUILD phases cannot land without recorded consensus review unless explicitly bypassed with audit trail
- Consensus blockers are highlighted clearly
- Unresolved blocker disagreements escalate instead of silently passing

## Command Migration Order

Port commands in this order:

1. Context loaders
2. Review and analysis commands
3. Planning commands
4. `/spec`
5. `/begin`
6. Cluster-dispatched execution
7. `/autopilot`
8. Browser-heavy or highly interactive commands

## Rollout Strategy

### Stage 1: Hidden Internal

- Runtime abstraction exists
- Claude still owns all real workflows
- Codex runs only where already integrated or in internal test paths

### Stage 2: Shadow Mode

- Codex runs beside Claude on review/planning tasks
- BR3 logs output comparisons
- No user-visible behavior change unless explicitly enabled

### Stage 3: Opt-In Runtime Selection

- User can choose `runtime=codex` for selected commands or projects
- Claude remains default

### Stage 4: Production-Safe Codex Workflows

- Codex owns a defined subset of workflows reliably
- Cluster dispatch supports Codex end to end
- High-stakes reviews use the bounded Claude + Codex consensus loop with audit trail

### Stage 5: Full Dual-Runtime BR3

- BR3 can run the same orchestration layer on either runtime
- Runtime choice becomes a normal BR3 config decision rather than an experiment

## Risks and Controls

### Risk: Claude behavior gets disrupted during migration

Control:

- Keep Claude as default
- Introduce feature flags
- Route all Codex work through explicit opt-in or shadow mode first

### Risk: Policy behavior diverges between Claude and Codex

Control:

- Move critical policy into BR3-managed preflight/postflight
- Keep runtime-specific hooks secondary

### Risk: Dashboard becomes fragmented

Control:

- Keep one event server
- keep one state machine
- add runtime metadata instead of building a new dashboard

### Risk: Codex execution differs too much from Claude

Control:

- Standardize BR3 workflow ownership
- let runtime adapters differ internally
- avoid forcing one runtime to imitate the other exactly

### Risk: Migration becomes too broad

Control:

- Ship by command family
- prioritize review and planning first
- postpone autopilot and rich interactive flows

### Risk: Consensus Review Creates Friction

Control:

- Use bounded review loops, not infinite debate
- Keep advisory-only review surfaces separate from authoritative writers
- Allow explicit audited bypass for emergencies

## Initial Implementation Backlog

### Milestone 1

- Add runtime config and feature flags
- Define runtime adapter interface
- Wrap current Claude path in `ClaudeRuntime`

### Milestone 2

- Add runtime metadata to dashboard/state records
- Implement Codex adapter for review-only flows
- Connect existing Codex adversarial review logic into the shared runtime layer

### Milestone 3

- Build shared preflight/postflight pipeline
- Move BUILD/spec gating and protected-file enforcement into BR3-managed stages

### Milestone 4

- Port review and analysis commands to Codex
- Run shadow mode comparisons against Claude

### Milestone 5

- Port `/spec`
- validate output shape and approval flows

### Milestone 6

- Port bounded `/begin`
- keep sequential execution only at first

### Milestone 7

- Generalize cluster dispatch and sidecar for Codex
- enable runtime-aware remote execution

### Milestone 8

- Add consensus adversarial review for `/spec`, `/amend`, and new BUILD phases
- write tracking files
- enforce review presence before commit

## Final Recommendation

Treat this as an architecture extraction project first and a Codex migration second.

If BR3 becomes the true owner of orchestration, then Claude and Codex become interchangeable runtimes over time.

If BR3 stays dependent on Claude’s native runtime model, Codex will always feel bolted on.

The safest path is:

- preserve Claude
- add runtime abstraction
- centralize policy in BR3
- ship Codex in shadow mode first
- promote Codex by workflow, not by ideology
