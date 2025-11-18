"""
Integration tests for parallel execution system
"""
import pytest
from core.orchestrator import TaskOrchestrator
from core.integrations.parallel_integration import (
    integrate_parallel,
    create_parallel_session,
    get_session_status,
    get_parallel_summary,
)


class TestParallelIntegration:
    """Test parallel execution integration with orchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with parallel execution enabled"""
        return TaskOrchestrator(
            enable_telemetry=False,
            enable_routing=False,
            enable_parallel=True,
            max_concurrent_sessions=4,
        )

    @pytest.fixture
    def orchestrator_without_parallel(self):
        """Create orchestrator without parallel execution"""
        return TaskOrchestrator(
            enable_telemetry=False,
            enable_routing=False,
            enable_parallel=False,
        )

    def test_integrate_parallel_creates_components(self, orchestrator):
        """Test that parallel integration creates session manager and coordinator"""
        assert orchestrator.session_manager is not None
        assert orchestrator.worker_coordinator is not None
        assert orchestrator.dashboard is not None

    def test_orchestrator_without_parallel_has_no_components(self, orchestrator_without_parallel):
        """Test that disabling parallel doesn't create components"""
        assert orchestrator_without_parallel.session_manager is None
        assert orchestrator_without_parallel.worker_coordinator is None
        assert orchestrator_without_parallel.dashboard is None

    def test_execute_parallel_creates_session(self, orchestrator):
        """Test that executing tasks in parallel creates a session"""
        tasks = [
            {'id': 'task1', 'name': 'Task 1', 'description': 'Test'},
            {'id': 'task2', 'name': 'Task 2', 'description': 'Test'},
        ]

        result = orchestrator.execute_parallel(tasks, session_name="test_session")

        assert result['success'] is True
        assert 'session_id' in result
        assert result['session_name'] == "test_session"
        assert result['task_count'] == 2

    def test_execute_parallel_without_support_fails(self, orchestrator_without_parallel):
        """Test that parallel execution fails when not enabled"""
        tasks = [{'id': 'task1', 'name': 'Task', 'description': 'Test'}]

        result = orchestrator_without_parallel.execute_parallel(tasks)

        assert result['success'] is False
        assert 'error' in result
        assert 'not enabled' in result['error'].lower()

    def test_create_parallel_session(self, orchestrator):
        """Test creating a parallel session"""
        session = create_parallel_session(
            orchestrator.session_manager,
            session_name="test_session",
            metadata={'test': 'data'},
        )

        assert session is not None
        assert hasattr(session, 'session_id')
        assert hasattr(session, 'name')

    def test_get_session_status(self, orchestrator):
        """Test getting session status"""
        # Create a session
        session = create_parallel_session(
            orchestrator.session_manager,
            session_name="status_test",
        )

        # Get status
        status = get_session_status(
            orchestrator.session_manager,
            session.session_id,
        )

        assert status['found'] is True
        assert status['session_id'] == session.session_id
        assert 'status' in status

    def test_get_parallel_summary(self, orchestrator):
        """Test getting parallel execution summary"""
        # Create some sessions
        create_parallel_session(orchestrator.session_manager, session_name="session1")
        create_parallel_session(orchestrator.session_manager, session_name="session2")

        summary = get_parallel_summary(
            orchestrator.session_manager,
            orchestrator.worker_coordinator,
        )

        assert 'total_sessions' in summary
        assert 'total_workers' in summary
        assert summary['total_sessions'] >= 2
