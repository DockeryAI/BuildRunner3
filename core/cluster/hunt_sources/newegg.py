"""
BR3 Hunt Source — Newegg HTML Scrape + Below Extraction
Fetches Newegg search results, sends product grid HTML to Below for structured extraction.
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

    if len(html) > 30000:
        html = html[:30000]

    prompt = f"""Extract product listings from this Newegg search results HTML.
Return a JSON array of objects with fields: title, price (float USD), condition ("New"/"Used"/"Refurbished"/"Open Box"), seller (default "Newegg"), url (https://www.newegg.com/...), in_stock (bool).
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

            # Try parsing as-is first (format:json should give clean output)
            try:
                parsed = json.loads(text)
                # Could be {"listings": [...]} or just [...]
                if isinstance(parsed, list):
                    listings = parsed
                elif isinstance(parsed, dict):
                    # Find the first list value
                    listings = next((v for v in parsed.values() if isinstance(v, list)), [])
                else:
                    listings = []
            except json.JSONDecodeError:
                # Fallback: extract array from text
                start = text.find("[")
                end = text.rfind("]")
                if start == -1 or end == -1:
                    logger.warning(f"No JSON array in Below response for Newegg '{hunt_name}'")
                    return []
                listings = json.loads(text[start : end + 1])

            logger.info(f"Below extracted {len(listings)} Newegg listings for '{hunt_name}'")
            return listings

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
