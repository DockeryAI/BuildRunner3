"""
WebSocket Live Updates

Provides real-time updates for:
- Task status changes
- Telemetry events
- Session updates
- Progress notifications
"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set, List
import asyncio
import json
from datetime import datetime

# Import core modules
from core.telemetry import Event, EventCollector
from core.task_queue import TaskQueue
from core.parallel import SessionManager

router = APIRouter()


class ConnectionManager:
    """
    Manages WebSocket connections and broadcasts.

    Handles:
    - Connection lifecycle
    - Broadcasting to all clients
    - Targeted messages to specific clients
    """

    def __init__(self):
        self.active_connections: Set[WebSocket] = set()
        self.client_metadata: Dict[WebSocket, Dict] = {}

    async def connect(self, websocket: WebSocket, client_id: str = None):
        """
        Accept and register a new WebSocket connection.

        Args:
            websocket: WebSocket connection
            client_id: Optional client identifier
        """
        await websocket.accept()
        self.active_connections.add(websocket)
        self.client_metadata[websocket] = {
            "client_id": client_id or str(id(websocket)),
            "connected_at": datetime.now().isoformat(),
        }

    def disconnect(self, websocket: WebSocket):
        """
        Remove a WebSocket connection.

        Args:
            websocket: WebSocket connection to remove
        """
        self.active_connections.discard(websocket)
        self.client_metadata.pop(websocket, None)

    async def send_personal_message(self, message: Dict, websocket: WebSocket):
        """
        Send message to specific client.

        Args:
            message: Message to send
            websocket: Target WebSocket
        """
        try:
            await websocket.send_json(message)
        except Exception:
            # Connection closed
            self.disconnect(websocket)

    async def broadcast(self, message: Dict):
        """
        Broadcast message to all connected clients.

        Args:
            message: Message to broadcast
        """
        disconnected = set()

        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except Exception:
                # Mark for removal
                disconnected.add(connection)

        # Clean up disconnected clients
        for connection in disconnected:
            self.disconnect(connection)

    def get_connection_count(self) -> int:
        """Get number of active connections"""
        return len(self.active_connections)


# Global connection manager
manager = ConnectionManager()


@router.websocket("/updates")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket endpoint for real-time updates.

    Clients connect to this endpoint to receive:
    - Task status updates
    - Telemetry events
    - Session changes
    - Progress notifications
    """
    await manager.connect(websocket)

    try:
        # Send welcome message
        await websocket.send_json({
            "type": "connection",
            "status": "connected",
            "timestamp": datetime.now().isoformat(),
            "message": "Connected to BuildRunner live updates",
        })

        # Keep connection alive and handle incoming messages
        while True:
            # Receive messages from client
            try:
                data = await websocket.receive_text()
                message = json.loads(data)

                # Handle client messages (ping, subscribe, etc.)
                if message.get("type") == "ping":
                    await websocket.send_json({
                        "type": "pong",
                        "timestamp": datetime.now().isoformat(),
                    })
                elif message.get("type") == "subscribe":
                    # Handle subscription to specific event types
                    await websocket.send_json({
                        "type": "subscribed",
                        "topics": message.get("topics", []),
                        "timestamp": datetime.now().isoformat(),
                    })

            except WebSocketDisconnect:
                break
            except json.JSONDecodeError:
                # Invalid JSON
                await websocket.send_json({
                    "type": "error",
                    "message": "Invalid JSON",
                })
            except Exception as e:
                # Other errors
                await websocket.send_json({
                    "type": "error",
                    "message": str(e),
                })

    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(websocket)


async def broadcast_task_update(task_id: str, status: str, data: Dict = None):
    """
    Broadcast task status update to all clients.

    Args:
        task_id: Task identifier
        status: New task status
        data: Additional task data
    """
    message = {
        "type": "task_update",
        "task_id": task_id,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "data": data or {},
    }
    await manager.broadcast(message)


async def broadcast_telemetry_event(event: Event):
    """
    Broadcast telemetry event to all clients.

    Args:
        event: Telemetry event
    """
    message = {
        "type": "telemetry_event",
        "event_type": event.event_type.value,
        "event_id": event.event_id,
        "timestamp": event.timestamp.isoformat(),
        "session_id": event.session_id or "",
        "metadata": event.metadata or {},
    }
    await manager.broadcast(message)


async def broadcast_progress_update(completed: int, total: int, percent: float):
    """
    Broadcast progress update to all clients.

    Args:
        completed: Number of completed tasks
        total: Total number of tasks
        percent: Completion percentage
    """
    message = {
        "type": "progress_update",
        "completed": completed,
        "total": total,
        "percent": percent,
        "timestamp": datetime.now().isoformat(),
    }
    await manager.broadcast(message)


async def broadcast_session_update(session_id: str, status: str, data: Dict = None):
    """
    Broadcast session update to all clients.

    Args:
        session_id: Session identifier
        status: New session status
        data: Additional session data
    """
    message = {
        "type": "session_update",
        "session_id": session_id,
        "status": status,
        "timestamp": datetime.now().isoformat(),
        "data": data or {},
    }
    await manager.broadcast(message)


def get_connection_manager() -> ConnectionManager:
    """
    Get the global connection manager.

    Returns:
        ConnectionManager instance
    """
    return manager


# Background task to periodically send updates
async def periodic_updates_task(interval: int = 5):
    """
    Background task that sends periodic updates to clients.

    Args:
        interval: Update interval in seconds
    """
    while True:
        await asyncio.sleep(interval)

        if manager.get_connection_count() > 0:
            # Send heartbeat
            await manager.broadcast({
                "type": "heartbeat",
                "timestamp": datetime.now().isoformat(),
                "connections": manager.get_connection_count(),
            })
