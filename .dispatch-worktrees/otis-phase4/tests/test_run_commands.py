"""Tests for orchestration run CLI commands"""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock

from cli.run_commands import run_app
from core.task_queue import TaskQueue, TaskStatus, QueuedTask


runner = CliRunner()


@pytest.fixture
def mock_queue_with_ready_tasks():
    """Create mock task queue with ready tasks"""
    queue = TaskQueue()
    task1 = QueuedTask(
        id="task1",
        name="Create API endpoint",
        description="Create API endpoint",
        file_path="api/endpoint.py",
        estimated_minutes=60,
        complexity="medium",
        domain="backend",
        dependencies=[],
    )
    task2 = QueuedTask(
        id="task2",
        name="Add tests",
        description="Add tests",
        file_path="tests/test_endpoint.py",
        estimated_minutes=30,
        complexity="simple",
        domain="testing",
        dependencies=[],
    )
    task3 = QueuedTask(
        id="task3",
        name="Update docs",
        description="Update docs",
        file_path="docs/api.md",
        estimated_minutes=20,
        complexity="simple",
        domain="documentation",
        dependencies=["task2"],
    )
    queue.add_task(task1)
    queue.add_task(task2)
    queue.add_task(task3)
    return queue


class TestRunAuto:
    @patch("cli.run_commands.get_task_queue")
    def test_run_auto_no_tasks(self, mock_get_queue, tmp_path, monkeypatch):
        """Test run --auto with no tasks"""
        monkeypatch.chdir(tmp_path)

        mock_queue = TaskQueue()
        mock_get_queue.return_value = mock_queue

        result = runner.invoke(run_app, ["auto"], input="n\n")

        assert result.exit_code == 1
        assert "No tasks found" in result.stdout

    @patch("cli.run_commands.get_task_queue")
    def test_run_auto_no_ready_tasks(self, mock_get_queue, tmp_path, monkeypatch):
        """Test run --auto with no ready tasks"""
        monkeypatch.chdir(tmp_path)

        mock_queue = TaskQueue()
        task1 = QueuedTask(
            id="task1",
            name="Task 1",
            description="Task 1",
            file_path="test.py",
            estimated_minutes=60,
            complexity="medium",
            domain="backend",
            dependencies=["task0"],  # Depends on non-existent task
        )
        mock_queue.add_task(task1)
        mock_get_queue.return_value = mock_queue

        result = runner.invoke(run_app, ["auto"], input="n\n")

        assert result.exit_code == 0
        assert "No ready tasks" in result.stdout

    @patch("cli.run_commands.get_task_queue")
    @patch("cli.run_commands.save_task_queue")
    @patch("cli.run_commands.BatchOptimizer")
    @patch("cli.run_commands.PromptBuilder")
    @patch("cli.run_commands.ContextManager")
    def test_run_auto_success_interactive(
        self,
        mock_context_cls,
        mock_prompt_cls,
        mock_batch_cls,
        mock_save,
        mock_get_queue,
        mock_queue_with_ready_tasks,
        tmp_path,
        monkeypatch,
    ):
        """Test successful auto-run in interactive mode"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue_with_ready_tasks

        # Mock batch optimizer
        mock_batch = Mock()
        mock_batch.id = 1
        mock_batch.tasks = [
            {
                "id": "task1",
                "description": "Task 1",
                "duration_minutes": 60,
                "complexity": "medium",
                "domain": "backend",
            }
        ]
        mock_optimizer = Mock()
        mock_optimizer.optimize_batches.return_value = [mock_batch]
        mock_batch_cls.return_value = mock_optimizer

        # Mock prompt builder
        mock_prompt = Mock()
        mock_prompt.build_prompt.return_value = "Test prompt"
        mock_prompt_cls.return_value = mock_prompt

        # Mock context manager
        mock_context = Mock()
        mock_context.get_context.return_value = "Test context"
        mock_context_cls.return_value = mock_context

        # Simulate user completing first batch and declining second
        result = runner.invoke(run_app, ["auto"], input="y\ny\nn\n")

        assert result.exit_code == 0
        assert "Auto-Orchestration Mode" in result.stdout
        assert "Execution Plan" in result.stdout

    @patch("cli.run_commands.get_task_queue")
    @patch("cli.run_commands.BatchOptimizer")
    def test_run_auto_cancel(
        self, mock_batch_cls, mock_get_queue, mock_queue_with_ready_tasks, tmp_path, monkeypatch
    ):
        """Test cancelling auto-run"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue_with_ready_tasks

        # Mock batch optimizer
        mock_batch = Mock()
        mock_batch.id = 1
        mock_batch.tasks = [{"id": "task1", "description": "Task 1"}]
        mock_optimizer = Mock()
        mock_optimizer.optimize_batches.return_value = [mock_batch]
        mock_batch_cls.return_value = mock_optimizer

        # User declines to start
        result = runner.invoke(run_app, ["auto"], input="n\n")

        assert result.exit_code == 0
        assert "cancelled" in result.stdout.lower()

    @patch("cli.run_commands.get_task_queue")
    @patch("cli.run_commands.BatchOptimizer")
    @patch("cli.run_commands.PromptBuilder")
    @patch("cli.run_commands.ContextManager")
    def test_run_auto_non_interactive(
        self,
        mock_context_cls,
        mock_prompt_cls,
        mock_batch_cls,
        mock_get_queue,
        mock_queue_with_ready_tasks,
        tmp_path,
        monkeypatch,
    ):
        """Test auto-run in non-interactive mode"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue_with_ready_tasks

        # Mock components
        mock_batch = Mock()
        mock_batch.id = 1
        mock_batch.tasks = [
            {
                "id": "task1",
                "description": "Task 1",
                "duration_minutes": 60,
                "complexity": "medium",
                "domain": "backend",
            }
        ]
        mock_optimizer = Mock()
        mock_optimizer.optimize_batches.return_value = [mock_batch]
        mock_batch_cls.return_value = mock_optimizer

        mock_prompt = Mock()
        mock_prompt.build_prompt.return_value = "Test prompt"
        mock_prompt_cls.return_value = mock_prompt

        mock_context = Mock()
        mock_context.get_context.return_value = "Test context"
        mock_context_cls.return_value = mock_context

        result = runner.invoke(run_app, ["auto", "--non-interactive"])

        assert result.exit_code == 0
        assert "Auto-Orchestration Mode" in result.stdout

    @patch("cli.run_commands.get_task_queue")
    @patch("cli.run_commands.save_task_queue")
    @patch("cli.run_commands.BatchOptimizer")
    @patch("cli.run_commands.PromptBuilder")
    @patch("cli.run_commands.ContextManager")
    @patch("cli.run_commands.VerificationEngine")
    def test_run_auto_with_verification(
        self,
        mock_verify_cls,
        mock_context_cls,
        mock_prompt_cls,
        mock_batch_cls,
        mock_save,
        mock_get_queue,
        mock_queue_with_ready_tasks,
        tmp_path,
        monkeypatch,
    ):
        """Test auto-run with verification enabled"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue_with_ready_tasks

        # Mock batch with file_path
        mock_batch = Mock()
        mock_batch.id = 1
        mock_batch.tasks = [
            {
                "id": "task1",
                "description": "Task 1",
                "duration_minutes": 60,
                "complexity": "medium",
                "domain": "backend",
                "file_path": "test.py",
            }
        ]
        mock_optimizer = Mock()
        mock_optimizer.optimize_batches.return_value = [mock_batch]
        mock_batch_cls.return_value = mock_optimizer

        mock_prompt = Mock()
        mock_prompt.build_prompt.return_value = "Test prompt"
        mock_prompt_cls.return_value = mock_prompt

        mock_context = Mock()
        mock_context.get_context.return_value = "Test context"
        mock_context_cls.return_value = mock_context

        # Mock verification
        mock_result = Mock()
        mock_result.passed = True
        mock_result.message = "All files verified"
        mock_verifier = Mock()
        mock_verifier.verify_files_exist.return_value = mock_result
        mock_verify_cls.return_value = mock_verifier

        result = runner.invoke(run_app, ["auto", "--verify"], input="y\ny\nn\n")

        assert result.exit_code == 0
        assert "Running verification" in result.stdout


class TestRunStatus:
    @patch("cli.run_commands.get_task_queue")
    def test_status_no_tasks(self, mock_get_queue, tmp_path, monkeypatch):
        """Test status with no tasks"""
        monkeypatch.chdir(tmp_path)

        mock_queue = TaskQueue()
        mock_get_queue.return_value = mock_queue

        result = runner.invoke(run_app, ["status"])

        assert result.exit_code == 0
        assert "No orchestration in progress" in result.stdout

    @patch("cli.run_commands.get_task_queue")
    def test_status_with_tasks(
        self, mock_get_queue, mock_queue_with_ready_tasks, tmp_path, monkeypatch
    ):
        """Test status displays task progress"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue_with_ready_tasks

        result = runner.invoke(run_app, ["status"])

        assert result.exit_code == 0
        assert "Orchestration Status" in result.stdout
        assert "Progress" in result.stdout

    @patch("cli.run_commands.get_task_queue")
    def test_status_with_completed_tasks(
        self, mock_get_queue, mock_queue_with_ready_tasks, tmp_path, monkeypatch
    ):
        """Test status shows completion percentage"""
        monkeypatch.chdir(tmp_path)

        # Complete some tasks
        mock_queue_with_ready_tasks.complete_task("task1")

        mock_get_queue.return_value = mock_queue_with_ready_tasks

        result = runner.invoke(run_app, ["status"])

        assert result.exit_code == 0
        assert "Completed" in result.stdout

    @patch("cli.run_commands.get_task_queue")
    def test_status_shows_next_batch(
        self, mock_get_queue, mock_queue_with_ready_tasks, tmp_path, monkeypatch
    ):
        """Test status shows next batch info"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue_with_ready_tasks

        result = runner.invoke(run_app, ["status"])

        assert result.exit_code == 0
        assert "Next Batch" in result.stdout
        assert "br run --auto" in result.stdout
