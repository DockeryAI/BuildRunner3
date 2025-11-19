"""
FastAPI Server for BuildRunner 3.2 Web UI

Provides REST API and WebSocket endpoints for the BuildRunner web interface.
Integrates with core orchestrator, telemetry, and task queue systems.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import Dict

# Import routes
from api.routes import orchestrator, telemetry, agents
from api.websockets import live_updates


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting BuildRunner API server...")
    yield
    # Shutdown
    print("Shutting down BuildRunner API server...")


# Create FastAPI app
app = FastAPI(
    title="BuildRunner API",
    description="REST API and WebSocket interface for BuildRunner 3.2",
    version="3.2.0",
    lifespan=lifespan,
)

# Configure CORS for React frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React dev server
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"],
    max_age=3600,
)


# Health check endpoint
@app.get("/health")
async def health_check() -> Dict:
    """
    Health check endpoint.

    Returns:
        Status information about the API server
    """
    return {
        "status": "healthy",
        "service": "BuildRunner API",
        "version": "3.2.0",
    }


@app.get("/")
async def root() -> Dict:
    """
    Root endpoint.

    Returns:
        API information
    """
    return {
        "service": "BuildRunner API",
        "version": "3.2.0",
        "docs": "/docs",
        "websocket": "/ws",
    }


# Include routers
app.include_router(orchestrator.router, prefix="/api/orchestrator", tags=["orchestrator"])
app.include_router(telemetry.router, prefix="/api/telemetry", tags=["telemetry"])
app.include_router(agents.router, prefix="/api/agents", tags=["agents"])

# Include WebSocket
app.include_router(live_updates.router, prefix="/ws", tags=["websocket"])


def run_server(host: str = "127.0.0.1", port: int = 8080, reload: bool = True):
    """
    Run the FastAPI server.

    Args:
        host: Host to bind to
        port: Port to bind to
        reload: Enable auto-reload for development
    """
    uvicorn.run(
        "api.server:app",
        host=host,
        port=port,
        reload=reload,
        log_level="info",
    )


if __name__ == "__main__":
    run_server()
