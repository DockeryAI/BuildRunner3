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
Files: ~/.buildrunner/dashboard/public/index.html (MODIFY), ~/.buildrunner/dashboard/public/styles.css (MODIFY), ~/.buildrunner/dashboard/events.mjs (MODIFY proxy endpoints)
Goal: Full intel feed + deals as separate workspace with sub-tabs
Dependencies: Phase 2 (workspace switching must exist)
APIs called: Lockwood /api/intel/items, /api/intel/alerts, /api/deals/items, /api/deals/hunts

## Phase 4: Terminal Workspace
Files: ~/.buildrunner/dashboard/public/index.html (MODIFY), ~/.buildrunner/dashboard/public/styles.css (MODIFY), ~/.buildrunner/dashboard/events.mjs (MODIFY session tracking)
Goal: Full-screen multi-tab terminal, command toolbar, split view
Dependencies: Phase 2 (workspace switching)
Existing: WebSocket terminal already built in Phase 1 of dashboard-intel build

## Phase 5: Build Workspace
Files: ~/.buildrunner/dashboard/public/index.html (MODIFY), ~/.buildrunner/dashboard/public/styles.css (MODIFY)
Goal: Build management with phase detail and terminal-integrated actions
Dependencies: Phase 4 (actions open terminal)
APIs called: /api/registry, /api/builds/:id/dispatch, /api/builds/:id/status

## Phase 6: Mobile Responsive
Files: ~/.buildrunner/dashboard/public/styles.css (MODIFY), ~/.buildrunner/dashboard/public/index.html (MODIFY)
Goal: Touch-friendly, bottom tab bar, responsive terminal
Dependencies: Phases 2, 4

## Phase 7: Session Management + Node Actions
Files: ~/.buildrunner/dashboard/public/index.html (MODIFY), ~/.buildrunner/dashboard/events.mjs (MODIFY)
Goal: Session clone/kill, node context menus
Dependencies: Phase 4
