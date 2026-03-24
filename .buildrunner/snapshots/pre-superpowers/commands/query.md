---
description: Analyze query.log — cache hit rates, stale patterns, hydration timing
allowed-tools: Read, Bash, Grep, Glob
model: sonnet
arguments:
  - name: project
    description: 'Optional: project alias or path'
    required: false
---

# Query Cache Analysis

Analyze the React Query cache log for hit/miss rates, duplicate keys, stale patterns, and hydration issues.

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
echo "Looking for query.log in: $PROJECT_PATH"
```

---

## Step 1: Environment Check

Before reading logs, check freshness and environment match:

```bash
ls -la "${PROJECT_PATH}/.buildrunner/"*.log 2>/dev/null
```

If the log is missing, empty, or stale (>1 hour old): the dev server may not be running, or BRLogger may not be deployed to the environment where the issue occurs. For prod/phone issues, deploy first: `npm run build && npx netlify deploy --dir=dist --alias=br-debug`. For PWA issues, verify device.log shows `displayMode: standalone`, not `browser`.

---

## Step 2: Read Query Log

```bash
cat "${PROJECT_PATH}/.buildrunner/query.log" 2>/dev/null | tail -400
```

---

## Step 3: Analyze

Scan for these patterns:

- `[HYDRATE]` — App startup cache restoration. Note time (ms) and query count. 0 queries = cache not persisting. >500ms = slow.
- `[FETCH] REFETCH` vs `[FETCH] FRESH` — Calculate hit rate. High fresh rate = cache ineffective.
- `[FETCH] SUCCESS ... → true ⚠` — The loadData anti-pattern. useQuery caches a boolean instead of data. Cache is useless for this query.
- `[INVALIDATE] ALL` — PullToRefresh or auth event nuking entire cache. Look at what triggers it.
- `[INVALIDATE]` rapid succession — Invalidation storm. Correlate with device.log visibility events.
- Duplicate fetches — Same data under different keys within seconds (e.g., `trips.byGroup.X` and `nav.trips.X`).
- `[FETCH] REFETCH ... (data age: Xs)` — If age is always <staleTime, something is invalidating early.
- `[IDB]` — IndexedDB chat cache operations. Missing reads = cache bypassed.
- `[STORAGE]` — localStorage writes for persistence tracking.

<example>
**Query Cache Analysis** (trailsync)

**Hydration:** 145ms, 8/12 queries restored from localStorage
**Cache hit rate:** 34% (12 refetches, 23 fresh)

### Critical Issues

- **loadData anti-pattern**: `schedule.byTrip.e146` caches `true` (boolean) — 4 fetches all hit DB despite "cache hit"
- **Duplicate keys**: `trips.byGroup.cd1b` and `nav.trips.cd1b` both fetch `getGroupTrips()` within 50ms — same data, different cache entries
- **Invalidation storm** at 09:15:33: `[INVALIDATE] ALL` followed by 8 refetches in 2s — triggered by PullToRefresh

### Cache Efficiency

| Query Key          | Hits | Misses | Avg Age | Issue                                 |
| ------------------ | ---- | ------ | ------- | ------------------------------------- |
| trips.detail.\*    | 3    | 5      | 12s     | Short-lived — invalidated by realtime |
| groups.my          | 0    | 4      | n/a     | Always fresh fetch                    |
| schedule.byTrip.\* | 2    | 2      | 0s      | Caches `true` — anti-pattern          |

### Recommendations

1. Fix loadData anti-pattern in TripSchedule/Menus — return actual data from queryFn
2. Consolidate `nav.trips` → `trips.byGroup` (same data, one key)
3. Scope PullToRefresh to current page keys, not ALL
   </example>
