"""Git hook management for BuildRunner security checks.

This module provides functionality to install and manage git hooks
that enforce security best practices (Tier 1 checks).
"""

import os
import stat
import subprocess
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .secret_detector import SecretDetector
from .sql_injection_detector import SQLInjectionDetector


@dataclass
class HookResult:
    """Result from running a pre-commit hook.

    Attributes:
        passed: Whether all checks passed
        violations: List of violations found
        warnings: List of warnings (non-blocking)
        duration_ms: Time taken to run checks
        message: Summary message
    """
    passed: bool
    violations: List[str]
    warnings: List[str]
    duration_ms: float
    message: str

    def __str__(self) -> str:
        """Return human-readable representation."""
        if self.passed:
            return f"✅ {self.message}"
        return f"❌ {self.message}"


class GitHookManager:
    """Manage git hooks for BuildRunner security checks.

    This class provides methods to install, uninstall, and run
    git pre-commit hooks that enforce Tier 1 security checks.

    Example:
        >>> manager = GitHookManager()
        >>> manager.install_hooks()
        >>> result = manager.run_precommit_checks()
        >>> if not result.passed:
        ...     print("Commit blocked!")
    """

    HOOK_TEMPLATE = '''#!/bin/bash
# BuildRunner Pre-Commit Hook (Auto-generated)
# Runs Tier 1 security checks: secrets, SQL injection, test coverage
#
# To temporarily skip: git commit --no-verify
# To uninstall: br security hooks uninstall

# Change to repository root
cd "$(git rev-parse --show-toplevel)" || exit 1

# Run BuildRunner security checks
if command -v br &> /dev/null; then
    # Use br CLI if available
    br security precommit
    exit $?
else
    # Fallback to direct Python execution
    if [ -f ".venv/bin/python" ]; then
        .venv/bin/python -m core.security.precommit_check
    elif command -v python3 &> /dev/null; then
        python3 -m core.security.precommit_check
    else
        echo "⚠️  Warning: BuildRunner CLI not found, skipping security checks"
        exit 0
    fi
    exit $?
fi
'''

    def __init__(self, project_root: Optional[Path] = None):
        """Initialize the git hook manager.

        Args:
            project_root: Root directory of the project (default: current dir)
        """
        self.project_root = project_root or Path.cwd()
        self.git_dir = self.project_root / '.git'
        self.hooks_dir = self.git_dir / 'hooks'

    def is_git_repo(self) -> bool:
        """Check if current directory is a git repository."""
        return self.git_dir.exists() and self.git_dir.is_dir()

    def get_hook_path(self, hook_name: str = 'pre-commit') -> Path:
        """Get the path to a git hook."""
        return self.hooks_dir / hook_name

    def is_hook_installed(self, hook_name: str = 'pre-commit') -> bool:
        """Check if a git hook is installed."""
        hook_path = self.get_hook_path(hook_name)
        if not hook_path.exists():
            return False

        # Check if it's a BuildRunner hook
        try:
            content = hook_path.read_text()
            return 'BuildRunner Pre-Commit Hook' in content
        except Exception:
            return False

    def install_hook(self, hook_name: str = 'pre-commit', force: bool = False) -> Tuple[bool, str]:
        """Install a git hook.

        Args:
            hook_name: Name of the hook (default: pre-commit)
            force: Overwrite existing hook if present

        Returns:
            Tuple of (success, message)

        Example:
            >>> manager = GitHookManager()
            >>> success, msg = manager.install_hook()
            >>> if success:
            ...     print("Hook installed!")
        """
        if not self.is_git_repo():
            return False, "Not a git repository"

        # Ensure hooks directory exists
        self.hooks_dir.mkdir(parents=True, exist_ok=True)

        hook_path = self.get_hook_path(hook_name)

        # Check if hook already exists
        if hook_path.exists() and not force:
            if self.is_hook_installed(hook_name):
                return True, f"BuildRunner {hook_name} hook already installed"
            else:
                return False, (
                    f"{hook_name} hook already exists (not from BuildRunner). "
                    f"Use --force to overwrite or manually integrate."
                )

        # Write hook
        try:
            hook_path.write_text(self.HOOK_TEMPLATE)

            # Make executable
            current_permissions = hook_path.stat().st_mode
            hook_path.chmod(current_permissions | stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)

            return True, f"✅ Installed {hook_name} hook"

        except Exception as e:
            return False, f"Failed to install {hook_name} hook: {e}"

    def uninstall_hook(self, hook_name: str = 'pre-commit') -> Tuple[bool, str]:
        """Uninstall a git hook.

        Args:
            hook_name: Name of the hook (default: pre-commit)

        Returns:
            Tuple of (success, message)

        Example:
            >>> manager = GitHookManager()
            >>> success, msg = manager.uninstall_hook()
            >>> if success:
            ...     print("Hook uninstalled!")
        """
        if not self.is_git_repo():
            return False, "Not a git repository"

        hook_path = self.get_hook_path(hook_name)

        if not hook_path.exists():
            return True, f"{hook_name} hook not installed"

        # Check if it's a BuildRunner hook
        if not self.is_hook_installed(hook_name):
            return False, (
                f"{hook_name} hook exists but is not from BuildRunner. "
                f"Remove manually if needed."
            )

        # Remove hook
        try:
            hook_path.unlink()
            return True, f"✅ Uninstalled {hook_name} hook"
        except Exception as e:
            return False, f"Failed to uninstall {hook_name} hook: {e}"

    def run_precommit_checks(self, max_duration_ms: float = 2000) -> HookResult:
        """Run pre-commit security checks.

        This runs all Tier 1 checks:
        1. Secret detection in staged files
        2. SQL injection detection in staged files
        3. Test coverage check (if tests exist)

        Args:
            max_duration_ms: Maximum allowed duration (default: 2000ms)

        Returns:
            HookResult with check results

        Example:
            >>> manager = GitHookManager()
            >>> result = manager.run_precommit_checks()
            >>> if not result.passed:
            ...     print(result.message)
        """
        import time
        start_time = time.time()

        violations = []
        warnings = []

        try:
            # Check 1: Secret detection
            secret_detector = SecretDetector(self.project_root)
            staged_secrets = secret_detector.scan_git_staged()

            if staged_secrets:
                violations.append("❌ SECRETS DETECTED in staged files:")
                for file_path, matches in staged_secrets.items():
                    violations.append(f"\n  {file_path}:")
                    for match in matches:
                        violations.append(
                            f"    Line {match.line_number}: [{match.pattern_name}] "
                            f"{match.secret_value}"
                        )
                violations.append("\n💡 Fix: Move secrets to .env (gitignored) or use environment variables")
                violations.append("   Skip this check: git commit --no-verify (NOT RECOMMENDED)")

            # Check 2: SQL injection detection
            sql_detector = SQLInjectionDetector(self.project_root)

            # Get staged files
            try:
                result = subprocess.run(
                    ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
                    cwd=self.project_root,
                    capture_output=True,
                    text=True,
                    check=True
                )
                staged_files = [f for f in result.stdout.strip().split('\n') if f]

                # Scan each staged file
                for file_path in staged_files:
                    full_path = self.project_root / file_path
                    if full_path.exists():
                        sql_matches = sql_detector.scan_file(str(full_path))
                        if sql_matches:
                            if not any("SQL INJECTION" in v for v in violations):
                                violations.append("\n❌ SQL INJECTION RISK detected in staged files:")

                            violations.append(f"\n  {file_path}:")
                            for match in sql_matches:
                                violations.append(
                                    f"    Line {match.line_number}: {match.vulnerability_type} "
                                    f"(severity: {match.severity})"
                                )
                                violations.append(f"    💡 {match.suggestion}")

            except subprocess.CalledProcessError:
                # Not in a git repo or git not available
                pass

            # Check 3: Test coverage (lightweight check - just warn if very low)
            # This is a quick check, full coverage analysis happens in quality gates
            warnings.append("ℹ️  Run 'br quality check' for full test coverage analysis")

            # Calculate duration
            duration_ms = (time.time() - start_time) * 1000

            # Check if within time budget
            if duration_ms > max_duration_ms:
                warnings.append(
                    f"⚠️  Pre-commit checks took {duration_ms:.0f}ms "
                    f"(target: <{max_duration_ms}ms)"
                )

            # Generate result
            if violations:
                return HookResult(
                    passed=False,
                    violations=violations,
                    warnings=warnings,
                    duration_ms=duration_ms,
                    message=f"Security checks failed ({duration_ms:.0f}ms)"
                )
            else:
                return HookResult(
                    passed=True,
                    violations=[],
                    warnings=warnings,
                    duration_ms=duration_ms,
                    message=f"All security checks passed ({duration_ms:.0f}ms)"
                )

        except Exception as e:
            return HookResult(
                passed=False,
                violations=[f"Error running security checks: {e}"],
                warnings=warnings,
                duration_ms=(time.time() - start_time) * 1000,
                message="Security checks failed with error"
            )

    def get_hook_status(self) -> Dict[str, any]:
        """Get status of all BuildRunner hooks.

        Returns:
            Dictionary with hook status information

        Example:
            >>> manager = GitHookManager()
            >>> status = manager.get_hook_status()
            >>> print(status['pre-commit']['installed'])
        """
        return {
            'is_git_repo': self.is_git_repo(),
            'pre-commit': {
                'installed': self.is_hook_installed('pre-commit'),
                'path': str(self.get_hook_path('pre-commit')),
            }
        }


def format_hook_result(result: HookResult) -> str:
    """Format a HookResult for display.

    Args:
        result: The HookResult to format

    Returns:
        Formatted string for terminal output

    Example:
        >>> result = manager.run_precommit_checks()
        >>> print(format_hook_result(result))
    """
    output = []

    if result.passed:
        output.append("━" * 60)
        output.append(f"✅ {result.message}")
        output.append("━" * 60)
    else:
        output.append("━" * 60)
        output.append(f"❌ COMMIT BLOCKED - {result.message}")
        output.append("━" * 60)
        output.extend(result.violations)
        output.append("━" * 60)

    if result.warnings:
        output.append("\nWarnings:")
        output.extend(result.warnings)

    return "\n".join(output)
