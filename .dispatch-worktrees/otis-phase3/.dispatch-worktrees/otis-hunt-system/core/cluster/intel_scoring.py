"""
BR3 Cluster — Intel Scoring Pipeline (Phase 2)
Scores intel_items and deal_items via Below's Ollama (qwen3:8b).

Handles:
- Intel scoring: relevance/urgency/actionability 1-10, category, priority, summary
- Deal scoring: weighted 0-100 score, verdict, assessment
- Deduplication via URL hash + title embedding cosine similarity
- Confidence flagging: malformed responses -> needs_opus_review
- Exceptional deal Discord alerts (score 80+)
- Below offline fallback: skip scoring cycle, items accumulate
"""

import json
import logging
import math
import os
import time
import threading
from typing import Optional

try:
    import httpx
except ImportError:
    httpx = None

logger = logging.getLogger(__name__)

# --- Config ---
BELOW_OLLAMA_URL = os.environ.get("BELOW_OLLAMA_URL", "http://below.local:11434")
BELOW_MODEL = os.environ.get("BELOW_MODEL", "qwen3:8b")
BELOW_CONNECT_TIMEOUT = float(os.environ.get("BELOW_CONNECT_TIMEOUT", "3"))
BELOW_REQUEST_TIMEOUT = float(os.environ.get("BELOW_REQUEST_TIMEOUT", "60"))
DISCORD_DEAL_WEBHOOK_URL = os.environ.get("DISCORD_DEAL_WEBHOOK_URL", "")
SCORING_INTERVAL = int(os.environ.get("SCORING_INTERVAL", "1800"))  # 30 minutes
DEDUP_SIMILARITY_THRESHOLD = float(os.environ.get("DEDUP_SIMILARITY_THRESHOLD", "0.92"))

# Valid values
VALID_CATEGORIES = {
    "api-change", "model-release", "community-tool",
    "ecosystem-news", "cluster-relevant", "general-news",
}
VALID_PRIORITIES = {"critical", "high", "medium", "low"}
VALID_VERDICTS = {"exceptional", "good", "fair", "pass"}


# --- Below Client ---

async def _call_below_chat(
    prompt: str,
    system: str = "",
    json_mode: bool = True,
    max_tokens: int = 500,
) -> Optional[str]:
    """Call Below's Ollama /api/chat endpoint. Returns response text or None on failure."""
    if not httpx:
        logger.warning("httpx not installed — cannot call Below")
        return None

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(BELOW_REQUEST_TIMEOUT, connect=BELOW_CONNECT_TIMEOUT)
        ) as client:
            messages = []
            if system:
                messages.append({"role": "system", "content": system})
            messages.append({"role": "user", "content": prompt})

            payload = {
                "model": BELOW_MODEL,
                "messages": messages,
                "stream": False,
                "think": False,
                "options": {"num_predict": max_tokens, "temperature": 0},
            }
            if json_mode:
                payload["format"] = "json"

            resp = await client.post(f"{BELOW_OLLAMA_URL}/api/chat", json=payload)
            resp.raise_for_status()
            data = resp.json()
            return data.get("message", {}).get("content", "")
    except Exception as e:
        logger.warning(f"Below unreachable or error: {e}")
        return None


async def _call_below_embed(text: str) -> Optional[list[float]]:
    """Get embeddings from Below's Ollama /api/embed endpoint."""
    if not httpx:
        return None

    try:
        async with httpx.AsyncClient(
            timeout=httpx.Timeout(BELOW_REQUEST_TIMEOUT, connect=BELOW_CONNECT_TIMEOUT)
        ) as client:
            resp = await client.post(
                f"{BELOW_OLLAMA_URL}/api/embed",
                json={"model": BELOW_MODEL, "input": text},
            )
            resp.raise_for_status()
            data = resp.json()
            embeddings = data.get("embeddings", [])
            if embeddings:
                return embeddings[0]
            return None
    except Exception as e:
        logger.warning(f"Below embed failed: {e}")
        return None


# --- Cosine Similarity ---

def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    """Compute cosine similarity between two vectors."""
    if len(v1) != len(v2) or not v1:
        return 0.0
    dot = sum(a * b for a, b in zip(v1, v2))
    mag1 = math.sqrt(sum(a * a for a in v1))
    mag2 = math.sqrt(sum(b * b for b in v2))
    if mag1 == 0 or mag2 == 0:
        return 0.0
    return dot / (mag1 * mag2)


# --- Intel Scoring ---

def _build_intel_prompt(item: dict) -> str:
    """Build the scoring prompt for an intel item."""
    title = item.get("title", "")
    source = item.get("source", "")
    raw_content = item.get("raw_content", "")

    # Truncate raw_content to avoid huge prompts
    if raw_content and len(raw_content) > 2000:
        raw_content = raw_content[:2000] + "..."

    return f"""Score this intelligence item for a software development cluster (BR3).

Title: {title}
Source: {source}
Content: {raw_content}

Respond with JSON only:
{{
  "relevance": <1-10, how relevant to Claude/Anthropic/AI development>,
  "urgency": <1-10, how time-sensitive>,
  "actionability": <1-10, how actionable for a dev team>,
  "category": <one of: api-change, model-release, community-tool, ecosystem-news, cluster-relevant, general-news>,
  "priority": <one of: critical, high, medium, low>,
  "summary": <one-line summary of what this is and why it matters>
}}"""


def _parse_intel_score(response: str) -> Optional[dict]:
    """Parse Below's intel scoring response. Returns dict or None if malformed."""
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None

    # Validate required fields
    required = ["relevance", "urgency", "actionability", "category", "priority", "summary"]
    if not all(k in data for k in required):
        return None

    # Validate numeric ranges
    for field in ["relevance", "urgency", "actionability"]:
        val = data[field]
        if not isinstance(val, (int, float)) or val < 1 or val > 10:
            return None

    # Validate categorical values
    if data["category"] not in VALID_CATEGORIES:
        return None
    if data["priority"] not in VALID_PRIORITIES:
        return None
    if not isinstance(data["summary"], str) or not data["summary"].strip():
        return None

    # Compute composite score (average of three dimensions, rounded)
    score = round((data["relevance"] + data["urgency"] + data["actionability"]) / 3)

    return {
        "score": score,
        "priority": data["priority"],
        "category": data["category"],
        "summary": data["summary"].strip(),
    }


# --- Deal Scoring ---

# TCO adjustments — known accessory costs that affect true deal value
TCO_ADJUSTMENTS = {
    "blower": {"cost": 80, "reason": "blower cooler needs aftermarket replacement (~$80)"},
    "reference": {"cost": 60, "reason": "reference PCB may need thermal pad replacement (~$60)"},
    "founders edition": {"cost": 0, "reason": "FE cooler is adequate"},
    "ftw3": {"cost": 0, "reason": "premium cooler, no mods needed"},
    "gaming x trio": {"cost": 0, "reason": "good cooler, no mods needed"},
    "strix": {"cost": 0, "reason": "premium cooler, no mods needed"},
    "canada": {"cost": 400, "reason": "import duties + brokerage fees (~$400 CAD)"},
    "international": {"cost": 200, "reason": "international shipping + potential duties (~$200)"},
}

# Timing intelligence — known seasonal pricing patterns
TIMING_PATTERNS = {
    1: {"trend": "neutral", "note": "Post-holiday market, decent used prices"},
    2: {"trend": "neutral", "note": "Quiet period, steady prices"},
    3: {"trend": "neutral", "note": "Tax refund season — demand up slightly"},
    4: {"trend": "neutral", "note": "Pre-summer lull"},
    5: {"trend": "neutral", "note": "Quiet period before summer sales"},
    6: {"trend": "wait", "note": "Wait for Prime Day (mid-July) — prices often drop 10-15%"},
    7: {"trend": "wait", "note": "Prime Day mid-July — check for price drops"},
    8: {"trend": "neutral", "note": "Post-Prime Day, some residual deals"},
    9: {"trend": "wait", "note": "New GPU generations announce — used prices may drop"},
    10: {"trend": "wait", "note": "Pre-Black Friday — wait for November deals"},
    11: {"trend": "buy", "note": "Black Friday/Cyber Monday — best prices of the year"},
    12: {"trend": "neutral", "note": "Holiday demand drives prices up, but deals exist"},
}


def _get_timing_context() -> dict:
    """Get current timing context for deal assessment."""
    from datetime import datetime
    now = datetime.now()
    month = now.month
    return TIMING_PATTERNS.get(month, {"trend": "neutral", "note": ""})


def _calculate_tco(item: dict) -> dict:
    """Calculate total cost of ownership adjustments.

    Returns:
        {"extra_cost": float, "reasons": list[str], "effective_price": float}
    """
    name = (item.get("name", "") or "").lower()
    condition = (item.get("condition", "") or "").lower()
    seller = (item.get("seller", "") or "").lower()
    price = item.get("price") or 0

    extra_cost = 0
    reasons = []

    for keyword, adj in TCO_ADJUSTMENTS.items():
        if keyword in name or keyword in condition or keyword in seller:
            extra_cost += adj["cost"]
            if adj["cost"] > 0:
                reasons.append(adj["reason"])

    return {
        "extra_cost": extra_cost,
        "reasons": reasons,
        "effective_price": price + extra_cost,
    }


def _check_pair_availability(item: dict) -> dict:
    """Check if this deal is part of an available pair (NVLink requirement).

    Returns:
        {"pair_available": bool, "pair_count": int, "pair_seller": str}
    """
    attrs = item.get("attributes")
    if isinstance(attrs, str):
        try:
            attrs = json.loads(attrs)
        except (json.JSONDecodeError, TypeError):
            attrs = {}
    attrs = attrs or {}

    return {
        "pair_available": attrs.get("pair_available", False),
        "pair_count": attrs.get("pair_count", 0),
        "pair_seller": attrs.get("pair_seller", ""),
    }


def _build_deal_prompt(item: dict, hunt: dict) -> str:
    """Build the scoring prompt for a deal item with intelligence context."""
    name = item.get("name", "")
    price = item.get("price", "unknown")
    condition = item.get("condition", "unknown")
    seller = item.get("seller", "unknown")
    seller_rating = item.get("seller_rating", "unknown")
    target_price = hunt.get("target_price", "not set")
    category = hunt.get("category", "other")

    # Intelligence context
    tco = _calculate_tco(item)
    timing = _get_timing_context()
    pair_info = _check_pair_availability(item)

    tco_section = ""
    if tco["extra_cost"] > 0:
        tco_section = f"\nTCO Adjustments: +${tco['extra_cost']} ({'; '.join(tco['reasons'])})"
        tco_section += f"\nEffective Price (with TCO): ${tco['effective_price']}"

    pair_section = ""
    if pair_info["pair_available"]:
        pair_section = f"\nPair Available: YES — {pair_info['pair_count']} matching items from seller {pair_info['pair_seller']} (NVLink-critical)"

    timing_section = f"\nTiming: {timing['note']} (trend: {timing['trend']})"

    return f"""Score this deal for a hardware purchase.

Product: {name}
Category: {category}
Price: ${price}
Target Price: ${target_price}
Condition: {condition}
Seller: {seller}
Seller Rating: {seller_rating}{tco_section}{pair_section}{timing_section}

Score using this weighted formula:
- Price vs target price (0.30 weight) — use effective price (with TCO) if TCO adjustments exist
- Seller rating (0.20 weight)
- Condition quality (0.20 weight)
- Market context (0.15 weight) — rarity, pair availability, timing
- Scarcity/urgency (0.15 weight) — pair availability is high urgency for NVLink needs

If a pair is available from the same seller, boost score by 5-10 points.
If timing trend is "wait", note this but don't heavily penalize — the deal itself may still be good.

Respond with JSON only:
{{
  "score": <0-100>,
  "verdict": <one of: exceptional, good, fair, pass>,
  "assessment": <one-line assessment including TCO and timing context>,
  "timing_note": <one-line: buy now, wait, or neutral with reason>,
  "tco_note": <one-line: effective price and any hidden costs, or "no adjustments">
}}"""


def _parse_deal_score(response: str) -> Optional[dict]:
    """Parse Below's deal scoring response. Returns dict or None if malformed."""
    try:
        data = json.loads(response)
    except (json.JSONDecodeError, TypeError):
        return None

    required = ["score", "verdict", "assessment"]
    if not all(k in data for k in required):
        return None

    score = data["score"]
    if not isinstance(score, (int, float)) or score < 0 or score > 100:
        return None

    if data["verdict"] not in VALID_VERDICTS:
        return None

    if not isinstance(data["assessment"], str) or not data["assessment"].strip():
        return None

    result = {
        "score": int(score),
        "verdict": data["verdict"],
        "assessment": data["assessment"].strip(),
    }

    # Optional intelligence fields
    if "timing_note" in data and isinstance(data["timing_note"], str):
        result["timing_note"] = data["timing_note"].strip()
    if "tco_note" in data and isinstance(data["tco_note"], str):
        result["tco_note"] = data["tco_note"].strip()

    return result


# --- Confidence Flagging ---

def _flag_needs_opus_review(item_id: int, item_type: str = "intel"):
    """Flag an item as needing Opus review after scoring failure."""
    from core.cluster.intel_collector import _get_intel_db
    conn = _get_intel_db()
    try:
        if item_type == "intel":
            conn.execute(
                "UPDATE intel_items SET needs_opus_review = 1 WHERE id = ?",
                (item_id,)
            )
        elif item_type == "deal":
            conn.execute(
                "UPDATE deal_items SET needs_opus_review = 1 WHERE id = ?",
                (item_id,)
            )
        conn.commit()
    finally:
        conn.close()


# --- Deduplication ---

async def _check_duplicate_by_embedding(title: str, item_type: str = "intel") -> bool:
    """Check if a title is a semantic duplicate of recent items via Below embeddings.
    Returns True if duplicate found (cosine similarity > threshold).
    """
    from core.cluster.intel_collector import _get_intel_db
    conn = _get_intel_db()

    try:
        # Get recent titles from last 48h
        if item_type == "intel":
            rows = conn.execute(
                """SELECT title FROM intel_items
                   WHERE collected_at >= datetime('now', '-2 days')
                   AND scored = 1""",
            ).fetchall()
        else:
            rows = conn.execute(
                """SELECT name as title FROM deal_items
                   WHERE collected_at >= datetime('now', '-2 days')
                   AND deal_score IS NOT NULL""",
            ).fetchall()

        if not rows:
            return False

        # Get embedding for new title
        new_embedding = await _call_below_embed(title)
        if not new_embedding:
            return False  # Can't check — not a duplicate

        # Check against each recent title
        for row in rows:
            existing_embedding = await _call_below_embed(row["title"])
            if existing_embedding:
                sim = _cosine_similarity(new_embedding, existing_embedding)
                if sim > DEDUP_SIMILARITY_THRESHOLD:
                    logger.info(
                        f"Duplicate detected: '{title}' similar to '{row['title']}' "
                        f"(cosine={sim:.3f})"
                    )
                    return True

        return False
    finally:
        conn.close()


# --- Discord Alert ---

def _build_discord_alert_payload(deal: dict) -> dict:
    """Build Discord webhook payload for exceptional deal alert."""
    name = deal.get("name", "Unknown")
    price = deal.get("price", "?")
    score = deal.get("deal_score", 0)
    verdict = deal.get("verdict", "unknown")
    listing_url = deal.get("listing_url", "")
    assessment = deal.get("assessment", deal.get("below_assessment", ""))

    # Intelligence context
    tco = _calculate_tco(deal)
    timing = _get_timing_context()
    pair_info = _check_pair_availability(deal)

    desc_parts = [
        f"**Score:** {score}/100 ({verdict})",
        f"**Price:** ${price}",
    ]
    if tco["extra_cost"] > 0:
        desc_parts.append(f"**Effective Price (TCO):** ${tco['effective_price']}")
    if pair_info["pair_available"]:
        desc_parts.append(f"**Pair Available** from {pair_info['pair_seller']}")
    desc_parts.append(f"**Timing:** {timing['note']}")
    if assessment:
        desc_parts.append(f"**Assessment:** {assessment}")
    desc_parts.append(f"**Link:** {listing_url}")

    return {
        "embeds": [{
            "title": f"Deal Alert: {name}",
            "description": "\n".join(desc_parts),
            "color": 0x00FF00 if score >= 80 else 0xFFAA00,
            "footer": {"text": "BR3 Deal Tracker — Hunt System"},
        }]
    }


async def _send_discord_alert(deal: dict):
    """Send Discord webhook notification for exceptional deal."""
    webhook_url = os.environ.get("DISCORD_DEAL_WEBHOOK_URL", "")
    if not webhook_url or not httpx:
        return

    payload = _build_discord_alert_payload(deal)
    try:
        async with httpx.AsyncClient(timeout=httpx.Timeout(10.0, connect=3.0)) as client:
            resp = await client.post(webhook_url, json=payload)
            if resp.status_code >= 400:
                logger.warning(f"Discord webhook failed: {resp.status_code}")
    except Exception as e:
        logger.warning(f"Discord alert failed: {e}")


# --- Main Scoring Functions ---

async def score_intel_items() -> dict:
    """Score all unscored intel items via Below. Returns summary stats."""
    from core.cluster.intel_collector import _get_intel_db

    conn = _get_intel_db()
    unscored = conn.execute(
        "SELECT * FROM intel_items WHERE scored = 0 ORDER BY collected_at ASC"
    ).fetchall()
    conn.close()

    stats = {"total": len(unscored), "scored": 0, "flagged": 0, "duplicates": 0, "errors": 0}

    for row in unscored:
        item = dict(row)
        item_id = item["id"]

        # Deduplication check
        is_dup = await _check_duplicate_by_embedding(item["title"], "intel")
        if is_dup:
            # Mark as scored but with low priority to avoid re-processing
            conn = _get_intel_db()
            conn.execute(
                "UPDATE intel_items SET scored = 1, priority = 'low', "
                "summary = 'Duplicate — skipped scoring' WHERE id = ?",
                (item_id,)
            )
            conn.commit()
            conn.close()
            stats["duplicates"] += 1
            continue

        # Call Below for scoring
        prompt = _build_intel_prompt(item)
        response = await _call_below_chat(prompt)

        if response is None:
            # Below offline — stop this cycle, items stay unscored
            logger.warning("Below offline — stopping intel scoring cycle")
            stats["errors"] += 1
            break

        parsed = _parse_intel_score(response)

        conn = _get_intel_db()
        if parsed:
            conn.execute(
                """UPDATE intel_items SET scored = 1, score = ?, priority = ?,
                   category = ?, summary = ? WHERE id = ?""",
                (parsed["score"], parsed["priority"], parsed["category"],
                 parsed["summary"], item_id)
            )
            stats["scored"] += 1
        else:
            # Malformed response — flag for Opus review
            _flag_needs_opus_review(item_id, "intel")
            conn.execute(
                "UPDATE intel_items SET scored = 1 WHERE id = ?", (item_id,)
            )
            stats["flagged"] += 1
            logger.warning(f"Intel item {item_id} flagged for Opus review (malformed Below response)")

        conn.commit()
        conn.close()

    return stats


async def score_deal_items() -> dict:
    """Score all unscored deal items via Below. Returns summary stats."""
    from core.cluster.intel_collector import _get_intel_db

    conn = _get_intel_db()
    unscored = conn.execute(
        "SELECT * FROM deal_items WHERE deal_score IS NULL ORDER BY collected_at ASC"
    ).fetchall()
    conn.close()

    stats = {"total": len(unscored), "scored": 0, "flagged": 0, "alerts_sent": 0, "errors": 0}

    for row in unscored:
        item = dict(row)
        item_id = item["id"]
        hunt_id = item.get("hunt_id")

        # Get hunt for target price context
        hunt = {}
        if hunt_id:
            conn = _get_intel_db()
            hunt_row = conn.execute(
                "SELECT * FROM active_hunts WHERE id = ?", (hunt_id,)
            ).fetchone()
            conn.close()
            if hunt_row:
                hunt = dict(hunt_row)

        # Call Below for scoring
        prompt = _build_deal_prompt(item, hunt)
        response = await _call_below_chat(prompt)

        if response is None:
            logger.warning("Below offline — stopping deal scoring cycle")
            stats["errors"] += 1
            break

        parsed = _parse_deal_score(response)

        conn = _get_intel_db()
        if parsed:
            # Apply pair scoring boost (post-scoring adjustment)
            pair_info = _check_pair_availability(item)
            if pair_info["pair_available"]:
                pair_boost = min(10, max(5, pair_info["pair_count"] * 3))
                parsed["score"] = min(100, parsed["score"] + pair_boost)
                parsed["assessment"] += f" [+{pair_boost} pair boost]"
                # Re-evaluate verdict after boost
                if parsed["score"] >= 90:
                    parsed["verdict"] = "exceptional"
                elif parsed["score"] >= 70:
                    parsed["verdict"] = "good"

            # Build enriched assessment with timing + TCO context
            full_assessment = parsed["assessment"]
            if parsed.get("timing_note"):
                full_assessment += f" | Timing: {parsed['timing_note']}"
            if parsed.get("tco_note") and "no adjustment" not in parsed.get("tco_note", "").lower():
                full_assessment += f" | TCO: {parsed['tco_note']}"

            conn.execute(
                """UPDATE deal_items SET deal_score = ?, verdict = ?,
                   below_assessment = ? WHERE id = ?""",
                (parsed["score"], parsed["verdict"], full_assessment, item_id)
            )
            stats["scored"] += 1

            # Exceptional deal alert
            if parsed["score"] >= 80:
                deal_with_score = {**item, **parsed, "deal_score": parsed["score"]}
                await _send_discord_alert(deal_with_score)
                stats["alerts_sent"] += 1
        else:
            _flag_needs_opus_review(item_id, "deal")
            stats["flagged"] += 1
            logger.warning(f"Deal item {item_id} flagged for Opus review")

        conn.commit()
        conn.close()

    return stats


# --- Scoring Cron ---

async def run_scoring_cycle():
    """Run one complete scoring cycle (intel + deals)."""
    logger.info("Starting scoring cycle")
    intel_stats = await score_intel_items()
    deal_stats = await score_deal_items()
    logger.info(
        f"Scoring cycle complete — Intel: {intel_stats['scored']} scored, "
        f"{intel_stats['flagged']} flagged | Deals: {deal_stats['scored']} scored, "
        f"{deal_stats['alerts_sent']} alerts"
    )
    return {"intel": intel_stats, "deals": deal_stats}


def _scoring_cron_loop():
    """Background thread: run scoring cycle every 30 minutes."""
    import asyncio
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    while True:
        try:
            loop.run_until_complete(run_scoring_cycle())
        except Exception as e:
            logger.error(f"Scoring cron error: {e}")
        time.sleep(SCORING_INTERVAL)


def start_scoring_cron():
    """Start the background scoring cron thread."""
    t = threading.Thread(target=_scoring_cron_loop, daemon=True, name="intel-scoring-cron")
    t.start()
    logger.info(f"Started scoring cron (every {SCORING_INTERVAL}s)")
    return t
