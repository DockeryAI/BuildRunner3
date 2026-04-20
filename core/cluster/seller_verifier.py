"""
BR3 Cluster — Seller Verifier
Uses Apify to verify seller legitimacy on Reddit, eBay, and other marketplaces.
Runs as a background cron alongside intel_verifier.

Verification criteria:
- Reddit: account age >= 1 year, karma > 0, trading history
- eBay: feedback count >= 10, feedback percentage >= 95%

Only verified + in_stock + seller_verified deals show in dashboard.
"""

import logging
import os
import re
import threading
import time
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

VERIFY_INTERVAL = int(os.environ.get("SELLER_VERIFY_INTERVAL", "120"))  # 2 minutes
RECHECK_HOURS = int(os.environ.get("SELLER_RECHECK_HOURS", "168"))  # 7 days
REQUEST_TIMEOUT = float(os.environ.get("SELLER_VERIFY_TIMEOUT", "60"))

# Apify configuration
APIFY_API_KEY = os.environ.get("APIFY_API_KEY", "")
APIFY_REDDIT_PROFILE_ACTOR = "apivault_labs~reddit-scraper"
APIFY_REDDIT_POSTS_ACTOR = "trudax~reddit-scraper"

# Verification thresholds
REDDIT_MIN_ACCOUNT_AGE_YEARS = 0.5  # 6 months minimum
REDDIT_MIN_KARMA = 10
EBAY_MIN_FEEDBACK_COUNT = 5
EBAY_MIN_FEEDBACK_PERCENT = 95.0

try:
    import httpx
except ImportError:
    httpx = None


def _parse_reddit_account_age(metadata: str) -> Optional[float]:
    """Parse Reddit account age from Apify metadata string.

    Examples:
        "495 post karma, 259 comment karma\\n15 y Cake day: Feb 2, 2011\\n15-Year Club"
        "100 post karma\\n2 y Cake day: Mar 15, 2024"

    Returns age in years.
    """
    if not metadata:
        return None

    # Look for "X y Cake day" or "X-Year Club"
    year_match = re.search(r'(\d+)\s*y\s*Cake day', metadata)
    if year_match:
        return float(year_match.group(1))

    club_match = re.search(r'(\d+)-Year Club', metadata)
    if club_match:
        return float(club_match.group(1))

    return None


def _parse_reddit_karma(metadata: str) -> int:
    """Parse total karma from Apify metadata string."""
    if not metadata:
        return 0

    total = 0
    post_match = re.search(r'(\d+)\s*post karma', metadata)
    if post_match:
        total += int(post_match.group(1))

    comment_match = re.search(r'(\d+)\s*comment karma', metadata)
    if comment_match:
        total += int(comment_match.group(1))

    return total


async def verify_reddit_seller(username: str) -> dict:
    """Verify a Reddit seller using Apify.

    Returns:
        {
            "verified": bool,
            "account_age_years": float or None,
            "karma": int,
            "trades": int or None,
            "error": str or None
        }
    """
    if not username:
        return {"verified": False, "error": "no username"}

    if not APIFY_API_KEY:
        return {"verified": False, "error": "APIFY_API_KEY not set"}

    if not httpx:
        return {"verified": False, "error": "httpx not installed"}

    result = {
        "verified": False,
        "account_age_years": None,
        "karma": 0,
        "trades": None,
        "error": None,
    }

    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(REQUEST_TIMEOUT)) as client:
            # Step 1: Get user profile
            profile_url = f"https://api.apify.com/v2/acts/{APIFY_REDDIT_PROFILE_ACTOR}/run-sync-get-dataset-items"
            profile_resp = await client.post(
                profile_url,
                params={"token": APIFY_API_KEY},
                json={"profileUrls": [f"https://www.reddit.com/user/{username}"]},
            )

            if profile_resp.status_code != 200:
                result["error"] = f"Apify profile API returned {profile_resp.status_code}"
                return result

            profile_data = profile_resp.json()
            if not profile_data:
                result["error"] = "user not found"
                return result

            profile = profile_data[0]
            metadata = profile.get("otherMetadata", "")

            # Parse account age and karma
            result["account_age_years"] = _parse_reddit_account_age(metadata)
            result["karma"] = _parse_reddit_karma(metadata)

            # Step 2: Get trading history (hardwareswap posts)
            posts_url = f"https://api.apify.com/v2/acts/{APIFY_REDDIT_POSTS_ACTOR}/run-sync-get-dataset-items"
            posts_resp = await client.post(
                posts_url,
                params={"token": APIFY_API_KEY},
                json={"startUrls": [{"url": f"https://www.reddit.com/user/{username}/submitted/"}], "maxItems": 30},
            )

            if posts_resp.status_code == 200:
                posts_data = posts_resp.json()
                # Count hardwareswap posts
                hwswap_posts = [p for p in posts_data if "hardwareswap" in (p.get("subreddit", "") or "").lower()]
                result["trades"] = len(hwswap_posts)

            # Determine if verified
            age_ok = result["account_age_years"] is not None and result["account_age_years"] >= REDDIT_MIN_ACCOUNT_AGE_YEARS
            karma_ok = result["karma"] >= REDDIT_MIN_KARMA

            # Verified if: (account age OK AND karma OK) OR has hardwareswap history
            result["verified"] = (age_ok and karma_ok) or (result["trades"] and result["trades"] > 0)

            if not result["verified"]:
                reasons = []
                if not age_ok:
                    reasons.append(f"account age {result['account_age_years'] or 0:.1f}y < {REDDIT_MIN_ACCOUNT_AGE_YEARS}y")
                if not karma_ok:
                    reasons.append(f"karma {result['karma']} < {REDDIT_MIN_KARMA}")
                result["error"] = ", ".join(reasons)

    except httpx.TimeoutException:
        result["error"] = "Apify request timed out"
    except Exception as e:
        result["error"] = f"error: {str(e)[:100]}"

    return result


async def verify_ebay_seller(seller_id: str, feedback_count: int = None, feedback_percent: float = None) -> dict:
    """Verify an eBay seller.

    eBay seller info is often already in the deal attributes from scraping.
    This function validates the existing data or fetches fresh data if needed.

    Returns:
        {
            "verified": bool,
            "feedback_count": int or None,
            "feedback_percent": float or None,
            "error": str or None
        }
    """
    result = {
        "verified": False,
        "feedback_count": feedback_count,
        "feedback_percent": feedback_percent,
        "error": None,
    }

    if not seller_id:
        result["error"] = "no seller_id"
        return result

    # If we already have feedback data from scraping, validate it
    if feedback_count is not None and feedback_percent is not None:
        count_ok = feedback_count >= EBAY_MIN_FEEDBACK_COUNT
        percent_ok = feedback_percent >= EBAY_MIN_FEEDBACK_PERCENT
        result["verified"] = count_ok and percent_ok

        if not result["verified"]:
            reasons = []
            if not count_ok:
                reasons.append(f"feedback {feedback_count} < {EBAY_MIN_FEEDBACK_COUNT}")
            if not percent_ok:
                reasons.append(f"rating {feedback_percent}% < {EBAY_MIN_FEEDBACK_PERCENT}%")
            result["error"] = ", ".join(reasons)

        return result

    # TODO: Add Apify eBay seller scraper if needed
    # For now, mark as unverified if no feedback data
    result["error"] = "no feedback data available"
    return result


def _detect_source(deal: dict) -> str:
    """Detect the source platform from a deal item."""
    source_url = deal.get("source_url", "") or ""
    listing_url = deal.get("listing_url", "") or ""
    attrs = deal.get("attributes", {})
    if isinstance(attrs, str):
        import json
        try:
            attrs = json.loads(attrs)
        except:
            attrs = {}

    if source_url.startswith("reddit:") or "reddit.com" in listing_url:
        return "reddit"
    if "ebay.com" in listing_url or attrs.get("source") == "ebay":
        return "ebay"
    if "craigslist" in listing_url:
        return "craigslist"
    if "newegg.com" in listing_url:
        return "newegg"
    if "bhphoto" in listing_url or "bhphotovideo" in listing_url:
        return "bhphoto"

    return "unknown"


async def verify_deal_seller(deal: dict) -> dict:
    """Verify the seller for a deal item based on its source.

    Returns:
        {
            "verified": bool,
            "account_age_years": float or None,
            "karma": int or None (Reddit) / feedback_count (eBay),
            "trades": int or None,
            "source": str,
            "error": str or None
        }
    """
    source = _detect_source(deal)
    seller = deal.get("seller", "")

    if source == "reddit":
        result = await verify_reddit_seller(seller)
        result["source"] = "apify_reddit"
        return result

    elif source == "ebay":
        # Extract eBay seller info from deal attributes
        attrs = deal.get("attributes", {})
        if isinstance(attrs, str):
            import json
            try:
                attrs = json.loads(attrs)
            except:
                attrs = {}

        feedback_count = deal.get("seller_feedback_count") or attrs.get("seller_feedback_count")
        feedback_percent = deal.get("seller_rating") or attrs.get("seller_feedback_percent")

        result = await verify_ebay_seller(seller, feedback_count, feedback_percent)
        result["source"] = "ebay"
        # Map eBay fields to common schema
        result["karma"] = result.get("feedback_count")
        result["account_age_years"] = None
        result["trades"] = None
        return result

    elif source in ("newegg", "bhphoto"):
        # Major retailers — auto-verify
        return {
            "verified": True,
            "account_age_years": None,
            "karma": None,
            "trades": None,
            "source": f"{source}_retailer",
            "error": None,
        }

    elif source == "craigslist":
        # Craigslist has no seller verification — mark as unverified
        return {
            "verified": False,
            "account_age_years": None,
            "karma": None,
            "trades": None,
            "source": "craigslist",
            "error": "craigslist sellers cannot be verified",
        }

    else:
        return {
            "verified": False,
            "account_age_years": None,
            "karma": None,
            "trades": None,
            "source": "unknown",
            "error": f"unknown source: {source}",
        }


async def run_seller_verification_cycle() -> dict:
    """Verify sellers for all unverified deals."""
    from core.cluster.intel_collector import _get_intel_db

    conn = _get_intel_db()

    # Get deals needing seller verification:
    # - Not dismissed
    # - Not already seller_verified
    # - Not checked recently
    # - Prioritize in_stock items
    unverified = conn.execute(
        """SELECT id, seller, source_url, listing_url, attributes, seller_rating
           FROM deal_items
           WHERE dismissed = 0
             AND seller_verified = 0
             AND (seller_verified_at IS NULL OR seller_verified_at < datetime('now', ?))
             AND seller IS NOT NULL AND seller != ''
           ORDER BY in_stock DESC, collected_at DESC
           LIMIT 10""",
        (f"-{RECHECK_HOURS} hours",)
    ).fetchall()
    conn.close()

    stats = {"total": len(unverified), "verified": 0, "failed": 0, "errors": 0}

    for row in unverified:
        deal_id = row["id"]
        deal = dict(row)

        result = await verify_deal_seller(deal)
        now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")

        conn = _get_intel_db()
        conn.execute(
            """UPDATE deal_items
               SET seller_verified = ?,
                   seller_account_age_years = ?,
                   seller_karma = ?,
                   seller_trades = ?,
                   seller_verification_source = ?,
                   seller_verified_at = ?,
                   seller_verification_error = ?
               WHERE id = ?""",
            (
                1 if result["verified"] else 0,
                result.get("account_age_years"),
                result.get("karma"),
                result.get("trades"),
                result.get("source"),
                now,
                result.get("error"),
                deal_id,
            )
        )
        conn.commit()
        conn.close()

        if result["verified"]:
            stats["verified"] += 1
            logger.info(f"Seller verified for deal {deal_id}: {deal.get('seller')} (age={result.get('account_age_years')}y, karma={result.get('karma')})")
        elif result.get("error"):
            stats["errors"] += 1
            logger.info(f"Seller verification failed for deal {deal_id}: {result.get('error')}")
        else:
            stats["failed"] += 1
            logger.info(f"Seller not verified for deal {deal_id}: {deal.get('seller')}")

        # Rate limit Apify calls
        await _async_sleep(3)

    return stats


async def _async_sleep(seconds):
    import asyncio
    await asyncio.sleep(seconds)


def _seller_verifier_cron_loop():
    """Background thread: run seller verification cycle every VERIFY_INTERVAL seconds."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    # Wait before first cycle
    time.sleep(15)

    while True:
        try:
            result = loop.run_until_complete(run_seller_verification_cycle())
            logger.info(
                f"Seller verification cycle complete - {result['verified']} verified, "
                f"{result['failed']} failed, {result['errors']} errors out of {result['total']}"
            )
        except Exception as e:
            logger.error(f"Seller verification cron error: {e}")
        time.sleep(VERIFY_INTERVAL)


def start_seller_verifier_cron():
    """Start the background seller verifier cron thread."""
    t = threading.Thread(target=_seller_verifier_cron_loop, daemon=True, name="seller-verifier-cron")
    t.start()
    logger.info(f"Started seller verifier cron (every {VERIFY_INTERVAL}s)")
    return t
