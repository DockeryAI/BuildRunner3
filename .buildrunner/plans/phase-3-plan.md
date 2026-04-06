# Phase 3 Plan: Token & Cost Tracking

## Tasks

### Task 3.1: Create usage.mjs integration
- New file: ~/.buildrunner/dashboard/integrations/usage.mjs
- Read ~/.buildrunner/usage-estimate.json locally for Muddy
- SSH to remote nodes to read their usage-estimate.json
- Cache results with 15s TTL, export getUsageData() and startPolling()
- Emit usage.warning SSE event when any node hits 85%

### Task 3.2: Add /api/usage endpoint to events.mjs
- Import getUsageData from ./integrations/usage.mjs
- Add GET /api/usage endpoint returning per-node token usage
- Add usage.warning to VALID_TYPES set
- Start usage polling on server boot

### Task 3.3: Add token stats to header in index.html
- Add "Tokens: X / Y" stat to header-stats div
- Color-coded budget bar (green -> yellow at 80% -> red at 90%)
- Auto-pause indicator when swap-suggested

### Task 3.4: Add per-session token estimate in session grid
- Extend session card rendering to show token estimate
- Pull from usage data matched by node

### Task 3.5: Add budget bar CSS to styles.css
- Token bar styles for header
- Color transitions for budget thresholds

### Task 3.6: Wire up SSE usage.warning handling + auto-refresh
- Process usage.warning events in processEvent()
- Show toast notification on warning
- Fetch usage data on initial load and refresh periodically

## Tests
- Non-testable (integration with SSH/local files, no vitest in dashboard project)
- Verification via manual endpoint testing
