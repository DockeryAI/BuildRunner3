"""
Telemetry Integration Module

Provides helper functions for integrating telemetry into the orchestrator.
Handles event emission, context creation, and telemetry lifecycle.
"""

from typing import Dict, Any, Optional, List
from datetime import datetime
import time

from core.telemetry import (
    EventCollector,
    EventType,
    TaskEvent,
    BuildEvent,
    ErrorEvent,
    PerformanceEvent,
)


def integrate_telemetry(orchestrator) -> EventCollector:
    """
    Integrate telemetry into an orchestrator instance.

    Args:
        orchestrator: The TaskOrchestrator instance

    Returns:
        EventCollector instance attached to the orchestrator
    """
    event_collector = EventCollector()
    orchestrator.event_collector = event_collector
    return event_collector


def emit_task_event(
    event_collector: EventCollector,
    event_type: EventType,
    task_id: str,
    task_type: Optional[str] = None,
    task_description: Optional[str] = None,
    success: bool = True,
    error_message: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
    duration_ms: Optional[float] = None,
) -> TaskEvent:
    """
    Emit a task-related event.

    Args:
        event_collector: The EventCollector instance
        event_type: Type of event (TASK_STARTED, TASK_COMPLETED, TASK_FAILED)
        task_id: Unique task identifier
        task_type: Optional task type
        task_description: Optional task description
        success: Whether task succeeded
        error_message: Error message if task failed
        metadata: Additional metadata
        duration_ms: Task duration in milliseconds

    Returns:
        The created TaskEvent
    """
    event = TaskEvent(
        event_type=event_type,
        timestamp=datetime.now(),
        task_id=task_id,
        task_type=task_type or "task",
        task_description=task_description or "",
        success=success,
        error_message=error_message or "",
        metadata=metadata or {},
        duration_ms=duration_ms or 0.0,
    )

    event_collector.collect(event)
    return event


def emit_batch_event(
    event_collector: EventCollector,
    event_type: EventType,
    batch_id: str,
    task_count: int,
    success: bool = True,
    metadata: Optional[Dict[str, Any]] = None,
) -> BuildEvent:
    """
    Emit a batch-related event.

    Args:
        event_collector: The EventCollector instance
        event_type: Type of event (BUILD_STARTED, BUILD_COMPLETED, BUILD_FAILED)
        batch_id: Unique batch identifier
        task_count: Number of tasks in batch
        success: Whether batch succeeded
        metadata: Additional metadata

    Returns:
        The created BuildEvent
    """
    event = BuildEvent(
        event_type=event_type,
        timestamp=datetime.now(),
        build_id=batch_id,
        build_phase=metadata.get("phase", "execution") if metadata else "execution",
        total_tasks=task_count,
        success=success,
        metadata=metadata or {},
    )

    event_collector.collect(event)
    return event


def emit_error_event(
    event_collector: EventCollector,
    error_type: str,
    error_message: str,
    component: str,
    stack_trace: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> ErrorEvent:
    """
    Emit an error event.

    Args:
        event_collector: The EventCollector instance
        error_type: Type of error
        error_message: Error message
        component: Component where error occurred
        stack_trace: Optional stack trace
        metadata: Additional metadata

    Returns:
        The created ErrorEvent
    """
    event = ErrorEvent(
        event_type=EventType.ERROR_OCCURRED,
        timestamp=datetime.now(),
        error_type=error_type,
        error_message=error_message,
        component=component,
        stack_trace=stack_trace,
        metadata=metadata or {},
    )

    event_collector.collect(event)
    return event


def emit_performance_event(
    event_collector: EventCollector,
    operation_name: str,
    duration_ms: float,
    metadata: Optional[Dict[str, Any]] = None,
) -> PerformanceEvent:
    """
    Emit a performance event.

    Args:
        event_collector: The EventCollector instance
        operation_name: Name of the operation
        duration_ms: Duration in milliseconds
        metadata: Additional metadata

    Returns:
        The created PerformanceEvent
    """
    event = PerformanceEvent(
        event_type=EventType.PERFORMANCE_MEASURED,
        timestamp=datetime.now(),
        metric_name=operation_name,
        metric_value=duration_ms,
        metric_unit="ms",
        operation=operation_name,
        metadata=metadata or {},
    )

    event_collector.collect(event)
    return event


def create_telemetry_context(
    event_collector: EventCollector,
    operation_name: str,
) -> "TelemetryContext":
    """
    Create a telemetry context for automatic timing and event emission.

    Usage:
        with create_telemetry_context(collector, "batch_execution") as ctx:
            # Do work
            ctx.add_metadata("task_count", 5)

    Args:
        event_collector: The EventCollector instance
        operation_name: Name of the operation

    Returns:
        TelemetryContext instance
    """
    return TelemetryContext(event_collector, operation_name)


class TelemetryContext:
    """Context manager for automatic telemetry timing and event emission."""

    def __init__(self, event_collector: EventCollector, operation_name: str):
        self.event_collector = event_collector
        self.operation_name = operation_name
        self.start_time = None
        self.metadata = {}
        self.success = True
        self.error = None

    def __enter__(self):
        """Start timing on context entry."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Emit performance event on context exit."""
        duration_ms = (time.time() - self.start_time) * 1000

        if exc_type is not None:
            self.success = False
            self.error = str(exc_val)
            self.metadata["error_type"] = exc_type.__name__

        emit_performance_event(
            self.event_collector,
            self.operation_name,
            duration_ms,
            metadata={
                **self.metadata,
                "success": self.success,
                "error": self.error,
            },
        )

        # Don't suppress exceptions
        return False

    def add_metadata(self, key: str, value: Any):
        """Add metadata to be included in the performance event."""
        self.metadata[key] = value

    def mark_failed(self, error_message: str):
        """Mark the operation as failed."""
        self.success = False
        self.error = error_message


def get_event_summary(event_collector: EventCollector) -> Dict[str, Any]:
    """
    Get a summary of collected events.

    Args:
        event_collector: The EventCollector instance

    Returns:
        Dictionary with event counts and statistics
    """
    # Get statistics from the event collector
    stats = event_collector.get_statistics()

    # Also get recent events for detailed analysis
    recent_events = event_collector.get_recent(count=1000)

    summary = {
        "total_events": stats.get("total_events", 0),
        "by_type": stats.get("by_type", {}),
        "errors": 0,
        "tasks_completed": 0,
        "tasks_failed": 0,
    }

    # Count task-specific events from recent events
    for event in recent_events:
        if isinstance(event, TaskEvent):
            if event.event_type == EventType.TASK_COMPLETED:
                summary["tasks_completed"] += 1
            elif event.event_type == EventType.TASK_FAILED:
                summary["tasks_failed"] += 1

        if isinstance(event, ErrorEvent):
            summary["errors"] += 1

    return summary
