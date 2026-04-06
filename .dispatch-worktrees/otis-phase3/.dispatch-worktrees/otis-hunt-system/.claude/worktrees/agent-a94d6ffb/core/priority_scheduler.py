"""
Priority Scheduler for Task Orchestration

Determines optimal task execution order based on priority, complexity,
dependencies, and resource availability.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from enum import Enum


class SchedulingStrategy(Enum):
    """Task scheduling strategies"""

    PRIORITY_FIRST = "priority_first"  # Highest priority first
    SHORTEST_FIRST = "shortest_first"  # Shortest duration first
    CRITICAL_PATH = "critical_path"  # Critical path method
    DEPENDENCY_FIRST = "dependency_first"  # Tasks that unblock most others


@dataclass
class ScheduledTask:
    """Task with scheduling metadata"""

    task_id: str
    priority_score: float
    estimated_minutes: int
    dependencies_count: int
    dependents_count: int  # How many tasks depend on this one
    critical_path: bool = False


class PriorityScheduler:
    """
    Schedules tasks for optimal execution order.

    Considers:
    - Task priority
    - Dependencies
    - Complexity
    - Critical path
    - Resource availability
    """

    # Priority weights
    PRIORITY_WEIGHT = 1.0
    DEPENDENCY_WEIGHT = 0.8
    CRITICAL_PATH_WEIGHT = 2.0
    DURATION_WEIGHT = 0.5

    def __init__(self, strategy: SchedulingStrategy = SchedulingStrategy.PRIORITY_FIRST):
        self.strategy = strategy
        self.task_priorities: Dict[str, float] = {}

    def calculate_priority(
        self,
        task_id: str,
        base_priority: int,
        dependencies_count: int,
        dependents_count: int,
        estimated_minutes: int,
        is_critical_path: bool = False,
    ) -> float:
        """
        Calculate scheduling priority score for a task.

        Args:
            task_id: Task identifier
            base_priority: Base priority (1-10)
            dependencies_count: Number of dependencies
            dependents_count: Number of tasks that depend on this
            estimated_minutes: Estimated duration
            is_critical_path: Whether task is on critical path

        Returns:
            Priority score (higher = execute sooner)
        """
        score = 0.0

        # Base priority (scaled 0-10)
        score += (base_priority / 10.0) * self.PRIORITY_WEIGHT

        # Dependency factor (fewer dependencies = higher priority)
        dep_factor = 1.0 / (1.0 + dependencies_count)
        score += dep_factor * self.DEPENDENCY_WEIGHT

        # Dependent factor (more dependents = higher priority)
        dependent_factor = dependents_count / 10.0  # Scale down
        score += dependent_factor * self.DEPENDENCY_WEIGHT

        # Duration factor (strategy-dependent)
        if self.strategy == SchedulingStrategy.SHORTEST_FIRST:
            # Shorter tasks get higher priority
            duration_factor = 1.0 / (1.0 + estimated_minutes / 60.0)
            score += duration_factor * self.DURATION_WEIGHT

        # Critical path (significant boost)
        if is_critical_path:
            score += self.CRITICAL_PATH_WEIGHT

        self.task_priorities[task_id] = score
        return score

    def schedule_tasks(self, tasks: List) -> List[str]:
        """
        Schedule tasks for execution.

        Args:
            tasks: List of tasks to schedule (must have dependencies attribute)

        Returns:
            List of task IDs in execution order
        """
        if not tasks:
            return []

        # Build dependency graph
        task_map = {t.id: t for t in tasks}
        dependents_map = self._build_dependents_map(tasks)

        # Calculate priorities for all tasks
        scheduled_tasks = []

        for task in tasks:
            dependents_count = len(dependents_map.get(task.id, []))
            base_priority = getattr(task, "priority", 5)  # Default priority 5

            score = self.calculate_priority(
                task_id=task.id,
                base_priority=base_priority,
                dependencies_count=len(task.dependencies),
                dependents_count=dependents_count,
                estimated_minutes=task.estimated_minutes,
                is_critical_path=getattr(task, "critical_path", False),
            )

            scheduled_tasks.append(
                ScheduledTask(
                    task_id=task.id,
                    priority_score=score,
                    estimated_minutes=task.estimated_minutes,
                    dependencies_count=len(task.dependencies),
                    dependents_count=dependents_count,
                    critical_path=getattr(task, "critical_path", False),
                )
            )

        # Sort by priority score (highest first)
        scheduled_tasks.sort(key=lambda x: x.priority_score, reverse=True)

        return [t.task_id for t in scheduled_tasks]

    def reschedule(
        self,
        remaining_tasks: List,
        completed_task_ids: List[str],
    ) -> List[str]:
        """
        Reschedule remaining tasks after some completions.

        Args:
            remaining_tasks: Tasks still to execute
            completed_task_ids: IDs of completed tasks

        Returns:
            Updated execution order
        """
        # Recalculate priorities with updated information
        return self.schedule_tasks(remaining_tasks)

    def get_priority_score(self, task_id: str) -> Optional[float]:
        """Get priority score for a task"""
        return self.task_priorities.get(task_id)

    def _build_dependents_map(self, tasks: List) -> Dict[str, List[str]]:
        """Build map of task_id -> list of tasks that depend on it"""
        dependents: Dict[str, List[str]] = {}

        for task in tasks:
            for dep_id in task.dependencies:
                if dep_id not in dependents:
                    dependents[dep_id] = []
                dependents[dep_id].append(task.id)

        return dependents

    def get_stats(self) -> Dict:
        """Get scheduler statistics"""
        if not self.task_priorities:
            return {
                "strategy": self.strategy.value,
                "tasks_scheduled": 0,
                "average_priority": 0.0,
            }

        return {
            "strategy": self.strategy.value,
            "tasks_scheduled": len(self.task_priorities),
            "average_priority": sum(self.task_priorities.values()) / len(self.task_priorities),
            "highest_priority": max(self.task_priorities.values()),
            "lowest_priority": min(self.task_priorities.values()),
        }
