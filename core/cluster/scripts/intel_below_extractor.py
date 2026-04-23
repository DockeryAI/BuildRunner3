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
import sys
import time
import urllib.error
import urllib.request
from typing import Any

# Allow running as a module from the repo root
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "..")))
from core.cluster.cluster_config import get_below_host, get_below_model  # noqa: E402

logger = logging.getLogger(__name__)

BELOW_HOST = os.environ.get("BELOW_INTEL_HOST") or get_below_host()   # single source of truth — core/cluster/cluster_config.py
BELOW_MODEL = os.environ.get("BELOW_INTEL_MODEL") or get_below_model()  # single source of truth — core/cluster/cluster_config.py
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
# Collect helpers — replaces `claude -p` at collect-intel.sh Phase 1 and Phase 2
# ---------------------------------------------------------------------------

# Tech news URLs polled by Phase 1 (source collection)
_TECH_NEWS_SOURCES = [
    ("https://anthropic.com/news", "Claude/Anthropic news"),
    ("https://supabase.com/blog", "Supabase updates"),
    ("https://github.com/trending/python?since=weekly", "Python trending"),
    ("https://github.com/trending/typescript?since=weekly", "TypeScript trending"),
]

# Innovation / MCP sources polled by Phase 2
_INNOVATION_SOURCES = [
    ("https://github.com/punkpeye/awesome-mcp-servers/raw/main/README.md", "MCP servers"),
    ("https://github.com/trending?since=daily&spoken_language_code=en", "GitHub trending"),
]

_LOCKWOOD_INTEL_URL = os.environ.get(
    "BR3_LOCKWOOD_INTEL_URL",
    "http://10.0.1.106:8101/api/intel/items",
)


def _fetch_text(url: str, timeout: int = 10) -> str:
    """Fetch URL content as plain text; return empty string on error."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "BR3-intel-collector/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read()
        # Decode + strip HTML tags simply (no dependency on bs4)
        text = raw.decode("utf-8", errors="replace")
        text = re.sub(r"<[^>]+>", " ", text)
        text = re.sub(r"[ \t]+", " ", text)
        return text[:16000]
    except Exception as exc:
        logger.debug("fetch_text %s failed: %s", url, exc)
        return ""


try:
    import re as re  # already imported above; alias for clarity
except ImportError:
    pass


def _post_item(item: dict[str, Any], lockwood_url: str) -> bool:
    """POST one intel item to Lockwood. Returns True on HTTP 2xx."""
    try:
        body = json.dumps(item).encode()
        req = urllib.request.Request(
            lockwood_url, data=body,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            return 200 <= resp.status < 300
    except Exception as exc:
        logger.debug("post_item failed: %s", exc)
        return False


def collect_and_post(sources: list[tuple[str, str]], lockwood_url: str) -> int:
    """Fetch each source URL, extract intel items via Below, POST to Lockwood.

    Returns total items posted.
    """
    total = 0
    for url, context in sources:
        text = _fetch_text(url)
        if not text:
            continue
        items = extract_intel_items(text, context=context)
        for item in items:
            if _post_item(item, lockwood_url):
                total += 1
                logger.info("posted: %s", item.get("title", "?"))
    return total


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------

if __name__ == "__main__":
    import argparse
    import sys

    logging.basicConfig(level=logging.INFO)

    parser = argparse.ArgumentParser(description="Below intel extractor / collector")
    subparsers = parser.add_subparsers(dest="command")

    # Legacy --stage interface (preserved for Phase 1.5 / 2.25 shell callers)
    parser.add_argument("--stage", type=int, choices=[1, 2], default=None)
    parser.add_argument("--text", default="", help="Raw text for stage 1")
    parser.add_argument("--items", default="[]", help="JSON array of items for stage 2")
    parser.add_argument("--context", default="tech news", help="Context hint for stage 1")

    # New --collect interface (replaces claude -p in collect-intel.sh phases 1 and 2)
    parser.add_argument(
        "--collect",
        choices=["phase1", "phase2"],
        default=None,
        help="Run collection pipeline: phase1=tech news, phase2=innovation/MCP discovery",
    )
    parser.add_argument(
        "--lockwood-url",
        default=_LOCKWOOD_INTEL_URL,
        help="Lockwood intel POST endpoint",
    )

    args = parser.parse_args()

    if not _BELOW_INTEL_ENABLED:
        print("[]")
        sys.exit(1)

    if args.collect:
        sources = _TECH_NEWS_SOURCES if args.collect == "phase1" else _INNOVATION_SOURCES
        n = collect_and_post(sources, args.lockwood_url)
        print(f"[intel_below_extractor] {args.collect}: posted {n} items to Lockwood")
        sys.exit(0 if n >= 0 else 1)
    elif args.stage == 1:
        result = extract_intel_items(args.text, context=args.context)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result else 1)
    elif args.stage == 2:
        items = json.loads(args.items)
        result = categorize_intel_items(items)
        print(json.dumps(result, indent=2))
        sys.exit(0 if result else 1)
    else:
        parser.print_help()
        sys.exit(1)
