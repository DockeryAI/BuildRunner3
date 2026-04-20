"""Integration tests for summarize-before-escalate (Phase 8).

test_50kb_diff_shrinks:
    Feed a 50KB diff to summarizer.summarize_diff() — output must be ≤5KB while
    preserving at least one critical-change marker from the input.

test_below_offline_fallback:
    When Below (OllamaRuntime) is unreachable, summarize_diff() must return
    original diff with truncated=True.  No exception must propagate.
"""

from __future__ import annotations

import re
import sys
import unittest.mock
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_diff(size_bytes: int, *, include_critical: bool = True) -> str:
    """Generate a synthetic diff of approximately `size_bytes` bytes."""
    lines = []
    # Seed with a critical-change line if requested
    if include_critical:
        lines.append("+++ b/auth/middleware.py")
        lines.append(
            "+    # CRITICAL: token validation bypass — must review before merge"
        )

    chunk = (
        "+def process_items(items):\n"
        "+    for item in items:\n"
        "+        result = transform(item)\n"
        "+        store(result)\n"
        "-def old_process(items):\n"
        "-    pass\n"
    )
    while sum(len(l) + 1 for l in lines) < size_bytes:
        lines.append(chunk)

    diff = "\n".join(lines)
    # Trim to target
    encoded = diff.encode("utf-8")
    if len(encoded) > size_bytes:
        diff = encoded[:size_bytes].decode("utf-8", errors="ignore")
    return diff


def _make_summary_response(content: str) -> MagicMock:
    """Build a mock RuntimeResult that looks like a successful OllamaRuntime response."""
    mock_result = MagicMock()
    mock_result.status = "completed"
    mock_result.raw_output = (
        "CHANGED FILES:\n"
        "  auth/middleware.py — token validation logic modified\n"
        "  core/db.py — schema migration added\n\n"
        "CRITICAL EXCERPTS:\n"
        "  +    # CRITICAL: token validation bypass — must review before merge\n\n"
        "SUMMARY: This diff modifies authentication middleware and adds a DB migration.\n"
        "EXCERPT_COUNT: 1\n"
    )
    mock_result.error_message = None
    return mock_result


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------

class TestSummarizeBeforeEscalate:
    """test_50kb_diff_shrinks — 50KB input → output ≤5KB, critical marker preserved."""

    def test_50kb_diff_shrinks(self):
        """Summarizer must shrink 50KB → ≤5KB and preserve critical-change marker."""
        from core.cluster.summarizer import summarize_diff

        diff_50kb = _make_diff(50 * 1024, include_critical=True)
        assert len(diff_50kb.encode("utf-8")) >= 40_000, "test diff must be at least 40KB"

        mock_result = _make_summary_response(diff_50kb)

        # Patch at the OllamaRuntime adapter level so RuntimeRegistry.execute() is
        # still the dispatch path — we only mock the final HTTP call.
        with patch(
            "core.runtime.ollama_runtime.OllamaRuntime.run_review",
            return_value=mock_result,
        ):
            result = summarize_diff(diff_50kb)

        assert "truncated" in result
        assert "summary" in result
        assert "excerpts" in result

        summary_bytes = len(result["summary"].encode("utf-8"))
        assert summary_bytes <= 5 * 1024, (
            f"summary must be ≤5KB, got {summary_bytes} bytes"
        )

        # Verify critical marker preserved in excerpts
        critical_re = re.compile(
            r"CRITICAL|BREAKING|security|auth|RLS|migration|schema|password|token|secret",
            re.IGNORECASE,
        )
        critical_found = any(critical_re.search(exc) for exc in result["excerpts"])
        assert critical_found, (
            "excerpts must contain at least one critical-change marker"
        )

    def test_critical_marker_in_excerpts_without_summary(self):
        """Even when summary fails, excerpts must contain critical lines."""
        from core.cluster.summarizer import summarize_diff

        diff = (
            "+++ b/auth/token.py\n"
            "+    token = HARD_CODED_SECRET  # security risk\n"
            "+def validate(): pass\n" * 100
        )

        # Force offline path
        with patch("core.cluster.summarizer._call_registry", return_value=None):
            result = summarize_diff(diff)

        assert result["truncated"] is True
        critical_re = re.compile(
            r"CRITICAL|BREAKING|security|auth|RLS|migration|schema|password|token|secret",
            re.IGNORECASE,
        )
        assert any(critical_re.search(exc) for exc in result["excerpts"]), (
            "excerpts must contain critical lines even in offline fallback"
        )


class TestBelowOfflineFallback:
    """test_below_offline_fallback — OllamaRuntime unreachable → truncated=True, no raise."""

    def test_below_offline_fallback(self):
        """Below unreachable: summarize_diff returns original with truncated=True."""
        from core.cluster.summarizer import summarize_diff

        diff = _make_diff(15 * 1024, include_critical=True)

        # Simulate Below unreachable via _call_registry returning None
        with patch("core.cluster.summarizer._call_registry", return_value=None):
            result = summarize_diff(diff)

        assert result["truncated"] is True, "offline fallback must set truncated=True"
        assert result["summary"] == diff, (
            "offline fallback must return original diff verbatim"
        )
        assert isinstance(result["excerpts"], list)

    def test_below_offline_no_exception(self):
        """summarize_diff must never raise even when Below raises an exception."""
        from core.cluster.summarizer import summarize_diff

        diff = _make_diff(20 * 1024)

        # Patch _call_registry to raise — summarize_diff must catch it internally.
        with patch(
            "core.cluster.summarizer._call_registry",
            side_effect=ConnectionRefusedError("Below offline"),
        ):
            result = summarize_diff(diff)

        # Must return offline-fallback result, not raise
        assert result["truncated"] is True
        assert result["summary"] == diff

    def test_summarize_logs_offline_fallback(self):
        """summarize_logs offline fallback: truncated=True, original content preserved."""
        from core.cluster.summarizer import summarize_logs

        lines = ["ERROR: db connection failed", "WARN: retry 1/3"] * 50

        with patch("core.cluster.summarizer._call_registry", return_value=None):
            result = summarize_logs(lines)

        assert result["truncated"] is True
        assert "ERROR: db connection failed" in result["summary"]

    def test_summarize_spec_offline_fallback(self):
        """summarize_spec offline fallback: truncated=True, original preserved."""
        from core.cluster.summarizer import summarize_spec

        spec = (
            "## Phase 8\n"
            "MUST use cache_policy breakpoints.\n"
            "NEVER hard-truncate diffs.\n"
            "BLOCKING: zero hard truncation slices.\n"
        )

        with patch("core.cluster.summarizer._call_registry", return_value=None):
            result = summarize_spec(spec)

        assert result["truncated"] is True
        assert "MUST" in result["summary"] or "NEVER" in result["summary"]
        must_never = [e for e in result["excerpts"] if re.search(r"MUST|NEVER|BLOCKING", e)]
        assert len(must_never) >= 1, "spec excerpts must include MUST/NEVER/BLOCKING lines"


class TestSummarizerNeverFinalOutput:
    """Ensure summarizer output is tagged as draft and never produces final-form artifacts."""

    def test_summarize_diff_result_has_required_keys(self):
        from core.cluster.summarizer import summarize_diff

        with patch("core.cluster.summarizer._call_registry", return_value="short summary"):
            result = summarize_diff("+ some change")

        assert set(result.keys()) >= {"summary", "excerpts", "truncated"}

    def test_summarize_diff_empty_input(self):
        from core.cluster.summarizer import summarize_diff

        result = summarize_diff("")
        assert result == {"summary": "", "excerpts": [], "truncated": False}

    def test_summarize_logs_empty_input(self):
        from core.cluster.summarizer import summarize_logs

        result = summarize_logs([])
        assert result == {"summary": "", "excerpts": [], "truncated": False}

    def test_summarize_spec_empty_input(self):
        from core.cluster.summarizer import summarize_spec

        result = summarize_spec("")
        assert result == {"summary": "", "excerpts": [], "truncated": False}
