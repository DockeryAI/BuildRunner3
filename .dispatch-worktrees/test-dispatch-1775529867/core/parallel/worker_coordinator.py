"""
Worker Coordinator - Coordinates task distribution across workers

Features:
- Task distribution and load balancing
- Worker health monitoring
- Task assignment and tracking
- Worker pool management
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Set
import uuid


class WorkerStatus(str, Enum):
    """Worker status."""

    IDLE = "idle"
    BUSY = "busy"
    OFFLINE = "offline"
    ERROR = "error"


@dataclass
class Worker:
    """Worker instance."""

    worker_id: str
    status: WorkerStatus
    current_session: Optional[str] = None  # Changed from session_id to current_session
    current_task: Optional[str] = None
    tasks_completed: int = 0
    tasks_failed: int = 0
    last_heartbeat: Optional[datetime] = None
    created_at: datetime = field(default_factory=datetime.now)
    metadata: Dict[str, any] = field(default_factory=dict)


class WorkerCoordinator:
    """Coordinates task distribution across workers."""

    # Worker heartbeat timeout (seconds)
    HEARTBEAT_TIMEOUT = 30

    def __init__(self, session_manager=None, max_workers: int = 3):
        """
        Initialize worker coordinator.

        Args:
            session_manager: SessionManager instance (optional)
            max_workers: Maximum number of concurrent workers
        """
        self.session_manager = session_manager
        self.max_workers = max_workers
        self.workers: Dict[str, Worker] = {}
        self.task_queue: List[Dict[str, any]] = []
        self.task_assignments: Dict[str, str] = {}  # task_id -> worker_id

    def register_worker(self, metadata: Optional[Dict[str, any]] = None) -> Worker:
        """
        Register a new worker.

        Args:
            metadata: Worker metadata

        Returns:
            Worker instance
        """
        worker = Worker(
            worker_id=str(uuid.uuid4()),
            status=WorkerStatus.IDLE,
            last_heartbeat=datetime.now(),
            metadata=metadata or {},
        )

        self.workers[worker.worker_id] = worker
        return worker

    def unregister_worker(self, worker_id: str):
        """
        Unregister a worker.

        Args:
            worker_id: Worker ID
        """
        if worker_id in self.workers:
            # Reassign any tasks
            worker = self.workers[worker_id]
            if worker.current_task:
                self._requeue_task(worker.current_task)

            del self.workers[worker_id]

    def get_worker(self, worker_id: str) -> Optional[Worker]:
        """Get worker by ID."""
        return self.workers.get(worker_id)

    def list_workers(self, status: Optional[WorkerStatus] = None) -> List[Worker]:
        """
        List workers.

        Args:
            status: Filter by status

        Returns:
            List of workers
        """
        workers = list(self.workers.values())

        if status:
            workers = [w for w in workers if w.status == status]

        return workers

    def assign_task(
        self,
        task_id: str,
        task_data: Dict[str, any],
        session_id: Optional[str] = None,
    ) -> Optional[str]:
        """
        Assign task to a worker.

        Args:
            task_id: Task ID
            task_data: Task data
            session_id: Session ID

        Returns:
            Worker ID if assigned, None if no workers available
        """
        # Find idle worker
        idle_workers = [w for w in self.workers.values() if w.status == WorkerStatus.IDLE]

        if not idle_workers:
            # Queue task for later
            self.task_queue.append(
                {
                    "task_id": task_id,
                    "task_data": task_data,
                    "session_id": session_id,
                }
            )
            return None

        # Assign to first idle worker
        worker = idle_workers[0]
        worker.status = WorkerStatus.BUSY
        worker.current_task = task_id
        worker.session_id = session_id

        self.task_assignments[task_id] = worker.worker_id

        return worker.worker_id

    def complete_task(
        self,
        worker_id: str,
        task_id: str,
        success: bool = True,
    ):
        """
        Mark task as completed.

        Args:
            worker_id: Worker ID
            task_id: Task ID
            success: Whether task succeeded
        """
        worker = self.get_worker(worker_id)
        if not worker:
            return

        if success:
            worker.tasks_completed += 1
        else:
            worker.tasks_failed += 1

        worker.status = WorkerStatus.IDLE
        worker.current_task = None
        worker.session_id = None

        # Remove from assignments
        if task_id in self.task_assignments:
            del self.task_assignments[task_id]

        # Assign next queued task
        self._assign_next_queued_task(worker_id)

    def heartbeat(self, worker_id: str):
        """
        Update worker heartbeat.

        Args:
            worker_id: Worker ID
        """
        worker = self.get_worker(worker_id)
        if worker:
            worker.last_heartbeat = datetime.now()

            # If worker was offline, mark as idle
            if worker.status == WorkerStatus.OFFLINE:
                worker.status = WorkerStatus.IDLE

    def check_worker_health(self):
        """Check worker health and mark offline workers."""
        now = datetime.now()
        timeout = timedelta(seconds=self.HEARTBEAT_TIMEOUT)

        for worker in self.workers.values():
            if worker.last_heartbeat is None:
                continue

            if now - worker.last_heartbeat > timeout:
                # Worker is offline
                if worker.status != WorkerStatus.OFFLINE:
                    worker.status = WorkerStatus.OFFLINE

                    # Requeue any assigned task
                    if worker.current_task:
                        self._requeue_task(worker.current_task)
                        worker.current_task = None

    def get_load_distribution(self) -> Dict[str, any]:
        """
        Get current load distribution across workers.

        Returns:
            Distribution statistics
        """
        total_workers = len(self.workers)
        idle_workers = sum(1 for w in self.workers.values() if w.status == WorkerStatus.IDLE)
        busy_workers = sum(1 for w in self.workers.values() if w.status == WorkerStatus.BUSY)
        offline_workers = sum(1 for w in self.workers.values() if w.status == WorkerStatus.OFFLINE)

        total_completed = sum(w.tasks_completed for w in self.workers.values())
        total_failed = sum(w.tasks_failed for w in self.workers.values())

        return {
            "total_workers": total_workers,
            "idle_workers": idle_workers,
            "busy_workers": busy_workers,
            "offline_workers": offline_workers,
            "queued_tasks": len(self.task_queue),
            "total_completed": total_completed,
            "total_failed": total_failed,
            "utilization": (busy_workers / total_workers * 100) if total_workers > 0 else 0,
        }

    def scale_workers(self, target_count: int):
        """
        Scale worker pool to target count.

        Args:
            target_count: Target number of workers
        """
        current_count = len(self.workers)

        if target_count > current_count:
            # Add workers
            for _ in range(target_count - current_count):
                if len(self.workers) >= self.max_workers:
                    break
                self.register_worker()

        elif target_count < current_count:
            # Remove idle workers
            idle_workers = [w for w in self.workers.values() if w.status == WorkerStatus.IDLE]
            to_remove = current_count - target_count

            for worker in idle_workers[:to_remove]:
                self.unregister_worker(worker.worker_id)

    def _assign_next_queued_task(self, worker_id: str):
        """Assign next queued task to worker."""
        if not self.task_queue:
            return

        worker = self.get_worker(worker_id)
        if not worker or worker.status != WorkerStatus.IDLE:
            return

        # Get next task
        task = self.task_queue.pop(0)

        # Assign to worker
        worker.status = WorkerStatus.BUSY
        worker.current_task = task["task_id"]
        worker.current_session = task.get("session_id")

        self.task_assignments[task["task_id"]] = worker.worker_id

    def _requeue_task(self, task_id: str):
        """Requeue a task that was assigned to a failed worker."""
        # Find task in assignments
        if task_id not in self.task_assignments:
            return

        # Remove from assignments
        del self.task_assignments[task_id]

        # Add back to queue (we don't have the task data, so this is a placeholder)
        # In a real implementation, we'd need to store task data
        self.task_queue.append(
            {
                "task_id": task_id,
                "task_data": {},
                "session_id": None,
            }
        )

    def get_statistics(self) -> Dict[str, any]:
        """
        Get coordinator statistics.

        Returns:
            Statistics dictionary
        """
        distribution = self.get_load_distribution()

        # Per-worker stats
        worker_stats = []
        for worker in self.workers.values():
            worker_stats.append(
                {
                    "worker_id": worker.worker_id,
                    "status": worker.status.value,
                    "tasks_completed": worker.tasks_completed,
                    "tasks_failed": worker.tasks_failed,
                    "current_task": worker.current_task,
                }
            )

        return {
            "distribution": distribution,
            "workers": worker_stats,
        }

    def get_all_workers(self) -> List[Worker]:
        """
        Get all workers.

        Returns:
            List of all Worker instances
        """
        return list(self.workers.values())

    def get_stats(self) -> Dict[str, any]:
        """
        Get worker statistics.

        Returns:
            Statistics dictionary
        """
        return self.get_statistics()
