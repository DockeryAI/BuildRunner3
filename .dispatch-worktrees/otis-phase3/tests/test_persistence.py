"""
Tests for BuildRunner persistence layer (Database and models)
"""

import pytest
from pathlib import Path
from datetime import datetime, UTC
import tempfile
import os

from core.persistence.database import Database
from core.persistence.models import CostEntry, MetricEntry


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test.db"
        db = Database(db_path)
        yield db
        db.close()


@pytest.fixture
def initialized_db(temp_db):
    """Create database with cost_entries table."""
    migration_sql = """
    CREATE TABLE cost_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        timestamp TEXT NOT NULL,
        task_id TEXT,
        model_name TEXT NOT NULL,
        input_tokens INTEGER NOT NULL,
        output_tokens INTEGER NOT NULL,
        cost_usd REAL NOT NULL,
        session_id TEXT
    );

    CREATE INDEX idx_cost_timestamp ON cost_entries(timestamp);
    CREATE INDEX idx_cost_task_id ON cost_entries(task_id);
    CREATE INDEX idx_cost_session_id ON cost_entries(session_id);
    """
    temp_db.run_migration(migration_sql)
    return temp_db


class TestDatabase:
    """Test Database class functionality."""

    def test_database_initialization(self, temp_db):
        """Test database can be initialized."""
        assert temp_db.db_path.exists()
        assert temp_db.conn is not None

    def test_table_exists(self, initialized_db):
        """Test table_exists method."""
        assert initialized_db.table_exists("cost_entries")
        assert not initialized_db.table_exists("nonexistent_table")

    def test_insert_and_query(self, initialized_db):
        """Test inserting and querying data."""
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": "test-task-1",
            "model_name": "claude-sonnet-4",
            "input_tokens": 1000,
            "output_tokens": 500,
            "cost_usd": 0.015,
            "session_id": "session-123",
        }

        # Insert
        row_id = initialized_db.insert("cost_entries", data)
        assert row_id > 0

        # Query
        results = initialized_db.query("SELECT * FROM cost_entries WHERE id = ?", (row_id,))
        assert len(results) == 1
        assert results[0]["model_name"] == "claude-sonnet-4"
        assert results[0]["input_tokens"] == 1000

    def test_query_one(self, initialized_db):
        """Test query_one method."""
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": "test-task-2",
            "model_name": "claude-opus-4",
            "input_tokens": 2000,
            "output_tokens": 1000,
            "cost_usd": 0.045,
            "session_id": "session-456",
        }

        row_id = initialized_db.insert("cost_entries", data)

        # Query single row
        result = initialized_db.query_one("SELECT * FROM cost_entries WHERE id = ?", (row_id,))
        assert result is not None
        assert result["model_name"] == "claude-opus-4"

        # Query non-existent row
        result = initialized_db.query_one("SELECT * FROM cost_entries WHERE id = ?", (99999,))
        assert result is None

    def test_update(self, initialized_db):
        """Test updating data."""
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": "test-task-3",
            "model_name": "claude-haiku-4",
            "input_tokens": 500,
            "output_tokens": 250,
            "cost_usd": 0.003,
            "session_id": "session-789",
        }

        row_id = initialized_db.insert("cost_entries", data)

        # Update
        update_data = {"cost_usd": 0.005}
        rows_updated = initialized_db.update("cost_entries", update_data, "id = ?", (row_id,))
        assert rows_updated == 1

        # Verify update
        result = initialized_db.query_one("SELECT * FROM cost_entries WHERE id = ?", (row_id,))
        assert result["cost_usd"] == 0.005

    def test_delete(self, initialized_db):
        """Test deleting data."""
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": "test-task-4",
            "model_name": "claude-sonnet-4",
            "input_tokens": 1500,
            "output_tokens": 750,
            "cost_usd": 0.022,
            "session_id": "session-abc",
        }

        row_id = initialized_db.insert("cost_entries", data)

        # Delete
        rows_deleted = initialized_db.delete("cost_entries", "id = ?", (row_id,))
        assert rows_deleted == 1

        # Verify deletion
        result = initialized_db.query_one("SELECT * FROM cost_entries WHERE id = ?", (row_id,))
        assert result is None

    def test_transaction_commit(self, initialized_db):
        """Test transaction commits on success."""
        with initialized_db.transaction():
            initialized_db.cursor.execute(
                "INSERT INTO cost_entries (timestamp, task_id, model_name, input_tokens, output_tokens, cost_usd) VALUES (?, ?, ?, ?, ?, ?)",
                (datetime.now(UTC).isoformat(), "task-5", "claude-sonnet-4", 1000, 500, 0.015),
            )

        # Verify data was committed
        results = initialized_db.query("SELECT * FROM cost_entries WHERE task_id = 'task-5'")
        assert len(results) == 1

    def test_transaction_rollback(self, initialized_db):
        """Test transaction rolls back on error."""
        try:
            with initialized_db.transaction():
                initialized_db.cursor.execute(
                    "INSERT INTO cost_entries (timestamp, task_id, model_name, input_tokens, output_tokens, cost_usd) VALUES (?, ?, ?, ?, ?, ?)",
                    (datetime.now(UTC).isoformat(), "task-6", "claude-sonnet-4", 1000, 500, 0.015),
                )
                # Trigger error
                raise ValueError("Test error")
        except ValueError:
            pass

        # Verify data was NOT committed
        results = initialized_db.query("SELECT * FROM cost_entries WHERE task_id = 'task-6'")
        assert len(results) == 0


class TestCostEntry:
    """Test CostEntry model."""

    def test_cost_entry_create(self):
        """Test CostEntry.create() static method."""
        entry = CostEntry.create(
            model_name="claude-sonnet-4",
            input_tokens=1000,
            output_tokens=500,
            cost_usd=0.015,
            task_id="test-task",
            session_id="session-123",
        )

        assert entry.model_name == "claude-sonnet-4"
        assert entry.input_tokens == 1000
        assert entry.output_tokens == 500
        assert entry.cost_usd == 0.015
        assert entry.task_id == "test-task"
        assert entry.session_id == "session-123"
        assert entry.timestamp is not None
        assert entry.id is None

    def test_cost_entry_to_dict(self):
        """Test CostEntry.to_dict() method."""
        entry = CostEntry.create(
            model_name="claude-opus-4", input_tokens=2000, output_tokens=1000, cost_usd=0.045
        )

        data = entry.to_dict()
        assert data["model_name"] == "claude-opus-4"
        assert data["input_tokens"] == 2000
        assert data["output_tokens"] == 1000
        assert data["cost_usd"] == 0.045
        assert "id" not in data  # Should be removed if None
        assert "timestamp" in data

    def test_cost_entry_from_dict(self):
        """Test CostEntry.from_dict() method."""
        data = {
            "timestamp": datetime.now(UTC).isoformat(),
            "task_id": "test-task",
            "model_name": "claude-haiku-4",
            "input_tokens": 500,
            "output_tokens": 250,
            "cost_usd": 0.003,
            "session_id": "session-456",
            "id": 123,
        }

        entry = CostEntry.from_dict(data)
        assert entry.model_name == "claude-haiku-4"
        assert entry.input_tokens == 500
        assert entry.id == 123


class TestMetricEntry:
    """Test MetricEntry model."""

    def test_metric_entry_creation(self):
        """Test MetricEntry creation."""
        entry = MetricEntry(
            timestamp=datetime.now(UTC).isoformat(),
            period_type="hourly",
            total_tasks=100,
            successful_tasks=95,
            failed_tasks=5,
            total_cost_usd=1.50,
            total_tokens=50000,
            avg_duration_ms=250.5,
        )

        assert entry.period_type == "hourly"
        assert entry.total_tasks == 100
        assert entry.successful_tasks == 95
        assert entry.failed_tasks == 5

    def test_metric_entry_success_rate(self):
        """Test MetricEntry.success_rate property."""
        entry = MetricEntry(
            timestamp=datetime.now(UTC).isoformat(),
            period_type="daily",
            total_tasks=200,
            successful_tasks=180,
            failed_tasks=20,
            total_cost_usd=3.00,
            total_tokens=100000,
            avg_duration_ms=300.0,
        )

        assert entry.success_rate == 0.9  # 180/200

    def test_metric_entry_avg_cost_per_task(self):
        """Test MetricEntry.avg_cost_per_task property."""
        entry = MetricEntry(
            timestamp=datetime.now(UTC).isoformat(),
            period_type="weekly",
            total_tasks=1000,
            successful_tasks=950,
            failed_tasks=50,
            total_cost_usd=15.00,
            total_tokens=500000,
            avg_duration_ms=275.0,
        )

        assert entry.avg_cost_per_task == 0.015  # 15.00/1000

    def test_metric_entry_to_dict(self):
        """Test MetricEntry.to_dict() method."""
        entry = MetricEntry(
            timestamp=datetime.now(UTC).isoformat(),
            period_type="monthly",
            total_tasks=5000,
            successful_tasks=4800,
            failed_tasks=200,
            total_cost_usd=75.00,
            total_tokens=2500000,
            avg_duration_ms=280.0,
        )

        data = entry.to_dict()
        assert data["period_type"] == "monthly"
        assert data["total_tasks"] == 5000
        assert "id" not in data  # Should be removed if None


class TestCostTrackerIntegration:
    """Test CostTracker integration with SQLite."""

    def test_cost_tracker_uses_database(self):
        """Test that CostTracker properly initializes and uses database."""
        from core.routing.cost_tracker import CostTracker

        with tempfile.TemporaryDirectory() as tmpdir:
            db_path = Path(tmpdir) / "test_tracker.db"
            tracker = CostTracker(storage_path=db_path)

            # Record a cost entry
            tracker.record(
                model="claude-sonnet-4",
                task_id="test-integration",
                task_type="code_generation",
                input_tokens=1000,
                output_tokens=500,
                input_cost=0.010,
                output_cost=0.005,
            )

            # Verify database was created and has data
            assert db_path.exists()
            assert tracker.db.table_exists("cost_entries")

            # Verify data was stored
            results = tracker.db.query(
                "SELECT * FROM cost_entries WHERE task_id = 'test-integration'"
            )
            assert len(results) == 1
            assert results[0]["model_name"] == "claude-sonnet-4"
            assert results[0]["input_tokens"] == 1000
