"""
embed.py — Shared embedding client for Below's nomic-embed-text model.

Usage:
    from core.cluster.below.embed import embed_batch

    vectors = embed_batch(["log line one", "log line two"])
    # Returns list[list[float]], each vector is 768-d.
    # On Below-offline: raises BelowOfflineError (callers should catch and fall through).

Below API endpoint: POST http://10.0.1.105:11434/api/embed
Model: nomic-embed-text (768-d output, normalized)
"""

from __future__ import annotations

import logging
import time
from typing import Optional

import httpx

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

BELOW_HOST: str = "10.0.1.105"
BELOW_EMBED_PORT: int = 11434
BELOW_EMBED_URL: str = f"http://{BELOW_HOST}:{BELOW_EMBED_PORT}/api/embed"
EMBED_MODEL: str = "nomic-embed-text"

# Network settings
DEFAULT_TIMEOUT_SECONDS: float = 10.0
DEFAULT_RETRY_COUNT: int = 2
DEFAULT_RETRY_DELAY_SECONDS: float = 0.5

# Circuit breaker: trip after this many consecutive failures, reset after window
_CIRCUIT_THRESHOLD: int = 5
_CIRCUIT_RESET_WINDOW_SECONDS: float = 60.0

# Expected embedding dimension
EMBED_DIM: int = 768


# ---------------------------------------------------------------------------
# Exceptions
# ---------------------------------------------------------------------------


class BelowOfflineError(RuntimeError):
    """Raised when Below is unreachable or the circuit breaker is open."""


class EmbedDimensionError(ValueError):
    """Raised when the returned vectors have unexpected dimension."""


class MalformedEmbedResponse(ValueError):
    """Raised when Below returns a structurally invalid embed response."""


# ---------------------------------------------------------------------------
# Circuit breaker (module-level, single-process)
# ---------------------------------------------------------------------------


class _CircuitBreaker:
    def __init__(self, threshold: int, reset_window: float) -> None:
        self._threshold = threshold
        self._reset_window = reset_window
        self._failures: int = 0
        self._tripped_at: Optional[float] = None

    def record_success(self) -> None:
        self._failures = 0
        self._tripped_at = None

    def record_failure(self) -> None:
        self._failures += 1
        if self._failures >= self._threshold:
            self._tripped_at = time.monotonic()
            logger.warning(
                "embed circuit breaker: tripped after %d consecutive failures",
                self._failures,
            )

    def is_open(self) -> bool:
        if self._tripped_at is None:
            return False
        elapsed = time.monotonic() - self._tripped_at
        if elapsed >= self._reset_window:
            # Auto-reset: allow a probe attempt
            logger.info("embed circuit breaker: reset window elapsed — probing Below")
            self._failures = 0
            self._tripped_at = None
            return False
        return True


_circuit = _CircuitBreaker(_CIRCUIT_THRESHOLD, _CIRCUIT_RESET_WINDOW_SECONDS)


# ---------------------------------------------------------------------------
# Core embed function
# ---------------------------------------------------------------------------


def embed_batch(
    texts: list[str],
    *,
    model: str = EMBED_MODEL,
    timeout: float = DEFAULT_TIMEOUT_SECONDS,
    retries: int = DEFAULT_RETRY_COUNT,
    retry_delay: float = DEFAULT_RETRY_DELAY_SECONDS,
) -> list[list[float]]:
    """
    Embed a batch of texts using Below's nomic-embed-text model.

    Args:
        texts:        Non-empty list of strings to embed.
        model:        Ollama model name (default: nomic-embed-text).
        timeout:      HTTP timeout per attempt in seconds.
        retries:      Number of retry attempts on transient failure (0 = no retry).
        retry_delay:  Seconds to wait between retries.

    Returns:
        list[list[float]] — one 768-d vector per input text, same order as input.

    Raises:
        BelowOfflineError:      Below is unreachable (network) or circuit breaker open.
        MalformedEmbedResponse: Below returned a structurally invalid response.
        EmbedDimensionError:    Returned vectors have unexpected dimension.
        ValueError:             texts is empty.
    """
    if not texts:
        raise ValueError("embed_batch requires at least one text")

    if _circuit.is_open():
        raise BelowOfflineError("embed circuit breaker is open — Below is unavailable")

    payload = {"model": model, "input": texts}
    last_error: Optional[Exception] = None

    for attempt in range(retries + 1):
        try:
            response = httpx.post(
                BELOW_EMBED_URL,
                json=payload,
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

            # Validate response structure
            embeddings = _extract_embeddings(data, expected_count=len(texts))

            _circuit.record_success()
            logger.debug(
                "embed_batch: %d texts embedded via Below (%s)", len(texts), model
            )
            return embeddings

        except (httpx.ConnectError, httpx.TimeoutException, httpx.NetworkError) as exc:
            last_error = exc
            _circuit.record_failure()
            logger.warning(
                "embed_batch: attempt %d/%d — network error: %s",
                attempt + 1,
                retries + 1,
                exc,
            )
            if attempt < retries:
                time.sleep(retry_delay)

        except httpx.HTTPStatusError as exc:
            last_error = exc
            _circuit.record_failure()
            logger.warning(
                "embed_batch: attempt %d/%d — HTTP %s from Below",
                attempt + 1,
                retries + 1,
                exc.response.status_code,
            )
            if attempt < retries:
                time.sleep(retry_delay)

        except (MalformedEmbedResponse, EmbedDimensionError):
            # Don't retry structural errors — they won't fix themselves
            _circuit.record_failure()
            raise

    raise BelowOfflineError(
        f"embed_batch: Below unreachable after {retries + 1} attempts — {last_error}"
    ) from last_error


# ---------------------------------------------------------------------------
# Response validation helpers
# ---------------------------------------------------------------------------


def _extract_embeddings(data: object, *, expected_count: int) -> list[list[float]]:
    """
    Parse and validate the Ollama /api/embed response.

    Ollama returns:
        {"model": "...", "embeddings": [[...], [...]], "total_duration": ...}
    """
    if not isinstance(data, dict):
        raise MalformedEmbedResponse(
            f"Expected dict from Below /api/embed, got {type(data).__name__}"
        )

    embeddings = data.get("embeddings")
    if embeddings is None:
        raise MalformedEmbedResponse(
            f"Below /api/embed response missing 'embeddings' key; keys={list(data.keys())}"
        )

    if not isinstance(embeddings, list):
        raise MalformedEmbedResponse(
            f"'embeddings' should be a list, got {type(embeddings).__name__}"
        )

    if len(embeddings) != expected_count:
        raise MalformedEmbedResponse(
            f"Expected {expected_count} embeddings, got {len(embeddings)}"
        )

    validated: list[list[float]] = []
    for i, vec in enumerate(embeddings):
        if not isinstance(vec, list) or not all(
            isinstance(v, (int, float)) for v in vec
        ):
            raise MalformedEmbedResponse(
                f"Embedding [{i}] is not a list of numbers: {type(vec).__name__}"
            )
        if len(vec) != EMBED_DIM:
            raise EmbedDimensionError(
                f"Embedding [{i}] has dimension {len(vec)}, expected {EMBED_DIM}"
            )
        validated.append([float(v) for v in vec])

    return validated


# ---------------------------------------------------------------------------
# Health check utility
# ---------------------------------------------------------------------------


def check_below_embed_available(timeout: float = 3.0) -> bool:
    """
    Quick health check — returns True if Below's embed endpoint is reachable.
    Does NOT raise; safe to call from fail-open code paths.
    """
    try:
        resp = httpx.post(
            BELOW_EMBED_URL,
            json={"model": EMBED_MODEL, "input": ["ping"]},
            timeout=timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        return "embeddings" in data
    except Exception as exc:  # noqa: BLE001
        logger.debug("check_below_embed_available: %s", exc)
        return False


def reset_circuit_breaker() -> None:
    """Force-reset the circuit breaker (for tests and manual recovery)."""
    _circuit.record_success()
