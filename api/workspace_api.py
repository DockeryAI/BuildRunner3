"""
Workspace Management API
Endpoints for managing workspace files and Claude integration
"""
from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Optional
import json
from datetime import datetime
import logging

# Import our modules
from api.log_streamer import manager as log_manager, websocket_endpoint
from api.workspace_watcher import monitor, manager as workspace_manager

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/workspace", tags=["workspace"])


class PRDRequest(BaseModel):
    project_name: str
    content: str
    metadata: Optional[Dict] = {}


class TaskRequest(BaseModel):
    project_name: str
    tasks: List[Dict]


class ContextRequest(BaseModel):
    project_name: str
    context_type: str
    content: str


@router.on_event("startup")
async def startup_event():
    """Start workspace monitoring on server startup"""
    monitor.start()
    logger.info("Workspace monitoring started")


@router.on_event("shutdown")
async def shutdown_event():
    """Stop workspace monitoring on server shutdown"""
    monitor.stop()
    logger.info("Workspace monitoring stopped")


@router.post("/prd/save")
async def save_prd(request: PRDRequest):
    """Save PRD to workspace"""
    try:
        result = await workspace_manager.save_prd(
            request.project_name,
            request.content
        )
        return result
    except Exception as e:
        logger.error(f"Error saving PRD: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/tasks/save")
async def save_tasks(request: TaskRequest):
    """Save task list to workspace"""
    try:
        result = await workspace_manager.save_tasks(
            request.project_name,
            request.tasks
        )
        return result
    except Exception as e:
        logger.error(f"Error saving tasks: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/save")
async def save_context(request: ContextRequest):
    """Save context file for Claude"""
    try:
        result = await workspace_manager.save_context(
            request.project_name,
            request.context_type,
            request.content
        )
        return result
    except Exception as e:
        logger.error(f"Error saving context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/output/list")
async def list_outputs(project_name: Optional[str] = None):
    """List Claude output files"""
    try:
        outputs = await workspace_manager.list_outputs(project_name)
        return {"outputs": outputs}
    except Exception as e:
        logger.error(f"Error listing outputs: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/output/read/{filename}")
async def read_output(filename: str):
    """Read a specific Claude output file"""
    try:
        content = await workspace_manager.read_output(filename)
        if content is None:
            raise HTTPException(status_code=404, detail="Output file not found")
        return {"content": content}
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error reading output: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/context/generate/{project_name}")
async def generate_claude_context(project_name: str):
    """Generate comprehensive context file for Claude"""
    try:
        filepath = await workspace_manager.generate_claude_context(project_name)
        return {
            "success": True,
            "context_file": filepath,
            "message": f"Context generated. Run: claude {filepath}"
        }
    except Exception as e:
        logger.error(f"Error generating context: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/state")
async def get_workspace_state():
    """Get current workspace state"""
    try:
        state = monitor.get_workspace_state()
        return state
    except Exception as e:
        logger.error(f"Error getting workspace state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    """WebSocket endpoint for log streaming"""
    await websocket_endpoint(websocket)


@router.websocket("/ws/events")
async def websocket_events(websocket: WebSocket):
    """WebSocket endpoint for workspace events"""
    await websocket.accept()

    async def send_event(event_data):
        try:
            await websocket.send_json(event_data)
        except:
            pass

    # Add callback for workspace events
    monitor.add_callback(send_event)

    try:
        # Send initial state
        state = monitor.get_workspace_state()
        await websocket.send_json({
            'type': 'initial_state',
            'data': state
        })

        # Keep connection alive
        while True:
            data = await websocket.receive_json()
            if data.get('type') == 'ping':
                await websocket.send_json({'type': 'pong'})

    except WebSocketDisconnect:
        monitor.remove_callback(send_event)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        monitor.remove_callback(send_event)


# Integration with BuildRunner CLI
class BuildRunnerBridge:
    """Bridge between UI and BuildRunner CLI"""

    @staticmethod
    async def init_project(project_name: str) -> dict:
        """Initialize BuildRunner project and create workspace"""
        import subprocess
        import os

        try:
            # Run br init
            result = subprocess.run(
                ['br', 'init', project_name],
                capture_output=True,
                text=True,
                cwd='/Users/byronhudson/Projects/BuildRunner3'
            )

            # Create initial PRD template
            prd_template = f"""# {project_name} - Product Requirements Document

## Overview
[Describe the project purpose and goals]

## Features
1. Feature 1
2. Feature 2
3. Feature 3

## Technical Requirements
- Requirement 1
- Requirement 2
- Requirement 3

## Success Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

---
Generated by BuildRunner UI
"""
            await workspace_manager.save_prd(project_name, prd_template)

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'workspace': f'/workspace/prd/{project_name}.md'
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }

    @staticmethod
    async def run_build(project_name: str) -> dict:
        """Execute BuildRunner build process"""
        import subprocess

        try:
            # Generate context first
            context_file = await workspace_manager.generate_claude_context(project_name)

            # Run br run with context
            result = subprocess.run(
                ['br', 'run', '--context', context_file],
                capture_output=True,
                text=True,
                cwd='/Users/byronhudson/Projects/BuildRunner3'
            )

            # Log output
            log_file = f"/Users/byronhudson/Projects/BuildRunner3/workspace/logs/{project_name}_build.log"
            with open(log_file, 'w') as f:
                f.write(result.stdout)
                if result.stderr:
                    f.write(f"\n\nERRORS:\n{result.stderr}")

            return {
                'success': result.returncode == 0,
                'output': result.stdout,
                'error': result.stderr,
                'log_file': log_file
            }
        except Exception as e:
            return {
                'success': False,
                'error': str(e)
            }


bridge = BuildRunnerBridge()


@router.post("/buildrunner/init/{project_name}")
async def init_buildrunner_project(project_name: str):
    """Initialize BuildRunner project"""
    result = await bridge.init_project(project_name)
    return result


@router.post("/buildrunner/run/{project_name}")
async def run_buildrunner_build(project_name: str):
    """Run BuildRunner build process"""
    result = await bridge.run_build(project_name)
    return result