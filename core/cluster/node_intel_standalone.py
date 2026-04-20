"""
BR3 — Intel Service standalone wrapper
Used by br3-intel.service systemd unit.
Imports the intel router into a minimal FastAPI app.
"""
from core.cluster.base_service import create_app
from core.cluster.node_intelligence import router as intel_router, intel_startup

app = create_app(role="intel-service", version="0.1.0")
app.include_router(intel_router)

@app.on_event("startup")
async def _startup():
    await intel_startup()
