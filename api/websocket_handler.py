"""WebSocket handler for real-time build monitoring"""

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from typing import Dict, Set
import json
import asyncio

router = APIRouter()

# Store active WebSocket connections by session_id
active_connections: Dict[str, Set[WebSocket]] = {}


@router.websocket("/api/build/stream/{session_id}")
async def websocket_endpoint(websocket: WebSocket, session_id: str):
    await websocket.accept()

    # Add connection to active connections
    if session_id not in active_connections:
        active_connections[session_id] = set()
    active_connections[session_id].add(websocket)

    try:
        # Send initial connection message
        await websocket.send_json(
            {"type": "connection", "status": "connected", "session_id": session_id}
        )

        # Keep connection alive and handle incoming messages
        while True:
            data = await websocket.receive_text()
            message = json.loads(data)

            # Handle ping messages
            if message.get("type") == "ping":
                await websocket.send_json({"type": "pong"})

    except WebSocketDisconnect:
        # Remove connection on disconnect
        if session_id in active_connections:
            active_connections[session_id].discard(websocket)
            if not active_connections[session_id]:
                del active_connections[session_id]


async def broadcast_to_session(session_id: str, message: dict):
    """Broadcast message to all connections for a session"""
    if session_id not in active_connections:
        return

    # Send to all connected clients for this session
    disconnected = set()
    for connection in active_connections[session_id]:
        try:
            await connection.send_json(message)
        except:
            disconnected.add(connection)

    # Clean up disconnected clients
    active_connections[session_id] -= disconnected
    if not active_connections[session_id]:
        del active_connections[session_id]
