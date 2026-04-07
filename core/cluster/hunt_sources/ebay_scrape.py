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
                logger.warning(f"eBay returned suspiciously short response ({len(html)} chars) for '{keywords}'")
                return ""
            return html
    except Exception as e:
        logger.error(f"eBay search fetch failed for '{keywords}': {type(e).__name__}: {e}")
        return ""


def _extract_listings_from_html(html: str) -> list[dict]:
    """Extract listings directly from eBay HTML using regex patterns.
    eBay embeds listing data in the HTML even though the page is JS-enhanced.
    """
    import re
    import json as _json

    listings = []

    # Method 1: Extract from srp-results JSON-LD or structured data
    # eBay includes item data in script tags
    json_ld_matches = re.findall(
        r'<script[^>]*type="application/ld\+json"[^>]*>(.*?)</script>',
        html, re.DOTALL
    )
    for match in json_ld_matches:
        try:
            data = _json.loads(match)
            if isinstance(data, dict) and data.get("@type") == "ItemList":
                for elem in data.get("itemListElement", []):
                    item = elem.get("item", elem)
                    offer = item.get("offers", {})
                    listings.append({
                        "title": item.get("name", ""),
                        "price": float(offer.get("price", 0)),
                        "url": item.get("url", ""),
                        "condition": "Unknown",
                        "seller": "",
                        "in_stock": offer.get("availability", "") != "OutOfStock",
                    })
        except Exception:
            continue

    if listings:
        return listings

    # Method 2: Parse s-item blocks (server-rendered listing cards)
    item_blocks = re.findall(
        r'<li[^>]*class="[^"]*s-item[^"]*"[^>]*>(.*?)</li>',
        html, re.DOTALL
    )
    for block in item_blocks:
        title_match = re.search(
            r'<(?:span|div)[^>]*class="[^"]*s-item__title[^"]*"[^>]*>.*?<span[^>]*>(.*?)</span>',
            block, re.DOTALL
        )
        price_match = re.search(
            r'<span[^>]*class="[^"]*s-item__price[^"]*"[^>]*>\s*\$\s*([\d,]+(?:\.\d{2})?)',
            block, re.DOTALL
        )
        link_match = re.search(r'<a[^>]*href="(https://www\.ebay\.com/itm/[^"?]*)', block)

        if title_match and link_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            if title.lower() in ("shop on ebay", "results matching fewer words", ""):
                continue
            price = None
            if price_match:
                try:
                    price = float(price_match.group(1).replace(",", ""))
                except (ValueError, TypeError):
                    pass

            # Condition
            cond_match = re.search(r'<span[^>]*class="[^"]*SECONDARY_INFO[^"]*"[^>]*>(.*?)</span>', block, re.DOTALL)
            condition = re.sub(r'<[^>]+>', '', cond_match.group(1)).strip() if cond_match else "Unknown"

            listings.append({
                "title": title,
                "price": price,
                "url": link_match.group(1),
                "condition": condition,
                "seller": "",
                "in_stock": True,
            })

    return listings


async def _extract_listings_via_below(html: str, hunt_name: str) -> list[dict]:
    """Extract listings from eBay HTML. Uses regex first, falls back to Below LLM."""
    if not html:
        return []

    # Try direct HTML parsing first (faster, no LLM needed)
    listings = _extract_listings_from_html(html)
    if listings:
        logger.info(f"Extracted {len(listings)} listings from HTML for '{hunt_name}'")
        return listings

    # Fallback: send to Below LLM via /api/chat with schema-constrained output
    if not httpx:
        return []

    import re as _re
    # Strip scripts, styles, nav, footer — reduce token count
    cleaned = _re.sub(r'<(script|style|nav|footer|header|noscript)[^>]*>.*?</\1>', '', html, flags=_re.DOTALL | _re.IGNORECASE)
    cleaned = _re.sub(r'<!--.*?-->', '', cleaned, flags=_re.DOTALL)
    cleaned = _re.sub(r'\s+', ' ', cleaned)
    if len(cleaned) > 20000:
        cleaned = cleaned[:20000]

    # JSON schema for grammar-constrained output (~99% compliance per /llm research)
    listing_schema = {
        "type": "object",
        "properties": {
            "listings": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "title": {"type": "string"},
                        "price": {"type": "number"},
                        "condition": {"type": "string"},
                        "seller": {"type": "string"},
                        "url": {"type": "string"},
                        "in_stock": {"type": "boolean"},
                    },
                    "required": ["title", "price", "url", "in_stock"],
                },
            }
        },
        "required": ["listings"],
    }

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{BELOW_OLLAMA_URL}/api/chat",
                json={
                    "model": BELOW_MODEL,
                    "stream": False,
                    "format": listing_schema,
                    "think": False,
                    "messages": [
                        {"role": "system", "content": "Extract product listings from HTML as JSON. Use null for missing fields. Return as JSON."},
                        {"role": "user", "content": "Extract: '<div class=\"s-item\"><span class=\"s-item__title\">EVGA RTX 3090 FTW3</span><span class=\"s-item__price\">$899.99</span></div>'"},
                        {"role": "assistant", "content": '{"listings":[{"title":"EVGA RTX 3090 FTW3","price":899.99,"condition":"Unknown","seller":"","url":"","in_stock":true}]}'},
                        {"role": "user", "content": "Extract: '<div>No items found</div>'"},
                        {"role": "assistant", "content": '{"listings":[]}'},
                        {"role": "user", "content": f"Extract product listings from this eBay HTML. Only real products, no ads.\n\n{cleaned}"},
                    ],
                    "options": {"temperature": 0.2, "num_ctx": 8192, "num_predict": 2048, "presence_penalty": 1.5},
                },
            )
            if resp.status_code != 200:
                logger.error(f"Below extraction failed: {resp.status_code}")
                return []

            import json
            text = resp.json().get("message", {}).get("content", "")

            try:
                parsed = json.loads(text)
                listings = parsed.get("listings", []) if isinstance(parsed, dict) else parsed if isinstance(parsed, list) else []
            except json.JSONDecodeError:
                # Fallback: try to find array
                start = text.find("[")
                end = text.rfind("]")
                if start == -1 or end == -1:
                    logger.warning(f"No JSON in Below response for '{hunt_name}'")
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
