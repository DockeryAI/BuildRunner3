"""Cluster metrics API routes — Phase 7.

Endpoints:
  GET /cluster/cost   — rolling 24h and 7d cost totals from the cost ledger
  GET /cluster/cache  — cache hit-rate per runtime over the last 7 days

Feature-gated: both endpoints return data regardless of BR3_GATEWAY flag
(the ledger is only written when the flag is on, so results will be empty
until Phase 13 cutover).
"""

from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cluster", tags=["cluster"])


# ---------------------------------------------------------------------------
# Response models
# ---------------------------------------------------------------------------


class CostWindow(BaseModel):
    """Cost summary for a single rolling time window."""

    window: str  # e.g. "24h" or "7d"
    total_cost_usd: float
    total_input_tokens: int
    total_output_tokens: int
    total_cache_read_tokens: int
    total_cache_write_tokens: int
    call_count: int


class CostResponse(BaseModel):
    """Response for GET /cluster/cost — two rolling windows."""

    last_24h: CostWindow
    last_7d: CostWindow
    generated_at: str  # ISO timestamp


class RuntimeCacheStats(BaseModel):
    """Cache statistics for a single runtime."""

    runtime: str
    cache_hit_rate: float  # 0.0–1.0  (cache_read_tokens / total_input_tokens)
    total_calls: int
    total_input_tokens: int
    total_cache_read_tokens: int


class CacheResponse(BaseModel):
    """Response for GET /cluster/cache — hit-rate per runtime."""

    window: str  # always "7d"
    runtimes: list[RuntimeCacheStats]
    overall_hit_rate: float
    generated_at: str  # ISO timestamp


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _get_ledger_records(days: int) -> list[dict[str, Any]]:
    """Fetch records from CostLedger for the last ``days`` days.

    Returns empty list if ledger is unavailable — callers handle gracefully.
    """
    try:
        from core.cluster.cost_ledger import CostLedger

        ledger = CostLedger()
        return ledger.read_window(days=days)
    except Exception as exc:  # noqa: BLE001
        logger.warning("cluster_metrics: ledger unavailable: %s", exc)
        return []


def _summarise_window(records: list[dict[str, Any]], window_label: str) -> CostWindow:
    """Aggregate raw JSONL records into a CostWindow summary."""
    total_cost = 0.0
    total_in = 0
    total_out = 0
    total_cr = 0
    total_cw = 0

    for rec in records:
        total_cost += float(rec.get("cost_usd", 0.0))
        total_in += int(rec.get("input_tokens", 0))
        total_out += int(rec.get("output_tokens", 0))
        total_cr += int(rec.get("cache_read_tokens", 0))
        total_cw += int(rec.get("cache_write_tokens", 0))

    return CostWindow(
        window=window_label,
        total_cost_usd=round(total_cost, 6),
        total_input_tokens=total_in,
        total_output_tokens=total_out,
        total_cache_read_tokens=total_cr,
        total_cache_write_tokens=total_cw,
        call_count=len(records),
    )


def _filter_by_hours(records: list[dict[str, Any]], hours: int) -> list[dict[str, Any]]:
    """Filter records to those within the last ``hours`` hours."""
    cutoff = datetime.now(tz=timezone.utc) - timedelta(hours=hours)
    out = []
    for rec in records:
        try:
            ts = datetime.fromisoformat(rec["ts"])
            if ts >= cutoff:
                out.append(rec)
        except (KeyError, ValueError):
            continue
    return out


# ---------------------------------------------------------------------------
# Routes
# ---------------------------------------------------------------------------


@router.get("/cost", response_model=CostResponse, summary="Rolling 24h and 7d cost totals")
async def get_cluster_cost() -> CostResponse:
    """Return rolling cost totals from the Jimmy cost ledger.

    Both 24h and 7d windows are returned in a single call.  The ledger is
    written only when BR3_GATEWAY=on; before Phase 13 cutover, all totals
    will be zero.
    """
    try:
        records_7d = _get_ledger_records(days=7)
        records_24h = _filter_by_hours(records_7d, hours=24)

        return CostResponse(
            last_24h=_summarise_window(records_24h, "24h"),
            last_7d=_summarise_window(records_7d, "7d"),
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        )
    except Exception as exc:
        logger.exception("cluster_metrics /cost failed")
        raise HTTPException(status_code=500, detail=f"cost ledger error: {exc}") from exc


@router.get(
    "/cache",
    response_model=CacheResponse,
    summary="Cache hit-rate per runtime over the last 7 days",
)
async def get_cluster_cache() -> CacheResponse:
    """Return prompt-cache hit-rate broken down by runtime.

    Hit-rate = cache_read_tokens / max(input_tokens, 1) per runtime.
    Covers the last 7 days.
    """
    try:
        records = _get_ledger_records(days=7)

        # Aggregate per runtime
        per_runtime: dict[str, dict[str, int]] = {}
        for rec in records:
            rt = rec.get("runtime", "unknown")
            if rt not in per_runtime:
                per_runtime[rt] = {
                    "total_calls": 0,
                    "total_input_tokens": 0,
                    "total_cache_read_tokens": 0,
                }
            per_runtime[rt]["total_calls"] += 1
            per_runtime[rt]["total_input_tokens"] += int(rec.get("input_tokens", 0))
            per_runtime[rt]["total_cache_read_tokens"] += int(rec.get("cache_read_tokens", 0))

        runtime_stats: list[RuntimeCacheStats] = []
        for rt_name, stats in per_runtime.items():
            in_tokens = max(stats["total_input_tokens"], 1)
            hit_rate = stats["total_cache_read_tokens"] / in_tokens
            runtime_stats.append(
                RuntimeCacheStats(
                    runtime=rt_name,
                    cache_hit_rate=round(hit_rate, 4),
                    total_calls=stats["total_calls"],
                    total_input_tokens=stats["total_input_tokens"],
                    total_cache_read_tokens=stats["total_cache_read_tokens"],
                )
            )

        # Overall hit rate across all runtimes
        all_in = sum(s.total_input_tokens for s in runtime_stats)
        all_cr = sum(s.total_cache_read_tokens for s in runtime_stats)
        overall_hit_rate = round(all_cr / max(all_in, 1), 4)

        return CacheResponse(
            window="7d",
            runtimes=runtime_stats,
            overall_hit_rate=overall_hit_rate,
            generated_at=datetime.now(tz=timezone.utc).isoformat(),
        )
    except Exception as exc:
        logger.exception("cluster_metrics /cache failed")
        raise HTTPException(status_code=500, detail=f"cache stats error: {exc}") from exc
