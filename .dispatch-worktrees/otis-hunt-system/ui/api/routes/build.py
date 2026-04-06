"""
Build Management API Routes

FastAPI routes for project initialization and build session management.
Integrates project_initializer and session_manager for full build lifecycle.

This module provides 11 endpoints for:
- Project initialization with PRD data
- Build session lifecycle management (start, pause, resume, cancel)
- Session monitoring and statistics
- Cleanup and maintenance
"""

import sys
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, HTTPException, status, Query
from pydantic import BaseModel, Field

# Add parent directory to path to import from core
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from core.build.project_initializer import project_initializer, ProjectInitError
from core.build.session_manager import session_manager, SessionStatus, BuildSessionError

# Configure logging
logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api/build", tags=["build"])


# ============================================================================
# Request/Response Models
# ============================================================================


class ProjectInitRequest(BaseModel):
    """Request model for project initialization"""

    alias: str = Field(
        ...,
        min_length=1,
        max_length=50,
        pattern=r"^[a-zA-Z0-9-_]+$",
        description="Short name for the project (alphanumeric, dash, underscore)",
    )
    project_path: str = Field(
        ..., min_length=1, description="Absolute path where project should be created"
    )
    prd_data: Optional[Dict[str, Any]] = Field(
        None, description="PRD data to generate PROJECT_SPEC.md"
    )

    class Config:
        json_schema_extra = {
            "example": {
                "alias": "myapp",
                "project_path": "/Users/username/projects/myapp",
                "prd_data": {
                    "name": "My Application",
                    "description": "A web application for managing tasks",
                    "features": [
                        {
                            "name": "User Authentication",
                            "description": "Login and registration with JWT",
                        },
                        {
                            "name": "Task Management",
                            "description": "Create, edit, and delete tasks",
                        },
                    ],
                    "tech_stack": ["Python", "FastAPI", "React", "PostgreSQL"],
                },
            }
        }


class ProjectInitResponse(BaseModel):
    """Response model for project initialization"""

    success: bool
    message: str
    project_path: str
    alias: str
    errors: Optional[List[str]] = None
    created_at: str


class BuildStartRequest(BaseModel):
    """Request model for starting a build session"""

    project_alias: str = Field(..., min_length=1, description="Project alias")
    project_path: str = Field(..., min_length=1, description="Absolute path to project directory")

    class Config:
        json_schema_extra = {
            "example": {"project_alias": "myapp", "project_path": "/Users/username/projects/myapp"}
        }


class BuildStartResponse(BaseModel):
    """Response model for starting a build session"""

    session_id: str
    status: str
    created_at: str


class SessionStatusResponse(BaseModel):
    """Response model for session status"""

    session_id: str
    project_alias: str
    project_path: str
    status: str
    created_at: str
    updated_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    current_batch: Optional[int] = None
    current_task: Optional[str] = None
    total_tasks: int
    completed_tasks: int
    failed_tasks: int
    progress_percentage: float
    execution_time: float
    estimated_time_remaining: Optional[float] = None
    components: List[Dict[str, Any]] = []
    features: List[Dict[str, Any]] = []
    batches_completed: List[int]
    tasks_completed: List[str]
    errors: List[Dict[str, Any]]
    metadata: Dict[str, Any]


class BuildActionRequest(BaseModel):
    """Request model for build actions (pause/resume/cancel)"""

    session_id: str = Field(..., min_length=1, description="Session identifier")


class BuildActionResponse(BaseModel):
    """Response model for build actions"""

    success: bool
    message: str
    session_id: str
    status: str


class SessionStatsResponse(BaseModel):
    """Response model for session statistics"""

    total_sessions: int
    active: int
    completed: int
    failed: int
    by_status: Dict[str, int]


class CleanupResponse(BaseModel):
    """Response model for cleanup operations"""

    deleted_count: int


# ============================================================================
# Endpoints
# ============================================================================


@router.post(
    "/init",
    response_model=ProjectInitResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Initialize a new project",
    description="""
    Initialize a new BuildRunner project with directory structure,
    PROJECT_SPEC.md generation from PRD data, and alias registration.

    Creates:
    - Project directory structure (.buildrunner/, core/, tests/, docs/)
    - PROJECT_SPEC.md from PRD data (if provided)
    - README.md and .gitignore
    - Registers project alias for easy access
    """,
)
async def initialize_project(request: ProjectInitRequest):
    """
    Initialize a new BuildRunner project.

    Creates directory structure, installs BuildRunner via pipx,
    generates PROJECT_SPEC.md from PRD data, and registers project alias.

    Args:
        request: Project initialization parameters

    Returns:
        Project initialization result with paths and status

    Raises:
        HTTPException 400: If initialization fails due to invalid input
        HTTPException 500: If initialization fails due to internal error
    """
    try:
        logger.info(f"Initializing project: {request.alias} at {request.project_path}")

        result = project_initializer.create_project_structure(
            alias=request.alias, path=request.project_path, prd_data=request.prd_data
        )

        logger.info(f"Project initialized successfully: {request.alias}")
        return ProjectInitResponse(**result)

    except ProjectInitError as e:
        logger.error(f"Project initialization failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error during project initialization: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Project initialization failed: {str(e)}",
        )


@router.post(
    "/start",
    response_model=BuildStartResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Start a build session",
    description="""
    Create and start a new build session for a project.

    The session tracks build progress, current tasks, components,
    and features throughout the build lifecycle.

    File watcher is automatically started to monitor build artifacts.
    """,
)
async def start_build_session(request: BuildStartRequest):
    """
    Start a new build session.

    Creates a new build session for the specified project.
    The session tracks build progress and state.

    Args:
        request: Build start parameters

    Returns:
        Build session details including session_id and status

    Raises:
        HTTPException 400: If session creation fails or path is invalid
        HTTPException 500: If session creation fails due to internal error
    """
    try:
        logger.info(f"Starting build session for: {request.project_alias}")

        session = session_manager.create_session(
            project_alias=request.project_alias, project_path=request.project_path
        )

        # Set status to initializing
        session.status = SessionStatus.INITIALIZING
        session.started_at = datetime.now()
        session.updated_at = datetime.now()

        logger.info(f"Build session started: {session.session_id}")

        return BuildStartResponse(
            session_id=session.session_id,
            status=session.status.value,
            created_at=session.created_at.isoformat(),
        )

    except BuildSessionError as e:
        logger.error(f"Build session creation failed: {str(e)}")
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except Exception as e:
        logger.error(f"Unexpected error starting build session: {str(e)}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to start build session: {str(e)}",
        )


@router.get(
    "/status/{session_id}",
    response_model=SessionStatusResponse,
    summary="Get build session status",
    description="""
    Retrieve current status and progress information for a build session.

    Returns detailed information including:
    - Current status and progress percentage
    - Task completion statistics
    - Component and feature status
    - Execution time and estimates
    - Any errors encountered
    """,
)
async def get_build_status(session_id: str):
    """
    Get build session status.

    Retrieves current status and progress information for a build session.

    Args:
        session_id: Session identifier

    Returns:
        Session status and progress details

    Raises:
        HTTPException 404: If session not found
    """
    session = session_manager.get_session(session_id)

    if not session:
        logger.warning(f"Session not found: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}"
        )

    return SessionStatusResponse(**session.to_dict())


@router.post(
    "/pause",
    response_model=BuildActionResponse,
    summary="Pause a build session",
    description="""
    Pause a running build session, allowing it to be resumed later.

    Only sessions in RUNNING status can be paused.
    """,
)
async def pause_build(request: BuildActionRequest):
    """
    Pause a running build session.

    Pauses the specified build session, allowing it to be resumed later.

    Args:
        request: Build action parameters

    Returns:
        Action result with updated status

    Raises:
        HTTPException 404: If session not found
        HTTPException 400: If session cannot be paused
    """
    success = session_manager.pause_session(request.session_id)

    if not success:
        session = session_manager.get_session(request.session_id)
        if not session:
            logger.warning(f"Session not found for pause: {request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {request.session_id}",
            )
        else:
            logger.warning(f"Cannot pause session in {session.status.value} state")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot pause session in {session.status.value} state",
            )

    session = session_manager.get_session(request.session_id)
    logger.info(f"Build session paused: {request.session_id}")

    return BuildActionResponse(
        success=True,
        message="Build session paused successfully",
        session_id=request.session_id,
        status=session.status.value,
    )


@router.post(
    "/resume",
    response_model=BuildActionResponse,
    summary="Resume a paused build session",
    description="""
    Resume execution of a previously paused build session.

    Only sessions in PAUSED status can be resumed.
    """,
)
async def resume_build(request: BuildActionRequest):
    """
    Resume a paused build session.

    Resumes execution of a previously paused build session.

    Args:
        request: Build action parameters

    Returns:
        Action result with updated status

    Raises:
        HTTPException 404: If session not found
        HTTPException 400: If session cannot be resumed
    """
    success = session_manager.resume_session(request.session_id)

    if not success:
        session = session_manager.get_session(request.session_id)
        if not session:
            logger.warning(f"Session not found for resume: {request.session_id}")
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Session not found: {request.session_id}",
            )
        else:
            logger.warning(f"Cannot resume session in {session.status.value} state")
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot resume session in {session.status.value} state",
            )

    session = session_manager.get_session(request.session_id)
    logger.info(f"Build session resumed: {request.session_id}")

    return BuildActionResponse(
        success=True,
        message="Build session resumed successfully",
        session_id=request.session_id,
        status=session.status.value,
    )


@router.post(
    "/cancel",
    response_model=BuildActionResponse,
    summary="Cancel a build session",
    description="""
    Cancel a build session, marking it as cancelled.

    Can be called on sessions in any status.
    """,
)
async def cancel_build(request: BuildActionRequest):
    """
    Cancel a build session.

    Cancels the specified build session, marking it as cancelled.

    Args:
        request: Build action parameters

    Returns:
        Action result with updated status

    Raises:
        HTTPException 404: If session not found
    """
    success = session_manager.cancel_session(request.session_id)

    if not success:
        logger.warning(f"Session not found for cancel: {request.session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {request.session_id}"
        )

    session = session_manager.get_session(request.session_id)
    logger.info(f"Build session cancelled: {request.session_id}")

    return BuildActionResponse(
        success=True,
        message="Build session cancelled successfully",
        session_id=request.session_id,
        status=session.status.value,
    )


@router.get(
    "/sessions",
    response_model=List[SessionStatusResponse],
    summary="List build sessions",
    description="""
    Retrieve all build sessions with optional filtering.

    Filter by:
    - Project alias
    - Status (idle, initializing, running, paused, completed, failed, cancelled)
    - Limit number of results
    """,
)
async def list_sessions(
    status: Optional[str] = Query(None, description="Filter by status"),
    limit: Optional[int] = Query(
        None, ge=1, le=100, description="Maximum number of sessions to return"
    ),
):
    """
    List build sessions.

    Retrieves all build sessions with optional filtering by status.

    Args:
        status: Filter by status (idle, initializing, running, paused, completed, failed, cancelled)
        limit: Maximum number of sessions to return

    Returns:
        List of matching sessions
    """
    sessions = session_manager.list_sessions(status=status)

    if limit:
        sessions = sessions[:limit]

    return [SessionStatusResponse(**s.to_dict()) for s in sessions]


@router.get(
    "/sessions/active",
    response_model=Optional[SessionStatusResponse],
    summary="Get active build session for a project",
    description="""
    Retrieve the active (running or paused) session for a specific project.

    Returns null if no active session exists for the project.
    """,
)
async def get_active_sessions(
    alias: Optional[str] = Query(None, description="Filter by project alias")
):
    """
    Get active build session for a project.

    Retrieves the currently active (running or paused) build session
    for a specific project alias.

    Args:
        alias: Project alias to search for

    Returns:
        Active session or None if no active session exists
    """
    if alias:
        session = session_manager.get_active_session_for_project(alias)
        return SessionStatusResponse(**session.to_dict()) if session else None

    # Return all active sessions if no alias specified
    sessions = session_manager.get_active_sessions()
    return [SessionStatusResponse(**s.to_dict()) for s in sessions]


@router.get(
    "/stats",
    response_model=SessionStatsResponse,
    summary="Get session statistics",
    description="""
    Get aggregate statistics about all build sessions.

    Returns:
    - Total number of sessions
    - Count by status
    - Active session count
    """,
)
async def get_session_stats():
    """
    Get session statistics.

    Returns aggregate statistics about build sessions.

    Returns:
        Session statistics including totals and breakdown by status
    """
    stats = session_manager.get_session_stats()

    # Extract counts for specific statuses
    by_status = stats.get("by_status", {})

    return SessionStatsResponse(
        total_sessions=stats.get("total_sessions", 0),
        active=stats.get("active_sessions", 0),
        completed=by_status.get("completed", 0),
        failed=by_status.get("failed", 0),
        by_status=by_status,
    )


@router.delete(
    "/sessions/{session_id}",
    status_code=status.HTTP_200_OK,
    summary="Delete a build session",
    description="""
    Remove a session from memory.

    Returns success status indicating if session was deleted.
    """,
)
async def delete_session(session_id: str):
    """
    Delete a build session.

    Removes the specified session from memory.

    Args:
        session_id: Session identifier

    Returns:
        Success status

    Raises:
        HTTPException 404: If session not found
    """
    success = session_manager.delete_session(session_id)

    if not success:
        logger.warning(f"Session not found for deletion: {session_id}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail=f"Session not found: {session_id}"
        )

    logger.info(f"Session deleted: {session_id}")
    return {"success": True, "message": "Session deleted successfully"}


@router.post(
    "/cleanup",
    response_model=CleanupResponse,
    summary="Clean up old sessions",
    description="""
    Remove completed or failed sessions older than specified time.

    Default: Remove sessions older than 24 hours
    Range: 1 to 168 hours (7 days)
    """,
)
async def cleanup_sessions(
    older_than_days: int = Query(
        1, ge=0, le=7, description="Remove sessions older than this many days"
    )
):
    """
    Clean up old completed sessions.

    Removes completed or failed sessions older than specified days.

    Args:
        older_than_days: Remove sessions older than this many days (0-7)

    Returns:
        Number of sessions cleaned up
    """
    older_than_hours = older_than_days * 24
    count = session_manager.cleanup_completed_sessions(older_than_hours)

    logger.info(f"Cleaned up {count} sessions older than {older_than_days} days")

    return CleanupResponse(deleted_count=count)
