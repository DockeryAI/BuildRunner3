"""cache_policy.py — Prompt cache breakpoint builder for BR3 Claude requests.

3-breakpoint contract (per AGENTS.md):
  1. system + tools      — stable, cache_control: ephemeral
  2. project/skill context — stable within session, cache_control: ephemeral
  3. task payload        — per-request; no cache_control

NEVER inline timestamps, random IDs, or user input into breakpoints 1-2.
NEVER create inline cache_control dicts outside this module.
"""

from __future__ import annotations

from typing import Any

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
    """Build a 3-breakpoint cacheable content-block list for a Claude request.

    Breakpoints:
        1 — system_text   (cache_control: ephemeral)
        2 — skill_context (cache_control: ephemeral)
        3 — task_payload  (no cache_control — changes every call)

    Args:
        system_text: System prompt + tool descriptions. Must be byte-stable
            across repeated calls (no timestamps, no UUIDs).
        skill_context: Project-level / skill-level context (CLAUDE.md, AGENTS.md
            scope). Stable within a session.
        task_payload: The per-request payload (diff, log lines, spec excerpt).

    Returns:
        A list of content-block dicts ready for the Anthropic messages API.
    """
    return [
        _make_text_block(system_text, cached=True),     # breakpoint 1
        _make_text_block(skill_context, cached=True),   # breakpoint 2
        _make_text_block(task_payload, cached=False),   # breakpoint 3
    ]


def get_breakpoint_count() -> int:
    """Return the canonical number of cache breakpoints (always 3)."""
    return 3


def has_cache_control(block: dict[str, Any]) -> bool:
    """Return True if the given content block carries a cache_control marker."""
    return "cache_control" in block


def cached_block_indices() -> list[int]:
    """Return the 0-based indices of blocks that carry cache_control.

    By contract, breakpoints 1 and 2 (indices 0 and 1) are cached;
    breakpoint 3 (index 2) is not.
    """
    return [0, 1]
