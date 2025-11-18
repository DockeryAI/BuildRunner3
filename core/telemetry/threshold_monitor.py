"""
Threshold Monitor - Monitors metrics against thresholds and raises alerts

Monitors:
- Success rate thresholds
- Error rate thresholds
- Performance thresholds (latency, duration)
- Cost thresholds
- Security violation limits
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Callable, Dict, List, Optional

from .metrics_analyzer import MetricsAnalyzer, MetricsSummary


class AlertLevel(str, Enum):
    """Alert severity levels."""

    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


@dataclass
class Threshold:
    """Metric threshold configuration."""

    name: str
    metric_name: str
    operator: str  # "gt", "lt", "gte", "lte", "eq"
    value: float
    level: AlertLevel = AlertLevel.WARNING
    description: str = ""
    enabled: bool = True


@dataclass
class Alert:
    """Alert raised when threshold is violated."""

    timestamp: datetime
    level: AlertLevel
    threshold_name: str
    message: str
    metric_name: str
    metric_value: float
    threshold_value: float
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary."""
        return {
            'timestamp': self.timestamp.isoformat(),
            'level': self.level.value,
            'threshold_name': self.threshold_name,
            'message': self.message,
            'metric_name': self.metric_name,
            'metric_value': self.metric_value,
            'threshold_value': self.threshold_value,
            'metadata': self.metadata,
        }


class ThresholdMonitor:
    """Monitors metrics against thresholds and raises alerts."""

    # Default thresholds
    DEFAULT_THRESHOLDS = [
        Threshold(
            name="low_success_rate",
            metric_name="success_rate",
            operator="lt",
            value=80.0,
            level=AlertLevel.WARNING,
            description="Success rate below 80%",
        ),
        Threshold(
            name="critical_success_rate",
            metric_name="success_rate",
            operator="lt",
            value=50.0,
            level=AlertLevel.CRITICAL,
            description="Success rate below 50%",
        ),
        Threshold(
            name="high_error_rate",
            metric_name="error_rate",
            operator="gt",
            value=10.0,
            level=AlertLevel.WARNING,
            description="Error rate above 10%",
        ),
        Threshold(
            name="critical_error_rate",
            metric_name="error_rate",
            operator="gt",
            value=25.0,
            level=AlertLevel.CRITICAL,
            description="Error rate above 25%",
        ),
        Threshold(
            name="high_latency",
            metric_name="p95_duration_ms",
            operator="gt",
            value=5000.0,  # 5 seconds
            level=AlertLevel.WARNING,
            description="P95 latency above 5 seconds",
        ),
        Threshold(
            name="daily_cost_limit",
            metric_name="total_cost_usd",
            operator="gt",
            value=10.0,
            level=AlertLevel.WARNING,
            description="Daily cost exceeds $10",
        ),
        Threshold(
            name="security_violations",
            metric_name="security_violations",
            operator="gt",
            value=0,
            level=AlertLevel.CRITICAL,
            description="Security violations detected",
        ),
    ]

    def __init__(
        self,
        metrics_analyzer: MetricsAnalyzer,
        thresholds: Optional[List[Threshold]] = None,
    ):
        """
        Initialize threshold monitor.

        Args:
            metrics_analyzer: MetricsAnalyzer to monitor
            thresholds: Custom thresholds (uses defaults if None)
        """
        self.analyzer = metrics_analyzer
        self.thresholds = thresholds or self.DEFAULT_THRESHOLDS.copy()

        self.alerts: List[Alert] = []
        self.alert_handlers: List[Callable[[Alert], None]] = []

    def check_thresholds(self, summary: MetricsSummary) -> List[Alert]:
        """
        Check all thresholds against metrics summary.

        Args:
            summary: MetricsSummary to check

        Returns:
            List of alerts raised
        """
        raised_alerts = []

        for threshold in self.thresholds:
            if not threshold.enabled:
                continue

            # Get metric value from summary
            metric_value = self._get_metric_value(summary, threshold.metric_name)

            if metric_value is None:
                continue

            # Check threshold
            violated = self._check_threshold(
                metric_value,
                threshold.operator,
                threshold.value
            )

            if violated:
                alert = Alert(
                    timestamp=datetime.now(),
                    level=threshold.level,
                    threshold_name=threshold.name,
                    message=threshold.description or f"{threshold.metric_name} threshold violated",
                    metric_name=threshold.metric_name,
                    metric_value=metric_value,
                    threshold_value=threshold.value,
                )

                raised_alerts.append(alert)
                self.alerts.append(alert)

                # Notify handlers
                for handler in self.alert_handlers:
                    try:
                        handler(alert)
                    except Exception as e:
                        print(f"Warning: Alert handler failed: {e}")

        return raised_alerts

    def _get_metric_value(
        self,
        summary: MetricsSummary,
        metric_name: str
    ) -> Optional[float]:
        """Get metric value from summary."""
        if hasattr(summary, metric_name):
            value = getattr(summary, metric_name)
            if isinstance(value, (int, float)):
                return float(value)
        return None

    def _check_threshold(
        self,
        metric_value: float,
        operator: str,
        threshold_value: float
    ) -> bool:
        """Check if metric violates threshold."""
        if operator == "gt":
            return metric_value > threshold_value
        elif operator == "gte":
            return metric_value >= threshold_value
        elif operator == "lt":
            return metric_value < threshold_value
        elif operator == "lte":
            return metric_value <= threshold_value
        elif operator == "eq":
            return metric_value == threshold_value
        else:
            return False

    def add_threshold(self, threshold: Threshold):
        """
        Add a custom threshold.

        Args:
            threshold: Threshold to add
        """
        self.thresholds.append(threshold)

    def remove_threshold(self, threshold_name: str):
        """
        Remove a threshold by name.

        Args:
            threshold_name: Name of threshold to remove
        """
        self.thresholds = [
            t for t in self.thresholds
            if t.name != threshold_name
        ]

    def enable_threshold(self, threshold_name: str):
        """Enable a threshold."""
        for threshold in self.thresholds:
            if threshold.name == threshold_name:
                threshold.enabled = True

    def disable_threshold(self, threshold_name: str):
        """Disable a threshold."""
        for threshold in self.thresholds:
            if threshold.name == threshold_name:
                threshold.enabled = False

    def add_alert_handler(self, handler: Callable[[Alert], None]):
        """
        Add alert handler.

        Args:
            handler: Function to call when alert is raised
        """
        self.alert_handlers.append(handler)

    def remove_alert_handler(self, handler: Callable[[Alert], None]):
        """Remove alert handler."""
        if handler in self.alert_handlers:
            self.alert_handlers.remove(handler)

    def get_recent_alerts(
        self,
        count: int = 10,
        level: Optional[AlertLevel] = None,
    ) -> List[Alert]:
        """
        Get recent alerts.

        Args:
            count: Number of alerts to return
            level: Filter by alert level

        Returns:
            List of recent alerts
        """
        alerts = self.alerts

        if level:
            alerts = [a for a in alerts if a.level == level]

        # Sort by timestamp (most recent first)
        sorted_alerts = sorted(alerts, key=lambda a: a.timestamp, reverse=True)

        return sorted_alerts[:count]

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics about alerts.

        Returns:
            Statistics dictionary
        """
        if not self.alerts:
            return {
                'total_alerts': 0,
                'alerts_by_level': {},
                'alerts_by_threshold': {},
            }

        # Count by level
        by_level = {}
        for level in AlertLevel:
            count = sum(1 for a in self.alerts if a.level == level)
            if count > 0:
                by_level[level.value] = count

        # Count by threshold
        by_threshold = {}
        for alert in self.alerts:
            by_threshold[alert.threshold_name] = \
                by_threshold.get(alert.threshold_name, 0) + 1

        return {
            'total_alerts': len(self.alerts),
            'alerts_by_level': by_level,
            'alerts_by_threshold': by_threshold,
            'active_thresholds': len([t for t in self.thresholds if t.enabled]),
            'total_thresholds': len(self.thresholds),
        }

    def clear_alerts(self):
        """Clear all stored alerts."""
        self.alerts.clear()
