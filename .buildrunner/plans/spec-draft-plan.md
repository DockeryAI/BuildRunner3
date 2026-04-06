# Spec Draft: Dashboard Command Center

## Phase 1: Cloudflare Tunnel + Auth
Files: ~/.cloudflared/config.yml (NEW), ~/.buildrunner/dashboard/events.mjs (MODIFY CORS), ~/Library/LaunchAgents/com.cloudflare.band-tunnel.plist (NEW)
Goal: band.taskwatcher.ai serves dashboard with Google auth
Dependencies: None

## Phase 2: Dashboard Redesign — Layout + Navigation
Files: ~/.buildrunner/dashboard/public/index.html (REWRITE), ~/.buildrunner/dashboard/public/styles.css (REWRITE)
Goal: Sidebar nav, workspace switching, new visual design, preserve all existing functionality
Dependencies: None (can parallel Phase 1)

## Phase 3: Intelligence Workspace
Files: ~/.buildrunner/dashboard/public/index.html (MODIFY), ~/.buildrunner/dashboard/public/styles.css (MODIFY), ~/.buildrunner/dashboard/events.mjs (MODIFY — add proxy endpoints)
Goal: Full intel feed + deals as separate workspace with sub-tabs fetching from Lockwood via proxy
Dependencies: Phase 2 (workspace containers must exist)
Proxy endpoints: GET /api/proxy/intel/items, /api/proxy/intel/alerts, /api/proxy/deals/items, /api/proxy/deals/hunts — forward to Lockwood http://10.0.1.101:8100

## Phase 4: Terminal Workspace
Files: ~/.buildrunner/dashboard/public/index.html (MODIFY), ~/.buildrunner/dashboard/public/styles.css (MODIFY), ~/.buildrunner/dashboard/events.mjs (MODIFY — session tracking)
Goal: Full-screen multi-tab xterm.js terminal with command toolbar and split view
Dependencies: Phase 2 (workspace containers)
Existing: WebSocket terminal endpoint already exists at /ws/terminal/:node in events.mjs

## Phase 5: Build Workspace
Files: ~/.buildrunner/dashboard/public/index.html (MODIFY), ~/.buildrunner/dashboard/public/styles.css (MODIFY)
Goal: Build management with phase detail, dispatch, and terminal-integrated actions
Dependencies: Phase 4 (build actions open terminal)
Existing endpoints: GET /api/registry, POST /api/builds/:id/dispatch, POST /api/builds/:id/status

## Phase 6: Mobile Responsive
Files: ~/.buildrunner/dashboard/public/styles.css (MODIFY), ~/.buildrunner/dashboard/public/index.html (MODIFY)
Goal: Touch-friendly dashboard from phone — bottom tab bar, responsive terminal
Dependencies: Phases 2, 4

## Phase 7: Session Management + Node Actions
Files: ~/.buildrunner/dashboard/public/index.html (MODIFY), ~/.buildrunner/dashboard/events.mjs (MODIFY)
Goal: Session clone/kill, node context menus with terminal integration
Dependencies: Phase 4
