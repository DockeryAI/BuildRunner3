"""
Telemetry Commands - CLI commands for monitoring and metrics

Commands:
- br telemetry summary - Show metrics summary
- br telemetry events - List recent events
- br telemetry alerts - Show recent alerts
- br telemetry performance - Show performance metrics
"""

import sys
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional

from core.telemetry import (
    EventCollector,
    EventFilter,
    EventType,
    MetricsAnalyzer,
    ThresholdMonitor,
    PerformanceTracker,
    AlertLevel,
)

telemetry_app = typer.Typer(help="Telemetry and monitoring")
console = Console()


@telemetry_app.command("summary")
def show_summary(
    period: str = typer.Option("day", "--period", "-p", help="Time period (hour/day/week/all)"),
):
    """
    Show metrics summary.

    Example:
        br telemetry summary
        br telemetry summary --period week
    """
    console.print(f"\n[bold blue]Telemetry Summary - {period.upper()}[/bold blue]\n")

    # Load collector and analyzer
    collector = EventCollector()
    analyzer = MetricsAnalyzer(collector)

    # Calculate summary
    summary = analyzer.calculate_summary(period)

    if summary.total_tasks == 0:
        console.print("[yellow]No telemetry data available[/yellow]\n")
        return

    # Display summary
    console.print(
        f"[bold]Period:[/bold] {summary.start_time.strftime('%Y-%m-%d %H:%M')} to {summary.end_time.strftime('%Y-%m-%d %H:%M')}"
    )

    # Task metrics
    console.print(f"\n[bold]Task Metrics:[/bold]")
    console.print(f"  Total Tasks: {summary.total_tasks}")
    console.print(f"  Successful: [green]{summary.successful_tasks}[/green]")
    console.print(f"  Failed: [red]{summary.failed_tasks}[/red]")
    success_color = (
        "green" if summary.success_rate >= 80 else "yellow" if summary.success_rate >= 50 else "red"
    )
    console.print(f"  Success Rate: [{success_color}]{summary.success_rate:.1f}%[/{success_color}]")

    # Performance metrics
    if summary.avg_duration_ms > 0:
        console.print(f"\n[bold]Performance Metrics:[/bold]")
        console.print(f"  Avg Duration: {summary.avg_duration_ms:.1f}ms")
        console.print(f"  P95 Duration: {summary.p95_duration_ms:.1f}ms")
        console.print(f"  P99 Duration: {summary.p99_duration_ms:.1f}ms")

    # Cost metrics
    if summary.total_cost_usd > 0:
        console.print(f"\n[bold]Cost Metrics:[/bold]")
        console.print(f"  Total Cost: [yellow]${summary.total_cost_usd:.4f}[/yellow]")
        console.print(f"  Avg Cost/Task: ${summary.avg_cost_per_task:.6f}")
        console.print(f"  Total Tokens: {summary.total_tokens:,}")

    # Error metrics
    if summary.total_errors > 0:
        console.print(f"\n[bold]Error Metrics:[/bold]")
        console.print(f"  Total Errors: {summary.total_errors}")
        error_color = (
            "red" if summary.error_rate > 10 else "yellow" if summary.error_rate > 5 else "green"
        )
        console.print(f"  Error Rate: [{error_color}]{summary.error_rate:.1f}%[/{error_color}]")

        if summary.errors_by_type:
            console.print(f"  Top Error Types:")
            for error_type, count in list(summary.errors_by_type.items())[:3]:
                console.print(f"    • {error_type}: {count}")

    # Model usage
    if summary.models_used:
        console.print(f"\n[bold]Model Usage:[/bold]")
        for model, count in sorted(summary.models_used.items(), key=lambda x: x[1], reverse=True):
            console.print(f"  {model}: {count} tasks")
        console.print(f"  Most Used: [green]{summary.most_used_model}[/green]")

    # Security
    if summary.security_violations > 0:
        console.print(f"\n[bold red]Security:[/bold red]")
        console.print(f"  Violations: [red]{summary.security_violations}[/red]")

    console.print()


@telemetry_app.command("events")
def list_events(
    count: int = typer.Option(10, "--count", "-n", help="Number of events to show"),
    event_type: Optional[str] = typer.Option(None, "--type", "-t", help="Filter by event type"),
):
    """
    List recent events.

    Example:
        br telemetry events
        br telemetry events --count 20
        br telemetry events --type task_failed
    """
    console.print(f"\n[bold blue]Recent Events[/bold blue]\n")

    collector = EventCollector()

    # Query events
    if event_type:
        try:
            et = EventType(event_type)
            events = collector.query(filter=EventFilter(event_types=[et]), limit=count)
        except ValueError:
            console.print(f"[red]Invalid event type: {event_type}[/red]\n")
            console.print("Valid types:")
            for et in EventType:
                console.print(f"  • {et.value}")
            console.print()
            return
    else:
        events = collector.get_recent(count=count)

    if not events:
        console.print("[yellow]No events found[/yellow]\n")
        return

    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Timestamp", style="dim")
    table.add_column("Type")
    table.add_column("Details")
    table.add_column("ID", style="dim")

    for event in events:
        timestamp = event.timestamp.strftime("%Y-%m-%d %H:%M:%S")
        event_type_str = event.event_type.value

        # Extract details based on event type
        details = ""
        if hasattr(event, "task_id") and event.task_id:
            details = f"Task: {event.task_id}"
            if hasattr(event, "success"):
                status = "✓" if event.success else "✗"
                details += f" {status}"
        elif hasattr(event, "error_type") and event.error_type:
            details = f"Error: {event.error_type}"

        event_id = event.event_id[:8] if event.event_id else ""

        table.add_row(timestamp, event_type_str, details, event_id)

    console.print(table)
    console.print(f"\nShowing {len(events)} event(s)")
    console.print()


@telemetry_app.command("alerts")
def list_alerts(
    count: int = typer.Option(10, "--count", "-n", help="Number of alerts to show"),
    level: Optional[str] = typer.Option(
        None, "--level", "-l", help="Filter by level (info/warning/error/critical)"
    ),
):
    """
    Show recent alerts.

    Example:
        br telemetry alerts
        br telemetry alerts --level critical
        br telemetry alerts --count 20
    """
    console.print(f"\n[bold blue]Recent Alerts[/bold blue]\n")

    # Load monitor
    collector = EventCollector()
    analyzer = MetricsAnalyzer(collector)
    monitor = ThresholdMonitor(analyzer)

    # Check current thresholds
    summary = analyzer.calculate_summary("hour")
    current_alerts = monitor.check_thresholds(summary)

    if current_alerts:
        console.print("[bold red]⚠️  Active Alerts:[/bold red]\n")
        for alert in current_alerts:
            level_colors = {
                AlertLevel.INFO: "blue",
                AlertLevel.WARNING: "yellow",
                AlertLevel.ERROR: "red",
                AlertLevel.CRITICAL: "bold red",
            }
            color = level_colors.get(alert.level, "white")
            console.print(f"  [{color}][{alert.level.value.upper()}][/{color}] {alert.message}")
            console.print(
                f"    {alert.metric_name} = {alert.metric_value} (threshold: {alert.threshold_value})"
            )
        console.print()

    # Get alert history
    alert_level = None
    if level:
        try:
            alert_level = AlertLevel(level)
        except ValueError:
            console.print(f"[red]Invalid level: {level}[/red]\n")
            console.print("Valid levels: info, warning, error, critical\n")
            return

    alerts = monitor.get_recent_alerts(count=count, level=alert_level)

    if not alerts:
        console.print("[green]No alerts in history[/green]\n")
        return

    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Timestamp", style="dim")
    table.add_column("Level")
    table.add_column("Message")
    table.add_column("Value")

    for alert in alerts:
        timestamp = alert.timestamp.strftime("%Y-%m-%d %H:%M:%S")

        level_colors = {
            "info": "blue",
            "warning": "yellow",
            "error": "red",
            "critical": "bold red",
        }
        level_color = level_colors.get(alert.level.value, "white")
        level_text = f"[{level_color}]{alert.level.value.upper()}[/{level_color}]"

        value_text = f"{alert.metric_value:.2f}"

        table.add_row(timestamp, level_text, alert.message, value_text)

    console.print(table)
    console.print(f"\nShowing {len(alerts)} alert(s)")

    # Statistics
    stats = monitor.get_statistics()
    if stats["total_alerts"] > 0:
        console.print(f"\n[bold]Alert Statistics:[/bold]")
        console.print(f"  Total Alerts: {stats['total_alerts']}")
        console.print(f"  By Level: {stats['alerts_by_level']}")

    console.print()


@telemetry_app.command("performance")
def show_performance(
    hours: int = typer.Option(24, "--hours", "-h", help="Number of hours to analyze"),
    operation: Optional[str] = typer.Option(
        None, "--operation", "-o", help="Filter by operation type"
    ),
):
    """
    Show performance metrics.

    Example:
        br telemetry performance
        br telemetry performance --hours 48
        br telemetry performance --operation task_execution
    """
    console.print(f"\n[bold blue]Performance Metrics - Last {hours} Hours[/bold blue]\n")

    tracker = PerformanceTracker()
    metrics = tracker.get_metrics(operation_type=operation, hours=hours)

    if metrics.total_operations == 0:
        console.print("[yellow]No performance data available[/yellow]\n")
        return

    # Display metrics
    console.print(f"[bold]Operations:[/bold] {metrics.total_operations:,}")
    console.print(f"[bold]Throughput:[/bold] {metrics.operations_per_second:.2f} ops/second")

    console.print(f"\n[bold]Duration Metrics:[/bold]")
    console.print(f"  Average: {metrics.avg_duration_ms:.1f}ms")
    console.print(f"  Min: {metrics.min_duration_ms:.1f}ms")
    console.print(f"  Max: {metrics.max_duration_ms:.1f}ms")
    console.print(f"  P50 (median): {metrics.p50_duration_ms:.1f}ms")
    console.print(f"  P95: {metrics.p95_duration_ms:.1f}ms")
    console.print(f"  P99: {metrics.p99_duration_ms:.1f}ms")

    if metrics.avg_cpu_percent > 0:
        console.print(f"\n[bold]Resource Usage:[/bold]")
        console.print(f"  Avg CPU: {metrics.avg_cpu_percent:.1f}%")
        console.print(f"  Avg Memory: {metrics.avg_memory_mb:.1f}MB")
        console.print(f"  Peak Memory: {metrics.peak_memory_mb:.1f}MB")

    # By operation type
    if metrics.by_operation and len(metrics.by_operation) > 1:
        console.print(f"\n[bold]By Operation Type:[/bold]")
        for op_type, op_metrics in sorted(
            metrics.by_operation.items(), key=lambda x: x[1]["count"], reverse=True
        ):
            console.print(f"  {op_type}:")
            console.print(f"    Count: {op_metrics['count']}")
            console.print(f"    Avg: {op_metrics['avg_duration_ms']:.1f}ms")

    # Slowest operations
    slowest = tracker.get_slowest_operations(limit=5, operation_type=operation)
    if slowest:
        console.print(f"\n[bold]Slowest Operations:[/bold]")
        for op in slowest:
            timestamp = op["timestamp"][:19]  # Trim microseconds
            console.print(f"  {op['duration_ms']:.1f}ms - {op['operation_type']} ({timestamp})")

    console.print()


@telemetry_app.command("export")
def export_data(
    output: str = typer.Argument(..., help="Output file path"),
    data_type: str = typer.Option("events", "--type", "-t", help="Data type (events/performance)"),
):
    """
    Export telemetry data to CSV.

    Example:
        br telemetry export events.csv
        br telemetry export perf.csv --type performance
    """
    console.print(f"\n[bold blue]Exporting {data_type.title()} Data...[/bold blue]\n")

    output_path = Path(output)

    if data_type == "events":
        collector = EventCollector()
        collector.export_csv(output_path)
        console.print(
            f"[green]✓ Exported {collector.get_statistics()['total_events']} events to {output}[/green]"
        )

    elif data_type == "performance":
        console.print(f"[yellow]Performance export not yet implemented[/yellow]")

    else:
        console.print(f"[red]Invalid data type: {data_type}[/red]")
        console.print("Valid types: events, performance")

    console.print()
