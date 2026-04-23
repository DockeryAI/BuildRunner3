"""
BR3 Cluster — Hunt Sourcer Service (Walter)
Background service that polls deal sources on a schedule per hunt.
Feeds results into Lockwood, Below scores automatically.

Run: python -m core.cluster.hunt_sourcer
Deploy to Walter: scp + systemd service
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional

from core.cluster.cluster_config import get_jimmy_semantic_url, get_below_ollama_url, get_below_model
from core.cluster.utils import url_hash, last_checked_lock, cosine_similarity

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# --- Config ---
CONFIG_PATH = Path(__file__).parent / "hunt_sourcer_config.json"
JIMMY_URL = get_jimmy_semantic_url()        # single source of truth — core/cluster/cluster_config.py
BELOW_OLLAMA_URL = get_below_ollama_url()   # single source of truth — core/cluster/cluster_config.py
BELOW_MODEL = get_below_model()             # single source of truth — core/cluster/cluster_config.py
BELOW_EMBED_MODEL = os.environ.get("BELOW_EMBED_MODEL", "nomic-embed-text")
CHECK_HUNTS_INTERVAL = int(os.environ.get("CHECK_HUNTS_INTERVAL", "300"))  # 5min


def _load_config() -> dict:
    """Load sourcer configuration."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "sources": {
            "ebay_browse": {"enabled": True, "marketplace_id": "EBAY_US", "limit": 50},
            "reddit_rss": {"enabled": True, "subreddits": ["buildapcsales", "hardwareswap"]},
            "craigslist_rss": {"enabled": True, "cities": ["sfbay", "losangeles", "seattle"]},
            "pcpartpicker": {"enabled": True, "use_playwright": False},
            "newegg": {"enabled": True},
            "shopify": {"enabled": True, "stores": [
                {"name": "Minisforum", "domain": "www.minisforum.com"},
            ]},
            "bhphoto": {"enabled": True},
        },
        "dedup": {"url_hash": True, "title_similarity": True, "similarity_threshold": 0.85},
        "pair_detection": {"enabled": True, "same_seller_window_hours": 72},
    }


# _url_hash moved to core.cluster.utils


# --- Lockwood Client ---

async def _get_active_hunts() -> list[dict]:
    """Fetch active hunts from Lockwood API, fallback to local DB."""
    # Try Lockwood API first
    if httpx:
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{JIMMY_URL}/api/deals/hunts")
                resp.raise_for_status()
                hunts = resp.json().get("hunts", [])
                if hunts:
                    return hunts
        except Exception as e:
            logger.warning(f"Lockwood API unavailable ({e}), falling back to local DB")

    # Fallback: read directly from local SQLite
    try:
        from core.cluster.intel_collector import _get_intel_db
        conn = _get_intel_db()
        rows = conn.execute(
            "SELECT * FROM active_hunts WHERE active = 1 ORDER BY id"
        ).fetchall()
        conn.close()
        return [dict(row) for row in rows]
    except Exception as e:
        logger.error(f"Failed to fetch hunts from local DB: {e}")
        return []


async def _get_existing_deal_urls(hunt_id: int) -> set[str]:
    """Get set of existing source_url hashes for a hunt (for dedup)."""
    if not httpx:
        return set()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{JIMMY_URL}/api/deals/items",
                params={"hunt_id": hunt_id, "limit": 500},
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])
            return {item.get("source_url", "") for item in items}
    except Exception as e:
        logger.warning(f"Failed to fetch existing deals: {e}")
        return set()


async def _post_deal_item(item: dict) -> Optional[int]:
    """Post a new deal item to Lockwood. Returns item ID or None."""
    if not httpx:
        return None
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.post(
                f"{JIMMY_URL}/api/deals/items",
                json=item,
            )
            if resp.status_code in (200, 201):
                return resp.json().get("id")
            else:
                logger.warning(f"Post deal failed: {resp.status_code} {resp.text}")
                return None
    except Exception as e:
        logger.error(f"Failed to post deal item: {e}")
        return None


# --- Requirements Validation ---

def _validate_item(item: dict, requirements: dict, hunt_keywords: str = "") -> tuple[bool, str]:
    """Validate a deal item against hunt requirements.
    Returns (passed, reason). Reason is empty string if passed.
    Hard gates: relevance checks (wrong product, excluded terms, out of stock).
    """
    if not requirements:
        excluded = [kw[1:].lower() for kw in hunt_keywords.split() if kw.startswith("-")]
        name_lower = item.get("name", "").lower()
        if excluded and any(ex in name_lower for ex in excluded):
            return False, f"excluded term in title"
        return True, ""

    filters = requirements.get("filters", {})
    name_lower = item.get("name", "").lower()
    attrs = item.get("attributes", {})
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except (json.JSONDecodeError, TypeError):
            attrs = {}

    # In-stock check
    if filters.get("in_stock_only", True):
        if isinstance(attrs, dict) and attrs.get("in_stock") is False:
            return False, "out of stock"

    # Title must contain (AND — all must be present)
    must_contain = filters.get("title_must_contain", [])
    if must_contain:
        missing = [t for t in must_contain if t.lower() not in name_lower]
        if missing:
            return False, f"title missing required terms: {missing}"

    # Title must contain ANY (OR — at least one must be present)
    must_contain_any = filters.get("title_must_contain_any", [])
    if must_contain_any:
        if not any(t.lower() in name_lower for t in must_contain_any):
            return False, f"title missing any of: {must_contain_any}"

    # Title must NOT contain
    must_not_contain = filters.get("title_must_not_contain", [])
    if must_not_contain:
        for term in must_not_contain:
            if term.lower() in name_lower:
                return False, f"title contains excluded term: {term}"

    # Condition accept/reject
    condition = item.get("condition", "").lower()
    condition_accept = filters.get("condition_accept", [])
    if condition_accept and condition:
        if not any(c.lower() in condition for c in condition_accept):
            return False, f"condition '{condition}' not in accepted: {condition_accept}"

    condition_reject = filters.get("condition_reject", [])
    if condition_reject and condition:
        for c in condition_reject:
            if c.lower() in condition:
                return False, f"condition '{condition}' is rejected"

    # Domestic-only check (reject international sellers/locations)
    if filters.get("domestic_only", False):
        item_location = ""
        if isinstance(attrs, dict):
            item_location = (attrs.get("item_location", "") or "").lower()
        seller_location = (item.get("seller_location", "") or "").lower()
        location = item_location or seller_location
        if location and location not in ("us", "usa", "united states", ""):
            return False, f"international seller/location: {location}"

    # Min seller feedback count
    min_feedback = filters.get("min_seller_feedback")
    if min_feedback:
        feedback = item.get("seller_feedback_count") or (attrs.get("seller_feedback_count") if isinstance(attrs, dict) else None)
        if feedback is not None and feedback < min_feedback:
            return False, f"seller feedback {feedback} below minimum {min_feedback}"

    # Min seller rating percentage
    min_rating = filters.get("min_seller_rating")
    if min_rating:
        rating = item.get("seller_rating")
        if rating is not None and rating < min_rating:
            return False, f"seller rating {rating}% below minimum {min_rating}%"

    # Also check keyword-based exclusions as fallback
    excluded = [kw[1:].lower() for kw in hunt_keywords.split() if kw.startswith("-")]
    if excluded and any(ex in name_lower for ex in excluded):
        return False, f"keyword exclusion: matched excluded term"

    return True, ""


def _check_price_range(item: dict, requirements: dict) -> bool:
    """Check if item price falls within the hunt's target range.
    Returns True if in range (highlighted), False if outside.
    """
    if not requirements:
        return True
    filters = requirements.get("filters", {})
    price = item.get("price")
    if price is None:
        return False
    price_min = filters.get("price_min")
    price_max = filters.get("price_max")
    if price_min and price < price_min:
        return False
    if price_max and price > price_max:
        return False
    return True


# --- Batch Insert via Direct DB (Lockwood-local) or API ---

TOP_N_DEALS = 10  # Always insert top N cheapest relevant items per hunt


async def _batch_insert_deals(items: list[dict], hunt_id: int, requirements: dict = None, hunt_keywords: str = "") -> int:
    """Insert top N cheapest relevant deal items per hunt cycle.
    Relevance = passes hard gates (title match, excluded terms, stock).
    Price range is a soft flag (in_range), not a gate — items always insert.
    Returns count of new items inserted.
    """
    existing_urls = await _get_existing_deal_urls(hunt_id)
    new_count = 0
    skip_dup = 0
    skip_relevance = 0
    skip_insert = 0

    # Phase 1: filter to relevant items only (hard gates — wrong product, excluded, OOS)
    relevant = []
    for item in items:
        source_url = item.get("source_url", "")
        if source_url in existing_urls:
            skip_dup += 1
            continue

        passed, reason = _validate_item(item, requirements, hunt_keywords)
        if not passed:
            skip_relevance += 1
            logger.debug(f"  Irrelevant '{item.get('name', '')[:60]}': {reason}")
            continue

        # Log price ONLY for validated items (prevents accessory pollution)
        item_price = item.get("price")
        if item_price and item_price > 0:
            try:
                from core.cluster.intel_collector import log_market_price
                log_market_price(
                    hunt_id=hunt_id,
                    price=item_price,
                    source=item.get("attributes", {}).get("source", source_url[:50] if source_url else "unknown"),
                    title=item.get("name"),
                    url=item.get("listing_url") or source_url,
                    is_sold=0,
                    condition=item.get("condition"),
                )
            except Exception as e:
                logger.debug(f"Market price log failed: {e}")

        relevant.append(item)

    # Phase 2: sort by price ascending, take top N cheapest
    relevant.sort(key=lambda x: x.get("price") or float("inf"))
    top_items = relevant[:TOP_N_DEALS]

    # Phase 3: insert all top items, flag in_range
    in_range_count = 0
    for rank, item in enumerate(top_items, 1):
        source_url = item.get("source_url", "")
        in_range = _check_price_range(item, requirements)
        if in_range:
            in_range_count += 1

        # Inject flags into attributes
        attrs = item.get("attributes", {})
        if isinstance(attrs, str):
            try:
                attrs = json.loads(attrs)
            except (json.JSONDecodeError, TypeError):
                attrs = {}
        attrs["in_range"] = in_range
        attrs["price_rank"] = rank
        item["attributes"] = attrs

        # Always use API to insert (sourcer runs on Walter, DB is on Lockwood)
        deal_id = await _post_deal_item(item)
        if deal_id:
            new_count += 1
            existing_urls.add(source_url)
        else:
            skip_insert += 1

    # Log summary
    logger.info(f"  Insert: {len(items)} scraped, {len(relevant)} relevant, top {len(top_items)} → {new_count} new ({in_range_count} in range)")
    if skip_dup:
        logger.info(f"    {skip_dup} url-dup, {skip_relevance} irrelevant, {skip_insert} db-dup")

    return new_count


# --- Pair Detection ---

async def _detect_pairs(hunt_id: int, config: dict):
    """Detect matching pairs from the same seller (NVLink requirement).
    Flags deals where 2+ matching items exist from same seller within window.
    """
    if not config.get("pair_detection", {}).get("enabled", False):
        return

    try:
        from core.cluster.intel_collector import _get_intel_db
        conn = _get_intel_db()

        window_hours = config.get("pair_detection", {}).get("same_seller_window_hours", 72)

        # Find sellers with 2+ items for this hunt within the window
        rows = conn.execute(
            """SELECT seller, COUNT(*) as cnt, GROUP_CONCAT(id) as item_ids
               FROM deal_items
               WHERE hunt_id = ? AND dismissed = 0 AND seller != ''
                 AND collected_at >= datetime('now', ?)
               GROUP BY seller
               HAVING cnt >= 2""",
            (hunt_id, f"-{window_hours} hours")
        ).fetchall()

        for row in rows:
            item_ids = row["item_ids"].split(",")
            for item_id in item_ids:
                # Tag the deal with pair info in attributes
                existing = conn.execute(
                    "SELECT attributes FROM deal_items WHERE id = ?", (int(item_id),)
                ).fetchone()
                if existing:
                    attrs = json.loads(existing["attributes"] or "{}")
                    attrs["pair_available"] = True
                    attrs["pair_seller"] = row["seller"]
                    attrs["pair_count"] = row["cnt"]
                    conn.execute(
                        "UPDATE deal_items SET attributes = ? WHERE id = ?",
                        (json.dumps(attrs), int(item_id))
                    )

        conn.commit()
        conn.close()

        if rows:
            logger.info(f"Pair detection: found {len(rows)} sellers with matching pairs for hunt {hunt_id}")

    except ImportError:
        logger.info("Pair detection requires running on Lockwood (direct DB access)")
    except Exception as e:
        logger.error(f"Pair detection failed: {e}")


# --- Below Dedup (Title Similarity) ---

async def _dedup_by_title_similarity(items: list[dict], threshold: float = 0.85) -> list[dict]:
    """Remove items whose titles are too similar to each other.
    Uses Below's embedding endpoint for semantic dedup.
    """
    if not httpx or not items or len(items) < 2:
        return items

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            # Get embeddings for all titles
            embeddings = {}
            for item in items:
                title = item.get("name", "")
                if not title:
                    continue
                try:
                    resp = await client.post(
                        f"{BELOW_OLLAMA_URL}/api/embed",
                        json={"model": BELOW_EMBED_MODEL, "input": title},
                    )
                    if resp.status_code == 200:
                        data = resp.json()
                        embs = data.get("embeddings", [])
                        if embs:
                            embeddings[id(item)] = embs[0]
                except Exception:
                    continue

            if len(embeddings) < 2:
                return items

            # Remove duplicates using shared cosine_similarity
            kept = []
            seen_ids = set()

            for item in items:
                item_id = id(item)
                if item_id in seen_ids:
                    continue

                emb = embeddings.get(item_id)
                if not emb:
                    kept.append(item)
                    continue

                is_dup = False
                for kept_item in kept:
                    kept_emb = embeddings.get(id(kept_item))
                    if not kept_emb:
                        continue
                    sim = cosine_similarity(emb, kept_emb)
                    if sim > threshold:
                        is_dup = True
                        break

                if not is_dup:
                    kept.append(item)
                else:
                    seen_ids.add(item_id)

            if len(items) != len(kept):
                logger.info(f"Title dedup: {len(items)} -> {len(kept)} items")
            return kept

    except Exception as e:
        logger.warning(f"Title dedup failed: {e}")
        return items


# --- Source Runner ---

async def _run_source(source_name: str, hunt: dict, source_config: dict) -> list[dict]:
    """Run a single source search for a hunt."""
    try:
        if source_name == "ebay_sold":
            from core.cluster.hunt_sources.ebay_sold import search
        elif source_name == "ebay_browse":
            # Only enable when BOTH API keys present
            app_id = os.environ.get("EBAY_APP_ID", "")
            secret = os.environ.get("EBAY_SECRET", "")
            if not (app_id and secret):
                logger.debug("ebay_browse skipped — requires EBAY_APP_ID + EBAY_SECRET env vars")
                return []
            from core.cluster.hunt_sources.ebay_browse import search
        elif source_name == "reddit_rss":
            from core.cluster.hunt_sources.reddit_rss import search
        elif source_name == "craigslist_rss":
            from core.cluster.hunt_sources.craigslist_rss import search
        elif source_name == "pcpartpicker":
            from core.cluster.hunt_sources.pcpartpicker import search
        elif source_name == "newegg":
            from core.cluster.hunt_sources.newegg import search
        elif source_name == "shopify":
            from core.cluster.hunt_sources.shopify import search
        elif source_name == "bhphoto":
            from core.cluster.hunt_sources.bhphoto import search
        elif source_name == "crucial":
            from core.cluster.hunt_sources.crucial import search
        else:
            logger.warning(f"Unknown source: {source_name}")
            return []

        return await search(hunt, source_config)
    except Exception as e:
        logger.error(f"Source {source_name} failed for hunt '{hunt.get('name')}': {e}")
        return []


# --- Main Loop ---

# In-process cache of last-checked timestamps (fast path; backed by SQLite column)
_last_checked: dict[int, float] = {}


BELOW_NEEDS_LLM = {"newegg", "bhphoto"}


def _get_hunt_last_checked_db(hunt_id: int) -> float:
    """Read last_checked_at from the active_hunts SQLite column (multi-process safe)."""
    try:
        from core.cluster.intel_collector import _get_intel_db, INTEL_DB_PATH
        conn = _get_intel_db()
        row = conn.execute(
            "SELECT last_checked_at FROM active_hunts WHERE id = ?", (hunt_id,)
        ).fetchone()
        conn.close()
        if row and row[0]:
            import datetime
            dt = datetime.datetime.fromisoformat(row[0].replace("Z", "+00:00"))
            return dt.timestamp()
    except Exception as exc:
        logger.debug("last_checked_at read failed for hunt %d: %s", hunt_id, exc)
    return 0.0


def _set_hunt_last_checked_db(hunt_id: int, ts: float) -> None:
    """Write last_checked_at to the active_hunts SQLite column (multi-process safe)."""
    try:
        import datetime
        from core.cluster.intel_collector import _get_intel_db
        iso = datetime.datetime.utcfromtimestamp(ts).strftime("%Y-%m-%dT%H:%M:%SZ")
        conn = _get_intel_db()
        conn.execute(
            "UPDATE active_hunts SET last_checked_at = ? WHERE id = ?", (iso, hunt_id)
        )
        conn.commit()
        conn.close()
    except Exception as exc:
        logger.debug("last_checked_at write failed for hunt %d: %s", hunt_id, exc)


async def _check_below_online() -> bool:
    """Check if Below's Ollama is reachable."""
    if not httpx:
        return False
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{BELOW_OLLAMA_URL}/api/tags")
            return resp.status_code == 200
    except Exception:
        return False


async def check_hunts_once():
    """Run one check cycle: fetch hunts, run sources for any due hunts."""
    config = _load_config()
    hunts = await _get_active_hunts()

    if not hunts:
        logger.debug("No active hunts")
        return

    now = time.time()

    for hunt in hunts:
        hunt_id = hunt["id"]
        interval = hunt.get("check_interval_minutes", 60) * 60

        with last_checked_lock:
            # Fast path: in-process cache.  Seed from DB on first encounter so
            # a fresh process respects the persisted check time across restarts.
            if hunt_id not in _last_checked:
                _last_checked[hunt_id] = _get_hunt_last_checked_db(hunt_id)
            last = _last_checked[hunt_id]
            if now - last < interval:
                continue
            _last_checked[hunt_id] = now
        # Persist to DB outside the in-process lock (non-blocking; best-effort)
        _set_hunt_last_checked_db(hunt_id, now)

        logger.info(f"Checking hunt [{hunt_id}] '{hunt['name']}'")  # noqa: Q000

        below_online = await _check_below_online()
        if not below_online:
            logger.warning("Below offline — HTML adapters (eBay/Newegg/B&H) skipped, JSON-only sources running")

        all_items = []
        for source_name, source_config in config.get("sources", {}).items():
            if not source_config.get("enabled", True):
                continue
            if not below_online and source_name in BELOW_NEEDS_LLM:
                continue
            items = await _run_source(source_name, hunt, source_config)
            all_items.extend(items)

        if not all_items:
            logger.info(f"  No new items from any source")
            continue

        # Dedup by title similarity
        dedup_config = config.get("dedup", {})
        if dedup_config.get("title_similarity", True):
            threshold = dedup_config.get("similarity_threshold", 0.85)
            all_items = await _dedup_by_title_similarity(all_items, threshold)

        # Load hunt requirements (JSON column, may be None for legacy hunts)
        hunt_keywords = hunt.get("keywords", "")
        requirements_raw = hunt.get("requirements")
        requirements = None
        if requirements_raw:
            try:
                requirements = json.loads(requirements_raw) if isinstance(requirements_raw, str) else requirements_raw
            except (json.JSONDecodeError, TypeError):
                pass

        # Insert into Lockwood — validates every item against requirements
        new_count = await _batch_insert_deals(all_items, hunt_id, requirements, hunt_keywords)
        logger.info(f"  Hunt [{hunt_id}]: {len(all_items)} found, {new_count} new items inserted")

        # Run Reddit historical search for market data collection
        try:
            from core.cluster.hunt_sources.reddit_rss import search_historical
            reddit_config = config.get("sources", {}).get("reddit_rss", {})
            if reddit_config.get("enabled", True):
                await search_historical(hunt, reddit_config)
        except Exception as e:
            logger.debug(f"Reddit historical search failed for hunt [{hunt_id}]: {e}")

        # Pair detection
        await _detect_pairs(hunt_id, config)


async def run_forever():
    """Main loop: check hunts on interval."""
    logger.info(f"Hunt sourcer starting — checking every {CHECK_HUNTS_INTERVAL}s")
    logger.info(f"Lockwood: {JIMMY_URL}")

    while True:
        try:
            await check_hunts_once()
        except Exception as e:
            logger.error(f"Hunt check cycle error: {e}")
        await asyncio.sleep(CHECK_HUNTS_INTERVAL)


_sourcer_thread = None


def start_sourcer_cron():
    """Start the sourcer as a background thread (for embedding in node_intelligence).
    Thread-safe: only one sourcer runs at a time.
    """
    global _sourcer_thread
    import threading

    if _sourcer_thread and _sourcer_thread.is_alive():
        logger.info("Sourcer cron already running")
        return

    def _run():
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
        )
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(run_forever())
        except Exception as e:
            logger.error(f"Sourcer cron crashed: {e}")
        finally:
            loop.close()

    _sourcer_thread = threading.Thread(target=_run, daemon=True, name="hunt-sourcer")
    _sourcer_thread.start()
    logger.info("Hunt sourcer cron started in background thread")


def main():
    """Entry point for systemd service."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
