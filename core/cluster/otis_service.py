"""
BR3 Cluster — Otis Node Service
Composes base_service + TypecheckManager.
Exposes /pause, /resume, /status on the uvicorn app.

Run: uvicorn core.cluster.otis_service:app --host 0.0.0.0 --port 8103
     (Otis is 10.0.1.103, port 8103 by convention)
"""

import os
import time
import logging


from core.cluster.base_service import create_app
from core.cluster.otis_typecheck import get_manager

logger = logging.getLogger("otis.service")

SERVICE_VERSION = "0.1.0"
SERVICE_ROLE = "tsc-typecheck"

# Port Otis listens on
PORT = int(os.environ.get("OTIS_PORT", "8103"))

# ── App ───────────────────────────────────────────────────────────────────────

app = create_app(role=SERVICE_ROLE, version=SERVICE_VERSION)

# ── Startup / shutdown ────────────────────────────────────────────────────────

_service_start = time.time()


@app.on_event("startup")
async def startup():
    """Start the TypecheckManager on server start."""
    manager = get_manager()
    manager.start()
    logger.info("Otis TypecheckManager started")


@app.on_event("shutdown")
async def shutdown():
    """Stop all workers cleanly."""
    manager = get_manager()
    manager.stop()
    logger.info("Otis TypecheckManager stopped")


# ── Routes ────────────────────────────────────────────────────────────────────

@app.post("/pause")
async def pause():
    """
    SIGTERM all running tsc workers (free compilation cache).
    Called by the router when it dispatches heavy work to Otis.
    Workers cold-start on /resume (~8s per project).
    """
    manager = get_manager()
    manager.pause()
    return {"status": "paused", "message": "All tsc workers stopped"}


@app.post("/resume")
async def resume():
    """
    Cold-start all tsc workers.
    Called by the router when the dispatched work finishes on Otis.
    """
    manager = get_manager()
    manager.resume()
    return {"status": "resumed", "message": "All tsc workers restarted"}


@app.get("/status")
async def status():
    """
    Full typecheck status.
    Returns workloads[] (Phase 1 schema), busy_state, label.
    """
    manager = get_manager()
    return manager.status()


@app.get("/workloads")
async def workloads():
    """
    Raw workloads[] list — Phase 1 schema.
    Consumed by the cluster dashboard.
    """
    manager = get_manager()
    return {"workloads": manager.workloads()}


# ── Extended /health (overlays base_service /health) ──────────────────────────

@app.get("/api/health")
async def otis_health():
    """Otis-specific health — includes typecheck summary."""
    manager = get_manager()
    st = manager.status()

    return {
        "status": "healthy",
        "role": SERVICE_ROLE,
        "version": SERVICE_VERSION,
        "uptime": round(time.time() - _service_start, 1),
        "tsc": {
            "label": st["label"],
            "busy_state": st["busy_state"],
            "paused": st["paused"],
            "project_count": st["project_count"],
            "active_count": st["active_count"],
            "total_errors": st["total_errors"],
        },
    }
