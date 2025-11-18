"""
Metrics aggregation and storage

Pre-aggregates metrics at different time intervals (hourly, daily, weekly)
for fast querying and dashboard display.
"""

from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Optional, Dict, Any
import logging

from core.persistence.database import Database
from core.persistence.models import MetricEntry

logger = logging.getLogger(__name__)


class MetricsDB:
    """Manages aggregated metrics storage."""

    def __init__(self, db_path: Optional[Path] = None):
        """
        Initialize metrics database.

        Args:
            db_path: Path to database file (default: .buildrunner/data.db)
        """
        self.db = Database(db_path)
        self._init_schema()

    def _init_schema(self):
        """Initialize metrics tables if they don't exist."""
        if not self.db.table_exists("metrics_hourly"):
            migration_sql = """
            CREATE TABLE metrics_hourly (
                timestamp TEXT PRIMARY KEY,
                period_type TEXT NOT NULL DEFAULT 'hourly',
                total_tasks INTEGER NOT NULL DEFAULT 0,
                successful_tasks INTEGER NOT NULL DEFAULT 0,
                failed_tasks INTEGER NOT NULL DEFAULT 0,
                total_cost_usd REAL NOT NULL DEFAULT 0.0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                avg_duration_ms REAL NOT NULL DEFAULT 0.0
            );

            CREATE INDEX idx_metrics_timestamp ON metrics_hourly(timestamp);
            CREATE INDEX idx_metrics_period_type ON metrics_hourly(period_type);
            """
            self.db.run_migration(migration_sql)
            logger.info("Metrics database schema initialized")

    def aggregate_from_cost_entries(
        self,
        start_time: datetime,
        end_time: datetime,
        period_type: str = 'hourly'
    ) -> MetricEntry:
        """
        Aggregate metrics from cost_entries table for a time period.

        Args:
            start_time: Start of aggregation period
            end_time: End of aggregation period
            period_type: Type of period ('hourly', 'daily', 'weekly')

        Returns:
            MetricEntry with aggregated metrics
        """
        # Query cost entries for the period
        sql = """
        SELECT
            COUNT(*) as total_tasks,
            SUM(cost_usd) as total_cost_usd,
            SUM(input_tokens + output_tokens) as total_tokens
        FROM cost_entries
        WHERE timestamp >= ? AND timestamp < ?
        """

        result = self.db.query_one(sql, (
            start_time.isoformat(),
            end_time.isoformat()
        ))

        if not result or result['total_tasks'] == 0:
            return MetricEntry(
                timestamp=start_time.isoformat(),
                period_type=period_type,
                total_tasks=0,
                successful_tasks=0,
                failed_tasks=0,
                total_cost_usd=0.0,
                total_tokens=0,
                avg_duration_ms=0.0
            )

        # For now, assume all tasks are successful (no failure tracking in cost_entries)
        total_tasks = result['total_tasks']

        return MetricEntry(
            timestamp=start_time.isoformat(),
            period_type=period_type,
            total_tasks=total_tasks,
            successful_tasks=total_tasks,  # Assume success if cost recorded
            failed_tasks=0,
            total_cost_usd=result['total_cost_usd'] or 0.0,
            total_tokens=result['total_tokens'] or 0,
            avg_duration_ms=0.0  # Duration not tracked in cost_entries
        )

    def save_metric(self, metric: MetricEntry):
        """
        Save aggregated metric to database.

        Args:
            metric: MetricEntry to save
        """
        try:
            # Use INSERT OR REPLACE to handle duplicates
            data = metric.to_dict()

            # Check if metric already exists
            existing = self.db.query_one(
                "SELECT * FROM metrics_hourly WHERE timestamp = ? AND period_type = ?",
                (metric.timestamp, metric.period_type)
            )

            if existing:
                # Update existing
                self.db.update(
                    'metrics_hourly',
                    data,
                    'timestamp = ? AND period_type = ?',
                    (metric.timestamp, metric.period_type)
                )
                logger.debug(f"Updated metric for {metric.timestamp}")
            else:
                # Insert new
                self.db.insert('metrics_hourly', data)
                logger.debug(f"Inserted metric for {metric.timestamp}")

        except Exception as e:
            logger.error(f"Failed to save metric: {e}")
            raise

    def get_metrics(
        self,
        start_time: Optional[datetime] = None,
        end_time: Optional[datetime] = None,
        period_type: Optional[str] = None
    ) -> List[MetricEntry]:
        """
        Get metrics for a time range.

        Args:
            start_time: Start of time range (optional)
            end_time: End of time range (optional)
            period_type: Filter by period type (optional)

        Returns:
            List of MetricEntry objects
        """
        sql = "SELECT * FROM metrics_hourly WHERE 1=1"
        params = []

        if start_time:
            sql += " AND timestamp >= ?"
            params.append(start_time.isoformat())

        if end_time:
            sql += " AND timestamp < ?"
            params.append(end_time.isoformat())

        if period_type:
            sql += " AND period_type = ?"
            params.append(period_type)

        sql += " ORDER BY timestamp DESC"

        try:
            results = self.db.query(sql, tuple(params))
            return [MetricEntry.from_dict(row) for row in results]
        except Exception as e:
            logger.error(f"Failed to get metrics: {e}")
            return []

    def get_latest_metric(self, period_type: str = 'hourly') -> Optional[MetricEntry]:
        """
        Get the most recent metric for a period type.

        Args:
            period_type: Period type to query

        Returns:
            Latest MetricEntry or None
        """
        result = self.db.query_one(
            "SELECT * FROM metrics_hourly WHERE period_type = ? ORDER BY timestamp DESC LIMIT 1",
            (period_type,)
        )

        if result:
            return MetricEntry.from_dict(result)
        return None

    def aggregate_hourly(self, hour: datetime) -> MetricEntry:
        """
        Aggregate metrics for a specific hour.

        Args:
            hour: Hour to aggregate (truncated to hour)

        Returns:
            MetricEntry for the hour
        """
        # Truncate to hour
        start_time = hour.replace(minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(hours=1)

        return self.aggregate_from_cost_entries(start_time, end_time, 'hourly')

    def aggregate_daily(self, day: datetime) -> MetricEntry:
        """
        Aggregate metrics for a specific day.

        Args:
            day: Day to aggregate (truncated to day)

        Returns:
            MetricEntry for the day
        """
        # Truncate to day
        start_time = day.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(days=1)

        return self.aggregate_from_cost_entries(start_time, end_time, 'daily')

    def aggregate_weekly(self, week_start: datetime) -> MetricEntry:
        """
        Aggregate metrics for a specific week.

        Args:
            week_start: Start of week (typically Monday)

        Returns:
            MetricEntry for the week
        """
        # Truncate to day
        start_time = week_start.replace(hour=0, minute=0, second=0, microsecond=0)
        end_time = start_time + timedelta(weeks=1)

        return self.aggregate_from_cost_entries(start_time, end_time, 'weekly')

    def aggregate_and_save(self, period: datetime, period_type: str):
        """
        Aggregate metrics and save to database.

        Args:
            period: Time period to aggregate
            period_type: Type of period ('hourly', 'daily', 'weekly')
        """
        if period_type == 'hourly':
            metric = self.aggregate_hourly(period)
        elif period_type == 'daily':
            metric = self.aggregate_daily(period)
        elif period_type == 'weekly':
            metric = self.aggregate_weekly(period)
        else:
            raise ValueError(f"Invalid period_type: {period_type}")

        self.save_metric(metric)
        logger.info(f"Aggregated and saved {period_type} metrics for {period.isoformat()}")

    def aggregate_recent_hours(self, hours: int = 24):
        """
        Aggregate metrics for recent hours.

        Args:
            hours: Number of recent hours to aggregate
        """
        now = datetime.now()

        for i in range(hours):
            hour = now - timedelta(hours=i)
            hour = hour.replace(minute=0, second=0, microsecond=0)

            metric = self.aggregate_hourly(hour)
            if metric.total_tasks > 0:  # Only save if there's data
                self.save_metric(metric)

        logger.info(f"Aggregated last {hours} hours of metrics")

    def get_summary(
        self,
        period_type: str = 'hourly',
        limit: int = 24
    ) -> Dict[str, Any]:
        """
        Get summary statistics for recent periods.

        Args:
            period_type: Period type to summarize
            limit: Number of recent periods to include

        Returns:
            Dictionary with summary statistics
        """
        metrics = self.get_metrics(period_type=period_type)[:limit]

        if not metrics:
            return {
                'period_type': period_type,
                'periods': 0,
                'total_tasks': 0,
                'total_cost_usd': 0.0,
                'avg_success_rate': 0.0,
                'avg_cost_per_task': 0.0
            }

        total_tasks = sum(m.total_tasks for m in metrics)
        total_cost = sum(m.total_cost_usd for m in metrics)
        avg_success_rate = sum(m.success_rate for m in metrics) / len(metrics)

        return {
            'period_type': period_type,
            'periods': len(metrics),
            'total_tasks': total_tasks,
            'total_cost_usd': total_cost,
            'avg_success_rate': avg_success_rate,
            'avg_cost_per_task': total_cost / total_tasks if total_tasks > 0 else 0.0,
            'metrics': [m.to_dict() for m in metrics]
        }

    def cleanup_old_metrics(self, days: int = 90):
        """
        Delete metrics older than specified days.

        Args:
            days: Number of days to retain
        """
        cutoff = datetime.now() - timedelta(days=days)

        deleted = self.db.delete(
            'metrics_hourly',
            'timestamp < ?',
            (cutoff.isoformat(),)
        )

        if deleted > 0:
            logger.info(f"Cleaned up {deleted} old metrics")
