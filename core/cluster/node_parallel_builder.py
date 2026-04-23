"""
BR3 Cluster — Node 3: Otis (Parallel Builder) — primary port 8100

Minimal primary-role endpoint for the parallel-builder node. All real
compute (tsc-typecheck, codex dispatch) lives on companion ports; this
service exists so the dashboard + router see Phase 1 schema=2 ground
truth at the canonical cluster port.

Run: uvicorn core.cluster.node_parallel_builder:app --host 0.0.0.0 --port 8100
"""

from core.cluster.base_service import create_app

SERVICE_ROLE = "parallel-builder"
SERVICE_VERSION = "0.2.0"

app = create_app(role=SERVICE_ROLE, version=SERVICE_VERSION)
