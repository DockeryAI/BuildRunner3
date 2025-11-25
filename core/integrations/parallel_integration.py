"""
Parallel Integration Module

Provides helper functions for integrating parallel execution into the orchestrator.
Handles session management, worker coordination, and parallel task distribution.
"""

from typing import Dict, Any, Optional, List, Tuple
from datetime import datetime
import uuid

from core.parallel import (
    SessionManager,
    Session,
    SessionStatus,
    WorkerCoordinator,
    Worker,
    WorkerStatus,
    LiveDashboard,
    DashboardConfig,
)


def integrate_parallel(
    orchestrator,
    max_concurrent_sessions: int = 4,
    enable_dashboard: bool = True,
) -> Dict[str, Any]:
    """
    Integrate parallel execution into an orchestrator instance.

    Args:
        orchestrator: The TaskOrchestrator instance
        max_concurrent_sessions: Maximum number of concurrent sessions (not currently used)
        enable_dashboard: Whether to enable live dashboard

    Returns:
        Dictionary with integrated components
    """
    session_manager = SessionManager()
    worker_coordinator = WorkerCoordinator()

    dashboard = None
    if enable_dashboard:
        dashboard_config = DashboardConfig(
            refresh_rate=0.5,
            show_workers=True,
            show_sessions=True,
            show_tasks=True,
            compact_mode=False,
            max_sessions_display=10,
            max_workers_display=20,
        )
        dashboard = LiveDashboard(
            session_manager=session_manager,
            worker_coordinator=worker_coordinator,
            config=dashboard_config,
        )

    orchestrator.session_manager = session_manager
    orchestrator.worker_coordinator = worker_coordinator
    orchestrator.dashboard = dashboard

    return {
        "session_manager": session_manager,
        "worker_coordinator": worker_coordinator,
        "dashboard": dashboard,
    }


def create_parallel_session(
    session_manager: SessionManager,
    session_name: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Session:
    """
    Create a new parallel execution session.

    Args:
        session_manager: SessionManager instance
        session_name: Optional name for the session
        metadata: Additional metadata

    Returns:
        Created Session instance
    """
    name = session_name or f"session_{str(uuid.uuid4())[:8]}"

    session = session_manager.create_session(
        name=name,
        total_tasks=0,
        metadata=metadata or {},
    )

    return session


def assign_task_to_worker(
    worker_coordinator: WorkerCoordinator,
    task_id: str,
    task_data: Dict[str, Any],
    session_id: str,
    worker_id: Optional[str] = None,
) -> Worker:
    """
    Assign a task to a worker.

    Args:
        worker_coordinator: WorkerCoordinator instance
        task_id: Unique task identifier
        task_data: Task data/payload
        session_id: Session identifier
        worker_id: Optional specific worker to assign to

    Returns:
        Worker instance handling the task
    """
    worker = worker_coordinator.assign_task(
        task_id=task_id,
        task_data=task_data,
        session_id=session_id,
        worker_id=worker_id,
    )

    return worker


def coordinate_parallel_execution(
    session_manager: SessionManager,
    worker_coordinator: WorkerCoordinator,
    tasks: List[Dict[str, Any]],
    session_name: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Coordinate parallel execution of multiple tasks.

    Creates a session and distributes tasks across available workers.

    Args:
        session_manager: SessionManager instance
        worker_coordinator: WorkerCoordinator instance
        tasks: List of task dictionaries
        session_name: Optional session name

    Returns:
        Dictionary with execution details
    """
    # Create session
    session = create_parallel_session(
        session_manager,
        session_name=session_name,
        metadata={"task_count": len(tasks)},
    )

    # Assign tasks to workers
    assigned_workers = []
    for task in tasks:
        task_id = task.get("id", str(uuid.uuid4()))
        worker = assign_task_to_worker(
            worker_coordinator,
            task_id=task_id,
            task_data=task,
            session_id=session.session_id,
        )
        assigned_workers.append(
            {
                "task_id": task_id,
                "worker_id": worker.worker_id,
                "worker_status": worker.status.value,
            }
        )

    return {
        "session_id": session.session_id,
        "session_name": session.name,
        "task_count": len(tasks),
        "workers": assigned_workers,
        "status": session.status.value,
    }


def get_session_status(
    session_manager: SessionManager,
    session_id: str,
) -> Dict[str, Any]:
    """
    Get status of a parallel session.

    Args:
        session_manager: SessionManager instance
        session_id: Session identifier

    Returns:
        Dictionary with session status
    """
    session = session_manager.get_session(session_id)

    if not session:
        return {
            "found": False,
            "session_id": session_id,
        }

    return {
        "found": True,
        "session_id": session.session_id,
        "name": session.name,
        "status": session.status.value,
        "created_at": session.created_at.isoformat() if hasattr(session, "created_at") else None,
        "metadata": session.metadata if hasattr(session, "metadata") else {},
    }


def get_worker_status(
    worker_coordinator: WorkerCoordinator,
    worker_id: str,
) -> Dict[str, Any]:
    """
    Get status of a worker.

    Args:
        worker_coordinator: WorkerCoordinator instance
        worker_id: Worker identifier

    Returns:
        Dictionary with worker status
    """
    worker = worker_coordinator.get_worker(worker_id)

    if not worker:
        return {
            "found": False,
            "worker_id": worker_id,
        }

    return {
        "found": True,
        "worker_id": worker.worker_id,
        "status": worker.status.value,
        "current_task": worker.current_task_id if hasattr(worker, "current_task_id") else None,
        "tasks_completed": worker.tasks_completed if hasattr(worker, "tasks_completed") else 0,
    }


def get_parallel_summary(
    session_manager: SessionManager,
    worker_coordinator: WorkerCoordinator,
) -> Dict[str, Any]:
    """
    Get summary of parallel execution state.

    Args:
        session_manager: SessionManager instance
        worker_coordinator: WorkerCoordinator instance

    Returns:
        Dictionary with parallel execution statistics
    """
    sessions = session_manager.get_active_sessions()
    workers = worker_coordinator.list_workers()

    active_sessions = [s for s in sessions if s.status == SessionStatus.ACTIVE]
    active_workers = [w for w in workers if w.status == WorkerStatus.BUSY]

    return {
        "total_sessions": len(sessions),
        "active_sessions": len(active_sessions),
        "total_workers": len(workers),
        "active_workers": len(active_workers),
        "idle_workers": len([w for w in workers if w.status == WorkerStatus.IDLE]),
        "sessions": [
            {
                "session_id": s.session_id,
                "name": s.name,
                "status": s.status.value,
            }
            for s in sessions
        ],
        "workers": [
            {
                "worker_id": w.worker_id,
                "status": w.status.value,
            }
            for w in workers
        ],
    }


def wait_for_session_completion(
    session_manager: SessionManager,
    session_id: str,
    timeout_seconds: Optional[int] = None,
) -> Tuple[bool, Dict[str, Any]]:
    """
    Wait for a session to complete.

    Args:
        session_manager: SessionManager instance
        session_id: Session identifier
        timeout_seconds: Optional timeout

    Returns:
        Tuple of (completed, status_dict)
    """
    import time

    start_time = time.time()

    while True:
        status = get_session_status(session_manager, session_id)

        if not status["found"]:
            return False, status

        if status["status"] in ["completed", "failed", "cancelled"]:
            return True, status

        if timeout_seconds and (time.time() - start_time) > timeout_seconds:
            return False, {**status, "timeout": True}

        time.sleep(1)


def cancel_session(
    session_manager: SessionManager,
    worker_coordinator: WorkerCoordinator,
    session_id: str,
) -> Dict[str, Any]:
    """
    Cancel a parallel session and stop all workers.

    Args:
        session_manager: SessionManager instance
        worker_coordinator: WorkerCoordinator instance
        session_id: Session identifier

    Returns:
        Dictionary with cancellation result
    """
    # Stop session
    session = session_manager.get_session(session_id)
    if not session:
        return {
            "success": False,
            "error": f"Session {session_id} not found",
        }

    session_manager.cancel_session(session_id)

    # Stop workers for this session
    workers = worker_coordinator.get_workers_for_session(session_id)
    stopped_workers = []

    for worker in workers:
        worker_coordinator.stop_worker(worker.worker_id)
        stopped_workers.append(worker.worker_id)

    return {
        "success": True,
        "session_id": session_id,
        "workers_stopped": len(stopped_workers),
    }
