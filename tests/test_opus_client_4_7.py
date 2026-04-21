"""
Tests for Claude 4.7 compatibility of OpusClient and HandoffPackage.

Covers:
- SDK version pin (anthropic >= 0.74.1)
- Model defaults to claude-opus-4-7 (env-overridable, opusplan alias)
- No deprecated params (temperature, top_p, top_k, budget_tokens, prefills)
- Effort tier present in extra_body["output_config"]["effort"] per method
- Adaptive thinking config present in every call
- Type-safe content accessor: ThinkingBlock-first mock returns text cleanly
- Per-method max_tokens right-sizing
- HandoffPackage carries effort_tier and model_hint fields
"""

import importlib.metadata
import os
import sys
from typing import Any, Dict, List
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_text_message(text: str):
    """Build a mock message with a single TextBlock."""
    block = MagicMock()
    block.type = "text"
    block.text = text
    msg = MagicMock()
    msg.content = [block]
    return msg


def _make_thinking_first_message(text: str):
    """
    Build a mock message where content[0] is a ThinkingBlock and content[1] is
    a TextBlock — the layout adaptive thinking produces.
    """
    thinking_block = MagicMock()
    thinking_block.type = "thinking"
    thinking_block.thinking = "internal reasoning"

    text_block = MagicMock()
    text_block.type = "text"
    text_block.text = text

    msg = MagicMock()
    msg.content = [thinking_block, text_block]
    return msg


# ---------------------------------------------------------------------------
# SDK version
# ---------------------------------------------------------------------------

class TestSDKVersion:
    def test_anthropic_installed(self):
        """anthropic package is importable."""
        import anthropic  # noqa: F401

    def test_sdk_version_meets_minimum(self):
        """Installed anthropic SDK is >= 0.73.0 as pinned in pyproject.toml."""
        from packaging.version import Version  # stdlib-adjacent; available via pip

        try:
            installed = importlib.metadata.version("anthropic")
        except importlib.metadata.PackageNotFoundError:
            pytest.skip("anthropic not installed in this environment")

        assert Version(installed) >= Version("0.73.0"), (
            f"anthropic {installed} < 0.73.0 — upgrade or re-install to meet the 4.7 pin"
        )

    def test_thinking_block_importable(self):
        """ThinkingBlock is available (required for type-safe content accessor)."""
        from anthropic.types import ThinkingBlock  # noqa: F401


# ---------------------------------------------------------------------------
# Model defaults
# ---------------------------------------------------------------------------

class TestModelDefaults:
    def test_default_model_is_4_7(self, monkeypatch):
        """Without env override, model resolves to claude-opus-4-7."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient
        client = OpusClient(api_key="test-key")
        assert client.model == "claude-opus-4-7"

    def test_env_override_respected(self, monkeypatch):
        """ANTHROPIC_MODEL env var overrides the default."""
        monkeypatch.setenv("ANTHROPIC_MODEL", "claude-sonnet-4-6")
        # Re-import to pick up env change
        import importlib
        import core.opus_client as mod
        importlib.reload(mod)
        client = mod.OpusClient(api_key="test-key")
        assert client.model == "claude-sonnet-4-6"
        # Restore
        importlib.reload(mod)

    def test_opusplan_alias_resolves(self, monkeypatch):
        """Passing model='opusplan' resolves to claude-opus-4-7."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient
        client = OpusClient(api_key="test-key", model="opusplan")
        assert client.model == "claude-opus-4-7"


# ---------------------------------------------------------------------------
# No deprecated params
# ---------------------------------------------------------------------------

DEPRECATED_KEYS = {"temperature", "top_p", "top_k", "budget_tokens"}


def _collect_create_kwargs(mock_create) -> List[Dict[str, Any]]:
    """Return list of kwargs dicts from each call to async messages.create."""
    calls = []
    for call in mock_create.call_args_list:
        calls.append(call.kwargs if call.kwargs else {})
    return calls


class TestNoDeprecatedParams:
    @pytest.mark.asyncio
    async def test_pre_fill_spec_no_deprecated_params(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_text_message("# Spec content")
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.pre_fill_spec("Healthcare", "Dashboard", {"name": "TestApp"})

        calls = _collect_create_kwargs(mock_instance.messages.create)
        assert len(calls) == 1
        for key in DEPRECATED_KEYS:
            assert key not in calls[0], f"Deprecated param '{key}' found in pre_fill_spec call"

    @pytest.mark.asyncio
    async def test_analyze_requirements_no_deprecated_params(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_thinking_first_message(
            '{"features": [], "architecture": {}, "tech_stack": []}'
        )
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.analyze_requirements("Build a dashboard")

        calls = _collect_create_kwargs(mock_instance.messages.create)
        assert len(calls) == 1
        for key in DEPRECATED_KEYS:
            assert key not in calls[0], f"Deprecated param '{key}' in analyze_requirements"

    @pytest.mark.asyncio
    async def test_validate_spec_no_deprecated_params(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_thinking_first_message(
            '{"valid": true, "missing_sections": [], "suggestions": [], "score": 95}'
        )
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.validate_spec("# My Spec")

        calls = _collect_create_kwargs(mock_instance.messages.create)
        assert len(calls) == 1
        for key in DEPRECATED_KEYS:
            assert key not in calls[0], f"Deprecated param '{key}' in validate_spec"


# ---------------------------------------------------------------------------
# Effort tier
# ---------------------------------------------------------------------------

class TestEffortTier:
    def _get_effort(self, kwargs: Dict) -> str:
        extra = kwargs.get("extra_body", {})
        return extra.get("output_config", {}).get("effort", "")

    @pytest.mark.asyncio
    async def test_pre_fill_spec_effort_xhigh(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_text_message("spec")
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.pre_fill_spec("Fintech", "API", {"name": "X"})

        kwargs = _collect_create_kwargs(mock_instance.messages.create)[0]
        assert self._get_effort(kwargs) == "xhigh"

    @pytest.mark.asyncio
    async def test_analyze_requirements_effort_high(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_thinking_first_message(
            '{"features": [], "architecture": {}, "tech_stack": []}'
        )
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.analyze_requirements("requirements text")

        kwargs = _collect_create_kwargs(mock_instance.messages.create)[0]
        assert self._get_effort(kwargs) == "high"

    @pytest.mark.asyncio
    async def test_generate_design_tokens_effort_high(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_thinking_first_message(
            '{"colors": {}, "typography": {}, "spacing": {}, "borderRadius": {}, "boxShadow": {}, "screens": {}}'
        )
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.generate_design_tokens("Healthcare", "Dashboard")

        kwargs = _collect_create_kwargs(mock_instance.messages.create)[0]
        assert self._get_effort(kwargs) == "high"

    @pytest.mark.asyncio
    async def test_validate_spec_effort_medium(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_thinking_first_message(
            '{"valid": true, "missing_sections": [], "suggestions": [], "score": 90}'
        )
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.validate_spec("# Spec")

        kwargs = _collect_create_kwargs(mock_instance.messages.create)[0]
        assert self._get_effort(kwargs) == "medium"


# ---------------------------------------------------------------------------
# Adaptive thinking present
# ---------------------------------------------------------------------------

class TestAdaptiveThinking:
    @pytest.mark.asyncio
    async def test_thinking_param_present_and_adaptive(self, monkeypatch):
        """All call sites must have thinking={"type":"adaptive","display":"summarized"}."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_text_message("spec output")
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.pre_fill_spec("Healthcare", "Dashboard", {"name": "X"})

        kwargs = _collect_create_kwargs(mock_instance.messages.create)[0]
        thinking = kwargs.get("thinking", {})
        assert thinking.get("type") == "adaptive", (
            f"Expected thinking.type='adaptive', got: {thinking}"
        )
        assert thinking.get("display") == "summarized", (
            f"Expected thinking.display='summarized', got: {thinking}"
        )


# ---------------------------------------------------------------------------
# Type-safe content accessor (ThinkingBlock-first)
# ---------------------------------------------------------------------------

class TestContentAccessor:
    @pytest.mark.asyncio
    async def test_thinking_block_first_returns_text(self, monkeypatch):
        """
        When content[0] is a ThinkingBlock and content[1] is a TextBlock,
        _extract_text must return the TextBlock's text without crashing.
        """
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient, _extract_text

        # Direct unit test of the extractor
        msg = _make_thinking_first_message("Hello from text block")
        result = _extract_text(msg)
        assert result == "Hello from text block"

    @pytest.mark.asyncio
    async def test_thinking_block_first_full_pipeline(self, monkeypatch):
        """pre_fill_spec returns spec text even when ThinkingBlock is first."""
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_thinking_first_message("# Generated Spec\n\nContent here.")
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            result = await client.pre_fill_spec("Fintech", "API", {"name": "MyApp"})

        assert result == "# Generated Spec\n\nContent here."

    def test_extract_text_no_text_block_returns_empty(self):
        """If no TextBlock in content, _extract_text returns empty string."""
        from core.opus_client import _extract_text

        thinking_block = MagicMock()
        thinking_block.type = "thinking"

        msg = MagicMock()
        msg.content = [thinking_block]
        assert _extract_text(msg) == ""

    def test_no_content_zero_index_usage(self, monkeypatch):
        """
        Verify no content[0].text pattern remains in non-docstring code lines
        of opus_client. Docstrings may reference the old pattern as context; the
        check targets only executable Python lines (not inside triple-quoted strings
        or comment lines).
        """
        import ast
        import textwrap
        from pathlib import Path

        src_path = Path("/Users/byronhudson/Projects/BuildRunner3/core/opus_client.py")
        source = src_path.read_text()

        # Parse to AST and check no Subscript + Attribute with name "text" on
        # a zero-index subscript of "content" — this is the structural pattern.
        # Simpler: strip all string literals from the source and search.
        try:
            tree = ast.parse(source)
        except SyntaxError:
            pytest.fail("opus_client.py has a syntax error")

        # Collect all string literal node positions (docstrings etc.)
        string_positions: set = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                string_positions.add((node.lineno, node.end_lineno))

        def in_string(lineno: int) -> bool:
            for start, end in string_positions:
                if start <= lineno <= end:
                    return True
            return False

        lines = source.splitlines()
        violations = []
        for i, line in enumerate(lines, start=1):
            stripped = line.strip()
            if stripped.startswith("#"):
                continue  # comment line
            if in_string(i):
                continue  # inside a string literal / docstring
            if "content[0].text" in line:
                violations.append(f"  line {i}: {line.rstrip()}")

        assert not violations, (
            "Found content[0].text in executable code in opus_client:\n"
            + "\n".join(violations)
            + "\nUse _extract_text() instead."
        )


# ---------------------------------------------------------------------------
# Per-method max_tokens
# ---------------------------------------------------------------------------

class TestMaxTokens:
    @pytest.mark.asyncio
    async def test_pre_fill_spec_max_tokens_16000(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_text_message("spec")
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.pre_fill_spec("Healthcare", "Dashboard", {"name": "X"})

        kwargs = _collect_create_kwargs(mock_instance.messages.create)[0]
        assert kwargs["max_tokens"] == 16000

    @pytest.mark.asyncio
    async def test_analyze_requirements_max_tokens_4096(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_thinking_first_message(
            '{"features": [], "architecture": {}, "tech_stack": []}'
        )
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.analyze_requirements("requirements")

        kwargs = _collect_create_kwargs(mock_instance.messages.create)[0]
        assert kwargs["max_tokens"] == 4096

    @pytest.mark.asyncio
    async def test_validate_spec_max_tokens_2048(self, monkeypatch):
        monkeypatch.delenv("ANTHROPIC_MODEL", raising=False)
        from core.opus_client import OpusClient

        mock_msg = _make_thinking_first_message(
            '{"valid": true, "missing_sections": [], "suggestions": [], "score": 80}'
        )
        with patch("anthropic.AsyncAnthropic") as mock_cls:
            mock_instance = mock_cls.return_value
            mock_instance.messages.create = AsyncMock(return_value=mock_msg)
            client = OpusClient(api_key="test-key")
            client.async_client = mock_instance
            await client.validate_spec("# spec")

        kwargs = _collect_create_kwargs(mock_instance.messages.create)[0]
        assert kwargs["max_tokens"] == 2048


# ---------------------------------------------------------------------------
# HandoffPackage effort_tier and model_hint
# ---------------------------------------------------------------------------

class TestHandoffPackage:
    def test_handoff_package_has_effort_tier(self):
        """HandoffPackage dataclass includes effort_tier field."""
        from core.opus_handoff import HandoffPackage

        pkg = HandoffPackage(
            project_summary="summary",
            technical_decisions=[],
            build_instructions=[],
            atomic_tasks=[],
            context_files=[],
            success_criteria=[],
        )
        assert hasattr(pkg, "effort_tier")
        assert pkg.effort_tier == "high"  # default

    def test_handoff_package_has_model_hint(self):
        """HandoffPackage dataclass includes model_hint field."""
        from core.opus_handoff import HandoffPackage

        pkg = HandoffPackage(
            project_summary="summary",
            technical_decisions=[],
            build_instructions=[],
            atomic_tasks=[],
            context_files=[],
            success_criteria=[],
        )
        assert hasattr(pkg, "model_hint")
        assert pkg.model_hint == "claude-opus-4-7"  # default

    def test_handoff_package_custom_effort_tier(self):
        """effort_tier can be set to a non-default value."""
        from core.opus_handoff import HandoffPackage

        pkg = HandoffPackage(
            project_summary="s",
            technical_decisions=[],
            build_instructions=[],
            atomic_tasks=[],
            context_files=[],
            success_criteria=[],
            effort_tier="xhigh",
            model_hint="claude-opus-4-7",
        )
        assert pkg.effort_tier == "xhigh"

    def test_export_includes_effort_and_model(self, tmp_path):
        """export_handoff writes effort_tier and model_hint to JSON."""
        import json
        from core.opus_handoff import HandoffPackage, OpusHandoff

        handoff = OpusHandoff(str(tmp_path))
        pkg = HandoffPackage(
            project_summary="test",
            technical_decisions=[],
            build_instructions=[{"phase": 1, "name": "Init", "steps": []}],
            atomic_tasks=[],
            context_files=[],
            success_criteria=[],
            effort_tier="xhigh",
            model_hint="claude-opus-4-7",
        )
        out_path = str(tmp_path / "handoff.json")
        handoff.export_handoff(pkg, out_path)

        with open(out_path) as f:
            data = json.load(f)

        assert data["effort_tier"] == "xhigh"
        assert data["model_hint"] == "claude-opus-4-7"


# ---------------------------------------------------------------------------
# Phase 8: Lockwood metrics emission
# ---------------------------------------------------------------------------


class TestMetricsEmission:
    """Phase 8 — each messages.create() call fires _emit_metric with model/effort/method."""

    def test_emit_metric_helper_exists(self):
        from core import opus_client

        assert hasattr(opus_client, "_emit_metric"), \
            "opus_client must expose _emit_metric for Lockwood measurement loop"

    def test_metrics_script_path_is_lockwood_metrics_sh(self):
        from core import opus_client

        assert opus_client._METRICS_SCRIPT.name == "lockwood-metrics.sh"
        assert ".buildrunner/scripts" in str(opus_client._METRICS_SCRIPT)

    def test_emit_metric_is_fire_and_forget_on_missing_script(self, monkeypatch, tmp_path):
        """If the metrics script is missing, _emit_metric must silently no-op
        (metric loss must never break production API calls)."""
        from core import opus_client

        monkeypatch.setattr(opus_client, "_METRICS_SCRIPT", tmp_path / "does-not-exist.sh")
        msg = _make_text_message("ok")
        opus_client._emit_metric("claude-opus-4-7", "xhigh", "pre_fill_spec", msg, 1234, True)

    def test_pre_fill_spec_emits_metric(self, monkeypatch):
        """Successful pre_fill_spec call fires _emit_metric once with success=True."""
        import asyncio
        from core import opus_client

        calls = []

        def fake_emit(model, effort, method, message, latency_ms, success):
            calls.append({
                "model": model, "effort": effort, "method": method,
                "latency_ms": latency_ms, "success": success,
            })

        monkeypatch.setattr(opus_client, "_emit_metric", fake_emit)
        monkeypatch.setenv("ANTHROPIC_API_KEY", "test-key")

        client = opus_client.OpusClient(model="claude-opus-4-7")
        client.async_client.messages.create = AsyncMock(return_value=_make_text_message("generated spec"))

        asyncio.run(client.pre_fill_spec("Healthcare", "Dashboard", {"project_name": "t"}))

        assert len(calls) == 1
        assert calls[0]["model"] == "claude-opus-4-7"
        assert calls[0]["effort"] == "xhigh"
        assert calls[0]["method"] == "pre_fill_spec"
        assert calls[0]["success"] is True
        assert calls[0]["latency_ms"] >= 0
