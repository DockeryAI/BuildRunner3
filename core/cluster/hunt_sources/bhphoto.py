"""
BR3 Hunt Source — B&H Photo HTML Scrape + Below Extraction
Fetches B&H search results, sends to Below for structured extraction.
"""

import asyncio
import logging

from core.cluster.cluster_config import get_below_ollama_url, get_below_model
from core.cluster.utils import filter_hallucinations

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

BELOW_OLLAMA_URL = get_below_ollama_url()  # single source of truth — core/cluster/cluster_config.py
BELOW_MODEL = get_below_model()            # single source of truth — core/cluster/cluster_config.py
BH_SEARCH_URL = "https://www.bhphotovideo.com/c/search"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
RATE_LIMIT_DELAY = 2.0


async def _fetch_search_html(keywords: str, max_price: float = None) -> str:
    """Fetch B&H search results page HTML."""
    if not httpx:
        return ""
    params = {
        "q": keywords,
        "sts": "ta",  # search type
    }
    if max_price:
        params["pn"] = "0"
        params["px"] = str(int(max_price))

    headers = {
        "User-Agent": USER_AGENT,
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "Sec-Fetch-Dest": "document",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "same-origin",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Referer": "https://www.bhphotovideo.com/",
        "DNT": "1",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            # Hit homepage first to get session cookies (avoids 403 on direct search)
            try:
                await client.get("https://www.bhphotovideo.com/", headers={"User-Agent": USER_AGENT})
            except Exception:
                pass  # Best effort — search may still work without
            resp = await client.get(
                BH_SEARCH_URL,
                params=params,
                headers=headers,
            )
            resp.raise_for_status()
            html = resp.text
            if len(html) < 1000:
                logger.warning(f"B&H returned short response ({len(html)} chars) for '{keywords}'")
                return ""
            return html
    except Exception as e:
        logger.error(f"B&H search fetch failed for '{keywords}': {type(e).__name__}: {e}")
        return ""


async def _extract_listings_via_below(html: str, hunt_name: str) -> list[dict]:
    """Send HTML to Below's LLM for structured extraction."""
    if not httpx or not html:
        return []

    # Check Below reachability
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            health = await client.get(f"{BELOW_OLLAMA_URL}/api/tags")
            if health.status_code != 200:
                logger.warning("Below unreachable — skipping B&H extraction")
                return []
    except Exception:
        logger.warning("Below unreachable — skipping B&H extraction")
        return []

    import re as _re
    cleaned = _re.sub(r'<(script|style|nav|footer|header|noscript)[^>]*>.*?</\1>', '', html, flags=_re.DOTALL | _re.IGNORECASE)
    cleaned = _re.sub(r'<!--.*?-->', '', cleaned, flags=_re.DOTALL)
    cleaned = _re.sub(r'\s+', ' ', cleaned)
    if len(cleaned) > 20000:
        cleaned = cleaned[:20000]

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
                        "relevant": {"type": "boolean"},
                    },
                    "required": ["title", "price", "url", "in_stock", "relevant"],
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
                        {"role": "system", "content": f"Extract product listings from B&H Photo HTML as JSON. Only include listings that match the search intent: '{hunt_name}'. Mark accessories, cables, adapters, and unrelated products as relevant: false. Use null for missing fields."},
                        # Example 1: relevant product
                        {"role": "user", "content": "Extract: '<div class=\"product\">PNY NVLink Bridge 3-Slot for RTX A6000 $149.99 In Stock</div>'"},
                        {"role": "assistant", "content": '{"listings":[{"title":"PNY NVLink Bridge 3-Slot for RTX A6000","price":149.99,"condition":"New","seller":"B&H Photo","url":"","in_stock":true,"relevant":true}]}'},
                        # Example 2: irrelevant accessory
                        {"role": "user", "content": "Extract: '<div class=\"product\">NVLink Bridge Protective Cover $9.99 In Stock</div>'"},
                        {"role": "assistant", "content": '{"listings":[{"title":"NVLink Bridge Protective Cover","price":9.99,"condition":"New","seller":"B&H Photo","url":"","in_stock":true,"relevant":false}]}'},
                        # Example 3: empty
                        {"role": "user", "content": "Extract: '<div>No results</div>'"},
                        {"role": "assistant", "content": '{"listings":[]}'},
                        {"role": "user", "content": f"Extract product listings from this B&H Photo HTML. Only mark actual '{hunt_name}' products as relevant — not accessories, covers, cables, or unrelated items.\n\n{cleaned}"},
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
                start = text.find("[")
                end = text.rfind("]")
                if start == -1 or end == -1:
                    logger.warning(f"No JSON in Below response for B&H '{hunt_name}'")
                    return []
                listings = json.loads(text[start : end + 1])

            relevant = [l for l in listings if l.get("relevant", True)]
            filtered = len(listings) - len(relevant)
            if filtered:
                logger.info(f"Below filtered {filtered} irrelevant B&H items for '{hunt_name}'")

            # Hallucination guard: filter items lacking tech indicators
            relevant = filter_hallucinations(relevant, "B&H", hunt_name)

            logger.info(f"Below extracted {len(relevant)} relevant B&H listings for '{hunt_name}'")
            return relevant

    except Exception as e:
        logger.error(f"Below extraction failed for B&H '{hunt_name}': {e}")
        return []


async def search(hunt: dict, source_config: dict) -> list[dict]:
    """Search B&H Photo via HTML scrape + Below extraction."""
    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    await asyncio.sleep(RATE_LIMIT_DELAY)

    html = await _fetch_search_html(keywords, hunt.get("target_price"))
    if not html:
        return []

    listings = await _extract_listings_via_below(html, hunt.get("name", keywords))
    if not listings:
        return []

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
            "condition": listing.get("condition", "New"),
            "seller": "B&H Photo",
            "attributes": {
                "source": "bhphoto",
                "in_stock": listing.get("in_stock", True),
            },
        })

    logger.info(f"B&H Photo: {len(items)} items for '{hunt.get('name', keywords)}'")
    return items
