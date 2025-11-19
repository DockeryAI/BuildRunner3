"""
Tests for Agent Commands - CLI integration tests

Tests:
- br agent run
- br agent status
- br agent stats
- br agent list
- br agent cancel
- br agent retry
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from typer.testing import CliRunner

from cli.agent_commands import agent_app
from core.agents import AgentType, AgentAssignment, AgentResponse, AgentStatus
from core.task_queue import QueuedTask, TaskStatus


runner = CliRunner()


@pytest.fixture
def sample_task():
    """Create sample task"""
    return QueuedTask(
        id="test-task-001",
        name="Test Task",
        description="Test task description",
        file_path="test.py",
        estimated_minutes=60,
        complexity="simple",
        domain="backend",
        status=TaskStatus.READY,
    )


@pytest.fixture
def mock_bridge():
    """Create mock agent bridge"""
    bridge = MagicMock()
    bridge.get_stats.return_value = {
        'total_dispatched': 10,
        'total_completed': 9,
        'total_failed': 1,
        'total_retries': 2,
        'success_rate': 0.9,
        'by_agent_type': {'implement': 5, 'test': 3, 'review': 2},
        'by_status': {'completed': 9, 'failed': 1},
    }

    # Create sample assignments
    assignment = AgentAssignment(
        assignment_id="assign-001",
        task_id="test-task-001",
        agent_type=AgentType.IMPLEMENT,
        created_at=datetime.now(),
        started_at=datetime.now(),
        completed_at=datetime.now(),
        response=AgentResponse(
            agent_type=AgentType.IMPLEMENT,
            task_id="test-task-001",
            status=AgentStatus.COMPLETED,
            success=True,
            output="Task completed",
            files_created=["test.py"],
        ),
    )

    bridge.list_assignments.return_value = [assignment]
    bridge.get_assignment.return_value = assignment
    bridge.get_response.return_value = assignment.response

    return bridge


class TestAgentRun:
    """Test br agent run command"""

    @patch('cli.agent_commands.get_agent_bridge')
    @patch('cli.agent_commands.TaskQueue')
    def test_agent_run_success(self, mock_task_queue_class, mock_get_bridge, sample_task):
        """Test successful agent run"""
        # Setup mocks
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge

        task_queue = MagicMock()
        mock_task_queue_class.return_value = task_queue
        task_queue.get_task.return_value = sample_task

        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="test-task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
            response=AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="test-task-001",
                status=AgentStatus.COMPLETED,
                success=True,
                output="Completed",
            ),
        )

        mock_bridge.dispatch_task.return_value = assignment

        result = runner.invoke(
            agent_app,
            ["run", "test-task-001", "--type", "implement"],
        )

        assert result.exit_code == 0
        output_lower = result.stdout.lower()
        assert "dispatched" in output_lower or "success" in output_lower or "task id" in output_lower

    @patch('cli.agent_commands.get_agent_bridge')
    @patch('cli.agent_commands.TaskQueue')
    def test_agent_run_invalid_type(self, mock_task_queue_class, mock_get_bridge):
        """Test agent run with invalid agent type"""
        result = runner.invoke(
            agent_app,
            ["run", "test-task-001", "--type", "invalid"],
        )

        assert result.exit_code == 1
        assert "invalid agent type" in result.stdout.lower()

    @patch('cli.agent_commands.get_agent_bridge')
    @patch('cli.agent_commands.TaskQueue')
    def test_agent_run_task_not_found(self, mock_task_queue_class, mock_get_bridge):
        """Test agent run when task not found"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge

        task_queue = MagicMock()
        mock_task_queue_class.return_value = task_queue
        task_queue.get_task.return_value = None

        result = runner.invoke(
            agent_app,
            ["run", "nonexistent", "--type", "implement"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @patch('cli.agent_commands.get_agent_bridge')
    @patch('cli.agent_commands.TaskQueue')
    def test_agent_run_with_prompt(self, mock_task_queue_class, mock_get_bridge, sample_task):
        """Test agent run with custom prompt"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge

        task_queue = MagicMock()
        mock_task_queue_class.return_value = task_queue
        task_queue.get_task.return_value = sample_task

        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="test-task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
            response=AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="test-task-001",
                status=AgentStatus.COMPLETED,
                success=True,
                output="Completed",
            ),
        )

        mock_bridge.dispatch_task.return_value = assignment

        result = runner.invoke(
            agent_app,
            [
                "run",
                "test-task-001",
                "--type",
                "implement",
                "--prompt",
                "Custom prompt",
            ],
        )

        assert result.exit_code == 0

    @patch('cli.agent_commands.get_agent_bridge')
    @patch('cli.agent_commands.TaskQueue')
    def test_agent_run_with_context(self, mock_task_queue_class, mock_get_bridge, sample_task):
        """Test agent run with context"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge

        task_queue = MagicMock()
        mock_task_queue_class.return_value = task_queue
        task_queue.get_task.return_value = sample_task

        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="test-task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
            response=AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="test-task-001",
                status=AgentStatus.COMPLETED,
                success=True,
                output="Completed",
            ),
        )

        mock_bridge.dispatch_task.return_value = assignment

        result = runner.invoke(
            agent_app,
            [
                "run",
                "test-task-001",
                "--type",
                "test",
                "--context",
                "Test context",
            ],
        )

        assert result.exit_code == 0


class TestAgentStatus:
    """Test br agent status command"""

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_status_with_id(self, mock_get_bridge, mock_bridge):
        """Test agent status with specific ID"""
        mock_get_bridge.return_value = mock_bridge

        result = runner.invoke(
            agent_app,
            ["status", "assign-001"],
        )

        assert result.exit_code == 0
        assert "assign-001" in result.stdout
        assert "Status" in result.stdout

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_status_no_id(self, mock_get_bridge, mock_bridge):
        """Test agent status without ID (shows latest)"""
        mock_get_bridge.return_value = mock_bridge

        result = runner.invoke(
            agent_app,
            ["status"],
        )

        assert result.exit_code == 0

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_status_not_found(self, mock_get_bridge):
        """Test agent status for non-existent assignment"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge
        mock_bridge.get_assignment.return_value = None
        mock_bridge.list_assignments.return_value = []

        result = runner.invoke(
            agent_app,
            ["status", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestAgentStats:
    """Test br agent stats command"""

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_stats(self, mock_get_bridge, mock_bridge):
        """Test agent stats command"""
        mock_get_bridge.return_value = mock_bridge

        result = runner.invoke(
            agent_app,
            ["stats"],
        )

        assert result.exit_code == 0
        assert "statistics" in result.stdout.lower() or "stats" in result.stdout.lower()
        assert "10" in result.stdout  # total_dispatched
        assert "0.9" in result.stdout or "90" in result.stdout  # success_rate

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_stats_shows_by_type(self, mock_get_bridge, mock_bridge):
        """Test that stats shows breakdown by agent type"""
        mock_get_bridge.return_value = mock_bridge

        result = runner.invoke(
            agent_app,
            ["stats"],
        )

        assert result.exit_code == 0
        # Check for agent type breakdown
        assert "implement" in result.stdout.lower() or "5" in result.stdout


class TestAgentList:
    """Test br agent list command"""

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_list(self, mock_get_bridge, mock_bridge):
        """Test agent list command"""
        mock_get_bridge.return_value = mock_bridge

        result = runner.invoke(
            agent_app,
            ["list"],
        )

        assert result.exit_code == 0
        assert "assign-001" in result.stdout
        assert "recent" in result.stdout.lower() or "assignments" in result.stdout.lower()

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_list_with_limit(self, mock_get_bridge, mock_bridge):
        """Test agent list with limit"""
        mock_get_bridge.return_value = mock_bridge

        result = runner.invoke(
            agent_app,
            ["list", "--limit", "5"],
        )

        assert result.exit_code == 0
        mock_bridge.list_assignments.assert_called_with(limit=5)

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_list_empty(self, mock_get_bridge):
        """Test agent list when empty"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge
        mock_bridge.list_assignments.return_value = []

        result = runner.invoke(
            agent_app,
            ["list"],
        )

        assert result.exit_code == 0
        assert "no assignments" in result.stdout.lower()


class TestAgentCancel:
    """Test br agent cancel command"""

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_cancel_success(self, mock_get_bridge):
        """Test successful agent cancellation"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge
        mock_bridge.cancel_assignment.return_value = True

        result = runner.invoke(
            agent_app,
            ["cancel", "assign-001"],
        )

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_cancel_not_found(self, mock_get_bridge):
        """Test cancelling non-existent assignment"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge
        mock_bridge.cancel_assignment.return_value = False

        result = runner.invoke(
            agent_app,
            ["cancel", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()


class TestAgentRetry:
    """Test br agent retry command"""

    @patch('cli.agent_commands.get_agent_bridge')
    @patch('cli.agent_commands.TaskQueue')
    def test_agent_retry_success(self, mock_task_queue_class, mock_get_bridge, sample_task):
        """Test successful agent retry"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge

        task_queue = MagicMock()
        mock_task_queue_class.return_value = task_queue
        task_queue.get_task.return_value = sample_task

        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="test-task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
        )

        new_assignment = AgentAssignment(
            assignment_id="assign-002",
            task_id="test-task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
            response=AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="test-task-001",
                status=AgentStatus.COMPLETED,
                success=True,
                output="Retried successfully",
            ),
        )

        mock_bridge.get_assignment.return_value = assignment
        mock_bridge.retry_assignment.return_value = new_assignment

        result = runner.invoke(
            agent_app,
            ["retry", "assign-001"],
        )

        assert result.exit_code == 0
        assert "retried" in result.stdout.lower()

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_retry_not_found(self, mock_get_bridge):
        """Test retrying non-existent assignment"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge
        mock_bridge.get_assignment.return_value = None

        result = runner.invoke(
            agent_app,
            ["retry", "nonexistent"],
        )

        assert result.exit_code == 1
        assert "not found" in result.stdout.lower()

    @patch('cli.agent_commands.get_agent_bridge')
    @patch('cli.agent_commands.TaskQueue')
    def test_agent_retry_with_prompt(self, mock_task_queue_class, mock_get_bridge, sample_task):
        """Test agent retry with custom prompt"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge

        task_queue = MagicMock()
        mock_task_queue_class.return_value = task_queue
        task_queue.get_task.return_value = sample_task

        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="test-task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
        )

        mock_bridge.get_assignment.return_value = assignment
        mock_bridge.retry_assignment.return_value = assignment

        result = runner.invoke(
            agent_app,
            ["retry", "assign-001", "--prompt", "New prompt"],
        )

        assert result.exit_code == 0


class TestAgentCommandsEdgeCases:
    """Test edge cases and error conditions"""

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_stats_no_data(self, mock_get_bridge):
        """Test stats when no data available"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge
        mock_bridge.get_stats.return_value = {
            'total_dispatched': 0,
            'total_completed': 0,
            'total_failed': 0,
            'total_retries': 0,
            'success_rate': 0,
            'by_agent_type': {},
            'by_status': {},
        }
        mock_bridge.list_assignments.return_value = []

        result = runner.invoke(
            agent_app,
            ["stats"],
        )

        assert result.exit_code == 0

    @patch('cli.agent_commands.get_agent_bridge')
    def test_agent_run_with_all_options(self, mock_get_bridge):
        """Test agent run with all available options"""
        mock_bridge = MagicMock()
        mock_get_bridge.return_value = mock_bridge

        with patch('cli.agent_commands.TaskQueue') as mock_task_queue_class:
            task_queue = MagicMock()
            mock_task_queue_class.return_value = task_queue

            sample = QueuedTask(
                id="test",
                name="Test",
                description="Test",
                file_path="test.py",
                estimated_minutes=60,
                complexity="simple",
                domain="backend",
                status=TaskStatus.READY,
            )
            task_queue.get_task.return_value = sample

            mock_bridge.dispatch_task.return_value = AgentAssignment(
                assignment_id="a1",
                task_id="test",
                agent_type=AgentType.TEST,
                created_at=datetime.now(),
                response=AgentResponse(
                    agent_type=AgentType.TEST,
                    task_id="test",
                    status=AgentStatus.COMPLETED,
                    success=True,
                    output="Done",
                ),
            )

            result = runner.invoke(
                agent_app,
                [
                    "run",
                    "test",
                    "--type",
                    "test",
                    "--prompt",
                    "Test prompt",
                    "--context",
                    "Test context",
                    "--no-wait",
                ],
            )

            assert result.exit_code == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=cli.agent_commands", "--cov-report=term-missing"])
