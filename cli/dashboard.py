"""
Dashboard CLI Command for BuildRunner 3.0

Terminal UI for viewing status across multiple BuildRunner projects.
Because staring at colorful tables makes failure more bearable.
"""

import time
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, BarColumn, TextColumn, TaskProgressColumn
from rich.panel import Panel
from rich.layout import Layout
from rich.live import Live
from rich.text import Text

from core.dashboard_views import DashboardScanner, DashboardViews, ProjectStatus


console = Console()


@click.group()
def dashboard():
    """Multi-repo dashboard commands"""
    pass


@dashboard.command()
@click.option('--path', '-p', type=click.Path(exists=True), default=None,
              help='Root directory to scan for projects (default: current directory)')
@click.option('--watch', '-w', is_flag=True,
              help='Auto-refresh dashboard every 30 seconds')
@click.option('--view', '-v', type=click.Choice(['overview', 'alerts', 'timeline']),
              default='overview',
              help='Dashboard view to display')
@click.option('--detail', '-d', type=str, default=None,
              help='Show detailed view for specific project')
def show(path: Optional[str], watch: bool, view: str, detail: Optional[str]):
    """
    Show multi-repo dashboard.

    Scans for all BuildRunner projects and displays aggregated status.

    Examples:
        br dashboard show
        br dashboard show --path /Users/me/projects
        br dashboard show --watch
        br dashboard show --detail MyProject
        br dashboard show --view alerts
    """
    root_path = Path(path) if path else Path.cwd()

    if watch:
        # Auto-refresh mode
        try:
            with Live(console=console, refresh_per_second=0.5) as live:
                while True:
                    output = _generate_dashboard(root_path, view, detail)
                    live.update(output)
                    time.sleep(30)
        except KeyboardInterrupt:
            console.print("\n👋 Dashboard closed")
    else:
        # Single render
        output = _generate_dashboard(root_path, view, detail)
        console.print(output)


def _generate_dashboard(root_path: Path, view: str, detail: Optional[str]) -> Panel:
    """Generate dashboard output"""
    # Scan for projects
    with console.status("[bold green]Scanning for projects..."):
        scanner = DashboardScanner(root_path)
        projects = scanner.discover_projects()

    if not projects:
        return Panel(
            "[yellow]No BuildRunner projects found.[/yellow]\n\n"
            f"Searched in: {root_path}\n"
            "Hint: Make sure projects have .buildrunner/features.json",
            title="📊 BuildRunner Dashboard",
            border_style="yellow"
        )

    views = DashboardViews(projects)

    # Generate requested view
    if detail:
        content = _render_detail_view(views, detail)
    elif view == 'alerts':
        content = _render_alerts_view(views)
    elif view == 'timeline':
        content = _render_timeline_view(views)
    else:  # overview
        content = _render_overview(views)

    return Panel(
        content,
        title="📊 BuildRunner Multi-Repo Dashboard",
        border_style="blue",
        subtitle=f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}"
    )


def _render_overview(views: DashboardViews) -> Table:
    """Render overview table"""
    overview = views.get_overview_data()

    # Summary stats
    summary = Text()
    summary.append(f"Total Projects: ", style="bold")
    summary.append(f"{overview['total_projects']}\n")
    summary.append(f"Overall Completion: ", style="bold")
    summary.append(f"{overview['overall_completion']}% ", style="green")
    summary.append(f"({overview['total_completed']}/{overview['total_features']} features)\n")
    summary.append(f"Active: ", style="bold")
    summary.append(f"{overview['active_projects']} ", style="cyan")
    summary.append(f"Stale: ", style="bold")
    summary.append(f"{overview['stale_projects']} ", style="yellow")
    summary.append(f"Blocked: ", style="bold")
    summary.append(f"{overview['blocked_projects']}\n", style="red")

    # Project table
    table = Table(title="Projects Overview", show_header=True, header_style="bold magenta")
    table.add_column("Project", style="cyan", no_wrap=True)
    table.add_column("Status", justify="center")
    table.add_column("Progress", justify="right")
    table.add_column("Features", justify="center")
    table.add_column("Active", justify="center")
    table.add_column("Health", justify="center")
    table.add_column("Last Updated", justify="right")

    for project in overview['projects']:
        # Status emoji
        status_emoji = "✅" if project.completion_percentage == 100 else "🔨" if project.in_progress > 0 else "📋"

        # Progress bar
        progress_text = f"{project.completion_percentage}%"
        if project.completion_percentage >= 75:
            progress_color = "green"
        elif project.completion_percentage >= 50:
            progress_color = "yellow"
        else:
            progress_color = "red"

        # Features summary
        features_text = f"{project.completed}/{project.total_features}"

        # Active features count
        active_text = str(project.in_progress) if project.in_progress > 0 else "-"

        # Health indicator
        health = project.health_status
        if health == "healthy":
            health_display = "[green]●[/green]"
        elif health == "warning":
            health_display = "[yellow]●[/yellow]"
        else:
            health_display = "[red]●[/red]"

        # Days since update
        days_ago = (time.time() - project.last_updated.timestamp()) / 86400
        if days_ago < 1:
            updated = "Today"
        elif days_ago < 2:
            updated = "Yesterday"
        else:
            updated = f"{int(days_ago)}d ago"

        if project.is_stale:
            updated = f"[yellow]{updated}[/yellow]"

        table.add_row(
            project.name,
            status_emoji,
            f"[{progress_color}]{progress_text}[/{progress_color}]",
            features_text,
            active_text,
            health_display,
            updated
        )

    # Combine summary and table
    layout = Text()
    layout.append_text(summary)
    layout.append("\n")

    return Group(layout, table)


def _render_detail_view(views: DashboardViews, project_name: str) -> str:
    """Render detailed view for a single project"""
    detail = views.get_detail_data(project_name)

    if not detail:
        return f"[red]Project '{project_name}' not found[/red]"

    project = detail['project']

    # Build detail output
    output = f"""[bold cyan]{project.name}[/bold cyan]
[dim]{project.path}[/dim]

📊 Status: {project.status}
📦 Version: {project.version}
📈 Progress: {project.completion_percentage}% ({project.completed}/{project.total_features} features)

Features by Status:
  ✅ Completed: {detail['features_by_status']['completed']}
  🔨 In Progress: {detail['features_by_status']['in_progress']}
  📋 Planned: {detail['features_by_status']['planned']}

Health: {"[green]Healthy[/green]" if detail['health'] == 'healthy' else "[yellow]Warning[/yellow]" if detail['health'] == 'warning' else "[red]Critical[/red]"}
Last Updated: {detail['days_since_update']} days ago
"""

    if project.active_features:
        output += "\n[bold]Active Features:[/bold]\n"
        for feature in project.active_features:
            output += f"  • {feature}\n"

    if project.blockers:
        output += "\n[bold red]Blockers:[/bold red]\n"
        for blocker in project.blockers:
            output += f"  ⚠️  {blocker}\n"

    return output


def _render_alerts_view(views: DashboardViews) -> Table:
    """Render alerts view"""
    alerts = views.get_alerts_data()

    table = Table(title="⚠️  Alerts", show_header=True, header_style="bold yellow")
    table.add_column("Type", style="yellow", no_wrap=True)
    table.add_column("Project", style="cyan")
    table.add_column("Details", style="white")

    # Stale projects
    for project in alerts['stale']:
        days = (time.time() - project.last_updated.timestamp()) / 86400
        table.add_row(
            "🕐 Stale",
            project.name,
            f"No activity for {int(days)} days"
        )

    # Blocked projects
    for project in alerts['blocked']:
        table.add_row(
            "🚫 Blocked",
            project.name,
            f"{len(project.blockers)} blocker(s)"
        )

    # No progress
    for project in alerts['no_progress']:
        table.add_row(
            "⏸️  No Progress",
            project.name,
            f"{project.planned} features planned, 0 in progress"
        )

    # High WIP
    for project in alerts['high_wip']:
        table.add_row(
            "⚠️  High WIP",
            project.name,
            f"{project.in_progress} features in progress (>5)"
        )

    if table.row_count == 0:
        return "[green]✅ No alerts - all projects healthy![/green]"

    return table


def _render_timeline_view(views: DashboardViews) -> Table:
    """Render timeline view"""
    timeline = views.get_timeline_data(days=30)

    table = Table(title="📅 Recent Activity (Last 30 Days)", show_header=True, header_style="bold cyan")
    table.add_column("Date", style="cyan", no_wrap=True)
    table.add_column("Project", style="white")
    table.add_column("Event", style="green")
    table.add_column("Progress", justify="right")

    for event in timeline[:20]:  # Limit to 20 most recent
        date_str = event['timestamp'].strftime("%Y-%m-%d %H:%M")
        table.add_row(
            date_str,
            event['project'],
            event['event'],
            f"{event['completion']}%"
        )

    if table.row_count == 0:
        return "[yellow]No recent activity in the last 30 days[/yellow]"

    return table


# Helper for grouping renderables
from rich.console import Group


if __name__ == "__main__":
    dashboard()
