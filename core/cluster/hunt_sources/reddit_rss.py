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
    # Parse keywords: required terms and exclusions (prefixed with -)
    required = []
    excluded = []
    for kw in keywords.split():
        if kw.startswith("-"):
            excluded.append(kw[1:].lower())
        elif len(kw) >= 2:  # skip single-char noise
            required.append(kw.lower())

    # Identify the most distinctive terms for matching:
    # - Model numbers (contain digits): "3090", "1200w", "rm1200x", "ms-a2", "9955hx"
    # - Brand names (4+ chars, no digits): "evga", "corsair", "minisforum", "crucial"
    # At least one model-number term AND one brand/product term must match.
    model_terms = [t for t in required if any(c.isdigit() for c in t)]
    brand_terms = [t for t in required if not any(c.isdigit() for c in t) and len(t) >= 4]

    # Fallback: if no clear model/brand split, require 2+ of all terms
    core_terms = [t for t in required if len(t) >= 3 or t.isdigit()]
    if not core_terms:
        core_terms = required

    items = []

    for subreddit in subreddits:
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
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

                    # Skip [W] want-to-buy posts from hardwareswap
                    # These are people looking to buy, not sell
                    if subreddit == "hardwareswap":
                        # Format: [H] have [W] want — skip if our keywords are in the [W] section
                        w_idx = title_lower.find("[w]")
                        h_idx = title_lower.find("[h]")
                        if w_idx != -1 and h_idx != -1 and h_idx < w_idx:
                            # Keywords appear after [W] = this is a want post
                            after_w = title_lower[w_idx:]
                            before_w = title_lower[:w_idx]
                            core_in_want = sum(1 for ct in core_terms if ct in after_w)
                            core_in_have = sum(1 for ct in core_terms if ct in before_w)
                            if core_in_want > core_in_have:
                                continue

                    # Skip bundle/prebuilt posts — they contain component keywords
                    # but price is for the whole system, not the component
                    if re.match(r'\[(?:prebuilt|bundle|combo)\]', title_lower):
                        continue

                    # Smart matching: require model number + brand/product term
                    if model_terms and brand_terms:
                        has_model = any(mt in title_lower for mt in model_terms)
                        has_brand = any(bt in title_lower for bt in brand_terms)
                        if not (has_model and has_brand):
                            continue
                    else:
                        # Fallback: require at least 2 core terms (or all if fewer)
                        match_count = sum(1 for ct in core_terms if ct in title_lower)
                        min_required = min(2, len(core_terms))
                        if match_count < min_required:
                            continue

                    # None of the excluded terms may be present
                    if any(ex in title_lower for ex in excluded):
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


async def search_historical(hunt: dict, config: dict) -> list[dict]:
    """Search Reddit's JSON search API for historical price data (last 30 days).
    Different from the RSS feed — uses /search.json which returns more results
    and allows time filtering. Logs prices to market data.
    """
    if not httpx:
        logger.warning("httpx not installed — Reddit historical search unavailable")
        return []

    keywords = hunt.get("keywords", hunt.get("name", ""))
    if not keywords:
        return []

    subreddits = config.get("subreddits", DEFAULT_SUBREDDITS)
    prices_logged = 0

    for subreddit in subreddits:
        try:
            async with httpx.AsyncClient(
                timeout=10.0,
                headers={"User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"},
            ) as client:
                # Reddit search JSON API — last 30 days
                # Clean keywords for search: remove exclusion terms (-)
                search_terms = " ".join(
                    kw for kw in keywords.split() if not kw.startswith("-")
                )
                url = f"https://www.reddit.com/r/{subreddit}/search.json"
                params = {
                    "q": search_terms,
                    "restrict_sr": "on",
                    "sort": "new",
                    "t": "month",  # last 30 days
                    "limit": 100,
                }
                resp = await client.get(url, params=params)

                if resp.status_code == 429:
                    logger.warning(f"Reddit rate limit on r/{subreddit} search")
                    continue
                if resp.status_code != 200:
                    logger.warning(f"Reddit r/{subreddit} search returned {resp.status_code}")
                    continue

                data = resp.json()
                children = data.get("data", {}).get("children", [])

                target_price = hunt.get("target_price")
                price_ceiling = target_price * 3 if target_price else None
                price_floor = target_price * 0.1 if target_price else None

                for child in children:
                    post = child.get("data", {})
                    title = post.get("title", "")
                    if not title:
                        continue

                    # Skip bundle/prebuilt posts
                    title_lower = title.lower()
                    if re.match(r'\[(?:prebuilt|bundle|combo)\]', title_lower):
                        continue

                    # Extract price from title
                    price = _extract_price(title)
                    if not price or price <= 0:
                        continue

                    # Skip prices that are clearly bundles (3x+ target) or accessories (< 10% target)
                    if price_ceiling and price > price_ceiling:
                        continue
                    if price_floor and price < price_floor:
                        continue

                    permalink = post.get("permalink", "")
                    post_url = f"https://www.reddit.com{permalink}" if permalink else ""

                    # Log to market data
                    try:
                        from core.cluster.intel_collector import log_market_price
                        # r/hardwareswap posts are completed sales (is_sold=1)
                        # r/buildapcsales are active deals (is_sold=0)
                        is_sold = 1 if subreddit == "hardwareswap" else 0
                        result = log_market_price(
                            hunt_id=hunt["id"],
                            price=price,
                            source=f"reddit/{subreddit}",
                            title=title,
                            url=post_url,
                            is_sold=is_sold,
                            condition=_extract_condition(title),
                        )
                        if result:
                            prices_logged += 1
                    except ImportError:
                        pass

        except Exception as e:
            logger.error(f"Reddit historical search failed for r/{subreddit}: {e}")

    logger.info(f"Reddit historical: logged {prices_logged} prices for '{keywords}'")
    return []  # Historical search only logs market data, doesn't return deal items
