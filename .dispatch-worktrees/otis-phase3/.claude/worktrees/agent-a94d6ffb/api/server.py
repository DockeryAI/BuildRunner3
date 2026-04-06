"""
FastAPI Server for BuildRunner 3.2 Web UI

Provides REST API and WebSocket endpoints for the BuildRunner web interface.
Integrates with core orchestrator, telemetry, and task queue systems.
"""

import os
from pathlib import Path
from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
import uvicorn
from typing import Dict
import logging

# Load environment variables from .env file
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(dotenv_path=env_path)
print(f"Loaded .env from: {env_path}")
print(f"OpenRouter API Key present: {bool(os.getenv('OPENROUTER_API_KEY'))}")

# Import routes
from api.routes import orchestrator, telemetry, agents, execute
from api.routes.prd_builder import router as prd_router
from api.routes.prd_sync import router as prd_sync_router
from api.websockets import live_updates
from api.workspace_api import router as workspace_router

# Import telemetry (commented out - needs opentelemetry package)
# from core.telemetry.otel_instrumentation import initialize_telemetry, get_telemetry

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan manager"""
    # Startup
    print("Starting BuildRunner API server...")

    # Initialize OpenTelemetry (disabled for now - needs opentelemetry package)
    # initialize_telemetry()
    # logger.info("OpenTelemetry instrumentation initialized")

    yield

    # Shutdown
    print("Shutting down BuildRunner API server...")

    # Shutdown telemetry gracefully (disabled for now)
    # get_telemetry().shutdown()


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
        "http://localhost:3001",  # React dev server (alternate port)
        "http://localhost:5173",  # Vite dev server
        "http://127.0.0.1:3000",
        "http://127.0.0.1:3001",
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
app.include_router(execute.router, prefix="/api", tags=["execute"])
app.include_router(prd_router, prefix="/api", tags=["prd"])
app.include_router(prd_sync_router, tags=["prd-sync"])
app.include_router(workspace_router, tags=["workspace"])

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
