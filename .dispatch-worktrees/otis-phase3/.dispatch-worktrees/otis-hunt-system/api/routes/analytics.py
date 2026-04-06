"""
Analytics API Routes

Provides endpoints for:
- Agent performance metrics and charts
- Cost breakdown visualization by agent/model
- Success rate trends over time
- Historical performance comparisons
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
from pydantic import BaseModel

# Import metrics modules
from core.telemetry.metrics_analyzer import MetricsAnalyzer, MetricType
from core.persistence.metrics_db import MetricsDB
from core.telemetry.event_collector import EventCollector

router = APIRouter(prefix="/analytics", tags=["analytics"])

# Global instances
_metrics_analyzer: Optional[MetricsAnalyzer] = None
_metrics_db: Optional[MetricsDB] = None
_event_collector: Optional[EventCollector] = None


def get_metrics_analyzer() -> MetricsAnalyzer:
    """Get or create metrics analyzer instance"""
    global _metrics_analyzer
    if _metrics_analyzer is None:
        event_collector = get_event_collector()
        _metrics_analyzer = MetricsAnalyzer(event_collector)
    return _metrics_analyzer


def get_metrics_db() -> MetricsDB:
    """Get or create metrics database instance"""
    global _metrics_db
    if _metrics_db is None:
        _metrics_db = MetricsDB()
    return _metrics_db


def get_event_collector() -> EventCollector:
    """Get or create event collector instance"""
    global _event_collector
    if _event_collector is None:
        _event_collector = EventCollector()
    return _event_collector


# Response Models


class AgentPerformanceMetric(BaseModel):
    """Agent performance metric data"""

    agent_id: str
    success_rate: float  # 0-100
    total_tasks: int
    successful_tasks: int
    failed_tasks: int
    avg_duration_ms: float
    p95_duration_ms: float
    p99_duration_ms: float
    total_cost_usd: float
    avg_cost_per_task: float
    timestamp: datetime


class CostBreakdownItem(BaseModel):
    """Cost breakdown by agent or model"""

    name: str  # Agent name or model name
    cost_usd: float
    percentage: float
    token_count: int
    task_count: int


class CostBreakdownResponse(BaseModel):
    """Cost breakdown visualization data"""

    total_cost_usd: float
    period: str  # "hour", "day", "week"
    breakdown_by_agent: List[CostBreakdownItem]
    breakdown_by_model: List[CostBreakdownItem]
    breakdown_by_type: List[CostBreakdownItem]  # e.g., input vs output tokens


class SuccessTrendPoint(BaseModel):
    """Single point in success trend data"""

    timestamp: str  # ISO format date/time
    success_rate: float  # 0-100
    total_tasks: int
    successful_tasks: int
    failed_tasks: int


class SuccessTrendsResponse(BaseModel):
    """Success rate trends over time"""

    period: str  # "hour", "day", "week"
    start_date: str
    end_date: str
    points: List[SuccessTrendPoint]
    avg_success_rate: float
    min_success_rate: float
    max_success_rate: float


class HistoricalComparisonPeriod(BaseModel):
    """Historical data for a comparison period"""

    period: str
    success_rate: float
    cost_per_task: float
    total_tasks: int
    avg_duration_ms: float


class HistoricalComparisonResponse(BaseModel):
    """Historical comparison data"""

    current_period: HistoricalComparisonPeriod
    previous_period: HistoricalComparisonPeriod
    week_ago: HistoricalComparisonPeriod
    month_ago: HistoricalComparisonPeriod
    improvements: Dict[str, float]  # e.g., {"success_rate": 5.2, "cost_per_task": -10.3}
    trends: Dict[str, str]  # e.g., {"success_rate": "up", "cost_per_task": "down"}


@router.get("/agent-performance", response_model=List[AgentPerformanceMetric])
async def get_agent_performance(
    period: str = Query("day", pattern="^(hour|day|week|all)$")
) -> List[AgentPerformanceMetric]:
    """
    Get agent performance metrics and charts.

    Args:
        period: Time period for metrics ("hour", "day", "week", "all")

    Returns:
        List of agent performance metrics
    """
    try:
        analyzer = get_metrics_analyzer()

        # Calculate summary for the period
        summary = analyzer.calculate_summary(period=period)

        # For now, return a single aggregated metric
        # In production, this would break down by agent_id
        result = AgentPerformanceMetric(
            agent_id="aggregated",
            success_rate=summary.success_rate,
            total_tasks=summary.total_tasks,
            successful_tasks=summary.successful_tasks,
            failed_tasks=summary.failed_tasks,
            avg_duration_ms=summary.avg_duration_ms,
            p95_duration_ms=summary.p95_duration_ms,
            p99_duration_ms=summary.p99_duration_ms,
            total_cost_usd=summary.total_cost_usd,
            avg_cost_per_task=summary.avg_cost_per_task,
            timestamp=datetime.now(),
        )

        return [result]

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve agent performance: {str(e)}"
        )


@router.get("/cost-breakdown", response_model=CostBreakdownResponse)
async def get_cost_breakdown(
    period: str = Query("day", pattern="^(hour|day|week)$")
) -> CostBreakdownResponse:
    """
    Get cost breakdown visualization by agent and model.

    Args:
        period: Time period for breakdown ("hour", "day", "week")

    Returns:
        Cost breakdown data with visualization points
    """
    try:
        analyzer = get_metrics_analyzer()

        # Calculate summary
        summary = analyzer.calculate_summary(period=period)

        # Build agent breakdown
        agent_breakdown = [
            CostBreakdownItem(
                name="aggregated",
                cost_usd=summary.total_cost_usd,
                percentage=100.0,
                token_count=summary.total_tokens,
                task_count=summary.total_tasks,
            )
        ]

        # Build model breakdown
        model_breakdown = []
        if summary.models_used:
            total_cost = summary.total_cost_usd if summary.total_cost_usd > 0 else 1
            for model_name, count in summary.models_used.items():
                cost_per_model = (
                    (total_cost / len(summary.models_used)) if summary.models_used else 0
                )
                model_breakdown.append(
                    CostBreakdownItem(
                        name=model_name,
                        cost_usd=cost_per_model,
                        percentage=(cost_per_model / total_cost * 100) if total_cost > 0 else 0,
                        token_count=(
                            summary.total_tokens // len(summary.models_used)
                            if summary.models_used
                            else 0
                        ),
                        task_count=count,
                    )
                )

        # Build token type breakdown (input vs output estimate)
        token_breakdown = []
        if summary.total_tokens > 0:
            # Assume 30% input, 70% output (typical LLM pattern)
            input_tokens = int(summary.total_tokens * 0.3)
            output_tokens = summary.total_tokens - input_tokens
            # Assume input tokens cost less than output (typical LLM pricing)
            input_cost = summary.total_cost_usd * 0.25
            output_cost = summary.total_cost_usd * 0.75

            token_breakdown = [
                CostBreakdownItem(
                    name="input_tokens",
                    cost_usd=input_cost,
                    percentage=25.0,
                    token_count=input_tokens,
                    task_count=summary.total_tasks,
                ),
                CostBreakdownItem(
                    name="output_tokens",
                    cost_usd=output_cost,
                    percentage=75.0,
                    token_count=output_tokens,
                    task_count=summary.total_tasks,
                ),
            ]

        return CostBreakdownResponse(
            total_cost_usd=summary.total_cost_usd,
            period=period,
            breakdown_by_agent=agent_breakdown,
            breakdown_by_model=model_breakdown,
            breakdown_by_type=token_breakdown,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve cost breakdown: {str(e)}")


@router.get("/success-trends", response_model=SuccessTrendsResponse)
async def get_success_trends(
    period: str = Query("day", pattern="^(hour|day|week)$"), days: int = Query(7, ge=1, le=90)
) -> SuccessTrendsResponse:
    """
    Get success rate trends over time.

    Args:
        period: Granularity of trend points ("hour", "day", "week")
        days: Number of days to include in trend

    Returns:
        Success trends data for chart visualization
    """
    try:
        analyzer = get_metrics_analyzer()

        # Get performance trends
        trends = analyzer.get_performance_trends(days=days, metric="duration_ms")

        # Build trend points
        now = datetime.now()
        points = []
        success_rates = []

        for i in range(days):
            day = now - timedelta(days=i)
            date_key = day.strftime("%Y-%m-%d")

            # Calculate metrics for this day
            day_start = day.replace(hour=0, minute=0, second=0)
            day_end = day.replace(hour=23, minute=59, second=59)

            daily_summary = analyzer.calculate_summary(
                period="day", start_time=day_start, end_time=day_end
            )

            success_rate = daily_summary.success_rate
            success_rates.append(success_rate)

            points.append(
                SuccessTrendPoint(
                    timestamp=date_key,
                    success_rate=success_rate,
                    total_tasks=daily_summary.total_tasks,
                    successful_tasks=daily_summary.successful_tasks,
                    failed_tasks=daily_summary.failed_tasks,
                )
            )

        # Reverse to chronological order (oldest first)
        points.reverse()

        # Calculate statistics
        avg_success_rate = sum(success_rates) / len(success_rates) if success_rates else 0.0
        min_success_rate = min(success_rates) if success_rates else 0.0
        max_success_rate = max(success_rates) if success_rates else 0.0

        start_date = (now - timedelta(days=days - 1)).strftime("%Y-%m-%d")
        end_date = now.strftime("%Y-%m-%d")

        return SuccessTrendsResponse(
            period=period,
            start_date=start_date,
            end_date=end_date,
            points=points,
            avg_success_rate=avg_success_rate,
            min_success_rate=min_success_rate,
            max_success_rate=max_success_rate,
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve success trends: {str(e)}")


@router.get("/historical-comparison", response_model=HistoricalComparisonResponse)
async def get_historical_comparison() -> HistoricalComparisonResponse:
    """
    Get historical performance comparisons across different time periods.

    Returns:
        Comparison data for current period vs previous periods
    """
    try:
        analyzer = get_metrics_analyzer()
        now = datetime.now()

        # Current period (last 24 hours)
        current_start = now - timedelta(hours=24)
        current_end = now
        current_summary = analyzer.calculate_summary(
            period="day", start_time=current_start, end_time=current_end
        )

        # Previous 24 hours
        prev_start = now - timedelta(days=2)
        prev_end = now - timedelta(days=1)
        prev_summary = analyzer.calculate_summary(
            period="day", start_time=prev_start, end_time=prev_end
        )

        # Week ago
        week_ago_start = now - timedelta(days=8)
        week_ago_end = now - timedelta(days=7)
        week_ago_summary = analyzer.calculate_summary(
            period="day", start_time=week_ago_start, end_time=week_ago_end
        )

        # Month ago
        month_ago_start = now - timedelta(days=31)
        month_ago_end = now - timedelta(days=30)
        month_ago_summary = analyzer.calculate_summary(
            period="day", start_time=month_ago_start, end_time=month_ago_end
        )

        # Calculate improvements (positive = better)
        success_rate_improvement = current_summary.success_rate - prev_summary.success_rate
        cost_improvement = prev_summary.avg_cost_per_task - current_summary.avg_cost_per_task

        return HistoricalComparisonResponse(
            current_period=HistoricalComparisonPeriod(
                period="current_24h",
                success_rate=current_summary.success_rate,
                cost_per_task=current_summary.avg_cost_per_task,
                total_tasks=current_summary.total_tasks,
                avg_duration_ms=current_summary.avg_duration_ms,
            ),
            previous_period=HistoricalComparisonPeriod(
                period="previous_24h",
                success_rate=prev_summary.success_rate,
                cost_per_task=prev_summary.avg_cost_per_task,
                total_tasks=prev_summary.total_tasks,
                avg_duration_ms=prev_summary.avg_duration_ms,
            ),
            week_ago=HistoricalComparisonPeriod(
                period="week_ago",
                success_rate=week_ago_summary.success_rate,
                cost_per_task=week_ago_summary.avg_cost_per_task,
                total_tasks=week_ago_summary.total_tasks,
                avg_duration_ms=week_ago_summary.avg_duration_ms,
            ),
            month_ago=HistoricalComparisonPeriod(
                period="month_ago",
                success_rate=month_ago_summary.success_rate,
                cost_per_task=month_ago_summary.avg_cost_per_task,
                total_tasks=month_ago_summary.total_tasks,
                avg_duration_ms=month_ago_summary.avg_duration_ms,
            ),
            improvements={
                "success_rate": round(success_rate_improvement, 2),
                "cost_per_task": round(cost_improvement, 4),
            },
            trends={
                "success_rate": "up" if success_rate_improvement >= 0 else "down",
                "cost_per_task": "down" if cost_improvement >= 0 else "up",
            },
        )

    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Failed to retrieve historical comparison: {str(e)}"
        )
