# Phase 4: Diff Review Queue — Implementation Plan

## Tasks

### Task 4.1: Create reviews.mjs integration
- Watch build.phase_complete events from the dashboard event DB
- SSH to remote nodes to fetch git diff for completed branches
- Maintain an in-memory review queue with status (pending/approved/rejected)
- Export: getReviews(), approveReview(id), rejectReview(id), startWatching()

### Task 4.2: Add review API endpoints to events.mjs
- GET /api/reviews — return review queue
- POST /api/reviews/:id/approve — approve and trigger merge
- POST /api/reviews/:id/reject — mark as rejected
- Import reviews.mjs and wire into handler

### Task 4.3: Add Review Queue panel to index.html
- New panel in dashboard grid showing pending diffs with file count, lines +/-
- Badge count in panel header for pending reviews
- Click review to open diff viewer modal

### Task 4.4: Build diff viewer modal in index.html
- Modal with green/red line-by-line diff display
- File navigator sidebar
- Approve and Reject buttons in modal footer

### Task 4.5: Add diff viewer CSS to styles.css
- Green/red line styles for additions/removals
- Review queue card styles

### Task 4.6: Wire SSE + polling for reviews
- Process build.phase_complete events in frontend
- Auto-refresh review queue via SSE

## Tests
- Non-testable (no vitest in dashboard project). Manual verification.
