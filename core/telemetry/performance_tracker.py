"""
Performance Tracker - Tracks system performance metrics

Tracks:
- Operation durations
- Resource usage (CPU, memory)
- Throughput (tasks per second)
- API latency
- System health
"""

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
import time
import json


@dataclass
class PerformanceMetrics:
    """Performance metrics for a time period."""

    start_time: datetime
    end_time: datetime

    # Timing metrics
    total_operations: int = 0
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0
    p50_duration_ms: float = 0.0
    p95_duration_ms: float = 0.0
    p99_duration_ms: float = 0.0

    # Throughput
    operations_per_second: float = 0.0

    # Resource usage
    avg_cpu_percent: float = 0.0
    avg_memory_mb: float = 0.0
    peak_memory_mb: float = 0.0
    cpu_percent: float = 0.0  # Alias for avg_cpu_percent
    memory_mb: float = 0.0     # Alias for avg_memory_mb

    # Active state
    active_operations: int = 0
    avg_operation_time_ms: float = 0.0  # Alias for avg_duration_ms

    # By operation type
    by_operation: Dict[str, Dict[str, float]] = field(default_factory=dict)


class PerformanceTracker:
    """Tracks system performance metrics."""

    def __init__(self, storage_path: Optional[Path] = None):
        """
        Initialize performance tracker.

        Args:
            storage_path: Path to store performance data
        """
        self.storage_path = storage_path or Path.cwd() / ".buildrunner" / "performance.json"

        self.measurements: List[Dict[str, any]] = []
        self.active_timers: Dict[str, float] = {}

        self._load()

    def start_timer(self, operation_id: str):
        """
        Start timing an operation.

        Args:
            operation_id: Unique identifier for the operation
        """
        self.active_timers[operation_id] = time.time()

    def stop_timer(
        self,
        operation_id: str,
        operation_type: str = "unknown",
        metadata: Optional[Dict[str, any]] = None,
    ) -> float:
        """
        Stop timing an operation and record measurement.

        Args:
            operation_id: Operation identifier
            operation_type: Type of operation
            metadata: Additional metadata

        Returns:
            Duration in milliseconds
        """
        if operation_id not in self.active_timers:
            return 0.0

        start_time = self.active_timers.pop(operation_id)
        duration_ms = (time.time() - start_time) * 1000

        # Record measurement
        self.record_measurement(
            operation_type=operation_type,
            duration_ms=duration_ms,
            metadata=metadata or {},
        )

        return duration_ms

    def record_measurement(
        self,
        operation_type: str,
        duration_ms: float,
        cpu_percent: float = 0.0,
        memory_mb: float = 0.0,
        metadata: Optional[Dict[str, any]] = None,
    ):
        """
        Record a performance measurement.

        Args:
            operation_type: Type of operation
            duration_ms: Duration in milliseconds
            cpu_percent: CPU usage percentage
            memory_mb: Memory usage in MB
            metadata: Additional metadata
        """
        measurement = {
            'timestamp': datetime.now().isoformat(),
            'operation_type': operation_type,
            'duration_ms': duration_ms,
            'cpu_percent': cpu_percent,
            'memory_mb': memory_mb,
            'metadata': metadata or {},
        }

        self.measurements.append(measurement)

        # Auto-save periodically
        if len(self.measurements) % 100 == 0:
            self._save()

    def get_metrics(
        self,
        operation_type: Optional[str] = None,
        hours: int = 24,
    ) -> PerformanceMetrics:
        """
        Get performance metrics.

        Args:
            operation_type: Filter by operation type
            hours: Number of hours to analyze

        Returns:
            PerformanceMetrics
        """
        now = datetime.now()
        start_time = now - timedelta(hours=hours)

        # Filter measurements
        filtered = []
        for m in self.measurements:
            timestamp = datetime.fromisoformat(m['timestamp'])
            if timestamp < start_time:
                continue

            if operation_type and m['operation_type'] != operation_type:
                continue

            filtered.append(m)

        if not filtered:
            return PerformanceMetrics(start_time=start_time, end_time=now)

        # Calculate metrics
        durations = [m['duration_ms'] for m in filtered]
        cpu_values = [m['cpu_percent'] for m in filtered if m['cpu_percent'] > 0]
        memory_values = [m['memory_mb'] for m in filtered if m['memory_mb'] > 0]

        sorted_durations = sorted(durations)
        total_operations = len(filtered)

        # Timing metrics
        avg_duration = sum(durations) / len(durations) if durations else 0
        min_duration = min(durations) if durations else 0
        max_duration = max(durations) if durations else 0

        p50_idx = int(len(sorted_durations) * 0.50)
        p95_idx = int(len(sorted_durations) * 0.95)
        p99_idx = int(len(sorted_durations) * 0.99)

        p50 = sorted_durations[p50_idx] if sorted_durations else 0
        p95 = sorted_durations[p95_idx] if sorted_durations else 0
        p99 = sorted_durations[p99_idx] if sorted_durations else 0

        # Throughput
        time_span_seconds = (now - start_time).total_seconds()
        ops_per_second = total_operations / time_span_seconds if time_span_seconds > 0 else 0

        # Resource usage
        avg_cpu = sum(cpu_values) / len(cpu_values) if cpu_values else 0
        avg_memory = sum(memory_values) / len(memory_values) if memory_values else 0
        peak_memory = max(memory_values) if memory_values else 0

        # By operation type
        by_operation = {}
        operation_types = set(m['operation_type'] for m in filtered)

        for op_type in operation_types:
            op_measurements = [m for m in filtered if m['operation_type'] == op_type]
            op_durations = [m['duration_ms'] for m in op_measurements]

            by_operation[op_type] = {
                'count': len(op_measurements),
                'avg_duration_ms': sum(op_durations) / len(op_durations),
                'min_duration_ms': min(op_durations),
                'max_duration_ms': max(op_durations),
            }

        return PerformanceMetrics(
            start_time=start_time,
            end_time=now,
            total_operations=total_operations,
            avg_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            p50_duration_ms=p50,
            p95_duration_ms=p95,
            p99_duration_ms=p99,
            operations_per_second=ops_per_second,
            avg_cpu_percent=avg_cpu,
            avg_memory_mb=avg_memory,
            peak_memory_mb=peak_memory,
            by_operation=by_operation,
        )

    def get_slowest_operations(
        self,
        limit: int = 10,
        operation_type: Optional[str] = None,
    ) -> List[Dict[str, any]]:
        """
        Get slowest operations.

        Args:
            limit: Number of operations to return
            operation_type: Filter by operation type

        Returns:
            List of operation measurements
        """
        filtered = self.measurements

        if operation_type:
            filtered = [m for m in filtered if m['operation_type'] == operation_type]

        # Sort by duration (slowest first)
        sorted_ops = sorted(filtered, key=lambda m: m['duration_ms'], reverse=True)

        return sorted_ops[:limit]

    def get_current_metrics(self) -> PerformanceMetrics:
        """
        Get current performance metrics snapshot.

        Returns:
            PerformanceMetrics with current system state
        """
        import psutil

        # Get system metrics
        cpu_percent = psutil.cpu_percent(interval=0.1)
        memory = psutil.virtual_memory()
        memory_mb = memory.used / (1024 * 1024)

        # Get active operations count
        active_operations = len(self.active_timers)

        # Get total operations and average time
        total_operations = len(self.measurements)
        avg_operation_time_ms = 0.0
        if self.measurements:
            recent_measurements = self.measurements[-100:]  # Last 100
            durations = [m['duration_ms'] for m in recent_measurements]
            avg_operation_time_ms = sum(durations) / len(durations) if durations else 0.0

        now = datetime.now()
        return PerformanceMetrics(
            start_time=now,
            end_time=now,
            total_operations=total_operations,
            avg_duration_ms=avg_operation_time_ms,
            min_duration_ms=0.0,
            max_duration_ms=0.0,
            p50_duration_ms=0.0,
            p95_duration_ms=0.0,
            p99_duration_ms=0.0,
            operations_per_second=0.0,
            avg_cpu_percent=cpu_percent,
            avg_memory_mb=memory_mb,
            peak_memory_mb=memory_mb,
            cpu_percent=cpu_percent,
            memory_mb=memory_mb,
            active_operations=active_operations,
            avg_operation_time_ms=avg_operation_time_ms,
            by_operation={},
        )

    def clear_old_measurements(self, days: int = 7):
        """
        Clear measurements older than specified days.

        Args:
            days: Number of days to keep
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        self.measurements = [
            m for m in self.measurements
            if datetime.fromisoformat(m['timestamp']) >= cutoff
        ]

        self._save()

    def _save(self):
        """Save measurements to disk."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                'measurements': self.measurements,
                'version': '1.0',
            }

            with open(self.storage_path, 'w') as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Warning: Failed to save performance data: {e}")

    def _load(self):
        """Load measurements from disk."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, 'r') as f:
                data = json.load(f)

            self.measurements = data.get('measurements', [])

        except Exception as e:
            print(f"Warning: Failed to load performance data: {e}")
            self.measurements = []


# Context manager for timing operations
class Timer:
    """Context manager for timing operations."""

    def __init__(
        self,
        tracker: PerformanceTracker,
        operation_type: str,
        metadata: Optional[Dict[str, any]] = None,
    ):
        """
        Initialize timer.

        Args:
            tracker: PerformanceTracker to record to
            operation_type: Type of operation
            metadata: Additional metadata
        """
        self.tracker = tracker
        self.operation_type = operation_type
        self.metadata = metadata or {}
        self.start_time = 0.0
        self.duration_ms = 0.0

    def __enter__(self):
        """Start timing."""
        self.start_time = time.time()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Stop timing and record."""
        self.duration_ms = (time.time() - self.start_time) * 1000

        self.tracker.record_measurement(
            operation_type=self.operation_type,
            duration_ms=self.duration_ms,
            metadata=self.metadata,
        )


# Missing import
from datetime import timedelta
