"""Upgrade packaged BuildRunner assets in the user environment."""

import typer
from rich.console import Console

from core.asset_resolver import install_legacy_attach_stub, sync_packaged_templates

console = Console()


def upgrade_command() -> None:
    """Sync packaged templates to ~/.buildrunner/templates and retire legacy br-attach."""
    try:
        template_result = sync_packaged_templates()
        attach_result = install_legacy_attach_stub()
    except Exception as exc:
        console.print(f"[red]❌ Upgrade failed: {exc}[/red]")
        raise typer.Exit(1) from exc

    written = len(template_result.written)
    skipped = len(template_result.skipped)

    if written:
        console.print(
            f"[green]✅ Synced {written} template file(s) to ~/.buildrunner/templates[/green]"
        )
    else:
        console.print("[dim]Templates already up to date in ~/.buildrunner/templates[/dim]")

    if skipped:
        console.print(f"[dim]Skipped {skipped} unchanged template file(s)[/dim]")

    if attach_result.changed and attach_result.backup_path is not None:
        console.print(
            f"[yellow]⚠️  Moved legacy br-attach to {attach_result.backup_path}[/yellow]"
        )
    elif attach_result.stub_path is not None:
        console.print("[dim]Legacy br-attach stub already installed[/dim]")
