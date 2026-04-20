"""summarizer.py — Pre-summary helper for large inputs before paid-model escalation.

Routes through RuntimeRegistry.execute() → OllamaRuntime (qwen3:8b on Below).

CONTRACT:
  - Returns {summary, excerpts, truncated: bool}.
  - truncated=True means summarization was skipped (Below offline / error) and
    the original content is returned verbatim as summary.
  - NEVER produces final-form code, final diagnoses, or authoritative reviews.
    All output is tagged draft=True by RuntimeRegistry.
  - Below offline → silent fallback; returns original with truncated=True.

IMPORTANT: Do NOT call ollama/curl/requests.post directly.
RuntimeRegistry.execute() is the ONLY dispatch path for local model calls.
"""

from __future__ import annotations

import asyncio
import logging
import re
import uuid
from typing import TYPE_CHECKING, Any

# TYPE_CHECKING block is intentionally minimal — runtime imports are deferred
# inside _call_registry() to break the circular-import chain:
#   summarizer → runtime_registry → ollama_runtime → cross_model_review → summarizer
if TYPE_CHECKING:
    from core.runtime.types import RuntimeTask  # noqa: F401

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Summarization model — qwen3:8b for classification/extraction tasks per spec.
# ---------------------------------------------------------------------------
_SUMMARIZER_MODEL = "qwen3:8b"
_MAX_OUTPUT_BYTES = 5 * 1024  # 5 KB target ceiling on summarizer output

_DIFF_PROMPT_TEMPLATE = """\
You are a pre-summary assistant. Your output will be read by a code reviewer, NOT shipped as a final result.

Summarize the following diff for a code reviewer. Your summary MUST:
1. List every file changed (added/modified/deleted) with a 1-line description.
2. Extract ALL lines that match critical-change markers: lines containing
   "CRITICAL", "BREAKING", "security", "auth", "RLS", "migration", "schema",
   "password", "token", "secret", or function-signature additions/deletions.
3. Be concise — the total output MUST fit within 5KB.
4. End with a line: "EXCERPT_COUNT: N" where N is the count of critical lines.

DO NOT produce final-form code. DO NOT diagnose bugs. DO NOT recommend fixes.
This is a pre-summary only.

--- DIFF START ---
{content}
--- DIFF END ---
"""

_LOGS_PROMPT_TEMPLATE = """\
You are a pre-summary assistant. Your output will be read by an analyst, NOT shipped as a final result.

Summarize the following log lines for an analyst. Your summary MUST:
1. Count total lines and unique log levels (ERROR/WARN/INFO/DEBUG).
2. List the 10 most frequent log messages (template, not full text).
3. Extract ALL error and warning lines verbatim (up to 50 lines).
4. Be concise — the total output MUST fit within 5KB.

DO NOT diagnose root causes. DO NOT recommend fixes.
This is a pre-summary only.

--- LOGS START ---
{content}
--- LOGS END ---
"""

_SPEC_PROMPT_TEMPLATE = """\
You are a pre-summary assistant. Your output will be read by a builder, NOT shipped as a final result.

Summarize the following spec/markdown for a builder. Your summary MUST:
1. List all section headings.
2. Extract every deliverable, constraint, and "MUST"/"NEVER"/"BLOCKING" sentence verbatim.
3. Be concise — the total output MUST fit within 5KB.

DO NOT produce a plan. DO NOT produce code. DO NOT diagnose anything.
This is a pre-summary only.

--- SPEC START ---
{content}
--- SPEC END ---
"""


def _extract_excerpts(text: str) -> list[str]:
    """Pull critical-change lines from the text (diff context)."""
    pattern = re.compile(
        r"(CRITICAL|BREAKING|security|auth|RLS|migration|schema|password|token|secret)",
        re.IGNORECASE,
    )
    return [line for line in text.splitlines() if pattern.search(line)]


def _make_offline_result(content: str) -> dict[str, Any]:
    """Return original content as summary when Below is offline."""
    return {"summary": content, "excerpts": _extract_excerpts(content), "truncated": True}


def _call_registry(prompt: str) -> str | None:
    """Dispatch summarization via RuntimeRegistry → OllamaRuntime.

    Returns the model output string, or None on any error.
    Imports are deferred inside the function to break the circular-import
    between summarizer → runtime_registry → ollama_runtime → cross_model_review.
    """
    try:
        # pylint: disable=import-outside-toplevel
        from core.runtime.runtime_registry import (  # noqa: PLC0415
            create_runtime_registry,
        )
        from core.runtime.types import RuntimeTask  # noqa: PLC0415

        config = {"backends": {"ollama": {"model": _SUMMARIZER_MODEL}}}
        registry = create_runtime_registry(config)
        registration = registry.get("ollama")

        task = RuntimeTask(
            task_id=f"summarize-{uuid.uuid4().hex[:8]}",
            task_type="summarize",
            diff_text=prompt,
            spec_text="",
            project_root="",
            commit_sha="",
            metadata={"draft": True, "purpose": "pre-summary"},
        )

        loop = asyncio.new_event_loop()
        try:
            result = loop.run_until_complete(registration.adapter.run_review(task))
        finally:
            loop.close()

    except Exception as exc:  # noqa: BLE001
        logger.warning("summarizer: registry call failed: %s", exc)
        return None
    else:
        if result.status == "completed" and result.raw_output:
            return result.raw_output
        logger.warning(
            "summarizer: OllamaRuntime returned status=%s error=%s",
            result.status,
            result.error_message,
        )
        return None


def _truncate_to_limit(output: str) -> str:
    """Hard-cap the output to _MAX_OUTPUT_BYTES, appending a notice if truncated."""
    encoded = output.encode("utf-8")
    if len(encoded) <= _MAX_OUTPUT_BYTES:
        return output
    truncated = encoded[:_MAX_OUTPUT_BYTES].decode("utf-8", errors="ignore")
    return truncated + "\n[SUMMARY TRUNCATED AT 5KB]"


def summarize_diff(diff: str) -> dict[str, Any]:
    """Summarize a diff via qwen3:8b. Returns {summary, excerpts, truncated: bool}.

    If Below is offline or the call fails, returns original diff with truncated=True.
    Preserves critical-change markers regardless of summarization path.
    Never raises — all failures are silent offline fallbacks.
    """
    if not diff:
        return {"summary": "", "excerpts": [], "truncated": False}

    excerpts = _extract_excerpts(diff)
    try:
        prompt = _DIFF_PROMPT_TEMPLATE.format(content=diff)
        output = _call_registry(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("summarize_diff: unexpected error, using offline fallback: %s", exc)
        output = None

    if output is None:
        return _make_offline_result(diff)

    return {
        "summary": _truncate_to_limit(output),
        "excerpts": excerpts,
        "truncated": False,
    }


def summarize_logs(lines: list[str]) -> dict[str, Any]:
    """Summarize log lines via qwen3:8b. Returns {summary, excerpts, truncated: bool}.

    If Below is offline or the call fails, returns original content with truncated=True.
    Never raises — all failures are silent offline fallbacks.
    """
    if not lines:
        return {"summary": "", "excerpts": [], "truncated": False}

    content = "\n".join(lines)
    error_lines = [ln for ln in lines if re.search(r"\b(ERROR|WARN|CRITICAL)\b", ln, re.IGNORECASE)]

    try:
        prompt = _LOGS_PROMPT_TEMPLATE.format(content=content)
        output = _call_registry(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("summarize_logs: unexpected error, using offline fallback: %s", exc)
        output = None

    if output is None:
        return {"summary": content, "excerpts": error_lines, "truncated": True}

    return {
        "summary": _truncate_to_limit(output),
        "excerpts": error_lines,
        "truncated": False,
    }


def summarize_spec(md: str) -> dict[str, Any]:
    """Summarize a spec/markdown document via qwen3:8b.

    Returns {summary, excerpts, truncated: bool}.
    excerpts = all MUST/NEVER/BLOCKING sentences.
    If Below is offline, returns original with truncated=True.
    Never raises — all failures are silent offline fallbacks.
    """
    if not md:
        return {"summary": "", "excerpts": [], "truncated": False}

    constraint_pattern = re.compile(r"(MUST|NEVER|BLOCKING)", re.IGNORECASE)
    excerpts = [line.strip() for line in md.splitlines() if constraint_pattern.search(line)]

    try:
        prompt = _SPEC_PROMPT_TEMPLATE.format(content=md)
        output = _call_registry(prompt)
    except Exception as exc:  # noqa: BLE001
        logger.warning("summarize_spec: unexpected error, using offline fallback: %s", exc)
        output = None

    if output is None:
        return {"summary": md, "excerpts": excerpts, "truncated": True}

    return {
        "summary": _truncate_to_limit(output),
        "excerpts": excerpts,
        "truncated": False,
    }
