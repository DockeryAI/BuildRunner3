"""
Agent Commands - CLI commands for Claude Agent Bridge

Commands:
- br agent run <task> --type explore|test|review|refactor|implement
- br agent status [assignment_id]
- br agent stats
- br agent list
- br agent cancel <assignment_id>
- br agent retry <assignment_id>
"""

import json
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.agents import ClaudeAgentBridge, AgentType
from core.task_queue import TaskQueue, TaskStatus
from core.telemetry import EventCollector

agent_app = typer.Typer(help="Claude Agent Bridge commands")
console = Console()


def get_agent_bridge() -> ClaudeAgentBridge:
    """Get or create agent bridge instance"""
    project_root = Path.cwd()
    event_collector = EventCollector()
    return ClaudeAgentBridge(
        project_root=str(project_root),
        event_collector=event_collector,
        timeout_seconds=300,
        enable_retries=True,
    )


@agent_app.command("run")
def agent_run(
    task_id: str = typer.Argument(..., help="Task ID to run"),
    agent_type: str = typer.Option(
        "implement",
        "--type",
        "-t",
        help="Agent type: explore, test, review, refactor, implement",
    ),
    prompt: Optional[str] = typer.Option(
        None,
        "--prompt",
        "-p",
        help="Custom prompt for the agent",
    ),
    context: Optional[str] = typer.Option(
        None,
        "--context",
        "-c",
        help="Additional context for the agent",
    ),
    wait: bool = typer.Option(
        True,
        "--wait/--no-wait",
        help="Wait for agent to complete",
    ),
):
    """Run a task with a Claude agent"""
    try:
        # Validate agent type
        try:
            agent_enum = AgentType(agent_type)
        except ValueError:
            console.print(
                f"[red]❌ Invalid agent type: {agent_type}[/red]\n"
                f"Valid types: {', '.join([t.value for t in AgentType])}"
            )
            raise typer.Exit(1)

        console.print(
            f"\n[bold blue]🤖 Dispatching Task to Agent[/bold blue]\n"
            f"Task ID: [cyan]{task_id}[/cyan]\n"
            f"Agent Type: [cyan]{agent_type}[/cyan]\n"
        )

        # Get or create task from queue
        project_root = Path.cwd()
        task_queue = TaskQueue(project_root)
        task = task_queue.get_task(task_id)

        if not task:
            console.print(f"[red]❌ Task not found: {task_id}[/red]")
            raise typer.Exit(1)

        # Get agent bridge
        bridge = get_agent_bridge()

        # Use default prompt if not provided
        if not prompt:
            prompt = f"Execute this {agent_type} task for the BuildRunner project."

        # Dispatch task
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task(f"Dispatching to {agent_type} agent...", total=None)

            try:
                assignment = bridge.dispatch_task(
                    task=task,
                    agent_type=agent_enum,
                    prompt=prompt,
                    context=context,
                )

                console.print(
                    f"\n[green]✓ Task dispatched successfully![/green]\n"
                    f"Assignment ID: [cyan]{assignment.assignment_id}[/cyan]\n"
                )

                # Show response details
                if assignment.response:
                    response = assignment.response
                    console.print(f"[bold]Response:[/bold]")
                    console.print(f"  Status: {response.status.value}")
                    console.print(f"  Success: {response.success}")
                    console.print(f"  Duration: {response.duration_ms:.0f}ms")

                    if response.files_created:
                        console.print(f"  Files Created: {len(response.files_created)}")
                        for file in response.files_created[:5]:
                            console.print(f"    - {file}")
                        if len(response.files_created) > 5:
                            console.print(f"    ... and {len(response.files_created) - 5} more")

                    if response.errors:
                        console.print(f"  [red]Errors:[/red]")
                        for error in response.errors[:3]:
                            console.print(f"    - {error}")
                        if len(response.errors) > 3:
                            console.print(f"    ... and {len(response.errors) - 3} more")

                    console.print(f"\n[cyan]Output:[/cyan]")
                    # Show first 500 chars of output
                    output = (
                        response.output[:500] + "..."
                        if len(response.output) > 500
                        else response.output
                    )
                    console.print(output)

                # Suggest next steps
                console.print(f"\n[bold]Next steps:[/bold]")
                console.print(
                    f"  - Run [cyan]br agent status {assignment.assignment_id}[/cyan] to check status"
                )
                console.print(f"  - Run [cyan]br agent stats[/cyan] to view agent statistics")

            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("status")
def agent_status(
    assignment_id: Optional[str] = typer.Argument(
        None, help="Assignment ID (optional, shows latest if not provided)"
    ),
):
    """Check status of an agent assignment"""
    try:
        bridge = get_agent_bridge()

        if not assignment_id:
            # Show latest assignment
            assignments = bridge.list_assignments(limit=1)
            if not assignments:
                console.print("[yellow]No assignments found[/yellow]")
                return
            assignment = assignments[0]
            assignment_id = assignment.assignment_id
        else:
            assignment = bridge.get_assignment(assignment_id)
            if not assignment:
                console.print(f"[red]❌ Assignment not found: {assignment_id}[/red]")
                raise typer.Exit(1)

        # Display assignment details
        console.print(f"\n[bold blue]📋 Assignment Status[/bold blue]\n")

        # Create status table
        table = Table(show_header=False, box=None)
        table.add_column(style="cyan", no_wrap=True)
        table.add_column(style="white")

        table.add_row("Assignment ID", assignment.assignment_id)
        table.add_row("Task ID", assignment.task_id)
        table.add_row("Agent Type", assignment.agent_type.value.upper())
        table.add_row("Created", assignment.created_at.isoformat())

        if assignment.started_at:
            table.add_row("Started", assignment.started_at.isoformat())

        if assignment.completed_at:
            table.add_row("Completed", assignment.completed_at.isoformat())
            if assignment.duration_ms():
                table.add_row("Duration", f"{assignment.duration_ms():.0f}ms")

        table.add_row("Retries", str(assignment.retry_count))

        if assignment.response:
            response = assignment.response
            table.add_row("Response Status", response.status.value)
            table.add_row("Success", "✓ Yes" if response.success else "✗ No")
            table.add_row("Duration", f"{response.duration_ms:.0f}ms")
            table.add_row("Files Created", str(len(response.files_created)))
            table.add_row("Files Modified", str(len(response.files_modified)))
            table.add_row("Errors", str(len(response.errors)))

        console.print(table)

        # Show response details
        if assignment.response:
            response = assignment.response

            if response.files_created:
                console.print(f"\n[bold]Files Created:[/bold]")
                for file in response.files_created:
                    console.print(f"  ✓ {file}")

            if response.files_modified:
                console.print(f"\n[bold]Files Modified:[/bold]")
                for file in response.files_modified:
                    console.print(f"  ◆ {file}")

            if response.errors:
                console.print(f"\n[bold red]Errors:[/bold red]")
                for error in response.errors:
                    console.print(f"  ✗ {error}")

            if response.output:
                console.print(f"\n[bold]Output (first 1000 chars):[/bold]")
                output = (
                    response.output[:1000] + "..."
                    if len(response.output) > 1000
                    else response.output
                )
                console.print(Panel(output, border_style="cyan"))

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("stats")
def agent_stats():
    """Show agent bridge statistics"""
    try:
        bridge = get_agent_bridge()
        stats = bridge.get_stats()

        console.print(f"\n[bold blue]📊 Agent Bridge Statistics[/bold blue]\n")

        # Summary table
        summary_table = Table(title="Summary", show_header=False, box=None)
        summary_table.add_column(style="cyan", no_wrap=True)
        summary_table.add_column(style="white")

        summary_table.add_row("Total Dispatched", str(stats["total_dispatched"]))
        summary_table.add_row("Total Completed", str(stats["total_completed"]))
        summary_table.add_row("Total Failed", str(stats["total_failed"]))
        summary_table.add_row("Total Retries", str(stats["total_retries"]))

        success_rate = stats["success_rate"]
        rate_color = "green" if success_rate >= 0.9 else "yellow" if success_rate >= 0.7 else "red"
        summary_table.add_row("Success Rate", f"[{rate_color}]{success_rate:.1%}[/{rate_color}]")

        console.print(summary_table)

        # By agent type
        if stats["by_agent_type"]:
            console.print(f"\n[bold]By Agent Type:[/bold]")
            agent_table = Table(show_header=True)
            agent_table.add_column("Agent Type", style="cyan")
            agent_table.add_column("Count", justify="right", style="white")

            for agent_type, count in sorted(stats["by_agent_type"].items()):
                agent_table.add_row(agent_type.upper(), str(count))

            console.print(agent_table)

        # By status
        if stats["by_status"]:
            console.print(f"\n[bold]By Status:[/bold]")
            status_table = Table(show_header=True)
            status_table.add_column("Status", style="cyan")
            status_table.add_column("Count", justify="right", style="white")

            for status, count in sorted(stats["by_status"].items()):
                status_table.add_row(status, str(count))

            console.print(status_table)

        # Recent assignments
        assignments = bridge.list_assignments(limit=5)
        if assignments:
            console.print(f"\n[bold]Recent Assignments:[/bold]")
            recent_table = Table(show_header=True)
            recent_table.add_column("Assignment ID", style="cyan")
            recent_table.add_column("Task ID", style="cyan")
            recent_table.add_column("Agent Type", style="yellow")
            recent_table.add_column("Status", style="white")

            for assignment in reversed(assignments):
                status = assignment.response.status.value if assignment.response else "pending"
                recent_table.add_row(
                    assignment.assignment_id,
                    assignment.task_id,
                    assignment.agent_type.value,
                    status,
                )

            console.print(recent_table)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("list")
def agent_list(
    limit: int = typer.Option(
        20,
        "--limit",
        "-l",
        help="Number of assignments to list",
    ),
):
    """List recent agent assignments"""
    try:
        bridge = get_agent_bridge()
        assignments = bridge.list_assignments(limit=limit)

        if not assignments:
            console.print("[yellow]No assignments found[/yellow]")
            return

        console.print(f"\n[bold blue]📋 Recent Agent Assignments[/bold blue]\n")

        table = Table(show_header=True)
        table.add_column("ID", style="cyan")
        table.add_column("Task ID", style="cyan")
        table.add_column("Agent Type", style="yellow")
        table.add_column("Status", style="white")
        table.add_column("Created", style="white")
        table.add_column("Duration", justify="right", style="white")

        for assignment in reversed(assignments):
            status = assignment.response.status.value if assignment.response else "pending"
            duration = f"{assignment.duration_ms():.0f}ms" if assignment.duration_ms() else "-"
            created = assignment.created_at.strftime("%H:%M:%S")

            table.add_row(
                assignment.assignment_id,
                assignment.task_id,
                assignment.agent_type.value,
                status,
                created,
                duration,
            )

        console.print(table)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("cancel")
def agent_cancel(
    assignment_id: str = typer.Argument(..., help="Assignment ID to cancel"),
):
    """Cancel an agent assignment"""
    try:
        bridge = get_agent_bridge()

        if bridge.cancel_assignment(assignment_id):
            console.print(f"[green]✓ Assignment cancelled: {assignment_id}[/green]")
        else:
            console.print(f"[red]❌ Assignment not found: {assignment_id}[/red]")
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@agent_app.command("retry")
def agent_retry(
    assignment_id: str = typer.Argument(..., help="Assignment ID to retry"),
    prompt: Optional[str] = typer.Option(
        None,
        "--prompt",
        "-p",
        help="New prompt for retry",
    ),
):
    """Retry a failed agent assignment"""
    try:
        bridge = get_agent_bridge()
        assignment = bridge.get_assignment(assignment_id)

        if not assignment:
            console.print(f"[red]❌ Assignment not found: {assignment_id}[/red]")
            raise typer.Exit(1)

        console.print(
            f"\n[bold blue]🔄 Retrying Assignment[/bold blue]\n"
            f"Assignment ID: [cyan]{assignment_id}[/cyan]\n"
            f"Task ID: [cyan]{assignment.task_id}[/cyan]\n"
        )

        # Reconstruct task
        project_root = Path.cwd()
        task_queue = TaskQueue(project_root)
        task = task_queue.get_task(assignment.task_id)

        if not task:
            console.print(f"[red]❌ Task not found: {assignment.task_id}[/red]")
            raise typer.Exit(1)

        # Use new prompt or default
        retry_prompt = prompt or f"Retry: {assignment.agent_type.value} agent task"

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            progress.add_task("Retrying assignment...", total=None)

            try:
                new_assignment = bridge.retry_assignment(
                    assignment_id=assignment_id,
                    task=task,
                    agent_type=assignment.agent_type,
                    prompt=retry_prompt,
                )

                console.print(
                    f"\n[green]✓ Assignment retried successfully![/green]\n"
                    f"New Assignment ID: [cyan]{new_assignment.assignment_id}[/cyan]\n"
                )

                if new_assignment.response:
                    response = new_assignment.response
                    console.print(f"[bold]Result:[/bold]")
                    console.print(f"  Status: {response.status.value}")
                    console.print(f"  Success: {response.success}")

            except Exception as e:
                console.print(f"[red]❌ Error: {e}[/red]")
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)
