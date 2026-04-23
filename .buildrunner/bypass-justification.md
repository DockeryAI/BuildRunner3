# Adversarial Review Bypass — cluster-visibility-sharding

**Date:** 2026-04-23
**Plan:** .buildrunner/plans/plan-cluster-visibility-sharding.md
**Build:** BUILD_cluster-visibility-sharding.md

## Why bypass

The consensus adversarial review tooling was unable to run end-to-end because the summarizer step hit an infrastructure error:

```
summarizer: OllamaRuntime returned status=error error=Unsupported task_type: summarize; project_root is required; commit_sha is required
```

This is tied to uncommitted edits in `core/runtime/ollama_runtime.py` (visible in git status at session start). The Otis fallback path was blocked by the one-review-per-plan mechanical guard (`cross_model_review.py --mode plan`) that forbids retries on the same plan in the same invocation — the guard was designed to prevent runaway review loops, not to handle summarizer infra failures.

## What substituted

Per the /spec skill's third fallback path ("If both fail, fall back to a local Explore subagent using the adversarial prompt from the script output."), a local Explore subagent ran an adversarial read of the plan with an explicit blocker/warning/suggestion rubric. The review cited concrete file:line evidence from the codebase — not vibes — and surfaced four legitimate blockers plus six warnings.

## Blockers raised by the Explore review (all fixed inline in the plan)

1. **B1 — `BR3_ROUTER_LEGACY_SATURATION` env var did not exist.** Plan now codes it as an explicit Phase 3 deliverable, not assumed.
2. **B2 — `cluster-check.sh --health-json` drops new fields** (`cluster-check.sh:118,147` hand-construct JSON). Plan now includes a Phase 2 deliverable to rewrite both branches to proxy the `/health` payload verbatim.
3. **B3 — `server.mjs` does not exist; the real file is `events.mjs`** with a 30s (not ≤10s) poll. Plan corrected to reference `events.mjs` and added a `BR3_NODE_HEALTH_POLL_MS` knob with 10s default.
4. **B4 — `jobs-aggregator.js` only listens to SSE events** (`jobs-aggregator.js:160-184`). Plan now adds a seventh SSE event type `node.workload` emitted from `events.mjs`, with dedupe semantics (SSE origin wins on shared `build_id`).

## Warnings addressed inline

- W1 — Dual endpoints `/health` + `/api/health` now explicitly synchronized as superset/subset in Phase 1 deliverables.
- W2 — `cluster-builds.json` single-writer contract now enforced via `build-state-machine.mjs` in Phase 4.
- W3 — Router latency guarded by new `BR3_NODE_HEALTH_TIMEOUT_MS` fail-open (default 500ms).
- W4 — Shard strategy switched from file-count split to `vitest --shard=N/M` built-in.
- W5 — `psutil` install + first-call warmup explicitly in Phase 1 deliverables.
- W6 — Phase 6 pause/resume switched from SIGSTOP to kill-and-relaunch.

## Suggestions adopted

- Phase 4 SSH reachability (exit 255 requeue) now a deliverable.
- Phase 4 SSH username map (byronhudson vs byron for Below) documented.
- Phase 4 sharding strategy note explaining why built-in `--shard` beats custom splitter.

## Decision

The local Explore review produced higher-signal findings than an infra-broken consensus run would have. Every blocker has been addressed in the plan before writing the BUILD spec. Bypass authorized for this single spec; the underlying ollama summarizer bug should be fixed in a separate tracked task so the consensus path works for the next spec.

## Override authority

Roy-concise profile, auto-continue mode, one-review-per-spec rule. No product-decision blockers — all issues were technical fixes the model could make.
