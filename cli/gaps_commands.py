"""
Gap Analysis Commands - CLI commands for analyzing spec vs implementation gaps

Commands:
- br gaps analyze - Analyze gaps between spec and implementation
- br gaps report - Generate detailed gap analysis report
- br gaps list - List all detected gaps
- br gaps summary - Show gap analysis summary
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from typing import Optional

from core.gap_analyzer import GapAnalyzer, GapAnalysis
from core.codebase_scanner import CodebaseScanner

gaps_app = typer.Typer(help="Gap analysis and spec validation commands")
console = Console()


@gaps_app.command("analyze")
def analyze_gaps(
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Save report to file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed analysis")
):
    """
    Analyze gaps between spec and implementation

    Detects:
    - Missing features
    - Incomplete implementations (TODOs, stubs)
    - Missing dependencies
    - Spec violations

    Example:
        br gaps analyze
        br gaps analyze --output gap_report.txt --verbose
    """
    try:
        console.print("\n[bold blue]🔍 Running Gap Analysis...[/bold blue]\n")

        project_root = Path.cwd()

        # Run gap analysis
        analyzer = GapAnalyzer(project_root)
        analysis = analyzer.analyze()

        # Display summary
        _display_summary(analysis)

        # Display gaps by category
        if verbose or analysis.total_gaps > 0:
            console.print("\n" + "="*80 + "\n")
            _display_feature_gaps(analysis)
            _display_implementation_gaps(analysis)
            _display_dependency_gaps(analysis)
            _display_spec_violations(analysis)

        # Save to file if requested
        if output_file:
            _save_report(analysis, Path(output_file))
            console.print(f"\n[green]✓ Report saved to: {output_file}[/green]\n")

        # Exit code based on severity
        if analysis.severity_high > 0:
            console.print("[red]⚠️  Critical gaps detected[/red]\n")
            raise typer.Exit(1)
        elif analysis.total_gaps > 0:
            console.print("[yellow]⚠️  Some gaps detected[/yellow]\n")
            raise typer.Exit(0)
        else:
            console.print("[green]✓ No gaps detected![/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Error during gap analysis: {e}[/red]")
        import traceback
        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@gaps_app.command("report")
def generate_report(
    output_file: str = typer.Option(".buildrunner/gap_report.md", "--output", "-o", help="Output file path"),
    format: str = typer.Option("markdown", "--format", "-f", help="Report format (markdown/json/text)")
):
    """
    Generate detailed gap analysis report

    Example:
        br gaps report
        br gaps report --output custom_report.md
        br gaps report --format json --output gaps.json
    """
    try:
        console.print(f"\n[bold blue]📊 Generating Gap Analysis Report...[/bold blue]\n")

        project_root = Path.cwd()

        # Run analysis
        analyzer = GapAnalyzer(project_root)
        analysis = analyzer.analyze()

        # Generate report
        output_path = Path(output_file)
        output_path.parent.mkdir(parents=True, exist_ok=True)

        if format == "json":
            import json
            import dataclasses
            with open(output_path, 'w') as f:
                json.dump(dataclasses.asdict(analysis), f, indent=2)
        elif format == "markdown":
            _save_report(analysis, output_path)
        else:  # text
            _save_text_report(analysis, output_path)

        console.print(f"[green]✓ Report generated: {output_path}[/green]")
        console.print(f"  Total gaps: {analysis.total_gaps}")
        console.print(f"  High severity: {analysis.severity_high}")
        console.print(f"  Medium severity: {analysis.severity_medium}")
        console.print(f"  Low severity: {analysis.severity_low}\n")

    except Exception as e:
        console.print(f"[red]❌ Error generating report: {e}[/red]")
        raise typer.Exit(1)


@gaps_app.command("list")
def list_gaps(
    severity: Optional[str] = typer.Option(None, "--severity", "-s", help="Filter by severity (high/medium/low)"),
    category: Optional[str] = typer.Option(None, "--category", "-c", help="Filter by category (features/implementation/dependencies)")
):
    """
    List all detected gaps

    Example:
        br gaps list
        br gaps list --severity high
        br gaps list --category features
    """
    try:
        console.print("\n[bold blue]📋 Gap List[/bold blue]\n")

        project_root = Path.cwd()

        # Run analysis
        analyzer = GapAnalyzer(project_root)
        analysis = analyzer.analyze()

        gaps_shown = 0

        # Feature gaps (high severity)
        if (not severity or severity == "high") and (not category or category == "features"):
            if analysis.missing_features:
                console.print("[bold red]Missing Features (High):[/bold red]")
                for feature in analysis.missing_features:
                    console.print(f"  • {feature.get('name', 'Unknown')} - {feature.get('status', 'Unknown')}")
                    gaps_shown += 1
                console.print()

        # Implementation gaps
        if not category or category == "implementation":
            if analysis.todos and (not severity or severity == "low"):
                console.print("[bold yellow]TODOs (Low):[/bold yellow]")
                for todo in analysis.todos[:10]:
                    console.print(f"  • {todo.get('file', 'Unknown')}:{todo.get('line', '?')} - {todo.get('message', 'No message')}")
                    gaps_shown += 1
                if len(analysis.todos) > 10:
                    console.print(f"  ... and {len(analysis.todos) - 10} more")
                console.print()

            if analysis.stubs and (not severity or severity == "high"):
                console.print("[bold red]Stubs/NotImplemented (High):[/bold red]")
                for stub in analysis.stubs:
                    console.print(f"  • {stub.get('file', 'Unknown')}:{stub.get('line', '?')}")
                    gaps_shown += 1
                console.print()

        # Dependency gaps
        if (not severity or severity == "medium") and (not category or category == "dependencies"):
            if analysis.missing_dependencies:
                console.print("[bold yellow]Missing Dependencies (Medium):[/bold yellow]")
                for dep in analysis.missing_dependencies:
                    console.print(f"  • {dep}")
                    gaps_shown += 1
                console.print()

        if gaps_shown == 0:
            console.print("[green]✓ No gaps found matching criteria[/green]\n")
        else:
            console.print(f"[dim]Showing {gaps_shown} gaps[/dim]\n")

    except Exception as e:
        console.print(f"[red]❌ Error listing gaps: {e}[/red]")
        raise typer.Exit(1)


@gaps_app.command("summary")
def show_summary():
    """
    Show gap analysis summary

    Example:
        br gaps summary
    """
    try:
        console.print("\n[bold blue]📊 Gap Analysis Summary[/bold blue]\n")

        project_root = Path.cwd()

        # Run analysis
        analyzer = GapAnalyzer(project_root)
        analysis = analyzer.analyze()

        # Display summary
        _display_summary(analysis)

        # Quick stats
        console.print("\n[bold]Quick Stats:[/bold]")
        console.print(f"  Missing features: {len(analysis.missing_features)}")
        console.print(f"  Incomplete features: {len(analysis.incomplete_features)}")
        console.print(f"  TODOs: {analysis.todo_count}")
        console.print(f"  Stubs: {analysis.stub_count}")
        console.print(f"  Missing dependencies: {len(analysis.missing_dependencies)}\n")

        # Recommendations
        if analysis.severity_high > 0:
            console.print("[bold red]⚠️  Action Required:[/bold red]")
            console.print("  Critical gaps detected. Run 'br gaps analyze --verbose' for details\n")
        elif analysis.total_gaps > 0:
            console.print("[yellow]ℹ️  Some gaps exist but none critical[/yellow]\n")
        else:
            console.print("[green]✓ Implementation appears complete![/green]\n")

    except Exception as e:
        console.print(f"[red]❌ Error generating summary: {e}[/red]")
        raise typer.Exit(1)


# Helper functions

def _display_summary(analysis: GapAnalysis):
    """Display gap analysis summary"""
    table = Table(title="Gap Analysis Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Count", justify="right", style="green")
    table.add_column("Severity", style="yellow")

    table.add_row("Total Gaps", str(analysis.total_gaps), "")
    table.add_row("High Severity", str(analysis.severity_high), "[red]Critical[/red]")
    table.add_row("Medium Severity", str(analysis.severity_medium), "[yellow]Warning[/yellow]")
    table.add_row("Low Severity", str(analysis.severity_low), "[dim]Info[/dim]")

    console.print(table)


def _display_feature_gaps(analysis: GapAnalysis):
    """Display feature-related gaps"""
    if not analysis.missing_features and not analysis.incomplete_features and not analysis.blocked_features:
        return

    console.print("[bold]Feature Gaps:[/bold]\n")

    if analysis.missing_features:
        console.print(f"[red]Missing Features ({len(analysis.missing_features)}):[/red]")
        for feature in analysis.missing_features[:5]:
            console.print(f"  • {feature.get('name', 'Unknown')}")
        if len(analysis.missing_features) > 5:
            console.print(f"  ... and {len(analysis.missing_features) - 5} more\n")

    if analysis.incomplete_features:
        console.print(f"[yellow]Incomplete Features ({len(analysis.incomplete_features)}):[/yellow]")
        for feature in analysis.incomplete_features[:5]:
            console.print(f"  • {feature.get('name', 'Unknown')}")
        if len(analysis.incomplete_features) > 5:
            console.print(f"  ... and {len(analysis.incomplete_features) - 5} more\n")

    if analysis.blocked_features:
        console.print(f"[yellow]Blocked Features ({len(analysis.blocked_features)}):[/yellow]")
        for feature in analysis.blocked_features[:5]:
            console.print(f"  • {feature.get('name', 'Unknown')}")
        if len(analysis.blocked_features) > 5:
            console.print(f"  ... and {len(analysis.blocked_features) - 5} more\n")


def _display_implementation_gaps(analysis: GapAnalysis):
    """Display implementation gaps (TODOs, stubs, etc)"""
    if analysis.todo_count == 0 and analysis.stub_count == 0:
        return

    console.print("[bold]Implementation Gaps:[/bold]\n")

    if analysis.stub_count > 0:
        console.print(f"[red]Stubs/NotImplemented ({analysis.stub_count}):[/red]")
        for stub in analysis.stubs[:5]:
            console.print(f"  • {stub.get('file', 'Unknown')}:{stub.get('line', '?')}")
        if len(analysis.stubs) > 5:
            console.print(f"  ... and {len(analysis.stubs) - 5} more")
        console.print()

    if analysis.todo_count > 0:
        console.print(f"[yellow]TODOs/FIXMEs ({analysis.todo_count}):[/yellow]")
        for todo in analysis.todos[:5]:
            console.print(f"  • {todo.get('file', 'Unknown')}:{todo.get('line', '?')} - {todo.get('message', 'No message')[:60]}")
        if len(analysis.todos) > 5:
            console.print(f"  ... and {len(analysis.todos) - 5} more")
        console.print()


def _display_dependency_gaps(analysis: GapAnalysis):
    """Display dependency gaps"""
    if not analysis.missing_dependencies and not analysis.circular_dependencies:
        return

    console.print("[bold]Dependency Gaps:[/bold]\n")

    if analysis.missing_dependencies:
        console.print(f"[yellow]Missing Dependencies ({len(analysis.missing_dependencies)}):[/yellow]")
        for dep in analysis.missing_dependencies[:10]:
            console.print(f"  • {dep}")
        if len(analysis.missing_dependencies) > 10:
            console.print(f"  ... and {len(analysis.missing_dependencies) - 10} more")
        console.print()

    if analysis.circular_dependencies:
        console.print(f"[red]Circular Dependencies ({len(analysis.circular_dependencies)}):[/red]")
        for cycle in analysis.circular_dependencies[:3]:
            console.print(f"  • {' → '.join(cycle)}")
        if len(analysis.circular_dependencies) > 3:
            console.print(f"  ... and {len(analysis.circular_dependencies) - 3} more")
        console.print()


def _display_spec_violations(analysis: GapAnalysis):
    """Display spec violations"""
    if not analysis.spec_violations and not analysis.missing_components:
        return

    console.print("[bold]Spec Violations:[/bold]\n")

    if analysis.spec_violations:
        console.print(f"[yellow]Violations ({len(analysis.spec_violations)}):[/yellow]")
        for violation in analysis.spec_violations[:5]:
            console.print(f"  • {violation.get('message', 'Unknown violation')}")
        if len(analysis.spec_violations) > 5:
            console.print(f"  ... and {len(analysis.spec_violations) - 5} more")
        console.print()

    if analysis.missing_components:
        console.print(f"[red]Missing Components ({len(analysis.missing_components)}):[/red]")
        for component in analysis.missing_components:
            console.print(f"  • {component}")
        console.print()


def _save_report(analysis: GapAnalysis, output_path: Path):
    """Save gap analysis report to markdown file"""
    with open(output_path, 'w') as f:
        f.write("# Gap Analysis Report\n\n")
        f.write(f"**Generated:** {Path.cwd()}\n\n")
        f.write("## Summary\n\n")
        f.write(f"- Total Gaps: {analysis.total_gaps}\n")
        f.write(f"- High Severity: {analysis.severity_high}\n")
        f.write(f"- Medium Severity: {analysis.severity_medium}\n")
        f.write(f"- Low Severity: {analysis.severity_low}\n\n")

        if analysis.missing_features:
            f.write("## Missing Features\n\n")
            for feature in analysis.missing_features:
                f.write(f"- {feature.get('name', 'Unknown')}\n")
            f.write("\n")

        if analysis.incomplete_features:
            f.write("## Incomplete Features\n\n")
            for feature in analysis.incomplete_features:
                f.write(f"- {feature.get('name', 'Unknown')}\n")
            f.write("\n")

        if analysis.stubs:
            f.write("## Stubs/NotImplemented\n\n")
            for stub in analysis.stubs:
                f.write(f"- {stub.get('file', 'Unknown')}:{stub.get('line', '?')}\n")
            f.write("\n")

        if analysis.todos:
            f.write("## TODOs\n\n")
            for todo in analysis.todos:
                f.write(f"- {todo.get('file', 'Unknown')}:{todo.get('line', '?')} - {todo.get('message', '')}\n")
            f.write("\n")

        if analysis.missing_dependencies:
            f.write("## Missing Dependencies\n\n")
            for dep in analysis.missing_dependencies:
                f.write(f"- {dep}\n")
            f.write("\n")


def _save_text_report(analysis: GapAnalysis, output_path: Path):
    """Save gap analysis report to text file"""
    with open(output_path, 'w') as f:
        f.write("GAP ANALYSIS REPORT\n")
        f.write("=" * 80 + "\n\n")
        f.write(f"Total Gaps: {analysis.total_gaps}\n")
        f.write(f"High Severity: {analysis.severity_high}\n")
        f.write(f"Medium Severity: {analysis.severity_medium}\n")
        f.write(f"Low Severity: {analysis.severity_low}\n\n")

        # Add sections similar to markdown but plain text format
        if analysis.missing_features:
            f.write("MISSING FEATURES\n" + "-" * 80 + "\n")
            for feature in analysis.missing_features:
                f.write(f"  • {feature.get('name', 'Unknown')}\n")
            f.write("\n")


if __name__ == "__main__":
    gaps_app()
