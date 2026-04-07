# Phase 3 Plan: Race Condition Fixes (Dashboard Layer)

## Tasks

1. **RC17 — Registry write atomicity (events.mjs)**
   - Replace `fs.writeFileSync(REGISTRY_PATH, ...)` with write-to-temp + `fs.renameSync`
   - Helper function `writeRegistryAtomic(reg)` used at both write sites (lines 612, 2025)

2. **RC21 — SSE broadcast safety (events.mjs)**
   - Copy client set before iterating: `const clients = [...sseClients]`
   - Apply in `broadcastEvent()` (line 245) and shutdown handler (line 2060)

3. **RC10 — Walter polling stacking (walter.mjs)**
   - Replace `setInterval(poll, 30000)` with sequential `poll().then(() => setTimeout(poll, 30000))`
   - Track timeout handle instead of interval

4. **RC11 — Lock lastCoverage updates (walter.mjs)**
   - Ensure lastCoverage read+compute+assign happens in single synchronous block (RC10 fix prevents concurrent overlap)

## Tests

These are runtime infrastructure files (Node.js scripts, not app code). No vitest — verification via code review.
