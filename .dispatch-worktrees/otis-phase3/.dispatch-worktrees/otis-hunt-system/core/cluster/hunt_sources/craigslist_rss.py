"""
BR3 Hunt Source — Craigslist RSS
Uses Craigslist's built-in RSS feed for search results.
Free, no API key. Configurable city.
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

DEFAULT_CITIES = ["sfbay", "losangeles", "seattle"]
DEFAULT_CATEGORY = "sss"  # For sale - all


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


def _extract_price_from_title(title: str) -> Optional[float]:
    """Extract price from Craigslist title (usually appended as $XXX)."""
    matches = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', title)
    if matches:
        try:
            return float(matches[0].replace(",", ""))
        except (ValueError, TypeError):
            pass
    return None


def _parse_rss_xml(xml_text: str) -> list[dict]:
    """Parse Craigslist RSS (RSS 2.0 format) into entries."""
    entries = []
    parts = xml_text.split("<item>")[1:]
    for part in parts:
        entry = {}
        title_match = re.search(r"<title>(.*?)</title>", part, re.DOTALL)
        if title_match:
            raw = title_match.group(1).strip()
            entry["title"] = raw.replace("<![CDATA[", "").replace("]]>", "").strip()

        link_match = re.search(r"<link>(.*?)</link>", part, re.DOTALL)
        if link_match:
            entry["url"] = link_match.group(1).strip()

        desc_match = re.search(r"<description>(.*?)</description>", part, re.DOTALL)
        if desc_match:
            entry["description"] = desc_match.group(1).strip()

        date_match = re.search(r"<dc:date>(.*?)</dc:date>", part)
        if not date_match:
            date_match = re.search(r"<pubDate>(.*?)</pubDate>", part)
        if date_match:
            entry["published"] = date_match.group(1).strip()

        if entry.get("title"):
            entries.append(entry)

    return entries


async def search(hunt: dict, config: dict) -> list[dict]:
    """Search Craigslist RSS feeds for items matching a hunt.

    Args:
        hunt: Hunt dict with keys: id, name, keywords, target_price, category
        config: Source config with optional keys: cities, cl_category

    Returns:
        List of deal item dicts ready for insert.
    """
    if not httpx:
        logger.warning("httpx not installed — Craigslist source unavailable")
        return []

    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    cities = config.get("cities", DEFAULT_CITIES)
    cl_category = config.get("cl_category", DEFAULT_CATEGORY)
    keyword_parts = [k.lower() for k in keywords.split()]
    items = []

    for city in cities:
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "BR3-HuntSourcer/1.0"},
            ) as client:
                search_query = "+".join(keywords.split())
                url = f"https://{city}.craigslist.org/search/{cl_category}?query={search_query}&format=rss"
                resp = await client.get(url)

                if resp.status_code != 200:
                    logger.warning(f"Craigslist {city} returned {resp.status_code}")
                    continue

                entries = _parse_rss_xml(resp.text)

                for entry in entries:
                    title = entry.get("title", "")
                    title_lower = title.lower()

                    # Keyword match
                    if not any(kw in title_lower for kw in keyword_parts):
                        continue

                    price = _extract_price_from_title(title)
                    post_url = entry.get("url", "")

                    items.append({
                        "hunt_id": hunt["id"],
                        "name": title,
                        "category": hunt.get("category", "other"),
                        "attributes": {
                            "city": city,
                            "cl_category": cl_category,
                            "published": entry.get("published", ""),
                        },
                        "source_url": f"craigslist:{_url_hash(post_url)}",
                        "price": price,
                        "condition": "Used",
                        "seller": f"craigslist/{city}",
                        "seller_rating": None,
                        "listing_url": post_url,
                    })

        except Exception as e:
            logger.error(f"Craigslist search failed for {city}: {e}")

    logger.info(f"Craigslist search for '{keywords}' returned {len(items)} items across {len(cities)} cities")
    return items
