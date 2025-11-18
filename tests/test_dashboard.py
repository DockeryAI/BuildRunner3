"""
Tests for BuildRunner 3.0 Dashboard

Comprehensive test coverage for multi-repo dashboard functionality.
"""

import json
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import Mock, patch, mock_open, MagicMock

from core.dashboard_views import (
    ProjectStatus,
    DashboardScanner,
    DashboardViews
)


# Fixtures

@pytest.fixture
def sample_features_data():
    """Sample features.json data"""
    return {
        "project": "TestProject",
        "version": "1.0.0",
        "status": "active",
        "last_updated": "2024-01-15T10:00:00Z",
        "features": [
            {"id": "f1", "name": "Feature 1", "status": "complete"},
            {"id": "f2", "name": "Feature 2", "status": "in_progress"},
            {"id": "f3", "name": "Feature 3", "status": "planned"}
        ],
        "metrics": {
            "completion_percentage": 33.3
        }
    }


@pytest.fixture
def mock_project():
    """Create a mock ProjectStatus"""
    return ProjectStatus(
        name="TestProject",
        path=Path("/test/project"),
        version="1.0.0",
        status="active",
        total_features=3,
        completed=1,
        in_progress=1,
        planned=1,
        completion_percentage=33.3,
        last_updated=datetime.now() - timedelta(days=2),
        blockers=[],
        active_features=["Feature 2"]
    )


@pytest.fixture
def mock_stale_project():
    """Create a stale project (>7 days)"""
    return ProjectStatus(
        name="StaleProject",
        path=Path("/test/stale"),
        version="0.5.0",
        status="stale",
        total_features=5,
        completed=2,
        in_progress=0,
        planned=3,
        completion_percentage=40.0,
        last_updated=datetime.now() - timedelta(days=10),
        blockers=[],
        active_features=[]
    )


@pytest.fixture
def mock_blocked_project():
    """Create a blocked project"""
    return ProjectStatus(
        name="BlockedProject",
        path=Path("/test/blocked"),
        version="2.0.0",
        status="blocked",
        total_features=10,
        completed=7,
        in_progress=2,
        planned=1,
        completion_percentage=70.0,
        last_updated=datetime.now() - timedelta(days=1),
        blockers=["Missing dependency", "Build failure"],
        active_features=["Feature X", "Feature Y"]
    )


# ProjectStatus Tests

class TestProjectStatus:
    """Test ProjectStatus dataclass properties"""

    def test_is_stale_false(self, mock_project):
        """Project updated <7 days ago is not stale"""
        assert not mock_project.is_stale

    def test_is_stale_true(self, mock_stale_project):
        """Project updated >7 days ago is stale"""
        assert mock_stale_project.is_stale

    def test_health_status_healthy(self):
        """Project with no blockers and good progress is healthy"""
        project = ProjectStatus(
            name="Healthy",
            path=Path("/test"),
            version="1.0.0",
            status="active",
            total_features=10,
            completed=8,
            in_progress=2,
            planned=0,
            completion_percentage=80.0,
            last_updated=datetime.now(),
            blockers=[],
            active_features=[]
        )
        assert project.health_status == "healthy"

    def test_health_status_warning_stale(self, mock_stale_project):
        """Stale project has warning status"""
        assert mock_stale_project.health_status == "warning"

    def test_health_status_warning_high_wip(self):
        """Project with more WIP than completed has warning status"""
        project = ProjectStatus(
            name="HighWIP",
            path=Path("/test"),
            version="1.0.0",
            status="active",
            total_features=10,
            completed=2,
            in_progress=5,
            planned=3,
            completion_percentage=20.0,
            last_updated=datetime.now(),
            blockers=[],
            active_features=[]
        )
        assert project.health_status == "warning"

    def test_health_status_critical_blocked(self, mock_blocked_project):
        """Project with blockers is critical"""
        assert mock_blocked_project.health_status == "critical"


# DashboardScanner Tests

class TestDashboardScanner:
    """Test DashboardScanner filesystem discovery"""

    def test_init_default_path(self):
        """Scanner initializes with current directory by default"""
        scanner = DashboardScanner()
        assert scanner.root_path == Path.cwd()

    def test_init_custom_path(self):
        """Scanner initializes with custom path"""
        scanner = DashboardScanner(Path("/custom/path"))
        assert scanner.root_path == Path("/custom/path")

    @patch('core.dashboard_views.Path.iterdir')
    def test_find_features_files_single(self, mock_iterdir):
        """Find single features.json file"""
        # Setup mock directory structure
        buildrunner_dir = MagicMock()
        buildrunner_dir.name = ".buildrunner"
        buildrunner_dir.is_dir.return_value = True

        features_file = MagicMock()
        features_file.exists.return_value = True
        buildrunner_dir.__truediv__.return_value = features_file

        mock_iterdir.return_value = [buildrunner_dir]

        scanner = DashboardScanner(Path("/test"))
        files = scanner._find_features_files(max_depth=5)

        assert len(files) == 1

    @patch('core.dashboard_views.Path.iterdir')
    def test_find_features_files_excludes_common_dirs(self, mock_iterdir):
        """Excludes .git, node_modules, etc."""
        # Setup mock directory structure with excluded dirs
        git_dir = MagicMock()
        git_dir.name = ".git"
        git_dir.is_dir.return_value = True

        node_modules = MagicMock()
        node_modules.name = "node_modules"
        node_modules.is_dir.return_value = True

        mock_iterdir.return_value = [git_dir, node_modules]

        scanner = DashboardScanner(Path("/test"))
        files = scanner._find_features_files(max_depth=5)

        # Should not find any files in excluded directories
        assert len(files) == 0

    def test_parse_project_valid(self, sample_features_data, tmp_path):
        """Parse valid features.json file"""
        # Create temp features.json
        project_dir = tmp_path / "project"
        buildrunner_dir = project_dir / ".buildrunner"
        buildrunner_dir.mkdir(parents=True)

        features_file = buildrunner_dir / "features.json"
        features_file.write_text(json.dumps(sample_features_data))

        scanner = DashboardScanner()
        project = scanner._parse_project(features_file)

        assert project is not None
        assert project.name == "TestProject"
        assert project.version == "1.0.0"
        assert project.total_features == 3
        assert project.completed == 1
        assert project.in_progress == 1
        assert project.planned == 1
        assert project.completion_percentage == 33.3

    def test_parse_project_invalid_json(self, tmp_path):
        """Handle invalid JSON gracefully"""
        features_file = tmp_path / "features.json"
        features_file.write_text("invalid json {")

        scanner = DashboardScanner()
        project = scanner._parse_project(features_file)

        assert project is None

    def test_parse_project_missing_fields(self, tmp_path):
        """Handle missing fields with defaults"""
        minimal_data = {
            "features": [
                {"status": "complete"},
                {"status": "planned"}
            ]
        }

        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps(minimal_data))

        scanner = DashboardScanner()
        project = scanner._parse_project(features_file)

        assert project is not None
        assert project.name == "Unknown"
        assert project.version == "0.0.0"
        assert project.status == "unknown"
        assert project.total_features == 2

    def test_parse_project_calculates_completion(self, tmp_path):
        """Calculate completion percentage when not in metrics"""
        data = {
            "project": "Test",
            "features": [
                {"status": "complete"},
                {"status": "complete"},
                {"status": "planned"}
            ],
            "metrics": {}
        }

        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps(data))

        scanner = DashboardScanner()
        project = scanner._parse_project(features_file)

        assert project.completion_percentage == 66.7  # 2/3

    def test_parse_project_active_features(self, tmp_path):
        """Extract active features list"""
        data = {
            "project": "Test",
            "features": [
                {"name": "Feature 1", "status": "in_progress"},
                {"name": "Feature 2", "status": "in_progress"},
                {"name": "Feature 3", "status": "complete"}
            ]
        }

        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps(data))

        scanner = DashboardScanner()
        project = scanner._parse_project(features_file)

        assert len(project.active_features) == 2
        assert "Feature 1" in project.active_features
        assert "Feature 2" in project.active_features

    def test_parse_project_limits_active_features(self, tmp_path):
        """Limit active features to 5"""
        data = {
            "project": "Test",
            "features": [
                {"name": f"Feature {i}", "status": "in_progress"}
                for i in range(10)
            ]
        }

        features_file = tmp_path / "features.json"
        features_file.write_text(json.dumps(data))

        scanner = DashboardScanner()
        project = scanner._parse_project(features_file)

        assert len(project.active_features) == 5


# DashboardViews Tests

class TestDashboardViews:
    """Test DashboardViews aggregation and filtering"""

    def test_get_overview_data(self, mock_project, mock_stale_project, mock_blocked_project):
        """Aggregate overview data across all projects"""
        projects = [mock_project, mock_stale_project, mock_blocked_project]
        views = DashboardViews(projects)

        overview = views.get_overview_data()

        assert overview['total_projects'] == 3
        assert overview['total_features'] == 18  # 3 + 5 + 10
        assert overview['total_completed'] == 10  # 1 + 2 + 7
        assert overview['total_in_progress'] == 3  # 1 + 0 + 2
        assert overview['total_planned'] == 5  # 1 + 3 + 1
        assert overview['overall_completion'] == 55.6  # 10/18 * 100
        assert overview['stale_projects'] == 1
        assert overview['blocked_projects'] == 1
        assert overview['active_projects'] == 2  # Projects with in_progress > 0
        assert len(overview['projects']) == 3

    def test_get_overview_data_empty(self):
        """Handle empty project list"""
        views = DashboardViews([])
        overview = views.get_overview_data()

        assert overview['total_projects'] == 0
        assert overview['total_features'] == 0
        assert overview['overall_completion'] == 0

    def test_get_detail_data_found(self, mock_project):
        """Get detail data for existing project"""
        views = DashboardViews([mock_project])
        detail = views.get_detail_data("TestProject")

        assert detail is not None
        assert detail['project'].name == "TestProject"
        assert detail['features_by_status']['completed'] == 1
        assert detail['features_by_status']['in_progress'] == 1
        assert detail['features_by_status']['planned'] == 1
        assert detail['health'] == "healthy"
        assert detail['days_since_update'] == 2

    def test_get_detail_data_not_found(self, mock_project):
        """Return None for non-existent project"""
        views = DashboardViews([mock_project])
        detail = views.get_detail_data("NonExistent")

        assert detail is None

    def test_get_timeline_data(self, mock_project, mock_stale_project):
        """Get timeline of recent activity"""
        views = DashboardViews([mock_project, mock_stale_project])
        timeline = views.get_timeline_data(days=30)

        # Both projects updated within 30 days (10 and 2 days ago)
        assert len(timeline) == 2

        # Should be sorted by timestamp descending (most recent first)
        assert timeline[0]['project'] == "TestProject"  # 2 days ago
        assert timeline[1]['project'] == "StaleProject"  # 10 days ago

        # Check structure
        assert 'timestamp' in timeline[0]
        assert 'event' in timeline[0]
        assert 'completion' in timeline[0]

    def test_get_timeline_data_filtered_by_days(self):
        """Filter timeline by date range"""
        old_project = ProjectStatus(
            name="OldProject",
            path=Path("/test"),
            version="1.0.0",
            status="active",
            total_features=5,
            completed=5,
            in_progress=0,
            planned=0,
            completion_percentage=100.0,
            last_updated=datetime.now() - timedelta(days=60),
            blockers=[],
            active_features=[]
        )

        recent_project = ProjectStatus(
            name="RecentProject",
            path=Path("/test"),
            version="1.0.0",
            status="active",
            total_features=3,
            completed=1,
            in_progress=2,
            planned=0,
            completion_percentage=33.3,
            last_updated=datetime.now() - timedelta(days=5),
            blockers=[],
            active_features=[]
        )

        views = DashboardViews([old_project, recent_project])
        timeline = views.get_timeline_data(days=30)

        # Should only include recent project
        assert len(timeline) == 1
        assert timeline[0]['project'] == "RecentProject"

    def test_get_alerts_data(self, mock_project, mock_stale_project, mock_blocked_project):
        """Get all alert categories"""
        # Add a no-progress project
        no_progress = ProjectStatus(
            name="NoProgress",
            path=Path("/test"),
            version="1.0.0",
            status="planned",
            total_features=5,
            completed=0,
            in_progress=0,
            planned=5,
            completion_percentage=0.0,
            last_updated=datetime.now(),
            blockers=[],
            active_features=[]
        )

        # Add high WIP project
        high_wip = ProjectStatus(
            name="HighWIP",
            path=Path("/test"),
            version="1.0.0",
            status="active",
            total_features=20,
            completed=5,
            in_progress=8,
            planned=7,
            completion_percentage=25.0,
            last_updated=datetime.now(),
            blockers=[],
            active_features=[]
        )

        projects = [mock_project, mock_stale_project, mock_blocked_project, no_progress, high_wip]
        views = DashboardViews(projects)

        alerts = views.get_alerts_data()

        # Check alert categories
        assert len(alerts['stale']) == 1
        assert alerts['stale'][0].name == "StaleProject"

        assert len(alerts['blocked']) == 1
        assert alerts['blocked'][0].name == "BlockedProject"

        # Both StaleProject and NoProgress have 0 in_progress but have planned features
        assert len(alerts['no_progress']) == 2
        no_progress_names = [p.name for p in alerts['no_progress']]
        assert "StaleProject" in no_progress_names
        assert "NoProgress" in no_progress_names

        assert len(alerts['high_wip']) == 1
        assert alerts['high_wip'][0].name == "HighWIP"

    def test_get_alerts_data_no_alerts(self, mock_project):
        """Return empty lists when no alerts"""
        views = DashboardViews([mock_project])
        alerts = views.get_alerts_data()

        assert len(alerts['stale']) == 0
        assert len(alerts['blocked']) == 0
        assert len(alerts['no_progress']) == 0
        assert len(alerts['high_wip']) == 0

    def test_get_summary_stats(self, mock_project, mock_stale_project):
        """Generate text summary"""
        views = DashboardViews([mock_project, mock_stale_project])
        summary = views.get_summary_stats()

        assert "📊 Multi-Repo Dashboard Summary" in summary
        assert "Projects: 2" in summary
        assert "3/8 complete" in summary  # 3 completed, 8 total features
        assert "Active: 1" in summary  # 1 project with in_progress > 0
        assert "1 stale" in summary
        assert "0 blocked" in summary


# Integration Tests

class TestDashboardIntegration:
    """End-to-end integration tests"""

    def test_full_scan_and_aggregate(self, tmp_path):
        """Full workflow: scan filesystem, parse projects, generate views"""
        # Create mock project structure
        project1_dir = tmp_path / "project1" / ".buildrunner"
        project1_dir.mkdir(parents=True)

        project1_data = {
            "project": "Project1",
            "version": "1.0.0",
            "status": "active",
            "features": [
                {"status": "complete"},
                {"status": "complete"},
                {"status": "in_progress"}
            ],
            "metrics": {"completion_percentage": 66.7}
        }
        (project1_dir / "features.json").write_text(json.dumps(project1_data))

        project2_dir = tmp_path / "project2" / ".buildrunner"
        project2_dir.mkdir(parents=True)

        project2_data = {
            "project": "Project2",
            "version": "2.0.0",
            "status": "active",
            "features": [
                {"status": "planned"},
                {"status": "planned"}
            ]
        }
        (project2_dir / "features.json").write_text(json.dumps(project2_data))

        # Scan and discover
        scanner = DashboardScanner(tmp_path)
        projects = scanner.discover_projects()

        assert len(projects) == 2

        # Generate views
        views = DashboardViews(projects)
        overview = views.get_overview_data()

        assert overview['total_projects'] == 2
        assert overview['total_features'] == 5
        assert overview['total_completed'] == 2
        assert overview['active_projects'] == 1

    def test_empty_directory(self, tmp_path):
        """Handle directory with no BuildRunner projects"""
        scanner = DashboardScanner(tmp_path)
        projects = scanner.discover_projects()

        assert len(projects) == 0

        views = DashboardViews(projects)
        overview = views.get_overview_data()

        assert overview['total_projects'] == 0
