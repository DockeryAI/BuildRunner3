"""
Quality Commands - CLI commands for code quality checking and reporting

Commands:
- br quality check - Run quality gates on codebase
- br quality report - Generate detailed quality report
- br quality score - Show overall quality score
- br quality fix - Auto-fix formatting issues (if available)
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from typing import Optional

from core.code_quality import CodeQualityAnalyzer, QualityGate, QualityGateError

quality_app = typer.Typer(help="Code quality checking and reporting")
console = Console()


@quality_app.command("check")
def quality_check(
    strict: bool = typer.Option(False, "--strict", help="Enforce strict quality standards"),
    min_score: Optional[float] = typer.Option(
        None, "--min-score", help="Minimum required quality score (0-10)"
    ),
):
    """
    Run quality gates on codebase

    Checks:
    - Code structure and organization
    - Security vulnerabilities
    - Test coverage
    - Documentation completeness
    - Overall quality score

    Example:
        br quality check
        br quality check --strict
        br quality check --min-score 8.0
    """
    try:
        console.print("\n[bold blue]🔍 Running Quality Checks...[/bold blue]\n")

        project_root = Path.cwd()

        # Run quality analysis
        analyzer = CodeQualityAnalyzer(project_root)
        metrics = analyzer.analyze_project()

        # Display results
        _display_quality_metrics(metrics, analyzer)

        # Check gates
        gate = QualityGate()
        passed, violations = gate.check(metrics)

        if violations:
            console.print("\n[bold yellow]⚠️  Quality Gate Violations:[/bold yellow]")
            for violation in violations:
                console.print(f"  • {violation}")
            console.print()

        # Enforce if strict
        if strict:
            try:
                gate.enforce(metrics, strict=True)
                console.print("[green]✓ Strict quality gates passed![/green]\n")
            except QualityGateError as e:
                console.print(f"[red]❌ Quality gates failed: {e}[/red]\n")
                raise typer.Exit(1)
        elif min_score and metrics.overall_score < min_score:
            console.print(
                f"[red]❌ Quality score {metrics.overall_score:.1f} below minimum {min_score}[/red]\n"
            )
            raise typer.Exit(1)
        elif not passed:
            console.print("[yellow]⚠️  Some quality checks failed[/yellow]\n")
            raise typer.Exit(1)
        else:
            console.print("[green]✓ Quality checks passed![/green]\n")

    except QualityGateError:
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during quality check: {e}[/red]")
        import traceback

        console.print(f"[dim]{traceback.format_exc()}[/dim]")
        raise typer.Exit(1)


@quality_app.command("report")
def quality_report(
    output_file: Optional[str] = typer.Option(None, "--output", "-o", help="Save report to file"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed breakdown"),
):
    """
    Generate detailed quality report

    Example:
        br quality report
        br quality report --output quality_report.md --verbose
    """
    try:
        console.print("\n[bold blue]📊 Generating Quality Report...[/bold blue]\n")

        project_root = Path.cwd()

        # Run quality analysis
        analyzer = CodeQualityAnalyzer(project_root)
        metrics = analyzer.analyze_project()

        # Display detailed metrics
        _display_quality_metrics(metrics, analyzer, verbose=True)

        # Save report if requested
        if output_file:
            _save_quality_report(metrics, analyzer, Path(output_file))
            console.print(f"\n[green]✓ Report saved to: {output_file}[/green]\n")
        else:
            console.print()

    except Exception as e:
        console.print(f"[red]❌ Error generating report: {e}[/red]")
        raise typer.Exit(1)


@quality_app.command("score")
def show_score():
    """
    Show overall quality score

    Example:
        br quality score
    """
    try:
        console.print("\n[bold blue]📈 Quality Score[/bold blue]\n")

        project_root = Path.cwd()

        # Run quality analysis
        analyzer = CodeQualityAnalyzer(project_root)
        metrics = analyzer.analyze_project()

        # Display score with color coding
        score = metrics.overall_score
        if score >= 8.0:
            color = "green"
            rating = "Excellent"
        elif score >= 7.0:
            color = "blue"
            rating = "Good"
        elif score >= 6.0:
            color = "yellow"
            rating = "Fair"
        else:
            color = "red"
            rating = "Needs Improvement"

        console.print(
            Panel(
                f"[bold {color}]{score:.1f}/10[/bold {color}] - {rating}",
                title="Overall Quality Score",
                border_style=color,
            )
        )

        # Quick breakdown
        console.print("\n[bold]Score Breakdown:[/bold]")
        console.print(f"  Structure: {analyzer.calculate_structure_score(metrics):.1f}/10")
        console.print(f"  Security:  {analyzer.calculate_security_score(metrics):.1f}/10")
        console.print(f"  Testing:   {analyzer.calculate_testing_score(metrics):.1f}/10")
        console.print(f"  Docs:      {analyzer.calculate_docs_score(metrics):.1f}/10\n")

    except Exception as e:
        console.print(f"[red]❌ Error calculating score: {e}[/red]")
        raise typer.Exit(1)


@quality_app.command("lint")
def lint_check(
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues where possible"),
    paths: Optional[str] = typer.Argument(None, help="Paths to check (default: all)"),
):
    """
    Run Ruff linter on the codebase

    Example:
        br quality lint
        br quality lint --fix
        br quality lint core/
    """
    import subprocess

    try:
        console.print("\n[bold blue]🧹 Running Ruff Linter...[/bold blue]\n")

        # Default paths if not specified
        if not paths:
            paths = "."

        # Build command
        cmd = ["ruff", "check"]
        if fix:
            cmd.append("--fix")
        cmd.append(paths)

        # Run Ruff
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[green]✓ No linting issues found[/green]\n")
        else:
            console.print("[yellow]⚠ Linting issues found:[/yellow]\n")
            if result.stdout:
                console.print(result.stdout)
            raise typer.Exit(1)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Ruff failed: {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ Ruff not installed. Install with: pip install ruff[/red]")
        raise typer.Exit(1)


@quality_app.command("typecheck")
def type_check(
    strict: bool = typer.Option(False, "--strict", help="Enable strict type checking"),
    paths: Optional[str] = typer.Argument(None, help="Paths to check (default: all)"),
):
    """
    Run MyPy type checker

    Example:
        br quality typecheck
        br quality typecheck --strict
        br quality typecheck core/
    """
    import subprocess

    try:
        console.print("\n[bold blue]🎯 Running MyPy Type Checker...[/bold blue]\n")

        # Default paths if not specified
        if not paths:
            paths = "."

        # Build command
        cmd = ["mypy"]
        if strict:
            cmd.append("--strict")
        cmd.append(paths)

        # Run MyPy
        result = subprocess.run(cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[green]✓ No type errors found[/green]\n")
        else:
            console.print("[yellow]⚠ Type errors found:[/yellow]\n")
            if result.stdout:
                # Parse and display MyPy output nicely
                for line in result.stdout.splitlines():
                    if "error:" in line:
                        console.print(f"[red]{line}[/red]")
                    elif "note:" in line:
                        console.print(f"[dim]{line}[/dim]")
                    else:
                        console.print(line)
            raise typer.Exit(1)

    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ MyPy failed: {e}[/red]")
        raise typer.Exit(1)
    except FileNotFoundError:
        console.print("[red]❌ MyPy not installed. Install with: pip install mypy[/red]")
        raise typer.Exit(1)


@quality_app.command("fix")
def auto_fix(
    dry_run: bool = typer.Option(True, "--dry-run/--apply", help="Preview changes without applying")
):
    """
    Auto-fix formatting and linting issues

    Uses Black for formatting and Ruff for linting fixes.

    Example:
        br quality fix --dry-run
        br quality fix --apply
    """
    import subprocess

    try:
        console.print("\n[bold blue]🔧 Auto-Fix Quality Issues...[/bold blue]\n")

        if dry_run:
            console.print("[yellow]DRY RUN MODE - No changes will be made[/yellow]\n")

        # Run Black
        console.print("[cyan]Running Black formatter...[/cyan]")
        black_cmd = ["black", "--check" if dry_run else "", "."]
        black_cmd = [arg for arg in black_cmd if arg]  # Remove empty strings
        result = subprocess.run(black_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            if dry_run:
                console.print("[green]✓ Code is already formatted[/green]")
            else:
                console.print("[green]✓ Code formatted successfully[/green]")
        else:
            if dry_run:
                console.print("[yellow]⚠ Files would be reformatted[/yellow]")
            else:
                console.print("[green]✓ Files reformatted[/green]")

        # Run Ruff
        console.print("\n[cyan]Running Ruff linter...[/cyan]")
        ruff_cmd = ["ruff", "check", "--fix" if not dry_run else "", "."]
        ruff_cmd = [arg for arg in ruff_cmd if arg]  # Remove empty strings
        result = subprocess.run(ruff_cmd, capture_output=True, text=True)

        if result.returncode == 0:
            console.print("[green]✓ No linting issues found[/green]")
        else:
            if dry_run:
                console.print("[yellow]⚠ Issues found that can be fixed[/yellow]")
                if result.stdout:
                    console.print(result.stdout)
            else:
                console.print("[green]✓ Fixed linting issues[/green]")

        console.print()

    except subprocess.CalledProcessError as e:
        console.print(f"[red]❌ Command failed: {e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]❌ Error during auto-fix: {e}[/red]")
        raise typer.Exit(1)


# Helper functions


def _display_quality_metrics(metrics, analyzer, verbose=False):
    """Display quality metrics in a formatted table"""

    # Main scores table
    table = Table(title="Quality Metrics")
    table.add_column("Category", style="cyan")
    table.add_column("Score", justify="right", style="green")
    table.add_column("Status", justify="center")

    # Calculate scores
    structure_score = analyzer.calculate_structure_score(metrics)
    security_score = analyzer.calculate_security_score(metrics)
    testing_score = analyzer.calculate_testing_score(metrics)
    docs_score = analyzer.calculate_docs_score(metrics)

    def get_status(score):
        if score >= 8.0:
            return "[green]✓[/green]"
        elif score >= 6.0:
            return "[yellow]⚠[/yellow]"
        else:
            return "[red]✗[/red]"

    table.add_row(
        "Structure & Organization", f"{structure_score:.1f}/10", get_status(structure_score)
    )
    table.add_row("Security", f"{security_score:.1f}/10", get_status(security_score))
    table.add_row("Testing", f"{testing_score:.1f}/10", get_status(testing_score))
    table.add_row("Documentation", f"{docs_score:.1f}/10", get_status(docs_score))
    table.add_row(
        "[bold]Overall[/bold]",
        f"[bold]{metrics.overall_score:.1f}/10[/bold]",
        get_status(metrics.overall_score),
    )

    console.print(table)

    # Stats table if verbose
    if verbose:
        console.print()
        stats_table = Table(title="Codebase Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", justify="right", style="blue")

        stats_table.add_row("Total Files", str(metrics.file_count))
        stats_table.add_row("Total Lines", f"{metrics.total_lines:,}")
        stats_table.add_row("Functions", str(metrics.function_count))
        stats_table.add_row("Classes", str(metrics.class_count))
        stats_table.add_row("Average Complexity", f"{metrics.avg_complexity:.1f}")
        stats_table.add_row("Max Complexity", str(metrics.max_complexity))

        console.print(stats_table)


def _save_quality_report(metrics, analyzer, output_path: Path):
    """Save quality report to markdown file"""
    with open(output_path, "w") as f:
        f.write("# Code Quality Report\n\n")
        f.write(f"**Project:** {Path.cwd().name}\n\n")

        f.write("## Overall Score\n\n")
        f.write(f"**{metrics.overall_score:.1f}/10**\n\n")

        f.write("## Score Breakdown\n\n")
        f.write(
            f"- Structure & Organization: {analyzer.calculate_structure_score(metrics):.1f}/10\n"
        )
        f.write(f"- Security: {analyzer.calculate_security_score(metrics):.1f}/10\n")
        f.write(f"- Testing: {analyzer.calculate_testing_score(metrics):.1f}/10\n")
        f.write(f"- Documentation: {analyzer.calculate_docs_score(metrics):.1f}/10\n\n")

        f.write("## Codebase Statistics\n\n")
        f.write(f"- Total Files: {metrics.file_count}\n")
        f.write(f"- Total Lines: {metrics.total_lines:,}\n")
        f.write(f"- Functions: {metrics.function_count}\n")
        f.write(f"- Classes: {metrics.class_count}\n")
        f.write(f"- Average Complexity: {metrics.avg_complexity:.1f}\n")
        f.write(f"- Max Complexity: {metrics.max_complexity}\n\n")

        f.write("## Quality Gates\n\n")
        gate = QualityGate()
        passed, violations = gate.check(metrics)

        if passed:
            f.write("✓ All quality gates passed\n\n")
        else:
            f.write("Violations:\n\n")
            for violation in violations:
                f.write(f"- {violation}\n")
            f.write("\n")


if __name__ == "__main__":
    quality_app()
