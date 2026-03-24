---
description: Debug Supabase issues - reads supabase.log and analyzes operations
allowed-tools: Read, Bash, Grep, Glob
model: opus
arguments:
  - name: project
    description: 'Optional: project alias (sales, oracle, synapse, marba) or path'
    required: false
---

# Supabase Debug Analysis

You are debugging Supabase issues. Read and analyze the Supabase operation logs.

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

```bash
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
echo "Looking for supabase.log in: $PROJECT_PATH"
```

---

## Step 1: Environment Check

Before reading logs, check freshness and environment match:

```bash
ls -la "${PROJECT_PATH}/.buildrunner/"*.log 2>/dev/null
```

If the log is missing, empty, or stale (>1 hour old): the dev server may not be running, or BRLogger may not be deployed to the environment where the issue occurs. For prod/phone issues, deploy first: `npm run build && npx netlify deploy --dir=dist --alias=br-debug`. For PWA issues, verify device.log shows `displayMode: standalone`, not `browser`.

---

## Step 2: Find and Read Supabase Log

```bash
cat "${PROJECT_PATH}/.buildrunner/supabase.log" 2>/dev/null | tail -200
```

If no log found:

```bash
ls -la ~/Projects/*/.buildrunner/supabase.log 2>/dev/null
```

If still nothing, tell the user the Supabase logger may not be integrated in this project yet.

---

## Step 3: Analyze the Logs

Parse each JSON log line and look for these patterns:

### EMPTY_200 — RLS Denials (CRITICAL)

- Lines containing `EMPTY_200` — the query succeeded (200) but returned no rows
- This usually means RLS policies are blocking access
- Report: which table, what operation, suggested policy fix

### CLIENT_ERROR / SERVER_ERROR (CRITICAL)

- `CLIENT_ERROR` (4xx) — auth failures, bad requests, missing resources
- `SERVER_ERROR` (5xx) — Supabase or PostgREST crashes
- Report: status code, table/endpoint, error message

### TOKEN_REFRESH_FAIL (HIGH)

- Auth token refresh failures
- Causes cascading 401s across all subsequent requests
- Report: when it happened, how many requests failed after

### Slow Operations (MEDIUM)

- Any operation with duration > 1000ms
- Report: which table/operation, duration, whether it's a pattern

### Edge Function Internal Logs (MEDIUM-HIGH)

- Lines containing `[EDGE_FN:function-name]` — internal logs from edge functions
- These come from the `withDevLogs` wrapper when `DEBUG=true` is set on the Supabase project
- Look for: API call failures, timeout messages, retry attempts, token/cost tracking
- Report: which function, what went wrong inside it, any external API failures

### Failed Realtime Connections (HIGH)

- Realtime subscribe failures or disconnections
- Report: channel, error details, reconnection attempts

### Auth Issues (HIGH)

- Sign-in/sign-up failures
- Session expiry patterns
- Report: auth method, error type

---

## Step 4: Report

<example>
**Supabase Log Analysis** (trailsync)

**Log window:** 09:14:22 → 09:27:45 (84 entries)

### Critical Issues

- **Duplicate queries:** `group_members` SELECT called 3x within 200ms at 09:14:24 — same data, different callers (groups.my + nav.adminGroups + notifications.groups)
- **RLS denial:** `[QUERY] GET /rest/v1/push_subscriptions 200 0b` at 09:15:01 — EMPTY_200, anon key can't read push_subscriptions
- **Auth race:** `[AUTH] SIGNED_OUT` at 09:14:23 followed by `[AUTH] SIGNED_IN` 120ms later — token refresh fires SIGNED_OUT during startup

### Warnings

- 2 slow queries >500ms: `trips` SELECT with full schedule join (395ms, 2341b)
- `[REALTIME] global-invalidation: CHANNEL_ERROR` at 09:16:00 — missed invalidation window

### Summary

- Total: 84 ops | Errors: 1 | Warnings: 5 | Slow: 2 | Duplicate: 6

### Recommended Actions

1. Consolidate duplicate group_members queries (3 cache keys for 1 dataset)
2. Use service role for push_subscriptions query
3. Check `/device` for visibility events correlating with the auth race
   </example>

---

## Step 5: Cross-Reference with Browser Log

If Supabase errors are found, also check browser.log for correlated frontend errors:

```bash
cat "${PROJECT_PATH}/.buildrunner/browser.log" 2>/dev/null | tail -100 | grep -i "supabase\|auth\|401\|403\|network"
```

Report any browser-side errors that correlate with Supabase log entries.

---

## Step 6: Fix or Advise

If the fix is clear (e.g., missing RLS policy, auth config):

1. Explain the root cause
2. Suggest the fix
3. Implement if straightforward

If unclear:

- Ask user for more context
- Suggest enabling more verbose logging

---

## Log Entry Format Reference

Entries are JSON lines with fields like:

```json
{
  "timestamp": "ISO-8601",
  "operation": "select|insert|update|delete|auth|realtime",
  "table": "table_name",
  "duration_ms": 123,
  "status": 200,
  "classification": "SUCCESS|EMPTY_200|CLIENT_ERROR|SERVER_ERROR",
  "error": "optional error message"
}
```
