"""Tests for core/runtime/cache_policy.py — 3-breakpoint prompt cache contract."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from core.runtime.cache_policy import (
    EPHEMERAL_CACHE_CONTROL,
    build_cached_prompt,
    cached_block_indices,
    get_breakpoint_count,
    has_cache_control,
    shape_bundle,
)


class TestBreakpointCount:
    def test_three_breakpoints(self):
        assert get_breakpoint_count() == 3


class TestBuildCachedPrompt:
    def _build(self, system="sys", skill="skill", task="task"):
        return build_cached_prompt(system, skill, task)

    def test_returns_three_blocks(self):
        blocks = self._build()
        assert len(blocks) == 3

    def test_all_blocks_are_text_type(self):
        blocks = self._build()
        for block in blocks:
            assert block["type"] == "text"

    def test_breakpoint_1_has_cache_control(self):
        blocks = self._build(system="system prompt")
        assert has_cache_control(blocks[0])
        assert blocks[0]["cache_control"] == EPHEMERAL_CACHE_CONTROL

    def test_breakpoint_2_has_cache_control(self):
        blocks = self._build(skill="skill context")
        assert has_cache_control(blocks[1])
        assert blocks[1]["cache_control"] == EPHEMERAL_CACHE_CONTROL

    def test_breakpoint_3_no_cache_control(self):
        blocks = self._build(task="task payload")
        assert not has_cache_control(blocks[2])

    def test_content_preserved_breakpoint_1(self):
        blocks = self._build(system="hello system")
        assert blocks[0]["text"] == "hello system"

    def test_content_preserved_breakpoint_2(self):
        blocks = self._build(skill="hello skill")
        assert blocks[1]["text"] == "hello skill"

    def test_content_preserved_breakpoint_3(self):
        blocks = self._build(task="hello task")
        assert blocks[2]["text"] == "hello task"

    def test_empty_strings_allowed(self):
        blocks = build_cached_prompt("", "", "")
        assert len(blocks) == 3
        for block in blocks:
            assert block["text"] == ""

    def test_unicode_preserved(self):
        payload = "diff: 日本語テスト\n+行追加"
        blocks = build_cached_prompt("sys", "skill", payload)
        assert blocks[2]["text"] == payload

    def test_large_payload_no_truncation(self):
        """Payload content must not be silently truncated inside cache_policy."""
        large = "x" * 100_000
        blocks = build_cached_prompt("sys", "skill", large)
        assert blocks[2]["text"] == large

    def test_byte_identity_breakpoints_1_and_2(self):
        """Breakpoints 1 and 2 must be byte-identical on repeated calls with same inputs."""
        blocks_a = build_cached_prompt("system", "skill-ctx", "task-1")
        blocks_b = build_cached_prompt("system", "skill-ctx", "task-2")
        assert blocks_a[0] == blocks_b[0], "breakpoint 1 must be byte-stable"
        assert blocks_a[1] == blocks_b[1], "breakpoint 2 must be byte-stable"

    def test_task_payload_differs_across_calls(self):
        blocks_a = build_cached_prompt("sys", "skill", "task-A")
        blocks_b = build_cached_prompt("sys", "skill", "task-B")
        assert blocks_a[2]["text"] != blocks_b[2]["text"]


class TestCacheControlHelpers:
    def test_has_cache_control_true(self):
        block = {"type": "text", "text": "x", "cache_control": {"type": "ephemeral"}}
        assert has_cache_control(block) is True

    def test_has_cache_control_false(self):
        block = {"type": "text", "text": "x"}
        assert has_cache_control(block) is False

    def test_cached_block_indices_are_0_and_1(self):
        assert cached_block_indices() == [0, 1]

    def test_ephemeral_cache_control_shape(self):
        assert EPHEMERAL_CACHE_CONTROL == {"type": "ephemeral"}


class TestNoInlineCacheControlInPrompts:
    """Ensure callers use cache_policy — no raw cache_control dicts in prompts."""

    def test_structured_blocks_not_strings(self):
        blocks = build_cached_prompt("sys", "skill", "task")
        for block in blocks:
            assert isinstance(block, dict), "blocks must be dicts, not strings"

    def test_cached_blocks_count(self):
        blocks = build_cached_prompt("sys", "skill", "task")
        cached = [b for b in blocks if has_cache_control(b)]
        assert len(cached) == 2, "exactly 2 blocks must carry cache_control"

    def test_uncached_blocks_count(self):
        blocks = build_cached_prompt("sys", "skill", "task")
        uncached = [b for b in blocks if not has_cache_control(b)]
        assert len(uncached) == 1, "exactly 1 block must be uncached (task payload)"


class TestShapeBundle:
    def test_happy_path_returns_four_segments_and_three_breakpoints(self):
        shaped = shape_bundle("claude-opus-4-7", "sys", "tools", "window", "tail")
        assert shaped["cache_breakpoints"] == [0, 1, 2]
        assert len(shaped["segments"]) == 4
        assert [segment["role"] for segment in shaped["segments"]] == [
            "static_system",
            "static_tools",
            "sliding_window",
            "dynamic_tail",
        ]

    def test_all_empty_strings_are_legal(self):
        shaped = shape_bundle("", "", "", "", "")
        assert shaped["cache_breakpoints"] == [0, 1, 2]
        assert [segment["content"] for segment in shaped["segments"]] == ["", "", "", ""]

    @pytest.mark.parametrize(
        ("field_name", "bad_value"),
        [
            ("model", 123),
            ("model", None),
            ("static_system", 123),
            ("static_system", None),
            ("static_tools", 123),
            ("static_tools", None),
            ("sliding_window", 123),
            ("sliding_window", None),
            ("dynamic_tail", 123),
            ("dynamic_tail", None),
        ],
    )
    def test_type_violations_raise_validation_error(self, field_name, bad_value):
        kwargs = {
            "model": "claude-opus-4-7",
            "static_system": "sys",
            "static_tools": "tools",
            "sliding_window": "window",
            "dynamic_tail": "tail",
        }
        kwargs[field_name] = bad_value

        with pytest.raises(ValidationError):
            shape_bundle(**kwargs)

    def test_unicode_content_is_preserved(self):
        sliding_window = "履歴\nΔοκιμή\nemoji 🚀"
        dynamic_tail = "следующий шаг"
        shaped = shape_bundle("claude-opus-4-7", "sys", "tools", sliding_window, dynamic_tail)
        assert shaped["segments"][2]["content"] == sliding_window
        assert shaped["segments"][3]["content"] == dynamic_tail

    def test_very_long_sliding_window_is_not_truncated(self):
        sliding_window = "context-line\n" * 50_000
        shaped = shape_bundle("claude-opus-4-7", "sys", "tools", sliding_window, "tail")
        assert shaped["segments"][2]["content"] == sliding_window

    def test_segments_length_matches_breakpoint_plus_one_invariant(self):
        shaped = shape_bundle("claude-opus-4-7", "sys", "tools", "window", "tail")
        assert len(shaped["segments"]) == len(shaped["cache_breakpoints"]) + 1

    def test_breakpoints_are_strictly_ascending(self):
        shaped = shape_bundle("claude-opus-4-7", "sys", "tools", "window", "tail")
        breakpoints = shaped["cache_breakpoints"]
        assert breakpoints[0] < breakpoints[1] < breakpoints[2]

    def test_only_first_three_segments_are_cache_marked(self):
        shaped = shape_bundle("claude-opus-4-7", "sys", "tools", "window", "tail")
        assert shaped["segments"][0]["cache_control"] == EPHEMERAL_CACHE_CONTROL
        assert shaped["segments"][1]["cache_control"] == EPHEMERAL_CACHE_CONTROL
        assert shaped["segments"][2]["cache_control"] == EPHEMERAL_CACHE_CONTROL
        assert shaped["segments"][3]["cache_control"] is None
