"""
Dashboard Views for BuildRunner 3.0

Multi-repo dashboard to aggregate status across all BuildRunner projects.
Because one burning repository isn't enough - let's see ALL of them at once.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from dataclasses import dataclass, field


@dataclass
class ProjectStatus:
    """Status for a single BuildRunner project"""

    name: str
    path: Path
    version: str
    status: str
    total_features: int
    completed: int
    in_progress: int
    planned: int
    completion_percentage: float
    last_updated: datetime
    blockers: List[str] = field(default_factory=list)
    active_features: List[str] = field(default_factory=list)

    @property
    def is_stale(self) -> bool:
        """Check if project hasn't been updated in >7 days"""
        return (datetime.now() - self.last_updated).days > 7

    @property
    def health_status(self) -> str:
        """Overall health: healthy, warning, critical"""
        if len(self.blockers) > 0:
            return "critical"
        elif self.is_stale or self.in_progress > self.completed:
            return "warning"
        else:
            return "healthy"


class DashboardScanner:
    """
    Scans filesystem for BuildRunner projects.

    Looks for .buildrunner/features.json files to identify projects.
    Because recursively searching filesystems is always a good idea.
    """

    def __init__(self, root_path: Optional[Path] = None):
        """
        Initialize scanner.

        Args:
            root_path: Root directory to start scanning (default: current directory)
        """
        self.root_path = Path(root_path or Path.cwd())

    def discover_projects(self, max_depth: int = 5) -> List[ProjectStatus]:
        """
        Discover all BuildRunner projects.

        Args:
            max_depth: Maximum directory depth to search

        Returns:
            List of ProjectStatus objects
        """
        projects = []

        # Search for features.json files
        for features_file in self._find_features_files(max_depth):
            try:
                project = self._parse_project(features_file)
                if project:
                    projects.append(project)
            except Exception as e:
                print(f"⚠️  Failed to parse project at {features_file.parent}: {e}")

        return sorted(projects, key=lambda p: p.name)

    def _find_features_files(self, max_depth: int) -> List[Path]:
        """Find all .buildrunner/features.json files"""
        features_files = []

        def search_dir(path: Path, depth: int):
            if depth > max_depth:
                return

            try:
                for item in path.iterdir():
                    if item.is_dir():
                        # Check if this is a .buildrunner directory
                        if item.name == ".buildrunner":
                            features_json = item / "features.json"
                            if features_json.exists():
                                features_files.append(features_json)
                        # Don't recurse into common exclusions
                        elif item.name not in {
                            ".git",
                            "node_modules",
                            ".venv",
                            "venv",
                            "__pycache__",
                            "dist",
                            "build",
                        }:
                            search_dir(item, depth + 1)
            except PermissionError:
                pass  # Skip directories we can't access

        search_dir(self.root_path, 0)
        return features_files

    def _parse_project(self, features_file: Path) -> Optional[ProjectStatus]:
        """Parse a single project from features.json"""
        try:
            with open(features_file, "r") as f:
                data = json.load(f)

            # Extract project info
            project_name = data.get("project", "Unknown")
            version = data.get("version", "0.0.0")
            status = data.get("status", "unknown")
            features = data.get("features", [])
            metrics = data.get("metrics", {})
            last_updated_str = data.get("last_updated", datetime.now().isoformat())

            # Parse last updated
            try:
                last_updated = datetime.fromisoformat(last_updated_str.replace("Z", "+00:00"))
            except:
                last_updated = datetime.now()

            # Count features by status
            total = len(features)
            completed = sum(1 for f in features if f.get("status") == "complete")
            in_progress = sum(1 for f in features if f.get("status") == "in_progress")
            planned = sum(1 for f in features if f.get("status") == "planned")

            completion = metrics.get("completion_percentage", 0)
            if total > 0 and completion == 0:
                completion = round((completed / total) * 100, 1)

            # Get active features (in_progress)
            active_features = [
                f.get("name", "Unknown") for f in features if f.get("status") == "in_progress"
            ]

            # Check for blockers (TODO: could read from .buildrunner/context/blockers.md)
            blockers = []

            return ProjectStatus(
                name=project_name,
                path=features_file.parent.parent,  # Go up from .buildrunner/features.json
                version=version,
                status=status,
                total_features=total,
                completed=completed,
                in_progress=in_progress,
                planned=planned,
                completion_percentage=completion,
                last_updated=last_updated,
                blockers=blockers,
                active_features=active_features[:5],  # Limit to 5
            )

        except Exception as e:
            print(f"Error parsing {features_file}: {e}")
            return None


class DashboardViews:
    """
    Generate different dashboard views.

    Views include: Overview, Detail, Timeline, Alerts.
    """

    def __init__(self, projects: List[ProjectStatus]):
        """
        Initialize with list of projects.

        Args:
            projects: List of ProjectStatus objects
        """
        self.projects = projects

    def get_overview_data(self) -> Dict[str, Any]:
        """
        Get overview data for all projects.

        Returns:
            Dictionary with aggregated metrics
        """
        total_projects = len(self.projects)
        total_features = sum(p.total_features for p in self.projects)
        total_completed = sum(p.completed for p in self.projects)
        total_in_progress = sum(p.in_progress for p in self.projects)
        total_planned = sum(p.planned for p in self.projects)

        overall_completion = 0
        if total_features > 0:
            overall_completion = round((total_completed / total_features) * 100, 1)

        stale_projects = [p for p in self.projects if p.is_stale]
        blocked_projects = [p for p in self.projects if len(p.blockers) > 0]
        active_projects = [p for p in self.projects if p.in_progress > 0]

        return {
            "total_projects": total_projects,
            "total_features": total_features,
            "total_completed": total_completed,
            "total_in_progress": total_in_progress,
            "total_planned": total_planned,
            "overall_completion": overall_completion,
            "stale_projects": len(stale_projects),
            "blocked_projects": len(blocked_projects),
            "active_projects": len(active_projects),
            "projects": self.projects,
        }

    def get_detail_data(self, project_name: str) -> Optional[Dict[str, Any]]:
        """
        Get detailed data for a single project.

        Args:
            project_name: Name of project to get details for

        Returns:
            Project details or None if not found
        """
        project = next((p for p in self.projects if p.name == project_name), None)
        if not project:
            return None

        return {
            "project": project,
            "features_by_status": {
                "completed": project.completed,
                "in_progress": project.in_progress,
                "planned": project.planned,
            },
            "health": project.health_status,
            "days_since_update": (datetime.now() - project.last_updated).days,
        }

    def get_timeline_data(self, days: int = 30) -> List[Dict[str, Any]]:
        """
        Get timeline of recent activity.

        Args:
            days: Number of days to include

        Returns:
            List of activity events
        """
        cutoff = datetime.now() - timedelta(days=days)
        timeline = []

        for project in self.projects:
            if project.last_updated >= cutoff:
                timeline.append(
                    {
                        "project": project.name,
                        "timestamp": project.last_updated,
                        "event": "updated",
                        "completion": project.completion_percentage,
                    }
                )

        return sorted(timeline, key=lambda x: x["timestamp"], reverse=True)

    def get_alerts_data(self) -> Dict[str, List[ProjectStatus]]:
        """
        Get alerts for problematic projects.

        Returns:
            Dictionary with different alert categories
        """
        stale_projects = [p for p in self.projects if p.is_stale]
        blocked_projects = [p for p in self.projects if len(p.blockers) > 0]
        no_progress = [p for p in self.projects if p.in_progress == 0 and p.planned > 0]
        high_wip = [p for p in self.projects if p.in_progress > 5]  # Too much WIP

        return {
            "stale": stale_projects,
            "blocked": blocked_projects,
            "no_progress": no_progress,
            "high_wip": high_wip,
        }

    def get_summary_stats(self) -> str:
        """
        Get a text summary of key stats.

        Returns:
            Formatted summary string
        """
        overview = self.get_overview_data()

        return f"""📊 Multi-Repo Dashboard Summary

Projects: {overview['total_projects']}
Features: {overview['total_completed']}/{overview['total_features']} complete ({overview['overall_completion']}%)
Active: {overview['active_projects']} projects in progress
Alerts: {overview['stale_projects']} stale, {overview['blocked_projects']} blocked
"""
