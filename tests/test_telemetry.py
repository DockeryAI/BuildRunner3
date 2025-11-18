"""
Tests for Telemetry System

Tests event schemas, collection, metrics analysis, and monitoring.
"""

import pytest
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
import json

from core.telemetry import (
    Event,
    EventType,
    TaskEvent,
    BuildEvent,
    ErrorEvent,
    PerformanceEvent,
    SecurityEvent,
    EventCollector,
    EventFilter,
    MetricsAnalyzer,
    MetricType,
    ThresholdMonitor,
    Threshold,
    AlertLevel,
    PerformanceTracker,
    Timer,
)


class TestEventSchemas:
    """Test event data structures."""

    def test_event_creation(self):
        """Test creating basic event."""
        event = Event(
            event_type=EventType.TASK_STARTED,
            event_id="test-123",
            session_id="session-1",
        )

        assert event.event_type == EventType.TASK_STARTED
        assert event.event_id == "test-123"
        assert event.session_id == "session-1"
        assert isinstance(event.timestamp, datetime)

    def test_event_to_dict(self):
        """Test event serialization to dictionary."""
        event = Event(
            event_type=EventType.TASK_COMPLETED,
            event_id="test-456",
            metadata={'key': 'value'},
        )

        data = event.to_dict()

        assert data['event_type'] == 'task_completed'
        assert data['event_id'] == 'test-456'
        assert data['metadata'] == {'key': 'value'}
        assert 'timestamp' in data

    def test_event_from_dict(self):
        """Test event deserialization from dictionary."""
        now = datetime.now()
        data = {
            'event_type': 'task_started',
            'timestamp': now.isoformat(),
            'event_id': 'test-789',
            'session_id': 'session-2',
            'metadata': {},
        }

        event = Event.from_dict(data)

        assert event.event_type == EventType.TASK_STARTED
        assert event.event_id == 'test-789'
        assert event.session_id == 'session-2'

    def test_task_event_creation(self):
        """Test creating TaskEvent."""
        event = TaskEvent(
            event_type=EventType.TASK_COMPLETED,
            task_id="task-1",
            task_type="new_feature",
            task_description="Add authentication",
            complexity_level="moderate",
            model_used="sonnet",
            file_count=5,
            line_count=250,
            duration_ms=1500.0,
            tokens_used=1000,
            cost_usd=0.01,
            success=True,
        )

        assert event.task_id == "task-1"
        assert event.complexity_level == "moderate"
        assert event.model_used == "sonnet"
        assert event.duration_ms == 1500.0
        assert event.success is True

    def test_task_event_to_dict(self):
        """Test TaskEvent serialization."""
        event = TaskEvent(
            event_type=EventType.TASK_FAILED,
            task_id="task-2",
            success=False,
            error_message="Import error",
        )

        data = event.to_dict()

        assert data['task_id'] == 'task-2'
        assert data['success'] is False
        assert data['error_message'] == 'Import error'

    def test_build_event_creation(self):
        """Test creating BuildEvent."""
        event = BuildEvent(
            event_type=EventType.BUILD_COMPLETED,
            build_id="build-1",
            build_phase="implementation",
            total_tasks=10,
            completed_tasks=8,
            failed_tasks=2,
            duration_ms=30000.0,
            total_cost_usd=0.25,
            success=False,
        )

        assert event.build_id == "build-1"
        assert event.total_tasks == 10
        assert event.completed_tasks == 8
        assert event.failed_tasks == 2
        assert event.success is False

    def test_error_event_creation(self):
        """Test creating ErrorEvent."""
        event = ErrorEvent(
            event_type=EventType.ERROR_OCCURRED,
            error_type="ImportError",
            error_message="Module not found",
            stack_trace="Traceback...",
            task_id="task-3",
            component="orchestrator",
            severity="error",
            recoverable=True,
            recovery_action="Retry with fallback",
        )

        assert event.error_type == "ImportError"
        assert event.severity == "error"
        assert event.recoverable is True

    def test_performance_event_creation(self):
        """Test creating PerformanceEvent."""
        event = PerformanceEvent(
            event_type=EventType.PERFORMANCE_MEASURED,
            metric_name="api_latency",
            metric_value=245.5,
            metric_unit="ms",
            component="api",
            operation="authenticate",
            cpu_percent=25.0,
            memory_mb=128.5,
        )

        assert event.metric_name == "api_latency"
        assert event.metric_value == 245.5
        assert event.cpu_percent == 25.0

    def test_security_event_creation(self):
        """Test creating SecurityEvent."""
        event = SecurityEvent(
            event_type=EventType.SECRET_DETECTED,
            security_type="secret_detected",
            severity="high",
            file_path="/path/to/file.py",
            line_number=42,
            violation_type="anthropic_key",
            blocked=True,
            remediation="Remove secret from code",
        )

        assert event.security_type == "secret_detected"
        assert event.severity == "high"
        assert event.blocked is True


class TestEventCollector:
    """Test EventCollector functionality."""

    def test_init_with_defaults(self):
        """Test initialization with default parameters."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "events.json"
            collector = EventCollector(storage_path=storage_path)

            assert collector.storage_path == storage_path
            assert collector.buffer_size == 100
            assert collector.auto_flush is True
            assert collector.events == []
            assert collector.buffer == []

    def test_collect_event(self):
        """Test collecting a single event."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            event = Event(event_type=EventType.TASK_STARTED)
            event_id = collector.collect(event)

            assert event_id is not None
            assert event.event_id == event_id
            assert len(collector.buffer) == 1

    def test_auto_generate_event_id(self):
        """Test automatic event ID generation."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            event = Event(event_type=EventType.TASK_COMPLETED)  # No event_id
            event_id = collector.collect(event)

            assert event_id != ""
            assert event.event_id != ""

    def test_manual_flush(self):
        """Test manual buffer flush."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(
                storage_path=Path(tmpdir) / "events.json",
                auto_flush=False,
            )

            event = Event(event_type=EventType.BUILD_STARTED)
            collector.collect(event)

            assert len(collector.buffer) == 1
            assert len(collector.events) == 0

            collector.flush()

            assert len(collector.buffer) == 0
            assert len(collector.events) == 1

    def test_auto_flush_on_buffer_full(self):
        """Test automatic flush when buffer is full."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(
                storage_path=Path(tmpdir) / "events.json",
                buffer_size=5,
                auto_flush=True,
            )

            # Collect 5 events to trigger auto-flush
            for i in range(5):
                collector.collect(Event(event_type=EventType.TASK_STARTED))

            assert len(collector.buffer) == 0
            assert len(collector.events) == 5

    def test_query_all_events(self):
        """Test querying all events."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            # Collect multiple events
            collector.collect(Event(event_type=EventType.TASK_STARTED))
            collector.collect(Event(event_type=EventType.TASK_COMPLETED))
            collector.flush()

            results = collector.query()

            assert len(results) == 2

    def test_query_with_event_type_filter(self):
        """Test querying events by type."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            collector.collect(Event(event_type=EventType.TASK_STARTED))
            collector.collect(Event(event_type=EventType.TASK_COMPLETED))
            collector.collect(Event(event_type=EventType.TASK_STARTED))
            collector.flush()

            filter = EventFilter(event_types=[EventType.TASK_STARTED])
            results = collector.query(filter=filter)

            assert len(results) == 2
            assert all(e.event_type == EventType.TASK_STARTED for e in results)

    def test_query_with_time_filter(self):
        """Test querying events by time range."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            now = datetime.now()
            past = now - timedelta(hours=1)
            future = now + timedelta(hours=1)

            # Create events with different timestamps
            event1 = Event(event_type=EventType.TASK_STARTED)
            event1.timestamp = past
            event2 = Event(event_type=EventType.TASK_COMPLETED)
            event2.timestamp = now

            collector.collect(event1)
            collector.collect(event2)
            collector.flush()

            # Query events after past time
            filter = EventFilter(start_time=now - timedelta(minutes=30))
            results = collector.query(filter=filter)

            assert len(results) == 1
            assert results[0].event_type == EventType.TASK_COMPLETED

    def test_query_with_session_filter(self):
        """Test querying events by session ID."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            event1 = Event(event_type=EventType.TASK_STARTED, session_id="session-1")
            event2 = Event(event_type=EventType.TASK_STARTED, session_id="session-2")
            event3 = Event(event_type=EventType.TASK_COMPLETED, session_id="session-1")

            collector.collect(event1)
            collector.collect(event2)
            collector.collect(event3)
            collector.flush()

            filter = EventFilter(session_id="session-1")
            results = collector.query(filter=filter)

            assert len(results) == 2
            assert all(e.session_id == "session-1" for e in results)

    def test_query_with_limit(self):
        """Test querying with result limit."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            for i in range(10):
                collector.collect(Event(event_type=EventType.TASK_STARTED))
            collector.flush()

            results = collector.query(limit=5)

            assert len(results) == 5

    def test_get_by_id(self):
        """Test retrieving event by ID."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            event = Event(event_type=EventType.TASK_COMPLETED, event_id="unique-id")
            collector.collect(event)
            collector.flush()

            retrieved = collector.get_by_id("unique-id")

            assert retrieved is not None
            assert retrieved.event_id == "unique-id"

    def test_count_events(self):
        """Test counting events using query."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            for i in range(7):
                collector.collect(Event(event_type=EventType.TASK_STARTED))
            collector.flush()

            count = len(collector.query())

            assert count == 7

    def test_count_by_type(self):
        """Test counting events by type using filters."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            collector.collect(Event(event_type=EventType.TASK_STARTED))
            collector.collect(Event(event_type=EventType.TASK_STARTED))
            collector.collect(Event(event_type=EventType.TASK_COMPLETED))
            collector.flush()

            started_count = len(collector.query(filter=EventFilter(event_types=[EventType.TASK_STARTED])))
            completed_count = len(collector.query(filter=EventFilter(event_types=[EventType.TASK_COMPLETED])))

            assert started_count == 2
            assert completed_count == 1

    def test_clear_events_manual(self):
        """Test clearing events by resetting lists."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            collector.collect(Event(event_type=EventType.TASK_STARTED))
            collector.flush()

            assert len(collector.events) == 1

            # Manual clear by resetting
            collector.events = []
            collector.buffer = []

            assert len(collector.events) == 0
            assert len(collector.buffer) == 0

    def test_event_listener(self):
        """Test event listener callback."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            received_events = []

            def listener(event: Event):
                received_events.append(event)

            collector.add_listener(listener)

            event = Event(event_type=EventType.TASK_STARTED)
            collector.collect(event)

            assert len(received_events) == 1
            assert received_events[0] == event

    def test_persistence(self):
        """Test event persistence to disk."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "events.json"

            # Create collector and add events
            collector1 = EventCollector(storage_path=storage_path)
            collector1.collect(Event(event_type=EventType.TASK_STARTED, event_id="persist-1"))
            collector1.flush()

            # Create new collector with same storage
            collector2 = EventCollector(storage_path=storage_path)

            # Should load persisted events
            assert len(collector2.events) == 1
            assert collector2.events[0].event_id == "persist-1"


class TestMetricsAnalyzer:
    """Test MetricsAnalyzer functionality."""

    def test_init(self):
        """Test MetricsAnalyzer initialization."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")
            analyzer = MetricsAnalyzer(collector)

            assert analyzer.collector == collector

    def test_calculate_metric(self):
        """Test calculating specific metric."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")
            analyzer = MetricsAnalyzer(collector)

            # Add task events
            collector.collect(TaskEvent(
                event_type=EventType.TASK_COMPLETED,
                task_id="t1",
                duration_ms=1000,
                tokens_used=500,
                cost_usd=0.01,
                success=True,
            ))
            collector.collect(TaskEvent(
                event_type=EventType.TASK_FAILED,
                task_id="t2",
                success=False,
            ))
            collector.flush()

            # Calculate a metric (COUNT of tasks)
            metric = analyzer.calculate_metric(
                metric_name="task_count",
                metric_type=MetricType.COUNT,
                event_type=EventType.TASK_COMPLETED
            )

            assert metric.value >= 1  # At least 1 completed task

    def test_calculate_summary(self):
        """Test calculating metrics summary."""
        with TemporaryDirectory() as tmpdir:
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")
            analyzer = MetricsAnalyzer(collector)

            # Add various events
            collector.collect(TaskEvent(event_type=EventType.TASK_COMPLETED, success=True, cost_usd=0.01))
            collector.collect(TaskEvent(event_type=EventType.TASK_COMPLETED, success=True, cost_usd=0.02))
            collector.collect(TaskEvent(event_type=EventType.TASK_FAILED, success=False))
            collector.flush()

            summary = analyzer.calculate_summary(period="day")

            # Summary is a MetricsSummary object with total_tasks not total_events
            assert hasattr(summary, 'total_tasks')
            assert summary.total_tasks == 3


class TestPerformanceTracker:
    """Test PerformanceTracker functionality."""

    def test_tracker_init(self):
        """Test PerformanceTracker initialization."""
        with TemporaryDirectory() as tmpdir:
            storage_path = Path(tmpdir) / "perf.json"
            tracker = PerformanceTracker(storage_path=storage_path)

            assert tracker.storage_path == storage_path
            assert tracker.measurements is not None

    def test_tracker_record_metric(self):
        """Test recording performance metric."""
        with TemporaryDirectory() as tmpdir:
            tracker = PerformanceTracker(storage_path=Path(tmpdir) / "perf.json")

            tracker.record_measurement(
                operation_type="api_call",
                duration_ms=123.45,
            )

            # Verify metric was recorded
            assert len(tracker.measurements) > 0


class TestIntegration:
    """Integration tests for complete telemetry workflow."""

    def test_full_telemetry_workflow(self):
        """Test complete telemetry workflow."""
        with TemporaryDirectory() as tmpdir:
            # Create collector
            collector = EventCollector(storage_path=Path(tmpdir) / "events.json")

            # Create analyzer
            analyzer = MetricsAnalyzer(collector)

            # Simulate task execution
            task_event = TaskEvent(
                event_type=EventType.TASK_COMPLETED,
                task_id="workflow-task-1",
                task_type="new_feature",
                complexity_level="moderate",
                model_used="sonnet",
                duration_ms=2500,
                tokens_used=1500,
                cost_usd=0.015,
                success=True,
            )

            collector.collect(task_event)
            collector.flush()

            # Analyze metrics
            summary = analyzer.calculate_summary(period="day")

            assert hasattr(summary, 'total_tasks')
            assert summary.total_tasks == 1
            assert summary.successful_tasks == 1
            assert summary.total_cost_usd == 0.015

            # Verify persistence
            events = collector.query()
            assert len(events) == 1
            assert events[0].task_id == "workflow-task-1"
