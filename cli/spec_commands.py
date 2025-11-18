"""
PROJECT_SPEC Commands - CLI commands for spec wizard and management

Commands:
- br spec wizard - Start interactive PROJECT_SPEC creation
- br spec edit <section> - Edit specific section
- br spec sync - Sync spec → features.json → build plans
- br spec validate - Check spec completeness
- br spec review - Section-by-section review mode
- br spec confirm - Lock spec and generate build plans
- br spec unlock - Unlock for changes (triggers rebuild)
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table

from core.prd_wizard import PRDWizard, SpecState
from core.prd_parser import PRDParser
from core.prd_mapper import PRDMapper
from core.design_profiler import DesignProfiler
from core.design_researcher import DesignResearcher

spec_app = typer.Typer(help="PROJECT_SPEC management commands")
console = Console()


@spec_app.command("brainstorm")
def spec_brainstorm():
    """Conversational PRD builder - describe your project and get a complete spec"""
    try:
        console.print("\n[bold blue]💭 Brainstorming Mode[/bold blue]\n")
        console.print("[cyan]Describe your project idea in detail, and I'll build your PRD.[/cyan]\n")

        project_root = Path.cwd()
        wizard = PRDWizard(str(project_root))

        # Run brainstorming mode
        spec = wizard.run_simple_brainstorm()

        console.print("\n[green]✓ PROJECT_SPEC created successfully![/green]")
        console.print(f"  Location: {wizard.spec_path}")
        console.print(f"  Status: {spec.state.value}")

        # Suggest next step
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Run [cyan]br spec sync[/cyan] to generate features.json")
        console.print("  2. Run [cyan]br spec confirm[/cyan] to lock the spec")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@spec_app.command("wizard")
def spec_wizard():
    """Start interactive PROJECT_SPEC creation wizard"""
    try:
        console.print("\n[bold blue]🧙 PROJECT_SPEC Wizard[/bold blue]\n")

        project_root = Path.cwd()
        wizard = PRDWizard(str(project_root))

        # Run wizard
        spec = wizard.run()

        console.print("\n[green]✓ PROJECT_SPEC created successfully![/green]")
        console.print(f"  Location: {wizard.spec_path}")
        console.print(f"  Status: {spec.state.value}")

        # Suggest next step
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  1. Run [cyan]br spec sync[/cyan] to generate features.json")
        console.print("  2. Run [cyan]br spec confirm[/cyan] to lock the spec")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@spec_app.command("sync")
def spec_sync():
    """Sync PROJECT_SPEC to features.json and build plans"""
    try:
        console.print("\n[bold blue]🔄 Syncing PROJECT_SPEC[/bold blue]\n")

        project_root = Path.cwd()
        mapper = PRDMapper(str(project_root))

        # Sync
        features_data = mapper.sync_spec_to_features()

        console.print("[green]✓ Sync complete![/green]")
        console.print(f"  Features: {len(features_data['features'])}")
        console.print(f"  Phases: {len(features_data.get('phases', []))}")
        console.print(f"  File: {mapper.features_path}")

        # Show parallel build opportunities
        parallel_groups = mapper.identify_parallel_builds(features_data)
        if parallel_groups['parallel']:
            console.print(f"\n[cyan]💡 {len(parallel_groups['parallel'])} features can be built in parallel[/cyan]")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@spec_app.command("validate")
def spec_validate():
    """Validate PROJECT_SPEC completeness"""
    try:
        console.print("\n[bold blue]✅ Validating PROJECT_SPEC[/bold blue]\n")

        project_root = Path.cwd()
        spec_path = project_root / ".buildrunner" / "PROJECT_SPEC.md"

        parser = PRDParser(str(spec_path))
        spec = parser.parse()

        # Validate
        issues = parser.validate_completeness(spec)

        if not issues:
            console.print("[green]✓ PROJECT_SPEC is complete![/green]")
            console.print(f"  Industry: {spec.industry}")
            console.print(f"  Use Case: {spec.use_case}")
            console.print(f"  Features: {len(spec.features)}")
            console.print(f"  Phases: {len(spec.phases)}")
        else:
            console.print("[yellow]⚠️  Issues found:[/yellow]\n")

            for section, section_issues in issues.items():
                console.print(f"[bold]{section}:[/bold]")
                for issue in section_issues:
                    console.print(f"  - {issue}")

            raise typer.Exit(1)

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@spec_app.command("confirm")
def spec_confirm():
    """Lock PROJECT_SPEC and generate build plans"""
    try:
        console.print("\n[bold blue]🔒 Confirming PROJECT_SPEC[/bold blue]\n")

        project_root = Path.cwd()
        wizard = PRDWizard(str(project_root))

        # Load current spec
        spec = wizard.load_spec_state()

        if not spec:
            console.print("[red]❌ No spec found. Run 'br spec wizard' first.[/red]")
            raise typer.Exit(1)

        # Change state to confirmed
        spec.state = SpecState.CONFIRMED
        wizard.save_spec_state(spec)

        console.print("[green]✓ PROJECT_SPEC confirmed and locked![/green]")
        console.print("\n[bold]Next steps:[/bold]")
        console.print("  Run [cyan]br build start[/cyan] to begin implementation")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@spec_app.command("unlock")
def spec_unlock():
    """Unlock PROJECT_SPEC for editing (triggers rebuild)"""
    try:
        project_root = Path.cwd()
        wizard = PRDWizard(str(project_root))

        spec = wizard.load_spec_state()

        if not spec:
            console.print("[red]❌ No spec found.[/red]")
            raise typer.Exit(1)

        spec.state = SpecState.DRAFT
        wizard.save_spec_state(spec)

        console.print("[yellow]⚠️  PROJECT_SPEC unlocked for editing[/yellow]")
        console.print("[dim]Changes will trigger rebuild when confirmed[/dim]")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


# Design commands
design_app = typer.Typer(help="Design system commands")


@design_app.command("profile")
def design_profile(
    industry: str = typer.Argument(..., help="Industry (healthcare, fintech, etc.)"),
    use_case: str = typer.Argument(..., help="Use case (dashboard, marketplace, etc.)")
):
    """Preview merged design profile for industry + use case"""
    try:
        console.print(f"\n[bold blue]🎨 Design Profile: {industry} + {use_case}[/bold blue]\n")

        project_root = Path.cwd()
        templates_dir = project_root / "templates"

        profiler = DesignProfiler(str(templates_dir))
        profile = profiler.create_profile(industry, use_case)

        if not profile:
            console.print(f"[red]❌ Could not load profiles for {industry} + {use_case}[/red]")
            console.print("[dim]Check that template files exist in templates/[/dim]")
            raise typer.Exit(1)

        # Display profile info
        table = Table(title="Design Profile")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Industry", profile.industry)
        table.add_row("Use Case", profile.use_case)
        table.add_row("Components", str(len(profile.components)))
        table.add_row("Compliance", ", ".join(profile.compliance_requirements))
        table.add_row("Colors", str(len(profile.colors)))

        console.print(table)

        # Show component list
        console.print("\n[bold]Required Components:[/bold]")
        for component in profile.components[:10]:  # Show first 10
            console.print(f"  - {component}")

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


@design_app.command("research")
def design_research(
    industry: str = typer.Argument(None, help="Industry (optional, reads from spec)"),
    use_case: str = typer.Argument(None, help="Use case (optional, reads from spec)")
):
    """Research design patterns for project"""
    try:
        console.print("\n[bold blue]🔍 Design Research[/bold blue]\n")

        project_root = Path.cwd()

        # If not provided, read from spec
        if not industry or not use_case:
            spec_path = project_root / ".buildrunner" / "PROJECT_SPEC.md"
            parser = PRDParser(str(spec_path))
            spec = parser.parse()
            industry = industry or spec.industry
            use_case = use_case or spec.use_case

        if not industry or not use_case:
            console.print("[red]❌ Industry and use case required[/red]")
            raise typer.Exit(1)

        # Research
        researcher = DesignResearcher(str(project_root))
        research = researcher.research_design_patterns(industry, use_case)

        # Save research
        project_name = f"{industry}_{use_case}"
        output_path = researcher.save_research(research, project_name)

        console.print(f"[green]✓ Research complete![/green]")
        console.print(f"  Patterns: {len(research.patterns)}")
        console.print(f"  Best Practices: {len(research.best_practices)}")
        console.print(f"  Components: {len(research.components)}")
        console.print(f"  Saved to: {output_path}")

        # Show brief
        brief = researcher.generate_design_brief(research)
        console.print("\n[bold]Design Brief:[/bold]")
        console.print(Panel(brief[:500] + "...", expand=False))

    except Exception as e:
        console.print(f"[red]❌ Error: {e}[/red]")
        raise typer.Exit(1)


if __name__ == "__main__":
    spec_app()
