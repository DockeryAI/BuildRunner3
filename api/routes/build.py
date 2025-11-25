"""Build monitoring API routes"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from core.build_session import session_manager, Component, Feature, ComponentStatus

router = APIRouter(prefix="/api/build", tags=["build"])

class CreateSessionRequest(BaseModel):
    project_name: str
    project_alias: str
    project_path: str
    components: List[dict] = []
    features: List[dict] = []

class SessionResponse(BaseModel):
    id: str
    project_name: str
    project_alias: str
    project_path: str
    start_time: int
    status: str
    components: List[dict]
    features: List[dict]
    current_component: Optional[str] = None
    current_feature: Optional[str] = None

@router.post("/init")
async def initialize_session(req: CreateSessionRequest):
    """Initialize a new build session"""
    session = session_manager.create_session(
        project_name=req.project_name,
        project_alias=req.project_alias,
        project_path=req.project_path
    )
    
    # Add components
    for comp_data in req.components:
        comp = Component(
            id=comp_data.get('id', ''),
            name=comp_data.get('name', ''),
            type=comp_data.get('type', 'service'),
            dependencies=comp_data.get('dependencies', [])
        )
        session.components.append(comp)
    
    # Add features
    for feat_data in req.features:
        feat = Feature(
            id=feat_data.get('id', ''),
            name=feat_data.get('name', ''),
            description=feat_data.get('description', ''),
            priority=feat_data.get('priority', 'medium'),
            component=feat_data.get('component', ''),
            tasks=feat_data.get('tasks', [])
        )
        session.features.append(feat)
    
    return {
        "session_id": session.id,
        "project_alias": session.project_alias,
        "message": "Session initialized successfully"
    }

@router.get("/status/{project_alias}")
async def get_session_status(project_alias: str):
    """Get build session status"""
    session = session_manager.get_session(project_alias)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    return {
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
                "error": c.error
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
                "estimatedTime": f.estimated_time
            }
            for f in session.features
        ],
        "currentComponent": session.current_component,
        "currentFeature": session.current_feature
    }

@router.get("/sessions")
async def list_sessions():
    """List all build sessions"""
    sessions = session_manager.list_sessions()
    return {
        "sessions": [
            {
                "id": s.id,
                "project_name": s.project_name,
                "project_alias": s.project_alias,
                "status": s.status.value,
                "start_time": s.start_time
            }
            for s in sessions
        ]
    }
