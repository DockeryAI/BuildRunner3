"""
Profile CLI Commands
Commands for managing personality profiles and user preferences
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel

from core.profile_manager import ProfileManager, ProfileError
from cli.config_manager import get_config_manager

app = typer.Typer(help="Personality profile management")
console = Console()


@app.command("activate")
def activate_profile(
    name: str = typer.Argument(..., help="Profile name to activate")
):
    """
    Activate a personality profile for this session.

    The profile will persist across Claude Code context clearing and compaction.
    Profiles are written to CLAUDE.md which is automatically read by Claude Code.

    Examples:
        br profile activate roy
        br profile activate roddy
    """
    try:
        manager = ProfileManager()
        claude_md = manager.activate_profile(name)

        profile_path = manager.get_profile_path(name)
        source = "project-specific" if profile_path.parent == manager.project_personalities_dir else "global"

        console.print(f"\n[bold green]✓[/bold green] Profile '[cyan]{name}[/cyan]' activated!")
        console.print(f"[dim]Source: {source}[/dim]")
        console.print(f"[dim]Written to: {claude_md}[/dim]\n")

        console.print("[yellow]Note:[/yellow] The profile will take effect on the next Claude Code request.")
        console.print("[dim]To deactivate: br profile deactivate[/dim]\n")

    except ProfileError as e:
        console.print(f"\n[bold red]✗[/bold red] {e}\n")
        raise typer.Exit(1)


@app.command("deactivate")
def deactivate_profile():
    """
    Deactivate the currently active profile.

    Removes CLAUDE.md and returns to default Claude behavior.
    """
    try:
        manager = ProfileManager()
        active = manager.get_active_profile()

        if not active:
            console.print("\n[yellow]No profile is currently active.[/yellow]\n")
            return

        manager.deactivate_profile()
        console.print(f"\n[bold green]✓[/bold green] Profile '[cyan]{active}[/cyan]' deactivated.")
        console.print("[dim]CLAUDE.md removed. Returning to default behavior.[/dim]\n")

    except ProfileError as e:
        console.print(f"\n[bold red]✗[/bold red] {e}\n")
        raise typer.Exit(1)


@app.command("list")
def list_profiles():
    """
    List all available personality profiles.

    Shows both project-specific and global profiles.
    """
    manager = ProfileManager()
    profiles = manager.list_profiles()
    active = manager.get_active_profile()

    if not profiles:
        console.print("\n[yellow]No profiles found.[/yellow]")
        console.print(f"\nSearched in:")
        console.print(f"  • Project: {manager.project_personalities_dir}")
        console.print(f"  • Global: {manager.global_personalities_dir}\n")
        return

    # Create table
    table = Table(title="\nAvailable Profiles", show_header=True, header_style="bold cyan")
    table.add_column("Profile", style="cyan")
    table.add_column("Source", style="dim")
    table.add_column("Status", style="green")

    for name, source in sorted(profiles.items()):
        status = "● ACTIVE" if name == active else ""
        table.add_row(name, source, status)

    console.print(table)
    console.print()

    if active:
        console.print(f"[dim]Current: {active}[/dim]")
        console.print(f"[dim]To deactivate: br profile deactivate[/dim]\n")
    else:
        console.print(f"[dim]To activate: br profile activate <name>[/dim]\n")


@app.command("show")
def show_profile(
    name: str = typer.Argument(..., help="Profile name to display")
):
    """
    Display the content of a profile.

    Shows the full markdown content of the specified profile.
    """
    try:
        manager = ProfileManager()
        content = manager.read_profile(name)
        profile_path = manager.get_profile_path(name)
        source = "project-specific" if profile_path.parent == manager.project_personalities_dir else "global"

        console.print(Panel(
            f"[cyan]{name}[/cyan] ({source})\n[dim]{profile_path}[/dim]",
            title="Profile",
            border_style="cyan"
        ))
        console.print()
        console.print(content)
        console.print()

    except ProfileError as e:
        console.print(f"\n[bold red]✗[/bold red] {e}\n")
        raise typer.Exit(1)


@app.command("status")
def profile_status():
    """
    Show current profile status.

    Displays which profile is active and where it's located.
    """
    manager = ProfileManager()
    active = manager.get_active_profile()

    if not active:
        console.print("\n[yellow]No profile is currently active.[/yellow]")
        console.print("[dim]To activate: br profile activate <name>[/dim]\n")
        return

    profile_path = manager.get_profile_path(active)
    source = "project-specific" if profile_path and profile_path.parent == manager.project_personalities_dir else "global"

    console.print(Panel(
        f"[bold green]●[/bold green] [cyan]{active}[/cyan]\n"
        f"[dim]Source: {source}[/dim]\n"
        f"[dim]File: {profile_path}[/dim]\n"
        f"[dim]Active in: {manager.claude_md}[/dim]",
        title="Active Profile",
        border_style="green"
    ))
    console.print()


@app.command("copy")
def copy_profile(
    name: str = typer.Argument(..., help="Profile name to copy"),
    from_source: str = typer.Option("global", "--from", help="Copy from 'global' or 'project'"),
    overwrite: bool = typer.Option(False, "--overwrite", help="Overwrite if exists")
):
    """
    Copy a profile between project and global locations.

    Examples:
        br profile copy roy --from global    # Copy global roy to project
        br profile copy myteam --from project --overwrite  # Copy to global
    """
    try:
        manager = ProfileManager()
        dest = manager.copy_profile(name, source=from_source, overwrite=overwrite)

        to_source = "project" if from_source == "global" else "global"
        console.print(f"\n[bold green]✓[/bold green] Profile '[cyan]{name}[/cyan]' copied")
        console.print(f"[dim]From: {from_source} → To: {to_source}[/dim]")
        console.print(f"[dim]Destination: {dest}[/dim]\n")

    except ProfileError as e:
        console.print(f"\n[bold red]✗[/bold red] {e}\n")
        raise typer.Exit(1)


@app.command("create")
def create_profile(
    name: str = typer.Argument(..., help="Profile name"),
    scope: str = typer.Option("project", "--scope", help="Create in 'project' or 'global'"),
    template: str = typer.Option(None, "--template", help="Base on existing profile")
):
    """
    Create a new personality profile.

    Opens the profile file in your default editor after creation.

    Examples:
        br profile create myprofile
        br profile create myteam --scope global
        br profile create custom --template roy
    """
    try:
        manager = ProfileManager()

        # Get content from template or use blank
        if template:
            content = manager.read_profile(template)
            console.print(f"[dim]Using template: {template}[/dim]")
        else:
            content = f"""# {name.title()} Personality

## Your Personality

Describe how Claude should respond in this profile.

## Catchphrases

- List common phrases or expressions
- Define speaking style

## Technical Quirks

- How to handle code reviews
- How to explain concepts
- Tone and style preferences

## Example Responses

Show examples of how to respond to common scenarios.
"""

        profile_path = manager.create_profile(name, content, scope=scope)

        console.print(f"\n[bold green]✓[/bold green] Profile '[cyan]{name}[/cyan]' created")
        console.print(f"[dim]Location: {profile_path}[/dim]\n")

        console.print("[yellow]Edit the profile:[/yellow]")
        console.print(f"  code {profile_path}\n")

        console.print("[yellow]Activate it:[/yellow]")
        console.print(f"  br profile activate {name}\n")

    except ProfileError as e:
        console.print(f"\n[bold red]✗[/bold red] {e}\n")
        raise typer.Exit(1)


@app.command("init")
def init_personalities(
    scope: str = typer.Option("both", "--scope", help="Initialize 'project', 'global', or 'both'")
):
    """
    Initialize personality directories with README.

    Creates the personalities directory structure for storing profiles.

    Examples:
        br profile init              # Initialize both project and global
        br profile init --scope project
        br profile init --scope global
    """
    try:
        manager = ProfileManager()
        created = manager.init_personalities_dir(scope=scope)

        console.print(f"\n[bold green]✓[/bold green] Personalities directories initialized:\n")
        for path in created:
            console.print(f"  • {path}")

        console.print(f"\n[yellow]Next steps:[/yellow]")
        if scope in ['project', 'both']:
            console.print(f"  1. Add personality files to: {manager.project_personalities_dir}")
        if scope in ['global', 'both']:
            console.print(f"  2. Add global personalities to: {manager.global_personalities_dir}")
        console.print(f"  3. Activate a profile: br profile activate <name>\n")

    except Exception as e:
        console.print(f"\n[bold red]✗[/bold red] Failed to initialize: {e}\n")
        raise typer.Exit(1)


@app.command("set-default")
def set_default_profile(
    name: str = typer.Argument(..., help="Profile to set as global default")
):
    """
    Set global default profile for ALL projects.

    The default profile will auto-activate in any project that doesn't
    already have a profile active.

    Examples:
        br profile set-default roy-concise
        br profile set-default none  # Clear default
    """
    try:
        # Validate profile exists
        if name.lower() != 'none':
            manager = ProfileManager()
            manager.read_profile(name)  # Will raise if not found

        # Store in global config
        config = get_config_manager()
        if name.lower() == 'none':
            config.set('profiles.default_profile', None, scope='global')
            console.print(f"\n[bold green]✓[/bold green] Cleared global default profile\n")
        else:
            config.set('profiles.default_profile', name, scope='global')
            console.print(f"\n[bold green]✓[/bold green] Set global default: [cyan]{name}[/cyan]")
            console.print(f"[dim]Will auto-activate in all new projects[/dim]\n")

    except ProfileError as e:
        console.print(f"\n[bold red]✗[/bold red] {e}\n")
        raise typer.Exit(1)


@app.command("get-default")
def get_default_profile():
    """
    Show the current global default profile.
    """
    config = get_config_manager()
    default = config.get('profiles.default_profile')

    if default:
        console.print(f"\n[bold]Global Default:[/bold] [cyan]{default}[/cyan]")
        console.print(f"[dim]Auto-activates in all new projects[/dim]\n")
    else:
        console.print(f"\n[yellow]No global default profile set[/yellow]")
        console.print(f"[dim]Use: br profile set-default <name>[/dim]\n")


if __name__ == "__main__":
    app()
