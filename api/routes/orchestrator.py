"""
Orchestrator API Routes

Provides endpoints for:
- Task status and progress
- Batch information
- Execution control (start, pause, resume, stop)
- Queue statistics
"""

from fastapi import APIRouter, HTTPException
from typing import Dict, List, Optional
from pydantic import BaseModel

# Import core modules
from core.orchestrator import TaskOrchestrator, OrchestrationStatus
from core.task_queue import TaskQueue, TaskStatus, QueuedTask

router = APIRouter()

# Global instances (in production, these would be dependency-injected)
_orchestrator: Optional[TaskOrchestrator] = None
_task_queue: Optional[TaskQueue] = None


def get_orchestrator() -> TaskOrchestrator:
    """Get or create orchestrator instance"""
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = TaskOrchestrator(
            enable_telemetry=True,
            enable_routing=True,
            enable_parallel=True,
        )
    return _orchestrator


def get_task_queue() -> TaskQueue:
    """Get or create task queue instance"""
    global _task_queue
    if _task_queue is None:
        _task_queue = TaskQueue()
    return _task_queue


# Response models
class TaskResponse(BaseModel):
    """Task information response"""

    id: str
    name: str
    description: str
    status: str
    domain: str
    complexity: str
    estimated_minutes: int
    dependencies: List[str]
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    error_message: Optional[str] = None
    retry_count: int


class ProgressResponse(BaseModel):
    """Progress information response"""

    total: int
    completed: int
    failed: int
    in_progress: int
    pending: int
    blocked: int
    skipped: int
    percent_complete: float


class StatusResponse(BaseModel):
    """Orchestration status response"""

    status: str
    current_batch: Optional[str]
    batches_executed: int
    tasks_completed: int
    execution_errors: int
    completed_batches: int
    failed_batches: int


@router.options("/status")
async def status_options():
    """Handle OPTIONS for CORS preflight"""
    return {}


@router.get("/status", response_model=StatusResponse)
async def get_status() -> StatusResponse:
    """
    Get current orchestration status.

    Returns:
        Current status of the orchestrator
    """
    orchestrator = get_orchestrator()
    status = orchestrator.get_status()
    return StatusResponse(**status)


@router.get("/progress", response_model=ProgressResponse)
async def get_progress() -> ProgressResponse:
    """
    Get task execution progress.

    Returns:
        Progress statistics
    """
    queue = get_task_queue()
    progress = queue.get_progress()
    return ProgressResponse(**progress)


@router.get("/tasks", response_model=List[TaskResponse])
async def get_tasks(status: Optional[str] = None) -> List[TaskResponse]:
    """
    Get all tasks, optionally filtered by status.

    Args:
        status: Optional status filter (pending, ready, in_progress, completed, failed)

    Returns:
        List of tasks
    """
    queue = get_task_queue()

    if status:
        try:
            task_status = TaskStatus(status)
            tasks = queue.get_tasks_by_status(task_status)
        except ValueError:
            raise HTTPException(status_code=400, detail=f"Invalid status: {status}")
    else:
        tasks = list(queue.tasks.values())

    return [
        TaskResponse(
            id=task.id,
            name=task.name,
            description=task.description,
            status=task.status.value,
            domain=task.domain,
            complexity=task.complexity,
            estimated_minutes=task.estimated_minutes,
            dependencies=task.dependencies,
            started_at=task.started_at.isoformat() if task.started_at else None,
            completed_at=task.completed_at.isoformat() if task.completed_at else None,
            error_message=task.error_message,
            retry_count=task.retry_count,
        )
        for task in tasks
    ]


@router.get("/tasks/{task_id}", response_model=TaskResponse)
async def get_task(task_id: str) -> TaskResponse:
    """
    Get specific task by ID.

    Args:
        task_id: Task identifier

    Returns:
        Task information
    """
    queue = get_task_queue()
    task = queue.get_task(task_id)

    if not task:
        raise HTTPException(status_code=404, detail=f"Task not found: {task_id}")

    return TaskResponse(
        id=task.id,
        name=task.name,
        description=task.description,
        status=task.status.value,
        domain=task.domain,
        complexity=task.complexity,
        estimated_minutes=task.estimated_minutes,
        dependencies=task.dependencies,
        started_at=task.started_at.isoformat() if task.started_at else None,
        completed_at=task.completed_at.isoformat() if task.completed_at else None,
        error_message=task.error_message,
        retry_count=task.retry_count,
    )


@router.post("/control/pause")
async def pause_orchestration() -> Dict:
    """
    Pause orchestration.

    Returns:
        Success status
    """
    orchestrator = get_orchestrator()
    orchestrator.pause()
    return {"success": True, "status": "paused"}


@router.post("/control/resume")
async def resume_orchestration() -> Dict:
    """
    Resume orchestration.

    Returns:
        Success status
    """
    orchestrator = get_orchestrator()
    orchestrator.resume()
    return {"success": True, "status": "running"}


@router.post("/control/stop")
async def stop_orchestration() -> Dict:
    """
    Stop orchestration.

    Returns:
        Success status
    """
    orchestrator = get_orchestrator()
    orchestrator.stop()
    return {"success": True, "status": "stopped"}


@router.get("/batches")
async def get_batches() -> Dict:
    """
    Get batch information.

    Returns:
        Completed and failed batches
    """
    orchestrator = get_orchestrator()
    return {
        "completed": [
            {"id": b.get("id") if isinstance(b, dict) else (b.id if hasattr(b, "id") else str(i))}
            for i, b in enumerate(orchestrator.completed_batches)
        ],
        "failed": [
            {"id": b.get("id") if isinstance(b, dict) else (b.id if hasattr(b, "id") else str(i))}
            for i, b in enumerate(orchestrator.failed_batches)
        ],
    }


@router.get("/stats")
async def get_stats() -> Dict:
    """
    Get comprehensive statistics.

    Returns:
        Combined orchestrator and queue statistics
    """
    orchestrator = get_orchestrator()
    queue = get_task_queue()

    return {
        "orchestrator": orchestrator.get_status(),
        "queue": queue.get_stats(),
        "integration": orchestrator.get_integration_status(),
    }
