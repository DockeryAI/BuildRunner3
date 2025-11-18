"""
Task Management Commands - CLI commands for task generation and management

Commands:
- br tasks generate - Generate tasks from PROJECT_SPEC.md
- br tasks list - Show task queue status
- br tasks add - Manually add a task
- br tasks complete - Mark task as complete
- br tasks fail - Mark task as failed
- br tasks retry - Retry a failed task
"""

import json
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.spec_parser import SpecParser
from core.task_decomposer import TaskDecomposer, TaskComplexity
from core.dependency_graph import DependencyGraph
from core.task_queue import TaskQueue, TaskStatus, QueuedTask
from core.priority_scheduler import PriorityScheduler, SchedulingStrategy
from core.state_persistence import StatePersistence

tasks_app = typer.Typer(help="Task generation and management commands")
console = Console()


def get_task_queue() -> TaskQueue:
    """Load or create task queue"""
    project_root = Path.cwd()
    state_dir = project_root / ".buildrunner" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    persistence = StatePersistence(str(state_dir))
    state = persistence.load_state()

    if state and "tasks" in state:
        queue = TaskQueue()
        # Restore tasks from state (state["tasks"] is a dict of task_id: task_data)
        for task_id, task_data in state["tasks"].items():
            queued_task = QueuedTask(
                id=task_data["id"],
                name=task_data.get("name", task_data["description"][:50]),
                description=task_data["description"],
                file_path=task_data.get("file_path", ""),
                estimated_minutes=task_data.get("estimated_minutes", 60),
                complexity=task_data.get("complexity", "medium"),
                domain=task_data.get("domain", "general"),
                dependencies=task_data.get("dependencies", []),
                acceptance_criteria=task_data.get("acceptance_criteria", [])
            )
            # Restore status
            if task_data.get("status"):
                queued_task.status = TaskStatus(task_data["status"])

            queue.add_task(queued_task)

        # Restore execution order if present
        if "execution_order" in state:
            queue.execution_order = state["execution_order"]

        return queue

    return TaskQueue()


def save_task_queue(queue: TaskQueue):
    """Save task queue to state"""
    project_root = Path.cwd()
    state_dir = project_root / ".buildrunner" / "state"
    state_dir.mkdir(parents=True, exist_ok=True)

    persistence = StatePersistence(str(state_dir))

    # Convert tasks to dict (StatePersistence expects Dict[str, task])
    tasks_dict = {}
    for task in queue.tasks.values():
        tasks_dict[task.id] = task

    # Get execution order and progress
    execution_order = queue.execution_order
    progress = queue.get_progress()

    persistence.save_state(
        tasks=tasks_dict,
        execution_order=execution_order,
        progress=progress
    )


@tasks_app.command("generate")
def tasks_generate(
    spec_path: str = typer.Option(
        None,
        "--spec",
        "-s",
        help="Path to PROJECT_SPEC.md (default: .buildrunner/PROJECT_SPEC.md)"
    ),
    force: bool = typer.Option(
        False,
        "--force",
        "-f",
        help="Regenerate tasks even if they already exist"
    )
):
    """Generate atomic tasks from PROJECT_SPEC.md"""
    try:
        console.print("\n[bold blue]⚙️  Generating Tasks from PROJECT_SPEC[/bold blue]\n")

        project_root = Path.cwd()

        # Default spec path
        if not spec_path:
            spec_path = str(project_root / ".buildrunner" / "PROJECT_SPEC.md")

        if not Path(spec_path).exists():
            console.print(f"[red]❌ PROJECT_SPEC not found: {spec_path}[/red]")
            console.print("[dim]💡 Tip: Run 'br spec wizard' to create one[/dim]")
            raise typer.Exit(1)

        # Check if tasks already exist
        state_dir = project_root / ".buildrunner" / "state"
        if not force and (state_dir / "orchestration.json").exists():
            console.print("[yellow]⚠️  Tasks already exist. Use --force to regenerate[/yellow]")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            # Parse spec
            task = progress.add_task("Parsing PROJECT_SPEC...", total=None)
            parser = SpecParser()
            spec_data = parser.parse_spec(Path(spec_path))
            progress.update(task, description=f"✓ Parsed {len(spec_data['features'])} features")

            # Decompose into tasks
            task = progress.add_task("Decomposing features into tasks...", total=None)
            decomposer = TaskDecomposer()
            all_tasks = []

            for feature_dict in spec_data['features']:
                feature_tasks = decomposer.decompose_feature(feature_dict)
                all_tasks.extend(feature_tasks)

            progress.update(task, description=f"✓ Generated {len(all_tasks)} atomic tasks")

            # Build dependency graph
            task = progress.add_task("Building dependency graph...", total=None)
            graph = DependencyGraph()

            for t in all_tasks:
                graph.add_task({
                    'id': t.id,
                    'dependencies': t.dependencies,
                    'estimated_minutes': t.estimated_minutes
                })

            # Check for circular dependencies
            if graph.has_circular_dependency():
                console.print("[red]❌ Circular dependency detected in tasks![/red]")
                raise typer.Exit(1)

            progress.update(task, description="✓ Dependency graph validated")

            # Create task queue
            task = progress.add_task("Creating task queue...", total=None)
            queue = TaskQueue()

            for t in all_tasks:
                queued_task = QueuedTask(
                    id=t.id,
                    name=t.name,
                    description=t.description,
                    file_path=getattr(t, 'file_path', ''),
                    estimated_minutes=t.estimated_minutes,
                    complexity=t.complexity.value,
                    domain=t.category,  # Use category as domain
                    dependencies=t.dependencies,
                    acceptance_criteria=t.acceptance_criteria
                )
                queue.add_task(queued_task)

            # Save queue
            save_task_queue(queue)
            progress.update(task, description="✓ Task queue saved")

        # Display summary
        console.print("\n[green]✅ Task generation complete![/green]\n")

        summary_table = Table(title="Task Summary")
        summary_table.add_column("Metric", style="cyan")
        summary_table.add_column("Value", style="green", justify="right")

        summary_table.add_row("Total Tasks", str(len(all_tasks)))
        summary_table.add_row("Ready Tasks", str(len(queue.get_ready_tasks())))
        summary_table.add_row("Blocked Tasks", str(len(queue.get_pending_tasks())))

        # Complexity breakdown
        complexity_counts = {}
        for t in all_tasks:
            c = t.complexity.value
            complexity_counts[c] = complexity_counts.get(c, 0) + 1

        for complexity, count in sorted(complexity_counts.items()):
            summary_table.add_row(f"  {complexity.title()}", str(count))

        # Time estimate
        total_time = sum(t.estimated_minutes for t in all_tasks)
        summary_table.add_row("Est. Total Time", f"{total_time // 60}h {total_time % 60}m")

        console.print(summary_table)

        # Execution plan
        levels = graph.get_execution_levels()
        console.print(f"\n[bold]Execution Plan:[/bold] {len(levels)} levels")
        console.print(f"  Parallelizable tasks in level 1: {len(levels[0].tasks) if levels else 0}")

        # Next steps
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Run [cyan]br tasks list[/cyan] to see task queue")
        console.print("  2. Run [cyan]br run --auto[/cyan] to start auto-orchestration")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@tasks_app.command("list")
def tasks_list(
    status: str = typer.Option(
        None,
        "--status",
        "-s",
        help="Filter by status (pending, ready, in_progress, completed, failed)"
    ),
    show_all: bool = typer.Option(
        False,
        "--all",
        "-a",
        help="Show all tasks including completed"
    )
):
    """Show task queue status"""
    try:
        console.print("\n[bold blue]📋 Task Queue[/bold blue]\n")

        queue = get_task_queue()

        if len(queue.tasks) == 0:
            console.print("[yellow]No tasks found. Run 'br tasks generate' first.[/yellow]")
            return

        # Get tasks to display
        if status:
            try:
                status_filter = TaskStatus[status.upper()]
                tasks = [t for t in queue.tasks.values() if t.status == status_filter]
                title = f"Tasks: {status.title()}"
            except (ValueError, KeyError):
                console.print(f"[red]❌ Invalid status: {status}[/red]")
                console.print("[dim]Valid: pending, ready, in_progress, completed, failed[/dim]")
                raise typer.Exit(1)
        elif show_all:
            tasks = list(queue.tasks.values())
            title = "All Tasks"
        else:
            # Default: show non-completed tasks
            tasks = [t for t in queue.tasks.values() if t.status != TaskStatus.COMPLETED]
            title = "Active Tasks"

        if not tasks:
            console.print(f"[yellow]No {status or 'active'} tasks found.[/yellow]")
            return

        # Display table
        table = Table(title=title)
        table.add_column("ID", style="cyan", width=20)
        table.add_column("Description", style="white", width=40)
        table.add_column("Status", style="yellow", width=12)
        table.add_column("Priority", style="magenta", justify="right", width=8)
        table.add_column("Duration", style="blue", justify="right", width=8)
        table.add_column("Dependencies", style="dim", width=15)

        for task in tasks[:50]:  # Limit to 50 for display
            # Status color
            status_colors = {
                TaskStatus.PENDING: "yellow",
                TaskStatus.READY: "green",
                TaskStatus.IN_PROGRESS: "blue",
                TaskStatus.COMPLETED: "bright_green",
                TaskStatus.FAILED: "red",
                TaskStatus.BLOCKED: "red",
                TaskStatus.SKIPPED: "dim"
            }
            status_color = status_colors.get(task.status, "white")

            # Truncate description
            desc = task.description[:37] + "..." if len(task.description) > 40 else task.description

            # Format dependencies
            deps = f"{len(task.dependencies)} deps" if task.dependencies else "-"

            table.add_row(
                task.id,
                desc,
                f"[{status_color}]{task.status.value}[/{status_color}]",
                "-",  # QueuedTask doesn't have priority field
                f"{task.estimated_minutes}m",
                deps
            )

        console.print(table)

        if len(tasks) > 50:
            console.print(f"\n[dim]... and {len(tasks) - 50} more tasks[/dim]")

        # Summary stats
        stats = queue.get_progress()
        console.print(f"\n[bold]Queue Statistics:[/bold]")
        console.print(f"  Total: {stats['total']}")
        console.print(f"  Ready: [green]{len(queue.get_ready_tasks())}[/green]")
        console.print(f"  In Progress: [blue]{stats['in_progress']}[/blue]")
        console.print(f"  Completed: [bright_green]{stats['completed']}[/bright_green]")
        console.print(f"  Failed: [red]{stats['failed']}[/red]")

        if stats['completed'] > 0:
            completion_rate = (stats['completed'] / stats['total']) * 100
            console.print(f"\n  Progress: {completion_rate:.1f}%")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@tasks_app.command("complete")
def tasks_complete(
    task_id: str = typer.Argument(..., help="Task ID to mark complete")
):
    """Mark a task as completed"""
    try:
        queue = get_task_queue()

        if queue.complete_task(task_id):
            save_task_queue(queue)
            console.print(f"[green]✓ Task {task_id} marked as completed[/green]")

            # Show newly ready tasks
            ready_tasks = queue.get_ready_tasks()
            if ready_tasks:
                console.print(f"\n[cyan]💡 {len(ready_tasks)} tasks are now ready to execute[/cyan]")
        else:
            console.print(f"[red]❌ Task {task_id} not found[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@tasks_app.command("fail")
def tasks_fail(
    task_id: str = typer.Argument(..., help="Task ID to mark failed"),
    error: str = typer.Option("", "--error", "-e", help="Error message")
):
    """Mark a task as failed"""
    try:
        queue = get_task_queue()

        if queue.fail_task(task_id, error):
            save_task_queue(queue)

            task = queue.tasks.get(task_id)
            if task and task.status == TaskStatus.FAILED:
                console.print(f"[red]✗ Task {task_id} marked as failed (max retries exceeded)[/red]")
            else:
                console.print(f"[yellow]⚠️  Task {task_id} failed (retry {task.retry_count}/{queue.max_retries})[/yellow]")
        else:
            console.print(f"[red]❌ Task {task_id} not found[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    tasks_app()
