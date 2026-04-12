# TEST_PLAN: Hunt Lifecycle Management

**Build:** BUILD_hunt-lifecycle.md
**Last Updated:** 2026-04-12
**Tested By:** pending

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

| Precondition                                | User Action                | Expected Result                                                                             | Status   |
| ------------------------------------------- | -------------------------- | ------------------------------------------------------------------------------------------- | -------- |
| Deal card visible with "Mark Bought" button | Click "Mark Bought" button | Button changes to "Bought ✓ / Mark Received", card gets purchased styling (opacity reduced) | UNTESTED |
| Deal marked as bought                       | Refresh page               | Deal still shows "Bought ✓ / Mark Received" (persisted)                                     | UNTESTED |

### Flow: Mark as Received

| Precondition                                 | User Action                             | Expected Result                                             | Status   |
| -------------------------------------------- | --------------------------------------- | ----------------------------------------------------------- | -------- |
| Deal shows "Bought ✓ / Mark Received" button | Click "Bought ✓ / Mark Received" button | Button changes to "Received ✓✓", card gets received styling | UNTESTED |
| Deal marked as received                      | Refresh page                            | Deal still shows "Received ✓✓" (persisted)                  | UNTESTED |

### Flow: Undo Received

| Precondition                    | User Action                | Expected Result                                                            | Status   |
| ------------------------------- | -------------------------- | -------------------------------------------------------------------------- | -------- |
| Deal shows "Received ✓✓" button | Click "Received ✓✓" button | Button changes back to "Bought ✓ / Mark Received", received status cleared | UNTESTED |

---

## Feature: Deal Card User Notes

### Flow: Add Note

| Precondition                             | User Action                                     | Expected Result                 | Status   |
| ---------------------------------------- | ----------------------------------------------- | ------------------------------- | -------- |
| Deal card visible with "+ add note" text | Click "+ add note"                              | Textarea appears for editing    | UNTESTED |
| Textarea visible                         | Type "Test note from UX plan" and click outside | Note saves and displays on card | UNTESTED |
| Note visible on card                     | Refresh page                                    | Note persists and displays      | UNTESTED |

### Flow: Edit Note

| Precondition                        | User Action                                 | Expected Result                         | Status   |
| ----------------------------------- | ------------------------------------------- | --------------------------------------- | -------- |
| Deal card has existing note         | Click on the note text                      | Textarea appears with current note text | UNTESTED |
| Textarea visible with existing text | Modify text to "Updated test note" and blur | Updated note displays on card           | UNTESTED |

---

## Feature: Deal Card URL Editing

### Flow: Add URL on Purchased Item

| Precondition                                | User Action                                   | Expected Result                   | Status   |
| ------------------------------------------- | --------------------------------------------- | --------------------------------- | -------- |
| Deal marked as purchased, shows "+ add URL" | Click "+ add URL"                             | Input field appears for URL entry | UNTESTED |
| URL input visible                           | Paste "https://example.com/purchase" and blur | URL saves and displays on card    | UNTESTED |
| URL visible on card                         | Refresh page                                  | URL persists                      | UNTESTED |

---

## Feature: Deal Card Delete

### Flow: Delete Deal

| Precondition                        | User Action               | Expected Result                                                         | Status   |
| ----------------------------------- | ------------------------- | ----------------------------------------------------------------------- | -------- |
| Deal card visible with red X button | Click red X delete button | Confirmation dialog appears: "Delete this deal? This cannot be undone." | UNTESTED |
| Confirmation dialog visible         | Click Cancel/dismiss      | Deal remains, no deletion                                               | UNTESTED |
| Confirmation dialog visible         | Click OK/confirm          | Deal disappears from list                                               | UNTESTED |
| Deal deleted                        | Refresh page              | Deal does not reappear (permanently deleted)                            | UNTESTED |

---

## Feature: Hunt Completion

### Flow: Complete Hunt

| Precondition                                         | User Action                                             | Expected Result                                       | Status   |
| ---------------------------------------------------- | ------------------------------------------------------- | ----------------------------------------------------- | -------- |
| Active hunt card visible with "Complete Hunt" button | Click "Complete Hunt"                                   | Confirmation dialog appears asking to confirm         | UNTESTED |
| Confirmation visible                                 | Confirm completion                                      | Prompt for completion notes appears                   | UNTESTED |
| Notes prompt visible                                 | Enter "Hunt completed - all items received" and confirm | Hunt disappears from active hunts                     | UNTESTED |
| Hunt completed                                       | Scroll to Archived Hunts section                        | Completed hunt appears in archived section with notes | UNTESTED |

---

## Feature: Archived Hunts Panel

### Flow: View Archived Hunts

| Precondition                            | User Action                          | Expected Result                                                           | Status   |
| --------------------------------------- | ------------------------------------ | ------------------------------------------------------------------------- | -------- |
| At least one hunt is archived/completed | Look for "Archived Hunts (N)" toggle | Toggle is visible below active hunt cards                                 | UNTESTED |
| Archived toggle visible (collapsed)     | Click toggle                         | Panel expands showing archived hunt cards                                 | UNTESTED |
| Panel expanded                          | Observe archived hunt card           | Shows hunt name, item count, purchased count, received count, total spent | UNTESTED |

### Flow: Revive Hunt

| Precondition                                         | User Action                | Expected Result                  | Status   |
| ---------------------------------------------------- | -------------------------- | -------------------------------- | -------- |
| Archived hunt card visible with "Revive Hunt" button | Click "Revive Hunt"        | Toast shows "Hunt revived"       | UNTESTED |
| Hunt revived                                         | Check active hunts section | Hunt now appears in active hunts | UNTESTED |
| Hunt revived                                         | Check archived section     | Hunt no longer in archived list  | UNTESTED |

---

## Feature: Tracking Display

### Flow: Display Tracking Info

| Precondition                                                      | User Action    | Expected Result                                                          | Status   |
| ----------------------------------------------------------------- | -------------- | ------------------------------------------------------------------------ | -------- |
| Deal has tracking number set via API (PATCH with tracking_number) | View deal card | Tracking number displays on card                                         | UNTESTED |
| Deal has carrier and delivery_status set                          | View deal card | Delivery status badge shows (color-coded: shipped=blue, delivered=green) | UNTESTED |

---

## Summary

| Feature          | Total Tests | PASS  | FAILED | UNTESTED |
| ---------------- | ----------- | ----- | ------ | -------- |
| Lifecycle Toggle | 5           | 0     | 0      | 5        |
| User Notes       | 5           | 0     | 0      | 5        |
| URL Editing      | 3           | 0     | 0      | 3        |
| Delete           | 4           | 0     | 0      | 4        |
| Hunt Completion  | 4           | 0     | 0      | 4        |
| Archived Hunts   | 5           | 0     | 0      | 5        |
| Tracking Display | 2           | 0     | 0      | 2        |
| **TOTAL**        | **28**      | **0** | **0**  | **28**   |
