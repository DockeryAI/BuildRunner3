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

from core.dashboard_views import (
    DashboardScanner,
    DashboardViews,
    ExecutionMonitorView,
    PlanReviewView,
    ProjectStatus,
)


console = Console()


@click.group()
def dashboard():
    """Multi-repo dashboard commands"""
    pass


@dashboard.command()
@click.option(
    "--path",
    "-p",
    type=click.Path(exists=True),
    default=None,
    help="Root directory to scan for projects (default: current directory)",
)
@click.option("--watch", "-w", is_flag=True, help="Auto-refresh dashboard every 30 seconds")
@click.option(
    "--view",
    "-v",
    type=click.Choice(["overview", "alerts", "timeline", "plan", "exec"]),
    default="overview",
    help="Dashboard view to display",
)
@click.option(
    "--detail", "-d", type=str, default=None, help="Show detailed view for specific project"
)
@click.option("--history", is_flag=True, help="Show past plans table (with --view plan)")
@click.option("--context", is_flag=True, help="Show BUILD spec phase alongside plan (with --view plan)")
@click.option("--diff", "show_diff", is_flag=True, help="Show plan comparison diff (with --view plan)")
def show(path: Optional[str], watch: bool, view: str, detail: Optional[str], history: bool = False, context: bool = False, show_diff: bool = False):
    """
    Show multi-repo dashboard.

    Scans for all BuildRunner projects and displays aggregated status.

    Examples:
        br dashboard show
        br dashboard show --path /Users/me/projects
        br dashboard show --watch
        br dashboard show --detail MyProject
        br dashboard show --view alerts
        br dashboard show --view plan
        br dashboard show --view plan --history
        br dashboard show --view plan --context
        br dashboard show --view plan --diff
        br dashboard show --view exec
    """
    root_path = Path(path) if path else Path.cwd()

    # Plan view is special — doesn't need project scanning
    if view == "plan":
        output = _render_plan_review(root_path, history, context, show_diff)
        console.print(output)
        return

    # Exec view reads lock directory progress — no project scanning needed
    if view == "exec":
        output = _render_exec_monitor(root_path)
        console.print(output)
        return

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
            border_style="yellow",
        )

    views = DashboardViews(projects)

    # Generate requested view
    if detail:
        content = _render_detail_view(views, detail)
    elif view == "alerts":
        content = _render_alerts_view(views)
    elif view == "timeline":
        content = _render_timeline_view(views)
    else:  # overview
        content = _render_overview(views)

    return Panel(
        content,
        title="📊 BuildRunner Multi-Repo Dashboard",
        border_style="blue",
        subtitle=f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
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

    for project in overview["projects"]:
        # Status emoji
        status_emoji = (
            "✅"
            if project.completion_percentage == 100
            else "🔨" if project.in_progress > 0 else "📋"
        )

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
            updated,
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

    project = detail["project"]

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
    for project in alerts["stale"]:
        days = (time.time() - project.last_updated.timestamp()) / 86400
        table.add_row("🕐 Stale", project.name, f"No activity for {int(days)} days")

    # Blocked projects
    for project in alerts["blocked"]:
        table.add_row("🚫 Blocked", project.name, f"{len(project.blockers)} blocker(s)")

    # No progress
    for project in alerts["no_progress"]:
        table.add_row(
            "⏸️  No Progress", project.name, f"{project.planned} features planned, 0 in progress"
        )

    # High WIP
    for project in alerts["high_wip"]:
        table.add_row(
            "⚠️  High WIP", project.name, f"{project.in_progress} features in progress (>5)"
        )

    if table.row_count == 0:
        return "[green]✅ No alerts - all projects healthy![/green]"

    return table


def _render_timeline_view(views: DashboardViews) -> Table:
    """Render timeline view"""
    timeline = views.get_timeline_data(days=30)

    table = Table(
        title="📅 Recent Activity (Last 30 Days)", show_header=True, header_style="bold cyan"
    )
    table.add_column("Date", style="cyan", no_wrap=True)
    table.add_column("Project", style="white")
    table.add_column("Event", style="green")
    table.add_column("Progress", justify="right")

    for event in timeline[:20]:  # Limit to 20 most recent
        date_str = event["timestamp"].strftime("%Y-%m-%d %H:%M")
        table.add_row(date_str, event["project"], event["event"], f"{event['completion']}%")

    if table.row_count == 0:
        return "[yellow]No recent activity in the last 30 days[/yellow]"

    return table


# Helper for grouping renderables
from rich.console import Group


def _render_plan_review(root_path: Path, history: bool = False, context: bool = False, show_diff: bool = False) -> Panel:
    """Render the plan review dashboard — the human verification gate."""
    review = PlanReviewView(root_path)

    if not review.plan_file:
        return Panel(
            "[yellow]No plan files found.[/yellow]\n\n"
            f"Searched in: {root_path / '.buildrunner' / 'plans'}\n"
            "Hint: Run /setlist to generate a plan first.",
            title="Plan Review",
            border_style="yellow",
        )

    if history:
        return _render_plan_history(review)

    renderables = []

    # --- BUILD spec context panel (--context) ---
    if context:
        spec_data = review.get_build_spec_context()
        if spec_data:
            spec_text = Text()
            spec_text.append(f"Phase {spec_data['phase_num']}: ", style="bold cyan")
            spec_text.append(spec_data["title"], style="bold")
            spec_text.append(f"  ({spec_data['build_file']})\n", style="dim")

            if spec_data.get("deliverables"):
                spec_text.append("\nDeliverables:\n", style="bold")
                for d in spec_data["deliverables"]:
                    spec_text.append(f"  - {d}\n", style="white")

            if spec_data.get("success_criteria"):
                spec_text.append("\nSuccess Criteria: ", style="bold green")
                spec_text.append(spec_data["success_criteria"], style="green")

            renderables.append(
                Panel(
                    spec_text,
                    title="BUILD Spec Context",
                    border_style="magenta",
                    padding=(0, 1),
                )
            )

    # --- Plan comparison diff (--diff) ---
    if show_diff:
        diff_data = review.get_plan_diff()
        if diff_data.get("has_previous"):
            diff_text = Text()
            diff_text.append(f"Compared with: {diff_data.get('previous_file', '')}\n\n", style="dim")

            if diff_data["added"]:
                for task in diff_data["added"]:
                    diff_text.append(f"+ [{task['id']}] ", style="bold green")
                    diff_text.append(f"{task['what']}\n", style="green")

            if diff_data["removed"]:
                for task in diff_data["removed"]:
                    diff_text.append(f"- [{task['id']}] ", style="bold red")
                    diff_text.append(f"{task['what']}\n", style="red")

            if diff_data["modified"]:
                for mod in diff_data["modified"]:
                    diff_text.append(f"~ [{mod['id']}] ", style="bold yellow")
                    diff_text.append(f"{mod['old_what']}", style="dim yellow")
                    diff_text.append(" -> ", style="yellow")
                    diff_text.append(f"{mod['new_what']}\n", style="yellow")

            if not diff_data["added"] and not diff_data["removed"] and not diff_data["modified"]:
                diff_text.append("No changes detected.", style="dim")

            renderables.append(
                Panel(
                    diff_text,
                    title="Plan Diff",
                    border_style="yellow",
                    padding=(0, 1),
                )
            )
        elif show_diff:
            renderables.append(
                Panel(
                    "[dim]No previous plan version found for comparison.[/dim]",
                    title="Plan Diff",
                    border_style="dim",
                    padding=(0, 1),
                )
            )

    # --- Code health warning bar ---
    health = review.get_code_health_data()
    low_health = {f: s for f, s in health.items() if s < 9.5}
    if low_health:
        warnings = ", ".join(f"{f} ({s}/10)" for f, s in low_health.items())
        renderables.append(
            Panel(
                f"[bold yellow]Code health warning:[/bold yellow] {warnings}",
                border_style="yellow",
                padding=(0, 1),
            )
        )

    # --- Task table ---
    tasks = review.get_task_table_data()
    if tasks:
        task_table = Table(
            title="Tasks",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
        )
        task_table.add_column("#", style="cyan", no_wrap=True, width=5)
        task_table.add_column("WHAT", style="white", ratio=3)
        task_table.add_column("WHY", style="dim", ratio=2)
        task_table.add_column("VERIFY", style="green", ratio=2)

        for task in tasks:
            task_table.add_row(
                task["id"],
                task["what"],
                task["why"],
                task["verify"],
            )
        renderables.append(task_table)

    # --- Dependency diagram (rendered as Rich Tree if present) ---
    dep_nodes = review.get_dependency_diagram()
    if dep_nodes:
        from rich.tree import Tree
        dep_tree = Tree("[bold]Dependencies[/bold]")
        # Build lookup for which tasks have deps
        dep_map = {n["task"]: n["depends_on"] for n in dep_nodes}
        roots = [n["task"] for n in dep_nodes if not n["depends_on"]]
        non_roots = [n["task"] for n in dep_nodes if n["depends_on"]]

        # Add roots first, then dependents
        tree_nodes = {}
        for root_id in roots:
            tree_nodes[root_id] = dep_tree.add(f"[cyan]{root_id}[/cyan]")
        for task_id in non_roots:
            deps = dep_map.get(task_id, [])
            # Attach to first dependency that has a tree node, or to root
            parent = None
            for d in deps:
                if d in tree_nodes:
                    parent = tree_nodes[d]
                    break
            if parent is None:
                parent = dep_tree
            label = f"[cyan]{task_id}[/cyan] [dim](depends on {', '.join(deps)})[/dim]"
            tree_nodes[task_id] = parent.add(label)

        renderables.append(
            Panel(dep_tree, border_style="cyan", padding=(0, 1))
        )

    # --- Adversarial findings panel ---
    findings = review.get_adversarial_data()
    if findings:
        findings_text = Text()
        for finding in findings:
            severity = finding.get("severity", "note")
            text = finding.get("finding", "")
            if severity == "blocker":
                findings_text.append("BLOCKER ", style="bold red")
                findings_text.append(f"{text}\n", style="red")
            elif severity == "warning":
                findings_text.append("WARNING ", style="bold yellow")
                findings_text.append(f"{text}\n", style="yellow")
            else:
                findings_text.append("NOTE    ", style="dim")
                findings_text.append(f"{text}\n", style="dim")

        renderables.append(
            Panel(
                findings_text,
                title="Adversarial Findings",
                border_style="red" if any(f.get("severity") == "blocker" for f in findings) else "yellow",
                padding=(0, 1),
            )
        )

    # --- Test baseline panel ---
    try:
        baseline = review.get_test_baseline_data()
        if baseline:
            test_table = Table(
                title="Test Baseline",
                show_header=True,
                header_style="bold cyan",
                border_style="cyan",
            )
            test_table.add_column("Source File", style="white")
            test_table.add_column("Test File", style="cyan")
            test_table.add_column("Status", justify="center")

            for source_file, test_info in baseline.items():
                if isinstance(test_info, list):
                    for t in test_info:
                        status = "[green]PASS[/green]" if t.get("status") == "pass" else "[red]FAIL[/red]"
                        test_table.add_row(source_file, t.get("file", ""), status)
                elif isinstance(test_info, dict):
                    status = "[green]PASS[/green]" if test_info.get("status") == "pass" else "[red]FAIL[/red]"
                    test_table.add_row(source_file, test_info.get("file", ""), status)

            if test_table.row_count > 0:
                renderables.append(test_table)
    except Exception:
        pass  # Walter offline — skip

    # --- Historical outcomes panel ---
    try:
        history_data = review.get_historical_data()
        if history_data:
            hist_table = Table(
                title="Similar Past Plans",
                show_header=True,
                header_style="bold green",
                border_style="green",
            )
            hist_table.add_column("Plan", style="white", ratio=3)
            hist_table.add_column("Outcome", justify="center", width=8)
            hist_table.add_column("Accuracy", justify="right", width=10)
            hist_table.add_column("Lesson", style="dim", ratio=2)

            for plan in history_data[:3]:
                plan_text = str(plan.get("plan_text", ""))[:60]
                outcome = plan.get("outcome", "?")
                outcome_style = "green" if outcome == "pass" else "red" if outcome == "fail" else "yellow"
                accuracy = plan.get("accuracy_pct")
                accuracy_str = f"{accuracy:.0f}%" if accuracy else "-"
                drift = str(plan.get("drift_notes", ""))[:40] or "-"

                hist_table.add_row(
                    plan_text,
                    f"[{outcome_style}]{outcome}[/{outcome_style}]",
                    accuracy_str,
                    drift,
                )

            if hist_table.row_count > 0:
                renderables.append(hist_table)
    except Exception:
        pass  # Lockwood offline — skip

    # --- Actions bar ---
    actions = review.get_actions()
    action_text = Text()
    action_text.append("Actions: ", style="bold")
    for i, action in enumerate(actions):
        if i > 0:
            action_text.append(" | ")
        action_text.append(f"[{action['shortcut']}] ", style="bold cyan")
        action_text.append(action["name"].capitalize(), style="white")
    renderables.append(
        Panel(action_text, border_style="blue", padding=(0, 1))
    )

    plan_name = review.plan_file.name if review.plan_file else "unknown"
    return Panel(
        Group(*renderables),
        title=f"Plan Review: {plan_name}",
        border_style="blue",
        subtitle=f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    )


def _render_exec_monitor(root_path: Path) -> Panel:
    """Render the execution monitor dashboard — live task progress during /begin."""
    monitor = ExecutionMonitorView(root_path)
    data = monitor.get_execution_data()

    if not data.get("phase"):
        return Panel(
            "[yellow]No active execution found.[/yellow]\n\n"
            "Hint: This view shows progress during /begin execution.\n"
            "Run /begin with a setlist plan to see live progress.",
            title="Execution Monitor",
            border_style="yellow",
        )

    renderables = []

    # --- Phase header ---
    phase_text = Text()
    phase_text.append(f"Phase {data['phase']}: ", style="bold cyan")
    phase_text.append(data.get("phase_name", ""), style="bold")
    phase_text.append(f"  [{data.get('step_label', '')}]", style="dim")
    renderables.append(phase_text)
    renderables.append(Text(""))

    # --- Session metrics bar ---
    metrics = data["session_metrics"]
    metrics_text = Text()

    # Interaction count
    i_color = {"normal": "green", "yellow": "yellow", "red": "red"}[metrics["interaction_color"]]
    metrics_text.append("Interactions: ", style="bold")
    metrics_text.append(
        f"{metrics['interaction_count']}/{metrics['interaction_limit']}",
        style=i_color,
    )
    metrics_text.append("  ")

    # Elapsed time
    t_color = {"normal": "green", "yellow": "yellow", "red": "red"}[metrics["time_color"]]
    metrics_text.append("Time: ", style="bold")
    metrics_text.append(
        f"{metrics['elapsed_minutes']:.0f}/{metrics['time_limit']}m",
        style=t_color,
    )
    metrics_text.append("  ")

    # Compaction count
    comp = metrics["compaction_count"]
    metrics_text.append("Compactions: ", style="bold")
    metrics_text.append(str(comp), style="red" if comp > 0 else "green")

    renderables.append(
        Panel(metrics_text, border_style="cyan", padding=(0, 1), title="Session")
    )

    # --- Task progress table ---
    tasks = data.get("tasks", [])
    if tasks:
        task_table = Table(
            title=f"Tasks: {data['tasks_done']}/{data['tasks_total']}",
            show_header=True,
            header_style="bold magenta",
            border_style="blue",
        )
        task_table.add_column("#", style="cyan", no_wrap=True, width=5)
        task_table.add_column("Task", style="white", ratio=3)
        task_table.add_column("Verify", justify="center", width=8)

        for task in tasks:
            result = task.get("verify_result", "pending")
            if result == "pass":
                verify_display = "[green]PASS[/green]"
            elif result == "fail":
                verify_display = "[red]FAIL[/red]"
            else:
                verify_display = "[dim]...[/dim]"

            # Highlight current task
            task_style = "bold white" if task["what"] == data.get("current_task") else "white"
            task_table.add_row(
                task["id"],
                Text(task["what"][:60], style=task_style),
                verify_display,
            )

        renderables.append(task_table)

    # --- Consecutive failures warning ---
    failures = data.get("consecutive_failures", 0)
    if failures > 0:
        fail_style = "red" if failures >= 2 else "yellow"
        renderables.append(
            Panel(
                f"[bold {fail_style}]Consecutive failures: {failures}[/bold {fail_style}]"
                + (" — circuit breaker triggered" if failures >= 2 else ""),
                border_style=fail_style,
                padding=(0, 1),
            )
        )

    # --- Drift indicator ---
    drift = data.get("drift", {})
    drift_pct = drift.get("drift_pct", 0)
    if drift_pct > 0:
        drift_color = "red" if drift_pct > 30 else "yellow" if drift_pct > 10 else "dim"
        drift_text = Text()
        drift_text.append(f"Drift: {drift_pct:.0f}%", style=f"bold {drift_color}")
        if drift.get("files_unplanned"):
            drift_text.append(f"  Unplanned: {', '.join(drift['files_unplanned'])}", style="dim")
        if drift.get("files_missed"):
            drift_text.append(f"  Missed: {', '.join(drift['files_missed'])}", style="dim")
        renderables.append(
            Panel(drift_text, border_style=drift_color, padding=(0, 1), title="Drift")
        )

    # --- Affected files ---
    affected = data.get("affected_files", [])
    if affected:
        file_table = Table(
            title="Affected Files",
            show_header=True,
            header_style="bold cyan",
            border_style="cyan",
        )
        file_table.add_column("File", style="white", ratio=3)
        file_table.add_column("Exists", justify="center", width=7)
        file_table.add_column("Lines", justify="right", width=7)
        file_table.add_column("Modified", style="dim", width=20)

        for f in affected:
            exists_display = "[green]yes[/green]" if f["exists"] else "[red]NO[/red]"
            lines_display = str(f["lines"]) if f["exists"] else "-"
            modified_display = f["modified"][:19] if f.get("modified") else "-"
            file_table.add_row(f["path"], exists_display, lines_display, modified_display)

        renderables.append(file_table)

    # --- Errors/warnings ---
    errors = data.get("errors", [])
    if errors:
        err_text = Text()
        for err in errors:
            err_text.append(f"ERROR: {err}\n", style="red")
        renderables.append(Panel(err_text, border_style="red", padding=(0, 1)))

    return Panel(
        Group(*renderables),
        title=f"Execution Monitor: Phase {data['phase']}",
        border_style="blue",
        subtitle=f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    )


def _render_plan_history(review: PlanReviewView) -> Panel:
    """Render historical plans table."""
    history_data = review.get_historical_data()

    if not history_data:
        return Panel(
            "[yellow]No historical plans found.[/yellow]\n"
            "Plans are recorded after execution via Lockwood.",
            title="Plan History",
            border_style="yellow",
        )

    table = Table(
        title="Past Plans",
        show_header=True,
        header_style="bold green",
    )
    table.add_column("Plan", style="white", ratio=3)
    table.add_column("Outcome", justify="center", width=8)
    table.add_column("Accuracy", justify="right", width=10)
    table.add_column("Lesson", style="dim", ratio=2)

    for plan in history_data:
        plan_text = str(plan.get("plan_text", ""))[:80]
        outcome = plan.get("outcome", "?")
        outcome_style = "green" if outcome == "pass" else "red" if outcome == "fail" else "yellow"
        accuracy = plan.get("accuracy_pct")
        accuracy_str = f"{accuracy:.0f}%" if accuracy else "-"
        drift = str(plan.get("drift_notes", ""))[:60] or "-"

        table.add_row(
            plan_text,
            f"[{outcome_style}]{outcome}[/{outcome_style}]",
            accuracy_str,
            drift,
        )

    return Panel(
        table,
        title="Plan History",
        border_style="green",
        subtitle=f"Last updated: {time.strftime('%Y-%m-%d %H:%M:%S')}",
    )


if __name__ == "__main__":
    dashboard()
