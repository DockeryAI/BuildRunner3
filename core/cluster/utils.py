"""
BR3 Cluster — Shared Utilities
Common functions used across cluster modules.
"""

import hashlib
import math
import re
import threading
import logging

logger = logging.getLogger(__name__)


def url_hash(url: str) -> str:
    """Generate 16-char hash of normalized URL for deduplication."""
    return hashlib.sha256(url.strip().lower().encode()).hexdigest()[:16]


def cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 > 0 and mag2 > 0:
        return dot / (mag1 * mag2)
    return 0.0


# Tech indicator regex for hallucination filtering (hardware products)
TECH_INDICATOR_PATTERN = re.compile(
    r'\d|GB|TB|MHz|GHz|DDR|RTX|GTX|NVLink|USB|SSD|NVMe|PCIe|HDMI|'
    r'Corsair|EVGA|ASUS|MSI|Gigabyte|Crucial|Minisforum|PNY',
    re.IGNORECASE
)


def filter_hallucinations(listings: list[dict], source_name: str, hunt_name: str) -> list[dict]:
    """Filter LLM-extracted listings that lack tech indicators (likely hallucinations).

    Args:
        listings: List of listing dicts with 'title' key
        source_name: Source identifier for logging (e.g., 'Newegg', 'B&H')
        hunt_name: Hunt name for logging context

    Returns:
        Filtered list with only listings containing tech indicators in title
    """
    if not listings:
        return listings

    real = [l for l in listings if TECH_INDICATOR_PATTERN.search(l.get("title", ""))]
    hallucinated = len(listings) - len(real)

    if hallucinated:
        logger.warning(f"{source_name} '{hunt_name}': dropped {hallucinated}/{len(listings)} titles lacking tech indicators")
        for l in listings:
            if not TECH_INDICATOR_PATTERN.search(l.get("title", "")):
                logger.debug(f"  Hallucination: '{l.get('title', '')}'")

    return real


# Thread-safe locks for shared state
last_checked_lock = threading.Lock()
rate_limit_lock = threading.Lock()
