"""BR3 Attach - Retrofit existing projects to BuildRunner 3"""

import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
import logging
import json

from core.retrofit import CodebaseScanner, FeatureExtractor, PRDSynthesizer
from core.retrofit.version_detector import BRVersionDetector, BRVersion
from core.migration.v2_parser import V2ProjectParser
from core.migration.converter import MigrationConverter
from core.prd.prd_controller import get_prd_controller
from core.claude_md_generator import ClaudeMdGenerator

attach_app = typer.Typer(help="Attach BR3 to existing projects")
console = Console()
logger = logging.getLogger(__name__)


@attach_app.command()
def attach(
    directory: Path = typer.Argument(
        None,
        help="Project directory to attach (defaults to current directory)"
    ),
    output: Path = typer.Option(
        None,
        "--output",
        "-o",
        help="Output path for PROJECT_SPEC.md (defaults to .buildrunner/PROJECT_SPEC.md)"
    ),
    dry_run: bool = typer.Option(
        False,
        "--dry-run",
        help="Preview without writing files"
    ),
):
    """
    Attach BuildRunner 3 to an existing project.

    Scans the codebase, analyzes structure, extracts features,
    and generates a PROJECT_SPEC.md that becomes the source of truth.
    """
    # Default to current directory
    if directory is None:
        directory = Path.cwd()
    else:
        directory = Path(directory).resolve()

    # Validate directory
    if not directory.exists():
        console.print(f"[red]Error: Directory not found: {directory}[/red]")
        raise typer.Exit(1)

    if not directory.is_dir():
        console.print(f"[red]Error: Not a directory: {directory}[/red]")
        raise typer.Exit(1)

    # Default output path
    if output is None:
        output = directory / ".buildrunner" / "PROJECT_SPEC.md"

    # Show welcome message
    console.print()
    console.print(Panel.fit(
        "[bold cyan]BuildRunner 3 - Attach to Existing Project[/bold cyan]\n\n"
        f"[white]Analyzing codebase at:[/white] [yellow]{directory}[/yellow]",
        border_style="cyan"
    ))
    console.print()

    # Phase 0: Detect BR Version
    console.print("[bold]Phase 0:[/bold] Detecting BuildRunner version...")
    detector = BRVersionDetector(directory)
    version_result = detector.detect()

    console.print(f"  Version: [cyan]{version_result.version.value}[/cyan]")
    console.print(f"  Confidence: [yellow]{version_result.confidence:.0%}[/yellow]")
    console.print()

    # Handle legacy BR2 projects - migrate first
    if version_result.version == BRVersion.BR2:
        console.print("[yellow]⚠️  BuildRunner 2.0 detected - migrating to BR3 first...[/yellow]")
        console.print()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            migrate_task = progress.add_task("📦 Migrating BR2 → BR3...", total=None)

            # Parse BR2 project
            parser = V2ProjectParser(directory)
            v2_project = parser.parse()

            # Convert to BR3
            converter = MigrationConverter(v2_project)
            conversion_result = converter.convert()

            # Write migrated features.json
            if not dry_run and conversion_result.success:
                buildrunner_dir = directory / ".buildrunner"
                buildrunner_dir.mkdir(exist_ok=True)

                features_file = buildrunner_dir / "features.json"
                with open(features_file, 'w') as f:
                    json.dump(conversion_result.features_json, f, indent=2)

                progress.update(migrate_task, description="✅ BR2 data migrated to features.json")
            else:
                progress.update(migrate_task, description="✅ BR2 migration preview (dry-run)")

        console.print()
        console.print("[green]✅ Migration complete - now scanning codebase for features...[/green]")
        console.print()

    elif version_result.version == BRVersion.BR3:
        console.print("[green]✅ BuildRunner 3 already attached - updating PRD...[/green]")
        console.print()

    # Phase 1: Scan Codebase
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        # Scan
        scan_task = progress.add_task("🔍 Scanning codebase...", total=None)
        scanner = CodebaseScanner(directory)
        scan_result = scanner.scan()
        progress.update(scan_task, description="✅ Codebase scan complete")

    # Show scan results
    _show_scan_results(scan_result)

    # Phase 2: Extract Features
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        extract_task = progress.add_task("🧩 Extracting features...", total=None)
        extractor = FeatureExtractor()
        features = extractor.extract_features(scan_result)
        progress.update(extract_task, description=f"✅ Extracted {len(features)} features")

    # Show extracted features
    _show_features(features)

    # Phase 3: Synthesize PRD
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        synth_task = progress.add_task("📝 Generating PROJECT_SPEC.md...", total=None)
        synthesizer = PRDSynthesizer()

        if not dry_run:
            prd = synthesizer.synthesize(scan_result, output)
            progress.update(synth_task, description="✅ PROJECT_SPEC.md generated")
        else:
            prd = synthesizer.synthesize(scan_result, None)
            progress.update(synth_task, description="✅ PRD preview generated (dry-run)")

    # Phase 4: Generate CLAUDE.md with attach mode instructions
    claude_md_path = None
    if not dry_run:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            claude_task = progress.add_task("📋 Generating CLAUDE.md for attach mode...", total=None)
            generator = ClaudeMdGenerator(directory)
            claude_md_path = generator.generate_attach_mode(force=True)
            progress.update(claude_task, description="✅ CLAUDE.md generated with attach instructions")

    # Show summary
    console.print()
    if dry_run:
        console.print(Panel(
            "[yellow]Dry-run mode - no files written[/yellow]\n\n"
            f"Would write PROJECT_SPEC.md to:\n[cyan]{output}[/cyan]\n\n"
            "Run without --dry-run to create the file.",
            title="🔍 Preview",
            border_style="yellow"
        ))
    else:
        console.print(Panel(
            f"[green]✅ BuildRunner 3 attached successfully![/green]\n\n"
            f"**Files Generated:**\n"
            f"  • PROJECT_SPEC.md: [cyan]{output}[/cyan]\n"
            f"  • CLAUDE.md: [cyan]{claude_md_path}[/cyan]\n\n"
            f"**Next Steps:**\n"
            f"1. Open Claude Code in this directory\n"
            f"2. Claude will auto-read CLAUDE.md and know about your existing features\n"
            f"3. Ask Claude to build new features - it will check PROJECT_SPEC.md first\n"
            f"4. Features marked [cyan]DISCOVERED[/cyan] = already built, [cyan]PLANNED[/cyan] = ready to build\n\n"
            f"**CLAUDE.md Instructions:**\n"
            f"  • Auto-continue mode: Claude builds to 100% without pausing\n"
            f"  • Codebase awareness: Claude checks PROJECT_SPEC.md before building\n"
            f"  • Profile active: {generator.profile_manager.get_active_profile() or 'none'}",
            title="✅ Attach Complete",
            border_style="green"
        ))

    console.print()


def _show_scan_results(scan_result):
    """Display scan results in a table"""
    console.print()
    console.print("[bold cyan]📊 Scan Results[/bold cyan]")
    console.print()

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Metric", style="dim")
    table.add_column("Value", style="bold white")

    table.add_row("Files Scanned", str(scan_result.total_files))
    table.add_row("Lines of Code", f"{scan_result.total_lines:,}")
    table.add_row("Languages", ", ".join(scan_result.languages))
    if scan_result.frameworks:
        table.add_row("Frameworks", ", ".join(scan_result.frameworks))
    table.add_row("Code Artifacts", str(len(scan_result.artifacts)))
    table.add_row("Scan Time", f"{scan_result.scan_duration_seconds:.1f}s")

    console.print(table)
    console.print()


def _show_features(features):
    """Display extracted features in a table"""
    console.print()
    console.print("[bold cyan]🧩 Extracted Features[/bold cyan]")
    console.print()

    if not features:
        console.print("[yellow]No features detected[/yellow]")
        return

    table = Table(show_header=True, box=None)
    table.add_column("Feature", style="bold cyan")
    table.add_column("Artifacts", justify="right", style="white")
    table.add_column("Files", justify="right", style="white")
    table.add_column("Priority", style="yellow")
    table.add_column("Confidence", justify="right")

    for feature in features:
        # Confidence emoji
        if feature.confidence >= 0.8:
            conf_display = "🟢 High"
        elif feature.confidence >= 0.6:
            conf_display = "🟡 Med"
        else:
            conf_display = "🔴 Low"

        table.add_row(
            feature.name,
            str(len(feature.artifacts)),
            str(len(set(str(a.file_path) for a in feature.artifacts))),
            feature.priority.title(),
            conf_display
        )

    console.print(table)
    console.print()


if __name__ == "__main__":
    attach_app()
