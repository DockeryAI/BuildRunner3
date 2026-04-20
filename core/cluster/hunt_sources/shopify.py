"""
BR3 Hunt Source — Shopify Store Search (Minisforum, Crucial)
Uses Shopify's search/suggest.json API + direct product.json fetch.
Works even when Below is offline.
"""

import asyncio
import logging
import re
from urllib.parse import urlparse

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# Shopify stores to search (only stores confirmed to use Shopify)
DEFAULT_STORES = [
    {"name": "Minisforum", "domain": "store.minisforum.com"},
]

USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36"
RATE_LIMIT_DELAY = 2.0


async def _fetch_product_direct(url: str, variant_filter: str | None = None) -> list[dict]:
    """Fetch a specific Shopify product via product.json and extract variants."""
    if not httpx:
        return []

    # Convert product URL to .json endpoint
    # https://store.minisforum.com/products/foo -> https://store.minisforum.com/products/foo.json
    parsed = urlparse(url)
    if "/products/" not in parsed.path:
        return []

    json_url = url.rstrip("/")
    if not json_url.endswith(".json"):
        json_url += ".json"

    try:
        async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
            resp = await client.get(json_url, headers={"User-Agent": USER_AGENT})
            if resp.status_code != 200:
                logger.warning(f"Shopify product fetch {json_url} returned {resp.status_code}")
                return []

            data = resp.json()
            product = data.get("product", {})
            title = product.get("title", "")
            variants = product.get("variants", [])
            handle = product.get("handle", "")

            listings = []
            for v in variants:
                variant_title = v.get("title", "")
                full_title = f"{title} - {variant_title}" if variant_title else title

                # Filter by variant name if specified
                if variant_filter and variant_filter.lower() not in full_title.lower():
                    continue

                price = None
                price_str = v.get("price", "")
                if price_str:
                    try:
                        price = float(str(price_str).replace(",", ""))
                    except (ValueError, TypeError):
                        pass

                # Check availability
                available = v.get("available", True)
                inventory = v.get("inventory_quantity")
                if inventory is not None:
                    available = inventory > 0

                variant_id = v.get("id", "")
                product_url = f"https://{parsed.netloc}/products/{handle}?variant={variant_id}" if variant_id else url

                listings.append({
                    "title": full_title,
                    "price": price,
                    "url": product_url,
                    "in_stock": available,
                    "sku": v.get("sku", ""),
                    "store": parsed.netloc,
                    "variant_id": variant_id,
                })

            logger.info(f"Shopify product {handle}: {len(listings)} variants" +
                       (f" matching '{variant_filter}'" if variant_filter else ""))
            return listings

    except Exception as e:
        logger.error(f"Shopify product fetch failed for {url}: {e}")
        return []


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
    """Search Shopify stores for items matching a hunt.

    If source_urls contain direct product URLs (*/products/*), fetch those directly.
    Otherwise, search stores by keywords.
    """
    keywords = hunt.get("keywords", hunt.get("name", ""))
    items = []

    # Check for direct product URLs in source_urls
    source_urls = hunt.get("source_urls", "")
    if isinstance(source_urls, str):
        try:
            import json
            source_urls = json.loads(source_urls) if source_urls else []
        except Exception:
            source_urls = []

    # Extract variant filter from requirements if present
    variant_filter = None
    requirements = hunt.get("requirements", "")
    if isinstance(requirements, str):
        try:
            import json
            requirements = json.loads(requirements) if requirements else {}
        except Exception:
            requirements = {}
    if isinstance(requirements, dict):
        notes = requirements.get("notes", [])
        # Look for variant hints in notes (e.g., "9955HX barebones")
        for note in notes:
            if isinstance(note, str):
                # Extract CPU model mentions
                match = re.search(r"(9955HX|9945HX|7945HX|7745HX|8945HX)", note, re.I)
                if match:
                    variant_filter = match.group(1)
                    break

    # Fetch direct product URLs
    direct_product_urls = [u for u in source_urls if "/products/" in u]
    for url in direct_product_urls:
        await asyncio.sleep(RATE_LIMIT_DELAY)
        listings = await _fetch_product_direct(url, variant_filter)

        for listing in listings:
            title = listing.get("title", "")
            listing_url = listing.get("url", url)
            if not title:
                continue

            items.append({
                "hunt_id": hunt["id"],
                "name": title,
                "category": hunt.get("category", ""),
                "source_url": url,
                "listing_url": listing_url,
                "price": listing.get("price"),
                "condition": "New",
                "seller": listing.get("store", "Shopify"),
                "attributes": {
                    "source": "shopify_direct",
                    "store": listing.get("store", ""),
                    "in_stock": listing.get("in_stock", True),
                    "sku": listing.get("sku", ""),
                    "variant_id": listing.get("variant_id", ""),
                },
            })

    # Also search stores by keywords if no direct URLs or keywords provided
    if not direct_product_urls and keywords:
        stores = source_config.get("stores", DEFAULT_STORES)

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
