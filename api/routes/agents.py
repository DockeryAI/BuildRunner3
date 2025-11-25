"""
Agents API Routes

Provides endpoints for:
- Agent pool status and metrics
- Active agents and their work
- Session management
- Worker coordination
"""

from fastapi import APIRouter, HTTPException, Query
from typing import Dict, List, Optional
from pydantic import BaseModel
from datetime import datetime

# Import parallel execution modules
from core.parallel import SessionManager, WorkerCoordinator, LiveDashboard

# Import health and load balancing modules
from core.agents.health import AgentHealthMonitor, HealthStatus
from core.agents.load_balancer import (
    AgentLoadBalancer,
    LoadBalancingStrategy,
    LoadBalancingRequest,
)

router = APIRouter()

# Global instances
_session_manager: Optional[SessionManager] = None
_worker_coordinator: Optional[WorkerCoordinator] = None
_dashboard: Optional[LiveDashboard] = None
_health_monitor: Optional[AgentHealthMonitor] = None
_load_balancer: Optional[AgentLoadBalancer] = None


def get_session_manager() -> SessionManager:
    """Get or create session manager instance"""
    global _session_manager
    if _session_manager is None:
        _session_manager = SessionManager(max_concurrent_sessions=4)
    return _session_manager


def get_worker_coordinator() -> WorkerCoordinator:
    """Get or create worker coordinator instance"""
    global _worker_coordinator
    if _worker_coordinator is None:
        session_manager = get_session_manager()
        _worker_coordinator = WorkerCoordinator(session_manager=session_manager)
    return _worker_coordinator


def get_dashboard_instance() -> LiveDashboard:
    """Get or create live dashboard instance"""
    global _dashboard
    if _dashboard is None:
        session_manager = get_session_manager()
        _dashboard = LiveDashboard(session_manager=session_manager)
    return _dashboard


def get_health_monitor(agent_ids: Optional[List[str]] = None) -> AgentHealthMonitor:
    """Get or create health monitor instance"""
    global _health_monitor
    if _health_monitor is None:
        default_agents = agent_ids or ["agent-1", "agent-2", "agent-3"]
        _health_monitor = AgentHealthMonitor(default_agents)
    return _health_monitor


def get_load_balancer(agent_ids: Optional[List[str]] = None) -> AgentLoadBalancer:
    """Get or create load balancer instance"""
    global _load_balancer
    if _load_balancer is None:
        default_agents = agent_ids or ["agent-1", "agent-2", "agent-3"]
        health_monitor = get_health_monitor(default_agents)
        _load_balancer = AgentLoadBalancer(default_agents, health_monitor)
    return _load_balancer


# Response models
class SessionResponse(BaseModel):
    """Session information response"""

    session_id: str
    name: str
    status: str
    created_at: str
    started_at: Optional[str]
    completed_at: Optional[str]
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    in_progress_tasks: int
    worker_id: Optional[str]
    progress_percent: float


class WorkerResponse(BaseModel):
    """Worker information response"""

    worker_id: str
    status: str
    current_session: Optional[str]
    tasks_completed: int
    tasks_failed: int
    uptime_seconds: float


class AgentPoolResponse(BaseModel):
    """Agent pool status response"""

    total_sessions: int
    active_sessions: int
    paused_sessions: int
    completed_sessions: int
    failed_sessions: int
    max_concurrent: int
    available_slots: int


class AgentHealthResponse(BaseModel):
    """Agent health information"""

    agent_id: str
    status: str
    response_time_ms: float
    cpu_percent: float
    memory_percent: float
    memory_mb: float
    disk_percent: float
    last_successful_check: Optional[datetime]
    consecutive_failures: int


class HealthSummaryResponse(BaseModel):
    """Health summary for agent pool"""

    total_agents: int
    healthy: int
    degraded: int
    failing: int
    offline: int
    healthy_agents: List[str]
    failing_agents: List[str]
    offline_agents: List[str]
    timestamp: datetime


class AgentLoadResponse(BaseModel):
    """Agent load information"""

    agent_id: str
    current_connections: int
    available_connections: int
    capacity_percentage: float
    max_connections: int
    weight: float
    available: bool
    last_assigned: Optional[datetime]


class LoadBalancingAssignmentResponse(BaseModel):
    """Load balancing assignment result"""

    request_id: str
    assigned_agent_id: str
    strategy_used: str
    confidence_score: float
    alternative_agents: List[str]
    reason: str
    timestamp: datetime


@router.get("/pool", response_model=AgentPoolResponse)
async def get_agent_pool() -> AgentPoolResponse:
    """
    Get agent pool status.

    Returns:
        Agent pool statistics
    """
    session_manager = get_session_manager()
    stats = session_manager.get_stats()

    return AgentPoolResponse(
        total_sessions=stats["total_sessions"],
        active_sessions=stats["active_sessions"],
        paused_sessions=stats.get("paused_sessions", 0),
        completed_sessions=stats["completed_sessions"],
        failed_sessions=stats["failed_sessions"],
        max_concurrent=session_manager.max_concurrent_sessions,
        available_slots=session_manager.max_concurrent_sessions - stats["active_sessions"],
    )


@router.get("/sessions", response_model=List[SessionResponse])
async def get_sessions(status: Optional[str] = None) -> List[SessionResponse]:
    """
    Get all sessions, optionally filtered by status.

    Args:
        status: Optional status filter (running, completed, failed, etc.)

    Returns:
        List of sessions
    """
    session_manager = get_session_manager()

    if status:
        sessions = session_manager.get_sessions_by_status(status)
    else:
        sessions = session_manager.get_all_sessions()

    return [
        SessionResponse(
            session_id=session.session_id,
            name=session.name,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            started_at=session.started_at.isoformat() if session.started_at else None,
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            total_tasks=session.total_tasks,
            completed_tasks=session.completed_tasks,
            failed_tasks=session.failed_tasks,
            in_progress_tasks=session.in_progress_tasks,
            worker_id=session.worker_id,
            progress_percent=session.progress_percent,
        )
        for session in sessions
    ]


@router.get("/sessions/{session_id}", response_model=SessionResponse)
async def get_session(session_id: str) -> SessionResponse:
    """
    Get specific session by ID.

    Args:
        session_id: Session identifier

    Returns:
        Session information
    """
    session_manager = get_session_manager()
    session = session_manager.get_session(session_id)

    if not session:
        raise HTTPException(status_code=404, detail=f"Session not found: {session_id}")

    return SessionResponse(
        session_id=session.session_id,
        name=session.name,
        status=session.status.value,
        created_at=session.created_at.isoformat(),
        started_at=session.started_at.isoformat() if session.started_at else None,
        completed_at=session.completed_at.isoformat() if session.completed_at else None,
        total_tasks=session.total_tasks,
        completed_tasks=session.completed_tasks,
        failed_tasks=session.failed_tasks,
        in_progress_tasks=session.in_progress_tasks,
        worker_id=session.worker_id,
        progress_percent=session.progress_percent,
    )


@router.get("/active", response_model=List[SessionResponse])
async def get_active_sessions() -> List[SessionResponse]:
    """
    Get all active sessions.

    Returns:
        List of active sessions
    """
    session_manager = get_session_manager()
    sessions = session_manager.get_active_sessions()

    return [
        SessionResponse(
            session_id=session.session_id,
            name=session.name,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
            started_at=session.started_at.isoformat() if session.started_at else None,
            completed_at=session.completed_at.isoformat() if session.completed_at else None,
            total_tasks=session.total_tasks,
            completed_tasks=session.completed_tasks,
            failed_tasks=session.failed_tasks,
            in_progress_tasks=session.in_progress_tasks,
            worker_id=session.worker_id,
            progress_percent=session.progress_percent,
        )
        for session in sessions
    ]


@router.get("/workers", response_model=List[WorkerResponse])
async def get_workers() -> List[WorkerResponse]:
    """
    Get all workers and their status.

    Returns:
        List of workers
    """
    coordinator = get_worker_coordinator()
    workers = coordinator.get_all_workers()

    return [
        WorkerResponse(
            worker_id=worker.worker_id,
            status=worker.status.value,
            current_session=worker.current_session,
            tasks_completed=worker.tasks_completed,
            tasks_failed=worker.tasks_failed,
            uptime_seconds=(
                (worker.last_heartbeat - worker.created_at).total_seconds()
                if worker.last_heartbeat
                else 0.0
            ),
        )
        for worker in workers
    ]


@router.get("/dashboard")
async def get_dashboard() -> Dict:
    """
    Get live dashboard data.

    Returns:
        Dashboard statistics and visualizations
    """
    dashboard = get_dashboard_instance()
    data = dashboard.get_dashboard_data()

    return {
        "sessions": data.get("sessions", []),
        "workers": data.get("workers", []),
        "stats": data.get("stats", {}),
        "timeline": data.get("timeline", []),
    }


@router.get("/metrics")
async def get_agent_metrics() -> Dict:
    """
    Get agent pool metrics.

    Returns:
        Comprehensive agent metrics
    """
    session_manager = get_session_manager()
    coordinator = get_worker_coordinator()

    session_stats = session_manager.get_stats()
    worker_stats = coordinator.get_stats()

    return {
        "sessions": session_stats,
        "workers": worker_stats,
        "utilization": {
            "session_utilization": (
                session_stats["active_sessions"] / session_manager.max_concurrent_sessions
                if session_manager.max_concurrent_sessions > 0
                else 0
            ),
            "total_capacity": session_manager.max_concurrent_sessions,
            "available_capacity": session_manager.max_concurrent_sessions
            - session_stats["active_sessions"],
        },
    }


# ============================================================================
# Health Monitoring Endpoints (Feature 6)
# ============================================================================


@router.get("/health", response_model=HealthSummaryResponse)
async def get_agent_health_summary():
    """Get health summary for all agents"""
    health_monitor = get_health_monitor()
    summary = health_monitor.get_summary()

    return HealthSummaryResponse(
        total_agents=summary["total_agents"],
        healthy=summary["healthy"],
        degraded=summary["degraded"],
        failing=summary["failing"],
        offline=summary["offline"],
        healthy_agents=summary["healthy_agents"],
        failing_agents=summary["failing_agents"],
        offline_agents=summary["offline_agents"],
        timestamp=datetime.now(),
    )


@router.get("/health/{agent_id}", response_model=AgentHealthResponse)
async def get_agent_health(agent_id: str):
    """Get health status of specific agent"""
    health_monitor = get_health_monitor()
    result = health_monitor.get_health_status(agent_id)

    if not result:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentHealthResponse(
        agent_id=result.agent_id,
        status=result.status.value,
        response_time_ms=result.response_time_ms,
        cpu_percent=result.cpu_percent,
        memory_percent=result.memory_percent,
        memory_mb=result.memory_mb,
        disk_percent=result.disk_percent,
        last_successful_check=result.last_successful_check,
        consecutive_failures=result.consecutive_failures,
    )


@router.post("/health/check/{agent_id}")
async def trigger_agent_health_check(agent_id: str):
    """Trigger immediate health check for agent"""
    health_monitor = get_health_monitor()
    result = await health_monitor.check_agent(agent_id)
    return result.to_dict()


@router.get("/health/{agent_id}/history")
async def get_agent_health_history(agent_id: str, limit: int = Query(50, ge=1, le=200)):
    """Get health history for agent"""
    health_monitor = get_health_monitor()
    return {"history": health_monitor.get_history(agent_id, limit)}


@router.get("/failover/candidates")
async def get_failover_candidates():
    """Get agents that need failover"""
    health_monitor = get_health_monitor()
    load_balancer = get_load_balancer()

    candidates = health_monitor.detect_failover_candidates()
    recommendations = []

    for agent_id in candidates:
        health = health_monitor.get_health_status(agent_id)
        alternatives = [a for a in health_monitor.get_healthy_agents() if a != agent_id]

        reason = "Unknown"
        if health:
            if health.status == HealthStatus.FAILING:
                reason = "Agent health check failing"
            elif health.consecutive_failures > 3:
                reason = f"Too many consecutive failures"

        recommendations.append(
            {
                "agent_id": agent_id,
                "reason": reason,
                "recommended_action": "failover",
                "alternative_agents": alternatives[:3],
            }
        )

    return recommendations


@router.post("/failover/{agent_id}")
async def trigger_failover(agent_id: str):
    """Trigger failover for specific agent"""
    load_balancer = get_load_balancer()
    health_monitor = get_health_monitor()

    # Disable agent
    load_balancer.set_agent_available(agent_id, False)

    # Get alternatives
    alternatives = health_monitor.get_healthy_agents()

    return {
        "status": "failover_initiated",
        "agent_id": agent_id,
        "alternative_agents": alternatives,
        "timestamp": datetime.now().isoformat(),
    }


# ============================================================================
# Load Balancing Endpoints (Feature 6)
# ============================================================================


@router.get("/load")
async def get_agent_load_summary():
    """Get load summary for all agents"""
    load_balancer = get_load_balancer()
    return load_balancer.get_load_summary()


@router.get("/load/{agent_id}", response_model=AgentLoadResponse)
async def get_agent_load(agent_id: str):
    """Get load information for specific agent"""
    load_balancer = get_load_balancer()
    load_info = load_balancer.get_agent_load(agent_id)

    if not load_info:
        raise HTTPException(status_code=404, detail="Agent not found")

    return AgentLoadResponse(
        agent_id=load_info["agent_id"],
        current_connections=load_info["current_connections"],
        available_connections=load_info["available_connections"],
        capacity_percentage=load_info["capacity_percentage"],
        max_connections=load_info["max_connections"],
        weight=load_info["weight"],
        available=load_info["available"],
        last_assigned=load_info.get("last_assigned"),
    )


@router.post("/assign")
async def assign_request(
    task_type: str, priority: int = 0, affinity_agent_id: Optional[str] = None
):
    """Assign request to best available agent"""
    import uuid

    load_balancer = get_load_balancer()

    request_id = str(uuid.uuid4())
    request = LoadBalancingRequest(
        request_id=request_id,
        task_type=task_type,
        priority=priority,
        affinity_agent_id=affinity_agent_id,
    )

    decision = await load_balancer.assign_request(request)

    return LoadBalancingAssignmentResponse(
        request_id=decision.request_id,
        assigned_agent_id=decision.assigned_agent_id,
        strategy_used=decision.strategy_used.value,
        confidence_score=decision.confidence_score,
        alternative_agents=decision.alternative_agents,
        reason=decision.reason,
        timestamp=decision.timestamp,
    )


@router.post("/release/{request_id}")
async def release_request(request_id: str):
    """Release request and free agent capacity"""
    load_balancer = get_load_balancer()
    success = await load_balancer.release_request(request_id)

    if not success:
        raise HTTPException(status_code=404, detail="Request not found")

    return {"status": "released", "request_id": request_id}


@router.get("/strategy")
async def get_balancing_strategy():
    """Get current load balancing strategy"""
    load_balancer = get_load_balancer()
    return {"strategy": load_balancer.current_strategy.value}


@router.post("/strategy/{strategy_name}")
async def set_balancing_strategy(strategy_name: str):
    """Set load balancing strategy"""
    load_balancer = get_load_balancer()

    try:
        strategy = LoadBalancingStrategy(strategy_name)
        load_balancer.set_strategy(strategy)
        return {"status": "updated", "strategy": strategy_name}
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Unknown strategy: {strategy_name}")
