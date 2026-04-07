# Build: Dashboard Intelligence Layer

**Created:** 2026-04-06
**Status:** ✅ COMPLETE
**Deploy:** local-service — `pkill -f "node events.mjs"; cd ~/.buildrunner/dashboard && node events.mjs`

## Overview

Turn The Band's cluster dashboard (localhost:4400) from an interactive status board into a full development control plane. Web terminals, diff review with auto Claude Code review, token tracking, session visibility, build health sparklines. Every panel shows data AND lets you act on it.

Research basis: `~/Projects/research-library/docs/techniques/dev-cluster-dashboard-actions.md` (60+ sources, Proxmox/Conductor/Codex/Buildkite/Datadog patterns).

## Parallelization Matrix

| Phase | Key Files                                                    | Can Parallel With | Blocked By |
| ----- | ------------------------------------------------------------ | ----------------- | ---------- |
| 1     | events.mjs (WebSocket), index.html (terminal modal)          | —                 | —          |
| 2     | integrations/sessions.mjs (NEW), index.html (sessions panel) | 1                 | —          |
| 3     | integrations/usage.mjs (NEW), index.html (token stats)       | 1, 2              | —          |
| 4     | integrations/reviews.mjs (NEW), index.html (diff viewer)     | 1, 2, 3           | —          |
| 5     | reviews.mjs (MODIFY), auto-review-diff.sh (NEW)              | 1, 2, 3           | 4          |
| 6     | events.mjs (health endpoint), index.html (sparklines)        | 1, 2, 3, 4        | —          |
| 7     | events.mjs (rollback endpoint), index.html (inline buttons)  | 1, 2, 3, 4, 6     | —          |
| 8     | events.mjs (processes endpoint), index.html (process table)  | 1, 2, 3, 4, 6, 7  | —          |

## Phases

### PHASE 1: Web Terminal

**Status:** ✅ COMPLETE
**Goal:** Click any node in the dashboard, get a live terminal in the browser. No SSH keys, no remembering IPs.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — add terminal modal with xterm.js)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — terminal styles)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add WebSocket terminal proxy endpoint)
- `~/.buildrunner/dashboard/package.json` (MODIFY — add xterm.js + ws deps)

**Blocked by:** None

**Deliverables:**

- [x] WebSocket endpoint `/ws/terminal/:node` that spawns SSH session to target node
- [x] xterm.js terminal component in modal (opens from node detail or context menu)
- [x] Terminal resize handling (cols/rows sync)
- [x] Auto-close on disconnect, reconnect option
- [x] Muddy terminal connects to local shell (no SSH)

**Success Criteria:** Click Lockwood in dashboard → terminal opens → run commands on Lockwood from the browser.

---

### PHASE 2: Session Grid

**Status:** ✅ COMPLETE
**Goal:** See every active Claude Code session across all nodes in one view.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — add Sessions panel)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — session grid styles)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add `/api/sessions` endpoint)
- `~/.buildrunner/dashboard/integrations/sessions.mjs` (NEW — polls nodes for active Claude Code sessions)

**Blocked by:** None
**After:** Phase 1 (logical sequence, CAN parallelize)

**Deliverables:**

- [x] Integration that polls each node for active Claude Code processes via SSH (ps + session files)
- [x] `/api/sessions` endpoint returning session list across all nodes
- [x] Sessions panel showing: node, project, branch, state, elapsed time, last activity
- [x] Click session → detail modal with recent output, token estimate
- [x] Auto-refresh every 15s via SSE

**Success Criteria:** Dashboard shows "3 active sessions: Muddy (BuildRunner3), Otis (Synapse), Below (workfloDock)" with live status.

---

### PHASE 3: Token & Cost Tracking

**Status:** ✅ COMPLETE
**Goal:** Per-session and per-node token usage with budget warnings. Know before you hit the wall.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — add token stats to header + session grid)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — token bar styles)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add `/api/usage` endpoint)
- `~/.buildrunner/dashboard/integrations/usage.mjs` (NEW — reads usage-estimate.json from each node)

**Blocked by:** None
**After:** Phase 2 (uses session data)

**Deliverables:**

- [x] Integration that reads `~/.buildrunner/usage-estimate.json` from each node (SSH + local)
- [x] `/api/usage` endpoint returning per-node token usage
- [x] Header stat showing total cluster token spend today
- [x] Per-session token estimate in session grid
- [x] Budget bar (green → yellow at 80% → red at 90%) with auto-pause indicator
- [x] SSE event `usage.warning` when any node hits 85%

**Success Criteria:** Header shows "Tokens: 142K / 500K" with color-coded bar. Yellow warning when Otis hits 82%.

---

### PHASE 4: Diff Review Queue

**Status:** ✅ COMPLETE
**Goal:** When autopilot finishes phases on remote nodes, diffs appear in the dashboard for review. Approve or reject from the browser.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — add Review Queue panel + diff viewer)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — diff viewer styles, green/red lines)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add `/api/reviews`, `/api/reviews/:id/approve`, `/api/reviews/:id/reject`)
- `~/.buildrunner/dashboard/integrations/reviews.mjs` (NEW — watches for completed remote phases, fetches diffs)

**Blocked by:** None
**After:** Phase 2

**Deliverables:**

- [x] Integration that watches `build.phase_complete` events from remote nodes
- [x] Auto-fetches `git diff` from remote branches via SSH
- [x] Review Queue panel showing pending diffs with file count, lines added/removed
- [x] Click review → diff viewer modal with green/red line-by-line display
- [x] Approve button (triggers merge on Muddy) and Reject button (marks as rejected)
- [x] Badge count on panel header showing pending reviews

**Success Criteria:** Otis finishes Phase 3 of Synapse → "1 pending review" appears → click → see diff → approve → merged.

---

### PHASE 5: Auto Code Review on Diffs

**Status:** ✅ COMPLETE
**Goal:** Claude Code automatically reviews remote diffs before you see them. Issues flagged inline.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — add review annotations to diff viewer)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — annotation styles)
- `~/.buildrunner/dashboard/integrations/reviews.mjs` (MODIFY — trigger auto-review after fetching diff)
- `~/.buildrunner/scripts/auto-review-diff.sh` (NEW — runs Claude Code review on a diff, outputs structured findings)

**Blocked by:** Phase 4 (needs diff viewer)

**Deliverables:**

- [x] Script that runs Claude Code `/review` on a branch diff and outputs JSON findings
- [x] Auto-triggers when a new review enters the queue
- [x] Findings displayed as annotations in diff viewer (critical=red, warning=yellow, info=blue)
- [x] Summary line: "2 warnings, 0 critical" shown on review card
- [x] Critical findings block the Approve button (must acknowledge to override)

**Success Criteria:** Otis finishes a phase → diff appears with "1 critical: SQL injection in user input handler" pinned to line 47 → Approve button disabled until acknowledged.

---

### PHASE 6: Build Health Sparklines

**Status:** ✅ COMPLETE
**Goal:** At-a-glance health for every project — sparklines showing pass/fail, speed, frequency.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — add sparklines to builds table and node cards)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — sparkline styles)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add `/api/builds/health` endpoint)

**Blocked by:** None
**After:** Phase 4

**Deliverables:**

- [x] `/api/builds/health` endpoint querying build history from events DB (last 30 per project)
- [x] Canvas-based sparkline renderer (30 bars: height=duration, color=pass/fail)
- [x] Sparklines added to Active Builds table rows
- [x] Reliability percentage (pass rate over 30 builds) shown per project
- [x] Speed trend (avg duration, arrow up/down vs previous 30)

**Success Criteria:** Each build row has a sparkline showing green/red bars. "Synapse: 87% reliability, avg 4.2m, trending faster."

---

### PHASE 7: Inline Log Actions + One-Click Rollback

**Status:** ✅ COMPLETE
**Goal:** Restart and rollback buttons inside the log viewer. Deploy previous build to Lomax without rebuilding.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — add action buttons to Prod Logs panel and builds table)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add `/api/projects/:name/rollback` endpoint)

**Blocked by:** None

**Deliverables:**

- [x] Restart button inline in Prod Logs panel header (restarts project dev server or service)
- [x] Rollback button per build in builds table (redeploys previous successful build to Lomax)
- [x] `/api/projects/:name/rollback` endpoint triggering Lomax to deploy previous build
- [x] Confirmation dialog before rollback
- [x] Toast notification with rollback result

**Success Criteria:** See error in Prod Logs → click Restart → service restarts → logs clear. Click Rollback → previous version deployed to Lomax.

---

### PHASE 8: Node Process Viewer

**Status:** ✅ COMPLETE
**Goal:** See exactly what's using CPU and memory on each node — process list with resource usage, sortable, killable.

**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — add process list to node detail modal)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — process table styles)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — add `/api/nodes/:name/processes` endpoint)

**Blocked by:** None
**After:** Phase 1

**Deliverables:**

- [x] `/api/nodes/:name/processes` endpoint that SSHs to node and runs `ps aux --sort=-%cpu | head -20`
- [x] Process table in node detail modal showing: PID, user, CPU%, MEM%, command
- [x] Sortable by CPU or MEM (client-side toggle)
- [x] Highlight Claude Code processes, node_semantic, node_tests etc in accent color
- [x] Kill button per process (with confirmation) via `ssh kill <PID>`
- [x] Auto-refresh button to re-poll

**Success Criteria:** Click Lockwood → node detail → see "node_semantic.py: 12% CPU, 340MB" and "chromadb: 8% CPU, 280MB" in a sortable table. Can kill a runaway process from the browser.

---

## Out of Scope (Future / Tier 2)

- AI query in Cmd+K (Headlamp pattern — "show failing builds" answered by Lockwood)
- Batch dispatch (select multiple builds, dispatch to multiple nodes)
- Campaign/phase timeline view (BUILD spec progress across all phases)
- Env var viewer/editor per project
- Node resource history graphs (CPU/MEM over time, not just current)
- Mobile-responsive layout

---

## Session Log

[Will be updated by /begin]
