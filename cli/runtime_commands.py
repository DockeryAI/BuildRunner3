"""Runtime default management commands."""

from __future__ import annotations

import subprocess
from pathlib import Path

import typer
from rich.console import Console

runtime_app = typer.Typer(help="Project runtime defaults")
console = Console()
_RUNTIME_SCRIPT = Path.home() / ".buildrunner" / "scripts" / "br-runtime.sh"


def _run_runtime_script(args: list[str]) -> None:
    if not _RUNTIME_SCRIPT.exists():
        console.print(f"[red]❌ Runtime helper not found: {_RUNTIME_SCRIPT}[/red]")
        raise typer.Exit(1)

    result = subprocess.run(  # noqa: S603
        ["/bin/bash", str(_RUNTIME_SCRIPT), *args],
        capture_output=True,
        text=True,
        check=False,
    )

    if result.stdout:
        console.print(result.stdout.rstrip())
    if result.returncode != 0:
        if result.stderr:
            console.print(f"[red]{result.stderr.rstrip()}[/red]")
        raise typer.Exit(result.returncode)


@runtime_app.command("get")
def runtime_get() -> None:
    """Show the current project runtime default."""
    _run_runtime_script(["get"])


@runtime_app.command("set")
def runtime_set(
    runtime: str = typer.Argument(..., help="Runtime default to persist: codex or claude"),
) -> None:
    """Set the current project runtime default."""
    _run_runtime_script(["set", runtime])
