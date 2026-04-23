"""
tests/cluster/test_schema_classifier.py

Unit tests for core.cluster.below.schema_classifier — schema-constrained
classifier via Below Ollama. All HTTP calls are mocked; no real network access.
"""

from __future__ import annotations

import json
import pytest
import httpx
from typing import Literal
from unittest.mock import patch, MagicMock

from pydantic import BaseModel

from core.cluster.below.schema_classifier import (
    ClassifierBelowError,
    ClassifierValidationError,
    SchemaClassifier,
    YesNoResult,
    classify_yes_no,
    fallback_rate_by_model,
)


# ---------------------------------------------------------------------------
# Test schemas
# ---------------------------------------------------------------------------


class ActionSchema(BaseModel):
    action: Literal["approve", "reject", "escalate"]
    confidence: float
    reasoning: str


class SimpleVerdict(BaseModel):
    verdict: Literal["yes", "no"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_ollama_response(content: dict) -> MagicMock:
    """Fake a successful Ollama /api/chat response."""
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.raise_for_status.return_value = None
    mock_resp.json.return_value = {
        "model": "qwen2.5:14b",
        "message": {"role": "assistant", "content": json.dumps(content)},
        "done": True,
    }
    return mock_resp


def _make_error_response(status_code: int) -> MagicMock:
    mock_resp = MagicMock()
    mock_resp.status_code = status_code
    mock_resp.raise_for_status.side_effect = httpx.HTTPStatusError(
        f"HTTP {status_code}", request=MagicMock(), response=mock_resp
    )
    return mock_resp


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestSchemaClassifierHappyPath:
    def test_classifies_with_valid_schema(self):
        payload = {"action": "approve", "confidence": 0.95, "reasoning": "looks good"}
        with patch("core.cluster.below.schema_classifier.httpx.post",
                   return_value=_make_ollama_response(payload)):
            clf = SchemaClassifier(model="qwen2.5:14b")
            result, tier = clf.classify("approve this?", ActionSchema)

        assert isinstance(result, ActionSchema)
        assert result.action == "approve"
        assert result.confidence == pytest.approx(0.95)
        assert tier == 1

    def test_yes_no_convenience_function(self):
        payload = {"decision": "yes", "confidence": 0.9, "reasoning": "matches pattern"}
        with patch("core.cluster.below.schema_classifier.httpx.post",
                   return_value=_make_ollama_response(payload)):
            result, tier = classify_yes_no("should we merge?", model="qwen2.5:14b")

        assert isinstance(result, YesNoResult)
        assert result.decision == "yes"
        assert tier == 1

    def test_tier_1_returned_on_below_success(self):
        payload = {"verdict": "yes"}
        with patch("core.cluster.below.schema_classifier.httpx.post",
                   return_value=_make_ollama_response(payload)):
            clf = SchemaClassifier(model="qwen3:8b")
            _, tier = clf.classify("test", SimpleVerdict)
        assert tier == 1

    def test_different_models_accepted(self):
        payload = {"verdict": "no"}
        for model in ["qwen2.5:14b", "qwen3:8b"]:
            with patch("core.cluster.below.schema_classifier.httpx.post",
                       return_value=_make_ollama_response(payload)):
                clf = SchemaClassifier(model=model)
                result, _ = clf.classify("test", SimpleVerdict)
            assert result.verdict == "no"


# ---------------------------------------------------------------------------
# Pydantic schema validation
# ---------------------------------------------------------------------------


class TestSchemaValidation:
    def test_invalid_schema_triggers_fallback(self):
        """Below returns valid JSON but wrong shape → fallback invoked."""
        bad_payload = {"wrong_key": "value"}
        fallback_called = []

        def my_fallback(prompt: str) -> ActionSchema:
            fallback_called.append(prompt)
            return ActionSchema(action="escalate", confidence=0.5, reasoning="fallback")

        with patch("core.cluster.below.schema_classifier.httpx.post",
                   return_value=_make_ollama_response(bad_payload)):
            clf = SchemaClassifier(model="qwen2.5:14b", retries=1)
            result, tier = clf.classify("test", ActionSchema, claude_fallback=my_fallback)

        assert tier == 2
        assert result.action == "escalate"
        assert len(fallback_called) == 1

    def test_invalid_json_triggers_fallback(self):
        """Below returns non-JSON in message content."""
        mock_resp = MagicMock()
        mock_resp.raise_for_status.return_value = None
        mock_resp.json.return_value = {
            "message": {"content": "not valid json at all {{{{"}
        }

        def my_fallback(prompt: str) -> SimpleVerdict:
            return SimpleVerdict(verdict="no")

        with patch("core.cluster.below.schema_classifier.httpx.post", return_value=mock_resp):
            clf = SchemaClassifier(model="qwen3:8b", retries=1)
            result, tier = clf.classify("test", SimpleVerdict, claude_fallback=my_fallback)

        assert tier == 2
        assert result.verdict == "no"

    def test_no_fallback_raises_on_validation_failure(self):
        bad_payload = {"not": "valid"}
        with patch("core.cluster.below.schema_classifier.httpx.post",
                   return_value=_make_ollama_response(bad_payload)):
            clf = SchemaClassifier(model="qwen2.5:14b", retries=1)
            with pytest.raises(ClassifierValidationError):
                clf.classify("test", ActionSchema)


# ---------------------------------------------------------------------------
# Fallback-to-Claude harness
# ---------------------------------------------------------------------------


class TestClaudeFallbackHarness:
    def test_fallback_called_on_below_unreachable(self):
        fallback_called = []

        def my_fallback(prompt: str) -> YesNoResult:
            fallback_called.append(prompt)
            return YesNoResult(decision="no", confidence=0.7, reasoning="claude fallback")

        with patch("core.cluster.below.schema_classifier.httpx.post",
                   side_effect=httpx.ConnectError("refused")):
            clf = SchemaClassifier(model="qwen2.5:14b", retries=2)
            result, tier = clf.classify("test?", YesNoResult, claude_fallback=my_fallback)

        assert tier == 2
        assert result.decision == "no"
        assert len(fallback_called) == 1

    def test_no_fallback_raises_on_network_failure(self):
        with patch("core.cluster.below.schema_classifier.httpx.post",
                   side_effect=httpx.ConnectError("refused")):
            clf = SchemaClassifier(model="qwen2.5:14b", retries=2)
            with pytest.raises(ClassifierBelowError):
                clf.classify("test?", YesNoResult)

    def test_fallback_failure_raises_below_error(self):
        def bad_fallback(prompt: str) -> YesNoResult:
            raise RuntimeError("claude also down")

        with patch("core.cluster.below.schema_classifier.httpx.post",
                   side_effect=httpx.ConnectError("refused")):
            clf = SchemaClassifier(model="qwen2.5:14b", retries=1)
            with pytest.raises(ClassifierBelowError, match="Claude fallback also failed|Both Below.*Claude fallback failed"):
                clf.classify("test", YesNoResult, claude_fallback=bad_fallback)

    def test_library_decoupled_from_claude_client(self):
        """Fallback is a plain callable — no anthropic import required in library."""
        import importlib
        import sys

        # Confirm schema_classifier doesn't import anthropic at module level
        mod = importlib.import_module("core.cluster.below.schema_classifier")
        src = open(mod.__file__).read()
        assert "import anthropic" not in src
        assert "from anthropic" not in src


# ---------------------------------------------------------------------------
# Retry budget
# ---------------------------------------------------------------------------


class TestRetryBudget:
    def test_retries_exhausted_before_fallback(self):
        call_count = 0

        def counting_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            raise httpx.ConnectError("down")

        with patch("core.cluster.below.schema_classifier.httpx.post",
                   side_effect=counting_post):
            clf = SchemaClassifier(model="qwen2.5:14b", retries=3)
            with pytest.raises(ClassifierBelowError):
                clf.classify("test", SimpleVerdict)

        assert call_count == 3, f"Expected 3 attempts, got {call_count}"

    def test_default_retry_budget_is_2(self):
        clf = SchemaClassifier()
        assert clf.retries == 2

    def test_custom_retry_budget(self):
        clf = SchemaClassifier(retries=5)
        assert clf.retries == 5

    def test_second_attempt_succeeds(self):
        call_count = 0
        payload = {"verdict": "yes"}

        def flaky_post(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise httpx.ConnectError("transient")
            return _make_ollama_response(payload)

        with patch("core.cluster.below.schema_classifier.httpx.post",
                   side_effect=flaky_post):
            clf = SchemaClassifier(model="qwen3:8b", retries=2)
            result, tier = clf.classify("test", SimpleVerdict)

        assert call_count == 2
        assert tier == 1
        assert result.verdict == "yes"


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


class TestMetrics:
    def test_metrics_written_on_success(self, tmp_path):
        payload = {"verdict": "yes"}
        metrics_path = tmp_path / "metrics.jsonl"

        with patch("core.cluster.below.schema_classifier.METRICS_FILE", metrics_path):
            with patch("core.cluster.below.schema_classifier.httpx.post",
                       return_value=_make_ollama_response(payload)):
                clf = SchemaClassifier(model="qwen2.5:14b")
                clf.classify("test", SimpleVerdict)

        lines = metrics_path.read_text().strip().splitlines()
        assert len(lines) == 1
        record = json.loads(lines[0])
        assert record["tier"] == 1
        assert record["accepted"] is True
        assert record["model"] == "qwen2.5:14b"

    def test_fallback_rate_by_model(self, tmp_path):
        metrics_path = tmp_path / "metrics.jsonl"
        records = [
            {"model": "qwen2.5:14b", "tier": 1, "latency_ms": 100, "accepted": True, "ts": "x"},
            {"model": "qwen2.5:14b", "tier": 1, "latency_ms": 110, "accepted": True, "ts": "x"},
            {"model": "qwen2.5:14b", "tier": 2, "latency_ms": 500, "accepted": True, "ts": "x"},
            {"model": "qwen3:8b", "tier": 1, "latency_ms": 90, "accepted": True, "ts": "x"},
        ]
        with metrics_path.open("w") as f:
            for r in records:
                f.write(json.dumps(r) + "\n")

        stats = fallback_rate_by_model(metrics_file=metrics_path)

        assert "qwen2.5:14b" in stats
        assert stats["qwen2.5:14b"]["tier2_rate"] == pytest.approx(1 / 3, abs=0.01)
        assert stats["qwen3:8b"]["tier1_rate"] == pytest.approx(1.0)
