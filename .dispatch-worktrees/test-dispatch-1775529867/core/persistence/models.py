"""
Data models for BuildRunner persistence layer
"""

from dataclasses import dataclass, asdict
from datetime import datetime, UTC
from typing import Optional


@dataclass
class CostEntry:
    """Cost tracking entry"""

    timestamp: str
    task_id: Optional[str]
    model_name: str
    input_tokens: int
    output_tokens: int
    cost_usd: float
    session_id: Optional[str] = None
    id: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "CostEntry":
        """Create CostEntry from dictionary"""
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        data = asdict(self)
        # Remove id if None (for inserts)
        if data.get("id") is None:
            data.pop("id", None)
        return data

    @staticmethod
    def create(
        model_name: str,
        input_tokens: int,
        output_tokens: int,
        cost_usd: float,
        task_id: Optional[str] = None,
        session_id: Optional[str] = None,
    ) -> "CostEntry":
        """
        Create new cost entry with current timestamp

        Args:
            model_name: Name of AI model used
            input_tokens: Number of input tokens
            output_tokens: Number of output tokens
            cost_usd: Cost in USD
            task_id: Optional task identifier
            session_id: Optional session identifier

        Returns:
            New CostEntry instance
        """
        return CostEntry(
            timestamp=datetime.now(UTC).isoformat(),
            task_id=task_id,
            model_name=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=cost_usd,
            session_id=session_id,
        )


@dataclass
class MetricEntry:
    """Aggregated metrics entry"""

    timestamp: str  # ISO format timestamp for period start
    period_type: str  # 'hourly', 'daily', 'weekly'
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    total_cost_usd: float
    total_tokens: int
    avg_duration_ms: float
    id: Optional[int] = None

    @classmethod
    def from_dict(cls, data: dict) -> "MetricEntry":
        """Create MetricEntry from dictionary"""
        return cls(**data)

    def to_dict(self) -> dict:
        """Convert to dictionary for database storage"""
        data = asdict(self)
        # Remove id if None (for inserts)
        if data.get("id") is None:
            data.pop("id", None)
        return data

    @property
    def success_rate(self) -> float:
        """Calculate success rate"""
        if self.total_tasks == 0:
            return 0.0
        return self.successful_tasks / self.total_tasks

    @property
    def avg_cost_per_task(self) -> float:
        """Calculate average cost per task"""
        if self.total_tasks == 0:
            return 0.0
        return self.total_cost_usd / self.total_tasks
