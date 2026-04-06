"""
Parallel Orchestration System for BuildRunner 3.1

This module provides parallel task execution:
- Session management for multi-session coordination
- Worker coordination for task distribution
- Live dashboard for real-time monitoring
- Synchronization and conflict resolution
"""

from .session_manager import SessionManager, Session, SessionStatus
from .worker_coordinator import WorkerCoordinator, Worker, WorkerStatus
from .live_dashboard import LiveDashboard, DashboardConfig

__all__ = [
    "SessionManager",
    "Session",
    "SessionStatus",
    "WorkerCoordinator",
    "Worker",
    "WorkerStatus",
    "LiveDashboard",
    "DashboardConfig",
]
