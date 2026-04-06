"""Tests for task management CLI commands"""

import pytest
from pathlib import Path
from typer.testing import CliRunner
from unittest.mock import Mock, patch, MagicMock

from cli.tasks_commands import tasks_app
from core.task_queue import TaskQueue, TaskStatus, QueuedTask


runner = CliRunner()


@pytest.fixture
def mock_queue():
    """Create mock task queue"""
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
        dependencies=["task1"],
    )
    task3 = QueuedTask(
        id="task3",
        name="Update docs",
        description="Update docs",
        file_path="docs/api.md",
        estimated_minutes=20,
        complexity="simple",
        domain="documentation",
        dependencies=["task1"],
    )
    queue.add_task(task1)
    queue.add_task(task2)
    queue.add_task(task3)
    return queue


class TestTasksGenerate:
    def test_generate_no_spec(self, tmp_path, monkeypatch):
        """Test generate fails when no PROJECT_SPEC exists"""
        monkeypatch.chdir(tmp_path)

        result = runner.invoke(tasks_app, ["generate"])

        assert result.exit_code == 1
        assert "PROJECT_SPEC not found" in result.stdout

    @patch("cli.tasks_commands.SpecParser")
    @patch("cli.tasks_commands.TaskDecomposer")
    @patch("cli.tasks_commands.DependencyGraph")
    @patch("cli.tasks_commands.save_task_queue")
    def test_generate_success(
        self, mock_save, mock_graph_cls, mock_decomposer_cls, mock_parser_cls, tmp_path, monkeypatch
    ):
        """Test successful task generation"""
        monkeypatch.chdir(tmp_path)

        # Create spec file
        br_dir = tmp_path / ".buildrunner"
        br_dir.mkdir()
        spec_file = br_dir / "PROJECT_SPEC.md"
        spec_file.write_text("# Test Spec")

        # Mock spec parsing
        mock_spec = Mock()
        mock_spec.features = [Mock(id="F1", name="Feature 1")]
        mock_parser = Mock()
        mock_parser.parse.return_value = mock_spec
        mock_parser_cls.return_value = mock_parser

        # Mock task decomposition
        mock_task = Mock()
        mock_task.task_id = "T1"
        mock_task.description = "Task 1"
        mock_task.dependencies = []
        mock_task.priority = 5
        mock_task.duration_minutes = 60
        mock_task.complexity = Mock(value="medium")

        mock_decomposer = Mock()
        mock_decomposer.decompose_feature.return_value = [mock_task]
        mock_decomposer_cls.return_value = mock_decomposer

        # Mock dependency graph
        mock_graph = Mock()
        mock_graph.has_circular_dependency.return_value = False
        mock_graph.get_execution_levels.return_value = [[mock_task.task_id]]
        mock_graph_cls.return_value = mock_graph

        result = runner.invoke(tasks_app, ["generate"])

        assert result.exit_code == 0
        assert "Task generation complete" in result.stdout
        mock_save.assert_called_once()

    @patch("cli.tasks_commands.SpecParser")
    @patch("cli.tasks_commands.TaskDecomposer")
    @patch("cli.tasks_commands.DependencyGraph")
    def test_generate_circular_dependency(
        self, mock_graph_cls, mock_decomposer_cls, mock_parser_cls, tmp_path, monkeypatch
    ):
        """Test generate fails with circular dependencies"""
        monkeypatch.chdir(tmp_path)

        # Create spec file
        br_dir = tmp_path / ".buildrunner"
        br_dir.mkdir()
        spec_file = br_dir / "PROJECT_SPEC.md"
        spec_file.write_text("# Test Spec")

        # Mock spec parsing
        mock_spec = Mock()
        mock_spec.features = [Mock(id="F1")]
        mock_parser = Mock()
        mock_parser.parse.return_value = mock_spec
        mock_parser_cls.return_value = mock_parser

        # Mock task decomposition
        mock_task = Mock()
        mock_task.task_id = "T1"
        mock_task.dependencies = ["T2"]
        mock_task.complexity = Mock(value="medium")
        mock_decomposer = Mock()
        mock_decomposer.decompose_feature.return_value = [mock_task]
        mock_decomposer_cls.return_value = mock_decomposer

        # Mock graph with circular dependency
        mock_graph = Mock()
        mock_graph.has_circular_dependency.return_value = True
        mock_graph_cls.return_value = mock_graph

        result = runner.invoke(tasks_app, ["generate"])

        assert result.exit_code == 1
        assert "Circular dependency" in result.stdout


class TestTasksList:
    @patch("cli.tasks_commands.get_task_queue")
    def test_list_no_tasks(self, mock_get_queue, tmp_path, monkeypatch):
        """Test list with no tasks"""
        monkeypatch.chdir(tmp_path)

        mock_queue = TaskQueue()
        mock_get_queue.return_value = mock_queue

        result = runner.invoke(tasks_app, ["list"])

        assert result.exit_code == 0
        assert "No tasks found" in result.stdout

    @patch("cli.tasks_commands.get_task_queue")
    def test_list_with_tasks(self, mock_get_queue, mock_queue, tmp_path, monkeypatch):
        """Test list displays tasks"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue

        result = runner.invoke(tasks_app, ["list"])

        assert result.exit_code == 0
        assert "Task Queue" in result.stdout
        assert "task1" in result.stdout

    @patch("cli.tasks_commands.get_task_queue")
    def test_list_filter_by_status(self, mock_get_queue, mock_queue, tmp_path, monkeypatch):
        """Test list with status filter"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue

        # Mark one task completed
        mock_queue.complete_task("task1")

        result = runner.invoke(tasks_app, ["list", "--status", "completed"])

        assert result.exit_code == 0
        assert "task1" in result.stdout

    @patch("cli.tasks_commands.get_task_queue")
    def test_list_show_all(self, mock_get_queue, mock_queue, tmp_path, monkeypatch):
        """Test list with --all flag"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue

        mock_queue.complete_task("task1")

        result = runner.invoke(tasks_app, ["list", "--all"])

        assert result.exit_code == 0
        assert "All Tasks" in result.stdout

    @patch("cli.tasks_commands.get_task_queue")
    def test_list_invalid_status(self, mock_get_queue, mock_queue, tmp_path, monkeypatch):
        """Test list with invalid status"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue

        result = runner.invoke(tasks_app, ["list", "--status", "invalid"])

        assert result.exit_code == 1
        assert "Invalid status" in result.stdout


class TestTasksComplete:
    @patch("cli.tasks_commands.get_task_queue")
    @patch("cli.tasks_commands.save_task_queue")
    def test_complete_task_success(
        self, mock_save, mock_get_queue, mock_queue, tmp_path, monkeypatch
    ):
        """Test marking task as complete"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue

        result = runner.invoke(tasks_app, ["complete", "task1"])

        assert result.exit_code == 0
        assert "marked as completed" in result.stdout
        mock_save.assert_called_once()

    @patch("cli.tasks_commands.get_task_queue")
    def test_complete_task_not_found(self, mock_get_queue, tmp_path, monkeypatch):
        """Test completing nonexistent task"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = TaskQueue()

        result = runner.invoke(tasks_app, ["complete", "invalid"])

        assert result.exit_code == 1
        assert "not found" in result.stdout


class TestTasksFail:
    @patch("cli.tasks_commands.get_task_queue")
    @patch("cli.tasks_commands.save_task_queue")
    def test_fail_task_success(self, mock_save, mock_get_queue, mock_queue, tmp_path, monkeypatch):
        """Test marking task as failed"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = mock_queue

        result = runner.invoke(tasks_app, ["fail", "task1", "--error", "Test error"])

        assert result.exit_code == 0
        assert "failed" in result.stdout.lower()
        mock_save.assert_called_once()

    @patch("cli.tasks_commands.get_task_queue")
    def test_fail_task_not_found(self, mock_get_queue, tmp_path, monkeypatch):
        """Test failing nonexistent task"""
        monkeypatch.chdir(tmp_path)
        mock_get_queue.return_value = TaskQueue()

        result = runner.invoke(tasks_app, ["fail", "invalid"])

        assert result.exit_code == 1
        assert "not found" in result.stdout
