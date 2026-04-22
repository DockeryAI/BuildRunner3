import pytest
from pydantic import ValidationError

from core.runtime.metrics_schema import DispatchMetrics


def _valid_payload() -> dict[str, object]:
    return {
        "timestamp": "2026-04-22T14:00:00Z",
        "session_id": "session-1",
        "bucket": "backend-build",
        "builder": "codex",
        "model": "gpt-5.4",
        "effort": "medium",
        "prompt_tokens": 10,
        "output_tokens": 20,
        "latency_ms": 100,
        "done_when_passed": True,
        "verdict": "passed",
    }


def test_dispatch_metrics_accepts_valid_payload() -> None:
    metrics = DispatchMetrics(**_valid_payload())

    assert metrics.builder == "codex"
    assert metrics.done_when_passed is True
    assert metrics.verdict == "passed"


def test_dispatch_metrics_requires_done_when_passed() -> None:
    payload = _valid_payload()
    payload.pop("done_when_passed")

    with pytest.raises(ValidationError):
        DispatchMetrics(**payload)


def test_dispatch_metrics_requires_override_reason_for_overridden_verdict() -> None:
    payload = _valid_payload()
    payload["verdict"] = "overridden"

    with pytest.raises(ValidationError):
        DispatchMetrics(**payload)


def test_dispatch_metrics_accepts_override_reason_when_overridden() -> None:
    payload = _valid_payload()
    payload["verdict"] = "overridden"
    payload["override_reason"] = "manual operator override"

    metrics = DispatchMetrics(**payload)

    assert metrics.override_reason == "manual operator override"
