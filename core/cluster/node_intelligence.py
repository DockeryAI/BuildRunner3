"""
BR3 Cluster — Node: Lockwood Intelligence Service
FastAPI endpoints for intelligence collection and deal tracking.

Run: uvicorn core.cluster.node_intelligence:app --host 0.0.0.0 --port 8100
(Shares port with node_semantic — mount as sub-app or run separately)
"""

import asyncio
import os
import hmac
import hashlib
import json
import logging
from typing import Optional

from fastapi import APIRouter, Request, HTTPException, Query
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# --- Config ---
MINIFLUX_WEBHOOK_SECRET = os.environ.get("MINIFLUX_WEBHOOK_SECRET", "")
DISABLE_POLLERS = os.environ.get("DISABLE_POLLERS", "true").lower() in ("true", "1", "yes")
DISABLE_SCORING = os.environ.get("DISABLE_SCORING", "true").lower() in ("true", "1", "yes")
DISABLE_VERIFIER = os.environ.get("DISABLE_VERIFIER", "false").lower() in ("true", "1", "yes")
DISABLE_SOURCER = os.environ.get("DISABLE_SOURCER", "false").lower() in ("true", "1", "yes")

# --- Router (included by node_semantic.py) ---
router = APIRouter()


# --- Pydantic Models ---

class HuntCreate(BaseModel):
    name: str
    category: str = "other"
    keywords: Optional[str] = None
    target_price: Optional[float] = None
    check_interval_minutes: int = 60
    source_urls: Optional[list] = None


class ImprovementCreate(BaseModel):
    title: str
    rationale: str
    complexity: str = "medium"  # simple/medium/complex
    setlist_prompt: str
    affected_files: Optional[list] = None
    source_intel_id: Optional[int] = None
    overlap_action: Optional[str] = None  # adopt/adapt/ignore
    overlap_notes: Optional[str] = None
    type: str = "fix"  # fix/upgrade/new_capability/new_skill/research


class AutoActLog(BaseModel):
    log: str


class ImprovementStatusUpdate(BaseModel):
    status: str  # pending/planned/built/archived
    build_spec_name: Optional[str] = None


class OpusIntelReview(BaseModel):
    opus_synthesis: str
    br3_improvement: bool = False


class OpusDealReview(BaseModel):
    opus_assessment: str


# --- Startup ---

async def intel_startup():
    """Initialize DB tables and start pollers if enabled. Called by node_semantic on startup.

    Crons are staggered to avoid overwhelming the M2's single-core SQLite I/O:
    - Pollers start immediately (lightweight RSS/webhook receivers)
    - Scoring starts after 30s (Below API calls, not I/O heavy)
    - Verifier starts after 60s (HTTP checks, moderate I/O)
    - Sourcer starts after 90s (heavy: external scrapes + SQLite writes)
    """
    import asyncio

    from core.cluster.intel_collector import _get_intel_db
    # Ensure tables exist on startup
    conn = _get_intel_db()
    conn.close()
    logger.info("Intel DB initialized")

    if not DISABLE_POLLERS:
        from core.cluster.intel_collector import start_pollers
        start_pollers()
    else:
        logger.info("DISABLE_POLLERS=true — skipping background pollers")

    # Stagger cron startups so they don't all hit SQLite simultaneously
    async def _deferred_crons():
        if not DISABLE_SCORING:
            await asyncio.sleep(30)
            from core.cluster.intel_scoring import start_scoring_cron
            start_scoring_cron()
        else:
            logger.info("DISABLE_SCORING=true — skipping scoring cron")

        if not DISABLE_VERIFIER:
            await asyncio.sleep(30)
            from core.cluster.intel_verifier import start_verifier_cron
            start_verifier_cron()
        else:
            logger.info("DISABLE_VERIFIER=true — skipping deal verifier cron")

        if not DISABLE_SOURCER:
            await asyncio.sleep(30)
            from core.cluster.hunt_sourcer import start_sourcer_cron
            start_sourcer_cron()
        else:
            logger.info("DISABLE_SOURCER=true — skipping hunt sourcer cron")

    asyncio.create_task(_deferred_crons())


# --- Manual Intel Submission ---

class IntelCreate(BaseModel):
    title: str
    source: str = "claude-code-collector"
    url: Optional[str] = None
    raw_content: Optional[str] = None
    source_type: str = "official"
    category: str = "ecosystem-news"
    priority: Optional[str] = None
    summary: Optional[str] = None


@router.post("/api/intel/items")
async def create_intel_endpoint(item: IntelCreate):
    """Create an intel item directly (used by Claude Code collector)."""
    from core.cluster.intel_collector import create_intel_item, _get_intel_db
    item_id = create_intel_item(
        title=item.title, source=item.source, url=item.url,
        raw_content=item.raw_content, source_type=item.source_type,
        category=item.category,
    )
    if item_id and (item.priority or item.summary):
        conn = _get_intel_db()
        updates = []
        params = []
        if item.priority:
            updates.append("priority = ?")
            params.append(item.priority)
            updates.append("scored = 1")
        if item.summary:
            updates.append("summary = ?")
            params.append(item.summary)
        params.append(item_id)
        conn.execute(f"UPDATE intel_items SET {', '.join(updates)} WHERE id = ?", params)
        conn.commit()
        conn.close()
    if item_id is None:
        return {"status": "duplicate", "id": None}
    return {"status": "created", "id": item_id}


# --- Intel Endpoints ---

@router.get("/api/intel/items")
async def get_intel_items(
    priority: Optional[str] = Query(None, description="Comma-separated: critical,high,medium,low"),
    category: Optional[str] = None,
    source_type: Optional[str] = None,
    read: Optional[bool] = None,
    limit: int = 50,
    days: Optional[int] = None,
):
    """Get intelligence items with filters."""
    from core.cluster.intel_collector import get_intel_items as _get_items, compute_tier
    items = _get_items(
        priority=priority, category=category, source_type=source_type,
        read=read, limit=limit, days=days,
    )
    for item in items:
        item["tier"] = compute_tier(item, kind="item")
    return {"items": items, "count": len(items)}


@router.get("/api/intel/alerts")
async def get_intel_alerts():
    """Get count of unread critical + high intel items."""
    from core.cluster.intel_collector import get_intel_alerts as _get_alerts
    return _get_alerts()


@router.post("/api/intel/items/{item_id}/read")
async def mark_read(item_id: int):
    """Mark an intel item as read."""
    from core.cluster.intel_collector import mark_intel_read
    mark_intel_read(item_id)
    return {"status": "ok"}


@router.post("/api/intel/items/{item_id}/dismiss")
async def dismiss_item(item_id: int):
    """Dismiss an intel item."""
    from core.cluster.intel_collector import dismiss_intel_item
    dismiss_intel_item(item_id)
    return {"status": "ok"}


@router.post("/api/intel/items/{item_id}/opus-review")
async def opus_review_intel(item_id: int, review: OpusIntelReview):
    """Write Opus synthesis back to an intel item."""
    from core.cluster.intel_collector import opus_review_intel_item
    opus_review_intel_item(
        item_id, review.opus_synthesis, review.br3_improvement
    )
    return {"status": "ok"}


# --- Improvement Endpoints ---

@router.get("/api/intel/improvements")
async def get_improvements(
    status: Optional[str] = Query(None, description="Comma-separated: pending,planned,built,archived"),
    limit: int = 50,
):
    """Get improvements filtered by status."""
    from core.cluster.intel_collector import get_improvements as _get_improvements, compute_tier
    items = _get_improvements(status=status, limit=limit)
    for item in items:
        item["tier"] = compute_tier(item, kind="improvement")
    return {"improvements": items, "count": len(items)}


@router.post("/api/intel/improvements")
async def create_improvement(improvement: ImprovementCreate):
    """Create a new improvement from intel-review Opus pass."""
    from core.cluster.intel_collector import create_improvement as _create
    imp_id = _create(
        title=improvement.title,
        rationale=improvement.rationale,
        complexity=improvement.complexity,
        setlist_prompt=improvement.setlist_prompt,
        affected_files=improvement.affected_files,
        source_intel_id=improvement.source_intel_id,
        overlap_action=improvement.overlap_action,
        overlap_notes=improvement.overlap_notes,
        type=improvement.type,
    )
    return {"id": imp_id, "status": "created"}


@router.post("/api/intel/improvements/{improvement_id}/status")
async def update_improvement_status(improvement_id: int, body: ImprovementStatusUpdate):
    """Update improvement lifecycle status (pending -> planned -> built -> archived)."""
    from core.cluster.intel_collector import update_improvement_status as _update
    _update(improvement_id, body.status, body.build_spec_name)
    return {"status": "ok"}


# --- Brief & Auto-Act Endpoints ---

@router.get("/api/intel/brief")
async def get_intel_brief():
    """Morning summary: auto-acted count, suggested count, new capabilities, awareness, last run."""
    from core.cluster.intel_collector import _get_intel_db, compute_tier, get_improvements
    conn = _get_intel_db()

    # Auto-acted count (improvements auto-fixed overnight)
    auto_acted_count = conn.execute(
        "SELECT COUNT(*) as cnt FROM intel_improvements WHERE auto_acted = 1"
    ).fetchone()["cnt"]

    # Get auto-act results for expandable detail
    auto_act_rows = conn.execute(
        "SELECT id, title, auto_act_log FROM intel_improvements WHERE auto_acted = 1 ORDER BY created_at DESC LIMIT 20"
    ).fetchall()
    auto_act_results = [dict(r) for r in auto_act_rows]

    # Get all pending/planned improvements to compute tier counts
    improvements = get_improvements(status="pending,planned", limit=500)
    suggested_count = 0
    new_capabilities_count = 0
    awareness_count = 0
    for imp in improvements:
        tier = compute_tier(imp, kind="improvement")
        if tier == 2:
            suggested_count += 1
        elif tier == 3:
            new_capabilities_count += 1
        elif tier == 4:
            awareness_count += 1

    # Last nightly run timestamp (most recent intel item collected)
    last_row = conn.execute(
        "SELECT collected_at FROM intel_items ORDER BY collected_at DESC LIMIT 1"
    ).fetchone()
    last_run = last_row["collected_at"] if last_row else None

    conn.close()
    return {
        "auto_acted_count": auto_acted_count,
        "suggested_count": suggested_count,
        "new_capabilities_count": new_capabilities_count,
        "awareness_count": awareness_count,
        "last_run": last_run,
        "auto_act_results": auto_act_results,
    }


@router.post("/api/intel/improvements/{improvement_id}/auto-act")
async def auto_act_improvement(improvement_id: int, body: AutoActLog):
    """Mark an improvement as auto-acted and store the execution log."""
    from core.cluster.intel_collector import mark_improvement_auto_acted
    success = mark_improvement_auto_acted(improvement_id, body.log)
    if not success:
        raise HTTPException(status_code=404, detail="Improvement not found")
    return {"status": "ok"}


# --- Deal Endpoints ---

@router.get("/api/deals/items")
async def get_deal_items(
    hunt_id: Optional[int] = None,
    min_score: Optional[int] = None,
    read: Optional[bool] = None,
    verified_only: Optional[bool] = None,
    in_stock_only: Optional[bool] = None,
    limit: int = 50,
):
    """Get deal items with filters."""
    from core.cluster.intel_collector import get_deal_items as _get_deals
    items = _get_deals(
        hunt_id=hunt_id, min_score=min_score, limit=limit,
        verified_only=verified_only, in_stock_only=in_stock_only,
    )
    return {"items": items, "count": len(items)}


@router.get("/api/deals/hunts")
async def get_hunts():
    """Get all active hunts."""
    from core.cluster.intel_collector import get_hunts as _get_hunts
    hunts = _get_hunts()
    return {"hunts": hunts}


@router.post("/api/deals/hunts")
async def create_hunt(hunt: HuntCreate):
    """Create a new hunt."""
    from core.cluster.intel_collector import create_hunt as _create_hunt
    hunt_id = _create_hunt(
        name=hunt.name, category=hunt.category, keywords=hunt.keywords,
        target_price=hunt.target_price,
        check_interval_minutes=hunt.check_interval_minutes,
        source_urls=hunt.source_urls,
    )
    return {"id": hunt_id, "status": "created"}


@router.post("/api/deals/hunts/{hunt_id}/archive")
async def archive_hunt(hunt_id: int):
    """Archive a hunt."""
    from core.cluster.intel_collector import archive_hunt as _archive
    _archive(hunt_id)
    return {"status": "archived"}


@router.get("/api/deals/price-history/{deal_item_id}")
async def get_price_history(deal_item_id: int):
    """Get price history for a deal item."""
    from core.cluster.intel_collector import get_price_history as _get_history
    history = _get_history(deal_item_id)
    return {"history": history, "count": len(history)}


@router.post("/api/deals/items/{item_id}/read")
async def mark_deal_read_endpoint(item_id: int):
    """Mark a deal item as read."""
    from core.cluster.intel_collector import mark_deal_read
    mark_deal_read(item_id)
    return {"status": "ok"}


@router.post("/api/deals/items/{item_id}/dismiss")
async def dismiss_deal_endpoint(item_id: int):
    """Dismiss a deal item."""
    from core.cluster.intel_collector import dismiss_deal_item
    dismiss_deal_item(item_id)
    return {"status": "ok"}


@router.post("/api/deals/verify")
async def trigger_verification():
    """Manually trigger a deal verification cycle."""
    from core.cluster.intel_verifier import run_verification_cycle
    result = await run_verification_cycle()
    return {"status": "ok", "result": result}


@router.post("/api/deals/items/{item_id}/verify")
async def verify_single_deal(item_id: int):
    """Verify a single deal item's link."""
    from core.cluster.intel_collector import _get_intel_db
    from core.cluster.intel_verifier import verify_deal_link
    from datetime import datetime

    conn = _get_intel_db()
    row = conn.execute("SELECT listing_url FROM deal_items WHERE id = ?", (item_id,)).fetchone()
    conn.close()
    if not row:
        raise HTTPException(status_code=404, detail="Deal not found")

    result = await verify_deal_link(row["listing_url"])
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

    conn = _get_intel_db()
    conn.execute(
        "UPDATE deal_items SET verified = 1, link_status = ?, in_stock = ?, last_checked = ? WHERE id = ?",
        (result["status"], result["in_stock"], now, item_id)
    )
    conn.commit()
    conn.close()

    return {"status": "ok", "link_status": result["status"], "in_stock": result["in_stock"], "reason": result["reason"]}


@router.post("/api/deals/items/{item_id}/opus-review")
async def opus_review_deal(item_id: int, review: OpusDealReview):
    """Write Opus assessment back to a deal item."""
    from core.cluster.intel_collector import opus_review_deal_item
    opus_review_deal_item(item_id, review.opus_assessment)
    return {"status": "ok"}


# --- Market Stats & Purchase Tracking Endpoints ---


class DealItemUpdate(BaseModel):
    purchased: Optional[int] = None
    purchased_price: Optional[float] = None
    notes: Optional[str] = None
    dismissed: Optional[int] = None
    deal_score: Optional[int] = None
    verdict: Optional[str] = None


@router.get("/api/deals/market/{hunt_id}")
async def get_market_stats(hunt_id: int, days: int = Query(90, description="Lookback window in days")):
    """Get market statistics for a hunt — median, percentiles, trend, sample count."""
    from core.cluster.intel_collector import get_market_stats as _get_stats
    stats = _get_stats(hunt_id, days=days)
    return stats


@router.patch("/api/deals/items/{item_id}")
async def update_deal_item_endpoint(item_id: int, body: DealItemUpdate):
    """Update a deal item — toggle purchased, set price, add notes."""
    from core.cluster.intel_collector import update_deal_item
    fields = {k: v for k, v in body.model_dump().items() if v is not None}
    if not fields:
        raise HTTPException(status_code=400, detail="No fields to update")
    success = update_deal_item(item_id, **fields)
    if not success:
        raise HTTPException(status_code=404, detail="Deal item not found")
    return {"status": "ok", "updated_fields": list(fields.keys())}


@router.get("/api/deals/summary")
async def get_deals_summary():
    """Per-hunt spend summary — budget (sum of target_price), spent (sum of purchased_price), counts."""
    from core.cluster.intel_collector import _get_intel_db
    conn = _get_intel_db()

    # Get per-hunt stats
    hunts = conn.execute(
        "SELECT id, name, category, target_price FROM active_hunts WHERE active = 1 ORDER BY id"
    ).fetchall()

    hunt_stats = []
    total_budget = 0
    total_spent = 0
    total_bought = 0
    total_deals = 0

    for hunt in hunts:
        hunt_id = hunt["id"]
        target = hunt["target_price"] or 0

        # Count deals and purchased for this hunt
        deal_row = conn.execute(
            """SELECT COUNT(*) as deal_count,
                      SUM(CASE WHEN purchased = 1 THEN 1 ELSE 0 END) as bought_count,
                      SUM(CASE WHEN purchased = 1 THEN purchased_price ELSE 0 END) as spent
               FROM deal_items WHERE hunt_id = ? AND dismissed = 0""",
            (hunt_id,)
        ).fetchone()

        # Market data count
        market_row = conn.execute(
            "SELECT COUNT(*) as cnt FROM price_history WHERE hunt_id = ?",
            (hunt_id,)
        ).fetchone()

        deal_count = deal_row["deal_count"] or 0
        bought_count = deal_row["bought_count"] or 0
        spent = deal_row["spent"] or 0

        hunt_stats.append({
            "hunt_id": hunt_id,
            "name": hunt["name"],
            "category": hunt["category"],
            "budget": target,
            "spent": round(spent, 2),
            "bought_count": bought_count,
            "deal_count": deal_count,
            "market_data_points": market_row["cnt"] or 0,
        })

        total_budget += target
        total_spent += spent
        total_bought += bought_count
        total_deals += deal_count

    conn.close()

    return {
        "hunts": hunt_stats,
        "totals": {
            "budget": round(total_budget, 2),
            "spent": round(total_spent, 2),
            "bought_count": total_bought,
            "deal_count": total_deals,
            "hunt_count": len(hunt_stats),
        },
    }


# --- Scoring Endpoints ---

@router.post("/api/intel/score")
async def trigger_scoring():
    """Manually trigger a scoring cycle (intel + deals via Below)."""
    from core.cluster.intel_scoring import run_scoring_cycle
    result = await run_scoring_cycle()
    return {"status": "ok", "result": result}


@router.get("/api/intel/scoring-status")
async def scoring_status():
    """Get scoring pipeline status — unscored counts and Below reachability."""
    from core.cluster.intel_collector import _get_intel_db
    conn = _get_intel_db()
    intel_unscored = conn.execute(
        "SELECT COUNT(*) as cnt FROM intel_items WHERE scored = 0"
    ).fetchone()["cnt"]
    deal_unscored = conn.execute(
        "SELECT COUNT(*) as cnt FROM deal_items WHERE deal_score IS NULL"
    ).fetchone()["cnt"]
    flagged_intel = conn.execute(
        "SELECT COUNT(*) as cnt FROM intel_items WHERE needs_opus_review = 1"
    ).fetchone()["cnt"]
    flagged_deals = conn.execute(
        "SELECT COUNT(*) as cnt FROM deal_items WHERE needs_opus_review = 1"
    ).fetchone()["cnt"]
    conn.close()
    return {
        "intel_unscored": intel_unscored,
        "deal_unscored": deal_unscored,
        "flagged_intel": flagged_intel,
        "flagged_deals": flagged_deals,
        "scoring_cron_enabled": not DISABLE_SCORING,
    }


# --- Webhook Endpoints ---

def _verify_hmac(request_body: bytes, signature: str, secret: str) -> bool:
    """Verify HMAC-SHA256 signature from Miniflux."""
    if not secret:
        return True  # No secret configured, skip verification
    expected = hmac.HMAC(
        secret.encode(), request_body, hashlib.sha256
    ).hexdigest()
    return hmac.compare_digest(expected, signature)


@router.post("/api/intel/webhook/miniflux")
async def webhook_miniflux(request: Request):
    """Receive Miniflux RSS webhook notifications.
    Verifies HMAC-SHA256 signature if MINIFLUX_WEBHOOK_SECRET is set.
    """
    body = await request.body()

    if MINIFLUX_WEBHOOK_SECRET:
        signature = request.headers.get("X-Miniflux-Signature", "")
        if not _verify_hmac(body, signature, MINIFLUX_WEBHOOK_SECRET):
            raise HTTPException(status_code=401, detail="Invalid signature")

    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from core.cluster.intel_collector import parse_miniflux_webhook
    items = parse_miniflux_webhook(payload)
    return {"status": "ok", "items_created": len(items), "items": items}


@router.post("/api/intel/webhook/newreleases")
async def webhook_newreleases(request: Request):
    """Receive NewReleases.io webhook notifications."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from core.cluster.intel_collector import parse_newreleases_webhook
    items = parse_newreleases_webhook(payload)
    return {"status": "ok", "items_created": len(items), "items": items}


@router.post("/api/intel/webhook/f5bot")
async def webhook_f5bot(request: Request):
    """Receive F5Bot keyword alert webhook."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from core.cluster.intel_collector import parse_f5bot_webhook
    items = parse_f5bot_webhook(payload)
    return {"status": "ok", "items_created": len(items), "items": items}


@router.post("/api/deals/webhook/changedetection")
async def webhook_changedetection(request: Request):
    """Receive changedetection.io webhook notifications."""
    try:
        payload = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    from core.cluster.intel_collector import parse_changedetection_webhook
    items = parse_changedetection_webhook(payload)
    return {"status": "ok", "items_created": len(items), "items": items}


_sourcer_task: Optional[asyncio.Task] = None


@router.post("/api/deals/source")
async def trigger_sourcer():
    """Manually trigger one sourcer check cycle. Fire-and-forget — returns immediately."""
    global _sourcer_task
    if _sourcer_task and not _sourcer_task.done():
        return {"status": "running", "message": "Sourcer cycle already in progress"}

    async def _run_sourcer():
        try:
            from core.cluster.hunt_sourcer import check_hunts_once, _last_checked
            _last_checked.clear()
            await check_hunts_once()
            logger.info("Manual sourcer cycle completed")
        except Exception as e:
            logger.error(f"Manual sourcer trigger failed: {e}")

    _sourcer_task = asyncio.create_task(_run_sourcer())
    return {"status": "started", "message": "Sourcer cycle started in background"}


@router.get("/api/deals/source/status")
async def sourcer_status():
    """Check if a sourcer cycle is currently running."""
    if _sourcer_task and not _sourcer_task.done():
        return {"status": "running"}
    return {"status": "idle"}
