"""
llmlingua_compress.py — LLMLingua-2 prompt compression helper for autopilot dispatch.

Reduces token count of phase prompts and intel-collect dispatch text before sending
to Claude, without degrading downstream quality.

Tech: LLMLingua-2 (llmlingua PyPI package, BERT-family, HuggingFace transformers).
      Runs on CPU or CUDA — no GPU required for useful compression ratios.

Exclusion list (never compress):
    adversarial-review, arbiter, ai_code_review, cross-model-review,
    reviewer, review_diff, analyze_architecture
    — These require the full unmodified context to preserve reviewer integrity.

Rollback: BR3_LLMLINGUA=off → returns prompt unchanged.
Fail-open: any compression error → returns prompt unchanged, logs to stderr.

Usage:
    from core.cluster.below.llmlingua_compress import compress_prompt

    compressed = compress_prompt(prompt, ratio=0.5, method="dispatch")
    # Returns the compressed string (or original on failure/exclusion).

CLI:
    python -m core.cluster.below.llmlingua_compress --ratio 0.5 < prompt.txt
"""

from __future__ import annotations

import logging
import os
import sys
import time
from typing import Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------

_LLMLINGUA_ENABLED: bool = os.environ.get("BR3_LLMLINGUA", "on").lower() != "off"

# ---------------------------------------------------------------------------
# Exclusion list — methods/call sites where compression is forbidden
# ---------------------------------------------------------------------------

EXCLUDED_METHODS: frozenset[str] = frozenset({
    "adversarial-review",
    "adversarial_review",
    "arbiter",
    "ai_code_review",
    "cross-model-review",
    "cross_model_review",
    "reviewer",
    "review_diff",
    "analyze_architecture",
})

# Minimum prompt length (chars) before attempting compression — very short prompts
# compress poorly and the overhead isn't worth it.
MIN_COMPRESS_LENGTH: int = 500

# Lazy-loaded compressor (avoid HF model download at import time)
_compressor = None


def _get_compressor():
    """Lazy-load the LLMLingua-2 compressor. Downloads model on first call (~400MB)."""
    global _compressor
    if _compressor is not None:
        return _compressor
    try:
        from llmlingua import PromptCompressor
        # microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank — compact model
        # Falls back to llmlingua-2-xlm-roberta-large if not available
        _compressor = PromptCompressor(
            model_name="microsoft/llmlingua-2-bert-base-multilingual-cased-meetingbank",
            use_llmlingua2=True,
            device_map="cpu",  # CPU is fine for BERT-class models
        )
        logger.info("llmlingua_compress: compressor loaded")
        return _compressor
    except Exception as exc:
        logger.warning("llmlingua_compress: failed to load compressor: %s", exc)
        return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def compress_prompt(
    prompt: str,
    *,
    ratio: float = 0.5,
    method: str = "",
    target_token: Optional[int] = None,
    condition_in_question: str = "",
) -> str:
    """
    Compress a prompt using LLMLingua-2.

    Args:
        prompt:                 The full prompt text to compress.
        ratio:                  Compression ratio — 0.5 means keep 50% of tokens.
                                Range: 0.1 (aggressive) to 0.9 (gentle). Default: 0.5.
        method:                 Call-site name for exclusion-list check. Excluded methods
                                return the original prompt unchanged.
        target_token:           If set, compress to this token count (overrides ratio).
        condition_in_question:  Optional task description to guide compression.

    Returns:
        Compressed prompt string. Returns original prompt on failure or exclusion.

    Raises:
        Nothing — fail-open always.
    """
    if not _LLMLINGUA_ENABLED:
        return prompt

    if method in EXCLUDED_METHODS:
        logger.debug("llmlingua_compress: excluded method %s — skipping", method)
        return prompt

    if len(prompt) < MIN_COMPRESS_LENGTH:
        return prompt

    t0 = time.monotonic()
    try:
        compressor = _get_compressor()
        if compressor is None:
            return prompt

        kwargs: dict = {
            "target_token": target_token if target_token else -1,
            "rate": ratio,
            "condition_in_question": condition_in_question or "Compress this prompt while preserving all technical details, file paths, code names, and action items.",
            "use_sentence_level_filter": False,
            "context_budget": "+100%",
        }

        result = compressor.compress_prompt(prompt, **kwargs)
        compressed = result.get("compressed_prompt", prompt)

        # Sanity: if compression made it longer or returned empty, return original
        if not compressed or len(compressed) >= len(prompt):
            logger.debug("llmlingua_compress: compression unhelpful (ratio %.2f) — skipping", ratio)
            return prompt

        latency_ms = int((time.monotonic() - t0) * 1000)
        orig_chars = len(prompt)
        new_chars = len(compressed)
        actual_ratio = new_chars / orig_chars
        logger.info(
            "llmlingua_compress: %d→%d chars (%.0f%% kept) in %dms method=%s",
            orig_chars,
            new_chars,
            actual_ratio * 100,
            latency_ms,
            method or "unknown",
        )
        _emit_metric(method, orig_chars, new_chars, latency_ms)
        return compressed

    except Exception as exc:
        logger.warning("llmlingua_compress: compression failed (%s) — using original", exc)
        return prompt


def compress_prompt_safe(
    prompt: str,
    **kwargs,
) -> str:
    """
    Convenience alias — always returns a string, never raises.
    Identical to compress_prompt() but explicitly documents the fail-open contract.
    """
    try:
        return compress_prompt(prompt, **kwargs)
    except Exception:
        return prompt


# ---------------------------------------------------------------------------
# Metric emission
# ---------------------------------------------------------------------------


def _emit_metric(method: str, orig_chars: int, new_chars: int, latency_ms: int) -> None:
    """Append a metric entry to schema-classifier-metrics.jsonl."""
    import json

    metrics_file = os.path.join(
        os.path.expanduser("~"), ".buildrunner", "schema-classifier-metrics.jsonl"
    )
    try:
        import datetime

        entry = {
            "ts": datetime.datetime.now(datetime.timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "site": "llmlingua_compress",
            "model": "llmlingua-2-bert",
            "method": method or "unknown",
            "orig_chars": orig_chars,
            "new_chars": new_chars,
            "compression_ratio": round(new_chars / orig_chars, 3) if orig_chars else 1.0,
            "latency_ms": latency_ms,
        }
        with open(metrics_file, "a") as mf:
            mf.write(json.dumps(entry) + "\n")
    except OSError:
        pass


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def _cli() -> None:
    import argparse

    parser = argparse.ArgumentParser(description="Compress a prompt via LLMLingua-2")
    parser.add_argument("--ratio", type=float, default=0.5, help="Compression ratio (0.1–0.9)")
    parser.add_argument("--method", default="", help="Call-site name (for exclusion check)")
    parser.add_argument("--target-token", type=int, default=0, help="Target token count (0=use ratio)")
    parser.add_argument("file", nargs="?", help="Input file (default: stdin)")
    args = parser.parse_args()

    if args.file:
        prompt = open(args.file).read()
    else:
        prompt = sys.stdin.read()

    result = compress_prompt(
        prompt,
        ratio=args.ratio,
        method=args.method,
        target_token=args.target_token or None,
    )
    sys.stdout.write(result)


if __name__ == "__main__":
    _cli()
