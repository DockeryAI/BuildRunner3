"""
Checkpoint Manager - Save and restore build state for rollback capability

Provides:
- Checkpoint creation after successful build phases
- State persistence to .buildrunner/checkpoints/
- Rollback to previous checkpoints
- Resume from last good state
"""

import json
from pathlib import Path
from typing import Dict, List, Optional, Any
from datetime import datetime
from dataclasses import dataclass, asdict
from enum import Enum


class CheckpointStatus(Enum):
    """Checkpoint status"""
    CREATED = "created"
    ACTIVE = "active"
    ROLLED_BACK = "rolled_back"


@dataclass
class Checkpoint:
    """Represents a build state checkpoint"""
    id: str
    timestamp: str
    phase: str
    tasks_completed: List[str]
    files_created: List[str]
    status: CheckpointStatus
    metadata: Dict[str, Any]

    def to_dict(self) -> Dict:
        """Convert to dictionary"""
        data = asdict(self)
        data['status'] = self.status.value
        return data

    @classmethod
    def from_dict(cls, data: Dict) -> 'Checkpoint':
        """Create from dictionary"""
        data['status'] = CheckpointStatus(data['status'])
        return cls(**data)


class CheckpointManager:
    """
    Manage build checkpoints for rollback and resume.

    Features:
    - Create checkpoints after each build phase
    - Save complete build state
    - Rollback to previous checkpoint
    - Resume from last checkpoint
    - List all checkpoints
    """

    def __init__(self, project_root: Path):
        """
        Initialize CheckpointManager.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root)
        self.checkpoint_dir = self.project_root / ".buildrunner" / "checkpoints"
        self.checkpoint_dir.mkdir(parents=True, exist_ok=True)
        self.checkpoints: List[Checkpoint] = []
        self._load_checkpoints()

    def create_checkpoint(
        self,
        phase: str,
        tasks_completed: List[str],
        files_created: List[str],
        metadata: Optional[Dict[str, Any]] = None
    ) -> Checkpoint:
        """
        Create a new checkpoint.

        Args:
            phase: Build phase name (e.g., "batch_1", "feature_auth")
            tasks_completed: List of completed task IDs
            files_created: List of created file paths
            metadata: Optional additional metadata

        Returns:
            Created checkpoint
        """
        checkpoint_id = f"checkpoint_{datetime.now().strftime('%Y%m%d_%H%M%S_%f')}"

        checkpoint = Checkpoint(
            id=checkpoint_id,
            timestamp=datetime.now().isoformat(),
            phase=phase,
            tasks_completed=tasks_completed.copy(),
            files_created=files_created.copy(),
            status=CheckpointStatus.CREATED,
            metadata=metadata or {}
        )

        # Save checkpoint to disk
        self._save_checkpoint(checkpoint)
        self.checkpoints.append(checkpoint)

        return checkpoint

    def get_checkpoint(self, checkpoint_id: str) -> Optional[Checkpoint]:
        """
        Get checkpoint by ID.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            Checkpoint or None if not found
        """
        for checkpoint in self.checkpoints:
            if checkpoint.id == checkpoint_id:
                return checkpoint
        return None

    def get_latest_checkpoint(self) -> Optional[Checkpoint]:
        """
        Get most recent checkpoint.

        Returns:
            Latest checkpoint or None
        """
        if not self.checkpoints:
            return None
        return self.checkpoints[-1]

    def list_checkpoints(self) -> List[Checkpoint]:
        """
        List all checkpoints.

        Returns:
            List of checkpoints ordered by creation time
        """
        return self.checkpoints.copy()

    def rollback(self, checkpoint_id: str) -> bool:
        """
        Rollback to a specific checkpoint.

        Args:
            checkpoint_id: Checkpoint ID to rollback to

        Returns:
            True if rollback successful

        Note:
            This marks the checkpoint but doesn't actually delete files.
            File deletion should be done by the caller based on checkpoint data.
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return False

        # Mark checkpoint as active
        checkpoint.status = CheckpointStatus.ACTIVE
        self._save_checkpoint(checkpoint)

        # Mark later checkpoints as rolled back
        found = False
        for cp in self.checkpoints:
            if cp.id == checkpoint_id:
                found = True
                continue
            if found:
                cp.status = CheckpointStatus.ROLLED_BACK
                self._save_checkpoint(cp)

        return True

    def delete_checkpoint(self, checkpoint_id: str) -> bool:
        """
        Delete a checkpoint.

        Args:
            checkpoint_id: Checkpoint ID

        Returns:
            True if deleted
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return False

        # Delete file
        checkpoint_file = self.checkpoint_dir / f"{checkpoint_id}.json"
        if checkpoint_file.exists():
            checkpoint_file.unlink()

        # Remove from list
        self.checkpoints = [cp for cp in self.checkpoints if cp.id != checkpoint_id]

        return True

    def _save_checkpoint(self, checkpoint: Checkpoint) -> None:
        """Save checkpoint to disk"""
        checkpoint_file = self.checkpoint_dir / f"{checkpoint.id}.json"

        with open(checkpoint_file, 'w') as f:
            json.dump(checkpoint.to_dict(), f, indent=2)

    def _load_checkpoints(self) -> None:
        """Load all checkpoints from disk"""
        self.checkpoints = []

        if not self.checkpoint_dir.exists():
            return

        for checkpoint_file in sorted(self.checkpoint_dir.glob("checkpoint_*.json")):
            try:
                with open(checkpoint_file, 'r') as f:
                    data = json.load(f)
                    checkpoint = Checkpoint.from_dict(data)
                    self.checkpoints.append(checkpoint)
            except Exception as e:
                # Skip corrupted checkpoints
                print(f"Warning: Failed to load checkpoint {checkpoint_file}: {e}")
                continue

    def get_files_to_rollback(self, checkpoint_id: str) -> List[str]:
        """
        Get list of files created after a checkpoint.

        Args:
            checkpoint_id: Checkpoint to rollback to

        Returns:
            List of file paths that should be deleted
        """
        checkpoint = self.get_checkpoint(checkpoint_id)
        if not checkpoint:
            return []

        files_to_delete = []
        found = False

        for cp in self.checkpoints:
            if cp.id == checkpoint_id:
                found = True
                continue
            if found:
                files_to_delete.extend(cp.files_created)

        return files_to_delete

    def get_resume_state(self) -> Optional[Dict[str, Any]]:
        """
        Get state to resume from latest checkpoint.

        Returns:
            Resume state dict or None
        """
        latest = self.get_latest_checkpoint()
        if not latest:
            return None

        return {
            "checkpoint_id": latest.id,
            "phase": latest.phase,
            "tasks_completed": latest.tasks_completed,
            "files_created": latest.files_created,
            "timestamp": latest.timestamp,
            "metadata": latest.metadata
        }
