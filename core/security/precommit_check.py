"""Standalone pre-commit check script.

This script is called by the git pre-commit hook to run security checks.
It's designed to be fast (<2s) and provide clear feedback.
"""

import sys
from pathlib import Path

# Add project root to path
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from core.security.git_hooks import GitHookManager, format_hook_result


def main():
    """Run pre-commit checks and exit with appropriate code."""
    manager = GitHookManager()
    result = manager.run_precommit_checks()

    # Print result
    print(format_hook_result(result))

    # Exit with appropriate code
    sys.exit(0 if result.passed else 1)


if __name__ == '__main__':
    main()
