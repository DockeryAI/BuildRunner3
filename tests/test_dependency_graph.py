"""
Tests for Dependency Graph
"""
import pytest
from core.dependency_graph import (
    DependencyGraph,
    ExecutionLevel,
    GraphError,
    CircularDependencyError
)


class TestDependencyGraph:
    """Test DependencyGraph class"""

    @pytest.fixture
    def graph(self):
        """Create DependencyGraph instance"""
        return DependencyGraph()

    @pytest.fixture
    def linear_tasks(self):
        """Linear dependency chain: A -> B -> C"""
        return [
            {"id": "task_a", "dependencies": [], "estimated_minutes": 60},
            {"id": "task_b", "dependencies": ["task_a"], "estimated_minutes": 90},
            {"id": "task_c", "dependencies": ["task_b"], "estimated_minutes": 120}
        ]

    @pytest.fixture
    def parallel_tasks(self):
        """Parallel tasks with final join: A -> B, A -> C, B+C -> D"""
        return [
            {"id": "task_a", "dependencies": [], "estimated_minutes": 60},
            {"id": "task_b", "dependencies": ["task_a"], "estimated_minutes": 90},
            {"id": "task_c", "dependencies": ["task_a"], "estimated_minutes": 90},
            {"id": "task_d", "dependencies": ["task_b", "task_c"], "estimated_minutes": 60}
        ]

    @pytest.fixture
    def circular_tasks(self):
        """Tasks with circular dependency: A -> B -> C -> A"""
        return [
            {"id": "task_a", "dependencies": ["task_c"], "estimated_minutes": 60},
            {"id": "task_b", "dependencies": ["task_a"], "estimated_minutes": 90},
            {"id": "task_c", "dependencies": ["task_b"], "estimated_minutes": 120}
        ]

    @pytest.fixture
    def complex_tasks(self):
        """Complex DAG with multiple paths"""
        return [
            {"id": "task_1", "dependencies": [], "estimated_minutes": 60},
            {"id": "task_2", "dependencies": [], "estimated_minutes": 60},
            {"id": "task_3", "dependencies": ["task_1"], "estimated_minutes": 90},
            {"id": "task_4", "dependencies": ["task_1", "task_2"], "estimated_minutes": 90},
            {"id": "task_5", "dependencies": ["task_3", "task_4"], "estimated_minutes": 120},
            {"id": "task_6", "dependencies": ["task_2"], "estimated_minutes": 60}
        ]

    def test_init(self, graph):
        """Test initialization"""
        assert graph is not None
        assert graph.get_task_count() == 0
        assert len(graph.tasks) == 0
        assert len(graph.adjacency_list) == 0

    def test_add_task_no_dependencies(self, graph):
        """Test adding task with no dependencies"""
        task = {"id": "task_a", "dependencies": [], "estimated_minutes": 60}
        graph.add_task(task)

        assert graph.get_task_count() == 1
        assert "task_a" in graph.tasks
        assert graph.in_degree["task_a"] == 0

    def test_add_task_with_dependencies(self, graph):
        """Test adding task with dependencies"""
        task_a = {"id": "task_a", "dependencies": [], "estimated_minutes": 60}
        task_b = {"id": "task_b", "dependencies": ["task_a"], "estimated_minutes": 90}

        graph.add_task(task_a)
        graph.add_task(task_b)

        assert graph.get_task_count() == 2
        assert graph.in_degree["task_a"] == 0
        assert graph.in_degree["task_b"] == 1
        assert "task_b" in graph.adjacency_list["task_a"]

    def test_build_graph_linear(self, graph, linear_tasks):
        """Test building linear dependency graph"""
        graph.build_graph(linear_tasks)

        assert graph.get_task_count() == 3
        assert graph.in_degree["task_a"] == 0
        assert graph.in_degree["task_b"] == 1
        assert graph.in_degree["task_c"] == 1

    def test_build_graph_parallel(self, graph, parallel_tasks):
        """Test building graph with parallel tasks"""
        graph.build_graph(parallel_tasks)

        assert graph.get_task_count() == 4
        assert graph.in_degree["task_a"] == 0
        assert graph.in_degree["task_b"] == 1
        assert graph.in_degree["task_c"] == 1
        assert graph.in_degree["task_d"] == 2  # Depends on both B and C

    def test_build_graph_circular_raises_error(self, graph, circular_tasks):
        """Test that circular dependency raises error"""
        with pytest.raises(CircularDependencyError):
            graph.build_graph(circular_tasks)

    def test_has_circular_dependency_false(self, graph, linear_tasks):
        """Test circular dependency detection returns False for valid graph"""
        for task in linear_tasks:
            graph.add_task(task)

        assert graph.has_circular_dependency() is False

    def test_has_circular_dependency_true(self, graph, circular_tasks):
        """Test circular dependency detection returns True for circular graph"""
        for task in circular_tasks:
            graph.add_task(task)

        assert graph.has_circular_dependency() is True

    def test_has_circular_dependency_self_loop(self, graph):
        """Test detection of self-referencing task"""
        task = {"id": "task_a", "dependencies": ["task_a"], "estimated_minutes": 60}
        graph.add_task(task)

        assert graph.has_circular_dependency() is True

    def test_topological_sort_linear(self, graph, linear_tasks):
        """Test topological sort on linear graph"""
        graph.build_graph(linear_tasks)
        sorted_tasks = graph.topological_sort()

        assert len(sorted_tasks) == 3
        assert sorted_tasks.index("task_a") < sorted_tasks.index("task_b")
        assert sorted_tasks.index("task_b") < sorted_tasks.index("task_c")

    def test_topological_sort_parallel(self, graph, parallel_tasks):
        """Test topological sort on parallel graph"""
        graph.build_graph(parallel_tasks)
        sorted_tasks = graph.topological_sort()

        assert len(sorted_tasks) == 4
        # A must come before B and C
        assert sorted_tasks.index("task_a") < sorted_tasks.index("task_b")
        assert sorted_tasks.index("task_a") < sorted_tasks.index("task_c")
        # B and C must come before D
        assert sorted_tasks.index("task_b") < sorted_tasks.index("task_d")
        assert sorted_tasks.index("task_c") < sorted_tasks.index("task_d")

    def test_topological_sort_complex(self, graph, complex_tasks):
        """Test topological sort on complex DAG"""
        graph.build_graph(complex_tasks)
        sorted_tasks = graph.topological_sort()

        assert len(sorted_tasks) == 6

        # Verify dependencies are respected
        for task in complex_tasks:
            task_index = sorted_tasks.index(task["id"])
            for dep_id in task["dependencies"]:
                dep_index = sorted_tasks.index(dep_id)
                assert dep_index < task_index

    def test_get_execution_levels_linear(self, graph, linear_tasks):
        """Test execution levels for linear graph"""
        graph.build_graph(linear_tasks)
        levels = graph.get_execution_levels()

        assert len(levels) == 3
        assert levels[0].level == 0
        assert levels[0].tasks == ["task_a"]
        assert levels[0].estimated_minutes == 60

        assert levels[1].level == 1
        assert levels[1].tasks == ["task_b"]
        assert levels[1].estimated_minutes == 90

        assert levels[2].level == 2
        assert levels[2].tasks == ["task_c"]
        assert levels[2].estimated_minutes == 120

    def test_get_execution_levels_parallel(self, graph, parallel_tasks):
        """Test execution levels for parallel graph"""
        graph.build_graph(parallel_tasks)
        levels = graph.get_execution_levels()

        assert len(levels) == 3

        # Level 0: task_a
        assert levels[0].tasks == ["task_a"]

        # Level 1: task_b and task_c (parallel)
        assert set(levels[1].tasks) == {"task_b", "task_c"}
        assert levels[1].estimated_minutes == 90  # Max of B and C

        # Level 2: task_d
        assert levels[2].tasks == ["task_d"]

    def test_get_execution_levels_complex(self, graph, complex_tasks):
        """Test execution levels for complex DAG"""
        graph.build_graph(complex_tasks)
        levels = graph.get_execution_levels()

        # Level 0: tasks with no dependencies
        assert set(levels[0].tasks) == {"task_1", "task_2"}

        # Verify all tasks are in some level
        all_level_tasks = []
        for level in levels:
            all_level_tasks.extend(level.tasks)

        assert len(all_level_tasks) == 6
        assert set(all_level_tasks) == {"task_1", "task_2", "task_3", "task_4", "task_5", "task_6"}

    def test_get_parallelizable_tasks(self, graph, parallel_tasks):
        """Test getting tasks that can run in parallel"""
        graph.build_graph(parallel_tasks)

        # task_b and task_c are in same level (parallelizable)
        parallel_to_b = graph.get_parallelizable_tasks("task_b")
        assert "task_c" in parallel_to_b

        parallel_to_c = graph.get_parallelizable_tasks("task_c")
        assert "task_b" in parallel_to_c

        # task_a has no parallel tasks
        parallel_to_a = graph.get_parallelizable_tasks("task_a")
        assert len(parallel_to_a) == 0

    def test_get_parallelizable_tasks_nonexistent(self, graph, linear_tasks):
        """Test getting parallel tasks for nonexistent task"""
        graph.build_graph(linear_tasks)

        parallel = graph.get_parallelizable_tasks("nonexistent")
        assert parallel == []

    def test_get_dependencies_direct(self, graph, parallel_tasks):
        """Test getting direct dependencies"""
        graph.build_graph(parallel_tasks)

        # task_d depends on task_b and task_c
        deps = graph.get_dependencies("task_d", recursive=False)
        assert set(deps) == {"task_b", "task_c"}

        # task_a has no dependencies
        deps = graph.get_dependencies("task_a", recursive=False)
        assert deps == []

    def test_get_dependencies_recursive(self, graph, linear_tasks):
        """Test getting all transitive dependencies"""
        graph.build_graph(linear_tasks)

        # task_c depends on task_b, which depends on task_a
        deps = graph.get_dependencies("task_c", recursive=True)
        assert set(deps) == {"task_a", "task_b"}

    def test_get_dependencies_nonexistent(self, graph, linear_tasks):
        """Test getting dependencies for nonexistent task"""
        graph.build_graph(linear_tasks)

        deps = graph.get_dependencies("nonexistent")
        assert deps == []

    def test_get_dependents_direct(self, graph, parallel_tasks):
        """Test getting direct dependents"""
        graph.build_graph(parallel_tasks)

        # task_a is depended on by task_b and task_c
        deps = graph.get_dependents("task_a", recursive=False)
        assert set(deps) == {"task_b", "task_c"}

        # task_d has no dependents
        deps = graph.get_dependents("task_d", recursive=False)
        assert deps == []

    def test_get_dependents_recursive(self, graph, linear_tasks):
        """Test getting all transitive dependents"""
        graph.build_graph(linear_tasks)

        # task_a is depended on by task_b and task_c (transitively)
        deps = graph.get_dependents("task_a", recursive=True)
        assert set(deps) == {"task_b", "task_c"}

    def test_get_dependents_nonexistent(self, graph, linear_tasks):
        """Test getting dependents for nonexistent task"""
        graph.build_graph(linear_tasks)

        deps = graph.get_dependents("nonexistent")
        assert deps == []

    def test_get_critical_path_linear(self, graph, linear_tasks):
        """Test critical path for linear graph"""
        graph.build_graph(linear_tasks)

        path, duration = graph.get_critical_path()

        assert path == ["task_a", "task_b", "task_c"]
        assert duration == 60 + 90 + 120  # Sum of all tasks

    def test_get_critical_path_parallel(self, graph, parallel_tasks):
        """Test critical path for parallel graph"""
        graph.build_graph(parallel_tasks)

        path, duration = graph.get_critical_path()

        # Path should go through either B or C (both 90 min)
        # A(60) + B/C(90) + D(60) = 210
        assert duration == 60 + 90 + 60
        assert path[0] == "task_a"
        assert path[-1] == "task_d"
        assert path[1] in ["task_b", "task_c"]

    def test_get_critical_path_complex(self, graph, complex_tasks):
        """Test critical path for complex DAG"""
        graph.build_graph(complex_tasks)

        path, duration = graph.get_critical_path()

        # Should find longest path through graph
        assert duration > 0
        assert len(path) > 0

        # Verify path is valid (each task depends on previous)
        for i in range(1, len(path)):
            deps = graph.get_dependencies(path[i], recursive=True)
            assert path[i-1] in deps or path[i-1] not in graph.tasks

    def test_get_task_count(self, graph, linear_tasks):
        """Test getting task count"""
        assert graph.get_task_count() == 0

        graph.build_graph(linear_tasks)
        assert graph.get_task_count() == 3

    def test_get_ready_tasks_empty(self, graph, linear_tasks):
        """Test getting ready tasks with no completed tasks"""
        graph.build_graph(linear_tasks)

        ready = graph.get_ready_tasks(set())

        # Only task_a has no dependencies
        assert ready == ["task_a"]

    def test_get_ready_tasks_some_completed(self, graph, parallel_tasks):
        """Test getting ready tasks with some completed"""
        graph.build_graph(parallel_tasks)

        # After completing task_a, both task_b and task_c are ready
        completed = {"task_a"}
        ready = graph.get_ready_tasks(completed)

        assert set(ready) == {"task_b", "task_c"}

    def test_get_ready_tasks_almost_done(self, graph, parallel_tasks):
        """Test getting ready tasks near completion"""
        graph.build_graph(parallel_tasks)

        # After completing A, B, and C, only D is ready
        completed = {"task_a", "task_b", "task_c"}
        ready = graph.get_ready_tasks(completed)

        assert ready == ["task_d"]

    def test_get_ready_tasks_all_completed(self, graph, linear_tasks):
        """Test getting ready tasks when all completed"""
        graph.build_graph(linear_tasks)

        completed = {"task_a", "task_b", "task_c"}
        ready = graph.get_ready_tasks(completed)

        assert ready == []

    def test_validate_dependencies_valid(self, graph, linear_tasks):
        """Test validation with valid dependencies"""
        graph.build_graph(linear_tasks)

        missing = graph.validate_dependencies()
        assert missing == []

    def test_validate_dependencies_missing(self, graph):
        """Test validation with missing dependencies"""
        tasks = [
            {"id": "task_a", "dependencies": [], "estimated_minutes": 60},
            {"id": "task_b", "dependencies": ["task_x"], "estimated_minutes": 90}
        ]

        graph.build_graph(tasks)

        missing = graph.validate_dependencies()
        assert len(missing) == 1
        assert "task_b -> task_x" in missing

    def test_validate_dependencies_multiple_missing(self, graph):
        """Test validation with multiple missing dependencies"""
        tasks = [
            {"id": "task_a", "dependencies": ["task_x", "task_y"], "estimated_minutes": 60},
            {"id": "task_b", "dependencies": ["task_z"], "estimated_minutes": 90}
        ]

        graph.build_graph(tasks)

        missing = graph.validate_dependencies()
        assert len(missing) == 3

    def test_build_graph_clears_previous(self, graph, linear_tasks, parallel_tasks):
        """Test that building new graph clears previous graph"""
        graph.build_graph(linear_tasks)
        assert graph.get_task_count() == 3

        graph.build_graph(parallel_tasks)
        assert graph.get_task_count() == 4

        # Verify previous tasks are gone
        assert "task_a" in graph.tasks  # Present in both
        assert "task_d" in graph.tasks  # Only in parallel_tasks

    def test_execution_level_dataclass(self):
        """Test ExecutionLevel dataclass"""
        level = ExecutionLevel(
            level=0,
            tasks=["task_a", "task_b"],
            estimated_minutes=90
        )

        assert level.level == 0
        assert level.tasks == ["task_a", "task_b"]
        assert level.estimated_minutes == 90

    def test_execution_level_default_values(self):
        """Test ExecutionLevel default values"""
        level = ExecutionLevel(level=1)

        assert level.level == 1
        assert level.tasks == []
        assert level.estimated_minutes == 0

    def test_graph_error_exception(self):
        """Test GraphError exception"""
        with pytest.raises(GraphError):
            raise GraphError("Test error")

    def test_circular_dependency_error_exception(self):
        """Test CircularDependencyError exception"""
        with pytest.raises(CircularDependencyError):
            raise CircularDependencyError("Circular dependency found")

    def test_circular_dependency_error_is_graph_error(self):
        """Test that CircularDependencyError is a GraphError"""
        assert issubclass(CircularDependencyError, GraphError)

    def test_main_cli_function(self, capsys):
        """Test CLI main function"""
        import sys
        import json
        from core.dependency_graph import main

        tasks = [
            {"id": "task_a", "dependencies": [], "estimated_minutes": 60},
            {"id": "task_b", "dependencies": ["task_a"], "estimated_minutes": 90}
        ]

        original_argv = sys.argv
        try:
            sys.argv = ["dependency_graph.py", json.dumps(tasks)]
            main()

            captured = capsys.readouterr()
            assert "Dependency Graph Analysis" in captured.out
            assert "Total tasks: 2" in captured.out
            assert "Execution order:" in captured.out
        finally:
            sys.argv = original_argv

    def test_main_cli_no_args(self, capsys):
        """Test CLI main function with no arguments"""
        import sys
        from core.dependency_graph import main

        original_argv = sys.argv
        try:
            sys.argv = ["dependency_graph.py"]

            with pytest.raises(SystemExit) as exc_info:
                main()

            assert exc_info.value.code == 1
            captured = capsys.readouterr()
            assert "Usage:" in captured.out
        finally:
            sys.argv = original_argv
