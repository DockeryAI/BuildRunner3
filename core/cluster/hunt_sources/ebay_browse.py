"""
BR3 Hunt Source — eBay Browse API
Free tier: 5,000 calls/day. Searches active + sold/completed listings.
"""

import os
import logging
from typing import Optional
from datetime import datetime

from core.cluster.utils import url_hash

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# eBay Browse API (free tier)
EBAY_APP_ID = os.environ.get("EBAY_APP_ID", "")
EBAY_BROWSE_URL = "https://api.ebay.com/buy/browse/v1"
EBAY_AUTH_URL = "https://api.ebay.com/identity/v1/oauth2/token"
EBAY_SECRET = os.environ.get("EBAY_SECRET", "")

_token_cache = {"token": None, "expires": 0}


async def _get_auth_token() -> Optional[str]:
    """Get OAuth2 application token (client_credentials grant)."""
    if not EBAY_APP_ID or not EBAY_SECRET or not httpx:
        return None

    now = datetime.now().timestamp()
    if _token_cache["token"] and _token_cache["expires"] > now:
        return _token_cache["token"]

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.post(
                EBAY_AUTH_URL,
                data={"grant_type": "client_credentials", "scope": "https://api.ebay.com/oauth/api_scope"},
                auth=(EBAY_APP_ID, EBAY_SECRET),
                headers={"Content-Type": "application/x-www-form-urlencoded"},
            )
            resp.raise_for_status()
            data = resp.json()
            _token_cache["token"] = data["access_token"]
            _token_cache["expires"] = now + data.get("expires_in", 7200) - 60
            return _token_cache["token"]
    except Exception as e:
        logger.error(f"eBay auth failed: {e}")
        return None


# _url_hash moved to core.cluster.utils


async def search(hunt: dict, config: dict) -> list[dict]:
    """Search eBay Browse API for items matching a hunt.

    Args:
        hunt: Hunt dict with keys: id, name, keywords, target_price, category
        config: Source config with optional keys: marketplace_id, category_ids, condition_filter

    Returns:
        List of deal item dicts ready for insert via create_deal_item()
    """
    if not httpx:
        logger.warning("httpx not installed — eBay source unavailable")
        return []

    token = await _get_auth_token()
    if not token:
        logger.warning("eBay auth token unavailable — skipping")
        return []

    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    marketplace = config.get("marketplace_id", "EBAY_US")
    items = []

    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            headers = {
                "Authorization": f"Bearer {token}",
                "X-EBAY-C-MARKETPLACE-ID": marketplace,
            }

            params = {
                "q": keywords,
                "limit": config.get("limit", 50),
                "sort": "price",
            }

            # Condition filter (NEW, USED, etc.)
            condition = config.get("condition_filter")
            if condition:
                params["filter"] = f"conditionIds:{{{condition}}}"

            # Category filter
            category_ids = config.get("category_ids")
            if category_ids:
                if "filter" in params:
                    params["filter"] += f",categoryIds:{{{category_ids}}}"
                else:
                    params["filter"] = f"categoryIds:{{{category_ids}}}"

            resp = await client.get(
                f"{EBAY_BROWSE_URL}/item_summary/search",
                headers=headers,
                params=params,
            )

            if resp.status_code == 429:
                logger.warning("eBay rate limit hit — backing off")
                return []
            resp.raise_for_status()
            data = resp.json()

            for item in data.get("itemSummaries", []):
                price_val = None
                price_data = item.get("price", {})
                if price_data.get("value"):
                    try:
                        price_val = float(price_data["value"])
                    except (ValueError, TypeError):
                        pass

                seller_info = item.get("seller", {})
                seller_name = seller_info.get("username", "")
                seller_pct = seller_info.get("feedbackPercentage")
                seller_rating = None
                if seller_pct:
                    try:
                        seller_rating = float(seller_pct)
                    except (ValueError, TypeError):
                        pass

                condition_text = item.get("condition", "")
                listing_url = item.get("itemWebUrl", item.get("itemHref", ""))

                # eBay Browse API only returns active listings
                items.append({
                    "hunt_id": hunt["id"],
                    "name": item.get("title", ""),
                    "category": hunt.get("category", "other"),
                    "attributes": {
                        "ebay_item_id": item.get("itemId", ""),
                        "image_url": item.get("image", {}).get("imageUrl", ""),
                        "buying_options": item.get("buyingOptions", []),
                        "item_location": item.get("itemLocation", {}).get("country", ""),
                        "source": "ebay_browse",
                        "in_stock": True,  # Browse API only returns active listings
                    },
                    "source_url": f"ebay_browse:{url_hash(listing_url)}",
                    "price": price_val,
                    "condition": condition_text,
                    "seller": seller_name,
                    "seller_rating": seller_rating,
                    "listing_url": listing_url,
                })

    except Exception as e:
        logger.error(f"eBay Browse API search failed: {e}")

    logger.info(f"eBay search for '{keywords}' returned {len(items)} items")
    return items
