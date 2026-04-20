# ui/dashboard — AGENTS.md (Cluster Max Dashboard, port 4400)

## Stack

- vanilla HTML + vanilla JS. no React, no Vue, no Svelte, no framework.
- No bundler. Pages are served as static HTML by a tiny Python server in `core/cluster/scripts/dashboard-serve.py`.
- Port: 4400 only. NEVER rebind. NEVER multiplex with the main app (port 3000).

## File layout

- `index.html` — single entry. Loads `app.js` as a classic script (no ESM imports from node_modules).
- `panels/<name>.js` — one panel per file. Each panel exports `render(container, data)` and `wire(container, ws)` via window globals, NOT ES modules.
- `styles.css` — single stylesheet. No preprocessors.

## WebSocket reconnect contract

- Exponential backoff: 500 ms, 1 s, 2 s, 4 s, 8 s, 16 s, 30 s. Cap at 30 s; retry indefinitely.
- On reconnect: request full state replay via `{"type":"resync"}`. NEVER assume state is intact across a disconnect.
- Heartbeat ping every 15 s. If no pong in 30 s, force-close and reconnect.

## Per-file validation

- `npx eslint --fix ui/dashboard/panels/<file>.js`
- NEVER run `npx eslint` on the whole directory — Codex defaults to file-scoped only.

## Constraints

- NEVER import from `node_modules`. The dashboard has no build step.
- NEVER add TypeScript. The dashboard is vanilla JS only.
- IMPORTANT: Each panel ≤300 lines. Split if larger.
- Dark theme only. Match palette from `../../src/index.css` CSS variables (read, do not import).
