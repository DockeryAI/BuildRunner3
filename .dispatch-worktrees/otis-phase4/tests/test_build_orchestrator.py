"""Tests for Build Orchestrator and CheckpointManager"""

import pytest
from pathlib import Path
from datetime import datetime

from core.build_orchestrator import BuildOrchestrator, BuildPhase, BuildState
from core.checkpoint_manager import CheckpointManager, Checkpoint, CheckpointStatus
from core.task_queue import TaskQueue, TaskStatus, QueuedTask


@pytest.fixture
def temp_project(tmp_path):
    """Create temporary project directory"""
    project_root = tmp_path / "test_project"
    project_root.mkdir()
    (project_root / ".buildrunner").mkdir()
    return project_root


@pytest.fixture
def sample_queue():
    """Create sample task queue"""
    queue = TaskQueue()

    task1 = QueuedTask(
        id="task1",
        name="Task 1",
        description="First task",
        file_path="file1.py",
        estimated_minutes=60,
        complexity="medium",
        domain="backend",
        dependencies=[],
    )

    task2 = QueuedTask(
        id="task2",
        name="Task 2",
        description="Second task",
        file_path="file2.py",
        estimated_minutes=90,
        complexity="medium",
        domain="backend",
        dependencies=["task1"],
    )

    task3 = QueuedTask(
        id="task3",
        name="Task 3",
        description="Third task",
        file_path="file3.py",
        estimated_minutes=30,
        complexity="simple",
        domain="testing",
        dependencies=["task1"],
    )

    queue.add_task(task1)
    queue.add_task(task2)
    queue.add_task(task3)

    return queue


class TestCheckpointManager:
    def test_create_checkpoint(self, temp_project):
        """Test checkpoint creation"""
        manager = CheckpointManager(temp_project)

        checkpoint = manager.create_checkpoint(
            phase="test_phase",
            tasks_completed=["task1", "task2"],
            files_created=["file1.py", "file2.py"],
            metadata={"test": "value"},
        )

        assert checkpoint is not None
        assert checkpoint.phase == "test_phase"
        assert len(checkpoint.tasks_completed) == 2
        assert len(checkpoint.files_created) == 2
        assert checkpoint.status == CheckpointStatus.CREATED

    def test_get_checkpoint(self, temp_project):
        """Test getting checkpoint by ID"""
        manager = CheckpointManager(temp_project)

        checkpoint = manager.create_checkpoint(phase="test", tasks_completed=[], files_created=[])

        retrieved = manager.get_checkpoint(checkpoint.id)
        assert retrieved is not None
        assert retrieved.id == checkpoint.id

    def test_get_latest_checkpoint(self, temp_project):
        """Test getting latest checkpoint"""
        manager = CheckpointManager(temp_project)

        checkpoint1 = manager.create_checkpoint("phase1", [], [])
        checkpoint2 = manager.create_checkpoint("phase2", [], [])

        latest = manager.get_latest_checkpoint()
        assert latest is not None
        assert latest.id == checkpoint2.id

    def test_list_checkpoints(self, temp_project):
        """Test listing all checkpoints"""
        manager = CheckpointManager(temp_project)

        manager.create_checkpoint("phase1", [], [])
        manager.create_checkpoint("phase2", [], [])

        checkpoints = manager.list_checkpoints()
        assert len(checkpoints) == 2

    def test_rollback(self, temp_project):
        """Test rollback to checkpoint"""
        manager = CheckpointManager(temp_project)

        checkpoint1 = manager.create_checkpoint("phase1", ["task1"], ["file1.py"])
        checkpoint2 = manager.create_checkpoint(
            "phase2", ["task1", "task2"], ["file1.py", "file2.py"]
        )

        success = manager.rollback(checkpoint1.id)
        assert success is True

        # Check checkpoint status updated
        assert checkpoint1.status == CheckpointStatus.ACTIVE

    def test_get_files_to_rollback(self, temp_project):
        """Test getting files created after checkpoint"""
        manager = CheckpointManager(temp_project)

        checkpoint1 = manager.create_checkpoint("phase1", [], ["file1.py"])
        checkpoint2 = manager.create_checkpoint("phase2", [], ["file2.py"])
        checkpoint3 = manager.create_checkpoint("phase3", [], ["file3.py"])

        files = manager.get_files_to_rollback(checkpoint1.id)
        assert "file2.py" in files
        assert "file3.py" in files
        assert "file1.py" not in files

    def test_get_resume_state(self, temp_project):
        """Test getting resume state"""
        manager = CheckpointManager(temp_project)

        manager.create_checkpoint(
            phase="test_phase",
            tasks_completed=["task1"],
            files_created=["file1.py"],
            metadata={"key": "value"},
        )

        resume_state = manager.get_resume_state()
        assert resume_state is not None
        assert resume_state["phase"] == "test_phase"
        assert "task1" in resume_state["tasks_completed"]


class TestBuildOrchestrator:
    def test_init(self, temp_project, sample_queue):
        """Test orchestrator initialization"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        assert orchestrator.project_root == temp_project
        assert orchestrator.task_queue == sample_queue
        assert orchestrator.checkpoint_manager is not None

    def test_analyze_dependencies(self, temp_project, sample_queue):
        """Test dependency analysis"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        analysis = orchestrator.analyze_dependencies()

        assert "execution_levels" in analysis
        assert "total_levels" in analysis
        assert "parallelizable_tasks" in analysis
        assert "critical_path" in analysis

        # Should have at least 2 levels (task1, then task2/task3)
        assert analysis["total_levels"] >= 2

    def test_create_checkpoint(self, temp_project, sample_queue):
        """Test creating checkpoint through orchestrator"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        checkpoint_id = orchestrator.create_checkpoint(phase="batch_1", metadata={"batch": 1})

        assert checkpoint_id is not None
        assert orchestrator.current_state is not None
        assert orchestrator.current_state.checkpoint_id == checkpoint_id

    def test_rollback_to_checkpoint(self, temp_project, sample_queue):
        """Test rollback functionality"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        # Create initial checkpoint
        checkpoint_id = orchestrator.create_checkpoint("phase1")

        # Simulate progress
        orchestrator.track_task_completed("task1")

        # Rollback
        success = orchestrator.rollback_to_checkpoint(checkpoint_id)
        assert success is True

    def test_resume_from_checkpoint(self, temp_project, sample_queue):
        """Test resume functionality"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        # Create checkpoint
        checkpoint_id = orchestrator.create_checkpoint("test_phase")

        # Create new orchestrator and resume
        orchestrator2 = BuildOrchestrator(temp_project, sample_queue)
        success = orchestrator2.resume_from_checkpoint(checkpoint_id)

        assert success is True
        assert orchestrator2.current_state is not None
        assert orchestrator2.current_state.phase == "test_phase"

    def test_interruption_gates(self, temp_project, sample_queue):
        """Test interruption gate functionality"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        orchestrator.add_interruption_gate("task2")
        assert orchestrator.is_interruption_gate("task2") is True
        assert orchestrator.is_interruption_gate("task1") is False

    def test_get_next_parallelizable_batch(self, temp_project, sample_queue):
        """Test getting parallelizable task batch"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        # Mark task1 as completed so task2 and task3 become ready
        sample_queue.complete_task("task1")

        batch = orchestrator.get_next_parallelizable_batch(max_tasks=3)

        # Should get task2 and task3 (both depend on task1)
        assert len(batch) <= 3
        assert all(isinstance(t, QueuedTask) for t in batch)

    def test_track_file_created(self, temp_project, sample_queue):
        """Test file creation tracking"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        orchestrator.create_checkpoint("phase1")
        orchestrator.track_file_created("test.py")

        assert "test.py" in orchestrator.current_state.files_created

    def test_track_task_completed(self, temp_project, sample_queue):
        """Test task completion tracking"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        orchestrator.create_checkpoint("phase1")
        orchestrator.current_state.tasks_in_progress.append("task1")

        orchestrator.track_task_completed("task1")

        assert "task1" in orchestrator.current_state.tasks_completed
        assert "task1" not in orchestrator.current_state.tasks_in_progress

    def test_get_build_progress(self, temp_project, sample_queue):
        """Test getting build progress"""
        orchestrator = BuildOrchestrator(temp_project, sample_queue)

        # Before creating state
        progress = orchestrator.get_build_progress()
        assert progress["phase"] == "not_started"
        assert progress["progress_percent"] == 0

        # After creating state
        orchestrator.create_checkpoint("batch_1")
        orchestrator.track_task_completed("task1")

        progress = orchestrator.get_build_progress()
        assert progress["phase"] == "batch_1"
        assert progress["tasks_completed"] == 1
        assert progress["progress_percent"] > 0
