# BUILD: Cluster Build Orchestration

**Project:** BuildRunner3 (BR3 framework)
**Created:** 2026-04-05
**Rewritten:** 2026-04-05 — reordered for impact-first, automation-compounding execution
**Amended:** 2026-04-06 — added Phases 35-38 (dispatch reliability, intel pipeline, Walter testing, dashboard polish)
**Status:** ✅ COMPLETE — All 38 Phases Done
**Impact:** GLOBAL — every BR3 project gets automatic cluster dispatch + intelligence

---

## 0. Purpose (For a New Claude)

**What this spec does:** Turns the Blues Cluster from dumb infrastructure into an automated development team. Five nodes are online (Lockwood/memory, Walter/testing, Otis/builder, Lomax/staging+Supabase, Below/inference). They all work. But today almost nothing uses them automatically — skills ignore the cluster, commits don't trigger validation, Below's GPU sits idle, and context gets lost between sessions.

This build wires everything together in impact order: first make the daily workflow smarter (Below inference in skills, commit-triggered testing, institutional memory), then build the dispatch system (registry, auto-assignment, parallel builds), then add the dashboard for visibility.

**Key principle:** Every phase adds automation that subsequent phases USE. By Phase 5, the cluster is doing real work on every commit. By Phase 10, builds dispatch themselves. By Phase 20, you have a self-monitoring development factory.

**The Cluster (all online, all verified 2026-04-05):**

| Node                  | IP         | Role                                     | API            |
| --------------------- | ---------- | ---------------------------------------- | -------------- |
| Muddy (M5)            | 10.0.1.100 | Command — primary dev                    | localhost      |
| Lockwood (M2)         | 10.0.1.101 | Memory — sessions, notes, patterns       | :8100          |
| Walter (M2)           | 10.0.1.102 | Testing — continuous vitest + Playwright | :8100          |
| Otis (M2)             | 10.0.1.103 | Builder — headless Claude Code           | SSH only       |
| Lomax (M2)            | 10.0.1.104 | Staging — 11 projects + Supabase sandbox | :8100          |
| Below (Win i9+2080Ti) | 10.0.1.105 | Inference — Qwen 3 8B, 82 tok/s          | :8100 + :11434 |

**READ FIRST:**

1. `~/.buildrunner/cluster.json` — node definitions
2. `~/.buildrunner/scripts/cluster-check.sh` — node discovery (returns URL or empty)
3. `~/.claude/settings.json` — hooks (SessionStart, PostToolUse, Stop)
4. `~/.buildrunner/scripts/auto-save-session.sh` — fires on commit + session end
5. `~/.buildrunner/scripts/developer-brief.sh` — SessionStart context injection
6. `core/cluster/node_inference.py` — Below's FastAPI (classify/draft/summarize/gpu)
7. `core/cluster/node_tests.py` — Walter's FastAPI (results/coverage/flaky/run)
8. `core/cluster/node_staging.py` — Lomax's FastAPI (projects/build/preview)
9. `core/cluster/node_semantic.py` — Lockwood's FastAPI (brief/memory/notes/session)
10. Research: `~/Projects/research-library/docs/techniques/windows-headless-inference-supabase-server.md`

**DO NOT:**

- Break existing single-machine workflows
- Require the cluster to be online (graceful fallback to local-only)
- Hard-code node IPs anywhere (all reads from cluster.json via cluster-check.sh)

---

## BLOCK 1: IMMEDIATE AUTOMATION (Phases 1-6)

_Wire the cluster into daily workflow. Every phase here delivers value the same day it ships._

---

### PHASE 1: Commit-Triggered Cluster Validation

**Status:** ✅ COMPLETE

**Goal:** Every `git commit` on Muddy automatically triggers tests on Walter and build validation on Lomax. Results surface in the next brief or /begin call.

**Files to MODIFY:**

- `~/.buildrunner/scripts/auto-save-session.sh` — add 6 lines after the Lockwood session push:

```bash
# Trigger Walter test run
WALTER_URL=$("$HOME/.buildrunner/scripts/cluster-check.sh" test-runner 2>/dev/null)
[ -n "$WALTER_URL" ] && curl -s --max-time 3 -X POST "$WALTER_URL/api/run?project=$PROJECT" >/dev/null 2>&1 &

# Trigger Lomax build validation
LOMAX_URL=$("$HOME/.buildrunner/scripts/cluster-check.sh" staging-server 2>/dev/null)
[ -n "$LOMAX_URL" ] && curl -s --max-time 3 -X POST "$LOMAX_URL/api/projects/$PROJECT/build" >/dev/null 2>&1 &
```

**Acceptance:**

- `git commit` triggers Walter test run (verify via Walter `/api/results`)
- `git commit` triggers Lomax build validation (verify via Lomax `/api/projects/{name}/build/status`)
- Both fire-and-forget, never block the commit
- If Walter/Lomax offline, silently skip

---

### PHASE 2: Below Intelligence in Skills

**Status:** ✅ COMPLETE

**Goal:** Below's local inference replaces Claude API calls for mechanical tasks. Zero API cost, instant response, always available.

**Files to MODIFY:**

- `~/.claude/commands/spec.md` — at phase classification step, add:

```bash
BELOW_URL=$(~/.buildrunner/scripts/cluster-check.sh inference)
if [ -n "$BELOW_URL" ]; then
  CLASSIFICATION=$(curl -s --max-time 10 -X POST "$BELOW_URL/api/classify" \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"$PHASE_DESCRIPTION\",\"categories\":[\"backend\",\"frontend\",\"fullstack\",\"docs\",\"infra\",\"testing\",\"data-migration\"]}")
fi
```

- `~/.claude/commands/commit.md` — before drafting commit message, offer Below draft:

```bash
BELOW_URL=$(~/.buildrunner/scripts/cluster-check.sh inference)
if [ -n "$BELOW_URL" ]; then
  DIFF_SUMMARY=$(git diff --cached --stat | head -20)
  DRAFT=$(curl -s --max-time 15 -X POST "$BELOW_URL/api/draft" \
    -H "Content-Type: application/json" \
    -d "{\"prompt\":\"Write a concise git commit message for these changes: $DIFF_SUMMARY\"}")
fi
```

- `~/.buildrunner/scripts/developer-brief.sh` — add Below log summarization:

```bash
BELOW_URL=$("$CLUSTER_CHECK" inference 2>/dev/null)
if [ -n "$BELOW_URL" ] && [ -n "$LOG_PATTERNS" ]; then
  SUMMARY=$(curl -s --max-time 10 -X POST "$BELOW_URL/api/summarize" \
    -H "Content-Type: application/json" \
    -d "{\"text\":\"$LOG_PATTERNS\"}")
fi
```

- `~/.claude/commands/root.md` — add Below-powered failure explanation as first pass before Claude Opus analysis

**Acceptance:**

- `/spec` auto-classifies phases via Below (verify: no Claude tokens spent on classification)
- `/commit` offers Below-drafted commit message
- Developer brief shows Below-summarized log patterns
- `/root` uses Below for initial failure triage
- All fall back gracefully if Below offline

---

### PHASE 3: Skill Write-Back to Lockwood

**Status:** ✅ COMPLETE

**Goal:** Skills that discover useful information save it to Lockwood automatically. Builds institutional memory.

**Files to MODIFY (add Lockwood POST at end of each skill):**

- `~/.claude/commands/root.md` — after generating root-cause report:

```bash
NODE_URL=$(~/.buildrunner/scripts/cluster-check.sh semantic-search)
[ -n "$NODE_URL" ] && curl -s -X POST "$NODE_URL/api/memory/note" \
  -H "Content-Type: application/json" \
  -d "{\"topic\":\"root-cause: $SUMMARY\",\"content\":\"$FULL_REPORT\",\"project\":\"$PROJECT\",\"source\":\"root\"}"
```

- `~/.claude/commands/guard.md` — save governance violations
- `~/.claude/commands/review.md` — save review findings
- `~/.claude/commands/gaps.md` — save gap analysis results
- `~/.claude/commands/dead.md` — save dead code findings
- `~/.claude/commands/e2e.md` — push test results to Lockwood (Walter has them, but Lockwood needs cross-project view)

**Acceptance:**

- After `/root`, Lockwood has a note with the root cause
- After `/guard`, violations recorded
- After `/review`, findings recorded
- Future `/predict` and `/root` calls benefit from historical data
- Brief shows "X root causes, Y violations, Z reviews recorded" from Lockwood

---

### PHASE 4: Pre-Commit Cluster Gate

**Status:** ✅ COMPLETE

**Goal:** `/commit` checks Walter + Lomax before pushing. Prevents shipping broken code.

**Files to MODIFY:**

- `~/.claude/commands/commit.md` — before `git push`, add:

```bash
# Check Walter for test failures
WALTER_URL=$(~/.buildrunner/scripts/cluster-check.sh test-runner)
if [ -n "$WALTER_URL" ]; then
  RESULTS=$(curl -s --max-time 5 "$WALTER_URL/api/coverage?project=$PROJECT")
  PASS_RATE=$(echo "$RESULTS" | python3 -c "import sys,json; print(json.load(sys.stdin).get('pass_rate',1))")
  if [ "$PASS_RATE" != "1.0" ] && [ "$PASS_RATE" != "1" ]; then
    echo "⚠ Walter reports failing tests (pass_rate: $PASS_RATE)"
  fi
fi

# Check Lomax for build status
LOMAX_URL=$(~/.buildrunner/scripts/cluster-check.sh staging-server)
if [ -n "$LOMAX_URL" ]; then
  BUILD=$(curl -s --max-time 5 "$LOMAX_URL/api/projects/$PROJECT_LC/build/status")
  # Warn if build is failing
fi
```

- `~/.claude/commands/begin.md` — Step 6.5 (Verification Gate): add Lomax build check and Walter test trigger via `POST /api/run`

**Acceptance:**

- `/commit` warns before pushing if Walter has failing tests
- `/commit` warns if Lomax build is broken
- `/begin` verification gate triggers Walter test run and waits for result
- `/begin` checks Lomax build status
- Warnings only — never blocks (user decides)

---

### PHASE 4.5: Runtime Error Detection + Auto-Fix

**Status:** ✅ COMPLETE (built 2026-04-06)

**Goal:** BRLogger catches runtime errors. The log analyzer detects them within 30 seconds. macOS notification fires immediately. Alert pushed to Walter. If the error is a known fixable pattern (e.g. edge function not deployed), auto-fix runs automatically.

**Files MODIFIED:**

- `core/cluster/node_analysis.py` — Added:
  - `edge_function_error` pattern detection (400 from `/functions/v1/`)
  - `_send_macos_notification()` — fires macOS notification on critical/high patterns
  - `_push_alert_to_walter()` — pushes alert to Walter for brief integration
  - `_attempt_auto_fix()` — rule engine for automatic remediation
  - Rule 1: "Unknown action" + action exists in local code → `supabase functions deploy` automatically
  - `_alerted_fingerprints` set prevents duplicate alerts

- `core/cluster/node_tests.py` (Walter) — Added:
  - `POST /api/alert` — receives runtime alerts from log analyzer
  - `GET /api/alerts` — serves alerts for developer brief

- `~/.buildrunner/scripts/developer-brief.sh` — Added:
  - Queries Walter `/api/alerts` after test results
  - Shows runtime alerts with severity icons in session brief

**Auto-fix rules implemented:**

| Pattern                      | Diagnostic                               | Auto-Fix                     |
| ---------------------------- | ---------------------------------------- | ---------------------------- |
| Edge fn 400 "Unknown action" | Check if action exists in local index.ts | `supabase functions deploy`  |
| Auth refresh loop (>50x)     | Logged for investigation                 | Manual (needs investigation) |

**Flow:** `BRLogger → browser.log → node_analysis.py (30s) → detect → macOS notification + Walter alert + auto-fix attempt`

**Acceptance:**

- [x] Edge function 400 errors detected as `edge_function_error` pattern
- [x] macOS notification fires within 30 seconds of error
- [x] Alert pushed to Walter and visible via `/api/alerts`
- [x] Developer brief shows runtime alerts section
- [x] Auto-deploy fires when "Unknown action" detected and code exists locally
- [x] All verified end-to-end

---

### PHASE 5: Migration Safety Loop

**Status:** ✅ COMPLETE

**Goal:** `/begin` validates database migrations against Lomax's Supabase sandbox before pushing to prod.

**Files to MODIFY:**

- `~/.claude/commands/begin.md` — when phase touches `supabase/migrations/`:

```bash
LOMAX_URL=$(~/.buildrunner/scripts/cluster-check.sh staging-server)
if [ -n "$LOMAX_URL" ]; then
  echo "Testing migration against Lomax Supabase sandbox..."
  PGSSLMODE=disable supabase db push --dry-run \
    --db-url "postgresql://postgres:postgres@10.0.1.104:54322/postgres"
fi
```

**Acceptance:**

- Migration dry-run runs automatically when phase modifies `supabase/migrations/`
- Failures block the phase with clear error output
- Skipped gracefully if Lomax offline

---

### PHASE 6: Account Swap Fix + Usage Warning

**Status:** ✅ COMPLETE

**Goal:** Fix the broken `/swap` command and add proactive usage monitoring.

**Files to MODIFY:**

- `~/.buildrunner/scripts/br-swap-accounts.sh` — debug and fix the credential issue (likely stale backup keychain entries)
- `~/.buildrunner/scripts/br-account-setup.sh` — add token validation step

**Files to CREATE:**

- `~/.buildrunner/scripts/usage-monitor.sh` — tracks estimated token usage per session:
  - Count tool calls and estimate tokens from conversation length
  - Warn at 80% of estimated daily limit
  - Auto-suggest swap at 90%
  - Hook into `PostToolUse` with a lightweight check every N calls

- `~/.claude/hooks/usage-check.sh` — `PreToolUse` hook (runs on every tool call, must be <100ms):
  - Reads `~/.buildrunner/usage-estimate.json` (updated by auto-save)
  - If approaching limit: inject warning message
  - If over limit: suggest swap command

**Research needed:** Determine if Claude OAuth token response includes billing/usage data, or if we must estimate from conversation token counts.

**Acceptance:**

- `/swap` works reliably (both accounts swap on Muddy + Otis)
- Warning appears at 80% estimated usage
- Swap suggestion at 90%
- Never hit the wall without warning

---

## BLOCK 2: BUILD REGISTRY + DISPATCH (Phases 7-14)

_Foundation for autonomous multi-node builds. Each phase uses the automation from Block 1._

---

### PHASE 7: Registry Schema + Storage

**Status:** ✅ COMPLETE

**Goal:** Build the cluster-wide build registry.

**Files to CREATE:**

- `~/.buildrunner/cluster-builds.json` — master registry (see schema below)
- `~/.buildrunner/scripts/registry.mjs` — CLI for registry operations:
  - `registry add <build_id> <fields>` — register
  - `registry update <build_id> <fields>` — update status/progress
  - `registry list [--node X] [--status Y] [--project Z]` — query
  - `registry assign <build_id> <node>` — manual override
  - `registry remove <build_id>` — deregister
  - `registry suggest-node <build_id>` — compute ideal node (uses Below `/api/classify` for work type)
  - `registry ready-to-dispatch` — list builds with deps met + node available

**Registry schema:**

```typescript
interface ClusterBuild {
  build_id: string; // "{project}:{build_name}"
  project: string;
  project_path: string;
  build_name: string;
  spec_path: string;
  created_at: string;
  updated_at: string;
  assigned_node: string | null;
  assignment_reason: string;
  work_type: 'backend' | 'frontend' | 'fullstack' | 'docs' | 'infra' | 'testing' | 'data-migration';
  estimated_phases: number;
  phase_parallelism: 'sequential' | 'parallelizable' | 'mixed';
  depends_on: string[];
  blocks: string[];
  status:
    | 'registered'
    | 'queued'
    | 'dispatched'
    | 'running'
    | 'paused'
    | 'blocked'
    | 'complete'
    | 'failed';
  current_phase: number;
  total_phases: number;
  phases_complete: number;
  progress_pct: number;
  requires_user_gate: boolean;
  user_gate_phases: number[];
}
```

**Node assignment matrix:**

```typescript
const NODE_WORK_MATRIX = {
  muddy: { accepts: ['backend', 'frontend', 'fullstack', 'infra'], priority: 'command' },
  otis: { accepts: ['backend', 'frontend', 'fullstack'], priority: 'parallel' },
  walter: { accepts: ['testing'], priority: 'dedicated' },
  lomax: { accepts: ['infra', 'data-migration', 'testing'], priority: 'validation' },
  below: { accepts: ['backend', 'data-migration'], priority: 'heavy' },
};
```

**Below integration:** `registry suggest-node` calls Below `/api/classify` to determine work_type from the spec content. Free, instant, no Claude tokens.

**Acceptance:**

- Registry CRUD works via CLI
- `suggest-node` uses Below for classification
- File-lock prevents concurrent write corruption

---

### PHASE 8: Lockwood Mirror

**Status:** ✅ COMPLETE

**Goal:** Mirror registry to Lockwood so any node can query cluster-wide state.

**Files to CREATE:**

- `~/.buildrunner/scripts/registry-sync.mjs` — push local → Lockwood, pull Lockwood → local
- Lockwood API endpoint: `POST /api/registry/sync`

**Sync triggers:**

- Every `registry` CLI write → async push to Lockwood
- On any node, `registry list` → pull from Lockwood first (cached 30s)
- Lockwood down → use local file, log warning

**Acceptance:**

- Changes on Muddy visible from Otis via `registry list`
- Lockwood-down case: local reads still work

---

### PHASE 9: `/spec` Auto-Register

**Status:** ✅ COMPLETE

**Goal:** `/spec` automatically registers builds with the cluster orchestrator.

**Files to MODIFY:**

- `~/.claude/commands/spec.md` — at end of spec-writing:
  1. Below classifies work_type (Phase 2 already wired)
  2. `registry add` via bash
  3. `registry suggest-node` for assignment
  4. `registry assign` to commit
  5. Report: "Registered as {build_id}. Assigned to {node}."

**Also add:**

- `--register <spec_path>` flag to register existing specs
- `--register-all` to bulk-register across all projects

**Acceptance:**

- `/spec` outputs "Assigned to {node}" before finishing
- Existing specs registrable via `--register`

---

### PHASE 10: `/amend` Registry Update

**Status:** ✅ COMPLETE

**Goal:** Amendments update the registry.

**Files to MODIFY:**

- `~/.claude/commands/amend.md` — call `registry update` with new phase count, work_type if changed

---

### PHASE 11: Generalized Dispatch

**Status:** ✅ COMPLETE

**Goal:** `/autopilot` dispatches to any node, not just Otis.

**Files to CREATE:**

- `~/.buildrunner/scripts/dispatch-to-node.sh` — generalized from `dispatch-to-otis.sh`
- `~/.buildrunner/scripts/_dispatch-core.sh` — shared SSH + credential + health-check logic

**Files to REWRITE as thin wrappers:**

- `dispatch-to-otis.sh` → `exec dispatch-to-node.sh otis "$@"`
- `dispatch-phase-to-otis.sh` → `exec dispatch-phase-to-node.sh otis "$@"`

**Files to MODIFY:**

- `~/.claude/commands/autopilot.md`:
  - Check registry for assigned_node
  - If assigned elsewhere → dispatch via `dispatch-to-node.sh`
  - `--force-local` override
  - `--cluster` flag: dispatch all ready builds cluster-wide
  - `--dry-run`: show what would dispatch

**Acceptance:**

- `/autopilot` on Muddy for an Otis-assigned build dispatches automatically
- Progress streamed to terminal
- `--force-local` works

---

### PHASE 12: Progress Reporting

**Status:** ✅ COMPLETE

**Goal:** Running autopilot updates registry as phases complete.

**Files to MODIFY:**

- `~/.claude/commands/autopilot.md` — after each phase: `registry update` with progress, status, timestamp
- On failure: `status=failed`, auto-trigger `/root` via Below (Phase 2), save to Lockwood (Phase 3)

---

### PHASE 13: `/dash` Cluster View

**Status:** ✅ COMPLETE

**Goal:** `/dash` shows cluster-wide build status.

**Files to MODIFY:**

- `~/.claude/commands/dash.md` — add cluster sections:

```
CLUSTER BUILDS
┌─ Muddy ──────────────────┐  ┌─ Otis ──────────────────┐
│ workflodock:synapse  61%  │  │ synapse:intake     33%  │
└──────────────────────────┘  └──────────────────────────┘

QUEUED: 1 build waiting on dependencies
BELOW: Qwen 3 8B, 82 tok/s, GPU 28°C
WALTER: 2 test runs, 0 failures
LOMAX: 7 containers, 422MB, build OK
```

---

### PHASE 14: Dependency Resolution + Ready Queue

**Status:** ✅ COMPLETE

**Goal:** `/autopilot` without args picks next ready build.

**Files to CREATE:**

- `~/.buildrunner/scripts/next-ready-build.mjs` — returns build where deps met + node available

**Files to MODIFY:**

- `~/.claude/commands/autopilot.md` — no args → call `next-ready-build.mjs` → auto-dispatch

---

## BLOCK 3: RESILIENCE + INTELLIGENCE (Phases 15-20)

_Self-healing, governance, cross-node coordination._

---

### PHASE 15: User Gates + Cross-Project Waits

**Status:** ✅ COMPLETE

**Goal:** Builds pause at user-defined gates. Cross-project dependencies verified.

**Files to MODIFY:**

- `autopilot.md` — on gate phase: `status=paused`, notification, wait for `/autopilot --resume`
- Before each phase: verify `waits_for_deployment` URLs return 200

---

### PHASE 16: Node Health Integration

**Status:** ✅ COMPLETE

**Files to MODIFY:**

- `cluster-check.sh` — add `--health-json` returning structured health
- `registry.mjs` — `assign` considers CPU load, memory, current build count

---

### PHASE 17: Failure Handling + Auto-Root

**Status:** ✅ COMPLETE

**Goal:** Failed builds auto-trigger root-cause analysis via Below + Lockwood.

**Flow:** phase_failed → Below `/api/summarize` (instant triage) → Lockwood search for similar past failures → attach report to registry → notification

**Files to MODIFY:**

- `autopilot.md` — on failure: trigger Below + Lockwood, save report, offer retry/reassign

---

### PHASE 18: Pre-Dispatch Governance

**Status:** ✅ COMPLETE

**Goal:** Before any build dispatches, auto-run `/guard` + `/gaps` + `/predict` + `/impact`.

**Files to MODIFY:**

- `autopilot.md` — before phase 1 dispatch:
  1. `/guard` validates governance
  2. `/gaps` scans for spec gaps
  3. `/predict` estimates difficulty (uses Lockwood build history)
  4. `/impact` checks cross-project (uses Lockwood semantic search)
  5. Critical findings block dispatch

---

### PHASE 19: Background Daemon

**Status:** ✅ COMPLETE

**Goal:** Each node polls registry and auto-picks ready builds.

**Files to CREATE:**

- `~/.buildrunner/scripts/cluster-daemon.mjs` — launchd/systemd service per node
- `~/.buildrunner/cluster-daemon-config.json` — per-node auto_dispatch enable/disable

---

### PHASE 20: Retroactive Bulk Registration

**Status:** ✅ COMPLETE

**Goal:** Register all existing BUILD specs across all projects.

**Files to CREATE:**

- `~/.buildrunner/scripts/registry-bootstrap.sh` — scans all projects, registers unregistered specs, infers status from phase markers

---

## BLOCK 4: DASHBOARD + VISIBILITY (Phases 21-30)

_Web UI, notifications, observability. Built on top of all the automation from Blocks 1-3._

---

### PHASE 21: Event-Sourced Backend

**Status:** ✅ COMPLETE

Append-only event log. SSE streaming. SQLite FTS5 index. Events from all nodes.

Event types: `build.*`, `node.*`, `test.result` (Walter), `staging.*` (Lomax), `intelligence.*` (Below), `governance.*`

### PHASE 22: Walter Dashboard Integration

**Status:** ✅ COMPLETE

Walter test results as first-class dashboard data. Per-build test panel. Flaky warnings. Coverage deltas.

### PHASE 23: Lomax Dashboard Integration

**Status:** ✅ COMPLETE

Auto-deploy successful builds to Lomax staging. Preview URLs. Validation status badges.

### PHASE 24: Lockwood Dashboard Integration

**Status:** ✅ COMPLETE

Semantic search across code, builds, failures, decisions. "Similar Past Failures" panel. Cmd+K search.

### PHASE 25: Below Dashboard Integration

**Status:** ✅ COMPLETE

Below-powered intelligence on dashboard: failure explanations, log summaries, phase difficulty predictions, anomaly detection.

### PHASE 26: Web Dashboard UI

**Status:** ✅ COMPLETE

SvelteKit + React Flow. DAG view. Build detail. Node health. Live SSE log tail. Command palette.

Served at `http://muddy.local:4400`.

### PHASE 27: Slim TUI Refactor

**Status:** ✅ COMPLETE

Reduce Ink dashboard to status-only for SSH. Web dashboard handles everything else.

### PHASE 28: macOS Notifications

**Status:** ✅ COMPLETE

Native notifications for: user gates, build failures, governance violations, dependency unblocked.

### PHASE 29: Parallelism Recommender

**Status:** ✅ COMPLETE

Dashboard suggests when to parallelize. Auto-dispatch if config allows.

### PHASE 30: BRLogger Prod Debug Panel

**Status:** ✅ COMPLETE

Live BRLogger streams in dashboard per deployed build. Cross-correlation button.

### PHASE 31: Decisions Log Integration

**Status:** ✅ COMPLETE

Decisions tab per build. Global timeline. Every approve/reject/reassign recorded.

### PHASE 32: Research Library Integration

**Status:** ✅ COMPLETE

Auto-fetch relevant research per phase. Citation-grade references.

### PHASE 33: Dashboard Observability

**Status:** ✅ COMPLETE

Self-monitoring: event volume, dispatch latency, node uptime, SSE reconnects.

### PHASE 34: Documentation + Config

**Status:** ✅ COMPLETE

User guide. Config reference. Skill docs updated.

---

## Build Order

**Block 1 (days 1-3):** 1 → 2 → 3 → 4 → 5 → 6
**Block 2 (days 4-8):** 7 → 8 → 9 → 10 → 11 → 12 → 13 → 14
**Block 3 (days 9-12):** 15 → 16 → 17 → 18 → 19 → 20
**Block 4 (days 13-20):** 21 → 22 → 23 → 24 → 25 → 26 → 27 → 28 → 29 → 30 → 31 → 32 → 33 → 34

**Parallelization:** Phases 2+3 can run in parallel. Phases 22-25 can run in parallel. Otis can handle backend phases while Muddy handles frontend.

---

## Risk Register

| Risk                              | Mitigation                                             |
| --------------------------------- | ------------------------------------------------------ |
| Lockwood down                     | Local file fallback + graceful degradation             |
| Below offline                     | Fall back to Claude Haiku for utility calls            |
| Walter/Lomax offline              | Skip validation, log warning                           |
| Wrong node assignment             | Manual `--reassign` command                            |
| Registry corruption               | File lock + JSON validation + backup before write      |
| Account exhaustion mid-build      | Phase 6 usage monitoring + proactive swap              |
| Network partition during dispatch | Retry with backoff; stale dispatches timeout           |
| Cluster disabled mid-build        | `BR3_CLUSTER=off` runs local, existing workflow intact |

---

## BLOCK 6: SESSION FIXES (Phases 35-38)

_Issues discovered during 2026-04-06 session. Dispatch reliability, node expansion, pipeline activation, dashboard polish._

---

### PHASE 35: Dispatch Reliability + Node Expansion _(added: 2026-04-06)_

**Status:** ✅ COMPLETE
**Goal:** Make remote dispatch reliable (retry on no-work), expand builder pool to 3 nodes (Muddy + Otis + Lomax), fix Below WSL dispatch, and make autopilot chain all phases in one agent.
**Blocked by:** None

**Deliverables:**

- [ ] Add retry logic to `dispatch-to-node.sh` — after `claude -p`, check remote `git diff --stat`; if no changes, retry once with hardened prompt including "Do NOT ask questions, commit when done"; if still nothing, exit 5 (no-work) so autopilot falls back to local _(added: 2026-04-06)_
- [ ] Install Claude CLI on Lomax (`npm install -g @anthropic-ai/claude-code`), sync OAuth credentials via `sync_credentials "lomax"`, add `parallel-builder` as secondary role in `cluster.json` _(added: 2026-04-06)_
- [ ] Add `parallel-builder` as secondary role for Below in `cluster.json`, fix WSL dispatch path to use root user (not byron) _(added: 2026-04-06)_
- [ ] Update `/autopilot` skill agent dispatch to pass ALL remaining phases to a single agent with chaining instructions, instead of spawning one agent per phase _(added: 2026-04-06)_

**Success Criteria:** Dispatch to Otis/Lomax/Below with retry. Autopilot chains 5+ phases in one agent without manual re-launch.

---

### PHASE 36: Intel Pipeline Activation _(added: 2026-04-06)_

**Status:** ✅ COMPLETE
**Goal:** Wire the intelligence workspace to live data from Lockwood/Below instead of mock data. Activate the full intel pipeline.
**Blocked by:** Phase 35 (Below must be dispatchable for classification)

**Deliverables:**

- [ ] Add Lockwood proxy endpoints to `events.mjs`: `/api/proxy/intel/items`, `/api/proxy/deals/items`, `/api/proxy/intel/items/:id/read`, `/api/proxy/deals/items/:id/dismiss` — all forward to Lockwood `http://10.0.1.101:8100` _(added: 2026-04-06)_
- [ ] Replace mock data arrays in `~/.buildrunner/dashboard/public/js/ws-intel.js` with fetch calls to proxy endpoints, with fallback to empty state when Lockwood offline _(added: 2026-04-06)_
- [ ] Activate intel pipeline scheduled jobs — source scraping → Below classification → Lockwood storage → dashboard display _(added: 2026-04-06)_

**Success Criteria:** Intelligence workspace shows live data from Lockwood. New intel items appear within 30s of pipeline run. Mock data removed.

---

### PHASE 37: Walter Commit-Triggered Testing _(added: 2026-04-06)_

**Status:** ✅ COMPLETE
**Goal:** Wire Walter to automatically run tests on commit and report results to Lockwood for dashboard health tracking.
**Blocked by:** None

**Deliverables:**

- [ ] Set up git post-receive hook or file watcher on Walter that runs `vitest run` + `playwright test` against changed projects when commits land _(added: 2026-04-06)_
- [ ] Report test results back to Lockwood via `POST /api/memory/tests` for build health tracking and dashboard sparklines _(added: 2026-04-06)_

**Success Criteria:** Commit on Muddy → Walter runs tests within 30s → results visible in dashboard health sparklines.

---

### PHASE 38: Dashboard Polish + Spec Hygiene _(added: 2026-04-06)_

**Status:** ✅ COMPLETE
**Goal:** Fix dashboard console errors, backfill health data, standardize BUILD spec formats, clean up stale dispatch artifacts.
**Blocked by:** None

**Deliverables:**

- [ ] Fix 4 console errors in dashboard `index.html` / `events.mjs` (identified in Playwright screenshots throughout session) _(added: 2026-04-06)_
- [ ] Backfill existing health events in `events.db` with phase names extracted from BUILD specs _(added: 2026-04-06)_
- [ ] Standardize BUILD spec status format across all 13 specs: `✅ COMPLETE` for done, `not_started` for pending, `🚧 in_progress` for active _(added: 2026-04-06)_
- [ ] Clean up stale `.dispatch-worktrees/` from all repos on Muddy and Otis; add `.dispatch-worktrees` to `.gitignore` in all projects _(added: 2026-04-06)_

**Success Criteria:** Zero console errors in Playwright. All BUILD specs use canonical status format. No stale worktree directories.

---

## Acceptance Criteria Summary

- [x] Every commit triggers Walter tests + Lomax build validation (Phase 1)
- [x] Below classifies phases, drafts commits, summarizes logs (Phase 2)
- [x] Skills write findings back to Lockwood (Phase 3)
- [x] `/commit` warns on failing tests/builds (Phase 4)
- [x] Migrations dry-run on Lomax before prod (Phase 5)
- [x] Account swap works + proactive warning (Phase 6)
- [x] Registry tracks all builds cluster-wide (Phase 7)
- [x] `/spec` auto-registers with node assignment (Phase 9)
- [x] `/autopilot` dispatches to correct node (Phase 11)
- [x] `/dash` shows cluster-wide status (Phase 13)
- [x] Failed builds auto-analyze via Below + Lockwood (Phase 17)
- [x] Governance checks run before every dispatch (Phase 18)
- [x] Web dashboard with live SSE updates (Phase 26)
- [x] Dispatch retries on no-work, Lomax + Below as builders (Phase 35)
- [x] Intel workspace wired to live Lockwood/Below data (Phase 36)
- [x] Walter commit-triggered testing with Lockwood reporting (Phase 37)
- [x] Dashboard console errors fixed, spec formats standardized (Phase 38)
