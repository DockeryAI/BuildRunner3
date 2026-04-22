# Build: ship-self-healing-prepush

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: terminal-build, assigned_node: muddy }
      phase_2: { bucket: terminal-build, assigned_node: muddy }
      phase_3: { bucket: terminal-build, assigned_node: muddy }
      phase_4: { bucket: terminal-build, assigned_node: walter }
      phase_5: { bucket: terminal-build, assigned_node: lockwood }
      phase_6: { bucket: architecture, assigned_node: muddy }
```

**Created:** 2026-04-22
**Status:** Phases 1-5 Complete — Phase 6 In Progress
**Deploy:** web — `npm run build` (framework-level skill; deploy target is N/A for the BR3 framework itself)
**Source Plan File:** .buildrunner/plans/spec-ship-self-healing-prepush-plan.md
**Source Plan SHA:** 9e725f1a38361e5dab7e42e1fab2fd40bbbb67ce3dd65277094e78e94c9cc118
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-22T20:21:38Z

## Overview

`/ship` is a single command that turns `git push` into a gated delivery pipeline. Every gate (preflight, rebase, review, test, docs, log-scan, commit, publish) has a bounded self-healing fix loop. Routine failures auto-recover within strict scope-locks, diff caps, and escalation budgets; real failures surface to the operator with an actionable URL. Integrates BR3's existing review/dispatch/metrics infrastructure. Exists at the BR3 framework level (`~/.buildrunner/scripts/ship/` + `~/.claude/commands/ship.md`) and is installed into individual repos via a pre-push hook fragment that slots into the existing BR3 composed-hook chain.

## Parallelization Matrix

| Phase | Key Files                                      | Can Parallel With | Blocked By                |
| ----- | ---------------------------------------------- | ----------------- | ------------------------- |
| 1     | `commands/ship.md`, `ship-runner.sh`, config   | —                 | —                         |
| 2     | `ship/gates/*.sh`                              | —                 | 1 (needs runner + config) |
| 3     | `ship/healing/*.sh`                            | 4, 5              | 2 (needs gates)           |
| 4     | `ship/ci/*.sh`                                 | 3, 5              | 2 (needs publish.sh)      |
| 5     | `ship/telemetry/*.sh`, `lockwood-metrics.sh`   | 3, 4              | 2 (needs gates)           |
| 6     | autopilot hook, commit-local, governance, docs | —                 | 3, 4, 5                   |

## Phases

### Phase 1: Foundation — Command, Config, Sentinel, Hook Integration

**Status:** ✅ COMPLETE
**Files:**

- `~/.claude/commands/ship.md` (NEW)
- `~/.buildrunner/scripts/ship/ship-runner.sh` (NEW)
- `~/.buildrunner/scripts/ship/ship-config.yaml` (NEW)
- `~/.buildrunner/scripts/ship/ship-sentinel.sh` (NEW)
- `.buildrunner/hooks/pre-push.d/50-ship-gate.sh` (NEW)
- `.buildrunner/hooks/install-hooks.sh` (MODIFY)
- `.gitignore` (MODIFY)

**Blocked by:** None

**Deliverables:**

- [x] Command at `~/.claude/commands/ship.md` with frontmatter (effort: xhigh, adaptive summarized thinking), docs, flags `--fast` / `--full` / `--dry-run` / `--resume` / `stats`
- [x] `ship-runner.sh` CLI with subcommands: `run` (default), `stats`, `resume`, `status`
- [x] `ship-config.yaml` schema: `gates[]`, `escalation_budget` per gate (default 2), `scope_locks[]`, `diff_cap_lines` (default 200), `diff_cap_exclude[]`, `branch_policies{main,release/*,*}`, `stale_window_seconds` (default 1800)
- [x] Sentinel at `.buildrunner/ship/last-ship.json` with schema `{head_sha, base_sha_at_review, branch, mode, gates_required[], gates_passed[], gates_failed[], started_at, completed_at, heal_attempts_by_gate}`
- [x] Pre-push hook fragment `50-ship-gate.sh`: blocks push if sentinel missing, stale, head_sha mismatch, or `gates_passed[] ⊉ gates_required[]`
- [x] `install-hooks.sh` modified to register the new fragment; idempotent; preserves existing fragments
- [x] `.gitignore` entries for `.buildrunner/ship/*.json` and `.buildrunner/ship/*.log` added before any sentinel writes

**Success Criteria:** `/ship --dry-run` loads config and prints gate sequence with zero side effects. `git push` blocked unless sentinel fresh + all required gates passed. Existing hook fragments unchanged after `install-hooks.sh` re-run. `git status` clean after any `/ship` invocation.

---

### Phase 2: Gate Orchestration (no healing yet)

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/ship/gates/preflight.sh` (NEW)
- `~/.buildrunner/scripts/ship/gates/rebase.sh` (NEW)
- `~/.buildrunner/scripts/ship/gates/review.sh` (NEW) — wraps `auto-review-diff.sh`
- `~/.buildrunner/scripts/ship/gates/test.sh` (NEW)
- `~/.buildrunner/scripts/ship/gates/docs.sh` (NEW)
- `~/.buildrunner/scripts/ship/gates/log-scan.sh` (NEW)
- `~/.buildrunner/scripts/ship/gates/ship-commit.sh` (NEW) — git-only commit; does NOT wrap `/commit`
- `~/.buildrunner/scripts/ship/gates/publish.sh` (NEW) — atomic push + PR create/update
- `~/.buildrunner/scripts/ship/gates/rollback.sh` (NEW)
- `~/.buildrunner/scripts/ship/ship-runner.sh` — extend (created in Phase 1): gate sequencing, sentinel updates, resume logic, rollback wiring

**Blocked by:** Phase 1

**Deliverables:**

- [x] Each gate: exit 0=pass, 1=fail, 2=skip; single-line status output
- [x] Runner sequence: `[preflight, rebase, review, test, docs, log-scan, ship-commit, publish]`
- [x] Resume rule explicit: gate skipped only when `gates_passed[]` contains it AND `head_sha` unchanged AND `base_sha_at_review` still matches `origin/main`
- [x] Rollback runs on any non-zero exit: pops preflight stash if present; deletes orphan remote branch if publish partially completed
- [x] `--dry-run` prints gate sequence and planned actions without executing
- [x] Per-gate outcome logged to `.buildrunner/ship/run-log.jsonl`

**Success Criteria:** Happy path ships cleanly, PR opens, sentinel complete. Failure: rollback restores preflight stash, repo clean, no remote branch. Resume after local fix: head_sha advances → downstream gates re-run; preflight/rebase skipped only when base hasn't moved.

---

### Phase 3: Self-Healing Fix Loops

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/ship/healing/fix-orchestrator.sh` (NEW)
- `~/.buildrunner/scripts/ship/healing/scope-guard.sh` (NEW)
- `~/.buildrunner/scripts/ship/healing/diff-cap.sh` (NEW)
- `~/.buildrunner/scripts/ship/healing/parallel-fix.sh` (NEW)
- `~/.buildrunner/scripts/ship/healing/revert-heal.sh` (NEW)
- `~/.buildrunner/scripts/ship/healing/heal-log.sh` (NEW)
- `~/.buildrunner/scripts/ship/ship-config.yaml` — extend (created in Phase 1): per-gate `fix_policy` block; `branch_policies` adds `audit_log_path`
- `~/.buildrunner/scripts/ship/gates/*.sh` — extend (created in Phase 2, 6 files): invoke fix-orchestrator on failure

**Blocked by:** Phase 2

**Deliverables:**

- [x] Orchestrator: max 2 attempts per gate; fixed 2-second gap between attempts
- [x] Scope guard deny-list: `*.sql`, `governance.yaml`, `supabase/migrations/**`, `api/auth.py`, `src/**/auth/**`, top-level `CLAUDE.md` on main/release, `.env`, `.env.*`, `**/.env`, `**/.env.*`, linguist-generated files
- [x] Diff-size cap: 200 lines default, computed over non-excluded files; exclude `package-lock.json`, `pnpm-lock.yaml`, `yarn.lock`, `dist/**`, `build/**`, generated code
- [x] Parallel mode: each attempt runs in `.buildrunner/ship/worktrees/attempt-N/` via `dispatch-to-node.sh`; first green wins; losing attempts killed and worktrees deleted
- [x] Branch policy: on main / `release/*`, auto-fix requires confirmation or `BR3_SHIP_AUTOHEAL=force`; overrides appended to `.buildrunner/ship/autoheal-overrides.log`; daily rollup flags >5/day
- [x] Heal log records `{gate, attempt_n, branch, diff_lines, files_touched[], outcome, duration_ms, scope_violation?}`
- [x] Revert: heal commit tied to downstream CI failure via diff-intersection gets auto-reverted, original gate re-triggered with attempts reset
- [x] Resume guard: scope-guard re-validates diff before any gate re-run

**Success Criteria:** Lint auto-fixes on attempt 1. Test flake retries once per Tier 1 rule. Main-branch heal requires confirmation; `force` override audit-logged. Scope violation declined cleanly. Parallel mode applies winner without double-edits. Bad heal auto-reverts within one CI cycle.

---

### Phase 4: CI Babysit + PR Management

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/ship/ci/watch-ci.sh` (NEW) — nohup + PID file
- `~/.buildrunner/scripts/ship/ci/ci-classifier.sh` (NEW)
- `~/.buildrunner/scripts/ship/ci/ci-heal.sh` (NEW) — refreshes sentinel before push
- `~/.buildrunner/scripts/ship/ci/ci-lock.sh` (NEW) — per-branch lock file
- `~/.buildrunner/scripts/ship/ci/pr-body-gen.sh` (NEW)
- `~/.buildrunner/scripts/ship/gates/publish.sh` — extend (created in Phase 2): pr-body-gen + `gh pr edit` on update

**Blocked by:** Phase 2
**After:** Phase 3 (CAN parallelize with Phase 3)

**Deliverables:**

- [x] Background watcher launched via `nohup ./watch-ci.sh … &`, PID at `.buildrunner/ship/ci-watch.pid`, state at `.buildrunner/ship/ci-state.json`
- [x] Classifier: lint/format/prettier → fixable; known-flaky Playwright → fixable (1 retry); broken unit test → real; type error → real; migration failure → real
- [x] CI-heal sequence: acquire per-branch lock → pull failing log → orchestrator heal → commit → rewrite sentinel → push `--force-with-lease` → release lock
- [x] Global CI-heal budget: 3 attempts per PR; 4th failure disables auto-heal for that branch until next `/ship` run
- [x] Real failures: one-line notification with run URL + failing step name; no further action
- [x] PR body generated on first publish; regenerated via `gh pr edit --body` on subsequent pushes
- [x] Existing PR detection via `gh pr view --json number,state`

**Success Criteria:** Lint-fail on CI auto-heals end-to-end. Logic bug surfaces run URL, zero side effects. Concurrent `/ship` on same branch: lock prevents collision. 4 fixable failures in a row: auto-heal self-disables, user notified.

---

### Phase 5: Observability + Telemetry

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/ship/telemetry/emit.sh` (NEW) — reuses existing `lockwood-metrics.sh` transport
- `~/.buildrunner/scripts/ship/telemetry/rollup.sh` (NEW)
- `~/.buildrunner/scripts/ship/telemetry/drift-detect.sh` (NEW)
- `~/.buildrunner/scripts/ship/ship-runner.sh` — extend (created in Phase 1): add `stats` subcommand
- `~/.buildrunner/scripts/lockwood-metrics.sh` (MODIFY) — register `ship.*` metric names

**Blocked by:** Phase 2
**After:** CAN parallelize with Phase 3 and Phase 4

**Deliverables:**

- [x] `emit.sh` calls `lockwood-metrics.sh emit ship.<gate>.<outcome>` with JSON `{duration_ms, heal_attempts, branch, mode, exit_code}`
- [x] Weekly rollup: top 3 failing gates, mean heal success rate, mean time-to-ship, total ships, override count
- [x] Drift detection: heal rate on any gate rising >20% WoW writes to `.buildrunner/ship/drift-alerts.json`
- [x] `ship stats` subcommand calls `rollup.sh --week-current`
- [x] Emit degrades to local JSONL fallback if Lockwood is offline — never fails a gate

**Success Criteria:** `/ship` run emits metrics visible in `lockwood-metrics.sh rollup 1`. Simulated 40% failure rate → drift alert written. `/ship stats` prints useful summary.

---

### Phase 6: Integration — Autopilot, /commit (global), /begin, Governance, Docs, Smoke Test

**Status:** not_started
**Files:**

- `~/.buildrunner/scripts/autopilot-phase-hook.sh` (NEW) — real flow-control, invoked from autopilot post-phase callback
- `~/.buildrunner/scripts/autopilot-dispatch-prefix.sh` (MODIFY) — documentation pointer only
- `~/.claude/commands/commit.md` (MODIFY) — global `/commit` routed through `/ship` since `/commit` pushes
- `~/.claude/commands/begin.md` (MODIFY) — post-completion `/ship` hook with opt-out
- `~/.claude/commands/amend.md` (AUDIT) — confirm no push path; note in docs if added later
- `.buildrunner/governance/ship-rules.yaml` (NEW) — project-local governance path
- `.buildrunner/governance/governance.yaml` (MODIFY) — include `ship:` section
- `/Users/byronhudson/.claude/CLAUDE.md` (MODIFY) — add `/ship` section with push-surface routing table
- `/Users/byronhudson/Projects/BuildRunner3/CLAUDE.md` (MODIFY) — add `/ship` to skill triggers table
- `.buildrunner/docs/ship.md` (NEW) — user-facing docs
- `~/.buildrunner/scripts/ship/smoke-test.sh` (NEW) — end-to-end smoke test

**Blocked by:** Phases 3, 4, 5

**Deliverables:**

- [ ] Autopilot phase hook: runs `/ship --fast` after final phase unless `BR3_AUTOPILOT_SHIP=off`; if autopilot lacks a callback surface, deliverable includes adding a minimal hook point
- [ ] Global `/commit` modified to invoke `/ship` whenever a push would occur (since `/commit` stages + commits + pushes). Preserves existing `/commit` behavior when `--no-push` is passed or no remote exists. Applies to **all** projects, not just BR3 — `/commit` is a push surface and must route through gates universally
- [ ] `/begin` post-completion hook: on final-phase success, invokes `/ship --fast` unless `BR3_BEGIN_SHIP=off`; mirrors the autopilot opt-out pattern
- [ ] `/amend` audited and confirmed to NOT push (as of spec authoring). Deliverable includes a doc note in `ship.md` flagging that any future skill which adds `git push` must route through `/ship`
- [ ] Push-surface integration table maintained in `~/.claude/CLAUDE.md` listing every command/skill that can push and how each routes to `/ship`. Pre-push hook (`50-ship-gate.sh`) documented as the universal enforcement point — any `git push` from any source (raw git, `gh`, IDE buttons, future skills) is gated
- [ ] `ship-rules.yaml` at project-local path; loaded by existing `core/governance.py` without loader changes
- [ ] Global CLAUDE.md — `/ship` section with flags, exit codes, env vars, push-surface routing table
- [ ] Project CLAUDE.md — `/ship` in skill triggers table
- [ ] `.buildrunner/docs/ship.md` — flags, exit codes, config schema, troubleshooting, push-surface routing table, "adding a new push path" checklist
- [ ] Smoke test extended: (a) modifies throwaway file, (b) runs `/ship --dry-run` asserting gate sequence, (c) runs `/ship` on scratch branch asserting PR opens + sentinel written + telemetry emitted + cleanup, (d) runs `/commit` on scratch branch asserting it routes through `/ship` (not a plain push), (e) runs `/begin` no-op phase asserting post-completion `/ship` fires with `BR3_BEGIN_SHIP=off` honored, (f) deletes test PR

**Success Criteria:** Autopilot final phase auto-ships respecting opt-out. `/commit` routes through `/ship` in every project (not just BR3). `/begin` auto-ships on completion unless opted out. Raw `git push` from any source (CLI, `gh`, IDE) blocked by pre-push hook unless gates passed. Governance loads through existing loader. Fresh operator uses `/ship` from docs alone. Smoke test passes all 6 assertions.

---

## Session Log

[Will be updated by /begin]
