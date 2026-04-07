"""
BR3 Hunt Source — B&H Photo HTML Scrape + Below Extraction
Fetches B&H search results, sends to Below for structured extraction.
"""

import asyncio
import os
import logging

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

BELOW_OLLAMA_URL = os.environ.get("BELOW_OLLAMA_URL", "http://10.0.1.105:11434")
BELOW_MODEL = os.environ.get("BELOW_MODEL", "qwen3:8b")
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
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-User": "?1",
        "Upgrade-Insecure-Requests": "1",
        "Cache-Control": "max-age=0",
    }
    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
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

    if len(html) > 30000:
        html = html[:30000]

    prompt = f"""Extract product listings from this B&H Photo search results HTML.
Return a JSON array of objects with fields: title, price (float USD), condition ("New"/"Used"/"Refurbished"/"Open Box"), seller ("B&H Photo"), url (https://www.bhphotovideo.com/...), in_stock (bool).
Only real product listings, no ads. Return ONLY the JSON array.

HTML:
{html}"""

    try:
        async with httpx.AsyncClient(timeout=90.0) as client:
            resp = await client.post(
                f"{BELOW_OLLAMA_URL}/api/generate",
                json={
                    "model": BELOW_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "format": "json",
                    "options": {"temperature": 0.1, "num_ctx": 32768},
                },
            )
            if resp.status_code != 200:
                logger.error(f"Below extraction failed: {resp.status_code}")
                return []

            import json
            text = resp.json().get("response", "")

            try:
                parsed = json.loads(text)
                if isinstance(parsed, list):
                    listings = parsed
                elif isinstance(parsed, dict):
                    listings = next((v for v in parsed.values() if isinstance(v, list)), [])
                else:
                    listings = []
            except json.JSONDecodeError:
                start = text.find("[")
                end = text.rfind("]")
                if start == -1 or end == -1:
                    logger.warning(f"No JSON array in Below response for B&H '{hunt_name}'")
                    return []
                listings = json.loads(text[start : end + 1])

            logger.info(f"Below extracted {len(listings)} B&H listings for '{hunt_name}'")
            return listings

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
