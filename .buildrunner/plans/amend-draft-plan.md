# Amendment: Auto-Redispatch Watchdog (Phase 3)

## Phase 3: Auto-Redispatch Watchdog

**Status:** pending
**Blocked by:** Phase 2 (complete)
**Goal:** When the scanner marks a build `stalled`, automatically re-dispatch it if the build opts in.
**Files:**

- `~/.buildrunner/dashboard/events.mjs` (MODIFY) — auto-redispatch logic in scanner

**Deliverables:**

- Add `auto_redispatch` field support — scanner checks `build.auto_redispatch === true`
- Add `_redispatch_count` tracking in closure — reset on manual dispatch or running
- Max 3 auto-redispatches — after 3, set status to `failed`
- On stalled + auto_redispatch: call dispatch-to-node.sh for remote, spawn claude interactive for local
- Emit `build.redispatched` event
- Add `build.redispatched` to VALID_TYPES
- Dashboard Dispatch All sets `auto_redispatch: true` on dispatched builds
