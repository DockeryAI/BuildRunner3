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
):
    """
    Jump to a project by alias and start Claude Code

    This command:
    1. Resolves the alias to a project path
    2. Changes to that directory
    3. Generates a project status prompt
    4. Copies it to clipboard
    5. Launches Claude Code with --dangerously-skip-permissions
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

    # Generate project status prompt
    prompt = alias_manager.get_project_status_prompt(project_path)

    # Copy prompt to clipboard
    try:
        subprocess.run(["pbcopy"], input=prompt.encode(), check=True, capture_output=True)
        console.print("✓ Project prompt copied to clipboard", style="green")
    except subprocess.CalledProcessError:
        console.print("⚠ Could not copy to clipboard (pbcopy not available)", style="yellow")
    except FileNotFoundError:
        console.print("⚠ Could not copy to clipboard (pbcopy not found)", style="yellow")

    # Change directory and launch Claude Code
    os.chdir(project_path)
    console.print(f"✓ Changed directory to: {os.getcwd()}", style="green")

    # Launch Claude Code
    console.print("Launching Claude Code...", style="cyan")
    try:
        subprocess.run(
            ["claude", "--dangerously-skip-permissions", project_path],
            check=False,  # Don't error if Claude Code exits normally
        )
    except FileNotFoundError:
        console.print("\nError: 'claude' command not found", style="red")
        console.print("Install Claude Code CLI first: https://code.claude.ai", style="yellow")
        console.print(f"\nYou can manually navigate to: {project_path}", style="cyan")
        console.print("And paste the clipboard content into Claude.", style="cyan")
        raise typer.Exit(1)


if __name__ == "__main__":
    alias_app()
