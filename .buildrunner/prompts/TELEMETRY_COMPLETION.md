# Worktree B: Telemetry Completion (3-4 hours)

## Goal
Wire telemetry auto-collection into orchestrator with SQLite persistence.

## Tasks

### 1. Add SQLite Persistence (1.5 hours)
**File**: `core/telemetry/collector.py`

Add to EventCollector:
```python
def __init__(self, db_path: Path = None):
    self.db_path = db_path or Path('.buildrunner/telemetry.db')
    self._init_database()

def _init_database(self):
    """Create events table"""
    # CREATE TABLE events (
    #   id INTEGER PRIMARY KEY AUTOINCREMENT,
    #   event_type TEXT NOT NULL,
    #   timestamp TEXT NOT NULL,
    #   data JSON,
    #   task_id TEXT,
    #   session_id TEXT,
    #   duration_ms INTEGER
    # )
    # CREATE INDEX idx_event_type ON events(event_type)
    # CREATE INDEX idx_timestamp ON events(timestamp)

def collect(self, event: TelemetryEvent):
    """Collect event and persist to SQLite"""
    # Serialize event to JSON
    # INSERT INTO events
    # COMMIT
```

### 2. Wire into Orchestrator (1.5 hours)
**File**: `core/orchestrator.py`

Modify Orchestrator class:
```python
from core.telemetry.collector import EventCollector
from core.telemetry.events import TaskEvent, BuildEvent, ModelEvent

class Orchestrator:
    def __init__(self, ...):
        self.event_collector = EventCollector()

    def execute_task(self, task: Task):
        # Emit TASK_STARTED
        self.event_collector.collect(TaskEvent(
            event_type='TASK_STARTED',
            task_id=task.id,
            timestamp=datetime.now(UTC).isoformat()
        ))

        try:
            start = time.time()
            result = self._run_task(task)
            duration = (time.time() - start) * 1000

            # Emit TASK_COMPLETED
            self.event_collector.collect(TaskEvent(
                event_type='TASK_COMPLETED',
                task_id=task.id,
                duration_ms=duration
            ))
        except Exception as e:
            # Emit TASK_FAILED
            self.event_collector.collect(TaskEvent(
                event_type='TASK_FAILED',
                task_id=task.id,
                error=str(e)
            ))

    def execute_batch(self, batch: Batch):
        # Emit BUILD_STARTED
        self.event_collector.collect(BuildEvent(
            event_type='BUILD_STARTED',
            batch_id=batch.id
        ))

        # Execute tasks...

        # Emit BUILD_COMPLETED
        self.event_collector.collect(BuildEvent(
            event_type='BUILD_COMPLETED',
            batch_id=batch.id,
            tasks_completed=len(batch.tasks)
        ))
```

Auto-emit on model selection:
```python
def select_model(self, task: Task):
    model = self.complexity_estimator.estimate(task.description)

    # Emit MODEL_SELECTED
    self.event_collector.collect(ModelEvent(
        event_type='MODEL_SELECTED',
        task_id=task.id,
        model=model.recommended_model,
        complexity=model.level.value
    ))

    return model
```

### 3. Integration Tests (1 hour)
**File**: `tests/integration/test_telemetry_integration.py`

```python
def test_orchestrator_emits_events(tmp_path):
    """Test orchestrator auto-emits and persists events"""
    db_path = tmp_path / "telemetry.db"
    orchestrator = Orchestrator(telemetry_db=db_path)

    # Execute task
    task = Task(id='test', description='test task')
    orchestrator.execute_task(task)

    # Verify events in database
    db = Database(db_path)
    events = db.query("SELECT * FROM events WHERE task_id = 'test'")

    assert len(events) >= 2  # STARTED + COMPLETED
    assert events[0]['event_type'] == 'TASK_STARTED'
    assert events[-1]['event_type'] == 'TASK_COMPLETED'
    assert events[-1]['duration_ms'] > 0

def test_telemetry_cli_shows_data(tmp_path):
    """Test CLI displays real telemetry data"""
    # Run orchestrator to generate events
    # Execute: br telemetry summary
    # Verify output contains event counts
```

### 4. CLI Validation (0.5 hours)
Test these commands show real data:
```bash
br run --auto  # Collects events
br telemetry summary  # Shows aggregated stats
br telemetry events --last 10  # Shows recent events
br telemetry events --type TASK_COMPLETED
```

## Acceptance Criteria
- [ ] `.buildrunner/telemetry.db` created automatically
- [ ] Orchestrator emits events on all task/batch/model operations
- [ ] Events persisted to SQLite with correct schema
- [ ] `br telemetry summary` shows real aggregated data
- [ ] `br telemetry events` queries work
- [ ] Integration tests passing (90%+ coverage)
- [ ] Quality check passes

## Notes
- Use existing Database class from core/persistence/
- Follow event schema from core/telemetry/events.py
- Non-blocking collection (don't slow down orchestrator)
- Handle database errors gracefully
