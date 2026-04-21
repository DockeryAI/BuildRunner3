# Dynamic PRD-Driven Build System

**Version:** 1.0.0
**Last Updated:** 2026-04-20T20:05:49.619710

## Project Overview

Transform BuildRunner 3 into a dynamic, PRD-driven system where the PROJECT_SPEC.md is the single source of truth. Any change to the PRD (via chat, UI, or direct file edit) automatically regenerates the build plan while preserving all completed work.

## Feature 1: PRD Controller

**Priority:** Critical

### Description

Central controller that manages the PROJECT_SPEC.md as the single source of truth. Handles all PRD updates from multiple sources, provides version control, and emits events for downstream systems.

### Requirements

- Single in-memory representation of PRD (PydanticV2 model)
- Bidirectional sync with PROJECT_SPEC.md file
- Automatic file write on any change
- Atomic updates with file locking
- Parse chat messages to detect PRD change intent
- Extract feature additions/modifications/deletions
- Convert natural language to structured PRD updates
- Support commands: "add feature X", "remove feature Y", "update feature Z to..."
- Store last 10 PRD versions in memory
- Each version tagged with timestamp, author, change summary
- Rollback to previous version
- Diff between versions showing exact changes
- Emit `prd.updated` event on every change
- Event payload includes: full PRD, changed sections, diff
- Support multiple subscribers
- Async event dispatch (non-blocking)
- File-level locking for PROJECT_SPEC.md writes
- Operational transforms for concurrent edits
- Conflict detection and resolution
- Last-write-wins with merge capability

### Acceptance Criteria

- [ ] [ ] Can parse natural language: "add authentication feature" → updates PRD with new feature
- [ ] [ ] Updates to in-memory PRD automatically write to PROJECT_SPEC.md within 100ms
- [ ] [ ] File locking prevents simultaneous writes (test with 5 concurrent updates)
- [ ] [ ] Can rollback to any of last 10 versions
- [ ] [ ] Emits `prd.updated` event within 50ms of change
- [ ] [ ] Event payload contains full PRD and diff
- [ ] [ ] Handles 100+ subscribers without performance degradation
- [ ] [ ] Concurrent edits merge correctly (test 3 simultaneous updates)

## Feature 2: Adaptive Planner

**Priority:** Critical

### Description

Intelligent planner that listens to PRD change events and regenerates only the affected portions of the build plan. Preserves all completed work and optimizes the task queue based on new dependencies.

### Requirements

- Subscribe to `prd.updated` events from PRD Controller
- Trigger regeneration within 100ms of event receipt
- Run regeneration in background (non-blocking)
- Compare new PRD vs current task queue
- Identify added/removed/modified features
- Generate tasks only for changed features
- Preserve existing tasks for unchanged features
- Never regenerate tasks with status "completed"
- Never reset progress on in-progress tasks
- If feature is removed, mark its tasks as "cancelled" (don't delete)
- If feature is modified, only regenerate pending tasks
- Recalculate dependency graph with new tasks
- Detect new blocking relationships
- Update "ready" task queue
- Preserve topological order
- Re-prioritize tasks based on new dependencies
- Batch new tasks with existing tasks efficiently
- Minimize context switches
- Notify orchestrator of queue changes
- Cache unchanged task generation
- Incremental dependency graph updates (not full rebuild)
- Target <3s regeneration for 1-2 feature changes
- Parallel task decomposition for multiple features

### Acceptance Criteria

- [ ] [ ] Receives `prd.updated` event and starts regeneration within 100ms
- [ ] [ ] Regeneration for 1-2 feature changes completes in <3 seconds
- [ ] [ ] Completed tasks remain unchanged after regeneration
- [ ] [ ] In-progress tasks retain their status and progress percentage
- [ ] [ ] Removed features have tasks marked "cancelled", not deleted
- [ ] [ ] Modified features only regenerate pending tasks
- [ ] [ ] Dependency graph updates correctly with new tasks
- [ ] [ ] New "ready" tasks appear in queue within 1 second
- [ ] [ ] Concurrent PRD changes queue regeneration (no race conditions)
- [ ] [ ] Task batches maintain coherence (no domain mixing)

## Feature 3: Sync Layer

**Priority:** Critical

### Description

Universal synchronization layer that connects all PRD input channels (chat, UI, file) and broadcasts changes to all clients in real-time. Provides consistent API for PRD modifications and ensures all clients stay in sync.

### Requirements

- POST /api/prd/update - Accept PRD changes from any source
- GET /api/prd/current - Get current PRD state
- POST /api/prd/parse-nl - Parse natural language to PRD changes (preview mode)
- POST /api/prd/rollback/:version - Rollback to specific version
- GET /api/prd/versions - List version history
- WebSocket /api/prd/stream - Real-time PRD update stream
- Monitor PROJECT_SPEC.md for direct edits
- Detect changes within 500ms
- Parse changed file and emit event
- Ignore changes from internal writes (debounce)
- Broadcast PRD updates to all connected clients
- Send within 100ms of change
- Include diff and affected features
- Support 100+ concurrent connections
- Rich text editor for PROJECT_SPEC.md
- Syntax highlighting for markdown
- Live preview pane showing current PRD structure
- Save button triggers API update
- Show "Regenerating plan..." indicator during updates
- Zustand store for PRD state
- Optimistic updates (update UI immediately)
- Rollback on API failure
- WebSocket sync for multi-client consistency
- Version history UI
- Chat input field: "Add feature: user authentication"
- Preview mode shows what will change
- Confirm/Cancel buttons before applying
- Integrate with existing chat interface

### Acceptance Criteria

- [ ] [ ] POST /api/prd/update accepts JSON or markdown and updates PRD
- [ ] [ ] File watcher detects PROJECT_SPEC.md edits within 500ms
- [ ] [ ] WebSocket broadcasts updates to all clients within 100ms
- [ ] [ ] UI editor shows current PRD content on load
- [ ] [ ] Saving in UI editor updates backend and broadcasts to other clients
- [ ] [ ] Natural language "add feature X" shows preview of changes
- [ ] [ ] Preview mode displays affected features and new tasks
- [ ] [ ] Confirm button applies changes and triggers regeneration
- [ ] [ ] Multiple clients see changes instantly (test with 3 browser windows)
- [ ] [ ] Optimistic UI updates revert on API failure
- [ ] [ ] Version history shows last 10 changes with rollback buttons
- [ ] [ ] Rollback restores PRD and triggers regeneration
- [ ] [ ] Handles 100+ concurrent WebSocket connections

## Feature 4: Broadcast Test Feature

**Priority:** Medium

### Description

Testing broadcast
