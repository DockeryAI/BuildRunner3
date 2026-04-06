"""
Routing Commands - CLI commands for model routing and cost management

Commands:
- br routing estimate - Estimate complexity for a task
- br routing select - Select model for a task
- br routing costs - Show cost summary
- br routing models - List available models
"""

import sys
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from typing import Optional, List

from core.routing import (
    ComplexityEstimator,
    ModelSelector,
    CostTracker,
)

routing_app = typer.Typer(help="Model routing and cost management")
console = Console()


@routing_app.command("estimate")
def estimate_complexity(
    description: str = typer.Argument(..., help="Task description"),
    files: Optional[List[str]] = typer.Option(None, "--file", "-f", help="Files involved"),
):
    """
    Estimate task complexity and recommend model.

    Example:
        br routing estimate "Add user authentication"
        br routing estimate "Fix bug" --file auth.py --file middleware.py
    """
    console.print("\n[bold blue]Estimating Task Complexity...[/bold blue]\n")

    estimator = ComplexityEstimator()

    # Convert file paths
    file_paths = [Path(f) for f in files] if files else []

    # Estimate
    complexity = estimator.estimate(
        task_description=description,
        files=file_paths,
    )

    # Display results
    console.print(f"[cyan]Task:[/cyan] {description}")
    if files:
        console.print(f"[cyan]Files:[/cyan] {len(files)} file(s)")

    console.print(f"\n[bold]Complexity Analysis:[/bold]")
    console.print(f"  Level: [yellow]{complexity.level.value.upper()}[/yellow]")
    console.print(f"  Score: {complexity.score:.1f}/100")
    console.print(f"  Task Type: {complexity.task_type}")

    console.print(
        f"\n[bold]Recommended Model:[/bold] [green]{complexity.recommended_model}[/green]"
    )
    console.print(f"  Estimated Tokens: {complexity.estimated_tokens:,}")

    if complexity.reasons:
        console.print(f"\n[bold]Reasons:[/bold]")
        for reason in complexity.reasons[:5]:
            console.print(f"  • {reason}")

    # Complexity factors
    factors = []
    if complexity.has_architecture_changes:
        factors.append("Architecture changes")
    if complexity.has_security_implications:
        factors.append("Security implications")
    if complexity.has_performance_requirements:
        factors.append("Performance requirements")
    if complexity.has_concurrency:
        factors.append("Concurrency")
    if complexity.requires_deep_reasoning:
        factors.append("Deep reasoning")

    if factors:
        console.print(f"\n[bold]Complexity Factors:[/bold]")
        for factor in factors:
            console.print(f"  • {factor}")

    console.print()


@routing_app.command("select")
def select_model(
    description: str = typer.Argument(..., help="Task description"),
    files: Optional[List[str]] = typer.Option(None, "--file", "-f", help="Files involved"),
    override: Optional[str] = typer.Option(None, "--model", help="Force specific model"),
    cost_limit: Optional[float] = typer.Option(None, "--cost-limit", help="Max cost in USD"),
):
    """
    Select optimal model for a task.

    Example:
        br routing select "Refactor database layer"
        br routing select "Add feature" --cost-limit 0.05
        br routing select "Fix bug" --model opus
    """
    console.print("\n[bold blue]Selecting Model...[/bold blue]\n")

    # Estimate complexity
    estimator = ComplexityEstimator()
    file_paths = [Path(f) for f in files] if files else []
    complexity = estimator.estimate(description, files=file_paths)

    # Select model
    selector = ModelSelector(cost_threshold=cost_limit)
    selection = selector.select(complexity, override_model=override)

    # Display results
    console.print(f"[cyan]Task:[/cyan] {description}")
    console.print(f"[cyan]Complexity:[/cyan] {complexity.level.value} ({complexity.score:.1f}/100)")

    console.print(f"\n[bold green]Selected Model: {selection.model.name.upper()}[/bold green]")
    console.print(f"  Reason: {selection.reason}")
    console.print(f"  Estimated Cost: [yellow]${selection.estimated_cost:.6f}[/yellow]")

    # Model details
    model = selection.model
    console.print(f"\n[bold]Model Details:[/bold]")
    console.print(f"  Provider: {model.provider}")
    console.print(f"  Tier: {model.tier.value}")
    console.print(f"  Context Window: {model.context_window:,} tokens")
    console.print(f"  Max Output: {model.max_tokens:,} tokens")
    console.print(f"  Input Cost: ${model.input_cost_per_1m:.2f}/1M tokens")
    console.print(f"  Output Cost: ${model.output_cost_per_1m:.2f}/1M tokens")
    console.print(f"  Avg Latency: {model.avg_latency_ms:.0f}ms")

    # Alternatives
    if selection.alternatives:
        console.print(f"\n[bold]Alternatives:[/bold]")
        for alt in selection.alternatives:
            console.print(f"  • {alt.name} ({alt.tier.value})")

    console.print()


@routing_app.command("costs")
def show_costs(
    period: str = typer.Option(
        "day", "--period", "-p", help="Time period (hour/day/week/month/all)"
    ),
    export: Optional[str] = typer.Option(None, "--export", help="Export to CSV file"),
):
    """
    Show cost summary.

    Example:
        br routing costs
        br routing costs --period week
        br routing costs --export costs.csv
    """
    console.print(f"\n[bold blue]Cost Summary - {period.upper()}[/bold blue]\n")

    tracker = CostTracker()
    summary = tracker.get_summary(period)

    if summary.total_requests == 0:
        console.print("[yellow]No cost data available[/yellow]\n")
        return

    # Summary panel
    console.print(
        f"[bold]Period:[/bold] {summary.start_date.strftime('%Y-%m-%d %H:%M')} to {summary.end_date.strftime('%Y-%m-%d %H:%M')}"
    )
    console.print(f"\n[bold]Overall:[/bold]")
    console.print(f"  Total Requests: {summary.total_requests:,}")
    console.print(f"  Total Cost: [yellow]${summary.total_cost:.4f}[/yellow]")
    console.print(f"  Total Tokens: {summary.total_tokens:,}")
    console.print(f"  Avg Cost/Request: ${summary.avg_cost_per_request:.6f}")
    console.print(f"  Avg Tokens/Request: {summary.avg_tokens_per_request:.0f}")

    # Cost by model
    if summary.cost_by_model:
        console.print(f"\n[bold]Cost by Model:[/bold]")
        for model, cost in sorted(summary.cost_by_model.items(), key=lambda x: x[1], reverse=True):
            requests = summary.requests_by_model.get(model, 0)
            console.print(f"  {model}: ${cost:.4f} ({requests} requests)")

    # Cost by task type
    if summary.cost_by_task_type:
        console.print(f"\n[bold]Cost by Task Type:[/bold]")
        for task_type, cost in sorted(
            summary.cost_by_task_type.items(), key=lambda x: x[1], reverse=True
        ):
            console.print(f"  {task_type}: ${cost:.4f}")

    console.print(f"\n[bold]Most Expensive Model:[/bold] {summary.most_expensive_model}")
    console.print(f"[bold]Most Used Model:[/bold] {summary.most_used_model}")

    # Export
    if export:
        tracker.export_csv(Path(export))
        console.print(f"\n[green]✓ Exported to {export}[/green]")

    console.print()


@routing_app.command("models")
def list_models(
    available_only: bool = typer.Option(False, "--available", help="Show only available models"),
):
    """
    List available models.

    Example:
        br routing models
        br routing models --available
    """
    console.print("\n[bold blue]Available Models[/bold blue]\n")

    selector = ModelSelector()
    models = selector.list_models(available_only=available_only)

    if not models:
        console.print("[yellow]No models available[/yellow]\n")
        return

    # Create table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Model", style="dim")
    table.add_column("Tier")
    table.add_column("Context")
    table.add_column("Max Out")
    table.add_column("Input Cost", justify="right")
    table.add_column("Output Cost", justify="right")
    table.add_column("Latency", justify="right")
    table.add_column("Available")

    for model in models:
        status = "[green]✓[/green]" if model.is_available else "[red]✗[/red]"
        table.add_row(
            model.name,
            model.tier.value,
            f"{model.context_window:,}",
            f"{model.max_tokens:,}",
            f"${model.input_cost_per_1m:.2f}/1M",
            f"${model.output_cost_per_1m:.2f}/1M",
            f"{model.avg_latency_ms:.0f}ms",
            status,
        )

    console.print(table)
    console.print()
