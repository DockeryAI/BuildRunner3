"""
claude_cache_wrapper.py — Thin semantic-cache wrapper for Claude API calls.

Routes Claude API calls through SemanticCache (Phase 4) before dispatching
to the actual Anthropic API. Reduces token spend on repeated/similar prompts
by serving cached answers when cosine similarity exceeds the cache threshold
(default 0.95).

Usage:
    from core.cluster.below.claude_cache_wrapper import ClaudeCacheWrapper

    wrapper = ClaudeCacheWrapper()
    text = await wrapper.call(
        model="claude-opus-4-7",
        method="analyze_requirements",
        messages=[{"role": "user", "content": prompt}],
    )

Exclusion list (always skip_cache=True):
    - ai_code_review          — per-diff, must never cache
    - adversarial-review      — quality-sensitive, must never cache
    - arbiter                 — quality-sensitive, must never cache
    - cross-model-review      — quality-sensitive, must never cache
    - reviewer                — quality-sensitive, must never cache
    - user-specific context   — personalised, must never cache

7-day warm-up period:
    During the first 7 days of cache operation, cache hits are logged but
    not served. The SemanticCache.lookup() returns None during warm-up — the
    wrapper transparently falls through to the live API. This prevents false
    positives before the cache has been calibrated.

Metrics:
    Hit/miss and similarity distribution written to:
    ~/.buildrunner/cache-wrapper-metrics.jsonl

Rollback:
    BR3_SEMANTIC_CACHE=off — wrapper calls live API unconditionally.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

# Methods that MUST bypass the cache (security/quality-sensitive)
_CACHE_EXCLUSION_METHODS: frozenset[str] = frozenset({
    "ai_code_review",
    "adversarial_review",
    "adversarial-review",
    "arbiter",
    "cross_model_review",
    "cross-model-review",
    "reviewer",
    "review_diff",
    "analyze_architecture",
})

_CACHE_ENABLED: bool = os.environ.get("BR3_SEMANTIC_CACHE", "on").lower() != "off"

_DB_PATH: Path = Path(os.environ.get(
    "BR3_CACHE_DB",
    str(Path.home() / ".buildrunner" / "state" / "answer_cache.db"),
))

_METRICS_FILE: Path = Path.home() / ".buildrunner" / "cache-wrapper-metrics.jsonl"


def _emit_metric(
    model: str,
    method: str,
    hit: bool,
    similarity: float | None,
    latency_ms: int,
    skipped: bool = False,
    skip_reason: str = "",
) -> None:
    """Fire-and-forget metric write. Never raises."""
    entry = {
        "ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        "model": model,
        "method": method,
        "hit": hit,
        "similarity": similarity,
        "latency_ms": latency_ms,
        "skipped": skipped,
        "skip_reason": skip_reason,
    }
    try:
        _METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(_METRICS_FILE, "a", encoding="utf-8") as mf:
            mf.write(json.dumps(entry) + "\n")
    except OSError:
        pass


def _prompt_from_messages(messages: List[Dict[str, Any]]) -> str:
    """Flatten messages list to a single string for cache keying."""
    parts = []
    for msg in messages:
        role = msg.get("role", "")
        content = msg.get("content", "")
        if isinstance(content, list):
            # Content blocks (tool use etc.) — extract text blocks only
            text_parts = [b.get("text", "") for b in content if isinstance(b, dict) and b.get("type") == "text"]
            content = " ".join(text_parts)
        parts.append(f"{role}: {content}")
    return "\n".join(parts)


class ClaudeCacheWrapper:
    """
    Semantic cache wrapper for Claude API calls.

    Thread-safe: each call opens the SQLite connection independently
    (WAL mode handles concurrent reads).
    """

    def __init__(
        self,
        db_path: Path | None = None,
        threshold: float = 0.95,
        ttl_days: int = 30,
        warmup_days: int = 7,
    ) -> None:
        self._db_path = db_path or _DB_PATH
        self._threshold = threshold
        self._ttl_days = ttl_days
        self._warmup_days = warmup_days
        self._cache: Any = None  # lazy-loaded SemanticCache

    def _get_cache(self) -> Any:
        """Lazy-load SemanticCache to avoid import overhead when disabled."""
        if self._cache is None:
            from core.cluster.below.semantic_cache import SemanticCache
            self._cache = SemanticCache(
                db_path=self._db_path,
                threshold=self._threshold,
                ttl_days=self._ttl_days,
                warmup_days=self._warmup_days,
            )
        return self._cache

    def _should_skip(self, method: str, skip_cache: bool) -> tuple[bool, str]:
        """Return (should_skip, reason)."""
        if not _CACHE_ENABLED:
            return True, "BR3_SEMANTIC_CACHE=off"
        if skip_cache:
            return True, "caller skip_cache=True"
        if method in _CACHE_EXCLUSION_METHODS:
            return True, f"method {method!r} in exclusion list"
        return False, ""

    async def call(
        self,
        *,
        model: str,
        method: str,
        messages: List[Dict[str, Any]],
        skip_cache: bool = False,
        # Pass-through kwargs for the underlying Anthropic API
        **api_kwargs: Any,
    ) -> str:
        """
        Route a Claude API call through the semantic cache.

        Args:
            model:      Claude model identifier (e.g. "claude-opus-4-7").
            method:     Caller-defined method name (used for cache partitioning
                        and exclusion list matching).
            messages:   Anthropic messages array.
            skip_cache: Force bypass for this call.
            **api_kwargs: Forwarded to anthropic.messages.create() unchanged.

        Returns:
            Extracted text string from the response (cached or live).

        Guarantees:
            - Never raises on cache errors (falls through to live API).
            - Never caches excluded methods.
            - Returns live response if Below embed is offline.
        """
        prompt = _prompt_from_messages(messages)
        should_skip, skip_reason = self._should_skip(method, skip_cache)

        if not should_skip:
            t0 = time.perf_counter()
            try:
                cached = self._get_cache().lookup(model, method, prompt)
                latency = int((time.perf_counter() - t0) * 1000)
                if cached is not None:
                    _emit_metric(model, method, hit=True, similarity=None, latency_ms=latency)
                    logger.debug("cache hit: model=%s method=%s", model, method)
                    return cached
                _emit_metric(model, method, hit=False, similarity=None, latency_ms=latency)
            except Exception as exc:  # noqa: BLE001
                logger.debug("cache lookup failed (falling through): %s", exc)
        else:
            _emit_metric(model, method, hit=False, similarity=None, latency_ms=0,
                         skipped=True, skip_reason=skip_reason)

        # --- Live API call ---
        result_text = await self._live_call(model=model, messages=messages, **api_kwargs)

        # Store in cache (best-effort, non-blocking)
        if not should_skip:
            try:
                self._get_cache().store(model, method, prompt, result_text)
            except Exception as exc:  # noqa: BLE001
                logger.debug("cache store failed (non-fatal): %s", exc)

        return result_text

    async def _live_call(
        self,
        *,
        model: str,
        messages: List[Dict[str, Any]],
        **api_kwargs: Any,
    ) -> str:
        """Make the actual Anthropic API call and extract text."""
        from anthropic import AsyncAnthropic

        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if not api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")

        client = AsyncAnthropic(api_key=api_key)
        message = await client.messages.create(
            model=model,
            messages=messages,
            **api_kwargs,
        )
        # Safe text extraction (adaptive thinking puts ThinkingBlock first)
        for block in getattr(message, "content", None) or []:
            text = getattr(block, "text", None)
            if isinstance(text, str):
                return text
        return ""

    def hit_rate(self) -> float:
        """Return cache hit rate from metrics file (last 1000 entries)."""
        try:
            lines = _METRICS_FILE.read_text().splitlines()[-1000:]
            records = [json.loads(l) for l in lines if l.strip()]
            # Only non-skipped lookups count
            eligible = [r for r in records if not r.get("skipped")]
            if not eligible:
                return 0.0
            hits = sum(1 for r in eligible if r.get("hit"))
            return hits / len(eligible)
        except (OSError, json.JSONDecodeError):
            return 0.0


# ---------------------------------------------------------------------------
# Module-level singleton (shared across call sites in the same process)
# ---------------------------------------------------------------------------

_wrapper: Optional[ClaudeCacheWrapper] = None


def get_wrapper(
    db_path: Path | None = None,
    threshold: float = 0.95,
    ttl_days: int = 30,
    warmup_days: int = 7,
) -> ClaudeCacheWrapper:
    """Return the module-level wrapper singleton, creating it if needed."""
    global _wrapper
    if _wrapper is None:
        _wrapper = ClaudeCacheWrapper(
            db_path=db_path,
            threshold=threshold,
            ttl_days=ttl_days,
            warmup_days=warmup_days,
        )
    return _wrapper
