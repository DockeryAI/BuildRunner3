"""
BR3 Cluster — Node: Lockwood Intelligence Service
FastAPI endpoints for intelligence collection and deal tracking.

Run: uvicorn core.cluster.node_intelligence:app --host 0.0.0.0 --port 8100
(Shares port with node_semantic — mount as sub-app or run separately)
"""

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
    """Initialize DB tables and start pollers if enabled. Called by node_semantic on startup."""
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

    if not DISABLE_SCORING:
        from core.cluster.intel_scoring import start_scoring_cron
        start_scoring_cron()
    else:
        logger.info("DISABLE_SCORING=true — skipping scoring cron")


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
    from core.cluster.intel_collector import get_intel_items as _get_items
    items = _get_items(
        priority=priority, category=category, source_type=source_type,
        read=read, limit=limit, days=days,
    )
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
    from core.cluster.intel_collector import get_improvements as _get_improvements
    items = _get_improvements(status=status, limit=limit)
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
    )
    return {"id": imp_id, "status": "created"}


@router.post("/api/intel/improvements/{improvement_id}/status")
async def update_improvement_status(improvement_id: int, body: ImprovementStatusUpdate):
    """Update improvement lifecycle status (pending -> planned -> built -> archived)."""
    from core.cluster.intel_collector import update_improvement_status as _update
    _update(improvement_id, body.status, body.build_spec_name)
    return {"status": "ok"}


# --- Deal Endpoints ---

@router.get("/api/deals/items")
async def get_deal_items(
    hunt_id: Optional[int] = None,
    min_score: Optional[int] = None,
    read: Optional[bool] = None,
    limit: int = 50,
):
    """Get deal items with filters."""
    from core.cluster.intel_collector import get_deal_items as _get_deals
    items = _get_deals(hunt_id=hunt_id, min_score=min_score, limit=limit)
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


@router.post("/api/deals/items/{item_id}/opus-review")
async def opus_review_deal(item_id: int, review: OpusDealReview):
    """Write Opus assessment back to a deal item."""
    from core.cluster.intel_collector import opus_review_deal_item
    opus_review_deal_item(item_id, review.opus_assessment)
    return {"status": "ok"}


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
