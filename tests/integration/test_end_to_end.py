"""
End-to-end integration tests

Tests complete workflows with all systems integrated.
"""

import pytest
from core.orchestrator import TaskOrchestrator
from core.telemetry import EventType
from core.integrations import (
    get_event_summary,
    get_routing_summary,
    get_parallel_summary,
)


class TestEndToEndIntegration:
    """Test complete end-to-end workflows"""

    @pytest.fixture
    def full_orchestrator(self):
        """Create orchestrator with all integrations enabled"""
        return TaskOrchestrator(
            enable_telemetry=True,
            enable_routing=True,
            enable_parallel=True,
        )

    def test_complete_batch_execution_with_all_integrations(self, full_orchestrator):
        """Test executing a batch with telemetry, routing, and parallel all enabled"""
        tasks = [
            {"id": "task1", "name": "Simple Task", "description": "Basic CRUD operation"},
            {
                "id": "task2",
                "name": "Complex Task",
                "description": "Implement authentication system",
            },
        ]

        result = full_orchestrator.execute_batch(tasks)

        # Verify execution succeeded
        assert result["success"] is True
        assert result["batches_completed"] >= 1

        # Verify telemetry collected events
        assert full_orchestrator.event_collector is not None
        events = full_orchestrator.event_collector.get_recent(count=100)
        assert len(events) > 0

        # Verify routing was used
        assert full_orchestrator.complexity_estimator is not None
        assert full_orchestrator.model_selector is not None

    def test_parallel_execution_with_telemetry(self, full_orchestrator):
        """Test parallel execution emits telemetry events"""
        tasks = [
            {"id": "task1", "name": "Task 1", "description": "Test"},
            {"id": "task2", "name": "Task 2", "description": "Test"},
        ]

        result = full_orchestrator.execute_parallel(tasks, session_name="telemetry_test")

        # Verify execution succeeded
        assert result["success"] is True

        # Verify telemetry was emitted
        events = full_orchestrator.event_collector.get_recent(count=100)
        batch_events = [e for e in events if e.event_type == EventType.BUILD_STARTED]
        assert len(batch_events) > 0

    def test_integration_status_reports_all_systems(self, full_orchestrator):
        """Test that integration status reports all enabled systems"""
        status = full_orchestrator.get_integration_status()

        assert status["telemetry_enabled"] is True
        assert status["routing_enabled"] is True
        assert status["parallel_enabled"] is True
        assert status["cost_tracking_enabled"] is True
        assert status["dashboard_enabled"] is True

    def test_orchestrator_with_selective_integrations(self):
        """Test orchestrator with only some integrations enabled"""
        orch = TaskOrchestrator(
            enable_telemetry=True,
            enable_routing=False,
            enable_parallel=False,
        )

        status = orch.get_integration_status()

        assert status["telemetry_enabled"] is True
        assert status["routing_enabled"] is False
        assert status["parallel_enabled"] is False

    def test_telemetry_and_routing_integration(self):
        """Test telemetry tracks routing decisions"""
        orch = TaskOrchestrator(
            enable_telemetry=True,
            enable_routing=True,
            enable_parallel=False,
        )

        tasks = [
            {"id": "task1", "name": "Test", "description": "Simple task"},
        ]

        result = orch.execute_batch(tasks)

        assert result["success"] is True

        # Check that routing decisions were tracked in telemetry
        events = orch.event_collector.get_recent(count=100)
        from core.telemetry import TaskEvent

        task_events = [e for e in events if isinstance(e, TaskEvent)]

        # At least one task event should have model metadata
        assert any("model" in e.metadata for e in task_events if hasattr(e, "metadata"))

    def test_error_handling_across_integrations(self, full_orchestrator):
        """Test that errors are properly handled across all integrations"""
        # Test with empty tasks - should fail gracefully
        result = full_orchestrator.execute_batch([])

        assert result["success"] is False
        assert "error" in result

    def test_orchestrator_statistics_tracking(self, full_orchestrator):
        """Test that orchestrator tracks statistics correctly"""
        tasks = [
            {"id": "task1", "name": "Task 1", "description": "Test"},
            {"id": "task2", "name": "Task 2", "description": "Test"},
        ]

        initial_status = full_orchestrator.get_status()

        result = full_orchestrator.execute_batch(tasks)
        assert result["success"] is True

        final_status = full_orchestrator.get_status()

        # Verify statistics were updated
        assert final_status["batches_executed"] > initial_status["batches_executed"]
        assert final_status["tasks_completed"] > initial_status["tasks_completed"]

    def test_reset_clears_state(self, full_orchestrator):
        """Test that reset clears orchestrator state"""
        tasks = [{"id": "task1", "name": "Test", "description": "Test"}]

        full_orchestrator.execute_batch(tasks)

        # Verify state was updated
        status_before = full_orchestrator.get_status()
        assert status_before["batches_executed"] > 0

        # Reset
        full_orchestrator.reset()

        # Verify state was cleared
        status_after = full_orchestrator.get_status()
        assert status_after["batches_executed"] == 0
        assert status_after["tasks_completed"] == 0
