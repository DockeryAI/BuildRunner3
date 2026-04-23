# Build: burnin-harness

```yaml
role-matrix:
  inherit: default-role-matrix
  overrides:
    phases:
      phase_1: { bucket: backend-build, assigned_node: muddy }
      phase_2: { bucket: backend-build, assigned_node: muddy }
      phase_3: { bucket: backend-build, assigned_node: muddy }
      phase_4: { bucket: terminal-build, assigned_node: muddy }
      phase_5: { bucket: ui-build, assigned_node: muddy }
      phase_6: { bucket: backend-build, assigned_node: muddy }
      phase_7: { bucket: backend-build, assigned_node: muddy }
      phase_8: { bucket: backend-build, assigned_node: muddy }
      phase_9: { bucket: backend-build, assigned_node: muddy }
      phase_10: { bucket: terminal-build, assigned_node: muddy }
      phase_11: { bucket: backend-build, assigned_node: muddy }
      phase_12: { bucket: terminal-build, assigned_node: muddy }
```

**Created:** 2026-04-23
**Status:** Phases 1-8 Complete — Phase 4 In Progress
**Deploy:** operator-tooling — no user-facing deploy; harness writes to `~/.buildrunner/` and `~/.claude/skills/`.
**Source Plan File:** .buildrunner/plans/plan-burnin-harness.md
**Source Plan SHA:** ad48f9367987ac3403ab50af859a8add9cf772a3610bdf22629566bb5bf5b4e6
**Adversarial Review Verdict:** BYPASSED:.buildrunner/bypass-justification.md
**Adversarial Review Timestamp:** 2026-04-23T17:30:00Z
**Owner:** byronhudson

---

## Overview

Stand up a plugin-per-case burn-in harness that validates every cluster feature against real work, auto-heals failures under a bounded Claude fix loop, promotes cases out of active testing once stable, then retires to telemetry-only when everything is green. Installs as a single top-level Claude Code skill (`/burnin`) where the default action is **add a new test case** and subcommands cover status/run/fix/quarantine/retire/kill. Fully integrated into the existing BR3 dashboard (events.db + SSE bus + per-concern `integrations/*.mjs` pattern). Designed so adding or removing a test is a single 10-line YAML file — no code changes.

**Validation surface (initial 44 cases):**

- Below offload (17) — every site in BUILD_below-offload
- Walter sentinel (10) — auto-restart, repo freshness, race-condition guards from BUILD_walter-sentinel-hardening
- Cluster sharding + visibility (12) — process detector, busy_state accuracy, saturation handoff, shard fan-out from BUILD_cluster-visibility-sharding
- Cross-node end-to-end (5) — autopilot dispatch, /research round-trip, /ship gates, /begin spec drift, offline fallback

**State machine per case:** untested → probation → (fixing ↔ probation) → promoted → retired. A case promotes after 3 consecutive greens across 3 conditions (cold / warm / under-load). A promoted case drops to daily canary. Two weeks green on canary → retired. Fix loop bounded to 3 attempts with hard diff-size cap; exceeded budget flips case to `needs_human`.

**"Done" state:** all cases retired → kill switch shuts off canary → telemetry + drift alarm remain as the only active signal.

---

## Parallelization Matrix

| Phase | Key Files                                                                                         | Parallel With | Blocked By |
| ----- | ------------------------------------------------------------------------------------------------- | ------------- | ---------- |
| 1     | ~/.buildrunner/burnin/schema.sql, cases/, PLUGIN_SPEC.md                                          | —             | —          |
| 2     | scripts/burnin/burnin.sh, lib/{state,runner,db}.sh                                                | —             | 1          |
| 3     | lib/conditions.sh, lib/fix-loop.sh                                                                | 4, 5          | 2          |
| 4     | ~/.claude/skills/burnin/SKILL.md, skills/burnin/scripts/add.sh                                    | 3, 5          | 2          |
| 5     | dashboard/integrations/burnin.mjs, dashboard/public/burnin-panel.html, public/js/burnin-widget.js | 3, 4          | 2          |
| 6     | burnin/cases/below/\*.yaml (17)                                                                   | 7, 8, 9       | 3, 4       |
| 7     | burnin/cases/walter/\*.yaml (10)                                                                  | 6, 8, 9       | 3, 4       |
| 8     | burnin/cases/sharding/\*.yaml (12)                                                                | 6, 7, 9       | 3, 4       |
| 9     | burnin/cases/e2e/\*.yaml (5)                                                                      | 6, 7, 8       | 3, 4       |
| 10    | scripts/burnin/lib/canary.sh, burnin.sh (kill subcommand)                                         | 11            | 3          |
| 11    | scripts/burnin/lib/cost.sh, lib/reconcile.sh                                                      | 10            | 3          |
| 12    | ~/.buildrunner/docs/burnin.md, SKILL.md (runbook section)                                         | —             | 10,11      |

**Waves:**

- **Wave A:** Phase 1
- **Wave B:** Phase 2
- **Wave C (parallel):** Phase 3 || Phase 4 || Phase 5
- **Wave D (parallel):** Phase 6 || Phase 7 || Phase 8 || Phase 9
- **Wave E (parallel):** Phase 10 || Phase 11
- **Wave F:** Phase 12

---

## Phases

### Phase 1: Foundation — schema, folder layout, plugin spec

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/burnin/schema.sql` (NEW) — `burnin_cases`, `burnin_runs`, `fix_requests`, `cost_estimates`
- `~/.buildrunner/burnin/cases/` (NEW; subfolders `below/ walter/ sharding/ e2e/`)
- `~/.buildrunner/burnin/PLUGIN_SPEC.md` (NEW) — canonical YAML schema + assertion vocabulary
- `~/.buildrunner/dashboard/events.db` (MODIFY) — apply schema.sql via idempotent migration

**Blocked by:** None

**Deliverables:**

- [x] `burnin_cases` table: `id TEXT PK`, `group`, `title`, `state`, `consecutive_greens INT`, `fix_attempts INT`, `last_run_at`, `last_result`, `last_failure`, `promoted_at`, `retired_at`, `quarantined BOOL`, `plugin_path TEXT`.
- [x] `burnin_runs` table: `run_id PK`, `case_id FK`, `condition` (cold/warm/loaded), `started_at`, `duration_ms`, `exit_code`, `passed BOOL`, `executed_on`, `assertion_failures JSON`, `stdout_excerpt`, `stderr_excerpt`.
- [x] `fix_requests` table: `case_id`, `created_at`, `attempt_n`, `failure_artifact`, `status`, `diff_sha`, `resolver`.
- [x] `cost_estimates` table: `run_id FK`, `tokens_in`, `tokens_out`, `estimated_claude_usd`, `savings_usd`.
- [x] PLUGIN_SPEC.md defines required YAML fields and assertion DSL.
- [x] Validator `validate-plugin.sh` fails closed on unknown fields.
- [x] Migration idempotent.

**Success Criteria:** `sqlite3 events.db ".schema burnin_cases"` returns expected columns; validator rejects malformed YAML and accepts reference YAML.

---

### Phase 2: Runner core — `burnin.sh` with state machine + DB I/O

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/burnin.sh` (NEW) — top-level router
- `~/.buildrunner/scripts/burnin/lib/state.sh` (NEW) — state transitions
- `~/.buildrunner/scripts/burnin/lib/runner.sh` (NEW) — executes one case under one condition
- `~/.buildrunner/scripts/burnin/lib/db.sh` (NEW) — SQLite helpers
- `~/.buildrunner/scripts/burnin/lib/assert.py` (NEW) — assertion DSL evaluator

**Blocked by:** Phase 1

**Deliverables:**

- [x] Subcommands: `status`, `run [case|group|all]`, `list`, `show <case>`, `reset <case>`, `register`.
- [x] Valid state transitions enforced; invalid transitions logged + aborted.
- [x] `run` captures stdout/stderr/exit/latency/executed_on, evaluates assertions, writes `burnin_runs`, advances or resets `consecutive_greens`.
- [x] Promotion gate: 3 greens × 3 conditions → `promoted`.
- [x] Failure: write `fix_requests` row, flip to `fixing`.
- [x] All writes through `db.sh`.
- [x] `status` prints 5-line summary + 3 most recent reds.

**Success Criteria:** `burnin run all` with zero plugins is a clean no-op; with one reference plugin, runs end-to-end.

---

### Phase 3: Execution — 3-condition matrix + bounded fix loop

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/scripts/burnin/lib/conditions.sh` (NEW)
- `~/.buildrunner/scripts/burnin/lib/fix-loop.sh` (NEW)
- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY — wire conditions + `fix` subcommand)

**Blocked by:** Phase 2

**Deliverables:**

- [x] Cold = real service restart via SSH (e.g., `ollama stop/start`), not a sleep.
- [x] Warm = one throwaway call first.
- [x] Loaded = 5 concurrent decoy calls during test.
- [x] Per-plugin condition opt-in; default all three.
- [x] Fix loop: failure artifact + 40-line diff cap + 3-attempt budget + 4th failure → `needs_human`.
- [x] Diff applied to worktree branch, operator approves unless `BR3_BURNIN_AUTOAPPLY=1`.
- [x] Every attempt logged to `fix_requests`.

**Success Criteria:** Deliberately-broken plugin fails → `fixing` → Claude called → diff approved → re-run green. ✅ Verified: rejected-diff path, NEEDS_HUMAN short-circuit, diff-cap reject → budget exhaustion → `needs_human`, condition opt-in (1/1 vs 3/3).

---

### Phase 4: `/burnin` Claude Code skill (default action = ADD)

**Status:** PLANNED
**Files:**

- `~/.claude/skills/burnin/SKILL.md` (NEW)
- `~/.claude/skills/burnin/scripts/add.sh` (NEW)

**Blocked by:** Phase 2

**Deliverables:**

- [ ] `/burnin` (no arg) → ADD: 4 questions, scaffolded YAML, first-run validation, commit on green.
- [ ] Subcommands: `status`, `run [target]`, `fix <id>`, `show <id>`, `remove <id>`, `quarantine <id>`, `unquarantine <id>`, `retire <id>`, `report`, `kill`.
- [ ] Skill frontmatter: `model: claude-opus-4-7`, `effort: xhigh`, adaptive thinking summarized.
- [ ] Validates YAML via `validate-plugin.sh` before first run.
- [ ] `report` writes `.buildrunner/burnin-report-<YYYYMMDD>.md`.
- [ ] `remove` archives DB rows as tombstones (never hard-deletes).
- [ ] `kill` refuses unless all retired.

**Success Criteria:** `/burnin` (no arg) produces a working plugin end-to-end in under 2 minutes with no manual YAML editing.

---

### Phase 5: Dashboard integration — SSE event + panel + widget

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/integrations/burnin.mjs` (NEW) — matches `below.mjs` / `walter.mjs` pattern
- `~/.buildrunner/dashboard/public/burnin-panel.html` (NEW)
- `~/.buildrunner/dashboard/public/js/burnin-widget.js` (NEW)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — register `burnin.update` + 5s poll

**Blocked by:** Phase 2

**Deliverables:**

- [x] `burnin.mjs` polls every 5s, emits SSE `burnin.update` on diff (no spam).
- [x] Top strip: counters (Untested / Probation / Promoted / Retired) + red badge for `needs_human` + global progress bar.
- [x] Group tabs: Below · Walter · Sharding · E2E.
- [x] Case table: id, state, 3-dots greens indicator, last run, expandable failure.
- [x] Per-case sparkline: last 20 runs as green/red pips.
- [x] Alert feed: running log of state transitions.
- [x] Kill button disabled until all retired.
- [x] Self-contained ES module, no framework.

**Success Criteria:** 3 cases in varied states render correctly; kill button stays disabled.

---

### Phase 6: Plugin library — Below (17 cases)

**Status:** ✅ COMPLETE — 17/17 cases written, validated, registered (0 SMOKE; all real callers)
**Files:**

- `~/.buildrunner/burnin/cases/below/` (17 YAML files)

**Blocked by:** Phase 3, Phase 4

**Deliverables — one case per site:**

- [x] `below-embed` — `embed_batch` real corpus, asserts 768-d vectors + `executed_on=below`.
- [x] `below-schema-classifier` — known-label fixture, asserts label match.
- [x] `below-log-cluster` — 200-line sample, asserts cluster count range.
- [x] `below-semantic-cache` — insert + retrieve, asserts hit.
- [x] `below-commit-msg` — real staged diff → conventional commit, asserts regex.
- [x] `below-reranker` — `/retrieve` with reranker on, asserts top_k reorder + metric emission.
- [x] `below-log-cluster-commands` — log fixture piped through log-cluster.py stdin helper, covers /dbg /sdb /diag /device /query clustering step (Phase 7). Note: below-context-bundle merged here; context-bundle has no discrete CLI surface, covered by reranker case.
- [x] `below-auto-remediate` — seeded fixable issue, asserts remediation through Below.
- [x] `below-dep-triage` — stale dep fixture, asserts triage output.
- [x] `below-pr-body` — fixture commit range, asserts output shape.
- [x] `below-ci-classifier` — hybrid mode, novel pattern triggers qwen3:8b path, asserts category label.
- [x] `below-test-failure-cluster` — multi-failure fixture, asserts clusters + outliers preserved.
- [x] `below-semantic-cache-integration` — ClaudeCacheWrapper double-call, asserts hit on second call.
- [x] `below-intel-collect` — synthetic snapshot, asserts extract + categorize schema.
- [x] `below-llmlingua-compress` — autopilot prompt fixture, asserts 2x+ compression ratio.
- [x] `below-ai-code-review-prefilter` — clean vs flagged diff, asserts severity routing.
- [x] `below-spec-drift` — mutated spec fixture, asserts drift_detected=true.

Real caller (no mocks), 3 conditions, `promote_after: 3`, realistic `timeout_s`.

**Success Criteria:** All 17 validate + enter `probation` on first run.

---

### Phase 7: Plugin library — Walter (10 cases)

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/burnin/cases/walter/` (10 YAML files)

**Blocked by:** Phase 3, Phase 4

**Deliverables:**

- [x] `walter-auto-restart` — kill Walter, assert respawn within 30s.
- [x] `walter-repo-freshness` — sentinel commit, assert hash-based detection.
- [x] `walter-trigger-logs` — fire auto-save-session.sh, assert persisted log.
- [x] `walter-blocking-gate` — inject test failure, assert gate blocks.
- [x] `walter-lockwood-reporting` — run test, assert Lockwood row written.
- [x] `walter-race-rc1` — two concurrent `/api/run`, assert serialization.
- [x] `walter-race-rc4` — `_test_loop` + manual `/api/run` overlap, assert single execution.
- [x] `walter-race-rc5` — concurrent SQLite writes, assert no corruption.
- [x] `walter-race-rc6` — concurrent runs, assert temp-file isolation.
- [x] `walter-sparklines-render` — dashboard pull, assert sparkline data.

**Success Criteria:** Every RC case actually fires the race window.

---

### Phase 8: Plugin library — Cluster sharding + visibility (12 cases)

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/burnin/cases/sharding/` (12 YAML files)

**Blocked by:** Phase 3, Phase 4

**Deliverables:**

- [x] `sharding-process-detector-mac` — Muddy, assert workload entries.
- [x] `sharding-process-detector-win` — Below, assert Windows branch returns entries.
- [x] `sharding-health-busy-state` — `/health`, assert `busy_state` in {idle,active,saturated} + `cpu_pct` present.
- [x] `sharding-dashboard-chip` — saturate node, assert chip flips to `saturated` within 10s.
- [x] `sharding-router-overflow-walter` — saturate Walter, dispatch test, assert lands on Lockwood or Lomax.
- [x] `sharding-router-overflow-otis` — saturate Otis, dispatch phase, assert overflow picks it up.
- [x] `sharding-shard-collector-merge` — 3 shard XMLs → collect, assert merged count = sum.
- [x] `sharding-br-test-fanout` — 3-shard project, assert shards on 3 different nodes.
- [x] `sharding-otis-typecheck` — assert LaunchAgent `tsc --watch` running.
- [x] `sharding-sse-node-workload` — start workload, assert SSE event fires.
- [x] `sharding-poll-env-override` — set `BR3_NODE_HEALTH_POLL_MS=2000`, assert interval change.
- [x] `sharding-cluster-check-passthrough` — `cluster-check.sh --health-json`, assert no field dropping.

**Success Criteria:** Router-overflow cases actually saturate under `loaded` and verify shard destination.

---

### Phase 9: Plugin library — Cross-node E2E (5 cases)

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/burnin/cases/e2e/` (5 YAML files)

**Blocked by:** Phase 3, Phase 4

**Deliverables:**

- [x] `e2e-autopilot-otis-dispatch` — no-op phase, assert executes on Otis.
- [x] `e2e-research-jimmy-roundtrip` — `/research` query, assert Jimmy `/retrieve` hit.
- [x] `e2e-ship-full-gate` — `/ship --full` clean branch, assert all 8 gates pass.
- [x] `e2e-begin-spec-drift` — mutate spec mid-build, assert drift flagged.
- [x] `e2e-offline-fallback` — Below offline, assert fallback + fallback log.

Long `timeout_s` (5–15 min); only `cold` + `warm` conditions.

**Success Criteria:** Each round-trips the cluster + verifies cross-node artifact.

---

### Phase 10: Canary mode + retire lifecycle + kill switch

**Status:** PLANNED
**Files:**

- `~/.buildrunner/scripts/burnin/lib/canary.sh` (NEW)
- `~/.buildrunner/scripts/burnin/burnin.sh` (MODIFY — `canary` + `kill`)
- `~/.buildrunner/scripts/burnin/launch.plist` (NEW)

**Blocked by:** Phase 3

**Deliverables:**

- [ ] `burnin canary` iterates promoted cases, warm condition only.
- [ ] Failure → demote to `probation`, reset greens, alert feed event.
- [ ] 14 clean canary runs → auto-retire.
- [ ] LaunchAgent at 03:00 daily; logs to `~/.buildrunner/logs/burnin-canary.log`.
- [ ] `burnin kill` requires all retired, uninstalls LaunchAgent, writes tombstone.
- [ ] Flake tag: red→green→red within 5 → `flaky: true`, bump `promote_after: 5`.

**Success Criteria:** Promoted case that fails canary demotes; kill refuses unless all retired.

---

### Phase 11: Cost estimation + Anthropic usage reconciliation

**Status:** PLANNED
**Files:**

- `~/.buildrunner/scripts/burnin/lib/cost.sh` (NEW)
- `~/.buildrunner/scripts/burnin/lib/reconcile.sh` (NEW)
- `~/.buildrunner/burnin/rate-table.yaml` (NEW — versioned pricing)

**Blocked by:** Phase 3

**Deliverables:**

- [ ] Below-offload run records tokens_in/out, computes `estimated_claude_usd`.
- [ ] Report line: "Estimated weekly savings" — always labeled `(estimated)`.
- [ ] Dashboard shows running estimate.
- [ ] Weekly cron fetches Anthropic `/v1/usage`, diffs, writes drift %.
- [ ] Drift >25% → dashboard counter yellow + alert feed note.
- [ ] Rate-table updates tracked in git.

**Success Criteria:** Report prints labeled estimate; reconciliation runs cleanly.

---

### Phase 12: Documentation + operator runbook

**Status:** PLANNED
**Files:**

- `~/.buildrunner/docs/burnin.md` (NEW)
- `~/.claude/skills/burnin/SKILL.md` (MODIFY — append runbook)

**Blocked by:** Phase 10, Phase 11

**Deliverables:**

- [ ] `docs/burnin.md`: add flow, YAML schema reference, state diagram, troubleshooting, kill procedure.
- [ ] SKILL.md runbook: common operator flows.
- [ ] `~/.buildrunner/README.md` entry linking to docs.
- [ ] Decision-log entry stamps go-live + initial case count.

**Success Criteria:** New operator can add a case + drive to promotion using only `docs/burnin.md`.

---

## Non-Goals

- Not a replacement for unit tests in `tests/cluster/`.
- Not a CI gate; pre-push hook unchanged.
- Not a load tester; `loaded` is contention, not scale.
- Does not own Anthropic billing truth; reconciliation is the source of record.
- No new inference paths; every case exercises an existing caller.

## Risks

| Risk                                             | Mitigation                                            |
| ------------------------------------------------ | ----------------------------------------------------- |
| Uncapped Claude fix loop introduces new bugs     | 3-attempt + 40-line cap + worktree + human approval   |
| Flaky cases churn between states                 | Flake tag bumps `promote_after` to 5                  |
| Rate table drifts                                | Weekly reconciliation; yellow alert >25% drift        |
| Plugin library grows untracked                   | `/burnin remove` only path; tombstones kept           |
| Canary burns tokens on retired cases             | `retired` excluded; kill removes LaunchAgent          |
| Dashboard panel contends with other integrations | Own SSE channel + DB tables; matches existing pattern |

## Rollout

1. Ship Phase 1–5 as framework — no cases yet.
2. Ship Phase 6 (Below) — dogfood add flow.
3. Ship Phases 7–9 in parallel once shape validated.
4. Ship Phase 10 after ≥5 cases reach `promoted`.
5. Ship Phase 11 last.
6. Ship Phase 12 at end.

## Success = all-retired

Build done when `/burnin status` shows `Retired: 44 / 44`, `/burnin kill` run, LaunchAgent uninstalled, only telemetry + drift alarm active.
