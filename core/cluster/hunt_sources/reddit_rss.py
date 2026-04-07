"""
BR3 Hunt Source — Reddit RSS
Parses r/buildapcsales and r/hardwareswap RSS feeds.
Free, no API key needed. Uses .rss endpoint.
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

DEFAULT_SUBREDDITS = [
    "buildapcsales",
    "hardwareswap",
]


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


def _extract_price(text: str) -> Optional[float]:
    """Extract price from Reddit post title/body. Returns first dollar amount found."""
    matches = re.findall(r'\$\s*([\d,]+(?:\.\d{2})?)', text)
    if matches:
        try:
            return float(matches[0].replace(",", ""))
        except (ValueError, TypeError):
            pass
    return None


def _extract_condition(text: str) -> str:
    """Guess condition from Reddit post text."""
    text_lower = text.lower()
    if any(w in text_lower for w in ["bnib", "brand new", "sealed", "nib"]):
        return "New"
    if any(w in text_lower for w in ["like new", "mint", "excellent"]):
        return "Used - Like New"
    if any(w in text_lower for w in ["good condition", "works great", "no issues"]):
        return "Used - Good"
    if "used" in text_lower:
        return "Used"
    return "Unknown"


def _parse_rss_xml(xml_text: str) -> list[dict]:
    """Parse Reddit RSS XML into entries. Minimal XML parsing without lxml."""
    entries = []
    # Split on <entry> tags (Atom feed)
    parts = xml_text.split("<entry>")[1:]  # skip header
    for part in parts:
        entry = {}
        # Title
        title_match = re.search(r"<title[^>]*>(.*?)</title>", part, re.DOTALL)
        if title_match:
            entry["title"] = title_match.group(1).strip()
            # Unescape HTML entities
            entry["title"] = entry["title"].replace("&amp;", "&").replace("&lt;", "<").replace("&gt;", ">").replace("&#39;", "'").replace("&quot;", '"')

        # Link
        link_match = re.search(r'<link[^>]*href="([^"]*)"', part)
        if link_match:
            entry["url"] = link_match.group(1)

        # Content
        content_match = re.search(r"<content[^>]*>(.*?)</content>", part, re.DOTALL)
        if content_match:
            entry["content"] = content_match.group(1).strip()

        # Author
        author_match = re.search(r"<name>(.*?)</name>", part)
        if author_match:
            entry["author"] = author_match.group(1).strip().lstrip("/u/")

        # Published
        published_match = re.search(r"<published>(.*?)</published>", part)
        if published_match:
            entry["published"] = published_match.group(1).strip()

        if entry.get("title"):
            entries.append(entry)

    return entries


async def search(hunt: dict, config: dict) -> list[dict]:
    """Search Reddit RSS feeds for items matching a hunt.

    Args:
        hunt: Hunt dict with keys: id, name, keywords, target_price, category
        config: Source config with optional keys: subreddits, limit

    Returns:
        List of deal item dicts ready for insert.
    """
    if not httpx:
        logger.warning("httpx not installed — Reddit source unavailable")
        return []

    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    subreddits = config.get("subreddits", DEFAULT_SUBREDDITS)
    limit = config.get("limit", 25)
    keyword_parts = [k.lower() for k in keywords.split()]
    items = []

    for subreddit in subreddits:
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "BR3-HuntSourcer/1.0"},
            ) as client:
                url = f"https://www.reddit.com/r/{subreddit}/new/.rss?limit={limit}"
                resp = await client.get(url)

                if resp.status_code == 429:
                    logger.warning(f"Reddit rate limit on r/{subreddit}")
                    continue
                if resp.status_code != 200:
                    logger.warning(f"Reddit r/{subreddit} returned {resp.status_code}")
                    continue

                entries = _parse_rss_xml(resp.text)

                for entry in entries:
                    title = entry.get("title", "")
                    title_lower = title.lower()

                    # Check if any keyword matches
                    if not any(kw in title_lower for kw in keyword_parts):
                        continue

                    content = entry.get("content", "")
                    combined_text = f"{title} {content}"
                    price = _extract_price(combined_text)
                    condition = _extract_condition(combined_text)
                    post_url = entry.get("url", "")

                    items.append({
                        "hunt_id": hunt["id"],
                        "name": title,
                        "category": hunt.get("category", "other"),
                        "attributes": {
                            "subreddit": subreddit,
                            "author": entry.get("author", ""),
                            "published": entry.get("published", ""),
                        },
                        "source_url": f"reddit:{_url_hash(post_url)}",
                        "price": price,
                        "condition": condition,
                        "seller": entry.get("author", ""),
                        "seller_rating": None,
                        "listing_url": post_url,
                    })

        except Exception as e:
            logger.error(f"Reddit RSS search failed for r/{subreddit}: {e}")

    logger.info(f"Reddit search for '{keywords}' returned {len(items)} items across {len(subreddits)} subreddits")
    return items
