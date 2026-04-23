"""
tests/cluster/test_log_cluster.py

Unit tests for core.cluster.below.log_cluster — DBSCAN clustering of log lines.
All embedding calls are mocked; no real network or scikit-learn computation
except where the DBSCAN logic itself is under test (with synthetic 2-d vectors).
"""

from __future__ import annotations

import json
import math
import os
from pathlib import Path
from unittest.mock import patch

import pytest

from core.cluster.below.embed import BelowOfflineError
from core.cluster.below.log_cluster import (
    ClusterResult,
    Outlier,
    cluster_lines,
    format_cluster_summary,
)

FIXTURES_DIR = Path(__file__).parent.parent / "fixtures"
BENCHMARK_FILE = FIXTURES_DIR / "cluster_benchmark.jsonl"

# ---------------------------------------------------------------------------
# Synthetic vector helpers
# ---------------------------------------------------------------------------

EMBED_DIM = 768


def _unit_vec(angle_rad: float) -> list[float]:
    """Return a 768-d unit vector pointing in a 2-d direction (rest zeros)."""
    v = [0.0] * EMBED_DIM
    v[0] = math.cos(angle_rad)
    v[1] = math.sin(angle_rad)
    return v


def _make_cluster_vectors(n_per_cluster: int, n_clusters: int, n_outliers: int):
    """
    Build synthetic vectors where:
    - n_clusters groups of n_per_cluster vectors point in the same direction
    - n_outliers vectors are orthogonal to all clusters
    Returns (vectors, expected_cluster_count, expected_outlier_count).
    """
    vecs = []
    # Clusters: each cluster points at angle k * (2pi / n_clusters)
    for k in range(n_clusters):
        angle = k * (2 * math.pi / n_clusters)
        for _ in range(n_per_cluster):
            # Add tiny jitter (stays within eps=0.25 cosine distance from centroid)
            jitter_angle = angle + 0.01
            vecs.append(_unit_vec(jitter_angle))

    # Outliers: unique directions orthogonal to all clusters
    for i in range(n_outliers):
        angle = math.pi / 2 + i * 0.001  # near orthogonal
        vecs.append(_unit_vec(angle))

    return vecs


# ---------------------------------------------------------------------------
# Happy path
# ---------------------------------------------------------------------------


class TestClusterLinesHappyPath:
    def test_clusters_identical_lines(self):
        """Lines with the same text should form a single cluster."""
        lines = ["ERROR connection refused"] * 5
        vecs = [_unit_vec(0.0)] * 5

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.25, min_samples=2)

        assert len(result.clusters) == 1
        assert result.clusters[0].frequency == 5
        assert len(result.outliers) == 0

    def test_two_distinct_clusters(self):
        lines = (["ERROR connection refused"] * 4 + ["WARNING retry attempt"] * 4)
        # Two groups of 4, pointing in orthogonal directions
        vecs = [_unit_vec(0.0)] * 4 + [_unit_vec(math.pi / 2)] * 4

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.25, min_samples=2)

        assert len(result.clusters) == 2
        assert len(result.outliers) == 0
        frequencies = sorted(c.frequency for c in result.clusters)
        assert frequencies == [4, 4]

    def test_result_shape(self):
        lines = ["line a"] * 3 + ["line b"] * 3
        vecs = [_unit_vec(0.0)] * 3 + [_unit_vec(math.pi / 2)] * 3

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines)

        assert isinstance(result, ClusterResult)
        assert hasattr(result, "clusters")
        assert hasattr(result, "outliers")
        assert result.total_lines == 6

    def test_member_indices_are_original_indices(self):
        """member_indices must refer to positions in the original input list."""
        lines = ["A"] * 3 + ["B"] * 3
        vecs = [_unit_vec(0.0)] * 3 + [_unit_vec(math.pi / 2)] * 3

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.25, min_samples=2)

        all_indices = [i for c in result.clusters for i in c.member_indices]
        assert sorted(all_indices) == list(range(6))

    def test_empty_lines_skipped(self):
        lines = ["", "ERROR something", "", "ERROR something else", ""]
        vecs = [_unit_vec(0.1), _unit_vec(0.15)]  # two non-empty lines

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.25, min_samples=2)

        # embed_batch called only for non-empty lines
        assert result.total_lines == 2

    def test_empty_input_raises(self):
        with pytest.raises(ValueError, match="at least one line"):
            cluster_lines([])

    def test_all_empty_lines_returns_empty_result(self):
        result = cluster_lines(["", "   ", "\t"])
        assert result.clusters == []
        assert result.outliers == []


# ---------------------------------------------------------------------------
# Outlier handling — DBSCAN label -1
# ---------------------------------------------------------------------------


class TestOutlierHandling:
    def test_singletons_become_outliers(self):
        """Lines that don't meet min_samples threshold become outliers."""
        lines = ["unique error A", "unique error B", "unique error C"]
        # Each line in its own direction — all singletons
        vecs = [_unit_vec(i * math.pi / 3) for i in range(3)]

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.1, min_samples=2)

        # All are outliers since no cluster has ≥2 members
        assert len(result.outliers) == 3
        assert len(result.clusters) == 0

    def test_outliers_expose_original_text(self):
        lines = ["CRITICAL disk full", "FATAL kernel OOM"]
        vecs = [_unit_vec(0.0), _unit_vec(math.pi / 2)]

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.1, min_samples=2)

        outlier_texts = {o.text for o in result.outliers}
        assert "CRITICAL disk full" in outlier_texts
        assert "FATAL kernel OOM" in outlier_texts

    def test_outliers_have_correct_indices(self):
        lines = ["cluster line", "cluster line", "singleton"]
        vecs = [_unit_vec(0.0), _unit_vec(0.01), _unit_vec(math.pi / 2)]

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.25, min_samples=2)

        assert len(result.outliers) == 1
        assert result.outliers[0].index == 2
        assert result.outliers[0].text == "singleton"

    def test_outliers_never_dropped(self):
        """100% of singletons must appear in result.outliers."""
        lines = [f"unique line {i}" for i in range(10)]
        # All distinct directions → all singletons
        vecs = [_unit_vec(i * 0.3) for i in range(10)]

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.01, min_samples=2)

        assert len(result.outliers) == 10, "All singletons must be in outliers"


# ---------------------------------------------------------------------------
# Below-offline fail-open behaviour
# ---------------------------------------------------------------------------


class TestBelowOfflineBehaviour:
    def test_raises_below_offline_error(self):
        with patch(
            "core.cluster.below.log_cluster.embed_batch",
            side_effect=BelowOfflineError("circuit open"),
        ):
            with pytest.raises(BelowOfflineError):
                cluster_lines(["some log line"])

    def test_error_propagates_for_caller_to_catch(self):
        """Callers are expected to catch BelowOfflineError and fall through."""
        caught = []

        def caller_with_failopen(lines):
            try:
                return cluster_lines(lines)
            except BelowOfflineError:
                caught.append(True)
                return None  # fall through

        with patch(
            "core.cluster.below.log_cluster.embed_batch",
            side_effect=BelowOfflineError("down"),
        ):
            result = caller_with_failopen(["a", "b"])

        assert result is None
        assert len(caught) == 1


# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------


class TestRollbackFlag:
    def test_br3_log_cluster_off_raises_runtime_error(self):
        with patch.dict(os.environ, {"BR3_LOG_CLUSTER": "off"}):
            # Re-import to pick up env var (the module-level check needs reload)
            import importlib
            import core.cluster.below.log_cluster as mod
            orig = mod._CLUSTER_ENABLED
            mod._CLUSTER_ENABLED = False
            try:
                with pytest.raises(RuntimeError, match="BR3_LOG_CLUSTER=off"):
                    cluster_lines(["test"], eps=0.25, min_samples=2)
            finally:
                mod._CLUSTER_ENABLED = orig


# ---------------------------------------------------------------------------
# Line cap
# ---------------------------------------------------------------------------


class TestLineCap:
    def test_max_lines_caps_embed_calls(self):
        lines = [f"line {i}" for i in range(200)]
        capped_vecs = [_unit_vec(i * 0.01 % (2 * math.pi)) for i in range(50)]

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=capped_vecs) as mock:
            result = cluster_lines(lines, max_lines=50)

        # embed_batch should have been called with 50 texts, not 200
        call_args = mock.call_args[0][0]
        assert len(call_args) == 50


# ---------------------------------------------------------------------------
# format_cluster_summary
# ---------------------------------------------------------------------------


class TestFormatClusterSummary:
    def test_summary_contains_frequency(self):
        lines = ["ERROR db"] * 3 + ["WARN retry"] * 2
        vecs = [_unit_vec(0.0)] * 3 + [_unit_vec(math.pi / 2)] * 2

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.25, min_samples=2)

        summary = format_cluster_summary(result)
        assert "[3x]" in summary or "[2x]" in summary

    def test_summary_lists_all_outliers(self):
        lines = ["cluster"] * 3 + ["unique A", "unique B"]
        # Use eps=0.01 to force "unique A" and "unique B" at angles 1.0 and 1.5
        # to be isolated singletons (cosine distance between them is ~0.23, just
        # above the tight threshold)
        vecs = [_unit_vec(0.0)] * 3 + [_unit_vec(1.0), _unit_vec(math.pi)]

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.1, min_samples=2)

        summary = format_cluster_summary(result)
        # Both singletons must appear
        assert "unique A" in summary
        assert "unique B" in summary

    def test_summary_section_headers(self):
        lines = ["cluster"] * 3
        vecs = [_unit_vec(0.0)] * 3

        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_lines(lines, eps=0.25, min_samples=2)

        summary = format_cluster_summary(result)
        assert "Clustered patterns" in summary


# ---------------------------------------------------------------------------
# Benchmark fixture (structure check only — no live embedding)
# ---------------------------------------------------------------------------


class TestBenchmarkFixture:
    def test_fixture_exists(self):
        assert BENCHMARK_FILE.exists(), f"Benchmark fixture missing: {BENCHMARK_FILE}"

    def test_fixture_has_required_fields(self):
        with BENCHMARK_FILE.open() as f:
            lines = [json.loads(l) for l in f if l.strip()]
        assert len(lines) > 0
        for record in lines:
            assert "id" in record
            assert "text" in record
            assert "expected_cluster" in record

    def test_fixture_has_singletons(self):
        with BENCHMARK_FILE.open() as f:
            lines = [json.loads(l) for l in f if l.strip()]
        singletons = [r for r in lines if r["expected_cluster"] == "singleton"]
        assert len(singletons) >= 2, "Fixture must have ≥2 singleton entries"

    def test_fixture_has_multiple_clusters(self):
        with BENCHMARK_FILE.open() as f:
            lines = [json.loads(l) for l in f if l.strip()]
        cluster_names = {r["expected_cluster"] for r in lines if r["expected_cluster"] != "singleton"}
        assert len(cluster_names) >= 3, "Fixture must have ≥3 distinct cluster groups"
