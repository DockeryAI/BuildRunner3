"""
Parallel BUILD Coordination CLI Commands

Commands for managing multi-instance parallel BUILD spec execution.
Different from parallel_commands.py which handles sessions/workers.

Commands:
    br parallel build-status   - Show instances, phases, progress
    br parallel build-release  - Release stale instance claims
    br parallel build-finish   - Wait for completion, cleanup
"""

import json
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from core.parallel_build_coordinator import (
    ParallelBuildCoordinator,
    InstanceStatus,
)

console = Console()


def find_build_spec() -> Optional[Path]:
    """Find active BUILD spec in .buildrunner/builds/."""
    buildrunner_dir = Path.cwd() / ".buildrunner"
    if not buildrunner_dir.exists():
        return None

    # Check for parallel_state.json to find active build
    state_file = buildrunner_dir / "parallel_state.json"
    if state_file.exists():
        try:
            with open(state_file) as f:
                state = json.load(f)
                if "build_spec" in state:
                    spec_path = Path(state["build_spec"])
                    if spec_path.exists():
                        return spec_path
        except (json.JSONDecodeError, KeyError):
            pass

    # Fallback: find most recent BUILD_*.md
    builds_dir = buildrunner_dir / "builds"
    if builds_dir.exists():
        specs = list(builds_dir.glob("BUILD_*.md"))
        if specs:
            return max(specs, key=lambda p: p.stat().st_mtime)

    return None


def get_coordinator(build_spec: Optional[str] = None) -> ParallelBuildCoordinator:
    """Get coordinator for active or specified BUILD spec."""
    if build_spec:
        spec_path = Path(build_spec)
    else:
        spec_path = find_build_spec()
        if not spec_path:
            raise typer.BadParameter(
                "No BUILD spec found. Specify with --spec or ensure parallel_state.json exists"
            )

    if not spec_path.exists():
        raise typer.BadParameter(f"BUILD spec not found: {spec_path}")

    return ParallelBuildCoordinator(spec_path)


def build_status(
    spec: Optional[str] = typer.Option(None, "--spec", "-s", help="BUILD spec path"),
    auto_cleanup: bool = typer.Option(
        False, "--auto-cleanup", help="Auto-cleanup stale instances"
    ),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed info"),
):
    """
    Show parallel BUILD coordination status.

    Displays all instances, claimed phases, and progress.

    Example:
        br parallel build-status
        br parallel build-status --spec .buildrunner/builds/BUILD_3.5.md
        br parallel build-status --auto-cleanup
    """
    try:
        coord = get_coordinator(spec)
        status = coord.get_status()

        # Header panel
        spec_name = Path(status.get("build_spec", "unknown")).name
        coordinator_id = status.get("coordinator_id")
        coord_display = coordinator_id[:8] if coordinator_id else "None"

        console.print(
            Panel.fit(
                f"[bold]BUILD Spec:[/bold] {spec_name}\n"
                f"[bold]Coordinator:[/bold] {coord_display}",
                title="Parallel Build Status",
            )
        )

        # Instances table
        instances = coord.get_all_instances()
        stale_ids = coord.get_stale_instances()

        if instances:
            table = Table(title=f"Instances ({len(instances)})", show_header=True)
            table.add_column("ID", style="dim", width=12)
            table.add_column("Status")
            table.add_column("Phase")
            table.add_column("Progress", justify="right")
            table.add_column("Last Heartbeat")
            table.add_column("Files Locked", justify="right")

            for inst in instances:
                # Status color
                status_color = {
                    InstanceStatus.RUNNING: "green",
                    InstanceStatus.COMPLETED: "blue",
                    InstanceStatus.ABANDONED: "red",
                }.get(inst.status, "white")

                is_stale = inst.id in stale_ids
                status_text = f"[{status_color}]{inst.status.value}[/{status_color}]"
                if is_stale:
                    status_text += " [yellow](stale)[/yellow]"

                # Heartbeat age
                age = datetime.now() - inst.last_heartbeat
                age_seconds = max(0, age.total_seconds())  # Handle clock drift
                if age_seconds < 60:
                    hb_text = f"{int(age_seconds)}s ago"
                elif age_seconds < 3600:
                    hb_text = f"{int(age_seconds / 60)}m ago"
                else:
                    hb_text = f"{int(age_seconds / 3600)}h ago"

                if is_stale:
                    hb_text = f"[red]{hb_text}[/red]"

                table.add_row(
                    inst.id[:12],
                    status_text,
                    inst.phase or "-",
                    f"{inst.progress * 100:.0f}%",
                    hb_text,
                    str(len(inst.files_locked)),
                )

            console.print(table)
        else:
            console.print("[yellow]No instances registered[/yellow]")

        # Phase status
        phases = status.get("phases", {})
        console.print("\n[bold]Phase Status:[/bold]")
        console.print(f"  Total Phases: {phases.get('total', 0)}")
        console.print(f"  Completed: [green]{phases.get('completed', 0)}[/green]")
        console.print(f"  Claimed: [yellow]{phases.get('claimed', 0)}[/yellow]")
        console.print(f"  Available: [cyan]{phases.get('available', 0)}[/cyan]")

        completed_phases = status.get("completed_phases", [])
        if completed_phases:
            console.print(f"  Completed: {', '.join(completed_phases)}")

        # Available phases
        available = coord.get_available_phases()
        if available:
            console.print(f"\n[cyan]Available phases: {', '.join(available)}[/cyan]")
            console.print(
                "[dim]Run '/begin join' in another terminal to claim one[/dim]"
            )

        # Stale instance handling
        if stale_ids:
            console.print(f"\n[yellow]Found {len(stale_ids)} stale instance(s)[/yellow]")

            if auto_cleanup:
                cleaned = coord.cleanup_stale_instances()
                console.print(
                    f"[green]Cleaned up {len(cleaned)} stale instance(s)[/green]"
                )
            else:
                console.print(
                    "[dim]Use --auto-cleanup or 'br parallel build-release stale' to release[/dim]"
                )

        # Verbose info
        if verbose:
            console.print("\n[bold]Claimed Phases:[/bold]")
            claimed = coord.get_claimed_phases()
            if claimed:
                for phase, inst_id in claimed.items():
                    console.print(f"  Phase {phase}: {inst_id[:12]}")
            else:
                console.print("  [dim]None[/dim]")

        console.print()

    except typer.BadParameter as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def build_release(
    instance_id: str = typer.Argument(
        ..., help="Instance ID to release (or 'stale' for all stale)"
    ),
    spec: Optional[str] = typer.Option(None, "--spec", "-s", help="BUILD spec path"),
    force: bool = typer.Option(
        False, "--force", "-f", help="Force release without confirmation"
    ),
):
    """
    Release instance claims.

    Use 'stale' to release all stale instances, or provide specific ID.

    Example:
        br parallel build-release stale
        br parallel build-release abc123def456
        br parallel build-release stale --force
    """
    try:
        coord = get_coordinator(spec)

        if instance_id == "stale":
            stale = coord.get_stale_instances()
            if not stale:
                console.print("[green]No stale instances found[/green]")
                return

            console.print(f"[yellow]Found {len(stale)} stale instance(s):[/yellow]")
            for sid in stale:
                inst = coord.get_instance(sid)
                if inst:
                    console.print(f"  {sid[:12]} - Phase: {inst.phase or 'None'}")

            if not force:
                if not typer.confirm("Release all stale instances?"):
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            cleaned = coord.cleanup_stale_instances()
            console.print(f"[green]Released {len(cleaned)} instance(s)[/green]")
        else:
            # Find matching instance
            inst = coord.get_instance(instance_id)
            if not inst:
                # Try partial match
                all_instances = coord.get_all_instances()
                matches = [i for i in all_instances if i.id.startswith(instance_id)]
                if len(matches) == 1:
                    inst = matches[0]
                elif len(matches) > 1:
                    console.print(
                        f"[yellow]Ambiguous ID, matches: {[i.id[:12] for i in matches]}[/yellow]"
                    )
                    raise typer.Exit(1)
                else:
                    console.print(f"[red]Instance not found: {instance_id}[/red]")
                    raise typer.Exit(1)

            console.print("[yellow]Releasing instance:[/yellow]")
            console.print(f"  ID: {inst.id[:12]}")
            console.print(f"  Phase: {inst.phase or 'None'}")
            console.print(f"  Status: {inst.status.value}")

            if not force:
                if not typer.confirm("Release this instance?"):
                    console.print("[yellow]Cancelled[/yellow]")
                    raise typer.Exit(0)

            coord.release_instance(inst.id)
            console.print(f"[green]Released instance {inst.id[:12]}[/green]")

        console.print()

    except typer.BadParameter as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)


def build_finish(
    spec: Optional[str] = typer.Option(None, "--spec", "-s", help="BUILD spec path"),
    timeout: int = typer.Option(300, "--timeout", "-t", help="Wait timeout in seconds"),
    cleanup: bool = typer.Option(
        True, "--cleanup/--no-cleanup", help="Cleanup state file on finish"
    ),
):
    """
    Wait for all instances to complete and cleanup.

    Monitors progress and waits for all phases to complete.

    Example:
        br parallel build-finish
        br parallel build-finish --timeout 600
        br parallel build-finish --no-cleanup
    """
    try:
        coord = get_coordinator(spec)

        console.print("[bold]Waiting for parallel build completion...[/bold]\n")

        start_time = time.time()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Monitoring instances...", total=None)

            while True:
                status = coord.get_status()
                instances_info = status.get("instances", {})
                phases_info = status.get("phases", {})

                running = instances_info.get("running", 0)
                completed_phases = phases_info.get("completed", 0)
                total_phases = phases_info.get("total", 0)

                if running == 0:
                    # Check if build is actually complete or just abandoned
                    if completed_phases < total_phases:
                        progress.update(
                            task,
                            description="[yellow]No running instances but build incomplete[/yellow]",
                        )
                        console.print(
                            f"\n[yellow]Warning: {total_phases - completed_phases} phase(s) remain unclaimed with no running instances[/yellow]"
                        )
                    else:
                        progress.update(task, description="All instances completed")
                    break

                elapsed = time.time() - start_time
                if elapsed > timeout:
                    progress.update(task, description="[red]Timeout reached[/red]")
                    console.print(
                        f"\n[red]Timeout after {timeout}s with {running} instance(s) still running[/red]"
                    )
                    raise typer.Exit(1)

                # Check for stale and auto-cleanup
                stale = coord.get_stale_instances()
                if stale:
                    coord.cleanup_stale_instances()

                progress.update(
                    task,
                    description=f"Running: {running}, Phases: {completed_phases}/{total_phases}",
                )
                time.sleep(5)

        # Final status
        status = coord.get_status()
        instances_info = status.get("instances", {})
        phases_info = status.get("phases", {})

        console.print("\n[green]Build coordination complete![/green]")
        console.print(
            f"  Phases completed: {phases_info.get('completed', 0)}/{phases_info.get('total', 0)}"
        )
        console.print(f"  Total instances: {instances_info.get('total', 0)}")
        console.print(f"  Completed: {instances_info.get('completed', 0)}")

        # Cleanup state file
        if cleanup:
            state_file = coord.state_file
            if state_file.exists():
                state_file.unlink()
                console.print(f"\n[green]Cleaned up: {state_file}[/green]")

        console.print()

    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted - instances still running[/yellow]")
        raise typer.Exit(130)
    except typer.BadParameter as e:
        console.print(f"[red]{e}[/red]")
        raise typer.Exit(1)
    except Exception as e:
        console.print(f"[red]Error: {e}[/red]")
        raise typer.Exit(1)
