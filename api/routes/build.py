"""Build monitoring API routes"""

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, Field
from typing import List, Optional
from core.build_session import session_manager, Component, Feature
from api.websocket_handler import broadcast_to_session

router = APIRouter(prefix="/api/build", tags=["build"])


class CreateSessionRequest(BaseModel):
    project_name: str
    project_alias: str
    project_path: str
    components: List[dict] = Field(default_factory=list)
    features: List[dict] = Field(default_factory=list)
    runtime: str = "claude"
    backend: Optional[str] = None
    runtime_source: Optional[str] = None
    runtime_session_id: Optional[str] = None
    capabilities: dict = Field(default_factory=dict)
    dispatch_mode: str = "direct"
    shadow_runtime: Optional[str] = None
    shadow_status: Optional[str] = None


class RuntimeMetadataUpdateRequest(BaseModel):
    runtime: Optional[str] = None
    backend: Optional[str] = None
    runtime_source: Optional[str] = None
    runtime_session_id: Optional[str] = None
    capabilities: Optional[dict] = None
    dispatch_mode: Optional[str] = None
    shadow_runtime: Optional[str] = None
    shadow_status: Optional[str] = None


def _serialize_session(session) -> dict:
    payload = {
        "id": session.id,
        "project_name": session.project_name,
        "project_alias": session.project_alias,
        "project_path": session.project_path,
        "start_time": session.start_time,
        "status": session.status.value,
        "components": [
            {
                "id": c.id,
                "name": c.name,
                "type": c.type,
                "status": c.status.value,
                "progress": c.progress,
                "dependencies": c.dependencies,
                "files": c.files,
                "testsPass": c.tests_pass,
                "error": c.error,
            }
            for c in session.components
        ],
        "features": [
            {
                "id": f.id,
                "name": f.name,
                "description": f.description,
                "priority": f.priority,
                "component": f.component,
                "status": f.status.value,
                "progress": f.progress,
                "tasks": f.tasks,
                "estimatedTime": f.estimated_time,
            }
            for f in session.features
        ],
        "current_component": session.current_component,
        "current_feature": session.current_feature,
        "runtime": session.runtime,
        "backend": session.backend,
        "runtime_source": session.runtime_source,
        "runtime_session_id": session.runtime_session_id,
        "capabilities": session.capabilities,
        "dispatch_mode": session.dispatch_mode,
        "shadow_runtime": session.shadow_runtime,
        "shadow_status": session.shadow_status,
    }
    payload.update(
        {
            "projectName": payload["project_name"],
            "projectAlias": payload["project_alias"],
            "projectPath": payload["project_path"],
            "startTime": payload["start_time"],
            "currentComponent": payload["current_component"],
            "currentFeature": payload["current_feature"],
            "runtimeSource": payload["runtime_source"],
            "runtimeSessionId": payload["runtime_session_id"],
            "dispatchMode": payload["dispatch_mode"],
            "shadowRuntime": payload["shadow_runtime"],
            "shadowStatus": payload["shadow_status"],
        }
    )
    return payload


@router.post("/init")
async def initialize_session(req: CreateSessionRequest):
    """Initialize a new build session"""
    session = session_manager.create_session(
        project_name=req.project_name,
        project_alias=req.project_alias,
        project_path=req.project_path,
        runtime=req.runtime,
        backend=req.backend,
        runtime_source=req.runtime_source,
        runtime_session_id=req.runtime_session_id,
        capabilities=req.capabilities,
        dispatch_mode=req.dispatch_mode,
        shadow_runtime=req.shadow_runtime,
        shadow_status=req.shadow_status,
    )

    # Add components
    for comp_data in req.components:
        comp = Component(
            id=comp_data.get("id", ""),
            name=comp_data.get("name", ""),
            type=comp_data.get("type", "service"),
            dependencies=comp_data.get("dependencies", []),
        )
        session.components.append(comp)

    # Add features
    for feat_data in req.features:
        feat = Feature(
            id=feat_data.get("id", ""),
            name=feat_data.get("name", ""),
            description=feat_data.get("description", ""),
            priority=feat_data.get("priority", "medium"),
            component=feat_data.get("component", ""),
            tasks=feat_data.get("tasks", []),
        )
        session.features.append(feat)

    return {
        "session_id": session.id,
        "project_alias": session.project_alias,
        "message": "Session initialized successfully",
    }


@router.get("/status/{project_alias}")
async def get_session_status(project_alias: str):
    """Get build session status"""
    session = session_manager.get_session(project_alias)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    return _serialize_session(session)


@router.patch("/status/{project_alias}/runtime")
async def update_session_runtime(project_alias: str, req: RuntimeMetadataUpdateRequest):
    """Update runtime-aware session metadata and broadcast it to subscribers."""
    session = session_manager.update_runtime_metadata(
        project_alias,
        runtime=req.runtime,
        backend=req.backend,
        runtime_source=req.runtime_source,
        runtime_session_id=req.runtime_session_id,
        capabilities=req.capabilities,
        dispatch_mode=req.dispatch_mode,
        shadow_runtime=req.shadow_runtime,
        shadow_status=req.shadow_status,
    )
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    await broadcast_to_session(
        session.id,
        {
            "type": "runtime_update",
            "runtime": session.runtime,
            "backend": session.backend,
            "runtime_source": session.runtime_source,
            "runtime_session_id": session.runtime_session_id,
            "capabilities": session.capabilities,
            "dispatch_mode": session.dispatch_mode,
            "shadow_runtime": session.shadow_runtime,
            "shadow_status": session.shadow_status,
        },
    )
    return {"ok": True, "session": _serialize_session(session)}


@router.get("/sessions")
async def list_sessions(runtime: Optional[str] = None, backend: Optional[str] = None):
    """List all build sessions"""
    sessions = session_manager.list_sessions()
    if runtime:
        sessions = [session for session in sessions if session.runtime == runtime]
    if backend:
        sessions = [session for session in sessions if session.backend == backend]
    return {
        "sessions": [
            {
                "id": s.id,
                "project_name": s.project_name,
                "project_alias": s.project_alias,
                "status": s.status.value,
                "start_time": s.start_time,
                "runtime": s.runtime,
                "backend": s.backend,
                "runtime_source": s.runtime_source,
                "dispatch_mode": s.dispatch_mode,
                "shadow_runtime": s.shadow_runtime,
                "shadow_status": s.shadow_status,
            }
            for s in sessions
        ]
    }
