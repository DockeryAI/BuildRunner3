"""
Parallel Orchestration CLI Commands

Commands for managing parallel build sessions and workers.
"""

from pathlib import Path
from typing import Optional, List
import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn, BarColumn

from core.parallel import (
    SessionManager,
    Session,
    SessionStatus,
    WorkerCoordinator,
    Worker,
    WorkerStatus,
    LiveDashboard,
    DashboardConfig,
)

parallel_app = typer.Typer(help="Parallel orchestration commands")
console = Console()


@parallel_app.command("start")
def start_session(
    name: str = typer.Argument(..., help="Session name"),
    total_tasks: int = typer.Option(0, "--tasks", "-t", help="Total number of tasks"),
    workers: int = typer.Option(3, "--workers", "-w", help="Number of workers"),
    watch: bool = typer.Option(False, "--watch", help="Show live dashboard"),
):
    """Start a new parallel build session."""
    try:
        console.print(f"\n[bold]Starting Parallel Session:[/bold] {name}\n")

        # Initialize managers
        session_manager = SessionManager()
        worker_coordinator = WorkerCoordinator(max_workers=workers)

        # Create session
        session = session_manager.create_session(
            name=name,
            total_tasks=total_tasks,
        )

        console.print(f"✓ Session created: [cyan]{session.session_id}[/cyan]")

        # Register workers
        console.print(f"\nRegistering {workers} workers...")
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Registering workers...", total=workers)

            for i in range(workers):
                worker = worker_coordinator.register_worker(
                    metadata={'index': i, 'session': session.session_id}
                )
                progress.update(task, advance=1)
                console.print(f"  ✓ Worker {i+1}/{workers}: {worker.worker_id[:8]}")

        # Start session
        first_worker = worker_coordinator.list_workers()[0]
        session_manager.start_session(session.session_id, worker_id=first_worker.worker_id)

        console.print(f"\n[green]✓ Session started successfully[/green]")
        console.print(f"\nSession ID: [cyan]{session.session_id}[/cyan]")
        console.print(f"Workers: {workers}")
        console.print(f"Total Tasks: {total_tasks}")

        # Show dashboard if requested
        if watch:
            console.print("\n[yellow]Starting live dashboard... (Ctrl+C to exit)[/yellow]\n")
            dashboard = LiveDashboard(session_manager, worker_coordinator)
            try:
                dashboard.start_live()
            except KeyboardInterrupt:
                console.print("\n\n[yellow]Dashboard stopped[/yellow]")

    except Exception as e:
        console.print(f"\n[red]Error starting session: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("status")
def show_status(
    session_id: Optional[str] = typer.Argument(None, help="Session ID (or latest)"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed status"),
):
    """Show session status."""
    try:
        session_manager = SessionManager()

        # Get session
        if session_id:
            session = session_manager.get_session(session_id)
            if not session:
                console.print(f"[red]Session not found: {session_id}[/red]")
                raise typer.Exit(1)
        else:
            # Get latest session
            sessions = session_manager.list_sessions()
            if not sessions:
                console.print("[yellow]No sessions found[/yellow]")
                return
            session = sessions[0]

        # Display status
        console.print(f"\n[bold]Session Status[/bold]\n")

        # Status color
        status_colors = {
            SessionStatus.CREATED: "yellow",
            SessionStatus.RUNNING: "green",
            SessionStatus.PAUSED: "yellow",
            SessionStatus.COMPLETED: "blue",
            SessionStatus.FAILED: "red",
            SessionStatus.CANCELLED: "dim",
        }
        status_color = status_colors.get(session.status, "white")

        # Basic info
        console.print(f"ID: [cyan]{session.session_id}[/cyan]")
        console.print(f"Name: {session.name}")
        console.print(f"Status: [{status_color}]{session.status.value.upper()}[/{status_color}]")
        console.print(f"Created: {session.created_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if session.started_at:
            console.print(f"Started: {session.started_at.strftime('%Y-%m-%d %H:%M:%S')}")

        if session.completed_at:
            console.print(f"Completed: {session.completed_at.strftime('%Y-%m-%d %H:%M:%S')}")

        # Progress
        console.print(f"\n[bold]Progress[/bold]")
        console.print(f"Total Tasks: {session.total_tasks}")
        console.print(f"Completed: [green]{session.completed_tasks}[/green]")
        console.print(f"Failed: [red]{session.failed_tasks}[/red]")
        console.print(f"In Progress: [yellow]{session.in_progress_tasks}[/yellow]")
        console.print(f"Progress: {session.progress_percent:.1f}%")

        # Progress bar
        bar_length = 30
        filled = int(bar_length * session.progress_percent / 100)
        bar = "█" * filled + "░" * (bar_length - filled)
        console.print(f"{bar} {session.progress_percent:.0f}%")

        # Verbose info
        if verbose:
            console.print(f"\n[bold]Details[/bold]")
            console.print(f"Worker ID: {session.worker_id or 'None'}")
            console.print(f"Files Locked: {len(session.files_locked)}")
            console.print(f"Files Modified: {len(session.files_modified)}")

            if session.files_locked:
                console.print(f"\n[bold]Locked Files:[/bold]")
                for file in list(session.files_locked)[:10]:
                    console.print(f"  • {file}")

            if session.files_modified:
                console.print(f"\n[bold]Modified Files:[/bold]")
                for file in list(session.files_modified)[:10]:
                    console.print(f"  • {file}")

    except Exception as e:
        console.print(f"\n[red]Error getting status: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("list")
def list_sessions(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(20, "--limit", "-l", help="Maximum sessions to show"),
):
    """List all sessions."""
    try:
        session_manager = SessionManager()

        # Parse status filter
        status_filter = None
        if status:
            try:
                status_filter = SessionStatus(status.lower())
            except ValueError:
                console.print(f"[red]Invalid status: {status}[/red]")
                console.print("Valid statuses: created, running, paused, completed, failed, cancelled")
                raise typer.Exit(1)

        # Get sessions
        sessions = session_manager.list_sessions(status=status_filter)

        if not sessions:
            console.print("[yellow]No sessions found[/yellow]")
            return

        # Create table
        table = Table(title="Build Sessions", show_header=True, header_style="bold magenta")

        table.add_column("ID", style="dim", width=12)
        table.add_column("Name", style="cyan")
        table.add_column("Status", width=12)
        table.add_column("Progress", width=25)
        table.add_column("Tasks", justify="right")
        table.add_column("Created", width=16)

        for session in sessions[:limit]:
            # Status with color
            status_colors = {
                SessionStatus.CREATED: "yellow",
                SessionStatus.RUNNING: "green",
                SessionStatus.PAUSED: "yellow",
                SessionStatus.COMPLETED: "blue",
                SessionStatus.FAILED: "red",
                SessionStatus.CANCELLED: "dim",
            }
            status_color = status_colors.get(session.status, "white")
            status_text = f"[{status_color}]{session.status.value.upper()}[/{status_color}]"

            # Progress bar
            bar_length = 15
            filled = int(bar_length * session.progress_percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            progress_text = f"{bar} {session.progress_percent:.0f}%"

            # Tasks
            tasks_text = f"{session.completed_tasks}/{session.total_tasks}"
            if session.failed_tasks > 0:
                tasks_text += f" ({session.failed_tasks}✗)"

            # Created date
            created_text = session.created_at.strftime('%Y-%m-%d %H:%M')

            table.add_row(
                session.session_id[:12],
                session.name,
                status_text,
                progress_text,
                tasks_text,
                created_text,
            )

        console.print("\n")
        console.print(table)
        console.print(f"\nShowing {len(sessions[:limit])} of {len(sessions)} session(s)\n")

    except Exception as e:
        console.print(f"\n[red]Error listing sessions: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("pause")
def pause_session(
    session_id: str = typer.Argument(..., help="Session ID to pause"),
):
    """Pause a running session."""
    try:
        session_manager = SessionManager()

        session = session_manager.get_session(session_id)
        if not session:
            console.print(f"[red]Session not found: {session_id}[/red]")
            raise typer.Exit(1)

        if session.status != SessionStatus.RUNNING:
            console.print(f"[yellow]Session is not running (status: {session.status.value})[/yellow]")
            return

        session_manager.pause_session(session_id)
        console.print(f"[green]✓ Session paused: {session.name}[/green]")

    except Exception as e:
        console.print(f"\n[red]Error pausing session: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("resume")
def resume_session(
    session_id: str = typer.Argument(..., help="Session ID to resume"),
    worker_id: Optional[str] = typer.Option(None, "--worker", "-w", help="Worker ID"),
):
    """Resume a paused session."""
    try:
        session_manager = SessionManager()

        session = session_manager.get_session(session_id)
        if not session:
            console.print(f"[red]Session not found: {session_id}[/red]")
            raise typer.Exit(1)

        if session.status != SessionStatus.PAUSED:
            console.print(f"[yellow]Session is not paused (status: {session.status.value})[/yellow]")
            return

        session_manager.start_session(session_id, worker_id=worker_id)
        console.print(f"[green]✓ Session resumed: {session.name}[/green]")

    except Exception as e:
        console.print(f"\n[red]Error resuming session: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("cancel")
def cancel_session(
    session_id: str = typer.Argument(..., help="Session ID to cancel"),
    force: bool = typer.Option(False, "--force", "-f", help="Force cancellation"),
):
    """Cancel a session."""
    try:
        session_manager = SessionManager()

        session = session_manager.get_session(session_id)
        if not session:
            console.print(f"[red]Session not found: {session_id}[/red]")
            raise typer.Exit(1)

        if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
            console.print(f"[yellow]Session already finished (status: {session.status.value})[/yellow]")
            return

        if not force:
            confirm = typer.confirm(f"Cancel session '{session.name}'?")
            if not confirm:
                console.print("[yellow]Cancelled[/yellow]")
                return

        session_manager.cancel_session(session_id)
        console.print(f"[green]✓ Session cancelled: {session.name}[/green]")

    except Exception as e:
        console.print(f"\n[red]Error cancelling session: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("dashboard")
def show_dashboard(
    duration: Optional[int] = typer.Option(None, "--duration", "-d", help="Duration in seconds"),
    compact: bool = typer.Option(False, "--compact", "-c", help="Compact mode"),
    refresh: float = typer.Option(0.5, "--refresh", "-r", help="Refresh rate in seconds"),
):
    """Show live dashboard."""
    try:
        session_manager = SessionManager()
        worker_coordinator = WorkerCoordinator()

        config = DashboardConfig(
            refresh_rate=refresh,
            compact_mode=compact,
        )

        dashboard = LiveDashboard(session_manager, worker_coordinator, config)

        console.print("[yellow]Starting live dashboard... (Ctrl+C to exit)[/yellow]\n")

        try:
            dashboard.start_live(duration=duration)
        except KeyboardInterrupt:
            console.print("\n\n[yellow]Dashboard stopped[/yellow]")

    except Exception as e:
        console.print(f"\n[red]Error showing dashboard: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("workers")
def list_workers(
    status: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status"),
    limit: int = typer.Option(50, "--limit", "-l", help="Maximum workers to show"),
):
    """List workers."""
    try:
        worker_coordinator = WorkerCoordinator()

        # Parse status filter
        status_filter = None
        if status:
            try:
                status_filter = WorkerStatus(status.lower())
            except ValueError:
                console.print(f"[red]Invalid status: {status}[/red]")
                console.print("Valid statuses: idle, busy, offline, error")
                raise typer.Exit(1)

        # Get workers
        workers = worker_coordinator.list_workers(status=status_filter)

        if not workers:
            console.print("[yellow]No workers found[/yellow]")
            return

        # Create table
        table = Table(title="Worker Pool", show_header=True, header_style="bold cyan")

        table.add_column("ID", style="dim", width=12)
        table.add_column("Status", width=10)
        table.add_column("Session", width=12)
        table.add_column("Current Task", width=15)
        table.add_column("Completed", justify="right")
        table.add_column("Failed", justify="right")
        table.add_column("Last Heartbeat", width=15)

        for worker in workers[:limit]:
            # Status with color
            status_colors = {
                WorkerStatus.IDLE: "green",
                WorkerStatus.BUSY: "yellow",
                WorkerStatus.OFFLINE: "red",
                WorkerStatus.ERROR: "red bold",
            }
            status_color = status_colors.get(worker.status, "white")
            status_text = f"[{status_color}]{worker.status.value.upper()}[/{status_color}]"

            # Session ID
            session_text = worker.session_id[:12] if worker.session_id else "-"

            # Current task
            task_text = worker.current_task[:15] if worker.current_task else "-"

            # Last heartbeat
            from datetime import datetime
            if worker.last_heartbeat:
                time_ago = (datetime.now() - worker.last_heartbeat).total_seconds()
                if time_ago < 10:
                    hb_text = "just now"
                elif time_ago < 60:
                    hb_text = f"{int(time_ago)}s ago"
                elif time_ago < 3600:
                    hb_text = f"{int(time_ago/60)}m ago"
                else:
                    hb_text = f"{int(time_ago/3600)}h ago"
            else:
                hb_text = "never"

            table.add_row(
                worker.worker_id[:12],
                status_text,
                session_text,
                task_text,
                str(worker.tasks_completed),
                str(worker.tasks_failed),
                hb_text,
            )

        console.print("\n")
        console.print(table)
        console.print(f"\nShowing {len(workers[:limit])} of {len(workers)} worker(s)\n")

        # Show statistics
        load_dist = worker_coordinator.get_load_distribution()
        console.print(f"[bold]Statistics:[/bold]")
        console.print(f"  Utilization: {load_dist['utilization']:.1f}%")
        console.print(f"  Queued Tasks: {load_dist['queued_tasks']}")
        console.print(f"  Total Completed: {load_dist['total_completed']}")
        console.print(f"  Total Failed: {load_dist['total_failed']}")
        console.print()

    except Exception as e:
        console.print(f"\n[red]Error listing workers: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("summary")
def show_summary():
    """Show brief system summary."""
    try:
        session_manager = SessionManager()
        worker_coordinator = WorkerCoordinator()

        dashboard = LiveDashboard(session_manager, worker_coordinator)
        dashboard.print_summary()

    except Exception as e:
        console.print(f"\n[red]Error showing summary: {e}[/red]")
        raise typer.Exit(1)


@parallel_app.command("cleanup")
def cleanup_sessions(
    days: int = typer.Option(7, "--days", "-d", help="Delete sessions older than N days"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Show what would be deleted"),
):
    """Clean up old completed/failed sessions."""
    try:
        session_manager = SessionManager()

        from datetime import datetime, timedelta
        cutoff = datetime.now() - timedelta(days=days)

        # Find sessions to delete
        to_delete = []
        for session_id, session in session_manager.sessions.items():
            if session.status in [SessionStatus.COMPLETED, SessionStatus.FAILED, SessionStatus.CANCELLED]:
                if session.completed_at and session.completed_at < cutoff:
                    to_delete.append((session_id, session))

        if not to_delete:
            console.print(f"[yellow]No sessions older than {days} days found[/yellow]")
            return

        console.print(f"\n[bold]Sessions to delete (older than {days} days):[/bold]\n")
        for session_id, session in to_delete:
            console.print(f"  • {session.name} ({session.status.value}) - {session.completed_at.strftime('%Y-%m-%d')}")

        console.print(f"\nTotal: {len(to_delete)} session(s)")

        if dry_run:
            console.print("\n[yellow]Dry run - no sessions deleted[/yellow]")
            return

        confirm = typer.confirm(f"\nDelete {len(to_delete)} session(s)?")
        if not confirm:
            console.print("[yellow]Cancelled[/yellow]")
            return

        session_manager.cleanup_old_sessions(days=days)
        console.print(f"\n[green]✓ Deleted {len(to_delete)} session(s)[/green]")

    except Exception as e:
        console.print(f"\n[red]Error cleaning up sessions: {e}[/red]")
        raise typer.Exit(1)
