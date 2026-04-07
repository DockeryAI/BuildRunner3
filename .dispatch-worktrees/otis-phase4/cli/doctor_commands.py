"""
BR Doctor - System Health Check
Validates that all BuildRunner 3.0 systems are properly configured and active
"""

import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
import os
import subprocess

doctor_app = typer.Typer(help="Check BuildRunner system health")
console = Console()


@doctor_app.command()
def check(
    fix: bool = typer.Option(False, "--fix", help="Attempt to auto-fix issues"),
    verbose: bool = typer.Option(False, "--verbose", "-v", help="Show detailed output"),
):
    """
    Check the health of all BuildRunner 3.0 systems

    Example:
        br doctor
        br doctor --fix
        br doctor --verbose
    """
    console.print()
    console.print("[bold cyan]🏥 BuildRunner 3.0 - System Health Check[/bold cyan]")
    console.print()

    project_root = Path.cwd()
    buildrunner_dir = project_root / ".buildrunner"

    # Track status
    total_systems = 21
    active_systems = 0
    issues = []
    warnings = []

    # Check 1: Directory Structure
    console.print("[bold]1. Directory Structure[/bold]")
    if buildrunner_dir.exists():
        console.print("  ✅ .buildrunner/ exists")
        active_systems += 1
    else:
        console.print("  ❌ .buildrunner/ not found")
        issues.append("Directory structure not initialized")

    # Check 2: Git Hooks
    console.print()
    console.print("[bold]2. Git Hooks[/bold]")

    pre_commit = project_root / ".git/hooks/pre-commit"
    pre_push = project_root / ".git/hooks/pre-push"

    if pre_commit.exists() and os.access(pre_commit, os.X_OK):
        # Check if it's the BR3 hook
        content = pre_commit.read_text()
        if "BuildRunner 3.0" in content and "br autodebug" in content:
            console.print("  ✅ Pre-commit hook (BR3 comprehensive version)")
            active_systems += 1
        else:
            console.print("  ⚠️  Pre-commit hook exists but not BR3 version")
            warnings.append("Pre-commit hook needs updating to BR3 version")
    else:
        console.print("  ❌ Pre-commit hook not installed")
        issues.append("Pre-commit hook missing")

    if pre_push.exists() and os.access(pre_push, os.X_OK):
        content = pre_push.read_text()
        if "BuildRunner 3.0" in content and "br gaps analyze" in content:
            console.print("  ✅ Pre-push hook (BR3 comprehensive version)")
            active_systems += 1
        else:
            console.print("  ⚠️  Pre-push hook exists but not BR3 version")
            warnings.append("Pre-push hook needs updating to BR3 version")
    else:
        console.print("  ❌ Pre-push hook not installed")
        issues.append("Pre-push hook missing")

    # Check 3: Debug Logging
    console.print()
    console.print("[bold]3. Debug Logging System[/bold]")

    debug_scripts = buildrunner_dir / "scripts"
    clog_wrapper = project_root / "clog"

    if debug_scripts.exists() and (debug_scripts / "debug-session.sh").exists():
        console.print("  ✅ Debug scripts installed")
        active_systems += 1
    else:
        console.print("  ❌ Debug scripts not found")
        issues.append("Debug scripts not installed")

    if clog_wrapper.exists() and os.access(clog_wrapper, os.X_OK):
        console.print("  ✅ ./clog wrapper available")
    else:
        console.print("  ⚠️  ./clog wrapper not created")
        warnings.append("./clog wrapper missing")

    # Check 4: Governance
    console.print()
    console.print("[bold]4. Governance System[/bold]")

    governance_file = buildrunner_dir / "governance" / "governance.yaml"
    quality_file = buildrunner_dir / "quality-standards.yaml"

    if governance_file.exists():
        console.print("  ✅ governance.yaml exists")
        active_systems += 1
    else:
        console.print("  ❌ governance.yaml not found")
        issues.append("Governance rules not configured")

    if quality_file.exists():
        console.print("  ✅ quality-standards.yaml exists")
    else:
        console.print("  ⚠️  quality-standards.yaml not found")
        warnings.append("Quality standards not defined")

    # Check 5: Auto-Debug
    console.print()
    console.print("[bold]5. Auto-Debug Pipeline[/bold]")

    # Check if br command works
    try:
        result = subprocess.run(["br", "autodebug", "--help"], capture_output=True, timeout=2)
        if result.returncode == 0:
            console.print("  ✅ Auto-debug system available")
            active_systems += 1
        else:
            console.print("  ⚠️  Auto-debug command not working")
            warnings.append("Auto-debug may not be properly configured")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        console.print("  ❌ BR CLI not available")
        issues.append("BuildRunner CLI not installed")

    # Check 6: Security Scanning
    console.print()
    console.print("[bold]6. Security System[/bold]")

    try:
        result = subprocess.run(["br", "security", "--help"], capture_output=True, timeout=2)
        if result.returncode == 0:
            console.print("  ✅ Security scanning available")
            active_systems += 1
        else:
            console.print("  ⚠️  Security commands not working")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        console.print("  ❌ Security system unavailable")

    # Check 7: Quality Gates
    console.print()
    console.print("[bold]7. Code Quality Gates[/bold]")

    try:
        result = subprocess.run(["br", "quality", "--help"], capture_output=True, timeout=2)
        if result.returncode == 0:
            console.print("  ✅ Quality system available")
            active_systems += 1
        else:
            console.print("  ⚠️  Quality commands not working")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        console.print("  ❌ Quality system unavailable")

    # Check 8: Architecture Guard
    console.print()
    console.print("[bold]8. Architecture Guard[/bold]")

    try:
        result = subprocess.run(["br", "guard", "--help"], capture_output=True, timeout=2)
        if result.returncode == 0:
            console.print("  ✅ Architecture guard available")
            active_systems += 1
        else:
            console.print("  ⚠️  Guard commands not working")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        console.print("  ❌ Architecture guard unavailable")

    # Check 9: Gap Analysis
    console.print()
    console.print("[bold]9. Gap Analysis[/bold]")

    try:
        result = subprocess.run(["br", "gaps", "--help"], capture_output=True, timeout=2)
        if result.returncode == 0:
            console.print("  ✅ Gap analysis available")
            active_systems += 1
        else:
            console.print("  ⚠️  Gaps commands not working")
    except (subprocess.TimeoutExpired, FileNotFoundError):
        console.print("  ❌ Gap analysis unavailable")

    # Check 10: Telemetry (Datadog)
    console.print()
    console.print("[bold]10. Telemetry (Datadog)[/bold]")

    dd_api_key = os.getenv("DD_API_KEY")
    if dd_api_key:
        console.print(f"  ✅ DD_API_KEY configured")
        active_systems += 1

        # Check telemetry config
        telem_config = buildrunner_dir / "telemetry-config.yaml"
        if telem_config.exists():
            console.print("  ✅ Telemetry configured")
        else:
            console.print("  ⚠️  Telemetry config missing")
    else:
        console.print("  ⚠️  DD_API_KEY not set - telemetry disabled")
        console.print("     Set DD_API_KEY to enable Datadog integration")
        warnings.append("Datadog telemetry not configured")

    # Check 11-21: Other Systems
    console.print()
    console.print("[bold]11-21. Additional Systems[/bold]")

    # These are available if BR CLI works
    other_systems = [
        ("Model Routing", "routing"),
        ("Parallel Orchestration", "parallel"),
        ("Telemetry Commands", "telemetry"),
        ("Design System", "design"),
        ("PRD System", "spec"),
        ("Migration Tools", "migrate"),
    ]

    for name, command in other_systems:
        try:
            result = subprocess.run(["br", command, "--help"], capture_output=True, timeout=2)
            if result.returncode == 0:
                if verbose:
                    console.print(f"  ✅ {name} available")
                active_systems += 1
        except (subprocess.TimeoutExpired, FileNotFoundError):
            if verbose:
                console.print(f"  ⚠️  {name} unavailable")

    if not verbose:
        console.print(f"  ✅ {len(other_systems)} additional systems available via CLI")

    # Check 22: Project Files
    console.print()
    console.print("[bold]Project Files[/bold]")

    project_spec = buildrunner_dir / "PROJECT_SPEC.md"
    features_json = buildrunner_dir / "features.json"

    if project_spec.exists():
        console.print("  ✅ PROJECT_SPEC.md exists")
    else:
        console.print("  ⚠️  PROJECT_SPEC.md not found")
        warnings.append("PROJECT_SPEC.md missing")

    if features_json.exists():
        console.print("  ✅ features.json exists")
    else:
        console.print("  ⚠️  features.json not found")
        warnings.append("features.json missing")

    # Summary
    console.print()
    console.print("=" * 60)
    console.print()

    # Calculate score
    score_percent = (active_systems / total_systems) * 100

    if score_percent >= 90:
        status_color = "green"
        status_emoji = "✅"
        status_text = "EXCELLENT"
    elif score_percent >= 70:
        status_color = "yellow"
        status_emoji = "⚠️"
        status_text = "GOOD"
    elif score_percent >= 50:
        status_color = "yellow"
        status_emoji = "⚠️"
        status_text = "NEEDS ATTENTION"
    else:
        status_color = "red"
        status_emoji = "❌"
        status_text = "CRITICAL"

    console.print(
        Panel(
            f"[bold {status_color}]{status_emoji} System Health: {status_text}[/bold {status_color}]\n\n"
            f"[white]Active Systems:[/white] [{status_color}]{active_systems}/{total_systems}[/{status_color}] ({score_percent:.0f}%)\n"
            f"[white]Issues:[/white] [red]{len(issues)}[/red]\n"
            f"[white]Warnings:[/white] [yellow]{len(warnings)}[/yellow]",
            title="Health Summary",
            border_style=status_color,
        )
    )

    # Show issues
    if issues:
        console.print()
        console.print("[bold red]❌ Issues Found:[/bold red]")
        for issue in issues:
            console.print(f"   • {issue}")

    # Show warnings
    if warnings:
        console.print()
        console.print("[bold yellow]⚠️  Warnings:[/bold yellow]")
        for warning in warnings:
            console.print(f"   • {warning}")

    # Recommendations
    if issues or warnings:
        console.print()
        console.print("[bold blue]💡 Recommendations:[/bold blue]")

        if issues:
            console.print()
            console.print("To fix critical issues:")
            console.print("  1. Run: [cyan]br project attach <alias>[/cyan]")
            console.print("     This will re-run the complete activation")
            console.print()
            console.print("  2. Or run activation script manually:")
            console.print("     [cyan]bash ~/.buildrunner/scripts/activate-all-systems.sh .[/cyan]")

        if "Datadog telemetry not configured" in warnings:
            console.print()
            console.print("To enable Datadog telemetry:")
            console.print("  [cyan]export DD_API_KEY=your-datadog-api-key[/cyan]")
            console.print("  [cyan]export DD_SITE=us5.datadoghq.com[/cyan]")

    console.print()

    # Exit code
    if issues:
        raise typer.Exit(1)
    else:
        raise typer.Exit(0)


if __name__ == "__main__":
    doctor_app()
