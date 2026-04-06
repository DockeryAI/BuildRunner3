# Phase 8: Node Process Viewer — Implementation Plan

## Tasks

### 8.1 — Add `/api/nodes/:name/processes` endpoint to events.mjs
- Insert BELOW the build health sparklines section (before static file serving)
- For muddy: run `ps aux` locally, parse output
- For remote nodes: SSH + `ps aux --sort=-%cpu | head -20`
- Return JSON: `{ node, processes: [{ pid, user, cpu, mem, command }] }`

### 8.2 — Add `/api/nodes/:name/kill` endpoint to events.mjs
- POST endpoint accepting `{ pid }` in body
- For muddy: run `kill <PID>` locally
- For remote nodes: SSH + `kill <PID>`
- Prevent killing PID 1 or init

### 8.3 — Add process table section to node detail modal in index.html
- Add BELOW the "Recent Logs" section in `showNodeDetail()`
- Process table with columns: PID, User, CPU%, MEM%, Command
- Client-side sort toggle (CPU/MEM)
- Highlight known BR3 processes (claude, node_semantic, chromadb, vitest, playwright)
- Kill button per row with confirmation
- Auto-refresh button

### 8.4 — Add process table styles to styles.css
- `.proc-table`, `.proc-row`, `.proc-header`, `.proc-cell`
- `.proc-highlight` for known BR3 processes
- `.proc-kill-btn` for kill buttons
- `.proc-sort-btn` for sort toggles
- `.proc-refresh-btn` for refresh

## Tests
- Non-testable (dashboard UI + SSH-dependent endpoints). Skip TDD.
