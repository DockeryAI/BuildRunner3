"""
Build Orchestrator - Enhanced orchestration with DAG, checkpoints, and parallel execution

Provides:
- Dependency graph analysis
- Parallel build coordination
- Checkpoint/rollback system
- Smart interruption gates
- Build state management
"""

from pathlib import Path
from typing import Dict, List, Optional, Set, Any
from dataclasses import dataclass, field
from enum import Enum

from core.dependency_graph import DependencyGraph
from core.checkpoint_manager import CheckpointManager
from core.task_queue import TaskQueue, TaskStatus, QueuedTask


class BuildPhase(Enum):
    """Build phase states"""

    NOT_STARTED = "not_started"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    CHECKPOINTED = "checkpointed"


@dataclass
class BuildState:
    """Current build state"""

    phase: str
    status: BuildPhase
    tasks_completed: List[str] = field(default_factory=list)
    tasks_in_progress: List[str] = field(default_factory=list)
    tasks_pending: List[str] = field(default_factory=list)
    files_created: List[str] = field(default_factory=list)
    checkpoint_id: Optional[str] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class BuildOrchestrator:
    """
    Enhanced build orchestrator with advanced features.

    Features:
    - Dependency graph analysis
    - Parallel execution identification
    - Checkpoint/rollback system
    - Smart interruption gates (pause for user input)
    - Build state tracking
    - Resume from checkpoints
    """

    def __init__(self, project_root: Path, task_queue: TaskQueue, auto_checkpoint: bool = True):
        """
        Initialize BuildOrchestrator.

        Args:
            project_root: Project root directory
            task_queue: Task queue to orchestrate
            auto_checkpoint: Automatically checkpoint after each phase
        """
        self.project_root = Path(project_root)
        self.task_queue = task_queue
        self.auto_checkpoint = auto_checkpoint

        # Initialize managers
        self.checkpoint_manager = CheckpointManager(project_root)
        self.dependency_graph = DependencyGraph()

        # Build state
        self.current_state: Optional[BuildState] = None
        self.interruption_gates: Set[str] = set()

    def analyze_dependencies(self) -> Dict[str, Any]:
        """
        Analyze task dependencies and build execution plan.

        Returns:
            Dict with:
                - execution_levels: List of task groups that can run in parallel
                - critical_path: Longest dependency chain
                - total_levels: Number of sequential levels
                - parallelizable_tasks: Tasks that can run in parallel
        """
        # Build dependency graph from task queue
        tasks_dict = []
        for task in self.task_queue.tasks.values():
            tasks_dict.append(
                {
                    "id": task.id,
                    "dependencies": task.dependencies,
                    "estimated_minutes": task.estimated_minutes,
                }
            )

        self.dependency_graph.build_graph(tasks_dict)

        # Get execution levels
        levels = self.dependency_graph.get_execution_levels()

        # Identify parallelizable tasks (tasks in same level)
        parallelizable = []
        for level in levels:
            if len(level.tasks) > 1:
                parallelizable.append(
                    {"level": level.level, "tasks": level.tasks, "count": len(level.tasks)}
                )

        # Calculate critical path (longest path through graph)
        critical_path = self._calculate_critical_path()

        return {
            "execution_levels": levels,
            "total_levels": len(levels),
            "parallelizable_tasks": parallelizable,
            "critical_path": critical_path,
            "critical_path_duration": sum(
                self.task_queue.tasks[tid].estimated_minutes
                for tid in critical_path
                if tid in self.task_queue.tasks
            ),
        }

    def create_checkpoint(self, phase: str, metadata: Optional[Dict] = None) -> str:
        """
        Create checkpoint at current build state.

        Args:
            phase: Build phase name
            metadata: Optional metadata

        Returns:
            Checkpoint ID
        """
        if not self.current_state:
            self.current_state = BuildState(phase=phase, status=BuildPhase.IN_PROGRESS)

        checkpoint = self.checkpoint_manager.create_checkpoint(
            phase=phase,
            tasks_completed=self.current_state.tasks_completed.copy(),
            files_created=self.current_state.files_created.copy(),
            metadata=metadata or self.current_state.metadata,
        )

        self.current_state.checkpoint_id = checkpoint.id
        self.current_state.status = BuildPhase.CHECKPOINTED

        return checkpoint.id

    def rollback_to_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Rollback build to specific checkpoint.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            True if rollback successful
        """
        checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return False

        # Rollback checkpoint state
        success = self.checkpoint_manager.rollback(checkpoint_id)
        if not success:
            return False

        # Update current state
        self.current_state = BuildState(
            phase=checkpoint.phase,
            status=BuildPhase.CHECKPOINTED,
            tasks_completed=checkpoint.tasks_completed.copy(),
            files_created=checkpoint.files_created.copy(),
            checkpoint_id=checkpoint_id,
            metadata=checkpoint.metadata.copy(),
        )

        # Update task queue status
        for task_id in checkpoint.tasks_completed:
            if task_id in self.task_queue.tasks:
                self.task_queue.tasks[task_id].status = TaskStatus.COMPLETED

        # Reset tasks completed after checkpoint
        files_to_remove = self.checkpoint_manager.get_files_to_rollback(checkpoint_id)

        return True

    def resume_from_checkpoint(self, checkpoint_id: Optional[str] = None) -> bool:
        """
        Resume build from checkpoint.

        Args:
            checkpoint_id: Specific checkpoint ID, or None for latest

        Returns:
            True if resumed
        """
        if checkpoint_id:
            checkpoint = self.checkpoint_manager.get_checkpoint(checkpoint_id)
        else:
            checkpoint = self.checkpoint_manager.get_latest_checkpoint()

        if not checkpoint:
            return False

        # Restore state
        self.current_state = BuildState(
            phase=checkpoint.phase,
            status=BuildPhase.IN_PROGRESS,
            tasks_completed=checkpoint.tasks_completed.copy(),
            files_created=checkpoint.files_created.copy(),
            checkpoint_id=checkpoint.id,
            metadata=checkpoint.metadata.copy(),
        )

        return True

    def add_interruption_gate(self, task_id: str) -> None:
        """
        Mark task as requiring user input (interruption gate).

        Args:
            task_id: Task ID that requires user action
        """
        self.interruption_gates.add(task_id)

    def is_interruption_gate(self, task_id: str) -> bool:
        """
        Check if task is an interruption gate.

        Args:
            task_id: Task ID

        Returns:
            True if task requires user input
        """
        return task_id in self.interruption_gates

    def get_next_parallelizable_batch(self, max_tasks: int = 3) -> List[QueuedTask]:
        """
        Get next batch of tasks that can run in parallel.

        Args:
            max_tasks: Maximum tasks per batch

        Returns:
            List of tasks that can run in parallel
        """
        ready_tasks = self.task_queue.get_ready_tasks()

        if not ready_tasks:
            return []

        # Filter out interruption gates
        non_gate_tasks = [t for t in ready_tasks if not self.is_interruption_gate(t.id)]

        return non_gate_tasks[:max_tasks]

    def track_file_created(self, file_path: str) -> None:
        """
        Track file creation for rollback.

        Args:
            file_path: Created file path
        """
        if self.current_state:
            self.current_state.files_created.append(file_path)

    def track_task_completed(self, task_id: str) -> None:
        """
        Track task completion.

        Args:
            task_id: Completed task ID
        """
        if self.current_state:
            if task_id in self.current_state.tasks_in_progress:
                self.current_state.tasks_in_progress.remove(task_id)
            self.current_state.tasks_completed.append(task_id)

    def get_build_progress(self) -> Dict[str, Any]:
        """
        Get current build progress.

        Returns:
            Progress information dict
        """
        if not self.current_state:
            return {
                "phase": "not_started",
                "status": "not_started",
                "progress_percent": 0,
                "tasks_completed": 0,
                "tasks_total": len(self.task_queue.tasks),
            }

        total_tasks = len(self.task_queue.tasks)
        completed_tasks = len(self.current_state.tasks_completed)

        return {
            "phase": self.current_state.phase,
            "status": self.current_state.status.value,
            "progress_percent": (completed_tasks / total_tasks * 100) if total_tasks > 0 else 0,
            "tasks_completed": completed_tasks,
            "tasks_in_progress": len(self.current_state.tasks_in_progress),
            "tasks_pending": len(self.current_state.tasks_pending),
            "tasks_total": total_tasks,
            "checkpoint_id": self.current_state.checkpoint_id,
            "files_created": len(self.current_state.files_created),
        }

    def _calculate_critical_path(self) -> List[str]:
        """
        Calculate critical path (longest dependency chain).

        Returns:
            List of task IDs in critical path
        """
        # Simple implementation: find longest path in DAG
        # This is a placeholder - full implementation would use dynamic programming

        max_path = []
        max_duration = 0

        # For each task with no dependencies, calculate path length
        for task in self.task_queue.tasks.values():
            if not task.dependencies:
                path = self._find_longest_path(task.id, set())
                duration = sum(
                    self.task_queue.tasks[tid].estimated_minutes
                    for tid in path
                    if tid in self.task_queue.tasks
                )
                if duration > max_duration:
                    max_duration = duration
                    max_path = path

        return max_path

    def _find_longest_path(self, task_id: str, visited: Set[str]) -> List[str]:
        """Find longest path from task_id"""
        if task_id in visited:
            return []

        visited = visited.copy()
        visited.add(task_id)

        # Find all tasks that depend on this task
        dependent_tasks = [t for t in self.task_queue.tasks.values() if task_id in t.dependencies]

        if not dependent_tasks:
            return [task_id]

        # Recursively find longest path
        max_subpath = []
        for dep_task in dependent_tasks:
            subpath = self._find_longest_path(dep_task.id, visited)
            if len(subpath) > len(max_subpath):
                max_subpath = subpath

        return [task_id] + max_subpath
