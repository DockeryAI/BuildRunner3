"""
schema_classifier.py — Schema-constrained classifier via Below Ollama.

Calls Ollama /api/chat with `format: <json_schema>` to get structured JSON output,
validates against a caller-supplied Pydantic schema, and falls back to a
caller-injected Claude function on validation failure or timeout.

Usage:
    from pydantic import BaseModel
    from core.cluster.below.schema_classifier import SchemaClassifier

    class Verdict(BaseModel):
        action: Literal["yes", "no"]
        confidence: float
        reasoning: str

    classifier = SchemaClassifier(model="qwen2.5:14b")

    result, tier = classifier.classify(
        prompt="Should this CI failure be auto-remediated? ...",
        schema=Verdict,
        claude_fallback=my_claude_fn,   # optional; called if Below fails
    )
    # result: Verdict instance
    # tier: 1 (Below) or 2 (Claude fallback)

Models validated by this library:
    - qwen2.5:14b  — target <2% fallback rate on synthetic load
    - qwen3:8b     — target <5% fallback rate on synthetic load

Separate success metrics per model are logged to ~/.buildrunner/schema-classifier-metrics.jsonl.
"""

from __future__ import annotations

import json
import logging
import time
from typing import Any, Callable, Optional, Type, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from core.cluster.cluster_config import get_below_host, get_ollama_port

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

BELOW_HOST: str = get_below_host()          # single source of truth — core/cluster/cluster_config.py
BELOW_OLLAMA_PORT: int = get_ollama_port()  # single source of truth — core/cluster/cluster_config.py
BELOW_CHAT_URL: str = f"http://{BELOW_HOST}:{BELOW_OLLAMA_PORT}/api/chat"

DEFAULT_TIMEOUT: float = 12.0
DEFAULT_RETRY_BUDGET: int = 2  # attempts before falling back to Claude

from pathlib import Path

METRICS_FILE: Path = Path.home() / ".buildrunner" / "schema-classifier-metrics.jsonl"

T = TypeVar("T", bound=BaseModel)

# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class ClassifierBelowError(RuntimeError):
    """Below unreachable or returned an unretryable error."""


class ClassifierValidationError(ValueError):
    """Below responded but output failed schema validation."""


# ---------------------------------------------------------------------------
# Metrics
# ---------------------------------------------------------------------------


def _emit_metric(
    model: str,
    tier: int,
    latency_ms: float,
    accepted: bool,
    error: Optional[str] = None,
) -> None:
    try:
        record: dict[str, Any] = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "model": model,
            "tier": tier,
            "latency_ms": round(latency_ms, 1),
            "accepted": accepted,
        }
        if error:
            record["error"] = error
        METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with METRICS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception:  # noqa: BLE001
        pass


# ---------------------------------------------------------------------------
# Core classifier
# ---------------------------------------------------------------------------


class SchemaClassifier:
    """
    Schema-constrained classifier backed by Below Ollama.

    Args:
        model:   Ollama model name (qwen2.5:14b or qwen3:8b recommended).
        timeout: HTTP timeout per attempt in seconds.
        retries: Max attempts before fallback (default: DEFAULT_RETRY_BUDGET).
    """

    def __init__(
        self,
        model: str = "qwen2.5:14b",
        timeout: float = DEFAULT_TIMEOUT,
        retries: int = DEFAULT_RETRY_BUDGET,
    ) -> None:
        self.model = model
        self.timeout = timeout
        self.retries = retries

    def classify(
        self,
        prompt: str,
        schema: Type[T],
        *,
        system: str = "You are a precise JSON classifier. Respond ONLY with valid JSON matching the provided schema.",
        claude_fallback: Optional[Callable[[str], T]] = None,
    ) -> tuple[T, int]:
        """
        Classify using Below with schema-constrained JSON output.

        Args:
            prompt:          The classification task prompt.
            schema:          Pydantic BaseModel subclass defining the output shape.
            system:          System message for the Ollama chat request.
            claude_fallback: Optional callable(prompt) -> T; invoked after retries
                             exhausted. Library stays decoupled from Claude client.

        Returns:
            (result, tier) where tier=1 means Below succeeded, tier=2 means fallback used.

        Raises:
            ClassifierBelowError: Below unreachable AND no fallback provided.
            ClassifierValidationError: Below responded but schema invalid AND no fallback.
        """
        json_schema = schema.model_json_schema()
        last_error: Optional[Exception] = None

        for attempt in range(self.retries):
            t0 = time.monotonic()
            try:
                result = self._call_below(prompt, system, json_schema)
                validated = schema.model_validate(result)
                latency_ms = (time.monotonic() - t0) * 1000
                _emit_metric(self.model, 1, latency_ms, True)
                return validated, 1

            except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                _emit_metric(self.model, 1, latency_ms, False, error=str(exc))
                last_error = exc
                logger.debug(
                    "schema_classifier: attempt %d/%d — network error: %s",
                    attempt + 1, self.retries, exc,
                )

            except httpx.HTTPStatusError as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                _emit_metric(self.model, 1, latency_ms, False, error=f"HTTP {exc.response.status_code}")
                last_error = exc
                logger.debug(
                    "schema_classifier: attempt %d/%d — HTTP %s",
                    attempt + 1, self.retries, exc.response.status_code,
                )

            except (json.JSONDecodeError, ValidationError) as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                _emit_metric(self.model, 1, latency_ms, False, error=str(exc))
                last_error = exc
                logger.debug(
                    "schema_classifier: attempt %d/%d — validation error: %s",
                    attempt + 1, self.retries, exc,
                )

        # Retries exhausted — invoke Claude fallback if provided
        if claude_fallback is not None:
            t0 = time.monotonic()
            try:
                result = claude_fallback(prompt)
                latency_ms = (time.monotonic() - t0) * 1000
                _emit_metric(self.model, 2, latency_ms, True)
                logger.info(
                    "schema_classifier: fallback to Claude succeeded after %d Below attempts",
                    self.retries,
                )
                return result, 2
            except Exception as exc:
                latency_ms = (time.monotonic() - t0) * 1000
                _emit_metric(self.model, 2, latency_ms, False, error=str(exc))
                logger.error("schema_classifier: Claude fallback also failed: %s", exc)
                raise ClassifierBelowError(
                    f"Both Below ({self.retries} attempts) and Claude fallback failed. "
                    f"Last Below error: {last_error}; Claude error: {exc}"
                ) from exc

        # No fallback provided
        if isinstance(last_error, (json.JSONDecodeError, ValidationError)):
            raise ClassifierValidationError(
                f"Below schema validation failed after {self.retries} attempts: {last_error}"
            ) from last_error

        raise ClassifierBelowError(
            f"Below unreachable after {self.retries} attempts: {last_error}"
        ) from last_error

    def _call_below(
        self,
        prompt: str,
        system: str,
        json_schema: dict[str, Any],
    ) -> dict[str, Any]:
        """
        POST to Ollama /api/chat with format=<json_schema>.
        Returns parsed JSON dict. Raises on network error or non-200.
        """
        payload: dict[str, Any] = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
            "format": json_schema,
            "options": {
                "temperature": 0.1,  # Low temp for deterministic classification
                "num_predict": 256,
            },
        }

        resp = httpx.post(BELOW_CHAT_URL, json=payload, timeout=self.timeout)
        resp.raise_for_status()
        data = resp.json()

        # Extract the message content from Ollama response
        content = data.get("message", {}).get("content", "")
        if not content:
            raise json.JSONDecodeError("Empty content from Ollama", "", 0)

        return json.loads(content)


# ---------------------------------------------------------------------------
# Convenience functions for common yes/no classification
# ---------------------------------------------------------------------------


class YesNoResult(BaseModel):
    """Minimal yes/no classification schema."""

    decision: str  # "yes" or "no"
    confidence: float  # 0.0–1.0
    reasoning: str


def classify_yes_no(
    prompt: str,
    model: str = "qwen2.5:14b",
    claude_fallback: Optional[Callable[[str], YesNoResult]] = None,
    retries: int = DEFAULT_RETRY_BUDGET,
) -> tuple[YesNoResult, int]:
    """
    Convenience wrapper: classify a yes/no question via Below.

    Returns (YesNoResult, tier).
    """
    classifier = SchemaClassifier(model=model, retries=retries)
    return classifier.classify(
        prompt=prompt,
        schema=YesNoResult,
        system=(
            "You are a precise binary classifier. "
            "Respond ONLY with valid JSON: "
            '{"decision": "yes" or "no", "confidence": 0.0-1.0, "reasoning": "brief explanation"}'
        ),
        claude_fallback=claude_fallback,
    )


# ---------------------------------------------------------------------------
# Fallback rate stats utility
# ---------------------------------------------------------------------------


def fallback_rate_by_model(
    metrics_file: Path = METRICS_FILE,
) -> dict[str, dict[str, float]]:
    """
    Compute per-model fallback rate from the metrics file.

    Returns:
        {model: {"invocations": N, "tier1_rate": 0.92, "tier2_rate": 0.08}}
    """
    if not metrics_file.exists():
        return {}

    records: list[dict[str, Any]] = []
    with metrics_file.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue

    stats: dict[str, dict[str, int]] = {}
    for r in records:
        model = r.get("model", "unknown")
        tier = r.get("tier", 0)
        if model not in stats:
            stats[model] = {"total": 0, "tier1": 0, "tier2": 0}
        stats[model]["total"] += 1
        if tier == 1:
            stats[model]["tier1"] += 1
        elif tier == 2:
            stats[model]["tier2"] += 1

    result: dict[str, dict[str, float]] = {}
    for model, s in stats.items():
        total = s["total"] or 1
        result[model] = {
            "invocations": float(s["total"]),
            "tier1_rate": round(s["tier1"] / total, 4),
            "tier2_rate": round(s["tier2"] / total, 4),
        }
    return result
