"""
BR3 Cluster — Deal Link Verifier
Checks listing_url for each deal item: HTTP status, in-stock detection.
Runs as a background cron on Lockwood alongside scoring.

Only verified + in_stock deals are shown in the dashboard.
"""

import logging
import os
import re
import threading
import time
from datetime import datetime

logger = logging.getLogger(__name__)

VERIFY_INTERVAL = int(os.environ.get("VERIFY_INTERVAL", "300"))  # 5 minutes
RECHECK_HOURS = int(os.environ.get("RECHECK_HOURS", "12"))  # re-verify after 12h
REQUEST_TIMEOUT = float(os.environ.get("VERIFY_TIMEOUT", "15"))

# Patterns that indicate an item is OUT of stock
OUT_OF_STOCK_PATTERNS = [
    r"This listing has ended",
    r"This listing was ended",
    r"No longer available",
    r"Item is no longer available",
    r"out of stock",
    r"sold out",
    r"currently unavailable",
    r"no items found",
    r"This item is currently not available",
    r"Bidding has ended on this item",
    r"This Buy It Now listing has ended",
    r"The item you selected is no longer available",
]
OUT_OF_STOCK_RE = re.compile("|".join(OUT_OF_STOCK_PATTERNS), re.IGNORECASE)

# Patterns that indicate an item IS in stock
IN_STOCK_PATTERNS = [
    r"Buy It Now",
    r"Add to cart",
    r"Buy it now",
    r"Place bid",
    r"Add to Cart",
    r"In Stock",
    r"in stock",
    r"Available",
    r"Buy now",
    r"Order now",
]
IN_STOCK_RE = re.compile("|".join(IN_STOCK_PATTERNS), re.IGNORECASE)


try:
    import httpx
except ImportError:
    httpx = None


async def verify_deal_link(listing_url: str) -> dict:
    """Check a single listing URL. Returns {status, in_stock, reason}."""
    if not listing_url:
        return {"status": 0, "in_stock": None, "reason": "no URL"}

    if not httpx:
        return {"status": 0, "in_stock": None, "reason": "httpx not installed"}

    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/125.0.0.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.5",
    }

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(REQUEST_TIMEOUT, connect=5.0),
            follow_redirects=True,
            max_redirects=5,
        ) as client:
            resp = await client.get(listing_url, headers=headers)
            status = resp.status_code

            if status == 404:
                return {"status": 404, "in_stock": 0, "reason": "listing not found (404)"}
            if status >= 500:
                return {"status": status, "in_stock": None, "reason": f"server error ({status})"}
            if status >= 400:
                return {"status": status, "in_stock": None, "reason": f"client error ({status})"}

            body = resp.text[:50000]  # only scan first 50KB

            if OUT_OF_STOCK_RE.search(body):
                return {"status": status, "in_stock": 0, "reason": "out of stock pattern detected"}

            if IN_STOCK_RE.search(body):
                return {"status": status, "in_stock": 1, "reason": "in stock pattern detected"}

            # Page loaded but couldn't determine stock — mark as unknown
            return {"status": status, "in_stock": None, "reason": "page loaded, stock status unclear"}

    except httpx.TimeoutException:
        return {"status": 0, "in_stock": None, "reason": "request timed out"}
    except Exception as e:
        return {"status": 0, "in_stock": None, "reason": f"error: {str(e)[:100]}"}


async def run_verification_cycle() -> dict:
    """Verify all unverified deals + recheck stale ones."""
    from core.cluster.intel_collector import _get_intel_db

    conn = _get_intel_db()

    # Get unverified deals + deals not checked in RECHECK_HOURS
    unverified = conn.execute(
        """SELECT id, listing_url FROM deal_items
           WHERE dismissed = 0
             AND (verified = 0 OR last_checked < datetime('now', ?))
           ORDER BY verified ASC, collected_at DESC
           LIMIT 20""",
        (f"-{RECHECK_HOURS} hours",)
    ).fetchall()
    conn.close()

    stats = {"total": len(unverified), "verified": 0, "in_stock": 0, "out_of_stock": 0, "errors": 0}

    for row in unverified:
        deal_id = row["id"]
        listing_url = row["listing_url"]

        result = await verify_deal_link(listing_url)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        conn = _get_intel_db()
        conn.execute(
            """UPDATE deal_items
               SET verified = 1, link_status = ?, in_stock = ?, last_checked = ?
               WHERE id = ?""",
            (result["status"], result["in_stock"], now, deal_id)
        )
        conn.commit()
        conn.close()

        if result["in_stock"] == 1:
            stats["in_stock"] += 1
            stats["verified"] += 1
        elif result["in_stock"] == 0:
            stats["out_of_stock"] += 1
            stats["verified"] += 1
        else:
            stats["errors"] += 1

        logger.info(f"Verified deal {deal_id}: status={result['status']} in_stock={result['in_stock']} — {result['reason']}")

        # Small delay between requests to avoid rate limiting
        await _async_sleep(2)

    return stats


async def _async_sleep(seconds):
    import asyncio
    await asyncio.sleep(seconds)


def _verifier_cron_loop():
    """Background thread: run verification cycle every VERIFY_INTERVAL seconds."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            result = loop.run_until_complete(run_verification_cycle())
            logger.info(
                f"Verification cycle complete — {result['verified']} verified, "
                f"{result['in_stock']} in stock, {result['out_of_stock']} out of stock, "
                f"{result['errors']} errors"
            )
        except Exception as e:
            logger.error(f"Verification cron error: {e}")
        time.sleep(VERIFY_INTERVAL)


def start_verifier_cron():
    """Start the background verifier cron thread."""
    t = threading.Thread(target=_verifier_cron_loop, daemon=True, name="deal-verifier-cron")
    t.start()
    logger.info(f"Started deal verifier cron (every {VERIFY_INTERVAL}s)")
    return t
