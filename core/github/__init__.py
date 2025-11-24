"""
GitHub Automation Module

Provides complete GitHub workflow automation including:
- Branch management
- Release/versioning
- PR automation
- Deployment workflows
- Metrics and analytics
"""

from .branch_manager import BranchManager
from .push_intelligence import PushIntelligence
from .conflict_detector import ConflictDetector
from .version_manager import VersionManager
from .changelog_generator import ChangelogGenerator
from .release_manager import ReleaseManager
from .pr_manager import PRManager
from .commit_builder import CommitBuilder
from .protection_manager import ProtectionManager
from .snapshot_manager import SnapshotManager
from .metrics_tracker import MetricsTracker
from .health_checker import HealthChecker
from .issues_manager import IssuesManager
from .coauthor_manager import CoAuthorManager
from .deployment_manager import DeploymentManager

__all__ = [
    'BranchManager',
    'PushIntelligence',
    'ConflictDetector',
    'VersionManager',
    'ChangelogGenerator',
    'ReleaseManager',
    'PRManager',
    'CommitBuilder',
    'ProtectionManager',
    'SnapshotManager',
    'MetricsTracker',
    'HealthChecker',
    'IssuesManager',
    'CoAuthorManager',
    'DeploymentManager',
]

__version__ = '1.0.0'
