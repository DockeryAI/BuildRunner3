"""
Telemetry System for BuildRunner 3.1

This module provides comprehensive telemetry and monitoring:
- Event tracking and collection
- Metrics analysis and aggregation
- Threshold monitoring and alerts
- Performance tracking
- Health monitoring
"""

from .event_schemas import (
    Event,
    EventType,
    TaskEvent,
    BuildEvent,
    ErrorEvent,
    PerformanceEvent,
    SecurityEvent,
)
from .event_collector import EventCollector, EventFilter
from .metrics_analyzer import MetricsAnalyzer, MetricType, Metric, MetricsSummary
from .threshold_monitor import ThresholdMonitor, Threshold, Alert, AlertLevel
from .performance_tracker import PerformanceTracker, PerformanceMetrics, Timer

__all__ = [
    # Event schemas
    "Event",
    "EventType",
    "TaskEvent",
    "BuildEvent",
    "ErrorEvent",
    "PerformanceEvent",
    "SecurityEvent",
    # Event collection
    "EventCollector",
    "EventFilter",
    # Metrics
    "MetricsAnalyzer",
    "MetricType",
    "Metric",
    "MetricsSummary",
    # Monitoring
    "ThresholdMonitor",
    "Threshold",
    "Alert",
    "AlertLevel",
    # Performance
    "PerformanceTracker",
    "PerformanceMetrics",
    "Timer",
]
