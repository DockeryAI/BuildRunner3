"""PRD Sync API - REST endpoints for PRD management"""

from fastapi import APIRouter, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel
from typing import List, Dict, Any, Optional, Set
from pathlib import Path
import asyncio
import logging

from core.prd.prd_controller import get_prd_controller, PRDChangeEvent
from core.prd_integration import get_prd_integration, start_prd_system

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/prd", tags=["prd"])

# WebSocket connection management
active_connections: Set[WebSocket] = set()

# Start PRD system integration on module load
try:
    prd_integration = start_prd_system()
    # Register WebSocket broadcast handler
    prd_integration.set_websocket_broadcast_handler(lambda event: broadcast_prd_update(event))
    logger.info("PRD system integration initialized")
except Exception as e:
    logger.error(f"Failed to initialize PRD system: {e}")


class UpdatePRDRequest(BaseModel):
    updates: Dict[str, Any]
    author: str = "user"


class ParseNLRequest(BaseModel):
    text: str


class RollbackRequest(BaseModel):
    version_index: int


@router.get("/current")
async def get_current_prd():
    """Get current PRD state"""
    try:
        controller = get_prd_controller()
        prd = controller.prd

        return {
            "project_name": prd.project_name,
            "version": prd.version,
            "overview": prd.overview,
            "features": [
                {
                    "id": f.id,
                    "name": f.name,
                    "description": f.description,
                    "priority": f.priority,
                    "requirements": f.requirements,
                    "acceptance_criteria": f.acceptance_criteria,
                    "technical_details": f.technical_details,
                    "dependencies": f.dependencies,
                }
                for f in prd.features
            ],
            "last_updated": prd.last_updated,
        }
    except Exception as e:
        logger.error(f"Error getting PRD: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/update")
async def update_prd(request: UpdatePRDRequest):
    """Update PRD with changes"""
    try:
        controller = get_prd_controller()
        event = controller.update_prd(request.updates, request.author)

        # Broadcast to all WebSocket clients
        await broadcast_prd_update(event)

        return {
            "success": True,
            "event_type": event.event_type.value,
            "affected_features": event.affected_features,
            "timestamp": event.timestamp,
        }
    except Exception as e:
        logger.error(f"Error updating PRD: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/parse-nl")
async def parse_natural_language(request: ParseNLRequest):
    """Parse natural language to PRD updates (preview mode)"""
    try:
        controller = get_prd_controller()
        updates = controller.parse_natural_language(request.text)

        if not updates:
            return {
                "success": False,
                "message": "Could not parse natural language input",
                "updates": {},
            }

        return {
            "success": True,
            "message": "Successfully parsed natural language",
            "updates": updates,
            "preview": _generate_preview(updates, controller.prd),
        }
    except Exception as e:
        logger.error(f"Error parsing NL: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/versions")
async def get_versions():
    """Get PRD version history"""
    try:
        controller = get_prd_controller()
        versions = controller.get_versions()

        return {
            "versions": [
                {
                    "index": i,
                    "timestamp": v.timestamp,
                    "author": v.author,
                    "summary": v.summary,
                    "feature_count": len(v.prd_snapshot.features),
                }
                for i, v in enumerate(versions)
            ]
        }
    except Exception as e:
        logger.error(f"Error getting versions: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback")
async def rollback_version(request: RollbackRequest):
    """Rollback to a previous PRD version"""
    try:
        controller = get_prd_controller()
        controller.rollback_to_version(request.version_index)

        return {"success": True, "message": f"Rolled back to version {request.version_index}"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"Error rolling back: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.websocket("/stream")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time PRD updates"""
    await websocket.accept()
    active_connections.add(websocket)

    try:
        # Send initial PRD state
        controller = get_prd_controller()
        prd = controller.prd
        await websocket.send_json({"type": "initial", "prd": prd.to_dict()})

        # Keep connection alive
        while True:
            data = await websocket.receive_text()
            # Handle ping/pong
            if data == "ping":
                await websocket.send_text("pong")

    except WebSocketDisconnect:
        active_connections.discard(websocket)
        logger.debug("WebSocket client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        active_connections.discard(websocket)


async def broadcast_prd_update(event: PRDChangeEvent):
    """Broadcast PRD update to all connected WebSocket clients"""
    if not active_connections:
        return

    message = {
        "type": "prd_updated",
        "event_type": event.event_type.value,
        "affected_features": event.affected_features,
        "diff": event.diff,
        "timestamp": event.timestamp,
        "prd": event.full_prd.to_dict(),
    }

    disconnected = set()
    for connection in active_connections:
        try:
            await connection.send_json(message)
        except Exception as e:
            logger.error(f"Error broadcasting to client: {e}")
            disconnected.add(connection)

    # Clean up disconnected clients
    active_connections.difference_update(disconnected)


def _generate_preview(updates: Dict[str, Any], current_prd) -> str:
    """Generate preview text of what will change"""
    preview_lines = []

    if "add_feature" in updates:
        feature = updates["add_feature"]
        preview_lines.append(f"➕ Will add feature: {feature['name']}")

    if "remove_feature" in updates:
        feature_id = updates["remove_feature"]
        # Find feature name
        for f in current_prd.features:
            if f.id == feature_id:
                preview_lines.append(f"➖ Will remove feature: {f.name}")
                break

    if "update_feature" in updates:
        feature_id = updates["update_feature"]["id"]
        changes = updates["update_feature"]["updates"]
        for f in current_prd.features:
            if f.id == feature_id:
                preview_lines.append(f"✏️ Will update feature: {f.name}")
                for key in changes:
                    preview_lines.append(f"   - Update {key}")
                break

    return "\n".join(preview_lines) if preview_lines else "No changes detected"
