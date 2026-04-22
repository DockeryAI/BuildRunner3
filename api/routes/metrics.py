"""api/routes/metrics.py — dispatch observability endpoints.

Provides a fail-open metrics ingress for BR3 dispatch telemetry and a recent
records read endpoint for the routing dashboard panel.

IMPORTANT: This module exposes ONLY an APIRouter named 'router'.
"""

from __future__ import annotations

import logging
import sqlite3
import subprocess
from pathlib import Path

from fastapi import APIRouter, Query, status
from fastapi.responses import JSONResponse

from core.runtime.metrics_schema import DispatchMetrics

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/metrics", tags=["metrics"])

_BRIDGE_SCRIPT = Path.home() / ".buildrunner" / "scripts" / "lockwood-metrics.sh"
_METRICS_DB = Path.home() / ".buildrunner" / "metrics" / "opus.db"


def _enqueue_dispatch_metrics(metrics: DispatchMetrics) -> None:
    if not _BRIDGE_SCRIPT.exists():
        raise FileNotFoundError(f"metrics bridge unavailable: {_BRIDGE_SCRIPT}")

    subprocess.run(  # noqa: S603
        ["/bin/bash", str(_BRIDGE_SCRIPT), "emit-dispatch-json"],
        input=metrics.model_dump_json(),
        capture_output=True,
        text=True,
        timeout=5,
        check=True,
    )


def _read_recent_dispatch_metrics(limit: int) -> list[DispatchMetrics]:
    if not _METRICS_DB.exists():
        return []

    query = """
        SELECT
          timestamp,
          session_id,
          bucket,
          builder,
          model,
          effort,
          prompt_tokens,
          output_tokens,
          latency_ms,
          done_when_passed,
          verdict,
          override_reason
        FROM dispatch_metrics
        ORDER BY datetime(timestamp) DESC, rowid DESC
        LIMIT ?
    """

    try:
        conn = sqlite3.connect(str(_METRICS_DB))
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(query, (limit,)).fetchall()
        finally:
            conn.close()
    except sqlite3.Error as exc:
        logger.warning("dispatch metrics read failed: %s", exc)
        return []

    records: list[DispatchMetrics] = []
    for row in rows:
        payload = dict(row)
        payload["done_when_passed"] = bool(payload["done_when_passed"])
        try:
            records.append(DispatchMetrics.model_validate(payload))
        except Exception as exc:  # noqa: BLE001
            logger.warning("discarding invalid dispatch metrics row: %s", exc)
    return records


@router.post("/dispatch", status_code=status.HTTP_202_ACCEPTED)
async def post_dispatch_metrics(metrics: DispatchMetrics) -> JSONResponse:
    try:
        _enqueue_dispatch_metrics(metrics)
    except Exception as exc:  # noqa: BLE001
        logger.warning("dispatch metrics bridge unavailable; continuing fail-open: %s", exc)
    return JSONResponse(status_code=status.HTTP_202_ACCEPTED, content={"accepted": True})


@router.get("/dispatch")
async def get_dispatch_metrics(limit: int = Query(50, ge=1, le=500)) -> list[dict[str, object]]:
    return [record.model_dump(mode="json") for record in _read_recent_dispatch_metrics(limit)]
