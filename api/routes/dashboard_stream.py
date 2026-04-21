"""dashboard_stream.py — WebSocket broadcaster for Cluster Max Dashboard.

Runs as part of the dashboard service on port 4400.
WS path: /ws

Emits event types:
  node-health       — per-node CPU/RAM/task metrics + Jimmy-specific + Below VRAM
  overflow-reserve  — Lockwood / Lomax idle/warming/active/draining + event log
  storage-health    — /srv/jimmy/ directory usage + backup timestamps + offsite sync
  consensus         — recent adversarial review results
  feature-health    — 15 feature-health tiles from telemetry.db (Phase 6)
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
# Feature-health collector (Phase 6)
# Reads telemetry.db to produce tile status for all 15 feature-health tiles.
# All tiles resolve to green/yellow/red — never "unknown".
# ---------------------------------------------------------------------------

import sqlite3 as _sqlite3
from datetime import timedelta


def _fh_query_db(db_path: Path, sql: str, params: tuple = ()) -> list[dict[str, Any]]:
    """Query telemetry.db; return [] on any error."""
    try:
        conn = _sqlite3.connect(str(db_path))
        conn.row_factory = _sqlite3.Row
        try:
            cur = conn.execute(sql, params)
            return [dict(r) for r in cur.fetchall()]
        finally:
            conn.close()
    except Exception:  # noqa: BLE001
        return []


def _fh_count(db_path: Path, event_type: str, since_iso: str) -> int:
    rows = _fh_query_db(
        db_path,
        "SELECT COUNT(*) as n FROM events WHERE event_type=? AND timestamp>=?",
        (event_type, since_iso),
    )
    return rows[0]["n"] if rows else 0


def _collect_feature_health() -> dict[str, Any]:
    """Collect 15-tile feature-health state from telemetry.db + local status files."""
    now = datetime.now(timezone.utc)
    h1_ago = (now - timedelta(hours=1)).isoformat()
    h24_ago = (now - timedelta(hours=24)).isoformat()
    m5_ago = (now - timedelta(minutes=5)).isoformat()

    # Locate telemetry.db — check several candidates
    db_candidates = [
        Path(os.environ.get("BR3_PROJECT_ROOT", "")) / ".buildrunner" / "telemetry.db",
        Path.cwd() / ".buildrunner" / "telemetry.db",
        Path.home() / "Projects" / "BuildRunner3" / ".buildrunner" / "telemetry.db",
    ]
    db_path: Path | None = next((p for p in db_candidates if p.exists()), None)

    def _tile(idx: int, label: str, status: str, detail: str) -> dict[str, Any]:
        return {"tile": idx, "label": label, "status": status, "detail": detail}

    tiles: list[dict[str, Any]] = []

    # ── Tile 1: Role Matrix dispatch ─────────────────────────────────────────
    dispatches_1h = _fh_count(db_path, "runtime_dispatched", h1_ago) if db_path else 0
    tiles.append(_tile(1, "Role Matrix dispatch",
        "green" if dispatches_1h > 0 else "yellow",
        f"{dispatches_1h} dispatch(es) in last hour" if dispatches_1h > 0 else "no dispatches in last hour"))

    # ── Tile 2: RuntimeRegistry health ───────────────────────────────────────
    if db_path:
        rows = _fh_query_db(db_path,
            "SELECT success, COUNT(*) as n FROM events WHERE event_type='runtime_dispatched' AND timestamp>=? GROUP BY success",
            (h24_ago,))
        total = sum(r["n"] for r in rows)
        successes = sum(r["n"] for r in rows if r["success"])
        pct = (successes / total * 100) if total > 0 else 100
        tiles.append(_tile(2, "RuntimeRegistry health",
            "green" if pct >= 90 else "red",
            f"{pct:.0f}% success ({successes}/{total}) in 24h" if total > 0 else "no dispatches in 24h — yellow"))
        if total == 0:
            tiles[-1]["status"] = "yellow"
    else:
        tiles.append(_tile(2, "RuntimeRegistry health", "yellow", "telemetry.db not found"))

    # ── Tile 3: 3-way adversarial review ─────────────────────────────────────
    if db_path:
        rows = _fh_query_db(db_path,
            "SELECT metadata FROM events WHERE event_type='adversarial_review_ran' AND timestamp>=? ORDER BY timestamp DESC LIMIT 5",
            (h24_ago,))
        three_way_runs = 0
        for r in rows:
            try:
                import json as _json
                meta = _json.loads(r.get("metadata") or "{}")
                if meta.get("mode") == "3-way":
                    three_way_runs += 1
            except Exception:  # noqa: BLE001
                pass
        flag_on = os.environ.get("BR3_ADVERSARIAL_3WAY", "off").lower() == "on"
        if not flag_on:
            tiles.append(_tile(3, "3-way adversarial review", "yellow", "BR3_ADVERSARIAL_3WAY=off"))
        elif three_way_runs > 0:
            tiles.append(_tile(3, "3-way adversarial review", "green", f"{three_way_runs} 3-way run(s) in 24h"))
        else:
            tiles.append(_tile(3, "3-way adversarial review", "yellow", "flag on but no 3-way runs in 24h"))
    else:
        tiles.append(_tile(3, "3-way adversarial review", "yellow", "telemetry.db not found"))

    # ── Tile 4: Cache breakpoints ─────────────────────────────────────────────
    flag_cache = os.environ.get("BR3_CACHE_BREAKPOINTS", "off").lower() == "on"
    cache_hits_24h = _fh_count(db_path, "cache_hit", h24_ago) if db_path else 0
    if not flag_cache:
        tiles.append(_tile(4, "Cache breakpoints", "yellow", "BR3_CACHE_BREAKPOINTS=off"))
    elif cache_hits_24h > 0:
        tiles.append(_tile(4, "Cache breakpoints", "green", f"{cache_hits_24h} hit(s) in 24h"))
    else:
        tiles.append(_tile(4, "Cache breakpoints", "red", "flag on but zero hits in 24h"))

    # ── Tile 5: Codex bridge ──────────────────────────────────────────────────
    bundles_24h = _fh_count(db_path, "context_bundle_served", h24_ago) if db_path else 0
    dispatches_24h = _fh_count(db_path, "runtime_dispatched", h24_ago) if db_path else 0
    if dispatches_24h == 0:
        tiles.append(_tile(5, "Codex bridge", "yellow", "no Codex dispatches in 24h"))
    elif bundles_24h >= dispatches_24h:
        tiles.append(_tile(5, "Codex bridge", "green", f"{bundles_24h} bundle(s) for {dispatches_24h} dispatch(es)"))
    else:
        tiles.append(_tile(5, "Codex bridge", "red", f"only {bundles_24h} bundle(s) for {dispatches_24h} dispatch(es)"))

    # ── Tile 6: Auto-context Jimmy /retrieve ─────────────────────────────────
    jimmy_status_file = _JIMMY_SRV / "status" / "nodes" / "jimmy.json"
    jimmy_data = _safe_read_json(jimmy_status_file) if jimmy_status_file.exists() else {}
    if jimmy_data.get("online"):
        tiles.append(_tile(6, "Auto-context Jimmy /retrieve", "green", "Jimmy online"))
    else:
        tiles.append(_tile(6, "Auto-context Jimmy /retrieve", "yellow", "Jimmy status unknown — check /srv/jimmy/status/nodes/jimmy.json"))

    # ── Tile 7: Local routing Below ───────────────────────────────────────────
    below_status_file = _JIMMY_SRV / "status" / "nodes" / "below.json"
    below_data = _safe_read_json(below_status_file) if below_status_file.exists() else {}
    if below_data.get("online"):
        tiles.append(_tile(7, "Local routing Below", "green", "Below online"))
    else:
        tiles.append(_tile(7, "Local routing Below", "yellow", "no Below dispatches in 24h — check node status"))

    # ── Tile 8: Otis dispatch ─────────────────────────────────────────────────
    otis_status_file = _JIMMY_SRV / "status" / "nodes" / "otis.json"
    otis_data = _safe_read_json(otis_status_file) if otis_status_file.exists() else {}
    daemon_cfg = Path.home() / ".buildrunner" / "cluster-daemon-config.json"
    daemon_data = _safe_read_json(daemon_cfg) if daemon_cfg.exists() else {}
    if otis_data.get("online") and daemon_data.get("auto_dispatch"):
        tiles.append(_tile(8, "Otis dispatch", "green", "Otis online + daemon auto_dispatch=true"))
    elif daemon_data.get("auto_dispatch"):
        tiles.append(_tile(8, "Otis dispatch", "yellow", "daemon active but Otis status unknown"))
    else:
        tiles.append(_tile(8, "Otis dispatch", "yellow", "cluster daemon auto_dispatch not confirmed"))

    # ── Tile 9: Walter gate ───────────────────────────────────────────────────
    walter_status_file = _JIMMY_SRV / "status" / "nodes" / "walter.json"
    walter_data = _safe_read_json(walter_status_file) if walter_status_file.exists() else {}
    last_hb = walter_data.get("last_heartbeat")
    if last_hb:
        try:
            from datetime import datetime as _dt2
            hb_dt = _dt2.fromisoformat(last_hb.replace("Z", "+00:00"))
            age_s = (now - hb_dt).total_seconds()
            if age_s <= 300:
                tiles.append(_tile(9, "Walter gate", "green", f"heartbeat {int(age_s)}s ago"))
            else:
                tiles.append(_tile(9, "Walter gate", "red", f"stale {int(age_s)}s — >5min"))
        except Exception:  # noqa: BLE001
            tiles.append(_tile(9, "Walter gate", "yellow", "cannot parse Walter heartbeat"))
    else:
        tiles.append(_tile(9, "Walter gate", "yellow", "no Walter heartbeat found"))

    # ── Tile 10: Lomax shard ──────────────────────────────────────────────────
    reserve = _collect_overflow_reserve()
    lomax_state = reserve.get("nodes", {}).get("lomax", {}).get("state", "idle")
    if lomax_state in ("active", "warming"):
        tiles.append(_tile(10, "Lomax shard", "green", f"state={lomax_state}"))
    elif lomax_state == "idle":
        tiles.append(_tile(10, "Lomax shard", "yellow", "Lomax idle — shards fire when Walter queue >2"))
    else:
        tiles.append(_tile(10, "Lomax shard", "yellow", f"state={lomax_state}"))

    # ── Tile 11: Cluster daemon ───────────────────────────────────────────────
    daemon_plist = Path.home() / "Library" / "LaunchAgents" / "com.br3.cluster-daemon.plist"
    if daemon_plist.exists():
        tiles.append(_tile(11, "Cluster daemon", "green", "LaunchAgent plist present"))
    else:
        tiles.append(_tile(11, "Cluster daemon", "red", "LaunchAgent plist missing"))

    # ── Tile 12: Node matrix consulted ───────────────────────────────────────
    node_matrix = Path.home() / ".buildrunner" / "scripts" / "node-matrix.mjs"
    if node_matrix.exists():
        tiles.append(_tile(12, "Node matrix consulted", "green", "node-matrix.mjs present"))
    else:
        tiles.append(_tile(12, "Node matrix consulted", "yellow", "node-matrix.mjs not found — may use hardcoded path"))

    # ── Tile 13: Dispatch log writer ──────────────────────────────────────────
    decisions_log = Path.cwd() / ".buildrunner" / "decisions.log"
    if not decisions_log.exists():
        decisions_log = Path.home() / "Projects" / "BuildRunner3" / ".buildrunner" / "decisions.log"
    if decisions_log.exists():
        age_s = (now - datetime.fromtimestamp(decisions_log.stat().st_mtime, tz=timezone.utc)).total_seconds()
        if age_s <= 86400:
            tiles.append(_tile(13, "Dispatch log writer", "green", f"decisions.log updated {int(age_s/3600)}h ago"))
        else:
            tiles.append(_tile(13, "Dispatch log writer", "red", f"decisions.log stale {int(age_s/3600)}h — >24h"))
    else:
        tiles.append(_tile(13, "Dispatch log writer", "yellow", "decisions.log not found"))

    # ── Tile 14: Context bundle parity ───────────────────────────────────────
    if db_path:
        rows = _fh_query_db(db_path,
            "SELECT metadata FROM events WHERE event_type='context_bundle_served' AND timestamp>=? ORDER BY timestamp DESC LIMIT 20",
            (h24_ago,))
        # If any bundles served in 24h, consider parity green (Phase 12 ships parity; tile tracks delivery)
        if rows:
            tiles.append(_tile(14, "Context bundle parity", "green", f"{len(rows)} bundle(s) delivered in 24h"))
        else:
            tiles.append(_tile(14, "Context bundle parity", "yellow", "no context bundles delivered in 24h"))
    else:
        tiles.append(_tile(14, "Context bundle parity", "yellow", "telemetry.db not found"))

    # ── Tile 15: Adversarial review cap ──────────────────────────────────────
    if db_path:
        import json as _json2
        rows = _fh_query_db(db_path,
            "SELECT metadata FROM events WHERE event_type='adversarial_review_ran' AND timestamp>=? ORDER BY timestamp DESC LIMIT 50",
            (h24_ago,))
        exceeded = 0
        for r in rows:
            try:
                meta = _json2.loads(r.get("metadata") or "{}")
                if int(meta.get("review_round", 1)) > 1:
                    exceeded += 1
            except Exception:  # noqa: BLE001
                pass
        if exceeded > 0:
            tiles.append(_tile(15, "Adversarial review cap", "red", f"{exceeded} build(s) exceeded 1-round cap in 24h"))
        else:
            tiles.append(_tile(15, "Adversarial review cap", "green", "all reviews within 1-round cap"))
    else:
        tiles.append(_tile(15, "Adversarial review cap", "yellow", "telemetry.db not found"))

    return {"tiles": tiles, "collected_at": now.isoformat()}


# ---------------------------------------------------------------------------
# Broadcast loop
# ---------------------------------------------------------------------------

_INTERVALS: dict[str, float] = {
    "node-health":      5.0,
    "overflow-reserve": 10.0,
    "storage-health":   60.0,
    "consensus":        20.0,
    "feature-health":   15.0,
}

_COLLECTORS = {
    "node-health":      _collect_node_health,
    "overflow-reserve": _collect_overflow_reserve,
    "storage-health":   _collect_storage_health,
    "consensus":        _collect_consensus,
    "feature-health":   _collect_feature_health,
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

