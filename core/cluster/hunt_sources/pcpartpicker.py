"""
BR3 Hunt Source — PCPartPicker Price Scraper
Uses Playwright for price comparison across retailers.
Falls back to RSS if Playwright unavailable.
"""

import logging
import hashlib
import re
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

PCPP_BASE = "https://pcpartpicker.com"


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


async def _scrape_with_playwright(keywords: str, limit: int = 20) -> list[dict]:
    """Scrape PCPartPicker search results using Playwright."""
    try:
        from playwright.async_api import async_playwright
    except ImportError:
        logger.info("Playwright not available — skipping PCPartPicker scrape")
        return []

    results = []
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            search_url = f"{PCPP_BASE}/search/?q={keywords.replace(' ', '+')}"
            await page.goto(search_url, timeout=15000)

            # Wait for search results
            await page.wait_for_selector(".search-results__pageContent", timeout=5000)

            # Get product links from search results
            product_links = await page.query_selector_all(".search_results--link a")

            for link in product_links[:limit]:
                href = await link.get_attribute("href")
                text = await link.inner_text()
                if href and text:
                    results.append({
                        "title": text.strip(),
                        "url": f"{PCPP_BASE}{href}" if href.startswith("/") else href,
                    })

            # For each product, try to get price data
            enriched = []
            for result in results[:5]:  # Limit detail fetches
                try:
                    await page.goto(result["url"], timeout=10000)
                    price_el = await page.query_selector(".price--current")
                    if price_el:
                        price_text = await price_el.inner_text()
                        price_match = re.search(r'\$\s*([\d,]+(?:\.\d{2})?)', price_text)
                        if price_match:
                            result["price"] = float(price_match.group(1).replace(",", ""))

                    # Get retailer info
                    retailer_el = await page.query_selector(".product__retailer-name")
                    if retailer_el:
                        result["retailer"] = (await retailer_el.inner_text()).strip()

                    enriched.append(result)
                except Exception:
                    enriched.append(result)

            await browser.close()
            return enriched

    except Exception as e:
        logger.error(f"PCPartPicker Playwright scrape failed: {e}")
        return []


async def _search_html_fallback(keywords: str) -> list[dict]:
    """Fallback: scrape PCPartPicker search results page HTML."""
    if not httpx:
        return []

    results = []
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0 Safari/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    try:
        async with httpx.AsyncClient(
            timeout=15.0,
            follow_redirects=True,
            headers=headers,
        ) as client:
            search_url = f"{PCPP_BASE}/search/?q={keywords.replace(' ', '+')}"
            resp = await client.get(search_url)
            if resp.status_code != 200:
                logger.warning(f"PCPartPicker search returned {resp.status_code}")
                return []

            html = resp.text

            # Extract product entries from search results HTML
            # Each result has a link with class and product info
            import re as _re
            # Match product links: /product/xxx pattern with titles
            product_blocks = _re.findall(
                r'<a\s+href="(/product/[^"]+)"[^>]*>\s*([^<]+)</a>',
                html,
            )
            for href, title in product_blocks:
                title = title.strip()
                if not title or len(title) < 5:
                    continue
                results.append({
                    "title": title,
                    "url": f"{PCPP_BASE}{href}",
                })

            # Also try to find price info near products
            price_matches = _re.findall(
                r'href="(/product/[^"]+)".*?\$\s*([\d,]+(?:\.\d{2})?)',
                html,
                _re.DOTALL,
            )
            price_map = {}
            for href, price_str in price_matches:
                try:
                    price_map[f"{PCPP_BASE}{href}"] = float(price_str.replace(",", ""))
                except (ValueError, TypeError):
                    pass

            for r in results:
                if r["url"] in price_map:
                    r["price"] = price_map[r["url"]]

    except Exception as e:
        logger.warning(f"PCPartPicker search failed: {e}")

    return results


async def search(hunt: dict, config: dict) -> list[dict]:
    """Search PCPartPicker for items matching a hunt.

    Args:
        hunt: Hunt dict with keys: id, name, keywords, target_price, category
        config: Source config with optional keys: use_playwright (default True)

    Returns:
        List of deal item dicts ready for insert.
    """
    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    use_playwright = config.get("use_playwright", True)

    if use_playwright:
        raw_results = await _scrape_with_playwright(keywords)
    else:
        raw_results = []

    if not raw_results:
        raw_results = await _search_html_fallback(keywords)

    items = []
    for result in raw_results:
        listing_url = result.get("url", "")
        price = result.get("price")
        if price and isinstance(price, str):
            try:
                price = float(price.replace("$", "").replace(",", "").strip())
            except (ValueError, TypeError):
                price = None

        items.append({
            "hunt_id": hunt["id"],
            "name": result.get("title", ""),
            "category": hunt.get("category", "other"),
            "attributes": {
                "retailer": result.get("retailer", "PCPartPicker"),
                "source": "pcpartpicker",
            },
            "source_url": f"pcpp:{_url_hash(listing_url)}",
            "price": price,
            "condition": "New",
            "seller": result.get("retailer", "Various Retailers"),
            "seller_rating": None,
            "listing_url": listing_url,
        })

    logger.info(f"PCPartPicker search for '{keywords}' returned {len(items)} items")
    return items
