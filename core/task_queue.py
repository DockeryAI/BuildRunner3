"""
Task Queue Manager

Manages execution queue for task orchestration. Handles task queuing,
dequeuing, status tracking, and completion management.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import List, Dict, Optional, Set
from datetime import datetime
from pathlib import Path


class TaskStatus(Enum):
    """Task execution status"""
    PENDING = "pending"
    READY = "ready"           # Dependencies met, ready to execute
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"       # Dependencies not met
    SKIPPED = "skipped"


@dataclass
class QueuedTask:
    """Represents a task in the execution queue"""
    id: str
    name: str
    description: str
    file_path: str
    estimated_minutes: int
    complexity: str
    domain: str
    dependencies: List[str] = field(default_factory=list)
    acceptance_criteria: List[str] = field(default_factory=list)
    status: TaskStatus = TaskStatus.PENDING
    queued_at: datetime = field(default_factory=datetime.now)
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    error_message: Optional[str] = None
    retry_count: int = 0

    def duration_minutes(self) -> Optional[int]:
        """Calculate actual duration in minutes"""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() / 60)
        return None


class TaskQueue:
    """
    Manages task execution queue.

    Responsibilities:
    - Queue tasks for execution
    - Track task status
    - Handle dependencies
    - Manage completion
    - Support retries
    """

    def __init__(self, max_retries: int = 3):
        self.tasks: Dict[str, QueuedTask] = {}
        self.execution_order: List[str] = []
        self.max_retries = max_retries

        # Statistics
        self.tasks_queued = 0
        self.tasks_completed = 0
        self.tasks_failed = 0

    def add_task(self, task: QueuedTask) -> bool:
        """
        Add task to queue.

        Args:
            task: QueuedTask to add

        Returns:
            True if added, False if already exists
        """
        if task.id in self.tasks:
            return False

        self.tasks[task.id] = task
        self.tasks_queued += 1

        # Update execution order if task is ready
        if self._is_ready(task):
            task.status = TaskStatus.READY
            if task.id not in self.execution_order:
                self.execution_order.append(task.id)

        return True

    def add_tasks(self, tasks: List[QueuedTask]) -> int:
        """
        Add multiple tasks to queue.

        Returns:
            Number of tasks added
        """
        added = 0
        for task in tasks:
            if self.add_task(task):
                added += 1
        return added

    def get_next_task(self) -> Optional[QueuedTask]:
        """
        Get next task ready for execution.

        Returns:
            Next ready task, or None if queue empty
        """
        # Update ready status for all pending tasks
        self._update_ready_tasks()

        # Find first ready task in execution order
        for task_id in self.execution_order:
            task = self.tasks.get(task_id)
            if task and task.status == TaskStatus.READY:
                return task

        return None

    def start_task(self, task_id: str) -> bool:
        """
        Mark task as started.

        Args:
            task_id: ID of task to start

        Returns:
            True if started, False if task not found or not ready
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        if task.status != TaskStatus.READY:
            return False

        task.status = TaskStatus.IN_PROGRESS
        task.started_at = datetime.now()
        return True

    def complete_task(self, task_id: str) -> bool:
        """
        Mark task as completed.

        Args:
            task_id: ID of task to complete

        Returns:
            True if completed, False if task not found
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.status = TaskStatus.COMPLETED
        task.completed_at = datetime.now()
        self.tasks_completed += 1

        # Update dependent tasks
        self._update_ready_tasks()

        return True

    def fail_task(self, task_id: str, error_message: str) -> bool:
        """
        Mark task as failed.

        Args:
            task_id: ID of task to fail
            error_message: Error description

        Returns:
            True if task should be retried, False if max retries exceeded
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.error_message = error_message
        task.retry_count += 1

        if task.retry_count < self.max_retries:
            # Retry - reset to ready
            task.status = TaskStatus.READY
            task.started_at = None
            return True
        else:
            # Max retries exceeded - only increment failed count once
            if task.status != TaskStatus.FAILED:
                self.tasks_failed += 1
            task.status = TaskStatus.FAILED
            return False

    def skip_task(self, task_id: str, reason: str) -> bool:
        """
        Skip a task.

        Args:
            task_id: ID of task to skip
            reason: Reason for skipping

        Returns:
            True if skipped, False if task not found
        """
        task = self.tasks.get(task_id)
        if not task:
            return False

        task.status = TaskStatus.SKIPPED
        task.error_message = f"Skipped: {reason}"
        return True

    def get_task(self, task_id: str) -> Optional[QueuedTask]:
        """Get task by ID"""
        return self.tasks.get(task_id)

    def get_tasks_by_status(self, status: TaskStatus) -> List[QueuedTask]:
        """Get all tasks with given status"""
        return [t for t in self.tasks.values() if t.status == status]

    def get_pending_tasks(self) -> List[QueuedTask]:
        """Get all pending tasks"""
        return self.get_tasks_by_status(TaskStatus.PENDING)

    def get_ready_tasks(self) -> List[QueuedTask]:
        """Get all ready tasks"""
        self._update_ready_tasks()
        return self.get_tasks_by_status(TaskStatus.READY)

    def get_completed_tasks(self) -> List[QueuedTask]:
        """Get all completed tasks"""
        return self.get_tasks_by_status(TaskStatus.COMPLETED)

    def get_failed_tasks(self) -> List[QueuedTask]:
        """Get all failed tasks"""
        return self.get_tasks_by_status(TaskStatus.FAILED)

    def is_complete(self) -> bool:
        """Check if all tasks are complete or failed"""
        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.READY, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]:
                return False
        return True

    def get_progress(self) -> Dict:
        """
        Get progress statistics.

        Returns:
            Dictionary with progress information
        """
        total = len(self.tasks)
        if total == 0:
            return {
                "total": 0,
                "completed": 0,
                "failed": 0,
                "in_progress": 0,
                "pending": 0,
                "blocked": 0,
                "skipped": 0,
                "percent_complete": 0,
            }

        completed = self.tasks_completed
        failed = self.tasks_failed
        in_progress = len(self.get_tasks_by_status(TaskStatus.IN_PROGRESS))
        pending = len(self.get_pending_tasks()) + len(self.get_ready_tasks())

        return {
            "total": total,
            "completed": completed,
            "failed": failed,
            "in_progress": in_progress,
            "pending": pending,
            "blocked": len(self.get_tasks_by_status(TaskStatus.BLOCKED)),
            "skipped": len(self.get_tasks_by_status(TaskStatus.SKIPPED)),
            "percent_complete": (completed / total) * 100,
        }

    def clear(self):
        """Clear all tasks from queue"""
        self.tasks = {}
        self.execution_order = []
        self.tasks_queued = 0
        self.tasks_completed = 0
        self.tasks_failed = 0

    def _is_ready(self, task: QueuedTask) -> bool:
        """Check if task is ready (all dependencies completed)"""
        if not task.dependencies:
            return True

        for dep_id in task.dependencies:
            dep_task = self.tasks.get(dep_id)
            if not dep_task or dep_task.status != TaskStatus.COMPLETED:
                return False

        return True

    def _update_ready_tasks(self):
        """Update ready status for all pending/blocked tasks"""
        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.BLOCKED]:
                if self._is_ready(task):
                    task.status = TaskStatus.READY
                    if task.id not in self.execution_order:
                        self.execution_order.append(task.id)
                else:
                    task.status = TaskStatus.BLOCKED

    def get_stats(self) -> Dict:
        """Get queue statistics"""
        return {
            "tasks_queued": self.tasks_queued,
            "tasks_completed": self.tasks_completed,
            "tasks_failed": self.tasks_failed,
            "current_queue_size": len(self.tasks),
            "max_retries": self.max_retries,
            **self.get_progress(),
        }

    def get_summary(self) -> str:
        """Get human-readable queue summary"""
        stats = self.get_stats()
        return (
            f"Task Queue Summary:\n"
            f"  Total: {stats['total']} tasks\n"
            f"  Completed: {stats['completed']} ({stats['percent_complete']:.1f}%)\n"
            f"  Failed: {stats['failed']}\n"
            f"  In Progress: {stats['in_progress']}\n"
            f"  Pending: {stats['pending']}\n"
            f"  Blocked: {stats['blocked']}\n"
        )

    def get_estimated_time_remaining(self) -> int:
        """
        Get estimated time remaining in minutes.

        Returns:
            Estimated minutes for all incomplete tasks
        """
        remaining_minutes = 0

        for task in self.tasks.values():
            if task.status in [TaskStatus.PENDING, TaskStatus.READY, TaskStatus.IN_PROGRESS, TaskStatus.BLOCKED]:
                remaining_minutes += task.estimated_minutes

        return remaining_minutes
