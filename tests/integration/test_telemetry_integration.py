"""
Integration tests for telemetry system
"""
import pytest
from pathlib import Path
from core.orchestrator import TaskOrchestrator
from core.telemetry import EventType, TaskEvent, BuildEvent, EventCollector
from core.integrations.telemetry_integration import (
    integrate_telemetry,
    emit_task_event,
    emit_batch_event,
    get_event_summary,
)
from core.persistence.database import Database


class TestTelemetryIntegration:
    """Test telemetry integration with orchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with telemetry enabled"""
        return TaskOrchestrator(enable_telemetry=True, enable_routing=False, enable_parallel=False)

    @pytest.fixture
    def orchestrator_without_telemetry(self):
        """Create orchestrator without telemetry"""
        return TaskOrchestrator(enable_telemetry=False, enable_routing=False, enable_parallel=False)

    def test_integrate_telemetry_creates_event_collector(self, orchestrator):
        """Test that telemetry integration creates event collector"""
        assert orchestrator.event_collector is not None
        assert hasattr(orchestrator.event_collector, 'collect')
        assert hasattr(orchestrator.event_collector, 'get_recent')

    def test_orchestrator_without_telemetry_has_no_collector(self, orchestrator_without_telemetry):
        """Test that disabling telemetry doesn't create collector"""
        assert orchestrator_without_telemetry.event_collector is None

    def test_execute_batch_emits_batch_events(self, orchestrator):
        """Test that executing a batch emits batch started and completed events"""
        tasks = [
            {'id': 'task1', 'name': 'Test Task 1', 'description': 'Test description'},
            {'id': 'task2', 'name': 'Test Task 2', 'description': 'Another test'},
        ]

        result = orchestrator.execute_batch(tasks)

        assert result['success'] is True

        # Check that events were collected
        events = orchestrator.event_collector.get_recent(count=100)
        assert len(events) > 0

        # Find batch events
        batch_events = [e for e in events if isinstance(e, BuildEvent)]
        assert len(batch_events) >= 2  # At least started and completed

        # Verify event types
        event_types = [e.event_type for e in batch_events]
        assert EventType.BUILD_STARTED in event_types
        assert EventType.BUILD_COMPLETED in event_types

    def test_execute_batch_emits_task_events(self, orchestrator):
        """Test that executing a batch emits task started and completed events"""
        tasks = [
            {'id': 'task1', 'name': 'Test Task', 'description': 'Test'},
        ]

        result = orchestrator.execute_batch(tasks)

        assert result['success'] is True

        # Check for task events
        events = orchestrator.event_collector.get_recent(count=100)
        task_events = [e for e in events if isinstance(e, TaskEvent)]

        assert len(task_events) >= 2  # Started and completed

        # Verify task event types
        event_types = [e.event_type for e in task_events]
        assert EventType.TASK_STARTED in event_types
        assert EventType.TASK_COMPLETED in event_types

    def test_emit_task_event_creates_event(self, orchestrator):
        """Test emitting a task event"""
        event = emit_task_event(
            orchestrator.event_collector,
            EventType.TASK_STARTED,
            task_id="test_task_1",
            task_type="Test Task",
            task_description="Test description",
            metadata={'test': 'data'},
        )

        assert isinstance(event, TaskEvent)
        assert event.task_id == "test_task_1"
        assert event.task_type == "Test Task"
        assert event.metadata['test'] == 'data'

        # Verify event was collected
        events = orchestrator.event_collector.get_recent(count=100)
        assert event in events

    def test_emit_batch_event_creates_event(self, orchestrator):
        """Test emitting a batch event"""
        event = emit_batch_event(
            orchestrator.event_collector,
            EventType.BUILD_STARTED,
            batch_id="batch_1",
            task_count=5,
            metadata={'test': 'batch_data'},
        )

        assert isinstance(event, BuildEvent)
        assert event.build_id == "batch_1"
        assert event.metadata['test'] == 'batch_data'

        # Verify event was collected
        events = orchestrator.event_collector.get_recent(count=100)
        assert event in events

    def test_event_summary_counts_events_correctly(self, orchestrator):
        """Test that event summary provides correct counts"""
        # Emit some events
        emit_task_event(
            orchestrator.event_collector,
            EventType.TASK_STARTED,
            task_id="task1",
        )
        emit_task_event(
            orchestrator.event_collector,
            EventType.TASK_COMPLETED,
            task_id="task1",
            success=True,
        )
        emit_task_event(
            orchestrator.event_collector,
            EventType.TASK_FAILED,
            task_id="task2",
            success=False,
        )

        summary = get_event_summary(orchestrator.event_collector)

        assert summary['total_events'] == 3
        assert summary['tasks_completed'] == 1
        assert summary['tasks_failed'] == 1

    def test_execute_batch_tracks_performance(self, orchestrator):
        """Test that batch execution tracks performance metrics"""
        tasks = [{'id': 'task1', 'name': 'Test', 'description': 'Test'}]

        result = orchestrator.execute_batch(tasks)
        assert result['success'] is True

        # Check that performance events were emitted
        events = orchestrator.event_collector.get_recent(count=100)

        # Should have performance event from telemetry context
        from core.telemetry import PerformanceEvent
        perf_events = [e for e in events if isinstance(e, PerformanceEvent)]
        assert len(perf_events) > 0

        # Verify performance event has metric_value (duration)
        for event in perf_events:
            assert hasattr(event, 'metric_value')
            assert event.metric_value >= 0

    def test_orchestrator_emits_and_persists_events(self, tmp_path):
        """Test orchestrator auto-emits and persists events to SQLite"""
        # Create orchestrator with custom database path
        db_path = tmp_path / "telemetry.db"

        # Create event collector with custom db path
        collector = EventCollector(db_path=db_path, use_sqlite=True)

        # Create orchestrator and manually assign collector
        orchestrator = TaskOrchestrator(
            enable_telemetry=False,  # Don't auto-create
            enable_routing=False,
            enable_parallel=False,
        )
        orchestrator.event_collector = collector

        # Execute tasks
        tasks = [
            {'id': 'test1', 'name': 'Test Task', 'description': 'Test task description'},
            {'id': 'test2', 'name': 'Another Task', 'description': 'Another description'},
        ]

        result = orchestrator.execute_batch(tasks)
        assert result['success'] is True

        # Verify database was created
        assert db_path.exists()

        # Query database directly
        db = Database(db_path)
        events = db.query("SELECT * FROM events WHERE task_id IN ('test1', 'test2') ORDER BY timestamp")

        # Should have events for both tasks (started + completed for each)
        assert len(events) >= 4

        # Verify event types
        event_types = [e['event_type'] for e in events]
        assert 'task_started' in event_types
        assert 'task_completed' in event_types

        # Verify first event
        first_event = events[0]
        assert first_event['event_type'] in ['task_started', 'task_completed']
        assert first_event['task_id'] in ['test1', 'test2']
        assert first_event['timestamp'] is not None

        # Verify completed events have duration
        completed_events = [e for e in events if e['event_type'] == 'task_completed']
        assert len(completed_events) >= 2

        db.close()

    def test_sqlite_persistence_query_by_type(self, tmp_path):
        """Test querying events by type from SQLite"""
        db_path = tmp_path / "telemetry.db"
        collector = EventCollector(db_path=db_path, use_sqlite=True)

        # Emit various event types
        emit_task_event(
            collector,
            EventType.TASK_STARTED,
            task_id="task1",
            task_type="Test",
        )
        emit_task_event(
            collector,
            EventType.TASK_COMPLETED,
            task_id="task1",
            task_type="Test",
        )
        emit_batch_event(
            collector,
            EventType.BUILD_STARTED,
            batch_id="batch1",
            task_count=1,
        )

        # Query only task events
        from core.telemetry.event_collector import EventFilter
        filter = EventFilter(event_types=[EventType.TASK_STARTED, EventType.TASK_COMPLETED])
        task_events = collector.query(filter=filter)

        assert len(task_events) == 2
        assert all(isinstance(e, TaskEvent) for e in task_events)

    def test_sqlite_persistence_recent_events(self, tmp_path):
        """Test getting recent events from SQLite"""
        db_path = tmp_path / "telemetry.db"
        collector = EventCollector(db_path=db_path, use_sqlite=True)

        # Emit multiple events
        for i in range(20):
            emit_task_event(
                collector,
                EventType.TASK_STARTED,
                task_id=f"task{i}",
                task_type="Test",
            )

        # Get recent 10
        recent = collector.get_recent(count=10)

        assert len(recent) == 10
        # Most recent should be task19 (0-indexed, so 19 is the 20th task)
        assert recent[0].task_id == "task19"

    def test_sqlite_statistics_view(self, tmp_path):
        """Test that statistics are correctly aggregated from SQLite"""
        db_path = tmp_path / "telemetry.db"
        collector = EventCollector(db_path=db_path, use_sqlite=True)

        # Emit various events
        emit_task_event(collector, EventType.TASK_STARTED, task_id="task1")
        emit_task_event(collector, EventType.TASK_COMPLETED, task_id="task1", success=True)
        emit_task_event(collector, EventType.TASK_FAILED, task_id="task2", success=False)
        emit_batch_event(collector, EventType.BUILD_STARTED, batch_id="batch1", task_count=2)

        # Get statistics
        stats = collector.get_statistics()

        assert stats['total_events'] == 4
        assert stats['by_type']['task_started'] == 1
        assert stats['by_type']['task_completed'] == 1
        assert stats['by_type']['task_failed'] == 1
        assert stats['by_type']['build_started'] == 1

    def test_database_created_automatically(self, tmp_path):
        """Test that .buildrunner/telemetry.db is created automatically"""
        # Change working directory to temp path
        import os
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create event collector with default path
            collector = EventCollector(use_sqlite=True)

            # Emit an event
            emit_task_event(
                collector,
                EventType.TASK_STARTED,
                task_id="test",
            )

            # Verify database was created
            db_path = tmp_path / ".buildrunner" / "telemetry.db"
            assert db_path.exists()

            # Verify we can query it
            db = Database(db_path)
            events = db.query("SELECT * FROM events")
            assert len(events) >= 1

            db.close()
        finally:
            os.chdir(original_cwd)

    def test_model_selected_event_emitted(self, tmp_path):
        """Test that MODEL_SELECTED event is emitted when routing is enabled"""
        db_path = tmp_path / "telemetry.db"
        collector = EventCollector(db_path=db_path, use_sqlite=True)

        # Create orchestrator with telemetry and routing
        orchestrator = TaskOrchestrator(
            enable_telemetry=False,
            enable_routing=True,
            enable_parallel=False,
        )
        orchestrator.event_collector = collector

        # Execute a task
        tasks = [
            {'id': 'task1', 'name': 'Complex Task', 'description': 'Implement distributed system'},
        ]

        result = orchestrator.execute_batch(tasks)
        assert result['success'] is True

        # Query for MODEL_SELECTED events
        db = Database(db_path)
        model_events = db.query("SELECT * FROM events WHERE event_type = 'model_selected'")

        # Should have at least one model selection event
        assert len(model_events) >= 1

        # Verify metadata contains model info
        first_model_event = model_events[0]
        import json
        metadata = json.loads(first_model_event['metadata'])
        assert 'model' in metadata
        assert 'complexity' in metadata

        db.close()
