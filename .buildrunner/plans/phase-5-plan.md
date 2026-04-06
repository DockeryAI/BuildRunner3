# Phase 5 Plan: Auto Code Review on Diffs

## Tasks

### Task 5.1: Create auto-review-diff.sh script
- New script at ~/.buildrunner/scripts/auto-review-diff.sh
- Accepts: branch, project path, node
- Runs claude -p with review prompt on diff content
- Outputs structured JSON findings: [{severity, file, line, message}]
- Fallback: if claude CLI unavailable, output empty findings with warning

### Task 5.2: Modify reviews.mjs — trigger auto-review
- Add autoReview field to review objects
- After diff fetch in addReview, spawn auto-review-diff.sh
- Parse JSON output, attach findings to review
- Add summary counts (critical, warning, info)

### Task 5.3: Modify index.html — annotations in diff viewer
- Inline annotations on diff lines matching findings
- Color-code: critical=red, warning=yellow, info=blue
- Summary line on review card
- Auto-review status indicator
- Critical findings block Approve — acknowledge to override

### Task 5.4: Modify styles.css — annotation styles
- Annotation markers, severity colors
- Review summary badges
- Acknowledge checkbox, disabled approve button

## Tests
- Non-testable (shell scripts, HTML/CSS UI) — TDD skipped
