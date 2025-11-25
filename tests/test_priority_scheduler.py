"""Tests for PriorityScheduler"""

import pytest
from core.priority_scheduler import PriorityScheduler, SchedulingStrategy, ScheduledTask
from dataclasses import dataclass


@dataclass
class MockTask:
    """Mock task for testing"""

    id: str
    dependencies: list
    estimated_minutes: int
    priority: int = 5
    critical_path: bool = False


class TestPriorityScheduler:
    def test_init(self):
        scheduler = PriorityScheduler()
        assert scheduler.strategy == SchedulingStrategy.PRIORITY_FIRST

    def test_calculate_priority(self):
        scheduler = PriorityScheduler()
        score = scheduler.calculate_priority(
            task_id="task1",
            base_priority=8,
            dependencies_count=0,
            dependents_count=3,
            estimated_minutes=60,
            is_critical_path=False,
        )
        assert score > 0
        assert "task1" in scheduler.task_priorities

    def test_schedule_empty_tasks(self):
        scheduler = PriorityScheduler()
        result = scheduler.schedule_tasks([])
        assert result == []

    def test_schedule_single_task(self):
        scheduler = PriorityScheduler()
        task = MockTask(id="task1", dependencies=[], estimated_minutes=60)
        result = scheduler.schedule_tasks([task])
        assert result == ["task1"]

    def test_schedule_multiple_tasks_by_priority(self):
        scheduler = PriorityScheduler()
        tasks = [
            MockTask(id="task1", dependencies=[], estimated_minutes=60, priority=3),
            MockTask(id="task2", dependencies=[], estimated_minutes=60, priority=8),
            MockTask(id="task3", dependencies=[], estimated_minutes=60, priority=5),
        ]
        result = scheduler.schedule_tasks(tasks)
        # Higher priority first
        assert result[0] == "task2"

    def test_schedule_with_dependencies(self):
        scheduler = PriorityScheduler()
        tasks = [
            MockTask(id="task1", dependencies=[], estimated_minutes=60, priority=5),
            MockTask(id="task2", dependencies=["task1"], estimated_minutes=60, priority=5),
        ]
        result = scheduler.schedule_tasks(tasks)
        # task1 (no deps) should be higher priority
        assert result[0] == "task1"

    def test_get_priority_score(self):
        scheduler = PriorityScheduler()
        scheduler.calculate_priority("task1", 5, 0, 0, 60)
        score = scheduler.get_priority_score("task1")
        assert score is not None

    def test_get_stats(self):
        scheduler = PriorityScheduler()
        task = MockTask(id="task1", dependencies=[], estimated_minutes=60)
        scheduler.schedule_tasks([task])
        stats = scheduler.get_stats()
        assert stats["tasks_scheduled"] == 1
        assert "average_priority" in stats
