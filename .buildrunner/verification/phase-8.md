# Phase 8 Verification: Node Process Viewer

## Deliverables

| # | Deliverable | Status | Evidence |
|---|-------------|--------|----------|
| 1 | `/api/nodes/:name/processes` endpoint | PASS | events.mjs line 879-927, SSH for remote nodes, local ps for Muddy |
| 2 | Process table in node detail modal | PASS | index.html proc-viewer-section, proc-table-container |
| 3 | Sortable by CPU or MEM | PASS | procSortBy toggle, sortAndRenderProcesses() |
| 4 | Highlight BR3 processes | PASS | PROC_HIGHLIGHT_PATTERNS array, proc-highlight CSS class |
| 5 | Kill button per process with confirmation | PASS | killNodeProcess() + /api/nodes/:name/kill endpoint, confirm() dialog |
| 6 | Auto-refresh button | PASS | proc-refresh-btn calling loadNodeProcesses() |

## Notes
- Files are outside git repo (~/.buildrunner/dashboard/), so cannot be committed to BuildRunner3 repo
- PID validation rejects PID <= 1 to prevent killing init
- Kill events are logged to events DB and broadcast via SSE
- Process viewer uses distinct IDs (proc-*) to avoid conflicts with Phase 7's rollback/restart sections
