"""
BR3 Hunt Source — eBay HTML Scrape + Below Extraction
Default adapter — works with zero API keys.
Fetches eBay search results HTML, sends to Below's qwen3:8b for structured extraction.
"""

import os
import logging
import hashlib
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

BELOW_OLLAMA_URL = os.environ.get("BELOW_OLLAMA_URL", "http://10.0.1.105:11434")
BELOW_MODEL = os.environ.get("BELOW_MODEL", "qwen3:8b")
EBAY_SEARCH_URL = "https://www.ebay.com/sch/i.html"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"


async def _fetch_search_html(keywords: str, max_price: Optional[float] = None) -> str:
    """Fetch eBay search results page HTML."""
    if not httpx:
        return ""
    params = {
        "_nkw": keywords,
        "_sop": "15",  # sort by price+shipping lowest
        "LH_BIN": "1",  # Buy It Now only
        "_ipg": "60",  # 60 results per page
    }
    if max_price:
        params["_udhi"] = str(max_price)

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                EBAY_SEARCH_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.error(f"eBay search fetch failed for '{keywords}': {e}")
        return ""


async def _extract_listings_via_below(html: str, hunt_name: str) -> list[dict]:
    """Send HTML to Below's LLM for structured extraction."""
    if not httpx or not html:
        return []

    # Truncate HTML to ~30k chars to fit in context
    if len(html) > 30000:
        html = html[:30000]

    prompt = f"""Extract product listings from this eBay search results HTML.
For each listing, return a JSON array of objects with these fields:
- title: product name
- price: numeric price (float, USD)
- condition: "New", "Used", "Refurbished", or "Open Box"
- seller: seller name
- url: listing URL (starts with https://www.ebay.com)
- in_stock: true/false

Only include real product listings, not ads or sponsored content.
Return ONLY a JSON array, no other text.

HTML:
{html}"""

    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            resp = await client.post(
                f"{BELOW_OLLAMA_URL}/api/generate",
                json={
                    "model": BELOW_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1},
                },
            )
            if resp.status_code != 200:
                logger.error(f"Below extraction failed: {resp.status_code}")
                return []

            data = resp.json()
            text = data.get("response", "")

            # Parse JSON from response
            import json
            # Find JSON array in response
            start = text.find("[")
            end = text.rfind("]")
            if start == -1 or end == -1:
                logger.warning(f"No JSON array found in Below response for '{hunt_name}'")
                return []

            listings = json.loads(text[start : end + 1])
            logger.info(f"Below extracted {len(listings)} listings for '{hunt_name}'")
            return listings

    except Exception as e:
        logger.error(f"Below extraction failed for '{hunt_name}': {e}")
        return []


async def search(hunt: dict, source_config: dict) -> list[dict]:
    """Search eBay via HTML scrape + Below extraction."""
    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    max_price = hunt.get("target_price")

    html = await _fetch_search_html(keywords, max_price)
    if not html:
        return []

    listings = await _extract_listings_via_below(html, hunt.get("name", keywords))
    if not listings:
        return []

    # Convert to deal item format
    items = []
    for listing in listings:
        title = listing.get("title", "")
        url = listing.get("url", "")
        if not title or not url:
            continue

        items.append({
            "hunt_id": hunt["id"],
            "name": title,
            "category": hunt.get("category", ""),
            "source_url": url,
            "listing_url": url,
            "price": listing.get("price"),
            "condition": listing.get("condition", "Unknown"),
            "seller": listing.get("seller", ""),
            "attributes": {
                "source": "ebay_scrape",
                "in_stock": listing.get("in_stock", True),
            },
        })

    logger.info(f"eBay scrape: {len(items)} items for '{hunt.get('name', keywords)}'")
    return items
