# Runtime Observability

Phase 13 hardening keeps BR3 runtime posture visible without changing the default routing policy.

## Runtime Signals

- `~/.buildrunner/logs/runtime-capability.log`
  JSONL audit trail for Claude and Codex runtime executions, including `status`, `duration_ms`, `exit_code`, `error_class`, `session_id`, and runtime/backend metadata.
- `~/.buildrunner/logs/runtime-shadow.log`
  Advisory shadow-run records used to compare Claude primary results with Codex shadow outcomes.
- `~/.buildrunner/logs/cross-review-spend.json`
  Monthly budget file for review-related model spend.

## Dashboard Endpoints

- `GET /api/runtime/health`
  Returns runtime status summaries, recent error classes, spend posture, and audited command support levels.
- `GET /api/runtime/budget`
  Returns the current review-spend month, cap, used amount, remaining budget, and request count.

## Health Semantics

- `healthy`
  The runtime has recent successful runs and no newer blocking/error event than its latest success.
- `degraded`
  The runtime has recent activity, but the newest event is blocked or errored.
- `unknown`
  No recent runtime audit data is available.

## Command Support Inventory

The dashboard groups commands from `core/runtime/command_capabilities.json` into:

- `claude_only`
- `codex_ready`
- `codex_workflow_only`
- `codex_shadow_only`

This keeps rollout posture explicit and prevents accidental policy broadening.

## Budget Posture

Budget tracking stays review-scoped. Phase 13 does not introduce runtime auto-throttling or live routing changes.

- Budget cap source: `core/cluster/cross_model_review_config.json`
- Budget file: `~/.buildrunner/logs/cross-review-spend.json`
- Operator action when near cap: pause non-essential cross-model review traffic, keep Claude default path intact, and record the decision in the decisions log if enforcement changes are considered.
