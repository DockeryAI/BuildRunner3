# Phase 4: Diff Review Queue — Verification

## Deliverables Check

1. [x] **Integration that watches `build.phase_complete` events from remote nodes**
   - `reviews.mjs` exports `handlePhaseComplete()` which is called from events.mjs POST handler
   - Filters out local (muddy) events, only queues remote node completions

2. [x] **Auto-fetches `git diff` from remote branches via SSH**
   - `fetchDiff()` runs `git diff --stat` and `git diff` via SSH to remote nodes
   - `parseDiff()` parses raw diff into file objects with line-by-line type annotations
   - `parseDiffStats()` extracts files changed, insertions, deletions

3. [x] **Review Queue panel showing pending diffs with file count, lines added/removed**
   - Panel added to index.html with badge count, refresh button
   - `renderReviews()` renders cards with project, node, phase, stats (+/-/files)

4. [x] **Click review opens diff viewer modal with green/red line-by-line display**
   - Diff viewer modal with sidebar file navigator and line-by-line colored display
   - Hunk headers shown in accent color, additions green, deletions red
   - File sidebar shows per-file +/- stats, clicking switches displayed file

5. [x] **Approve button (triggers merge) and Reject button (marks as rejected)**
   - Both inline on review cards and in diff viewer modal footer
   - Approve calls `/api/reviews/:id/approve` which triggers merge for local branches
   - Reject calls `/api/reviews/:id/reject` which marks as rejected
   - Events broadcast via SSE for real-time updates

6. [x] **Badge count on panel header showing pending reviews**
   - `.review-badge.has-pending` class with red dim + pulse animation
   - Count updates automatically via SSE on phase_complete and review events

## API Endpoints Added
- `GET /api/reviews` — returns review list with pending count
- `GET /api/reviews/:id` — returns single review with full diff data
- `POST /api/reviews/:id/approve` — approve and merge
- `POST /api/reviews/:id/reject` — reject

## Event Types Added
- `review.pending`, `review.approved`, `review.rejected`

## Files Modified
- `~/.buildrunner/dashboard/integrations/reviews.mjs` (NEW — 230 lines)
- `~/.buildrunner/dashboard/events.mjs` (MODIFY — import, endpoints, event handler)
- `~/.buildrunner/dashboard/public/index.html` (MODIFY — panel, modal, JS)
- `~/.buildrunner/dashboard/public/styles.css` (MODIFY — review + diff styles)

## Notes
- Dashboard files live outside git repo (~/.buildrunner/dashboard/), no git commits possible
- TDD skipped — no test framework in dashboard project
- Remote merge is best-effort; notes when manual merge needed for non-local branches
