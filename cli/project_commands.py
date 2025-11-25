"""
Project Commands - Initialize and manage BuildRunner projects with shell aliases

Commands:
- br init [alias] - Initialize new project with planning mode
- br attach <alias> - Register existing project and create shell alias
- br project list - List all registered projects
- br project remove <alias> - Unregister project
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich.prompt import Prompt, Confirm
from rich import print as rprint
import logging

from core.project_registry import get_project_registry, ProjectInfo
from core.shell_integration import get_shell_integration
from core.planning_mode import PlanningModeDetector
from core.prd.prd_controller import get_prd_controller

console = Console()
logger = logging.getLogger(__name__)

project_app = typer.Typer(help="Project initialization and management")


@project_app.command("init")
def init_project(
    alias: str = typer.Argument(
        None,
        help="Short alias for this project (e.g., 'sales', 'myapp')"
    ),
    directory: Path = typer.Option(
        None,
        "--dir",
        "-d",
        help="Project directory (defaults to current directory)"
    ),
    template: str = typer.Option(
        "standard",
        "--template",
        "-t",
        help="Planning template: quick, standard, complete"
    ),
    editor: str = typer.Option(
        "claude",
        "--editor",
        "-e",
        help="Editor preference: claude, cursor, windsurf"
    ),
    skip_planning: bool = typer.Option(
        False,
        "--skip-planning",
        help="Skip planning mode, just initialize structure"
    )
):
    """
    Initialize a new BuildRunner project

    This command:
    1. Creates .buildrunner/ directory structure
    2. Enters planning mode to create PROJECT_SPEC.md (unless --skip-planning)
    3. Registers project with an alias
    4. Creates shell alias for quick launch

    Example:
        cd ~/Projects/my-new-app
        br init myapp

    Later:
        myapp  # Launches Claude Code in that directory
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

    # Get project name from directory if not provided
    project_name = directory.name

    # Prompt for alias if not provided
    if alias is None:
        suggested_alias = project_name.lower().replace(" ", "-").replace("_", "-")
        alias = Prompt.ask(
            "Enter alias for this project",
            default=suggested_alias
        )

    # Check if alias already exists
    registry = get_project_registry()
    if registry.alias_exists(alias):
        existing = registry.get_project(alias)
        if existing.path != str(directory):
            console.print(f"[red]Error: Alias '{alias}' already registered to {existing.path}[/red]")
            console.print(f"[yellow]Use 'br project remove {alias}' first or choose a different alias[/yellow]")
            raise typer.Exit(1)

    # Welcome message
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]BuildRunner 3 - Initialize Project[/bold cyan]\n\n"
        f"[white]Project:[/white] [yellow]{project_name}[/yellow]\n"
        f"[white]Alias:[/white] [yellow]{alias}[/yellow]\n"
        f"[white]Directory:[/white] [yellow]{directory}[/yellow]\n"
        f"[white]Template:[/white] [yellow]{template}[/yellow]",
        border_style="cyan"
    ))
    console.print()

    # Step 1: Create .buildrunner structure
    console.print("[bold]Step 1:[/bold] Creating project structure...")
    buildrunner_dir = directory / ".buildrunner"
    buildrunner_dir.mkdir(exist_ok=True)

    spec_path = buildrunner_dir / "PROJECT_SPEC.md"
    features_path = buildrunner_dir / "features.json"

    console.print(f"  ✓ Created {buildrunner_dir}")

    # Step 2: Planning mode (unless skipped)
    if not skip_planning:
        console.print()
        console.print("[bold]Step 2:[/bold] Entering planning mode...")
        console.print()

        # Initialize planning mode
        planner = PlanningMode(project_root=directory, template=template)

        try:
            # Run planning mode (interactive)
            prd = planner.run_interactive()

            # Write PROJECT_SPEC.md
            spec_path.write_text(planner.generate_spec_markdown(prd))
            console.print(f"  ✓ Created {spec_path}")

            # Create features.json
            features_data = {
                "project": project_name,
                "version": "1.0.0",
                "features": [],
                "status": "initialized"
            }
            import json
            features_path.write_text(json.dumps(features_data, indent=2))
            console.print(f"  ✓ Created {features_path}")

        except KeyboardInterrupt:
            console.print("\n[yellow]Planning cancelled by user[/yellow]")
            if not Confirm.ask("Continue with project initialization anyway?"):
                console.print("[red]Initialization cancelled[/red]")
                raise typer.Exit(1)

    else:
        console.print("[yellow]  Skipped planning mode[/yellow]")

        # Create minimal PROJECT_SPEC.md
        if not spec_path.exists():
            minimal_spec = f"""# {project_name}

**Version:** 1.0.0
**Status:** Initialized

## Project Overview

TODO: Add project description

## Features

TODO: Add features
"""
            spec_path.write_text(minimal_spec)
            console.print(f"  ✓ Created minimal {spec_path}")

    # Step 3: Register project
    console.print()
    console.print("[bold]Step 3:[/bold] Registering project...")

    try:
        project_info = registry.register_project(
            alias=alias,
            project_path=directory,
            editor=editor,
            spec_path=".buildrunner/PROJECT_SPEC.md"
        )
        console.print(f"  ✓ Registered '{alias}' in project registry")
    except ValueError as e:
        console.print(f"  [red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Step 4: Activate ALL BR3 Systems
    console.print()
    console.print("[bold]Step 4:[/bold] Activating ALL BuildRunner 3.0 systems...")
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
            console.print(f"[yellow]Warning: Activation script had issues[/yellow]")
            console.print(result.stderr)
    else:
        console.print("[yellow]  ⚠️ Activation script not found - manual setup required[/yellow]")
        console.print(f"  Run: bash ~/.buildrunner/scripts/activate-all-systems.sh {directory}")

    # Step 5: Create shell alias
    console.print()
    console.print("[bold]Step 5:[/bold] Creating shell alias...")

    shell_integration = get_shell_integration()
    try:
        shell_integration.add_alias(alias, str(directory), editor)
        config_path = shell_integration.get_primary_config()
        console.print(f"  ✓ Added alias to {config_path}")
        console.print(f"  ✓ Run: [cyan]source {config_path}[/cyan] to activate")
    except Exception as e:
        console.print(f"  [yellow]Warning: Could not create shell alias: {e}[/yellow]")

    # Success summary
    console.print()
    console.print(Panel(
        f"[green]✅ Project '{project_name}' initialized successfully![/green]\n\n"
        f"[white]Files Created:[/white]\n"
        f"  • PROJECT_SPEC.md: [cyan]{spec_path}[/cyan]\n"
        f"  • features.json: [cyan]{features_path}[/cyan]\n\n"
        f"[white]Shell Alias:[/white]\n"
        f"  • Type [cyan]{alias}[/cyan] in terminal to launch {editor.title()} Code in this directory\n"
        f"  • Or use: [cyan]br project jump {alias}[/cyan]\n\n"
        f"[white]Next Steps:[/white]\n"
        f"1. Reload shell: [cyan]source ~/.zshrc[/cyan] (or ~/.bashrc)\n"
        f"2. Launch editor: [cyan]{alias}[/cyan]\n"
        f"3. Start building features!",
        title="✅ Initialization Complete",
        border_style="green"
    ))
    console.print()


@project_app.command("attach")
def attach_project(
    alias: str = typer.Argument(
        ...,
        help="Short alias for this project (e.g., 'sales', 'myapp')"
    ),
    directory: Path = typer.Option(
        None,
        "--dir",
        "-d",
        help="Project directory (defaults to current directory)"
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
        help="Scan codebase and generate PROJECT_SPEC.md"
    )
):
    """
    Attach BuildRunner to an existing project

    This command:
    1. Registers project with an alias
    2. Creates shell alias for quick launch
    3. Optionally scans codebase to generate PROJECT_SPEC.md

    Example:
        cd ~/Projects/my-existing-app
        br project attach myapp

    Later:
        myapp  # Launches Claude Code in that directory
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

    project_name = directory.name

    # Check if alias already exists
    registry = get_project_registry()
    if registry.alias_exists(alias):
        existing = registry.get_project(alias)
        if existing.path != str(directory):
            console.print(f"[red]Error: Alias '{alias}' already registered to {existing.path}[/red]")
            console.print(f"[yellow]Use 'br project remove {alias}' first or choose a different alias[/yellow]")
            raise typer.Exit(1)
        console.print(f"[yellow]Alias '{alias}' already registered to this directory, updating...[/yellow]")

    # Welcome
    console.print()
    console.print(Panel.fit(
        f"[bold cyan]BuildRunner 3 - Attach to Project[/bold cyan]\n\n"
        f"[white]Project:[/white] [yellow]{project_name}[/yellow]\n"
        f"[white]Alias:[/white] [yellow]{alias}[/yellow]\n"
        f"[white]Directory:[/white] [yellow]{directory}[/yellow]",
        border_style="cyan"
    ))
    console.print()

    # Create .buildrunner if not exists
    buildrunner_dir = directory / ".buildrunner"
    if not buildrunner_dir.exists():
        console.print("[bold]Step 1:[/bold] Creating .buildrunner directory...")
        buildrunner_dir.mkdir(exist_ok=True)
        console.print(f"  ✓ Created {buildrunner_dir}")
    else:
        console.print("[bold]Step 1:[/bold] Found existing .buildrunner directory")

    # Check for PROJECT_SPEC.md
    spec_path = buildrunner_dir / "PROJECT_SPEC.md"

    if not spec_path.exists():
        if scan:
            # Run attach command to scan and generate spec
            console.print()
            console.print("[bold]Step 2:[/bold] Scanning codebase to generate PROJECT_SPEC.md...")
            console.print("[yellow]Note: This may take a few moments for large codebases[/yellow]")
            console.print()

            # Import and run attach command
            from cli.attach_commands import attach_command

            try:
                attach_command(
                    alias_or_directory=str(directory),
                    output=None,
                    dry_run=False,
                    editor=editor,
                    scan=True
                )
            except SystemExit:
                pass

        else:
            console.print()
            console.print("[yellow]Warning: No PROJECT_SPEC.md found[/yellow]")
            create_spec = Confirm.ask("Would you like to create a minimal PROJECT_SPEC.md?", default=True)

            if create_spec:
                minimal_spec = f"""# {project_name}

**Version:** 1.0.0
**Status:** Attached

## Project Overview

TODO: Add project description

## Features

TODO: Document existing features
"""
                spec_path.write_text(minimal_spec)
                console.print(f"  ✓ Created minimal PROJECT_SPEC.md")
                console.print(f"  [yellow]Edit {spec_path} to document your features[/yellow]")
            else:
                console.print("[yellow]  Skipped PROJECT_SPEC.md creation[/yellow]")

    else:
        console.print(f"[bold]Step 2:[/bold] Found existing PROJECT_SPEC.md at {spec_path}")

    # Register project
    console.print()
    console.print("[bold]Step 3:[/bold] Registering project...")

    try:
        registry.register_project(
            alias=alias,
            project_path=directory,
            editor=editor,
            spec_path=".buildrunner/PROJECT_SPEC.md"
        )
        console.print(f"  ✓ Registered '{alias}' in project registry")
    except ValueError as e:
        console.print(f"  [red]Error: {e}[/red]")
        raise typer.Exit(1)

    # Activate ALL BR3 Systems
    console.print()
    console.print("[bold]Step 4:[/bold] Activating ALL BuildRunner 3.0 systems...")
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
            console.print(f"[yellow]Warning: Activation script had issues[/yellow]")
            console.print(result.stderr)
    else:
        console.print("[yellow]  ⚠️ Activation script not found - using basic setup[/yellow]")

    # Create shell alias
    console.print()
    console.print("[bold]Step 5:[/bold] Creating shell alias...")

    shell_integration = get_shell_integration()
    try:
        shell_integration.add_alias(alias, str(directory), editor)
        config_path = shell_integration.get_primary_config()
        console.print(f"  ✓ Added alias to {config_path}")
    except Exception as e:
        console.print(f"  [yellow]Warning: Could not create shell alias: {e}[/yellow]")

    # Success
    console.print()
    console.print(Panel(
        f"[green]✅ Project '{project_name}' attached successfully![/green]\n\n"
        f"[white]Shell Alias:[/white]\n"
        f"  • Type [cyan]{alias}[/cyan] in terminal to launch {editor.title()} Code\n\n"
        f"[white]Next Steps:[/white]\n"
        f"1. Reload shell: [cyan]source {config_path}[/cyan]\n"
        f"2. Launch editor: [cyan]{alias}[/cyan]\n"
        f"3. Start building!",
        title="✅ Attach Complete",
        border_style="green"
    ))
    console.print()


@project_app.command("list")
def list_projects():
    """List all registered BuildRunner projects"""
    registry = get_project_registry()
    projects = registry.list_projects()

    if not projects:
        console.print("[yellow]No projects registered yet[/yellow]")
        console.print()
        console.print("Register a project with:")
        console.print("  • [cyan]br project attach <alias>[/cyan]  (existing project)")
        console.print("  • [cyan]br project init[/cyan]  (new project)")
        return

    console.print()
    console.print(f"[bold cyan]Registered Projects ({len(projects)})[/bold cyan]")
    console.print()

    table = Table(show_header=True, header_style="bold magenta")
    table.add_column("Alias", style="cyan", no_wrap=True)
    table.add_column("Path", style="white")
    table.add_column("Editor", style="yellow")
    table.add_column("Status", style="green")

    for project in sorted(projects, key=lambda p: p.alias):
        # Validate project
        validation = registry.validate_project(project.alias)

        if validation["valid"]:
            status = "✅ Valid"
        elif validation["exists"]:
            status = "⚠️  Incomplete"
        else:
            status = "❌ Missing"

        table.add_row(
            project.alias,
            project.path,
            project.editor,
            status
        )

    console.print(table)
    console.print()
    console.print(f"[dim]Launch a project: [cyan]<alias>[/cyan] (e.g., {projects[0].alias})[/dim]")
    console.print()


@project_app.command("remove")
def remove_project(
    alias: str = typer.Argument(
        ...,
        help="Project alias to remove"
    ),
    keep_shell_alias: bool = typer.Option(
        False,
        "--keep-shell-alias",
        help="Keep shell alias in config file"
    )
):
    """
    Remove a project from BuildRunner registry

    This removes the project from registry and optionally removes
    the shell alias from your .zshrc/.bashrc
    """
    registry = get_project_registry()
    project = registry.get_project(alias)

    if not project:
        console.print(f"[red]Project '{alias}' not found[/red]")
        console.print()
        console.print("Available projects:")
        list_projects()
        raise typer.Exit(1)

    console.print()
    console.print(f"[yellow]Removing project:[/yellow] {alias}")
    console.print(f"[dim]Path:[/dim] {project.path}")
    console.print()

    if not Confirm.ask(f"Remove '{alias}' from registry?", default=False):
        console.print("[yellow]Cancelled[/yellow]")
        raise typer.Exit(0)

    # Remove from registry
    registry.remove_project(alias)
    console.print(f"✓ Removed '{alias}' from project registry")

    # Remove shell alias
    if not keep_shell_alias:
        shell_integration = get_shell_integration()
        try:
            shell_integration.remove_alias(alias)
            console.print(f"✓ Removed shell alias from config")
            console.print(f"  Run: [cyan]source ~/.zshrc[/cyan] to apply changes")
        except Exception as e:
            console.print(f"[yellow]Warning: Could not remove shell alias: {e}[/yellow]")

    console.print()
    console.print("[green]✅ Project removed[/green]")
    console.print()


@project_app.command("jump")
def jump_to_project(
    alias: str = typer.Argument(
        ...,
        help="Project alias"
    )
):
    """
    Jump to a project directory

    Note: In most cases, just type the alias directly in your terminal.
    This command is for when shell aliases aren't loaded yet.
    """
    registry = get_project_registry()
    project = registry.get_project(alias)

    if not project:
        console.print(f"[red]Project '{alias}' not found[/red]")
        raise typer.Exit(1)

    # Validate project still exists
    project_path = Path(project.path)
    if not project_path.exists():
        console.print(f"[red]Project path no longer exists: {project_path}[/red]")
        console.print(f"[yellow]Remove this project with: br project remove {alias}[/yellow]")
        raise typer.Exit(1)

    # Update last accessed
    registry.update_last_accessed(alias)

    console.print(f"[cyan]Jumping to {alias}...[/cyan]")
    console.print(f"[dim]Path: {project_path}[/dim]")
    console.print()

    # Launch editor
    import subprocess
    import os

    os.chdir(project_path)

    editor_commands = {
        "claude": ["claude", "--dangerously-skip-permissions", str(project_path)],
        "cursor": ["cursor", "--disable-extensions", str(project_path)],
        "windsurf": ["windsurf", str(project_path)]
    }

    cmd = editor_commands.get(project.editor, ["claude", "--dangerously-skip-permissions", str(project_path)])

    try:
        subprocess.run(cmd, check=False)
    except FileNotFoundError:
        console.print(f"[red]Error: '{project.editor}' command not found[/red]")
        console.print(f"[yellow]Install {project.editor.title()} CLI first[/yellow]")
        raise typer.Exit(1)


if __name__ == "__main__":
    project_app()
