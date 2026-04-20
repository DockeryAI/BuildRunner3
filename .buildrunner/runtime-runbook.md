# Runtime Runbook

## Auth Failures

- Symptom: `CodexAuthError`, `401`, `unauthorized`, or explicit auth failure in `runtime-capability.log`
- Check:
  - `~/.codex/auth.json`
  - local `codex --version`
  - any recent `check-runtime-auth.sh` or preflight output
- Response:
  - direct Codex requests fail closed
  - shadow runs should show `shadow_skipped`
  - do not reroute silently to Codex remote or broaden policy

## Stalled Jobs

- Symptom: sidecar heartbeat stops advancing, dashboard marks build suspect/stalled
- Check:
  - lock heartbeat files under `.buildrunner/locks/phase-*`
  - sidecar metadata in `sidecar.json`
  - `dispatch_mode`, `runtime`, and runtime PID in dashboard health endpoints
- Response:
  - inspect the active runtime process first
  - preserve one BR3 state machine; do not invent runtime-specific completion rules

## Shadow Mismatches

- Symptom: Codex shadow produces blocker divergence from Claude primary output
- Check:
  - `~/.buildrunner/logs/runtime-shadow.log`
  - promotion threshold section in `.buildrunner/runtime-shadow-metrics.md`
- Response:
  - keep shadow advisory-only
  - record whether the mismatch is a false blocker, missed blocker, or expected warning delta
  - do not promote shadow results to authoritative output

## Fallback Routing

- Runtime omitted:
  - expected result is Claude via default precedence
- Codex command unsupported:
  - expected result is explicit block or BR3-owned workflow handoff
- Remote readiness unverified:
  - keep Codex local-only in policy and documentation

## Budget Pressure

- Symptom: review budget approaches monthly cap in `/api/runtime/budget`
- Response:
  - reduce optional cross-model review traffic first
  - keep mandatory governance reviews explicit and auditable
  - log any temporary bypass or policy exception in the decisions log
