"""
Build Management Commands - CLI commands for build orchestration, checkpoints, and rollback

Commands:
- br build checkpoint <name> - Create a named checkpoint
- br build rollback <checkpoint-id> - Rollback to a specific checkpoint
- br build resume [checkpoint-id] - Resume from checkpoint (latest if not specified)
- br build list-checkpoints - List all checkpoints
- br build status - Show current build state
- br build analyze - Analyze build dependencies and execution plan
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from typing import Optional
from datetime import datetime

from core.build_orchestrator import BuildOrchestrator, BuildPhase
from core.checkpoint_manager import CheckpointManager
from core.task_queue import TaskQueue
from cli.tasks_commands import get_task_queue, save_task_queue

build_app = typer.Typer(help="Build orchestration and checkpoint management")
console = Console()


def get_orchestrator() -> BuildOrchestrator:
    """Get or create build orchestrator"""
    project_root = Path.cwd()
    queue = get_task_queue()
    return BuildOrchestrator(project_root, queue)


@build_app.command("checkpoint")
def create_checkpoint(
    name: str = typer.Argument(..., help="Checkpoint name"),
    message: Optional[str] = typer.Option(None, "--message", "-m", help="Checkpoint description")
):
    """
    Create a named checkpoint of current build state

    Example:
        br build checkpoint batch1_complete -m "Completed Batch 1 implementation"
    """
    try:
        console.print(f"\n[bold blue]Creating checkpoint: {name}[/bold blue]\n")

        orchestrator = get_orchestrator()

        # Create metadata
        metadata = {
            "name": name,
            "description": message or f"Checkpoint: {name}",
            "created_by": "cli",
            "timestamp": datetime.now().isoformat()
        }

        # Create checkpoint
        checkpoint_id = orchestrator.create_checkpoint(
            phase=name,
            metadata=metadata
        )

        # Get progress info
        progress = orchestrator.get_build_progress()

        console.print(f"[green]✓ Checkpoint created: {checkpoint_id}[/green]\n")
        console.print(f"  Phase: {name}")
        console.print(f"  Tasks completed: {progress['tasks_completed']}/{progress['tasks_total']}")
        console.print(f"  Files created: {progress['files_created']}")
        console.print(f"  Progress: {progress['progress_percent']:.1f}%\n")

        if message:
            console.print(f"  Message: {message}\n")

    except Exception as e:
        console.print(f"[red]❌ Error creating checkpoint: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("rollback")
def rollback_checkpoint(
    checkpoint_id: str = typer.Argument(..., help="Checkpoint ID to rollback to")
):
    """
    Rollback build to a specific checkpoint

    Example:
        br build rollback checkpoint_20251117_142530_123456
    """
    try:
        console.print(f"\n[bold yellow]⚠️  Rolling back to checkpoint: {checkpoint_id}[/bold yellow]\n")

        orchestrator = get_orchestrator()
        checkpoint_manager = CheckpointManager(Path.cwd())

        # Get checkpoint info
        checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
        if not checkpoint:
            console.print(f"[red]❌ Checkpoint not found: {checkpoint_id}[/red]")
            raise typer.Exit(1)

        # Show what will be affected
        files_to_remove = checkpoint_manager.get_files_to_rollback(checkpoint_id)

        console.print(f"[bold]Checkpoint details:[/bold]")
        console.print(f"  Phase: {checkpoint.phase}")
        console.print(f"  Created: {checkpoint.timestamp}")
        console.print(f"  Tasks completed: {len(checkpoint.tasks_completed)}")
        console.print(f"  Files at checkpoint: {len(checkpoint.files_created)}\n")

        if files_to_remove:
            console.print(f"[yellow]⚠️  Files created after this checkpoint (will need manual cleanup):[/yellow]")
            for file in files_to_remove[:5]:
                console.print(f"    • {file}")
            if len(files_to_remove) > 5:
                console.print(f"    ... and {len(files_to_remove) - 5} more")
            console.print()

        # Confirm
        if not typer.confirm("Continue with rollback?", default=False):
            console.print("[yellow]Rollback cancelled[/yellow]")
            raise typer.Exit(0)

        # Perform rollback
        success = orchestrator.rollback_to_checkpoint(checkpoint_id)

        if success:
            # Update task queue
            queue = get_task_queue()
            save_task_queue(queue)

            console.print(f"\n[green]✓ Rolled back to checkpoint: {checkpoint_id}[/green]")
            console.print(f"  Phase restored: {checkpoint.phase}")
            console.print(f"  Tasks restored: {len(checkpoint.tasks_completed)}\n")

            if files_to_remove:
                console.print("[yellow]⚠️  Note: Files created after checkpoint still exist on disk[/yellow]")
                console.print("[dim]You may need to manually remove them[/dim]\n")
        else:
            console.print(f"[red]❌ Rollback failed[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error during rollback: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("resume")
def resume_from_checkpoint(
    checkpoint_id: Optional[str] = typer.Argument(None, help="Checkpoint ID to resume from (latest if not specified)")
):
    """
    Resume build from a checkpoint

    Example:
        br build resume                                    # Resume from latest
        br build resume checkpoint_20251117_142530_123456  # Resume from specific
    """
    try:
        console.print(f"\n[bold blue]Resuming build from checkpoint...[/bold blue]\n")

        orchestrator = get_orchestrator()
        checkpoint_manager = CheckpointManager(Path.cwd())

        # Get checkpoint
        if checkpoint_id:
            checkpoint = checkpoint_manager.get_checkpoint(checkpoint_id)
            if not checkpoint:
                console.print(f"[red]❌ Checkpoint not found: {checkpoint_id}[/red]")
                raise typer.Exit(1)
        else:
            checkpoint = checkpoint_manager.get_latest_checkpoint()
            if not checkpoint:
                console.print("[yellow]No checkpoints found. Nothing to resume.[/yellow]")
                raise typer.Exit(1)
            checkpoint_id = checkpoint.id

        # Resume
        success = orchestrator.resume_from_checkpoint(checkpoint_id)

        if success:
            console.print(f"[green]✓ Resumed from checkpoint: {checkpoint_id}[/green]\n")
            console.print(f"  Phase: {checkpoint.phase}")
            console.print(f"  Created: {checkpoint.timestamp}")
            console.print(f"  Tasks completed: {len(checkpoint.tasks_completed)}")
            console.print(f"  Files tracked: {len(checkpoint.files_created)}\n")

            # Show next steps
            queue = get_task_queue()
            ready_tasks = queue.get_ready_tasks()

            if ready_tasks:
                console.print(f"[bold]Next steps:[/bold]")
                console.print(f"  {len(ready_tasks)} tasks ready to execute")
                console.print(f"[dim]Run 'br run auto' to continue[/dim]\n")
            else:
                console.print(f"[yellow]No ready tasks. Build may be complete or blocked.[/yellow]\n")
        else:
            console.print(f"[red]❌ Resume failed[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error resuming: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("list-checkpoints")
def list_checkpoints():
    """
    List all checkpoints

    Example:
        br build list-checkpoints
    """
    try:
        console.print("\n[bold blue]📋 Build Checkpoints[/bold blue]\n")

        checkpoint_manager = CheckpointManager(Path.cwd())
        checkpoints = checkpoint_manager.list_checkpoints()

        if not checkpoints:
            console.print("[yellow]No checkpoints found[/yellow]\n")
            return

        # Create table
        table = Table(title=f"Checkpoints ({len(checkpoints)} total)")
        table.add_column("ID", style="cyan")
        table.add_column("Phase", style="blue")
        table.add_column("Created", style="green")
        table.add_column("Tasks", justify="right")
        table.add_column("Files", justify="right")
        table.add_column("Status", style="yellow")

        for cp in checkpoints:
            # Format timestamp
            try:
                dt = datetime.fromisoformat(cp.timestamp)
                time_str = dt.strftime("%Y-%m-%d %H:%M:%S")
            except:
                time_str = cp.timestamp

            table.add_row(
                cp.id[-20:],  # Show last 20 chars of ID
                cp.phase,
                time_str,
                str(len(cp.tasks_completed)),
                str(len(cp.files_created)),
                cp.status.value
            )

        console.print(table)
        console.print()

    except Exception as e:
        console.print(f"[red]❌ Error listing checkpoints: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("status")
def build_status():
    """
    Show current build state

    Example:
        br build status
    """
    try:
        console.print("\n[bold blue]🔨 Build Status[/bold blue]\n")

        orchestrator = get_orchestrator()
        progress = orchestrator.get_build_progress()

        # Build state panel
        if progress['phase'] == 'not_started':
            console.print("[yellow]Build not started[/yellow]\n")
            console.print("[dim]Run 'br run auto' to start orchestrated build[/dim]\n")
            return

        # Status table
        table = Table(title="Build Progress")
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green", justify="right")

        table.add_row("Phase", progress['phase'])
        table.add_row("Status", progress['status'])
        table.add_row("Progress", f"{progress['progress_percent']:.1f}%")
        table.add_row("Tasks Completed", f"{progress['tasks_completed']}/{progress['tasks_total']}")
        table.add_row("Tasks In Progress", str(progress['tasks_in_progress']))
        table.add_row("Tasks Pending", str(progress['tasks_pending']))
        table.add_row("Files Created", str(progress['files_created']))

        if progress.get('checkpoint_id'):
            table.add_row("Latest Checkpoint", progress['checkpoint_id'][-20:])

        console.print(table)
        console.print()

        # Recommendations
        if progress['progress_percent'] < 100:
            console.print("[bold]Next actions:[/bold]")
            console.print("  • Run 'br run auto' to continue orchestration")
            console.print("  • Run 'br build checkpoint <name>' to save current state")
            console.print()
        else:
            console.print("[green]✓ Build complete![/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Error getting build status: {e}[/red]")
        raise typer.Exit(1)


@build_app.command("analyze")
def analyze_dependencies():
    """
    Analyze build dependencies and execution plan

    Shows DAG analysis, parallel execution opportunities, and critical path.

    Example:
        br build analyze
    """
    try:
        console.print("\n[bold blue]📊 Build Dependency Analysis[/bold blue]\n")

        orchestrator = get_orchestrator()

        # Get dependency analysis
        analysis = orchestrator.analyze_dependencies()

        # Summary stats
        console.print("[bold]Execution Plan:[/bold]")
        console.print(f"  Total execution levels: {analysis['total_levels']}")
        console.print(f"  Critical path duration: ~{analysis['critical_path_duration']} minutes")
        console.print(f"  Critical path tasks: {len(analysis['critical_path'])}\n")

        # Parallel opportunities
        if analysis['parallelizable_tasks']:
            console.print("[bold]Parallel Execution Opportunities:[/bold]")
            for opp in analysis['parallelizable_tasks']:
                console.print(f"  Level {opp['level']}: {opp['count']} tasks can run in parallel")
            console.print()
        else:
            console.print("[yellow]No parallel execution opportunities found[/yellow]\n")

        # Critical path
        if analysis['critical_path']:
            console.print("[bold]Critical Path:[/bold]")
            for task_id in analysis['critical_path'][:10]:
                console.print(f"  → {task_id}")
            if len(analysis['critical_path']) > 10:
                console.print(f"  ... and {len(analysis['critical_path']) - 10} more")
            console.print()

        # Execution levels detail
        if typer.confirm("\nShow detailed execution levels?", default=False):
            console.print("\n[bold]Execution Levels:[/bold]")
            for level in analysis['execution_levels']:
                console.print(f"\n  Level {level.level} ({level.estimated_minutes} min):")
                for task_id in level.tasks:
                    console.print(f"    • {task_id}")

    except Exception as e:
        console.print(f"[red]❌ Error analyzing dependencies: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    build_app()
