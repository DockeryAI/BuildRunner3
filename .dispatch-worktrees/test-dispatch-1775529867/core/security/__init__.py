"""Security module for BuildRunner.

This module provides security safeguards including:
- Secret detection and masking
- SQL injection detection
- Pre-commit hooks
"""

from .secret_masker import SecretMasker
from .secret_detector import SecretDetector, SecretMatch
from .sql_injection_detector import SQLInjectionDetector, SQLInjectionMatch
from .git_hooks import GitHookManager, HookResult, format_hook_result

__all__ = [
    "SecretMasker",
    "SecretDetector",
    "SecretMatch",
    "SQLInjectionDetector",
    "SQLInjectionMatch",
    "GitHookManager",
    "HookResult",
    "format_hook_result",
]
