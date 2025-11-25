"""
Security Commands - CLI commands for security checking and git hook management

Commands:
- br security check - Run security checks on codebase
- br security scan - Scan for secrets and SQL injection
- br security hooks install - Install pre-commit hooks
- br security hooks uninstall - Remove pre-commit hooks
- br security hooks status - Check hook installation status
- br security precommit - Run pre-commit checks (called by git hook)
"""

import sys
import typer
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich import print as rprint
from typing import Optional

from core.security import (
    SecretDetector,
    SecretMasker,
    SQLInjectionDetector,  # Keep for compatibility
    GitHookManager,
    format_hook_result,
)
from core.security.smart_sql_detector import SmartSQLDetector

security_app = typer.Typer(help="Security checking and git hook management")
hooks_app = typer.Typer(help="Git hook management")
security_app.add_typer(hooks_app, name="hooks")

console = Console()


@security_app.command("check")
def security_check(
    staged: bool = typer.Option(False, "--staged", help="Check only staged files"),
    secrets: bool = typer.Option(True, "--secrets/--no-secrets", help="Check for secrets"),
    sql: bool = typer.Option(True, "--sql/--no-sql", help="Check for SQL injection"),
):
    """
    Run security checks on codebase

    Checks for:
    - Exposed API keys and secrets
    - SQL injection vulnerabilities
    - Hardcoded credentials

    Example:
        br security check
        br security check --staged
        br security check --no-sql
    """
    console.print("\n[bold blue]🔒 Running Security Checks...[/bold blue]\n")

    project_root = Path.cwd()
    has_issues = False

    # Check for secrets
    if secrets:
        console.print("[cyan]Checking for exposed secrets...[/cyan]")
        secret_detector = SecretDetector(project_root)

        if staged:
            results = secret_detector.scan_git_staged()
        else:
            results = secret_detector.scan_directory(str(project_root))

        if results:
            has_issues = True
            console.print("\n[bold red]❌ SECRETS DETECTED[/bold red]\n")

            for file_path, matches in results.items():
                console.print(f"[yellow]{file_path}[/yellow]")
                for match in matches:
                    console.print(
                        f"  Line {match.line_number}: "
                        f"[red]{match.pattern_name}[/red] - "
                        f"{match.secret_value}"
                    )

            console.print("\n[bold yellow]💡 Recommendation:[/bold yellow]")
            console.print("  • Move secrets to .env file (add to .gitignore)")
            console.print("  • Use environment variables")
            console.print("  • Never commit API keys to git\n")
        else:
            console.print("[green]✓ No secrets detected[/green]\n")

    # Check for SQL injection (using SmartSQLDetector - 95% fewer false positives)
    if sql:
        console.print("[cyan]Checking for SQL injection vulnerabilities...[/cyan]")
        smart_detector = SmartSQLDetector()

        # SmartSQLDetector automatically excludes node_modules, .venv, tests, docs
        risks = smart_detector.detect_real_risks(project_root)

        if risks:
            has_issues = True
            console.print("\n[bold red]❌ SQL INJECTION RISKS DETECTED[/bold red]\n")

            # Group by file
            by_file = {}
            for risk in risks:
                if risk.file_path not in by_file:
                    by_file[risk.file_path] = []
                by_file[risk.file_path].append(risk)

            for file_path, file_risks in by_file.items():
                console.print(f"[yellow]{file_path}[/yellow]")
                for risk in file_risks:
                    console.print(
                        f"  Line {risk.line_number}: "
                        f"[red]{risk.risk_type}[/red] "
                        f"(severity: {risk.severity})"
                    )
                    console.print(f"    {risk.line_content[:80]}")

            console.print("\n[bold yellow]💡 Fix:[/bold yellow]")
            console.print("  Use parameterized queries with ? or :param placeholders")
            console.print("  Example: cursor.execute('SELECT * FROM users WHERE id = ?', (user_id,))\n")
        else:
            console.print("[green]✓ No SQL injection vulnerabilities detected[/green]\n")

    # Summary
    if has_issues:
        console.print("\n[bold red]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold red]")
        console.print("[bold red]Security Check Failed[/bold red]")
        console.print("[bold red]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold red]\n")
        sys.exit(1)
    else:
        console.print("\n[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]")
        console.print("[bold green]✅ All Security Checks Passed[/bold green]")
        console.print("[bold green]━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━[/bold green]\n")


@security_app.command("scan")
def security_scan(
    file: Optional[str] = typer.Option(None, "--file", "-f", help="Scan specific file"),
    directory: Optional[str] = typer.Option(None, "--directory", "-d", help="Scan specific directory"),
):
    """
    Scan codebase for secrets and vulnerabilities

    Example:
        br security scan
        br security scan --file config.py
        br security scan --directory src/
    """
    project_root = Path.cwd()

    console.print("\n[bold blue]🔍 Scanning for Security Issues...[/bold blue]\n")

    # Determine what to scan
    if file:
        scan_path = Path(file)
        if not scan_path.exists():
            console.print(f"[red]Error: File not found: {file}[/red]")
            sys.exit(1)
    elif directory:
        scan_path = Path(directory)
        if not scan_path.exists():
            console.print(f"[red]Error: Directory not found: {directory}[/red]")
            sys.exit(1)
    else:
        scan_path = project_root

    # Scan for secrets
    secret_detector = SecretDetector(project_root)
    if scan_path.is_file():
        secret_matches = secret_detector.scan_file(str(scan_path))
        secret_results = {str(scan_path): secret_matches} if secret_matches else {}
    else:
        secret_results = secret_detector.scan_directory(str(scan_path))

    # Scan for SQL injection
    sql_detector = SQLInjectionDetector(project_root)
    if scan_path.is_file():
        sql_matches = sql_detector.scan_file(str(scan_path))
        sql_results = {str(scan_path): sql_matches} if sql_matches else {}
    else:
        sql_results = sql_detector.scan_directory(str(scan_path))

    # Display results
    total_issues = sum(len(m) for m in secret_results.values()) + sum(len(m) for m in sql_results.values())

    if total_issues == 0:
        console.print("[bold green]✅ No security issues found[/bold green]\n")
    else:
        console.print(f"[bold red]Found {total_issues} security issues:[/bold red]\n")

        if secret_results:
            console.print("[bold yellow]Secrets:[/bold yellow]")
            for file_path, matches in secret_results.items():
                console.print(f"  {file_path}: {len(matches)} secret(s)")

        if sql_results:
            console.print("[bold yellow]SQL Injection Risks:[/bold yellow]")
            for file_path, matches in sql_results.items():
                console.print(f"  {file_path}: {len(matches)} vulnerability(ies)")

        console.print("\nRun [cyan]br security check[/cyan] for detailed information.\n")


@security_app.command("precommit")
def security_precommit():
    """
    Run pre-commit security checks (called by git hook)

    This command is typically called automatically by the git pre-commit hook.
    Exit code 0 = checks passed, 1 = checks failed (blocks commit)

    Example:
        br security precommit
    """
    project_root = Path.cwd()
    manager = GitHookManager(project_root)

    result = manager.run_precommit_checks()

    # Print formatted result
    print(format_hook_result(result))

    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


@hooks_app.command("install")
def hooks_install(
    force: bool = typer.Option(False, "--force", "-f", help="Overwrite existing hook"),
):
    """
    Install git pre-commit hook for security checks

    The hook will automatically check for:
    - Secrets in staged files
    - SQL injection vulnerabilities
    - Test coverage (warning only)

    Example:
        br security hooks install
        br security hooks install --force
    """
    console.print("\n[bold blue]Installing Security Pre-Commit Hook...[/bold blue]\n")

    project_root = Path.cwd()
    manager = GitHookManager(project_root)

    if not manager.is_git_repo():
        console.print("[red]Error: Not a git repository[/red]")
        console.print("Run [cyan]git init[/cyan] first.\n")
        sys.exit(1)

    success, message = manager.install_hook('pre-commit', force=force)

    if success:
        console.print(f"[green]{message}[/green]")
        console.print("\n[bold yellow]Hook Details:[/bold yellow]")
        console.print("  • Checks run automatically before each commit")
        console.print("  • Blocks commits with security issues")
        console.print("  • Execution time: <2 seconds")
        console.print("\n[bold yellow]To bypass (not recommended):[/bold yellow]")
        console.print("  git commit --no-verify\n")
    else:
        console.print(f"[red]{message}[/red]")
        if "already exists" in message and not force:
            console.print("\nUse [cyan]--force[/cyan] to overwrite existing hook.\n")
        sys.exit(1)


@hooks_app.command("uninstall")
def hooks_uninstall():
    """
    Uninstall git pre-commit hook

    Example:
        br security hooks uninstall
    """
    console.print("\n[bold blue]Uninstalling Security Pre-Commit Hook...[/bold blue]\n")

    project_root = Path.cwd()
    manager = GitHookManager(project_root)

    if not manager.is_git_repo():
        console.print("[red]Error: Not a git repository[/red]\n")
        sys.exit(1)

    success, message = manager.uninstall_hook('pre-commit')

    if success:
        console.print(f"[green]{message}[/green]\n")
    else:
        console.print(f"[red]{message}[/red]\n")
        sys.exit(1)


@hooks_app.command("status")
def hooks_status():
    """
    Check git hook installation status

    Example:
        br security hooks status
    """
    console.print("\n[bold blue]Git Hook Status[/bold blue]\n")

    project_root = Path.cwd()
    manager = GitHookManager(project_root)

    status = manager.get_hook_status()

    if not status['is_git_repo']:
        console.print("[red]Not a git repository[/red]\n")
        sys.exit(1)

    # Create status table
    table = Table(show_header=True, header_style="bold cyan")
    table.add_column("Hook", style="dim")
    table.add_column("Status")
    table.add_column("Path", style="dim")

    hook_info = status['pre-commit']
    status_text = "[green]✓ Installed[/green]" if hook_info['installed'] else "[red]✗ Not installed[/red]"
    table.add_row("pre-commit", status_text, hook_info['path'])

    console.print(table)

    if not hook_info['installed']:
        console.print("\n[yellow]Install hook with:[/yellow] br security hooks install\n")
    else:
        console.print()
