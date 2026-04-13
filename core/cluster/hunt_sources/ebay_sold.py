"""
BR3 Hunt Source — eBay Completed/Sold Listings
Fetches historical sold prices from eBay for market data collection.
Uses LH_Sold=1&LH_Complete=1 parameters.
All entries are logged as market data with is_sold=1.
"""

import os
import logging
import re

from core.cluster.utils import url_hash

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

EBAY_SEARCH_URL = "https://www.ebay.com/sch/i.html"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"


async def _fetch_sold_html(keywords: str, max_price: float = None) -> str:
    """Fetch eBay completed/sold listings page HTML."""
    if not httpx:
        return ""
    params = {
        "_nkw": keywords,
        "_sop": "13",       # sort by end date recent first
        "LH_Sold": "1",     # sold items only
        "LH_Complete": "1",  # completed listings
        "_ipg": "60",
    }
    if max_price:
        params["_udhi"] = str(max_price)

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                EBAY_SEARCH_URL,
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            html = resp.text
            if len(html) < 1000:
                logger.warning(f"eBay sold returned short response ({len(html)} chars) for '{keywords}'")
                return ""
            return html
    except Exception as e:
        logger.error(f"eBay sold fetch failed for '{keywords}': {type(e).__name__}: {e}")
        return ""


def _extract_sold_listings(html: str) -> list[dict]:
    """Extract sold listing data from eBay completed listings HTML.
    Sold listings use a different price format — the sold price is shown with strikethrough original.
    """
    listings = []

    # eBay sold items use s-item blocks same as active listings
    item_blocks = re.findall(
        r'<li[^>]*class="[^"]*s-item[^"]*"[^>]*>(.*?)</li>',
        html, re.DOTALL
    )

    for block in item_blocks:
        # Title
        title_match = re.search(
            r'<(?:span|div)[^>]*class="[^"]*s-item__title[^"]*"[^>]*>.*?<span[^>]*>(.*?)</span>',
            block, re.DOTALL
        )
        if not title_match:
            continue
        title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
        if title.lower() in ("shop on ebay", "results matching fewer words", ""):
            continue

        # Sold price — eBay shows the actual sold price (may differ from listing price)
        # Look for the main price span
        price_match = re.search(
            r'<span[^>]*class="[^"]*s-item__price[^"]*"[^>]*>\s*\$\s*([\d,]+(?:\.\d{2})?)',
            block, re.DOTALL
        )
        price = None
        if price_match:
            try:
                price = float(price_match.group(1).replace(",", ""))
            except (ValueError, TypeError):
                pass

        if price is None:
            continue  # No price = useless for market data

        # Link
        link_match = re.search(r'<a[^>]*href="(https://www\.ebay\.com/itm/[^"?]*)', block)
        url = link_match.group(1) if link_match else ""

        # Condition
        cond_match = re.search(
            r'<span[^>]*class="[^"]*SECONDARY_INFO[^"]*"[^>]*>(.*?)</span>',
            block, re.DOTALL
        )
        condition = re.sub(r'<[^>]+>', '', cond_match.group(1)).strip() if cond_match else "Unknown"

        # Sold date (if present)
        date_match = re.search(r'Sold\s+(\w+\s+\d+,\s+\d{4})', block)
        sold_date = date_match.group(1) if date_match else None

        listings.append({
            "title": title,
            "price": price,
            "url": url,
            "condition": condition,
            "sold_date": sold_date,
        })

    return listings


async def search(hunt: dict, source_config: dict) -> list[dict]:
    """Search eBay completed/sold listings for market price data.
    Returns items formatted for the sourcer pipeline.
    All items are marked with is_sold=True in attributes for market logging.
    """
    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    max_price = hunt.get("target_price")
    # For sold listings, allow up to 2x target to capture full market range
    if max_price:
        max_price = max_price * 2

    html = await _fetch_sold_html(keywords, max_price)
    if not html:
        return []

    sold_listings = _extract_sold_listings(html)
    if not sold_listings:
        logger.info(f"eBay sold: no listings found for '{hunt.get('name', keywords)}'")
        return []

    # Filter out obvious non-products (accessories priced far below target)
    target_price = hunt.get("target_price")
    price_floor = target_price * 0.1 if target_price else 0
    if price_floor:
        before = len(sold_listings)
        sold_listings = [l for l in sold_listings if l.get("price", 0) >= price_floor]
        filtered = before - len(sold_listings)
        if filtered:
            logger.info(f"eBay sold: filtered {filtered} items below ${price_floor:.0f} floor for '{hunt.get('name', keywords)}'")

    # Log all sold prices directly to market data (these are confirmed transactions)
    try:
        from core.cluster.intel_collector import log_market_price
        logged = 0
        for listing in sold_listings:
            result = log_market_price(
                hunt_id=hunt["id"],
                price=listing["price"],
                source="ebay_sold",
                title=listing["title"],
                url=listing.get("url", ""),
                is_sold=1,
                condition=listing.get("condition"),
            )
            if result:
                logged += 1
        logger.info(f"eBay sold: logged {logged} sold prices for '{hunt.get('name', keywords)}'")
    except ImportError:
        logger.warning("log_market_price not available — sold data not logged")

    # Return items in standard deal format (they'll also go through normal pipeline)
    items = []
    for listing in sold_listings:
        title = listing.get("title", "")
        url = listing.get("url", "")
        if not title:
            continue

        items.append({
            "hunt_id": hunt["id"],
            "name": f"[SOLD] {title}",
            "category": hunt.get("category", ""),
            "source_url": f"ebay_sold:{url_hash(url or title)}",
            "listing_url": url,
            "price": listing.get("price"),
            "condition": listing.get("condition", "Unknown"),
            "seller": "",
            "attributes": {
                "source": "ebay_sold",
                "is_sold": True,
                "sold_date": listing.get("sold_date"),
                "in_stock": False,  # Sold items are not in stock
            },
        })

    logger.info(f"eBay sold: {len(items)} items for '{hunt.get('name', keywords)}'")
    return items
