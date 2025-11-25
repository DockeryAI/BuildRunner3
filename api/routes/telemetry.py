"""
Telemetry API Routes

Provides endpoints for:
- Telemetry events and timeline
- Event querying and filtering
- Metrics and statistics
- Performance tracking
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime
from pathlib import Path

# Import telemetry modules
from core.telemetry import (
    EventCollector,
    EventFilter,
    EventType,
    MetricsAnalyzer,
    PerformanceTracker,
)

router = APIRouter()

# Global instances
_event_collector: Optional[EventCollector] = None
_metrics_analyzer: Optional[MetricsAnalyzer] = None
_performance_tracker: Optional[PerformanceTracker] = None


def get_event_collector() -> EventCollector:
    """Get or create event collector instance"""
    global _event_collector
    if _event_collector is None:
        storage_path = Path.cwd() / ".buildrunner" / "events.json"
        db_path = Path.cwd() / ".buildrunner" / "telemetry.db"
        _event_collector = EventCollector(
            storage_path=storage_path,
            db_path=db_path,
            use_sqlite=True,
        )
    return _event_collector


def get_metrics_analyzer() -> MetricsAnalyzer:
    """Get or create metrics analyzer instance"""
    global _metrics_analyzer
    if _metrics_analyzer is None:
        collector = get_event_collector()
        _metrics_analyzer = MetricsAnalyzer(event_collector=collector)
    return _metrics_analyzer


def get_performance_tracker() -> PerformanceTracker:
    """Get or create performance tracker instance"""
    global _performance_tracker
    if _performance_tracker is None:
        storage_path = Path.cwd() / ".buildrunner" / "performance.json"
        _performance_tracker = PerformanceTracker(storage_path=storage_path)
    return _performance_tracker


# Response models
class EventResponse(BaseModel):
    """Event response model"""

    event_id: str
    event_type: str
    timestamp: str
    session_id: str
    metadata: Dict


class TimelineResponse(BaseModel):
    """Timeline response model"""

    events: List[EventResponse]
    total: int
    start_time: Optional[str]
    end_time: Optional[str]


class StatisticsResponse(BaseModel):
    """Statistics response model"""

    total_events: int
    events_by_type: Dict[str, int]
    oldest_event: Optional[str]
    newest_event: Optional[str]


@router.get("/events", response_model=List[EventResponse])
async def get_events(
    event_type: Optional[str] = None,
    session_id: Optional[str] = None,
    limit: int = Query(default=100, le=1000),
) -> List[EventResponse]:
    """
    Get telemetry events with optional filtering.

    Args:
        event_type: Filter by event type
        session_id: Filter by session ID
        limit: Maximum number of events to return

    Returns:
        List of events
    """
    collector = get_event_collector()

    # Build filter
    filter = EventFilter()
    if event_type:
        try:
            filter.event_types = [EventType(event_type)]
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")

    if session_id:
        filter.session_id = session_id

    # Query events
    events = collector.query(filter=filter, limit=limit)

    # Convert to response
    return [
        EventResponse(
            event_id=event.event_id,
            event_type=event.event_type.value,
            timestamp=event.timestamp.isoformat(),
            session_id=event.session_id or "",
            metadata=event.metadata or {},
        )
        for event in events
    ]


@router.get("/events/recent", response_model=List[EventResponse])
async def get_recent_events(count: int = Query(default=50, le=500)) -> List[EventResponse]:
    """
    Get most recent telemetry events.

    Args:
        count: Number of recent events to return

    Returns:
        List of recent events
    """
    collector = get_event_collector()
    events = collector.get_recent(count=count)

    return [
        EventResponse(
            event_id=event.event_id,
            event_type=event.event_type.value,
            timestamp=event.timestamp.isoformat(),
            session_id=event.session_id or "",
            metadata=event.metadata or {},
        )
        for event in events
    ]


@router.get("/timeline", response_model=TimelineResponse)
async def get_timeline(
    start_time: Optional[str] = None,
    end_time: Optional[str] = None,
    event_types: Optional[str] = None,
    limit: int = Query(default=200, le=1000),
) -> TimelineResponse:
    """
    Get telemetry timeline with time-based filtering.

    Args:
        start_time: Start time in ISO format
        end_time: End time in ISO format
        event_types: Comma-separated list of event types
        limit: Maximum number of events

    Returns:
        Timeline with events
    """
    collector = get_event_collector()

    # Build filter
    filter = EventFilter()

    if start_time:
        try:
            filter.start_time = datetime.fromisoformat(start_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid start_time format")

    if end_time:
        try:
            filter.end_time = datetime.fromisoformat(end_time)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid end_time format")

    if event_types:
        try:
            filter.event_types = [EventType(et.strip()) for et in event_types.split(",")]
        except ValueError as e:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {e}")

    # Query events
    events = collector.query(filter=filter, limit=limit)

    # Convert to response
    event_responses = [
        EventResponse(
            event_id=event.event_id,
            event_type=event.event_type.value,
            timestamp=event.timestamp.isoformat(),
            session_id=event.session_id or "",
            metadata=event.metadata or {},
        )
        for event in events
    ]

    return TimelineResponse(
        events=event_responses,
        total=len(event_responses),
        start_time=filter.start_time.isoformat() if filter.start_time else None,
        end_time=filter.end_time.isoformat() if filter.end_time else None,
    )


@router.get("/statistics", response_model=StatisticsResponse)
async def get_statistics() -> StatisticsResponse:
    """
    Get telemetry statistics.

    Returns:
        Statistics about collected events
    """
    collector = get_event_collector()
    stats = collector.get_statistics()

    return StatisticsResponse(
        total_events=stats["total_events"],
        events_by_type=stats["events_by_type"],
        oldest_event=stats.get("oldest_event"),
        newest_event=stats.get("newest_event"),
    )


@router.get("/metrics")
async def get_metrics() -> Dict:
    """
    Get aggregated metrics.

    Returns:
        Metrics summary
    """
    analyzer = get_metrics_analyzer()
    summary = analyzer.calculate_summary(period="all")

    # Calculate time range in hours
    time_range = summary.end_time - summary.start_time
    time_range_hours = time_range.total_seconds() / 3600 if time_range.total_seconds() > 0 else 0

    return {
        "total_events": summary.total_tasks,
        "time_range_hours": time_range_hours,
        "avg_task_duration_ms": summary.avg_duration_ms,
        "success_rate": summary.success_rate,
        "total_cost_usd": summary.total_cost_usd,
        "total_tokens": summary.total_tokens,
        "events_per_hour": summary.total_tasks / time_range_hours if time_range_hours > 0 else 0,
        "peak_hour": None,  # Not tracked in MetricsSummary
    }


@router.get("/performance")
async def get_performance() -> Dict:
    """
    Get performance metrics.

    Returns:
        Performance tracking data
    """
    tracker = get_performance_tracker()
    metrics = tracker.get_current_metrics()

    return {
        "cpu_percent": metrics.cpu_percent,
        "memory_mb": metrics.memory_mb,
        "active_operations": metrics.active_operations,
        "total_operations": metrics.total_operations,
        "avg_operation_time_ms": metrics.avg_operation_time_ms,
    }


@router.get("/events/count")
async def get_event_count(
    event_type: Optional[str] = None,
    since_hours: Optional[int] = None,
) -> Dict:
    """
    Get count of events.

    Args:
        event_type: Filter by event type
        since_hours: Count events from last N hours

    Returns:
        Event count
    """
    collector = get_event_collector()

    # Build parameters
    event_type_enum = None
    if event_type:
        try:
            event_type_enum = EventType(event_type)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid event type: {event_type}")

    since = None
    if since_hours:
        from datetime import timedelta

        since = datetime.now() - timedelta(hours=since_hours)

    count = collector.get_count(event_type=event_type_enum, since=since)

    return {
        "count": count,
        "event_type": event_type,
        "since_hours": since_hours,
    }
