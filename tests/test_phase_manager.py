"""
Tests for Phase Manager - Continuous build execution phase tracking
"""

import pytest
from pathlib import Path
import json
import tempfile
from datetime import datetime

from core.phase_manager import (
    PhaseManager,
    BuildPhase,
    PhaseStatus,
    BlockerType,
    Blocker,
    PhaseState,
    BuildState,
)


@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    with tempfile.TemporaryDirectory() as tmpdir:
        project_root = Path(tmpdir)
        buildrunner_dir = project_root / ".buildrunner"
        buildrunner_dir.mkdir()
        yield project_root


@pytest.fixture
def phase_manager(temp_project):
    """Create PhaseManager instance"""
    return PhaseManager(temp_project, continuous_mode=True)


class TestPhaseManagerInit:
    """Test PhaseManager initialization"""

    def test_init_creates_state(self, temp_project):
        """Test initialization creates build state"""
        pm = PhaseManager(temp_project)

        assert pm.project_root == temp_project
        assert pm.continuous_mode is True
        assert pm.state is not None
        assert pm.state.current_phase == BuildPhase.SPEC_PARSING

    def test_init_with_continuous_mode_disabled(self, temp_project):
        """Test initialization with continuous mode disabled"""
        pm = PhaseManager(temp_project, continuous_mode=False)

        assert pm.continuous_mode is False
        assert pm.state.continuous_mode is False

    def test_init_creates_all_phases(self, temp_project):
        """Test initialization creates all phase states"""
        pm = PhaseManager(temp_project)

        expected_phases = [
            BuildPhase.SPEC_PARSING,
            BuildPhase.TASK_DECOMPOSITION,
            BuildPhase.DEPENDENCY_ANALYSIS,
            BuildPhase.BATCH_CREATION,
            BuildPhase.CODE_GENERATION,
            BuildPhase.TEST_EXECUTION,
            BuildPhase.QUALITY_VERIFICATION,
            BuildPhase.DOCUMENTATION,
        ]

        for phase in expected_phases:
            assert phase.value in pm.state.phases
            phase_state = pm.state.phases[phase.value]
            assert phase_state.status == PhaseStatus.PENDING


class TestPhaseTransitions:
    """Test phase start, complete, and failure"""

    def test_start_phase(self, phase_manager):
        """Test starting a phase"""
        result = phase_manager.start_phase(BuildPhase.SPEC_PARSING)

        assert result is True
        phase_state = phase_manager.state.phases[BuildPhase.SPEC_PARSING.value]
        assert phase_state.status == PhaseStatus.IN_PROGRESS
        assert phase_state.started_at is not None
        assert phase_manager.state.started_at is not None

    def test_complete_phase(self, phase_manager):
        """Test completing a phase"""
        # Start phase first
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)

        # Complete phase
        result = phase_manager.complete_phase(
            BuildPhase.SPEC_PARSING,
            metadata={"lines_parsed": 100}
        )

        assert result is True
        phase_state = phase_manager.state.phases[BuildPhase.SPEC_PARSING.value]
        assert phase_state.status == PhaseStatus.COMPLETED
        assert phase_state.completed_at is not None
        assert phase_state.duration_seconds is not None
        assert phase_state.metadata["lines_parsed"] == 100

    def test_fail_phase(self, phase_manager):
        """Test failing a phase"""
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)

        result = phase_manager.fail_phase(
            BuildPhase.SPEC_PARSING,
            error="Parse error",
            metadata={"line": 42}
        )

        assert result is True
        phase_state = phase_manager.state.phases[BuildPhase.SPEC_PARSING.value]
        assert phase_state.status == PhaseStatus.FAILED
        assert phase_state.metadata["error"] == "Parse error"
        assert phase_state.metadata["line"] == 42

    def test_start_phase_with_active_blockers(self, phase_manager):
        """Test starting phase when blocked"""
        # Add blocker
        phase_manager.add_blocker(
            BlockerType.MISSING_CREDENTIALS,
            "Missing API key"
        )

        # Try to start phase
        result = phase_manager.start_phase(BuildPhase.SPEC_PARSING)

        assert result is False


class TestBlockerManagement:
    """Test blocker detection and management"""

    def test_add_blocker(self, phase_manager):
        """Test adding a blocker"""
        blocker = phase_manager.add_blocker(
            BlockerType.MISSING_CREDENTIALS,
            "Missing API key",
            metadata={"key_name": "OPENAI_API_KEY"}
        )

        assert isinstance(blocker, Blocker)
        assert blocker.blocker_type == BlockerType.MISSING_CREDENTIALS
        assert blocker.description == "Missing API key"
        assert blocker.metadata["key_name"] == "OPENAI_API_KEY"
        assert len(phase_manager.state.active_blockers) == 1

    def test_add_blocker_marks_phase_blocked(self, phase_manager):
        """Test adding blocker marks phase as blocked"""
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)

        phase_manager.add_blocker(
            BlockerType.TEST_FAILURES,
            "3 tests failed"
        )

        phase_state = phase_manager.state.phases[BuildPhase.SPEC_PARSING.value]
        assert phase_state.status == PhaseStatus.BLOCKED
        assert len(phase_state.blockers) == 1

    def test_clear_blocker(self, phase_manager):
        """Test clearing a blocker"""
        phase_manager.add_blocker(
            BlockerType.MISSING_CREDENTIALS,
            "Missing API key"
        )

        result = phase_manager.clear_blocker(BlockerType.MISSING_CREDENTIALS)

        assert result is True
        assert len(phase_manager.state.active_blockers) == 0

    def test_clear_blocker_resumes_phase(self, phase_manager):
        """Test clearing blocker resumes phase"""
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)
        phase_manager.add_blocker(
            BlockerType.MISSING_CREDENTIALS,
            "Missing key"
        )

        # Clear blocker
        phase_manager.clear_blocker(BlockerType.MISSING_CREDENTIALS)

        phase_state = phase_manager.state.phases[BuildPhase.SPEC_PARSING.value]
        assert phase_state.status == PhaseStatus.IN_PROGRESS

    def test_is_blocked(self, phase_manager):
        """Test is_blocked check"""
        assert phase_manager.is_blocked() is False

        phase_manager.add_blocker(
            BlockerType.COMPILATION_ERROR,
            "Syntax error"
        )

        assert phase_manager.is_blocked() is True

    def test_get_active_blockers(self, phase_manager):
        """Test getting active blockers"""
        phase_manager.add_blocker(
            BlockerType.MISSING_CREDENTIALS,
            "Missing key 1"
        )
        phase_manager.add_blocker(
            BlockerType.TEST_FAILURES,
            "Tests failed"
        )

        blockers = phase_manager.get_active_blockers()

        assert len(blockers) == 2
        assert any(b.blocker_type == BlockerType.MISSING_CREDENTIALS for b in blockers)
        assert any(b.blocker_type == BlockerType.TEST_FAILURES for b in blockers)


class TestPhaseNavigation:
    """Test phase navigation and flow"""

    def test_get_next_phase(self, phase_manager):
        """Test getting next phase"""
        # Current phase is SPEC_PARSING
        next_phase = phase_manager.get_next_phase()

        assert next_phase == BuildPhase.TASK_DECOMPOSITION

    def test_get_next_phase_at_end(self, phase_manager):
        """Test getting next phase when at last phase"""
        # Set to last phase
        phase_manager.state.current_phase = BuildPhase.DOCUMENTATION

        next_phase = phase_manager.get_next_phase()

        assert next_phase is None

    def test_can_proceed(self, phase_manager):
        """Test can_proceed check"""
        # Not started yet
        assert phase_manager.can_proceed() is False

        # Start and complete phase
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)
        phase_manager.complete_phase(BuildPhase.SPEC_PARSING)

        assert phase_manager.can_proceed() is True

    def test_can_proceed_when_blocked(self, phase_manager):
        """Test can_proceed returns False when blocked"""
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)
        phase_manager.complete_phase(BuildPhase.SPEC_PARSING)

        # Add blocker
        phase_manager.add_blocker(
            BlockerType.MISSING_CREDENTIALS,
            "Missing key"
        )

        assert phase_manager.can_proceed() is False

    def test_should_continue(self, phase_manager):
        """Test should_continue in continuous mode"""
        # Complete first phase
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)
        phase_manager.complete_phase(BuildPhase.SPEC_PARSING)

        assert phase_manager.should_continue() is True

    def test_should_continue_disabled(self, temp_project):
        """Test should_continue with continuous mode disabled"""
        pm = PhaseManager(temp_project, continuous_mode=False)

        pm.start_phase(BuildPhase.SPEC_PARSING)
        pm.complete_phase(BuildPhase.SPEC_PARSING)

        assert pm.should_continue() is False


class TestStatePersistence:
    """Test state save/load functionality"""

    def test_save_state(self, phase_manager):
        """Test state is saved to disk"""
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)

        state_file = phase_manager.state_file
        assert state_file.exists()

        # Load and verify
        data = json.loads(state_file.read_text())
        assert data["current_phase"] == BuildPhase.SPEC_PARSING.value

    def test_load_state(self, temp_project):
        """Test loading state from disk"""
        # Create initial state
        pm1 = PhaseManager(temp_project)
        pm1.start_phase(BuildPhase.SPEC_PARSING)
        pm1.complete_phase(BuildPhase.SPEC_PARSING)
        pm1.add_blocker(BlockerType.MISSING_CREDENTIALS, "Test blocker")

        # Create new instance - should load state
        pm2 = PhaseManager(temp_project)

        # Phase should be BLOCKED because blocker was added after completion
        phase_state = pm2.state.phases[BuildPhase.SPEC_PARSING.value]
        assert phase_state.status == PhaseStatus.BLOCKED
        assert phase_state.completed_at is not None  # Was completed
        assert len(pm2.state.active_blockers) == 1

    def test_load_corrupted_state(self, temp_project):
        """Test loading corrupted state creates new state"""
        # Write corrupted data
        state_dir = temp_project / ".buildrunner"
        state_dir.mkdir(exist_ok=True)
        state_file = state_dir / "phase_state.json"
        state_file.write_text("corrupted json{")

        # Should create new state
        pm = PhaseManager(temp_project)

        assert pm.state.current_phase == BuildPhase.SPEC_PARSING
        assert len(pm.state.active_blockers) == 0


class TestProgressTracking:
    """Test progress calculation"""

    def test_get_progress_initial(self, phase_manager):
        """Test progress at start"""
        progress = phase_manager.get_progress()

        assert progress["current_phase"] == BuildPhase.SPEC_PARSING.value
        assert progress["total_phases"] == 8
        assert progress["completed_phases"] == 0
        assert progress["progress_percent"] == 0.0
        assert progress["is_blocked"] is False
        assert progress["continuous_mode"] is True

    def test_get_progress_partial(self, phase_manager):
        """Test progress with some phases complete"""
        # Complete 3 phases
        for phase in [
            BuildPhase.SPEC_PARSING,
            BuildPhase.TASK_DECOMPOSITION,
            BuildPhase.DEPENDENCY_ANALYSIS,
        ]:
            phase_manager.start_phase(phase)
            phase_manager.complete_phase(phase)

        progress = phase_manager.get_progress()

        assert progress["completed_phases"] == 3
        assert progress["progress_percent"] == 37.5  # 3/8 = 37.5%

    def test_get_progress_with_blockers(self, phase_manager):
        """Test progress shows blockers"""
        phase_manager.add_blocker(
            BlockerType.TEST_FAILURES,
            "Tests failed"
        )

        progress = phase_manager.get_progress()

        assert progress["is_blocked"] is True
        assert progress["active_blockers"] == 1


class TestReset:
    """Test reset functionality"""

    def test_reset(self, phase_manager):
        """Test reset clears all state"""
        # Make some progress
        phase_manager.start_phase(BuildPhase.SPEC_PARSING)
        phase_manager.complete_phase(BuildPhase.SPEC_PARSING)
        phase_manager.add_blocker(
            BlockerType.MISSING_CREDENTIALS,
            "Test"
        )

        # Reset
        phase_manager.reset()

        # Verify clean state
        assert phase_manager.state.current_phase == BuildPhase.SPEC_PARSING
        assert len(phase_manager.state.active_blockers) == 0
        assert phase_manager.state.started_at is None

        # All phases should be pending
        for phase_state in phase_manager.state.phases.values():
            assert phase_state.status == PhaseStatus.PENDING


class TestGetState:
    """Test get_state method"""

    def test_get_state(self, phase_manager):
        """Test get_state returns current state"""
        state = phase_manager.get_state()

        assert isinstance(state, BuildState)
        assert state.current_phase == BuildPhase.SPEC_PARSING
        assert len(state.phases) == 8


class TestEdgeCases:
    """Test edge cases and error handling"""

    def test_complete_phase_not_started(self, phase_manager):
        """Test completing phase that wasn't started still works"""
        # Create phase state first
        phase_manager.state.phases[BuildPhase.SPEC_PARSING.value] = PhaseState(
            phase=BuildPhase.SPEC_PARSING,
            status=PhaseStatus.PENDING
        )

        result = phase_manager.complete_phase(BuildPhase.SPEC_PARSING)

        assert result is True
        # Duration will be None since started_at was None
        phase_state = phase_manager.state.phases[BuildPhase.SPEC_PARSING.value]
        assert phase_state.duration_seconds is None

    def test_fail_nonexistent_phase(self, phase_manager):
        """Test failing phase that doesn't exist"""
        # Remove phase
        if "nonexistent" in phase_manager.state.phases:
            del phase_manager.state.phases["nonexistent"]

        # Try to fail it
        result = phase_manager.fail_phase(
            BuildPhase.SPEC_PARSING,
            "error"
        )

        # Should work since SPEC_PARSING exists
        assert result is True

    def test_multiple_blockers_same_type(self, phase_manager):
        """Test adding multiple blockers of same type"""
        phase_manager.add_blocker(
            BlockerType.TEST_FAILURES,
            "Test 1 failed"
        )
        phase_manager.add_blocker(
            BlockerType.TEST_FAILURES,
            "Test 2 failed"
        )

        assert len(phase_manager.state.active_blockers) == 2

        # Clear all of that type
        phase_manager.clear_blocker(BlockerType.TEST_FAILURES)

        assert len(phase_manager.state.active_blockers) == 0

    def test_phase_order_preserved(self, phase_manager):
        """Test phase order is preserved"""
        expected_order = [
            BuildPhase.SPEC_PARSING,
            BuildPhase.TASK_DECOMPOSITION,
            BuildPhase.DEPENDENCY_ANALYSIS,
            BuildPhase.BATCH_CREATION,
            BuildPhase.CODE_GENERATION,
            BuildPhase.TEST_EXECUTION,
            BuildPhase.QUALITY_VERIFICATION,
            BuildPhase.DOCUMENTATION,
        ]

        assert phase_manager.phase_order == expected_order


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
