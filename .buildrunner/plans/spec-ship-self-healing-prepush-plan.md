# Plan: ship-self-healing-prepush

**Frozen snapshot** — dedicated plan file for `BUILD_ship-self-healing-prepush.md`.
Created to isolate this BUILD's Source Plan SHA from the shared `spec-draft-plan.md`
scratch pad, which is overwritten by parallel `/spec` and `/spec-codex` sessions.
Precedent: `fix(prometheus-build): freeze plan snapshot + restamp SHA` (d920807af).

## Goal

Ship `/ship` — a single command that turns `git push` into a gated delivery pipeline
with bounded self-healing fix loops. Every gate (preflight, rebase, review, test,
docs, log-scan, commit, publish) can auto-recover from routine failures within strict
scope-locks, diff caps, and escalation budgets; real failures surface to the operator
with an actionable URL. The pre-push hook is the universal enforcement point — any
`git push` from any source (raw git, `gh`, IDE buttons, `/commit`, future skills) is
gated through `/ship`.

## Phases

### Phase 1: Foundation — Command, Config, Sentinel, Hook Integration

Deliver the `/ship` command shell, runner CLI, config schema, sentinel file, and
pre-push hook fragment that slots into the BR3 composed-hook chain. No gates yet —
this phase lands the skeleton and the universal push-blocker.

### Phase 2: Gate Orchestration (no healing yet)

Implement the eight gates in sequence (preflight, rebase, review, test, docs,
log-scan, ship-commit, publish) plus rollback. No auto-healing — failures surface
directly. Runner handles sequencing, sentinel updates, resume logic.

### Phase 3: Self-Healing Fix Loops

Bounded fix loops per gate: max 2 attempts, scope-lock deny-list, 200-line diff cap,
parallel-worktree mode, branch-policy confirmation on main/release, heal log with
revert-on-CI-failure.

### Phase 4: CI Babysit + PR Management

Background CI watcher (`nohup` + PID + per-branch lock), classifier for fixable vs
real failures, CI-heal with `--force-with-lease`, global 3-attempt budget, PR body
generator with create/update via `gh`.

### Phase 5: Observability + Telemetry

Per-gate metric emission through existing `lockwood-metrics.sh`, weekly rollup
subcommand, drift detection >20% WoW, local JSONL fallback when Lockwood offline.

### Phase 6: Integration — Autopilot, /commit (global), /begin, Governance, Docs, Smoke Test

Route every push surface through `/ship`: autopilot final-phase hook, global
`/commit` override (not just BR3), `/begin` post-completion hook, `/amend` audit,
governance rules, CLAUDE.md updates with push-surface routing table, user docs,
and an extended smoke test asserting all routing paths work.

## Push-Surface Integration Summary (Phase 6)

Every push surface must route through `/ship`. The pre-push hook is the hard
enforcement; command overrides are the UX layer so users don't hit a blocked push.

| Surface                               | Routing                                                 |
| ------------------------------------- | ------------------------------------------------------- |
| Raw `git push` (any variant)          | Pre-push hook `50-ship-gate.sh` (Phase 1)               |
| `gh pr create` (pushes branch)        | Pre-push hook                                           |
| IDE push buttons                      | Pre-push hook                                           |
| `/commit` (stages + commits + pushes) | Global `~/.claude/commands/commit.md` routes to `/ship` |
| `/begin` (final phase)                | Post-completion hook → `/ship --fast`                   |
| Autopilot (final phase)               | `autopilot-phase-hook.sh` → `/ship --fast`              |
| Future skill that pushes              | Must route to `/ship`; pre-push hook catches otherwise  |

## Acceptance

- [ ] `/ship --dry-run` prints gate sequence with zero side effects
- [ ] Raw `git push` blocked unless sentinel fresh + all required gates passed
- [ ] `/commit` routes through `/ship` in every project
- [ ] `/begin` auto-ships on completion unless `BR3_BEGIN_SHIP=off`
- [ ] Autopilot auto-ships after final phase unless `BR3_AUTOPILOT_SHIP=off`
- [ ] Self-healing stays within scope-locks and diff caps; main/release require confirmation
- [ ] CI watcher classifies and heals fixable failures; real failures surface run URL
- [ ] Telemetry emits to Lockwood; `ship stats` rollup works; drift alerts fire >20% WoW
- [ ] Smoke test passes all assertions

See `BUILD_ship-self-healing-prepush.md` for full deliverables, files, and success criteria.
