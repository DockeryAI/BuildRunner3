---
description: Debug browser errors - reads browser logs and analyzes issues
allowed-tools: Read, Bash, Grep, Glob
model: opus
arguments:
  - name: project
    description: 'Optional: project alias (sales, oracle, synapse, marba) or path'
    required: false
---

# Browser Debug Analysis

You are debugging a frontend issue. Read and analyze the browser logs.

**Arguments:** $ARGUMENTS

---

## Step 0: Determine Project Path

If a project was specified in $ARGUMENTS, resolve it:

**Known project aliases:**

- `sales` → `~/Projects/sales-assistant/web/app`
- `oracle` → `~/Projects/buildrunner-oracle`
- `synapse` → `~/Projects/Synapse`
- `marba` → `~/Projects/MARBA`
- `synapse-admin` → `~/Projects/synapse-admin-panel`
- `synapse-triggers` → `~/Projects/Synapse-Triggers-3.0`
- `synapse-uvp` → `~/Projects/synapse-uvp-v2`

If argument contains `/` or `~`, treat as direct path.
If no argument, use current directory.

**IMPORTANT:** Before reading browser.log, verify which directory the dev server actually runs from:

```bash
lsof -iTCP:3000 -sTCP:LISTEN -P 2>/dev/null | head -3
```

The dev server's working directory is where browser.log is written. For Synapse, the dev server typically runs from `~/Projects/SynapseContentPerformance/` (a git worktree), NOT `~/Projects/Synapse/`.

```bash
# Resolve project path based on argument
case "$ARGUMENTS" in
  sales) PROJECT_PATH=~/Projects/sales-assistant/web/app ;;
  oracle) PROJECT_PATH=~/Projects/buildrunner-oracle ;;
  synapse) PROJECT_PATH=~/Projects/Synapse ;;
  marba) PROJECT_PATH=~/Projects/MARBA ;;
  synapse-admin) PROJECT_PATH=~/Projects/synapse-admin-panel ;;
  synapse-triggers) PROJECT_PATH=~/Projects/Synapse-Triggers-3.0 ;;
  synapse-uvp) PROJECT_PATH=~/Projects/synapse-uvp-v2 ;;
  */*|~*) PROJECT_PATH="$ARGUMENTS" ;;
  "") PROJECT_PATH="." ;;
  *) PROJECT_PATH=~/Projects/$ARGUMENTS ;;
esac
echo "Looking for browser.log in: $PROJECT_PATH"
```

---

## Step 1: Environment Check

Before reading logs, check freshness and environment match:

```bash
ls -la "${PROJECT_PATH}/.buildrunner/"*.log 2>/dev/null
```

If the log is missing, empty, or stale (>1 hour old): the dev server may not be running, or BRLogger may not be deployed to the environment where the issue occurs. For prod/phone issues, deploy first: `npm run build && npx netlify deploy --dir=dist --alias=br-debug`. For PWA issues, verify device.log shows `displayMode: standalone`, not `browser`.

---

## Step 2: Find and Read Browser Log

```bash
# Read the browser log from resolved project
cat "${PROJECT_PATH}/.buildrunner/browser.log" 2>/dev/null | tail -200
```

If no log found:

```bash
# List all projects with browser logs
ls -la ~/Projects/*/.buildrunner/browser.log ~/Projects/*/web/app/.buildrunner/browser.log 2>/dev/null
```

---

## Step 2b: Check Supabase Log (if relevant)

If browser.log contains Supabase-related errors (network errors to Supabase URLs, auth failures, 401/403 from PostgREST), also read the Supabase operation log:

```bash
cat "${PROJECT_PATH}/.buildrunner/supabase.log" 2>/dev/null | tail -100
```

Cross-reference timestamps between browser.log and supabase.log to correlate frontend errors with backend operations. If Supabase issues dominate, suggest the user run `/sdb` for deeper analysis.

---

## Step 3: Analyze the Logs

Scan for these entry types and flag anomalies:

- `[ERROR]` — JavaScript errors, exceptions, stack traces
- `[NET]` with status >= 400 or `ERR` — failed API calls, CORS, auth
- `[WARN]` — deprecation warnings, React warnings
- `[NAV]` — navigation events (pushState, replaceState, popstate). Correlate with timing of errors.
- `[LOG]` / `[INFO]` — console output around error timestamps

Also check other BR3 logs if relevant:

- Supabase errors → suggest `/sdb`
- Device/lifecycle issues → suggest `/device`
- Cache problems → suggest `/query`
- Full cross-file diagnosis → suggest `/diag`

---

## Step 4: Report

<example>
**Browser Log Analysis** (trailsync)

**Errors:** 2 found

1. `TypeError: Cannot read property 'name' of undefined` at 09:15:32 — occurs after NAV to /trips/e146. Trip data not loaded before render.
2. `[NET] POST /functions/v1/dispatch-notification 401` at 09:15:33 — auth token expired during push notification dispatch.

**Navigation Context:** User navigated Groups → Trips → TripDetail in 3s. Error correlates with TripDetail mount before query resolves.

**Recommended Fix:**

1. Add loading guard in TripDetail before accessing trip.name
2. Check Supabase token refresh timing — run `/sdb` for auth details
   </example>

---

## Step 5: Fix the Issue

If the fix is clear:

1. Read the relevant source file
2. Implement the fix
3. Tell user to refresh and verify

If unclear, suggest the appropriate BR3 debug command for deeper analysis.

---

## Log Entry Format

```
[timestamp] [session] [TYPE] message
```

Types: `[LOG]`, `[WARN]`, `[ERROR]`, `[NET]`, `[INFO]`, `[DEBUG]`, `[NAV]`
