---
description: Full diagnostic — cross-file correlation across all 4 BR3 logs
allowed-tools: Read, Bash, Grep, Glob
model: opus
arguments:
  - name: project
    description: 'Optional: project alias or path'
    required: false
---

# Full Diagnostic Analysis

Read all 4 BR3 log files, correlate timestamps across files, and produce a single unified diagnostic report. Work sequentially through all files — do not delegate to subagents since cross-file correlation requires shared context.

**Arguments:** $ARGUMENTS

---

## Step 0: Resolve Project Path

```bash
case "$ARGUMENTS" in
  sales) PROJECT_PATH=~/Projects/sales-assistant/web/app ;;
  oracle) PROJECT_PATH=~/Projects/buildrunner-oracle ;;
  synapse) PROJECT_PATH=~/Projects/Synapse ;;
  marba) PROJECT_PATH=~/Projects/MARBA ;;
  synapse-admin) PROJECT_PATH=~/Projects/synapse-admin-panel ;;
  */*|~*) PROJECT_PATH="$ARGUMENTS" ;;
  "") PROJECT_PATH="." ;;
  *) PROJECT_PATH=~/Projects/$ARGUMENTS ;;
esac
```

---

## Step 1: Environment Check

Before reading logs, verify we're looking at the right data:

```bash
# Check log freshness — are these from the right session?
ls -la "${PROJECT_PATH}/.buildrunner/"*.log 2>/dev/null
```

**If logs are missing, empty, or stale (>1 hour old):**

- Is the dev server running? Check `lsof -iTCP:3000 -iTCP:5173 -sTCP:LISTEN -P 2>/dev/null`
- Is the issue on prod/phone? → BRLogger may not be deployed. Build and deploy: `npm run build && npx netlify deploy --dir=dist --alias=br-debug`
- Is this a PWA? → Check device.log for `[DEVICE] displayMode: standalone` vs `browser`. If the issue is PWA-specific but logs show browser mode, you're testing wrong.
- Is the phone sending logs? → Check device.log for device tags like `ios-pwa`, `android-pwa`. If only `chrome-desktop` appears, no phone data is flowing.

Tell the user if logs don't match the reported problem environment before proceeding.

## Step 2: Read All Logs

Read the last 200 lines of each file in parallel:

- `${PROJECT_PATH}/.buildrunner/browser.log`
- `${PROJECT_PATH}/.buildrunner/supabase.log`
- `${PROJECT_PATH}/.buildrunner/device.log`
- `${PROJECT_PATH}/.buildrunner/query.log`

Note which files exist and which are empty/missing.

---

## Step 2: Cross-File Correlation

Build a unified timeline by merging timestamps. Look for causation chains:

1. `device.log [VISIBILITY] foreground` → `query.log [FETCH] REFETCH` → `supabase.log [QUERY] GET` = refetchOnWindowFocus cascade
2. `device.log [SW] update` → `browser.log [NAV]` → `query.log [HYDRATE]` = SW update triggered reload
3. `supabase.log [AUTH] SIGNED_OUT` → `query.log [INVALIDATE] ALL` = auth event nuking cache
4. `device.log [NETWORK] offline` → `supabase.log ⚠ SERVER_ERROR` → `browser.log [ERROR]` = network cascade
5. `query.log [INVALIDATE] ALL` → many `supabase.log [QUERY]` entries = pull-to-refresh storm
6. `supabase.log [REALTIME] ⚠ channel error` → missed `query.log [INVALIDATE]` = stale data

Measure:

- Time from app foreground to first useful data rendered
- Time from navigation to data loaded
- Ratio of DB calls to cache hits

---

## Step 3: Report

<example>
**Full Diagnostic Report** (trailsync)
**Log window:** 09:14:22 → 09:27:45 (13 min)
**Devices:** ios-pwa, chrome-desktop

## Timeline

1. 09:14:22 `[device]` ios-pwa session start — iPhone, standalone, 4G, 72% battery
2. 09:14:23 `[query]` HYDRATE complete in 145ms — 8/12 queries restored
3. 09:14:24 `[supabase]` AUTH SIGNED_IN — token refresh successful
4. 09:14:24 `[query]` 4x REFETCH triggered — groups.my, nav.trips, nav.adminGroups, nav.pendingCount
5. 09:14:25 `[supabase]` 4 GET requests in 800ms — all returned 200
6. 09:15:01 `[browser]` NAV pushState: /groups/cd1b/trips/e146
7. 09:15:01 `[query]` FRESH trips.detail.e146 — no cached data, fetching
8. 09:15:01 `[query]` FRESH schedule.byTrip.e146 → returned true ⚠
9. 09:15:32 `[device]` VISIBILITY background
10. 09:15:35 `[device]` VISIBILITY foreground
11. 09:15:35 `[query]` 6x REFETCH — all stale queries refetched on window focus
12. 09:15:36 `[supabase]` 6 GET requests in 1.2s

## Root Causes

1. **refetchOnWindowFocus causing DB call storms** — 3-second background/foreground cycle at 09:15:32 triggered 6 unnecessary refetches. Evidence: device.log visibility events correlate 1:1 with query.log refetches.
2. **loadData anti-pattern** — schedule.byTrip.e146 returns `true` (line 8). Cache "hit" is meaningless — page still fetches from DB on every mount.
3. **Duplicate query keys** — nav.trips and trips.byGroup both fetch getGroupTrips() (lines 4-5).

## Cache Efficiency

- Hydration: 145ms, 8/12 queries restored
- Hit rate: 28% (8 refetches, 21 fresh)
- Unnecessary refetches: 12 (caused by: window focus, duplicate keys)

## Fix Priority

1. Set `refetchOnWindowFocus: false` globally — realtime handles invalidation
2. Fix loadData in TripSchedule.tsx:428 — return actual data from queryFn
3. Merge nav.trips → trips.byGroup in GlobalNav.tsx:106
   </example>

---

## Rules

- Read all files directly — do not use subagents
- Only cite issues with log evidence (timestamps + specific entries)
- If a log file is empty or missing, note it and work with what's available
- Focus on the interaction between logs, not individual analysis
- Keep timeline to 15-20 most significant events, not every line
