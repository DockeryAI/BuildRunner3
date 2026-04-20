# Adversarial Review Tracking

Phase 14 makes consensus/adversarial review enforcement explicit and BR3-visible.

## File Layout

- Tracking files live under `.buildrunner/adversarial-reviews/`
- File pattern: `phase-{N}-{timestamp}.json`

## Required Schema Fields

- `schema_version`
- `task_id`
- `phase_number`
- `artifact_path`
- `plan_file`
- `reviewers`
- `merged_findings`
- `consensus_blockers`
- `unresolved_disagreements`
- `status`
- `pass`
- `generated_at`

## Enforcement Rules

- New BUILD phases must have a matching tracking file before commit.
- Any blocker from either reviewer remains blocking unless resolved explicitly in the tracked artifact.
- Unresolved blocker disagreements do not silently pass; they stay blocking and require user escalation.
- Emergency bypass is allowed only via `BR3_BYPASS_ADVERSARIAL_REVIEW=1` and must leave an audit entry in `.buildrunner/decisions.log`.

## Reviewer Roles

- Claude is the authoritative planning reviewer.
- Codex is the secondary adversarial reviewer.
- Secondary reviewers do not become authoritative writers through this tracking flow.
