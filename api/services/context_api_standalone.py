"""api/services/context_api_standalone.py — Standalone entrypoint for context API.

Bootstraps the FastAPI app for the context bundle service and mounts the
context router. Run independently on Jimmy (:4500) or alongside node_semantic.

This is the ONLY place where `app = create_app(role='context-api')` is called
for the context service. api/routes/context.py exports only an APIRouter —
no module-level app instantiation there.

Usage (standalone):
    # Run just the context API on port 4500
    python -m api.services.context_api_standalone

    # Or with uvicorn directly:
    uvicorn api.services.context_api_standalone:app --host 0.0.0.0 --port 4500

Usage (imported):
    from api.services.context_api_standalone import app, context_router

The standalone app is also used by node_semantic.py to mount context routes
alongside the semantic search endpoints.
"""

from __future__ import annotations

import logging
import os

from core.cluster.base_service import create_app
from api.routes.context import router as context_router  # noqa: F401 — re-exported

logger = logging.getLogger(__name__)

# Standalone FastAPI app — only created in this module.
# node_semantic.py imports context_router directly, not this app.
app = create_app(role="context-api", version="0.1.0")
app.include_router(context_router)


def _log_startup_info() -> None:
    flag = os.environ.get("BR3_MULTI_MODEL_CONTEXT", "off")
    port = int(os.environ.get("CONTEXT_API_PORT", "4500"))
    logger.info(
        "Context API standalone — port=%d BR3_MULTI_MODEL_CONTEXT=%s",
        port,
        flag,
    )


@app.on_event("startup")
async def _startup() -> None:
    _log_startup_info()


if __name__ == "__main__":
    import uvicorn

    host = os.environ.get("CONTEXT_API_HOST", "0.0.0.0")
    port = int(os.environ.get("CONTEXT_API_PORT", "4500"))

    _log_startup_info()
    uvicorn.run(
        "api.services.context_api_standalone:app",
        host=host,
        port=port,
        reload=False,
        log_level="info",
    )
