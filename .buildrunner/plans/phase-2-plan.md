# Phase 2: Session Grid — Implementation Plan

## Tasks

### Task 1: Create `integrations/sessions.mjs`
- Poll each node for active Claude Code processes via SSH (ps aux | grep claude)
- Parse session files from ~/.claude/projects/ on each node
- For Muddy: use local exec, no SSH
- Cache results with 15s TTL
- Export getActiveSessions() function
- Return: node, project, branch, state, elapsed time, last activity, pid

### Task 2: Add `/api/sessions` endpoint to `events.mjs`
- Import sessions integration
- GET endpoint returning session list across all nodes
- Add session.update to VALID_TYPES for SSE broadcasting

### Task 3: Add Sessions panel to `index.html`
- New panel in the grid between Build DAG and Event Log
- Session grid: node, project, branch, state, elapsed, last activity
- Click session -> detail modal with recent output info
- Auto-refresh via SSE every 15s
- Session count badge in panel title

### Task 4: Add session grid styles to `styles.css`
- Session card/row styles
- State badges (active, idle, waiting)
- Color coding per node

## Tests
- Non-testable (dashboard UI + SSH integration). Skip TDD.
