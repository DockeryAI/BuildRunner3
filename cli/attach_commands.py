"""BR3 Attach - Retrofit existing projects to BuildRunner 3"""

import typer
from pathlib import Path
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
from rich import print as rprint
from rich.prompt import Confirm
import logging
import json

from core.retrofit import CodebaseScanner, FeatureExtractor, PRDSynthesizer
from core.retrofit.version_detector import BRVersionDetector, BRVersion
from core.migration.v2_parser import V2ProjectParser
from core.migration.converter import MigrationConverter
from core.prd.prd_controller import get_prd_controller
from core.project_registry import get_project_registry
from core.shell_integration import get_shell_integration
from core.design_extractor import DesignExtractor
from core.enforcement_engine import ConfigGenerator

# Optional import - ClaudeMdGenerator may not exist yet
try:
    from core.claude_md_generator import ClaudeMdGenerator
    HAS_CLAUDE_MD = True
except ImportError:
    HAS_CLAUDE_MD = False
    logger.warning("ClaudeMdGenerator not available - CLAUDE.md generation will be skipped")

console = Console()
logger = logging.getLogger(__name__)


def attach_command(
    alias_or_directory: str = typer.Argument(
        None,
        help="Project alias (e.g., 'sales') or directory path"
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
    editor: str = typer.Option(
        "claude",
        "--editor",
        "-e",
        help="Editor preference: claude, cursor, windsurf"
    ),
    scan: bool = typer.Option(
        False,
        "--scan",
        help="Force codebase scan even if looks like alias"
    ),
):
    """
    Attach BuildRunner 3 to an existing project.

    Two modes:
    1. Quick register: br attach <alias> (e.g., br attach sales)
    2. Full scan: br attach /path/to/project or br attach --scan

    Quick register creates shell alias and registers project.
    Full scan analyzes codebase and generates PROJECT_SPEC.md.
    """
    # Detect if this is an alias (simple name) or directory path
    is_alias = False
    directory = None

    if alias_or_directory is None:
        # No argument - scan current directory
        directory = Path.cwd()
    elif not scan and "/" not in alias_or_directory and "\\" not in alias_or_directory:
        # Looks like an alias (no path separators)
        # Check if it's also a valid directory name in cwd
        potential_dir = Path.cwd() / alias_or_directory
        if potential_dir.exists() and potential_dir.is_dir():
            # Ambiguous - could be alias or subdirectory
            # Ask user
            console.print(f"[yellow]'{alias_or_directory}' could be:[/yellow]")
            console.print(f"  1. A project alias to register")
            console.print(f"  2. A subdirectory to scan: {potential_dir}")
            console.print()

            is_register = Confirm.ask("Register as project alias?", default=True)
            if is_register:
                is_alias = True
            else:
                directory = potential_dir
        else:
            # Not a directory, treat as alias
            is_alias = True
    else:
        # Has path separator or --scan flag - treat as directory
        directory = Path(alias_or_directory)

    # Mode 1: Quick register with alias
    if is_alias:
        alias = alias_or_directory
        directory = Path.cwd()

        console.print()
        console.print(Panel.fit(
            f"[bold cyan]Quick Register: {directory.name}[/bold cyan]\n\n"
            f"[white]Alias:[/white] [yellow]{alias}[/yellow]\n"
            f"[white]Directory:[/white] [yellow]{directory}[/yellow]\n"
            f"[white]Editor:[/white] [yellow]{editor}[/yellow]",
            border_style="cyan"
        ))
        console.print()

        # Create .buildrunner if not exists
        buildrunner_dir = directory / ".buildrunner"
        if not buildrunner_dir.exists():
            console.print("Creating .buildrunner directory...")
            buildrunner_dir.mkdir(exist_ok=True)

        # Check for PROJECT_SPEC.md
        spec_path = buildrunner_dir / "PROJECT_SPEC.md"
        if not spec_path.exists():
            console.print("[yellow]No PROJECT_SPEC.md found[/yellow]")
            create_spec = Confirm.ask("Create minimal PROJECT_SPEC.md?", default=True)

            if create_spec:
                minimal_spec = f"""# {directory.name}

**Version:** 1.0.0
**Status:** Attached

## Project Overview

TODO: Add project description

## Features

TODO: Document features
"""
                spec_path.write_text(minimal_spec)
                console.print(f"✓ Created {spec_path}")

        # Register project
        console.print()
        console.print("Registering project...")
        registry = get_project_registry()

        try:
            registry.register_project(
                alias=alias,
                project_path=directory,
                editor=editor,
                spec_path=".buildrunner/PROJECT_SPEC.md"
            )
            console.print(f"✓ Registered '{alias}' in project registry")
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]")
            raise typer.Exit(1)

        # Activate ALL BR3 Systems
        console.print()
        console.print("Activating ALL BuildRunner 3.0 systems...")
        console.print()

        # Find and run activation script
        activation_script = None
        for loc in [
            Path(__file__).parent.parent / ".buildrunner" / "scripts" / "activate-all-systems.sh",
            Path.home() / ".buildrunner" / "scripts" / "activate-all-systems.sh",
        ]:
            if loc.exists():
                activation_script = loc
                break

        if activation_script:
            import subprocess
            result = subprocess.run(
                ["bash", str(activation_script), str(directory)],
                capture_output=True,
                text=True
            )

            if result.returncode == 0:
                console.print(result.stdout)
            else:
                console.print(f"[yellow]Warning: Activation had issues[/yellow]")
                console.print(result.stderr)
        else:
            console.print("[yellow]  ⚠️ Activation script not found[/yellow]")

        # Create shell alias
        console.print()
        console.print("Creating shell alias...")
        shell = get_shell_integration()

        try:
            shell.add_alias(alias, str(directory), editor)
            config_path = shell.get_primary_config()
            console.print(f"✓ Added alias to {config_path}")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not create shell alias: {e}[/yellow]")

        # Success
        console.print()
        console.print(Panel(
            f"[green]✅ Project '{directory.name}' attached successfully![/green]\n\n"
            f"[white]Shell Alias:[/white]\n"
            f"  • Type [cyan]{alias}[/cyan] in terminal to launch {editor.title()} Code\n\n"
            f"[white]Next Steps:[/white]\n"
            f"1. Reload shell: [cyan]source ~/.zshrc[/cyan]\n"
            f"2. Launch editor: [cyan]{alias}[/cyan]\n"
            f"3. Start building!",
            title="✅ Attach Complete",
            border_style="green"
        ))
        console.print()
        return

    # Mode 2: Full codebase scan (original behavior)
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

    # Phase 1.5: Extract Design System
    design_system = None
    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console
    ) as progress:
        design_task = progress.add_task("🎨 Extracting design system...", total=None)
        design_extractor = DesignExtractor(directory)
        design_system = design_extractor.extract()

        if not dry_run:
            design_extractor.save()
            progress.update(design_task, description=f"✅ Design system extracted (confidence: {design_system.confidence:.0%})")
        else:
            progress.update(design_task, description=f"✅ Design system analyzed (dry-run)")

    # Show design system results
    _show_design_system(design_system)

    # Phase 1.75: Auto-Generate Required Configs (ENFORCEMENT)
    if not dry_run:
        console.print()
        console.print("[bold]🔧 Generating Required BR3 Configs (Enforcement)[/bold]")
        console.print()

        config_generator = ConfigGenerator(directory)
        generated = config_generator.generate_all()

        if generated:
            for item in generated:
                console.print(f"  ✅ Generated: {item}")
            console.print()
            console.print("[green]All required configs auto-generated![/green]")
        else:
            console.print("[dim]All configs already exist[/dim]")

        console.print()

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
            prd = synthesizer.synthesize(scan_result, output, project_root=directory)
            progress.update(synth_task, description="✅ PROJECT_SPEC.md generated")
        else:
            prd = synthesizer.synthesize(scan_result, None, project_root=directory)
            progress.update(synth_task, description="✅ PRD preview generated (dry-run)")

    # Phase 4: Generate CLAUDE.md with attach mode instructions (and design system guide)
    claude_md_path = None
    if not dry_run and HAS_CLAUDE_MD:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            claude_task = progress.add_task("📋 Generating CLAUDE.md for attach mode...", total=None)
            generator = ClaudeMdGenerator(directory)
            claude_md_path = generator.generate_attach_mode(force=True)
            progress.update(claude_task, description="✅ CLAUDE.md generated with attach instructions")
    elif not dry_run and design_system and design_system.confidence > 0.1:
        # Fallback: Write design system instructions to a separate file
        design_guide_path = directory / ".buildrunner" / "DESIGN_GUIDE.md"
        extractor = DesignExtractor(directory)
        extractor.design_system = design_system
        design_guide_content = extractor.generate_claude_instructions()
        design_guide_path.write_text(design_guide_content)
        console.print(f"\n[dim]💡 Design guide saved to {design_guide_path}[/dim]")

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


def _show_design_system(design_system):
    """Display extracted design system"""
    console.print()
    console.print("[bold cyan]🎨 Design System[/bold cyan]")
    console.print()

    if design_system.confidence < 0.1:
        console.print("[yellow]No design system detected[/yellow]")
        return

    table = Table(show_header=False, box=None, padding=(0, 2))
    table.add_column("Category", style="dim")
    table.add_column("Details", style="bold white")

    # Framework
    if design_system.framework:
        fw = design_system.framework
        fw_text = fw.name
        if fw.ui_library:
            fw_text += f" + {fw.ui_library}"
        if fw.styling_system:
            fw_text += f" ({fw.styling_system})"
        table.add_row("Framework", fw_text)

    # Design tokens
    token_count = (
        len(design_system.tokens.colors) +
        len(design_system.tokens.fonts) +
        len(design_system.tokens.font_sizes) +
        len(design_system.tokens.spacing)
    )
    if token_count > 0:
        token_details = []
        if design_system.tokens.colors:
            token_details.append(f"{len(design_system.tokens.colors)} colors")
        if design_system.tokens.fonts:
            token_details.append(f"{len(design_system.tokens.fonts)} fonts")
        if design_system.tokens.font_sizes:
            token_details.append(f"{len(design_system.tokens.font_sizes)} font sizes")
        if design_system.tokens.spacing:
            token_details.append(f"{len(design_system.tokens.spacing)} spacing")

        table.add_row("Design Tokens", ", ".join(token_details))

    # Components
    if design_system.components:
        table.add_row("Components", f"{len(design_system.components)} analyzed")

    # Naming conventions
    if design_system.naming_conventions:
        for category, convention in design_system.naming_conventions.items():
            table.add_row(f"{category.title()} Convention", convention)

    # Design system file
    if design_system.design_system_file:
        table.add_row("Design System File", design_system.design_system_file)

    # Confidence
    if design_system.confidence >= 0.8:
        conf_display = "🟢 High"
    elif design_system.confidence >= 0.5:
        conf_display = "🟡 Medium"
    else:
        conf_display = "🔴 Low"

    table.add_row("Extraction Confidence", f"{conf_display} ({design_system.confidence:.0%})")

    console.print(table)
    console.print()
    console.print("[dim]Design system saved to .buildrunner/design-system.json[/dim]")
    console.print()


if __name__ == "__main__":
    # Run as standalone script
    import sys
    from typer import run
    run(attach_command)
