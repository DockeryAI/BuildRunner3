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

import json as _json
import logging
import os
import sqlite3 as _sqlite3
import uuid as _uuid
from datetime import datetime as _dt
from datetime import timezone as _timezone
from pathlib import Path as _Path
from typing import Any, Optional, TypedDict

from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Phase 6: Non-blocking cache_hit telemetry emit
# ---------------------------------------------------------------------------

def _emit_cache_hit(breakpoint_index: int) -> None:
    """Emit a cache_hit event to telemetry.db. Swallows all errors."""
    try:
        db_candidates = [
            _Path.cwd() / ".buildrunner" / "telemetry.db",
            _Path.home() / "Projects" / "BuildRunner3" / ".buildrunner" / "telemetry.db",
        ]
        db_path = next((p for p in db_candidates if p.exists()), None)
        if db_path is None:
            return

        metadata = {"breakpoint": breakpoint_index}
        conn = _sqlite3.connect(str(db_path))
        try:
            conn.execute(
                "INSERT INTO events (event_id, event_type, timestamp, metadata, success) VALUES (?, ?, ?, ?, ?)",
                (
                    str(_uuid.uuid4()),
                    "cache_hit",
                    _dt.now(_timezone.utc).isoformat(),  # noqa: UP017
                    _json.dumps(metadata),
                    1,
                ),
            )
            conn.commit()
        finally:
            conn.close()
    except Exception as _exc:  # noqa: BLE001
        logger.warning("_emit_cache_hit: swallowed error: %s", _exc)

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


class CacheSegment(TypedDict):
    role: str
    content: str
    cache_control: Optional[dict[str, str]]  # noqa: UP045


class ShapedBundle(TypedDict):
    cache_breakpoints: list[int]
    segments: list[CacheSegment]


class _ShapeBundleInput(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    model: str
    static_system: str
    static_tools: str
    sliding_window: str
    dynamic_tail: str

    @field_validator(
        "model",
        "static_system",
        "static_tools",
        "sliding_window",
        "dynamic_tail",
    )
    @classmethod
    def _validate_string_fields(cls, value: str) -> str:
        return value


class _CacheSegmentModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    role: str
    content: str
    cache_control: Optional[dict[str, str]] = None  # noqa: UP045


class _ShapedBundleModel(BaseModel):
    model_config = ConfigDict(strict=True, extra="forbid")

    cache_breakpoints: list[int] = Field(min_length=3, max_length=3)
    segments: list[_CacheSegmentModel] = Field(min_length=4, max_length=4)

    @field_validator("cache_breakpoints")
    @classmethod
    def _validate_breakpoints(cls, value: list[int]) -> list[int]:
        if value != sorted(value):
            raise ValueError("cache_breakpoints must be strictly ascending")
        if len(set(value)) != len(value):
            raise ValueError("cache_breakpoints must be strictly ascending")
        return value

    @model_validator(mode="after")
    def _validate_segment_alignment(self) -> _ShapedBundleModel:
        if len(self.segments) != len(self.cache_breakpoints) + 1:
            raise ValueError("segments must equal len(cache_breakpoints) + 1")
        return self


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


def shape_bundle(
    model: str,
    static_system: str,
    static_tools: str,
    sliding_window: str,
    dynamic_tail: str,
) -> ShapedBundle:
    """Return the canonical 4-segment cache bundle shape.

    The bundle always contains four segments and exactly three cache breakpoints.
    Breakpoints are expressed as 0-based segment indices into ``segments`` and
    mark the end of the static-system, static-tools, and sliding-window segments.

    Args:
        model: Target runtime model identifier.
        static_system: Stable system text.
        static_tools: Stable tool-description text.
        sliding_window: Stable rolling context window.
        dynamic_tail: Per-request tail content.

    Returns:
        A dict with ``cache_breakpoints`` and ``segments`` keys.

    Raises:
        ValidationError: If any input is not a string.
    """
    validated = _ShapeBundleInput(
        model=model,
        static_system=static_system,
        static_tools=static_tools,
        sliding_window=sliding_window,
        dynamic_tail=dynamic_tail,
    )

    segments = [
        _CacheSegmentModel(
            role="static_system",
            content=validated.static_system,
            cache_control=dict(EPHEMERAL_CACHE_CONTROL),
        ),
        _CacheSegmentModel(
            role="static_tools",
            content=validated.static_tools,
            cache_control=dict(EPHEMERAL_CACHE_CONTROL),
        ),
        _CacheSegmentModel(
            role="sliding_window",
            content=validated.sliding_window,
            cache_control=dict(EPHEMERAL_CACHE_CONTROL),
        ),
        _CacheSegmentModel(
            role="dynamic_tail",
            content=validated.dynamic_tail,
            cache_control=None,
        ),
    ]

    shaped = _ShapedBundleModel(
        cache_breakpoints=[0, 1, 2],
        segments=segments,
    )
    return shaped.model_dump()


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
        _emit_cache_hit(0)  # breakpoint 1 fired
        _emit_cache_hit(1)  # breakpoint 2 fired
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
