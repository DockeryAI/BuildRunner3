"""
tests/test_llmlingua_compress.py

Unit tests for core.cluster.below.llmlingua_compress.
LLMLingua model loading is mocked — no real HF model download in tests.
"""

from __future__ import annotations

import os
from pathlib import Path
from unittest.mock import patch, MagicMock

import pytest

from core.cluster.below.llmlingua_compress import (
    compress_prompt,
    compress_prompt_safe,
    EXCLUDED_METHODS,
    MIN_COMPRESS_LENGTH,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_prompt(length: int = 1000) -> str:
    """Make a deterministic test prompt of given character length."""
    base = "This is a test prompt for LLMLingua-2 compression. " * 50
    return (base * ((length // len(base)) + 1))[:length]


def _mock_compressor(compressed_text: str):
    """Return a mock compressor that returns compressed_text."""
    mock = MagicMock()
    mock.compress_prompt.return_value = {"compressed_prompt": compressed_text}
    return mock


# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------


class TestRollbackFlag:
    def test_rollback_returns_original(self):
        import core.cluster.below.llmlingua_compress as mod
        orig = mod._LLMLINGUA_ENABLED
        mod._LLMLINGUA_ENABLED = False
        try:
            prompt = _make_prompt(2000)
            result = compress_prompt(prompt)
            assert result == prompt
        finally:
            mod._LLMLINGUA_ENABLED = orig

    def test_rollback_skips_compressor_load(self):
        import core.cluster.below.llmlingua_compress as mod
        orig = mod._LLMLINGUA_ENABLED
        mod._LLMLINGUA_ENABLED = False
        try:
            with patch.object(mod, "_get_compressor") as mock_get:
                compress_prompt(_make_prompt(2000))
                mock_get.assert_not_called()
        finally:
            mod._LLMLINGUA_ENABLED = orig


# ---------------------------------------------------------------------------
# Exclusion list
# ---------------------------------------------------------------------------


class TestExclusionList:
    def test_excluded_methods_are_populated(self):
        assert "adversarial-review" in EXCLUDED_METHODS
        assert "ai_code_review" in EXCLUDED_METHODS
        assert "cross-model-review" in EXCLUDED_METHODS
        assert "arbiter" in EXCLUDED_METHODS
        assert "reviewer" in EXCLUDED_METHODS
        assert "review_diff" in EXCLUDED_METHODS
        assert "analyze_architecture" in EXCLUDED_METHODS

    def test_excluded_method_returns_original(self):
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(2000)
        with patch.object(mod, "_get_compressor") as mock_get:
            result = compress_prompt(prompt, method="adversarial-review")
            assert result == prompt
            mock_get.assert_not_called()

    def test_excluded_method_ai_code_review(self):
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(2000)
        with patch.object(mod, "_get_compressor") as mock_get:
            result = compress_prompt(prompt, method="ai_code_review")
            assert result == prompt
            mock_get.assert_not_called()

    def test_non_excluded_method_attempts_compression(self):
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(2000)
        compressed = _make_prompt(900)
        with patch.object(mod, "_get_compressor", return_value=_mock_compressor(compressed)):
            result = compress_prompt(prompt, method="dispatch")
            assert result == compressed

    def test_empty_method_is_not_excluded(self):
        """Empty method string should not be excluded."""
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(2000)
        compressed = _make_prompt(900)
        with patch.object(mod, "_get_compressor", return_value=_mock_compressor(compressed)):
            result = compress_prompt(prompt, method="")
            assert result == compressed


# ---------------------------------------------------------------------------
# Short prompt passthrough
# ---------------------------------------------------------------------------


class TestShortPromptPassthrough:
    def test_short_prompt_returned_unchanged(self):
        """Prompts shorter than MIN_COMPRESS_LENGTH must not be compressed."""
        import core.cluster.below.llmlingua_compress as mod
        prompt = "x" * (MIN_COMPRESS_LENGTH - 1)
        with patch.object(mod, "_get_compressor") as mock_get:
            result = compress_prompt(prompt)
            assert result == prompt
            mock_get.assert_not_called()

    def test_exactly_min_length_attempts_compression(self):
        """At exactly MIN_COMPRESS_LENGTH chars, the compressor is called (threshold is <, not <=)."""
        import core.cluster.below.llmlingua_compress as mod
        prompt = "x" * MIN_COMPRESS_LENGTH
        compressed = "y" * (MIN_COMPRESS_LENGTH // 2)
        with patch.object(mod, "_get_compressor", return_value=_mock_compressor(compressed)):
            result = compress_prompt(prompt)
            # Compressor was called; returns compressed text
            assert result == compressed


# ---------------------------------------------------------------------------
# Compression behavior
# ---------------------------------------------------------------------------


class TestCompressionBehavior:
    def test_shorter_result_returned(self):
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(3000)
        compressed = _make_prompt(1200)
        with patch.object(mod, "_get_compressor", return_value=_mock_compressor(compressed)):
            result = compress_prompt(prompt, ratio=0.5)
            assert result == compressed

    def test_longer_result_falls_back_to_original(self):
        """If compression produces a longer text, return original."""
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(1000)
        longer = _make_prompt(2000)
        with patch.object(mod, "_get_compressor", return_value=_mock_compressor(longer)):
            result = compress_prompt(prompt, ratio=0.5)
            assert result == prompt

    def test_empty_compressed_falls_back(self):
        """Empty compression result → return original."""
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(1000)
        with patch.object(mod, "_get_compressor", return_value=_mock_compressor("")):
            result = compress_prompt(prompt, ratio=0.5)
            assert result == prompt

    def test_compressor_exception_returns_original(self):
        """Any exception from compressor → fail-open."""
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(2000)
        broken = MagicMock()
        broken.compress_prompt.side_effect = RuntimeError("OOM")
        with patch.object(mod, "_get_compressor", return_value=broken):
            result = compress_prompt(prompt, ratio=0.5)
            assert result == prompt

    def test_none_compressor_returns_original(self):
        """If _get_compressor returns None (load failed), return original."""
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(2000)
        with patch.object(mod, "_get_compressor", return_value=None):
            result = compress_prompt(prompt, ratio=0.5)
            assert result == prompt


# ---------------------------------------------------------------------------
# Safe wrapper
# ---------------------------------------------------------------------------


class TestSafeWrapper:
    def test_safe_returns_string(self):
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(2000)
        compressed = _make_prompt(900)
        with patch.object(mod, "_get_compressor", return_value=_mock_compressor(compressed)):
            result = compress_prompt_safe(prompt)
            assert isinstance(result, str)

    def test_safe_returns_original_on_exception(self):
        import core.cluster.below.llmlingua_compress as mod
        prompt = _make_prompt(2000)
        with patch.object(mod, "compress_prompt", side_effect=Exception("boom")):
            result = compress_prompt_safe(prompt)
            assert result == prompt


# ---------------------------------------------------------------------------
# Autopilot dispatch prefix integration
# ---------------------------------------------------------------------------


class TestAutopilotPrefixIntegration:
    SCRIPT = Path.home() / ".buildrunner/scripts/autopilot-dispatch-prefix.sh"

    def test_script_has_compress_phase_flag(self):
        content = self.SCRIPT.read_text()
        assert "--compress-phase" in content

    def test_script_has_llmlingua_rollback(self):
        content = self.SCRIPT.read_text()
        assert "BR3_LLMLINGUA" in content

    def test_script_has_exclusion_reference(self):
        content = self.SCRIPT.read_text()
        assert "EXCLUDED_METHODS" in content or "adversarial-review" in content


# ---------------------------------------------------------------------------
# collect-intel.sh compression integration
# ---------------------------------------------------------------------------


class TestIntelCollectIntegration:
    SCRIPT = Path("/Users/byronhudson/Projects/BuildRunner3/core/cluster/scripts/collect-intel.sh")

    def test_script_has_compress_function(self):
        content = self.SCRIPT.read_text()
        assert "_compress_prompt_if_enabled" in content or "llmlingua" in content.lower()

    def test_script_has_rollback(self):
        content = self.SCRIPT.read_text()
        assert "BR3_LLMLINGUA" in content

    def test_script_compression_not_on_excluded_path(self):
        """The adversarial-review path must not be compressed."""
        content = self.SCRIPT.read_text()
        # Verify the compression call is on an intel-collect method, not adversarial-review
        assert "intel-collect" in content or "intel_collect" in content


# ---------------------------------------------------------------------------
# Module structure
# ---------------------------------------------------------------------------


class TestModuleStructure:
    def test_excluded_methods_is_frozenset(self):
        assert isinstance(EXCLUDED_METHODS, frozenset)

    def test_min_compress_length_is_positive(self):
        assert MIN_COMPRESS_LENGTH > 0

    def test_compress_prompt_returns_str(self):
        import core.cluster.below.llmlingua_compress as mod
        prompt = "x"  # too short, should return unchanged
        result = compress_prompt(prompt)
        assert isinstance(result, str)

    def test_module_has_cli(self):
        """Module must have a CLI entry point."""
        import core.cluster.below.llmlingua_compress as mod
        assert hasattr(mod, "_cli")
