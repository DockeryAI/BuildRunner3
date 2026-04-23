# Plan: burnin-harness

**Created:** 2026-04-23
**Owner:** byronhudson
**Purpose:** Validate every Below offload site, Walter sentinel feature, cluster sharding behavior, and cross-node E2E path against real work, via a plugin-per-case harness with bounded Claude auto-fix, state-machine promotion, canary retirement, and full dashboard integration. `/burnin` is the single Claude Code skill entry point — default action is ADD a new case.

## Goals

1. Prove every cluster feature built to date actually works on real work (not just unit tests).
2. Auto-heal known-failure classes via bounded Claude fix loop (≤3 attempts, diff-capped, human-gated).
3. Reach a signed "done" state where active testing retires to telemetry-only — zero ongoing overhead.
4. Make adding or removing a test a single YAML file, no code changes.
5. Integrate with existing BR3 dashboard (events.db, SSE bus, integrations/\*.mjs pattern).

## Non-Goals

- Not a CI gate; does not block push.
- Not a replacement for pytest suites in `tests/cluster/`.
- Not a load tester; `loaded` condition is contention, not scale.
- Does not own Anthropic billing truth; cost numbers are always labeled estimates.

## Validation Surface (44 cases)

- **Below offload (17):** every site from BUILD_below-offload — embed, schema classifier, log cluster, semantic cache, commit-msg, reranker, context-bundle, auto-remediate, dep-triage, PR body, dbg/sdb/diag/device/query, ai-code-review prefilter, spec-drift.
- **Walter sentinel (10):** auto-restart, repo freshness (hash-based), trigger logging, blocking gate, Lockwood reporting, race conditions RC1/RC4/RC5/RC6, sparkline rendering.
- **Cluster sharding + visibility (12):** process detector (mac + win), /health busy_state, dashboard chip saturation, router overflow to Lockwood/Lomax, shard XML merge, br-test.sh fan-out, Otis tsc --watch, SSE node.workload, poll env override, cluster-check.sh passthrough.
- **Cross-node E2E (5):** autopilot→Otis dispatch, /research→Jimmy roundtrip, /ship full-gate, /begin spec-drift, offline fallback.

## State Machine

untested → probation → (fixing ↔ probation) → promoted → retired

- Promotion: 3 consecutive greens across {cold, warm, loaded} conditions.
- Canary (promoted): 1 warm-condition run/day; failure demotes.
- Retirement: 14 consecutive clean canary runs.
- Kill switch: all 44 retired → uninstall canary LaunchAgent, telemetry-only.
- Flake handling: red→green→red toggle within 5 runs → `flaky: true`, `promote_after: 5`.

## Fix Loop Guardrails

- Max 3 attempts per case; 4th failure → `needs_human`.
- Diff size cap 40 lines (configurable per plugin).
- Worktree isolation; diff review required unless `BR3_BURNIN_AUTOAPPLY=1`.
- Every fix attempt logged to `fix_requests` with SHA + resolver.

## /burnin Skill Surface

- `/burnin` (no arg) → default ADD flow: 4 questions, scaffolded YAML, first-run validation, commit.
- `/burnin status | run [target] | fix <id> | show <id> | list | remove <id> | quarantine <id> | unquarantine <id> | retire <id> | report | kill`

## Dashboard Integration

- New SSE event `burnin.update`, emitted by `dashboard/integrations/burnin.mjs` on state change.
- New panel `dashboard/public/burnin-panel.html` + widget `dashboard/public/js/burnin-widget.js`.
- Renders: top counters, group tabs, case table with 3-green-dots indicator, per-case 20-run sparkline, alert feed, global progress bar, kill button (disabled until all retired).

## Cost Estimation

- Per-run tokens_in/out → estimated Claude USD via versioned `rate-table.yaml`.
- Weekly reconciliation against Anthropic `/v1/usage`; drift >25% turns counter yellow.
- All dashboard labels say "estimated" — never "savings."

## Parallelization

- Wave A: 1
- Wave B: 2
- Wave C (parallel): 3 || 4 || 5
- Wave D (parallel): 6 || 7 || 8 || 9
- Wave E (parallel): 10 || 11
- Wave F: 12

## Phases

### Phase 1: Foundation — schema, folder layout, plugin spec

Create `~/.buildrunner/burnin/schema.sql` with tables `burnin_cases`, `burnin_runs`, `fix_requests`, `cost_estimates`. Create folder structure `~/.buildrunner/burnin/cases/{below,walter,sharding,e2e}/`. Author `PLUGIN_SPEC.md` defining required YAML fields and assertion DSL. Build `validate-plugin.sh` that fails closed on unknown fields. Apply schema via idempotent migration to `dashboard/events.db`.

### Phase 2: Runner core — `burnin.sh` with state machine + DB I/O

Build `burnin.sh` top-level router with subcommands `status`, `run`, `list`, `show`, `reset`. Split state transitions into `lib/state.sh` (enforces valid transitions, logs invalid to decision log). Put run execution in `lib/runner.sh` (capture stdout/stderr/exit/latency/executed_on, evaluate assertions, write rows). Centralize SQLite access in `lib/db.sh`. Promotion gate flips state to `promoted` on 3 greens × 3 conditions.

### Phase 3: Execution — 3-condition matrix + bounded fix loop

`lib/conditions.sh` exposes `prep_cold`, `prep_warm`, `prep_loaded`. Cold means a real service restart (e.g. `ollama stop/start` via SSH), not a sleep. Loaded fans out 5 concurrent decoy calls. `lib/fix-loop.sh` invokes Claude with failure artifact + 40-line diff cap; 3-attempt budget per case; 4th failure → `needs_human`. Diff applies to worktree branch; operator approves unless `BR3_BURNIN_AUTOAPPLY=1`. Every attempt logged to `fix_requests`.

### Phase 4: `/burnin` Claude Code skill (default action = ADD)

`~/.claude/skills/burnin/SKILL.md` with default action = ADD: 4 questions (group, id, command, primary assertion) → scaffolded YAML → validation → first run → commit on green. Subcommands `status`, `run`, `fix`, `show`, `remove`, `quarantine`, `unquarantine`, `retire`, `report`, `kill`. `remove` archives DB rows as tombstones. `kill` refuses unless all retired. Interactive add flow in `skills/burnin/scripts/add.sh`.

### Phase 5: Dashboard integration — SSE event + panel + widget

`dashboard/integrations/burnin.mjs` polls `burnin_cases` every 5s, emits SSE `burnin.update` on diff. Register event in `dashboard/events.mjs`. Panel `dashboard/public/burnin-panel.html` + widget `public/js/burnin-widget.js` render: top counters, group tabs (Below/Walter/Sharding/E2E), case table with 3-green-dot indicator, per-case 20-run sparkline, alert feed for state transitions, global progress bar, kill button (disabled until all retired).

### Phase 6: Plugin library — Below (17 cases)

One YAML per site in `~/.buildrunner/burnin/cases/below/`: embed, schema-classifier, log-cluster, semantic-cache, commit-msg, reranker, context-bundle, auto-remediate, dep-triage, pr-body, dbg, sdb, diag, device, query, ai-code-review-prefilter, spec-drift. Each exercises the real caller (no mocks), all 3 conditions, asserts `executed_on=below` plus site-specific success signal.

### Phase 7: Plugin library — Walter (10 cases)

One YAML per Walter surface in `~/.buildrunner/burnin/cases/walter/`: auto-restart, repo-freshness (hash-based, not mtime), trigger-logs, blocking-gate, lockwood-reporting, race-rc1/rc4/rc5/rc6 (actually fire concurrent work to hit the race window), sparklines-render.

### Phase 8: Plugin library — Cluster sharding + visibility (12 cases)

One YAML per sharding feature in `~/.buildrunner/burnin/cases/sharding/`: process-detector-mac, process-detector-win, health-busy-state, dashboard-chip, router-overflow-walter, router-overflow-otis, shard-collector-merge, br-test-fanout, otis-typecheck, sse-node-workload, poll-env-override, cluster-check-passthrough. Router overflow cases actually saturate a node under `loaded` condition.

### Phase 9: Plugin library — Cross-node E2E (5 cases)

One YAML per cluster-wide path in `~/.buildrunner/burnin/cases/e2e/`: autopilot→Otis dispatch, /research→Jimmy roundtrip, /ship full-gate, /begin spec-drift, offline-fallback. Long `timeout_s` (5–15 min). Only cold + warm conditions; skip loaded (E2E is expensive).

### Phase 10: Canary mode + retire lifecycle + kill switch

`lib/canary.sh` iterates promoted cases once under warm condition. Failure demotes to probation + resets greens. 14 clean canary runs → auto-retire. LaunchAgent runs `burnin canary` at 03:00 daily. `burnin kill` requires all retired, then uninstalls LaunchAgent + writes tombstone. Flake tag triggers on red→green→red within 5 runs — escalates `promote_after` to 5.

### Phase 11: Cost estimation + Anthropic usage reconciliation

`lib/cost.sh` records tokens_in/out per Below-offload run, computes `estimated_claude_usd` from versioned `rate-table.yaml`. Dashboard + report always label "estimated" — never "savings". `lib/reconcile.sh` fetches Anthropic `/v1/usage` weekly, diffs vs. estimate, writes drift %. Drift >25% turns counter yellow + alert feed notes "rate table stale."

### Phase 12: Documentation + operator runbook

`~/.buildrunner/docs/burnin.md` covers: add flow, plugin YAML schema, state machine diagram, troubleshooting (stuck in `fixing`, canary demotion loops, drift >25%), kill procedure. Append runbook section to SKILL.md for common operator flows. README entry linking to docs. Decision-log entry stamps go-live date + initial case count.

## Definition of Done

`/burnin status` shows `Retired: 44/44`, `/burnin kill` has been run, canary LaunchAgent uninstalled, only telemetry + drift alarm active. Decision-log entry stamps the go-dark date.

## Risks + Mitigations

| Risk                                     | Mitigation                                                     |
| ---------------------------------------- | -------------------------------------------------------------- |
| Claude fix loop introduces new bugs      | 3-attempt + 40-line cap + worktree + human approval by default |
| Flake churn between probation / promoted | Flake tag escalates `promote_after` to 5                       |
| Rate table drift                         | Weekly reconciliation; yellow alert >25% drift                 |
| Canary burns tokens on retired cases     | Retired state excluded; kill switch removes cron entirely      |
| Plugin library grows untracked           | `/burnin remove` is only supported path; tombstones kept in DB |
