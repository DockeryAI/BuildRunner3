"""
Session Manager - Manages multiple concurrent build sessions

Features:
- Multi-session coordination
- Session state management
- Conflict detection and resolution
- Session synchronization
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import json
import uuid


class SessionStatus(str, Enum):
    """Session status."""

    CREATED = "created"
    RUNNING = "running"
    PAUSED = "paused"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


@dataclass
class Session:
    """Build session."""

    session_id: str
    name: str
    status: SessionStatus
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None

    # Tasks
    total_tasks: int = 0
    completed_tasks: int = 0
    failed_tasks: int = 0
    in_progress_tasks: int = 0

    # Files
    files_locked: Set[str] = field(default_factory=set)
    files_modified: Set[str] = field(default_factory=set)

    # Worker
    worker_id: Optional[str] = None

    # Progress
    progress_percent: float = 0.0

    # Metadata
    metadata: Dict[str, any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, any]:
        """Convert to dictionary."""
        return {
            "session_id": self.session_id,
            "name": self.name,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "started_at": self.started_at.isoformat() if self.started_at else None,
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_tasks": self.total_tasks,
            "completed_tasks": self.completed_tasks,
            "failed_tasks": self.failed_tasks,
            "in_progress_tasks": self.in_progress_tasks,
            "files_locked": list(self.files_locked),
            "files_modified": list(self.files_modified),
            "worker_id": self.worker_id,
            "progress_percent": self.progress_percent,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls, data: Dict[str, any]) -> "Session":
        """Create from dictionary."""
        return cls(
            session_id=data["session_id"],
            name=data["name"],
            status=SessionStatus(data["status"]),
            created_at=datetime.fromisoformat(data["created_at"]),
            started_at=(
                datetime.fromisoformat(data["started_at"]) if data.get("started_at") else None
            ),
            completed_at=(
                datetime.fromisoformat(data["completed_at"]) if data.get("completed_at") else None
            ),
            total_tasks=data.get("total_tasks", 0),
            completed_tasks=data.get("completed_tasks", 0),
            failed_tasks=data.get("failed_tasks", 0),
            in_progress_tasks=data.get("in_progress_tasks", 0),
            files_locked=set(data.get("files_locked", [])),
            files_modified=set(data.get("files_modified", [])),
            worker_id=data.get("worker_id"),
            progress_percent=data.get("progress_percent", 0.0),
            metadata=data.get("metadata", {}),
        )


class SessionManager:
    """Manages multiple concurrent build sessions."""

    def __init__(self, storage_path: Optional[Path] = None, max_concurrent_sessions: int = 4):
        """
        Initialize session manager.

        Args:
            storage_path: Path to store session data
            max_concurrent_sessions: Maximum number of concurrent sessions
        """
        self.storage_path = storage_path or Path.cwd() / ".buildrunner" / "sessions.json"
        self.max_concurrent_sessions = max_concurrent_sessions
        self.sessions: Dict[str, Session] = {}
        self._load()

    def create_session(
        self,
        name: str,
        total_tasks: int = 0,
        metadata: Optional[Dict[str, any]] = None,
    ) -> Session:
        """
        Create a new session.

        Args:
            name: Session name
            total_tasks: Total number of tasks
            metadata: Additional metadata

        Returns:
            Created Session
        """
        session = Session(
            session_id=str(uuid.uuid4()),
            name=name,
            status=SessionStatus.CREATED,
            created_at=datetime.now(),
            total_tasks=total_tasks,
            metadata=metadata or {},
        )

        self.sessions[session.session_id] = session
        self._save()

        return session

    def get_session(self, session_id: str) -> Optional[Session]:
        """
        Get session by ID.

        Args:
            session_id: Session ID

        Returns:
            Session or None
        """
        return self.sessions.get(session_id)

    def list_sessions(
        self,
        status: Optional[SessionStatus] = None,
    ) -> List[Session]:
        """
        List sessions.

        Args:
            status: Filter by status

        Returns:
            List of sessions
        """
        sessions = list(self.sessions.values())

        if status:
            sessions = [s for s in sessions if s.status == status]

        # Sort by created date (newest first)
        sessions.sort(key=lambda s: s.created_at, reverse=True)

        return sessions

    def start_session(self, session_id: str, worker_id: Optional[str] = None):
        """
        Start a session.

        Args:
            session_id: Session ID
            worker_id: Worker ID assigned to session
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.status = SessionStatus.RUNNING
        session.started_at = datetime.now()
        session.worker_id = worker_id

        self._save()

    def pause_session(self, session_id: str):
        """Pause a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.status = SessionStatus.PAUSED
        self._save()

    def complete_session(self, session_id: str):
        """Complete a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.status = SessionStatus.COMPLETED
        session.completed_at = datetime.now()
        session.progress_percent = 100.0

        self._save()

    def fail_session(self, session_id: str):
        """Mark session as failed."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.status = SessionStatus.FAILED
        session.completed_at = datetime.now()

        self._save()

    def cancel_session(self, session_id: str):
        """Cancel a session."""
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.status = SessionStatus.CANCELLED
        session.completed_at = datetime.now()

        self._save()

    def update_progress(
        self,
        session_id: str,
        completed_tasks: int,
        failed_tasks: int = 0,
        in_progress_tasks: int = 0,
    ):
        """
        Update session progress.

        Args:
            session_id: Session ID
            completed_tasks: Number of completed tasks
            failed_tasks: Number of failed tasks
            in_progress_tasks: Number of in-progress tasks
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.completed_tasks = completed_tasks
        session.failed_tasks = failed_tasks
        session.in_progress_tasks = in_progress_tasks

        if session.total_tasks > 0:
            session.progress_percent = (completed_tasks / session.total_tasks) * 100

        self._save()

    def lock_files(self, session_id: str, files: List[str]):
        """
        Lock files for a session.

        Args:
            session_id: Session ID
            files: List of file paths to lock

        Raises:
            ValueError: If files are already locked by another session
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        # Check for conflicts
        for other_session in self.sessions.values():
            if other_session.session_id == session_id:
                continue

            if other_session.status not in [SessionStatus.RUNNING, SessionStatus.PAUSED]:
                continue

            conflicts = set(files) & other_session.files_locked
            if conflicts:
                raise ValueError(
                    f"Files already locked by session {other_session.session_id}: "
                    f"{', '.join(conflicts)}"
                )

        # Lock files
        session.files_locked.update(files)
        self._save()

    def unlock_files(self, session_id: str, files: Optional[List[str]] = None):
        """
        Unlock files for a session.

        Args:
            session_id: Session ID
            files: List of files to unlock (None = unlock all)
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        if files is None:
            session.files_locked.clear()
        else:
            session.files_locked -= set(files)

        self._save()

    def mark_files_modified(self, session_id: str, files: List[str]):
        """
        Mark files as modified by a session.

        Args:
            session_id: Session ID
            files: List of modified file paths
        """
        session = self.get_session(session_id)
        if not session:
            raise ValueError(f"Session not found: {session_id}")

        session.files_modified.update(files)
        self._save()

    def get_active_sessions(self) -> List[Session]:
        """Get all active (running or paused) sessions."""
        return [
            s
            for s in self.sessions.values()
            if s.status in [SessionStatus.RUNNING, SessionStatus.PAUSED]
        ]

    def get_all_sessions(self) -> List[Session]:
        """Get all sessions."""
        return list(self.sessions.values())

    def get_sessions_by_status(self, status: str) -> List[Session]:
        """
        Get sessions filtered by status.

        Args:
            status: Session status to filter by

        Returns:
            List of matching sessions
        """
        try:
            status_enum = SessionStatus(status)
            return [s for s in self.sessions.values() if s.status == status_enum]
        except ValueError:
            return []

    def get_stats(self) -> Dict[str, int]:
        """
        Get session statistics.

        Returns:
            Dictionary with session counts
        """
        total = len(self.sessions)
        active = len([s for s in self.sessions.values() if s.status == SessionStatus.RUNNING])
        paused = len([s for s in self.sessions.values() if s.status == SessionStatus.PAUSED])
        completed = len([s for s in self.sessions.values() if s.status == SessionStatus.COMPLETED])
        failed = len([s for s in self.sessions.values() if s.status == SessionStatus.FAILED])

        return {
            "total_sessions": total,
            "active_sessions": active,
            "paused_sessions": paused,
            "completed_sessions": completed,
            "failed_sessions": failed,
        }

    def cleanup_old_sessions(self, days: int = 7):
        """
        Clean up old completed/failed sessions.

        Args:
            days: Delete sessions older than this many days
        """
        from datetime import timedelta

        cutoff = datetime.now() - timedelta(days=days)

        to_delete = []
        for session_id, session in self.sessions.items():
            if session.status in [
                SessionStatus.COMPLETED,
                SessionStatus.FAILED,
                SessionStatus.CANCELLED,
            ]:
                if session.completed_at and session.completed_at < cutoff:
                    to_delete.append(session_id)

        for session_id in to_delete:
            del self.sessions[session_id]

        if to_delete:
            self._save()

    def _save(self):
        """Save sessions to disk."""
        try:
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)

            data = {
                "sessions": [s.to_dict() for s in self.sessions.values()],
                "version": "1.0",
            }

            with open(self.storage_path, "w") as f:
                json.dump(data, f, indent=2)

        except Exception as e:
            print(f"Warning: Failed to save sessions: {e}")

    def _load(self):
        """Load sessions from disk."""
        if not self.storage_path.exists():
            return

        try:
            with open(self.storage_path, "r") as f:
                data = json.load(f)

            for session_data in data.get("sessions", []):
                session = Session.from_dict(session_data)
                self.sessions[session.session_id] = session

        except Exception as e:
            print(f"Warning: Failed to load sessions: {e}")
            self.sessions = {}
