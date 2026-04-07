# Build: Dashboard Command Center

**Created:** 2026-04-06
**Status:** BUILD COMPLETE — All 7 Phases Done
**Deploy:** local-service — `pkill -f "node events.mjs"; cd ~/.buildrunner/dashboard && node events.mjs &`

## Overview

Remote-accessible dev control plane for The Band via `band.taskwatcher.ai`. Sidebar navigation, workspace switching (Dashboard/Intelligence/Terminal/Builds), full web terminal with command toolbar, intelligence feed with Lockwood proxy, build management with autopilot dispatch, mobile responsive. Cloudflare Tunnel + Access for secure remote access from any device.

**Architecture:** Vanilla HTML/JS/CSS at `~/.buildrunner/dashboard/`. No React, no build step. All files external to git repo — no worktree isolation for autopilot.

**Adversarial review:** 4 blockers found and resolved pre-spec. Key fixes: Lockwood proxy endpoints for remote access, workspace container pattern for incremental phase fills, exponential backoff on terminal reconnect.

**READ FIRST:**

1. `~/.buildrunner/dashboard/events.mjs` — 49KB Node.js server, 19 endpoints, 10 integration modules
2. `~/.buildrunner/dashboard/public/index.html` — 2,756 lines, tightly coupled render functions + inline handlers
3. `~/.buildrunner/dashboard/public/styles.css` — CSS variables define color system

**DO NOT:**

- Use React, Vue, or any framework — this is vanilla HTML/JS
- Reference `ui/src/components/` — that's an old dead React dashboard
- Use worktree isolation — all files are external to the project
- Break existing render functions (renderBuilds, renderNodes, renderSessions, renderReviews, etc.)
- Break existing event handlers (dispatch, rollback, kill, approve/reject)
- Remove CSS variables (--bg-_, --text-_, --accent-\*, --green, --red, --yellow)

## Parallelization Matrix

| Phase | Key Files                                      | Can Parallel With | Blocked By |
| ----- | ---------------------------------------------- | ----------------- | ---------- |
| 1     | `~/.cloudflared/config.yml`, events.mjs (CORS) | 2                 | —          |
| 2     | index.html (REWRITE), styles.css (REWRITE)     | 1                 | —          |
| 3     | index.html, styles.css, events.mjs             | —                 | 2          |
| 4     | index.html, styles.css, events.mjs             | —                 | 2          |
| 5     | index.html, styles.css                         | —                 | 4          |
| 6     | styles.css, index.html                         | —                 | 2, 4       |
| 7     | index.html, events.mjs                         | —                 | 4          |

**Optimal:** Wave 1 (P1+P2 parallel) → Wave 2 (P3, then P4) → Wave 3 (P5+P7) → Wave 4 (P6)

## Phases

### Phase 1: Cloudflare Tunnel + Auth

**Status:** ✅ COMPLETE
**Files:**

- `~/.cloudflared/config.yml` (NEW) ⚠️ external
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — CORS headers) ⚠️ external
- `~/Library/LaunchAgents/com.cloudflare.band-tunnel.plist` (NEW) ⚠️ external

**Blocked by:** None

**Deliverables:**

- [x] `cloudflared tunnel create band` + `cloudflared tunnel route dns band band.taskwatcher.ai`
- [x] Config file: tunnel ID, credentials path, ingress rule `localhost:4400`, WebSocket support enabled
- [x] launchd plist: auto-start on Muddy boot, restart on failure, keep-alive
- [x] Cloudflare Access application: `band.taskwatcher.ai/*`, Google IdP, Byron's email only
- [x] CORS in events.mjs: allow `band.taskwatcher.ai` origin on all API endpoints + WebSocket upgrade headers. Note: Cloudflare Access handles ALL auth — no OAuth, no callbacks, no middleware in events.mjs. It's a network-level gate before traffic reaches the server
- [x] Validation: phone → `band.taskwatcher.ai` → Google login → dashboard loads → terminal WebSocket connects over WSS

**Success Criteria:** Open `band.taskwatcher.ai` on phone, Google login, dashboard renders, terminal connects.

---

### Phase 2: Dashboard Redesign — Layout + Navigation

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (REWRITE) ⚠️ external
- `~/.buildrunner/dashboard/public/styles.css` (REWRITE) ⚠️ external

**Blocked by:** None
**After:** Phase 1 (can parallelize — different files)

**Deliverables:**

- [ ] Sidebar: 56px icon rail — Dashboard, Intelligence, Terminal, Builds icons. Active highlight. Red badge dot on Intelligence when unread alerts
- [ ] 4 workspace containers: `#ws-dashboard`, `#ws-intel`, `#ws-terminal`, `#ws-builds` with JS switching (no page reload)
- [ ] Topbar: "BR3 The Band" + workspace label + token stat + SSE indicator + uptime + ⌘K shortcut
- [ ] Dashboard workspace: cluster strip (6 node cards), KPI row (4 cards: builds/tokens/sessions/reviews), 2-column panel grid
- [ ] Alerts panel on dashboard: empty container for Phase 3 to populate with surfaced intel/deals + node down/unreachable alerts
- [ ] Node health alerting: if any node goes offline, becomes unreachable, or loses power — show a persistent red alert banner at the top of the dashboard with the node name, last seen time, and "Unreachable" status. Alert stays until the node comes back online. Check via the existing `/api/nodes` health polling (already runs every 30s). No new backend needed — frontend compares node status on each poll and triggers the alert
- [ ] Empty workspace containers for Intel/Terminal/Builds — placeholder text until later phases fill them
- [ ] Color system: navy-tinted dark mode (`#0b0f14`), tinted grays, colorblind-safe status colors, `rgba` borders
- [ ] Preserve xterm.js CDN imports (xterm 5.5.0 + addon-fit 0.10.0) — these are already in the current index.html and must survive the rewrite
- [ ] ALL existing render functions migrated: renderBuilds, renderNodes, renderSessions, renderReviews, renderDAG, renderEvents, renderSparklines, renderNodeHealth
- [ ] ALL existing event handlers migrated: dispatch, rollback, kill, approve/reject, terminal modal, ⌘K search
- [ ] ALL utility functions migrated: esc, timeAgo, showModal, showToast, apiAction

**Success Criteria:** Dashboard loads with sidebar. All existing panels render and function. Workspace icons show placeholders for unbuilt workspaces. Zero functionality regression.

---

### Phase 3: Intelligence Workspace

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — fill `#ws-intel`) ⚠️ external
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — intel styles) ⚠️ external
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — Lockwood proxy endpoints) ⚠️ external

**Blocked by:** Phase 2 (workspace containers must exist)

**Deliverables:**

- [ ] Proxy endpoints in events.mjs: `GET /api/proxy/intel/items`, `/api/proxy/intel/alerts`, `/api/proxy/deals/items`, `/api/proxy/deals/hunts`, `POST /api/proxy/intel/items/:id/read`, `POST /api/proxy/intel/items/:id/dismiss`, `POST /api/proxy/deals/items/:id/read`, `POST /api/proxy/deals/items/:id/dismiss` — all forward to Lockwood `http://10.0.1.101:8100`
- [ ] Sub-tab bar: Feed, Deals, Improvements, Hunts — tab switching within `#ws-intel`
- [ ] Feed tab: KPI row (total/critical/high/improvements/unread) + 2-column priority-sorted cards, filter dropdowns (source/priority/time), item actions (read/dismiss/source/"Build This")
- [ ] Deals tab: KPI row (hunts/tracked/exceptional/avg score) + hunt badges + deal cards with scores/verdicts, "Add Hunt" form
- [ ] Improvements tab: BR3 items with status lifecycle, "Build This" → switches to terminal workspace with `/setlist [prompt]` pre-filled
- [ ] Hunts tab: CRUD for deal watches — add/archive toggle
- [ ] Alert surfacing: critical+high intel + exceptional deals (score≥80) populate dashboard Alerts panel automatically
- [ ] Auto-refresh: items 30s, alerts 15s, sidebar badge update

**Success Criteria:** Intelligence workspace shows live Lockwood data via proxy. Works from `band.taskwatcher.ai`. "Build This" switches to terminal with command.

---

### Phase 4: Terminal Workspace

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — fill `#ws-terminal`) ⚠️ external
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — terminal workspace styles) ⚠️ external
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — terminal session tracking) ⚠️ external

**Blocked by:** Phase 2 (workspace containers)

**Deliverables:**

- [ ] Full-viewport xterm.js terminal in `#ws-terminal` (promoted from existing modal)
- [ ] Tab bar: multiple terminals open simultaneously, new tab dropdown picks node
- [ ] Project-scoped launch: when opened from Builds workspace, terminal `cd`s to project directory
- [ ] Command toolbar above terminal: `/begin`, `/autopilot go`, `/autopilot go --cluster`, `/setlist`, `/review`, `ctrl+c`, `tab`, `↑↓`, `esc` — click inserts text
- [ ] Contextual toolbar: pre-fills commands from Intelligence "Build This" or Builds actions
- [ ] Split view toggle: terminal 60% left + reference panel 40% right (loads BUILD spec content via fetch)
- [ ] Auto-reconnect with exponential backoff (1s → 2s → 4s → 8s → max 30s), status indicator (green/red/spinner)
- [ ] Session persistence: open tabs stored in localStorage, restored on page reload

**Success Criteria:** Terminal workspace → new tab → Muddy → interactive Claude Code session in browser. Command toolbar works. Split view shows BUILD spec. Reconnects on disconnect.

---

### Phase 5: Build Workspace

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — fill `#ws-builds`) ⚠️ external
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — build workspace styles) ⚠️ external

**Blocked by:** Phase 4 (build actions open terminal)

**Deliverables:**

- [ ] Build list: all builds from registry with status badges, progress bars, phase counts, node assignment
- [ ] Build detail: click build → expandable phase list with per-phase status, deliverables (parsed from BUILD spec via API), files, success criteria
- [ ] Build actions: "Autopilot Go" → opens terminal with `/autopilot go`, "Autopilot Cluster" → `/autopilot go --cluster`, "Pause" → `POST /api/builds/:id/status`, "Resume" → terminal with `/autopilot --resume`
- [ ] Phase actions: "Begin" → terminal with `/begin`, "Skip" → API, "View Diff" → existing diff viewer
- [ ] "New Build" button → opens terminal with `/spec`
- [ ] Dispatch: node selector dropdown + dispatch button (existing `/api/builds/:id/dispatch`)
- [ ] DAG visualization moved from dashboard workspace to builds workspace

**Success Criteria:** Click build → see phases → click "Autopilot Go" → terminal opens with command running.

---

### Phase 6: Mobile Responsive

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — media queries) ⚠️ external
- `~/.buildrunner/dashboard/public/index.html` (MODIFY — bottom tab bar, touch toolbar) ⚠️ external

**Blocked by:** Phases 2, 4 (layout + terminal must exist)

**Deliverables:**

- [x] Sidebar → bottom tab bar on `< 768px` — 4 icons with labels
- [x] Cluster strip: horizontal scroll, min-width 140px per card
- [x] KPI cards: 2×2 grid on mobile
- [x] Terminal: fills viewport, command toolbar docked above keyboard (position: fixed bottom)
- [x] Touch targets: 44px minimum on all buttons and interactive elements
- [x] Command toolbar buttons: 48px height for touch
- [x] Single column panel stack on mobile, full width
- [x] Replace existing breakpoints (1200px, 800px) with 768px + 480px

**Success Criteria:** `band.taskwatcher.ai` on iPhone → bottom bar → workspaces → terminal fills screen → toolbar works with thumb.

---

### Phase 7: Session Management + Node Actions

**Status:** ✅ COMPLETE
**Files:**

- `~/.buildrunner/dashboard/public/index.html` (MODIFY — actions UI) ⚠️ external
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — action endpoints + cache fix) ⚠️ external

**Blocked by:** Phase 4 (terminal workspace)

**Deliverables:**

- [ ] Session detail modal: PID, CPU, MEM, elapsed, project, branch, last activity
- [ ] Clone session: opens terminal tab cd'd to same project + branch
- [ ] Kill session: SIGTERM via SSH with confirmation dialog
- [ ] Node context menu (right-click desktop / long-press mobile): Open Terminal, View Logs, Swap Accounts, Reset Node
- [ ] "View Logs" → opens terminal tailing `.buildrunner/*.log` on that node
- [ ] "Swap Accounts" → runs swap script on target node via SSH
- [ ] Session cache invalidation on backend errors (fix stale data from adversarial review)

**Success Criteria:** Right-click node → Open Terminal → connected. Click session → Kill → terminated.

---

## Out of Scope (Future)

- Plan editor in browser (use terminal for plan iteration)
- Multi-user auth (single user — Byron's email only)
- Push notifications to phone
- Persistent terminal across server restarts (needs tmux)
- Dashboard theme customization UI
- Chat-style Claude interface (terminal is the interface)

---

## Session Log

[Will be updated by /begin]
