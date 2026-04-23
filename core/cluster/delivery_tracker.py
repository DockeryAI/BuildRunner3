"""
BR3 Cluster — 17track Delivery Tracker Service (Walter)
Polls 17track API for delivery status updates on purchased items with tracking numbers.
Updates Lockwood via PATCH /api/deals/items/{id}.

Run: python -m core.cluster.delivery_tracker
Deploy to Walter: scp + systemd timer or integrate into hunt_sourcer scheduling
"""

import asyncio
import json
import logging
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

from core.cluster.cluster_config import get_jimmy_semantic_url
from core.cluster.utils import rate_limit_lock

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# --- Config ---
CONFIG_PATH = Path(__file__).parent / "hunt_sourcer_config.json"
JIMMY_URL = get_jimmy_semantic_url()  # single source of truth — core/cluster/cluster_config.py
TRACK17_API_KEY = os.environ.get("TRACK17_API_KEY", "")
TRACK17_BASE_URL = "https://api.17track.net/track/v2.2"
MAX_BATCH_SIZE = 40  # 17track limit per request
MAX_API_CALLS_PER_DAY = 100

# 17track status code → our delivery_status mapping
# See https://api.17track.net/track/v2.2 status codes:
#   0=NotFound, 10=InTransit, 20=Expired, 30=PickedUp, 35=Undelivered,
#   40=Delivered, 50=Alert/Exception
TRACK17_STATUS_MAP = {
    0: "ordered",         # NotFound — registered but no scan yet
    10: "in_transit",     # InTransit
    20: "shipped",        # Expired — was shipped but tracking stale
    30: "shipped",        # PickedUp — carrier has it
    35: "out_for_delivery",  # Undelivered — attempted delivery
    40: "delivered",      # Delivered
    50: "in_transit",     # Alert — exception, keep as in_transit
}

# Sub-status refinements (17track sub_status field)
# 1001=InfoReceived → ordered, 1002=InTransit, 1003=OutForDelivery, 1004=DeliveryFailed
TRACK17_SUB_STATUS_MAP = {
    1001: "ordered",
    1002: "in_transit",
    1003: "out_for_delivery",
    1004: "out_for_delivery",  # failed attempt, still out
}


def _load_config() -> dict:
    """Load tracker configuration from hunt_sourcer_config.json."""
    if CONFIG_PATH.exists():
        return json.loads(CONFIG_PATH.read_text())
    return {}


def _get_tracking_config() -> dict:
    """Get delivery_tracking section from config."""
    config = _load_config()
    return config.get("delivery_tracking", {
        "enabled": True,
        "check_interval_hours": 4,
        "api_key_env": "TRACK17_API_KEY",
    })


def _now_iso() -> str:
    """Current time as ISO 8601 string."""
    return datetime.now(timezone.utc).isoformat()


# --- Lockwood Client ---

async def _get_trackable_items() -> list[dict]:
    """Fetch items with tracking numbers that aren't delivered yet."""
    if not httpx:
        logger.error("httpx not installed — cannot query Lockwood")
        return []

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.get(
                f"{JIMMY_URL}/api/deals/items",
                params={"ready_only": "false", "limit": 500},
            )
            resp.raise_for_status()
            items = resp.json().get("items", [])

            # Filter: has tracking number AND not yet delivered
            trackable = [
                item for item in items
                if item.get("tracking_number")
                and item.get("delivery_status") != "delivered"
            ]

            logger.info(f"Found {len(trackable)} trackable items (of {len(items)} total)")
            return trackable
    except Exception as e:
        logger.error(f"Failed to fetch items from Lockwood: {e}")
        return []


async def _update_item_status(item_id: int, delivery_status: str,
                               carrier: str = None,
                               delivery_updated_at: str = None) -> bool:
    """Update a deal item's delivery status via Lockwood API."""
    if not httpx:
        return False

    fields = {"delivery_status": delivery_status}
    if carrier:
        fields["carrier"] = carrier
    if delivery_updated_at:
        fields["delivery_updated_at"] = delivery_updated_at

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            resp = await client.patch(
                f"{JIMMY_URL}/api/deals/items/{item_id}",
                json=fields,
            )
            if resp.status_code == 200:
                logger.info(f"  Item {item_id} → {delivery_status}" +
                           (f" (carrier: {carrier})" if carrier else ""))
                return True
            else:
                logger.warning(f"  Update item {item_id} failed: {resp.status_code} {resp.text}")
                return False
    except Exception as e:
        logger.error(f"  Update item {item_id} failed: {e}")
        return False


# --- 17track API ---

def _track17_headers() -> dict:
    """Build 17track API headers."""
    api_key = TRACK17_API_KEY or os.environ.get("TRACK17_API_KEY", "")
    if not api_key:
        raise ValueError("TRACK17_API_KEY not set")
    return {
        "17token": api_key,
        "Content-Type": "application/json",
    }


async def _register_tracking_numbers(numbers: list[dict]) -> dict:
    """Register tracking numbers with 17track (batch, up to 40).

    Args:
        numbers: list of {"number": "...", "carrier": 0} dicts
                 carrier=0 means auto-detect

    Returns:
        17track response dict
    """
    if not httpx or not numbers:
        return {}

    # Chunk into batches of MAX_BATCH_SIZE
    results = {}
    for i in range(0, len(numbers), MAX_BATCH_SIZE):
        batch = numbers[i:i + MAX_BATCH_SIZE]
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{TRACK17_BASE_URL}/register",
                    headers=_track17_headers(),
                    json=batch,
                )
                resp.raise_for_status()
                data = resp.json()
                accepted = data.get("data", {}).get("accepted", [])
                rejected = data.get("data", {}).get("rejected", [])
                logger.info(f"  Register batch: {len(accepted)} accepted, {len(rejected)} rejected")
                for item in rejected:
                    logger.debug(f"    Rejected: {item.get('number')} — {item.get('error', {}).get('message', 'unknown')}")
                results.update({item["number"]: item for item in accepted})
        except Exception as e:
            logger.error(f"  17track register failed: {e}")

    return results


async def _get_tracking_info(numbers: list[dict]) -> list[dict]:
    """Query tracking status from 17track (batch, up to 40).

    Args:
        numbers: list of {"number": "..."} dicts

    Returns:
        list of tracking info dicts from 17track
    """
    if not httpx or not numbers:
        return []

    all_results = []
    for i in range(0, len(numbers), MAX_BATCH_SIZE):
        batch = numbers[i:i + MAX_BATCH_SIZE]
        try:
            async with httpx.AsyncClient(timeout=30.0) as client:
                resp = await client.post(
                    f"{TRACK17_BASE_URL}/gettrackinfo",
                    headers=_track17_headers(),
                    json=batch,
                )
                resp.raise_for_status()
                data = resp.json()
                accepted = data.get("data", {}).get("accepted", [])
                all_results.extend(accepted)
                logger.info(f"  Tracking info batch: {len(accepted)} results")
        except Exception as e:
            logger.error(f"  17track gettrackinfo failed: {e}")

    return all_results


def _map_status(track_info: dict) -> tuple[str, Optional[str]]:
    """Map 17track tracking info to our delivery_status and carrier.

    Returns:
        (delivery_status, carrier_name)
    """
    package = track_info.get("package", {})
    latest_status = package.get("latest_status", 0)
    latest_sub_status = package.get("latest_sub_status")

    # Sub-status is more specific, prefer it
    if latest_sub_status and latest_sub_status in TRACK17_SUB_STATUS_MAP:
        status = TRACK17_SUB_STATUS_MAP[latest_sub_status]
    else:
        status = TRACK17_STATUS_MAP.get(latest_status, "shipped")

    # Carrier detection — 17track returns carrier code
    carrier_code = track_info.get("carrier", 0)
    carrier_name = track_info.get("carrier_name") or _carrier_code_to_name(carrier_code)

    return status, carrier_name


def _carrier_code_to_name(code: int) -> Optional[str]:
    """Map common 17track carrier codes to human names."""
    carriers = {
        100001: "UPS",
        100002: "FedEx",
        100003: "USPS",
        21051: "DHL",
        190271: "Amazon Logistics",
        100088: "OnTrac",
        100049: "LaserShip",
    }
    return carriers.get(code)


# --- Main Check Cycle ---

# Track daily API call count (resets at midnight UTC)
_daily_calls = 0
_daily_reset_date = ""


def _check_rate_limit() -> bool:
    """Check if we're within the daily API call limit. Thread-safe."""
    global _daily_calls, _daily_reset_date
    with rate_limit_lock:
        today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
        if today != _daily_reset_date:
            _daily_calls = 0
            _daily_reset_date = today
        return _daily_calls < MAX_API_CALLS_PER_DAY


def _increment_rate_limit(count: int = 1):
    """Increment daily API call counter. Thread-safe."""
    global _daily_calls
    with rate_limit_lock:
        _daily_calls += count


async def check_deliveries_once():
    """Run one delivery check cycle.

    1. Fetch trackable items from Lockwood
    2. Register any new tracking numbers with 17track
    3. Query status for all tracked numbers
    4. Update items with new status/carrier
    """
    tracking_config = _get_tracking_config()
    if not tracking_config.get("enabled", True):
        logger.debug("Delivery tracking disabled in config")
        return

    api_key = os.environ.get(tracking_config.get("api_key_env", "TRACK17_API_KEY"), "")
    if not api_key and not TRACK17_API_KEY:
        logger.warning("No 17track API key configured — skipping delivery check")
        return

    if not _check_rate_limit():
        logger.warning(f"Daily rate limit reached ({MAX_API_CALLS_PER_DAY} calls) — skipping")
        return

    # Step 1: Get items with tracking numbers
    items = await _get_trackable_items()
    if not items:
        logger.debug("No trackable items to check")
        return

    # Build lookup: tracking_number → item(s)
    tracking_map: dict[str, list[dict]] = {}
    for item in items:
        tn = item["tracking_number"].strip()
        if tn not in tracking_map:
            tracking_map[tn] = []
        tracking_map[tn].append(item)

    tracking_numbers = list(tracking_map.keys())
    logger.info(f"Checking {len(tracking_numbers)} unique tracking numbers")

    # Step 2: Register tracking numbers (idempotent — 17track ignores already-registered)
    register_payload = [{"number": tn, "carrier": 0} for tn in tracking_numbers]
    await _register_tracking_numbers(register_payload)
    _increment_rate_limit(len(range(0, len(register_payload), MAX_BATCH_SIZE)))

    # Step 3: Query status
    query_payload = [{"number": tn} for tn in tracking_numbers]
    tracking_results = await _get_tracking_info(query_payload)
    _increment_rate_limit(len(range(0, len(query_payload), MAX_BATCH_SIZE)))

    # Step 4: Update items
    updated = 0
    for result in tracking_results:
        tn = result.get("number", "")
        if tn not in tracking_map:
            continue

        new_status, carrier = _map_status(result)
        now_iso = _now_iso()

        for item in tracking_map[tn]:
            old_status = item.get("delivery_status", "none")
            old_carrier = item.get("carrier")

            # Only update if status changed or carrier was detected
            if new_status != old_status or (carrier and carrier != old_carrier):
                success = await _update_item_status(
                    item_id=item["id"],
                    delivery_status=new_status,
                    carrier=carrier,
                    delivery_updated_at=now_iso,
                )
                if success:
                    updated += 1

    logger.info(f"Delivery check complete: {len(tracking_results)} tracked, {updated} updated")


async def run_forever():
    """Main loop: check deliveries on configured interval."""
    tracking_config = _get_tracking_config()
    interval_hours = tracking_config.get("check_interval_hours", 4)
    interval_secs = interval_hours * 3600

    logger.info(f"Delivery tracker starting — checking every {interval_hours}h")
    logger.info(f"Lockwood: {JIMMY_URL}")
    logger.info(f"Daily API limit: {MAX_API_CALLS_PER_DAY}")

    while True:
        try:
            await check_deliveries_once()
        except Exception as e:
            logger.error(f"Delivery check cycle error: {e}")
        await asyncio.sleep(interval_secs)


_tracker_thread = None


def start_tracker_cron():
    """Start the tracker as a background thread (for embedding in hunt_sourcer).
    Thread-safe: only one tracker runs at a time.
    """
    global _tracker_thread
    import threading

    if _tracker_thread and _tracker_thread.is_alive():
        logger.info("Delivery tracker already running")
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
            logger.error(f"Delivery tracker crashed: {e}")
        finally:
            loop.close()

    _tracker_thread = threading.Thread(target=_run, daemon=True, name="delivery-tracker")
    _tracker_thread.start()
    logger.info("Delivery tracker started in background thread")


def main():
    """Entry point for standalone execution."""
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    )
    asyncio.run(run_forever())


if __name__ == "__main__":
    main()
