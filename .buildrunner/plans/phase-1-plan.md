# Phase 1: Web Terminal — Implementation Plan

## Approach
Add WebSocket-based terminal proxy to the dashboard. Click any node → xterm.js terminal in a modal.

## Tasks

### Task 1.1 — Add ws dependency to package.json
Add `ws` package for WebSocket support on the server side.

### Task 1.2 — WebSocket terminal proxy in events.mjs  
- Upgrade HTTP server to support WebSocket upgrade for `/ws/terminal/:node`
- For Muddy: spawn local shell via `child_process.spawn('bash')`
- For remote nodes: spawn SSH session via `child_process.spawn('ssh', [...])`
- Pipe stdin/stdout between WebSocket and child process
- Handle terminal resize (cols/rows) via special JSON messages
- Clean up child process on WebSocket close

### Task 1.3 — xterm.js terminal modal in index.html
- Load xterm.js + xterm-addon-fit from CDN (no build step)
- Add terminal modal overlay (separate from existing modal)
- Terminal opens when clicking node card or via context menu "Open Terminal"
- WebSocket connects to `/ws/terminal/:nodeName`
- Fit addon handles resize, sends resize events to server
- Close button + auto-close on disconnect + reconnect option

### Task 1.4 — Terminal styles in styles.css
- Terminal modal styles (full-width, dark background)
- Terminal header with node name + close button
- Status indicator (connected/disconnected)

### Task 1.5 — Add "Open Terminal" to node context menu + node detail modal

## Tests
Non-testable with vitest (WebSocket + SSH + PTY). Verification via manual browser check.
