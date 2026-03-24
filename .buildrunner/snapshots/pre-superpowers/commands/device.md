---
description: Analyze device.log — SW state, visibility, memory, network, permissions
allowed-tools: Read, Bash, Grep, Glob
model: sonnet
arguments:
  - name: project
    description: 'Optional: project alias or path'
    required: false
---

# Device Log Analysis

Analyze the device log for patterns and anomalies in device state, SW lifecycle, visibility, network, and performance.

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
echo "Looking for device.log in: $PROJECT_PATH"
```

---

## Step 1: Environment Check

Before reading logs, check freshness and environment match:

```bash
ls -la "${PROJECT_PATH}/.buildrunner/"*.log 2>/dev/null
```

If the log is missing, empty, or stale (>1 hour old): the dev server may not be running, or BRLogger may not be deployed to the environment where the issue occurs. For prod/phone issues, deploy first: `npm run build && npx netlify deploy --dir=dist --alias=br-debug`. For PWA issues, verify device.log shows `displayMode: standalone`, not `browser`.

---

## Step 2: Read Device Log

```bash
cat "${PROJECT_PATH}/.buildrunner/device.log" 2>/dev/null | tail -300
```

If empty/missing, tell the user BRLogger v2 may not be active and suggest `?br_debug=1`.

---

## Step 3: Analyze

Scan for these entry types and flag only what's abnormal:

- `[DEVICE]` — Note device type and display mode. PWA vs browser affects caching.
- `[SW]` — Service worker install/activate/update/controller changes. Frequent updates or stale SW are problems.
- `[VISIBILITY]` + `[FOCUS]` — Foreground/background transitions. Rapid cycling triggers refetchOnWindowFocus storms. Correlate timestamps with query.log.
- `[NETWORK]` — Online/offline/type changes. Flaky connections cause reconnect loops.
- `[PERF]` — Long tasks (>200ms), FID (>100ms), layout shifts (CLS >0.1), slow interactions (>200ms total).
- `[STORAGE]` — Quota and cache sizes. Flag if usage >80% or unexpected eviction.
- `[MEMORY]` — Memory pressure. iOS kills PWA under memory pressure.
- `[BATTERY]` — Note if low battery + not charging (iOS throttles background).
- `[RESOURCE]` — Failed image/asset loads.
- `[VIEWPORT]` — Keyboard show/hide events.

<example>
**Device Log Analysis** (trailsync, ios-pwa)

**Session:** 12 min | **Device:** iPhone (iOS 18.3) | **Display:** standalone (PWA)

### Issues Found

- **Rapid visibility cycling** (09:15:32-09:16:01): 6 foreground/background transitions in 29s — likely triggering refetchOnWindowFocus cascade. Check query.log for matching refetches.
- **SW controller change** at 09:14:55 without update — unexpected. May indicate forced SW reinstall.
- **Memory warning** at 09:17:12: 285MB / 350MB (81%) — iOS may kill app soon.

### Recommendations

1. Set `refetchOnWindowFocus: false` — realtime invalidation handles freshness
2. Investigate SW controller change — check for forced unregister in code
   </example>
