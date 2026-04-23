"""
Dashboard Views for BuildRunner 3.0

Multi-repo dashboard to aggregate status across all BuildRunner projects.
Because one burning repository isn't enough - let's see ALL of them at once.

PlanReviewView: Human verification gate for setlist plans — task table,
adversarial findings, test baseline, historical outcomes, code health.

ExecutionMonitorView: Live execution progress — task completion with verify
results, session metrics, drift indicator, affected files preview.
"""

import json
import re
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Any, Optional
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
    completed_date: Optional[datetime] = None  # When project reached 100%
    blockers: List[str] = field(default_factory=list)
    active_features: List[str] = field(default_factory=list)

    @property
    def is_complete(self) -> bool:
        """Check if project is 100% complete"""
        return self.completion_percentage == 100

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

        # Default sort: completed projects first (by completion date desc), then by name
        def sort_key(p: ProjectStatus):
            # Primary: completed projects first (0 for complete, 1 for incomplete)
            is_complete = 0 if p.completion_percentage == 100 else 1
            # Secondary: completion date descending (negate timestamp, or max for None)
            completed_ts = -(p.completed_date.timestamp() if p.completed_date else 0)
            # Tertiary: name alphabetically
            return (is_complete, completed_ts, p.name.lower())

        return sorted(projects, key=sort_key)

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

            # Extract completed_date from features when project is 100% complete
            completed_date = None
            if completion == 100 and total > 0:
                # Get the latest completed_at timestamp from all features
                completed_dates = []
                for feat in features:
                    if feat.get("status") == "complete" and feat.get("completed_at"):
                        try:
                            dt = datetime.fromisoformat(feat["completed_at"].replace("Z", "+00:00"))
                            completed_dates.append(dt)
                        except:
                            pass
                if completed_dates:
                    completed_date = max(completed_dates)

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
                completed_date=completed_date,
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


class PlanReviewView:
    """
    Human verification gate for setlist plans.

    Reads plan files, adversarial findings, and queries cluster APIs
    to present everything a reviewer needs for an informed approve/reject.
    Graceful degradation: plan + adversarial always shown even when
    Walter/Lockwood are offline.
    """

    # Severity sort order — blockers first
    _SEVERITY_ORDER = {"blocker": 0, "warning": 1, "note": 2}

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self.plans_dir = self.project_root / ".buildrunner" / "plans"
        self.plan_file = self._find_latest_plan()

    def _find_latest_plan(self) -> Optional[Path]:
        """Find the most recently modified plan file."""
        if not self.plans_dir.exists():
            return None
        plan_files = sorted(
            self.plans_dir.glob("phase-*-plan.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        return plan_files[0] if plan_files else None

    def get_task_table_data(self) -> List[Dict[str, str]]:
        """
        Parse plan file into structured task rows.

        Returns list of dicts with keys: id, what, why, verify.
        Each row is a single-function task.
        """
        if not self.plan_file or not self.plan_file.exists():
            return []

        content = self.plan_file.read_text()
        tasks = []

        # Parse markdown task sections: ### N.M title
        task_pattern = re.compile(
            r"^###\s+(\d+\.\d+)\s+(.+?)$", re.MULTILINE
        )
        matches = list(task_pattern.finditer(content))

        for i, match in enumerate(matches):
            task_id = match.group(1)
            # Get the block of text until the next task or end
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            block = content[start:end]

            what = self._extract_field(block, "WHAT")
            why = self._extract_field(block, "WHY")
            verify = self._extract_field(block, "VERIFY")

            tasks.append({
                "id": task_id,
                "what": what,
                "why": why,
                "verify": verify,
            })

        return tasks

    def _extract_field(self, block: str, field_name: str) -> str:
        """Extract a field value from a task block (e.g., WHAT, WHY, VERIFY)."""
        pattern = re.compile(
            rf"-\s+{field_name}:\s*(.+?)$", re.MULTILINE
        )
        match = pattern.search(block)
        return match.group(1).strip() if match else ""

    def get_adversarial_data(self) -> List[Dict[str, str]]:
        """
        Read adversarial findings JSON. Sorted: blockers first.

        Returns list of dicts with keys: finding, severity.
        """
        if not self.plans_dir.exists():
            return []

        adv_files = sorted(
            self.plans_dir.glob("adversarial-*.json"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )
        if not adv_files:
            return []

        try:
            findings = json.loads(adv_files[0].read_text())
        except (json.JSONDecodeError, OSError):
            return []

        if not isinstance(findings, list):
            return []

        # Sort by severity: blocker → warning → note
        findings.sort(
            key=lambda f: self._SEVERITY_ORDER.get(
                f.get("severity", "note"), 99
            )
        )
        return findings

    def get_test_baseline_data(self) -> Dict[str, Any]:
        """
        Query Walter for test baseline: file → test mapping with pass/fail.

        Returns empty dict if Walter is offline.
        """
        tasks = self.get_task_table_data()
        if not tasks:
            return {}

        # Extract source files from WHAT fields
        files = []
        for task in tasks:
            # Extract file path from backtick-quoted path
            file_match = re.search(r"`([^`]+\.\w+)`", task.get("what", ""))
            if file_match:
                files.append(file_match.group(1))

        if not files:
            return {}

        result = self._query_walter(files)
        return result if result else {}

    def get_historical_data(self) -> List[Dict[str, Any]]:
        """
        Query Lockwood for similar past plans. Max 3.

        Returns empty list if Lockwood is offline.
        """
        if not self.plan_file or not self.plan_file.exists():
            return []

        # Use plan content as query
        plan_text = self.plan_file.read_text()[:500]
        result = self._query_lockwood(plan_text)
        if not result:
            return []
        return result[:3]

    def get_code_health_data(self) -> Dict[str, float]:
        """
        Check health scores for planned files.

        Returns dict of file_path → health_score.
        Files with health < 9.5 should trigger a warning bar.
        """
        tasks = self.get_task_table_data()
        health = {}

        for task in tasks:
            file_match = re.search(r"`([^`]+\.\w+)`", task.get("what", ""))
            if file_match:
                file_path = file_match.group(1)
                full_path = self.project_root / file_path
                if full_path.exists():
                    # Simple health heuristic: file exists and is non-empty
                    try:
                        size = full_path.stat().st_size
                        health[file_path] = 10.0 if size > 0 else 0.0
                    except OSError:
                        health[file_path] = 0.0
                else:
                    # File doesn't exist yet — neutral (will be created)
                    health[file_path] = 10.0

        return health

    def get_actions(self) -> List[Dict[str, str]]:
        """
        Available review actions.

        Returns list of action dicts with name and description.
        """
        return [
            {
                "name": "approve",
                "description": "Approve plan and hand to /begin for execution",
                "shortcut": "a",
            },
            {
                "name": "revise",
                "description": "Add per-task comments for targeted re-synthesis",
                "shortcut": "r",
            },
            {
                "name": "reject",
                "description": "Reject plan with reason, archive to Lockwood",
                "shortcut": "x",
            },
        ]

    def get_build_spec_context(self) -> Dict[str, Any]:
        """
        Extract current phase context from BUILD spec.

        Finds BUILD_*.md in .buildrunner/builds/, extracts the phase matching
        the current plan's phase number: goal, deliverables, success criteria.
        Returns empty dict if BUILD spec not found or phase not parseable.
        """
        if not self.plan_file:
            return {}

        # Extract phase number from plan filename (phase-N-plan.md)
        phase_match = re.search(r"phase-(\d+)", self.plan_file.name)
        if not phase_match:
            return {}
        phase_num = phase_match.group(1)

        # Find BUILD spec files
        builds_dir = self.project_root / ".buildrunner" / "builds"
        if not builds_dir.exists():
            return {}

        build_files = list(builds_dir.glob("BUILD_*.md"))
        if not build_files:
            return {}

        # Collect plan file paths to match against BUILD spec phases
        plan_files_mentioned = set()
        tasks = self.get_task_table_data()
        for task in tasks:
            file_match = re.search(r"`([^`]+\.\w+)`", task.get("what", ""))
            if file_match:
                plan_files_mentioned.add(file_match.group(1))

        # Search each BUILD spec for the matching phase, prefer one referencing plan files
        candidates = []
        for build_file in build_files:
            try:
                content = build_file.read_text()
            except OSError:
                continue

            # Find phase section: ### Phase N: Title
            phase_pattern = re.compile(
                rf"^###\s+Phase\s+{phase_num}:\s*(.+?)$",
                re.MULTILINE,
            )
            match = phase_pattern.search(content)
            if not match:
                continue

            phase_title = match.group(1).strip()
            start = match.end()

            # Find end of phase section (next ### Phase or end of file)
            next_phase = re.search(r"^###\s+Phase\s+\d+:", content[start:], re.MULTILINE)
            end = start + next_phase.start() if next_phase else len(content)
            section = content[start:end]

            # Extract deliverables (lines starting with - [ ] or - [x])
            deliverables = re.findall(
                r"^-\s+\[[ x]\]\s+(.+?)$", section, re.MULTILINE
            )

            # Extract success criteria
            sc_match = re.search(
                r"\*\*Success Criteria:\*\*\s*(.+?)(?:\n\n|\n---|\Z)",
                section, re.DOTALL,
            )
            success_criteria = sc_match.group(1).strip() if sc_match else ""

            # Score by how many plan files are mentioned in this phase section
            score = sum(1 for pf in plan_files_mentioned if pf in section)
            candidates.append({
                "phase_num": int(phase_num),
                "title": phase_title,
                "build_file": build_file.name,
                "deliverables": deliverables,
                "success_criteria": success_criteria,
                "_score": score,
            })

        if not candidates:
            return {}

        # Pick the candidate with the most file references from the plan
        best = max(candidates, key=lambda c: c["_score"])
        best.pop("_score", None)
        return best

    def get_dependency_diagram(self) -> List[Dict[str, Any]]:
        """
        Parse dependency section from plan file into a tree structure.

        Looks for a Dependencies or Dependency section in the plan.
        Returns list of nodes: [{task, depends_on: [ids]}].
        Returns empty list if no dependency section found.
        """
        if not self.plan_file or not self.plan_file.exists():
            return []

        content = self.plan_file.read_text()

        # Look for a dependency section
        dep_section_match = re.search(
            r"^##\s+Dependenc(?:y|ies)\b.*?\n(.*?)(?=^##\s|\Z)",
            content, re.MULTILINE | re.DOTALL,
        )
        if not dep_section_match:
            return []

        section = dep_section_match.group(1)
        nodes = []

        # Parse lines like: "- 8.2 depends on 8.1" or "- 8.3 -> 8.1, 8.2"
        for line in section.strip().splitlines():
            line = line.strip().lstrip("- ")
            if not line:
                continue

            # Pattern: "X.Y depends on A.B, C.D" or "X.Y -> A.B, C.D"
            dep_match = re.match(
                r"(\d+\.\d+)\s+(?:depends\s+on|->|:)\s+(.+)",
                line, re.IGNORECASE,
            )
            if dep_match:
                task_id = dep_match.group(1)
                deps = [d.strip() for d in dep_match.group(2).split(",")]
                nodes.append({"task": task_id, "depends_on": deps})
            else:
                # Standalone task with no deps
                id_match = re.match(r"(\d+\.\d+)", line)
                if id_match:
                    nodes.append({"task": id_match.group(1), "depends_on": []})

        return nodes

    def get_plan_diff(self) -> Dict[str, Any]:
        """
        Compare current plan with previous version for the same phase.

        Finds plan files for the same phase number, compares task lists.
        Returns {added: [], removed: [], modified: [], has_previous: bool}.
        """
        if not self.plan_file or not self.plan_file.exists():
            return {"added": [], "removed": [], "modified": [], "has_previous": False}

        # Get phase number from current plan
        phase_match = re.search(r"phase-(\d+)", self.plan_file.name)
        if not phase_match:
            return {"added": [], "removed": [], "modified": [], "has_previous": False}

        phase_num = phase_match.group(1)

        # Find all plan files for this phase, sorted by mtime (newest first)
        plan_files = sorted(
            self.plans_dir.glob(f"phase-{phase_num}-plan*.md"),
            key=lambda p: p.stat().st_mtime,
            reverse=True,
        )

        # Need at least 2 files (current + previous)
        if len(plan_files) < 2:
            return {"added": [], "removed": [], "modified": [], "has_previous": False}

        previous_file = plan_files[1]

        # Parse tasks from both files
        current_tasks = self._parse_tasks_from_file(self.plan_file)
        previous_tasks = self._parse_tasks_from_file(previous_file)

        current_ids = {t["id"] for t in current_tasks}
        previous_ids = {t["id"] for t in previous_tasks}

        current_map = {t["id"]: t for t in current_tasks}
        previous_map = {t["id"]: t for t in previous_tasks}

        added = [current_map[tid] for tid in current_ids - previous_ids]
        removed = [previous_map[tid] for tid in previous_ids - current_ids]

        modified = []
        for tid in current_ids & previous_ids:
            if current_map[tid]["what"] != previous_map[tid]["what"]:
                modified.append({
                    "id": tid,
                    "old_what": previous_map[tid]["what"],
                    "new_what": current_map[tid]["what"],
                })

        return {
            "added": added,
            "removed": removed,
            "modified": modified,
            "has_previous": True,
            "previous_file": previous_file.name,
        }

    def _parse_tasks_from_file(self, file_path: Path) -> List[Dict[str, str]]:
        """Parse task list from a plan file."""
        content = file_path.read_text()
        tasks = []
        task_pattern = re.compile(r"^###\s+(\d+\.\d+)\s+(.+?)$", re.MULTILINE)
        matches = list(task_pattern.finditer(content))

        for i, match in enumerate(matches):
            task_id = match.group(1)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            block = content[start:end]

            tasks.append({
                "id": task_id,
                "what": self._extract_field(block, "WHAT"),
                "why": self._extract_field(block, "WHY"),
                "verify": self._extract_field(block, "VERIFY"),
            })

        return tasks

    def get_full_review_data(self) -> Dict[str, Any]:
        """
        Aggregate all review data into a single dict for rendering.

        Graceful: plan + adversarial always present.
        Test baseline, history, health — best-effort.
        """
        data = {
            "plan_file": str(self.plan_file) if self.plan_file else None,
            "tasks": self.get_task_table_data(),
            "adversarial": self.get_adversarial_data(),
            "actions": self.get_actions(),
        }

        # Best-effort cluster queries
        try:
            data["test_baseline"] = self.get_test_baseline_data()
        except Exception:
            data["test_baseline"] = {}

        try:
            data["history"] = self.get_historical_data()
        except Exception:
            data["history"] = []

        try:
            data["code_health"] = self.get_code_health_data()
        except Exception:
            data["code_health"] = {}

        return data

    def _query_walter(self, files: List[str]) -> Optional[Dict[str, Any]]:
        """Query Walter node for test mapping. Returns None if offline."""
        try:
            result = subprocess.run(
                ["bash", "-c",
                 "~/.buildrunner/scripts/cluster-check.sh test-runner 2>/dev/null"],
                capture_output=True, text=True, timeout=5,
            )
            walter_url = result.stdout.strip()
            if not walter_url:
                return None

            import urllib.request
            files_param = ",".join(files)
            url = f"{walter_url}/api/testmap?files={files_param}"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                return json.loads(resp.read())
        except Exception:
            return None

    def _query_lockwood(self, query_text: str) -> Optional[List[Dict[str, Any]]]:
        """Query Lockwood node for similar plans. Returns None if offline."""
        try:
            result = subprocess.run(
                ["bash", "-c",
                 "~/.buildrunner/scripts/cluster-check.sh semantic-search 2>/dev/null"],
                capture_output=True, text=True, timeout=5,
            )
            lockwood_url = result.stdout.strip()
            if not lockwood_url:
                return None

            import urllib.request
            import urllib.parse
            encoded_query = urllib.parse.quote(query_text[:200])
            url = f"{lockwood_url}/api/plans/similar?query={encoded_query}&limit=3"
            req = urllib.request.Request(url, method="GET")
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read())
                return data.get("results", [])
        except Exception:
            return None


class ExecutionMonitorView:
    """
    Live execution monitor for /begin runs with setlist gates.

    Reads progress.json from lock directories to show task completion,
    session metrics, drift indicators, and affected file previews.
    The Lusser's Law dashboard — every unverified step compounds.
    """

    # Thresholds for color coding
    _INTERACTION_LIMIT = 70
    _TIME_LIMIT_MINUTES = 35

    def __init__(self, project_root: Path):
        self.project_root = Path(project_root)
        self._progress = self._load_progress()
        self._plan_tasks = self._load_plan_tasks()

    def _find_latest_progress(self) -> Optional[Path]:
        """Find the most recent progress.json in any lock directory."""
        locks_dir = self.project_root / ".buildrunner" / "locks"
        if not locks_dir.exists():
            return None

        progress_files = []
        for lock_dir in locks_dir.iterdir():
            if lock_dir.is_dir():
                pf = lock_dir / "progress.json"
                if pf.exists():
                    progress_files.append(pf)

        if not progress_files:
            return None

        return max(progress_files, key=lambda p: p.stat().st_mtime)

    def _load_progress(self) -> Dict[str, Any]:
        """Load progress.json data."""
        pf = self._find_latest_progress()
        if not pf:
            return {}
        try:
            return json.loads(pf.read_text())
        except (json.JSONDecodeError, OSError):
            return {}

    def _load_plan_tasks(self) -> List[Dict[str, str]]:
        """Load tasks from the plan file matching the current phase."""
        phase = self._progress.get("phase")
        plans_dir = self.project_root / ".buildrunner" / "plans"
        if not plans_dir.exists():
            return []

        if phase:
            plan_file = plans_dir / f"phase-{phase}-plan.md"
            if not plan_file.exists():
                plan_file = None
        else:
            plan_file = None

        if not plan_file:
            plan_files = sorted(
                plans_dir.glob("phase-*-plan.md"),
                key=lambda p: p.stat().st_mtime,
                reverse=True,
            )
            plan_file = plan_files[0] if plan_files else None

        if not plan_file or not plan_file.exists():
            return []

        content = plan_file.read_text()
        tasks = []

        task_pattern = re.compile(
            r"^###\s+(\d+\.\d+)\s+(.+?)$", re.MULTILINE
        )
        matches = list(task_pattern.finditer(content))

        for i, match in enumerate(matches):
            task_id = match.group(1)
            start = match.end()
            end = matches[i + 1].start() if i + 1 < len(matches) else len(content)
            block = content[start:end]

            what = self._extract_field(block, "WHAT")
            verify = self._extract_field(block, "VERIFY")

            file_match = re.search(r"`([^`]+\.\w+)`", what)
            file_path = file_match.group(1) if file_match else ""

            tasks.append({
                "id": task_id,
                "what": what,
                "verify": verify,
                "file": file_path,
            })

        return tasks

    @staticmethod
    def _extract_field(block: str, field_name: str) -> str:
        """Extract a field value from a task block."""
        pattern = re.compile(
            rf"-\s+{field_name}:\s*(.+?)$", re.MULTILINE
        )
        match = pattern.search(block)
        return match.group(1).strip() if match else ""

    def get_task_progress(self) -> Dict[str, Any]:
        """
        Task progress with verify results.

        Returns dict with tasks (each with verify_result), tasks_done,
        tasks_total, consecutive_failures, and current_task.
        """
        verify_results = {
            r["task_id"]: r["result"]
            for r in self._progress.get("verify_results", [])
        }

        tasks = []
        for task in self._plan_tasks:
            tasks.append({
                "id": task["id"],
                "what": task["what"],
                "verify": task["verify"],
                "verify_result": verify_results.get(task["id"], "pending"),
            })

        return {
            "tasks": tasks,
            "tasks_done": self._progress.get("tasks_done", 0),
            "tasks_total": self._progress.get("tasks_total", len(self._plan_tasks)),
            "consecutive_failures": self._progress.get("consecutive_failures", 0),
            "current_task": self._progress.get("current_task"),
        }

    def get_session_metrics(self) -> Dict[str, Any]:
        """
        Session metrics: interaction count, elapsed time, compaction count.

        Colors: normal (< 80%), yellow (80-99%), red (>= 100%).
        """
        interaction_count = self._progress.get("interaction_count", 0)
        compaction_count = self._progress.get("compaction_count", 0)

        started_at = self._progress.get("started_at")
        if started_at:
            try:
                start = datetime.fromisoformat(started_at.replace("Z", "+00:00"))
                now = datetime.now(start.tzinfo) if start.tzinfo else datetime.now()
                elapsed = (now - start).total_seconds() / 60.0
            except (ValueError, TypeError):
                elapsed = 0.0
        else:
            elapsed = 0.0

        def _color(value: float, limit: float) -> str:
            pct = value / limit if limit > 0 else 0
            if pct >= 1.0:
                return "red"
            elif pct >= 0.8:
                return "yellow"
            return "normal"

        return {
            "interaction_count": interaction_count,
            "interaction_limit": self._INTERACTION_LIMIT,
            "interaction_color": _color(interaction_count, self._INTERACTION_LIMIT),
            "elapsed_minutes": round(elapsed, 1),
            "time_limit": self._TIME_LIMIT_MINUTES,
            "time_color": _color(elapsed, self._TIME_LIMIT_MINUTES),
            "compaction_count": compaction_count,
        }

    def get_drift_data(self) -> Dict[str, Any]:
        """
        Drift indicator: compares planned files vs actual files touched.

        Returns drift percentage. 0% = perfect alignment.
        """
        files_planned = set()
        for task in self._plan_tasks:
            if task.get("file"):
                files_planned.add(task["file"])

        files_actual = set(self._progress.get("files_actual", []))

        if not files_planned and not files_actual:
            return {
                "drift_pct": 0.0,
                "files_planned": [],
                "files_actual": [],
                "files_unplanned": [],
                "files_missed": [],
            }

        all_files = files_planned | files_actual
        diff_files = files_planned.symmetric_difference(files_actual)
        drift_pct = (len(diff_files) / len(all_files) * 100) if all_files else 0.0

        return {
            "drift_pct": round(drift_pct, 1),
            "files_planned": sorted(files_planned),
            "files_actual": sorted(files_actual),
            "files_unplanned": sorted(files_actual - files_planned),
            "files_missed": sorted(files_planned - files_actual),
        }

    def get_affected_files(self) -> List[Dict[str, Any]]:
        """
        Affected files preview: exists, last modified, line count.

        Spots stale assumptions like targeting deleted files.
        """
        files = []
        seen = set()

        for task in self._plan_tasks:
            file_path = task.get("file", "")
            if not file_path or file_path in seen:
                continue
            seen.add(file_path)

            full_path = self.project_root / file_path
            if full_path.exists():
                try:
                    stat = full_path.stat()
                    line_count = full_path.read_text().count("\n")
                    modified = datetime.fromtimestamp(stat.st_mtime)
                    files.append({
                        "path": file_path,
                        "exists": True,
                        "modified": modified.isoformat(),
                        "lines": line_count,
                    })
                except OSError:
                    files.append({
                        "path": file_path,
                        "exists": False,
                        "modified": None,
                        "lines": 0,
                    })
            else:
                files.append({
                    "path": file_path,
                    "exists": False,
                    "modified": None,
                    "lines": 0,
                })

        return files

    def get_execution_data(self) -> Dict[str, Any]:
        """
        Aggregate all execution monitor data into a single dict.

        Graceful: returns safe defaults when no progress data exists.
        """
        task_progress = self.get_task_progress()

        return {
            "phase": self._progress.get("phase", 0),
            "phase_name": self._progress.get("name", ""),
            "step": self._progress.get("step", 0),
            "step_label": self._progress.get("step_label", ""),
            "status": self._progress.get("status", "unknown"),
            "tasks": task_progress["tasks"],
            "tasks_done": task_progress["tasks_done"],
            "tasks_total": task_progress["tasks_total"],
            "consecutive_failures": task_progress["consecutive_failures"],
            "current_task": task_progress["current_task"],
            "session_metrics": self.get_session_metrics(),
            "drift": self.get_drift_data(),
            "affected_files": self.get_affected_files(),
            "commits": self._progress.get("commits", 0),
            "errors": self._progress.get("errors", []),
            "warnings": self._progress.get("warnings", []),
        }
