"""
Dependency Graph - Build DAG and calculate execution order

Creates directed acyclic graph (DAG) from task dependencies:
- Calculates optimal execution order
- Identifies parallelizable tasks
- Detects circular dependencies
- Groups tasks by execution level

Features:
- Topological sorting for task ordering
- Cycle detection
- Parallel execution opportunities
- Critical path analysis
"""
from typing import Dict, List, Set, Optional, Tuple
from dataclasses import dataclass, field
from collections import defaultdict, deque
from enum import Enum


class GraphError(Exception):
    """Base exception for graph-related errors"""
    pass


class CircularDependencyError(GraphError):
    """Raised when circular dependency is detected"""
    pass


@dataclass
class ExecutionLevel:
    """Represents a level in the execution plan"""
    level: int
    tasks: List[str] = field(default_factory=list)
    estimated_minutes: int = 0


class DependencyGraph:
    """
    Build and analyze task dependency graph

    Features:
    - Build DAG from task list
    - Topological sort for execution order
    - Detect circular dependencies
    - Identify parallelizable tasks
    - Calculate critical path
    """

    def __init__(self):
        """Initialize DependencyGraph"""
        self.tasks: Dict[str, Dict] = {}
        self.adjacency_list: Dict[str, List[str]] = defaultdict(list)
        self.reverse_adjacency: Dict[str, List[str]] = defaultdict(list)
        self.in_degree: Dict[str, int] = defaultdict(int)

    def add_task(self, task: Dict) -> None:
        """
        Add task to graph

        Args:
            task: Task dict with id, dependencies, estimated_minutes
        """
        task_id = task['id']
        self.tasks[task_id] = task

        # Initialize in-degree
        if task_id not in self.in_degree:
            self.in_degree[task_id] = 0

        # Add edges for dependencies
        dependencies = task.get('dependencies', [])
        for dep_id in dependencies:
            # Add edge from dependency to task
            self.adjacency_list[dep_id].append(task_id)
            self.reverse_adjacency[task_id].append(dep_id)
            self.in_degree[task_id] += 1

            # Ensure dependency task exists in in_degree
            if dep_id not in self.in_degree:
                self.in_degree[dep_id] = 0

    def build_graph(self, tasks: List[Dict]) -> None:
        """
        Build dependency graph from task list

        Args:
            tasks: List of task dicts

        Raises:
            CircularDependencyError: If circular dependency detected
        """
        # Clear existing graph
        self.tasks.clear()
        self.adjacency_list.clear()
        self.reverse_adjacency.clear()
        self.in_degree.clear()

        # Add all tasks
        for task in tasks:
            self.add_task(task)

        # Detect circular dependencies
        if self.has_circular_dependency():
            raise CircularDependencyError("Circular dependency detected in task graph")

    def has_circular_dependency(self) -> bool:
        """
        Detect circular dependencies using DFS

        Returns:
            True if circular dependency exists
        """
        # Track visit states: 0=unvisited, 1=visiting, 2=visited
        state = {task_id: 0 for task_id in self.tasks}

        def visit(task_id: str) -> bool:
            """DFS visit with cycle detection"""
            # Skip if task doesn't exist (missing dependency)
            if task_id not in state:
                return False

            if state[task_id] == 1:  # Currently visiting - found cycle
                return True
            if state[task_id] == 2:  # Already visited
                return False

            state[task_id] = 1  # Mark as visiting

            # Visit all dependencies (only those that exist)
            for dep_id in self.reverse_adjacency[task_id]:
                if visit(dep_id):
                    return True

            state[task_id] = 2  # Mark as visited
            return False

        # Check all tasks
        for task_id in self.tasks:
            if state[task_id] == 0:
                if visit(task_id):
                    return True

        return False

    def topological_sort(self) -> List[str]:
        """
        Perform topological sort using Kahn's algorithm

        Returns:
            List of task IDs in execution order

        Raises:
            CircularDependencyError: If graph has cycles
        """
        # Copy in-degree (will be modified)
        in_degree_copy = self.in_degree.copy()

        # Queue of tasks with no dependencies
        queue = deque([task_id for task_id, degree in in_degree_copy.items() if degree == 0])

        sorted_tasks = []

        while queue:
            # Process task with no remaining dependencies
            task_id = queue.popleft()
            sorted_tasks.append(task_id)

            # Reduce in-degree for dependent tasks
            for dependent_id in self.adjacency_list[task_id]:
                in_degree_copy[dependent_id] -= 1
                if in_degree_copy[dependent_id] == 0:
                    queue.append(dependent_id)

        # Check if all tasks were processed
        if len(sorted_tasks) != len(self.tasks):
            raise CircularDependencyError("Circular dependency prevents topological sort")

        return sorted_tasks

    def get_execution_levels(self) -> List[ExecutionLevel]:
        """
        Group tasks into execution levels (parallelizable groups)

        Returns:
            List of ExecutionLevel objects, ordered by level

        Each level contains tasks that:
        - Have all dependencies in previous levels
        - Can be executed in parallel with each other
        """
        # Copy in-degree (will be modified)
        in_degree_copy = self.in_degree.copy()

        # Track which tasks are in each level
        levels: List[ExecutionLevel] = []
        current_level = 0

        # Track processed tasks
        processed = set()

        while len(processed) < len(self.tasks):
            # Find tasks with no remaining dependencies
            level_tasks = [
                task_id for task_id, degree in in_degree_copy.items()
                if degree == 0 and task_id not in processed
            ]

            if not level_tasks:
                # No tasks available but not all processed - circular dependency
                raise CircularDependencyError("Circular dependency detected")

            # Calculate total estimated time for level (max of tasks, since parallel)
            max_duration = 0
            for task_id in level_tasks:
                task_duration = self.tasks[task_id].get('estimated_minutes', 0)
                max_duration = max(max_duration, task_duration)

            # Create execution level
            level = ExecutionLevel(
                level=current_level,
                tasks=level_tasks,
                estimated_minutes=max_duration
            )
            levels.append(level)

            # Mark tasks as processed and update dependencies
            for task_id in level_tasks:
                processed.add(task_id)

                # Reduce in-degree for dependent tasks
                for dependent_id in self.adjacency_list[task_id]:
                    in_degree_copy[dependent_id] -= 1

            current_level += 1

        return levels

    def get_parallelizable_tasks(self, task_id: str) -> List[str]:
        """
        Get tasks that can run in parallel with given task

        Args:
            task_id: Task ID to check

        Returns:
            List of task IDs that can run in parallel
        """
        if task_id not in self.tasks:
            return []

        # Get execution levels
        levels = self.get_execution_levels()

        # Find task's level
        task_level = None
        for level in levels:
            if task_id in level.tasks:
                task_level = level
                break

        if not task_level:
            return []

        # Return other tasks in same level
        return [tid for tid in task_level.tasks if tid != task_id]

    def get_dependencies(self, task_id: str, recursive: bool = False) -> List[str]:
        """
        Get dependencies for a task

        Args:
            task_id: Task ID
            recursive: If True, get all transitive dependencies

        Returns:
            List of task IDs this task depends on
        """
        if task_id not in self.tasks:
            return []

        if not recursive:
            return self.reverse_adjacency.get(task_id, [])

        # Get all transitive dependencies using DFS
        dependencies = set()
        visited = set()

        def visit(tid: str):
            if tid in visited:
                return
            visited.add(tid)

            for dep_id in self.reverse_adjacency.get(tid, []):
                dependencies.add(dep_id)
                visit(dep_id)

        visit(task_id)
        return list(dependencies)

    def get_dependents(self, task_id: str, recursive: bool = False) -> List[str]:
        """
        Get tasks that depend on this task

        Args:
            task_id: Task ID
            recursive: If True, get all transitive dependents

        Returns:
            List of task IDs that depend on this task
        """
        if task_id not in self.tasks:
            return []

        if not recursive:
            return self.adjacency_list.get(task_id, [])

        # Get all transitive dependents using DFS
        dependents = set()
        visited = set()

        def visit(tid: str):
            if tid in visited:
                return
            visited.add(tid)

            for dep_id in self.adjacency_list.get(tid, []):
                dependents.add(dep_id)
                visit(dep_id)

        visit(task_id)
        return list(dependents)

    def get_critical_path(self) -> Tuple[List[str], int]:
        """
        Calculate critical path (longest path through graph)

        Returns:
            Tuple of (task_ids_in_critical_path, total_duration_minutes)
        """
        # Get topological order
        topo_order = self.topological_sort()

        # Calculate longest path to each task
        longest_path = {task_id: 0 for task_id in self.tasks}
        predecessor = {task_id: None for task_id in self.tasks}

        for task_id in topo_order:
            task_duration = self.tasks[task_id].get('estimated_minutes', 0)

            # Check all dependencies
            for dep_id in self.reverse_adjacency[task_id]:
                dep_path_length = longest_path[dep_id] + task_duration

                if dep_path_length > longest_path[task_id]:
                    longest_path[task_id] = dep_path_length
                    predecessor[task_id] = dep_id

            # If no dependencies, path length is just task duration
            if not self.reverse_adjacency[task_id]:
                longest_path[task_id] = task_duration

        # Find task with longest path
        end_task = max(longest_path.keys(), key=lambda k: longest_path[k])
        total_duration = longest_path[end_task]

        # Reconstruct path
        path = []
        current = end_task
        while current is not None:
            path.append(current)
            current = predecessor[current]

        path.reverse()
        return path, total_duration

    def get_task_count(self) -> int:
        """Get total number of tasks in graph"""
        return len(self.tasks)

    def get_ready_tasks(self, completed_tasks: Set[str]) -> List[str]:
        """
        Get tasks that are ready to execute given completed tasks

        Args:
            completed_tasks: Set of completed task IDs

        Returns:
            List of task IDs ready to execute
        """
        ready = []

        for task_id in self.tasks:
            # Skip if already completed
            if task_id in completed_tasks:
                continue

            # Check if all dependencies are completed
            dependencies = self.reverse_adjacency.get(task_id, [])
            if all(dep_id in completed_tasks for dep_id in dependencies):
                ready.append(task_id)

        return ready

    def validate_dependencies(self) -> List[str]:
        """
        Validate all task dependencies exist

        Returns:
            List of missing dependency IDs
        """
        missing = []

        for task_id, task in self.tasks.items():
            dependencies = task.get('dependencies', [])
            for dep_id in dependencies:
                if dep_id not in self.tasks:
                    missing.append(f"{task_id} -> {dep_id}")

        return missing


def main():
    """CLI entry point for testing"""
    import sys
    import json

    if len(sys.argv) < 2:
        print("Usage: python dependency_graph.py <tasks_json>")
        sys.exit(1)

    tasks_json = sys.argv[1]
    tasks = json.loads(tasks_json)

    graph = DependencyGraph()
    graph.build_graph(tasks)

    print(f"\n=== Dependency Graph Analysis ===")
    print(f"Total tasks: {graph.get_task_count()}")

    # Topological sort
    print(f"\nExecution order:")
    topo_order = graph.topological_sort()
    for i, task_id in enumerate(topo_order, 1):
        print(f"  {i}. {task_id}")

    # Execution levels
    print(f"\nExecution levels (parallelizable):")
    levels = graph.get_execution_levels()
    for level in levels:
        print(f"  Level {level.level}: {len(level.tasks)} tasks ({level.estimated_minutes} min)")
        for task_id in level.tasks:
            print(f"    - {task_id}")

    # Critical path
    critical_path, duration = graph.get_critical_path()
    print(f"\nCritical path ({duration} minutes):")
    for task_id in critical_path:
        print(f"  -> {task_id}")


if __name__ == "__main__":
    main()
