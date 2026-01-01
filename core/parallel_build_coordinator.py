# PRD Feature: FEAT-PARA-001 through FEAT-PARA-005
"""
Parallel Build Coordinator - Cross-instance coordination for BUILD specs

Enables multiple Claude instances to work on different phases of a BUILD spec
simultaneously. Uses file-based locking for cross-process coordination.

Key features:
- Atomic file locking via fcntl.flock()
- Phase dependency parsing from BUILD specs
- File conflict detection between phases
- Instance heartbeat monitoring (5-min timeout)

Usage:
    coord = ParallelBuildCoordinator(Path("BUILD_3.5.md"))
    instance_id = coord.register_instance()

    # Claim an available phase
    if coord.claim_phase(instance_id, "1"):
        # Do work...
        coord.update_heartbeat(instance_id)
        coord.mark_completed(instance_id)
"""

import fcntl
import json
import re
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Set


class InstanceStatus(str, Enum):
    """Status of a parallel build instance."""

    RUNNING = "running"
    COMPLETED = "completed"
    ABANDONED = "abandoned"


@dataclass
class Instance:
    """A Claude instance participating in parallel build."""

    id: str
    status: InstanceStatus
    phase: Optional[str] = None
    tasks: List[str] = field(default_factory=list)
    files_locked: List[str] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.now)
    last_heartbeat: datetime = field(default_factory=datetime.now)
    progress: float = 0.0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization."""
        return {
            "id": self.id,
            "status": self.status.value,
            "phase": self.phase,
            "tasks": self.tasks,
            "files_locked": self.files_locked,
            "started_at": self.started_at.isoformat(),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "progress": self.progress,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "Instance":
        """Create from dictionary."""
        return cls(
            id=data["id"],
            status=InstanceStatus(data["status"]),
            phase=data.get("phase"),
            tasks=data.get("tasks", []),
            files_locked=data.get("files_locked", []),
            started_at=datetime.fromisoformat(data["started_at"]),
            last_heartbeat=datetime.fromisoformat(data["last_heartbeat"]),
            progress=data.get("progress", 0.0),
        )


@dataclass
class PhaseAnalysis:
    """Analysis of BUILD spec phases."""

    phases: List[str] = field(default_factory=list)
    dependencies: Dict[str, List[str]] = field(default_factory=dict)
    parallel_safe: List[List[str]] = field(default_factory=list)
    max_parallel: int = 1
    file_conflicts: Dict[str, List[str]] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "phases": self.phases,
            "dependencies": self.dependencies,
            "parallel_safe": self.parallel_safe,
            "max_parallel": self.max_parallel,
            "file_conflicts": self.file_conflicts,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PhaseAnalysis":
        """Create from dictionary."""
        return cls(
            phases=data.get("phases", []),
            dependencies=data.get("dependencies", {}),
            parallel_safe=data.get("parallel_safe", []),
            max_parallel=data.get("max_parallel", 1),
            file_conflicts=data.get("file_conflicts", {}),
        )


class ParallelBuildCoordinator:
    """
    Coordinates multiple Claude instances working on same BUILD spec.

    Uses file-based locking to ensure atomic state updates across processes.
    First instance to register becomes the coordinator.
    """

    # Heartbeat timeout in seconds (5 minutes)
    HEARTBEAT_TIMEOUT = 300

    # State file version
    STATE_VERSION = "1.0"

    def __init__(
        self,
        build_spec_path: Path,
        state_file: Optional[Path] = None,
    ):
        """
        Initialize coordinator.

        Args:
            build_spec_path: Path to BUILD_*.md spec file
            state_file: Optional path to state file (default: .buildrunner/parallel_state.json)
        """
        self.build_spec_path = Path(build_spec_path)
        self.state_file = state_file or Path(".buildrunner/parallel_state.json")

        # Ensure state file directory exists
        self.state_file.parent.mkdir(parents=True, exist_ok=True)

    # =========================================================================
    # FEAT-PARA-001: Instance Lifecycle & Atomic State Management
    # =========================================================================

    def _atomic_update(self, update_fn: Callable[[Dict], Dict]) -> Dict:
        """
        Perform atomic read-modify-write on state file.

        Uses fcntl.flock() for cross-process locking.

        Args:
            update_fn: Function that takes current state and returns modified state

        Returns:
            Updated state dictionary
        """
        # Create file if it doesn't exist
        if not self.state_file.exists():
            self._initialize_state()

        # Open for read+write
        with open(self.state_file, "r+") as f:
            # Acquire exclusive lock (blocking)
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                # Read current state
                f.seek(0)
                state = json.load(f)

                # Apply update function
                state = update_fn(state)

                # Write updated state
                f.seek(0)
                f.truncate()
                json.dump(state, f, indent=2)
                f.flush()

                return state
            finally:
                # Always release lock
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _initialize_state(self) -> None:
        """Initialize empty state file."""
        initial_state = {
            "version": self.STATE_VERSION,
            "build_spec": str(self.build_spec_path),
            "started_at": datetime.now().isoformat(),
            "coordinator_id": None,
            "instances": {},
            "phase_analysis": PhaseAnalysis().to_dict(),
            "completed_phases": [],
            "sync_points": [],
        }

        with open(self.state_file, "w") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            try:
                json.dump(initial_state, f, indent=2)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def _load_state(self) -> Dict:
        """Load state from file with locking."""
        if not self.state_file.exists():
            self._initialize_state()

        with open(self.state_file, "r") as f:
            fcntl.flock(f.fileno(), fcntl.LOCK_SH)  # Shared lock for read
            try:
                return json.load(f)
            finally:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)

    def register_instance(self) -> str:
        """
        Register a new instance.

        First instance becomes coordinator.

        Returns:
            Instance UUID
        """
        instance_id = str(uuid.uuid4())
        now = datetime.now()

        def update(state: Dict) -> Dict:
            instance = Instance(
                id=instance_id,
                status=InstanceStatus.RUNNING,
                started_at=now,
                last_heartbeat=now,
            )
            state["instances"][instance_id] = instance.to_dict()

            # First instance becomes coordinator
            if state["coordinator_id"] is None:
                state["coordinator_id"] = instance_id

            return state

        self._atomic_update(update)
        return instance_id

    def update_heartbeat(self, instance_id: str) -> bool:
        """
        Update instance heartbeat timestamp.

        Args:
            instance_id: Instance UUID

        Returns:
            True if updated, False if instance not found
        """
        now = datetime.now().isoformat()

        def update(state: Dict) -> Dict:
            if instance_id in state["instances"]:
                state["instances"][instance_id]["last_heartbeat"] = now
            return state

        state = self._atomic_update(update)
        return instance_id in state["instances"]

    def update_progress(self, instance_id: str, progress: float) -> bool:
        """
        Update instance progress.

        Args:
            instance_id: Instance UUID
            progress: Progress value (0.0 to 1.0)

        Returns:
            True if updated, False if instance not found
        """

        def update(state: Dict) -> Dict:
            if instance_id in state["instances"]:
                state["instances"][instance_id]["progress"] = progress
                state["instances"][instance_id]["last_heartbeat"] = datetime.now().isoformat()
            return state

        state = self._atomic_update(update)
        return instance_id in state["instances"]

    def mark_completed(self, instance_id: str) -> bool:
        """
        Mark instance as completed.

        Moves claimed phase to completed_phases.

        Args:
            instance_id: Instance UUID

        Returns:
            True if marked, False if instance not found
        """

        def update(state: Dict) -> Dict:
            if instance_id not in state["instances"]:
                return state

            instance = state["instances"][instance_id]
            instance["status"] = InstanceStatus.COMPLETED.value
            instance["progress"] = 1.0

            # Move phase to completed
            phase = instance.get("phase")
            if phase and phase not in state["completed_phases"]:
                state["completed_phases"].append(phase)

            # Clear locks
            instance["files_locked"] = []

            return state

        state = self._atomic_update(update)
        return instance_id in state["instances"]

    def release_instance(self, instance_id: str) -> bool:
        """
        Release instance and its claims.

        Args:
            instance_id: Instance UUID

        Returns:
            True if released, False if not found
        """

        def update(state: Dict) -> Dict:
            if instance_id in state["instances"]:
                del state["instances"][instance_id]

                # If this was coordinator, pick new one
                if state["coordinator_id"] == instance_id:
                    running = [
                        iid
                        for iid, inst in state["instances"].items()
                        if inst["status"] == InstanceStatus.RUNNING.value
                    ]
                    state["coordinator_id"] = running[0] if running else None

            return state

        state = self._atomic_update(update)
        return True

    def get_instance(self, instance_id: str) -> Optional[Instance]:
        """Get instance by ID."""
        state = self._load_state()
        if instance_id in state["instances"]:
            return Instance.from_dict(state["instances"][instance_id])
        return None

    def get_all_instances(self) -> List[Instance]:
        """Get all registered instances."""
        state = self._load_state()
        return [Instance.from_dict(data) for data in state["instances"].values()]

    def is_coordinator(self, instance_id: str) -> bool:
        """Check if instance is the coordinator."""
        state = self._load_state()
        return state["coordinator_id"] == instance_id

    # =========================================================================
    # FEAT-PARA-002: Phase Dependency Parser
    # =========================================================================

    def parse_phase_dependencies(self) -> Dict[str, List[str]]:
        """
        Parse BUILD spec for phase dependencies.

        Looks for patterns like:
        - **Depends on:** Phase 1
        - **Dependencies:** Phase 1, Phase 2

        Returns:
            Dict mapping phase -> list of dependency phases
        """
        if not self.build_spec_path.exists():
            return {}

        content = self.build_spec_path.read_text()
        dependencies: Dict[str, List[str]] = {}

        # Pattern: ## Phase N: Name ... **Depends on:** Phase M
        # Capture phase number and any dependencies
        phase_pattern = r"## Phase (\d+):([^\n]*)\n(.*?)(?=## Phase \d+:|$)"
        dep_pattern = r"\*\*(?:Depends on|Dependencies):\*\*\s*(?:Phase\s*)?([^\n]+)"

        for match in re.finditer(phase_pattern, content, re.DOTALL):
            phase_num = match.group(1)
            phase_content = match.group(3)

            # Find dependencies in phase content
            dep_match = re.search(dep_pattern, phase_content, re.IGNORECASE)
            if dep_match:
                dep_text = dep_match.group(1)
                # Extract phase numbers from text like "Phase 1" or "1, 2"
                dep_nums = re.findall(r"(\d+)", dep_text)
                dependencies[phase_num] = dep_nums

        return dependencies

    def build_dependency_graph(self) -> PhaseAnalysis:
        """
        Build complete phase analysis from BUILD spec.

        Returns:
            PhaseAnalysis with phases, dependencies, parallel groups
        """
        if not self.build_spec_path.exists():
            return PhaseAnalysis()

        content = self.build_spec_path.read_text()

        # Extract all phases
        phase_pattern = r"## Phase (\d+):"
        phases = sorted(set(re.findall(phase_pattern, content)))

        # Get dependencies
        dependencies = self.parse_phase_dependencies()

        # Determine parallel-safe groups (phases with no interdependencies)
        parallel_safe: List[List[str]] = []
        remaining = set(phases)
        completed: Set[str] = set()

        while remaining:
            # Find phases whose deps are all completed
            ready = []
            for phase in remaining:
                deps = dependencies.get(phase, [])
                if all(d in completed for d in deps):
                    ready.append(phase)

            if not ready:
                # Circular dependency or error - just take first remaining
                ready = [sorted(remaining)[0]]

            parallel_safe.append(ready)
            completed.update(ready)
            remaining -= set(ready)

        # Max parallel is size of largest group
        max_parallel = max(len(group) for group in parallel_safe) if parallel_safe else 1

        # Get file conflicts
        file_conflicts = self.detect_file_conflicts()

        return PhaseAnalysis(
            phases=phases,
            dependencies=dependencies,
            parallel_safe=parallel_safe,
            max_parallel=max_parallel,
            file_conflicts=file_conflicts,
        )

    # =========================================================================
    # FEAT-PARA-003: File Conflict Analyzer
    # =========================================================================

    def extract_phase_files(self, phase: str) -> List[str]:
        """
        Extract file paths from a phase's tasks.

        Looks for:
        - **Component:** `path/file.py`
        - Table format: | FEAT-XXX | ... | `path/file.py` |
        - **Files:** or **Target file:**

        Args:
            phase: Phase number

        Returns:
            List of file paths
        """
        if not self.build_spec_path.exists():
            return []

        content = self.build_spec_path.read_text()

        # Find phase content
        phase_pattern = rf"## Phase {phase}:(.*?)(?=## Phase \d+:|$)"
        phase_match = re.search(phase_pattern, content, re.DOTALL)
        if not phase_match:
            return []

        phase_content = phase_match.group(1)
        files: Set[str] = set()

        # Pattern 1: **Component:** `path/file.py`
        component_pattern = r"\*\*Component:\*\*\s*`([^`]+)`"
        files.update(re.findall(component_pattern, phase_content))

        # Pattern 2: Table format | FEAT-XXX | ... | `path/file.py` |
        table_pattern = r"\|\s*FEAT-[A-Z]+-\d+[^|]*\|[^|]*\|\s*`([^`]+)`"
        files.update(re.findall(table_pattern, phase_content))

        # Pattern 3: **Files:** or **Target file:**
        files_pattern = r"\*\*(?:Files|Target file):\*\*\s*\n((?:\s*-\s*`[^`]+`\n?)+)"
        files_match = re.search(files_pattern, phase_content)
        if files_match:
            file_list = re.findall(r"`([^`]+)`", files_match.group(1))
            files.update(file_list)

        return list(files)

    def detect_file_conflicts(self) -> Dict[str, List[str]]:
        """
        Detect file conflicts between phases.

        Returns:
            Dict mapping "phase1->phase2" to list of conflicting files
        """
        if not self.build_spec_path.exists():
            return {}

        content = self.build_spec_path.read_text()

        # Get all phases
        phase_pattern = r"## Phase (\d+):"
        phases = sorted(set(re.findall(phase_pattern, content)))

        # Extract files per phase
        phase_files: Dict[str, Set[str]] = {}
        for phase in phases:
            phase_files[phase] = set(self.extract_phase_files(phase))

        # Find conflicts between phases
        conflicts: Dict[str, List[str]] = {}
        for i, p1 in enumerate(phases):
            for p2 in phases[i + 1 :]:
                overlap = phase_files[p1] & phase_files[p2]
                if overlap:
                    conflicts[f"{p1}->{p2}"] = list(overlap)

        return conflicts

    # =========================================================================
    # FEAT-PARA-004: Phase Claiming
    # =========================================================================

    def claim_phase(self, instance_id: str, phase: str) -> bool:
        """
        Attempt to claim a phase for an instance.

        Checks:
        1. Phase dependencies satisfied (prereqs completed)
        2. No file conflicts with running instances
        3. Phase not already claimed

        Args:
            instance_id: Instance UUID
            phase: Phase number to claim

        Returns:
            True if claimed successfully, False otherwise
        """
        # Get phase analysis
        analysis = self.build_dependency_graph()
        phase_files = self.extract_phase_files(phase)

        def update(state: Dict) -> Dict:
            if instance_id not in state["instances"]:
                return state

            # Check 1: Phase dependencies satisfied
            deps = analysis.dependencies.get(phase, [])
            for dep in deps:
                if dep not in state["completed_phases"]:
                    return state  # Dependency not met

            # Check 2: Phase not already claimed by another running instance
            for iid, inst in state["instances"].items():
                if iid == instance_id:
                    continue
                if inst["status"] == InstanceStatus.RUNNING.value:
                    if inst.get("phase") == phase:
                        return state  # Already claimed

            # Check 3: No file conflicts with running instances
            for iid, inst in state["instances"].items():
                if iid == instance_id:
                    continue
                if inst["status"] == InstanceStatus.RUNNING.value:
                    locked = set(inst.get("files_locked", []))
                    conflicts = locked & set(phase_files)
                    if conflicts:
                        return state  # File conflict

            # All checks passed - claim the phase
            instance = state["instances"][instance_id]
            instance["phase"] = phase
            instance["files_locked"] = phase_files
            instance["last_heartbeat"] = datetime.now().isoformat()

            return state

        # Execute atomic update
        state = self._atomic_update(update)

        # Check if claim succeeded
        if instance_id in state["instances"]:
            return state["instances"][instance_id].get("phase") == phase

        return False

    def release_phase(self, instance_id: str) -> bool:
        """
        Release phase claim for an instance.

        Args:
            instance_id: Instance UUID

        Returns:
            True if released, False if not found
        """

        def update(state: Dict) -> Dict:
            if instance_id in state["instances"]:
                instance = state["instances"][instance_id]
                instance["phase"] = None
                instance["files_locked"] = []
            return state

        self._atomic_update(update)
        return True

    def get_available_phases(self) -> List[str]:
        """
        Get phases available for claiming.

        A phase is available if:
        1. All dependencies are in completed_phases
        2. Not currently claimed by a running instance

        Returns:
            List of available phase numbers
        """
        state = self._load_state()
        analysis = self.build_dependency_graph()

        available = []
        for phase in analysis.phases:
            # Check dependencies
            deps = analysis.dependencies.get(phase, [])
            if not all(d in state["completed_phases"] for d in deps):
                continue

            # Check if already claimed
            claimed = False
            for inst in state["instances"].values():
                if inst["status"] == InstanceStatus.RUNNING.value:
                    if inst.get("phase") == phase:
                        claimed = True
                        break

            # Check if already completed
            if phase in state["completed_phases"]:
                continue

            if not claimed:
                available.append(phase)

        return available

    def get_claimed_phases(self) -> Dict[str, str]:
        """
        Get mapping of claimed phases to instance IDs.

        Returns:
            Dict mapping phase -> instance_id
        """
        state = self._load_state()
        claimed = {}

        for iid, inst in state["instances"].items():
            if inst["status"] == InstanceStatus.RUNNING.value:
                phase = inst.get("phase")
                if phase:
                    claimed[phase] = iid

        return claimed

    # =========================================================================
    # FEAT-PARA-005: Heartbeat & Stale Detection
    # =========================================================================

    def get_stale_instances(self) -> List[str]:
        """
        Get instances with heartbeat older than timeout.

        Returns:
            List of stale instance IDs
        """
        state = self._load_state()
        cutoff = datetime.now() - timedelta(seconds=self.HEARTBEAT_TIMEOUT)
        stale = []

        for iid, inst in state["instances"].items():
            if inst["status"] != InstanceStatus.RUNNING.value:
                continue

            last_heartbeat = datetime.fromisoformat(inst["last_heartbeat"])
            if last_heartbeat < cutoff:
                stale.append(iid)

        return stale

    def cleanup_stale_instances(self) -> List[str]:
        """
        Mark stale instances as abandoned and release their claims.

        Returns:
            List of cleaned up instance IDs
        """
        stale = self.get_stale_instances()
        if not stale:
            return []

        def update(state: Dict) -> Dict:
            for iid in stale:
                if iid in state["instances"]:
                    instance = state["instances"][iid]
                    instance["status"] = InstanceStatus.ABANDONED.value
                    instance["phase"] = None
                    instance["files_locked"] = []

                    # If this was coordinator, pick new one
                    if state["coordinator_id"] == iid:
                        running = [
                            i
                            for i, inst in state["instances"].items()
                            if inst["status"] == InstanceStatus.RUNNING.value
                        ]
                        state["coordinator_id"] = running[0] if running else None

            return state

        self._atomic_update(update)
        return stale

    def get_status(self) -> Dict[str, Any]:
        """
        Get current coordination status.

        Returns:
            Dict with status summary
        """
        state = self._load_state()
        analysis = self.build_dependency_graph()

        running = [
            i for i in state["instances"].values() if i["status"] == InstanceStatus.RUNNING.value
        ]
        completed = [
            i for i in state["instances"].values() if i["status"] == InstanceStatus.COMPLETED.value
        ]

        return {
            "build_spec": state["build_spec"],
            "coordinator_id": state["coordinator_id"],
            "instances": {
                "total": len(state["instances"]),
                "running": len(running),
                "completed": len(completed),
            },
            "phases": {
                "total": len(analysis.phases),
                "completed": len(state["completed_phases"]),
                "available": len(self.get_available_phases()),
                "claimed": len(self.get_claimed_phases()),
            },
            "completed_phases": state["completed_phases"],
            "stale_instances": self.get_stale_instances(),
        }
