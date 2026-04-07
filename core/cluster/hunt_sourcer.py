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
import sys
import time
import hashlib
from datetime import datetime
from pathlib import Path
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# --- Config ---
CONFIG_PATH = Path(__file__).parent / "hunt_sourcer_config.json"
LOCKWOOD_URL = os.environ.get("LOCKWOOD_URL", "http://10.0.1.101:8100")
BELOW_OLLAMA_URL = os.environ.get("BELOW_OLLAMA_URL", "http://10.0.1.105:11434")
BELOW_MODEL = os.environ.get("BELOW_MODEL", "qwen3:8b")
CHECK_HUNTS_INTERVAL = int(os.environ.get("CHECK_HUNTS_INTERVAL", "300"))  # 5min


def _load_config() -> dict:
    """Load sourcer configuration."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {
        "sources": {
            "ebay_scrape": {"enabled": True},
            "ebay_browse": {"enabled": False, "marketplace_id": "EBAY_US", "limit": 50},
            "reddit_rss": {"enabled": True, "subreddits": ["buildapcsales", "hardwareswap"]},
            "craigslist_rss": {"enabled": True, "cities": ["sfbay", "losangeles", "seattle"]},
            "pcpartpicker": {"enabled": True, "use_playwright": False},
        },
        "dedup": {"url_hash": True, "title_similarity": True, "similarity_threshold": 0.85},
        "pair_detection": {"enabled": True, "same_seller_window_hours": 72},
    }


def _url_hash(url: str) -> str:
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


# --- Lockwood Client ---

async def _get_active_hunts() -> list[dict]:
    """Fetch active hunts from Lockwood."""
    if not httpx:
        return []
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(f"{LOCKWOOD_URL}/api/deals/hunts")
            resp.raise_for_status()
            return resp.json().get("hunts", [])
    except Exception as e:
        logger.error(f"Failed to fetch hunts from Lockwood: {e}")
        return []


async def _get_existing_deal_urls(hunt_id: int) -> set[str]:
    """Get set of existing source_url hashes for a hunt (for dedup)."""
    if not httpx:
        return set()
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get(
                f"{LOCKWOOD_URL}/api/deals/items",
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
                f"{LOCKWOOD_URL}/api/deals/items",
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


# --- Batch Insert via Direct DB (Lockwood-local) or API ---

async def _batch_insert_deals(items: list[dict], hunt_id: int) -> int:
    """Insert deal items, deduplicating against existing. Returns count of new items."""
    existing_urls = await _get_existing_deal_urls(hunt_id)
    new_count = 0

    for item in items:
        source_url = item.get("source_url", "")
        if source_url in existing_urls:
            continue

        # Use Lockwood's create_deal_item directly if running on Lockwood,
        # otherwise POST to API
        try:
            from core.cluster.intel_collector import create_deal_item
            deal_id = create_deal_item(
                hunt_id=item["hunt_id"],
                name=item["name"],
                category=item.get("category"),
                attributes=item.get("attributes"),
                source_url=source_url,
                price=item.get("price"),
                condition=item.get("condition"),
                seller=item.get("seller"),
                seller_rating=item.get("seller_rating"),
                listing_url=item.get("listing_url"),
            )
            if deal_id:
                new_count += 1
                existing_urls.add(source_url)
        except ImportError:
            deal_id = await _post_deal_item(item)
            if deal_id:
                new_count += 1
                existing_urls.add(source_url)

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
                        json={"model": BELOW_MODEL, "input": title},
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

            # Remove duplicates
            import math
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
                    # Cosine similarity
                    dot = sum(a * b for a, b in zip(emb, kept_emb))
                    mag1 = math.sqrt(sum(a * a for a in emb))
                    mag2 = math.sqrt(sum(b * b for b in kept_emb))
                    if mag1 > 0 and mag2 > 0:
                        sim = dot / (mag1 * mag2)
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
        if source_name == "ebay_scrape":
            from core.cluster.hunt_sources.ebay_scrape import search
        elif source_name == "ebay_browse":
            from core.cluster.hunt_sources.ebay_browse import search
        elif source_name == "reddit_rss":
            from core.cluster.hunt_sources.reddit_rss import search
        elif source_name == "craigslist_rss":
            from core.cluster.hunt_sources.craigslist_rss import search
        elif source_name == "pcpartpicker":
            from core.cluster.hunt_sources.pcpartpicker import search
        else:
            logger.warning(f"Unknown source: {source_name}")
            return []

        return await search(hunt, source_config)
    except Exception as e:
        logger.error(f"Source {source_name} failed for hunt '{hunt.get('name')}': {e}")
        return []


# --- Main Loop ---

# Track last check time per hunt
_last_checked: dict[int, float] = {}


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
        last = _last_checked.get(hunt_id, 0)

        if now - last < interval:
            continue

        logger.info(f"Checking hunt [{hunt_id}] '{hunt['name']}'")
        _last_checked[hunt_id] = now

        all_items = []
        for source_name, source_config in config.get("sources", {}).items():
            if not source_config.get("enabled", True):
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

        # Insert into Lockwood
        new_count = await _batch_insert_deals(all_items, hunt_id)
        logger.info(f"  Hunt [{hunt_id}]: {len(all_items)} found, {new_count} new items inserted")

        # Pair detection
        await _detect_pairs(hunt_id, config)


async def run_forever():
    """Main loop: check hunts on interval."""
    logger.info(f"Hunt sourcer starting — checking every {CHECK_HUNTS_INTERVAL}s")
    logger.info(f"Lockwood: {LOCKWOOD_URL}")

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
