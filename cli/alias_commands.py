"""
Alias Commands - Project alias management for quick switching
"""

import typer
import subprocess
import os
from pathlib import Path
from rich.console import Console
from rich.table import Table
from core.alias_manager import alias_manager
from core.runtime.config import RuntimeConfigError, apply_runtime_selection, resolve_runtime_selection

console = Console()
alias_app = typer.Typer(help="Manage project aliases")


@alias_app.command("set")
def set_alias(
    alias: str = typer.Argument(..., help="Alias name (e.g., 'br3', 'myapp')"),
    project_path: str = typer.Argument(
        None, help="Project directory path (defaults to current directory)"
    ),
):
    """Set an alias for a project directory"""
    if not project_path:
        project_path = os.getcwd()

    try:
        alias_manager.set_alias(alias, project_path)
        console.print(f"✓ Alias '{alias}' set to: {project_path}", style="green")
    except ValueError as e:
        console.print(f"Error: {e}", style="red")
        raise typer.Exit(1)


@alias_app.command("remove")
def remove_alias(
    alias: str = typer.Argument(..., help="Alias name to remove"),
):
    """Remove a project alias"""
    if alias_manager.remove_alias(alias):
        console.print(f"✓ Alias '{alias}' removed", style="green")
    else:
        console.print(f"Alias '{alias}' not found", style="yellow")


@alias_app.command("list")
def list_aliases():
    """List all project aliases"""
    aliases = alias_manager.list_aliases()

    if not aliases:
        console.print("No aliases configured yet.", style="yellow")
        console.print("\nSet an alias with: br alias set <name> [path]")
        return

    table = Table(title="Project Aliases", show_header=True, header_style="bold magenta")
    table.add_column("Alias", style="cyan", no_wrap=True)
    table.add_column("Project Path", style="green")

    for alias, path in sorted(aliases.items()):
        table.add_row(alias, path)

    console.print(table)


@alias_app.command("jump")
def jump_to_alias(
    alias: str = typer.Argument(..., help="Alias name"),
    runtime: str | None = typer.Option(
        None,
        "--runtime",
        help="Override runtime when launching from alias (claude or codex)",
    ),
):
    """
    Jump to a project by alias and start Claude Code

    This command:
    1. Resolves the alias to a project path
    2. Changes to that directory
    3. Launches Claude Code with --dangerously-skip-permissions
    """
    project_path = alias_manager.get_alias(alias)

    if not project_path:
        console.print(f"Alias '{alias}' not found", style="red")
        console.print("\nAvailable aliases:")
        list_aliases()
        raise typer.Exit(1)

    # Validate path still exists
    if not Path(project_path).exists():
        console.print(f"Project path no longer exists: {project_path}", style="red")
        console.print(f"Remove this alias with: br alias remove {alias}")
        raise typer.Exit(1)

    console.print(f"Jumping to: {project_path}", style="cyan")

    # Change directory and launch Claude Code
    os.chdir(project_path)
    console.print(f"✓ Changed directory to: {os.getcwd()}", style="green")

    try:
        resolution = resolve_runtime_selection(explicit_runtime=runtime, project_root=project_path)
        apply_runtime_selection(resolution)
    except RuntimeConfigError as exc:
        console.print(f"Error: {exc}", style="red")
        raise typer.Exit(1)

    # Launch selected runtime
    launch_runtime = resolution.runtime
    if launch_runtime == "codex":
        console.print("Launching Codex...", style="cyan")
    else:
        console.print("Launching Claude Code...", style="cyan")
    try:
        if launch_runtime == "codex":
            subprocess.run(["codex"], check=False)
        else:
            subprocess.run(
                ["claude", "--dangerously-skip-permissions", project_path],
                check=False,  # Don't error if Claude Code exits normally
            )
    except FileNotFoundError:
        console.print(f"\nError: '{launch_runtime}' command not found", style="red")
        if launch_runtime == "claude":
            console.print("Install Claude Code CLI first: https://code.claude.ai", style="yellow")
        else:
            console.print("Install Codex CLI first: https://github.com/openai/codex", style="yellow")
        console.print(f"\nYou can manually navigate to: {project_path}", style="cyan")
        raise typer.Exit(1)


if __name__ == "__main__":
    alias_app()
