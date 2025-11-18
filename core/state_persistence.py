"""
State Persistence for Task Orchestration

Saves and loads task execution state to/from disk, enabling recovery
from interruptions and tracking progress over time.
"""

import json
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime
from dataclasses import asdict


class StatePersistence:
    """
    Persists task orchestration state to disk.

    Responsibilities:
    - Save execution state
    - Load previous state
    - Enable recovery from interruptions
    - Track execution history
    """

    STATE_DIR = Path(".buildrunner/state")
    DEFAULT_STATE_FILE = "orchestration_state.json"

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.state_dir = self.project_root / self.STATE_DIR

        # Ensure state directory exists
        self._ensure_state_dir()

    def _ensure_state_dir(self):
        """Ensure state directory exists"""
        self.state_dir.mkdir(parents=True, exist_ok=True)

    def save_state(
        self,
        tasks: Dict,
        execution_order: List[str],
        progress: Dict,
        filename: str = DEFAULT_STATE_FILE,
        metadata: Optional[Dict] = None,
    ) -> bool:
        """
        Save orchestration state to disk.

        Args:
            tasks: Dictionary of task_id -> task data
            execution_order: Ordered list of task IDs
            progress: Progress statistics
            filename: State file name
            metadata: Optional metadata to save

        Returns:
            True if saved successfully
        """
        filepath = self.state_dir / filename

        # Serialize tasks (handle dataclasses)
        serialized_tasks = {}
        for task_id, task in tasks.items():
            if hasattr(task, '__dataclass_fields__'):
                task_data = asdict(task)
                # Convert datetime objects to ISO format
                for key, value in task_data.items():
                    if isinstance(value, datetime):
                        task_data[key] = value.isoformat()
                    elif hasattr(value, 'value'):  # Enum
                        task_data[key] = value.value
                serialized_tasks[task_id] = task_data
            else:
                serialized_tasks[task_id] = task

        state = {
            "version": "1.0",
            "timestamp": datetime.now().isoformat(),
            "tasks": serialized_tasks,
            "execution_order": execution_order,
            "progress": progress,
            "metadata": metadata or {},
        }

        try:
            with open(filepath, "w") as f:
                json.dump(state, f, indent=2)
            return True
        except Exception as e:
            print(f"Error saving state: {e}")
            return False

    def load_state(
        self,
        filename: str = DEFAULT_STATE_FILE,
    ) -> Optional[Dict]:
        """
        Load orchestration state from disk.

        Args:
            filename: State file name

        Returns:
            State dictionary or None if not found
        """
        filepath = self.state_dir / filename

        if not filepath.exists():
            return None

        try:
            with open(filepath, "r") as f:
                state = json.load(f)
            return state
        except Exception as e:
            print(f"Error loading state: {e}")
            return None

    def delete_state(self, filename: str = DEFAULT_STATE_FILE) -> bool:
        """
        Delete state file.

        Args:
            filename: State file name

        Returns:
            True if deleted successfully
        """
        filepath = self.state_dir / filename

        if not filepath.exists():
            return False

        try:
            filepath.unlink()
            return True
        except Exception as e:
            print(f"Error deleting state: {e}")
            return False

    def list_state_files(self) -> List[str]:
        """
        List all state files.

        Returns:
            List of state file names
        """
        if not self.state_dir.exists():
            return []

        return [f.name for f in self.state_dir.glob("*.json")]

    def save_checkpoint(
        self,
        tasks: Dict,
        execution_order: List[str],
        progress: Dict,
        checkpoint_name: str,
    ) -> bool:
        """
        Save a named checkpoint.

        Args:
            tasks: Task dictionary
            execution_order: Execution order
            progress: Progress stats
            checkpoint_name: Checkpoint identifier

        Returns:
            True if saved successfully
        """
        filename = f"checkpoint_{checkpoint_name}.json"
        return self.save_state(
            tasks=tasks,
            execution_order=execution_order,
            progress=progress,
            filename=filename,
            metadata={"checkpoint": checkpoint_name},
        )

    def load_checkpoint(self, checkpoint_name: str) -> Optional[Dict]:
        """
        Load a named checkpoint.

        Args:
            checkpoint_name: Checkpoint identifier

        Returns:
            State dictionary or None
        """
        filename = f"checkpoint_{checkpoint_name}.json"
        return self.load_state(filename)

    def get_latest_state(self) -> Optional[Dict]:
        """
        Get the most recently saved state.

        Returns:
            Latest state dictionary or None
        """
        state_files = self.list_state_files()
        if not state_files:
            return None

        # Sort by modification time
        state_paths = [self.state_dir / f for f in state_files]
        latest = max(state_paths, key=lambda p: p.stat().st_mtime)

        return self.load_state(latest.name)

    def clear_all_state(self) -> int:
        """
        Clear all state files.

        Returns:
            Number of files deleted
        """
        deleted = 0
        for filename in self.list_state_files():
            if self.delete_state(filename):
                deleted += 1
        return deleted

    def get_stats(self) -> Dict:
        """Get persistence statistics"""
        state_files = self.list_state_files()
        total_size = sum(
            (self.state_dir / f).stat().st_size
            for f in state_files
        )

        return {
            "state_dir": str(self.state_dir),
            "state_files_count": len(state_files),
            "total_size_bytes": total_size,
        }
