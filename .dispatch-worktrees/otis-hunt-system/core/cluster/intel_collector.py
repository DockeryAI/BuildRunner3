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
    """Create tables from schema file."""
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
    """Insert a new deal item. Returns item ID."""
    conn = _get_intel_db()
    try:
        cursor = conn.execute(
            """INSERT INTO deal_items (hunt_id, name, category, attributes,
               source_url, price, condition, seller, seller_rating, listing_url)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (hunt_id, name, category, json.dumps(attributes) if attributes else None,
             source_url, price, condition, seller, seller_rating, listing_url)
        )
        conn.commit()
        deal_id = cursor.lastrowid

        # Create initial price history entry
        if price is not None:
            conn.execute(
                "INSERT INTO price_history (deal_item_id, price, source) VALUES (?, ?, ?)",
                (deal_id, price, source_url)
            )
            conn.commit()

        return deal_id
    finally:
        conn.close()


def get_deal_items(hunt_id: int = None, min_score: int = None,
                   limit: int = 50) -> list[dict]:
    """Query deal items with filters."""
    conn = _get_intel_db()
    conditions = ["dismissed = 0"]
    params = []

    if hunt_id is not None:
        conditions.append("hunt_id = ?")
        params.append(hunt_id)
    if min_score is not None:
        conditions.append("deal_score >= ?")
        params.append(min_score)

    where = " AND ".join(conditions)
    query = f"""SELECT * FROM deal_items WHERE {where}
                ORDER BY deal_score DESC NULLS LAST, collected_at DESC
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


def update_hunt(hunt_id: int, name: str = None, category: str = None,
                keywords: str = None, target_price: float = None,
                check_interval_minutes: int = None, source_urls: list = None) -> bool:
    """Update an existing hunt's fields."""
    conn = _get_intel_db()
    updates = []
    params = []
    if name is not None:
        updates.append("name = ?")
        params.append(name)
    if category is not None:
        updates.append("category = ?")
        params.append(category)
    if keywords is not None:
        updates.append("keywords = ?")
        params.append(keywords)
    if target_price is not None:
        updates.append("target_price = ?")
        params.append(target_price)
    if check_interval_minutes is not None:
        updates.append("check_interval_minutes = ?")
        params.append(check_interval_minutes)
    if source_urls is not None:
        updates.append("source_urls = ?")
        params.append(json.dumps(source_urls))
    if updates:
        params.append(hunt_id)
        conn.execute(
            f"UPDATE active_hunts SET {', '.join(updates)} WHERE id = ?",
            params
        )
        conn.commit()
    conn.close()
    return True


def archive_hunt(hunt_id: int) -> bool:
    conn = _get_intel_db()
    conn.execute("UPDATE active_hunts SET active = 0 WHERE id = ?", (hunt_id,))
    conn.commit()
    conn.close()
    return True


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


# --- Improvement CRUD ---

def create_improvement(title: str, rationale: str, complexity: str,
                       setlist_prompt: str, affected_files: list = None,
                       source_intel_id: int = None,
                       overlap_action: str = None,
                       overlap_notes: str = None) -> int:
    """Create a new improvement record from Opus intel review."""
    conn = _get_intel_db()
    cursor = conn.execute(
        """INSERT INTO intel_improvements
           (title, rationale, complexity, setlist_prompt, affected_files,
            source_intel_id, overlap_action, overlap_notes)
           VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
        (title, rationale, complexity, setlist_prompt,
         json.dumps(affected_files) if affected_files else None,
         source_intel_id, overlap_action, overlap_notes)
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
