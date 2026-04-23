"""
intel_below_extractor.py — Below qwen3:8b structured intel extraction.

Replaces `claude -p` at intel pipeline stage 1 (sources) and stage 2 (categorize).
Sends raw tech-news text to Below for structured extraction into the Lockwood
intel item schema. Mirrors the pattern used by hunt_sources/bhphoto.py.

Stage 1 — sources extraction:
    Given raw HTML / markdown / text from a tech news page, extract intel items.

Stage 2 — categorize:
    Given a batch of item summaries, classify each with priority + source_type.

Usage:
    python3 -m core.cluster.scripts.intel_below_extractor --stage 1 --text "..."
    python3 -m core.cluster.scripts.intel_below_extractor --stage 2 --items '[{"id":1,"summary":"..."}]'

Exit codes:
    0 — success, JSON array of intel items written to stdout
    1 — Below offline (caller falls back to Claude or skips)

Rollback: BR3_BELOW_INTEL=off → exits 1 immediately.
"""

from __future__ import annotations

import json
import logging
import os
import time
import urllib.error
import urllib.request
from typing import Any

logger = logging.getLogger(__name__)

BELOW_HOST = os.environ.get("BELOW_HOST", "10.0.1.105")
BELOW_MODEL = os.environ.get("BELOW_INTEL_MODEL", "qwen3:8b")
_BELOW_INTEL_ENABLED = os.environ.get("BR3_BELOW_INTEL", "on").lower() != "off"

# ---- Lockwood intel item schema (matches /api/intel/items POST body) ----
INTEL_ITEM_SCHEMA = {
    "type": "object",
    "properties": {
        "items": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "source": {"type": "string"},
                    "url": {"type": "string"},
                    "summary": {"type": "string"},
                    "source_type": {
                        "type": "string",
                        "enum": ["official", "community", "blog"],
                    },
                    "category": {
                        "type": "string",
                        "enum": [
                            "model-release", "api-change", "community-tool",
                            "ecosystem-news", "security", "general-news",
                        ],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "relevant": {"type": "boolean"},
                },
                "required": ["title", "source", "url", "summary", "category", "priority", "relevant"],
            },
        }
    },
    "required": ["items"],
}

# ---- Categorize schema (stage 2: classify existing items) ----
CATEGORIZE_SCHEMA = {
    "type": "object",
    "properties": {
        "classified": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "id": {"type": "integer"},
                    "category": {
                        "type": "string",
                        "enum": [
                            "model-release", "api-change", "community-tool",
                            "ecosystem-news", "security", "general-news",
                        ],
                    },
                    "priority": {
                        "type": "string",
                        "enum": ["critical", "high", "medium", "low"],
                    },
                    "source_type": {
                        "type": "string",
                        "enum": ["official", "community", "blog"],
                    },
                },
                "required": ["id", "category", "priority", "source_type"],
            },
        }
    },
    "required": ["classified"],
}


def _below_chat(schema: dict, messages: list[dict], timeout: int = 20) -> dict | None:
    """
    POST to Below /api/chat with a json_schema format constraint.
    Returns parsed JSON content, or None on offline/error.
    """
    if not _BELOW_INTEL_ENABLED:
        return None

    body = json.dumps({
        "model": BELOW_MODEL,
        "messages": messages,
        "stream": False,
        "format": schema,
        "options": {"num_predict": 1024},
    }).encode()

    try:
        req = urllib.request.Request(
            f"http://{BELOW_HOST}:11434/api/chat",
            data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode()
        parsed = json.loads(raw)
        content = (parsed.get("message") or {}).get("content", "")
        return json.loads(content)
    except Exception as exc:
        logger.debug("Below intel chat failed: %s", exc)
        return None


def extract_intel_items(raw_text: str, context: str = "tech news") -> list[dict[str, Any]]:
    """
    Stage 1: Extract structured intel items from raw text.

    Args:
        raw_text:  Raw HTML / markdown / plain text from a tech news source.
        context:   Brief description of what we're looking for (used in prompt).

    Returns:
        List of intel item dicts matching Lockwood /api/intel/items schema.
        Empty list if Below is offline or extraction fails.
    """
    system = (
        "You are a tech intelligence extractor. Extract real, newsworthy items "
        "from the provided text. Only include verified findings with real URLs. "
        "Prioritize: Claude/Anthropic, Supabase, Tailwind, Vite, React, "
        "TypeScript, Playwright, security advisories, and hardware for ML workloads."
    )
    user = (
        f"Context: {context}\n\n"
        f"Text (first 8000 chars):\n{raw_text[:8000]}\n\n"
        "Extract intel items as JSON. Mark relevant=false for duplicates, "
        "obvious spam, or items unrelated to software dev / BR3 stack."
    )

    t0 = time.time()
    result = _below_chat(
        INTEL_ITEM_SCHEMA,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    latency = int((time.time() - t0) * 1000)

    if result is None:
        logger.info("intel_below_extractor: stage 1 offline (latency=%dms)", latency)
        return []

    items = result.get("items", [])
    relevant = [i for i in items if i.get("relevant", True)]
    logger.info("intel_below_extractor: stage 1 extracted %d/%d items (latency=%dms)",
                len(relevant), len(items), latency)
    return relevant


def categorize_intel_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """
    Stage 2: Classify a batch of items (priority, category, source_type).

    Args:
        items:  List of dicts with at least {"id": int, "title": str, "summary": str}.

    Returns:
        List of classification dicts: {"id", "category", "priority", "source_type"}.
        Empty list if Below is offline.
    """
    if not items:
        return []

    # Compact representation to fit in context
    batch_text = "\n".join(
        f"id={item['id']}: {item.get('title', '')} — {item.get('summary', '')[:200]}"
        for item in items[:50]  # cap at 50 to stay within context
    )

    system = (
        "You are a tech intel classifier. For each item, assign:\n"
        "- category: model-release | api-change | community-tool | ecosystem-news | security | general-news\n"
        "- priority: critical (security/breaking) | high (major release) | medium (update) | low (blog/minor)\n"
        "- source_type: official | community | blog"
    )
    user = f"Classify these intel items:\n{batch_text}"

    t0 = time.time()
    result = _below_chat(
        CATEGORIZE_SCHEMA,
        [{"role": "system", "content": system}, {"role": "user", "content": user}],
    )
    latency = int((time.time() - t0) * 1000)

    if result is None:
        logger.info("intel_below_extractor: stage 2 offline (latency=%dms)", latency)
        return []

    classified = result.get("classified", [])
    logger.info("intel_below_extractor: stage 2 classified %d items (latency=%dms)",
                len(classified), latency)
    return classified


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Below intel extractor")
    parser.add_argument("--stage", type=int, choices=[1, 2], required=True)
    parser.add_argument("--text", default="", help="Raw text for stage 1")
    parser.add_argument("--items", default="[]", help="JSON array of items for stage 2")
    parser.add_argument("--context", default="tech news", help="Context hint for stage 1")
    args = parser.parse_args()

    if not _BELOW_INTEL_ENABLED:
        print("[]")
        sys.exit(1)

    if args.stage == 1:
        result = extract_intel_items(args.text, context=args.context)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result else 1)
    else:
        items = json.loads(args.items)
        result = categorize_intel_items(items)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result else 1)
