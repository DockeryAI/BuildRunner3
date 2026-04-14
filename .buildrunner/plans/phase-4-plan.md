# Phase 4 Plan: Dashboard Panel + Review Convergence

## Assessment

Most Phase 4 deliverables already exist from earlier builds. Three integration gaps remain.

## Tasks

### Task 1: SSE event emission for cross_review_complete

The UI (index.html:2206) listens for `cross_review_complete` SSE events but events.mjs never emits them. Add a file watcher on `~/.buildrunner/cache/cross-reviews/` that emits `cross_review_complete` when new review files appear.

### Task 2: Convergence UI in dashboard

`findConvergence()` exists in cross-review.mjs but the HTML panel doesn't display convergent findings. Add a convergence section below the cross-review findings that highlights when both adversarial + cross-model flag the same file/severity.

### Task 3: Unified review status in Review Queue

`getUnifiedStatus()` exists in reviews.mjs but isn't exposed via API or shown in the review queue panel. Wire it into the existing review queue header as a combined pass/fail badge.

## Tests

- SSE emission: verify `cross_review_complete` fires when a new cache file is written
- Convergence: verify matching findings highlight correctly
- Unified status: verify badge reflects combined status
