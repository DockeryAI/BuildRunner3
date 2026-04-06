"""
BR3 Cluster — changedetection.io Watch Manager
Auto-creates and removes watches when hunts are created/archived.

changedetection.io runs on Lockwood port 5000.
API docs: https://changedetection.io/docs/api
"""

import json
import logging
import os
from typing import Optional
from pathlib import Path

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# changedetection.io instance on Lockwood
CHANGEDETECTION_URL = os.environ.get("CHANGEDETECTION_URL", "http://localhost:5000")
CHANGEDETECTION_API_KEY = os.environ.get("CHANGEDETECTION_API_KEY", "")

# Lockwood's own webhook URL for receiving change notifications
WEBHOOK_URL = os.environ.get(
    "HUNT_WEBHOOK_URL",
    "http://10.0.1.101:8100/api/deals/webhook/changedetection"
)

# Load selector config from hunt_sourcer_config.json
CONFIG_PATH = Path(__file__).parent / "hunt_sourcer_config.json"

# CSS selectors per source type for extracting listing data
DEFAULT_SELECTORS = {
    "ebay.com": {
        "css_selector": ".s-item",
        "title_selector": ".s-item__title",
        "price_selector": ".s-item__price",
        "link_selector": ".s-item__link",
    },
    "newegg.com": {
        "css_selector": ".item-cell",
        "title_selector": ".item-title",
        "price_selector": ".price-current",
        "link_selector": ".item-title",
    },
    "craigslist.org": {
        "css_selector": ".result-row",
        "title_selector": ".result-title",
        "price_selector": ".result-price",
        "link_selector": ".result-title",
    },
    "reddit.com": {
        "css_selector": ".Post",
        "title_selector": "h3",
        "price_selector": None,
        "link_selector": "a",
    },
}


def _get_selectors() -> dict:
    """Load CSS selectors from config, falling back to defaults."""
    if CONFIG_PATH.exists():
        try:
            config = json.loads(CONFIG_PATH.read_text())
            return config.get("selectors", DEFAULT_SELECTORS)
        except (json.JSONDecodeError, KeyError):
            pass
    return DEFAULT_SELECTORS


def _match_selector(url: str) -> Optional[dict]:
    """Find the best matching CSS selector config for a URL."""
    selectors = _get_selectors()
    url_lower = url.lower()
    for domain, sel_config in selectors.items():
        if domain in url_lower:
            return sel_config
    return None


def _headers() -> dict:
    """Build API request headers."""
    h = {"Content-Type": "application/json"}
    if CHANGEDETECTION_API_KEY:
        h["x-api-key"] = CHANGEDETECTION_API_KEY
    return h


async def create_watches_for_hunt(
    hunt_id: int,
    source_urls: list[str],
    check_interval_minutes: int = 60,
) -> list[dict]:
    """Create changedetection.io watches for each source URL.

    Args:
        hunt_id: The hunt ID (used in webhook context)
        source_urls: List of URLs to watch
        check_interval_minutes: How often to check (mapped to seconds)

    Returns:
        List of {"url": ..., "uuid": ..., "status": "created"|"error"} dicts
    """
    if not httpx:
        logger.warning("httpx not installed — cannot create watches")
        return []

    results = []
    check_seconds = check_interval_minutes * 60

    for url in source_urls:
        try:
            # Check if watch already exists
            existing_uuid = await _find_existing_watch(url)
            if existing_uuid:
                logger.info(f"Watch already exists for {url}: {existing_uuid}")
                results.append({"url": url, "uuid": existing_uuid, "status": "exists"})
                continue

            # Build watch config
            sel_config = _match_selector(url)
            watch_body = {
                "url": url,
                "title": f"Hunt #{hunt_id}",
                "time_between_check": {"seconds": check_seconds},
                "notification_urls": [WEBHOOK_URL],
                "tags": [f"hunt-{hunt_id}"],
            }

            # Add CSS selector if we have one for this domain
            if sel_config and sel_config.get("css_selector"):
                watch_body["include_filters"] = [sel_config["css_selector"]]

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.post(
                    f"{CHANGEDETECTION_URL}/api/v1/watch",
                    headers=_headers(),
                    json=watch_body,
                )

                if resp.status_code in (200, 201):
                    data = resp.json()
                    uuid = data.get("uuid", "")
                    logger.info(f"Created watch for {url}: {uuid}")
                    results.append({"url": url, "uuid": uuid, "status": "created"})
                else:
                    logger.warning(f"Failed to create watch for {url}: {resp.status_code} {resp.text}")
                    results.append({"url": url, "uuid": None, "status": "error"})

        except Exception as e:
            logger.error(f"Error creating watch for {url}: {e}")
            results.append({"url": url, "uuid": None, "status": "error"})

    return results


async def delete_watches_for_hunt(source_urls: list[str]) -> list[dict]:
    """Delete changedetection.io watches for archived hunt URLs.

    Args:
        source_urls: List of URLs to stop watching

    Returns:
        List of {"url": ..., "status": "deleted"|"not_found"|"error"} dicts
    """
    if not httpx:
        return []

    results = []

    for url in source_urls:
        try:
            uuid = await _find_existing_watch(url)
            if not uuid:
                results.append({"url": url, "status": "not_found"})
                continue

            async with httpx.AsyncClient(timeout=10.0) as client:
                resp = await client.delete(
                    f"{CHANGEDETECTION_URL}/api/v1/watch/{uuid}",
                    headers=_headers(),
                )

                if resp.status_code in (200, 204):
                    logger.info(f"Deleted watch {uuid} for {url}")
                    results.append({"url": url, "status": "deleted"})
                else:
                    logger.warning(f"Failed to delete watch {uuid}: {resp.status_code}")
                    results.append({"url": url, "status": "error"})

        except Exception as e:
            logger.error(f"Error deleting watch for {url}: {e}")
            results.append({"url": url, "status": "error"})

    return results


async def _find_existing_watch(url: str) -> Optional[str]:
    """Find UUID of an existing watch by URL."""
    if not httpx:
        return None

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{CHANGEDETECTION_URL}/api/v1/watch",
                headers=_headers(),
            )

            if resp.status_code != 200:
                return None

            watches = resp.json()
            # watches is a dict of uuid -> watch_config
            url_lower = url.lower().rstrip("/")
            for uuid, watch in watches.items():
                watch_url = (watch.get("url", "") or "").lower().rstrip("/")
                if watch_url == url_lower:
                    return uuid

    except Exception as e:
        logger.warning(f"Error checking existing watches: {e}")

    return None
