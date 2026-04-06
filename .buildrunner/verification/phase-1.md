# Phase 1: Web Terminal — Verification

## Deliverables

| # | Deliverable | Status | Evidence |
|---|-------------|--------|----------|
| 1 | WebSocket endpoint `/ws/terminal/:node` | PASS | events.mjs: `server.on('upgrade', ...)` + `wss.on('connection', ...)` at line ~670 |
| 2 | xterm.js terminal in modal | PASS | index.html: CDN-loaded xterm.js v5.5.0 + FitAddon, `openTerminal()` function |
| 3 | Terminal resize handling | PASS | FitAddon + ResizeObserver, sends `{type:'resize', cols, rows}` to server |
| 4 | Auto-close + reconnect | PASS | `ws.onclose` shows reconnect button, `child.on('exit')` sends exit message |
| 5 | Muddy local shell (no SSH) | PASS | `if (nodeName === 'muddy')` spawns `bash --login` directly |

## Access Points
- Node context menu (left-click dots): "Open Terminal" at top
- Node right-click menu: "Open Terminal" at top
- Node detail modal: "Open Terminal" button in footer

## Server Verification
- Module parse: OK (node dynamic import succeeds)
- ws dependency: installed via npm
- Only EADDRINUSE error (port 4400 already in use by running dashboard)

## Manual Verification Needed
- Restart dashboard (`pkill -f "node events.mjs"; cd ~/.buildrunner/dashboard && node events.mjs`)
- Click any node → Open Terminal → verify shell works
- Test Muddy (local bash) and a remote node (SSH)
