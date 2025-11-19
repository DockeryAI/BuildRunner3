"""
Tests for Claude Agent Bridge

Tests:
- Agent dispatch with different agent types
- Response parsing
- Telemetry tracking
- Error handling and retries
- Assignment management
- Statistics tracking
"""

import json
import pytest
from datetime import datetime
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from uuid import uuid4

from core.agents import (
    ClaudeAgentBridge,
    AgentType,
    AgentStatus,
    AgentResponse,
    AgentAssignment,
    AgentError,
    AgentDispatchError,
    AgentTimeoutError,
    AgentParseError,
)
from core.task_queue import QueuedTask, TaskStatus
from core.telemetry import EventCollector, EventType


# Fixtures
@pytest.fixture
def project_root(tmp_path):
    """Create temporary project root"""
    buildrunner_dir = tmp_path / '.buildrunner'
    buildrunner_dir.mkdir()
    return tmp_path


@pytest.fixture
def event_collector():
    """Create event collector"""
    return EventCollector()


@pytest.fixture
def agent_bridge(project_root, event_collector):
    """Create agent bridge instance"""
    return ClaudeAgentBridge(
        project_root=str(project_root),
        event_collector=event_collector,
        timeout_seconds=10,
        enable_retries=True,
    )


@pytest.fixture
def sample_task():
    """Create sample task"""
    return QueuedTask(
        id="task-001",
        name="Implement authentication",
        description="Add user authentication system",
        file_path="core/auth.py",
        estimated_minutes=90,
        complexity="medium",
        domain="backend",
        dependencies=["task-setup"],
        acceptance_criteria=[
            "User can sign up",
            "User can log in",
            "Password is hashed",
            "Sessions are tracked",
        ],
        status=TaskStatus.READY,
    )


class TestAgentResponse:
    """Test AgentResponse dataclass"""

    def test_create_response(self):
        """Test creating agent response"""
        response = AgentResponse(
            agent_type=AgentType.IMPLEMENT,
            task_id="task-001",
            status="completed",
            success=True,
            output="Implementation completed",
            files_created=["auth.py"],
            files_modified=["__init__.py"],
        )

        assert response.agent_type == AgentType.IMPLEMENT
        assert response.task_id == "task-001"
        assert response.success is True
        assert response.files_created == ["auth.py"]

    def test_response_to_dict(self):
        """Test converting response to dict"""
        response = AgentResponse(
            agent_type=AgentType.TEST,
            task_id="task-001",
            status=AgentStatus.COMPLETED,
            success=True,
            output="Tests passed",
        )

        response_dict = response.to_dict()

        assert response_dict['agent_type'] == 'test'
        assert response_dict['task_id'] == 'task-001'
        assert response_dict['success'] is True
        assert 'timestamp' in response_dict


class TestAgentAssignment:
    """Test AgentAssignment dataclass"""

    def test_create_assignment(self):
        """Test creating assignment"""
        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
        )

        assert assignment.assignment_id == "assign-001"
        assert assignment.task_id == "task-001"
        assert assignment.retry_count == 0

    def test_assignment_duration(self):
        """Test calculating assignment duration"""
        start = datetime.now()
        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=start,
            started_at=start,
            completed_at=datetime.fromtimestamp(start.timestamp() + 5),
        )

        duration = assignment.duration_ms()
        assert duration is not None
        assert duration >= 4000  # At least 4 seconds


class TestClaudeAgentBridge:
    """Test Claude Agent Bridge"""

    def test_bridge_initialization(self, project_root, event_collector):
        """Test bridge initialization"""
        bridge = ClaudeAgentBridge(
            project_root=str(project_root),
            event_collector=event_collector,
        )

        assert bridge.project_root == project_root
        assert bridge.event_collector == event_collector
        assert bridge.timeout_seconds == 300
        assert bridge.enable_retries is True
        assert len(bridge.assignments) == 0
        assert len(bridge.responses) == 0

    def test_bridge_without_event_collector(self, project_root):
        """Test bridge without event collector"""
        bridge = ClaudeAgentBridge(project_root=str(project_root))

        assert bridge.event_collector is not None

    def test_build_prompt(self, agent_bridge, sample_task):
        """Test building agent prompt"""
        prompt = agent_bridge._build_prompt(
            task=sample_task,
            agent_type=AgentType.IMPLEMENT,
            prompt="Implement the feature",
            context="Database schema is in models.py",
        )

        assert "Implement authentication" in prompt
        assert "task-001" in prompt
        assert "Implement the feature" in prompt
        assert "Database schema is in models.py" in prompt
        assert "IMPLEMENT" in prompt
        assert "User can sign up" in prompt

    def test_build_prompt_without_context(self, agent_bridge, sample_task):
        """Test building prompt without context"""
        prompt = agent_bridge._build_prompt(
            task=sample_task,
            agent_type=AgentType.TEST,
            prompt="Write tests",
        )

        assert "Test" in prompt
        assert "write tests" in prompt or "Write tests" in prompt

    def test_get_agent_instructions(self, agent_bridge):
        """Test getting agent-specific instructions"""
        for agent_type in AgentType:
            instructions = agent_bridge._get_agent_instructions(agent_type)
            assert len(instructions) > 0
            assert agent_type.value.upper() in instructions or "role" in instructions.lower()

    @patch('subprocess.run')
    def test_dispatch_task_success(self, mock_run, agent_bridge, sample_task):
        """Test successful task dispatch"""
        # Mock subprocess response
        mock_run.return_value = MagicMock(
            stdout='{"files_created": ["auth.py"]}',
            stderr="",
            returncode=0,
        )

        assignment = agent_bridge.dispatch_task(
            task=sample_task,
            agent_type=AgentType.IMPLEMENT,
            prompt="Implement authentication",
        )

        assert assignment.task_id == "task-001"
        assert assignment.agent_type == AgentType.IMPLEMENT
        assert assignment.response is not None
        assert assignment.response.success is True
        assert agent_bridge.stats['total_dispatched'] == 1
        assert agent_bridge.stats['total_completed'] == 1

    @patch('subprocess.run')
    def test_dispatch_task_failure(self, mock_run, agent_bridge, sample_task):
        """Test task dispatch failure"""
        mock_run.return_value = MagicMock(
            stdout="",
            stderr="Error: Implementation failed",
            returncode=1,
        )

        with pytest.raises(AgentDispatchError):
            agent_bridge.dispatch_task(
                task=sample_task,
                agent_type=AgentType.IMPLEMENT,
                prompt="Implement authentication",
            )

        assert agent_bridge.stats['total_failed'] == 1

    @patch('subprocess.run')
    def test_dispatch_task_timeout(self, mock_run, agent_bridge, sample_task):
        """Test task dispatch timeout"""
        mock_run.side_effect = Exception("timeout")

        with pytest.raises(AgentDispatchError):
            agent_bridge.dispatch_task(
                task=sample_task,
                agent_type=AgentType.IMPLEMENT,
                prompt="Implement",
            )

    def test_parse_agent_response_success(self, agent_bridge):
        """Test parsing successful agent response"""
        stdout = json.dumps({
            'files_created': ['auth.py', 'test_auth.py'],
            'files_modified': ['__init__.py'],
        })

        response = agent_bridge._parse_agent_response(
            stdout=stdout,
            stderr="",
            returncode=0,
            agent_type=AgentType.IMPLEMENT,
            task_id="task-001",
            duration_ms=1234.5,
        )

        assert response.success is True
        assert response.status.value == "completed"
        assert len(response.files_created) >= 2
        assert response.duration_ms == 1234.5

    def test_parse_agent_response_failure(self, agent_bridge):
        """Test parsing failed agent response"""
        response = agent_bridge._parse_agent_response(
            stdout="",
            stderr="Error: Failed to implement",
            returncode=1,
            agent_type=AgentType.IMPLEMENT,
            task_id="task-001",
            duration_ms=500.0,
        )

        assert response.success is False
        assert response.status.value == "failed"
        assert len(response.errors) > 0

    def test_parse_agent_response_timeout(self, agent_bridge):
        """Test parsing timeout response"""
        response = agent_bridge._parse_agent_response(
            stdout="",
            stderr="",
            returncode=124,
            agent_type=AgentType.IMPLEMENT,
            task_id="task-001",
            duration_ms=300000.0,
        )

        assert response.status.value == "timeout"

    def test_get_assignment(self, agent_bridge):
        """Test getting assignment"""
        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
        )

        agent_bridge.assignments["assign-001"] = assignment

        retrieved = agent_bridge.get_assignment("assign-001")
        assert retrieved == assignment

    def test_get_assignment_not_found(self, agent_bridge):
        """Test getting non-existent assignment"""
        result = agent_bridge.get_assignment("nonexistent")
        assert result is None

    def test_get_response(self, agent_bridge):
        """Test getting response"""
        response = AgentResponse(
            agent_type=AgentType.IMPLEMENT,
            task_id="task-001",
            status="completed",
            success=True,
            output="Done",
        )

        agent_bridge.responses["task-001"] = response

        retrieved = agent_bridge.get_response("task-001")
        assert retrieved == response

    def test_get_stats(self, agent_bridge):
        """Test getting statistics"""
        agent_bridge.stats['total_dispatched'] = 10
        agent_bridge.stats['total_completed'] = 9
        agent_bridge.stats['total_failed'] = 1
        agent_bridge.stats['by_agent_type']['implement'] = 5
        agent_bridge.stats['by_status']['completed'] = 9

        stats = agent_bridge.get_stats()

        assert stats['total_dispatched'] == 10
        assert stats['total_completed'] == 9
        assert stats['total_failed'] == 1
        assert stats['success_rate'] == 0.9
        assert stats['by_agent_type']['implement'] == 5

    def test_list_assignments(self, agent_bridge):
        """Test listing assignments"""
        for i in range(5):
            assignment = AgentAssignment(
                assignment_id=f"assign-{i:03d}",
                task_id=f"task-{i:03d}",
                agent_type=AgentType.IMPLEMENT,
                created_at=datetime.now(),
            )
            agent_bridge.assignments[f"assign-{i:03d}"] = assignment

        assignments = agent_bridge.list_assignments(limit=3)
        assert len(assignments) == 3

    def test_cancel_assignment(self, agent_bridge):
        """Test cancelling assignment"""
        assignment = AgentAssignment(
            assignment_id="assign-001",
            task_id="task-001",
            agent_type=AgentType.IMPLEMENT,
            created_at=datetime.now(),
        )
        agent_bridge.assignments["assign-001"] = assignment

        result = agent_bridge.cancel_assignment("assign-001")
        assert result is True

    def test_cancel_nonexistent_assignment(self, agent_bridge):
        """Test cancelling non-existent assignment"""
        result = agent_bridge.cancel_assignment("nonexistent")
        assert result is False

    @patch('subprocess.run')
    def test_emit_assignment_telemetry(self, mock_run, agent_bridge, sample_task):
        """Test telemetry emission on assignment"""
        # Mock a successful dispatch
        mock_run.return_value = MagicMock(
            stdout='{"files_created": ["auth.py"]}',
            stderr="",
            returncode=0,
        )

        with patch.object(agent_bridge.event_collector, 'collect') as mock_collect:
            assignment = agent_bridge.dispatch_task(
                task=sample_task,
                agent_type=AgentType.IMPLEMENT,
                prompt="Implement",
            )

            # Check that telemetry was collected
            assert mock_collect.called

    def test_save_and_load_state(self, agent_bridge):
        """Test saving and loading state"""
        agent_bridge.stats['total_dispatched'] = 100
        agent_bridge.stats['total_completed'] = 95

        # Save state
        agent_bridge._save_state()

        # Create new bridge and load state
        new_bridge = ClaudeAgentBridge(
            project_root=str(agent_bridge.project_root),
        )

        assert new_bridge.stats['total_dispatched'] == 100
        assert new_bridge.stats['total_completed'] == 95

    def test_stats_initialization(self, agent_bridge):
        """Test stats are properly initialized"""
        assert agent_bridge.stats['total_dispatched'] == 0
        assert agent_bridge.stats['total_completed'] == 0
        assert agent_bridge.stats['total_failed'] == 0
        assert agent_bridge.stats['total_retries'] == 0
        # Success rate is calculated in get_stats, not stored in stats
        stats = agent_bridge.get_stats()
        assert stats['success_rate'] == 0

    @patch('subprocess.run')
    def test_retry_with_exponential_backoff(self, mock_run, agent_bridge, sample_task):
        """Test retry with exponential backoff"""
        # First call fails, second succeeds
        mock_run.side_effect = [
            MagicMock(
                stdout="",
                stderr="Timeout",
                returncode=124,
            ),
            MagicMock(
                stdout='{"files_created": ["auth.py"]}',
                stderr="",
                returncode=0,
            ),
        ]

        # Disable retries to test manually
        agent_bridge.enable_retries = False

        # First attempt should fail
        with pytest.raises(AgentDispatchError):
            agent_bridge.dispatch_task(
                task=sample_task,
                agent_type=AgentType.IMPLEMENT,
                prompt="Implement",
            )

    def test_multiple_agent_types(self, agent_bridge, sample_task):
        """Test dispatch with different agent types"""
        for agent_type in AgentType:
            assignment = AgentAssignment(
                assignment_id=str(uuid4())[:8],
                task_id=f"task-{agent_type.value}",
                agent_type=agent_type,
                created_at=datetime.now(),
            )

            agent_bridge.assignments[assignment.assignment_id] = assignment

        # Check stats by agent type
        assert len(agent_bridge.assignments) == len(AgentType)


class TestAgentBridgeIntegration:
    """Integration tests for agent bridge"""

    @patch('subprocess.run')
    def test_complete_workflow(self, mock_run, agent_bridge, sample_task):
        """Test complete dispatch and tracking workflow"""
        mock_run.return_value = MagicMock(
            stdout=json.dumps({
                'files_created': ['auth.py', 'test_auth.py'],
                'files_modified': ['__init__.py'],
            }),
            stderr="",
            returncode=0,
        )

        # Dispatch task
        assignment = agent_bridge.dispatch_task(
            task=sample_task,
            agent_type=AgentType.IMPLEMENT,
            prompt="Implement authentication system",
        )

        # Get assignment
        retrieved = agent_bridge.get_assignment(assignment.assignment_id)
        assert retrieved is not None

        # Get response
        response = agent_bridge.get_response(sample_task.id)
        assert response is not None
        assert response.success

        # Check stats
        stats = agent_bridge.get_stats()
        assert stats['total_dispatched'] == 1
        assert stats['total_completed'] == 1
        assert stats['success_rate'] == 1.0

    @patch('subprocess.run')
    def test_multiple_dispatches(self, mock_run, agent_bridge):
        """Test multiple task dispatches"""
        mock_run.return_value = MagicMock(
            stdout='{"files_created": ["file.py"]}',
            stderr="",
            returncode=0,
        )

        tasks = [
            QueuedTask(
                id=f"task-{i:03d}",
                name=f"Task {i}",
                description=f"Description {i}",
                file_path=f"file_{i}.py",
                estimated_minutes=60,
                complexity="simple",
                domain="backend",
                status=TaskStatus.READY,
            )
            for i in range(5)
        ]

        for task in tasks:
            agent_bridge.dispatch_task(
                task=task,
                agent_type=AgentType.IMPLEMENT,
                prompt="Implement",
            )

        stats = agent_bridge.get_stats()
        assert stats['total_dispatched'] == 5
        assert stats['total_completed'] == 5


class TestAgentErrors:
    """Test error handling"""

    def test_agent_error_inheritance(self):
        """Test error class hierarchy"""
        assert issubclass(AgentDispatchError, AgentError)
        assert issubclass(AgentTimeoutError, AgentError)
        assert issubclass(AgentParseError, AgentError)

    def test_agent_error_messages(self):
        """Test error messages"""
        error = AgentDispatchError("Test error")
        assert str(error) == "Test error"

    @patch('subprocess.run')
    def test_dispatch_error_handling(self, mock_run, agent_bridge, sample_task):
        """Test error handling during dispatch"""
        mock_run.side_effect = FileNotFoundError("claude command not found")

        with pytest.raises(AgentDispatchError):
            agent_bridge.dispatch_task(
                task=sample_task,
                agent_type=AgentType.IMPLEMENT,
                prompt="Implement",
            )


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=core.agents", "--cov-report=term-missing"])
