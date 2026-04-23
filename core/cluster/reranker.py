"""
BR3 Cluster — Jimmy Reranker
Loads BAAI/bge-reranker-v2-m3 on CPU for cross-encoder reranking.

Deployed to Jimmy (10.0.1.106). Registered as sibling routes under the
br3-semantic FastAPI service on port 8100.

Usage (from node_semantic.py or api/routes/retrieve.py):
    from core.cluster.reranker import rerank, ScoredResult

Feature-gated: BR3_AUTO_CONTEXT=on must be set (set in scripts/service-env.sh);
otherwise reranker is a no-op.

Metrics emitted to ~/.buildrunner/reranker-metrics.jsonl (lockwood-metrics):
    {"ts": "...", "event": "rerank", "top_k": 5, "candidates": 20, "latency_ms": 42}
"""

import json
import os
import logging
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Feature gate — enabled when BR3_AUTO_CONTEXT=on (set in scripts/service-env.sh)
AUTO_CONTEXT_ENABLED = os.environ.get("BR3_AUTO_CONTEXT", "off").lower() == "on"

# Metrics output file (lockwood-metrics compatible)
_METRICS_FILE = Path.home() / ".buildrunner" / "reranker-metrics.jsonl"


def _emit_metric(event: str, **fields: object) -> None:
    """Append a single JSON line to the reranker metrics file. Never raises."""
    try:
        record = {"ts": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()), "event": event}
        record.update(fields)
        _METRICS_FILE.parent.mkdir(parents=True, exist_ok=True)
        with _METRICS_FILE.open("a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except Exception as exc:  # noqa: BLE001
        logger.debug("_emit_metric: failed to write metrics: %s", exc)

# Model config
RERANKER_MODEL = os.environ.get(
    "RERANKER_MODEL", "BAAI/bge-reranker-v2-m3"
)

# Lazy-loaded singleton
_reranker = None
_reranker_lock = None


@dataclass
class ScoredResult:
    """A candidate snippet with a relevance score from the cross-encoder."""
    text: str
    score: float
    source: str = ""
    source_url: str = ""
    start_line: int = 0
    end_line: int = 0
    metadata: Optional[dict] = None


def _get_reranker():
    """Lazy-load the bge-reranker-v2-m3 cross-encoder on CPU."""
    global _reranker, _reranker_lock
    import threading
    if _reranker_lock is None:
        _reranker_lock = threading.Lock()
    with _reranker_lock:
        if _reranker is None:
            try:
                from sentence_transformers import CrossEncoder
                logger.info(f"Loading reranker model: {RERANKER_MODEL}")
                _reranker = CrossEncoder(
                    RERANKER_MODEL,
                    max_length=512,
                    device="cpu",
                )
                logger.info("Reranker loaded successfully")
            except ImportError as e:
                logger.error(f"sentence-transformers not available: {e}")
                raise
            except Exception as e:
                logger.error(f"Failed to load reranker: {e}")
                raise
    return _reranker


def rerank(
    query: str,
    candidates: list[ScoredResult],
    top_k: int = 5,
) -> list[ScoredResult]:
    """
    Cross-encoder rerank: score (query, candidate_text) pairs and return top_k.

    Args:
        query: The search query string.
        candidates: List of ScoredResult from Stage 1 vector search.
        top_k: Number of results to return after reranking.

    Returns:
        List of ScoredResult sorted by cross-encoder score descending, length <= top_k.

    Behavior when flag is OFF:
        Returns candidates[:top_k] unchanged (no reranking). Zero behavior change.
    """
    if not candidates:
        return []

    if not AUTO_CONTEXT_ENABLED:
        # Flag off — passthrough, no model load, no change
        return candidates[:top_k]

    t_start = time.monotonic()
    try:
        model = _get_reranker()
        pairs = [(query, c.text[:512]) for c in candidates]
        scores = model.predict(pairs, show_progress_bar=False)

        # Attach cross-encoder scores
        scored = []
        for cand, score in zip(candidates, scores):
            updated = ScoredResult(
                text=cand.text,
                score=float(score),
                source=cand.source,
                source_url=cand.source_url,
                start_line=cand.start_line,
                end_line=cand.end_line,
                metadata=cand.metadata,
            )
            scored.append(updated)

        scored.sort(key=lambda x: x.score, reverse=True)
        result = scored[:top_k]

        latency_ms = round((time.monotonic() - t_start) * 1000, 1)
        _emit_metric(
            "rerank",
            top_k=top_k,
            candidates=len(candidates),
            returned=len(result),
            latency_ms=latency_ms,
            model=RERANKER_MODEL,
        )
        return result

    except Exception as e:
        latency_ms = round((time.monotonic() - t_start) * 1000, 1)
        _emit_metric("rerank_error", error=str(e), latency_ms=latency_ms)
        logger.warning(f"Reranker failed, returning passthrough results: {e}")
        # Fail gracefully — return Stage 1 results by original score
        return sorted(candidates, key=lambda x: x.score, reverse=True)[:top_k]


def reranker_health() -> dict:
    """Health check for the reranker endpoint."""
    if not AUTO_CONTEXT_ENABLED:
        return {"status": "disabled", "model": RERANKER_MODEL, "flag": "BR3_AUTO_CONTEXT=off"}
    try:
        model = _get_reranker()
        # Quick smoke test
        score = model.predict([("health check", "health check test")])
        return {
            "status": "ok",
            "model": RERANKER_MODEL,
            "device": "cpu",
            "score_sample": float(score[0]) if hasattr(score, '__iter__') else float(score),
        }
    except Exception as e:
        return {"status": "error", "model": RERANKER_MODEL, "error": str(e)}
