# Telemetry and Monitoring Guide

**BuildRunner v3.1** - Comprehensive Metrics, Alerts, and Performance Tracking

**Status:** ⚠️ **Beta** - Event schemas defined, collection needs orchestrator integration

---

## Overview

BuildRunner's telemetry system provides comprehensive monitoring of builds, tasks, and system performance with event collection, metrics analysis, threshold monitoring, and alerts.

**Key Features:**
- ✅ Event schemas defined (16 event types)
- ✅ Event collection with file-based storage
- ✅ Metrics analysis and aggregation
- ⚠️ Threshold monitoring (defined, needs testing)
- ⚠️ Performance tracking (defined, needs integration)
- ⚠️ Data persistence (file rotation available, SQLite in development)

---

## Quick Start

### View Metrics Summary

```bash
# Today's metrics
br telemetry summary

# Specific time period
br telemetry summary --period week
```

### List Recent Events

```bash
# Last 20 events
br telemetry events

# Filter by type
br telemetry events --type task_failed

# More events
br telemetry events --count 50
```

### Check Alerts

```bash
# All alerts
br telemetry alerts

# Only critical
br telemetry alerts --level critical
```

### View Performance Data

```bash
# Last 24 hours
br telemetry performance

# Specific time window
br telemetry performance --hours 48

# Filter by operation
br telemetry performance --operation task_execution
```

### Export Data

```bash
# Export events
br telemetry export events.csv

# Export performance data
br telemetry export perf.csv --type performance
```

---

## Event System

### Event Types

BuildRunner tracks 16 event types across 5 categories:

**Task Events:**
- `TASK_STARTED` - Task execution began
- `TASK_COMPLETED` - Task finished successfully
- `TASK_FAILED` - Task failed with error
- `TASK_SKIPPED` - Task skipped (dependencies not met)

**Build Events:**
- `BUILD_STARTED` - Build session started
- `BUILD_COMPLETED` - Build finished successfully
- `BUILD_FAILED` - Build failed

**Model Events:**
- `MODEL_SELECTED` - Model chosen for task
- `MODEL_FALLBACK` - Fallback to alternative model

**Error Events:**
- `ERROR_OCCURRED` - General error
- `RATE_LIMIT_HIT` - API rate limit reached
- `TIMEOUT_OCCURRED` - Operation timed out

**Security Events:**
- `SECURITY_VIOLATION` - Security check failed (secret exposed, SQL injection)

**Quality Events:**
- `QUALITY_GATE_PASSED` - Quality check passed
- `QUALITY_GATE_FAILED` - Quality check failed

**Performance Events:**
- `PERFORMANCE_DEGRADATION` - Performance below threshold

### Event Schema

Every event has:
- `event_id` - Unique identifier
- `timestamp` - When event occurred
- `event_type` - Type of event
- `severity` - INFO, WARNING, ERROR, CRITICAL
- `metadata` - Event-specific data

**Specialized Event Classes:**

**TaskEvent:**
```python
{
    'event_type': 'TASK_COMPLETED',
    'task_id': 'task-123',
    'task_name': 'Build API endpoint',
    'duration_ms': 1234,
    'model_used': 'sonnet',
    'cost_usd': 0.0125,
    'tokens_used': 1500,
    'success': True,
    'error_type': None,
}
```

**BuildEvent:**
```python
{
    'event_type': 'BUILD_STARTED',
    'build_id': 'build-456',
    'total_tasks': 50,
    'session_id': 'session-789',
}
```

**SecurityEvent:**
```python
{
    'event_type': 'SECURITY_VIOLATION',
    'violation_type': 'secret_detected',
    'file_path': 'src/config.py',
    'severity': 'CRITICAL',
    'pattern_matched': 'anthropic_api_key',
}
```

### Viewing Events

**List Recent Events:**
```bash
$ br telemetry events --count 5

Recent Events

┌─────────────────────┬──────────────────┬────────────────────┬──────────┐
│ Timestamp           │ Type             │ Details            │ ID       │
├─────────────────────┼──────────────────┼────────────────────┼──────────┤
│ 2025-11-18 14:30:15 │ task_completed   │ Task: task-42 ✓    │ a3f2e1d9 │
│ 2025-11-18 14:28:33 │ model_selected   │ Model: sonnet      │ b4e3f2c1 │
│ 2025-11-18 14:25:12 │ task_started     │ Task: task-41      │ c5d4e3f2 │
│ 2025-11-18 14:22:45 │ build_started    │ Build: build-v3.1  │ d6e5f4g3 │
│ 2025-11-18 14:20:08 │ task_failed      │ Task: task-40 ✗    │ e7f6g5h4 │
└─────────────────────┴──────────────────┴────────────────────┴──────────┘

Showing 5 event(s)
```

**Filter by Type:**
```bash
$ br telemetry events --type task_failed --count 10

# Shows only failed tasks
```

---

## Metrics Analysis

### Available Metrics

**Task Metrics:**
- Total tasks executed
- Success count and rate
- Failure count and rate
- Average duration
- Duration percentiles (P50, P95, P99)

**Cost Metrics:**
- Total cost (USD)
- Average cost per task
- Total tokens consumed
- Cost breakdown by model

**Model Metrics:**
- Usage by model (count)
- Average cost by model
- Success rate by model

**Error Metrics:**
- Total errors
- Error rate
- Error breakdown by type
- Most common errors

**Performance Metrics:**
- Average latency
- P95/P99 latency
- Throughput (tasks/second)
- Resource usage

### Viewing Metrics

**Summary:**
```bash
$ br telemetry summary --period day

Telemetry Summary - DAY

Period: 2025-11-17 14:30 to 2025-11-18 14:30

Task Metrics:
  Total Tasks: 47
  Successful: 43
  Failed: 4
  Success Rate: 91.5%

Performance Metrics:
  Avg Duration: 1,234.5ms
  P95 Duration: 3,450.2ms
  P99 Duration: 5,123.8ms

Cost Metrics:
  Total Cost: $2.1540
  Avg Cost/Task: $0.045830
  Total Tokens: 142,500

Error Metrics:
  Total Errors: 6
  Error Rate: 12.8%
  Top Error Types:
    • TimeoutError: 3
    • ValueError: 2
    • ConnectionError: 1

Model Usage:
  sonnet: 35 tasks (74.5%)
  haiku: 8 tasks (17.0%)
  opus: 4 tasks (8.5%)
  Most Used: sonnet

Security:
  Violations: 0
```

**Time Periods:**
- `hour` - Last 60 minutes
- `day` - Last 24 hours (default)
- `week` - Last 7 days
- `all` - All time

---

## Threshold Monitoring

### Built-in Thresholds

BuildRunner monitors 7 key thresholds:

| Threshold | Default | Level | Condition |
|-----------|---------|-------|-----------|
| **Success Rate** | 80% | WARNING | Below threshold |
| **Error Rate** | 20% | ERROR | Above threshold |
| **Avg Duration** | 5000ms | WARNING | Above threshold |
| **P95 Duration** | 10000ms | ERROR | Above threshold |
| **Daily Cost** | $10 | WARNING | Above threshold |
| **Hourly Cost** | $2 | ERROR | Above threshold |
| **Security Violations** | 0 | CRITICAL | Any violations |

### Alert Levels

- **INFO** - Informational, no action needed
- **WARNING** - Attention recommended
- **ERROR** - Action required
- **CRITICAL** - Immediate action required

### Viewing Alerts

**Current Alerts:**
```bash
$ br telemetry alerts

Recent Alerts

⚠️  Active Alerts:

  [WARNING] Success rate below 80%
    success_rate = 75.5 (threshold: 80.0)
    Triggered: 2025-11-18 14:30:15

  [WARNING] Daily cost exceeds $10
    total_cost_usd = 12.45 (threshold: 10.0)
    Triggered: 2025-11-18 13:15:42

┌─────────────────────┬─────────┬────────────────────────────────┬────────┐
│ Timestamp           │ Level   │ Message                        │ Value  │
├─────────────────────┼─────────┼────────────────────────────────┼────────┤
│ 2025-11-18 14:30:15 │ WARNING │ Success rate below 80%         │ 75.50  │
│ 2025-11-18 13:15:42 │ WARNING │ Daily cost exceeds $10         │ 12.45  │
│ 2025-11-18 10:22:18 │ ERROR   │ High error rate                │ 25.30  │
│ 2025-11-18 08:05:33 │ WARNING │ P95 duration above 10s         │ 11234  │
└─────────────────────┴─────────┴────────────────────────────────┴────────┘

Showing 4 alert(s)

Alert Statistics:
  Total Alerts: 12 (last 24h)
  By Level: {'warning': 7, 'error': 4, 'critical': 1}
```

**Filter by Level:**
```bash
# Only critical alerts
br telemetry alerts --level critical

# Only warnings and above
br telemetry alerts --level warning
```

### Custom Thresholds

```python
from core.telemetry import ThresholdMonitor, EventCollector

collector = EventCollector()
monitor = ThresholdMonitor(collector)

# Add custom threshold
monitor.add_threshold(
    name="custom_success_rate",
    metric="success_rate",
    threshold=95.0,
    comparison="below",
    level="WARNING",
)

# Check thresholds
alerts = monitor.check_thresholds()
for alert in alerts:
    print(f"[{alert.level}] {alert.message}")
```

---

## Performance Tracking

### Metrics Tracked

**Duration Metrics:**
- Total operations
- Average duration
- Min/max duration
- Percentiles (P50, P95, P99)

**Throughput:**
- Operations per second
- Operations per minute

**Resource Usage:**
- CPU usage (if available)
- Memory usage (if available)

### Viewing Performance

**Summary:**
```bash
$ br telemetry performance --hours 24

Performance Metrics - Last 24 Hours

Operations: 127
Throughput: 0.15 ops/second

Duration Metrics:
  Average: 1,450.2ms
  Min: 234.1ms
  Max: 8,923.5ms
  P50 (median): 1,205.0ms
  P95: 4,512.3ms
  P99: 7,234.1ms

By Operation Type:
  task_execution:
    Count: 95
    Avg: 1,523.4ms
  file_analysis:
    Count: 22
    Avg: 892.1ms
  code_generation:
    Count: 10
    Avg: 2,341.5ms

Slowest Operations:
  8,923.5ms - task_execution (2025-11-18 14:32:15)
  7,834.2ms - code_generation (2025-11-18 13:45:33)
  6,912.0ms - task_execution (2025-11-18 12:12:48)
  5,723.1ms - task_execution (2025-11-18 10:23:11)
  4,891.3ms - code_generation (2025-11-18 09:54:27)
```

**Filter by Operation:**
```bash
# Only task execution
br telemetry performance --operation task_execution

# Specific time window
br telemetry performance --hours 48
```

---

## CLI Commands Reference

### `br telemetry summary`

Show metrics summary.

**Usage:**
```bash
br telemetry summary [OPTIONS]
```

**Options:**
- `--period, -p` - Time period (hour/day/week/all)

**Output:**
- Task metrics (total, success rate, etc.)
- Performance metrics (duration, percentiles)
- Cost metrics (total, average, tokens)
- Error metrics (total, rate, types)
- Model usage distribution
- Security violations

### `br telemetry events`

List recent events.

**Usage:**
```bash
br telemetry events [OPTIONS]
```

**Options:**
- `--count` - Number of events to show (default: 20)
- `--type` - Filter by event type

**Output:**
- Table with timestamp, type, details, ID
- Event count

### `br telemetry alerts`

Show alerts.

**Usage:**
```bash
br telemetry alerts [OPTIONS]
```

**Options:**
- `--count` - Number of alerts to show (default: 20)
- `--level` - Filter by level (info/warning/error/critical)

**Output:**
- Active alerts (current violations)
- Alert history table
- Alert statistics by level

### `br telemetry performance`

View performance metrics.

**Usage:**
```bash
br telemetry performance [OPTIONS]
```

**Options:**
- `--hours` - Time window in hours (default: 24)
- `--operation` - Filter by operation type

**Output:**
- Total operations and throughput
- Duration metrics (avg, min, max, percentiles)
- Resource usage
- By operation type breakdown
- Slowest operations (top 5)

### `br telemetry export`

Export data to CSV.

**Usage:**
```bash
br telemetry export <output_path> [OPTIONS]
```

**Options:**
- `--type` - Data type (events/performance, default: events)

**Output:**
- CSV file with telemetry data

---

## Programmatic Usage

### Basic Example

```python
from core.telemetry import EventCollector, MetricsAnalyzer, TaskEvent, EventType

# Create collector
collector = EventCollector()

# Collect events
event = TaskEvent(
    event_type=EventType.TASK_COMPLETED,
    task_id="task-123",
    task_name="Build feature",
    duration_ms=1500,
    model_used="sonnet",
    cost_usd=0.015,
    tokens_used=1000,
    success=True,
)
collector.collect(event)

# Analyze metrics
analyzer = MetricsAnalyzer(collector)
summary = analyzer.calculate_summary(period="day")

print(f"Total tasks: {summary.total_tasks}")
print(f"Success rate: {summary.success_rate:.1f}%")
print(f"Total cost: ${summary.total_cost:.4f}")
```

### Advanced Event Collection

```python
from core.telemetry import EventCollector, BuildEvent, SecurityEvent, EventType, Severity

collector = EventCollector()

# Build started
build_event = BuildEvent(
    event_type=EventType.BUILD_STARTED,
    build_id="build-456",
    total_tasks=50,
    session_id="session-789",
)
collector.collect(build_event)

# Security violation
security_event = SecurityEvent(
    event_type=EventType.SECURITY_VIOLATION,
    violation_type="secret_detected",
    file_path="src/config.py",
    severity=Severity.CRITICAL,
    details={'pattern': 'anthropic_api_key'},
)
collector.collect(security_event)

# List events
events = collector.get_events(limit=10)
for event in events:
    print(f"{event.timestamp}: {event.event_type} - {event.severity}")
```

### Custom Metrics Analysis

```python
from core.telemetry import EventCollector, MetricsAnalyzer
from datetime import datetime, timedelta

collector = EventCollector()
analyzer = MetricsAnalyzer(collector)

# Calculate custom time range
end_time = datetime.now()
start_time = end_time - timedelta(hours=6)

summary = analyzer.calculate_summary(
    start_time=start_time,
    end_time=end_time,
)

# Analysis
print("Last 6 Hours Analysis:")
print(f"  Tasks: {summary.total_tasks}")
print(f"  Success Rate: {summary.success_rate:.1f}%")
print(f"  Avg Duration: {summary.avg_duration:.0f}ms")
print(f"  P95 Duration: {summary.p95_duration:.0f}ms")
print(f"  Cost: ${summary.total_cost:.4f}")

# Error analysis
if summary.error_rate > 10:
    print("\nHigh error rate detected!")
    print("Top errors:")
    for error_type, count in summary.error_types[:3]:
        print(f"  {error_type}: {count}")
```

### Threshold Monitoring

```python
from core.telemetry import EventCollector, ThresholdMonitor

collector = EventCollector()
monitor = ThresholdMonitor(collector)

# Check all thresholds
alerts = monitor.check_thresholds()

if alerts:
    print(f"Found {len(alerts)} alerts:")
    for alert in alerts:
        print(f"  [{alert.level}] {alert.message}")
        print(f"    Value: {alert.value}, Threshold: {alert.threshold}")

        # Take action based on level
        if alert.level == "CRITICAL":
            send_pagerduty_alert(alert)
        elif alert.level == "ERROR":
            send_slack_notification(alert)
        elif alert.level == "WARNING":
            log_warning(alert)
```

### Performance Tracking

```python
from core.telemetry import PerformanceTracker
import time

tracker = PerformanceTracker()

# Track operation
operation_id = tracker.start_operation(
    operation_type="task_execution",
    metadata={'task_id': 'task-123'},
)

# Do work...
time.sleep(1.5)

# End operation
tracker.end_operation(operation_id, success=True)

# Get metrics
metrics = tracker.get_metrics(hours=24)

print(f"Operations: {metrics.total_operations}")
print(f"Avg Duration: {metrics.avg_duration:.0f}ms")
print(f"P95: {metrics.p95_duration:.0f}ms")
print(f"Throughput: {metrics.throughput:.2f} ops/sec")

# Get slowest operations
slowest = tracker.get_slowest_operations(limit=10)
for op in slowest:
    print(f"{op.duration_ms}ms - {op.operation_type} ({op.timestamp})")
```

---

## Best Practices

### Event Collection

1. **Collect Meaningful Events**
   ```python
   # Good - captures important state change
   collector.collect(TaskEvent(
       event_type=EventType.TASK_COMPLETED,
       task_id=task.id,
       duration_ms=duration,
       success=True,
   ))

   # Avoid - too granular
   collector.collect(Event(event_type="token_received"))
   ```

2. **Include Context**
   ```python
   # Include relevant metadata
   event = TaskEvent(
       event_type=EventType.TASK_FAILED,
       task_id=task.id,
       error_type=type(e).__name__,
       error_message=str(e),
       metadata={'retry_count': 3, 'model': 'sonnet'},
   )
   ```

3. **Set Appropriate Severity**
   - INFO: Normal operations
   - WARNING: Degraded performance, non-critical issues
   - ERROR: Failures, retryable errors
   - CRITICAL: Security violations, data loss

### Metrics Analysis

1. **Regular Monitoring**
   ```bash
   # Daily review
   br telemetry summary --period day

   # Weekly trends
   br telemetry summary --period week
   ```

2. **Focus on Key Metrics**
   - Success rate (should be >90%)
   - P95 latency (should be <5s for most tasks)
   - Error rate (should be <10%)
   - Daily cost (monitor trends)

3. **Export for Deeper Analysis**
   ```bash
   # Weekly export
   br telemetry export weekly-metrics.csv
   # Analyze in spreadsheet/BI tool
   ```

### Alerting

1. **Set Realistic Thresholds**
   - Too low: Alert fatigue
   - Too high: Miss important issues
   - Adjust based on historical data

2. **Alert on Trends**
   - Not just single violations
   - Look for sustained degradation

3. **Actionable Alerts**
   - Each alert should suggest action
   - Include context for debugging

### Performance

1. **Track Critical Paths**
   ```python
   # Track important operations
   with tracker.track("critical_operation"):
       perform_critical_work()
   ```

2. **Identify Bottlenecks**
   ```bash
   # Find slowest operations
   br telemetry performance --hours 24
   ```

3. **Monitor Trends**
   - Watch for performance degradation over time
   - Correlate with system changes

---

## Troubleshooting

### No Events Showing

**Symptom:** `br telemetry events` shows no events

**Solutions:**
1. Check if events file exists:
   ```bash
   ls -la .buildrunner/events.json
   ```
2. Verify events are being collected:
   ```python
   from core.telemetry import EventCollector
   collector = EventCollector()
   print(f"Events: {len(collector.events)}")
   ```
3. Check file permissions

### Incorrect Metrics

**Symptom:** Metrics don't match expected values

**Solutions:**
1. Verify time period:
   ```bash
   br telemetry summary --period day  # vs week
   ```
2. Check event timestamps
3. Review event filtering logic

### Alerts Not Triggering

**Symptom:** Expected alerts don't appear

**Solutions:**
1. Check threshold values:
   ```python
   from core.telemetry import ThresholdMonitor
   monitor = ThresholdMonitor(collector)
   print(monitor.thresholds)
   ```
2. Verify enough events collected for analysis
3. Check alert level filtering

### High Memory Usage

**Symptom:** Large events file or high memory consumption

**Solutions:**
1. Limit event retention:
   ```python
   # Keep only recent events
   collector.cleanup_old_events(days=7)
   ```
2. Export and archive old data
3. Use event filtering to reduce collection

---

## Advanced Topics

### Custom Event Types

```python
from core.telemetry import Event, EventType, Severity
from dataclasses import dataclass

@dataclass
class DeploymentEvent(Event):
    """Custom deployment event."""
    environment: str
    version: str
    deploy_time_ms: int

    def to_dict(self):
        data = super().to_dict()
        data.update({
            'environment': self.environment,
            'version': self.version,
            'deploy_time_ms': self.deploy_time_ms,
        })
        return data

# Collect custom event
event = DeploymentEvent(
    event_type="deployment_completed",
    environment="production",
    version="v3.1.0",
    deploy_time_ms=45000,
    severity=Severity.INFO,
)
collector.collect(event)
```

### Real-Time Monitoring

```python
from core.telemetry import EventCollector
import time

collector = EventCollector()

# Add event listener
def on_event(event):
    if event.severity == "CRITICAL":
        send_alert(event)
    elif event.event_type == "TASK_FAILED":
        log_failure(event)

collector.add_listener(on_event)

# Events are now processed in real-time
```

### Metrics Dashboard

```python
from core.telemetry import EventCollector, MetricsAnalyzer
from rich.console import Console
from rich.table import Table
import time

collector = EventCollector()
analyzer = MetricsAnalyzer(collector)
console = Console()

def render_dashboard():
    summary = analyzer.calculate_summary(period="hour")

    table = Table(title="Telemetry Dashboard")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", justify="right")

    table.add_row("Tasks", str(summary.total_tasks))
    table.add_row("Success Rate", f"{summary.success_rate:.1f}%")
    table.add_row("Avg Duration", f"{summary.avg_duration:.0f}ms")
    table.add_row("Cost", f"${summary.total_cost:.4f}")

    console.clear()
    console.print(table)

# Live dashboard
while True:
    render_dashboard()
    time.sleep(5)
```

---

## Integration Examples

### With Task Orchestrator

```python
from core.orchestrator import Orchestrator
from core.telemetry import EventCollector, TaskEvent, EventType

class TelemetryOrchestrator(Orchestrator):
    def __init__(self):
        super().__init__()
        self.collector = EventCollector()

    def execute_task(self, task):
        # Start event
        start_time = time.time()
        self.collector.collect(TaskEvent(
            event_type=EventType.TASK_STARTED,
            task_id=task.id,
        ))

        try:
            # Execute
            result = super().execute_task(task)

            # Success event
            duration = (time.time() - start_time) * 1000
            self.collector.collect(TaskEvent(
                event_type=EventType.TASK_COMPLETED,
                task_id=task.id,
                duration_ms=duration,
                success=True,
            ))

            return result

        except Exception as e:
            # Failure event
            duration = (time.time() - start_time) * 1000
            self.collector.collect(TaskEvent(
                event_type=EventType.TASK_FAILED,
                task_id=task.id,
                duration_ms=duration,
                success=False,
                error_type=type(e).__name__,
            ))
            raise
```

### With Parallel Orchestration

```python
from core.parallel import SessionManager, WorkerCoordinator
from core.telemetry import EventCollector, BuildEvent, EventType

session_manager = SessionManager()
worker_coordinator = WorkerCoordinator()
collector = EventCollector()

# Track session start
session = session_manager.create_session("Build", total_tasks=10)
collector.collect(BuildEvent(
    event_type=EventType.BUILD_STARTED,
    build_id=session.session_id,
    total_tasks=session.total_tasks,
))

# ... execute build ...

# Track completion
collector.collect(BuildEvent(
    event_type=EventType.BUILD_COMPLETED,
    build_id=session.session_id,
    total_tasks=session.completed_tasks,
))
```

---

## FAQ

**Q: How long are events stored?**

A: Events are stored indefinitely in `.buildrunner/events.json`. Use `cleanup_old_events()` to remove old events.

**Q: Can I disable telemetry?**

A: Yes, but it's not recommended. Telemetry helps track build quality and costs. You can disable specific events or reduce retention.

**Q: How do alerts work?**

A: Alerts are checked when you run `br telemetry alerts`. They're not sent automatically. Integrate with your notification system for real-time alerts.

**Q: Can I export data to my monitoring system?**

A: Yes! Export to CSV and import into your system, or use the Python API to integrate directly.

**Q: What's the performance impact?**

A: Minimal. Event collection is <1ms, persistence is async where possible. Metrics calculation is <50ms for typical workloads.

---

## See Also

- [PARALLEL.md](PARALLEL.md) - Parallel orchestration
- [ROUTING.md](ROUTING.md) - Model routing
- [SECURITY.md](SECURITY.md) - Security safeguards
- [README.md](README.md) - Main documentation

---

*BuildRunner v3.1 - Telemetry and Monitoring System*
