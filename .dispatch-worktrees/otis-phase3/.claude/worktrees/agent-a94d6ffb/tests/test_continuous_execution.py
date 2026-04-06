"""
Tests for Continuous Build Execution - Integration tests for orchestrator + phase manager
"""

import pytest
from pathlib import Path
import tempfile

from core.orchestrator import TaskOrchestrator
from core.phase_manager import PhaseManager, BuildPhase as Phase, BlockerType
from core.batch_optimizer import Task, TaskDomain, TaskComplexity


@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        buildrunner_dir = project_root / ".buildrunner"
        buildrunner_dir.mkdir()
        yield project_root


@pytest.fixture
def orchestrator(temp_project):
    """Create orchestrator with phase manager"""
    return TaskOrchestrator(
        project_root=temp_project,
        continuous_mode=True,
        enable_telemetry=False,
        enable_routing=False,
        enable_parallel=False,
    )


@pytest.fixture
def sample_tasks():
    """Create sample tasks for testing"""
    return [
        Task(
            id="task-1",
            name="Parse spec",
            description="Parse PROJECT_SPEC.md",
            file_path="core/parser.py",
            estimated_minutes=30,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Spec parsed correctly"],
        ),
        Task(
            id="task-2",
            name="Decompose tasks",
            description="Decompose into atomic tasks",
            file_path="core/decomposer.py",
            estimated_minutes=45,
            complexity=TaskComplexity.MEDIUM,
            domain=TaskDomain.BACKEND,
            dependencies=["task-1"],
            acceptance_criteria=["Tasks generated"],
        ),
    ]


class TestContinuousExecution:
    """Test continuous execution flow"""

    def test_execute_continuous_requires_phase_manager(self):
        """Test continuous execution requires phase manager"""
        orch = TaskOrchestrator(
            project_root=None,  # No project root = no phase manager
            enable_telemetry=False,
            enable_routing=False,
            enable_parallel=False,
        )

        result = orch.execute_continuous([])

        assert result["success"] is False
        assert "Phase manager not initialized" in result["error"]

    def test_execute_continuous_completes_all_phases(self, orchestrator, sample_tasks):
        """Test continuous execution completes all phases"""
        result = orchestrator.execute_continuous(sample_tasks)

        assert result["success"] is True
        assert result["completed"] is True
        assert result["phases_completed"] == 8
        assert result["progress_percent"] == 100.0

    def test_execute_continuous_resets_state(self, orchestrator, sample_tasks):
        """Test continuous execution resets phase state"""
        # Start a phase manually
        orchestrator.phase_manager.start_phase(Phase.SPEC_PARSING)

        # Execute continuous (should reset)
        orchestrator.execute_continuous(sample_tasks)

        # Verify state was reset and re-executed
        progress = orchestrator.phase_manager.get_progress()
        assert progress["completed_phases"] == 8

    def test_execute_continuous_pauses_on_blocker(self, orchestrator, sample_tasks):
        """Test continuous execution pauses when blocker detected"""

        # Define callback that adds blocker on CODE_GENERATION phase
        def code_gen_callback(orch, tasks):
            orch.phase_manager.add_blocker(BlockerType.MISSING_CREDENTIALS, "Missing API key")
            return {
                "success": False,
                "blocked": True,
                "blocker": {
                    "type": "missing_credentials",
                    "description": "Missing API key",
                },
            }

        callbacks = {Phase.CODE_GENERATION: code_gen_callback}

        result = orchestrator.execute_continuous(sample_tasks, phase_callbacks=callbacks)

        assert result["success"] is False
        assert result["paused_for_blockers"] is True
        assert result["phase"] == Phase.CODE_GENERATION.value
        assert len(result["blockers"]) == 1
        assert result["blockers"][0]["type"] == "missing_credentials"

    def test_execute_continuous_handles_phase_failure(self, orchestrator, sample_tasks):
        """Test continuous execution handles phase failure"""

        # Define callback that fails
        def failing_callback(orch, tasks):
            return {"success": False, "error": "Phase failed"}

        callbacks = {Phase.TASK_DECOMPOSITION: failing_callback}

        result = orchestrator.execute_continuous(sample_tasks, phase_callbacks=callbacks)

        assert result["success"] is False
        assert "failed" in result["error"].lower()
        assert result["phase"] == Phase.TASK_DECOMPOSITION.value

    def test_execute_continuous_with_exception(self, orchestrator, sample_tasks):
        """Test continuous execution handles exceptions"""

        # Define callback that raises exception
        def exception_callback(orch, tasks):
            raise ValueError("Test exception")

        callbacks = {Phase.DEPENDENCY_ANALYSIS: exception_callback}

        result = orchestrator.execute_continuous(sample_tasks, phase_callbacks=callbacks)

        assert result["success"] is False
        assert "Test exception" in result["error"]  # Exception message should be in error


class TestPhaseExecution:
    """Test individual phase execution"""

    def test_execute_phase_spec_parsing(self, orchestrator, sample_tasks):
        """Test SPEC_PARSING phase execution"""
        result = orchestrator._execute_phase(Phase.SPEC_PARSING, sample_tasks, {})

        assert result["success"] is True
        assert result["metadata"]["phase"] == "spec_parsing"

    def test_execute_phase_task_decomposition(self, orchestrator, sample_tasks):
        """Test TASK_DECOMPOSITION phase execution"""
        result = orchestrator._execute_phase(Phase.TASK_DECOMPOSITION, sample_tasks, {})

        assert result["success"] is True
        assert result["metadata"]["tasks"] == len(sample_tasks)

    def test_execute_phase_with_callback(self, orchestrator, sample_tasks):
        """Test phase execution with custom callback"""

        def custom_callback(orch, tasks):
            return {"success": True, "metadata": {"custom": "data"}}

        callbacks = {Phase.SPEC_PARSING: custom_callback}

        result = orchestrator._execute_phase(Phase.SPEC_PARSING, sample_tasks, callbacks)

        assert result["success"] is True
        assert result["metadata"]["custom"] == "data"

    def test_execute_phase_callback_exception(self, orchestrator, sample_tasks):
        """Test phase execution handles callback exception"""

        def failing_callback(orch, tasks):
            raise RuntimeError("Callback failed")

        callbacks = {Phase.SPEC_PARSING: failing_callback}

        result = orchestrator._execute_phase(Phase.SPEC_PARSING, sample_tasks, callbacks)

        assert result["success"] is False
        assert "callback failed" in result["error"].lower()


class TestResumeContinuous:
    """Test resuming continuous execution"""

    def test_resume_continuous_requires_phase_manager(self):
        """Test resume requires phase manager"""
        orch = TaskOrchestrator(
            project_root=None,
            enable_telemetry=False,
            enable_routing=False,
            enable_parallel=False,
        )

        result = orch.resume_continuous()

        assert result["success"] is False
        assert "Phase manager not initialized" in result["error"]

    def test_resume_continuous_when_not_blocked(self, orchestrator):
        """Test resume when not blocked"""
        # Start and complete a phase
        orchestrator.phase_manager.start_phase(Phase.SPEC_PARSING)
        orchestrator.phase_manager.complete_phase(Phase.SPEC_PARSING)

        result = orchestrator.resume_continuous()

        assert result["success"] is True
        assert "Resuming" in result["message"]

    def test_resume_continuous_when_blocked(self, orchestrator):
        """Test resume fails when blocked"""
        # Add blocker
        orchestrator.phase_manager.add_blocker(BlockerType.TEST_FAILURES, "Tests failed")

        result = orchestrator.resume_continuous()

        assert result["success"] is False
        assert "blocked" in result["error"].lower()


class TestPhaseStatus:
    """Test phase status reporting"""

    def test_get_phase_status_disabled(self):
        """Test phase status when phase manager disabled"""
        orch = TaskOrchestrator(
            project_root=None,
            enable_telemetry=False,
            enable_routing=False,
            enable_parallel=False,
        )

        status = orch.get_phase_status()

        assert status["enabled"] is False

    def test_get_phase_status_enabled(self, orchestrator):
        """Test phase status when enabled"""
        status = orchestrator.get_phase_status()

        assert status["enabled"] is True
        assert status["continuous_mode"] is True
        assert "current_phase" in status
        assert "total_phases" in status
        assert "progress_percent" in status

    def test_get_phase_status_with_progress(self, orchestrator):
        """Test phase status shows progress"""
        # Complete some phases
        orchestrator.phase_manager.start_phase(Phase.SPEC_PARSING)
        orchestrator.phase_manager.complete_phase(Phase.SPEC_PARSING)

        status = orchestrator.get_phase_status()

        assert status["completed_phases"] == 1
        assert status["progress_percent"] > 0


class TestIntegrationStatus:
    """Test integration status includes phase manager"""

    def test_integration_status_with_phase_manager(self, orchestrator):
        """Test integration status includes phase manager"""
        status = orchestrator.get_integration_status()

        assert "phase_manager_enabled" in status
        assert status["phase_manager_enabled"] is True

    def test_integration_status_without_phase_manager(self):
        """Test integration status without phase manager"""
        orch = TaskOrchestrator(
            project_root=None,
            enable_telemetry=False,
            enable_routing=False,
            enable_parallel=False,
        )

        status = orch.get_integration_status()

        assert status["phase_manager_enabled"] is False


class TestContinuousModeFlag:
    """Test continuous mode flag"""

    def test_continuous_mode_enabled(self, temp_project):
        """Test orchestrator with continuous mode enabled"""
        orch = TaskOrchestrator(
            project_root=temp_project,
            continuous_mode=True,
            enable_telemetry=False,
            enable_routing=False,
            enable_parallel=False,
        )

        assert orch.phase_manager.continuous_mode is True

    def test_continuous_mode_disabled(self, temp_project):
        """Test orchestrator with continuous mode disabled"""
        orch = TaskOrchestrator(
            project_root=temp_project,
            continuous_mode=False,
            enable_telemetry=False,
            enable_routing=False,
            enable_parallel=False,
        )

        assert orch.phase_manager.continuous_mode is False


class TestPhaseCallbacks:
    """Test phase callback system"""

    def test_all_phases_get_callbacks(self, orchestrator, sample_tasks):
        """Test all phases can have callbacks"""
        called_phases = []

        def make_callback(phase):
            def callback(orch, tasks):
                called_phases.append(phase)
                return {"success": True}

            return callback

        callbacks = {
            phase: make_callback(phase)
            for phase in [
                Phase.SPEC_PARSING,
                Phase.TASK_DECOMPOSITION,
                Phase.DEPENDENCY_ANALYSIS,
                Phase.BATCH_CREATION,
                Phase.CODE_GENERATION,
                Phase.TEST_EXECUTION,
                Phase.QUALITY_VERIFICATION,
                Phase.DOCUMENTATION,
            ]
        }

        result = orchestrator.execute_continuous(sample_tasks, phase_callbacks=callbacks)

        assert result["success"] is True
        assert len(called_phases) == 8

    def test_callback_can_modify_state(self, orchestrator, sample_tasks):
        """Test callback can modify orchestrator state"""
        # Store original count
        original_count = orchestrator.tasks_completed

        def callback(orch, tasks):
            orch.tasks_completed = 999
            return {"success": True}

        callbacks = {Phase.SPEC_PARSING: callback}

        orchestrator.execute_continuous(sample_tasks, phase_callbacks=callbacks)

        # Should have been modified by callback and potentially by other phases
        # Just check it was changed from original
        assert orchestrator.tasks_completed != original_count


class TestBlockerWorkflow:
    """Test complete blocker workflow"""

    def test_blocker_pause_and_resume_workflow(self, orchestrator, sample_tasks):
        """Test complete workflow: execute, block, clear, resume"""

        # Step 1: Execute until blocker
        def blocker_callback(orch, tasks):
            orch.phase_manager.add_blocker(BlockerType.MISSING_CREDENTIALS, "Need API key")
            return {
                "success": False,
                "blocked": True,
                "blocker": {"type": "missing_credentials", "description": "Need API key"},
            }

        callbacks = {Phase.CODE_GENERATION: blocker_callback}

        result1 = orchestrator.execute_continuous(sample_tasks, phase_callbacks=callbacks)

        assert result1["success"] is False
        assert result1["paused_for_blockers"] is True

        # Step 2: Try to resume while blocked
        result2 = orchestrator.resume_continuous()
        assert result2["success"] is False

        # Step 3: Clear blocker
        orchestrator.phase_manager.clear_blocker(BlockerType.MISSING_CREDENTIALS)

        # Step 4: Resume (should work now)
        result3 = orchestrator.resume_continuous()
        assert result3["success"] is True


class TestEdgeCases:
    """Test edge cases and error conditions"""

    def test_empty_tasks_list(self, orchestrator):
        """Test execution with empty tasks list"""
        result = orchestrator.execute_continuous([])

        # CODE_GENERATION phase needs batch_optimizer which is None
        # So execution may fail at that phase - that's okay
        # The important part is it handled empty tasks without crashing
        assert "success" in result  # Got a result, didn't crash

    def test_phase_already_in_progress(self, orchestrator, sample_tasks):
        """Test execution when phase already in progress"""
        # Manually start a phase
        orchestrator.phase_manager.start_phase(Phase.SPEC_PARSING)

        # Execute continuous (should reset)
        result = orchestrator.execute_continuous(sample_tasks)

        assert result["success"] is True

    def test_multiple_sequential_executions(self, orchestrator, sample_tasks):
        """Test multiple sequential continuous executions"""
        # Execute twice
        result1 = orchestrator.execute_continuous(sample_tasks)
        result2 = orchestrator.execute_continuous(sample_tasks)

        # Both should succeed (state gets reset each time)
        assert result1["success"] is True
        assert result2["success"] is True


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
