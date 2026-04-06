"""
BR3 Cluster — Base Node Service

Every cluster node inherits from this. Provides:
- GET /health — returns {"status": "healthy", "role": "...", "uptime": ...}
- GET /info — returns capabilities, version, resource usage

Usage:
    from core.cluster.base_service import create_app

    app = create_app(role="semantic-search")

    @app.post("/api/search")
    async def search(request: Request):
        ...

    # Run with: uvicorn node_semantic:app --host 0.0.0.0 --port 8100
"""

import time
import platform
import psutil
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def create_app(role: str, version: str = "0.1.0") -> FastAPI:
    """Create a FastAPI app with standard cluster endpoints."""

    app = FastAPI(title=f"BR3 Cluster — {role}", version=version)
    start_time = time.time()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/health")
    async def health():
        return {
            "status": "healthy",
            "role": role,
            "uptime": round(time.time() - start_time, 1),
            "version": version,
        }

    @app.get("/info")
    async def info():
        mem = psutil.virtual_memory()
        disk = psutil.disk_usage("/")
        return {
            "role": role,
            "version": version,
            "uptime": round(time.time() - start_time, 1),
            "platform": platform.system(),
            "python": platform.python_version(),
            "memory": {
                "total_gb": round(mem.total / (1024**3), 1),
                "available_gb": round(mem.available / (1024**3), 1),
                "percent_used": mem.percent,
            },
            "disk": {
                "total_gb": round(disk.total / (1024**3), 1),
                "free_gb": round(disk.free / (1024**3), 1),
                "percent_used": round(disk.used / disk.total * 100, 1),
            },
            "cpu_count": psutil.cpu_count(),
            "cpu_percent": psutil.cpu_percent(interval=0.1),
        }

    return app
