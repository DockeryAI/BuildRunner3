"""cache_policy.py — Prompt cache breakpoint builder for BR3 Claude requests.

3-breakpoint contract (per AGENTS.md):
  1. system + tools      — stable, cache_control: ephemeral
  2. project/skill context — stable within session, cache_control: ephemeral
  3. task payload        — per-request; no cache_control

NEVER inline timestamps, random IDs, or user input into breakpoints 1-2.
NEVER create inline cache_control dicts outside this module.

Phase 4: BR3_CACHE_BREAKPOINTS gate
  on  → full 3-breakpoint contract (behaviour unchanged from pre-Phase-4 default)
  off → emit zero breakpoints; build_cached_prompt returns plain text blocks with
        no cache_control markers. get_breakpoint_count() returns 0.
        cached_block_indices() returns [].
"""

from __future__ import annotations

import os
from typing import Any

# ---------------------------------------------------------------------------
# Phase 4: Feature-flag gate — BR3_CACHE_BREAKPOINTS
#
# Read ONCE at module import time and cached here.  Restart the process to
# pick up a flag change — per-call re-reads are not supported.
#
# on  → 3-breakpoint cache contract (default; behaviour identical to pre-Phase-4)
# off → zero breakpoints emitted; all blocks returned without cache_control
# ---------------------------------------------------------------------------
_CACHE_BREAKPOINTS_ENABLED: bool = (
    os.environ.get("BR3_CACHE_BREAKPOINTS", "off").lower() == "on"
)

# ---------------------------------------------------------------------------
# Sentinel used as the cache_control value on cacheable breakpoints.
# ---------------------------------------------------------------------------
EPHEMERAL_CACHE_CONTROL: dict[str, str] = {"type": "ephemeral"}


def _make_text_block(text: str, *, cached: bool) -> dict[str, Any]:
    """Return an Anthropic-style content block dict.

    Args:
        text: The block text content.
        cached: When True, attach cache_control: ephemeral to this block.
    """
    block: dict[str, Any] = {"type": "text", "text": text}
    if cached:
        block["cache_control"] = EPHEMERAL_CACHE_CONTROL
    return block


def build_cached_prompt(
    system_text: str,
    skill_context: str,
    task_payload: str,
) -> list[dict[str, Any]]:
    """Build a content-block list for a Claude request.

    When BR3_CACHE_BREAKPOINTS=on (3-breakpoint contract):
        1 — system_text   (cache_control: ephemeral)
        2 — skill_context (cache_control: ephemeral)
        3 — task_payload  (no cache_control — changes every call)

    When BR3_CACHE_BREAKPOINTS=off:
        All three blocks are returned without any cache_control markers.
        Callers receive the same structure but zero breakpoints are emitted,
        meaning no behavior change from a caching perspective vs. pre-Phase-4.

    Args:
        system_text: System prompt + tool descriptions. Must be byte-stable
            across repeated calls (no timestamps, no UUIDs).
        skill_context: Project-level / skill-level context (CLAUDE.md, AGENTS.md
            scope). Stable within a session.
        task_payload: The per-request payload (diff, log lines, spec excerpt).

    Returns:
        A list of content-block dicts ready for the Anthropic messages API.
    """
    if _CACHE_BREAKPOINTS_ENABLED:
        return [
            _make_text_block(system_text, cached=True),     # breakpoint 1
            _make_text_block(skill_context, cached=True),   # breakpoint 2
            _make_text_block(task_payload, cached=False),   # breakpoint 3
        ]
    # Flag off — emit zero breakpoints; no cache_control on any block.
    return [
        _make_text_block(system_text, cached=False),
        _make_text_block(skill_context, cached=False),
        _make_text_block(task_payload, cached=False),
    ]


def get_breakpoint_count() -> int:
    """Return the active number of cache breakpoints.

    Returns 3 when BR3_CACHE_BREAKPOINTS=on (the cluster-max Phase 8 contract).
    Returns 0 when BR3_CACHE_BREAKPOINTS=off (no breakpoints emitted).
    """
    return 3 if _CACHE_BREAKPOINTS_ENABLED else 0


def has_cache_control(block: dict[str, Any]) -> bool:
    """Return True if the given content block carries a cache_control marker."""
    return "cache_control" in block


def cached_block_indices() -> list[int]:
    """Return the 0-based indices of blocks that carry cache_control.

    When BR3_CACHE_BREAKPOINTS=on: breakpoints 1 and 2 (indices 0 and 1) are cached;
    breakpoint 3 (index 2) is not.
    When BR3_CACHE_BREAKPOINTS=off: empty list — zero breakpoints emitted.
    """
    return [0, 1] if _CACHE_BREAKPOINTS_ENABLED else []
