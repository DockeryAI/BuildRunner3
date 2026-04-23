"""
tests/test_spec_drift.py

Unit tests for core.cluster.below.spec_drift — spec-drift detection.
All embedding calls are mocked; no real network access.
"""

from __future__ import annotations

import json
import os
import math
from pathlib import Path
from unittest.mock import patch

import pytest

from core.cluster.below.spec_drift import (
    DriftCandidate,
    DriftReport,
    _cosine_sim,
    _extract_code_symbols,
    _extract_spec_items,
    detect_spec_drift,
    format_drift_report,
)

EMBED_DIM = 768


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _unit_vec(angle: float) -> list[float]:
    v = [0.0] * EMBED_DIM
    v[0] = math.cos(angle)
    v[1] = math.sin(angle)
    return v


def _make_build_spec(tmp_path: Path, content: str) -> Path:
    builds_dir = tmp_path / ".buildrunner" / "builds"
    builds_dir.mkdir(parents=True)
    spec = builds_dir / "BUILD_test.md"
    spec.write_text(content)
    return spec


def _make_py_file(tmp_path: Path, rel_path: str, content: str) -> Path:
    p = tmp_path / rel_path
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(content)
    return p


# ---------------------------------------------------------------------------
# Project-scoping guard
# ---------------------------------------------------------------------------


class TestProjectScopingGuard:
    def test_returns_skipped_when_no_build_spec(self, tmp_path):
        result = detect_spec_drift(tmp_path)
        assert result.skipped is True
        assert "no BUILD spec" in result.skip_reason

    def test_returns_skipped_when_build_dir_missing(self, tmp_path):
        result = detect_spec_drift(tmp_path)
        assert result.skipped is True

    def test_not_skipped_when_build_spec_exists(self, tmp_path):
        _make_build_spec(tmp_path, "- [ ] implement embed_batch function")
        _make_py_file(tmp_path, "core/embed.py", "def embed_batch(): pass")

        vecs = [_unit_vec(0.0)]
        with patch("core.cluster.below.embed.embed_batch", return_value=vecs):
            result = detect_spec_drift(tmp_path)

        assert result.skipped is False


# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------


class TestRollbackFlag:
    def test_br3_spec_drift_off_returns_skipped(self, tmp_path):
        _make_build_spec(tmp_path, "- [ ] implement something")

        import core.cluster.below.spec_drift as mod
        orig = mod._DRIFT_ENABLED
        mod._DRIFT_ENABLED = False
        try:
            result = detect_spec_drift(tmp_path)
        finally:
            mod._DRIFT_ENABLED = orig

        assert result.skipped is True
        assert "BR3_SPEC_DRIFT=off" in result.skip_reason


# ---------------------------------------------------------------------------
# Drift detection — injected drift
# ---------------------------------------------------------------------------


class TestDriftDetection:
    def test_detects_injected_drift(self, tmp_path):
        """Spec item with no similar code symbol → drift candidate."""
        _make_build_spec(tmp_path, "- [ ] implement quantum_teleport function")
        _make_py_file(tmp_path, "core/foo.py", "def embed_batch(): pass")

        # Spec vec (angle 0) vs code vec (angle π/2) → cosine sim ≈ 0.0 → drift
        spec_vec = _unit_vec(0.0)
        code_vec = _unit_vec(math.pi / 2)

        with patch("core.cluster.below.embed.embed_batch") as mock_embed:
            mock_embed.side_effect = [
                [spec_vec],   # spec items embed
                [code_vec],   # code symbols embed
            ]
            result = detect_spec_drift(tmp_path, threshold=0.65)

        assert result.has_drift is True
        assert len(result.drift_candidates) >= 1
        assert result.drift_candidates[0].best_score < 0.65

    def test_clean_baseline_no_false_positives(self, tmp_path):
        """Spec item with highly similar code symbol → no drift."""
        _make_build_spec(tmp_path, "- [ ] implement embed_batch for Below")
        _make_py_file(tmp_path, "core/embed.py", "def embed_batch(): pass")

        # Both vecs nearly identical → cosine sim ≈ 1.0 → no drift
        similar_vec = _unit_vec(0.001)

        with patch("core.cluster.below.embed.embed_batch") as mock_embed:
            mock_embed.side_effect = [
                [similar_vec],   # spec
                [similar_vec],   # code
            ]
            result = detect_spec_drift(tmp_path, threshold=0.65)

        assert result.has_drift is False
        assert len(result.drift_candidates) == 0

    def test_advisory_only_no_mutations(self, tmp_path):
        """detect_spec_drift must never write to the project directory."""
        _make_build_spec(tmp_path, "- [ ] implement something")
        _make_py_file(tmp_path, "core/x.py", "def something(): pass")

        vecs = [_unit_vec(0.0)]
        files_before = set(tmp_path.rglob("*"))

        with patch("core.cluster.below.embed.embed_batch", return_value=vecs):
            detect_spec_drift(tmp_path)

        files_after = set(tmp_path.rglob("*"))
        # No new files should have been created
        new_files = files_after - files_before
        assert not new_files, f"detect_spec_drift created unexpected files: {new_files}"


# ---------------------------------------------------------------------------
# Below-offline handling
# ---------------------------------------------------------------------------


class TestBelowOfflineHandling:
    def test_returns_skipped_on_below_offline(self, tmp_path):
        _make_build_spec(tmp_path, "- [ ] implement embed_batch")
        _make_py_file(tmp_path, "core/embed.py", "def embed_batch(): pass")

        from core.cluster.below.embed import BelowOfflineError
        with patch("core.cluster.below.embed.embed_batch",
                   side_effect=BelowOfflineError("circuit open")):
            result = detect_spec_drift(tmp_path)

        assert result.skipped is True
        assert "offline" in result.skip_reason.lower() or "Below" in result.skip_reason

    def test_never_raises(self, tmp_path):
        """detect_spec_drift must never propagate exceptions."""
        _make_build_spec(tmp_path, "- [ ] implement something")

        with patch("core.cluster.below.embed.embed_batch",
                   side_effect=RuntimeError("unexpected crash")):
            result = detect_spec_drift(tmp_path)

        # Should return a report with error field, not raise
        assert result is not None
        assert isinstance(result, DriftReport)


# ---------------------------------------------------------------------------
# Spec item extraction
# ---------------------------------------------------------------------------


class TestExtractSpecItems:
    def test_extracts_unchecked_items(self, tmp_path):
        spec = _make_build_spec(tmp_path, """
## Deliverables

- [ ] implement embed_batch function
- [x] already done item
- [ ] add timeout and retry logic
""")
        items = _extract_spec_items([spec], max_items=100)
        texts = [t for t, _ in items]
        assert any("embed_batch" in t for t in texts)
        assert any("timeout" in t for t in texts)

    def test_skips_short_items(self, tmp_path):
        spec = _make_build_spec(tmp_path, "- [ ] ok\n- [ ] implement the full embed_batch wrapper")
        items = _extract_spec_items([spec], max_items=100)
        # "ok" is <10 chars, should be skipped
        texts = [t for t, _ in items]
        assert not any(t == "ok" for t in texts)

    def test_respects_max_items(self, tmp_path):
        lines = "\n".join(f"- [ ] implement feature number {i} with full tests" for i in range(50))
        spec = _make_build_spec(tmp_path, lines)
        items = _extract_spec_items([spec], max_items=10)
        assert len(items) <= 10


# ---------------------------------------------------------------------------
# Code symbol extraction
# ---------------------------------------------------------------------------


class TestExtractCodeSymbols:
    def test_extracts_public_functions(self, tmp_path):
        _make_py_file(tmp_path, "core/foo.py", "def embed_batch(texts): pass\ndef check_health(): pass\n")
        symbols = _extract_code_symbols(tmp_path, max_symbols=100)
        names = [s for s, _ in symbols]
        assert any("embed_batch" in n for n in names)
        assert any("check_health" in n for n in names)

    def test_skips_private_helpers(self, tmp_path):
        _make_py_file(tmp_path, "core/foo.py",
                      "def _private_helper(): pass\ndef public_fn(): pass\n")
        symbols = _extract_code_symbols(tmp_path, max_symbols=100)
        names = [s for s, _ in symbols]
        assert not any("_private_helper" in n for n in names)
        assert any("public_fn" in n for n in names)

    def test_extracts_classes(self, tmp_path):
        _make_py_file(tmp_path, "core/foo.py", "class SchemaClassifier:\n    pass\n")
        symbols = _extract_code_symbols(tmp_path, max_symbols=100)
        names = [s for s, _ in symbols]
        assert any("SchemaClassifier" in n for n in names)


# ---------------------------------------------------------------------------
# Format drift report
# ---------------------------------------------------------------------------


class TestFormatDriftReport:
    def test_skipped_report_message(self):
        report = DriftReport(skipped=True, skip_reason="no BUILD spec found")
        msg = format_drift_report(report)
        assert "skipped" in msg

    def test_clean_report_message(self):
        report = DriftReport(skipped=False, has_drift=False,
                             spec_items_checked=5, code_symbols_checked=10, threshold=0.65)
        msg = format_drift_report(report)
        assert "clean" in msg

    def test_drift_report_message(self):
        candidate = DriftCandidate(
            spec_item="implement quantum_teleport",
            best_score=0.12,
        )
        report = DriftReport(skipped=False, has_drift=True,
                             drift_candidates=[candidate], threshold=0.65)
        msg = format_drift_report(report)
        assert "DRIFT" in msg
        assert "quantum_teleport" in msg


# ---------------------------------------------------------------------------
# Cosine similarity helper
# ---------------------------------------------------------------------------


class TestCosineSim:
    def test_identical_vectors(self):
        v = [1.0, 0.5] + [0.0] * (EMBED_DIM - 2)
        assert _cosine_sim(v, v) == pytest.approx(1.0)

    def test_orthogonal_vectors(self):
        a = [1.0] + [0.0] * (EMBED_DIM - 1)
        b = [0.0, 1.0] + [0.0] * (EMBED_DIM - 2)
        assert _cosine_sim(a, b) == pytest.approx(0.0, abs=1e-9)
