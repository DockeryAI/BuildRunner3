"""
Tests for ExecutionMonitorView — Phase 7 Dashboard Execution Monitor.

Validates task progress, session metrics, drift detection,
affected files preview, and aggregated execution data.
"""

import json
import os
import pytest
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from core.dashboard_views import ExecutionMonitorView


@pytest.fixture
def tmp_project(tmp_path):
    """Create a temporary project structure with plan + progress files."""
    plans_dir = tmp_path / ".buildrunner" / "plans"
    plans_dir.mkdir(parents=True)
    locks_dir = tmp_path / ".buildrunner" / "locks" / "phase-3"
    locks_dir.mkdir(parents=True)

    # Write a plan file
    plan = plans_dir / "phase-3-plan.md"
    plan.write_text(
        "# Phase 3 Plan\n\n"
        "### 3.1 Add auth middleware\n"
        "- WHAT: Add auth check to `src/middleware/auth.ts`\n"
        "- WHY: Security requirement\n"
        "- VERIFY: test_auth_middleware passes\n\n"
        "### 3.2 Add rate limiter\n"
        "- WHAT: Rate limit in `src/middleware/rate.ts`\n"
        "- WHY: Prevent abuse\n"
        "- VERIFY: test_rate_limiter passes\n\n"
        "### 3.3 Add logging\n"
        "- WHAT: Request logging in `src/middleware/logger.ts`\n"
        "- WHY: Observability\n"
        "- VERIFY: test_logger passes\n"
    )

    # Write progress.json
    progress = {
        "phase": 3,
        "name": "Middleware",
        "step": 4,
        "step_name": "execute",
        "step_label": "Implementing tasks",
        "status": "active",
        "tasks_total": 3,
        "tasks_done": 1,
        "current_task": "3.2 — Add rate limiter",
        "tests_written": 3,
        "tests_passing": 1,
        "commits": 2,
        "errors": [],
        "warnings": [],
        "started_at": "2026-04-06T10:00:00Z",
        "updated_at": "2026-04-06T10:15:00Z",
        "history": [
            {"step": 1, "name": "setup", "label": "Setup & sync", "at": "2026-04-06T10:00:00Z", "status": "done"},
        ],
        "verify_results": [
            {"task_id": "3.1", "result": "pass"},
        ],
        "consecutive_failures": 0,
        "interaction_count": 25,
        "compaction_count": 0,
        "files_actual": ["src/middleware/auth.ts"],
    }
    (locks_dir / "progress.json").write_text(json.dumps(progress))

    # Create some source files for affected files preview
    src_dir = tmp_path / "src" / "middleware"
    src_dir.mkdir(parents=True)
    (src_dir / "auth.ts").write_text("export function auth() { return true; }\n" * 10)

    return tmp_path


@pytest.fixture
def monitor(tmp_project):
    """Create an ExecutionMonitorView for the tmp project."""
    return ExecutionMonitorView(tmp_project)


class TestExecutionMonitorViewInit:
    def test_instantiation(self, monitor):
        assert monitor is not None
        assert monitor.project_root is not None

    def test_finds_progress_json(self, monitor):
        data = monitor.get_execution_data()
        assert data is not None
        assert isinstance(data, dict)

    def test_no_progress_file(self, tmp_path):
        """Graceful when no progress.json exists."""
        (tmp_path / ".buildrunner" / "plans").mkdir(parents=True)
        mon = ExecutionMonitorView(tmp_path)
        data = mon.get_execution_data()
        assert data["tasks"] == []
        assert data["session_metrics"]["interaction_count"] == 0


class TestTaskProgress:
    def test_returns_task_list(self, monitor):
        progress = monitor.get_task_progress()
        assert isinstance(progress, dict)
        assert "tasks" in progress
        assert "tasks_done" in progress
        assert "tasks_total" in progress

    def test_task_count(self, monitor):
        progress = monitor.get_task_progress()
        assert progress["tasks_total"] == 3
        assert progress["tasks_done"] == 1

    def test_verify_results(self, monitor):
        progress = monitor.get_task_progress()
        # Task 3.1 should show pass
        task_3_1 = next((t for t in progress["tasks"] if t["id"] == "3.1"), None)
        assert task_3_1 is not None
        assert task_3_1["verify_result"] == "pass"

    def test_consecutive_failures(self, monitor):
        progress = monitor.get_task_progress()
        assert progress["consecutive_failures"] == 0

    def test_current_task(self, monitor):
        progress = monitor.get_task_progress()
        assert progress["current_task"] == "3.2 — Add rate limiter"


class TestSessionMetrics:
    def test_returns_metrics(self, monitor):
        metrics = monitor.get_session_metrics()
        assert "interaction_count" in metrics
        assert "interaction_limit" in metrics
        assert "elapsed_minutes" in metrics
        assert "time_limit" in metrics
        assert "compaction_count" in metrics

    def test_interaction_count(self, monitor):
        metrics = monitor.get_session_metrics()
        assert metrics["interaction_count"] == 25
        assert metrics["interaction_limit"] == 70

    def test_color_thresholds(self, monitor):
        metrics = monitor.get_session_metrics()
        # 25/70 = ~36% — should be "normal"
        assert metrics["interaction_color"] == "normal"

    def test_yellow_at_80_percent(self, tmp_project):
        """Color turns yellow at 80% of limit."""
        locks_dir = tmp_project / ".buildrunner" / "locks" / "phase-3"
        progress = json.loads((locks_dir / "progress.json").read_text())
        progress["interaction_count"] = 57  # 57/70 = 81%
        (locks_dir / "progress.json").write_text(json.dumps(progress))

        mon = ExecutionMonitorView(tmp_project)
        metrics = mon.get_session_metrics()
        assert metrics["interaction_color"] == "yellow"

    def test_red_at_100_percent(self, tmp_project):
        """Color turns red at 100% of limit."""
        locks_dir = tmp_project / ".buildrunner" / "locks" / "phase-3"
        progress = json.loads((locks_dir / "progress.json").read_text())
        progress["interaction_count"] = 70
        (locks_dir / "progress.json").write_text(json.dumps(progress))

        mon = ExecutionMonitorView(tmp_project)
        metrics = mon.get_session_metrics()
        assert metrics["interaction_color"] == "red"


class TestDriftIndicator:
    def test_returns_drift_data(self, monitor):
        drift = monitor.get_drift_data()
        assert "drift_pct" in drift
        assert "files_planned" in drift
        assert "files_actual" in drift

    def test_drift_percentage(self, monitor):
        drift = monitor.get_drift_data()
        # Plan has 3 files, only 1 actual — some drift expected
        assert isinstance(drift["drift_pct"], float)

    def test_zero_drift_when_matching(self, tmp_project):
        """0% drift when actual matches planned."""
        locks_dir = tmp_project / ".buildrunner" / "locks" / "phase-3"
        progress = json.loads((locks_dir / "progress.json").read_text())
        progress["files_actual"] = [
            "src/middleware/auth.ts",
            "src/middleware/rate.ts",
            "src/middleware/logger.ts",
        ]
        (locks_dir / "progress.json").write_text(json.dumps(progress))

        mon = ExecutionMonitorView(tmp_project)
        drift = mon.get_drift_data()
        assert drift["drift_pct"] == 0.0


class TestAffectedFiles:
    def test_returns_file_info(self, monitor):
        files = monitor.get_affected_files()
        assert isinstance(files, list)

    def test_existing_file_info(self, monitor):
        files = monitor.get_affected_files()
        auth_file = next((f for f in files if "auth.ts" in f["path"]), None)
        assert auth_file is not None
        assert auth_file["exists"] is True
        assert auth_file["lines"] > 0

    def test_missing_file_info(self, monitor):
        files = monitor.get_affected_files()
        rate_file = next((f for f in files if "rate.ts" in f["path"]), None)
        assert rate_file is not None
        assert rate_file["exists"] is False


class TestGetExecutionData:
    def test_aggregated_data(self, monitor):
        data = monitor.get_execution_data()
        assert "tasks" in data
        assert "session_metrics" in data
        assert "drift" in data
        assert "affected_files" in data
        assert "phase" in data

    def test_phase_info(self, monitor):
        data = monitor.get_execution_data()
        assert data["phase"] == 3
        assert data["phase_name"] == "Middleware"
