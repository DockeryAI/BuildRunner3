"""
Comprehensive tests for multi-agent workflow chains.

Tests cover:
- Sequential agent execution (AgentChain)
- Parallel agent execution (ParallelAgentPool)
- Workflow templates
- State management and checkpointing
- Error handling and recovery
"""

import pytest
import json
import tempfile
from pathlib import Path
from datetime import datetime
from unittest.mock import Mock, MagicMock, patch

from core.agents.chains import (
    AgentChain,
    ParallelAgentPool,
    WorkflowTemplates,
    WorkflowStatus,
    WorkflowPhase,
    AgentWorkItem,
    WorkflowCheckpoint,
)
from core.agents.claude_agent_bridge import (
    ClaudeAgentBridge,
    AgentType,
    AgentStatus,
    AgentResponse,
    AgentAssignment,
)
from core.task_queue import QueuedTask, TaskStatus


# Fixtures
@pytest.fixture
def mock_agent_bridge():
    """Create mock agent bridge"""
    bridge = Mock(spec=ClaudeAgentBridge)
    bridge.project_root = Path("/test")
    return bridge


@pytest.fixture
def test_task():
    """Create test task"""
    return QueuedTask(
        id="test-task-1",
        name="Test Feature",
        description="Test feature implementation",
        file_path="src/test_feature.py",
        estimated_minutes=90,
        complexity="medium",
        domain="backend",
        acceptance_criteria=["Criterion 1", "Criterion 2"],
    )


@pytest.fixture
def mock_agent_response():
    """Create mock agent response"""
    return AgentResponse(
        agent_type=AgentType.IMPLEMENT,
        task_id="test-task-1",
        status=AgentStatus.COMPLETED,
        success=True,
        output="Implementation complete",
        files_created=["src/test_feature.py"],
        files_modified=[],
        errors=[],
        duration_ms=5000.0,
        tokens_used=2000,
    )


@pytest.fixture
def mock_agent_assignment(mock_agent_response):
    """Create mock agent assignment"""
    assignment = Mock(spec=AgentAssignment)
    assignment.assignment_id = "assign-1"
    assignment.task_id = "test-task-1"
    assignment.agent_type = AgentType.IMPLEMENT
    assignment.response = mock_agent_response
    assignment.created_at = datetime.now()
    assignment.started_at = datetime.now()
    assignment.completed_at = datetime.now()
    return assignment


@pytest.fixture
def temp_checkpoint_dir():
    """Create temporary checkpoint directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


# AgentChain Tests
class TestAgentChain:
    """Tests for sequential AgentChain workflow"""

    def test_init(self, mock_agent_bridge, temp_checkpoint_dir):
        """Test AgentChain initialization"""
        chain = AgentChain(
            agent_bridge=mock_agent_bridge,
            checkpoint_dir=temp_checkpoint_dir,
        )

        assert chain.status == WorkflowStatus.PENDING
        assert chain.items == {}
        assert chain.completed_items == []
        assert chain.failed_items == []
        assert chain.phase == WorkflowPhase.EXPLORE

    def test_add_work_item(self, mock_agent_bridge, test_task):
        """Test adding work items"""
        chain = AgentChain(mock_agent_bridge)

        item_id = chain.add_work_item(
            agent_type=AgentType.EXPLORE,
            task=test_task,
            prompt="Explore the task",
        )

        assert item_id in chain.items
        assert chain.items[item_id].agent_type == AgentType.EXPLORE
        assert chain.items[item_id].task == test_task
        assert chain.stats["total_items"] == 1

    def test_add_multiple_work_items(self, mock_agent_bridge, test_task):
        """Test adding multiple work items"""
        chain = AgentChain(mock_agent_bridge)

        item_ids = []
        for i in range(3):
            item_id = chain.add_work_item(
                agent_type=AgentType.IMPLEMENT,
                task=test_task,
                prompt=f"Task {i}",
            )
            item_ids.append(item_id)

        assert len(chain.items) == 3
        assert chain.stats["total_items"] == 3

    def test_add_item_with_dependencies(self, mock_agent_bridge, test_task):
        """Test adding item with dependencies"""
        chain = AgentChain(mock_agent_bridge)

        item1 = chain.add_work_item(
            agent_type=AgentType.EXPLORE,
            task=test_task,
            prompt="Explore",
        )

        item2 = chain.add_work_item(
            agent_type=AgentType.IMPLEMENT,
            task=test_task,
            prompt="Implement",
            dependencies=[item1],
        )

        assert item1 in chain.items[item2].dependencies

    def test_execution_order_respects_dependencies(self, mock_agent_bridge, test_task):
        """Test that execution order respects dependencies"""
        chain = AgentChain(mock_agent_bridge)

        item1 = chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")
        item2 = chain.add_work_item(
            AgentType.IMPLEMENT,
            test_task,
            "Implement",
            dependencies=[item1],
        )
        item3 = chain.add_work_item(
            AgentType.TEST,
            test_task,
            "Test",
            dependencies=[item2],
        )

        order = chain._get_execution_order()

        # Verify order
        assert order.index(item1) < order.index(item2)
        assert order.index(item2) < order.index(item3)

    def test_dependencies_met_check(self, mock_agent_bridge, test_task):
        """Test dependency checking"""
        chain = AgentChain(mock_agent_bridge)

        item1 = chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")
        item2 = chain.add_work_item(
            AgentType.IMPLEMENT,
            test_task,
            "Implement",
            dependencies=[item1],
        )

        # Before completion
        assert not chain._dependencies_met(item2)

        # After completion
        chain.completed_items.append(item1)
        assert chain._dependencies_met(item2)

    def test_execute_single_item(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test executing single item"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")

        result = chain.execute()

        assert result is True
        assert chain.status == WorkflowStatus.COMPLETED
        assert len(chain.completed_items) == 1
        mock_agent_bridge.dispatch_task.assert_called_once()

    def test_execute_sequential_items(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test executing sequential items"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")
        chain.add_work_item(AgentType.IMPLEMENT, test_task, "Implement")
        chain.add_work_item(AgentType.TEST, test_task, "Test")

        result = chain.execute()

        assert result is True
        assert len(chain.completed_items) == 3
        assert mock_agent_bridge.dispatch_task.call_count == 3

    def test_execute_with_failed_item(
        self,
        mock_agent_bridge,
        test_task,
    ):
        """Test execution with failed item"""
        failed_response = AgentResponse(
            agent_type=AgentType.EXPLORE,
            task_id="test-task-1",
            status=AgentStatus.FAILED,
            success=False,
            output="Failed",
            files_created=[],
            files_modified=[],
            errors=["Test error"],
            duration_ms=1000.0,
            tokens_used=100,
        )

        failed_assignment = Mock(spec=AgentAssignment)
        failed_assignment.response = failed_response

        mock_agent_bridge.dispatch_task.return_value = failed_assignment

        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")

        result = chain.execute()

        assert result is False
        assert len(chain.failed_items) == 1
        assert chain.status == WorkflowStatus.FAILED

    def test_execute_with_callback(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test execution with callbacks"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(mock_agent_bridge)
        item_id = chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")

        on_complete_calls = []

        def on_complete(item):
            on_complete_calls.append(item.item_id)

        chain.execute(on_item_complete=on_complete)

        assert item_id in on_complete_calls

    def test_checkpoint_saving(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
        temp_checkpoint_dir,
    ):
        """Test checkpoint saving"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(
            mock_agent_bridge,
            checkpoint_dir=temp_checkpoint_dir,
            enable_checkpointing=True,
        )
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")

        chain.execute()

        # Check checkpoint file exists
        checkpoint_files = list(temp_checkpoint_dir.glob("*.json"))
        assert len(checkpoint_files) > 0

    def test_get_results(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test getting results"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")
        chain.execute()

        results = chain.get_results()

        assert results["status"] == "completed"
        assert results["workflow_id"] == chain.workflow_id
        assert len(results["items"]["completed"]) == 1

    def test_stats_calculation(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test statistics calculation"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")
        chain.add_work_item(AgentType.IMPLEMENT, test_task, "Implement")

        chain.execute()

        results = chain.get_results()
        stats = results["stats"]

        assert stats["total_items"] == 2
        assert stats["completed_items"] == 2
        assert stats["failed_items"] == 0

    def test_execute_empty_workflow_raises_error(self, mock_agent_bridge):
        """Test that executing empty workflow raises error"""
        chain = AgentChain(mock_agent_bridge)

        with pytest.raises(ValueError, match="No work items"):
            chain.execute()

    def test_execute_already_running_raises_error(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test that executing running workflow raises error"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")

        # Start execution
        chain.status = WorkflowStatus.RUNNING

        with pytest.raises(ValueError, match="already running"):
            chain.execute()


# ParallelAgentPool Tests
class TestParallelAgentPool:
    """Tests for parallel agent execution"""

    def test_init(self, mock_agent_bridge):
        """Test ParallelAgentPool initialization"""
        pool = ParallelAgentPool(mock_agent_bridge, max_workers=3)

        assert pool.max_workers == 3
        assert pool.items == {}
        assert pool.results == {}

    def test_add_work_item(self, mock_agent_bridge, test_task):
        """Test adding work items to pool"""
        pool = ParallelAgentPool(mock_agent_bridge)

        item_id = pool.add_work_item(
            agent_type=AgentType.EXPLORE,
            task=test_task,
            prompt="Explore",
        )

        assert item_id in pool.items
        assert pool.stats["total_items"] == 1

    def test_add_multiple_items(self, mock_agent_bridge, test_task):
        """Test adding multiple items to pool"""
        pool = ParallelAgentPool(mock_agent_bridge)

        for i in range(5):
            pool.add_work_item(
                agent_type=AgentType.EXPLORE,
                task=test_task,
                prompt=f"Task {i}",
            )

        assert len(pool.items) == 5
        assert pool.stats["total_items"] == 5

    def test_max_workers_capped_at_10(self, mock_agent_bridge):
        """Test that max_workers is capped at 10"""
        pool = ParallelAgentPool(mock_agent_bridge, max_workers=20)
        assert pool.max_workers == 10

    def test_execute_single_item(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test executing single item in pool"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        pool = ParallelAgentPool(mock_agent_bridge)
        pool.add_work_item(AgentType.EXPLORE, test_task, "Explore")

        result = pool.execute()

        assert result is True
        assert pool.stats["completed_items"] == 1

    def test_execute_multiple_items(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test executing multiple items in parallel"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        pool = ParallelAgentPool(mock_agent_bridge, max_workers=3)

        for i in range(5):
            pool.add_work_item(AgentType.EXPLORE, test_task, f"Task {i}")

        result = pool.execute()

        assert result is True
        assert pool.stats["completed_items"] == 5
        assert mock_agent_bridge.dispatch_task.call_count == 5

    def test_execute_empty_pool_raises_error(self, mock_agent_bridge):
        """Test that executing empty pool raises error"""
        pool = ParallelAgentPool(mock_agent_bridge)

        with pytest.raises(ValueError, match="No work items"):
            pool.execute()

    def test_execute_with_failed_items(
        self,
        mock_agent_bridge,
        test_task,
    ):
        """Test execution with some failed items"""
        # Mix of success and failure
        success_response = AgentResponse(
            agent_type=AgentType.EXPLORE,
            task_id="test-1",
            status=AgentStatus.COMPLETED,
            success=True,
            output="Success",
            files_created=[],
            errors=[],
            duration_ms=1000.0,
            tokens_used=100,
        )

        fail_response = AgentResponse(
            agent_type=AgentType.EXPLORE,
            task_id="test-2",
            status=AgentStatus.FAILED,
            success=False,
            output="Failed",
            files_created=[],
            errors=["Error"],
            duration_ms=500.0,
            tokens_used=50,
        )

        success_assign = Mock(spec=AgentAssignment)
        success_assign.response = success_response

        fail_assign = Mock(spec=AgentAssignment)
        fail_assign.response = fail_response

        # Alternate success and failure
        responses = [success_assign, fail_assign, success_assign]
        mock_agent_bridge.dispatch_task.side_effect = responses

        pool = ParallelAgentPool(mock_agent_bridge)
        for i in range(3):
            pool.add_work_item(AgentType.EXPLORE, test_task, f"Task {i}")

        result = pool.execute()

        assert result is False
        assert pool.stats["completed_items"] == 2
        assert pool.stats["failed_items"] == 1

    def test_get_results(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test getting pool results"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        pool = ParallelAgentPool(mock_agent_bridge)
        pool.add_work_item(AgentType.EXPLORE, test_task, "Task 1")
        pool.add_work_item(AgentType.IMPLEMENT, test_task, "Task 2")

        pool.execute()

        results = pool.get_results()

        assert results["pool_id"] == pool.pool_id
        assert results["total_items"] == 2
        assert results["completed"] == 2

    def test_checkpoint_saving(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
        temp_checkpoint_dir,
    ):
        """Test checkpoint saving for pool"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        pool = ParallelAgentPool(
            mock_agent_bridge,
            checkpoint_dir=temp_checkpoint_dir,
        )
        pool.add_work_item(AgentType.EXPLORE, test_task, "Task")

        pool.execute()

        checkpoint_files = list(temp_checkpoint_dir.glob("*.json"))
        assert len(checkpoint_files) > 0

    def test_parallel_execution_timing(
        self,
        mock_agent_bridge,
        test_task,
    ):
        """Test that parallel execution properly tracks timing"""
        responses = []
        for i in range(3):
            response = AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id=f"test-{i}",
                status=AgentStatus.COMPLETED,
                success=True,
                output="Success",
                files_created=[],
                errors=[],
                duration_ms=2000.0,
                tokens_used=100,
            )
            assign = Mock(spec=AgentAssignment)
            assign.response = response
            responses.append(assign)

        mock_agent_bridge.dispatch_task.side_effect = responses

        pool = ParallelAgentPool(mock_agent_bridge, max_workers=3)
        for i in range(3):
            pool.add_work_item(AgentType.EXPLORE, test_task, f"Task {i}")

        pool.execute()

        assert pool.stats["total_duration_ms"] > 0
        assert pool.stats["avg_item_duration_ms"] > 0


# WorkflowTemplates Tests
class TestWorkflowTemplates:
    """Tests for workflow templates"""

    def test_full_workflow_template(self, mock_agent_bridge, test_task):
        """Test full workflow template creation"""
        workflow = WorkflowTemplates.full_workflow(mock_agent_bridge, test_task)

        assert isinstance(workflow, AgentChain)
        assert len(workflow.items) == 4
        # Should have all phases: explore, implement, test, review

    def test_test_workflow_template(self, mock_agent_bridge, test_task):
        """Test test-focused workflow template"""
        workflow = WorkflowTemplates.test_workflow(mock_agent_bridge, test_task)

        assert isinstance(workflow, AgentChain)
        assert len(workflow.items) == 3
        # Should have: implement, test, review

    def test_review_workflow_template(self, mock_agent_bridge, test_task):
        """Test review workflow template"""
        workflow = WorkflowTemplates.review_workflow(mock_agent_bridge, test_task)

        assert isinstance(workflow, AgentChain)
        assert len(workflow.items) == 1
        # Should have only review phase

    def test_full_workflow_execution(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test executing full workflow template"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        workflow = WorkflowTemplates.full_workflow(mock_agent_bridge, test_task)
        result = workflow.execute()

        assert result is True
        assert len(workflow.completed_items) == 4
        assert workflow.status == WorkflowStatus.COMPLETED


# AgentWorkItem Tests
class TestAgentWorkItem:
    """Tests for work item data structure"""

    def test_work_item_creation(self, test_task):
        """Test creating work item"""
        item = AgentWorkItem(
            item_id="item-1",
            agent_type=AgentType.EXPLORE,
            prompt="Explore",
            task=test_task,
        )

        assert item.item_id == "item-1"
        assert item.agent_type == AgentType.EXPLORE
        assert item.task == test_task

    def test_work_item_duration(self, test_task):
        """Test duration calculation"""
        item = AgentWorkItem(
            item_id="item-1",
            agent_type=AgentType.EXPLORE,
            prompt="Explore",
            task=test_task,
            started_at=datetime.now(),
        )

        assert item.duration_ms() is None

        # Add completion time
        import time

        time.sleep(0.1)
        item.completed_at = datetime.now()

        duration = item.duration_ms()
        assert duration is not None
        assert duration > 0

    def test_work_item_to_dict(self, test_task):
        """Test converting work item to dict"""
        item = AgentWorkItem(
            item_id="item-1",
            agent_type=AgentType.EXPLORE,
            prompt="Explore",
            task=test_task,
            status=AgentStatus.COMPLETED,
        )

        item_dict = item.to_dict()

        assert item_dict["item_id"] == "item-1"
        assert item_dict["agent_type"] == "explore"
        assert item_dict["task_id"] == test_task.id
        assert item_dict["status"] == "completed"


# Integration Tests
class TestWorkflowIntegration:
    """Integration tests for workflows"""

    def test_chain_to_results_pipeline(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test full chain execution to results"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")
        chain.add_work_item(AgentType.IMPLEMENT, test_task, "Implement")

        assert chain.execute()

        results = chain.get_results()
        assert results["status"] == "completed"
        assert len(results["items"]["completed"]) == 2

    def test_pool_to_results_pipeline(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test full pool execution to results"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        pool = ParallelAgentPool(mock_agent_bridge)
        for i in range(3):
            pool.add_work_item(AgentType.EXPLORE, test_task, f"Task {i}")

        assert pool.execute()

        results = pool.get_results()
        assert results["completed"] == 3

    def test_mixed_workflow_execution(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test using both chain and pool in same execution"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        # Sequential phase
        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")
        assert chain.execute()

        # Parallel phase
        pool = ParallelAgentPool(mock_agent_bridge)
        for i in range(3):
            pool.add_work_item(AgentType.IMPLEMENT, test_task, f"Task {i}")
        assert pool.execute()

        # Verify both succeeded
        chain_results = chain.get_results()
        pool_results = pool.get_results()

        assert chain_results["status"] == "completed"
        assert pool_results["completed"] == 3

    def test_chain_with_circular_dependencies(
        self,
        mock_agent_bridge,
        test_task,
    ):
        """Test chain with circular dependencies"""
        chain = AgentChain(mock_agent_bridge)

        item1 = chain.add_work_item(AgentType.EXPLORE, test_task, "A", dependencies=[])
        item2 = chain.add_work_item(AgentType.IMPLEMENT, test_task, "B", dependencies=[item1])

        # Manually create circular dependency
        chain.items[item1].dependencies.append(item2)

        # Should handle gracefully
        execution_order = chain._get_execution_order()
        assert len(execution_order) == 2

    def test_chain_execution_with_exception(
        self,
        mock_agent_bridge,
        test_task,
    ):
        """Test chain handling agent execution exception"""
        mock_agent_bridge.dispatch_task.side_effect = Exception("Agent error")

        chain = AgentChain(mock_agent_bridge)
        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")

        result = chain.execute()

        assert result is False
        assert len(chain.failed_items) == 1

    def test_chain_execution_status_progression(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
    ):
        """Test workflow status changes during execution"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        chain = AgentChain(mock_agent_bridge)
        assert chain.status == WorkflowStatus.PENDING

        chain.add_work_item(AgentType.EXPLORE, test_task, "Explore")

        chain.execute()

        assert chain.status == WorkflowStatus.COMPLETED
        assert chain.completed_at is not None

    def test_pool_checkpoint_location(
        self,
        mock_agent_bridge,
        test_task,
        mock_agent_assignment,
        temp_checkpoint_dir,
    ):
        """Test pool checkpoint is saved in correct location"""
        mock_agent_bridge.dispatch_task.return_value = mock_agent_assignment

        pool = ParallelAgentPool(
            mock_agent_bridge,
            checkpoint_dir=temp_checkpoint_dir,
        )
        pool.add_work_item(AgentType.EXPLORE, test_task, "Task")

        pool.execute()

        # Verify checkpoint file naming
        checkpoint_files = list(temp_checkpoint_dir.glob("pool_*.json"))
        assert len(checkpoint_files) > 0
        assert pool.pool_id in checkpoint_files[0].name
