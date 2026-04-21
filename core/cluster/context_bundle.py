"""context_bundle.py — Per-model unified context bundle assembler (Phase 12).

Assembles {logs, memory, intel, decisions, research} from Jimmy sources, Lockwood DBs,
and the research library into a sized bundle ready for injection.

Feature-gated: BR3_AUTO_CONTEXT=on must be set. Default OFF until Phase 13.

IMPORTANT: Read-only surface. No mutation of any source through this module.
IMPORTANT: Two-layer [private] filter — filter runs here as defense-in-depth AFTER
           sync-cluster-context.sh already stripped [private] lines at the mirror.
           Filtering ONLY here is insufficient (raw decisions.log would still be readable
           on Otis/Below outside the bundle path).
IMPORTANT: Token budgets enforced via count-tokens.sh (tokenizer-true). No byte fallback.
           If count-tokens.sh exits 2 (tokenizer missing), bundle is REFUSED — never assembled.
"""

from __future__ import annotations

import json
import logging
import os
import re
import sqlite3
import subprocess
import tempfile
from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any, Optional

logger = logging.getLogger(__name__)

HOME = Path.home()

# Feature gate — default OFF until Phase 13
_MULTI_MODEL_CONTEXT_ENV = "BR3_AUTO_CONTEXT"


def _multi_model_context_enabled() -> bool:
    """Return True when BR3_AUTO_CONTEXT=on (case-insensitive)."""
    return os.environ.get(_MULTI_MODEL_CONTEXT_ENV, "").strip().lower() == "on"


# Paths resolved relative to home
_DECISIONS_LOG = HOME / ".buildrunner" / "decisions.log"
_DECISIONS_PUBLIC_LOG = HOME / ".buildrunner" / "decisions.public.log"
_BROWSER_LOG = HOME / ".buildrunner" / "browser.log"
_SUPABASE_LOG = HOME / ".buildrunner" / "supabase.log"
_DEVICE_LOG = HOME / ".buildrunner" / "device.log"
_QUERY_LOG = HOME / ".buildrunner" / "query.log"
_MEMORY_DB = HOME / ".lockwood" / "memory.db"
_INTEL_DB = HOME / ".lockwood" / "intel.db"
_RESEARCH_LIBRARY = HOME / "Projects" / "research-library"

# Jimmy paths (used when local DBs not available)
_JIMMY_MEMORY_DB = Path("/srv/jimmy/memory/memory.db")
_JIMMY_INTEL_DB = Path("/srv/jimmy/memory/intel.db")
_JIMMY_RESEARCH = Path("/srv/jimmy/research-library")

# count-tokens.sh path (Phase 10 deliverable)
_COUNT_TOKENS_SH = HOME / ".buildrunner" / "scripts" / "count-tokens.sh"

# Exclusion patterns — NEVER include files matching these in any bundle
_EXCLUSION_PATTERNS = [
    "secrets.env",
    "*.token",
    "*.key",
    "*.pem",
    "*.cert",
    "*.p12",
    "auth.json",
    "credentials.json",
    "service-account*.json",
    "*.secret",
    ".env",
    ".env.*",
    "active-token.env",
    "token-refresh*.log",
]

# [private] filter lives in core.cluster.private_filter — shared across all egress paths.
# Re-exported below for back-compat with existing imports.
from core.cluster.private_filter import filter_private_lines, _PRIVATE_PATTERN  # noqa: E402, F401

# Max log lines per file for bundle candidates
_MAX_LOG_LINES = 200
# Max decisions lines in bundle
_MAX_DECISIONS_LINES = 100
# Max research docs per bundle
_MAX_RESEARCH_DOCS = 5


@dataclass
class BundleSection:
    """A single typed section in a context bundle."""

    source_type: str  # logs | decisions | memory | intel | research
    content: str
    source_path: str = ""
    item_count: int = 0
    tokens: int = 0


@dataclass
class ContextBundle:
    """Assembled context bundle for one model.

    Fields:
        model       — target model (claude | codex | ollama)
        sections    — list of BundleSection, one per source type
        token_total — sum of tokens across all sections (tokenizer-true)
        budget      — {limit, used, tokenizer} for the response
        assembled_at — UTC ISO timestamp
    """

    model: str
    sections: list[BundleSection] = field(default_factory=list)
    token_total: int = 0
    budget: dict[str, Any] = field(default_factory=dict)
    assembled_at: str = ""

    def to_dict(self) -> dict[str, Any]:
        return {
            "model": self.model,
            "sections": [
                {
                    "source_type": s.source_type,
                    "content": s.content,
                    "source_path": s.source_path,
                    "item_count": s.item_count,
                    "tokens": s.tokens,
                }
                for s in self.sections
            ],
            "token_total": self.token_total,
            "budget": self.budget,
            "assembled_at": self.assembled_at,
        }

    def to_prompt_block(self) -> str:
        """Render as <cluster-context> prompt block for injection."""
        parts = ["<cluster-context>"]
        for sec in self.sections:
            if sec.content.strip():
                parts.append(f"## {sec.source_type.upper()}")
                parts.append(sec.content.strip())
        parts.append("</cluster-context>")
        return "\n\n".join(parts)


# ---------------------------------------------------------------------------
# Token counting — via count-tokens.sh (exit-2 = fail-closed)
# ---------------------------------------------------------------------------


def count_tokens(text: str, model: str) -> int:
    """Return tokenizer-true token count for text.

    Calls count-tokens.sh --model <model> via subprocess.
    Raises RuntimeError on exit 2 (tokenizer unavailable) — NO byte fallback.
    Maps 'ollama' → 'ollama', everything else → 'claude' or 'codex' per spec.

    Args:
        text:  Content to count.
        model: One of 'claude', 'codex', 'ollama'.

    Raises:
        RuntimeError: tokenizer unavailable (exit 2) — bundle must be refused.
        ValueError:   bad model argument.
    """
    if not _COUNT_TOKENS_SH.exists():
        raise RuntimeError(
            f"count-tokens.sh not found at {_COUNT_TOKENS_SH}. "
            "Cannot enforce token budgets. Bundle refused."
        )

    valid_models = ("claude", "codex", "ollama")
    if model not in valid_models:
        raise ValueError(f"Unknown model '{model}'. Must be one of: {valid_models}")

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".txt", delete=False, encoding="utf-8"
    ) as tf:
        tf.write(text)
        tmp_path = tf.name

    try:
        result = subprocess.run(
            [str(_COUNT_TOKENS_SH), "--model", model, tmp_path],
            capture_output=True,
            text=True,
            timeout=30,
        )
    finally:
        Path(tmp_path).unlink(missing_ok=True)

    if result.returncode == 2:
        raise RuntimeError(
            f"count-tokens.sh exited 2 (tokenizer unavailable for model={model}). "
            "Bundle REFUSED — no byte-count fallback permitted."
        )
    if result.returncode != 0:
        raise RuntimeError(
            f"count-tokens.sh failed (exit {result.returncode}): {result.stderr.strip()}"
        )

    try:
        return int(result.stdout.strip())
    except ValueError as exc:
        raise RuntimeError(
            f"count-tokens.sh returned non-integer: {result.stdout!r}"
        ) from exc


# ---------------------------------------------------------------------------
# Source extractors
# ---------------------------------------------------------------------------


def _extract_logs() -> BundleSection:
    """Read tail of each .buildrunner/*.log file, combine into one section."""
    log_files = [_BROWSER_LOG, _SUPABASE_LOG, _DEVICE_LOG, _QUERY_LOG]
    parts: list[str] = []
    total_lines = 0

    for log_path in log_files:
        if not log_path.exists():
            continue
        try:
            lines = log_path.read_text(encoding="utf-8", errors="replace").splitlines()
            tail = lines[-_MAX_LOG_LINES:]
            if tail:
                parts.append(f"### {log_path.name}")
                parts.append("\n".join(tail))
                total_lines += len(tail)
        except OSError as exc:
            logger.debug("_extract_logs: cannot read %s: %s", log_path, exc)

    content = "\n\n".join(parts)
    return BundleSection(
        source_type="logs",
        content=content,
        source_path=str(HOME / ".buildrunner"),
        item_count=total_lines,
    )


def _extract_decisions() -> BundleSection:
    """Read decisions.public.log (filtered). Re-filter here as defense-in-depth."""
    # Prefer pre-filtered public log; fall back to filtering raw log if public
    # version doesn't exist yet (only on Muddy, where raw log lives).
    if _DECISIONS_PUBLIC_LOG.exists():
        raw = _DECISIONS_PUBLIC_LOG.read_text(encoding="utf-8", errors="replace")
    elif _DECISIONS_LOG.exists():
        raw = _DECISIONS_LOG.read_text(encoding="utf-8", errors="replace")
    else:
        return BundleSection(source_type="decisions", content="", item_count=0)

    # Defense-in-depth: strip [private] lines even if public log was already filtered
    filtered = filter_private_lines(raw)
    lines = [ln for ln in filtered.splitlines() if ln.strip()]
    tail = lines[-_MAX_DECISIONS_LINES:]
    content = "\n".join(tail)

    return BundleSection(
        source_type="decisions",
        content=content,
        source_path=str(_DECISIONS_PUBLIC_LOG),
        item_count=len(tail),
    )


def _extract_memory() -> BundleSection:
    """Read recent session memory entries from memory.db."""
    for db_path in (_MEMORY_DB, _JIMMY_MEMORY_DB):
        if db_path.exists():
            break
    else:
        return BundleSection(source_type="memory", content="", item_count=0)

    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        # Try common schema shapes; graceful degrade if columns differ
        for query in (
            "SELECT content, created_at FROM memories ORDER BY created_at DESC LIMIT 20",
            "SELECT content, ts FROM memories ORDER BY ts DESC LIMIT 20",
            "SELECT content FROM memories ORDER BY rowid DESC LIMIT 20",
        ):
            try:
                rows = cur.execute(query).fetchall()
                break
            except sqlite3.OperationalError:
                continue
        else:
            conn.close()
            return BundleSection(source_type="memory", content="", item_count=0)

        conn.close()
        items = [dict(r) for r in rows]
        content = "\n".join(
            f"- {item.get('content', item.get('text', str(item)))}" for item in items
        )
        return BundleSection(
            source_type="memory",
            content=content,
            source_path=str(db_path),
            item_count=len(items),
        )
    except (sqlite3.Error, OSError) as exc:
        logger.debug("_extract_memory: DB error: %s", exc)
        return BundleSection(source_type="memory", content="", item_count=0)


def _extract_intel() -> BundleSection:
    """Read top-scored intel items from intel.db."""
    for db_path in (_INTEL_DB, _JIMMY_INTEL_DB):
        if db_path.exists():
            break
    else:
        return BundleSection(source_type="intel", content="", item_count=0)

    try:
        conn = sqlite3.connect(str(db_path), timeout=5)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()

        for query in (
            "SELECT content, score, created_at FROM intel ORDER BY score DESC LIMIT 20",
            "SELECT content, score FROM intel ORDER BY score DESC LIMIT 20",
            "SELECT content FROM intel ORDER BY rowid DESC LIMIT 20",
        ):
            try:
                rows = cur.execute(query).fetchall()
                break
            except sqlite3.OperationalError:
                continue
        else:
            conn.close()
            return BundleSection(source_type="intel", content="", item_count=0)

        conn.close()
        items = [dict(r) for r in rows]
        content = "\n".join(
            f"- [score={item.get('score', '?')}] {item.get('content', str(item))}"
            for item in items
        )
        return BundleSection(
            source_type="intel",
            content=content,
            source_path=str(db_path),
            item_count=len(items),
        )
    except (sqlite3.Error, OSError) as exc:
        logger.debug("_extract_intel: DB error: %s", exc)
        return BundleSection(source_type="intel", content="", item_count=0)


def _extract_research(
    max_docs: int = _MAX_RESEARCH_DOCS,
    ttl_days: int = 30,
    query: str = "",
) -> BundleSection:
    """Select research library docs for the bundle.

    Phase 7: prefer reranker-driven relevance over mtime recency when a
    ``query`` is provided. Falls back to mtime ordering when no query is
    available or the reranker is unreachable — never blocks assembly.
    """
    for research_root in (_RESEARCH_LIBRARY, _JIMMY_RESEARCH):
        if research_root.exists():
            break
    else:
        return BundleSection(source_type="research", content="", item_count=0)

    # Gather the full candidate pool — no mtime cutoff when reranker is in play.
    candidates: list[tuple[datetime, Path]] = []
    for ext in ("*.md", "*.txt", "*.json"):
        for doc in research_root.rglob(ext):
            if _is_excluded(doc):
                continue
            try:
                mtime = datetime.fromtimestamp(doc.stat().st_mtime, tz=timezone.utc)
                candidates.append((mtime, doc))
            except OSError:
                continue

    docs: list[tuple[datetime, Path]] = []
    if query:
        docs = _rerank_research_candidates(query, candidates, max_docs)

    if not docs:
        # Fallback: mtime-recency within TTL, same behavior as pre-Phase-7.
        cutoff = datetime.now(tz=timezone.utc) - timedelta(days=ttl_days)
        docs = [(mt, p) for mt, p in candidates if mt >= cutoff]
        docs.sort(key=lambda t: t[0], reverse=True)
        docs = docs[:max_docs]

    parts: list[str] = []
    for _mtime, doc in docs:
        try:
            text = doc.read_text(encoding="utf-8", errors="replace")
            # Defense-in-depth: scrub [private] lines before bundle append.
            text = filter_private_lines(text)
            # Truncate long docs
            if len(text) > 2000:
                text = text[:2000] + "\n...[truncated]"
            parts.append(f"### {doc.name}\n{text}")
        except OSError:
            continue

    content = "\n\n".join(parts)
    return BundleSection(
        source_type="research",
        content=content,
        source_path=str(research_root),
        item_count=len(docs),
    )


def _is_excluded(path: Path) -> bool:
    """Return True if path matches any exclusion pattern."""
    import fnmatch
    name = path.name
    for pattern in _EXCLUSION_PATTERNS:
        if fnmatch.fnmatch(name, pattern):
            return True
    return False


def _rerank_research_candidates(
    query: str,
    candidates: list[tuple[datetime, Path]],
    top_k: int,
) -> list[tuple[datetime, Path]]:
    """Rerank research docs by relevance to ``query`` using the bge cross-encoder.

    Reads a small preview from each doc (first 1200 chars) to keep the
    rerank payload bounded, then asks the Phase-10 reranker for the best
    ``top_k``. On any failure, returns [] so callers fall back to mtime.
    """
    if not candidates or top_k <= 0:
        return []
    try:
        from core.cluster.reranker import rerank, ScoredResult
    except Exception as exc:
        logger.debug("_rerank_research_candidates: reranker unavailable: %s", exc)
        return []

    # Bound the pool before reranking — reading every file is wasteful.
    pool = sorted(candidates, key=lambda t: t[0], reverse=True)[: max(top_k * 4, 20)]
    scored: list[ScoredResult] = []
    index: dict[str, tuple[datetime, Path]] = {}
    for mtime, path in pool:
        try:
            preview = path.read_text(encoding="utf-8", errors="replace")[:1200]
        except OSError:
            continue
        key = str(path)
        index[key] = (mtime, path)
        scored.append(ScoredResult(
            text=preview,
            score=0.0,
            source="research",
            source_url=key,
        ))
    if not scored:
        return []
    try:
        reranked = rerank(query, scored, top_k=top_k)
    except Exception as exc:
        logger.debug("_rerank_research_candidates: rerank failed: %s", exc)
        return []
    out: list[tuple[datetime, Path]] = []
    for r in reranked:
        entry = index.get(r.source_url)
        if entry:
            out.append(entry)
    return out


# ---------------------------------------------------------------------------
# Bundle assembler
# ---------------------------------------------------------------------------


class ContextBundleAssembler:
    """Assembles per-model context bundles.

    Usage::

        assembler = ContextBundleAssembler()
        bundle = assembler.assemble(model="codex", token_budget=48000)
    """

    def assemble(
        self,
        model: str,
        token_budget: int,
        query: str = "",
        phase: str = "",
        skill: str = "",
    ) -> ContextBundle:
        """Assemble a context bundle for the given model.

        Returns a ContextBundle with all five source types populated (where available).
        Token budget is enforced via count-tokens.sh. If tokenizer is unavailable,
        raises RuntimeError (fail-closed — never falls back to byte counting).

        Args:
            model:        Target model — 'claude', 'codex', or 'ollama'.
            token_budget: Hard token limit for the assembled bundle output.
            query:        Optional query string (for future reranker integration).
            phase:        Optional phase hint.
            skill:        Optional skill hint.

        Raises:
            RuntimeError: tokenizer unavailable (count-tokens.sh exit 2).
            ValueError:   unsupported model.
        """
        if not _multi_model_context_enabled():
            # Feature gate OFF — return empty bundle (zero behavior change)
            return ContextBundle(
                model=model,
                sections=[],
                token_total=0,
                budget={"limit": token_budget, "used": 0, "tokenizer": "disabled"},
                assembled_at=datetime.now(tz=timezone.utc).isoformat(),
            )

        valid_models = ("claude", "codex", "ollama")
        if model not in valid_models:
            raise ValueError(f"Unknown model '{model}'. Must be one of: {valid_models}")

        # Determine tokenizer name for budget field
        tokenizer_name = "cl100k_base" if model in ("claude", "codex") else "qwen2.5"

        # Extract all five source types. Query is forwarded to the
        # research extractor so Phase-7 reranking replaces the legacy
        # 30-day mtime glob when a query is provided.
        sections_raw = [
            _extract_logs(),
            _extract_decisions(),
            _extract_memory(),
            _extract_intel(),
            _extract_research(query=query),
        ]

        # Count tokens per section; trim to budget
        assembled_sections: list[BundleSection] = []
        used_tokens = 0

        for section in sections_raw:
            if not section.content.strip():
                # Keep empty sections (so parity test can enumerate source types)
                assembled_sections.append(section)
                continue

            try:
                tok = count_tokens(section.content, model)
            except RuntimeError:
                # Tokenizer unavailable — fail-closed, do NOT fall back to bytes
                raise

            if used_tokens + tok > token_budget:
                # Trim content to fit remaining budget
                remaining = token_budget - used_tokens
                if remaining <= 0:
                    # No room — include section header only to preserve source type
                    section.content = "[budget exhausted — content omitted]"
                    section.tokens = 0
                    assembled_sections.append(section)
                    continue
                # Binary-search trim: take first N chars that fit
                trimmed = _trim_to_budget(section.content, model, remaining)
                section.content = trimmed
                tok = count_tokens(trimmed, model)

            section.tokens = tok
            used_tokens += tok
            assembled_sections.append(section)

        return ContextBundle(
            model=model,
            sections=assembled_sections,
            token_total=used_tokens,
            budget={
                "limit": token_budget,
                "used": used_tokens,
                "tokenizer": tokenizer_name,
            },
            assembled_at=datetime.now(tz=timezone.utc).isoformat(),
        )


def _trim_to_budget(text: str, model: str, max_tokens: int) -> str:
    """Trim text to fit within max_tokens using binary search on character count."""
    if not text:
        return text

    lo, hi = 0, len(text)
    best = ""

    for _ in range(20):  # max iterations
        mid = (lo + hi) // 2
        candidate = text[:mid]
        try:
            tok = count_tokens(candidate, model)
        except RuntimeError:
            raise
        if tok <= max_tokens:
            best = candidate
            lo = mid + 1
        else:
            hi = mid - 1

        if lo > hi:
            break

    return best + ("\n...[trimmed to budget]" if best != text else "")
