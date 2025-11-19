"""
ATTACH Commands - Retrofit BuildRunner onto existing projects
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
import json
import time

from core.analyzer import CodebaseAnalyzer, SpecGenerator
from cli.config_manager import ConfigManager

attach_app = typer.Typer(help="Attach BuildRunner to existing projects")
console = Console()


@attach_app.command("analyze")
def attach_analyze(
    generate_spec: bool = typer.Option(True, help="Generate PROJECT_SPEC from code"),
    launch_planning: bool = typer.Option(True, help="Launch Claude Code planning mode")
):
    """
    Analyze existing codebase and generate PROJECT_SPEC

    This scans your entire project to:
    - Detect languages and frameworks
    - Extract features from code
    - Find API endpoints
    - Generate initial PROJECT_SPEC.md
    """
    try:
        project_root = Path.cwd()
        buildrunner_dir = project_root / ".buildrunner"

        console.print("\n[bold blue]🔍 Analyzing Existing Codebase[/bold blue]\n")

        # Step 1: Analyze codebase
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Scanning project files...", total=None)

            analyzer = CodebaseAnalyzer(str(project_root))
            analysis = analyzer.scan_project()

            progress.update(task, completed=True)

        # Show analysis results
        console.print("\n[bold green]✅ Analysis Complete![/bold green]\n")

        table = Table(title="Project Analysis", show_header=True)
        table.add_column("Metric", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Files Scanned", str(analysis.file_count))
        table.add_row("Lines of Code", f"{analysis.lines_of_code:,}")
        table.add_row("Languages", ", ".join(analysis.languages) or "Not detected")
        table.add_row("Frameworks", ", ".join(analysis.frameworks) or "None")
        table.add_row("Architecture", analysis.architecture)
        table.add_row("Database", analysis.database or "Not detected")
        table.add_row("Features Found", str(len(analysis.features)))
        table.add_row("API Endpoints", str(len(analysis.api_endpoints)))
        table.add_row("Test Coverage", f"{analysis.test_coverage:.1f}%")

        console.print(table)

        # Step 2: Create .buildrunner directory
        console.print("\n[bold blue]📁 Creating BuildRunner Structure[/bold blue]")
        buildrunner_dir.mkdir(exist_ok=True)
        (buildrunner_dir / "context").mkdir(exist_ok=True)
        (buildrunner_dir / "governance").mkdir(exist_ok=True)
        (buildrunner_dir / "standards").mkdir(exist_ok=True)
        console.print("[green]✅ .buildrunner/ directory created[/green]")

        # Step 3: Initialize features.json
        features_data = {
            "project": project_root.name,
            "version": "1.0.0",
            "status": "retrofit",
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "features": [],
            "metrics": {
                "files_analyzed": analysis.file_count,
                "lines_of_code": analysis.lines_of_code,
                "features_detected": len(analysis.features),
                "test_coverage": round(analysis.test_coverage, 1)
            }
        }

        features_file = buildrunner_dir / "features.json"
        with open(features_file, 'w') as f:
            json.dump(features_data, f, indent=2)

        console.print("[green]✅ features.json initialized[/green]")

        # Step 4: Generate PROJECT_SPEC
        if generate_spec:
            console.print("\n[bold blue]📝 Generating PROJECT_SPEC[/bold blue]")

            generator = SpecGenerator()
            spec_content = generator.from_existing_code(analysis)

            spec_path = buildrunner_dir / "PROJECT_SPEC.md"
            spec_path.write_text(spec_content)

            console.print(f"[green]✅ PROJECT_SPEC.md generated[/green]")
            console.print(f"[dim]   Location: {spec_path}[/dim]")

        # Step 5: Initialize config
        config_manager = ConfigManager(project_root)
        config_manager.init_project_config()
        console.print("[green]✅ Configuration initialized[/green]")

        # Summary
        console.print("\n[bold green]🎉 BuildRunner Attached Successfully![/bold green]\n")

        console.print(Panel(
            f"""[bold]Next Steps:[/bold]

1. Review the generated PROJECT_SPEC.md:
   [cyan]cat .buildrunner/PROJECT_SPEC.md[/cyan]

2. Edit and refine as needed:
   [cyan]br spec wizard[/cyan]

3. Start building:
   [cyan]br build start[/cyan]

[dim]BuildRunner is now managing your project![/dim]""",
            title="✅ Retrofit Complete",
            border_style="green"
        ))

        # Optional: Launch planning mode
        if launch_planning and generate_spec:
            console.print("\n[bold blue]🚀 Launching Planning Mode for Review[/bold blue]\n")

            # Create CLAUDE.md for planning
            claude_md_path = project_root / "CLAUDE.md"
            claude_content = f"""# 🎯 PLANNING MODE - Existing Project Review

**Project:** {project_root.name}
**Status:** RETROFIT - BuildRunner attached to existing codebase
**Generated Spec:** {spec_path}

---

## ⚠️ CRITICAL: Review Generated PROJECT_SPEC

BuildRunner has analyzed your existing codebase and generated an initial PROJECT_SPEC.md.

### Your Task:

1. **Review** the generated spec at: `{spec_path}`
2. **Validate** extracted features are accurate
3. **Add** any missing features or requirements
4. **Refine** priorities and acceptance criteria
5. **Approve** or edit each section

### Workflow:

- Read the generated PROJECT_SPEC.md
- Use the flexible PRD workflow from planning mode
- Update sections as needed
- When satisfied, you can use `br build start` to begin implementation

---

## 🚀 Start Review

Open and review: {spec_path}

Then use AskUserQuestion to confirm:
- Does the spec accurately represent your project?
- Are all major features captured?
- Are there missing capabilities to add?

Follow the standard planning workflow to refine the spec.
"""

            claude_md_path.write_text(claude_content)
            console.print(f"[green]✅ Created {claude_md_path}[/green]")
            console.print("[green]✅ Launching Claude Code for review...[/green]\n")

            # Launch Claude Code
            import os
            os.execvp('claude', ['claude', '--dangerously-skip-permissions', str(project_root)])

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@attach_app.command("minimal")
def attach_minimal():
    """
    Minimal BuildRunner setup - just add .buildrunner/ structure

    Creates the basic directory structure without code analysis.
    """
    try:
        project_root = Path.cwd()
        buildrunner_dir = project_root / ".buildrunner"

        console.print("\n[bold blue]📁 Minimal BuildRunner Setup[/bold blue]\n")

        # Create structure
        buildrunner_dir.mkdir(exist_ok=True)
        (buildrunner_dir / "context").mkdir(exist_ok=True)
        (buildrunner_dir / "governance").mkdir(exist_ok=True)
        (buildrunner_dir / "standards").mkdir(exist_ok=True)

        # Initialize empty features.json
        features_data = {
            "project": project_root.name,
            "version": "1.0.0",
            "status": "initialized",
            "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "features": [],
            "metrics": {
                "features_complete": 0,
                "features_in_progress": 0,
                "features_planned": 0,
                "completion_percentage": 0
            }
        }

        features_file = buildrunner_dir / "features.json"
        with open(features_file, 'w') as f:
            json.dump(features_data, f, indent=2)

        console.print("[green]✅ .buildrunner/ structure created[/green]")
        console.print("[green]✅ features.json initialized[/green]")

        console.print("\n[bold]Next step:[/bold]")
        console.print("  Run [cyan]br spec wizard[/cyan] to create PROJECT_SPEC.md")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@attach_app.command("security")
def attach_security():
    """
    Security-focused integration - add security scanning only

    Sets up pre-commit hooks and runs initial security scan.
    """
    try:
        project_root = Path.cwd()
        buildrunner_dir = project_root / ".buildrunner"

        console.print("\n[bold blue]🔒 Security Integration[/bold blue]\n")

        # Create minimal structure
        buildrunner_dir.mkdir(exist_ok=True)

        # Setup security hooks
        console.print("[bold]Installing security hooks...[/bold]")
        console.print("[yellow]⚠️  Security hooks implementation pending[/yellow]")
        console.print("[dim]Will be available in BuildRunner 3.1 final release[/dim]")

        console.print("\n[bold]Next step:[/bold]")
        console.print("  Run [cyan]br security scan[/cyan] to scan for vulnerabilities")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@attach_app.command()
def attach(
    mode: str = typer.Option("analyze", help="Mode: analyze|minimal|security"),
):
    """
    Attach BuildRunner to existing project (shorthand)

    Modes:
    - analyze: Full analysis + PROJECT_SPEC generation
    - minimal: Just create .buildrunner/ structure
    - security: Security scanning only
    """
    if mode == "analyze":
        attach_analyze()
    elif mode == "minimal":
        attach_minimal()
    elif mode == "security":
        attach_security()
    else:
        console.print(f"[red]❌ Unknown mode: {mode}[/red]")
        console.print("Valid modes: analyze, minimal, security")
        raise typer.Exit(1)


if __name__ == "__main__":
    attach_app()
