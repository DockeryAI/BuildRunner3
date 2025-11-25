"""
Tests for metrics aggregation and storage
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

from core.persistence.metrics_db import MetricsDB
from core.persistence.models import MetricEntry, CostEntry
from core.persistence.database import Database


@pytest.fixture
def temp_db():
    """Create temporary database for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        db_path = Path(tmpdir) / "test_metrics.db"
        yield db_path


@pytest.fixture
def metrics_db(temp_db):
    """Create MetricsDB instance with test database."""
    return MetricsDB(db_path=temp_db)


@pytest.fixture
def populated_db(temp_db):
    """Create database with sample cost entries."""
    db = Database(temp_db)

    # Initialize cost_entries table
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
    """
    db.run_migration(migration_sql)

    # Insert sample cost entries
    base_time = datetime(2025, 1, 18, 10, 0, 0)

    for i in range(10):
        entry = CostEntry.create(
            model_name="claude-sonnet-4",
            input_tokens=1000 + i * 100,
            output_tokens=500 + i * 50,
            cost_usd=0.015 + i * 0.001,
            task_id=f"task-{i}",
        )

        # Set specific timestamp (10 minutes apart)
        entry.timestamp = (base_time + timedelta(minutes=i * 10)).isoformat()

        db.insert("cost_entries", entry.to_dict())

    db.close()
    return temp_db


class TestMetricsDB:
    """Test MetricsDB class."""

    def test_schema_initialization(self, metrics_db):
        """Test that metrics schema is properly initialized."""
        assert metrics_db.db.table_exists("metrics_hourly")

        # Verify table structure
        result = metrics_db.db.query("SELECT name FROM pragma_table_info('metrics_hourly')")

        columns = [row["name"] for row in result]
        assert "timestamp" in columns
        assert "period_type" in columns
        assert "total_tasks" in columns
        assert "successful_tasks" in columns
        assert "total_cost_usd" in columns

    def test_save_and_retrieve_metric(self, metrics_db):
        """Test saving and retrieving a metric."""
        # Create metric
        metric = MetricEntry(
            timestamp=datetime(2025, 1, 18, 10, 0, 0).isoformat(),
            period_type="hourly",
            total_tasks=100,
            successful_tasks=95,
            failed_tasks=5,
            total_cost_usd=1.50,
            total_tokens=50000,
            avg_duration_ms=250.5,
        )

        # Save metric
        metrics_db.save_metric(metric)

        # Retrieve metric
        retrieved_metrics = metrics_db.get_metrics(
            start_time=datetime(2025, 1, 18, 9, 0, 0),
            end_time=datetime(2025, 1, 18, 11, 0, 0),
            period_type="hourly",
        )

        assert len(retrieved_metrics) == 1
        assert retrieved_metrics[0].total_tasks == 100
        assert retrieved_metrics[0].successful_tasks == 95
        assert retrieved_metrics[0].total_cost_usd == 1.50

    def test_aggregate_from_cost_entries(self, populated_db):
        """Test aggregating metrics from cost entries."""
        metrics_db = MetricsDB(db_path=populated_db)

        # Aggregate metrics for the hour
        start_time = datetime(2025, 1, 18, 10, 0, 0)
        end_time = datetime(2025, 1, 18, 11, 0, 0)

        metric = metrics_db.aggregate_from_cost_entries(start_time, end_time, "hourly")

        # Verify aggregation
        assert metric.total_tasks == 6  # Entries from 10:00 to 10:50 (6 entries)
        assert metric.total_cost_usd > 0
        assert metric.total_tokens > 0
        assert metric.period_type == "hourly"

    def test_hourly_aggregation(self, populated_db):
        """Test hourly metric aggregation."""
        metrics_db = MetricsDB(db_path=populated_db)

        # Aggregate for specific hour
        hour = datetime(2025, 1, 18, 10, 30, 45)  # Should truncate to 10:00

        metric = metrics_db.aggregate_hourly(hour)

        # Verify aggregation
        assert metric.period_type == "hourly"
        assert metric.timestamp == datetime(2025, 1, 18, 10, 0, 0).isoformat()
        assert metric.total_tasks > 0

    def test_daily_aggregation(self, populated_db):
        """Test daily metric aggregation."""
        metrics_db = MetricsDB(db_path=populated_db)

        # Aggregate for specific day
        day = datetime(2025, 1, 18, 15, 30, 45)  # Should truncate to 00:00

        metric = metrics_db.aggregate_daily(day)

        # Verify aggregation
        assert metric.period_type == "daily"
        assert metric.timestamp == datetime(2025, 1, 18, 0, 0, 0).isoformat()
        assert metric.total_tasks == 10  # All 10 entries from sample data

    def test_aggregate_and_save(self, populated_db):
        """Test aggregating and saving metrics in one operation."""
        metrics_db = MetricsDB(db_path=populated_db)

        # Aggregate and save hourly metric
        period = datetime(2025, 1, 18, 10, 0, 0)
        metrics_db.aggregate_and_save(period, "hourly")

        # Verify metric was saved
        latest = metrics_db.get_latest_metric("hourly")
        assert latest is not None
        assert latest.period_type == "hourly"
        assert latest.total_tasks > 0

    def test_get_summary(self, populated_db):
        """Test getting summary statistics."""
        metrics_db = MetricsDB(db_path=populated_db)

        # Create some hourly metrics
        for hour in range(5):
            period = datetime(2025, 1, 18, 10 + hour, 0, 0)
            metrics_db.aggregate_and_save(period, "hourly")

        # Get summary
        summary = metrics_db.get_summary(period_type="hourly", limit=5)

        # Verify summary
        assert summary["period_type"] == "hourly"
        assert summary["periods"] > 0
        assert summary["total_tasks"] >= 0
        assert "avg_success_rate" in summary
        assert "metrics" in summary

    def test_cleanup_old_metrics(self, metrics_db):
        """Test cleanup of old metrics."""
        # Create old metric (90+ days ago)
        old_time = datetime.now() - timedelta(days=100)
        old_metric = MetricEntry(
            timestamp=old_time.isoformat(),
            period_type="hourly",
            total_tasks=50,
            successful_tasks=50,
            failed_tasks=0,
            total_cost_usd=0.75,
            total_tokens=25000,
            avg_duration_ms=200.0,
        )
        metrics_db.save_metric(old_metric)

        # Create recent metric
        recent_time = datetime.now() - timedelta(days=1)
        recent_metric = MetricEntry(
            timestamp=recent_time.isoformat(),
            period_type="hourly",
            total_tasks=100,
            successful_tasks=95,
            failed_tasks=5,
            total_cost_usd=1.50,
            total_tokens=50000,
            avg_duration_ms=250.5,
        )
        metrics_db.save_metric(recent_metric)

        # Cleanup old metrics (90 days retention)
        metrics_db.cleanup_old_metrics(days=90)

        # Verify old metric removed, recent kept
        all_metrics = metrics_db.get_metrics()
        assert len(all_metrics) == 1
        assert all_metrics[0].total_tasks == 100  # Recent metric

    def test_update_existing_metric(self, metrics_db):
        """Test updating an existing metric."""
        timestamp = datetime(2025, 1, 18, 10, 0, 0).isoformat()

        # Create initial metric
        metric1 = MetricEntry(
            timestamp=timestamp,
            period_type="hourly",
            total_tasks=50,
            successful_tasks=45,
            failed_tasks=5,
            total_cost_usd=0.75,
            total_tokens=25000,
            avg_duration_ms=200.0,
        )
        metrics_db.save_metric(metric1)

        # Update with new values
        metric2 = MetricEntry(
            timestamp=timestamp,
            period_type="hourly",
            total_tasks=100,
            successful_tasks=95,
            failed_tasks=5,
            total_cost_usd=1.50,
            total_tokens=50000,
            avg_duration_ms=250.5,
        )
        metrics_db.save_metric(metric2)

        # Verify only one metric exists with updated values
        metrics = metrics_db.get_metrics(period_type="hourly")
        assert len(metrics) == 1
        assert metrics[0].total_tasks == 100
        assert metrics[0].total_cost_usd == 1.50
