"""
Migration CLI Commands

Commands for migrating BuildRunner 2.0 projects to 3.0
"""

from pathlib import Path
from typing import Optional
import typer
from rich.console import Console
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel
from rich.table import Table
import json
import yaml

from core.migration.v2_parser import V2ProjectParser
from core.migration.converter import MigrationConverter
from core.migration.validators import MigrationValidator
from core.migration.git_handler import GitMigrationHandler


# Create Typer app for migration commands
migrate_app = typer.Typer(help="Migration commands for BuildRunner 2.0 → 3.0")
console = Console()


@migrate_app.command("from-v2")
def migrate_from_v2(
    project_path: str = typer.Argument(..., help="Path to BuildRunner 2.0 project"),
    dry_run: bool = typer.Option(False, "--dry-run", help="Validate without making changes"),
    backup: bool = typer.Option(
        True, "--backup/--no-backup", help="Create backup before migration"
    ),
    force: bool = typer.Option(False, "--force", help="Override validation warnings"),
    output_dir: Optional[str] = typer.Option(None, "--output", help="Custom output directory"),
):
    """
    Migrate BuildRunner 2.0 project to 3.0 format

    This command converts:
    - .runner/hrpo.json → features.json
    - .runner/governance.json → .buildrunner/governance.yaml
    - Preserves git history
    - Creates backups

    Example:
        br migrate from-v2 /path/to/v2/project
        br migrate from-v2 /path/to/v2/project --dry-run
        br migrate from-v2 /path/to/v2/project --no-backup --force
    """
    console.print(
        Panel.fit("[bold cyan]BuildRunner Migration: v2.0 → v3.0[/bold cyan]", border_style="cyan")
    )

    project_path = Path(project_path).resolve()

    # Phase 1: Parse v2.0 project
    console.print("\n[bold]Phase 1:[/bold] Parsing v2.0 project...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Parsing project structure...", total=None)

        parser = V2ProjectParser(project_path)
        v2_project = parser.parse()

        progress.update(task, description="✓ Project parsed", completed=True)

    # Show summary
    console.print(parser.get_summary(v2_project))

    if not v2_project.is_valid:
        console.print("[bold red]❌ Project is not valid for migration[/bold red]")
        raise typer.Exit(1)

    # Phase 2: Pre-migration validation
    console.print("\n[bold]Phase 2:[/bold] Pre-migration validation...")

    validator = MigrationValidator(project_path)
    validation = validator.validate_pre_migration(v2_project)

    console.print(validator.format_validation_result(validation, "Pre-Migration Validation"))

    if not validation.passed and not force:
        console.print("\n[bold red]❌ Validation failed[/bold red]")
        console.print("Use --force to proceed anyway (not recommended)")
        raise typer.Exit(1)

    if dry_run:
        console.print("\n[bold yellow]🔍 Dry-run mode - no changes will be made[/bold yellow]")

    # Phase 3: Create backup
    if backup and v2_project.has_git and not dry_run:
        console.print("\n[bold]Phase 3:[/bold] Creating backup...")

        git_handler = GitMigrationHandler(project_path)
        backup_result = git_handler.create_pre_migration_backup()

        if backup_result.success:
            console.print(f"✓ Backup created: {backup_result.tag_name}")
            console.print(f"  Commit: {backup_result.commit_hash[:8]}")
            console.print(f"  Files: {backup_result.backup_path}")
        else:
            console.print("[bold red]❌ Backup failed[/bold red]")
            for error in backup_result.errors:
                console.print(f"  {error}")
            if not force:
                raise typer.Exit(1)

    # Phase 4: Convert data
    console.print("\n[bold]Phase 4:[/bold] Converting data...")

    with Progress(
        SpinnerColumn(),
        TextColumn("[progress.description]{task.description}"),
        console=console,
    ) as progress:
        task = progress.add_task("Converting HRPO → features.json...", total=None)

        converter = MigrationConverter(v2_project)
        conversion = converter.convert()

        progress.update(task, description="✓ Conversion complete", completed=True)

    # Show conversion summary
    _display_conversion_summary(conversion)

    if not conversion.success:
        console.print("[bold red]❌ Conversion failed[/bold red]")
        raise typer.Exit(1)

    # Phase 5: Post-migration validation
    console.print("\n[bold]Phase 5:[/bold] Validating converted data...")

    post_validation = validator.validate_post_migration(
        v2_project, conversion.features_json, conversion.governance_yaml
    )

    console.print(validator.format_validation_result(post_validation, "Post-Migration Validation"))

    if not post_validation.passed and not force:
        console.print("\n[bold red]❌ Validation failed[/bold red]")
        raise typer.Exit(1)

    # Phase 6: Write files (if not dry-run)
    if not dry_run:
        console.print("\n[bold]Phase 6:[/bold] Writing migrated files...")

        output_path = Path(output_dir) if output_dir else project_path

        # Write features.json
        features_file = output_path / "features.json"
        with open(features_file, "w") as f:
            json.dump(conversion.features_json, f, indent=2)
        console.print(f"✓ Created: {features_file}")

        # Write governance.yaml
        buildrunner_dir = output_path / ".buildrunner"
        buildrunner_dir.mkdir(exist_ok=True)

        governance_file = buildrunner_dir / "governance.yaml"
        with open(governance_file, "w") as f:
            yaml.dump(conversion.governance_yaml, f, default_flow_style=False)
        console.print(f"✓ Created: {governance_file}")

        # Write migration metadata
        metadata_file = buildrunner_dir / "migration_metadata.json"
        with open(metadata_file, "w") as f:
            json.dump(conversion.metadata, f, indent=2)
        console.print(f"✓ Created: {metadata_file}")

        # Phase 7: Create migration commit
        if v2_project.has_git:
            console.print("\n[bold]Phase 7:[/bold] Creating migration commit...")

            git_handler = GitMigrationHandler(project_path)
            commit_result = git_handler.create_migration_commit()

            if commit_result.success:
                console.print(f"✓ Migration commit created: {commit_result.commit_hash[:8]}")

                # Tag migration point
                tag_result = git_handler.tag_migration_point()
                if tag_result.success:
                    console.print(f"✓ Migration tagged: {tag_result.tag_name}")
            else:
                console.print("[bold yellow]⚠️  Could not create migration commit[/bold yellow]")
                for error in commit_result.errors:
                    console.print(f"  {error}")

        # Success!
        console.print(
            Panel.fit(
                "[bold green]✅ Migration Complete![/bold green]\n\n"
                f"Features migrated: {len(conversion.features_json['features'])}\n"
                f"Project: {conversion.metadata.get('project_name', 'Unknown')}\n"
                f"Version: {conversion.metadata.get('target_version', '3.0')}",
                border_style="green",
            )
        )

        # Show next steps
        console.print("\n[bold]Next steps:[/bold]")
        console.print("1. Review features.json and .buildrunner/governance.yaml")
        console.print("2. Run 'br gaps analyze' to check for missing features")
        console.print("3. Run 'br quality check' to validate code quality")
        console.print("4. Test your application thoroughly")

        if v2_project.has_git:
            console.print(f"\n[dim]To rollback: git revert HEAD or br migrate rollback[/dim]")
    else:
        console.print("\n[bold yellow]🔍 Dry-run complete - no files were changed[/bold yellow]")
        console.print("Run without --dry-run to perform actual migration")


@migrate_app.command("rollback")
def rollback_migration(
    project_path: str = typer.Argument(..., help="Path to migrated project"),
    tag: Optional[str] = typer.Option(None, help="Specific backup tag to rollback to"),
):
    """
    Rollback migration to pre-migration state

    Uses git tags to restore project to v2.0 format

    Example:
        br migrate rollback /path/to/project
        br migrate rollback /path/to/project --tag pre-migration-v2.0-20251117
    """
    console.print(Panel.fit("[bold yellow]Migration Rollback[/bold yellow]", border_style="yellow"))

    project_path = Path(project_path).resolve()

    git_handler = GitMigrationHandler(project_path)

    if not git_handler.is_git_repository():
        console.print("[bold red]❌ Not a git repository - cannot rollback[/bold red]")
        console.print("Rollback requires git. Restore from file backup manually.")
        raise typer.Exit(1)

    console.print(f"\n[bold]Rolling back migration...[/bold]")

    result = git_handler.rollback_migration(tag)

    if result.success:
        console.print(f"[bold green]✅ Rollback successful[/bold green]")
        console.print(f"Restored to: {result.tag_name}")
    else:
        console.print(f"[bold red]❌ Rollback failed[/bold red]")
        for error in result.errors:
            console.print(f"  {error}")
        raise typer.Exit(1)


@migrate_app.command("status")
def migration_status(
    project_path: str = typer.Argument(..., help="Path to project"),
):
    """
    Check migration status of project

    Detects if project is v2.0, v3.0, or partially migrated

    Example:
        br migrate status /path/to/project
    """
    project_path = Path(project_path).resolve()

    console.print(Panel.fit("[bold cyan]Migration Status Check[/bold cyan]", border_style="cyan"))

    # Check for v2.0 indicators
    has_v2 = (project_path / ".runner" / "hrpo.json").exists()
    has_v2_governance = (project_path / ".runner" / "governance.json").exists()

    # Check for v3.0 indicators
    has_v3_features = (project_path / "features.json").exists()
    has_v3_governance = (project_path / ".buildrunner" / "governance.yaml").exists()

    # Check for migration metadata
    has_migration_metadata = (project_path / ".buildrunner" / "migration_metadata.json").exists()

    # Determine status
    table = Table(title="Project Status")
    table.add_column("Component", style="cyan")
    table.add_column("v2.0", style="yellow")
    table.add_column("v3.0", style="green")

    table.add_row("Features", "✓" if has_v2 else "✗", "✓" if has_v3_features else "✗")
    table.add_row(
        "Governance", "✓" if has_v2_governance else "✗", "✓" if has_v3_governance else "✗"
    )
    table.add_row("Migration metadata", "—", "✓" if has_migration_metadata else "✗")

    console.print(table)

    # Interpret status
    if has_v3_features and has_v3_governance:
        console.print("\n[bold green]✅ Project is BuildRunner 3.0[/bold green]")
        if has_migration_metadata:
            console.print("[dim](Migrated from v2.0)[/dim]")
    elif has_v2 and has_v2_governance and not has_v3_features:
        console.print("\n[bold yellow]BuildRunner 2.0 project[/bold yellow]")
        console.print("Run 'br migrate from-v2 .' to migrate to 3.0")
    elif has_v2 and has_v3_features:
        console.print(
            "\n[bold yellow]⚠️  Mixed state - both v2.0 and v3.0 files exist[/bold yellow]"
        )
        console.print("Migration may be incomplete or rolled back")
    else:
        console.print("\n[bold red]❌ Unknown project state[/bold red]")
        console.print("Not a recognized BuildRunner project")


def _display_conversion_summary(conversion):
    """Display conversion summary"""
    table = Table(title="Conversion Summary")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Features converted", str(len(conversion.features_json.get("features", []))))
    table.add_row("Project name", conversion.metadata.get("project_name", "Unknown"))
    table.add_row("Source version", conversion.metadata.get("source_version", "Unknown"))
    table.add_row("Target version", conversion.metadata.get("target_version", "Unknown"))

    console.print(table)

    if conversion.warnings:
        console.print("\n[bold yellow]Warnings:[/bold yellow]")
        for warning in conversion.warnings:
            console.print(f"  ⚠️  {warning}")

    if conversion.errors:
        console.print("\n[bold red]Errors:[/bold red]")
        for error in conversion.errors:
            console.print(f"  ❌ {error}")
