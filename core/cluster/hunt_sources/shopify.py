"""
BR3 Hunt Source — Shopify Store Search (Minisforum, Crucial)
Uses Shopify's search/suggest.json API — pure JSON, no LLM needed.
Works even when Below is offline.
"""

import asyncio
import logging

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# Shopify stores to search (only stores confirmed to use Shopify)
DEFAULT_STORES = [
    {"name": "Minisforum", "domain": "www.minisforum.com"},
]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
RATE_LIMIT_DELAY = 2.0


async def _search_store(domain: str, store_name: str, keywords: str,
                        limit: int = 10) -> list[dict]:
    """Search a Shopify store via suggest.json API."""
    if not httpx:
        return []

    url = f"https://{domain}/search/suggest.json"
    params = {
        "q": keywords,
        "resources[type]": "product",
        "resources[limit]": str(limit),
    }

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(
                url,
                params=params,
                headers={"User-Agent": USER_AGENT},
            )
            if resp.status_code != 200:
                logger.warning(f"Shopify {store_name} returned {resp.status_code}")
                return []

            data = resp.json()
            resources = data.get("resources", {})
            results = resources.get("results", {})
            products = results.get("products", [])

            listings = []
            for product in products:
                title = product.get("title", "")
                if not title:
                    continue

                # Extract price from variants or price field
                price = None
                price_str = product.get("price", "")
                if price_str:
                    try:
                        price = float(str(price_str).replace(",", ""))
                        # Shopify prices are sometimes in cents
                        if price > 10000:
                            price = price / 100.0
                    except (ValueError, TypeError):
                        pass

                handle = product.get("handle", "")
                product_url = f"https://{domain}/products/{handle}" if handle else ""

                available = product.get("available", True)
                image = product.get("image", product.get("featured_image", {}).get("url", ""))

                listings.append({
                    "title": title,
                    "price": price,
                    "url": product_url,
                    "in_stock": available,
                    "image": image,
                    "store": store_name,
                })

            logger.info(f"Shopify {store_name}: {len(listings)} products for '{keywords}'")
            return listings

    except Exception as e:
        logger.error(f"Shopify search failed for {store_name}: {e}")
        return []


async def search(hunt: dict, source_config: dict) -> list[dict]:
    """Search Shopify stores for items matching a hunt."""
    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    stores = source_config.get("stores", DEFAULT_STORES)
    items = []

    for store in stores:
        domain = store.get("domain", "")
        store_name = store.get("name", domain)
        if not domain:
            continue

        await asyncio.sleep(RATE_LIMIT_DELAY)

        listings = await _search_store(domain, store_name, keywords)

        for listing in listings:
            title = listing.get("title", "")
            url = listing.get("url", "")
            if not title:
                continue

            items.append({
                "hunt_id": hunt["id"],
                "name": title,
                "category": hunt.get("category", ""),
                "source_url": url,
                "listing_url": url,
                "price": listing.get("price"),
                "condition": "New",
                "seller": listing.get("store", store_name),
                "attributes": {
                    "source": "shopify",
                    "store": store_name,
                    "in_stock": listing.get("in_stock", True),
                    "image": listing.get("image", ""),
                },
            })

    logger.info(f"Shopify: {len(items)} total items for '{hunt.get('name', keywords)}'")
    return items
