"""
Migration tools for BuildRunner 2.0 → 3.0

This package provides tools to migrate legacy BuildRunner 2.0 projects
to the new BuildRunner 3.0 format with zero data loss.
"""

from .v2_parser import V2ProjectParser, V2Project
from .converter import MigrationConverter
from .validators import MigrationValidator
from .git_handler import GitMigrationHandler

__all__ = [
    "V2ProjectParser",
    "V2Project",
    "MigrationConverter",
    "MigrationValidator",
    "GitMigrationHandler",
]
