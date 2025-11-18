"""
Tests for TaskQueue

Ensures proper task queuing, status tracking, dependency management,
and completion handling.
"""

import pytest
from datetime import datetime, timedelta
from core.task_queue import TaskQueue, QueuedTask, TaskStatus


class TestQueuedTask:
    """Test suite for QueuedTask"""

    def test_init_defaults(self):
        """Test QueuedTask initialization with defaults"""
        task = QueuedTask(
            id="task1",
            name="Test Task",
            description="Description",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        assert task.id == "task1"
        assert task.status == TaskStatus.PENDING
        assert task.dependencies == []
        assert task.started_at is None
        assert task.completed_at is None
        assert task.retry_count == 0

    def test_duration_minutes_not_started(self):
        """Test duration when task not started"""
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        assert task.duration_minutes() is None

    def test_duration_minutes_completed(self):
        """Test duration calculation for completed task"""
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        task.started_at = datetime.now()
        task.completed_at = task.started_at + timedelta(minutes=45)

        assert task.duration_minutes() == 45


class TestTaskQueue:
    """Test suite for TaskQueue"""

    def test_init(self):
        """Test TaskQueue initialization"""
        queue = TaskQueue()
        assert queue.tasks == {}
        assert queue.execution_order == []
        assert queue.max_retries == 3
        assert queue.tasks_queued == 0

    def test_add_task(self):
        """Test adding a task to queue"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test Task",
            description="Description",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        result = queue.add_task(task)

        assert result is True
        assert "task1" in queue.tasks
        assert queue.tasks_queued == 1

    def test_add_task_duplicate(self):
        """Test adding duplicate task returns False"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        result = queue.add_task(task)

        assert result is False
        assert queue.tasks_queued == 1

    def test_add_task_with_no_dependencies_becomes_ready(self):
        """Test task with no dependencies is marked ready"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
            dependencies=[],
        )

        queue.add_task(task)

        assert queue.tasks["task1"].status == TaskStatus.READY
        assert "task1" in queue.execution_order

    def test_add_tasks_multiple(self):
        """Test adding multiple tasks"""
        queue = TaskQueue()
        tasks = [
            QueuedTask(
                id=f"task{i}",
                name=f"Task {i}",
                description="Desc",
                file_path=f"core/test{i}.py",
                estimated_minutes=60,
                complexity="simple",
                domain="backend",
            )
            for i in range(3)
        ]

        added = queue.add_tasks(tasks)

        assert added == 3
        assert len(queue.tasks) == 3

    def test_get_next_task_empty_queue(self):
        """Test getting next task from empty queue"""
        queue = TaskQueue()
        task = queue.get_next_task()
        assert task is None

    def test_get_next_task_returns_ready_task(self):
        """Test getting next ready task"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        next_task = queue.get_next_task()

        assert next_task is not None
        assert next_task.id == "task1"

    def test_start_task(self):
        """Test starting a task"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        result = queue.start_task("task1")

        assert result is True
        assert queue.tasks["task1"].status == TaskStatus.IN_PROGRESS
        assert queue.tasks["task1"].started_at is not None

    def test_start_task_not_found(self):
        """Test starting non-existent task"""
        queue = TaskQueue()
        result = queue.start_task("nonexistent")
        assert result is False

    def test_start_task_not_ready(self):
        """Test starting task that's not ready"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
            dependencies=["task0"],
        )

        queue.add_task(task)
        result = queue.start_task("task1")

        assert result is False

    def test_complete_task(self):
        """Test completing a task"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        queue.start_task("task1")
        result = queue.complete_task("task1")

        assert result is True
        assert queue.tasks["task1"].status == TaskStatus.COMPLETED
        assert queue.tasks["task1"].completed_at is not None
        assert queue.tasks_completed == 1

    def test_complete_task_unblocks_dependent(self):
        """Test completing task unblocks dependent tasks"""
        queue = TaskQueue()
        task1 = QueuedTask(
            id="task1",
            name="Task 1",
            description="Desc",
            file_path="core/test1.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )
        task2 = QueuedTask(
            id="task2",
            name="Task 2",
            description="Desc",
            file_path="core/test2.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
            dependencies=["task1"],
        )

        queue.add_task(task1)
        queue.add_task(task2)

        # task2 should be blocked
        assert queue.tasks["task2"].status in [TaskStatus.PENDING, TaskStatus.BLOCKED]

        # Complete task1
        queue.start_task("task1")
        queue.complete_task("task1")

        # task2 should now be ready
        assert queue.tasks["task2"].status == TaskStatus.READY

    def test_fail_task_with_retries(self):
        """Test failing task allows retry"""
        queue = TaskQueue(max_retries=3)
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        queue.start_task("task1")
        should_retry = queue.fail_task("task1", "Test error")

        assert should_retry is True
        assert queue.tasks["task1"].status == TaskStatus.READY
        assert queue.tasks["task1"].retry_count == 1
        assert queue.tasks["task1"].error_message == "Test error"

    def test_fail_task_max_retries_exceeded(self):
        """Test failing task after max retries"""
        queue = TaskQueue(max_retries=2)
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)

        # Fail twice (should retry)
        queue.start_task("task1")
        queue.fail_task("task1", "Error 1")
        queue.start_task("task1")
        queue.fail_task("task1", "Error 2")

        # Third failure should mark as failed
        queue.start_task("task1")
        should_retry = queue.fail_task("task1", "Error 3")

        assert should_retry is False
        assert queue.tasks["task1"].status == TaskStatus.FAILED
        assert queue.tasks_failed == 1

    def test_skip_task(self):
        """Test skipping a task"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        result = queue.skip_task("task1", "Not needed")

        assert result is True
        assert queue.tasks["task1"].status == TaskStatus.SKIPPED
        assert "Skipped" in queue.tasks["task1"].error_message

    def test_get_task(self):
        """Test getting task by ID"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        retrieved = queue.get_task("task1")

        assert retrieved is not None
        assert retrieved.id == "task1"

    def test_get_tasks_by_status(self):
        """Test getting tasks by status"""
        queue = TaskQueue()
        task1 = QueuedTask(id="task1", name="Test 1", description="Desc", file_path="core/test1.py", estimated_minutes=60, complexity="simple", domain="backend")
        task2 = QueuedTask(id="task2", name="Test 2", description="Desc", file_path="core/test2.py", estimated_minutes=60, complexity="simple", domain="backend")

        queue.add_task(task1)
        queue.add_task(task2)
        queue.start_task("task1")

        in_progress = queue.get_tasks_by_status(TaskStatus.IN_PROGRESS)
        ready = queue.get_tasks_by_status(TaskStatus.READY)

        assert len(in_progress) == 1
        assert len(ready) == 1

    def test_get_pending_tasks(self):
        """Test getting pending tasks"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
            dependencies=["task0"],
        )

        queue.add_task(task)
        pending = queue.get_pending_tasks()

        # Task with unmet dependencies stays pending until update is called
        assert len(pending) == 1

    def test_get_ready_tasks(self):
        """Test getting ready tasks"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        ready = queue.get_ready_tasks()

        assert len(ready) == 1

    def test_is_complete_empty_queue(self):
        """Test is_complete on empty queue"""
        queue = TaskQueue()
        assert queue.is_complete() is True

    def test_is_complete_with_pending(self):
        """Test is_complete with pending tasks"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        assert queue.is_complete() is False

    def test_is_complete_all_done(self):
        """Test is_complete when all tasks done"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        queue.start_task("task1")
        queue.complete_task("task1")

        assert queue.is_complete() is True

    def test_get_progress(self):
        """Test getting progress statistics"""
        queue = TaskQueue()
        task1 = QueuedTask(id="task1", name="Test 1", description="Desc", file_path="core/test1.py", estimated_minutes=60, complexity="simple", domain="backend")
        task2 = QueuedTask(id="task2", name="Test 2", description="Desc", file_path="core/test2.py", estimated_minutes=60, complexity="simple", domain="backend")

        queue.add_task(task1)
        queue.add_task(task2)
        queue.start_task("task1")
        queue.complete_task("task1")

        progress = queue.get_progress()

        assert progress["total"] == 2
        assert progress["completed"] == 1
        assert progress["percent_complete"] == 50.0

    def test_clear(self):
        """Test clearing queue"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        queue.clear()

        assert len(queue.tasks) == 0
        assert queue.tasks_queued == 0

    def test_get_stats(self):
        """Test getting queue statistics"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        stats = queue.get_stats()

        assert "tasks_queued" in stats
        assert "tasks_completed" in stats
        assert "current_queue_size" in stats
        assert stats["tasks_queued"] == 1

    def test_get_summary(self):
        """Test getting human-readable summary"""
        queue = TaskQueue()
        task = QueuedTask(
            id="task1",
            name="Test",
            description="Desc",
            file_path="core/test.py",
            estimated_minutes=60,
            complexity="simple",
            domain="backend",
        )

        queue.add_task(task)
        summary = queue.get_summary()

        assert "Task Queue Summary" in summary
        assert "Total: 1 tasks" in summary

    def test_get_estimated_time_remaining(self):
        """Test estimated time remaining calculation"""
        queue = TaskQueue()
        task1 = QueuedTask(id="task1", name="Test 1", description="Desc", file_path="core/test1.py", estimated_minutes=60, complexity="simple", domain="backend")
        task2 = QueuedTask(id="task2", name="Test 2", description="Desc", file_path="core/test2.py", estimated_minutes=90, complexity="simple", domain="backend")

        queue.add_task(task1)
        queue.add_task(task2)
        queue.start_task("task1")
        queue.complete_task("task1")

        # Only task2 remaining
        remaining = queue.get_estimated_time_remaining()
        assert remaining == 90

    def test_complex_dependency_chain(self):
        """Test complex dependency chain execution"""
        queue = TaskQueue()

        # Create dependency chain: task1 -> task2 -> task3
        task1 = QueuedTask(id="task1", name="Task 1", description="Desc", file_path="core/test1.py", estimated_minutes=60, complexity="simple", domain="backend")
        task2 = QueuedTask(id="task2", name="Task 2", description="Desc", file_path="core/test2.py", estimated_minutes=60, complexity="simple", domain="backend", dependencies=["task1"])
        task3 = QueuedTask(id="task3", name="Task 3", description="Desc", file_path="core/test3.py", estimated_minutes=60, complexity="simple", domain="backend", dependencies=["task2"])

        queue.add_task(task1)
        queue.add_task(task2)
        queue.add_task(task3)

        # Only task1 should be ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "task1"

        # Complete task1
        queue.start_task("task1")
        queue.complete_task("task1")

        # Now task2 should be ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "task2"

        # Complete task2
        queue.start_task("task2")
        queue.complete_task("task2")

        # Now task3 should be ready
        ready = queue.get_ready_tasks()
        assert len(ready) == 1
        assert ready[0].id == "task3"
