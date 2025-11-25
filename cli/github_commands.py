"""
GitHub Automation CLI Commands

Complete GitHub workflow automation from branch creation to deployment.
"""

import typer
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from pathlib import Path
import sys

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.github.branch_manager import BranchManager
from core.github.push_intelligence import PushIntelligence
from core.github.conflict_detector import ConflictDetector
from core.github.version_manager import VersionManager
from core.github.release_manager import ReleaseManager
from core.github.pr_manager import PRManager
from core.github.commit_builder import CommitBuilder
from core.github.protection_manager import ProtectionManager
from core.github.snapshot_manager import SnapshotManager
from core.github.metrics_tracker import MetricsTracker
from core.github.health_checker import HealthChecker
from core.github.issues_manager import IssuesManager
from core.github.coauthor_manager import CoAuthorManager
from core.github.deployment_manager import DeploymentManager

console = Console()
app = typer.Typer(help="GitHub workflow automation")

# Branch commands
branch_app = typer.Typer(help="Branch management")
app.add_typer(branch_app, name="branch")

@branch_app.command("create")
def branch_create(
    feature_name: str = typer.Argument(..., help="Feature name"),
    week: int = typer.Option(None, "--week", "-w", help="Week number (auto-calculated if not provided)"),
    checkout: bool = typer.Option(True, "--checkout/--no-checkout", help="Checkout branch after creation")
):
    """Create feature branch with governance naming"""
    try:
        mgr = BranchManager()
        branch = mgr.create_branch(feature_name, week=week, checkout=checkout)

        console.print(f"\n[green]✅ Created branch:[/green] [cyan]{branch}[/cyan]\n")
        if checkout:
            console.print(f"[dim]Switched to branch {branch}[/dim]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@branch_app.command("list")
def branch_list():
    """List all feature branches"""
    try:
        mgr = BranchManager()
        branches = mgr.list_feature_branches()

        if not branches:
            console.print("\n[yellow]No feature branches found[/yellow]\n")
            return

        table = Table(title=f"\n📋 Feature Branches ({len(branches)} total)")
        table.add_column("Branch", style="cyan")
        table.add_column("Week", justify="right")
        table.add_column("Status", justify="center")
        table.add_column("Ready", justify="center")

        for branch in branches:
            current_marker = "→ " if branch.is_current else "  "
            ready_marker = "✅" if branch.is_mergeable else "⚠️"

            table.add_row(
                f"{current_marker}{branch.name}",
                str(branch.week_number or ""),
                "current" if branch.is_current else "",
                ready_marker
            )

        console.print(table)
        console.print()
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@branch_app.command("ready")
def branch_ready():
    """Check if current branch is ready to merge"""
    try:
        mgr = BranchManager()
        info = mgr.get_current_branch_info()

        console.print(f"\n[bold]Branch:[/bold] [cyan]{info.name}[/cyan]\n")

        if info.is_mergeable:
            console.print("[green]✅ Branch is ready to merge![/green]\n")
        else:
            console.print("[yellow]⚠️  Branch is not ready to merge[/yellow]\n")
            console.print("[bold]Issues:[/bold]")
            for issue in info.issues:
                console.print(f"  • {issue}")
            console.print()
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@branch_app.command("switch")
def branch_switch(feature_name: str = typer.Argument(..., help="Feature name to switch to")):
    """Switch to feature branch by name"""
    try:
        mgr = BranchManager()
        branch = mgr.switch_to_branch(feature_name)

        if branch:
            console.print(f"\n[green]✅ Switched to:[/green] [cyan]{branch}[/cyan]\n")
        else:
            console.print(f"\n[yellow]No branch found matching '{feature_name}'[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@branch_app.command("cleanup")
def branch_cleanup(
    dry_run: bool = typer.Option(True, "--dry-run/--execute", help="Show what would be deleted")
):
    """Delete merged branches"""
    try:
        mgr = BranchManager()
        branches = mgr.cleanup_merged_branches(dry_run=dry_run)

        if not branches:
            console.print("\n[green]No merged branches to clean up[/green]\n")
            return

        console.print(f"\n[bold]{'Would delete' if dry_run else 'Deleted'} {len(branches)} branches:[/bold]\n")
        for branch in branches:
            console.print(f"  • {branch}")

        if dry_run:
            console.print(f"\n[dim]Run with --execute to actually delete[/dim]\n")
        console.print()
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

# Push commands
@app.command("push")
def push_smart(
    when_ready: bool = typer.Option(False, "--when-ready", help="Only push if all checks pass"),
    check_conflicts: bool = typer.Option(True, "--check-conflicts/--skip-conflicts", help="Check for merge conflicts"),
    force: bool = typer.Option(False, "--force", help="Skip readiness checks")
):
    """Smart push with readiness checks"""
    try:
        if not force:
            # Check readiness
            intel = PushIntelligence()
            readiness = intel.assess_readiness(strict=when_ready)

            console.print(f"\n[bold]Push Readiness Assessment[/bold]\n")
            console.print(f"Score: {readiness.score}/100\n")

            if readiness.passed_checks:
                console.print("[bold green]✅ Passed Checks:[/bold green]")
                for check in readiness.passed_checks:
                    console.print(f"  • {check}")
                console.print()

            if readiness.warnings:
                console.print("[bold yellow]⚠️  Warnings:[/bold yellow]")
                for warning in readiness.warnings:
                    console.print(f"  • {warning}")
                console.print()

            if readiness.blockers:
                console.print("[bold red]❌ Blockers:[/bold red]")
                for blocker in readiness.blockers:
                    console.print(f"  • {blocker}")
                console.print()
                console.print("[red]Push blocked. Fix blockers first.[/red]\n")
                raise typer.Exit(1)

            if when_ready and not readiness.is_ready:
                console.print("[yellow]Not ready to push. Use --force to override.[/yellow]\n")
                raise typer.Exit(1)

        if check_conflicts:
            # Check for conflicts
            detector = ConflictDetector()
            status = detector.get_behind_status()
            console.print(f"{status}\n")

            info = detector.check_conflicts()
            if info.has_conflicts:
                console.print(f"[red]❌ Would cause merge conflicts. Fix conflicts first.[/red]\n")
                raise typer.Exit(1)

        # Do the push
        from core.github.git_client import GitClient
        import os

        # Set environment variable to signal pre-push hook that we're using br github push
        os.environ['BR_GITHUB_PUSH'] = 'true'

        git = GitClient()
        current = git.current_branch()

        console.print(f"[bold]Pushing {current}...[/bold]\n")
        git.push(set_upstream=True)
        console.print(f"[green]✅ Pushed successfully![/green]\n")

    except typer.Exit:
        raise
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@app.command("sync")
def sync_branch(
    rebase: bool = typer.Option(True, "--rebase/--merge", help="Rebase or merge")
):
    """Sync current branch with main"""
    try:
        detector = ConflictDetector()
        success, message = detector.sync_with_main(rebase=rebase)

        if success:
            console.print(f"\n[green]✅ {message}[/green]\n")
        else:
            console.print(f"\n[red]❌ {message}[/red]\n")
            raise typer.Exit(1)
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

# Release commands
release_app = typer.Typer(help="Release management")
app.add_typer(release_app, name="release")

@release_app.command("create")
def release_create(
    bump: str = typer.Argument("patch", help="major|minor|patch"),
):
    """Create release with automatic versioning"""
    try:
        mgr = ReleaseManager()
        console.print(f"\n[bold]Creating {bump} release...[/bold]\n")

        new_version = mgr.create_release(bump)

        console.print(f"[green]✅ Created release v{new_version}[/green]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@release_app.command("patch")
def release_patch():
    """Create patch release (v3.1.0 → v3.1.1)"""
    try:
        mgr = ReleaseManager()
        new_version = mgr.create_release('patch')
        console.print(f"\n[green]✅ Created patch release v{new_version}[/green]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@release_app.command("minor")
def release_minor():
    """Create minor release (v3.1.0 → v3.2.0)"""
    try:
        mgr = ReleaseManager()
        new_version = mgr.create_release('minor')
        console.print(f"\n[green]✅ Created minor release v{new_version}[/green]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@release_app.command("major")
def release_major():
    """Create major release (v3.1.0 → v4.0.0)"""
    try:
        mgr = ReleaseManager()
        new_version = mgr.create_release('major')
        console.print(f"\n[green]✅ Created major release v{new_version}[/green]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

# PR commands
pr_app = typer.Typer(help="Pull request management")
app.add_typer(pr_app, name="pr")

@pr_app.command("create")
def pr_create(
    title: str = typer.Option(None, "--title", "-t", help="PR title"),
    draft: bool = typer.Option(False, "--draft", "-d", help="Create as draft")
):
    """Create pull request"""
    try:
        mgr = PRManager()
        pr = mgr.create_pr(title=title, draft=draft)

        console.print(f"\n[green]✅ Created PR #{pr.number}[/green]")
        console.print(f"[cyan]{pr.url}[/cyan]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

# Snapshot commands
snapshot_app = typer.Typer(help="Snapshot management")
app.add_typer(snapshot_app, name="snapshot")

@snapshot_app.command("create")
def snapshot_create(name: str = typer.Argument(..., help="Snapshot name")):
    """Create named snapshot"""
    try:
        mgr = SnapshotManager()
        tag = mgr.create_snapshot(name)
        console.print(f"\n[green]✅ Created snapshot:[/green] [cyan]{tag}[/cyan]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

@snapshot_app.command("list")
def snapshot_list():
    """List all snapshots"""
    try:
        mgr = SnapshotManager()
        snapshots = mgr.list_snapshots()

        if not snapshots:
            console.print("\n[yellow]No snapshots found[/yellow]\n")
            return

        console.print(f"\n[bold]📸 Snapshots ({len(snapshots)} total):[/bold]\n")
        for snap in snapshots:
            console.print(f"  • {snap}")
        console.print()
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

# Protection commands
@app.command("protect")
def protect_setup(branch: str = typer.Option("main", "--branch", "-b", help="Branch to protect")):
    """Setup branch protection"""
    try:
        mgr = ProtectionManager()
        success = mgr.setup_protection(branch)

        if success:
            console.print(f"\n[green]✅ Branch protection enabled on {branch}[/green]\n")
        else:
            console.print(f"\n[yellow]⚠️  Could not enable protection (GitHub API token needed)[/yellow]\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)

# Commit commands
@app.command("commit")
def commit_interactive(
    type: str = typer.Option(None, "--type", "-t", help="Commit type (feat/fix/refactor/etc)"),
    message: str = typer.Option(None, "--message", "-m", help="Commit message"),
    scope: str = typer.Option(None, "--scope", "-s", help="Commit scope")
):
    """Interactive commit builder with conventional commits"""
    try:
        builder = CommitBuilder()

        if not type:
            type = typer.prompt("Commit type (feat/fix/refactor/docs/test/chore)")

        if not message:
            message = typer.prompt("Commit message")

        commit_msg = builder.build_commit_message(type, message, scope)

        # Add Claude attribution
        commit_msg += "\n\n🤖 Generated with [Claude Code](https://claude.com/claude-code)\n\nCo-Authored-By: Claude <noreply@anthropic.com>"

        # Create commit
        from core.github.git_client import GitClient
        git = GitClient()
        git.commit(commit_msg)

        console.print(f"\n[green]✅ Committed:[/green] {commit_msg.split(chr(10))[0]}\n")
    except Exception as e:
        console.print(f"\n[red]❌ Error: {e}[/red]\n")
        raise typer.Exit(1)


if __name__ == "__main__":
    app()
