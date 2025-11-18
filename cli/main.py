"""
BuildRunner 3.0 CLI

Main command-line interface with automated debugging and behavior config.
"""

import json
import sys
import time
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.progress import Progress, SpinnerColumn, TextColumn

from cli.config_manager import ConfigManager, ConfigError, get_config_manager
from cli.auto_pipe import CommandPiper, PipeError, auto_pipe_command
from cli.error_watcher import ErrorWatcher, WatcherError, start_watcher
from core.feature_registry import FeatureRegistry
from core.status_generator import StatusGenerator
from core.governance import get_governance_manager, GovernanceError
from core.governance_enforcer import get_enforcer, EnforcementError
from core.architecture_guard import ArchitectureGuard, ArchitectureViolation
from core.self_service import SelfServiceManager, ServiceRequirement
from core.prd_wizard import PRDWizard, SpecState

# Import new command groups
from cli.spec_commands import spec_app, design_app
from cli.tasks_commands import tasks_app
from cli.run_commands import run_app
from cli.build_commands import build_app
from cli.gaps_commands import gaps_app
from cli.quality_commands import quality_app
from cli.migrate import migrate_app
from cli.security_commands import security_app
from cli.routing_commands import routing_app
from cli.telemetry_commands import telemetry_app
from cli.parallel_commands import parallel_app


app = typer.Typer(
    name="br",
    help="BuildRunner 3.0 - Git-backed governance for AI-assisted development",
    add_completion=False
)

# Add command groups
app.add_typer(spec_app, name="spec")
app.add_typer(design_app, name="design")
app.add_typer(tasks_app, name="tasks")
app.add_typer(run_app, name="run")
app.add_typer(build_app, name="build")
app.add_typer(gaps_app, name="gaps")
app.add_typer(quality_app, name="quality")
app.add_typer(migrate_app, name="migrate")
app.add_typer(security_app, name="security")
app.add_typer(routing_app, name="routing")
app.add_typer(telemetry_app, name="telemetry")
app.add_typer(parallel_app, name="parallel")

# Create guard and service command groups
guard_app = typer.Typer(help="Architecture guard commands")
service_app = typer.Typer(help="Self-service commands")

app.add_typer(guard_app, name="guard")
app.add_typer(service_app, name="service")

console = Console()


# ===== Helper Functions =====

def get_project_root() -> Path:
    """Get project root directory."""
    return Path.cwd()


def retry_with_backoff(func, max_retries: int = 3, delays: list = [1, 2, 4, 8]):
    """
    Retry function with exponential backoff.

    Args:
        func: Function to retry
        max_retries: Maximum number of retries
        delays: Delay in seconds for each retry

    Returns:
        Function result if successful

    Raises:
        Exception: If all retries fail
    """
    last_exception = None

    for attempt in range(max_retries):
        try:
            return func()
        except Exception as e:
            last_exception = e
            if attempt < max_retries - 1:
                delay = delays[attempt] if attempt < len(delays) else delays[-1]
                console.print(
                    f"[yellow]⚠️  Attempt {attempt + 1} failed: {e}[/yellow]"
                )
                console.print(f"[yellow]Retrying in {delay}s...[/yellow]")
                time.sleep(delay)

    raise last_exception


def handle_error(error: Exception, show_debug_hint: bool = True):
    """Handle errors with rich formatting."""
    console.print(f"[red]❌ Error: {error}[/red]")
    if show_debug_hint:
        console.print("[dim]💡 Tip: Run 'br debug' for automated diagnostics[/dim]")


# ===== Core Commands =====

@app.command()
def init(
    project_name: str = typer.Argument(..., help="Project name"),
    force: bool = typer.Option(False, "--force", "-f", help="Force initialization")
):
    """Initialize a new BuildRunner project."""
    try:
        project_root = get_project_root()
        buildrunner_dir = project_root / ".buildrunner"

        if buildrunner_dir.exists() and not force:
            console.print("[red]❌ Project already initialized![/red]")
            console.print("[dim]Use --force to reinitialize[/dim]")
            raise typer.Exit(1)

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Initializing project...", total=None)

            # Create directory structure
            buildrunner_dir.mkdir(exist_ok=True)
            (buildrunner_dir / "context").mkdir(exist_ok=True)
            (buildrunner_dir / "governance").mkdir(exist_ok=True)
            (buildrunner_dir / "standards").mkdir(exist_ok=True)

            # Initialize features.json
            features_data = {
                "project": project_name,
                "version": "1.0.0",
                "status": "in_development",
                "last_updated": time.strftime("%Y-%m-%dT%H:%M:%SZ"),
                "features": [],
                "metrics": {
                    "features_complete": 0,
                    "features_in_progress": 0,
                    "features_planned": 0,
                    "completion_percentage": 0
                }
            }

            features_file = buildrunner_dir / "features.json"
            with open(features_file, 'w') as f:
                json.dump(features_data, f, indent=2)

            # Initialize project behavior config
            config_manager = ConfigManager(project_root)
            config_manager.init_project_config()

            progress.update(task, completed=True)

        console.print(f"[green]✅ Initialized BuildRunner project: {project_name}[/green]")
        console.print(f"[dim]Location: {buildrunner_dir}[/dim]")

        # Auto-launch Claude Code planning mode for new projects only
        spec_path = buildrunner_dir / "PROJECT_SPEC.md"
        if not spec_path.exists():
            # New project - trigger planning mode in Claude Code
            console.print(f"\n[bold yellow]→ Go to Claude Code and type:[/bold yellow]")
            console.print(f"   [cyan]{project_name}[/cyan]\n")

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


@app.command()
def plan(
    project_name: str = typer.Argument(None, help="Project name (optional if in project directory)")
):
    """Start interactive planning mode with Claude Code to create PROJECT_SPEC"""
    try:
        # Determine project root
        if project_name:
            project_root = Path.cwd() / project_name
        else:
            project_root = Path.cwd()

        buildrunner_dir = project_root / ".buildrunner"
        spec_path = buildrunner_dir / "PROJECT_SPEC.md"

        # Check if project exists
        if not buildrunner_dir.exists():
            console.print(f"[red]❌ No BuildRunner project found[/red]")
            if project_name:
                console.print(f"[dim]Run 'br init {project_name}' first[/dim]")
            else:
                console.print(f"[dim]Run 'br init <project>' first[/dim]")
            raise typer.Exit(1)

        # Check if spec already exists
        if spec_path.exists():
            console.print(f"[yellow]⚠️  PROJECT_SPEC.md already exists[/yellow]")
            console.print(f"[dim]Location: {spec_path}[/dim]")

            overwrite = typer.confirm("Start new planning session (will overwrite)?", default=False)
            if not overwrite:
                console.print("[dim]Planning cancelled[/dim]")
                raise typer.Exit(0)

        # Output planning trigger
        console.print("\n" + "="*70)
        console.print("  🧠 PLANNING MODE")
        console.print("="*70)
        console.print()
        console.print("[bold cyan]→ Go to Claude Code and say:[/bold cyan]")
        console.print(f'   [yellow]"plan {project_root.name}"[/yellow]\n')
        console.print("[dim]Claude will lead an interactive brainstorming session to build your PRD.[/dim]\n")
        console.print(f"[dim]Project: {project_root}[/dim]")
        console.print(f"[dim]PRD will be saved to: {spec_path}[/dim]\n")

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


@app.command()
def status():
    """Show project status and progress."""
    try:
        registry = FeatureRegistry()
        data = registry.load()

        # Display header
        console.print(Panel.fit(
            f"[bold]{data.get('project', 'Unknown')}[/bold] - v{data.get('version', '1.0.0')}",
            title="📊 Project Status"
        ))

        # Display metrics
        metrics = data.get('metrics', {})
        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Metric")
        table.add_column("Value", justify="right")

        table.add_row("Features Complete", str(metrics.get('features_complete', 0)))
        table.add_row("Features In Progress", str(metrics.get('features_in_progress', 0)))
        table.add_row("Features Planned", str(metrics.get('features_planned', 0)))
        table.add_row("Completion", f"{metrics.get('completion_percentage', 0)}%")

        console.print(table)

        # Show orchestration status if tasks exist
        try:
            from cli.tasks_commands import get_task_queue
            from core.task_queue import TaskStatus

            queue = get_task_queue()
            if len(queue.tasks) > 0:
                console.print("\n[bold cyan]Task Orchestration:[/bold cyan]")

                stats = queue.get_progress()
                orch_table = Table(show_header=False)
                orch_table.add_column("Metric", style="white")
                orch_table.add_column("Value", style="green", justify="right")

                orch_table.add_row("Total Tasks", str(stats['total']))
                orch_table.add_row("Completed", str(stats['completed']))
                orch_table.add_row("In Progress", str(stats['in_progress']))
                orch_table.add_row("Ready", str(len(queue.get_ready_tasks())))
                orch_table.add_row("Failed", str(stats['failed']))

                if stats['total'] > 0:
                    completion = (stats['completed'] / stats['total']) * 100
                    orch_table.add_row("Progress", f"{completion:.1f}%")

                console.print(orch_table)

                ready_count = len(queue.get_ready_tasks())
                if ready_count > 0:
                    console.print(f"\n[dim]💡 Run 'br run --auto' to execute {ready_count} ready tasks[/dim]")

        except Exception:
            # Silently skip if orchestration not initialized
            pass

        # List features
        features = data.get('features', [])
        if features:
            console.print("\n[bold]Features:[/bold]")
            for feature in features:
                status_icon = {
                    'complete': '✅',
                    'in_progress': '🚧',
                    'planned': '📋',
                    'blocked': '🚫'
                }.get(feature.get('status'), '❓')

                console.print(
                    f"  {status_icon} {feature.get('name')} "
                    f"[dim]({feature.get('id')})[/dim]"
                )

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


@app.command()
def generate():
    """Generate STATUS.md from features.json."""
    try:
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Generating STATUS.md...", total=None)

            generator = StatusGenerator()
            status_file = generator.generate()

            progress.update(task, completed=True)

        console.print(f"[green]✅ Generated: {status_file}[/green]")

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


# ===== Feature Commands =====

feature_app = typer.Typer(help="Manage features")
app.add_typer(feature_app, name="feature")


@feature_app.command("add")
def feature_add(
    name: str = typer.Argument(..., help="Feature name"),
    feature_id: Optional[str] = typer.Option(None, "--id", help="Feature ID"),
    priority: str = typer.Option("medium", "--priority", "-p", help="Priority level")
):
    """Add a new feature."""
    try:
        registry = FeatureRegistry()

        feature_data = {
            'name': name,
            'status': 'planned',
            'priority': priority
        }

        if feature_id:
            feature_data['id'] = feature_id

        added = registry.add_feature(feature_data)
        registry.save()

        console.print(f"[green]✅ Added feature: {added['name']} ({added['id']})[/green]")

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


@feature_app.command("complete")
def feature_complete(
    feature_id: str = typer.Argument(..., help="Feature ID to complete")
):
    """Mark a feature as complete."""
    try:
        registry = FeatureRegistry()

        registry.complete_feature(feature_id)
        registry.save()

        console.print(f"[green]✅ Completed feature: {feature_id}[/green]")

        # Auto-generate STATUS.md
        console.print("[dim]Auto-generating STATUS.md...[/dim]")
        generator = StatusGenerator()
        generator.generate()

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


@feature_app.command("list")
def feature_list(
    status_filter: Optional[str] = typer.Option(None, "--status", "-s", help="Filter by status")
):
    """List all features."""
    try:
        registry = FeatureRegistry()
        features = registry.list_features(status=status_filter)

        if not features:
            console.print("[yellow]No features found[/yellow]")
            return

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("ID")
        table.add_column("Name")
        table.add_column("Status")
        table.add_column("Priority")

        for feature in features:
            table.add_row(
                feature.get('id', ''),
                feature.get('name', ''),
                feature.get('status', ''),
                feature.get('priority', '')
            )

        console.print(table)

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


# ===== Config Commands =====

config_app = typer.Typer(help="Manage configuration")
app.add_typer(config_app, name="config")


@config_app.command("init")
def config_init(
    scope: str = typer.Option("global", "--scope", "-s", help="'global' or 'project'")
):
    """Initialize configuration file."""
    try:
        config_manager = ConfigManager()

        if scope == "global":
            config_file = config_manager.init_global_config()
            console.print(f"[green]✅ Created global config: {config_file}[/green]")
        elif scope == "project":
            config_file = config_manager.init_project_config()
            console.print(f"[green]✅ Created project config: {config_file}[/green]")
        else:
            console.print("[red]❌ Invalid scope. Use 'global' or 'project'[/red]")
            raise typer.Exit(1)

    except ConfigError as e:
        console.print(f"[yellow]⚠️  {e}[/yellow]")
    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


@config_app.command("set")
def config_set(
    key: str = typer.Argument(..., help="Config key (e.g., 'debug.auto_retry')"),
    value: str = typer.Argument(..., help="Config value"),
    scope: str = typer.Option("project", "--scope", "-s", help="'global' or 'project'")
):
    """Set configuration value."""
    try:
        config_manager = get_config_manager()

        # Parse value
        parsed_value = value
        if value.lower() in ['true', 'false']:
            parsed_value = value.lower() == 'true'
        elif value.isdigit():
            parsed_value = int(value)

        config_manager.set(key, parsed_value, scope=scope)

        console.print(f"[green]✅ Set {key} = {parsed_value} ({scope})[/green]")

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


@config_app.command("get")
def config_get(
    key: str = typer.Argument(..., help="Config key")
):
    """Get configuration value."""
    try:
        config_manager = get_config_manager()
        value = config_manager.get(key)

        if value is None:
            console.print(f"[yellow]⚠️  Key not found: {key}[/yellow]")
        else:
            console.print(f"[cyan]{key}[/cyan] = {value}")

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


@config_app.command("list")
def config_list():
    """List all configuration values."""
    try:
        config_manager = get_config_manager()
        config = config_manager.list_all(flat=True)

        table = Table(show_header=True, header_style="bold cyan")
        table.add_column("Key")
        table.add_column("Value")

        for key, value in sorted(config.items()):
            table.add_row(key, str(value))

        console.print(table)

    except Exception as e:
        handle_error(e)
        raise typer.Exit(1)


# ===== Debug/Pipe Commands =====

@app.command()
def pipe(
    command: str = typer.Argument(..., help="Command to execute and pipe"),
    tags: Optional[str] = typer.Option(None, "--tags", "-t", help="Comma-separated tags")
):
    """Run command and auto-pipe output to context."""
    try:
        tag_list = tags.split(',') if tags else None

        console.print(f"[cyan]▶️  Running: {command}[/cyan]")

        return_code = auto_pipe_command(
            command,
            show_output=True,
            tags=tag_list
        )

        if return_code == 0:
            console.print(f"[green]✅ Command succeeded (piped to context)[/green]")
        else:
            console.print(f"[red]❌ Command failed with code {return_code} (piped to context)[/red]")

    except PipeError as e:
        handle_error(e)
        raise typer.Exit(1)


@app.command()
def debug():
    """Run diagnostics with auto-retry suggestions."""
    try:
        console.print("[cyan]🔍 Running diagnostics...[/cyan]")

        # Check features.json
        try:
            registry = FeatureRegistry()
            registry.load()
            console.print("[green]✅ features.json valid[/green]")
        except Exception as e:
            console.print(f"[red]❌ features.json error: {e}[/red]")

        # Check governance
        try:
            governance = get_governance_manager()
            if governance.config_file.exists():
                console.print("[green]✅ Governance configured[/green]")
                if governance.verify_checksum():
                    console.print("[green]✅ Governance checksum valid[/green]")
                else:
                    console.print("[yellow]⚠️  Governance checksum mismatch[/yellow]")
        except Exception as e:
            console.print(f"[yellow]⚠️  Governance: {e}[/yellow]")

        # Check command outputs for failures
        piper = CommandPiper()
        analysis = piper.analyze_failures()

        console.print(f"\n[cyan]📊 Command Analysis:[/cyan]")
        console.print(f"  Total commands: {analysis['total_commands']}")
        console.print(f"  Failed commands: {analysis['failed_commands']}")
        console.print(f"  Failure rate: {analysis['failure_rate']}%")

        if analysis['common_errors']:
            console.print(f"\n[yellow]⚠️  Common error patterns:[/yellow]")
            for error in analysis['common_errors']:
                console.print(f"  • {error}")

        console.print("\n[dim]💡 Suggestions:[/dim]")
        console.print("  • Use 'br pipe <command>' to capture outputs")
        console.print("  • Use 'br watch' to monitor for errors")
        console.print("  • Check .buildrunner/context/ for details")

    except Exception as e:
        handle_error(e, show_debug_hint=False)
        raise typer.Exit(1)


@app.command()
def watch(
    daemon: bool = typer.Option(False, "--daemon", "-d", help="Run in background")
):
    """Start error watcher daemon."""
    try:
        config = get_config_manager()
        patterns = config.get('watch.patterns', ['*.log', '*.err', 'pytest.out'])

        if daemon:
            console.print("[yellow]Daemon mode not fully implemented. Running scan instead.[/yellow]")
            watcher = ErrorWatcher(watch_patterns=patterns)
            results = watcher.scan_once()

            console.print(f"[cyan]📊 Scan Results:[/cyan]")
            console.print(f"  Files scanned: {results['files_scanned']}")
            console.print(f"  Errors found: {results['errors_found']}")

            if results['files_with_errors']:
                console.print(f"\n[yellow]⚠️  Files with errors:[/yellow]")
                for file in results['files_with_errors']:
                    console.print(f"  • {file}")
        else:
            console.print("[cyan]👀 Starting error watcher...[/cyan]")
            console.print("[dim]Press Ctrl+C to stop[/dim]")

            watcher = start_watcher(patterns=patterns, daemon=False)

    except WatcherError as e:
        handle_error(e)
        raise typer.Exit(1)
    except KeyboardInterrupt:
        console.print("\n[yellow]Watcher stopped[/yellow]")


# ===== Guard Commands =====

@guard_app.command("check")
def guard_check(
    spec_path: Optional[str] = typer.Option(None, "--spec", "-s", help="Path to PROJECT_SPEC.md"),
    strict: bool = typer.Option(False, "--strict", help="Include info-level violations"),
    output: str = typer.Option("markdown", "--output", "-o", help="Output format: markdown, json, text")
):
    """Validate code against PROJECT_SPEC architecture."""
    try:
        project_root = get_project_root()
        guard = ArchitectureGuard(str(project_root))

        with console.status("[cyan]Loading PROJECT_SPEC...[/cyan]"):
            try:
                guard.load_spec(spec_path)
                console.print("✅ Loaded architectural specifications")
            except FileNotFoundError as e:
                console.print(f"[red]❌ {e}[/red]")
                console.print("[yellow]💡 Tip: Create PROJECT_SPEC.md in your project root[/yellow]")
                raise typer.Exit(1)

        with console.status("[cyan]Analyzing codebase...[/cyan]"):
            violations = guard.detect_violations(strict=strict)

        # Generate report
        report = guard.generate_violation_report(output_format=output)

        if output == "json":
            console.print(report)
        else:
            console.print(report)

        # Exit with error code if violations found
        if violations:
            critical_count = len([v for v in violations if v.severity == "critical"])
            warning_count = len([v for v in violations if v.severity == "warning"])

            console.print(f"\n[red]Found {len(violations)} violations[/red]")
            console.print(f"  Critical: {critical_count}, Warnings: {warning_count}")
            raise typer.Exit(1)
        else:
            console.print("\n[green]✅ No violations detected![/green]")

    except Exception as e:
        handle_error(e, show_debug_hint=False)
        raise typer.Exit(1)


# ===== Service Commands =====

@service_app.command("detect")
def service_detect():
    """Detect required external services in codebase."""
    try:
        project_root = get_project_root()
        manager = SelfServiceManager(str(project_root))

        with console.status("[cyan]Scanning codebase for service dependencies...[/cyan]"):
            requirements = manager.detect_required_services()

        if not requirements:
            console.print("✅ No external service dependencies detected")
            return

        # Create table
        table = Table(title="Detected Services", show_header=True, header_style="bold cyan")
        table.add_column("Service", style="cyan")
        table.add_column("Status", justify="center")
        table.add_column("Env Variables")
        table.add_column("Detected In")

        for service_name, req in requirements.items():
            status = "✅ Configured" if req.configured else "⚠️  Not configured"
            env_vars = ", ".join(req.env_vars)
            files = ", ".join(req.detected_in[:2])
            if len(req.detected_in) > 2:
                files += f" (+{len(req.detected_in) - 2} more)"

            table.add_row(service_name.title(), status, env_vars, files)

        console.print(table)

        # Show setup hint if any not configured
        unconfigured = [name for name, req in requirements.items() if not req.configured]
        if unconfigured:
            console.print(f"\n[yellow]💡 Run 'br service setup <service>' to configure:[/yellow]")
            for service in unconfigured:
                console.print(f"   br service setup {service}")

    except Exception as e:
        handle_error(e, show_debug_hint=False)
        raise typer.Exit(1)


@service_app.command("setup")
def service_setup(
    service: Optional[str] = typer.Argument(None, help="Service to set up (stripe, aws, supabase, etc.)"),
    non_interactive: bool = typer.Option(False, "--non-interactive", help="Generate template without prompting")
):
    """Interactively set up external service credentials."""
    try:
        project_root = get_project_root()
        manager = SelfServiceManager(str(project_root))

        # If no service specified, detect and list
        if not service:
            requirements = manager.detect_required_services()

            if not requirements:
                console.print("[yellow]No external services detected in codebase[/yellow]")
                console.print("[dim]Run 'br service detect' to scan for services[/dim]")
                return

            console.print("[cyan]Detected services that need setup:[/cyan]")
            for name, req in requirements.items():
                if not req.configured:
                    console.print(f"  • {name.title()}")

            console.print("\n[dim]Run 'br service setup <service>' to configure a specific service[/dim]")
            return

        # Setup specific service
        success = manager.setup_service(service, interactive=not non_interactive)

        if success:
            console.print(f"\n[green]✅ {service.title()} configured successfully![/green]")
            console.print(f"[dim]Credentials saved to .env[/dim]")
        else:
            console.print(f"\n[red]❌ Failed to configure {service}[/red]")
            raise typer.Exit(1)

    except ValueError as e:
        console.print(f"[red]❌ {e}[/red]")
        console.print("[yellow]Supported services: stripe, aws, supabase, openai, github, notion, slack[/yellow]")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e, show_debug_hint=False)
        raise typer.Exit(1)


@service_app.command("status")
def service_status():
    """Show setup status for all detected services."""
    try:
        project_root = get_project_root()
        manager = SelfServiceManager(str(project_root))

        report = manager.generate_setup_report()
        console.print(report)

    except Exception as e:
        handle_error(e, show_debug_hint=False)
        raise typer.Exit(1)


@service_app.command("template")
def service_template():
    """Generate .env.example template with detected services."""
    try:
        project_root = get_project_root()
        manager = SelfServiceManager(str(project_root))

        template = manager.generate_env_template()

        console.print("[green]✅ Generated .env.example[/green]")
        console.print("\n[cyan]Template preview:[/cyan]")
        console.print(template)
        console.print("\n[dim]Copy .env.example to .env and fill in your credentials[/dim]")

    except Exception as e:
        handle_error(e, show_debug_hint=False)
        raise typer.Exit(1)


@app.command()
def sync():
    """Trigger Supabase sync (placeholder)."""
    console.print("[yellow]⚠️  Supabase sync not yet implemented[/yellow]")
    console.print("[dim]This will be implemented in Build 2B (FastAPI Backend)[/dim]")


# ===== Quality Commands =====

quality_app = typer.Typer(help="Code quality analysis commands")
app.add_typer(quality_app, name="quality")


@quality_app.command("check")
def quality_check(
    fix: bool = typer.Option(False, "--fix", help="Auto-fix issues where possible"),
    threshold: int = typer.Option(80, "--threshold", help="Minimum overall score (0-100)"),
    strict: bool = typer.Option(False, "--strict", help="Fail if threshold not met")
):
    """Run code quality analysis."""
    try:
        from core.code_quality import CodeQualityAnalyzer, QualityGate

        project_root = get_project_root()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing code quality...", total=None)

            analyzer = CodeQualityAnalyzer(project_root)
            metrics = analyzer.analyze_project()

            progress.remove_task(task)

        # Display results
        console.print("\n[cyan]📊 Code Quality Report[/cyan]\n")

        # Component scores
        table = Table(title="Quality Scores")
        table.add_column("Component", style="cyan")
        table.add_column("Score", justify="right")
        table.add_column("Status", justify="center")

        def get_status(score: float) -> str:
            if score >= 90:
                return "[green]✓ Excellent[/green]"
            elif score >= 80:
                return "[green]✓ Good[/green]"
            elif score >= 70:
                return "[yellow]⚠ Fair[/yellow]"
            else:
                return "[red]✗ Poor[/red]"

        table.add_row("Structure", f"{metrics.structure_score:.1f}", get_status(metrics.structure_score))
        table.add_row("Security", f"{metrics.security_score:.1f}", get_status(metrics.security_score))
        table.add_row("Testing", f"{metrics.testing_score:.1f}", get_status(metrics.testing_score))
        table.add_row("Documentation", f"{metrics.docs_score:.1f}", get_status(metrics.docs_score))
        table.add_row("", "", "")
        table.add_row("OVERALL", f"{metrics.overall_score:.1f}", get_status(metrics.overall_score), style="bold")

        console.print(table)

        # Metrics details
        console.print("\n[cyan]📈 Metrics:[/cyan]")
        console.print(f"  Avg Complexity: {metrics.avg_complexity:.1f}")
        console.print(f"  Type Hint Coverage: {metrics.type_hint_coverage:.1f}%")
        console.print(f"  Test Coverage: {metrics.test_coverage:.1f}%")
        console.print(f"  Docstring Coverage: {metrics.docstring_coverage:.1f}%")

        # Security findings
        if metrics.vulnerabilities_high > 0 or metrics.vulnerabilities_medium > 0:
            console.print(f"\n[yellow]⚠️  Security Findings:[/yellow]")
            if metrics.vulnerabilities_high > 0:
                console.print(f"  [red]High: {metrics.vulnerabilities_high}[/red]")
            if metrics.vulnerabilities_medium > 0:
                console.print(f"  [yellow]Medium: {metrics.vulnerabilities_medium}[/yellow]")
            if metrics.vulnerabilities_low > 0:
                console.print(f"  [dim]Low: {metrics.vulnerabilities_low}[/dim]")

        # Issues and suggestions
        if metrics.issues:
            console.print("\n[red]❌ Issues:[/red]")
            for issue in metrics.issues:
                console.print(f"  • {issue}")

        if metrics.suggestions:
            console.print("\n[yellow]💡 Suggestions:[/yellow]")
            for suggestion in metrics.suggestions:
                console.print(f"  • {suggestion}")

        # Check quality gate
        gate = QualityGate({'overall': threshold})
        passed, failures = gate.check(metrics)

        if not passed:
            console.print(f"\n[red]❌ Quality gate FAILED (threshold: {threshold})[/red]")
            for failure in failures:
                console.print(f"  • {failure}")
            if strict:
                raise typer.Exit(1)
        else:
            console.print(f"\n[green]✅ Quality gate PASSED[/green]")

    except ImportError as e:
        console.print(f"[red]❌ Missing dependency: {e}[/red]")
        console.print("[dim]Run: pip install bandit safety[/dim]")
        raise typer.Exit(1)
    except Exception as e:
        handle_error(e, show_debug_hint=False)
        raise typer.Exit(1)


# ===== Gap Analysis Commands =====

gaps_app = typer.Typer(help="Gap analysis commands")
app.add_typer(gaps_app, name="gaps")


@gaps_app.command("analyze")
def gaps_analyze(
    spec_path: Optional[str] = typer.Option(None, "--spec", help="Path to PROJECT_SPEC.md"),
    output: Optional[str] = typer.Option(None, "--output", "-o", help="Save report to file")
):
    """Analyze implementation gaps."""
    try:
        from core.gap_analyzer import GapAnalyzer

        project_root = get_project_root()

        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console
        ) as progress:
            task = progress.add_task("Analyzing gaps...", total=None)

            analyzer = GapAnalyzer(project_root)
            analysis = analyzer.analyze()

            # Also analyze spec if provided
            if spec_path:
                spec_file = Path(spec_path)
                analyzer.analyze_spec(spec_file, analysis)

            progress.remove_task(task)

        # Display results
        console.print("\n[cyan]🔍 Gap Analysis Report[/cyan]\n")

        # Summary
        console.print(Panel(
            f"[bold]Total Gaps: {analysis.total_gaps}[/bold]\n"
            f"[red]High: {analysis.severity_high}[/red] | "
            f"[yellow]Medium: {analysis.severity_medium}[/yellow] | "
            f"[dim]Low: {analysis.severity_low}[/dim]",
            title="Summary"
        ))

        # Feature gaps
        if analysis.missing_features or analysis.incomplete_features or analysis.blocked_features:
            console.print("\n[cyan]📋 Feature Gaps:[/cyan]")

            if analysis.missing_features:
                console.print(f"\n[red]  Missing ({len(analysis.missing_features)}):[/red]")
                for feat in analysis.missing_features[:5]:
                    console.print(f"    • {feat['id']}: {feat['name']}")
                if len(analysis.missing_features) > 5:
                    console.print(f"    ... and {len(analysis.missing_features) - 5} more")

            if analysis.incomplete_features:
                console.print(f"\n[yellow]  Incomplete ({len(analysis.incomplete_features)}):[/yellow]")
                for feat in analysis.incomplete_features[:5]:
                    console.print(f"    • {feat['id']}: {feat['name']}")
                if len(analysis.incomplete_features) > 5:
                    console.print(f"    ... and {len(analysis.incomplete_features) - 5} more")

            if analysis.blocked_features:
                console.print(f"\n[red]  Blocked ({len(analysis.blocked_features)}):[/red]")
                for feat in analysis.blocked_features:
                    console.print(f"    • {feat['id']}: {feat['name']}")

        # Implementation gaps
        if analysis.todo_count > 0 or analysis.stub_count > 0:
            console.print("\n[cyan]🔧 Implementation Gaps:[/cyan]")

            if analysis.todo_count > 0:
                console.print(f"  TODOs: {analysis.todo_count}")

            if analysis.stub_count > 0:
                console.print(f"  Stubs/NotImplemented: {analysis.stub_count}")

            if analysis.pass_statements > 0:
                console.print(f"  Pass statements: {analysis.pass_statements}")

        # Dependency gaps
        if analysis.missing_dependencies or analysis.circular_dependencies:
            console.print("\n[cyan]📦 Dependency Gaps:[/cyan]")

            if analysis.missing_dependencies:
                console.print(f"  Missing dependencies: {len(analysis.missing_dependencies)}")
                for dep in analysis.missing_dependencies[:5]:
                    console.print(f"    • {dep}")
                if len(analysis.missing_dependencies) > 5:
                    console.print(f"    ... and {len(analysis.missing_dependencies) - 5} more")

            if analysis.circular_dependencies:
                console.print(f"  [red]Circular dependencies: {len(analysis.circular_dependencies)}[/red]")

        # Missing components
        if analysis.missing_components:
            console.print("\n[yellow]⚠️  Missing Components:[/yellow]")
            for component in analysis.missing_components[:10]:
                console.print(f"  • {component}")
            if len(analysis.missing_components) > 10:
                console.print(f"  ... and {len(analysis.missing_components) - 10} more")

        # Save report if requested
        if output:
            report = analyzer.generate_gap_report(analysis)
            output_path = Path(output)
            output_path.write_text(report)
            console.print(f"\n[green]✅ Report saved to: {output}[/green]")

    except Exception as e:
        handle_error(e, show_debug_hint=False)
        raise typer.Exit(1)


# ===== Main Entry Point =====

def cli():
    """CLI entry point."""
    try:
        app()
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted[/yellow]")
        sys.exit(130)


if __name__ == "__main__":
    cli()
