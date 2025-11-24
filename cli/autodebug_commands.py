"""
Auto-Debug CLI Commands
Commands for running automated debugging pipeline
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.auto_debug import AutoDebugPipeline, RetryAnalyzer, SessionAnalyzer, ErrorContext
import json

app = typer.Typer(help="Automated post-build debugging commands")
console = Console()


@app.command("run")
def run_autodebug(
    files: list[str] = typer.Option(None, "--files", "-f", help="Specific files to check"),
    skip_deep: bool = typer.Option(False, "--skip-deep", help="Skip deep verification checks"),
    save: bool = typer.Option(True, "--save/--no-save", help="Save report to disk")
):
    """
    Run the automatic debugging pipeline

    Automatically detects what was changed and runs appropriate checks:
    - Immediate checks (< 5s): syntax, imports, basic compilation
    - Quick checks (< 30s): unit tests, linting, type checking
    - Deep checks (< 2min): full test suite, gap analysis, quality scan
    """
    console.print("\n[bold cyan]🔍 BuildRunner Auto-Debug Pipeline[/bold cyan]\n")

    try:
        # Initialize pipeline
        project_root = Path.cwd()
        pipeline = AutoDebugPipeline(project_root)

        # Run pipeline
        report = pipeline.run(files=files, skip_deep=skip_deep)

        # Display results
        _display_report(report)

        # Save report
        if save:
            report_file = pipeline.save_report(report)
            console.print(f"\n📄 Report saved to: [cyan]{report_file}[/cyan]")

        # Exit with appropriate code
        if not report.overall_success:
            raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[bold red]❌ Auto-debug failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command("status")
def show_status():
    """Show last auto-debug report"""
    project_root = Path.cwd()
    reports_dir = project_root / ".buildrunner" / "build-reports"

    if not reports_dir.exists():
        console.print("[yellow]No auto-debug reports found[/yellow]")
        return

    # Find latest report
    reports = sorted(reports_dir.glob("autodebug_*.json"), reverse=True)
    if not reports:
        console.print("[yellow]No auto-debug reports found[/yellow]")
        return

    latest = reports[0]
    console.print(f"\n[bold]Latest Report:[/bold] {latest.name}")

    import json
    with open(latest) as f:
        report_data = json.load(f)

    console.print(f"\n[bold]Timestamp:[/bold] {report_data['timestamp']}")
    console.print(f"[bold]Overall Status:[/bold] {'✓ PASSED' if report_data['overall_success'] else '✗ FAILED'}")
    console.print(f"[bold]Duration:[/bold] {report_data['total_duration_ms']:.0f}ms")
    console.print(f"\n[bold]Checks Run:[/bold] {report_data['metadata']['checks_run']}")
    console.print(f"[bold]Errors:[/bold] {report_data['metadata']['total_errors']}")
    console.print(f"[bold]Warnings:[/bold] {report_data['metadata']['total_warnings']}")


@app.command("watch")
def watch_mode(
    interval: int = typer.Option(5, "--interval", "-i", help="Check interval in seconds")
):
    """
    Watch mode: continuously run quick checks on file changes

    Monitors the project for file changes and automatically runs
    appropriate checks based on what changed.
    """
    console.print("\n[bold cyan]👁️  Auto-Debug Watch Mode[/bold cyan]")
    console.print(f"Monitoring project for changes (interval: {interval}s)")
    console.print("Press Ctrl+C to stop\n")

    import time
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler

    class ChangeHandler(FileSystemEventHandler):
        def __init__(self, pipeline):
            self.pipeline = pipeline
            self.last_check = 0

        def on_modified(self, event):
            if event.is_directory:
                return

            # Debounce: only check once per interval
            now = time.time()
            if now - self.last_check < interval:
                return

            self.last_check = now
            console.print(f"\n[dim]File changed: {event.src_path}[/dim]")

            # Run quick checks only
            report = self.pipeline.run(skip_deep=True)
            if not report.overall_success:
                console.print("[red]✗ Quick checks failed[/red]")
            else:
                console.print("[green]✓ Quick checks passed[/green]")

    try:
        pipeline = AutoDebugPipeline(Path.cwd())
        event_handler = ChangeHandler(pipeline)
        observer = Observer()
        observer.schedule(event_handler, str(Path.cwd()), recursive=True)
        observer.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            observer.stop()
            console.print("\n[yellow]Watch mode stopped[/yellow]")

        observer.join()

    except Exception as e:
        console.print(f"\n[bold red]❌ Watch mode failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command("retry")
def retry_analysis(
    auto_fix: bool = typer.Option(False, "--auto-fix", help="Apply suggested fixes automatically")
):
    """
    Analyze last failure and suggest intelligent retry strategy

    Uses pattern matching to identify common failure types and suggest
    specific actions to resolve them.

    Example:
        br autodebug retry
        br autodebug retry --auto-fix
    """
    console.print("\n[bold cyan]🔍 Retry Analysis[/bold cyan]\n")

    try:
        project_root = Path.cwd()
        reports_dir = project_root / ".buildrunner" / "build-reports"

        if not reports_dir.exists() or not list(reports_dir.glob("autodebug_*.json")):
            console.print("[yellow]No debug reports found. Run 'br autodebug run' first.[/yellow]")
            raise typer.Exit(1)

        # Load last report
        reports = sorted(reports_dir.glob("autodebug_*.json"), reverse=True)
        latest = reports[0]

        with open(latest) as f:
            report_data = json.load(f)

        # Find first failed check
        failed_check = None
        for check in report_data.get('checks_run', []):
            if not check.get('passed', True) and not check.get('skipped', False):
                failed_check = check
                break

        if not failed_check:
            console.print("[green]✓ No failures in last report[/green]")
            return

        # Create error context
        error_log = "\n".join(failed_check.get('errors', []))
        context = ErrorContext(
            command=failed_check.get('name', 'unknown'),
            exit_code=1,
            log=error_log,
            working_dir=str(project_root),
            timestamp=report_data.get('timestamp', '')
        )

        # Analyze with RetryAnalyzer
        analyzer = RetryAnalyzer()
        strategy = analyzer.analyze_failure(error_log, context)

        # Display results
        console.print(f"[bold]Failure Type:[/bold] {strategy.type}")
        console.print(f"[bold]Confidence:[/bold] {strategy.confidence * 100:.0f}%")
        console.print(f"\n💡 {strategy.explanation}\n")

        console.print("[bold]Suggested Actions:[/bold]")
        for action, enabled in strategy.actions.items():
            if enabled:
                console.print(f"  ✓ {action.replace('_', ' ').title()}")

        # Show fix command
        fix_cmd = analyzer.suggest_fix_command(strategy, context)
        console.print(f"\n[bold]Suggested Command:[/bold]")
        console.print(f"  [cyan]{fix_cmd}[/cyan]\n")

        if auto_fix:
            console.print("[yellow]🚀 Applying fix...[/yellow]")
            import subprocess
            result = subprocess.run(fix_cmd, shell=True, capture_output=True, text=True, cwd=project_root)
            if result.returncode == 0:
                console.print("[green]✅ Fix applied successfully[/green]")
                if result.stdout:
                    console.print(result.stdout)
            else:
                console.print(f"[red]❌ Fix failed[/red]")
                console.print(result.stderr)
                raise typer.Exit(1)

    except Exception as e:
        console.print(f"\n[bold red]❌ Retry analysis failed: {e}[/bold red]")
        raise typer.Exit(1)


@app.command("history")
def show_history():
    """
    Analyze debug history and show patterns

    Provides insights into:
    - Failure hot spots (files/checks that fail often)
    - Error trends over time
    - Success rates by check type
    - Actionable recommendations

    Example:
        br autodebug history
    """
    console.print("\n[bold cyan]📊 Debug History Analysis[/bold cyan]\n")

    try:
        project_root = Path.cwd()
        analyzer = SessionAnalyzer(project_root)
        insights = analyzer.analyze_project_patterns()

        # Hot spots
        if insights.hot_spots:
            console.print("[bold]🔥 Failure Hot Spots:[/bold]")
            for spot in insights.hot_spots[:5]:  # Top 5
                icon = "🔴" if spot.severity == 'high' else "🟡" if spot.severity == 'medium' else "🟢"
                console.print(f"   {icon} {spot.location} ({spot.failure_count} failures, {spot.severity} severity)")
        else:
            console.print("[green]✓ No significant hot spots detected[/green]")

        # Trends
        console.print(f"\n[bold]📈 Error Trends:[/bold]")
        console.print(f"   Direction: {insights.error_trends.trend_direction}")
        console.print(f"   Most Common: {insights.error_trends.most_common_type}")

        # Success rates
        if insights.success_rates:
            console.print(f"\n[bold]📊 Success Rates:[/bold]")
            table = Table()
            table.add_column("Check", style="cyan")
            table.add_column("Success Rate", justify="right")

            for check_name, rate in sorted(insights.success_rates.items(), key=lambda x: x[1]):
                if rate < 70:
                    style = "[red]"
                elif rate < 90:
                    style = "[yellow]"
                else:
                    style = "[green]"
                table.add_row(check_name, f"{style}{rate:.1f}%[/]")

            console.print(table)

        # Recommendations
        console.print(f"\n[bold]💡 Recommendations:[/bold]")
        for rec in insights.recommendations:
            console.print(f"   • {rec}")

        console.print()

    except Exception as e:
        console.print(f"\n[bold red]❌ History analysis failed: {e}[/bold red]")
        raise typer.Exit(1)


def _display_report(report):
    """Display auto-debug report in terminal"""
    # Overall status
    if report.overall_success:
        console.print(Panel(
            "[bold green]✓ All checks passed![/bold green]",
            border_style="green"
        ))
    else:
        console.print(Panel(
            f"[bold red]✗ {len(report.critical_failures)} checks failed[/bold red]",
            border_style="red"
        ))

    # Build context
    console.print(f"\n[bold]Build Context:[/bold]")
    console.print(f"  Type: {report.build_context.build_type.value}")
    console.print(f"  Files changed: {len(report.build_context.changed_files)}")
    console.print(f"  Duration: {report.total_duration_ms:.0f}ms")

    # Results table
    table = Table(title="\nCheck Results")
    table.add_column("Check", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Duration", justify="right")
    table.add_column("Details")

    for result in report.checks_run:
        if result.skipped:
            status = "[dim]SKIPPED[/dim]"
            details = result.skip_reason
        elif result.passed:
            status = "[green]✓ PASS[/green]"
            details = ", ".join(result.info[:2]) if result.info else ""
        else:
            status = "[red]✗ FAIL[/red]"
            details = f"{len(result.errors)} errors"

        table.add_row(
            result.name,
            status,
            f"{result.duration_ms:.0f}ms",
            details
        )

    console.print(table)

    # Errors and warnings
    if report.critical_failures:
        console.print("\n[bold red]Critical Failures:[/bold red]")
        for failure in report.critical_failures:
            console.print(f"  • {failure}")

    # Show first few errors from each failed check
    for result in report.checks_run:
        if result.errors and not result.skipped:
            console.print(f"\n[bold red]Errors in {result.name}:[/bold red]")
            for error in result.errors[:3]:  # Show first 3
                console.print(f"  {error}")
            if len(result.errors) > 3:
                console.print(f"  ... and {len(result.errors) - 3} more")

    # Suggestions
    if report.suggestions:
        console.print("\n[bold yellow]Suggestions:[/bold yellow]")
        for suggestion in report.suggestions:
            console.print(f"  💡 {suggestion}")


if __name__ == "__main__":
    app()
