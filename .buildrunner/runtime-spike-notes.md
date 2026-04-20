# Runtime Spike Notes

Date: April 15, 2026
Status: phase1_complete_parallel_shadow

## Scope

- Added a Phase 1 runtime boundary under `core/runtime/*`.
- Added shared review context assembly in `core/runtime/context_compiler.py`.
- Added an opt-in runtime registry in `core/runtime/runtime_registry.py`.
- Added an explicit shadow-only review spike path.
- Left the live `core/cluster/cross_model_review.py::run_review()` default flow intact.

## Guardrails Preserved

- No live BR3 runtime routing changed.
- No default behavior changed.
- No cutover behavior changed.
- Codex review spike runs through an isolated temp workspace instead of the repo workspace.
- Claude review spike now also runs through an isolated temp workspace via local `claude -p`.

## Validation Run

- Real Phase 1 synthetic spike executed under task `review-spike-phase1synthetic`.
- Both runtimes completed through one BR3-owned `RuntimeTask` envelope.
- Claude completed through isolated local CLI execution.
- Codex completed through isolated `codex exec --json` execution.
- Both runtimes returned compatible `RuntimeResult` envelopes with runtime/backend/session metadata and keyed metrics.
- Live repo routing remained unchanged; all shadow execution stayed off the live BR3 path.

## Pending Follow-Up

- Add batch/chunk assembly before promoting Codex beyond isolated shadow review probes.
- Reconcile runtime result schema with later Phase 3 dispatch and checkpoint work.
- Decide how Phase 1 spike telemetry should feed dashboard/runtime state without touching the live path.
- Decide whether runtime registry/config resolution stays local to spike scaffolding or graduates into later global runtime selection work.
