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
    r"Listing Ended",
    r"item has ended",
    r"listing ended",
]
OUT_OF_STOCK_RE = re.compile("|".join(OUT_OF_STOCK_PATTERNS), re.IGNORECASE)

# Patterns that indicate an item IS in stock (eBay-focused)
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
    r"In \d+ carts",          # eBay: "In 8 carts"
    r"buy-it-now",            # eBay button class
    r"d-atc-button",          # eBay add to cart button
    r'"buyItNowPrice"',       # eBay JSON data
    r'data-testid="x-bin-action"',  # eBay buy it now button
]
IN_STOCK_RE = re.compile("|".join(IN_STOCK_PATTERNS), re.IGNORECASE)

# Price extraction patterns (ordered by reliability)
PRICE_PATTERNS = [
    # eBay JSON-LD schema
    r'"priceCurrency"\s*:\s*"USD"\s*,\s*"price"\s*:\s*["\']?([\d,]+\.?\d*)',
    r'"price"\s*:\s*["\']?([\d,]+\.?\d*)\s*,\s*"priceCurrency"\s*:\s*"USD"',
    # eBay specific
    r'itemprop="price"\s+content="([\d,]+\.?\d*)"',
    r'"binPrice"\s*:\s*"?\$?([\d,]+\.?\d*)',
    r'"buyItNowPrice"\s*:\s*\{[^}]*"value"\s*:\s*"?([\d,]+\.?\d*)',
    # Generic USD patterns
    r'US\s*\$\s*([\d,]+\.?\d*)',
    r'\$\s*([\d,]+\.?\d*)\s*(?:each|ea|/ea)',
    # BIN price in eBay
    r'class="x-price-primary"[^>]*>.*?\$\s*([\d,]+\.?\d*)',
]


def _extract_price(body: str, url: str) -> float | None:
    """Extract current price from page HTML. Returns None if not found."""
    for pattern in PRICE_PATTERNS:
        match = re.search(pattern, body, re.IGNORECASE | re.DOTALL)
        if match:
            try:
                price_str = match.group(1).replace(",", "")
                price = float(price_str)
                # Sanity check: ignore prices that are likely wrong
                if 1.0 <= price <= 50000:
                    return price
            except (ValueError, IndexError):
                continue
    return None


try:
    import httpx
except ImportError:
    httpx = None


# eBay Browse API integration — avoids CAPTCHA by using authenticated API
EBAY_ITEM_ID_RE = re.compile(r"ebay\.com/itm/(?:[^/]+/)?(\d{10,14})")


def _extract_ebay_item_id(url: str) -> str | None:
    """Extract eBay item ID from listing URL."""
    match = EBAY_ITEM_ID_RE.search(url)
    return match.group(1) if match else None


async def _verify_ebay_via_api(item_id: str) -> dict:
    """Verify eBay listing via Browse API getItem endpoint. No CAPTCHA."""
    from core.cluster.hunt_sources.ebay_browse import _get_auth_token, EBAY_BROWSE_URL

    token = await _get_auth_token()
    if not token:
        return {"status": 0, "in_stock": None, "reason": "eBay API auth failed", "current_price": None}

    # Legacy item ID format: v1|{item_id}|0
    endpoint = f"{EBAY_BROWSE_URL}/item/v1|{item_id}|0"
    headers = {
        "Authorization": f"Bearer {token}",
        "X-EBAY-C-MARKETPLACE-ID": "EBAY_US",
        "Accept": "application/json",
    }

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            resp = await client.get(endpoint, headers=headers)

            if resp.status_code == 404:
                return {"status": 404, "in_stock": 0, "reason": "eBay item not found", "current_price": None}
            if resp.status_code >= 400:
                return {"status": resp.status_code, "in_stock": None, "reason": f"eBay API error ({resp.status_code})", "current_price": None}

            data = resp.json()

            # Extract price from API response
            price = None
            if "price" in data:
                try:
                    price = float(data["price"].get("value", 0))
                except (ValueError, TypeError):
                    pass

            # Check availability - field is estimatedAvailabilityStatus
            availability = data.get("estimatedAvailabilities", [{}])[0]
            avail_status = availability.get("estimatedAvailabilityStatus", "")

            # IN_STOCK, LIMITED_QUANTITY = in stock; OUT_OF_STOCK, SOLD_OUT = ended
            if avail_status in ("OUT_OF_STOCK", "SOLD_OUT"):
                return {"status": 200, "in_stock": 0, "reason": f"eBay API: {avail_status}", "current_price": price}

            if avail_status in ("IN_STOCK", "LIMITED_QUANTITY") or data.get("buyingOptions"):
                return {"status": 200, "in_stock": 1, "reason": f"eBay API: {avail_status or 'available'}", "current_price": price}

            return {"status": 200, "in_stock": None, "reason": "eBay API: status unclear", "current_price": price}

    except httpx.TimeoutException:
        return {"status": 0, "in_stock": None, "reason": "eBay API timeout", "current_price": None}
    except Exception as e:
        return {"status": 0, "in_stock": None, "reason": f"eBay API error: {str(e)[:80]}", "current_price": None}


async def verify_deal_link(listing_url: str) -> dict:
    """Check a single listing URL. Returns {status, in_stock, reason, current_price}."""
    if not listing_url:
        return {"status": 0, "in_stock": None, "reason": "no URL", "current_price": None}

    if not httpx:
        return {"status": 0, "in_stock": None, "reason": "httpx not installed", "current_price": None}

    # eBay: use Browse API to avoid CAPTCHA
    ebay_item_id = _extract_ebay_item_id(listing_url)
    if ebay_item_id:
        return await _verify_ebay_via_api(ebay_item_id)

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
                return {"status": 404, "in_stock": 0, "reason": "listing not found (404)", "current_price": None}
            if status >= 500:
                return {"status": status, "in_stock": None, "reason": f"server error ({status})", "current_price": None}
            if status >= 400:
                return {"status": status, "in_stock": None, "reason": f"client error ({status})", "current_price": None}

            body = resp.text[:50000]  # only scan first 50KB

            # Extract current price
            current_price = _extract_price(body, listing_url)

            if OUT_OF_STOCK_RE.search(body):
                return {"status": status, "in_stock": 0, "reason": "out of stock pattern detected", "current_price": current_price}

            if IN_STOCK_RE.search(body):
                return {"status": status, "in_stock": 1, "reason": "in stock pattern detected", "current_price": current_price}

            # Page loaded but couldn't determine stock — mark as unknown
            return {"status": status, "in_stock": None, "reason": "page loaded, stock status unclear", "current_price": current_price}

    except httpx.TimeoutException:
        return {"status": 0, "in_stock": None, "reason": "request timed out", "current_price": None}
    except Exception as e:
        return {"status": 0, "in_stock": None, "reason": f"error: {str(e)[:100]}", "current_price": None}


async def run_verification_cycle() -> dict:
    """Verify all unverified deals + recheck stale ones. Updates prices."""
    from core.cluster.intel_collector import _get_intel_db

    conn = _get_intel_db()

    # Get unverified deals + deals not checked in RECHECK_HOURS
    unverified = conn.execute(
        """SELECT id, listing_url, price FROM deal_items
           WHERE dismissed = 0
             AND (verified = 0 OR last_checked < datetime('now', ?))
           ORDER BY verified ASC, collected_at DESC
           LIMIT 20""",
        (f"-{RECHECK_HOURS} hours",)
    ).fetchall()
    conn.close()

    stats = {"total": len(unverified), "verified": 0, "in_stock": 0, "out_of_stock": 0, "errors": 0, "price_updates": 0}

    for row in unverified:
        deal_id = row["id"]
        listing_url = row["listing_url"]
        old_price = row["price"]

        result = await verify_deal_link(listing_url)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
        current_price = result.get("current_price")

        conn = _get_intel_db()

        # Update price if we got a new one and it changed
        if current_price is not None and old_price is not None:
            try:
                old_price_num = float(str(old_price).replace("$", "").replace(",", ""))
                if abs(current_price - old_price_num) > 0.01:
                    # Price changed — update it
                    conn.execute(
                        """UPDATE deal_items
                           SET verified = 1, link_status = ?, in_stock = ?, last_checked = ?,
                               price = ?, price_updated_at = ?
                           WHERE id = ?""",
                        (result["status"], result["in_stock"], now,
                         current_price, now, deal_id)
                    )
                    stats["price_updates"] += 1
                    logger.info(f"Deal {deal_id} price updated: ${old_price_num:.2f} → ${current_price:.2f}")
                else:
                    conn.execute(
                        """UPDATE deal_items
                           SET verified = 1, link_status = ?, in_stock = ?, last_checked = ?
                           WHERE id = ?""",
                        (result["status"], result["in_stock"], now, deal_id)
                    )
            except (ValueError, TypeError):
                conn.execute(
                    """UPDATE deal_items
                       SET verified = 1, link_status = ?, in_stock = ?, last_checked = ?
                       WHERE id = ?""",
                    (result["status"], result["in_stock"], now, deal_id)
                )
        else:
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

        price_info = f" price=${current_price:.2f}" if current_price else ""
        logger.info(f"Verified deal {deal_id}: status={result['status']} in_stock={result['in_stock']}{price_info} — {result['reason']}")

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

    # Wait before first cycle so API is ready to serve
    time.sleep(10)
    while True:
        try:
            result = loop.run_until_complete(run_verification_cycle())
            logger.info(
                f"Verification cycle complete — {result['verified']} verified, "
                f"{result['in_stock']} in stock, {result['out_of_stock']} out of stock, "
                f"{result['errors']} errors, {result.get('price_updates', 0)} price updates"
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
