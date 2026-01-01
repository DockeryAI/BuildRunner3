# Multi-Instance Parallel Build Coordination

Run multiple Claude instances on different phases of a BUILD spec simultaneously. Maximize throughput while preventing conflicts.

## Overview

When working on large BUILD specs with independent phases, you can spawn multiple Claude instances to work in parallel. The first instance becomes the **coordinator**, subsequent instances **join** and claim available phases.

```
┌─────────────────────────────────────────────────────────────────┐
│                    Shared State Layer                           │
│  .buildrunner/parallel_state.json (file-locked, atomic writes)  │
└─────────────────────────────────────────────────────────────────┘
         ▲                    ▲                    ▲
         │                    │                    │
   ┌─────┴─────┐        ┌─────┴─────┐        ┌─────┴─────┐
   │ Claude #1 │        │ Claude #2 │        │ Claude #3 │
   │  /begin   │        │/begin join│        │/begin join│
   │ Phase 1   │        │ Phase 2   │        │ Phase 3   │
   └───────────┘        └───────────┘        └───────────┘
```

## Quick Start

### Terminal 1 (Coordinator)

```bash
cd your-project
claude

# Start working on the BUILD spec
/begin .buildrunner/builds/BUILD_X.md
```

The first instance:
- Creates `.buildrunner/parallel_state.json`
- Becomes the coordinator
- Analyzes phase dependencies
- Claims and starts Phase 1

### Terminal 2+ (Join)

```bash
cd your-project
claude

# Join the parallel session
/begin join
```

Subsequent instances:
- Detect existing `parallel_state.json`
- Register as participants
- Claim next available phase
- Work independently

## How It Works

### Phase Claiming

Phases are claimed **atomically** using file locks:

1. Instance checks phase dependencies (are prereqs complete?)
2. Instance checks file conflicts (would overlap with running work?)
3. If safe, claims phase atomically
4. Locks files listed in phase specification

### Heartbeat System

Instances send heartbeats every 60 seconds. If an instance goes 5+ minutes without a heartbeat, it's marked **stale** and its claims are released.

### Dependency Tracking

```markdown
## Phase 2: User Interface
**Depends on:** Phase 1
```

Phase 2 won't be available until Phase 1 is in `completed_phases`.

### File Conflict Detection

If Phase 1 and Phase 2 both modify `src/auth.py`, they can't run simultaneously. The coordinator detects this and marks them as sequential.

## CLI Commands

### `br parallel build-status`

Show coordination status: instances, phases, progress.

```bash
# Show status for active build
br parallel build-status

# Specify BUILD spec
br parallel build-status --spec .buildrunner/builds/BUILD_3.5.md

# Auto-cleanup stale instances
br parallel build-status --auto-cleanup
```

**Output:**

```
╭─────────────────────────────────────╮
│ BUILD Spec: BUILD_3.5.md            │
│ Coordinator: abc12345               │
╰─────────────────────────────────────╯

       Instances (3)
┏━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━━━━━━━┓
┃ ID         ┃ Status  ┃ Phase ┃Progress ┃ Last Heartbeat┃
┡━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━━━━━━━┩
│ abc12345   │ running │ 1     │ 75%     │ 30s ago       │
│ def67890   │ running │ 2     │ 50%     │ 45s ago       │
│ ghi11111   │ running │ 3     │ 25%     │ 15s ago       │
└────────────┴─────────┴───────┴─────────┴───────────────┘

Phase Status:
  Total Phases: 4
  Completed: 0
  Claimed: 3
  Available: 1
```

### `br parallel build-release`

Release stale or specific instance claims.

```bash
# Release all stale instances
br parallel build-release stale

# Release specific instance (supports partial ID)
br parallel build-release abc123

# Force without confirmation
br parallel build-release stale --force
```

### `br parallel build-finish`

Wait for all instances to complete, then cleanup.

```bash
# Wait with default 5-minute timeout
br parallel build-finish

# Custom timeout
br parallel build-finish --timeout 600

# Don't delete state file after
br parallel build-finish --no-cleanup
```

## State File Schema

Location: `.buildrunner/parallel_state.json`

```json
{
  "version": "1.0",
  "build_spec": ".buildrunner/builds/BUILD_3.5.md",
  "started_at": "2026-01-01T10:00:00Z",
  "coordinator_id": "abc12345-...",
  "instances": {
    "abc12345-...": {
      "id": "abc12345-...",
      "status": "running",
      "phase": "1",
      "tasks": ["FEAT-001", "FEAT-002"],
      "files_locked": ["src/auth.py"],
      "started_at": "2026-01-01T10:00:00Z",
      "last_heartbeat": "2026-01-01T10:05:00Z",
      "progress": 0.75
    }
  },
  "phase_analysis": {
    "phases": ["1", "2", "3"],
    "dependencies": {"2": ["1"], "3": ["2"]},
    "parallel_safe": [["1"], ["2", "3"]],
    "file_conflicts": {"1->2": ["src/shared.py"]}
  },
  "completed_phases": [],
  "sync_points": []
}
```

## Troubleshooting

### Instance appears stale but is running

The heartbeat may have failed to update. Check:
1. Is the instance still active? (check terminal)
2. Are there file permission issues on `parallel_state.json`?

If the instance is actually dead, release it:
```bash
br parallel build-release stale --force
```

### Phase not becoming available

Check dependencies:
```bash
br parallel build-status --verbose
```

Look for:
- Are prerequisite phases completed?
- Is there a file conflict with a running phase?

### File conflicts between phases

If phases share files, they must run sequentially. The coordinator detects this from the BUILD spec:

```markdown
### Phase 1
**Component:** `src/auth.py`

### Phase 2
**Component:** `src/auth.py`  # Conflict with Phase 1
```

Update your BUILD spec to minimize file overlap, or accept sequential execution.

### Coordinator died

The first available instance becomes the new coordinator automatically. If no instances are running, the next `/begin join` will take over.

### State file corrupted

Delete and restart:
```bash
rm .buildrunner/parallel_state.json
# Start fresh
/begin .buildrunner/builds/BUILD_X.md
```

## Best Practices

1. **Plan for parallelism**: When writing BUILD specs, minimize file overlap between phases
2. **Use verbose status**: Run `br parallel build-status -v` to understand blocking
3. **Clean stale instances**: Before starting, run `br parallel build-release stale`
4. **Monitor progress**: Use `br parallel build-finish` in a separate terminal to watch completion
5. **Don't exceed CPU cores**: More instances than cores causes context switching overhead
