# Parallel Orchestration Guide

**BuildRunner v3.1** - Multi-Session Coordination for Concurrent Builds

**Status:** ⚠️ **Alpha** - Unit tested (28 tests), needs production validation

---

## Overview

BuildRunner's parallel orchestration system enables you to run multiple build sessions concurrently with automatic task distribution, file locking, and real-time monitoring.

**Key Features:**
- ✅ Multi-session coordination (unit tested)
- ✅ Task distribution data structures (unit tested)
- ✅ File locking with conflict detection (unit tested)
- ⚠️ Worker health monitoring (logic defined, needs real workers)
- ⚠️ Real-time live dashboard (UI tested, needs live data)
- ⚠️ End-to-end execution (not yet tested in production)

---

## Quick Start

### Start a Parallel Session

```bash
# Start a session with 3 workers
br parallel start "Build v3.1" --tasks 50 --workers 3

# Start with live dashboard
br parallel start "Build v3.1" --tasks 50 --workers 3 --watch
```

### Monitor Progress

```bash
# View session status
br parallel status

# View specific session
br parallel status a3f2e1d9

# Show live dashboard
br parallel dashboard

# List all sessions
br parallel list
```

### Manage Sessions

```bash
# Pause a running session
br parallel pause a3f2e1d9

# Resume a paused session
br parallel resume a3f2e1d9

# Cancel a session
br parallel cancel a3f2e1d9

# Clean up old sessions
br parallel cleanup --days 7
```

---

## Architecture

### Components

**Session Manager**
- Manages session lifecycle and state
- Handles file locking with conflict detection
- Tracks progress and metadata
- Persists sessions to `.buildrunner/sessions.json`

**Worker Coordinator**
- Distributes tasks to available workers
- Monitors worker health via heartbeats
- Requeues tasks from offline workers
- Provides load distribution statistics

**Live Dashboard**
- Real-time monitoring with Rich console
- Visual progress bars and status indicators
- Multi-session view
- Worker pool status

---

## Session Lifecycle

### States

1. **CREATED** - Session initialized, not yet started
2. **RUNNING** - Session actively executing tasks
3. **PAUSED** - Session temporarily suspended
4. **COMPLETED** - All tasks finished successfully
5. **FAILED** - Session encountered fatal error
6. **CANCELLED** - Session manually cancelled

### Transitions

```
CREATED → RUNNING → COMPLETED
   ↓         ↓
   ↓      PAUSED → RUNNING
   ↓         ↓
   ↓      FAILED
   ↓         ↓
CANCELLED ←--+
```

---

## File Locking

### Purpose

File locking prevents multiple sessions from modifying the same files concurrently, avoiding race conditions and conflicts.

### How It Works

**Lock Files Before Modification:**
```python
from core.parallel import SessionManager

session_manager = SessionManager()
session = session_manager.create_session("Build", total_tasks=10)

# Lock files this session will modify
files = ["src/app.py", "src/utils.py", "tests/test_app.py"]
session_manager.lock_files(session.session_id, files)
```

**Conflict Detection:**
```python
# Session 1 locks files
session_manager.lock_files(session1_id, ["src/app.py", "src/utils.py"])

# Session 2 tries to lock overlapping files - raises ValueError
try:
    session_manager.lock_files(session2_id, ["src/utils.py", "src/config.py"])
except ValueError as e:
    print(f"Conflict: {e}")
    # Output: Files already locked by session <session1_id>: src/utils.py
```

**Unlock Files:**
```python
# Unlock specific files
session_manager.unlock_files(session_id, ["src/app.py"])

# Unlock all files
session_manager.unlock_files(session_id)
```

### Best Practices

1. **Lock Early** - Lock files before starting work
2. **Lock Minimal Set** - Only lock files you'll actually modify
3. **Unlock When Done** - Release locks as soon as possible
4. **Handle Conflicts** - Gracefully handle lock conflicts

---

## Worker Management

### Worker States

- **IDLE** - Available for task assignment
- **BUSY** - Currently executing a task
- **OFFLINE** - No heartbeat received (timeout)
- **ERROR** - Worker encountered an error

### Heartbeat Monitoring

Workers must send heartbeats to indicate they're alive:

```python
from core.parallel import WorkerCoordinator

coordinator = WorkerCoordinator(max_workers=5)
worker = coordinator.register_worker()

# Send heartbeat every 10 seconds
import time
while True:
    coordinator.heartbeat(worker.worker_id)
    time.sleep(10)
```

**Timeout:** 30 seconds (default)
- If a worker doesn't send a heartbeat within 30s, it's marked OFFLINE
- Tasks from offline workers are automatically requeued

### Task Distribution

**Automatic Assignment:**
```python
# Assign task to idle worker
worker_id = coordinator.assign_task(
    task_id="task-1",
    task_data={'description': 'Build feature X'},
    session_id=session.session_id,
)

if worker_id:
    print(f"Task assigned to worker: {worker_id}")
else:
    print("No workers available - task queued")
```

**Task Completion:**
```python
# Mark task complete
coordinator.complete_task(worker_id, task_id, success=True)

# Mark task failed
coordinator.complete_task(worker_id, task_id, success=False)
```

### Worker Scaling

```python
# Scale to 5 workers
coordinator.scale_workers(5)

# Scale down to 2 workers (removes idle workers)
coordinator.scale_workers(2)
```

---

## CLI Commands Reference

### `br parallel start`

Start a new parallel build session.

**Usage:**
```bash
br parallel start <name> [OPTIONS]
```

**Options:**
- `--tasks, -t` - Total number of tasks (default: 0)
- `--workers, -w` - Number of workers (default: 3)
- `--watch` - Show live dashboard after starting

**Examples:**
```bash
# Basic session
br parallel start "Build v3.1" --tasks 50 --workers 3

# With live dashboard
br parallel start "Build v3.1" --tasks 50 --workers 5 --watch
```

### `br parallel status`

Show session status and progress.

**Usage:**
```bash
br parallel status [SESSION_ID] [OPTIONS]
```

**Options:**
- `--verbose, -v` - Show detailed status including locked files

**Examples:**
```bash
# Latest session
br parallel status

# Specific session
br parallel status a3f2e1d9

# Verbose output
br parallel status a3f2e1d9 --verbose
```

### `br parallel list`

List all sessions.

**Usage:**
```bash
br parallel list [OPTIONS]
```

**Options:**
- `--status, -s` - Filter by status (created/running/paused/completed/failed/cancelled)
- `--limit, -l` - Maximum sessions to show (default: 20)

**Examples:**
```bash
# All sessions
br parallel list

# Only running sessions
br parallel list --status running

# Limit results
br parallel list --limit 10
```

### `br parallel pause`

Pause a running session.

**Usage:**
```bash
br parallel pause <SESSION_ID>
```

**Examples:**
```bash
br parallel pause a3f2e1d9
```

### `br parallel resume`

Resume a paused session.

**Usage:**
```bash
br parallel resume <SESSION_ID> [OPTIONS]
```

**Options:**
- `--worker, -w` - Worker ID to assign

**Examples:**
```bash
br parallel resume a3f2e1d9
br parallel resume a3f2e1d9 --worker b2c4d5e6
```

### `br parallel cancel`

Cancel a session.

**Usage:**
```bash
br parallel cancel <SESSION_ID> [OPTIONS]
```

**Options:**
- `--force, -f` - Skip confirmation prompt

**Examples:**
```bash
br parallel cancel a3f2e1d9
br parallel cancel a3f2e1d9 --force
```

### `br parallel dashboard`

Show live dashboard.

**Usage:**
```bash
br parallel dashboard [OPTIONS]
```

**Options:**
- `--duration, -d` - Duration in seconds (default: indefinite)
- `--compact, -c` - Compact mode
- `--refresh, -r` - Refresh rate in seconds (default: 0.5)

**Examples:**
```bash
# Live dashboard (Ctrl+C to exit)
br parallel dashboard

# Run for 60 seconds
br parallel dashboard --duration 60

# Compact mode with 1s refresh
br parallel dashboard --compact --refresh 1.0
```

### `br parallel workers`

List workers.

**Usage:**
```bash
br parallel workers [OPTIONS]
```

**Options:**
- `--status, -s` - Filter by status (idle/busy/offline/error)
- `--limit, -l` - Maximum workers to show (default: 50)

**Examples:**
```bash
# All workers
br parallel workers

# Only idle workers
br parallel workers --status idle

# Limit results
br parallel workers --limit 20
```

### `br parallel summary`

Show brief system summary.

**Usage:**
```bash
br parallel summary
```

**Example Output:**
```
Parallel Orchestration Summary

Workers: 2 idle / 3 busy / 0 offline (Total: 5, Utilization: 60.0%)
Sessions: 2 active / 5 total
Tasks: 127 completed / 8 failed / 4 queued
```

### `br parallel cleanup`

Clean up old completed/failed sessions.

**Usage:**
```bash
br parallel cleanup [OPTIONS]
```

**Options:**
- `--days, -d` - Delete sessions older than N days (default: 7)
- `--dry-run` - Show what would be deleted without deleting

**Examples:**
```bash
# Delete sessions older than 7 days
br parallel cleanup

# Delete sessions older than 30 days
br parallel cleanup --days 30

# Preview what would be deleted
br parallel cleanup --dry-run
```

---

## Programmatic Usage

### Basic Example

```python
from core.parallel import SessionManager, WorkerCoordinator

# Initialize
session_manager = SessionManager()
worker_coordinator = WorkerCoordinator(max_workers=3)

# Create session
session = session_manager.create_session(
    name="Build v3.1",
    total_tasks=10,
)

# Register workers
workers = []
for i in range(3):
    worker = worker_coordinator.register_worker(
        metadata={'index': i}
    )
    workers.append(worker)

# Start session
session_manager.start_session(
    session.session_id,
    worker_id=workers[0].worker_id,
)

# Lock files
files_to_modify = ["src/app.py", "src/utils.py"]
session_manager.lock_files(session.session_id, files_to_modify)

# Assign tasks
for i in range(10):
    worker_id = worker_coordinator.assign_task(
        task_id=f"task-{i}",
        task_data={'index': i},
        session_id=session.session_id,
    )

    if worker_id:
        print(f"Task {i} assigned to worker {worker_id}")
        # Execute task...
        worker_coordinator.complete_task(worker_id, f"task-{i}", success=True)
    else:
        print(f"Task {i} queued")

# Update progress
session_manager.update_progress(
    session.session_id,
    completed_tasks=10,
)

# Complete session
session_manager.complete_session(session.session_id)
```

### Live Dashboard Example

```python
from core.parallel import SessionManager, WorkerCoordinator, LiveDashboard, DashboardConfig

session_manager = SessionManager()
worker_coordinator = WorkerCoordinator(max_workers=5)

# Configure dashboard
config = DashboardConfig(
    refresh_rate=0.5,
    compact_mode=False,
    max_sessions_display=10,
    max_workers_display=20,
)

# Create dashboard
dashboard = LiveDashboard(session_manager, worker_coordinator, config)

# Show live dashboard (blocking)
dashboard.start_live(duration=60)  # Run for 60 seconds

# Or get snapshot
dashboard.render_snapshot()

# Or get summary data
summary = dashboard.get_summary()
print(f"Active sessions: {summary['sessions']['active']}")
print(f"Worker utilization: {summary['workers']['utilization']}%")
```

### Multi-Session Example

```python
from core.parallel import SessionManager, WorkerCoordinator

session_manager = SessionManager()
worker_coordinator = WorkerCoordinator(max_workers=5)

# Create two sessions
session1 = session_manager.create_session("Build Frontend", total_tasks=20)
session2 = session_manager.create_session("Build Backend", total_tasks=30)

# Start both
session_manager.start_session(session1.session_id)
session_manager.start_session(session2.session_id)

# Lock different files to avoid conflicts
session_manager.lock_files(session1.session_id, [
    "frontend/app.tsx",
    "frontend/components.tsx",
])

session_manager.lock_files(session2.session_id, [
    "backend/server.py",
    "backend/routes.py",
])

# Distribute tasks across workers
tasks = [
    ("frontend-task-1", session1.session_id),
    ("frontend-task-2", session1.session_id),
    ("backend-task-1", session2.session_id),
    ("backend-task-2", session2.session_id),
]

for task_id, session_id in tasks:
    worker_id = worker_coordinator.assign_task(task_id, {}, session_id)
    if worker_id:
        print(f"{task_id} → worker {worker_id}")
```

---

## Performance

### Metrics

**Session Operations:**
- Create session: <1ms
- Lock files: O(n) where n = number of active sessions
- Update progress: <1ms
- Persist to disk: <10ms

**Worker Operations:**
- Register worker: <1ms
- Assign task: O(n) where n = number of workers
- Complete task: <1ms
- Health check: O(n) where n = number of workers

**Dashboard:**
- Render snapshot: <50ms typical
- Live refresh: 0.5s default (configurable)

### Scalability

**Recommended Limits:**
- Workers: 3-10 per session (optimal)
- Concurrent sessions: 5-20 (depending on resources)
- Tasks per session: Unlimited (tested with 1000+)
- Files locked per session: Hundreds (O(n) lookup)

**Storage:**
- Sessions file: `.buildrunner/sessions.json`
- Size: ~1KB per session
- Auto-cleanup: Configurable (default: 7 days)

---

## Best Practices

### Session Management

1. **Name Sessions Clearly**
   ```bash
   br parallel start "Build v3.1 Frontend" --tasks 50
   br parallel start "Build v3.1 Backend" --tasks 40
   ```

2. **Set Accurate Task Counts**
   - Enables accurate progress tracking
   - Helps with resource planning

3. **Clean Up Regularly**
   ```bash
   # Weekly cleanup
   br parallel cleanup --days 7
   ```

### Worker Management

1. **Right-Size Worker Pools**
   - 3-5 workers: Most builds
   - 6-10 workers: Large builds with many independent tasks
   - 1-2 workers: Small builds or resource-constrained environments

2. **Monitor Worker Health**
   ```bash
   # Check worker status regularly
   br parallel workers
   ```

3. **Handle Failures Gracefully**
   - Tasks from offline workers are auto-requeued
   - Monitor failed task counts

### File Locking

1. **Lock Minimal Set**
   - Only lock files you'll modify
   - Reduces chance of conflicts

2. **Lock Early**
   - Lock before starting work
   - Prevents race conditions

3. **Handle Conflicts**
   ```python
   try:
       session_manager.lock_files(session_id, files)
   except ValueError as e:
       # Files locked by another session
       # Wait, retry, or choose different files
       print(f"Conflict: {e}")
   ```

### Monitoring

1. **Use Live Dashboard**
   ```bash
   # Monitor during long builds
   br parallel dashboard
   ```

2. **Check Progress Regularly**
   ```bash
   # Quick status check
   br parallel status
   ```

3. **Review Statistics**
   ```bash
   # System summary
   br parallel summary
   ```

---

## Troubleshooting

### Session Won't Start

**Symptom:** Session stuck in CREATED state

**Solutions:**
1. Check if session has worker assigned
   ```bash
   br parallel status <session-id> --verbose
   ```

2. Manually assign worker
   ```bash
   br parallel resume <session-id> --worker <worker-id>
   ```

### Worker Goes Offline

**Symptom:** Worker marked OFFLINE, tasks not completing

**Solutions:**
1. Check worker process is running
2. Verify heartbeat mechanism is working
3. Tasks will be automatically requeued
4. Register new worker to replace offline one

### File Lock Conflicts

**Symptom:** `ValueError: Files already locked by session...`

**Solutions:**
1. Check which session has the lock
   ```bash
   br parallel list --status running
   br parallel status <session-id> --verbose
   ```

2. Wait for other session to complete or pause it
   ```bash
   br parallel pause <other-session-id>
   ```

3. Choose different files to modify

### High Memory Usage

**Symptom:** Large `.buildrunner/sessions.json` file

**Solutions:**
1. Clean up old sessions
   ```bash
   br parallel cleanup --days 7
   ```

2. Complete/cancel abandoned sessions
   ```bash
   br parallel list
   br parallel cancel <old-session-id>
   ```

### Dashboard Not Updating

**Symptom:** Live dashboard frozen or not refreshing

**Solutions:**
1. Check refresh rate
   ```bash
   br parallel dashboard --refresh 0.5
   ```

2. Restart dashboard (Ctrl+C and restart)

3. Check terminal size (dashboard needs minimum dimensions)

---

## Advanced Topics

### Custom Worker Implementations

```python
from core.parallel import WorkerCoordinator
import threading
import time

class CustomWorker:
    def __init__(self, coordinator: WorkerCoordinator):
        self.coordinator = coordinator
        self.worker = coordinator.register_worker(metadata={
            'type': 'custom',
            'version': '1.0',
        })
        self.running = True

    def start(self):
        # Heartbeat thread
        heartbeat_thread = threading.Thread(target=self._heartbeat_loop)
        heartbeat_thread.start()

        # Work loop
        work_thread = threading.Thread(target=self._work_loop)
        work_thread.start()

    def _heartbeat_loop(self):
        while self.running:
            self.coordinator.heartbeat(self.worker.worker_id)
            time.sleep(10)  # Every 10 seconds

    def _work_loop(self):
        while self.running:
            # Check for assigned task
            worker = self.coordinator.get_worker(self.worker.worker_id)
            if worker.current_task:
                self._execute_task(worker.current_task)
            time.sleep(1)

    def _execute_task(self, task_id: str):
        try:
            # Execute task...
            result = self.execute_task_logic(task_id)
            self.coordinator.complete_task(
                self.worker.worker_id,
                task_id,
                success=True,
            )
        except Exception as e:
            self.coordinator.complete_task(
                self.worker.worker_id,
                task_id,
                success=False,
            )

    def stop(self):
        self.running = False
        self.coordinator.unregister_worker(self.worker.worker_id)
```

### Session Recovery

```python
from core.parallel import SessionManager

# Load existing sessions from disk
session_manager = SessionManager()

# Get interrupted sessions
interrupted = [
    s for s in session_manager.list_sessions()
    if s.status == SessionStatus.RUNNING
]

# Resume each one
for session in interrupted:
    print(f"Resuming session: {session.name}")
    # Session already in RUNNING state, just need to reassign work
    # ... assign pending tasks to workers ...
```

---

## Integration with Task Orchestrator

The parallel system integrates with BuildRunner's task orchestrator (Build 2B):

```python
from core.orchestrator import Orchestrator
from core.parallel import SessionManager, WorkerCoordinator

class ParallelOrchestrator(Orchestrator):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.session_manager = SessionManager()
        self.worker_coordinator = WorkerCoordinator(max_workers=5)

    def execute_batches_parallel(self, batches, session_name):
        # Create session
        session = self.session_manager.create_session(
            name=session_name,
            total_tasks=len(batches),
        )

        # Collect all files that will be modified
        all_files = set()
        for batch in batches:
            all_files.update(batch.expected_files)

        # Lock files
        self.session_manager.lock_files(session.session_id, list(all_files))

        # Distribute batches to workers
        for batch in batches:
            worker_id = self.worker_coordinator.assign_task(
                task_id=batch.id,
                task_data=batch.to_dict(),
                session_id=session.session_id,
            )

            if worker_id:
                # Execute on worker
                self.execute_batch_on_worker(batch, worker_id)

        # Wait for completion
        self.wait_for_session(session.session_id)

        # Cleanup
        self.session_manager.unlock_files(session.session_id)
        self.session_manager.complete_session(session.session_id)
```

---

## FAQ

**Q: How many workers should I use?**

A: Start with 3-5 workers. More workers help if you have many independent tasks, but too many can cause overhead. Monitor utilization with `br parallel workers`.

**Q: What happens if a worker crashes?**

A: After 30 seconds without a heartbeat, the worker is marked OFFLINE and its task is automatically requeued for another worker.

**Q: Can I run sessions on different machines?**

A: Not currently. Sessions and workers must run on the same machine. Distributed execution is planned for a future release.

**Q: How do I debug file lock conflicts?**

A: Use `br parallel status <session-id> --verbose` to see which files are locked by each session.

**Q: Can I manually assign tasks to specific workers?**

A: Not directly through the CLI. You can do this programmatically with `worker_coordinator.assign_task()`.

**Q: How is session data stored?**

A: Sessions are stored in `.buildrunner/sessions.json` and automatically loaded on startup.

**Q: Can I pause all sessions at once?**

A: Not with a single command. Use `br parallel list --status running` to get running sessions, then pause each one.

---

## See Also

- [ROUTING.md](ROUTING.md) - Model routing and complexity estimation
- [TELEMETRY.md](TELEMETRY.md) - Monitoring and metrics
- [SECURITY.md](SECURITY.md) - Security safeguards
- [README.md](README.md) - Main documentation

---

*BuildRunner v3.1 - Parallel Orchestration System*
