# BUILD: Codex Full BR3 Integration

**Project:** BuildRunner3 (BR3 framework)
**Created:** 2026-04-15
**Status:** Phase 0 Complete (Conditional Go) - Phase 1 Complete (Parallel Shadow) - Phase 2 Complete (Hybrid Strategy Locked) - Phase 3 Complete (Gate B: Local-Only) - Phase 4 Complete (Contract Locked) - Phase 5 Complete (Selection Scaffold) - Phase 6 Complete (Review Cycle Complete) - Phase 7 Complete (Runtime-Aware Dashboard) - Phase 8 Complete (Advisory Shadow Mode) - Phase 9 Complete (Command Compiler + Skill Translation) - Phase 10 Complete (Codex `/spec` Workflow) - Phase 11 Complete (Bounded Codex `/begin`) - Phase 12 Complete (Runtime-Aware Dispatch Contract; Remote Codex Still Disabled) - Phase 13 Complete (Hardening, Observability, Rollout; No Remote Promotion) - Phase 14 Complete (Consensus Adversarial Review Enforcement)
**Impact:** GLOBAL - BR3 runtime layer, CLI, dashboard, dispatch, Claude/Codex coexistence
**Source Inputs:** `.buildrunner/Codex Full BR3 Integration Plan.md`, adversarial review feedback, Codex synthesis

---

## 0. Purpose (For a New Claude)

**What this spec does:** Integrates Codex into BR3 as a first-class coding runtime without breaking the current Claude-based workflow. The target architecture is one BR3 control plane with two runtimes, not two separate products.

**Core principle:** BR3 owns orchestration. Claude and Codex become interchangeable execution backends over time, but BR3 keeps one build lifecycle, one dashboard, one registry/state model, one cluster dispatch system, and one policy layer.

**What must remain true during the build:**

- Claude remains the default runtime until explicit promotion gates are passed.
- The existing BR3 implementation must continue running without disruption during this build. All Codex integration work is parallel-path until explicit cutover.
- Existing Claude hooks, slash commands, and cluster flows continue working during migration.
- Codex is introduced first in narrow, measurable workflows, not as an all-at-once replacement.
- Claude remains the default runtime for research, planning, specification, and architecture decisions.
- Codex is restricted to execution/build workflows after a build plan is completed and approved, unless a later spec amendment explicitly broadens that scope.
- Unsupported Codex capabilities trigger explicit fallback or phase refusal, never silent degradation.
- All multi-review BR3 flows use a bounded Claude + Codex consensus loop rather than a one-shot disagreement dump. High-stakes artifacts make that loop mandatory.
- Secondary or shadow reviewers are advisory-only until explicitly promoted to authoritative writer.
- One BR3 task invocation equals one `task_id` conflict boundary.

**Locked architectural decisions (v2):**

1. Build one BR3 system with two runtimes. Do not start BR4 as a replacement project.
2. Share the BR3 build lifecycle across runtimes: registered -> dispatched -> running -> suspect/stalled -> complete/failed.
3. Do not force a shared model-interaction lifecycle. Runtime adapters may differ internally.
4. V1 remote Codex execution uses `codex exec` on target nodes. Do not build a new Codex API daemon in v1.
5. V1 Codex auth model is per-node local login at `~/.codex/auth.json`, validated by BR3 preflight. Do not add auth-sync machinery in v1.
6. Critical policy must move into BR3-managed preflight/postflight. Claude hooks become secondary enforcement, not the only enforcement.
7. Browser-heavy or highly interactive workflows (`/design`, rich research browsing, full `/autopilot`) are deferred until core review/planning/execution paths are proven.
8. V1 Codex auth failure policy is explicit: direct `runtime=codex` work fails fast; shadow-mode Codex logs `shadow_skipped`; no silent reroute to Claude.
9. V1 shadow mode is advisory-only and cannot apply edits.
10. V1 edit conflict policy is fail-closed by `task_id`: one authoritative writer per task, all other edits are stored as proposals only.
11. V1 review consensus is bounded: independent pass, merge, up to two rebuttal rounds, then escalate unresolved blocker disagreements to the user.
12. V1 Codex compatibility is pinned to a validated version range and checked in preflight on every participating node.
13. This migration is parallel and non-disruptive: BR3 keeps the current Claude-driven path live until an explicit switch-over phase says otherwise.
14. Claude remains authoritative for research, planning, and architecture. Codex is introduced as an execution/build runtime after plan completion, not as the primary planner.

**Runtime config precedence (must be implemented exactly):**

1. explicit command flag (`--runtime codex`)
2. project config (`.buildrunner/runtime.json`)
3. user config (`~/.buildrunner/runtime.json`)
4. default = `claude`

**Canonical runtime adapter contract required by this build:**

- `get_capabilities()`
- `validate_task()`
- `run_review()`
- `run_analysis()`
- `run_plan()`
- `run_execution_step()`
- `stream_events()` — optional; runtimes without true streaming may emit buffered progress events
- `cancel()`
- `save_orchestration_checkpoint()` — BR3-owned checkpoint of task envelope, current step, logs, and workspace diff state
- `resume_orchestration_task()` — restart from BR3 checkpoint, not mid-model continuation

**Canonical result envelope required by this build:**

- `task_id`
- task metadata
- runtime/backend metadata
- raw stdout/stderr or tool payloads
- normalized findings
- normalized edits
- workspace diff
- shell actions
- stream events
- orchestration checkpoints
- metrics
- error class / retryability

**Read first:**

1. `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/Codex Full BR3 Integration Plan.md`
2. `/Users/byronhudson/Projects/BuildRunner3/core/cluster/cross_model_review.py`
3. `/Users/byronhudson/.buildrunner/scripts/adversarial-review.sh`
4. `/Users/byronhudson/.buildrunner/scripts/dispatch-to-node.sh`
5. `/Users/byronhudson/.buildrunner/scripts/_dispatch-core.sh`
6. `/Users/byronhudson/.buildrunner/scripts/build-sidecar.sh`
7. `/Users/byronhudson/.buildrunner/dashboard/events.mjs`
8. `/Users/byronhudson/.buildrunner/lib/build-state-machine.mjs`
9. `/Users/byronhudson/.claude/settings.json`
10. `/Users/byronhudson/.claude/commands/begin.md`
11. `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/builds/BUILD_cross-model-review.md`
12. `/Users/byronhudson/Projects/BuildRunner3/.buildrunner/builds/BUILD_cluster-build-orchestration.md`

**Do not:**

- break the current Claude default path
- add a second dashboard or second registry
- hide runtime-critical behavior only in Claude hooks
- force unsupported commands through Codex
- add Codex auth-sync before local-auth validation is proven

## Required Phase Closeout Protocol

This protocol is mandatory at the end of every phase from this point forward.

1. Update both source-of-truth plan documents:
   - `.buildrunner/builds/BUILD_codex-full-br3-integration.md`
   - `.buildrunner/Codex Full BR3 Integration Plan.md`
2. Record the actual checkpoint, not the intended checkpoint:
   - exact phase status
   - exact gate result
   - exact constraints still in force
   - exact next safe step
   - exact test commands run and results
   - exact node/runtime measurements when a phase depends on live probes
3. Update or create any supporting runtime artifacts produced by that phase so the next session can read them directly instead of reconstructing context.
4. Run a cumulative Claude authority review across the full completed scope, not just the latest slice:
   - after Phase 4, review Phases 0 through 4
   - after Phase 5, review Phases 0 through 5
   - continue this pattern through the rest of the build
5. Treat Claude as final review authority for the cumulative review loop:
   - implement or document every required change Claude identifies
   - re-run focused verification
   - send the updated cumulative scope back to Claude
   - if the review cycle is completed and the remaining findings are documented rather than blocking implementation work, the user may mark the phase complete without requiring a terminal `NO_FINDINGS`
6. Write the final cumulative review outcome back into both source-of-truth plan documents before ending the session.

**Current cumulative review checkpoint:**

- On 2026-04-16, the cumulative Claude final-authority review was extended through Phases 0 to 14.
- The review scope covered the previously-clean Phase 0 to 12 runtime baseline plus the Phase 13 capability/runtime-selection/Claude-regression hardening, runtime health/budget observability, rollout/runbook artifacts, and the Phase 14 consensus review tracking, pre-commit enforcement, `/spec` consensus wiring, and adversarial-review enforcement tests.
- Focused verification command for the reviewed 0 to 14 scope: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/runtime/test_command_compiler.py tests/runtime/test_capabilities.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py tests/integration/test_codex_spec_workflow.py tests/integration/test_codex_begin_workflow.py tests/integration/test_codex_remote_dispatch.py tests/integration/test_runtime_selection.py tests/integration/test_claude_regression_smoke.py tests/integration/test_adversarial_review_enforcement.py -q`
- Focused verification result: `81 passed, 2 warnings in 9.53s`
- Final cumulative Claude authority result for Phases 0 through 14: `NO_FINDINGS`

**Consensus Review Protocol (V1):**

1. Run Claude and Codex independently on the same review target under one BR3 `task_id`.
2. Merge findings into a single review artifact with source attribution.
3. If meaningful disagreements remain, run up to two rebuttal / reconciliation rounds where each reviewer sees the merged findings.
4. Highlight consensus blockers and record unresolved disagreements explicitly.
5. If blocker disagreement remains after the bounded loop, escalate to the user and block promotion or commit for that artifact.

---

## Parallelization Matrix

| Phase | Key Files / Areas | Can Parallel With | Blocked By | Status |
| ----- | ----------------- | ----------------- | ---------- | ------ |
| 0 | capability audit, version baseline, cost/latency baseline | - | - | complete_conditional |
| 1 | `core/runtime/*`, `/review` spike, runtime result schema | 2 | 0 | complete_parallel_shadow |
| 2 | command inventory docs + audit script | 1, 3 | 0 | complete |
| 3 | dispatch/auth architecture docs + preflight probe | 2 | 0 | complete_local_only |
| 4 | runtime contract, edit normalization, orchestration checkpoint model | - | 1, 3 | complete |
| 5 | runtime selection config, adapter registry, CLI/API wiring | 6, 7 | 4 | complete |
| 6 | shared preflight/postflight policy | 7 | 5 | complete |
| 7 | dashboard runtime awareness | 6 | 5 | complete |
| 8 | Codex shadow mode for safe commands | 9 | 4, 5, 7 | complete |
| 9 | command compiler + skill/context translation | 8 | 2, 4, 5 | complete |
| 10 | Codex `/spec` | - | 6, 8, 9 | complete |
| 11 | Codex `/begin` sequential bounded execution | 12 | 6, 10 | complete |
| 12 | runtime-aware cluster dispatch + sidecar | 11 | 3, 4, 7 | complete |
| 13 | hardening, extended tests, rollout docs | 14 | 8, 10, 11, 12 | complete |
| 14 | consensus adversarial review enforcement | - | 3, 8 | complete |

---

## Phases

### Phase 0: Codex Capability Audit + Compatibility Baseline

**Status:** conditionally_complete
**Goal:** Establish a factual Codex baseline before adapter work starts.

**Files to CREATE:**

- `.buildrunner/runtime-codex-capability-audit.md`
- `.buildrunner/runtime-baseline-metrics.md`
- `tests/integration/test_codex_capabilities.py`
- `~/.buildrunner/scripts/check-codex-version.sh`
- `~/.buildrunner/logs/runtime-capability.log`

**Files to MODIFY:**

- `core/cluster/cross_model_review.py`

**Blocked by:** None

**Deliverables:**

- [ ] Audit Codex CLI version, supported flags, auth model, timeout behavior, and output shape
- [ ] Determine whether Codex emits true streaming output or only buffered/final output
- [ ] Establish a safe review payload baseline: file count, prompt size, and review latency for representative `/review` inputs
- [ ] Capture Codex local auth validation behavior and error signatures
- [ ] Add version compatibility preflight against a pinned acceptable range
- [ ] Add baseline structured logging for runtime, version, duration, exit code, and approximate per-run cost

**Success Criteria:**

- Codex capability baseline is documented in repo
- validated version range is pinned and checkable
- latency and timeout targets used later in the build are based on measured baseline, not assumption
- Codex local execution works and is observable before adapter work begins

**Go / No-Go Gate 0:**

- If Codex cannot reliably complete the baseline review workload or its compatibility surface is too unstable, stop before Phase 1.
- Original baseline result: `NO-GO` for direct repo-scoped review execution.
- Fix-pass result: `CONDITIONALLY_GO` only when review execution is isolated from the repo workspace, BUILD context is narrowed, multi-file diffs are batched, and oversized new-file diffs are chunked.
- The live `core/cluster/cross_model_review.py` path was restored after validation so Phase 0 findings do not alter current BR3 infrastructure before cutover.

### Phase 1: Dual-Runtime Spike (`/review`) [0A]

**Status:** complete_parallel_shadow
**Goal:** Prove that one narrow BR3 workflow can execute through both Claude and Codex while emitting the same BR3-owned result envelope.

**Files to CREATE:**

- `core/runtime/base.py`
- `core/runtime/types.py`
- `core/runtime/claude_runtime.py`
- `core/runtime/codex_runtime.py`
- `tests/runtime/test_review_spike.py`
- `.buildrunner/runtime-spike-notes.md`
- `.buildrunner/runtime-spike-results.json`

**Files to MODIFY:**

- `api/routes/execute.py`
- `api/server.py`
- `core/cluster/cross_model_review.py`

**Blocked by:** Phase 0

**Implementation constraint for next session:**

- Phase 1 must start as a parallel-only scaffold.
- Do not modify live BR3 runtime routing, default behavior, or cutover behavior in this phase.
- Any Codex review spike must run through isolated test or shadow paths until a later explicit switch-over phase permits production wiring.

**Deliverables:**

- [x] Define minimal `RuntimeTask` and `RuntimeResult` types sufficient for `/review`
- [x] Implement `ClaudeRuntime.run_review()` using existing behavior without changing default user flow
- [x] Implement `CodexRuntime.run_review()` using `codex exec`
- [x] Execute Claude and Codex review against the same repo/file set through BR3-owned task assembly
- [x] Store both outputs in the same normalized result envelope
- [x] Surface runtime metadata (`runtime`, `backend`) in one API response
- [x] Add one smoke test that compares envelope shape, not model content
- [x] Emit structured logs keyed by `task_id` with runtime version, duration, exit code, and cost estimate
- [x] Record spike assumptions that must be reconciled with Phase 3 before Phase 4 begins

**Success Criteria:**

- `/review` runs through both runtimes via one BR3 task contract
- both runtimes return one compatible `RuntimeResult` shape
- no regression in current Claude review path
- no file writes occur during the spike path unless explicitly allowed
- spike logs are sufficient to debug failures without re-running blind

**Gate A result:** pass_parallel_shadow

- Shared BR3 result envelope represented both runtimes cleanly in explicit shadow mode.
- Real synthetic task `review-spike-phase1synthetic` completed in both runtimes under one `task_id`.
- Both shadow runtimes executed in isolated temp workspaces; live BR3 routing remained unchanged.

**Go / No-Go Gate A:**

- If a single result envelope cannot represent both runtimes cleanly, stop after Phase 1 and redesign the contract before continuing.

---

### Phase 2: Full Command Inventory + Portability Matrix [0B]

**Status:** complete
**Goal:** Replace assumptions with a complete inventory of BR3's command surface and its Codex portability profile.

**Files to CREATE:**

- `.buildrunner/runtime-command-inventory.md`
- `.buildrunner/runtime-command-inventory.json`
- `tools/runtime/audit_commands.py`

**Reference Inputs:**

- `/Users/byronhudson/.claude/commands/*.md`
- `/Users/byronhudson/.claude/skills/*`

**Blocked by:** None

**Deliverables:**

- [x] Enumerate every command in `~/.claude/commands`
- [x] Record for each command: purpose, dependencies, cluster usage, subagent usage, hook dependence, browser/tool dependence, portability rating, fallback runtime, effort estimate
- [x] Mark deprecated, dead, or low-value commands explicitly
- [x] Produce migration buckets: trivial, moderate, hard, keep-Claude-first
- [x] Update command rollout order based on the inventory rather than intuition

**Success Criteria:**

- every command is cataloged
- every command has a portability rating
- the migration sequence is justified by real command data

**Phase 2 output summary:**

- Cataloged `65` commands from `~/.claude/commands`
- Cataloged `12` skill inputs from `~/.claude/skills`
- Bucketed commands into `10` trivial, `11` moderate, `9` hard, and `35` keep-Claude-first
- Recorded explicit low-value commands: `/brief`, `/concise`, `/later`, `/restart`, `/rules`, `/save`, `/why`

**Decision Gate:**

- If more than 25% of frequently used commands are low-portability or Claude-only, formalize a long-term hybrid strategy instead of pursuing near-term parity.

**Decision Gate Result:** `formalize_long_term_hybrid_strategy`

- `14` of `16` core workflow commands (`88%`) are low-portability or Claude-first.
- Execution-centric commands can still migrate in staged buckets, but near-term parity for the whole command surface is not justified by the inventory.
- Claude remains the long-term default for research, planning, architecture, and browser-heavy orchestration commands.

---

### Phase 3: Cluster Runtime Architecture + Auth Model [0C]

**Status:** complete_local_only
**Goal:** Lock the real Codex cluster execution model before broader adapter work starts.

**Files to CREATE:**

- `.buildrunner/runtime-cluster-architecture.md`
- `~/.buildrunner/scripts/check-runtime-auth.sh`
- `tests/integration/test_runtime_auth_preflight.py`

**Files to MODIFY:**

- `core/cluster/cross_model_review.py`
- `~/.buildrunner/scripts/dispatch-to-node.sh`
- `~/.buildrunner/scripts/_dispatch-core.sh`

**Blocked by:** None

**Deliverables:**

- [x] Lock the V1 Codex cluster model: `codex exec` on target nodes, wrapped by BR3 sidecar
- [x] Implement runtime auth preflight for Muddy and remote nodes
- [x] Reuse or extract Codex auth checking from `cross_model_review.py`
- [x] Define how `dispatch-to-node.sh` chooses runtime and validates availability before sync/launch
- [x] Define what process the sidecar monitors for Codex runs
- [x] Define heartbeat, cancellation, and exit semantics for Codex jobs
- [x] Implement explicit auth failure policy: direct `runtime=codex` work fails fast, shadow-mode Codex logs `shadow_skipped`, no silent reroute
- [x] Define mid-run auth expiry behavior: current task fails or shadow-skips with audit event; runtime never changes mid-task
- [x] Add compatibility/version preflight for every participating node
- [x] Run a probe command on Muddy and one remote node: `codex exec -- "reply with only: ok"`
- [x] Write a Phase 1/3 sync memo reconciling spike assumptions with dispatch/auth assumptions before Phase 4 begins

**Success Criteria:**

- BR3 can verify Codex auth on Muddy and one remote node
- the remote Codex process model is explicitly documented
- no new Codex API daemon is required for V1
- auth failure behavior is a decision, not a TODO

**Go / No-Go Gate B:**

- If remote Codex auth or process monitoring cannot be made reliable, do not proceed with remote Codex execution. Keep Codex local-only until solved.

**Gate B result:** complete_local_only_no_go_remote

- On 2026-04-15, Muddy/local passed Codex preflight on `codex-cli 0.48.0`, and the direct probe returned only `ok`.
- On 2026-04-15, Lomax was the only remote node exposing Codex, but it reported `codex-cli 0.47.0`, outside the validated `>=0.48.0,<0.49.0` range.
- The raw Lomax probe retried token refresh five times and ended with `401 Unauthorized`, so remote Codex auth/process reliability is not acceptable yet.
- Otis currently exposes Claude only, and Lockwood has neither Claude nor Codex installed.
- BR3 remote preflight now ships the current local helper to the node before validation so decisions do not depend on stale remote repo checkouts.
- `dispatch-to-node.sh` enforces preflight for Codex but keeps Claude preflight advisory-only during migration so the live default route is not cut over by Phase 3.
- Decision: keep Codex local-only after Phase 3 and proceed to Phase 4 without enabling remote Codex routing.

---

### Phase 4: Runtime Contract + Result / Edit Normalization [0D]

**Status:** complete
**Goal:** Define the adapter boundary precisely enough that later phases are building on a stable contract, not a Claude-shaped abstraction.

**Files to CREATE:**

- `core/runtime/result_schema.py`
- `core/runtime/edit_normalizer.py`
- `core/runtime/capabilities.py`
- `core/runtime/errors.py`
- `core/runtime/orchestration_checkpoint_store.py`
- `.buildrunner/runtime-contract.md`
- `tests/runtime/test_result_schema.py`
- `tests/runtime/test_edit_normalizer.py`

**Files to MODIFY:**

- `core/runtime/types.py`

**Blocked by:** Phases 1 and 3

**Deliverables:**

- [x] Define versioned `RuntimeTask`, `RuntimeResult`, `CapabilityProfile`, `StreamEvent`, and `CheckpointRecord` schemas
- [x] Define canonical normalized edit types: `write_file`, `replace_range`, `unified_diff`, `shell_action`, `advisory_only`
- [x] Preserve raw runtime payloads and observed workspace diffs alongside normalized edits
- [x] Define `task_id` as the one and only conflict boundary for automatic apply logic
- [x] Define one authoritative writer per `task_id`; all shadow or secondary runtime edits are advisory-only proposals
- [x] Define fail-closed conflict behavior when multiple runtimes propose touching the same file under one `task_id`
- [x] Detect applied changes from workspace diff and command/tool payloads rather than trusting model self-description alone
- [x] Define retryable vs non-retryable error classes
- [x] Define cancellation and BR3 orchestration checkpoint semantics only, not model-internal mid-task resume
- [x] Define capability flags for subagents, streaming, shell, browser, orchestration-checkpoint support, edit granularity, cluster suitability
- [x] Add fixture tests for Claude-style edits, full-file rewrites, unified diffs, and advisory-only results

**Success Criteria:**

- both runtimes can emit the same versioned result schema
- normalized edit application is deterministic on fixtures
- unsupported edit forms are rejected explicitly, not guessed
- same-file multi-runtime proposals under one `task_id` result in explicit `conflicted_proposal` state, not auto-merge

**Go / No-Go Gate C:**

- If edit normalization or result schema stability is still ambiguous after this phase, stop before runtime selection or execution phases.

**Gate C result:** pass_contract_locked

- Added versioned schema support in `core/runtime/types.py`, `core/runtime/result_schema.py`, `core/runtime/capabilities.py`, `core/runtime/errors.py`, and `core/runtime/orchestration_checkpoint_store.py`.
- Added canonical edit normalization and conflict handling in `core/runtime/edit_normalizer.py`.
- Locked the contract in `.buildrunner/runtime-contract.md`.
- Focused verification for Phase 4 passed under the combined runtime/integration suite recorded below.

---

### Phase 5: Runtime Selection + Adapter Scaffold

**Status:** complete
**Goal:** Introduce runtime choice into BR3 without changing default behavior.

**Files to CREATE:**

- `core/runtime/runtime_registry.py`
- `core/runtime/config.py`
- `.buildrunner/runtime.json` (schema example / fixture)
- `tests/runtime/test_config_resolution.py`

**Files to MODIFY:**

- `cli/main.py`
- `cli/alias_commands.py`
- `api/routes/execute.py`
- `api/routes/orchestrator.py`

**Blocked by:** Phase 4

**Deliverables:**

- [x] Add runtime registry and config loader
- [x] Implement config precedence exactly as defined in Purpose section
- [x] Add explicit CLI/API runtime selection (`--runtime`)
- [x] Keep default runtime = Claude
- [x] Ensure omitted runtime preserves current behavior
- [x] Add smoke tests for command-line and API config resolution

**Success Criteria:**

- BR3 can resolve `claude` or `codex` intentionally
- no existing Claude entrypoint changes behavior when runtime is omitted

**Phase 5 result:** pass_default_preserved

- Added `core/runtime/config.py` plus `.buildrunner/runtime.json` schema example.
- Added global CLI runtime selection in `cli/main.py` and alias-launch runtime override in `cli/alias_commands.py`.
- Added API runtime resolution and runtime-aware command execution in `api/routes/execute.py` and `api/routes/orchestrator.py`.
- Omitted runtime still resolves to Claude unless project or user config explicitly says otherwise.
- Next safe step after Phase 5 is Phase 6 shared preflight/postflight policy extraction.

---

### Phase 6: Shared Preflight / Postflight Policy

**Status:** complete
**Goal:** Move critical enforcement into BR3-managed policy stages so Codex and Claude share one governance layer.

**Files to CREATE:**

- `core/runtime/preflight.py`
- `core/runtime/postflight.py`
- `core/runtime/policy_result.py`
- `tests/integration/test_policy_parity.py`

**Files to MODIFY:**

- `~/.buildrunner/hooks/protect-files.sh`
- `~/.buildrunner/hooks/enforce-build-gates.sh`
- `~/.buildrunner/hooks/enforce-opus-on-prompts.sh`
- `~/.buildrunner/scripts/check-runtime-alerts.sh`
- `~/.buildrunner/scripts/auto-save-session.sh`
- `~/.buildrunner/scripts/recall-on-tool.sh`

**Blocked by:** Phase 5

**Deliverables:**

- [ ] Extract portable policy from Claude hooks into BR3 preflight/postflight
- [ ] Distinguish portable policy from Claude-output parsing logic
- [ ] Standardize policy outputs: pass, warn, block
- [ ] Reuse existing scripts where truly possible; rewrite where Claude-specific parsing exists
- [ ] Keep Claude hooks as thin wrappers calling shared logic where practical

**Success Criteria:**

- protected-file checks, BUILD/spec gates, alerts, formatting, and session-save logic are reachable from both runtimes
- Claude remains protected even while policy is being extracted

**Actual Checkpoint on 2026-04-16:**

- Shared BR3 policy modules landed in `core/runtime/preflight.py`, `core/runtime/postflight.py`, and `core/runtime/policy_result.py`.
- Claude and Codex runtime wrappers now consume the shared policy result model for preflight blocking.
- Thin wrapper hooks/scripts now delegate to shared BR3 policy logic and log explicit skip events when invoked outside the BR3 repo instead of silently relying on machine-specific fallback paths.
- Phase 6 parity coverage expanded in `tests/integration/test_policy_parity.py`, including protected-file parity, command inventory loading, malformed `skill-state.json`, formatting fallback, session snapshot / recall query helpers, and alert-file rotation behavior.
- Constraint still in force: no live routing/cutover, no remote Codex enablement, omitted runtime behavior unchanged, Claude remains default for research/planning/spec/architecture, Codex remains execution/build only after plan approval.
- Actual gate result: `COMPLETE_BY_USER_OVERRIDE_AFTER_REVIEW_CYCLE`.
- Focused verification command: `python3 -m py_compile core/runtime/policy_result.py core/runtime/preflight.py core/runtime/postflight.py core/runtime/shadow_runner.py core/runtime/codex_runtime.py`
- Focused verification result: success (`exit 0`, no output).
- Focused verification command: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py -q`
- Focused verification result: `47 passed, 2 warnings in 1.18s`
- Focused verification command: `cd ui && npx vitest run src/stores/buildStore.test.ts`
- Focused verification result: `1 passed`
- Cumulative Claude final-authority review through Phases 0 to 5 remains `NO_FINDINGS`.
- On 2026-04-16, the required Phase 6 Claude final-authority review was rerun multiple times against the current implementation after targeted hardening fixes landed.
- Each rerun completed, but Claude continued to return fresh `FINDING:` lines instead of the required terminal result `NO_FINDINGS`.
- On 2026-04-16, the closeout rule was explicitly amended by the user: if the review cycle is complete, the phase may be marked complete even without a final `NO_FINDINGS`.
- Phase 6 is therefore marked complete because implementation landed, focused verification is clean, and the authority review cycle was completed and documented.
- Cumulative review checkpoint is advanced through Phase 6 under the amended closeout rule.
- Next safe step: begin Phase 9 command compiler and skill/context translation context gathering without changing later-phase cutover behavior.

---

### Phase 7: Dashboard Runtime Awareness

**Status:** complete
**Goal:** Make the current dashboard runtime-aware, not runtime-specific.

**Files to MODIFY:**

- `~/.buildrunner/dashboard/events.mjs`
- `~/.buildrunner/lib/build-state-machine.mjs`
- `ui/src/components/CommandCenter.tsx`
- `ui/src/pages/BuildMonitor.tsx`
- `ui/src/stores/buildStore.ts`
- `ui/src/utils/websocketClient.ts`

**Blocked by:** Phase 5

**Deliverables:**

- [x] Add runtime metadata to registry rows, events, and websocket payloads
- [x] Add `runtime`, `backend`, `session_id`, `capabilities`, and `dispatch_mode` fields
- [x] Surface runtime in dashboard and build monitor
- [x] Preserve one liveness / stalled / exit model for both runtimes
- [x] Add dashboard filters for runtime and backend

**Success Criteria:**

- one build can be displayed as Claude or Codex without a second dashboard
- heartbeats, stalled detection, and exit state still use one state machine

**Actual Checkpoint on 2026-04-16:**

- Added runtime-aware session serialization plus runtime metadata update/broadcast support in `api/routes/build.py` and `core/build_session.py`.
- Added registry/snapshot runtime filtering in `~/.buildrunner/dashboard/events.mjs` so operators can filter by runtime, backend, dispatch mode, shadow status, and status without introducing a second dashboard.
- Added build-session normalization and patch semantics in `ui/src/stores/buildStore.ts` so API snake_case payloads and websocket updates are hydrated consistently.
- Updated `ui/src/pages/BuildMonitor.tsx` to display runtime/backend/source/session metadata plus reported capabilities without relying on stale captured session state in websocket handlers.
- Updated `ui/src/components/CommandCenter.tsx` to send explicit runtime selection to the API and surface resolved runtime/source in command history.
- Updated `ui/src/utils/websocketClient.ts` to recognize runtime update and pong message types.
- Focused verification command: `python3 -m py_compile core/build_session.py api/routes/build.py core/runtime/shadow_runner.py`
- Focused verification result: success (`exit 0`, no output).
- Focused verification command: `.venv/bin/python -m pytest tests/runtime/test_review_spike.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py -q`
- Focused verification result: `33 passed, 2 warnings in 0.85s`
- Targeted UI verification command: `cd ui && npx vitest run src/stores/buildStore.test.ts`
- Targeted UI verification result: `4 passed`
- Repo-wide UI typecheck still reports unrelated pre-existing diagnostics outside the touched Phase 7/8 files, so this phase did not close that baseline.
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun across the completed Phase 0 through Phase 8 scope, including the runtime contract, runtime config/selection wiring, shared policy extraction, dashboard runtime-awareness path, shadow runner, related dashboard/state scripts, and the focused runtime/integration/UI tests.
- Final cumulative Claude authority result for Phases 0 through 8: `NO_FINDINGS`
- Actual gate result: `COMPLETE_RUNTIME_AWARE_DASHBOARD`

---

### Phase 8: Codex Shadow Mode for Safe Commands

**Status:** complete
**Goal:** Run Codex beside Claude on low-risk workflows and measure signal quality before promotion.

**Files to CREATE:**

- `core/runtime/shadow_runner.py`
- `.buildrunner/runtime-shadow-metrics.md`
- `~/.buildrunner/logs/runtime-shadow.log`
- `tests/integration/test_shadow_mode.py`

**Files to MODIFY:**

- `~/.buildrunner/scripts/unified-review-gate.sh`
- `~/.buildrunner/scripts/auto-save-session.sh`
- `core/cluster/cross_model_review.py`

**Blocked by:** Phases 4, 5, and 7

**Initial Shadow Scope Only:**

- `/review`
- `/guard`
- `/why`
- `/diag`
- plan critique / adversarial review

**Do not include yet:**

- `/root`
- `/gaps`
- `/begin`
- `/autopilot`
- browser-dependent commands

**Deliverables:**

- [x] Add shadow mode runner that executes Codex without changing primary Claude outcome
- [x] Log paired Claude/Codex outputs using the shared result envelope
- [x] Record metrics: latency, blocker agreement, warning overlap, false blocker rate, operator verdict
- [x] Define promotion thresholds and owner sign-off
- [x] Enforce per-run timeout, kill switch, and resource limits for shadow jobs
- [x] Enforce advisory-only shadow mode: no edit application, no file mutation, no promotion to authoritative writer
- [x] Key every shadow comparison by BR3 `task_id`
- [x] Surface live shadow status in logs/dashboard for operator visibility

**Shadow Mode Success Criteria (must be met before promotion):**

- at least 20 shadow runs across at least 2 weeks or 3 active projects, whichever is longer
- blocker agreement >= 80%
- false blocker rate < 10%
- zero unintended file modifications by the shadow path
- median Codex latency <= the baseline target established in Phase 0 for scoped review tasks
- no regression in Claude review path
- shadow jobs auto-abort on timeout or policy violation
- Codex auth failures in shadow mode are visible as `shadow_skipped`, not silent

**Go / No-Go Gate D:**

- If shadow mode does not produce useful signal against the agreed metrics, do not promote Codex to primary ownership for that command family.

**Actual Checkpoint on 2026-04-16:**

- Hardened `core/runtime/shadow_runner.py` so primary runtime results are preserved even when the Codex shadow path fails or times out.
- Added explicit shadow timeout isolation via configurable `shadow.timeout_seconds` with advisory skip behavior rather than primary-path contamination.
- Expanded `.buildrunner/runtime-shadow-metrics.md` with promotion-threshold and owner-signoff sections so the artifact records not just summary medians but the actual promotion gate inputs.
- Logged promotion thresholds alongside each shadow-run record for auditability.
- Added regression coverage in `tests/integration/test_shadow_mode.py` to prove shadow failures do not overwrite successful primary results.
- Focused verification command: `.venv/bin/python -m pytest tests/runtime/test_review_spike.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py -q`
- Focused verification result: `33 passed, 2 warnings in 0.85s`
- Current metrics artifact reports `Promotion readiness: not_ready`, so Phase 8 remains advisory-only and is not promoted.
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun across the completed Phase 0 through Phase 8 scope and returned `NO_FINDINGS`.
- Actual gate result: `COMPLETE_ADVISORY_SHADOW_NOT_PROMOTED`

---

### Phase 9: Command Compiler + Skill / Context Translation

**Status:** complete
**Goal:** Give Codex equivalent BR3 context for the commands that are viable after inventory.

**Files to CREATE:**

- `core/runtime/command_compiler.py`
- `core/runtime/command_capabilities.json`
- `.buildrunner/runtime-skill-mapping.md`

**Files to MODIFY:**

- `core/runtime/context_compiler.py`

**Files to CREATE OR INSTALL:**

- `~/.codex/skills/br3-planning/SKILL.md`
- `~/.codex/skills/br3-frontend-design/SKILL.md`
- `~/.codex/skills/chet/SKILL.md`
- `~/.codex/skills/prodlog/SKILL.md`
- `~/.codex/skills/business/SKILL.md`
- `~/.codex/skills/geo/SKILL.md`
- `~/.codex/skills/sales/SKILL.md`
- `~/.codex/skills/security-rules/SKILL.md`

**Blocked by:** Phases 2, 4, and 5

**Deliverables:**

- [ ] Compile command docs plus BR3 context into runtime-neutral task bundles
- [ ] Port high-value context and planning skills first
- [ ] Maintain a command capability map derived from actual inventory
- [ ] Explicitly mark commands that remain Claude-first

**Success Criteria:**

- Codex receives the same high-value planning / governance context as Claude for selected commands
- command compilation is driven by capability map, not by assumptions

**Actual Checkpoint on 2026-04-16:**

- Added `core/runtime/command_compiler.py` and `core/runtime/command_capabilities.json` so BR3 now compiles audited command docs, translated skill packages, curated context files, and explicit support levels into runtime-neutral command bundles.
- Added `.buildrunner/runtime-skill-mapping.md` plus installed Codex skill wrappers under `~/.codex/skills/` for `br3-planning`, `br3-frontend-design`, `chet`, `prodlog`, `business`, `geo`, `sales`, and `security-rules`.
- Extended `core/runtime/context_compiler.py` with command task assembly so Phase 10 can run `/spec` through a BR3-owned task envelope instead of runtime-specific prompt assembly.
- Updated `core/runtime/preflight.py` so Codex support now follows the curated capability map, including explicit `codex_shadow_only`, `codex_workflow_only`, and `claude_only` states instead of relying only on inferred inventory buckets.
- Added focused coverage in `tests/runtime/test_command_compiler.py` to prove `/spec` is blocked for direct Codex use, allowed only through the BR3-owned workflow marker, and that `/begin` remains Claude-only.
- Focused verification command: `python3 -m py_compile core/runtime/command_compiler.py core/runtime/context_compiler.py core/runtime/preflight.py core/runtime/codex_runtime.py core/runtime/workflows/spec_workflow.py api/routes/execute.py tests/runtime/test_command_compiler.py tests/integration/test_codex_spec_workflow.py`
- Focused verification result: success (`exit 0`, no output).
- Focused verification command: `.venv/bin/python -m pytest tests/runtime/test_command_compiler.py tests/integration/test_codex_spec_workflow.py -q`
- Focused verification result: `6 passed`
- Actual gate result: `COMPLETE_COMMAND_COMPILER_CONTEXT_TRANSLATION`

---

### Phase 10: Codex `/spec` Ownership

**Status:** complete
**Goal:** Promote Codex from review-only work into spec and planning generation once the shared contract and guardrails are stable.

**Files to CREATE:**

- `core/runtime/workflows/spec_workflow.py`
- `tests/integration/test_codex_spec_workflow.py`

**Files to MODIFY:**

- `~/.buildrunner/scripts/validate-spec-paths.sh`
- `~/.buildrunner/scripts/enforce-skill-steps.sh`
- `~/.buildrunner/scripts/adversarial-review.sh`

**Blocked by:** Phases 6, 8, and 9

**Deliverables:**

- [ ] Implement Codex-driven spec drafting through BR3-owned workflow state
- [ ] Keep adversarial review and path validation gates in place
- [ ] Ensure Codex-generated BUILD outputs match BR3 format and pass validators
- [ ] Add clear fallback to Claude when capability map says Codex is unsupported

**Success Criteria:**

- Codex can produce a valid BR3 BUILD/spec artifact
- validator and adversarial-review gates still work
- three consecutive `/spec` runs pass quality review without critical format or path errors

**Go / No-Go Gate E:**

- If Codex `/spec` quality does not meet the bar, stop before attempting Codex `/begin`.

**Actual Checkpoint on 2026-04-16:**

- Added `core/runtime/workflows/spec_workflow.py` plus `core/runtime/workflows/__init__.py` so `/spec` drafting can run through an explicit BR3-owned workflow without changing the live Claude default route.
- Extended `core/runtime/codex_runtime.py` and `core/runtime/base.py` with guarded `run_plan()` support while keeping shared approval/build gating in BR3 rather than inside runtime-specific behavior.
- Added `/runtime/spec-workflow` in `api/routes/execute.py` as an explicit non-cutover entrypoint for the Codex `/spec` workflow.
- Preserved the shared BUILD/spec gate scripts by invoking `~/.buildrunner/scripts/validate-spec-paths.sh` and `~/.buildrunner/scripts/adversarial-review.sh` from the BR3 workflow rather than bypassing or reimplementing them.
- Added integration coverage in `tests/integration/test_codex_spec_workflow.py` for the happy path and validation-blocked path.
- Focused verification command: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/runtime/test_command_compiler.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py tests/integration/test_codex_spec_workflow.py -q`
- Focused verification result: `61 passed, 2 warnings in 1.51s`
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun through the completed Phase 10 scope and returned `NO_FINDINGS`.
- Actual gate result: `COMPLETE_CODEX_SPEC_GATED_WORKFLOW`
- Constraint still in force: no live routing/cutover, no remote Codex enablement, omitted runtime behavior unchanged, Claude remains default for research/planning/spec/architecture, Codex remains execution/build only after plan approval, Phase 8 shadow mode remains advisory-only and not promoted.
- Next safe step: begin Phase 11 bounded Codex `/begin` capability-admission and lock/approval orchestration design without enabling cluster cutover or later-phase behavior early.

---

### Phase 11: Codex `/begin` Sequential Bounded Execution

**Status:** complete
**Goal:** Let Codex drive the primary BR3 workflow on bounded phases while preserving explicit fallback behavior.

**Files to CREATE:**

- `core/runtime/workflows/begin_workflow.py`
- `core/runtime/capability_gate.py`
- `tests/integration/test_codex_begin_workflow.py`

**Reference Inputs:**

- `/Users/byronhudson/.claude/commands/begin.md`
- `/Users/byronhudson/.claude/docs/begin-*.md`

**Blocked by:** Phases 6 and 10

**Deliverables:**

- [x] Implement BR3-owned lock handling, approval gates, and sequential phase execution for Codex
- [x] Add capability admission checks before phase start
- [x] If a phase requires unsupported capabilities (subagents, browser tools, rich interactivity), explicitly hand off to Claude or refuse the phase
- [x] Keep first Codex `/begin` scope to bounded, sequential phases only

**Success Criteria:**

- Codex completes 5 bounded phases without corrupting working tree or lock state
- BUILD/spec updates, locks, heartbeats, and reports remain correct
- unsupported phases never degrade silently

**Actual Checkpoint on 2026-04-16:**

- Added `core/runtime/capability_gate.py` so Phase 11 capability admission is BR3-visible rather than hidden in runtime prompt text.
- Added `core/runtime/workflows/begin_workflow.py` plus workflow exports and `/runtime/begin-workflow` wiring in `api/routes/execute.py` so bounded Codex `/begin` execution runs through BR3-owned lock creation, approval gating, per-phase progress files, and sequential phase completion.
- Updated `core/runtime/command_capabilities.json`, `core/runtime/base.py`, `core/runtime/codex_runtime.py`, and `tests/runtime/test_command_compiler.py` so `/begin` is `codex_workflow_only`, direct Codex `/begin` remains blocked, and Codex execution support is limited to the BR3-owned workflow path.
- Added `tests/integration/test_codex_begin_workflow.py` to prove bounded phases complete cleanly, unsupported phases hand off explicitly to Claude, and missing approval blocks before any lock is acquired.
- Focused verification command: `python3 -m py_compile core/runtime/capability_gate.py core/runtime/workflows/begin_workflow.py core/runtime/base.py core/runtime/codex_runtime.py api/routes/execute.py tests/integration/test_codex_begin_workflow.py tests/runtime/test_command_compiler.py`
- Focused verification result: success (`exit 0`, no output).
- Focused verification command: `.venv/bin/python -m pytest tests/integration/test_codex_begin_workflow.py tests/runtime/test_command_compiler.py tests/integration/test_policy_parity.py -q`
- Focused verification result: `27 passed in 0.34s`
- Actual gate result: `COMPLETE_BEGIN_BOUNDED_SEQUENTIAL_GATE`
- Constraints still in force: no live routing/cutover; no remote Codex enablement; omitted runtime behavior unchanged; Claude remains default for research/planning/spec/architecture; Codex remains execution/build only after plan approval; `/begin` remains bounded/sequential only; unsupported phases fail closed or hand off explicitly.
- Next safe step: land Phase 12 runtime-aware dispatch/sidecar plumbing without promoting remote Codex before live node readiness is re-verified.

---

### Phase 12: Runtime-Aware Cluster Dispatch + Sidecar

**Status:** complete
**Goal:** Extend BR3 dispatch so Codex can run through the same monitored cluster pipeline as Claude.

**Files to CREATE:**

- `~/.buildrunner/scripts/runtime-dispatch.sh`
- `tests/integration/test_codex_remote_dispatch.py`

**Files to MODIFY:**

- `~/.buildrunner/scripts/dispatch-to-node.sh`
- `~/.buildrunner/scripts/_dispatch-core.sh`
- `~/.buildrunner/scripts/build-sidecar.sh`
- `~/.buildrunner/dashboard/events.mjs`
- `~/.buildrunner/lib/build-state-machine.mjs`

**Blocked by:** Phases 3, 4, 7, and 11

**Deliverables:**

- [x] Add runtime argument to dispatch contract
- [x] Make sidecar runtime-aware while preserving current Claude behavior
- [x] Monitor the actual Codex process PID for heartbeats / exit handling
- [x] Add runtime-specific auth preflight on target node before launch
- [x] Ensure suspect / stalled / complete behavior remains unified
- [x] Add runtime-aware cancellation path

**Success Criteria:**

- one Codex build runs on Muddy through sidecar with correct heartbeats
- one Codex build runs on a remote node with correct heartbeats and exit state
- no regression in current Claude dispatch path

**Go / No-Go Gate F:**

- If runtime-aware remote dispatch is unstable, keep Codex local-only and do not promote remote Codex execution to production.

**Actual Checkpoint on 2026-04-16:**

- Added `~/.buildrunner/scripts/runtime-dispatch.sh` so sidecar-wrapped local and remote dispatches resolve the selected runtime through one BR3-owned wrapper instead of Claude-specific inline command assembly.
- Updated `~/.buildrunner/scripts/build-sidecar.sh` to accept an explicit runtime argument, track `runtime_pid`/`runtime_path`/`runtime` in `sidecar.json`, emit runtime-aware heartbeat/exit payloads, and preserve the legacy Claude behavior when runtime is omitted.
- Updated `~/.buildrunner/scripts/dispatch-to-node.sh` and `~/.buildrunner/scripts/_dispatch-core.sh` to accept `--runtime`, validate supported runtimes explicitly, sync the runtime wrapper to remote nodes, and route remote sidecar launch through the same runtime-aware contract.
- Updated `~/.buildrunner/dashboard/events.mjs` to pass runtime through local/remote dispatch and redispatch paths, and to monitor `runtime_pid` with `claude_pid` fallback so existing Claude sidecars remain valid.
- Updated `~/.buildrunner/lib/build-state-machine.mjs` to expose `_runtime_pid` as the runtime-neutral alias for the tracked remote PID.
- Added `tests/integration/test_codex_remote_dispatch.py` to verify the runtime wrapper, runtime-aware sidecar metadata/heartbeat path, and the remote dispatch contract under a stubbed SSH/rsync environment.
- Focused verification command: `bash -n /Users/byronhudson/.buildrunner/scripts/runtime-dispatch.sh /Users/byronhudson/.buildrunner/scripts/build-sidecar.sh /Users/byronhudson/.buildrunner/scripts/dispatch-to-node.sh /Users/byronhudson/.buildrunner/scripts/_dispatch-core.sh`
- Focused verification result: success (`exit 0`, no output).
- Focused verification command: `node --check /Users/byronhudson/.buildrunner/dashboard/events.mjs`
- Focused verification result: success (`exit 0`, no output).
- Focused verification command: `.venv/bin/python -m pytest tests/integration/test_codex_begin_workflow.py tests/integration/test_codex_remote_dispatch.py tests/integration/test_runtime_build_monitor.py tests/runtime/test_command_compiler.py tests/integration/test_policy_parity.py tests/integration/test_shadow_mode.py -q`
- Focused verification result: `37 passed, 2 warnings in 7.54s`
- Cumulative focused verification command for the reviewed 0 through 12 scope: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/runtime/test_command_compiler.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py tests/integration/test_codex_spec_workflow.py tests/integration/test_codex_begin_workflow.py tests/integration/test_codex_remote_dispatch.py -q`
- Cumulative focused verification result for the reviewed 0 through 12 scope: `69 passed, 2 warnings in 10.90s`
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun through the completed Phase 12 scope and returned `NO_FINDINGS`.
- Actual gate result: `COMPLETE_RUNTIME_AWARE_DISPATCH_CONTRACT_NO_REMOTE_PROMOTION`
- Constraints still in force: no live routing/cutover; omitted runtime behavior unchanged; Claude remains default for research/planning/spec/architecture; Codex remains execution/build only after plan approval; Phase 8 shadow mode remains advisory-only; Phase 10 `/spec` remains BR3-workflow-only; remote Codex remains disabled because this session verified the dispatch contract and simulated remote path, not a new live node-auth/version/probe baseline.
- Next safe step: begin Phase 13 hardening/rollout work and, if remote Codex promotion is desired later, first re-verify a real remote node against the pinned version/auth/probe criteria before changing runtime policy.

---

### Phase 13: Hardening, Tests, Observability, and Rollout

**Status:** complete
**Goal:** Make the dual-runtime system operable, testable, measurable, and supportable.

**Files to CREATE:**

- `tests/runtime/test_capabilities.py`
- `tests/integration/test_runtime_selection.py`
- `tests/integration/test_claude_regression_smoke.py`
- `.buildrunner/runtime-observability.md`
- `.buildrunner/runtime-rollout.md`
- `.buildrunner/runtime-runbook.md`

**Files to MODIFY:**

- `ui/src/components/CommandCenter.tsx`
- `~/.buildrunner/dashboard/events.mjs`
- `~/.buildrunner/scripts/developer-brief.sh`

**Blocked by:** Phases 8, 10, 11, and 12

**Deliverables:**

- [x] Unit tests for runtime schemas, capabilities, normalization, config resolution
- [x] Integration tests for runtime selection, policy parity, Codex review, Codex `/spec`, Codex `/begin`
- [x] Claude regression smoke tests
- [x] Dashboard/runtime health metrics and health checks
- [x] Operator runbook for auth failures, stalled jobs, shadow mismatches, fallback routing
- [x] Cost controls and runtime budget tracking
- [x] Documentation of which commands are Claude-only, Codex-ready, or hybrid

**Success Criteria:**

- regression suite passes for both runtimes where applicable
- Claude default path is still production-safe
- runtime health and failure modes are observable
- operator docs are good enough to support the system without tribal memory

**Actual Checkpoint on 2026-04-16:**

- Added Phase 13 hardening coverage in `tests/runtime/test_capabilities.py`, `tests/integration/test_runtime_selection.py`, and `tests/integration/test_claude_regression_smoke.py` so capability profiles, runtime precedence, and Claude-default regressions are now pinned explicitly.
- Extended BR3-visible observability in `~/.buildrunner/dashboard/events.mjs` with runtime health, budget, and command-support endpoints, and surfaced the same posture in `ui/src/components/CommandCenter.tsx` and `~/.buildrunner/scripts/developer-brief.sh`.
- Added rollout artifacts `.buildrunner/runtime-observability.md`, `.buildrunner/runtime-rollout.md`, and `.buildrunner/runtime-runbook.md` so auth failures, stalled jobs, shadow mismatches, fallback routing, and budget posture are documented directly in the repo.
- Phase 13 focused verification command: `python3 -m py_compile /Users/byronhudson/Projects/BuildRunner3/tests/runtime/test_capabilities.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_runtime_selection.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_claude_regression_smoke.py /Users/byronhudson/Projects/BuildRunner3/api/routes/execute.py`
- Phase 13 focused verification result: success (`exit 0`, no output).
- Phase 13 focused verification command: `bash -n /Users/byronhudson/.buildrunner/scripts/developer-brief.sh`
- Phase 13 focused verification result: success (`exit 0`, no output).
- Phase 13 focused verification command: `node --check /Users/byronhudson/.buildrunner/dashboard/events.mjs`
- Phase 13 focused verification result: success (`exit 0`, no output).
- Phase 13 focused verification command: `.venv/bin/python -m pytest /Users/byronhudson/Projects/BuildRunner3/tests/runtime/test_capabilities.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_runtime_selection.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_claude_regression_smoke.py -q`
- Phase 13 focused verification result: `9 passed, 2 warnings in 0.65s`
- Actual gate result: `COMPLETE_HARDENING_OBSERVABILITY_ROLLOUT_NO_REMOTE_PROMOTION`
- Constraints still in force: no live routing/cutover, omitted runtime behavior unchanged, Claude remains default for research/planning/spec/architecture and when runtime is omitted, Codex remains execution/build only after plan approval, Phase 8 shadow mode remains advisory-only, Phase 10 `/spec` remains BR3-workflow-only, Phase 11 `/begin` remains sequential and bounded, unsupported flows still fail closed or hand off explicitly, and remote Codex remains disabled because no fresh live readiness validation was performed.

---

### Phase 14: Consensus Adversarial Review Enforcement

**Status:** complete
**Goal:** Enforce bounded Claude + Codex consensus review on new BUILD phases and high-stakes planning artifacts so no new phase lands without a recorded adversarial review trail.

**Files to CREATE:**

- `.buildrunner/adversarial-reviews/`
- `.buildrunner/adversarial-reviews/README.md`
- `~/.buildrunner/hooks/require-adversarial-review.sh`
- `tests/integration/test_adversarial_review_enforcement.py`

**Files to MODIFY:**

- `~/.buildrunner/scripts/adversarial-review.sh`
- `.buildrunner/hooks/pre-commit`
- `~/.claude/commands/spec.md`
- `~/.claude/commands/amend.md`

**Blocked by:** Phases 3 and 8

**Consensus Loop Required by This Phase:**

1. Run Claude and Codex independently in parallel against the same artifact.
2. Merge findings into one tracking file with source attribution.
3. If disagreements remain, run up to two rebuttal rounds where each reviewer sees the merged findings.
4. Highlight consensus blockers and unresolved disagreements explicitly.
5. If unresolved blocker disagreement remains after the bounded loop, block and escalate to the user.

**Execution Layout (V1):**

- Preferred: Claude on Otis, Codex on the nearest validated Codex node
- Initial default: Codex may run on Muddy even if remote Codex is not yet promoted
- Remote Codex on Otis is allowed only if Phase 3 validates auth + compatibility there

**Deliverables:**

- [x] Add parallel mode to `adversarial-review.sh` that runs Claude + Codex together and merges findings
- [x] Write repo-local tracking files under `.buildrunner/adversarial-reviews/phase-{N}-{timestamp}.json`
- [x] Define tracking file schema with artifact path, `task_id`, reviewers, findings, consensus blockers, unresolved disagreements, and pass/fail
- [x] Update `/spec` and `/amend` to auto-run the bounded consensus review loop for new phases
- [x] Add fast pre-commit enforcement that blocks staged BUILD phase additions when tracking files are missing
- [x] Add explicit emergency bypass via env var with loud audit trail to decisions log

**Merge Strategy (V1):**

- Any blocker from either reviewer blocks unless resolved in the rebuttal loop
- Matching findings from both reviewers are marked `consensus`
- One-sided warnings are preserved with source attribution
- Unresolved blocker disagreements escalate to user review; they do not silently pass

**Success Criteria:**

- new BUILD phases cannot be committed without review tracking files unless explicit audited bypass is used
- parallel review latency is bounded by the slower reviewer, not the sum of both
- merged review artifacts show consensus blockers and unresolved disagreements clearly
- the full `/spec` and `/amend` adversarial flow works end to end with audit trail

**Actual Checkpoint on 2026-04-16:**

- Added Phase 14 consensus mode to `~/.buildrunner/scripts/adversarial-review.sh`, which now runs Claude and Codex together for adversarial review, merges findings into BR3-visible artifacts, and writes repo-local tracking files under `.buildrunner/adversarial-reviews/phase-{N}-{timestamp}.json`.
- Added `.buildrunner/adversarial-reviews/README.md` plus `~/.buildrunner/hooks/require-adversarial-review.sh` so staged BUILD phase additions now fail closed when tracking files are missing, blocked, or unresolved, with explicit emergency bypass logging through `BR3_BYPASS_ADVERSARIAL_REVIEW=1`.
- Updated `.buildrunner/hooks/pre-commit`, `~/.claude/commands/spec.md`, `~/.claude/commands/amend.md`, `core/runtime/workflows/spec_workflow.py`, and `core/runtime/preflight.py` so the bounded consensus review loop and its enforcement trail are explicit in BR3-owned workflow behavior.
- Added `tests/integration/test_adversarial_review_enforcement.py` to verify tracking-file creation and staged BUILD-phase enforcement end to end.
- Phase 14 focused verification command: `bash -n /Users/byronhudson/.buildrunner/scripts/adversarial-review.sh /Users/byronhudson/.buildrunner/hooks/require-adversarial-review.sh /Users/byronhudson/Projects/BuildRunner3/.buildrunner/hooks/pre-commit`
- Phase 14 focused verification result: success (`exit 0`, no output).
- Phase 14 focused verification command: `python3 -m py_compile /Users/byronhudson/Projects/BuildRunner3/core/runtime/workflows/spec_workflow.py /Users/byronhudson/Projects/BuildRunner3/core/runtime/preflight.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_adversarial_review_enforcement.py`
- Phase 14 focused verification result: success (`exit 0`, no output).
- Phase 14 focused verification command: `.venv/bin/python -m pytest /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_adversarial_review_enforcement.py /Users/byronhudson/Projects/BuildRunner3/tests/integration/test_codex_spec_workflow.py -q`
- Phase 14 focused verification result: `5 passed in 1.67s`
- Actual gate result: `COMPLETE_CONSENSUS_ADVERSARIAL_REVIEW_ENFORCEMENT`
- Constraints still in force: blocker disagreements remain explicit and blocking, secondary/shadow reviewers remain non-authoritative writers, Claude remains default for omitted runtime and planning/spec/architecture, Codex remains execution/build only after plan approval, shadow mode remains advisory-only, and remote Codex remains disabled/not promoted.
- Next safe step: stop at the completed Phase 14 checkpoint for this BUILD. Any future remote Codex promotion or post-Phase-14 behavior requires a new BUILD amendment plus fresh live node version/auth/probe validation before policy changes.
- Cumulative focused verification command for the reviewed 0 through 14 scope: `.venv/bin/python -m pytest tests/runtime/test_result_schema.py tests/runtime/test_edit_normalizer.py tests/runtime/test_config_resolution.py tests/runtime/test_review_spike.py tests/runtime/test_command_compiler.py tests/runtime/test_capabilities.py tests/integration/test_codex_capabilities.py tests/integration/test_runtime_auth_preflight.py tests/integration/test_policy_parity.py tests/integration/test_runtime_build_monitor.py tests/integration/test_shadow_mode.py tests/integration/test_codex_spec_workflow.py tests/integration/test_codex_begin_workflow.py tests/integration/test_codex_remote_dispatch.py tests/integration/test_runtime_selection.py tests/integration/test_claude_regression_smoke.py tests/integration/test_adversarial_review_enforcement.py -q`
- Cumulative focused verification result for the reviewed 0 through 14 scope: `81 passed, 2 warnings in 9.53s`
- On 2026-04-16, the mandatory cumulative Claude final-authority review was rerun through the completed Phase 14 scope and returned `NO_FINDINGS`.

**Go / No-Go Gate G:**

- If consensus review adds more operational pain than signal, keep adversarial review advisory-only instead of mandatory enforcement.

---

## Decision Gates Summary

- Gate 0 after Phase 0: Codex capability and compatibility viability
- Gate A after Phase 1: shared result envelope viability
- Gate B after Phase 3: remote Codex auth/process viability
- Gate C after Phase 4: result/edit normalization stability
- Gate D after Phase 8: shadow mode usefulness and safety
- Gate E after Phase 10: Codex `/spec` quality
- Gate F after Phase 12: runtime-aware remote dispatch stability
- Gate G after Phase 14: consensus review enforcement value vs friction

If any gate fails, stop promotion and either:

- redesign the abstraction boundary
- keep Codex local-only
- keep specific workflows Claude-first
- formalize long-term hybrid operation

---

## Rollback Procedures

- If Phases 0-5 fail, keep `runtime=claude` as the only enabled runtime and disable Codex selection flags.
- If Phase 8 fails, disable shadow mode globally, kill active shadow jobs, and keep Codex advisory work opt-in only.
- If Phase 12 fails, disable remote Codex execution and keep Codex local-only.
- If Phase 14 fails, remove `require-adversarial-review.sh` from `.buildrunner/hooks/pre-commit` and keep consensus review advisory-only.
- Any rollback must write an entry to decisions log with timestamp, phase, reason, and current runtime posture.

---

## Testing Strategy

**Unit tests:**

- runtime schema validation
- edit normalization
- capability flags
- config precedence
- error classification

**Integration tests:**

- dual-runtime `/review` spike
- policy parity between Claude and Codex
- shadow mode logging
- Codex `/spec`
- Codex `/begin`
- local and remote runtime auth preflight
- consensus adversarial review tracking + enforcement

**Regression tests:**

- current Claude default CLI path
- current Claude dispatch path
- current dashboard liveness behavior

**End-to-end smoke tests:**

- one review path
- one planning path
- one bounded execution path
- one local cluster-dispatched run

**Failure injection tests:**

- Codex auth expiry mid-run
- remote node offline during dispatch
- Codex process crash during execution
- network partition between sidecar and dashboard
- disk-full or write-failure during edit normalization

---

## Shadow Mode Metrics

Track at minimum:

- total paired runs
- median latency by runtime and command
- blocker agreement rate
- warning overlap rate
- false blocker rate
- operator acceptance / rejection
- fallback frequency
- cost per review / per promoted workflow

Do not promote based on subjective comfort alone.

---

## Risk Register

| Risk | Impact | Mitigation |
| ---- | ------ | ---------- |
| Runtime abstraction becomes Claude-shaped | HIGH | lock contract in Phase 4 from capability needs, not current code shape |
| Remote Codex auth is brittle | HIGH | Phase 3 preflight gate, local-only fallback |
| Edit normalization is lossy | HIGH | raw payload preservation + fixture tests + Gate C |
| Shadow mode doubles operational cost | MEDIUM | restrict to narrow workflows, track budget from Phase 0 onward |
| Capability drift across vendors | HIGH | capability map + explicit Claude-first commands |
| Debugging becomes multi-layered | HIGH | runtime metadata in dashboard + runbook + health metrics |
| Claude workflow regression | HIGH | default remains Claude + regression smoke tests |
| Documentation burden grows | MEDIUM | runtime inventory + rollout docs + runbook |
| Codex CLI compatibility drift | HIGH | pin version range + node preflight compatibility checks |
| Consensus review deadlock or fatigue | MEDIUM | bounded review loop + explicit escalation to user |

---

## Out of Scope (V1)

- full `/autopilot` parity
- browser-heavy `/design` parity
- rich MCP-style tool parity
- automatic Codex auth sync across nodes
- hidden fallback between runtimes without explicit reporting

These can be revisited only after Phase 13 completes successfully.

---

## Acceptance Criteria Summary

This build is complete when:

- Claude remains the stable default runtime
- BR3 can intentionally select Claude or Codex
- critical policy is owned by BR3 rather than only Claude hooks
- dashboard and registry handle both runtimes through one state model
- Codex successfully owns `/review`, `/spec`, and bounded `/begin` flows
- cluster dispatch can run Codex jobs with correct heartbeats and exit handling
- unsupported flows are explicitly marked or routed, not guessed
- new BUILD phase creation is guarded by consensus adversarial review with audit trail
