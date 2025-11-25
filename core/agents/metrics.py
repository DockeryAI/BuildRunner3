"""
Agent Performance Metrics - Tracks and analyzes agent performance metrics

Features:
- Success rate tracking per agent type (explore, test, review, refactor, implement)
- Cost calculation (token usage × model pricing)
- Quality scoring (test pass rate, error rate, file changes)
- Persistence to .buildrunner/agent_metrics.json and SQLite database
- Historical performance analysis
- Per-task-type performance breakdown
"""

from dataclasses import dataclass, field, asdict
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Tuple
import json
import logging
from collections import defaultdict

from core.agents.claude_agent_bridge import AgentType
from core.persistence.database import Database

logger = logging.getLogger(__name__)


class ModelType(str, Enum):
    """Available Claude models for agent assignment."""

    HAIKU = "claude-haiku-4-5-20251001"
    SONNET = "claude-sonnet-4-5-20250929"
    OPUS = "claude-opus-4-1-20250805"


# Model pricing (USD per 1M tokens) - as of 2025-01-18
MODEL_PRICING = {
    ModelType.HAIKU: {
        "input": 0.80,  # $0.80 per 1M input tokens
        "output": 4.00,  # $4.00 per 1M output tokens
    },
    ModelType.SONNET: {
        "input": 3.00,  # $3.00 per 1M input tokens
        "output": 15.00,  # $15.00 per 1M output tokens
    },
    ModelType.OPUS: {
        "input": 15.00,  # $15.00 per 1M input tokens
        "output": 75.00,  # $75.00 per 1M output tokens
    },
}


@dataclass
class AgentMetric:
    """Single agent execution metric."""

    timestamp: datetime
    agent_type: str  # explore, test, review, refactor, implement
    task_id: str
    task_description: str
    model_used: str  # Model type used

    # Execution details
    duration_ms: float
    input_tokens: int
    output_tokens: int
    total_tokens: int

    # Cost
    cost_usd: float

    # Quality
    success: bool
    test_pass_rate: float = 1.0  # 0.0 to 1.0
    error_rate: float = 0.0  # 0.0 to 1.0
    files_created: int = 0
    files_modified: int = 0

    # Error tracking
    error_message: Optional[str] = None

    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            "timestamp": self.timestamp.isoformat(),
            "agent_type": self.agent_type,
            "task_id": self.task_id,
            "task_description": self.task_description,
            "model_used": self.model_used,
            "duration_ms": self.duration_ms,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
            "cost_usd": self.cost_usd,
            "success": self.success,
            "test_pass_rate": self.test_pass_rate,
            "error_rate": self.error_rate,
            "files_created": self.files_created,
            "files_modified": self.files_modified,
            "error_message": self.error_message,
        }


@dataclass
class AgentPerformanceSummary:
    """Summary statistics for an agent type."""

    agent_type: str

    # Count metrics
    total_tasks: int = 0
    successful_tasks: int = 0
    failed_tasks: int = 0

    # Success rate
    success_rate: float = 0.0  # 0.0 to 1.0

    # Cost metrics
    total_cost_usd: float = 0.0
    avg_cost_per_task: float = 0.0
    min_cost_per_task: float = 0.0
    max_cost_per_task: float = 0.0

    # Token metrics
    total_tokens: int = 0
    avg_tokens_per_task: int = 0

    # Quality metrics
    avg_test_pass_rate: float = 0.0
    avg_error_rate: float = 0.0
    avg_files_created: float = 0.0
    avg_files_modified: float = 0.0

    # Performance
    avg_duration_ms: float = 0.0
    min_duration_ms: float = 0.0
    max_duration_ms: float = 0.0

    # Model usage breakdown
    model_usage: Dict[str, int] = field(default_factory=dict)
    cost_by_model: Dict[str, float] = field(default_factory=dict)

    # Trend (last 7 days)
    success_rate_trend: float = 0.0  # Change from 7d average
    cost_trend: float = 0.0  # Change from 7d average

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return asdict(self)


class AgentMetrics:
    """Tracks and analyzes agent performance metrics."""

    def __init__(
        self,
        storage_path: Optional[Path] = None,
        db_path: Optional[Path] = None,
    ):
        """
        Initialize agent metrics tracker.

        Args:
            storage_path: Path to store metrics JSON (default: .buildrunner/agent_metrics.json)
            db_path: Path to SQLite database (default: .buildrunner/telemetry.db)
        """
        self.storage_path = storage_path or Path.cwd() / ".buildrunner" / "agent_metrics.json"
        self.db_path = db_path or Path.cwd() / ".buildrunner" / "telemetry.db"

        # Ensure .buildrunner directory exists
        self.storage_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self.db = Database(self.db_path)
        self._init_database()

        # In-memory metrics for current session
        self.metrics: List[AgentMetric] = []

        # Load existing metrics from file
        self._load_metrics()

    def _init_database(self):
        """Initialize SQLite database schema for agent metrics."""
        schema = """
        CREATE TABLE IF NOT EXISTS agent_metrics (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            timestamp TEXT NOT NULL,
            agent_type TEXT NOT NULL,
            task_id TEXT NOT NULL,
            task_description TEXT,
            model_used TEXT NOT NULL,
            duration_ms REAL NOT NULL,
            input_tokens INTEGER NOT NULL,
            output_tokens INTEGER NOT NULL,
            total_tokens INTEGER NOT NULL,
            cost_usd REAL NOT NULL,
            success BOOLEAN NOT NULL,
            test_pass_rate REAL DEFAULT 1.0,
            error_rate REAL DEFAULT 0.0,
            files_created INTEGER DEFAULT 0,
            files_modified INTEGER DEFAULT 0,
            error_message TEXT,
            created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        );

        CREATE INDEX IF NOT EXISTS idx_agent_type ON agent_metrics(agent_type);
        CREATE INDEX IF NOT EXISTS idx_timestamp ON agent_metrics(timestamp);
        CREATE INDEX IF NOT EXISTS idx_task_id ON agent_metrics(task_id);
        """

        if not self.db.table_exists("agent_metrics"):
            self.db.run_migration(schema)

    def record_metric(
        self,
        agent_type: str,
        task_id: str,
        task_description: str,
        model_used: str,
        duration_ms: float,
        input_tokens: int,
        output_tokens: int,
        success: bool,
        test_pass_rate: float = 1.0,
        error_rate: float = 0.0,
        files_created: int = 0,
        files_modified: int = 0,
        error_message: Optional[str] = None,
    ) -> AgentMetric:
        """
        Record an agent execution metric.

        Args:
            agent_type: Type of agent (explore, test, review, refactor, implement)
            task_id: Unique task identifier
            task_description: Description of the task
            model_used: Model used for execution (e.g., "claude-sonnet-4-5-20250929")
            duration_ms: Execution duration in milliseconds
            input_tokens: Number of input tokens used
            output_tokens: Number of output tokens used
            success: Whether the task succeeded
            test_pass_rate: Test pass rate (0.0 to 1.0)
            error_rate: Error rate (0.0 to 1.0)
            files_created: Number of files created
            files_modified: Number of files modified
            error_message: Optional error message if failed

        Returns:
            AgentMetric: The recorded metric
        """
        # Calculate cost
        total_tokens = input_tokens + output_tokens
        cost_usd = self._calculate_cost(model_used, input_tokens, output_tokens)

        # Create metric
        metric = AgentMetric(
            timestamp=datetime.now(),
            agent_type=agent_type,
            task_id=task_id,
            task_description=task_description,
            model_used=model_used,
            duration_ms=duration_ms,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
            cost_usd=cost_usd,
            success=success,
            test_pass_rate=test_pass_rate,
            error_rate=error_rate,
            files_created=files_created,
            files_modified=files_modified,
            error_message=error_message,
        )

        # Store in memory
        self.metrics.append(metric)

        # Store in database
        self._insert_metric_db(metric)

        # Save to file
        self._save_metrics()

        logger.info(
            f"Recorded metric for {agent_type} agent on task {task_id}: "
            f"cost=${cost_usd:.4f}, success={success}"
        )

        return metric

    def _calculate_cost(self, model_used: str, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD for token usage."""
        # Determine model type from model string
        model_type = self._get_model_type(model_used)

        if model_type not in MODEL_PRICING:
            logger.warning(f"Unknown model type: {model_used}, assuming Sonnet pricing")
            model_type = ModelType.SONNET

        pricing = MODEL_PRICING[model_type]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    @staticmethod
    def _get_model_type(model_str: str) -> ModelType:
        """Determine model type from model string."""
        if "haiku" in model_str.lower():
            return ModelType.HAIKU
        elif "sonnet" in model_str.lower():
            return ModelType.SONNET
        elif "opus" in model_str.lower():
            return ModelType.OPUS
        else:
            return ModelType.SONNET  # Default

    def get_summary(
        self,
        agent_type: Optional[str] = None,
        time_period_days: int = 7,
    ) -> Optional[AgentPerformanceSummary]:
        """
        Get performance summary for an agent type.

        Args:
            agent_type: Agent type to summarize (e.g., "explore"). None for all agents.
            time_period_days: Number of days to include in summary

        Returns:
            AgentPerformanceSummary: Performance summary, or None if no data
        """
        # Filter metrics by agent type and time period
        cutoff_time = datetime.now() - timedelta(days=time_period_days)

        filtered_metrics = [
            m
            for m in self.metrics
            if (agent_type is None or m.agent_type == agent_type) and m.timestamp >= cutoff_time
        ]

        if not filtered_metrics:
            return None

        # Calculate summary statistics
        total_tasks = len(filtered_metrics)
        successful_tasks = sum(1 for m in filtered_metrics if m.success)
        failed_tasks = total_tasks - successful_tasks
        success_rate = successful_tasks / total_tasks if total_tasks > 0 else 0.0

        # Cost metrics
        total_cost = sum(m.cost_usd for m in filtered_metrics)
        avg_cost = total_cost / total_tasks if total_tasks > 0 else 0.0
        costs = [m.cost_usd for m in filtered_metrics]
        min_cost = min(costs) if costs else 0.0
        max_cost = max(costs) if costs else 0.0

        # Token metrics
        total_tokens = sum(m.total_tokens for m in filtered_metrics)
        avg_tokens = total_tokens // total_tasks if total_tasks > 0 else 0

        # Quality metrics
        avg_test_pass_rate = (
            sum(m.test_pass_rate for m in filtered_metrics) / total_tasks
            if total_tasks > 0
            else 0.0
        )
        avg_error_rate = (
            sum(m.error_rate for m in filtered_metrics) / total_tasks if total_tasks > 0 else 0.0
        )
        avg_files_created = (
            sum(m.files_created for m in filtered_metrics) / total_tasks if total_tasks > 0 else 0.0
        )
        avg_files_modified = (
            sum(m.files_modified for m in filtered_metrics) / total_tasks
            if total_tasks > 0
            else 0.0
        )

        # Performance metrics
        durations = [m.duration_ms for m in filtered_metrics]
        avg_duration = sum(durations) / len(durations) if durations else 0.0
        min_duration = min(durations) if durations else 0.0
        max_duration = max(durations) if durations else 0.0

        # Model usage breakdown
        model_usage = defaultdict(int)
        cost_by_model = defaultdict(float)
        for m in filtered_metrics:
            model_usage[m.model_used] += 1
            cost_by_model[m.model_used] += m.cost_usd

        # Calculate trend (7-day trend by comparing to prior period)
        prior_cutoff = cutoff_time - timedelta(days=time_period_days)
        prior_metrics = [
            m
            for m in self.metrics
            if (agent_type is None or m.agent_type == agent_type)
            and prior_cutoff <= m.timestamp < cutoff_time
        ]

        success_rate_trend = 0.0
        cost_trend = 0.0

        if prior_metrics:
            prior_success_rate = sum(1 for m in prior_metrics if m.success) / len(prior_metrics)
            success_rate_trend = success_rate - prior_success_rate

            prior_cost = sum(m.cost_usd for m in prior_metrics)
            prior_avg_cost = prior_cost / len(prior_metrics)
            cost_trend = (
                (avg_cost - prior_avg_cost) / prior_avg_cost * 100 if prior_avg_cost > 0 else 0.0
            )

        return AgentPerformanceSummary(
            agent_type=agent_type or "all",
            total_tasks=total_tasks,
            successful_tasks=successful_tasks,
            failed_tasks=failed_tasks,
            success_rate=success_rate,
            total_cost_usd=total_cost,
            avg_cost_per_task=avg_cost,
            min_cost_per_task=min_cost,
            max_cost_per_task=max_cost,
            total_tokens=total_tokens,
            avg_tokens_per_task=avg_tokens,
            avg_test_pass_rate=avg_test_pass_rate,
            avg_error_rate=avg_error_rate,
            avg_files_created=avg_files_created,
            avg_files_modified=avg_files_modified,
            avg_duration_ms=avg_duration,
            min_duration_ms=min_duration,
            max_duration_ms=max_duration,
            model_usage=dict(model_usage),
            cost_by_model=dict(cost_by_model),
            success_rate_trend=success_rate_trend,
            cost_trend=cost_trend,
        )

    def get_agent_types_summary(
        self, time_period_days: int = 7
    ) -> Dict[str, AgentPerformanceSummary]:
        """
        Get performance summary for all agent types.

        Args:
            time_period_days: Number of days to include in summary

        Returns:
            Dict mapping agent type to AgentPerformanceSummary
        """
        summaries = {}

        for agent_type in [at.value for at in AgentType]:
            summary = self.get_summary(agent_type, time_period_days)
            if summary:
                summaries[agent_type] = summary

        return summaries

    def get_task_type_performance(self, task_type: str) -> Optional[AgentPerformanceSummary]:
        """
        Get performance metrics for a specific task type.

        Args:
            task_type: Type of task (e.g., "database", "frontend", "api")

        Returns:
            AgentPerformanceSummary filtered for the task type, or None
        """
        # Filter metrics by task description patterns
        filtered_metrics = [
            m for m in self.metrics if task_type.lower() in m.task_description.lower()
        ]

        if not filtered_metrics:
            return None

        # Create a summary for the task type
        summary = AgentPerformanceSummary(agent_type=f"task_type:{task_type}")

        summary.total_tasks = len(filtered_metrics)
        summary.successful_tasks = sum(1 for m in filtered_metrics if m.success)
        summary.failed_tasks = summary.total_tasks - summary.successful_tasks
        summary.success_rate = (
            summary.successful_tasks / summary.total_tasks if summary.total_tasks > 0 else 0.0
        )

        summary.total_cost_usd = sum(m.cost_usd for m in filtered_metrics)
        summary.avg_cost_per_task = (
            summary.total_cost_usd / summary.total_tasks if summary.total_tasks > 0 else 0.0
        )

        return summary

    def get_best_model_for_agent_type(self, agent_type: str) -> Optional[str]:
        """
        Get the best performing model for a specific agent type.

        Args:
            agent_type: Type of agent (explore, test, review, refactor, implement)

        Returns:
            Model name with best success rate and cost efficiency, or None
        """
        # Filter metrics for this agent type
        agent_metrics = [m for m in self.metrics if m.agent_type == agent_type]

        if not agent_metrics:
            return None

        # Group by model and calculate metrics
        model_stats = defaultdict(lambda: {"success": 0, "total": 0, "cost": 0.0})

        for m in agent_metrics:
            model_stats[m.model_used]["total"] += 1
            if m.success:
                model_stats[m.model_used]["success"] += 1
            model_stats[m.model_used]["cost"] += m.cost_usd

        # Find best model by success rate and cost efficiency
        best_model = None
        best_score = -1.0

        for model, stats in model_stats.items():
            if stats["total"] == 0:
                continue

            success_rate = stats["success"] / stats["total"]
            avg_cost = stats["cost"] / stats["total"]

            # Score: favor high success rate, penalize high cost
            # Weight: 70% success rate, 30% cost efficiency
            cost_efficiency = 1.0 / (avg_cost + 0.0001)  # Avoid division by zero
            max_cost_efficiency = 1.0 / 0.001  # For normalization
            normalized_cost = min(cost_efficiency / max_cost_efficiency, 1.0)

            score = (success_rate * 0.7) + (normalized_cost * 0.3)

            if score > best_score:
                best_score = score
                best_model = model

        return best_model

    def _insert_metric_db(self, metric: AgentMetric):
        """Insert metric into database."""
        try:
            self.db.insert(
                "agent_metrics",
                {
                    "timestamp": metric.timestamp.isoformat(),
                    "agent_type": metric.agent_type,
                    "task_id": metric.task_id,
                    "task_description": metric.task_description,
                    "model_used": metric.model_used,
                    "duration_ms": metric.duration_ms,
                    "input_tokens": metric.input_tokens,
                    "output_tokens": metric.output_tokens,
                    "total_tokens": metric.total_tokens,
                    "cost_usd": metric.cost_usd,
                    "success": metric.success,
                    "test_pass_rate": metric.test_pass_rate,
                    "error_rate": metric.error_rate,
                    "files_created": metric.files_created,
                    "files_modified": metric.files_modified,
                    "error_message": metric.error_message,
                },
            )
        except Exception as e:
            logger.error(f"Failed to insert metric into database: {e}")

    def _save_metrics(self):
        """Save metrics to JSON file for backup."""
        try:
            metrics_data = [m.to_dict() for m in self.metrics]
            self.storage_path.write_text(json.dumps(metrics_data, indent=2, default=str))
        except Exception as e:
            logger.error(f"Failed to save metrics to file: {e}")

    def _load_metrics(self):
        """Load metrics from JSON file."""
        if not self.storage_path.exists():
            return

        try:
            data = json.loads(self.storage_path.read_text())
            for item in data:
                metric = AgentMetric(
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    agent_type=item["agent_type"],
                    task_id=item["task_id"],
                    task_description=item.get("task_description", ""),
                    model_used=item["model_used"],
                    duration_ms=item["duration_ms"],
                    input_tokens=item["input_tokens"],
                    output_tokens=item["output_tokens"],
                    total_tokens=item["total_tokens"],
                    cost_usd=item["cost_usd"],
                    success=item["success"],
                    test_pass_rate=item.get("test_pass_rate", 1.0),
                    error_rate=item.get("error_rate", 0.0),
                    files_created=item.get("files_created", 0),
                    files_modified=item.get("files_modified", 0),
                    error_message=item.get("error_message"),
                )
                self.metrics.append(metric)
        except Exception as e:
            logger.error(f"Failed to load metrics from file: {e}")

    def clear_metrics(self):
        """Clear all stored metrics."""
        self.metrics.clear()
        if self.storage_path.exists():
            self.storage_path.unlink()
        logger.info("Cleared all stored metrics")

    def export_metrics(self, export_path: Path) -> bool:
        """
        Export metrics to a file.

        Args:
            export_path: Path to export metrics to

        Returns:
            True if successful, False otherwise
        """
        try:
            metrics_data = [m.to_dict() for m in self.metrics]
            export_path.write_text(json.dumps(metrics_data, indent=2, default=str))
            logger.info(f"Exported {len(self.metrics)} metrics to {export_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to export metrics: {e}")
            return False

    def import_metrics(self, import_path: Path) -> bool:
        """
        Import metrics from a file.

        Args:
            import_path: Path to import metrics from

        Returns:
            True if successful, False otherwise
        """
        try:
            data = json.loads(import_path.read_text())
            for item in data:
                metric = AgentMetric(
                    timestamp=datetime.fromisoformat(item["timestamp"]),
                    agent_type=item["agent_type"],
                    task_id=item["task_id"],
                    task_description=item.get("task_description", ""),
                    model_used=item["model_used"],
                    duration_ms=item["duration_ms"],
                    input_tokens=item["input_tokens"],
                    output_tokens=item["output_tokens"],
                    total_tokens=item["total_tokens"],
                    cost_usd=item["cost_usd"],
                    success=item["success"],
                    test_pass_rate=item.get("test_pass_rate", 1.0),
                    error_rate=item.get("error_rate", 0.0),
                    files_created=item.get("files_created", 0),
                    files_modified=item.get("files_modified", 0),
                    error_message=item.get("error_message"),
                )
                self.metrics.append(metric)

            # Save to database
            for metric in self.metrics:
                self._insert_metric_db(metric)

            logger.info(f"Imported {len(data)} metrics from {import_path}")
            return True
        except Exception as e:
            logger.error(f"Failed to import metrics: {e}")
            return False
