"""
BR3 Hunt Source — Crucial Direct Product Pages
Extracts price/availability from Crucial.com product pages via embedded JSON.
"""

import asyncio
import json
import logging
import re

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
RATE_LIMIT_DELAY = 2.0


async def _fetch_crucial_product(url: str) -> dict | None:
    """Fetch a Crucial product page and extract price/details from embedded JSON."""
    if not httpx:
        return None

    try:
        async with httpx.AsyncClient(timeout=15.0, follow_redirects=True) as client:
            resp = await client.get(url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                logger.warning(f"Crucial product fetch {url} returned {resp.status_code}")
                return None

            html = resp.text

            # Extract price from JSON-LD schema
            price = None
            title = None
            sku = None
            in_stock = True

            # Look for "price": "XXX.XX" pattern
            price_match = re.search(r'"price":\s*"(\d+\.?\d*)"', html)
            if price_match:
                try:
                    price = float(price_match.group(1))
                except (ValueError, TypeError):
                    pass

            # Look for title in page title or og:title (most reliable)
            # Format: "Crucial 64GB Kit (32GBx2) DDR5-5600 SODIMM | CT2K32G56C46S5 | crucial.com"
            title_match = re.search(r'<title>([^|<]+)', html)
            if title_match:
                title = title_match.group(1).strip()
            else:
                # Fallback to JSON title field
                title_match = re.search(r'"title":\s*"([^"]+)"', html)
                if title_match:
                    title = title_match.group(1)

            # Look for SKU
            sku_match = re.search(r'"sku":\s*"([^"]+)"', html)
            if sku_match:
                sku = sku_match.group(1)

            # Check buyable status
            buyable_match = re.search(r'"buyable":\s*"(true|false)"', html)
            if buyable_match:
                in_stock = buyable_match.group(1) == "true"

            if not title and not price:
                logger.warning(f"Could not extract product data from {url}")
                return None

            return {
                "title": title or f"Crucial Product ({sku or 'unknown'})",
                "price": price,
                "url": url,
                "sku": sku,
                "in_stock": in_stock,
                "store": "Crucial",
            }

    except Exception as e:
        logger.error(f"Crucial product fetch failed for {url}: {e}")
        return None


async def search(hunt: dict, source_config: dict) -> list[dict]:
    """Fetch Crucial products from direct URLs in source_urls."""
    items = []

    # Get source URLs from hunt
    source_urls = hunt.get("source_urls", "")
    if isinstance(source_urls, str):
        try:
            source_urls = json.loads(source_urls) if source_urls else []
        except Exception:
            source_urls = []

    # Filter to Crucial URLs
    crucial_urls = [u for u in source_urls if "crucial.com" in u]

    for url in crucial_urls:
        await asyncio.sleep(RATE_LIMIT_DELAY)
        product = await _fetch_crucial_product(url)

        if product:
            items.append({
                "hunt_id": hunt["id"],
                "name": product["title"],
                "category": hunt.get("category", ""),
                "source_url": url,
                "listing_url": url,
                "price": product.get("price"),
                "condition": "New",
                "seller": "Crucial",
                "attributes": {
                    "source": "crucial_direct",
                    "store": "Crucial",
                    "in_stock": product.get("in_stock", True),
                    "sku": product.get("sku", ""),
                },
            })

    logger.info(f"Crucial: {len(items)} items for '{hunt.get('name', '')}'")
    return items
