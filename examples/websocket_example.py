"""
WebSocket Real-Time Updates Example

Demonstrates:
1. Setting up WebSocket handler with FastAPI
2. Creating file watcher for build monitoring
3. Broadcasting updates to connected clients

Requirements:
    pip install fastapi uvicorn watchdog websockets

Usage:
    python examples/websocket_example.py

Then connect via WebSocket:
    ws://localhost:8000/api/build/stream/session_123
"""

import asyncio
from pathlib import Path
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

# Import WebSocket handler
from api.websocket_handler import (
    router as websocket_router,
    broadcast_component_update,
    broadcast_checkpoint_update,
    broadcast_terminal_output,
    broadcast_build_progress,
)

# Import file watcher
from core.build.file_watcher import create_file_watcher_with_websocket
from core.build.checkpoint_parser import parse_checkpoint


# Create FastAPI app
app = FastAPI(
    title="BuildRunner WebSocket Example",
    description="Real-time build monitoring via WebSocket",
    version="1.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include WebSocket router
app.include_router(websocket_router)


# Global watcher instance
file_watcher = None


@app.on_event("startup")
async def startup_event():
    """Start file watcher on application startup"""
    global file_watcher

    # Get project root
    project_root = Path(__file__).parent.parent

    # Session ID for this example
    session_id = "example_session"

    print(f"🚀 Starting file watcher for session: {session_id}")

    # Create file watcher with WebSocket broadcasting
    file_watcher = await create_file_watcher_with_websocket(
        project_root=str(project_root),
        session_id=session_id,
        websocket_broadcaster=broadcast_checkpoint_update
    )

    print(f"👁️  Watching: {project_root}/.buildrunner/")
    print(f"📡 WebSocket endpoint: /api/build/stream/{session_id}")


@app.on_event("shutdown")
async def shutdown_event():
    """Stop file watcher on application shutdown"""
    global file_watcher

    if file_watcher:
        await file_watcher.stop()
        print("🛑 File watcher stopped")


@app.get("/")
async def root():
    """Root endpoint with usage instructions"""
    return {
        "message": "BuildRunner WebSocket Server",
        "websocket_endpoint": "/api/build/stream/{session_id}",
        "example": "ws://localhost:8000/api/build/stream/example_session",
        "documentation": "/docs",
    }


@app.post("/demo/send-update")
async def send_demo_update(session_id: str = "example_session"):
    """
    Demo endpoint to manually trigger updates.

    Useful for testing without creating actual files.
    """
    # Send component update
    await broadcast_component_update(
        session_id=session_id,
        component_id="demo_component",
        status="in_progress",
        progress=50.0,
        metadata={"message": "Demo update from API"}
    )

    # Send terminal output
    await broadcast_terminal_output(
        session_id=session_id,
        output="Building component demo_component...\n",
        output_type="stdout",
        source="demo"
    )

    # Send build progress
    await broadcast_build_progress(
        session_id=session_id,
        total_components=10,
        completed_components=5,
        percent=50.0
    )

    return {"status": "Updates sent", "session_id": session_id}


if __name__ == "__main__":
    import uvicorn

    # Run server
    print("\n" + "="*60)
    print("BuildRunner WebSocket Server")
    print("="*60)
    print("\nStarting server on http://localhost:8000")
    print("\nWebSocket endpoints:")
    print("  • ws://localhost:8000/api/build/stream/{session_id}")
    print("\nAPI endpoints:")
    print("  • GET  /          - Server info")
    print("  • POST /demo/send-update - Send demo update")
    print("  • GET  /docs      - API documentation")
    print("\nTest with:")
    print("  curl -X POST http://localhost:8000/demo/send-update")
    print("="*60 + "\n")

    uvicorn.run(
        app,
        host="0.0.0.0",
        port=8000,
        log_level="info"
    )
