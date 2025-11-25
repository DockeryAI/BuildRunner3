"""
Branch Manager - Automated branch creation and lifecycle management

Implements:
- Automatic branch naming with governance rules
- Week number calculation
- Branch readiness checks
- Branch cleanup
"""

import json
from pathlib import Path
from typing import Optional, List, Dict
from datetime import datetime, date
from dataclasses import dataclass

from .git_client import GitClient


@dataclass
class BranchInfo:
    """Branch information"""

    name: str
    is_current: bool
    is_feature: bool
    week_number: Optional[int]
    feature_name: Optional[str]
    is_mergeable: bool
    issues: List[str]


class BranchManager:
    """Manage branch lifecycle with governance rules"""

    def __init__(self, repo_path: Optional[Path] = None):
        """
        Initialize branch manager

        Args:
            repo_path: Path to git repository
        """
        self.repo_path = repo_path or Path.cwd()
        self.git = GitClient(self.repo_path)
        self.buildrunner_dir = self.repo_path / ".buildrunner"

    def _load_governance(self) -> Dict:
        """Load governance rules"""
        gov_file = self.buildrunner_dir / "governance" / "governance.yaml"
        if not gov_file.exists():
            return {}

        import yaml

        with open(gov_file) as f:
            return yaml.safe_load(f)

    def _get_branch_pattern(self, branch_type: str = "feature") -> str:
        """Get branch naming pattern from governance"""
        gov = self._load_governance()
        patterns = gov.get("workflow", {}).get("branch_patterns", {})
        return patterns.get(branch_type, "build/week{week_number}-{feature_name}")

    def _calculate_week_number(self) -> int:
        """
        Calculate current week number

        Uses project start date from PROJECT_SPEC or defaults to week 1
        """
        spec_file = self.buildrunner_dir / "PROJECT_SPEC.md"
        if spec_file.exists():
            content = spec_file.read_text()
            # Try to find project start date in spec
            import re

            match = re.search(r"Start Date:\s*(\d{4}-\d{2}-\d{2})", content)
            if match:
                start_date = datetime.strptime(match.group(1), "%Y-%m-%d").date()
                today = date.today()
                days = (today - start_date).days
                week = (days // 7) + 1
                return max(1, week)

        # Default: check features.json for last week used
        features_file = self.buildrunner_dir / "features.json"
        if features_file.exists():
            with open(features_file) as f:
                data = json.load(f)
                # Look for highest week number in completed features
                max_week = 0
                for feature in data.get("features", []):
                    if feature.get("status") == "complete":
                        max_week = max(max_week, 1)
                return max_week + 1

        return 1  # Default to week 1

    def _parse_branch_name(self, branch: str) -> BranchInfo:
        """Parse branch name to extract metadata"""
        import re

        # Match: build/week{N}-{feature} or build/week{N}/{feature}
        match = re.match(r"build/week(\d+)[/-](.+)", branch)
        if match:
            week = int(match.group(1))
            feature = match.group(2)
            return BranchInfo(
                name=branch,
                is_current=branch == self.git.current_branch(),
                is_feature=True,
                week_number=week,
                feature_name=feature,
                is_mergeable=False,  # Will be calculated
                issues=[],
            )

        # Not a feature branch
        return BranchInfo(
            name=branch,
            is_current=branch == self.git.current_branch(),
            is_feature=False,
            week_number=None,
            feature_name=None,
            is_mergeable=False,
            issues=[],
        )

    def create_branch(
        self, feature_name: str, week: Optional[int] = None, checkout: bool = True
    ) -> str:
        """
        Create feature branch with correct naming

        Args:
            feature_name: Feature name (will be slugified)
            week: Week number (auto-calculated if not provided)
            checkout: Whether to checkout the branch

        Returns:
            Created branch name
        """
        # Slugify feature name
        slug = feature_name.lower().replace(" ", "-").replace("_", "-")
        slug = "".join(c for c in slug if c.isalnum() or c == "-")

        # Calculate week number
        if week is None:
            week = self._calculate_week_number()

        # Generate branch name
        pattern = self._get_branch_pattern("feature")
        branch_name = pattern.format(week_number=week, feature_name=slug, name=slug)

        # Create branch
        self.git.create_branch(branch_name, checkout=checkout)

        return branch_name

    def list_feature_branches(self) -> List[BranchInfo]:
        """List all feature branches"""
        branches = self.git.list_branches()
        feature_branches = []

        for branch in branches:
            info = self._parse_branch_name(branch)
            if info.is_feature:
                # Check if mergeable
                info.is_mergeable, info.issues = self.check_branch_ready(branch)
                feature_branches.append(info)

        return sorted(feature_branches, key=lambda b: (b.week_number or 0, b.name))

    def check_branch_ready(self, branch: Optional[str] = None) -> tuple[bool, List[str]]:
        """
        Check if branch is ready to merge

        Args:
            branch: Branch to check (default: current branch)

        Returns:
            (is_ready, list of issues)
        """
        if branch and branch != self.git.current_branch():
            # Can't check non-current branch comprehensively
            return False, ["Can only check current branch"]

        issues = []

        # Check if tests pass (if autodebug available)
        try:
            from core.auto_debug import AutoDebugPipeline

            pipeline = AutoDebugPipeline(self.repo_path)
            report = pipeline.run(skip_deep=True)
            if not report.overall_success:
                issues.append(f"Tests failing: {len(report.critical_failures)} critical failures")
        except Exception:
            # Auto-debug not available, skip test check
            pass

        # Check if behind main
        is_behind, count = self.git.is_behind("origin/main")
        if is_behind:
            issues.append(f"Branch is {count} commits behind origin/main")

        # Check for merge conflicts
        current = self.git.current_branch()
        if current != "main":
            try:
                has_conflicts, files = self.git.has_conflicts_with("origin/main")
                if has_conflicts:
                    issues.append(f"Merge conflicts in {len(files)} files")
            except Exception:
                pass

        # Check if work is committed
        status = self.git.get_status()
        if not status.is_clean:
            issues.append("Uncommitted changes")

        # Check features.json for incomplete features
        features_file = self.buildrunner_dir / "features.json"
        if features_file.exists():
            with open(features_file) as f:
                data = json.load(f)
                incomplete = [
                    f for f in data.get("features", []) if f.get("status") == "in_progress"
                ]
                if incomplete:
                    issues.append(f"{len(incomplete)} features in progress (not complete)")

        return len(issues) == 0, issues

    def cleanup_merged_branches(self, dry_run: bool = False) -> List[str]:
        """
        Delete branches that have been merged

        Args:
            dry_run: If True, just list branches without deleting

        Returns:
            List of deleted (or would-be-deleted) branches
        """
        # Get list of merged branches
        import subprocess

        result = subprocess.run(
            ["git", "branch", "--merged", "main"],
            cwd=self.repo_path,
            capture_output=True,
            text=True,
            check=True,
        )

        merged = []
        for line in result.stdout.splitlines():
            branch = line.strip().lstrip("* ").strip()
            if branch and branch != "main" and not branch.startswith("("):
                merged.append(branch)

        # Delete branches
        if not dry_run:
            for branch in merged:
                try:
                    self.git.delete_branch(branch, force=False)
                except Exception:
                    pass  # Branch might be current or protected

        return merged

    def switch_to_branch(self, feature_name: str) -> Optional[str]:
        """
        Switch to feature branch by feature name

        Args:
            feature_name: Feature name to search for

        Returns:
            Branch name if found and switched, None otherwise
        """
        # Find matching branch
        branches = self.list_feature_branches()
        matching = [
            b for b in branches if b.feature_name and feature_name.lower() in b.feature_name.lower()
        ]

        if not matching:
            return None

        if len(matching) > 1:
            raise ValueError(
                f"Multiple branches match '{feature_name}': " f"{[b.name for b in matching]}"
            )

        branch = matching[0].name
        self.git.checkout(branch)
        return branch

    def get_current_branch_info(self) -> BranchInfo:
        """Get information about current branch"""
        current = self.git.current_branch()
        info = self._parse_branch_name(current)
        info.is_mergeable, info.issues = self.check_branch_ready()
        return info

    def validate_branch_name(self, name: str) -> tuple[bool, Optional[str]]:
        """
        Validate branch name against governance rules

        Returns:
            (is_valid, error_message)
        """
        import re

        pattern = self._get_branch_pattern("feature")
        # Convert pattern to regex
        regex = pattern.replace("{week_number}", r"\d+").replace("{feature_name}", r"[a-z0-9-]+")

        if re.match(f"^{regex}$", name):
            return True, None

        return False, f"Branch name must match pattern: {pattern}"
