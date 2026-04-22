# /ship — Gated Delivery Pipeline

`/ship` turns `git push` into a gated delivery pipeline. Every gate has a bounded
self-healing fix loop. Routine failures auto-recover; real failures surface with an
actionable run URL.

---

## Quick Start

```bash
# Full pipeline (default)
/ship

# Skip review + docs gates (faster, for non-critical branches)
/ship --fast

# See what would run without executing
/ship --dry-run

# Resume after fixing a failure
/ship --resume

# Weekly stats
/ship stats
```

---

## Flags

| Flag        | Behavior                                                                              |
| ----------- | ------------------------------------------------------------------------------------- |
| `--full`    | All gates: preflight, rebase, review, test, docs, log-scan, commit, publish (default) |
| `--fast`    | Skip review and docs gates                                                            |
| `--dry-run` | Print gate sequence and planned actions; no side effects                              |
| `--resume`  | Resume from last failed gate; skips already-passed gates when SHA unchanged           |
| `stats`     | Print weekly rollup from telemetry                                                    |

---

## Exit Codes

| Code | Meaning                                      |
| ---- | -------------------------------------------- |
| 0    | All gates passed, push succeeded             |
| 1    | Gate failed after healing budget exhausted   |
| 2    | Blocked by scope guard or diff-cap violation |
| 3    | Sentinel stale or missing                    |
| 4    | Branch policy requires confirmation          |
| 5    | CI heal self-disabled (3 attempts exhausted) |

---

## Gate Sequence

```
preflight → rebase → review → test → docs → log-scan → ship-commit → publish
```

Each gate: exit 0=pass, 1=fail, 2=skip. On fail: healing loop fires (max 2 attempts, 2s gap).

| Gate          | What it does                                            | Healing strategy       |
| ------------- | ------------------------------------------------------- | ---------------------- |
| `preflight`   | Stashes uncommitted changes, checks for merge conflicts | stash restore          |
| `rebase`      | Fetches origin, rebases onto origin/main                | rebase retry           |
| `review`      | Wraps auto-review-diff.sh; two-pass findings + filter   | linter auto-fix        |
| `test`        | Runs project test suite (vitest/jest/pytest)            | lint + format auto-fix |
| `docs`        | Checks for undocumented exports; CHANGELOG advisory     | no-op (advisory)       |
| `log-scan`    | Scans diff for debug artifacts, hardcoded secrets       | linter auto-fix        |
| `ship-commit` | Stages all + commits if uncommitted changes exist       | none                   |
| `publish`     | Push + PR create/update via gh CLI; launches CI watcher | retry                  |

---

## Configuration

Config file: `~/.buildrunner/scripts/ship/ship-config.yaml`

Key settings:

```yaml
diff_cap_lines: 200 # max lines a heal can change
stale_window_seconds: 1800 # sentinel freshness window
escalation_budget: 2 # max heal attempts per gate
```

Project-local overrides: `.buildrunner/governance/ship-rules.yaml`

---

## Environment Variables

| Variable                    | Effect                                                   |
| --------------------------- | -------------------------------------------------------- |
| `BR3_SHIP_AUTOHEAL=force`   | Skip main/release confirmation on auto-heal (logged)     |
| `BR3_SHIP_DRY=1`            | Equivalent to `--dry-run`                                |
| `BR3_SHIP_FAST=1`           | Equivalent to `--fast`                                   |
| `BR3_AUTOPILOT_SHIP=off`    | Disable autopilot post-phase auto-ship                   |
| `BR3_BEGIN_SHIP=off`        | Disable /begin post-completion auto-ship                 |
| `BR3_SHIP_BYPASS_PREPUSH=1` | Emergency push bypass (logged to autoheal-overrides.log) |

---

## Push-Surface Routing Table

The pre-push hook `50-ship-gate.sh` is the universal enforcement point. Every push
from any source (raw git, `gh`, IDE buttons, scripts) is gated. Command-level routing
is the UX layer so users see a clean error rather than a blocked push.

| Surface                  | Routing                                                         |
| ------------------------ | --------------------------------------------------------------- |
| `git push` (any variant) | Pre-push hook `50-ship-gate.sh`                                 |
| `gh pr create`           | Pre-push hook                                                   |
| IDE push buttons         | Pre-push hook                                                   |
| `/commit`                | Routes to `/ship --fast` in Step 7 before push                  |
| `/begin` final phase     | Step 7.6 post-completion hook → `/ship --fast`                  |
| Autopilot final phase    | `autopilot-phase-hook.sh` → `/ship --fast`                      |
| Future skill that pushes | Must call `ship-runner.sh run`; pre-push hook catches otherwise |

### Adding a new push path

When writing a skill or script that calls `git push`:

1. Call `~/.buildrunner/scripts/ship/ship-runner.sh run --fast` before the push.
2. If the runner fails, surface the gate error to the user — do not bypass.
3. The pre-push hook (`50-ship-gate.sh`) is the safety net, but command-level routing
   is the UX requirement so users see a clean error message.
4. Document the new surface in `.buildrunner/governance/ship-rules.yaml` under
   `push_surfaces`.

---

## Self-Healing

The fix-orchestrator runs when a gate fails:

1. Attempt 1: linter auto-fix (`eslint --fix`, `ruff --fix`)
2. 2-second gap
3. Attempt 2: formatter auto-fix (`prettier`, `black`) or parallel worktree mode

Scope guard blocks healing of protected files:
`*.sql`, `governance.yaml`, `supabase/migrations/**`, `api/auth.py`, `src/**/auth/**`,
`CLAUDE.md` (on main/release), `.env`, `.env.*`, generated files.

Diff cap: 200 lines max (excluding lockfiles, dist/, build/).

On main/release branches: `BR3_SHIP_AUTOHEAL=force` required, or confirmation prompt.

---

## /amend and Push Paths

As of this spec, `/amend` does NOT push. If `/amend` ever gains a push path, it must
route through `/ship` first. The pre-push hook enforces this as a hard backstop.
Any future skill that adds `git push` must route to `/ship` — document it here.

---

## CI Watching

After `publish` succeeds, a background watcher (`watch-ci.sh`) monitors GitHub Actions:

- Polls every 30 seconds (max 1 hour)
- Classifies failures: fixable (lint/format/flaky playwright) vs real (type errors, broken tests)
- Fixable failures: invokes `ci-heal.sh` (3-attempt budget per PR)
- Real failures: surfaces run URL with one-line notification, no further action
- Budget exhausted: disables auto-heal for the branch until next `/ship` run

---

## Telemetry

Metrics emitted to Lockwood via `lockwood-metrics.sh`. Local JSONL fallback when
Lockwood is offline (never fails a gate).

Drift detection: heal rate rising >20% week-over-week writes to
`.buildrunner/ship/drift-alerts.json`.

```bash
/ship stats           # weekly summary
```

---

## Troubleshooting

**Push blocked: sentinel missing**
Run `/ship` (or `/ship --fast`) to generate a valid sentinel.

**Push blocked: head_sha mismatch**
You committed after running `/ship`. Run `/ship --resume` to re-gate with the new SHA.

**Push blocked: gates not passed**
Check which gates are missing: `~/.buildrunner/scripts/ship/ship-sentinel.sh read`
Run `/ship --resume` to run only missing gates.

**Heal scope denied**
The fix diff touched a protected file. Fix manually and run `/ship --resume`.

**CI heal disabled**
3 heal attempts exhausted. Run `/ship` fresh to reset the budget.

**Emergency bypass** (logged and audited):

```bash
BR3_SHIP_BYPASS_PREPUSH=1 git push
```
