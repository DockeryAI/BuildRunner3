# Runtime Contract

**Schema version:** `br3.runtime.task.v1` / `br3.runtime.result.v1`

## Purpose

Phase 4 defines the BR3-owned runtime contract that later phases must build on.

## Core Rules

- `task_id` is the only automatic conflict boundary.
- One runtime is the authoritative writer for a `task_id`.
- All shadow or secondary runtime edit proposals are normalized as advisory-only.
- Same-file multi-runtime proposals under one `task_id` fail closed as `conflicted_proposal`.
- BR3 preserves raw payloads, observed workspace diffs, normalized edits, shell actions, stream events, and checkpoint records together in one result envelope.
- BR3 checkpoint semantics are orchestration-only. Model-internal mid-task resume is out of scope.

## Versioned Schemas

- `RuntimeTask`
- `RuntimeResult`
- `CapabilityProfile`
- `StreamEvent`
- `CheckpointRecord`
- `ObservedChange`

## Canonical Edit Types

- `write_file`
- `replace_range`
- `unified_diff`
- `shell_action`
- `advisory_only`

## Error Policy

- Compatibility, validation, and conflict errors are non-retryable.
- Execution failures may be retryable.
- Result envelopes should preserve structured error class and retryability metadata.
