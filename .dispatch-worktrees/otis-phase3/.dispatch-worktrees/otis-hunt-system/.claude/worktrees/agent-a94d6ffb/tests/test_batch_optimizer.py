"""
Tests for BatchOptimizer

Ensures optimal task batching with 2-3 tasks max, no domain mixing,
complexity-based sizing, and coherence validation.
"""

import pytest
from core.batch_optimizer import (
    BatchOptimizer,
    Task,
    TaskBatch,
    TaskComplexity,
    TaskDomain,
)


class TestBatchOptimizer:
    """Test suite for BatchOptimizer"""

    def test_init(self):
        """Test BatchOptimizer initialization"""
        optimizer = BatchOptimizer()
        assert optimizer.batches == []
        assert optimizer._batch_counter == 0

    def test_batch_size_rules(self):
        """Test batch size rules are defined correctly"""
        rules = BatchOptimizer.BATCH_SIZE_RULES
        assert rules[TaskComplexity.SIMPLE] == 3
        assert rules[TaskComplexity.MEDIUM] == 2
        assert rules[TaskComplexity.COMPLEX] == 1
        assert rules[TaskComplexity.CRITICAL] == 1

    def test_optimize_empty_tasks_raises(self):
        """Test that optimizing empty task list raises error"""
        optimizer = BatchOptimizer()
        with pytest.raises(ValueError, match="Cannot optimize empty task list"):
            optimizer.optimize_batches([])

    def test_optimize_simple_single_task(self):
        """Test optimizing a single simple task"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="task1",
                name="Simple Task",
                description="A simple task",
                file_path="core/simple.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        batches = optimizer.optimize_batches(tasks)

        assert len(batches) == 1
        assert len(batches[0].tasks) == 1
        assert batches[0].tasks[0].id == "task1"
        assert batches[0].domain == TaskDomain.BACKEND

    def test_optimize_three_simple_tasks_same_domain(self):
        """Test that 3 simple tasks in same domain batch together"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id=f"task{i}",
                name=f"Simple Task {i}",
                description="A simple task",
                file_path=f"core/simple{i}.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
            for i in range(1, 4)
        ]

        batches = optimizer.optimize_batches(tasks)

        assert len(batches) == 1
        assert len(batches[0].tasks) == 3
        assert batches[0].total_minutes == 180

    def test_optimize_four_simple_tasks_creates_two_batches(self):
        """Test that 4 simple tasks create 2 batches (3+1)"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id=f"task{i}",
                name=f"Simple Task {i}",
                description="A simple task",
                file_path=f"core/simple{i}.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
            for i in range(1, 5)
        ]

        batches = optimizer.optimize_batches(tasks)

        assert len(batches) == 2
        assert len(batches[0].tasks) == 3
        assert len(batches[1].tasks) == 1

    def test_optimize_medium_tasks_max_two_per_batch(self):
        """Test that medium tasks batch with max 2 per batch"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id=f"task{i}",
                name=f"Medium Task {i}",
                description="A medium task",
                file_path=f"core/medium{i}.py",
                estimated_minutes=90,
                complexity=TaskComplexity.MEDIUM,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
            for i in range(1, 6)  # 5 medium tasks
        ]

        batches = optimizer.optimize_batches(tasks)

        # Should create 3 batches: 2+2+1
        assert len(batches) == 3
        assert len(batches[0].tasks) == 2
        assert len(batches[1].tasks) == 2
        assert len(batches[2].tasks) == 1

    def test_optimize_complex_tasks_one_per_batch(self):
        """Test that complex tasks batch with max 1 per batch"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id=f"task{i}",
                name=f"Complex Task {i}",
                description="A complex task",
                file_path=f"core/complex{i}.py",
                estimated_minutes=120,
                complexity=TaskComplexity.COMPLEX,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
            for i in range(1, 4)
        ]

        batches = optimizer.optimize_batches(tasks)

        # Should create 3 batches: 1+1+1
        assert len(batches) == 3
        for batch in batches:
            assert len(batch.tasks) == 1

    def test_optimize_critical_tasks_one_per_batch(self):
        """Test that critical tasks batch with max 1 per batch"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="auth",
                name="Authentication System",
                description="Critical auth task",
                file_path="core/auth.py",
                estimated_minutes=120,
                complexity=TaskComplexity.CRITICAL,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Secure"],
            ),
            Task(
                id="payment",
                name="Payment Processing",
                description="Critical payment task",
                file_path="core/payment.py",
                estimated_minutes=150,
                complexity=TaskComplexity.CRITICAL,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Secure"],
            ),
        ]

        batches = optimizer.optimize_batches(tasks)

        assert len(batches) == 2
        assert all(len(batch.tasks) == 1 for batch in batches)

    def test_optimize_mixed_domains_separate_batches(self):
        """Test that different domains create separate batches"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="frontend1",
                name="Frontend Task",
                description="Frontend work",
                file_path="ui/component.tsx",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.FRONTEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
            Task(
                id="backend1",
                name="Backend Task",
                description="Backend work",
                file_path="api/endpoint.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
            Task(
                id="database1",
                name="Database Task",
                description="Database work",
                file_path="db/migration.sql",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.DATABASE,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
        ]

        batches = optimizer.optimize_batches(tasks)

        # Should create 3 separate batches (one per domain)
        assert len(batches) == 3

        domains = {batch.domain for batch in batches}
        assert TaskDomain.FRONTEND in domains
        assert TaskDomain.BACKEND in domains
        assert TaskDomain.DATABASE in domains

    def test_optimize_respects_max_time_limit(self):
        """Test that batches don't exceed MAX_BATCH_TIME"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id=f"task{i}",
                name=f"Long Task {i}",
                description="A long task",
                file_path=f"core/long{i}.py",
                estimated_minutes=180,  # 3 hours each
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
            for i in range(1, 3)
        ]

        batches = optimizer.optimize_batches(tasks)

        # 2 tasks * 180min = 360min > 240min max, so should split
        assert len(batches) == 2
        for batch in batches:
            assert batch.total_minutes <= BatchOptimizer.MAX_BATCH_TIME

    def test_validate_tasks_duplicate_ids_raises(self):
        """Test that duplicate task IDs raise error"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="duplicate",
                name="Task 1",
                description="Task",
                file_path="core/task.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
            Task(
                id="duplicate",  # Same ID
                name="Task 2",
                description="Task",
                file_path="core/task2.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
        ]

        with pytest.raises(ValueError, match="Duplicate task IDs"):
            optimizer.optimize_batches(tasks)

    def test_validate_tasks_invalid_duration_raises(self):
        """Test that invalid duration raises error"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="invalid",
                name="Invalid Task",
                description="Task",
                file_path="core/task.py",
                estimated_minutes=0,  # Invalid
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        with pytest.raises(ValueError, match="invalid duration"):
            optimizer.optimize_batches(tasks)

    def test_validate_batch_success(self):
        """Test validate_batch on valid batch"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Task",
                file_path="core/task.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        batch = TaskBatch(
            id=1,
            tasks=tasks,
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        is_valid, violations = optimizer.validate_batch(batch)
        assert is_valid
        assert len(violations) == 0

    def test_validate_batch_too_many_tasks(self):
        """Test validate_batch detects too many tasks"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id=f"task{i}",
                name=f"Task {i}",
                description="Task",
                file_path=f"core/task{i}.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
            for i in range(1, 5)  # 4 tasks (exceeds max 3)
        ]

        batch = TaskBatch(
            id=1,
            tasks=tasks,
            total_minutes=240,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        is_valid, violations = optimizer.validate_batch(batch)
        assert not is_valid
        assert any("has 4 tasks" in v for v in violations)

    def test_validate_batch_mixed_domains(self):
        """Test validate_batch detects mixed domains"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="frontend",
                name="Frontend Task",
                description="Task",
                file_path="ui/component.tsx",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.FRONTEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
            Task(
                id="backend",
                name="Backend Task",
                description="Task",
                file_path="api/endpoint.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
        ]

        batch = TaskBatch(
            id=1,
            tasks=tasks,
            total_minutes=120,
            domain=TaskDomain.FRONTEND,  # Doesn't match all tasks
            complexity_level=TaskComplexity.SIMPLE,
        )

        is_valid, violations = optimizer.validate_batch(batch)
        assert not is_valid
        assert any("mixes domains" in v for v in violations)

    def test_validate_batch_exceeds_time_limit(self):
        """Test validate_batch detects time limit violation"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="long",
                name="Long Task",
                description="Task",
                file_path="core/long.py",
                estimated_minutes=300,  # Exceeds 240 limit
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        batch = TaskBatch(
            id=1,
            tasks=tasks,
            total_minutes=300,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        is_valid, violations = optimizer.validate_batch(batch)
        assert not is_valid
        assert any("exceeds time limit" in v for v in violations)

    def test_get_batch_summary(self):
        """Test get_batch_summary generates readable summary"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="task1",
                name="Task One",
                description="Task",
                file_path="core/task.py",
                estimated_minutes=90,
                complexity=TaskComplexity.MEDIUM,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        batch = TaskBatch(
            id=1,
            tasks=tasks,
            total_minutes=90,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.MEDIUM,
        )

        summary = optimizer.get_batch_summary(batch)

        assert "Batch 1" in summary
        assert "backend domain" in summary
        assert "1 tasks" in summary
        assert "90min" in summary
        assert "medium" in summary
        assert "Task One" in summary

    def test_get_execution_plan_empty(self):
        """Test get_execution_plan with no batches"""
        optimizer = BatchOptimizer()
        plan = optimizer.get_execution_plan()
        assert "No batches created yet" in plan

    def test_get_execution_plan_with_batches(self):
        """Test get_execution_plan generates full plan"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id=f"task{i}",
                name=f"Task {i}",
                description="Task",
                file_path=f"core/task{i}.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
            for i in range(1, 4)
        ]

        optimizer.optimize_batches(tasks)
        plan = optimizer.get_execution_plan()

        assert "Execution Plan" in plan
        assert "1 batches" in plan
        assert "Total estimated time: 180 minutes" in plan
        assert "3.0 hours" in plan

    def test_is_coherent_addition_same_complexity(self):
        """Test coherence check allows same complexity"""
        optimizer = BatchOptimizer()
        batch_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Task",
                file_path="core/task1.py",
                estimated_minutes=60,
                complexity=TaskComplexity.MEDIUM,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        new_task = Task(
            id="task2",
            name="Task 2",
            description="Task",
            file_path="core/task2.py",
            estimated_minutes=60,
            complexity=TaskComplexity.MEDIUM,  # Same complexity
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Works"],
        )

        assert optimizer._is_coherent_addition(batch_tasks, new_task)

    def test_is_coherent_addition_adjacent_complexity(self):
        """Test coherence check allows adjacent complexity levels"""
        optimizer = BatchOptimizer()
        batch_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Task",
                file_path="core/task1.py",
                estimated_minutes=60,
                complexity=TaskComplexity.MEDIUM,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        new_task = Task(
            id="task2",
            name="Task 2",
            description="Task",
            file_path="core/task2.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,  # Adjacent complexity
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Works"],
        )

        assert optimizer._is_coherent_addition(batch_tasks, new_task)

    def test_is_coherent_addition_rejects_distant_complexity(self):
        """Test coherence check rejects distant complexity levels"""
        optimizer = BatchOptimizer()
        batch_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Task",
                file_path="core/task1.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        new_task = Task(
            id="task2",
            name="Task 2",
            description="Task",
            file_path="core/task2.py",
            estimated_minutes=120,
            complexity=TaskComplexity.CRITICAL,  # Too far from SIMPLE
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Works"],
        )

        assert not optimizer._is_coherent_addition(batch_tasks, new_task)

    def test_is_coherent_addition_rejects_different_domain(self):
        """Test coherence check rejects different domain"""
        optimizer = BatchOptimizer()
        batch_tasks = [
            Task(
                id="task1",
                name="Task 1",
                description="Task",
                file_path="core/task1.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            )
        ]

        new_task = Task(
            id="task2",
            name="Task 2",
            description="Task",
            file_path="ui/component.tsx",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.FRONTEND,  # Different domain
            dependencies=[],
            acceptance_criteria=["Works"],
        )

        assert not optimizer._is_coherent_addition(batch_tasks, new_task)

    def test_complexity_sorting_prioritizes_critical(self):
        """Test that critical tasks are processed first"""
        optimizer = BatchOptimizer()
        tasks = [
            Task(
                id="simple",
                name="Simple Task",
                description="Task",
                file_path="core/simple.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
            Task(
                id="critical",
                name="Critical Task",
                description="Task",
                file_path="core/critical.py",
                estimated_minutes=120,
                complexity=TaskComplexity.CRITICAL,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
            Task(
                id="medium",
                name="Medium Task",
                description="Task",
                file_path="core/medium.py",
                estimated_minutes=90,
                complexity=TaskComplexity.MEDIUM,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Works"],
            ),
        ]

        batches = optimizer.optimize_batches(tasks)

        # Critical should be in first batch
        assert batches[0].tasks[0].id == "critical"
