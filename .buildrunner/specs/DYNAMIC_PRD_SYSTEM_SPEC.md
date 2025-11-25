# Dynamic PRD-Driven Build System

**Project:** BuildRunner 3 - Dynamic PRD Integration
**Version:** 1.0.0
**Created:** 2025-01-19

## Project Overview

Transform BuildRunner 3 into a dynamic, PRD-driven system where the PROJECT_SPEC.md is the single source of truth. Any change to the PRD (via chat, UI, or direct file edit) automatically regenerates the build plan while preserving all completed work.

## Core Requirements

1. **PRD as Single Source of Truth**: PROJECT_SPEC.md drives all build planning and execution
2. **Automatic Regeneration**: Any PRD change triggers intelligent plan regeneration (<3s for 90% of changes)
3. **Multi-Channel Updates**: Support PRD updates from:
   - Natural language chat messages
   - UI-based PRD editor
   - Direct file edits to PROJECT_SPEC.md
4. **Zero Work Loss**: Never regenerate or reset completed tasks
5. **Real-time Sync**: All clients see PRD changes instantly via WebSocket
6. **Smart Merging**: Handle concurrent edits via operational transforms

## Success Criteria

- [ ] PRD changes from any source trigger automatic plan regeneration
- [ ] Regeneration completes in <3 seconds for 1-2 feature changes
- [ ] Completed tasks are never regenerated or reset
- [ ] WebSocket broadcasts PRD changes to all connected clients in <100ms
- [ ] Natural language input (e.g., "add user authentication") correctly updates PRD
- [ ] UI editor shows live preview of plan changes before applying
- [ ] Direct PROJECT_SPEC.md edits are detected within 500ms
- [ ] Concurrent edits are merged without conflicts
- [ ] Rollback capability for last 10 PRD versions

---

## Feature 1: PRD Controller

**Priority:** Critical
**Component:** core/prd/prd_controller.py

### Description

Central controller that manages the PROJECT_SPEC.md as the single source of truth. Handles all PRD updates from multiple sources, provides version control, and emits events for downstream systems.

### Requirements

1. **Unified PRD Interface**
   - Single in-memory representation of PRD (PydanticV2 model)
   - Bidirectional sync with PROJECT_SPEC.md file
   - Automatic file write on any change
   - Atomic updates with file locking

2. **Natural Language Processing**
   - Parse chat messages to detect PRD change intent
   - Extract feature additions/modifications/deletions
   - Convert natural language to structured PRD updates
   - Support commands: "add feature X", "remove feature Y", "update feature Z to..."

3. **Version Control**
   - Store last 10 PRD versions in memory
   - Each version tagged with timestamp, author, change summary
   - Rollback to previous version
   - Diff between versions showing exact changes

4. **Event System**
   - Emit `prd.updated` event on every change
   - Event payload includes: full PRD, changed sections, diff
   - Support multiple subscribers
   - Async event dispatch (non-blocking)

5. **Concurrency Management**
   - File-level locking for PROJECT_SPEC.md writes
   - Operational transforms for concurrent edits
   - Conflict detection and resolution
   - Last-write-wins with merge capability

### Acceptance Criteria

- [ ] Can parse natural language: "add authentication feature" → updates PRD with new feature
- [ ] Updates to in-memory PRD automatically write to PROJECT_SPEC.md within 100ms
- [ ] File locking prevents simultaneous writes (test with 5 concurrent updates)
- [ ] Can rollback to any of last 10 versions
- [ ] Emits `prd.updated` event within 50ms of change
- [ ] Event payload contains full PRD and diff
- [ ] Handles 100+ subscribers without performance degradation
- [ ] Concurrent edits merge correctly (test 3 simultaneous updates)

### Technical Details

**Dependencies:**
- Pydantic V2 for PRD model
- watchdog for file monitoring
- filelock for atomic writes
- spaCy for NLP (or simple regex for MVP)

**Integration Points:**
- Input: Natural language parser, WebSocket handler, file watcher
- Output: Event emitter (to Adaptive Planner), WebSocket broadcaster

**Data Models:**
```python
class PRDVersion:
    timestamp: int
    author: str
    prd_snapshot: PRD
    changes: Dict[str, Any]
    summary: str

class PRDChangeEvent:
    event_type: str  # "feature_added", "feature_removed", "feature_updated"
    affected_features: List[str]
    full_prd: PRD
    diff: Dict[str, Any]
    timestamp: int
```

---

## Feature 2: Adaptive Planner

**Priority:** Critical
**Component:** core/orchestrator/adaptive_planner.py

### Description

Intelligent planner that listens to PRD change events and regenerates only the affected portions of the build plan. Preserves all completed work and optimizes the task queue based on new dependencies.

### Requirements

1. **Event-Driven Regeneration**
   - Subscribe to `prd.updated` events from PRD Controller
   - Trigger regeneration within 100ms of event receipt
   - Run regeneration in background (non-blocking)

2. **Differential Task Generation**
   - Compare new PRD vs current task queue
   - Identify added/removed/modified features
   - Generate tasks only for changed features
   - Preserve existing tasks for unchanged features

3. **Completed Work Protection**
   - Never regenerate tasks with status "completed"
   - Never reset progress on in-progress tasks
   - If feature is removed, mark its tasks as "cancelled" (don't delete)
   - If feature is modified, only regenerate pending tasks

4. **Dependency Re-evaluation**
   - Recalculate dependency graph with new tasks
   - Detect new blocking relationships
   - Update "ready" task queue
   - Preserve topological order

5. **Queue Optimization**
   - Re-prioritize tasks based on new dependencies
   - Batch new tasks with existing tasks efficiently
   - Minimize context switches
   - Notify orchestrator of queue changes

6. **Performance Optimization**
   - Cache unchanged task generation
   - Incremental dependency graph updates (not full rebuild)
   - Target <3s regeneration for 1-2 feature changes
   - Parallel task decomposition for multiple features

### Acceptance Criteria

- [ ] Receives `prd.updated` event and starts regeneration within 100ms
- [ ] Regeneration for 1-2 feature changes completes in <3 seconds
- [ ] Completed tasks remain unchanged after regeneration
- [ ] In-progress tasks retain their status and progress percentage
- [ ] Removed features have tasks marked "cancelled", not deleted
- [ ] Modified features only regenerate pending tasks
- [ ] Dependency graph updates correctly with new tasks
- [ ] New "ready" tasks appear in queue within 1 second
- [ ] Concurrent PRD changes queue regeneration (no race conditions)
- [ ] Task batches maintain coherence (no domain mixing)

### Technical Details

**Dependencies:**
- Existing task_decomposer.py
- Existing dependency_graph.py
- Existing task_queue.py
- Existing priority_scheduler.py

**Integration Points:**
- Input: PRD Controller events
- Output: Updated task queue, orchestrator notifications

**Algorithms:**
- Tree-diff for feature comparison
- Incremental topological sort for dependency updates
- Smart merge for task queue integration

---

## Feature 3: Sync Layer

**Priority:** Critical
**Components:**
- api/routes/prd_sync.py (backend)
- ui/src/stores/prdStore.ts (frontend)
- ui/src/components/PRDEditor.tsx (frontend)

### Description

Universal synchronization layer that connects all PRD input channels (chat, UI, file) and broadcasts changes to all clients in real-time. Provides consistent API for PRD modifications and ensures all clients stay in sync.

### Requirements

1. **Universal PRD API**
   - POST /api/prd/update - Accept PRD changes from any source
   - GET /api/prd/current - Get current PRD state
   - POST /api/prd/parse-nl - Parse natural language to PRD changes (preview mode)
   - POST /api/prd/rollback/:version - Rollback to specific version
   - GET /api/prd/versions - List version history
   - WebSocket /api/prd/stream - Real-time PRD update stream

2. **File Watcher**
   - Monitor PROJECT_SPEC.md for direct edits
   - Detect changes within 500ms
   - Parse changed file and emit event
   - Ignore changes from internal writes (debounce)

3. **WebSocket Broadcasting**
   - Broadcast PRD updates to all connected clients
   - Send within 100ms of change
   - Include diff and affected features
   - Support 100+ concurrent connections

4. **UI Editor**
   - Rich text editor for PROJECT_SPEC.md
   - Syntax highlighting for markdown
   - Live preview pane showing current PRD structure
   - Save button triggers API update
   - Show "Regenerating plan..." indicator during updates

5. **Frontend State Management**
   - Zustand store for PRD state
   - Optimistic updates (update UI immediately)
   - Rollback on API failure
   - WebSocket sync for multi-client consistency
   - Version history UI

6. **Natural Language Input**
   - Chat input field: "Add feature: user authentication"
   - Preview mode shows what will change
   - Confirm/Cancel buttons before applying
   - Integrate with existing chat interface

### Acceptance Criteria

- [ ] POST /api/prd/update accepts JSON or markdown and updates PRD
- [ ] File watcher detects PROJECT_SPEC.md edits within 500ms
- [ ] WebSocket broadcasts updates to all clients within 100ms
- [ ] UI editor shows current PRD content on load
- [ ] Saving in UI editor updates backend and broadcasts to other clients
- [ ] Natural language "add feature X" shows preview of changes
- [ ] Preview mode displays affected features and new tasks
- [ ] Confirm button applies changes and triggers regeneration
- [ ] Multiple clients see changes instantly (test with 3 browser windows)
- [ ] Optimistic UI updates revert on API failure
- [ ] Version history shows last 10 changes with rollback buttons
- [ ] Rollback restores PRD and triggers regeneration
- [ ] Handles 100+ concurrent WebSocket connections

### Technical Details

**Backend Dependencies:**
- FastAPI for REST API
- WebSockets for real-time updates
- watchdog for file monitoring

**Frontend Dependencies:**
- Zustand for state management
- Monaco Editor or CodeMirror for PRD editing
- WebSocket client with auto-reconnect
- React components

**Integration Points:**
- Input: HTTP API, file watcher, WebSocket messages
- Output: PRD Controller, WebSocket broadcast, UI state updates

**Data Flow:**
1. User input (chat/UI/file) → Sync Layer API
2. Sync Layer → PRD Controller (update)
3. PRD Controller → Emits `prd.updated` event
4. Sync Layer (event listener) → WebSocket broadcast
5. All clients → Receive update, refresh UI
6. Adaptive Planner (event listener) → Regenerate tasks

---

## Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      INPUT CHANNELS                          │
├──────────────┬──────────────┬──────────────┬───────────────┤
│   Chat NL    │  UI Editor   │  File Edit   │  API Direct   │
└──────┬───────┴──────┬───────┴──────┬───────┴───────┬───────┘
       │              │              │               │
       └──────────────┴──────────────┴───────────────┘
                           │
                           ▼
                   ┌───────────────┐
                   │   Sync Layer  │◄────────────┐
                   │(API + WS + FW)│             │
                   └───────┬───────┘             │
                           │                     │
                           ▼                     │
                   ┌───────────────┐         Broadcast
                   │PRD Controller │             │
                   │ (Core Logic)  │             │
                   └───────┬───────┘             │
                           │                     │
                    Emit prd.updated             │
                           │                     │
                ┌──────────┴──────────┐          │
                ▼                     ▼          │
        ┌───────────────┐     ┌──────────────┐  │
        │    Adaptive   │     │ Sync Layer   │──┘
        │    Planner    │     │ (WebSocket)  │
        └───────┬───────┘     └──────────────┘
                │                     │
        Regenerate Tasks              │
                │                     ▼
                ▼              ┌─────────────┐
        ┌───────────────┐     │UI Clients   │
        │  Orchestrator │     │(Real-time   │
        │  (Execute)    │     │ Updates)    │
        └───────────────┘     └─────────────┘
```

---

## Technical Constraints

1. **Performance**
   - Regeneration: <3s for 1-2 features, <10s for 5+ features
   - WebSocket latency: <100ms
   - File watch detection: <500ms
   - API response: <200ms for simple updates

2. **Reliability**
   - Zero data loss on PRD updates
   - Automatic recovery from file write failures
   - WebSocket auto-reconnect with exponential backoff
   - Transaction-like updates (atomic)

3. **Scalability**
   - Support 100+ concurrent WebSocket connections
   - Handle PRDs with 50+ features
   - Manage task queues with 500+ tasks
   - Version history for last 10 changes (circular buffer)

4. **Compatibility**
   - Integrate with existing BR3 task generation
   - Use existing dependency_graph, task_queue, orchestrator
   - Backward compatible with static spec mode
   - No breaking changes to existing APIs

---

## Implementation Order

1. **Phase 1: PRD Controller (Feature 1)**
   - Build core PRD model and version control
   - Implement event system
   - Add file sync and locking
   - Test concurrency and rollback

2. **Phase 2: Adaptive Planner (Feature 2)**
   - Subscribe to PRD events
   - Implement differential regeneration
   - Add completed work protection
   - Optimize for <3s regeneration

3. **Phase 3: Sync Layer (Feature 3)**
   - Build REST API endpoints
   - Add file watcher
   - Implement WebSocket broadcasting
   - Create UI editor and state management

4. **Phase 4: Integration**
   - Connect all three components
   - End-to-end testing
   - Performance optimization
   - Documentation

---

## Testing Strategy

1. **Unit Tests** (per component)
   - PRD Controller: version control, event emission, NLP parsing
   - Adaptive Planner: differential regen, dependency updates, queue merging
   - Sync Layer: API endpoints, file watching, WebSocket broadcast

2. **Integration Tests**
   - Chat message → PRD update → Task regeneration
   - UI editor save → WebSocket broadcast → Multi-client sync
   - Direct file edit → Detection → Plan update
   - Concurrent edits → Merge resolution

3. **Performance Tests**
   - Regeneration time for 1, 2, 5, 10 feature changes
   - WebSocket latency with 10, 50, 100 clients
   - File watch detection time
   - API throughput

4. **E2E Tests**
   - Complete user flow: chat → PRD → tasks → execution
   - Multi-client sync (3 browsers)
   - Rollback and recovery scenarios

---

## Non-Functional Requirements

1. **Usability**
   - Zero configuration required
   - Works out of the box with existing BR3 projects
   - Clear UI feedback during regeneration
   - Preview mode for all changes

2. **Maintainability**
   - Clean separation of concerns
   - Comprehensive logging
   - Error messages with actionable guidance
   - Type hints and documentation

3. **Security**
   - Validate all user input (XSS prevention)
   - File path sanitization
   - WebSocket authentication (future)
   - Rate limiting on API endpoints

---

## Success Metrics

- **User Experience**: User says "add auth" and sees tasks generated within 3 seconds
- **Reliability**: 0 data loss incidents in 100 regeneration cycles
- **Performance**: 95% of regenerations complete in <3 seconds
- **Real-time**: 100% of clients receive updates within 100ms
- **Adoption**: Used as default mode for all new BR3 projects

---

**End of Specification**
