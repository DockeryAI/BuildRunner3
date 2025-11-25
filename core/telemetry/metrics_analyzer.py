"""
Metrics Analyzer - Analyzes events and generates metrics

Generates metrics from telemetry events:
- Success/failure rates
- Performance metrics (latency, throughput)
- Cost metrics
- Error rates
- Security violations
- Model usage patterns
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional

from .event_collector import EventCollector, EventFilter
from .event_schemas import EventType, TaskEvent, BuildEvent, ErrorEvent, PerformanceEvent


class MetricType(str, Enum):
    """Types of metrics."""

    # Count metrics
    COUNT = "count"
    RATE = "rate"

    # Statistical metrics
    AVERAGE = "average"
    MEDIAN = "median"
    PERCENTILE_95 = "p95"
    PERCENTILE_99 = "p99"
    MIN = "min"
    MAX = "max"

    # Ratio metrics
    SUCCESS_RATE = "success_rate"
    FAILURE_RATE = "failure_rate"
    ERROR_RATE = "error_rate"


@dataclass
class Metric:
    """A calculated metric."""

    name: str
    metric_type: MetricType
    value: float
    unit: str = ""
    timestamp: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, any] = field(default_factory=dict)


@dataclass
class MetricsSummary:
    """Summary of calculated metrics."""

    period: str  # "hour", "day", "week", "all"
    start_time: datetime
    end_time: datetime

    # Task metrics
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0
    success_rate: float = 0.0

    # Performance metrics
    avg_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0

    # Cost metrics
    total_cost_usd: float = 0.0
    avg_cost_per_task: float = 0.0
    total_tokens: int = 0

    # Error metrics
    total_errors: int = 0
    error_rate: float = 0.0
    errors_by_type: Dict[str, int] = field(default_factory=dict)

    # Model metrics
    models_used: Dict[str, int] = field(default_factory=dict)
    most_used_model: str = ""

    # Security metrics
    security_violations: int = 0


class MetricsAnalyzer:
    """Analyzes events and generates metrics."""

    def __init__(self, event_collector: EventCollector):
        """
        Initialize metrics analyzer.

        Args:
            event_collector: EventCollector to analyze
        """
        self.collector = event_collector

    def calculate_summary(
        self,
        period: str = "day",
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
    ) -> MetricsSummary:
        """
        Calculate metrics summary for a time period.

        Args:
            period: Time period ("hour", "day", "week", "all")
            start_time: Custom start time
            end_time: Custom end time

        Returns:
            MetricsSummary with calculated metrics
        """
        now = datetime.now()

        # Determine time range
        if start_time and end_time:
            pass
        elif period == "hour":
            start_time = now - timedelta(hours=1)
            end_time = now
        elif period == "day":
            start_time = now - timedelta(days=1)
            end_time = now
        elif period == "week":
            start_time = now - timedelta(weeks=1)
            end_time = now
        else:  # "all"
            # Get all events
            all_events = self.collector.query()
            if all_events:
                start_time = min(e.timestamp for e in all_events)
                end_time = max(e.timestamp for e in all_events)
            else:
                start_time = now
                end_time = now

        # Query events
        filter = EventFilter(start_time=start_time, end_time=end_time)
        events = self.collector.query(filter=filter)

        # Initialize summary
        summary = MetricsSummary(
            period=period,
            start_time=start_time,
            end_time=end_time,
        )

        if not events:
            return summary

        # Analyze task events
        task_events = [e for e in events if isinstance(e, TaskEvent)]
        self._analyze_tasks(task_events, summary)

        # Analyze error events
        error_events = [e for e in events if isinstance(e, ErrorEvent)]
        self._analyze_errors(error_events, summary)

        # Analyze security events
        security_events = [
            e
            for e in events
            if e.event_type
            in [
                EventType.SECURITY_VIOLATION,
                EventType.SECRET_DETECTED,
                EventType.SQL_INJECTION_DETECTED,
            ]
        ]
        summary.security_violations = len(security_events)

        return summary

    def _analyze_tasks(self, events: List[TaskEvent], summary: MetricsSummary):
        """Analyze task events."""
        if not events:
            return

        summary.total_tasks = len(events)
        summary.successful_tasks = sum(1 for e in events if e.success)
        summary.failed_tasks = summary.total_tasks - summary.successful_tasks

        if summary.total_tasks > 0:
            summary.success_rate = (summary.successful_tasks / summary.total_tasks) * 100

        # Performance metrics
        durations = [e.duration_ms for e in events if e.duration_ms > 0]
        if durations:
            summary.avg_duration_ms = sum(durations) / len(durations)
            sorted_durations = sorted(durations)
            summary.p95_duration_ms = sorted_durations[int(len(sorted_durations) * 0.95)]
            summary.p99_duration_ms = sorted_durations[int(len(sorted_durations) * 0.99)]

        # Cost metrics
        summary.total_cost_usd = sum(e.cost_usd for e in events)
        summary.total_tokens = sum(e.tokens_used for e in events)
        if summary.total_tasks > 0:
            summary.avg_cost_per_task = summary.total_cost_usd / summary.total_tasks

        # Model usage
        for event in events:
            if event.model_used:
                summary.models_used[event.model_used] = (
                    summary.models_used.get(event.model_used, 0) + 1
                )

        if summary.models_used:
            summary.most_used_model = max(
                summary.models_used.keys(), key=lambda k: summary.models_used[k]
            )

    def _analyze_errors(self, events: List[ErrorEvent], summary: MetricsSummary):
        """Analyze error events."""
        summary.total_errors = len(events)

        if summary.total_tasks > 0:
            summary.error_rate = (summary.total_errors / summary.total_tasks) * 100

        # Count by error type
        for event in events:
            error_type = event.error_type or "unknown"
            summary.errors_by_type[error_type] = summary.errors_by_type.get(error_type, 0) + 1

    def calculate_metric(
        self,
        metric_name: str,
        metric_type: MetricType,
        event_type: Optional[EventType] = None,
        attribute: Optional[str] = None,
        period: str = "day",
    ) -> Metric:
        """
        Calculate a specific metric.

        Args:
            metric_name: Name of the metric
            metric_type: Type of metric to calculate
            event_type: Filter by event type
            attribute: Event attribute to analyze
            period: Time period

        Returns:
            Calculated Metric
        """
        # Get time range
        now = datetime.now()
        if period == "hour":
            start_time = now - timedelta(hours=1)
        elif period == "day":
            start_time = now - timedelta(days=1)
        elif period == "week":
            start_time = now - timedelta(weeks=1)
        else:
            start_time = None

        # Query events
        filter = EventFilter(
            event_types=[event_type] if event_type else None,
            start_time=start_time,
        )
        events = self.collector.query(filter=filter)

        # Calculate metric
        if metric_type == MetricType.COUNT:
            value = len(events)
            unit = "events"

        elif metric_type == MetricType.RATE:
            # Events per hour
            hours = (now - start_time).total_seconds() / 3600 if start_time else 1
            value = len(events) / hours
            unit = "events/hour"

        elif attribute and events:
            # Extract attribute values
            values = []
            for event in events:
                if hasattr(event, attribute):
                    val = getattr(event, attribute)
                    if isinstance(val, (int, float)):
                        values.append(val)

            if not values:
                value = 0.0
            elif metric_type == MetricType.AVERAGE:
                value = sum(values) / len(values)
            elif metric_type == MetricType.MIN:
                value = min(values)
            elif metric_type == MetricType.MAX:
                value = max(values)
            elif metric_type == MetricType.MEDIAN:
                sorted_values = sorted(values)
                mid = len(sorted_values) // 2
                value = sorted_values[mid]
            elif metric_type == MetricType.PERCENTILE_95:
                sorted_values = sorted(values)
                idx = int(len(sorted_values) * 0.95)
                value = sorted_values[idx]
            elif metric_type == MetricType.PERCENTILE_99:
                sorted_values = sorted(values)
                idx = int(len(sorted_values) * 0.99)
                value = sorted_values[idx]
            else:
                value = 0.0

            unit = ""
        else:
            value = 0.0
            unit = ""

        return Metric(
            name=metric_name,
            metric_type=metric_type,
            value=value,
            unit=unit,
        )

    def get_top_errors(self, limit: int = 10) -> List[Dict[str, any]]:
        """
        Get top errors by frequency.

        Args:
            limit: Number of errors to return

        Returns:
            List of error info dicts
        """
        error_events = self.collector.query(
            filter=EventFilter(event_types=[EventType.ERROR_OCCURRED, EventType.EXCEPTION_RAISED])
        )

        # Count by error type
        error_counts = {}
        error_examples = {}

        for event in error_events:
            if not isinstance(event, ErrorEvent):
                continue

            error_type = event.error_type or "unknown"
            error_counts[error_type] = error_counts.get(error_type, 0) + 1

            if error_type not in error_examples:
                error_examples[error_type] = {
                    "message": event.error_message,
                    "component": event.component,
                    "timestamp": event.timestamp,
                }

        # Sort by count
        sorted_errors = sorted(error_counts.items(), key=lambda x: x[1], reverse=True)[:limit]

        return [
            {
                "error_type": error_type,
                "count": count,
                "example": error_examples.get(error_type, {}),
            }
            for error_type, count in sorted_errors
        ]

    def get_performance_trends(
        self,
        days: int = 7,
        metric: str = "duration_ms",
    ) -> Dict[str, List[float]]:
        """
        Get performance trends over time.

        Args:
            days: Number of days to analyze
            metric: Metric to track (duration_ms, cost_usd, tokens_used)

        Returns:
            Dictionary with daily values
        """
        now = datetime.now()
        trends = {}

        for i in range(days):
            day = now - timedelta(days=i)
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day.replace(hour=23, minute=59, second=59)

            events = self.collector.query(
                filter=EventFilter(start_time=day_start, end_time=day_end)
            )

            task_events = [e for e in events if isinstance(e, TaskEvent)]

            values = []
            for event in task_events:
                if hasattr(event, metric):
                    val = getattr(event, metric)
                    if val > 0:
                        values.append(val)

            date_key = day.strftime("%Y-%m-%d")
            trends[date_key] = values

        return trends
