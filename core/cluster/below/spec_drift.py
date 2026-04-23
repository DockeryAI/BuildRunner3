"""
spec_drift.py — Spec-drift detection for /begin step 0.

Compares BUILD spec requirements against current codebase implementation
using embedding similarity. Surfaces draft candidates (requirements with no
clear implementation) and orphans (implementations with no spec item).

Advisory only — never auto-fixes. Integrates into begin_workflow.py step 0.

Usage:
    from core.cluster.below.spec_drift import detect_spec_drift, DriftReport

    report = detect_spec_drift(project_root=Path("."))
    if report.has_drift:
        for candidate in report.drift_candidates:
            print(f"[DRIFT] {candidate.spec_item} → no impl found")

Project-scoping guard:
    detect_spec_drift returns DriftReport(skipped=True) when no BUILD_*.md
    exists under .buildrunner/builds/. Silent; does not raise.

Rollback: set BR3_SPEC_DRIFT=off — function returns skipped=True immediately.

Uses core.cluster.below.embed (no coupling to log_cluster internals).
"""

from __future__ import annotations

import glob
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# Rollback flag
_DRIFT_ENABLED = os.environ.get("BR3_SPEC_DRIFT", "on").lower() != "off"

# Similarity threshold below which a spec item is considered "drifted"
DEFAULT_DRIFT_THRESHOLD: float = 0.65

# Max spec items / code symbols to embed (bounds latency)
MAX_SPEC_ITEMS: int = 100
MAX_CODE_SYMBOLS: int = 200


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class DriftCandidate:
    """A spec item with no sufficiently similar implementation."""

    spec_item: str            # Deliverable text from BUILD spec
    best_match: Optional[str] = None  # Closest code symbol, if any
    best_score: float = 0.0          # Cosine similarity of best match


@dataclass
class OrphanSymbol:
    """A code symbol/function with no corresponding spec item."""

    symbol: str           # Function/class name
    file_path: str        # Source file


@dataclass
class DriftReport:
    """Full drift detection output."""

    skipped: bool = False                          # True when no BUILD spec or flag off
    skip_reason: str = ""
    has_drift: bool = False
    drift_candidates: list[DriftCandidate] = field(default_factory=list)
    orphan_symbols: list[OrphanSymbol] = field(default_factory=list)
    spec_items_checked: int = 0
    code_symbols_checked: int = 0
    threshold: float = DEFAULT_DRIFT_THRESHOLD
    error: Optional[str] = None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def detect_spec_drift(
    project_root: Path,
    *,
    threshold: float = DEFAULT_DRIFT_THRESHOLD,
    max_spec_items: int = MAX_SPEC_ITEMS,
    max_code_symbols: int = MAX_CODE_SYMBOLS,
) -> DriftReport:
    """
    Detect drift between BUILD spec deliverables and codebase implementations.

    Args:
        project_root:    Root of the project to scan.
        threshold:       Cosine similarity below which a spec item is "drifted".
        max_spec_items:  Cap on spec items to embed (bounds latency).
        max_code_symbols: Cap on code symbols to embed.

    Returns:
        DriftReport — advisory only, never mutates the codebase.

    Guarantees:
        - Returns DriftReport(skipped=True) if no BUILD spec exists.
        - Returns DriftReport(skipped=True) if BR3_SPEC_DRIFT=off.
        - Never raises (all errors captured in DriftReport.error).
    """
    if not _DRIFT_ENABLED:
        return DriftReport(skipped=True, skip_reason="BR3_SPEC_DRIFT=off")

    builds_dir = project_root / ".buildrunner" / "builds"
    build_files = list(builds_dir.glob("BUILD_*.md"))
    if not build_files:
        return DriftReport(skipped=True, skip_reason="no BUILD spec found — not a BR3 project")

    try:
        return _run_drift_detection(
            project_root=project_root,
            build_files=build_files,
            threshold=threshold,
            max_spec_items=max_spec_items,
            max_code_symbols=max_code_symbols,
        )
    except Exception as exc:  # noqa: BLE001
        logger.warning("spec_drift: detection failed: %s", exc)
        return DriftReport(
            skipped=False,
            has_drift=False,
            error=str(exc),
        )


# ---------------------------------------------------------------------------
# Internal implementation
# ---------------------------------------------------------------------------


def _run_drift_detection(
    project_root: Path,
    build_files: list[Path],
    threshold: float,
    max_spec_items: int,
    max_code_symbols: int,
) -> DriftReport:
    from core.cluster.below.embed import embed_batch, BelowOfflineError

    # Extract spec items from all BUILD files
    spec_items = _extract_spec_items(build_files, max_items=max_spec_items)
    if not spec_items:
        return DriftReport(skipped=True, skip_reason="no deliverable items found in BUILD spec")

    # Extract code symbols from project Python/TS/JS files
    code_symbols = _extract_code_symbols(project_root, max_symbols=max_code_symbols)
    if not code_symbols:
        return DriftReport(
            skipped=False,
            spec_items_checked=len(spec_items),
            code_symbols_checked=0,
            threshold=threshold,
            skip_reason="no code symbols found in project",
        )

    # Embed spec items
    try:
        spec_vecs = embed_batch([item for item, _ in spec_items])
    except BelowOfflineError as exc:
        return DriftReport(
            skipped=True,
            skip_reason=f"Below embed offline: {exc}",
        )

    # Embed code symbol descriptions
    try:
        code_texts = [sym for sym, _ in code_symbols]
        code_vecs = embed_batch(code_texts)
    except BelowOfflineError as exc:
        return DriftReport(
            skipped=True,
            skip_reason=f"Below embed offline: {exc}",
        )

    # Compare: for each spec item, find best-matching code symbol
    drift_candidates: list[DriftCandidate] = []
    for i, (spec_text, _) in enumerate(spec_items):
        spec_vec = spec_vecs[i]
        best_score = 0.0
        best_sym: Optional[str] = None

        for j, code_vec in enumerate(code_vecs):
            score = _cosine_sim(spec_vec, code_vec)
            if score > best_score:
                best_score = score
                best_sym = code_symbols[j][0]

        if best_score < threshold:
            drift_candidates.append(
                DriftCandidate(
                    spec_item=spec_text[:120],
                    best_match=best_sym,
                    best_score=round(best_score, 3),
                )
            )

    # Orphan detection: code symbols with no matching spec item above threshold
    orphan_symbols: list[OrphanSymbol] = []
    for j, (sym_text, sym_file) in enumerate(code_symbols):
        code_vec = code_vecs[j]
        best_score = 0.0
        for spec_vec in spec_vecs:
            score = _cosine_sim(code_vec, spec_vec)
            if score > best_score:
                best_score = score
        if best_score < threshold:
            orphan_symbols.append(OrphanSymbol(symbol=sym_text[:80], file_path=sym_file))

    has_drift = bool(drift_candidates)
    return DriftReport(
        skipped=False,
        has_drift=has_drift,
        drift_candidates=drift_candidates,
        orphan_symbols=orphan_symbols,
        spec_items_checked=len(spec_items),
        code_symbols_checked=len(code_symbols),
        threshold=threshold,
    )


def _extract_spec_items(build_files: list[Path], max_items: int) -> list[tuple[str, str]]:
    """
    Extract deliverable checklist items from BUILD spec files.
    Returns list of (item_text, source_file).
    """
    items: list[tuple[str, str]] = []
    checklist_re = re.compile(r"^\s*-\s*\[[ x]\]\s*(.+)$", re.MULTILINE)

    for build_file in build_files:
        try:
            text = build_file.read_text(encoding="utf-8", errors="replace")
            for match in checklist_re.finditer(text):
                item_text = match.group(1).strip()
                if item_text and len(item_text) > 10:
                    items.append((item_text, str(build_file)))
                if len(items) >= max_items:
                    return items
        except OSError:
            continue

    return items


def _extract_code_symbols(project_root: Path, max_symbols: int) -> list[tuple[str, str]]:
    """
    Extract function/class definitions from Python files as (description, file) pairs.
    Produces human-readable descriptions suitable for embedding.
    """
    symbols: list[tuple[str, str]] = []
    func_re = re.compile(r"^\s*(?:async\s+)?def\s+([a-zA-Z_]\w*)\s*\(", re.MULTILINE)
    class_re = re.compile(r"^\s*class\s+([a-zA-Z_]\w*)\s*[:(]", re.MULTILINE)

    # Scan core/ and tests/ directories only (bounded scope)
    scan_dirs = [
        project_root / "core",
        project_root / "api",
    ]

    for scan_dir in scan_dirs:
        if not scan_dir.exists():
            continue
        for py_file in sorted(scan_dir.rglob("*.py")):
            if "__pycache__" in str(py_file):
                continue
            try:
                text = py_file.read_text(encoding="utf-8", errors="replace")
                rel_path = str(py_file.relative_to(project_root))

                for match in class_re.finditer(text):
                    sym = f"class {match.group(1)} in {rel_path}"
                    symbols.append((sym, rel_path))
                    if len(symbols) >= max_symbols:
                        return symbols

                for match in func_re.finditer(text):
                    name = match.group(1)
                    if name.startswith("_") and not name.startswith("__"):
                        continue  # skip private helpers
                    sym = f"function {name} in {rel_path}"
                    symbols.append((sym, rel_path))
                    if len(symbols) >= max_symbols:
                        return symbols

            except OSError:
                continue

    return symbols


def _cosine_sim(a: list[float], b: list[float]) -> float:
    """Fast cosine similarity for two equal-length vectors."""
    dot = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(y * y for y in b) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


# ---------------------------------------------------------------------------
# Human-readable summary for /begin output
# ---------------------------------------------------------------------------


def format_drift_report(report: DriftReport) -> str:
    """Format a DriftReport for advisory display in /begin step 0."""
    if report.skipped:
        return f"[spec-drift] skipped — {report.skip_reason}"

    if report.error:
        return f"[spec-drift] detection error: {report.error}"

    if not report.has_drift:
        return (
            f"[spec-drift] clean — {report.spec_items_checked} spec items, "
            f"{report.code_symbols_checked} code symbols checked, "
            f"all above {report.threshold:.0%} threshold"
        )

    lines = [
        f"[spec-drift] {len(report.drift_candidates)} drift candidate(s) — advisory only, no auto-fix"
    ]
    for c in report.drift_candidates[:10]:
        score_str = f"{c.best_score:.2f}" if c.best_score else "none"
        lines.append(f"  DRIFT  [{score_str}] {c.spec_item[:80]}")

    if report.orphan_symbols:
        lines.append(f"  {len(report.orphan_symbols)} code symbol(s) with no spec coverage")

    return "\n".join(lines)
