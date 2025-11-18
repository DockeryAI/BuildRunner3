"""
Cost Tracker - Tracks and analyzes API costs for model usage

Tracks:
- Per-request costs
- Daily/weekly/monthly aggregates
- Cost by model
- Cost by task type
- Budget alerts and warnings
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional
import json
import logging

from core.persistence.database import Database

logger = logging.getLogger(__name__)


@dataclass
class CostEntry:
    """Single cost entry for an API request."""

    timestamp: datetime
    model: str
    task_id: str
    task_type: str

    # Token usage
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Cost (USD)
    input_cost: float
    output_cost: float
    total_cost: float

    # Metadata
    success: bool = True
    error: Optional[str] = None
    duration_ms: float = 0.0


@dataclass
class CostSummary:
    """Cost summary for a time period."""

    period: str  # "hour", "day", "week", "month", "all"
    start_date: datetime
    end_date: datetime

    # Totals
    total_requests: int = 0
    total_cost: float = 0.0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    total_tokens: int = 0

    # Breakdowns
    cost_by_model: Dict[str, float] = field(default_factory=dict)
    cost_by_task_type: Dict[str, float] = field(default_factory=dict)
    requests_by_model: Dict[str, int] = field(default_factory=dict)

    # Statistics
    avg_cost_per_request: float = 0.0
    avg_tokens_per_request: float = 0.0
    most_expensive_model: str = ""
    most_used_model: str = ""


class CostTracker:
    """Tracks and analyzes API costs."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        budget_daily: Optional[float] = None,
        budget_monthly: Optional[float] = None,
    ):
        """
        Initialize cost tracker.

        Args:
            storage_path: Path to store cost data (SQLite database)
            budget_daily: Daily budget in USD (warning threshold)
            budget_monthly: Monthly budget in USD (warning threshold)
        """
        db_path = storage_path or Path.cwd() / ".buildrunner" / "data.db"
        self.db = Database(db_path)
        self.budget_daily = budget_daily
        self.budget_monthly = budget_monthly

        # Initialize database schema
        self._init_schema()

        self.entries: List[CostEntry] = []
        self._load()

    def record(
        self,
        model: str,
        task_id: str,
        task_type: str,
        input_tokens: int,
        output_tokens: int,
        input_cost: float,
        output_cost: float,
        success: bool = True,
        error: Optional[str] = None,
        duration_ms: float = 0.0,
    ) -> CostEntry:
        """
        Record a cost entry.

        Args:
            model: Model name used
            task_id: Task identifier
            task_type: Type of task
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            input_cost: Cost for input tokens (USD)
            output_cost: Cost for output tokens (USD)
            success: Whether request succeeded
            error: Error message if failed
            duration_ms: Request duration in milliseconds

        Returns:
            CostEntry that was recorded
        """
        entry = CostEntry(
            timestamp=datetime.now(),
            model=model,
            task_id=task_id,
            task_type=task_type,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
            input_cost=input_cost,
            output_cost=output_cost,
            total_cost=input_cost + output_cost,
            success=success,
            error=error,
            duration_ms=duration_ms,
        )

        self.entries.append(entry)
        self._save()

        # Check budget warnings
        self._check_budgets()

        return entry

    def get_summary(
        self,
        period: str = "all",
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
    ) -> CostSummary:
        """
        Get cost summary for a time period.

        Args:
            period: Time period ("hour", "day", "week", "month", "all")
            start_date: Custom start date (overrides period)
            end_date: Custom end date (overrides period)

        Returns:
            CostSummary for the period
        """
        now = datetime.now()

        # Determine date range
        if start_date and end_date:
            # Custom range
            pass
        elif period == "hour":
            start_date = now - timedelta(hours=1)
            end_date = now
        elif period == "day":
            start_date = now - timedelta(days=1)
            end_date = now
        elif period == "week":
            start_date = now - timedelta(weeks=1)
            end_date = now
        elif period == "month":
            start_date = now - timedelta(days=30)
            end_date = now
        else:  # "all"
            if self.entries:
                start_date = self.entries[0].timestamp
                end_date = now
            else:
                start_date = now
                end_date = now

        # Filter entries
        filtered = [
            e for e in self.entries
            if start_date <= e.timestamp <= end_date
        ]

        if not filtered:
            return CostSummary(
                period=period,
                start_date=start_date,
                end_date=end_date,
            )

        # Calculate totals
        total_requests = len(filtered)
        total_cost = sum(e.total_cost for e in filtered)
        total_input_tokens = sum(e.input_tokens for e in filtered)
        total_output_tokens = sum(e.output_tokens for e in filtered)
        total_tokens = total_input_tokens + total_output_tokens

        # Cost by model
        cost_by_model: Dict[str, float] = {}
        requests_by_model: Dict[str, int] = {}
        for entry in filtered:
            cost_by_model[entry.model] = cost_by_model.get(entry.model, 0.0) + entry.total_cost
            requests_by_model[entry.model] = requests_by_model.get(entry.model, 0) + 1

        # Cost by task type
        cost_by_task_type: Dict[str, float] = {}
        for entry in filtered:
            cost_by_task_type[entry.task_type] = \
                cost_by_task_type.get(entry.task_type, 0.0) + entry.total_cost

        # Find most expensive and most used
        most_expensive_model = max(cost_by_model.keys(), key=lambda k: cost_by_model[k]) \
            if cost_by_model else ""
        most_used_model = max(requests_by_model.keys(), key=lambda k: requests_by_model[k]) \
            if requests_by_model else ""

        return CostSummary(
            period=period,
            start_date=start_date,
            end_date=end_date,
            total_requests=total_requests,
            total_cost=total_cost,
            total_input_tokens=total_input_tokens,
            total_output_tokens=total_output_tokens,
            total_tokens=total_tokens,
            cost_by_model=cost_by_model,
            cost_by_task_type=cost_by_task_type,
            requests_by_model=requests_by_model,
            avg_cost_per_request=total_cost / total_requests,
            avg_tokens_per_request=total_tokens / total_requests,
            most_expensive_model=most_expensive_model,
            most_used_model=most_used_model,
        )

    def get_recent_entries(self, limit: int = 10) -> List[CostEntry]:
        """
        Get most recent cost entries.

        Args:
            limit: Number of entries to return

        Returns:
            List of recent CostEntry objects
        """
        return sorted(self.entries, key=lambda e: e.timestamp, reverse=True)[:limit]

    def clear_old_entries(self, days: int = 90):
        """
        Clear entries older than specified days.

        Args:
            days: Number of days to keep
        """
        cutoff = datetime.now() - timedelta(days=days)
        self.entries = [e for e in self.entries if e.timestamp >= cutoff]
        self._save()

    def _init_schema(self):
        """Initialize database schema if needed."""
        if not self.db.table_exists("cost_entries"):
            # Read and run migration
            migration_path = Path(__file__).parent.parent / "persistence" / "migrations" / "001_initial.sql"
            if migration_path.exists():
                with open(migration_path, 'r') as f:
                    migration_sql = f.read()
                self.db.run_migration(migration_sql)
                logger.info("Cost tracking database schema initialized")

    def _check_budgets(self):
        """Check if budgets are exceeded and print warnings."""
        if self.budget_daily:
            daily_summary = self.get_summary(period="day")
            if daily_summary.total_cost > self.budget_daily:
                print(f"⚠️  Daily budget exceeded: ${daily_summary.total_cost:.4f} / ${self.budget_daily:.2f}")

        if self.budget_monthly:
            monthly_summary = self.get_summary(period="month")
            if monthly_summary.total_cost > self.budget_monthly:
                print(f"⚠️  Monthly budget exceeded: ${monthly_summary.total_cost:.2f} / ${self.budget_monthly:.2f}")

    def _save(self):
        """Save cost entries to database."""
        try:
            # Save only the most recent entry (others are already saved)
            if self.entries:
                entry = self.entries[-1]
                data = {
                    'timestamp': entry.timestamp.isoformat(),
                    'task_id': entry.task_id,
                    'model_name': entry.model,
                    'input_tokens': entry.input_tokens,
                    'output_tokens': entry.output_tokens,
                    'cost_usd': entry.total_cost,
                    'session_id': None,  # Could be added later
                }
                self.db.insert('cost_entries', data)
                logger.debug(f"Saved cost entry: {entry.model} - ${entry.total_cost:.6f}")

        except Exception as e:
            logger.error(f"Failed to save cost data: {e}")

    def _load(self):
        """Load cost entries from database."""
        try:
            if not self.db.table_exists("cost_entries"):
                self.entries = []
                return

            # Query all entries from database
            rows = self.db.query("SELECT * FROM cost_entries ORDER BY timestamp DESC LIMIT 1000")

            # Convert to CostEntry objects
            # Note: Database has limited fields, so we reconstruct with defaults
            self.entries = [
                CostEntry(
                    timestamp=datetime.fromisoformat(row['timestamp']),
                    model=row['model_name'],
                    task_id=row['task_id'] or '',
                    task_type='unknown',  # Not stored in simplified schema
                    input_tokens=row['input_tokens'],
                    output_tokens=row['output_tokens'],
                    total_tokens=row['input_tokens'] + row['output_tokens'],
                    input_cost=0.0,  # Not stored separately
                    output_cost=0.0,  # Not stored separately
                    total_cost=row['cost_usd'],
                    success=True,  # Assume success if stored
                    error=None,
                    duration_ms=0.0,  # Not tracked in simplified schema
                )
                for row in rows
            ]

            logger.info(f"Loaded {len(self.entries)} cost entries from database")

        except Exception as e:
            logger.error(f"Failed to load cost data: {e}")
            self.entries = []

    def export_csv(self, output_path: Path):
        """
        Export cost entries to CSV.

        Args:
            output_path: Path to output CSV file
        """
        import csv

        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)

            # Header
            writer.writerow([
                'Timestamp', 'Model', 'Task ID', 'Task Type',
                'Input Tokens', 'Output Tokens', 'Total Tokens',
                'Input Cost', 'Output Cost', 'Total Cost',
                'Success', 'Error', 'Duration (ms)',
            ])

            # Data
            for entry in self.entries:
                writer.writerow([
                    entry.timestamp.isoformat(),
                    entry.model,
                    entry.task_id,
                    entry.task_type,
                    entry.input_tokens,
                    entry.output_tokens,
                    entry.total_tokens,
                    f"{entry.input_cost:.6f}",
                    f"{entry.output_cost:.6f}",
                    f"{entry.total_cost:.6f}",
                    entry.success,
                    entry.error or "",
                    f"{entry.duration_ms:.2f}",
                ])
