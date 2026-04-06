# Phase 6: Build Health Sparklines — Implementation Plan

## Tasks

### Task 6.1: Add /api/builds/health endpoint to events.mjs
- Query events DB for build.phase_complete, build.complete, build.failed events
- Group by project, return last 30 build results per project
- Each result: {project, status (pass/fail), duration_seconds, timestamp}
- Also compute: reliability_pct, avg_duration, speed_trend (faster/slower/stable)

### Task 6.2: Canvas sparkline renderer in index.html
- Pure JS canvas function: drawSparkline(canvas, data)
- 30 bars: height proportional to duration, color green (pass) / red (fail)
- Compact: fits in a table cell (~120x24px)

### Task 6.3: Add sparklines to Active Builds table rows
- Add "Health" column to builds table
- Fetch /api/builds/health on load and on interval
- Render sparkline canvas in each build row
- Show reliability % and speed trend text beside sparkline

### Task 6.4: Add sparklines to node cards
- Show mini sparkline per node in the node-grid cards
- Aggregates all builds assigned to that node

### Task 6.5: Sparkline CSS styles
- Canvas sizing, layout within table cells and node cards
- Distinct class names (sparkline-*) to avoid Phase 5 conflicts

## Tests
- Non-testable with vitest (browser canvas + HTTP endpoints on SQLite)
- Verification via manual endpoint check
