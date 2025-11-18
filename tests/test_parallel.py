"""
Tests for Parallel Orchestration System

Tests cover:
- Session management and lifecycle
- Worker coordination and task distribution
- File locking and conflict detection
- Live dashboard rendering
- State persistence
"""

import json
import tempfile
from datetime import datetime, timedelta
from pathlib import Path
import pytest

from core.parallel import (
    SessionManager,
    Session,
    SessionStatus,
    WorkerCoordinator,
    Worker,
    WorkerStatus,
    LiveDashboard,
    DashboardConfig,
)


# ===== Session Manager Tests =====


def test_session_creation():
    """Test creating a new session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        manager = SessionManager(storage_path=storage_path)

        session = manager.create_session(
            name="Test Build",
            total_tasks=10,
            metadata={'build': 'test'},
        )

        assert session.name == "Test Build"
        assert session.total_tasks == 10
        assert session.status == SessionStatus.CREATED
        assert session.metadata['build'] == 'test'
        assert session.session_id in manager.sessions


def test_session_lifecycle():
    """Test session lifecycle (create -> start -> complete)."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        manager = SessionManager(storage_path=storage_path)

        # Create session
        session = manager.create_session("Test Build", total_tasks=5)
        assert session.status == SessionStatus.CREATED

        # Start session
        manager.start_session(session.session_id, worker_id="worker-123")
        session = manager.get_session(session.session_id)
        assert session.status == SessionStatus.RUNNING
        assert session.started_at is not None
        assert session.worker_id == "worker-123"

        # Complete session
        manager.complete_session(session.session_id)
        session = manager.get_session(session.session_id)
        assert session.status == SessionStatus.COMPLETED
        assert session.completed_at is not None
        assert session.progress_percent == 100.0


def test_session_pause_resume():
    """Test pausing and resuming a session."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        manager = SessionManager(storage_path=storage_path)

        session = manager.create_session("Test Build", total_tasks=5)
        manager.start_session(session.session_id)

        # Pause
        manager.pause_session(session.session_id)
        session = manager.get_session(session.session_id)
        assert session.status == SessionStatus.PAUSED

        # Resume
        manager.start_session(session.session_id)
        session = manager.get_session(session.session_id)
        assert session.status == SessionStatus.RUNNING


def test_session_progress_tracking():
    """Test progress tracking and percentage calculation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        manager = SessionManager(storage_path=storage_path)

        session = manager.create_session("Test Build", total_tasks=10)

        # Update progress
        manager.update_progress(
            session.session_id,
            completed_tasks=3,
            failed_tasks=1,
            in_progress_tasks=2,
        )

        session = manager.get_session(session.session_id)
        assert session.completed_tasks == 3
        assert session.failed_tasks == 1
        assert session.in_progress_tasks == 2
        assert session.progress_percent == 30.0  # 3/10 * 100


def test_file_locking():
    """Test file locking mechanism."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        manager = SessionManager(storage_path=storage_path)

        session = manager.create_session("Test Build", total_tasks=5)
        manager.start_session(session.session_id)

        # Lock files
        files = ["file1.py", "file2.py", "file3.py"]
        manager.lock_files(session.session_id, files)

        session = manager.get_session(session.session_id)
        assert len(session.files_locked) == 3
        assert "file1.py" in session.files_locked

        # Unlock specific files
        manager.unlock_files(session.session_id, ["file1.py"])
        session = manager.get_session(session.session_id)
        assert len(session.files_locked) == 2
        assert "file1.py" not in session.files_locked

        # Unlock all
        manager.unlock_files(session.session_id)
        session = manager.get_session(session.session_id)
        assert len(session.files_locked) == 0


def test_file_locking_conflicts():
    """Test file locking conflict detection."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        manager = SessionManager(storage_path=storage_path)

        # Create two sessions
        session1 = manager.create_session("Build 1", total_tasks=5)
        session2 = manager.create_session("Build 2", total_tasks=5)

        manager.start_session(session1.session_id)
        manager.start_session(session2.session_id)

        # Session 1 locks files
        manager.lock_files(session1.session_id, ["file1.py", "file2.py"])

        # Session 2 tries to lock same files - should fail
        with pytest.raises(ValueError, match="already locked"):
            manager.lock_files(session2.session_id, ["file2.py", "file3.py"])

        # Session 2 can lock different files
        manager.lock_files(session2.session_id, ["file4.py"])
        session2 = manager.get_session(session2.session_id)
        assert "file4.py" in session2.files_locked


def test_session_persistence():
    """Test session persistence to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"

        # Create session
        manager1 = SessionManager(storage_path=storage_path)
        session = manager1.create_session("Test Build", total_tasks=10)
        session_id = session.session_id

        # Load in new manager
        manager2 = SessionManager(storage_path=storage_path)
        loaded_session = manager2.get_session(session_id)

        assert loaded_session is not None
        assert loaded_session.name == "Test Build"
        assert loaded_session.total_tasks == 10


def test_list_sessions():
    """Test listing and filtering sessions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        manager = SessionManager(storage_path=storage_path)

        # Create sessions with different statuses
        s1 = manager.create_session("Build 1", total_tasks=5)
        s2 = manager.create_session("Build 2", total_tasks=5)
        s3 = manager.create_session("Build 3", total_tasks=5)

        manager.start_session(s1.session_id)
        manager.start_session(s2.session_id)
        manager.complete_session(s2.session_id)

        # List all
        all_sessions = manager.list_sessions()
        assert len(all_sessions) == 3

        # List running
        running = manager.list_sessions(status=SessionStatus.RUNNING)
        assert len(running) == 1
        assert running[0].session_id == s1.session_id

        # List completed
        completed = manager.list_sessions(status=SessionStatus.COMPLETED)
        assert len(completed) == 1
        assert completed[0].session_id == s2.session_id


def test_cleanup_old_sessions():
    """Test cleaning up old sessions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        manager = SessionManager(storage_path=storage_path)

        # Create and complete sessions
        s1 = manager.create_session("Old Build", total_tasks=5)
        s2 = manager.create_session("Recent Build", total_tasks=5)

        manager.complete_session(s1.session_id)
        manager.complete_session(s2.session_id)

        # Make s1 old by modifying completed_at
        session1 = manager.get_session(s1.session_id)
        session1.completed_at = datetime.now() - timedelta(days=10)
        manager._save()

        # Cleanup sessions older than 7 days
        manager.cleanup_old_sessions(days=7)

        # s1 should be deleted, s2 should remain
        assert manager.get_session(s1.session_id) is None
        assert manager.get_session(s2.session_id) is not None


# ===== Worker Coordinator Tests =====


def test_worker_registration():
    """Test worker registration."""
    coordinator = WorkerCoordinator(max_workers=5)

    worker = coordinator.register_worker(metadata={'name': 'Test Worker'})

    assert worker.worker_id in coordinator.workers
    assert worker.status == WorkerStatus.IDLE
    assert worker.metadata['name'] == 'Test Worker'
    assert worker.last_heartbeat is not None


def test_worker_unregistration():
    """Test worker unregistration."""
    coordinator = WorkerCoordinator(max_workers=5)

    worker = coordinator.register_worker()
    worker_id = worker.worker_id

    coordinator.unregister_worker(worker_id)

    assert worker_id not in coordinator.workers


def test_task_assignment():
    """Test task assignment to workers."""
    coordinator = WorkerCoordinator(max_workers=3)

    # Register workers
    w1 = coordinator.register_worker()
    w2 = coordinator.register_worker()

    # Assign task
    assigned_worker_id = coordinator.assign_task(
        task_id="task-1",
        task_data={'description': 'Test task'},
        session_id="session-1",
    )

    assert assigned_worker_id is not None
    worker = coordinator.get_worker(assigned_worker_id)
    assert worker.status == WorkerStatus.BUSY
    assert worker.current_task == "task-1"
    assert worker.session_id == "session-1"


def test_task_queueing():
    """Test task queueing when no workers available."""
    coordinator = WorkerCoordinator(max_workers=1)

    # Register one worker
    w1 = coordinator.register_worker()

    # Assign first task
    assigned1 = coordinator.assign_task("task-1", {'data': 1})
    assert assigned1 is not None

    # Second task should be queued
    assigned2 = coordinator.assign_task("task-2", {'data': 2})
    assert assigned2 is None
    assert len(coordinator.task_queue) == 1


def test_task_completion():
    """Test task completion and worker state update."""
    coordinator = WorkerCoordinator(max_workers=3)

    worker = coordinator.register_worker()
    worker_id = worker.worker_id

    # Assign and complete task
    coordinator.assign_task("task-1", {})
    coordinator.complete_task(worker_id, "task-1", success=True)

    worker = coordinator.get_worker(worker_id)
    assert worker.status == WorkerStatus.IDLE
    assert worker.current_task is None
    assert worker.tasks_completed == 1
    assert worker.tasks_failed == 0


def test_task_failure():
    """Test task failure tracking."""
    coordinator = WorkerCoordinator(max_workers=3)

    worker = coordinator.register_worker()
    worker_id = worker.worker_id

    # Assign and fail task
    coordinator.assign_task("task-1", {})
    coordinator.complete_task(worker_id, "task-1", success=False)

    worker = coordinator.get_worker(worker_id)
    assert worker.tasks_completed == 0
    assert worker.tasks_failed == 1


def test_worker_heartbeat():
    """Test worker heartbeat updates."""
    coordinator = WorkerCoordinator(max_workers=3)

    worker = coordinator.register_worker()
    worker_id = worker.worker_id

    # Store initial heartbeat
    initial_hb = worker.last_heartbeat

    # Wait a bit and send heartbeat
    import time
    time.sleep(0.1)
    coordinator.heartbeat(worker_id)

    worker = coordinator.get_worker(worker_id)
    assert worker.last_heartbeat > initial_hb


def test_worker_health_monitoring():
    """Test worker health check and offline detection."""
    coordinator = WorkerCoordinator(max_workers=3)
    coordinator.HEARTBEAT_TIMEOUT = 1  # 1 second for testing

    worker = coordinator.register_worker()
    worker_id = worker.worker_id

    # Assign task
    coordinator.assign_task("task-1", {})

    # Make heartbeat old
    worker = coordinator.get_worker(worker_id)
    worker.last_heartbeat = datetime.now() - timedelta(seconds=2)

    # Check health
    coordinator.check_worker_health()

    worker = coordinator.get_worker(worker_id)
    assert worker.status == WorkerStatus.OFFLINE
    assert worker.current_task is None
    assert len(coordinator.task_queue) == 1  # Task was requeued


def test_load_distribution():
    """Test load distribution statistics."""
    coordinator = WorkerCoordinator(max_workers=5)

    # Register workers
    w1 = coordinator.register_worker()
    w2 = coordinator.register_worker()
    w3 = coordinator.register_worker()

    # Assign tasks
    coordinator.assign_task("task-1", {})
    coordinator.assign_task("task-2", {})

    # Complete one task
    coordinator.complete_task(w1.worker_id, "task-1", success=True)

    # Get distribution
    dist = coordinator.get_load_distribution()

    assert dist['total_workers'] == 3
    assert dist['idle_workers'] == 2  # w1 and w3
    assert dist['busy_workers'] == 1  # w2
    assert dist['total_completed'] == 1
    assert dist['utilization'] == pytest.approx(33.33, rel=0.1)


def test_worker_scaling():
    """Test worker pool scaling."""
    coordinator = WorkerCoordinator(max_workers=10)

    # Start with 0 workers
    assert len(coordinator.workers) == 0

    # Scale up to 3
    coordinator.scale_workers(3)
    assert len(coordinator.workers) == 3

    # Scale up to 5
    coordinator.scale_workers(5)
    assert len(coordinator.workers) == 5

    # Scale down to 2
    coordinator.scale_workers(2)
    assert len(coordinator.workers) == 2


def test_list_workers():
    """Test listing and filtering workers."""
    coordinator = WorkerCoordinator(max_workers=5)

    # Register workers
    w1 = coordinator.register_worker()
    w2 = coordinator.register_worker()
    w3 = coordinator.register_worker()

    # Assign task to w1
    coordinator.assign_task("task-1", {})

    # List all
    all_workers = coordinator.list_workers()
    assert len(all_workers) == 3

    # List idle
    idle = coordinator.list_workers(status=WorkerStatus.IDLE)
    assert len(idle) == 2

    # List busy
    busy = coordinator.list_workers(status=WorkerStatus.BUSY)
    assert len(busy) == 1


# ===== Live Dashboard Tests =====


def test_dashboard_creation():
    """Test dashboard creation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        session_manager = SessionManager(storage_path=storage_path)
        worker_coordinator = WorkerCoordinator(max_workers=3)

        dashboard = LiveDashboard(session_manager, worker_coordinator)

        assert dashboard.session_manager is session_manager
        assert dashboard.worker_coordinator is worker_coordinator
        assert dashboard.config is not None


def test_dashboard_config():
    """Test dashboard configuration."""
    config = DashboardConfig(
        refresh_rate=1.0,
        show_workers=False,
        compact_mode=True,
    )

    assert config.refresh_rate == 1.0
    assert config.show_workers is False
    assert config.compact_mode is True


def test_dashboard_sessions_table():
    """Test rendering sessions table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        session_manager = SessionManager(storage_path=storage_path)
        worker_coordinator = WorkerCoordinator(max_workers=3)

        # Create sessions
        s1 = session_manager.create_session("Build 1", total_tasks=10)
        session_manager.start_session(s1.session_id)
        session_manager.update_progress(s1.session_id, completed_tasks=5)

        dashboard = LiveDashboard(session_manager, worker_coordinator)
        table = dashboard.render_sessions_table()

        assert table is not None
        assert "Sessions" in table.title


def test_dashboard_workers_table():
    """Test rendering workers table."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        session_manager = SessionManager(storage_path=storage_path)
        worker_coordinator = WorkerCoordinator(max_workers=3)

        # Register workers
        worker_coordinator.register_worker()
        worker_coordinator.register_worker()

        dashboard = LiveDashboard(session_manager, worker_coordinator)
        table = dashboard.render_workers_table()

        assert table is not None
        assert "Worker" in table.title


def test_dashboard_statistics_panel():
    """Test rendering statistics panel."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        session_manager = SessionManager(storage_path=storage_path)
        worker_coordinator = WorkerCoordinator(max_workers=3)

        # Create some activity
        worker_coordinator.register_worker()
        session_manager.create_session("Build 1", total_tasks=10)

        dashboard = LiveDashboard(session_manager, worker_coordinator)
        panel = dashboard.render_statistics_panel()

        assert panel is not None
        assert "Statistics" in panel.title


def test_dashboard_summary():
    """Test getting dashboard summary."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        session_manager = SessionManager(storage_path=storage_path)
        worker_coordinator = WorkerCoordinator(max_workers=3)

        # Create activity
        worker = worker_coordinator.register_worker()
        session = session_manager.create_session("Build 1", total_tasks=10)
        session_manager.start_session(session.session_id)
        worker_coordinator.assign_task("task-1", {})

        dashboard = LiveDashboard(session_manager, worker_coordinator)
        summary = dashboard.get_summary()

        assert 'workers' in summary
        assert 'sessions' in summary
        assert 'tasks' in summary
        assert summary['workers']['total'] == 1
        assert summary['workers']['busy'] == 1
        assert summary['sessions']['active'] == 1


# ===== Integration Tests =====


def test_full_session_workflow():
    """Test complete session workflow with workers."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        session_manager = SessionManager(storage_path=storage_path)
        worker_coordinator = WorkerCoordinator(max_workers=3)

        # Register workers
        w1 = worker_coordinator.register_worker()
        w2 = worker_coordinator.register_worker()

        # Create session
        session = session_manager.create_session("Full Build", total_tasks=5)
        session_manager.start_session(session.session_id)

        # Lock files
        session_manager.lock_files(session.session_id, ["file1.py", "file2.py"])

        # Assign tasks
        worker_coordinator.assign_task("task-1", {}, session_id=session.session_id)
        worker_coordinator.assign_task("task-2", {}, session_id=session.session_id)

        # Complete tasks
        worker_coordinator.complete_task(w1.worker_id, "task-1", success=True)
        worker_coordinator.complete_task(w2.worker_id, "task-2", success=True)

        # Update session progress
        session_manager.update_progress(session.session_id, completed_tasks=2)

        # Mark files modified
        session_manager.mark_files_modified(session.session_id, ["file1.py"])

        # Verify final state
        session = session_manager.get_session(session.session_id)
        assert session.completed_tasks == 2
        assert session.progress_percent == 40.0  # 2/5 * 100
        assert "file1.py" in session.files_modified
        assert len(session.files_locked) == 2

        w1 = worker_coordinator.get_worker(w1.worker_id)
        w2 = worker_coordinator.get_worker(w2.worker_id)
        assert w1.tasks_completed == 1
        assert w2.tasks_completed == 1
        assert w1.status == WorkerStatus.IDLE
        assert w2.status == WorkerStatus.IDLE


def test_multi_session_coordination():
    """Test multiple concurrent sessions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        storage_path = Path(tmpdir) / "sessions.json"
        session_manager = SessionManager(storage_path=storage_path)
        worker_coordinator = WorkerCoordinator(max_workers=4)

        # Register workers
        workers = [worker_coordinator.register_worker() for _ in range(4)]

        # Create multiple sessions
        s1 = session_manager.create_session("Build 1", total_tasks=3)
        s2 = session_manager.create_session("Build 2", total_tasks=4)

        session_manager.start_session(s1.session_id)
        session_manager.start_session(s2.session_id)

        # Lock different files
        session_manager.lock_files(s1.session_id, ["file1.py", "file2.py"])
        session_manager.lock_files(s2.session_id, ["file3.py", "file4.py"])

        # Assign tasks
        worker_coordinator.assign_task("s1-task1", {}, s1.session_id)
        worker_coordinator.assign_task("s1-task2", {}, s1.session_id)
        worker_coordinator.assign_task("s2-task1", {}, s2.session_id)
        worker_coordinator.assign_task("s2-task2", {}, s2.session_id)

        # Verify load distribution
        dist = worker_coordinator.get_load_distribution()
        assert dist['busy_workers'] == 4
        assert dist['utilization'] == 100.0

        # Verify active sessions
        active = session_manager.get_active_sessions()
        assert len(active) == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
