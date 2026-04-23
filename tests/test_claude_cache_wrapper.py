"""
tests/test_claude_cache_wrapper.py

Unit tests for core.cluster.below.claude_cache_wrapper.
All Anthropic API calls are mocked. No real network access.
"""

from __future__ import annotations

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.cluster.below.claude_cache_wrapper import (
    ClaudeCacheWrapper,
    _CACHE_EXCLUSION_METHODS,
    _prompt_from_messages,
    get_wrapper,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_wrapper(tmp_path: Path) -> ClaudeCacheWrapper:
    db = tmp_path / "cache.db"
    return ClaudeCacheWrapper(db_path=db, threshold=0.95, ttl_days=30, warmup_days=0)


def _run(coro):
    return asyncio.run(coro)


# ---------------------------------------------------------------------------
# _prompt_from_messages
# ---------------------------------------------------------------------------


class TestPromptFromMessages:
    def test_single_user_message(self):
        msgs = [{"role": "user", "content": "hello world"}]
        result = _prompt_from_messages(msgs)
        assert "user: hello world" in result

    def test_multi_message(self):
        msgs = [
            {"role": "user", "content": "first"},
            {"role": "assistant", "content": "second"},
        ]
        result = _prompt_from_messages(msgs)
        assert "user: first" in result
        assert "assistant: second" in result

    def test_content_blocks_extracted(self):
        msgs = [{"role": "user", "content": [{"type": "text", "text": "from block"}]}]
        result = _prompt_from_messages(msgs)
        assert "from block" in result


# ---------------------------------------------------------------------------
# Exclusion list
# ---------------------------------------------------------------------------


class TestExclusionList:
    def test_ai_code_review_in_exclusion(self):
        assert "ai_code_review" in _CACHE_EXCLUSION_METHODS

    def test_adversarial_review_in_exclusion(self):
        assert "adversarial_review" in _CACHE_EXCLUSION_METHODS

    def test_arbiter_in_exclusion(self):
        assert "arbiter" in _CACHE_EXCLUSION_METHODS

    def test_review_diff_in_exclusion(self):
        assert "review_diff" in _CACHE_EXCLUSION_METHODS


# ---------------------------------------------------------------------------
# Cache hit / miss
# ---------------------------------------------------------------------------


class TestCacheHitMiss:
    def test_cache_miss_calls_live_api(self, tmp_path):
        wrapper = _make_wrapper(tmp_path)
        live_result = "live response text"

        with patch.object(wrapper, "_live_call", new_callable=AsyncMock, return_value=live_result) as mock_live:
            result = _run(wrapper.call(
                model="claude-opus-4-7",
                method="analyze_requirements",
                messages=[{"role": "user", "content": "what features should I build?"}],
                max_tokens=1024,
            ))

        assert result == live_result
        mock_live.assert_called_once()

    def test_cache_hit_does_not_call_live_api(self, tmp_path):
        wrapper = _make_wrapper(tmp_path)
        cached_text = "cached answer"
        messages = [{"role": "user", "content": "unique question for cache hit test"}]

        # Pre-populate the cache
        import math
        vec = [0.0] * 768
        vec[0] = math.cos(0.1)
        vec[1] = math.sin(0.1)

        with patch("core.cluster.below.embed.embed_batch", return_value=[vec]):
            wrapper._get_cache().store("claude-opus-4-7", "analyze_requirements",
                                       _prompt_from_messages(messages), cached_text)

        with patch("core.cluster.below.embed.embed_batch", return_value=[vec]):
            with patch.object(wrapper, "_live_call", new_callable=AsyncMock) as mock_live:
                result = _run(wrapper.call(
                    model="claude-opus-4-7",
                    method="analyze_requirements",
                    messages=messages,
                    max_tokens=1024,
                ))

        assert result == cached_text
        mock_live.assert_not_called()


# ---------------------------------------------------------------------------
# Exclusion enforcement
# ---------------------------------------------------------------------------


class TestExclusionEnforcement:
    def test_excluded_method_always_calls_live(self, tmp_path):
        """Methods in the exclusion list must bypass cache unconditionally."""
        wrapper = _make_wrapper(tmp_path)
        live_result = "live code review"

        with patch.object(wrapper, "_live_call", new_callable=AsyncMock, return_value=live_result) as mock_live:
            result = _run(wrapper.call(
                model="claude-opus-4-7",
                method="ai_code_review",
                messages=[{"role": "user", "content": "review this diff"}],
                max_tokens=2048,
            ))

        assert result == live_result
        mock_live.assert_called_once()

    def test_skip_cache_true_bypasses_cache(self, tmp_path):
        wrapper = _make_wrapper(tmp_path)

        with patch.object(wrapper, "_live_call", new_callable=AsyncMock, return_value="skip result") as mock_live:
            result = _run(wrapper.call(
                model="claude-opus-4-7",
                method="pre_fill_spec",
                messages=[{"role": "user", "content": "build me a spec"}],
                skip_cache=True,
                max_tokens=4096,
            ))

        assert result == "skip result"
        mock_live.assert_called_once()

    def test_adversarial_review_bypasses_cache(self, tmp_path):
        wrapper = _make_wrapper(tmp_path)

        with patch.object(wrapper, "_live_call", new_callable=AsyncMock, return_value="review") as mock_live:
            _run(wrapper.call(
                model="claude-sonnet-4-6",
                method="adversarial_review",
                messages=[{"role": "user", "content": "is this plan good?"}],
                max_tokens=1024,
            ))

        mock_live.assert_called_once()


# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------


class TestRollbackFlag:
    def test_cache_disabled_flag(self, tmp_path):
        """BR3_SEMANTIC_CACHE=off must make every call go to live API."""
        import core.cluster.below.claude_cache_wrapper as mod
        orig = mod._CACHE_ENABLED
        mod._CACHE_ENABLED = False
        try:
            wrapper = _make_wrapper(tmp_path)
            with patch.object(wrapper, "_live_call", new_callable=AsyncMock, return_value="off result") as mock_live:
                result = _run(wrapper.call(
                    model="claude-opus-4-7",
                    method="validate_spec",
                    messages=[{"role": "user", "content": "validate my spec"}],
                    max_tokens=2048,
                ))
            assert result == "off result"
            mock_live.assert_called_once()
        finally:
            mod._CACHE_ENABLED = orig


# ---------------------------------------------------------------------------
# Cross-model isolation
# ---------------------------------------------------------------------------


class TestCrossModelIsolation:
    def test_different_models_are_isolated(self, tmp_path):
        """Opus and Sonnet calls with the same prompt must not share cache entries."""
        wrapper = _make_wrapper(tmp_path)
        messages = [{"role": "user", "content": "same prompt for isolation test"}]

        import math
        vec = [0.0] * 768
        vec[0] = math.cos(0.05)
        vec[1] = math.sin(0.05)

        with patch("core.cluster.below.embed.embed_batch", return_value=[vec]):
            wrapper._get_cache().store("claude-opus-4-7", "pre_fill_spec",
                                       _prompt_from_messages(messages), "opus answer")

        with patch("core.cluster.below.embed.embed_batch", return_value=[vec]):
            with patch.object(wrapper, "_live_call", new_callable=AsyncMock, return_value="sonnet live") as mock_live:
                result = _run(wrapper.call(
                    model="claude-sonnet-4-6",
                    method="pre_fill_spec",
                    messages=messages,
                    max_tokens=4096,
                ))

        # Sonnet must not get Opus's cached answer
        assert result == "sonnet live"
        mock_live.assert_called_once()


# ---------------------------------------------------------------------------
# hit_rate helper
# ---------------------------------------------------------------------------


class TestHitRate:
    def test_hit_rate_returns_float(self, tmp_path):
        wrapper = _make_wrapper(tmp_path)
        rate = wrapper.hit_rate()
        assert isinstance(rate, float)
        assert 0.0 <= rate <= 1.0

    def test_hit_rate_zero_when_no_metrics(self, tmp_path):
        wrapper = _make_wrapper(tmp_path)
        # Override metrics file to non-existent path
        import core.cluster.below.claude_cache_wrapper as mod
        orig = mod._METRICS_FILE
        mod._METRICS_FILE = tmp_path / "nonexistent.jsonl"
        try:
            assert wrapper.hit_rate() == 0.0
        finally:
            mod._METRICS_FILE = orig


# ---------------------------------------------------------------------------
# get_wrapper singleton
# ---------------------------------------------------------------------------


class TestGetWrapperSingleton:
    def test_returns_same_instance(self):
        import core.cluster.below.claude_cache_wrapper as mod
        orig = mod._wrapper
        mod._wrapper = None
        try:
            w1 = get_wrapper()
            w2 = get_wrapper()
            assert w1 is w2
        finally:
            mod._wrapper = orig
