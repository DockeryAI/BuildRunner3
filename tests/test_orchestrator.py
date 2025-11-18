"""Tests for TaskOrchestrator"""

import pytest
from core.orchestrator import TaskOrchestrator, OrchestrationStatus


class TestTaskOrchestrator:
    def test_init(self):
        orch = TaskOrchestrator()
        assert orch.status == OrchestrationStatus.IDLE
        assert orch.batches_executed == 0

    def test_execute_batch_empty_tasks(self):
        orch = TaskOrchestrator()
        result = orch.execute_batch([])
        assert result["success"] is False

    def test_pause_and_resume(self):
        orch = TaskOrchestrator()
        orch.status = OrchestrationStatus.RUNNING
        orch.pause()
        assert orch.status == OrchestrationStatus.PAUSED
        orch.resume()
        assert orch.status == OrchestrationStatus.RUNNING

    def test_stop(self):
        orch = TaskOrchestrator()
        orch.status = OrchestrationStatus.RUNNING
        orch.stop()
        assert orch.status == OrchestrationStatus.IDLE

    def test_get_status(self):
        orch = TaskOrchestrator()
        status = orch.get_status()
        assert "status" in status
        assert "batches_executed" in status

    def test_reset(self):
        orch = TaskOrchestrator()
        orch.batches_executed = 5
        orch.tasks_completed = 10
        orch.reset()
        assert orch.batches_executed == 0
        assert orch.tasks_completed == 0
