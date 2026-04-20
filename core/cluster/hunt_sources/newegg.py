"""
BR3 Hunt Source — Newegg HTML Scrape + Below Extraction
Fetches Newegg search results, sends product grid HTML to Below for structured extraction.
"""

import asyncio
import os
import logging

from core.cluster.utils import filter_hallucinations

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

BELOW_OLLAMA_URL = os.environ.get("BELOW_OLLAMA_URL", "http://10.0.1.105:11434")
BELOW_MODEL = os.environ.get("BELOW_MODEL", "qwen3:8b")
NEWEGG_SEARCH_URL = "https://www.newegg.com/p/pl"
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
RATE_LIMIT_DELAY = 2.0


async def _fetch_search_html(keywords: str, max_price: float = None) -> str:
    """Fetch Newegg search results page HTML."""
    if not httpx:
        return ""
    params = {"d": keywords, "Order": "1"}  # Order=1 = best match
    if max_price:
        params["LeftPriceRange"] = "0"
        params["RightPriceRange"] = str(int(max_price))

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(
                NEWEGG_SEARCH_URL,
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            resp.raise_for_status()
            return resp.text
    except Exception as e:
        logger.error(f"Newegg search fetch failed for '{keywords}': {e}")
        return ""


def _extract_listings_from_html(html: str) -> list[dict]:
    """Extract Newegg listings directly from HTML using regex."""
    import re
    listings = []

    # Newegg item cells
    item_blocks = re.findall(
        r'<div[^>]*class="[^"]*item-cell[^"]*"[^>]*>(.*?)</div>\s*</div>\s*</div>',
        html, re.DOTALL
    )
    if not item_blocks:
        # Try item-container pattern
        item_blocks = re.findall(
            r'<div[^>]*class="[^"]*item-container[^"]*"[^>]*>(.*?)</div>\s*</div>',
            html, re.DOTALL
        )

    for block in item_blocks:
        title_match = re.search(r'<a[^>]*class="[^"]*item-title[^"]*"[^>]*>(.*?)</a>', block, re.DOTALL)
        if not title_match:
            title_match = re.search(r'<a[^>]*title="([^"]+)"[^>]*class="[^"]*item-title', block)

        price_match = re.search(r'<li[^>]*class="[^"]*price-current[^"]*"[^>]*>.*?\$\s*<strong>([\d,]+)</strong><sup>\.([\d]{2})</sup>', block, re.DOTALL)
        link_match = re.search(r'<a[^>]*href="(https://www\.newegg\.com/[^"]*)"', block)

        if title_match and link_match:
            title = re.sub(r'<[^>]+>', '', title_match.group(1)).strip()
            if not title:
                continue
            price = None
            if price_match:
                try:
                    price = float(f"{price_match.group(1).replace(',', '')}.{price_match.group(2)}")
                except (ValueError, TypeError):
                    pass

            in_stock = "OUT OF STOCK" not in block.upper()
            if not in_stock:
                continue  # Skip out-of-stock items entirely

            listings.append({
                "title": title,
                "price": price,
                "url": link_match.group(1),
                "condition": "New",
                "seller": "Newegg",
                "in_stock": True,
            })

    return listings


async def _extract_listings_via_below(html: str, hunt_name: str) -> list[dict]:
    """Extract Newegg listings. Uses regex first, falls back to Below LLM."""
    if not html:
        return []

    # Try direct HTML parsing first
    listings = _extract_listings_from_html(html)
    if listings:
        logger.info(f"Extracted {len(listings)} Newegg listings from HTML for '{hunt_name}'")
        return listings

    # Fallback: send to Below LLM
    if not httpx:
        return []

    # Check Below reachability
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            health = await client.get(f"{BELOW_OLLAMA_URL}/api/tags")
            if health.status_code != 200:
                logger.warning("Below unreachable — skipping Newegg extraction")
                return []
    except Exception:
        logger.warning("Below unreachable — skipping Newegg extraction")
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
                        {"role": "system", "content": f"Extract product listings from Newegg HTML as JSON. Only include listings that match the search intent: '{hunt_name}'. Mark accessories, cables, adapters, and unrelated products as relevant: false. Use null for missing fields."},
                        # Example 1: relevant product
                        {"role": "user", "content": "Extract: '<a class=\"item-title\">Corsair RM1200x SHIFT 1200W 80+ Gold ATX Power Supply</a><strong>194</strong><sup>.99</sup>'"},
                        {"role": "assistant", "content": '{"listings":[{"title":"Corsair RM1200x SHIFT 1200W 80+ Gold ATX Power Supply","price":194.99,"condition":"New","seller":"Newegg","url":"","in_stock":true,"relevant":true}]}'},
                        # Example 2: irrelevant accessory
                        {"role": "user", "content": "Extract: '<a class=\"item-title\">Corsair Sleeved Cable Kit for RM Series</a><strong>29</strong><sup>.99</sup>'"},
                        {"role": "assistant", "content": '{"listings":[{"title":"Corsair Sleeved Cable Kit for RM Series","price":29.99,"condition":"New","seller":"Newegg","url":"","in_stock":true,"relevant":false}]}'},
                        # Example 3: empty page
                        {"role": "user", "content": "Extract: '<div>No results found</div>'"},
                        {"role": "assistant", "content": '{"listings":[]}'},
                        {"role": "user", "content": f"Extract product listings from this Newegg HTML. Only mark actual '{hunt_name}' products as relevant — not accessories, cables, or unrelated items.\n\n{cleaned}"},
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
                    logger.warning(f"No JSON in Below response for Newegg '{hunt_name}'")
                    return []
                listings = json.loads(text[start : end + 1])

            relevant = [l for l in listings if l.get("relevant", True)]
            filtered = len(listings) - len(relevant)
            if filtered:
                logger.info(f"Below filtered {filtered} irrelevant Newegg items for '{hunt_name}'")

            # Hallucination guard: filter items lacking tech indicators
            relevant = filter_hallucinations(relevant, "Newegg", hunt_name)

            logger.info(f"Below extracted {len(relevant)} relevant Newegg listings for '{hunt_name}'")
            return relevant

    except Exception as e:
        logger.error(f"Below extraction failed for Newegg '{hunt_name}': {e}")
        return []


async def search(hunt: dict, source_config: dict) -> list[dict]:
    """Search Newegg via HTML scrape + Below extraction."""
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
            "seller": listing.get("seller", "Newegg"),
            "attributes": {
                "source": "newegg",
                "in_stock": listing.get("in_stock", True),
            },
        })

    logger.info(f"Newegg: {len(items)} items for '{hunt.get('name', keywords)}'")
    return items
