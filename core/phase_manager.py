"""
Phase Manager - Manages build phase tracking and continuous execution

Provides:
- Phase state tracking (8 build phases)
- Blocker detection (credentials, test failures, user flags)
- Auto-proceed logic (check completion, continue to next)
- State persistence (.buildrunner/phase_state.json)
- Phase transition management
"""

from pathlib import Path
from typing import Dict, List, Optional, Any, Set
from dataclasses import dataclass, field, asdict
from enum import Enum
from datetime import datetime
import json


class BuildPhase(Enum):
    """Build execution phases"""
    SPEC_PARSING = "spec_parsing"
    TASK_DECOMPOSITION = "task_decomposition"
    DEPENDENCY_ANALYSIS = "dependency_analysis"
    BATCH_CREATION = "batch_creation"
    CODE_GENERATION = "code_generation"
    TEST_EXECUTION = "test_execution"
    QUALITY_VERIFICATION = "quality_verification"
    DOCUMENTATION = "documentation"
    COMPLETED = "completed"


class PhaseStatus(Enum):
    """Phase execution status"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    FAILED = "failed"
    BLOCKED = "blocked"


class BlockerType(Enum):
    """Types of blockers that pause execution"""
    MISSING_CREDENTIALS = "missing_credentials"
    TEST_FAILURES = "test_failures"
    USER_INTERVENTION = "user_intervention"
    COMPILATION_ERROR = "compilation_error"
    RESOURCE_CONSTRAINT = "resource_constraint"
    NONE = "none"


@dataclass
class Blocker:
    """Represents a blocker that pauses execution"""
    blocker_type: BlockerType
    phase: BuildPhase
    description: str
    detected_at: str = field(default_factory=lambda: datetime.now().isoformat())
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class PhaseState:
    """State of a single build phase"""
    phase: BuildPhase
    status: PhaseStatus
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    duration_seconds: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)
    blockers: List[Blocker] = field(default_factory=list)


@dataclass
class BuildState:
    """Complete build state across all phases"""
    current_phase: BuildPhase = BuildPhase.SPEC_PARSING
    phases: Dict[str, PhaseState] = field(default_factory=dict)
    active_blockers: List[Blocker] = field(default_factory=list)
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    continuous_mode: bool = True
    metadata: Dict[str, Any] = field(default_factory=dict)


class PhaseManager:
    """
    Manages build phase tracking and continuous execution.

    Features:
    - Track progress through 8 build phases
    - Detect blockers (credentials, tests, user flags)
    - Auto-proceed logic
    - State persistence
    - Phase transition management
    """

    def __init__(self, project_root: Path, continuous_mode: bool = True):
        """
        Initialize PhaseManager.

        Args:
            project_root: Project root directory
            continuous_mode: Enable continuous execution (default True)
        """
        self.project_root = Path(project_root)
        self.continuous_mode = continuous_mode

        # State file location
        self.state_dir = self.project_root / ".buildrunner"
        self.state_file = self.state_dir / "phase_state.json"

        # Phase order - MUST be defined before _load_state()
        self.phase_order = [
            BuildPhase.SPEC_PARSING,
            BuildPhase.TASK_DECOMPOSITION,
            BuildPhase.DEPENDENCY_ANALYSIS,
            BuildPhase.BATCH_CREATION,
            BuildPhase.CODE_GENERATION,
            BuildPhase.TEST_EXECUTION,
            BuildPhase.QUALITY_VERIFICATION,
            BuildPhase.DOCUMENTATION,
        ]

        # Load or initialize state
        self.state = self._load_state()

    def _load_state(self) -> BuildState:
        """Load build state from disk or create new"""
        if self.state_file.exists():
            try:
                data = json.loads(self.state_file.read_text())

                # Reconstruct state with enums
                phases = {}
                for phase_name, phase_data in data.get('phases', {}).items():
                    blockers = [
                        Blocker(
                            blocker_type=BlockerType(b['blocker_type']),
                            phase=BuildPhase(b['phase']),
                            description=b['description'],
                            detected_at=b.get('detected_at', datetime.now().isoformat()),
                            metadata=b.get('metadata', {})
                        )
                        for b in phase_data.get('blockers', [])
                    ]

                    phases[phase_name] = PhaseState(
                        phase=BuildPhase(phase_data['phase']),
                        status=PhaseStatus(phase_data['status']),
                        started_at=phase_data.get('started_at'),
                        completed_at=phase_data.get('completed_at'),
                        duration_seconds=phase_data.get('duration_seconds'),
                        metadata=phase_data.get('metadata', {}),
                        blockers=blockers
                    )

                active_blockers = [
                    Blocker(
                        blocker_type=BlockerType(b['blocker_type']),
                        phase=BuildPhase(b['phase']),
                        description=b['description'],
                        detected_at=b.get('detected_at', datetime.now().isoformat()),
                        metadata=b.get('metadata', {})
                    )
                    for b in data.get('active_blockers', [])
                ]

                return BuildState(
                    current_phase=BuildPhase(data['current_phase']),
                    phases=phases,
                    active_blockers=active_blockers,
                    started_at=data.get('started_at'),
                    completed_at=data.get('completed_at'),
                    continuous_mode=data.get('continuous_mode', True),
                    metadata=data.get('metadata', {})
                )
            except Exception as e:
                print(f"Warning: Failed to load state: {e}, creating new state")

        # Create new state
        state = BuildState(continuous_mode=self.continuous_mode)

        # Initialize all phases
        for phase in self.phase_order:
            state.phases[phase.value] = PhaseState(
                phase=phase,
                status=PhaseStatus.PENDING
            )

        return state

    def _save_state(self):
        """Save build state to disk"""
        self.state_dir.mkdir(exist_ok=True)

        # Convert to serializable dict
        data = {
            'current_phase': self.state.current_phase.value,
            'phases': {
                name: {
                    'phase': ps.phase.value,
                    'status': ps.status.value,
                    'started_at': ps.started_at,
                    'completed_at': ps.completed_at,
                    'duration_seconds': ps.duration_seconds,
                    'metadata': ps.metadata,
                    'blockers': [
                        {
                            'blocker_type': b.blocker_type.value,
                            'phase': b.phase.value,
                            'description': b.description,
                            'detected_at': b.detected_at,
                            'metadata': b.metadata
                        }
                        for b in ps.blockers
                    ]
                }
                for name, ps in self.state.phases.items()
            },
            'active_blockers': [
                {
                    'blocker_type': b.blocker_type.value,
                    'phase': b.phase.value,
                    'description': b.description,
                    'detected_at': b.detected_at,
                    'metadata': b.metadata
                }
                for b in self.state.active_blockers
            ],
            'started_at': self.state.started_at,
            'completed_at': self.state.completed_at,
            'continuous_mode': self.state.continuous_mode,
            'metadata': self.state.metadata
        }

        self.state_file.write_text(json.dumps(data, indent=2))

    def start_phase(self, phase: BuildPhase) -> bool:
        """
        Start a build phase.

        Args:
            phase: Phase to start

        Returns:
            True if started successfully, False if blocked
        """
        # Check for active blockers
        if self.state.active_blockers:
            return False

        # Update phase state
        phase_state = self.state.phases.get(phase.value)
        if not phase_state:
            phase_state = PhaseState(phase=phase, status=PhaseStatus.IN_PROGRESS)
            self.state.phases[phase.value] = phase_state
        else:
            phase_state.status = PhaseStatus.IN_PROGRESS

        phase_state.started_at = datetime.now().isoformat()

        # Update build state
        self.state.current_phase = phase
        if not self.state.started_at:
            self.state.started_at = datetime.now().isoformat()

        self._save_state()
        return True

    def complete_phase(self, phase: BuildPhase, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark a phase as completed.

        Args:
            phase: Phase to complete
            metadata: Optional metadata about completion

        Returns:
            True if completed successfully
        """
        phase_state = self.state.phases.get(phase.value)
        if not phase_state:
            return False

        # Calculate duration
        if phase_state.started_at:
            started = datetime.fromisoformat(phase_state.started_at)
            completed = datetime.now()
            phase_state.duration_seconds = (completed - started).total_seconds()

        phase_state.status = PhaseStatus.COMPLETED
        phase_state.completed_at = datetime.now().isoformat()

        if metadata:
            phase_state.metadata.update(metadata)

        self._save_state()
        return True

    def fail_phase(self, phase: BuildPhase, error: str, metadata: Optional[Dict[str, Any]] = None) -> bool:
        """
        Mark a phase as failed.

        Args:
            phase: Phase that failed
            error: Error description
            metadata: Optional error metadata

        Returns:
            True if marked failed
        """
        phase_state = self.state.phases.get(phase.value)
        if not phase_state:
            return False

        phase_state.status = PhaseStatus.FAILED
        phase_state.metadata['error'] = error

        if metadata:
            phase_state.metadata.update(metadata)

        self._save_state()
        return True

    def add_blocker(self, blocker_type: BlockerType, description: str,
                    metadata: Optional[Dict[str, Any]] = None) -> Blocker:
        """
        Add a blocker to the current phase.

        Args:
            blocker_type: Type of blocker
            description: Human-readable description
            metadata: Optional blocker metadata

        Returns:
            Created blocker
        """
        blocker = Blocker(
            blocker_type=blocker_type,
            phase=self.state.current_phase,
            description=description,
            metadata=metadata or {}
        )

        # Add to active blockers
        self.state.active_blockers.append(blocker)

        # Add to phase
        phase_state = self.state.phases.get(self.state.current_phase.value)
        if phase_state:
            phase_state.blockers.append(blocker)
            phase_state.status = PhaseStatus.BLOCKED

        self._save_state()
        return blocker

    def clear_blocker(self, blocker_type: BlockerType) -> bool:
        """
        Clear a blocker by type.

        Args:
            blocker_type: Type of blocker to clear

        Returns:
            True if blocker was found and cleared
        """
        # Filter out blockers of this type
        original_count = len(self.state.active_blockers)
        self.state.active_blockers = [
            b for b in self.state.active_blockers
            if b.blocker_type != blocker_type
        ]

        # Resume phase if no more blockers
        if not self.state.active_blockers:
            phase_state = self.state.phases.get(self.state.current_phase.value)
            if phase_state and phase_state.status == PhaseStatus.BLOCKED:
                phase_state.status = PhaseStatus.IN_PROGRESS

        self._save_state()
        return len(self.state.active_blockers) < original_count

    def is_blocked(self) -> bool:
        """Check if execution is currently blocked"""
        return len(self.state.active_blockers) > 0

    def get_active_blockers(self) -> List[Blocker]:
        """Get list of active blockers"""
        return self.state.active_blockers.copy()

    def get_next_phase(self) -> Optional[BuildPhase]:
        """
        Get the next phase to execute.

        Returns:
            Next phase, or None if all complete
        """
        current_index = self.phase_order.index(self.state.current_phase)

        if current_index + 1 < len(self.phase_order):
            return self.phase_order[current_index + 1]

        return None

    def can_proceed(self) -> bool:
        """
        Check if can proceed to next phase.

        Returns:
            True if current phase is complete and no blockers
        """
        if self.is_blocked():
            return False

        phase_state = self.state.phases.get(self.state.current_phase.value)
        if not phase_state:
            return False

        return phase_state.status == PhaseStatus.COMPLETED

    def should_continue(self) -> bool:
        """
        Check if should continue to next phase automatically.

        Returns:
            True if continuous mode enabled and can proceed
        """
        if not self.continuous_mode:
            return False

        return self.can_proceed()

    def get_progress(self) -> Dict[str, Any]:
        """
        Get build progress summary.

        Returns:
            Progress summary with percentages and phase info
        """
        total_phases = len(self.phase_order)
        completed_phases = sum(
            1 for ps in self.state.phases.values()
            if ps.status == PhaseStatus.COMPLETED
        )

        progress_percent = (completed_phases / total_phases) * 100 if total_phases > 0 else 0

        return {
            'current_phase': self.state.current_phase.value,
            'total_phases': total_phases,
            'completed_phases': completed_phases,
            'progress_percent': progress_percent,
            'is_blocked': self.is_blocked(),
            'active_blockers': len(self.state.active_blockers),
            'continuous_mode': self.continuous_mode,
            'phases': {
                name: {
                    'status': ps.status.value,
                    'duration_seconds': ps.duration_seconds
                }
                for name, ps in self.state.phases.items()
            }
        }

    def reset(self):
        """Reset build state to initial state"""
        self.state = BuildState(continuous_mode=self.continuous_mode)

        # Initialize all phases
        for phase in self.phase_order:
            self.state.phases[phase.value] = PhaseState(
                phase=phase,
                status=PhaseStatus.PENDING
            )

        self._save_state()

    def get_state(self) -> BuildState:
        """Get current build state"""
        return self.state
