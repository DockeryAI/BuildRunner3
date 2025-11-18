"""
Orchestration Run Commands - CLI commands for auto-orchestrated task execution

Commands:
- br run --auto - Auto-orchestrate task execution with Claude prompts
- br run batch <batch-id> - Execute specific batch
- br run status - Show orchestration status
"""

import json
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import print as rprint

from core.task_queue import TaskQueue, TaskStatus
from core.batch_optimizer import BatchOptimizer, TaskComplexity, TaskDomain, Task as BatchTask
from core.prompt_builder import PromptBuilder
from core.context_manager import ContextManager, ContextEntry
from core.orchestrator import TaskOrchestrator, OrchestrationStatus
from core.file_monitor import FileMonitor
from core.verification_engine import VerificationEngine
from cli.tasks_commands import get_task_queue, save_task_queue

run_app = typer.Typer(help="Orchestration and execution commands")
console = Console()


def get_orchestrator() -> TaskOrchestrator:
    """Create and configure task orchestrator"""
    project_root = Path.cwd()

    # Initialize components
    batch_optimizer = BatchOptimizer()
    prompt_builder = PromptBuilder()
    context_manager = ContextManager(str(project_root))
    file_monitor = FileMonitor(project_root)
    verification_engine = VerificationEngine(project_root)

    # Create orchestrator
    orchestrator = TaskOrchestrator(
        batch_optimizer=batch_optimizer,
        prompt_builder=prompt_builder,
        context_manager=context_manager,
        file_monitor=file_monitor,
        verification_engine=verification_engine
    )

    return orchestrator


@run_app.command("auto")
def run_auto(
    max_batches: int = typer.Option(
        10,
        "--max-batches",
        "-m",
        help="Maximum number of batches to execute (safety limit)"
    ),
    interactive: bool = typer.Option(
        True,
        "--interactive/--non-interactive",
        "-i/-n",
        help="Prompt for confirmation between batches"
    ),
    verify: bool = typer.Option(
        True,
        "--verify/--no-verify",
        help="Run verification after each batch"
    )
):
    """
    Auto-orchestrate task execution with batch optimization and Claude prompts

    This command:
    1. Loads task queue
    2. Optimizes tasks into 2-3 task batches
    3. Generates Claude prompts for each batch
    4. Displays prompts for you to execute
    5. Monitors completion and verifies results
    """
    try:
        console.print("\n[bold blue]🚀 Auto-Orchestration Mode[/bold blue]\n")

        # Load task queue
        queue = get_task_queue()

        if len(queue.tasks) == 0:
            console.print("[yellow]No tasks found. Run 'br tasks generate' first.[/yellow]")
            raise typer.Exit(1)

        ready_tasks = queue.get_ready_tasks()
        if not ready_tasks:
            console.print("[yellow]No ready tasks to execute.[/yellow]")

            pending = queue.get_pending_tasks()
            if pending:
                console.print(f"\n[dim]{len(pending)} tasks are blocked by dependencies[/dim]")

            return

        console.print(f"[green]✓ Found {len(ready_tasks)} ready tasks[/green]\n")

        # Initialize orchestrator
        orchestrator = get_orchestrator()

        # Display plan
        batch_optimizer = BatchOptimizer()

        # Convert queue tasks to batch optimizer format (BatchTask objects)
        ready_task_objs = []
        for task in ready_tasks:  # ready_tasks contains QueuedTask objects, not IDs
            # Convert string complexity/domain to enums
            try:
                complexity_enum = TaskComplexity(task.complexity.lower())
            except ValueError:
                complexity_enum = TaskComplexity.MEDIUM

            try:
                domain_enum = TaskDomain(task.domain.lower())
            except ValueError:
                domain_enum = TaskDomain.UNKNOWN

            batch_task = BatchTask(
                id=task.id,
                name=task.name,
                description=task.description,
                file_path=task.file_path or "",
                estimated_minutes=task.estimated_minutes,
                complexity=complexity_enum,
                domain=domain_enum,
                dependencies=task.dependencies,
                acceptance_criteria=task.acceptance_criteria
            )
            ready_task_objs.append(batch_task)

        # Optimize into batches
        batches = batch_optimizer.optimize_batches(ready_task_objs[:max_batches * 3])

        console.print(f"[bold]Execution Plan:[/bold] {len(batches)} batches\n")

        # Display batch plan
        plan_table = Table(title="Batch Plan")
        plan_table.add_column("Batch", style="cyan", width=8)
        plan_table.add_column("Tasks", style="white", justify="right", width=8)
        plan_table.add_column("Time", style="blue", justify="right", width=8)
        plan_table.add_column("Complexity", style="yellow", width=12)
        plan_table.add_column("Domain", style="magenta", width=12)

        for batch in batches[:max_batches]:
            batch_tasks = batch.tasks if hasattr(batch, "tasks") else batch.get("tasks", [])
            total_time = sum(t.estimated_minutes for t in batch_tasks)
            complexities = set(t.complexity.value for t in batch_tasks)
            domains = set(t.domain.value for t in batch_tasks)

            plan_table.add_row(
                str(batch.id if hasattr(batch, "id") else batch.get("id")),
                str(len(batch_tasks)),
                f"{total_time}m",
                ", ".join(complexities),
                ", ".join(domains)
            )

        console.print(plan_table)
        console.print()

        if not interactive or typer.confirm("Start orchestration?", default=True):
            # Execute batches
            batches_executed = 0

            for i, batch in enumerate(batches[:max_batches], 1):
                console.print(f"\n[bold cyan]═══ Batch {i}/{min(len(batches), max_batches)} ═══[/bold cyan]\n")

                # Get batch tasks
                batch_tasks = batch.tasks if hasattr(batch, "tasks") else batch.get("tasks", [])

                # Display batch details
                console.print(f"[bold]Tasks in this batch:[/bold]")
                for task in batch_tasks:
                    task_id = task.get("id") if isinstance(task, dict) else task.id
                    task_desc = task.get("description") if isinstance(task, dict) else task.description
                    console.print(f"  • {task_id}: {task_desc}")

                console.print()

                # Generate prompt
                prompt_builder = PromptBuilder()
                context_manager = ContextManager(str(Path.cwd()))

                context = context_manager.get_context(max_chars=2000)
                prompt = prompt_builder.build_prompt(batch, context)

                # Display prompt
                console.print(Panel(
                    prompt,
                    title=f"[bold]Claude Prompt for Batch {i}[/bold]",
                    border_style="blue",
                    expand=False
                ))

                console.print("\n[bold yellow]📋 Copy the above prompt and execute it in Claude[/bold yellow]")

                if interactive:
                    if not typer.confirm("\nHave you completed this batch?", default=False):
                        console.print("[yellow]⏸️  Orchestration paused[/yellow]")
                        break

                    # Mark tasks as completed
                    for task in batch_tasks:
                        task_id = task.get("id") if isinstance(task, dict) else task.id
                        queue.complete_task(task_id)

                    # Update context
                    for task in batch_tasks:
                        task_id = task.get("id") if isinstance(task, dict) else task.id
                        file_path = task.get("file_path") if isinstance(task, dict) else getattr(task, "file_path", None)

                        if file_path:
                            context_manager.add_completed_file(file_path)
                        context_manager.add_completed_task(task_id)

                    save_task_queue(queue)
                    batches_executed += 1

                    # Verification
                    if verify:
                        console.print("\n[bold]Running verification...[/bold]")

                        verification_engine = VerificationEngine(Path.cwd())

                        # Check files exist
                        files_to_check = [
                            task.get("file_path") if isinstance(task, dict) else getattr(task, "file_path", None)
                            for task in batch_tasks
                            if (task.get("file_path") if isinstance(task, dict) else getattr(task, "file_path", None))
                        ]

                        if files_to_check:
                            result = verification_engine.verify_files_exist(files_to_check)
                            if result.passed:
                                console.print(f"[green]✓ {result.message}[/green]")
                            else:
                                console.print(f"[red]✗ {result.message}[/red]")
                                if result.details.get("missing_files"):
                                    console.print(f"[dim]Missing: {', '.join(result.details['missing_files'])}[/dim]")
                else:
                    # Non-interactive mode: just generate prompts
                    batches_executed += 1

                # Check if more ready tasks
                ready_tasks = queue.get_ready_tasks()
                if not ready_tasks and i < len(batches):
                    console.print("\n[yellow]No more ready tasks (remaining are blocked)[/yellow]")
                    break

            # Summary
            console.print(f"\n[bold green]✅ Orchestration Summary[/bold green]")
            console.print(f"  Batches executed: {batches_executed}")
            stats = queue.get_progress()
            console.print(f"  Tasks completed: {stats['completed']}")
            console.print(f"  Tasks remaining: {stats['total'] - stats['completed']}")

            if stats['completed'] == stats['total']:
                console.print("\n[bold bright_green]🎉 All tasks completed![/bold bright_green]")
            else:
                console.print("\n[dim]Run 'br run --auto' again to continue[/dim]")

        else:
            console.print("[yellow]Orchestration cancelled[/yellow]")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@run_app.command("status")
def run_status():
    """Show current orchestration status"""
    try:
        console.print("\n[bold blue]📊 Orchestration Status[/bold blue]\n")

        project_root = Path.cwd()

        # Load queue
        queue = get_task_queue()

        if len(queue.tasks) == 0:
            console.print("[yellow]No orchestration in progress[/yellow]")
            return

        # Stats
        stats = queue.get_progress()

        # Progress table
        table = Table(title="Progress")
        table.add_column("Metric", style="cyan")
        table.add_column("Count", style="green", justify="right")
        table.add_column("Percentage", style="blue", justify="right")

        table.add_row("Total Tasks", str(stats['total']), "100%")
        table.add_row(
            "Completed",
            str(stats['completed']),
            f"{(stats['completed'] / stats['total'] * 100):.1f}%"
        )
        table.add_row(
            "In Progress",
            str(stats['in_progress']),
            f"{(stats['in_progress'] / stats['total'] * 100):.1f}%"
        )
        table.add_row(
            "Ready",
            str(len(queue.get_ready_tasks())),
            f"{(len(queue.get_ready_tasks()) / stats['total'] * 100):.1f}%"
        )
        table.add_row(
            "Blocked",
            str(len(queue.get_pending_tasks())),
            f"{(len(queue.get_pending_tasks()) / stats['total'] * 100):.1f}%"
        )
        table.add_row("Failed", str(stats['failed']), "-")

        console.print(table)

        # Time estimate
        remaining_tasks = [t for t in queue.tasks.values() if t.status != TaskStatus.COMPLETED]
        remaining_time = sum(t.estimated_minutes for t in remaining_tasks)

        console.print(f"\n[bold]Time Estimate:[/bold]")
        console.print(f"  Remaining: ~{remaining_time // 60}h {remaining_time % 60}m")

        # Next batch preview
        ready_tasks = queue.get_ready_tasks()
        if ready_tasks:
            console.print(f"\n[bold]Next Batch:[/bold]")
            console.print(f"  {len(ready_tasks)} tasks ready to execute")
            console.print("[dim]Run 'br run --auto' to continue[/dim]")
        else:
            pending = queue.get_pending_tasks()
            if pending:
                console.print(f"\n[yellow]All remaining tasks are blocked by dependencies[/yellow]")
                console.print(f"[dim]{len(pending)} tasks waiting[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    run_app()
