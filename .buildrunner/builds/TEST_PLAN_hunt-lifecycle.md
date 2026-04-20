# TEST_PLAN: Hunt Lifecycle Management

**Build:** BUILD_hunt-lifecycle.md
**Last Updated:** 2026-04-12
**Tested By:** Claude Code (Opus 4.6) via Playwright MCP

---

## Rules (Read Before Any Test Work)

1. **PASS requires real browser confirmation.** Not code reading, not API calls, not assumptions. Open the dashboard, perform the action, observe the result.
2. **Every row must reach PASS.** No skipping, no "probably works", no shortcuts.
3. **Failed tests get healed.** Fix the issue, re-run, update status. Don't mark FAILED and move on.
4. **Preconditions must be true.** Verify the precondition before performing the action.
5. **Expected results must be observable.** If you can't see it in the browser, it's not PASS.
6. **Do not stop until every row is PASS.**

---

## Feature: Deal Card Lifecycle Toggle

### Flow: Mark as Bought

| Precondition                                | User Action                | Expected Result                                                                             | Status |
| ------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------- | ------ |
| Deal card visible with "Mark Bought" button | Click "Mark Bought" button | Button changes to "Bought ✓ / Mark Received", card gets purchased styling (opacity reduced) | PASS   |
| Deal marked as bought                       | Refresh page               | Deal still shows "Bought ✓ / Mark Received" (persisted)                                     | PASS   |

### Flow: Mark as Received

| Precondition                                 | User Action                             | Expected Result                                             | Status |
| -------------------------------------------- | --------------------------------------- | ----------------------------------------------------------- | ------ |
| Deal shows "Bought ✓ / Mark Received" button | Click "Bought ✓ / Mark Received" button | Button changes to "Received ✓✓", card gets received styling | PASS   |
| Deal marked as received                      | Refresh page                            | Deal still shows "Received ✓✓" (persisted)                  | PASS   |

### Flow: Undo Received

| Precondition                    | User Action                | Expected Result                                                            | Status |
| ------------------------------- | -------------------------- | -------------------------------------------------------------------------- | ------ |
| Deal shows "Received ✓✓" button | Click "Received ✓✓" button | Button changes back to "Bought ✓ / Mark Received", received status cleared | PASS   |

---

## Feature: Deal Card User Notes

### Flow: Add Note

| Precondition                             | User Action                                     | Expected Result                 | Status |
| ---------------------------------------- | ----------------------------------------------- | ------------------------------- | ------ |
| Deal card visible with "+ add note" text | Click "+ add note"                              | Textarea appears for editing    | PASS   |
| Textarea visible                         | Type "Test note from UX plan" and click outside | Note saves and displays on card | PASS   |
| Note visible on card                     | Refresh page                                    | Note persists and displays      | PASS   |

### Flow: Edit Note

| Precondition                        | User Action                                 | Expected Result                         | Status |
| ----------------------------------- | ------------------------------------------- | --------------------------------------- | ------ |
| Deal card has existing note         | Click on the note text                      | Textarea appears with current note text | PASS   |
| Textarea visible with existing text | Modify text to "Updated test note" and blur | Updated note displays on card           | PASS   |

---

## Feature: Deal Card URL Editing

### Flow: Add URL on Purchased Item

| Precondition                                | User Action                                   | Expected Result                   | Status |
| ------------------------------------------- | --------------------------------------------- | --------------------------------- | ------ |
| Deal marked as purchased, shows "+ add URL" | Click "+ add URL"                             | Input field appears for URL entry | PASS   |
| URL input visible                           | Paste "https://example.com/purchase" and blur | URL saves and displays on card    | PASS   |
| URL visible on card                         | Refresh page                                  | URL persists                      | PASS   |

---

## Feature: Deal Card Delete

### Flow: Delete Deal

| Precondition                        | User Action               | Expected Result                                                         | Status |
| ----------------------------------- | ------------------------- | ----------------------------------------------------------------------- | ------ |
| Deal card visible with red X button | Click red X delete button | Confirmation dialog appears: "Delete this deal? This cannot be undone." | PASS   |
| Confirmation dialog visible         | Click Cancel/dismiss      | Deal remains, no deletion                                               | PASS   |
| Confirmation dialog visible         | Click OK/confirm          | Deal disappears from list                                               | PASS   |
| Deal deleted                        | Refresh page              | Deal does not reappear (permanently deleted)                            | PASS   |

---

## Feature: Hunt Completion

### Flow: Complete Hunt

| Precondition                                         | User Action                                             | Expected Result                                       | Status |
| ---------------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------- | ------ |
| Active hunt card visible with "Complete Hunt" button | Click "Complete Hunt"                                   | Confirmation dialog appears asking to confirm         | PASS   |
| Confirmation visible                                 | Confirm completion                                      | Prompt for completion notes appears                   | PASS   |
| Notes prompt visible                                 | Enter "Hunt completed - all items received" and confirm | Hunt disappears from active hunts                     | PASS   |
| Hunt completed                                       | Scroll to Archived Hunts section                        | Completed hunt appears in archived section with notes | PASS   |

---

## Feature: Archived Hunts Panel

### Flow: View Archived Hunts

| Precondition                            | User Action                          | Expected Result                                                           | Status |
| --------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------- | ------ |
| At least one hunt is archived/completed | Look for "Archived Hunts (N)" toggle | Toggle is visible below active hunt cards                                 | PASS   |
| Archived toggle visible (collapsed)     | Click toggle                         | Panel expands showing archived hunt cards                                 | PASS   |
| Panel expanded                          | Observe archived hunt card           | Shows hunt name, item count, purchased count, received count, total spent | PASS   |

### Flow: Revive Hunt

| Precondition                                         | User Action                | Expected Result                  | Status |
| ---------------------------------------------------- | -------------------------- | -------------------------------- | ------ |
| Archived hunt card visible with "Revive Hunt" button | Click "Revive Hunt"        | Toast shows "Hunt revived"       | PASS   |
| Hunt revived                                         | Check active hunts section | Hunt now appears in active hunts | PASS   |
| Hunt revived                                         | Check archived section     | Hunt no longer in archived list  | PASS   |

---

## Feature: Tracking Display

### Flow: Display Tracking Info

| Precondition                                                      | User Action    | Expected Result                                                          | Status |
| ----------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------ | ------ |
| Deal has tracking number set via API (PATCH with tracking_number) | View deal card | Tracking number displays on card                                         | PASS   |
| Deal has carrier and delivery_status set                          | View deal card | Delivery status badge shows (color-coded: shipped=blue, delivered=green) | PASS   |

---

## Summary

| Feature          | Total Tests | PASS   | FAILED | UNTESTED |
| ---------------- | ----------- | ------ | ------ | -------- |
| Lifecycle Toggle | 5           | 5      | 0      | 0        |
| User Notes       | 5           | 5      | 0      | 0        |
| URL Editing      | 3           | 3      | 0      | 0        |
| Delete           | 4           | 4      | 0      | 0        |
| Hunt Completion  | 4           | 4      | 0      | 0        |
| Archived Hunts   | 6           | 6      | 0      | 0        |
| Tracking Display | 2           | 2      | 0      | 0        |
| **TOTAL**        | **29**      | **29** | **0**  | **0**    |

**Tested:** 2026-04-12
**Notes:** All tests passed. One bug fixed during testing (Test 9) — card click handler was intercepting inline edit clicks. Fix applied to ws-intel.js line 1632.
