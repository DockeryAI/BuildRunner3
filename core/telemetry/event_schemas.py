"""
Event Schemas - Defines event types and data structures for telemetry

Event Types:
- TaskEvent: Task lifecycle events (started, completed, failed)
- BuildEvent: Build process events
- ErrorEvent: Error and exception events
- PerformanceEvent: Performance metrics
- SecurityEvent: Security-related events
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Dict, Optional


class EventType(str, Enum):
    """Types of telemetry events."""

    # Task events
    TASK_STARTED = "task_started"
    TASK_COMPLETED = "task_completed"
    TASK_FAILED = "task_failed"
    TASK_CANCELLED = "task_cancelled"

    # Build events
    BUILD_STARTED = "build_started"
    BUILD_COMPLETED = "build_completed"
    BUILD_FAILED = "build_failed"

    # Error events
    ERROR_OCCURRED = "error_occurred"
    EXCEPTION_RAISED = "exception_raised"

    # Performance events
    PERFORMANCE_MEASURED = "performance_measured"
    LATENCY_RECORDED = "latency_recorded"

    # Security events
    SECURITY_VIOLATION = "security_violation"
    SECRET_DETECTED = "secret_detected"
    SQL_INJECTION_DETECTED = "sql_injection_detected"

    # Model routing events
    MODEL_SELECTED = "model_selected"
    MODEL_FAILED = "model_failed"
    FALLBACK_TRIGGERED = "fallback_triggered"

    # System events
    SYSTEM_STARTED = "system_started"
    SYSTEM_STOPPED = "system_stopped"
    HEALTH_CHECK = "health_check"


@dataclass
class Event:
    """Base event class."""

    event_type: EventType
    timestamp: datetime = field(default_factory=datetime.now)
    event_id: str = ""
    session_id: str = ""
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert event to dictionary."""
        return {
            'event_type': self.event_type.value,
            'timestamp': self.timestamp.isoformat(),
            'event_id': self.event_id,
            'session_id': self.session_id,
            'metadata': self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Event':
        """Create event from dictionary."""
        return cls(
            event_type=EventType(data['event_type']),
            timestamp=datetime.fromisoformat(data['timestamp']),
            event_id=data.get('event_id', ''),
            session_id=data.get('session_id', ''),
            metadata=data.get('metadata', {}),
        )


@dataclass
class TaskEvent(Event):
    """Task lifecycle event."""

    task_id: str = ""
    task_type: str = ""
    task_description: str = ""

    # Task details
    complexity_level: str = ""
    model_used: str = ""
    file_count: int = 0
    line_count: int = 0

    # Performance
    duration_ms: float = 0.0
    tokens_used: int = 0
    cost_usd: float = 0.0

    # Status
    success: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            'task_id': self.task_id,
            'task_type': self.task_type,
            'task_description': self.task_description,
            'complexity_level': self.complexity_level,
            'model_used': self.model_used,
            'file_count': self.file_count,
            'line_count': self.line_count,
            'duration_ms': self.duration_ms,
            'tokens_used': self.tokens_used,
            'cost_usd': self.cost_usd,
            'success': self.success,
            'error_message': self.error_message,
        })
        return base


@dataclass
class BuildEvent(Event):
    """Build process event."""

    build_id: str = ""
    build_phase: str = ""

    # Build details
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0

    # Performance
    duration_ms: float = 0.0
    total_cost_usd: float = 0.0

    # Status
    success: bool = True
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            'build_id': self.build_id,
            'build_phase': self.build_phase,
            'total_tasks': self.total_tasks,
            'completed_tasks': self.completed_tasks,
            'failed_tasks': self.failed_tasks,
            'duration_ms': self.duration_ms,
            'total_cost_usd': self.total_cost_usd,
            'success': self.success,
            'error_message': self.error_message,
        })
        return base


@dataclass
class ErrorEvent(Event):
    """Error or exception event."""

    error_type: str = ""
    error_message: str = ""
    stack_trace: str = ""

    # Context
    task_id: str = ""
    component: str = ""
    severity: str = "error"  # debug, info, warning, error, critical

    # Recovery
    recoverable: bool = False
    recovery_action: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            'error_type': self.error_type,
            'error_message': self.error_message,
            'stack_trace': self.stack_trace,
            'task_id': self.task_id,
            'component': self.component,
            'severity': self.severity,
            'recoverable': self.recoverable,
            'recovery_action': self.recovery_action,
        })
        return base


@dataclass
class PerformanceEvent(Event):
    """Performance measurement event."""

    metric_name: str = ""
    metric_value: float = 0.0
    metric_unit: str = ""

    # Context
    component: str = ""
    operation: str = ""

    # Additional metrics
    cpu_percent: float = 0.0
    memory_mb: float = 0.0
    disk_io_mb: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'metric_unit': self.metric_unit,
            'component': self.component,
            'operation': self.operation,
            'cpu_percent': self.cpu_percent,
            'memory_mb': self.memory_mb,
            'disk_io_mb': self.disk_io_mb,
        })
        return base


@dataclass
class SecurityEvent(Event):
    """Security-related event."""

    security_type: str = ""  # secret_detected, sql_injection, etc.
    severity: str = "high"

    # Details
    file_path: str = ""
    line_number: int = 0
    violation_type: str = ""

    # Action
    blocked: bool = True
    remediation: str = ""

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        base = super().to_dict()
        base.update({
            'security_type': self.security_type,
            'severity': self.severity,
            'file_path': self.file_path,
            'line_number': self.line_number,
            'violation_type': self.violation_type,
            'blocked': self.blocked,
            'remediation': self.remediation,
        })
        return base
