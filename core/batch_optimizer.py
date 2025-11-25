"""
Batch Optimizer for Task Orchestration

Groups tasks into optimal batches for Claude execution, ensuring:
- Maximum 2-3 tasks per batch
- No domain mixing (frontend/backend/database)
- Complexity-based batch sizing
- Coherence validation
"""

from dataclasses import dataclass
from enum import Enum
from typing import List, Dict, Set, Optional
from pathlib import Path


class TaskComplexity(Enum):
    """Task complexity levels"""

    SIMPLE = "simple"  # Basic CRUD, simple functions
    MEDIUM = "medium"  # Business logic, APIs
    COMPLEX = "complex"  # Algorithms, state machines
    CRITICAL = "critical"  # Auth, payments, security


class TaskDomain(Enum):
    """Task domain categories"""

    FRONTEND = "frontend"
    BACKEND = "backend"
    DATABASE = "database"
    TESTING = "testing"
    DOCUMENTATION = "documentation"
    INFRASTRUCTURE = "infrastructure"
    UNKNOWN = "unknown"


@dataclass
class Task:
    """Represents a single atomic task"""

    id: str
    name: str
    description: str
    file_path: str
    estimated_minutes: int
    complexity: TaskComplexity
    domain: TaskDomain
    dependencies: List[str]
    acceptance_criteria: List[str]

    def __hash__(self):
        return hash(self.id)


@dataclass
class TaskBatch:
    """Represents a batch of tasks for execution"""

    id: int
    tasks: List[Task]
    total_minutes: int
    domain: TaskDomain
    complexity_level: TaskComplexity


class BatchOptimizer:
    """
    Optimizes task grouping into batches for Claude execution.

    Key principles:
    - Max 2-3 tasks per batch (proven optimal for Claude)
    - Never mix domains in same batch
    - Adjust batch size by complexity
    - Validate batch coherence
    """

    # Batch size rules by complexity
    BATCH_SIZE_RULES = {
        TaskComplexity.SIMPLE: 3,  # Simple tasks: 3 per batch
        TaskComplexity.MEDIUM: 2,  # Medium tasks: 2 per batch
        TaskComplexity.COMPLEX: 1,  # Complex tasks: 1 per batch
        TaskComplexity.CRITICAL: 1,  # Critical tasks: 1 per batch
    }

    # Maximum time per batch (minutes)
    MAX_BATCH_TIME = 240  # 4 hours maximum

    # Domain compatibility matrix
    COMPATIBLE_DOMAINS = {
        TaskDomain.FRONTEND: {TaskDomain.FRONTEND},
        TaskDomain.BACKEND: {TaskDomain.BACKEND},
        TaskDomain.DATABASE: {TaskDomain.DATABASE},
        TaskDomain.TESTING: {TaskDomain.TESTING},
        TaskDomain.DOCUMENTATION: {TaskDomain.DOCUMENTATION, TaskDomain.TESTING},
        TaskDomain.INFRASTRUCTURE: {TaskDomain.INFRASTRUCTURE},
    }

    def __init__(self):
        self.batches: List[TaskBatch] = []
        self._batch_counter = 0

    def optimize_batches(self, tasks: List[Task]) -> List[TaskBatch]:
        """
        Group tasks into optimal batches.

        Args:
            tasks: List of tasks to batch

        Returns:
            List of optimized task batches

        Raises:
            ValueError: If tasks list is empty or contains invalid tasks
        """
        if not tasks:
            raise ValueError("Cannot optimize empty task list")

        # Validate tasks
        self._validate_tasks(tasks)

        # Group by domain first
        domain_groups = self._group_by_domain(tasks)

        # Create batches for each domain group
        batches = []
        for domain, domain_tasks in domain_groups.items():
            domain_batches = self._create_domain_batches(domain, domain_tasks)
            batches.extend(domain_batches)

        self.batches = batches
        return batches

    def _validate_tasks(self, tasks: List[Task]) -> None:
        """Validate task list for batch optimization"""
        if not tasks:
            raise ValueError("Task list cannot be empty")

        # Check for duplicate task IDs
        task_ids = [t.id for t in tasks]
        if len(task_ids) != len(set(task_ids)):
            raise ValueError("Duplicate task IDs found")

        # Validate each task
        for task in tasks:
            if not task.id or not task.name:
                raise ValueError(f"Task missing required fields: {task}")
            if task.estimated_minutes <= 0:
                raise ValueError(f"Task {task.id} has invalid duration: {task.estimated_minutes}")

    def _group_by_domain(self, tasks: List[Task]) -> Dict[TaskDomain, List[Task]]:
        """Group tasks by domain"""
        groups: Dict[TaskDomain, List[Task]] = {}

        for task in tasks:
            domain = task.domain
            if domain not in groups:
                groups[domain] = []
            groups[domain].append(task)

        return groups

    def _create_domain_batches(self, domain: TaskDomain, tasks: List[Task]) -> List[TaskBatch]:
        """Create batches for a single domain's tasks"""
        if not tasks:
            return []

        # Sort by complexity (critical first, simple last)
        complexity_order = [
            TaskComplexity.CRITICAL,
            TaskComplexity.COMPLEX,
            TaskComplexity.MEDIUM,
            TaskComplexity.SIMPLE,
        ]
        sorted_tasks = sorted(tasks, key=lambda t: complexity_order.index(t.complexity))

        batches = []
        current_batch_tasks = []
        current_batch_time = 0

        for task in sorted_tasks:
            max_batch_size = self.BATCH_SIZE_RULES[task.complexity]

            # Check if adding this task would violate batch rules
            if (
                len(current_batch_tasks) >= max_batch_size
                or current_batch_time + task.estimated_minutes > self.MAX_BATCH_TIME
                or (
                    current_batch_tasks
                    and not self._is_coherent_addition(current_batch_tasks, task)
                )
            ):

                # Create batch from current tasks
                if current_batch_tasks:
                    batches.append(self._create_batch(current_batch_tasks, domain))

                # Start new batch with current task
                current_batch_tasks = [task]
                current_batch_time = task.estimated_minutes
            else:
                # Add to current batch
                current_batch_tasks.append(task)
                current_batch_time += task.estimated_minutes

        # Create final batch
        if current_batch_tasks:
            batches.append(self._create_batch(current_batch_tasks, domain))

        return batches

    def _is_coherent_addition(self, batch_tasks: List[Task], new_task: Task) -> bool:
        """
        Check if adding a new task maintains batch coherence.

        Coherence rules:
        - Same domain
        - Similar complexity level (within 1 level)
        - Total time under max
        """
        if not batch_tasks:
            return True

        # Check domain compatibility
        batch_domain = batch_tasks[0].domain
        if new_task.domain != batch_domain:
            return False

        # Check complexity compatibility (allow adjacent levels)
        complexity_levels = [
            TaskComplexity.SIMPLE,
            TaskComplexity.MEDIUM,
            TaskComplexity.COMPLEX,
            TaskComplexity.CRITICAL,
        ]

        batch_complexities = {t.complexity for t in batch_tasks}
        new_complexity = new_task.complexity

        # Allow same complexity or adjacent complexity
        new_idx = complexity_levels.index(new_complexity)
        for batch_complexity in batch_complexities:
            batch_idx = complexity_levels.index(batch_complexity)
            if abs(new_idx - batch_idx) > 1:
                return False

        return True

    def _create_batch(self, tasks: List[Task], domain: TaskDomain) -> TaskBatch:
        """Create a TaskBatch from a list of tasks"""
        self._batch_counter += 1

        total_minutes = sum(t.estimated_minutes for t in tasks)

        # Determine batch complexity (highest complexity wins)
        complexity_order = [
            TaskComplexity.CRITICAL,
            TaskComplexity.COMPLEX,
            TaskComplexity.MEDIUM,
            TaskComplexity.SIMPLE,
        ]
        batch_complexity = min(
            (t.complexity for t in tasks), key=lambda c: complexity_order.index(c)
        )

        return TaskBatch(
            id=self._batch_counter,
            tasks=tasks,
            total_minutes=total_minutes,
            domain=domain,
            complexity_level=batch_complexity,
        )

    def validate_batch(self, batch: TaskBatch) -> tuple[bool, List[str]]:
        """
        Validate a batch against optimization rules.

        Returns:
            (is_valid, list_of_violations)
        """
        violations = []

        # Check batch size
        if len(batch.tasks) > 3:
            violations.append(f"Batch {batch.id} has {len(batch.tasks)} tasks (max 3)")

        # Check domain consistency
        domains = {t.domain for t in batch.tasks}
        if len(domains) > 1:
            violations.append(f"Batch {batch.id} mixes domains: {domains}")

        # Check time limit
        if batch.total_minutes > self.MAX_BATCH_TIME:
            violations.append(
                f"Batch {batch.id} exceeds time limit: "
                f"{batch.total_minutes}m > {self.MAX_BATCH_TIME}m"
            )

        # Check complexity-based batch size
        for task in batch.tasks:
            max_size = self.BATCH_SIZE_RULES[task.complexity]
            if len(batch.tasks) > max_size:
                violations.append(
                    f"Batch {batch.id} violates complexity rule for {task.complexity.value}: "
                    f"{len(batch.tasks)} tasks > {max_size} max"
                )
                break

        return (len(violations) == 0, violations)

    def get_batch_summary(self, batch: TaskBatch) -> str:
        """Generate human-readable batch summary"""
        task_names = [t.name for t in batch.tasks]
        return (
            f"Batch {batch.id}: {batch.domain.value} domain, "
            f"{len(batch.tasks)} tasks, {batch.total_minutes}min total\n"
            f"  Complexity: {batch.complexity_level.value}\n"
            f"  Tasks: {', '.join(task_names)}"
        )

    def get_execution_plan(self) -> str:
        """Generate full execution plan summary"""
        if not self.batches:
            return "No batches created yet"

        lines = [f"Execution Plan: {len(self.batches)} batches\n"]

        for batch in self.batches:
            is_valid, violations = self.validate_batch(batch)
            status = "✓" if is_valid else "✗"
            lines.append(f"\n{status} {self.get_batch_summary(batch)}")
            if violations:
                for violation in violations:
                    lines.append(f"    ! {violation}")

        total_time = sum(b.total_minutes for b in self.batches)
        lines.append(f"\nTotal estimated time: {total_time} minutes ({total_time/60:.1f} hours)")

        return "\n".join(lines)
