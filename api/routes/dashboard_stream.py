"""dashboard_stream.py — WebSocket broadcaster for Cluster Max Dashboard.

Runs as part of the dashboard service on port 4400.
WS path: /ws

Emits event types:
  node-health       — per-node CPU/RAM/task metrics + Jimmy-specific + Below VRAM
  overflow-reserve  — Lockwood / Lomax idle/warming/active/draining + event log
  storage-health    — /srv/jimmy/ directory usage + backup timestamps + offsite sync
  consensus         — recent adversarial review results
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(tags=["dashboard"])

# ---------------------------------------------------------------------------
# Connection manager
# ---------------------------------------------------------------------------

class _ConnectionManager:
    """Tracks active WebSocket connections and broadcasts to all."""

    def __init__(self) -> None:
        self._sockets: list[WebSocket] = []

    async def connect(self, ws: WebSocket) -> None:
        await ws.accept()
        self._sockets.append(ws)
        logger.info("dashboard_stream: client connected (%d total)", len(self._sockets))

    def disconnect(self, ws: WebSocket) -> None:
        self._sockets = [s for s in self._sockets if s is not ws]
        logger.info("dashboard_stream: client disconnected (%d remain)", len(self._sockets))

    async def broadcast(self, payload: dict[str, Any]) -> None:
        dead: list[WebSocket] = []
        text = json.dumps(payload)
        for ws in list(self._sockets):
            try:
                await ws.send_text(text)
            except Exception:  # noqa: BLE001
                dead.append(ws)
        for ws in dead:
            self.disconnect(ws)


_manager = _ConnectionManager()

# ---------------------------------------------------------------------------
# Data collectors — read from Jimmy filesystem
# ---------------------------------------------------------------------------

_JIMMY_SRV = Path(os.environ.get("JIMMY_SRV_ROOT", "/srv/jimmy"))


def _safe_read_json(path: Path) -> dict[str, Any]:
    try:
        return json.loads(path.read_text())
    except Exception:  # noqa: BLE001
        return {}


def _collect_node_health() -> dict[str, Any]:
    """Read per-node metrics from Jimmy status files."""
    status_dir = _JIMMY_SRV / "status" / "nodes"
    nodes: dict[str, Any] = {}
    node_ids = ["muddy", "lockwood", "walter", "otis", "lomax", "below", "jimmy"]
    for nid in node_ids:
        node_file = status_dir / f"{nid}.json"
        data = _safe_read_json(node_file) if node_file.exists() else {}
        nodes[nid] = data if data else {"online": False}
    return {"nodes": nodes}


def _collect_overflow_reserve() -> dict[str, Any]:
    """Read Lockwood / Lomax reserve state from Jimmy status files."""
    status_dir = _JIMMY_SRV / "status"
    reserve_file = status_dir / "overflow-reserve.json"
    if reserve_file.exists():
        return _safe_read_json(reserve_file)
    return {
        "nodes": {
            "lockwood": {"state": "idle", "since": None},
            "lomax":    {"state": "idle", "since": None},
        },
        "events": [],
        "freq": {},
    }


def _collect_storage_health() -> dict[str, Any]:
    """Read /srv/jimmy/ directory sizes + backup timestamps."""
    status_dir = _JIMMY_SRV / "status"
    storage_file = status_dir / "storage-health.json"
    if storage_file.exists():
        return _safe_read_json(storage_file)

    dg_file = status_dir / "disk-guard.json"
    dg = _safe_read_json(dg_file) if dg_file.exists() else None
    return {
        "disk_guard": dg,
        "disk_total_bytes": None,
        "disk_free_bytes": None,
        "dirs": {},
        "backup_timestamps": {},
        "offsite_sync": {},
        "cron_timestamps": {},
        "backups_paused": (status_dir / "backups-paused").exists(),
    }


def _collect_consensus() -> dict[str, Any]:
    """Read recent adversarial review results from Jimmy archive."""
    archive_dir = _JIMMY_SRV / "archive" / "adversarial-reviews"
    if not archive_dir.exists():
        return {"reviews": []}
    try:
        files = sorted(archive_dir.glob("*.json"), key=lambda p: p.stat().st_mtime, reverse=True)[:10]
        reviews = []
        for f in files:
            data = _safe_read_json(f)
            if data:
                reviews.append(data)
        return {"reviews": reviews}
    except Exception as exc:  # noqa: BLE001
        logger.debug("dashboard_stream: consensus collect failed: %s", exc)
        return {"reviews": []}


# ---------------------------------------------------------------------------
# Broadcast loop
# ---------------------------------------------------------------------------

_INTERVALS: dict[str, float] = {
    "node-health":      5.0,
    "overflow-reserve": 10.0,
    "storage-health":   60.0,
    "consensus":        20.0,
}

_COLLECTORS = {
    "node-health":      _collect_node_health,
    "overflow-reserve": _collect_overflow_reserve,
    "storage-health":   _collect_storage_health,
    "consensus":        _collect_consensus,
}

_last_sent: dict[str, float] = {k: 0.0 for k in _INTERVALS}
_cache:     dict[str, Any]   = {}


async def _broadcast_loop() -> None:
    """Background task: collect and broadcast each event type at its interval."""
    logger.info("dashboard_stream: broadcast loop started")
    while True:
        now = time.monotonic()
        for event_type, interval in _INTERVALS.items():
            if now - _last_sent.get(event_type, 0.0) >= interval:
                try:
                    data = await asyncio.get_event_loop().run_in_executor(
                        None, _COLLECTORS[event_type]
                    )
                    _cache[event_type] = data
                    _last_sent[event_type] = now
                    if _manager._sockets:
                        await _manager.broadcast({"type": event_type, "data": data})
                except Exception as exc:  # noqa: BLE001
                    logger.warning("dashboard_stream: collect error [%s]: %s", event_type, exc)
        await asyncio.sleep(1.0)


_loop_task: asyncio.Task | None = None  # type: ignore[type-arg]


def start_broadcast_loop() -> None:
    """Called once at app startup to begin the background broadcast loop."""
    global _loop_task
    if _loop_task is None or _loop_task.done():
        _loop_task = asyncio.ensure_future(_broadcast_loop())
        logger.info("dashboard_stream: broadcast loop scheduled")


# ---------------------------------------------------------------------------
# WebSocket endpoint
# ---------------------------------------------------------------------------

@router.websocket("/ws")
async def dashboard_ws(ws: WebSocket) -> None:
    """WebSocket endpoint at ws://10.0.1.106:4400/ws.

    On connect: sends a full-state resync of all cached event types.
    Handles {"type": "resync"} client messages by re-sending cached state.
    Heartbeat pings: client sends {"type": "ping"}, server replies {"type": "pong"}.
    """
    await _manager.connect(ws)
    for event_type, data in _cache.items():
        try:
            await ws.send_text(json.dumps({"type": event_type, "data": data}))
        except Exception:  # noqa: BLE001
            break
    try:
        while True:
            try:
                raw = await asyncio.wait_for(ws.receive_text(), timeout=35.0)
            except asyncio.TimeoutError:
                logger.debug("dashboard_stream: client heartbeat timeout, closing")
                break
            try:
                msg = json.loads(raw)
            except ValueError:
                continue
            msg_type = msg.get("type")
            if msg_type == "ping":
                await ws.send_text(json.dumps({"type": "pong", "ts": datetime.now(tz=timezone.utc).isoformat()}))
            elif msg_type == "resync":
                for event_type, data in _cache.items():
                    await ws.send_text(json.dumps({"type": event_type, "data": data}))
    except WebSocketDisconnect:
        pass
    except Exception as exc:  # noqa: BLE001
        logger.debug("dashboard_stream: ws error: %s", exc)
    finally:
        _manager.disconnect(ws)


# ---------------------------------------------------------------------------
# Standalone entry — uvicorn api.routes.dashboard_stream:app --port 4400
# ---------------------------------------------------------------------------

from fastapi.staticfiles import StaticFiles

from core.cluster.base_service import create_app

app = create_app(role="dashboard")
app.include_router(router)


@app.on_event("startup")
async def _startup() -> None:
    start_broadcast_loop()


_UI_DIR = Path(__file__).resolve().parents[2] / "ui" / "dashboard"
if _UI_DIR.exists():
    app.mount("/", StaticFiles(directory=str(_UI_DIR), html=True), name="dashboard-ui")

