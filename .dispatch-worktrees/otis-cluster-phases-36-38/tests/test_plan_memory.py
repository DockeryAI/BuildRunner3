"""Tests for Phase 2: Plan Memory (Lockwood)"""

import json
import os
import tempfile
import pytest
from unittest.mock import patch


@pytest.fixture
def temp_db():
    """Create a temp SQLite database for testing."""
    fd, path = tempfile.mkstemp(suffix=".db")
    os.close(fd)
    with patch.dict(os.environ, {"MEMORY_DB": path}):
        yield path
    os.unlink(path)


class TestPlanOutcomesTable:
    """T1: plan_outcomes table exists with correct schema."""

    def test_table_created(self, temp_db):
        from core.cluster.memory_store import _get_db
        conn = _get_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='plan_outcomes'"
        )
        assert cursor.fetchone() is not None, "plan_outcomes table should exist"
        conn.close()

    def test_table_columns(self, temp_db):
        from core.cluster.memory_store import _get_db
        conn = _get_db()
        cursor = conn.execute("PRAGMA table_info(plan_outcomes)")
        columns = {row[1] for row in cursor.fetchall()}
        expected = {
            "plan_id", "project", "build_name", "phase", "plan_text",
            "outcome", "accuracy_pct", "drift_notes", "files_planned",
            "files_actual", "duration_seconds", "timestamp"
        }
        assert expected.issubset(columns), f"Missing columns: {expected - columns}"
        conn.close()

    def test_index_exists(self, temp_db):
        from core.cluster.memory_store import _get_db
        conn = _get_db()
        cursor = conn.execute(
            "SELECT name FROM sqlite_master WHERE type='index' AND name='idx_plans_project'"
        )
        assert cursor.fetchone() is not None, "idx_plans_project index should exist"
        conn.close()


class TestRecordPlanOutcome:
    """T2: record_plan_outcome() stores plan data."""

    def test_record_and_retrieve(self, temp_db):
        from core.cluster.memory_store import record_plan_outcome, get_recent_plan_outcomes
        record_plan_outcome(
            project="synapse",
            build_name="BUILD_auth",
            phase="Phase 3",
            plan_text="Add JWT middleware to auth service",
            outcome="pass",
            accuracy_pct=95.0,
            drift_notes="None",
            files_planned=["src/auth/middleware.ts"],
            files_actual=["src/auth/middleware.ts", "src/auth/types.ts"],
            duration_seconds=120.5,
        )
        results = get_recent_plan_outcomes("synapse")
        assert len(results) >= 1
        r = results[0]
        assert r["project"] == "synapse"
        assert r["outcome"] == "pass"
        assert r["accuracy_pct"] == 95.0
        assert json.loads(r["files_planned"]) == ["src/auth/middleware.ts"]


class TestGetRecentPlanOutcomes:
    """T3: get_recent_plan_outcomes() filters by project."""

    def test_filters_by_project(self, temp_db):
        from core.cluster.memory_store import record_plan_outcome, get_recent_plan_outcomes
        record_plan_outcome("projA", "BUILD_a", "P1", "plan A", "pass")
        record_plan_outcome("projB", "BUILD_b", "P1", "plan B", "fail")
        record_plan_outcome("projA", "BUILD_a", "P2", "plan A2", "partial")

        results_a = get_recent_plan_outcomes("projA")
        assert len(results_a) == 2
        assert all(r["project"] == "projA" for r in results_a)

    def test_limit(self, temp_db):
        from core.cluster.memory_store import record_plan_outcome, get_recent_plan_outcomes
        for i in range(5):
            record_plan_outcome("proj", "BUILD", f"P{i}", f"plan {i}", "pass")
        results = get_recent_plan_outcomes("proj", limit=3)
        assert len(results) == 3

    def test_ordered_by_timestamp_desc(self, temp_db):
        from core.cluster.memory_store import record_plan_outcome, get_recent_plan_outcomes
        record_plan_outcome("proj", "BUILD", "P1", "first", "pass")
        record_plan_outcome("proj", "BUILD", "P2", "second", "fail")
        results = get_recent_plan_outcomes("proj")
        assert results[0]["phase"] == "P2"  # most recent first
