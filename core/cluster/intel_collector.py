"""
BR3 Cluster — Intelligence & Deals Collector
Cron-driven collection scripts for intel items and deal tracking.

Handles:
- Webhook payload parsing (Miniflux, changedetection.io, NewReleases.io, F5Bot)
- Models API polling (Anthropic /v1/models)
- Package version polling (npm + PyPI)
- SQLite CRUD for all intel/deals tables
"""

import os
import json
import hashlib
import sqlite3
import time
import threading
import logging
from pathlib import Path
from typing import Optional
from datetime import datetime, timedelta

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

INTEL_DB_PATH = os.environ.get("INTEL_DB", os.path.expanduser("~/.lockwood/intel.db"))
SCHEMA_PATH = Path(__file__).parent / "intel_schema.sql"

# Polling intervals
MODELS_POLL_INTERVAL = int(os.environ.get("MODELS_POLL_INTERVAL", "21600"))  # 6h
PACKAGE_POLL_INTERVAL = int(os.environ.get("PACKAGE_POLL_INTERVAL", "7200"))  # 2h

# Anthropic API
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
ANTHROPIC_MODELS_URL = "https://api.anthropic.com/v1/models"

# Packages to track
TRACKED_NPM_PACKAGES = [
    "@anthropic-ai/sdk",
    "@anthropic-ai/claude-code",
]
TRACKED_PYPI_PACKAGES = [
    "anthropic",
    "claude-agent-sdk",
]

# Source type classification
SOURCE_TYPE_MAP = {
    "github": "official",
    "status.claude.com": "official",
    "anthropic": "official",
    "reddit": "community",
    "news.google.com": "blog",
    "newreleases.io": "official",
    "f5bot": "community",
}


def _get_intel_db() -> sqlite3.Connection:
    """Get SQLite connection for intel database."""
    os.makedirs(os.path.dirname(INTEL_DB_PATH), exist_ok=True)
    conn = sqlite3.connect(INTEL_DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    _ensure_intel_tables(conn)
    return conn


def _ensure_intel_tables(conn: sqlite3.Connection):
    """Create tables from schema file, then migrate existing DBs.

    IMPORTANT: Migrations run BEFORE schema.sql so that indexes on new columns
    don't fail against stale on-disk tables (schema uses IF NOT EXISTS guards).
    """
    # Migration FIRST — add columns to existing tables before schema indexes reference them
    _migrate_columns = [
        ("intel_improvements", "type", "TEXT DEFAULT 'fix'"),
        ("intel_improvements", "auto_acted", "INTEGER DEFAULT 0"),
        ("intel_improvements", "auto_act_log", "TEXT"),
        ("deal_items", "listing_url_hash", "TEXT"),
        # Phase 6: price_history market data columns
        ("price_history", "hunt_id", "INTEGER"),
        ("price_history", "is_sold", "INTEGER DEFAULT 0"),
        ("price_history", "condition", "TEXT"),
        ("price_history", "title", "TEXT"),
        ("price_history", "url", "TEXT"),
        # Phase 7: deal_items purchase tracking
        ("deal_items", "purchased", "INTEGER DEFAULT 0"),
        ("deal_items", "purchased_price", "REAL"),
        # Seller verification (Apify-powered)
        ("deal_items", "seller_verified", "INTEGER DEFAULT 0"),
        ("deal_items", "seller_account_age_years", "REAL"),
        ("deal_items", "seller_karma", "INTEGER"),
        ("deal_items", "seller_trades", "INTEGER"),
        ("deal_items", "seller_verification_source", "TEXT"),
        ("deal_items", "seller_verified_at", "TEXT"),
        ("deal_items", "seller_verification_error", "TEXT"),
        # Hunt lifecycle tracking
        ("deal_items", "received", "INTEGER DEFAULT 0"),
        ("deal_items", "received_at", "TEXT"),
        ("deal_items", "user_notes", "TEXT"),
        ("deal_items", "actual_url", "TEXT"),
        ("deal_items", "tracking_number", "TEXT"),
        ("deal_items", "carrier", "TEXT"),
        ("deal_items", "delivery_status", "TEXT DEFAULT 'none'"),
        ("deal_items", "delivery_updated_at", "TEXT"),
        ("active_hunts", "completed_at", "TEXT"),
        ("active_hunts", "completion_notes", "TEXT"),
    ]
    for table, col, col_def in _migrate_columns:
        try:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN {col} {col_def}")
            conn.commit()
        except sqlite3.OperationalError:
            pass  # Column already exists

    # NOW apply schema (CREATE TABLE IF NOT EXISTS, CREATE INDEX IF NOT EXISTS)
    # Safe because migrations above ensure columns exist for any indexes
    if SCHEMA_PATH.exists():
        schema_sql = SCHEMA_PATH.read_text()
        conn.executescript(schema_sql)
    conn.commit()


def _url_hash(url: str) -> str:
    """Generate hash for URL deduplication."""
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


def _classify_source_type(source: str, url: str = "") -> str:
    """Classify source as official/community/blog."""
    source_lower = (source or "").lower()
    url_lower = (url or "").lower()
    for key, stype in SOURCE_TYPE_MAP.items():
        if key in source_lower or key in url_lower:
            return stype
    return "community"


# --- CRUD Operations ---

def create_intel_item(title: str, source: str, url: str = None,
                      raw_content: str = None, source_type: str = None,
                      category: str = None) -> Optional[int]:
    """Insert a new intel item. Returns item ID or None if duplicate."""
    conn = _get_intel_db()
    try:
        # Dedup by URL hash
        if url:
            uhash = _url_hash(url)
            existing = conn.execute(
                "SELECT id FROM intel_items WHERE url_hash = ?", (uhash,)
            ).fetchone()
            if existing:
                conn.close()
                return None
        else:
            uhash = None

        if source_type is None:
            source_type = _classify_source_type(source, url)

        cursor = conn.execute(
            """INSERT INTO intel_items (title, source, url, raw_content, source_type,
               category, url_hash) VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, source, url, raw_content, source_type, category, uhash)
        )
        conn.commit()
        item_id = cursor.lastrowid
        return item_id
    finally:
        conn.close()


def get_intel_items(priority: str = None, category: str = None,
                    source_type: str = None, read: bool = None,
                    limit: int = 50, days: int = None) -> list[dict]:
    """Query intel items with filters."""
    conn = _get_intel_db()
    conditions = []
    params = []

    if priority:
        priorities = [p.strip() for p in priority.split(",")]
        placeholders = ",".join("?" * len(priorities))
        conditions.append(f"priority IN ({placeholders})")
        params.extend(priorities)
    if category:
        conditions.append("category = ?")
        params.append(category)
    if source_type:
        conditions.append("source_type = ?")
        params.append(source_type)
    if read is not None:
        conditions.append("read = ?")
        params.append(1 if read else 0)
    if days:
        conditions.append("collected_at >= datetime('now', ?)")
        params.append(f"-{days} days")

    conditions.append("dismissed = 0")

    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"""SELECT * FROM intel_items WHERE {where}
                ORDER BY
                    CASE priority
                        WHEN 'critical' THEN 0
                        WHEN 'high' THEN 1
                        WHEN 'medium' THEN 2
                        WHEN 'low' THEN 3
                        ELSE 4
                    END,
                    collected_at DESC
                LIMIT ?"""
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_intel_alerts() -> dict:
    """Get count of unread critical + high items."""
    conn = _get_intel_db()
    row = conn.execute(
        """SELECT
            SUM(CASE WHEN priority = 'critical' THEN 1 ELSE 0 END) as critical_count,
            SUM(CASE WHEN priority = 'high' THEN 1 ELSE 0 END) as high_count
           FROM intel_items
           WHERE read = 0 AND dismissed = 0 AND priority IN ('critical', 'high')"""
    ).fetchone()
    conn.close()
    return {
        "critical_count": row["critical_count"] or 0,
        "high_count": row["high_count"] or 0,
    }


def mark_intel_read(item_id: int) -> bool:
    """Mark an intel item as read."""
    conn = _get_intel_db()
    conn.execute("UPDATE intel_items SET read = 1 WHERE id = ?", (item_id,))
    conn.commit()
    changed = conn.total_changes > 0
    conn.close()
    return changed


def dismiss_intel_item(item_id: int) -> bool:
    """Dismiss an intel item."""
    conn = _get_intel_db()
    conn.execute("UPDATE intel_items SET dismissed = 1 WHERE id = ?", (item_id,))
    conn.commit()
    changed = conn.total_changes > 0
    conn.close()
    return changed


# --- Deal CRUD ---

def create_deal_item(hunt_id: int, name: str, category: str = None,
                     attributes: dict = None, source_url: str = None,
                     price: float = None, condition: str = None,
                     seller: str = None, seller_rating: float = None,
                     listing_url: str = None) -> Optional[int]:
    """Insert a new deal item. Returns item ID. Deduplicates by listing_url hash."""
    conn = _get_intel_db()
    try:
        # Listing URL dedup — reject if same URL already exists for this hunt
        dedup_url = listing_url or source_url
        if dedup_url:
            import hashlib
            url_hash = hashlib.sha256(dedup_url.strip().lower().encode()).hexdigest()[:16]
            existing = conn.execute(
                "SELECT id FROM deal_items WHERE hunt_id = ? AND listing_url_hash = ?",
                (hunt_id, url_hash)
            ).fetchone()
            if existing:
                return None  # duplicate

        # Extract in_stock from attributes if present (sources like eBay Browse set this)
        in_stock = None
        if attributes and isinstance(attributes, dict):
            in_stock_attr = attributes.get("in_stock")
            if in_stock_attr is True:
                in_stock = 1
            elif in_stock_attr is False:
                in_stock = 0

        cursor = conn.execute(
            """INSERT INTO deal_items (hunt_id, name, category, attributes,
               source_url, price, condition, seller, seller_rating, listing_url, listing_url_hash, in_stock)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (hunt_id, name, category, json.dumps(attributes) if attributes else None,
             source_url, price, condition, seller, seller_rating, listing_url,
             hashlib.sha256((dedup_url or "").strip().lower().encode()).hexdigest()[:16] if dedup_url else None,
             in_stock)
        )
        conn.commit()
        deal_id = cursor.lastrowid

        # Create initial price history entry
        if price is not None:
            conn.execute(
                "INSERT INTO price_history (deal_item_id, hunt_id, price, source, title, url, condition) VALUES (?, ?, ?, ?, ?, ?, ?)",
                (deal_id, hunt_id, price, source_url, name, listing_url or source_url, condition)
            )
            conn.commit()

        return deal_id
    finally:
        conn.close()


def get_deal_items(hunt_id: int = None, min_score: int = None,
                   limit: int = 50, verified_only: bool = None,
                   in_stock_only: bool = None,
                   seller_verified_only: bool = None,
                   ready_only: bool = True,
                   include_out_of_stock: bool = False,
                   include_unverified_sellers: bool = False) -> list[dict]:
    """Query deal items with filters.

    By default (ready_only=True), only shows items that are:
    - in_stock = 1 (verified in stock)
    - seller_verified = 1 (seller legitimacy verified)

    This ensures the dashboard only shows deals you can actually buy from
    verified sellers. Set ready_only=False to see all items regardless of
    verification status.

    Args:
        hunt_id: Filter by hunt
        min_score: Minimum deal score
        limit: Max results
        verified_only: Require link verified (deprecated, use ready_only)
        in_stock_only: Require in_stock = 1
        seller_verified_only: Require seller_verified = 1
        ready_only: Require BOTH in_stock AND seller_verified (default True)
        include_out_of_stock: Include items marked out of stock
        include_unverified_sellers: Include items with unverified sellers
    """
    conn = _get_intel_db()
    conditions = ["dismissed = 0"]
    params = []

    if hunt_id is not None:
        conditions.append("hunt_id = ?")
        params.append(hunt_id)
    if min_score is not None:
        conditions.append("deal_score >= ?")
        params.append(min_score)
    if verified_only:
        conditions.append("verified = 1")

    # Ready mode: require both in_stock AND seller_verified
    if ready_only:
        conditions.append("in_stock = 1")
        conditions.append("seller_verified = 1")
    else:
        # When ready_only=False, show all deals by default.
        # Only apply filters if explicitly requested.
        if in_stock_only:
            conditions.append("in_stock = 1")
        if seller_verified_only:
            conditions.append("seller_verified = 1")

    where = " AND ".join(conditions)
    query = f"""SELECT * FROM deal_items WHERE {where}
                ORDER BY price ASC NULLS LAST, collected_at DESC
                LIMIT ?"""
    params.append(limit)

    rows = conn.execute(query, params).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_price_history(deal_item_id: int) -> list[dict]:
    """Get price history for a deal item."""
    conn = _get_intel_db()
    rows = conn.execute(
        "SELECT * FROM price_history WHERE deal_item_id = ? ORDER BY recorded_at ASC",
        (deal_item_id,)
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def log_market_price(hunt_id: int, price: float, source: str,
                     title: str = None, url: str = None,
                     is_sold: int = 0, condition: str = None) -> Optional[int]:
    """Log a market price data point for a hunt (no deal_item required).
    Used for building market stats. Applies price floor/ceiling sanity checks
    to prevent accessory pollution.
    Returns price_history row ID or None on error.
    """
    if price is None or price <= 0:
        return None
    conn = _get_intel_db()
    try:
        # Get hunt's target_price for sanity bounds
        hunt_row = conn.execute(
            "SELECT target_price FROM active_hunts WHERE id = ?", (hunt_id,)
        ).fetchone()
        if hunt_row and hunt_row["target_price"]:
            target = hunt_row["target_price"]
            price_floor = target * 0.1   # 10% of target
            price_ceiling = target * 3.0  # 300% of target
            if price < price_floor or price > price_ceiling:
                logger.debug(f"Price ${price:.2f} outside bounds [${price_floor:.0f}-${price_ceiling:.0f}] for hunt {hunt_id}")
                return None

        # Dedup: skip if same url already recorded for this hunt
        if url:
            existing = conn.execute(
                "SELECT id FROM price_history WHERE hunt_id = ? AND url = ?",
                (hunt_id, url)
            ).fetchone()
            if existing:
                return None

        cursor = conn.execute(
            """INSERT INTO price_history (deal_item_id, hunt_id, price, source, title, url, is_sold, condition)
               VALUES (NULL, ?, ?, ?, ?, ?, ?, ?)""",
            (hunt_id, price, source, title, url, is_sold, condition)
        )
        conn.commit()
        return cursor.lastrowid
    except Exception as e:
        logger.error(f"log_market_price failed: {e}")
        return None
    finally:
        conn.close()


def mark_deal_read(item_id: int) -> bool:
    conn = _get_intel_db()
    conn.execute("UPDATE deal_items SET read = 1 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return True


def dismiss_deal_item(item_id: int) -> bool:
    conn = _get_intel_db()
    conn.execute("UPDATE deal_items SET dismissed = 1 WHERE id = ?", (item_id,))
    conn.commit()
    conn.close()
    return True


def get_market_stats(hunt_id: int, days: int = 90) -> dict:
    """Compute market statistics for a hunt from price_history data.
    Returns: median, p25, p75, min, max, sample_count, sold_count, trend.
    Trend computed via linear regression on 30-day window.
    """
    import statistics

    conn = _get_intel_db()
    rows = conn.execute(
        """SELECT price, is_sold, recorded_at FROM price_history
           WHERE hunt_id = ? AND recorded_at >= datetime('now', ?)
           ORDER BY recorded_at ASC""",
        (hunt_id, f"-{days} days")
    ).fetchall()
    conn.close()

    if not rows:
        return {
            "hunt_id": hunt_id,
            "median": None, "p25": None, "p75": None,
            "min": None, "max": None,
            "sample_count": 0, "sold_count": 0,
            "trend": "unknown",
        }

    prices = [r["price"] for r in rows]
    sold_count = sum(1 for r in rows if r["is_sold"])

    # Outlier trimming: IQR-based filter to handle polluted data
    if len(prices) >= 5:
        sorted_prices = sorted(prices)
        q1_idx = len(sorted_prices) // 4
        q3_idx = (3 * len(sorted_prices)) // 4
        q1 = sorted_prices[q1_idx]
        q3 = sorted_prices[q3_idx]
        iqr = q3 - q1
        lower_bound = q1 - (1.5 * iqr)
        upper_bound = q3 + (1.5 * iqr)
        prices = [p for p in prices if lower_bound <= p <= upper_bound]
        if not prices:
            prices = [r["price"] for r in rows]  # fallback if filter too aggressive

    median = statistics.median(prices)
    p25, p75 = None, None
    if len(prices) >= 4:
        quartiles = statistics.quantiles(prices, n=4)
        p25 = quartiles[0]
        p75 = quartiles[2]

    # Trend: linear regression on 30-day window
    trend = _compute_trend(rows)

    return {
        "hunt_id": hunt_id,
        "median": round(median, 2),
        "p25": round(p25, 2) if p25 is not None else None,
        "p75": round(p75, 2) if p75 is not None else None,
        "min": round(min(prices), 2),
        "max": round(max(prices), 2),
        "sample_count": len(prices),
        "sold_count": sold_count,
        "trend": trend,
    }


def _compute_trend(rows: list) -> str:
    """Compute price trend via linear regression on recent data.
    Returns: 'rising', 'falling', or 'stable'.
    """
    if len(rows) < 3:
        return "unknown"

    # Use last 30 days only for trend
    from datetime import datetime
    now = datetime.utcnow()
    recent = []
    for r in rows:
        try:
            ts = datetime.fromisoformat(r["recorded_at"].replace("Z", "+00:00").replace("+00:00", ""))
        except (ValueError, AttributeError):
            try:
                ts = datetime.strptime(r["recorded_at"], "%Y-%m-%d %H:%M:%S")
            except (ValueError, AttributeError):
                continue
        days_ago = (now - ts).total_seconds() / 86400
        if days_ago <= 30:
            recent.append((days_ago, r["price"]))

    if len(recent) < 3:
        return "unknown"

    # Simple linear regression: slope of price vs time
    n = len(recent)
    sum_x = sum(t for t, _ in recent)
    sum_y = sum(p for _, p in recent)
    sum_xy = sum(t * p for t, p in recent)
    sum_x2 = sum(t * t for t, _ in recent)

    denom = n * sum_x2 - sum_x * sum_x
    if denom == 0:
        return "stable"

    slope = (n * sum_xy - sum_x * sum_y) / denom
    mean_price = sum_y / n

    # Normalize slope as percentage of mean price per day
    if mean_price > 0:
        pct_per_day = (slope / mean_price) * 100
    else:
        return "stable"

    # Thresholds: >0.5%/day = rising, <-0.5%/day = falling
    # Note: days_ago is inverted (higher = older), so negative slope = prices rising over time
    if pct_per_day < -0.5:
        return "rising"
    elif pct_per_day > 0.5:
        return "falling"
    return "stable"


def update_deal_item(item_id: int, **fields) -> bool:
    """General-purpose update for a deal item.
    Supported fields: purchased, purchased_price, notes, dismissed, read.
    Returns True if row was updated.
    """
    allowed = {"purchased", "purchased_price", "user_notes", "dismissed", "read",
               "deal_score", "verdict", "below_assessment", "opus_assessment",
               "received", "received_at", "actual_url", "tracking_number",
               "carrier", "delivery_status", "delivery_updated_at"}
    updates = []
    params = []
    for key, value in fields.items():
        if key in allowed:
            updates.append(f"{key} = ?")
            params.append(value)

    if not updates:
        return False

    params.append(item_id)
    conn = _get_intel_db()
    conn.execute(
        f"UPDATE deal_items SET {', '.join(updates)} WHERE id = ?",
        params
    )
    conn.commit()
    changed = conn.total_changes > 0
    conn.close()
    return changed


def mark_purchased(item_id: int, purchased_price: float = None) -> bool:
    """Mark a deal item as purchased with optional price override."""
    fields = {"purchased": 1}
    if purchased_price is not None:
        fields["purchased_price"] = purchased_price
    else:
        # Use the item's current price if no override
        conn = _get_intel_db()
        row = conn.execute("SELECT price FROM deal_items WHERE id = ?", (item_id,)).fetchone()
        conn.close()
        if row and row["price"]:
            fields["purchased_price"] = row["price"]
    return update_deal_item(item_id, **fields)


# --- Hunt CRUD ---

def create_hunt(name: str, category: str = "other", keywords: str = None,
                target_price: float = None, check_interval_minutes: int = 60,
                source_urls: list = None) -> int:
    """Create a new active hunt."""
    conn = _get_intel_db()
    cursor = conn.execute(
        """INSERT INTO active_hunts (name, category, keywords, target_price,
           check_interval_minutes, source_urls)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, category, keywords, target_price, check_interval_minutes,
         json.dumps(source_urls) if source_urls else None)
    )
    conn.commit()
    hunt_id = cursor.lastrowid
    conn.close()
    return hunt_id


def get_hunts(active_only: bool = True) -> list[dict]:
    """Get all hunts."""
    conn = _get_intel_db()
    if active_only:
        rows = conn.execute(
            "SELECT * FROM active_hunts WHERE active = 1 ORDER BY created_at DESC"
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM active_hunts ORDER BY created_at DESC"
        ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def archive_hunt(hunt_id: int) -> bool:
    conn = _get_intel_db()
    conn.execute("UPDATE active_hunts SET active = 0 WHERE id = ?", (hunt_id,))
    conn.commit()
    conn.close()
    return True


def complete_hunt(hunt_id: int, completion_notes: str = None) -> bool:
    """Complete a hunt — sets active=0, completed_at=now, optional notes."""
    conn = _get_intel_db()
    now = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
    conn.execute(
        "UPDATE active_hunts SET active = 0, completed_at = ?, completion_notes = ? WHERE id = ?",
        (now, completion_notes, hunt_id)
    )
    conn.commit()
    conn.close()
    return True


def get_archived_hunts() -> list[dict]:
    """Get archived/completed hunts with item counts and total spent."""
    conn = _get_intel_db()
    hunts = conn.execute(
        "SELECT * FROM active_hunts WHERE active = 0 ORDER BY completed_at DESC, created_at DESC"
    ).fetchall()
    result = []
    for hunt in hunts:
        h = dict(hunt)
        stats = conn.execute(
            """SELECT COUNT(*) as item_count,
                      SUM(CASE WHEN purchased = 1 THEN purchased_price ELSE 0 END) as total_spent,
                      SUM(CASE WHEN purchased = 1 THEN 1 ELSE 0 END) as purchased_count,
                      SUM(CASE WHEN received = 1 THEN 1 ELSE 0 END) as received_count
               FROM deal_items WHERE hunt_id = ?""",
            (h["id"],)
        ).fetchone()
        h["item_count"] = stats["item_count"] or 0
        h["total_spent"] = round(stats["total_spent"] or 0, 2)
        h["purchased_count"] = stats["purchased_count"] or 0
        h["received_count"] = stats["received_count"] or 0
        result.append(h)
    conn.close()
    return result


def revive_hunt(hunt_id: int) -> bool:
    """Revive an archived hunt — sets active=1, clears completed_at."""
    conn = _get_intel_db()
    conn.execute(
        "UPDATE active_hunts SET active = 1, completed_at = NULL, completion_notes = NULL WHERE id = ?",
        (hunt_id,)
    )
    conn.commit()
    conn.close()
    return True


def revive_item(item_id: int, target_hunt_id: int = None, new_hunt_name: str = None) -> dict:
    """Revive a deal item from an archived hunt.

    If target_hunt_id provided, clone item into that hunt.
    If new_hunt_name provided, create a new hunt and clone into it.
    If neither, create a hunt named 'Revived: {original_hunt_name}'.
    Cloned item has purchased=0, received=0 (fresh lifecycle).
    Returns {"item_id": new_id, "hunt_id": target_id}.
    """
    conn = _get_intel_db()
    row = conn.execute("SELECT * FROM deal_items WHERE id = ?", (item_id,)).fetchone()
    if not row:
        conn.close()
        return {"error": "Item not found"}
    item = dict(row)

    # Determine target hunt
    if target_hunt_id:
        dest_hunt_id = target_hunt_id
    elif new_hunt_name:
        cursor = conn.execute(
            "INSERT INTO active_hunts (name, category) VALUES (?, ?)",
            (new_hunt_name, item.get("category", "other"))
        )
        conn.commit()
        dest_hunt_id = cursor.lastrowid
    else:
        # Get original hunt name
        hunt_row = conn.execute(
            "SELECT name, category FROM active_hunts WHERE id = ?", (item["hunt_id"],)
        ).fetchone()
        hunt_name = hunt_row["name"] if hunt_row else "Unknown"
        hunt_cat = hunt_row["category"] if hunt_row else "other"
        cursor = conn.execute(
            "INSERT INTO active_hunts (name, category) VALUES (?, ?)",
            (f"Revived: {hunt_name}", hunt_cat)
        )
        conn.commit()
        dest_hunt_id = cursor.lastrowid

    # Clone the item into target hunt with reset lifecycle
    cursor = conn.execute(
        """INSERT INTO deal_items (hunt_id, name, category, attributes, source_url, price,
           condition, seller, seller_rating, listing_url, listing_url_hash,
           actual_url, user_notes, tracking_number, carrier)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (dest_hunt_id, item["name"], item.get("category"), item.get("attributes"),
         item.get("source_url"), item.get("price"), item.get("condition"),
         item.get("seller"), item.get("seller_rating"), item.get("listing_url"),
         item.get("listing_url_hash"), item.get("actual_url"), item.get("user_notes"),
         None, None)
    )
    conn.commit()
    new_item_id = cursor.lastrowid
    conn.close()
    return {"item_id": new_item_id, "hunt_id": dest_hunt_id}


def delete_deal_item(item_id: int) -> bool:
    """Delete a deal item and its price history."""
    conn = _get_intel_db()
    # Delete price history first (no FK cascade configured)
    conn.execute("DELETE FROM price_history WHERE deal_item_id = ?", (item_id,))
    conn.execute("DELETE FROM deal_items WHERE id = ?", (item_id,))
    conn.commit()
    changed = conn.total_changes > 0
    conn.close()
    return changed


# --- Model Snapshots ---

def save_model_snapshot(snapshot: dict, diff_summary: str = None) -> int:
    """Save a model API snapshot."""
    conn = _get_intel_db()
    cursor = conn.execute(
        "INSERT INTO model_snapshots (snapshot, diff_summary) VALUES (?, ?)",
        (json.dumps(snapshot), diff_summary)
    )
    conn.commit()
    snap_id = cursor.lastrowid
    conn.close()
    return snap_id


def get_last_model_snapshot() -> Optional[dict]:
    """Get the most recent model snapshot."""
    conn = _get_intel_db()
    row = conn.execute(
        "SELECT * FROM model_snapshots ORDER BY created_at DESC LIMIT 1"
    ).fetchone()
    conn.close()
    if row:
        result = dict(row)
        result["snapshot"] = json.loads(result["snapshot"])
        return result
    return None


# --- Webhook Parsers ---

def parse_miniflux_webhook(payload: dict) -> list[dict]:
    """Parse Miniflux webhook payload into intel items.
    Miniflux sends: {"entries": [{"title": ..., "url": ..., "content": ..., "feed": {"title": ...}}]}
    """
    items = []
    entries = payload.get("entries", [])
    if not entries and "entry" in payload:
        entries = [payload["entry"]]

    for entry in entries:
        feed = entry.get("feed", {})
        source = feed.get("title", "RSS Feed")
        url = entry.get("url", "")
        title = entry.get("title", "")

        if not title:
            continue

        item_id = create_intel_item(
            title=title,
            source=source,
            url=url,
            raw_content=entry.get("content", ""),
            source_type=_classify_source_type(source, url),
        )
        if item_id:
            items.append({"id": item_id, "title": title, "source": source})

    return items


def parse_changedetection_webhook(payload: dict) -> list[dict]:
    """Parse changedetection.io webhook payload into deal items.
    Payload contains watch info with current snapshot data.
    """
    items = []
    watch_url = payload.get("watch_url", "")
    title = payload.get("watch_title", payload.get("title", ""))
    current_snapshot = payload.get("current_snapshot", "")

    # Extract listings from snapshot (eBay CSS selectors)
    listings = payload.get("listings", [])

    if not listings and title:
        # Single item change notification
        price_str = payload.get("price", "")
        price = None
        if price_str:
            try:
                price = float(price_str.replace("$", "").replace(",", "").strip())
            except (ValueError, AttributeError):
                pass

        # Find matching hunt
        hunts = get_hunts(active_only=True)
        hunt_id = None
        for hunt in hunts:
            hunt_urls = json.loads(hunt.get("source_urls") or "[]")
            if watch_url in hunt_urls or any(watch_url in u for u in hunt_urls):
                hunt_id = hunt["id"]
                break

        if hunt_id and title:
            deal_id = create_deal_item(
                hunt_id=hunt_id,
                name=title,
                source_url=watch_url,
                price=price,
                seller=payload.get("seller", ""),
                seller_rating=payload.get("seller_rating"),
                condition=payload.get("condition", ""),
                listing_url=payload.get("listing_url", watch_url),
            )
            if deal_id:
                items.append({"id": deal_id, "name": title, "price": price})

    for listing in listings:
        hunts = get_hunts(active_only=True)
        hunt_id = None
        for hunt in hunts:
            hunt_urls = json.loads(hunt.get("source_urls") or "[]")
            if watch_url in hunt_urls or any(watch_url in u for u in hunt_urls):
                hunt_id = hunt["id"]
                break

        if hunt_id:
            price = None
            price_str = listing.get("price", "")
            if price_str:
                try:
                    price = float(str(price_str).replace("$", "").replace(",", "").strip())
                except (ValueError, AttributeError):
                    pass

            deal_id = create_deal_item(
                hunt_id=hunt_id,
                name=listing.get("title", ""),
                source_url=watch_url,
                price=price,
                seller=listing.get("seller", ""),
                seller_rating=listing.get("seller_rating"),
                condition=listing.get("condition", ""),
                listing_url=listing.get("url", watch_url),
            )
            if deal_id:
                items.append({"id": deal_id, "name": listing.get("title", ""), "price": price})

    return items


def parse_newreleases_webhook(payload: dict) -> list[dict]:
    """Parse NewReleases.io webhook payload into intel items.
    Payload: {"project": "...", "version": "...", "is_prerelease": false, ...}
    """
    items = []
    project = payload.get("project", "")
    version = payload.get("version", "")
    provider = payload.get("provider", "")
    url = payload.get("url", "")

    if project and version:
        title = f"New release: {project} v{version}"
        if payload.get("is_prerelease"):
            title += " (pre-release)"

        item_id = create_intel_item(
            title=title,
            source=f"newreleases.io/{provider}",
            url=url,
            raw_content=json.dumps(payload),
            source_type="official",
            category="api-change",
        )
        if item_id:
            items.append({"id": item_id, "title": title})

    return items


def parse_f5bot_webhook(payload: dict) -> list[dict]:
    """Parse F5Bot keyword alert payload into intel items.
    F5Bot sends email-style alerts; webhook payload varies.
    """
    items = []
    alerts = payload.get("alerts", [])
    if not alerts and "title" in payload:
        alerts = [payload]

    for alert in alerts:
        title = alert.get("title", "")
        url = alert.get("url", alert.get("link", ""))
        keyword = alert.get("keyword", "")
        source_site = alert.get("source", alert.get("site", "reddit"))

        if not title:
            continue

        item_id = create_intel_item(
            title=title,
            source=f"F5Bot/{source_site} ({keyword})",
            url=url,
            raw_content=alert.get("content", alert.get("body", "")),
            source_type=_classify_source_type(source_site, url),
        )
        if item_id:
            items.append({"id": item_id, "title": title})

    return items


# --- Pollers ---

def poll_anthropic_models() -> list[dict]:
    """Poll Anthropic Models API, compare against last snapshot, create intel items for changes."""
    if not ANTHROPIC_API_KEY or not httpx:
        logger.warning("Models poller: missing ANTHROPIC_API_KEY or httpx")
        return []

    try:
        resp = httpx.get(
            ANTHROPIC_MODELS_URL,
            params={"limit": 1000},
            headers={
                "x-api-key": ANTHROPIC_API_KEY,
                "anthropic-version": "2023-06-01",
            },
            timeout=15.0,
        )
        resp.raise_for_status()
        data = resp.json()
    except Exception as e:
        logger.error(f"Models API poll failed: {e}")
        return []

    models = {m["id"]: m for m in data.get("data", [])}
    last_snap = get_last_model_snapshot()
    items_created = []

    if last_snap:
        old_models = last_snap["snapshot"]
        old_ids = set(old_models.keys())
        new_ids = set(models.keys())

        # New models
        for model_id in new_ids - old_ids:
            model = models[model_id]
            title = f"New Anthropic model: {model_id}"
            item_id = create_intel_item(
                title=title,
                source="Anthropic Models API",
                url=f"https://docs.anthropic.com/en/docs/about-claude/models",
                raw_content=json.dumps(model),
                source_type="official",
                category="model-release",
            )
            if item_id:
                items_created.append({"id": item_id, "title": title})

        # Removed/deprecated models
        for model_id in old_ids - new_ids:
            title = f"Model removed/deprecated: {model_id}"
            item_id = create_intel_item(
                title=title,
                source="Anthropic Models API",
                raw_content=json.dumps(old_models[model_id]),
                source_type="official",
                category="api-change",
            )
            if item_id:
                items_created.append({"id": item_id, "title": title})

        diff = []
        if new_ids - old_ids:
            diff.append(f"Added: {', '.join(new_ids - old_ids)}")
        if old_ids - new_ids:
            diff.append(f"Removed: {', '.join(old_ids - new_ids)}")
        diff_summary = "; ".join(diff) if diff else "No changes"
    else:
        diff_summary = f"Initial snapshot: {len(models)} models"

    save_model_snapshot(models, diff_summary)
    return items_created


def poll_package_versions() -> list[dict]:
    """Poll npm and PyPI for version changes."""
    if not httpx:
        logger.warning("Package poller: httpx not installed")
        return []

    items_created = []
    conn = _get_intel_db()

    # npm packages
    for pkg in TRACKED_NPM_PACKAGES:
        try:
            resp = httpx.get(
                f"https://registry.npmjs.org/{pkg}/latest",
                timeout=10.0,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            version = data.get("version", "")

            stored = conn.execute(
                "SELECT version FROM package_versions WHERE package_name = ? AND registry = ?",
                (pkg, "npm")
            ).fetchone()

            if stored and stored["version"] == version:
                continue

            # Update or insert version record
            if stored:
                conn.execute(
                    "UPDATE package_versions SET version = ?, checked_at = datetime('now') WHERE package_name = ? AND registry = ?",
                    (version, pkg, "npm")
                )
            else:
                conn.execute(
                    "INSERT INTO package_versions (package_name, registry, version) VALUES (?, ?, ?)",
                    (pkg, "npm", version)
                )
            conn.commit()

            if stored:  # Only create intel item if this is a version bump, not first check
                title = f"npm update: {pkg} v{version}"
                item_id = create_intel_item(
                    title=title,
                    source=f"npm/{pkg}",
                    url=f"https://www.npmjs.com/package/{pkg}",
                    source_type="official",
                    category="api-change",
                )
                if item_id:
                    items_created.append({"id": item_id, "title": title})

        except Exception as e:
            logger.error(f"npm poll failed for {pkg}: {e}")

    # PyPI packages
    for pkg in TRACKED_PYPI_PACKAGES:
        try:
            resp = httpx.get(
                f"https://pypi.org/pypi/{pkg}/json",
                timeout=10.0,
            )
            if resp.status_code != 200:
                continue
            data = resp.json()
            version = data.get("info", {}).get("version", "")

            stored = conn.execute(
                "SELECT version FROM package_versions WHERE package_name = ? AND registry = ?",
                (pkg, "pypi")
            ).fetchone()

            if stored and stored["version"] == version:
                continue

            if stored:
                conn.execute(
                    "UPDATE package_versions SET version = ?, checked_at = datetime('now') WHERE package_name = ? AND registry = ?",
                    (version, pkg, "pypi")
                )
            else:
                conn.execute(
                    "INSERT INTO package_versions (package_name, registry, version) VALUES (?, ?, ?)",
                    (pkg, "pypi", version)
                )
            conn.commit()

            if stored:
                title = f"PyPI update: {pkg} v{version}"
                item_id = create_intel_item(
                    title=title,
                    source=f"pypi/{pkg}",
                    url=f"https://pypi.org/project/{pkg}/",
                    source_type="official",
                    category="api-change",
                )
                if item_id:
                    items_created.append({"id": item_id, "title": title})

        except Exception as e:
            logger.error(f"PyPI poll failed for {pkg}: {e}")

    conn.close()
    return items_created


# --- Background Cron ---

def _models_poller_loop():
    """Background thread: poll Anthropic Models API every 6 hours."""
    while True:
        try:
            results = poll_anthropic_models()
            if results:
                logger.info(f"Models poller: created {len(results)} items")
        except Exception as e:
            logger.error(f"Models poller error: {e}")
        time.sleep(MODELS_POLL_INTERVAL)


def _package_poller_loop():
    """Background thread: poll npm/PyPI every 2 hours."""
    while True:
        try:
            results = poll_package_versions()
            if results:
                logger.info(f"Package poller: created {len(results)} items")
        except Exception as e:
            logger.error(f"Package poller error: {e}")
        time.sleep(PACKAGE_POLL_INTERVAL)


# --- Tier Classification ---

VALID_IMPROVEMENT_TYPES = {"fix", "upgrade", "new_capability", "new_skill", "research"}


def compute_tier(item: dict, kind: str = "item") -> int:
    """Classify an intel item or improvement into tiers 1-4.

    kind="item" — uses intel_items fields (priority, category, br3_improvement)
    kind="improvement" — uses intel_improvements fields (complexity, type) + optional source item
    """
    if kind == "item":
        priority = (item.get("priority") or "").lower()
        category = (item.get("category") or "").lower()
        br3_improvement = item.get("br3_improvement", 0)
        item_type = (item.get("type") or "").lower()

        if priority == "critical" and category == "security":
            return 1
        if br3_improvement and priority in ("critical", "high"):
            return 2
        if category == "new_capability" or item_type == "community-tool":
            return 3
        return 4

    elif kind == "improvement":
        complexity = (item.get("complexity") or "medium").lower()
        imp_type = (item.get("type") or "fix").lower()
        # Source item priority (caller should join if needed)
        src_priority = (item.get("source_priority") or "").lower()
        has_deadline = bool(item.get("has_deadline"))

        if complexity == "simple" and (src_priority == "critical" or has_deadline):
            return 1
        if complexity in ("simple", "medium") and src_priority in ("critical", "high"):
            return 2
        if imp_type in ("new_capability", "new_skill", "research"):
            return 3
        return 4

    return 4


# --- Improvement CRUD ---

def create_improvement(title: str, rationale: str, complexity: str,
                       setlist_prompt: str, affected_files: list = None,
                       source_intel_id: int = None,
                       overlap_action: str = None,
                       overlap_notes: str = None,
                       type: str = "fix") -> int:
    """Create a new improvement record from Opus intel review."""
    if type not in VALID_IMPROVEMENT_TYPES:
        type = "fix"
    conn = _get_intel_db()
    cursor = conn.execute(
        """INSERT INTO intel_improvements
           (title, rationale, complexity, setlist_prompt, affected_files,
            source_intel_id, overlap_action, overlap_notes, type)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, rationale, complexity, setlist_prompt,
         json.dumps(affected_files) if affected_files else None,
         source_intel_id, overlap_action, overlap_notes, type)
    )
    conn.commit()
    imp_id = cursor.lastrowid
    conn.close()
    return imp_id


def get_improvements(status: str = None, limit: int = 50) -> list[dict]:
    """Get improvements filtered by status."""
    conn = _get_intel_db()
    conditions = []
    params = []
    if status:
        statuses = [s.strip() for s in status.split(",")]
        placeholders = ",".join("?" * len(statuses))
        conditions.append(f"status IN ({placeholders})")
        params.extend(statuses)
    where = " AND ".join(conditions) if conditions else "1=1"
    query = f"""SELECT * FROM intel_improvements WHERE {where}
                ORDER BY created_at DESC LIMIT ?"""
    params.append(limit)
    rows = conn.execute(query, params).fetchall()
    conn.close()
    results = []
    for r in rows:
        d = dict(r)
        if d.get("affected_files"):
            try:
                d["affected_files"] = json.loads(d["affected_files"])
            except (json.JSONDecodeError, TypeError):
                pass
        results.append(d)
    return results


def mark_improvement_auto_acted(improvement_id: int, log: str) -> bool:
    """Mark an improvement as auto-acted and store the execution log."""
    conn = _get_intel_db()
    conn.execute(
        "UPDATE intel_improvements SET auto_acted = 1, auto_act_log = ? WHERE id = ?",
        (log, improvement_id)
    )
    conn.commit()
    changed = conn.total_changes > 0
    conn.close()
    return changed


def update_improvement_status(improvement_id: int, status: str,
                              build_spec_name: str = None) -> bool:
    """Update improvement status (pending -> planned -> built -> archived)."""
    conn = _get_intel_db()
    if build_spec_name:
        conn.execute(
            "UPDATE intel_improvements SET status = ?, build_spec_name = ? WHERE id = ?",
            (status, build_spec_name, improvement_id)
        )
    else:
        conn.execute(
            "UPDATE intel_improvements SET status = ? WHERE id = ?",
            (status, improvement_id)
        )
    conn.commit()
    changed = conn.total_changes > 0
    conn.close()
    return changed


def opus_review_intel_item(item_id: int, opus_synthesis: str,
                           br3_improvement: bool = False) -> bool:
    """Write Opus review back to an intel item."""
    conn = _get_intel_db()
    conn.execute(
        """UPDATE intel_items SET opus_synthesis = ?, br3_improvement = ?,
           opus_reviewed = 1 WHERE id = ?""",
        (opus_synthesis, 1 if br3_improvement else 0, item_id)
    )
    conn.commit()
    changed = conn.total_changes > 0
    conn.close()
    return changed


def opus_review_deal_item(item_id: int, opus_assessment: str) -> bool:
    """Write Opus review back to a deal item."""
    conn = _get_intel_db()
    conn.execute(
        """UPDATE deal_items SET opus_assessment = ?, opus_reviewed = 1 WHERE id = ?""",
        (opus_assessment, item_id)
    )
    conn.commit()
    changed = conn.total_changes > 0
    conn.close()
    return changed


def start_pollers():
    """Start background polling threads."""
    t1 = threading.Thread(target=_models_poller_loop, daemon=True, name="models-poller")
    t1.start()
    t2 = threading.Thread(target=_package_poller_loop, daemon=True, name="package-poller")
    t2.start()
    logger.info("Started background pollers: models (6h), packages (2h)")
    return [t1, t2]
