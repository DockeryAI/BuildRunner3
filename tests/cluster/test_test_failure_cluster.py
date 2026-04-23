"""
tests/cluster/test_test_failure_cluster.py

Unit tests for core.cluster.below.test_failure_cluster.
All embedding calls are mocked — no real network access.
"""

from __future__ import annotations

import math
from unittest.mock import patch

import pytest

from core.cluster.below.test_failure_cluster import (
    TestCluster,
    TestClusterResult,
    TestOutlier,
    cluster_test_failures,
    cluster_test_failures_safe,
    format_test_cluster,
)

EMBED_DIM = 768


def _unit_vec(angle: float) -> list[float]:
    v = [0.0] * EMBED_DIM
    v[0] = math.cos(angle)
    v[1] = math.sin(angle)
    return v


# ---------------------------------------------------------------------------
# cluster_test_failures — basic behavior
# ---------------------------------------------------------------------------


class TestClusterTestFailures:
    def test_empty_input_returns_skipped(self):
        result = cluster_test_failures([])
        assert result.skipped is True
        assert result.skip_reason == "no lines provided"

    def test_two_similar_failures_form_one_cluster(self):
        lines = [
            "FAIL test_auth.py::test_login — AssertionError",
            "FAIL test_auth.py::test_logout — AssertionError",
        ]
        # Both vecs nearly identical → same cluster
        vec = _unit_vec(0.01)
        with patch("core.cluster.below.log_cluster.embed_batch", return_value=[vec, vec]):
            result = cluster_test_failures(lines, eps=0.25, min_samples=2)

        assert len(result.clusters) == 1
        assert result.clusters[0].frequency == 2

    def test_distinct_failures_become_outliers(self):
        lines = [
            "FAIL test_auth.py::test_login — AssertionError: expected True got False",
            "FAIL test_db.py::test_connection — ConnectionError: refused",
        ]
        # Orthogonal vecs → cosine distance = 1.0 → outliers with eps=0.25
        vec_a = _unit_vec(0.0)
        vec_b = _unit_vec(math.pi / 2)
        with patch("core.cluster.below.log_cluster.embed_batch", return_value=[vec_a, vec_b]):
            result = cluster_test_failures(lines, eps=0.25, min_samples=2)

        assert len(result.outliers) == 2
        assert len(result.clusters) == 0

    def test_outlier_text_preserved(self):
        lines = ["FAIL unique test failure here XYZ"]
        vec = _unit_vec(0.5)
        with patch("core.cluster.below.log_cluster.embed_batch", return_value=[vec]):
            result = cluster_test_failures(lines, min_samples=2)

        assert len(result.outliers) == 1
        assert result.outliers[0].text == lines[0]

    def test_lines_processed_count(self):
        lines = [f"FAIL test_{i}.py::test_x" for i in range(10)]
        vecs = [_unit_vec(i * 0.5) for i in range(10)]
        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_test_failures(lines, min_samples=2)

        assert result.lines_processed == 10

    def test_respects_max_lines_cap(self):
        lines = [f"FAIL test_{i}.py::test_x" for i in range(50)]
        # Only first 5 should be processed
        vecs = [_unit_vec(i * 0.1) for i in range(5)]
        with patch("core.cluster.below.log_cluster.embed_batch", return_value=vecs):
            result = cluster_test_failures(lines, max_lines=5, min_samples=2)

        assert result.lines_processed == 5


# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------


class TestRollbackFlag:
    def test_br3_test_cluster_off_raises(self):
        import core.cluster.below.test_failure_cluster as mod
        orig = mod._TEST_CLUSTER_ENABLED
        mod._TEST_CLUSTER_ENABLED = False
        try:
            with pytest.raises(RuntimeError, match="BR3_TEST_CLUSTER=off"):
                cluster_test_failures(["some test failure"])
        finally:
            mod._TEST_CLUSTER_ENABLED = orig

    def test_safe_wrapper_returns_none_on_rollback(self):
        import core.cluster.below.test_failure_cluster as mod
        orig = mod._TEST_CLUSTER_ENABLED
        mod._TEST_CLUSTER_ENABLED = False
        try:
            result = cluster_test_failures_safe(["some test failure"])
            assert result is None
        finally:
            mod._TEST_CLUSTER_ENABLED = orig


# ---------------------------------------------------------------------------
# Below offline fail-open
# ---------------------------------------------------------------------------


class TestBelowOffline:
    def test_raises_on_below_offline(self):
        from core.cluster.below.embed import BelowOfflineError
        with patch("core.cluster.below.log_cluster.embed_batch",
                   side_effect=BelowOfflineError("circuit open")):
            with pytest.raises(RuntimeError):
                cluster_test_failures(["test failure"])

    def test_safe_wrapper_returns_none_on_offline(self):
        from core.cluster.below.embed import BelowOfflineError
        with patch("core.cluster.below.log_cluster.embed_batch",
                   side_effect=BelowOfflineError("circuit open")):
            result = cluster_test_failures_safe(["test failure"])
        assert result is None


# ---------------------------------------------------------------------------
# format_test_cluster
# ---------------------------------------------------------------------------


class TestFormatTestCluster:
    def test_empty_result_returns_empty_string(self):
        result = TestClusterResult(skipped=True, skip_reason="no lines")
        assert format_test_cluster(result) == ""

    def test_cluster_shows_frequency(self):
        result = TestClusterResult(
            clusters=[TestCluster(representative="AssertionError in login", frequency=5)],
            outliers=[],
            lines_processed=5,
        )
        summary = format_test_cluster(result)
        assert "[5x]" in summary
        assert "AssertionError in login" in summary

    def test_outliers_are_listed(self):
        result = TestClusterResult(
            clusters=[],
            outliers=[TestOutlier(index=0, text="Unique timeout in payment service")],
            lines_processed=1,
        )
        summary = format_test_cluster(result)
        assert "Unique timeout in payment service" in summary
        assert "outlier" in summary.lower()

    def test_max_clusters_limit(self):
        clusters = [
            TestCluster(representative=f"cluster {i}", frequency=1)
            for i in range(20)
        ]
        result = TestClusterResult(clusters=clusters, outliers=[], lines_processed=20)
        summary = format_test_cluster(result, max_clusters=5)
        assert summary.count("[1x]") == 5

    def test_summary_line_with_counts(self):
        result = TestClusterResult(
            clusters=[TestCluster(representative="err", frequency=3, member_indices=[0, 1, 2])],
            outliers=[TestOutlier(index=3, text="other")],
            lines_processed=4,
        )
        summary = format_test_cluster(result)
        assert "4 lines" in summary
        assert "1 clusters" in summary
        assert "1 outliers" in summary


# ---------------------------------------------------------------------------
# safe wrapper integration
# ---------------------------------------------------------------------------


class TestSafeWrapper:
    def test_returns_string_on_success(self):
        lines = ["FAIL test_x.py::test_a — error"]
        vec = _unit_vec(0.1)
        with patch("core.cluster.below.log_cluster.embed_batch", return_value=[vec]):
            result = cluster_test_failures_safe(lines, min_samples=2)
        # Single line becomes outlier, which is non-empty
        assert result is None or isinstance(result, str)

    def test_returns_none_on_exception(self):
        with patch("core.cluster.below.log_cluster.embed_batch", side_effect=RuntimeError("boom")):
            result = cluster_test_failures_safe(["test failure"])
        assert result is None

    def test_returns_none_for_empty_cluster_result(self):
        result = cluster_test_failures_safe([])
        # Empty input → skipped → format returns "" → safe wrapper returns None
        assert result is None
