"""
Live Dashboard - Real-time monitoring for parallel build sessions

Features:
- Multi-session progress display
- Worker status monitoring
- Real-time updates
- Rich console formatting
"""

from dataclasses import dataclass
from datetime import datetime
from typing import Dict, List, Optional
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.progress import Progress, SpinnerColumn, BarColumn, TextColumn, TimeRemainingColumn
from rich.text import Text

from .session_manager import SessionManager, SessionStatus
from .worker_coordinator import WorkerCoordinator, WorkerStatus


@dataclass
class DashboardConfig:
    """Dashboard configuration."""

    refresh_rate: float = 0.5  # seconds
    show_workers: bool = True
    show_sessions: bool = True
    show_tasks: bool = True
    compact_mode: bool = False
    max_sessions_display: int = 10
    max_workers_display: int = 20


class LiveDashboard:
    """Real-time dashboard for parallel build monitoring."""

    def __init__(
        self,
        session_manager: SessionManager,
        worker_coordinator: Optional[WorkerCoordinator] = None,
        config: Optional[DashboardConfig] = None,
    ):
        """
        Initialize live dashboard.

        Args:
            session_manager: Session manager instance
            worker_coordinator: Worker coordinator instance (optional)
            config: Dashboard configuration
        """
        self.session_manager = session_manager
        self.worker_coordinator = worker_coordinator
        self.config = config or DashboardConfig()
        self.console = Console()

    def render_sessions_table(self) -> Table:
        """
        Render sessions table.

        Returns:
            Rich table with session data
        """
        table = Table(title="Active Sessions", show_header=True, header_style="bold magenta")

        table.add_column("ID", style="dim", width=8)
        table.add_column("Name", style="cyan")
        table.add_column("Status", width=12)
        table.add_column("Progress", width=20)
        table.add_column("Tasks", justify="right")
        table.add_column("Worker", justify="center", width=8)

        sessions = self.session_manager.get_active_sessions()
        if not sessions:
            sessions = self.session_manager.list_sessions()[: self.config.max_sessions_display]

        for session in sessions[: self.config.max_sessions_display]:
            # Status with color
            status_color = {
                SessionStatus.CREATED: "yellow",
                SessionStatus.RUNNING: "green",
                SessionStatus.PAUSED: "yellow",
                SessionStatus.COMPLETED: "blue",
                SessionStatus.FAILED: "red",
                SessionStatus.CANCELLED: "dim",
            }
            status_text = Text(
                session.status.value.upper(), style=status_color.get(session.status, "white")
            )

            # Progress bar
            progress_percent = session.progress_percent
            bar_length = 15
            filled = int(bar_length * progress_percent / 100)
            bar = "█" * filled + "░" * (bar_length - filled)
            progress_text = f"{bar} {progress_percent:.0f}%"

            # Tasks
            tasks_text = f"{session.completed_tasks}/{session.total_tasks}"
            if session.failed_tasks > 0:
                tasks_text += f" ({session.failed_tasks} failed)"

            # Worker ID (short)
            worker_id_short = session.worker_id[:8] if session.worker_id else "-"

            table.add_row(
                session.session_id[:8],
                session.name,
                status_text,
                progress_text,
                tasks_text,
                worker_id_short,
            )

        return table

    def render_workers_table(self) -> Table:
        """
        Render workers table.

        Returns:
            Rich table with worker data
        """
        table = Table(title="Worker Pool", show_header=True, header_style="bold cyan")

        table.add_column("ID", style="dim", width=8)
        table.add_column("Status", width=10)
        table.add_column("Current Task", width=12)
        table.add_column("Session", width=8)
        table.add_column("Completed", justify="right")
        table.add_column("Failed", justify="right")
        table.add_column("Last HB", width=12)

        workers = self.worker_coordinator.list_workers()[: self.config.max_workers_display]

        for worker in workers:
            # Status with color
            status_color = {
                WorkerStatus.IDLE: "green",
                WorkerStatus.BUSY: "yellow",
                WorkerStatus.OFFLINE: "red",
                WorkerStatus.ERROR: "red bold",
            }
            status_text = Text(
                worker.status.value.upper(), style=status_color.get(worker.status, "white")
            )

            # Current task (short)
            task_text = worker.current_task[:12] if worker.current_task else "-"

            # Session ID (short)
            session_text = worker.session_id[:8] if worker.session_id else "-"

            # Last heartbeat
            if worker.last_heartbeat:
                time_ago = (datetime.now() - worker.last_heartbeat).total_seconds()
                if time_ago < 10:
                    hb_text = "just now"
                elif time_ago < 60:
                    hb_text = f"{int(time_ago)}s ago"
                else:
                    hb_text = f"{int(time_ago/60)}m ago"
            else:
                hb_text = "never"

            table.add_row(
                worker.worker_id[:8],
                status_text,
                task_text,
                session_text,
                str(worker.tasks_completed),
                str(worker.tasks_failed),
                hb_text,
            )

        return table

    def render_statistics_panel(self) -> Panel:
        """
        Render statistics panel.

        Returns:
            Rich panel with statistics
        """
        # Get load distribution
        load_dist = self.worker_coordinator.get_load_distribution()

        # Session stats
        active_sessions = len(self.session_manager.get_active_sessions())
        total_sessions = len(self.session_manager.sessions)

        # Build statistics text
        stats_lines = [
            f"Workers: {load_dist['idle_workers']} idle / {load_dist['busy_workers']} busy / {load_dist['offline_workers']} offline (Total: {load_dist['total_workers']})",
            f"Sessions: {active_sessions} active / {total_sessions} total",
            f"Queue: {load_dist['queued_tasks']} tasks waiting",
            f"Completed: {load_dist['total_completed']} tasks",
            f"Failed: {load_dist['total_failed']} tasks",
            f"Utilization: {load_dist['utilization']:.1f}%",
        ]

        stats_text = "\n".join(stats_lines)

        return Panel(
            stats_text,
            title="System Statistics",
            border_style="green",
            padding=(1, 2),
        )

    def render_tasks_panel(self) -> Panel:
        """
        Render active tasks panel.

        Returns:
            Rich panel with active tasks
        """
        # Get active sessions and their tasks
        active_sessions = self.session_manager.get_active_sessions()

        if not active_sessions:
            return Panel(
                "No active tasks",
                title="Active Tasks",
                border_style="yellow",
                padding=(1, 2),
            )

        task_lines = []
        for session in active_sessions[:5]:  # Show max 5 sessions
            # Get worker for this session
            worker = None
            if session.worker_id:
                worker = self.worker_coordinator.get_worker(session.worker_id)

            if worker and worker.current_task:
                task_lines.append(
                    f"[cyan]{session.name}[/cyan]: {worker.current_task} "
                    f"({session.completed_tasks}/{session.total_tasks})"
                )

        if not task_lines:
            task_lines.append("No tasks in progress")

        tasks_text = "\n".join(task_lines)

        return Panel(
            tasks_text,
            title="Active Tasks",
            border_style="yellow",
            padding=(1, 2),
        )

    def render_layout(self) -> Layout:
        """
        Render complete dashboard layout.

        Returns:
            Rich layout with all components
        """
        layout = Layout()

        # Create sections
        if self.config.compact_mode:
            layout.split_column(
                Layout(name="stats", size=5),
                Layout(name="main"),
            )
            layout["main"].split_row(
                Layout(name="sessions"),
                Layout(name="workers"),
            )
        else:
            layout.split_column(
                Layout(name="stats", size=5),
                Layout(name="tasks", size=7),
                Layout(name="main"),
            )
            layout["main"].split_row(
                Layout(name="sessions"),
                Layout(name="workers"),
            )
            layout["tasks"].update(self.render_tasks_panel())

        # Populate sections
        layout["stats"].update(self.render_statistics_panel())

        if self.config.show_sessions:
            layout["sessions"].update(self.render_sessions_table())

        if self.config.show_workers:
            layout["workers"].update(self.render_workers_table())

        return layout

    def render_snapshot(self) -> None:
        """Render a single snapshot of the dashboard."""
        self.console.clear()
        layout = self.render_layout()
        self.console.print(layout)

    def start_live(self, duration: Optional[float] = None) -> None:
        """
        Start live dashboard display.

        Args:
            duration: Optional duration in seconds (None = run indefinitely)
        """
        import time

        start_time = time.time()

        with Live(
            self.render_layout(),
            refresh_per_second=1 / self.config.refresh_rate,
            console=self.console,
            screen=True,
        ) as live:
            while True:
                # Check duration
                if duration and (time.time() - start_time) > duration:
                    break

                # Update display
                live.update(self.render_layout())

                # Sleep
                time.sleep(self.config.refresh_rate)

    def get_summary(self) -> Dict[str, any]:
        """
        Get dashboard summary data.

        Returns:
            Summary dictionary
        """
        active_sessions = self.session_manager.get_active_sessions()

        # Get worker stats if coordinator is available
        workers_data = {}
        tasks_data = {}
        if self.worker_coordinator:
            load_dist = self.worker_coordinator.get_load_distribution()
            workers_data = {
                "total": load_dist["total_workers"],
                "idle": load_dist["idle_workers"],
                "busy": load_dist["busy_workers"],
                "offline": load_dist["offline_workers"],
                "utilization": load_dist["utilization"],
            }
            tasks_data = {
                "queued": load_dist["queued_tasks"],
                "completed": load_dist["total_completed"],
                "failed": load_dist["total_failed"],
            }
        else:
            workers_data = {
                "total": 0,
                "idle": 0,
                "busy": 0,
                "offline": 0,
                "utilization": 0.0,
            }
            tasks_data = {
                "queued": 0,
                "completed": 0,
                "failed": 0,
            }

        return {
            "timestamp": datetime.now().isoformat(),
            "workers": workers_data,
            "sessions": {
                "active": len(active_sessions),
                "total": len(self.session_manager.sessions),
            },
            "tasks": tasks_data,
        }

    def get_dashboard_data(self) -> Dict[str, any]:
        """
        Get comprehensive dashboard data for API responses.

        Returns:
            Dashboard data dictionary
        """
        sessions = self.session_manager.get_all_sessions()
        workers = self.worker_coordinator.get_all_workers() if self.worker_coordinator else []

        return {
            "sessions": [
                {
                    "session_id": s.session_id,
                    "name": s.name,
                    "status": s.status.value,
                    "progress_percent": s.progress_percent,
                    "total_tasks": s.total_tasks,
                    "completed_tasks": s.completed_tasks,
                    "failed_tasks": s.failed_tasks,
                }
                for s in sessions
            ],
            "workers": [
                {
                    "worker_id": w.worker_id,
                    "status": w.status.value,
                    "current_session": w.current_session,
                    "tasks_completed": w.tasks_completed,
                    "tasks_failed": w.tasks_failed,
                }
                for w in workers
            ],
            "stats": self.get_summary(),
            "timeline": [],  # Placeholder for timeline data
        }

    def print_summary(self) -> None:
        """Print a brief summary to console."""
        summary = self.get_summary()

        self.console.print("\n[bold]Parallel Orchestration Summary[/bold]\n")

        # Workers
        workers = summary["workers"]
        self.console.print(
            f"Workers: [green]{workers['idle']} idle[/green] / "
            f"[yellow]{workers['busy']} busy[/yellow] / "
            f"[red]{workers['offline']} offline[/red] "
            f"(Total: {workers['total']}, Utilization: {workers['utilization']:.1f}%)"
        )

        # Sessions
        sessions = summary["sessions"]
        self.console.print(
            f"Sessions: [cyan]{sessions['active']} active[/cyan] / {sessions['total']} total"
        )

        # Tasks
        tasks = summary["tasks"]
        self.console.print(
            f"Tasks: [blue]{tasks['completed']} completed[/blue] / "
            f"[red]{tasks['failed']} failed[/red] / "
            f"[yellow]{tasks['queued']} queued[/yellow]"
        )

        self.console.print()
