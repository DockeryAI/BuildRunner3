"""
test_failure_cluster.py — Cluster CI test failure lines before /root analysis.

Wraps core.cluster.below.log_cluster with test-failure-specific defaults:
lower eps (test failures are more distinct than log lines), shorter max_lines.

Usage:
    from core.cluster.below.test_failure_cluster import cluster_test_failures, format_test_cluster

    result = cluster_test_failures(failure_lines)
    summary = format_test_cluster(result)
    # Feed summary to /root instead of raw lines (≥25% token reduction)

Rollback: BR3_TEST_CLUSTER=off → raises RuntimeError (caller must catch and use raw lines).
Fail-open: Below offline → raises RuntimeError (caller must catch and use raw lines).

Mirrors log_cluster.py contract exactly so callers can swap them.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from typing import Optional

# Rollback flag
_TEST_CLUSTER_ENABLED: bool = os.environ.get("BR3_TEST_CLUSTER", "on").lower() != "off"

# Defaults tuned for test failure lines (more semantically distinct than logs)
DEFAULT_EPS: float = 0.20
DEFAULT_MIN_SAMPLES: int = 2
DEFAULT_MAX_LINES: int = 200


@dataclass
class TestCluster:
    """A cluster of semantically similar test failure lines."""
    representative: str          # Most common / central failure text
    frequency: int               # Number of lines in this cluster
    member_indices: list[int] = field(default_factory=list)


@dataclass
class TestOutlier:
    """A unique test failure with no cluster peers."""
    index: int
    text: str


@dataclass
class TestClusterResult:
    """Full clustering output for a batch of test failure lines."""
    clusters: list[TestCluster] = field(default_factory=list)
    outliers: list[TestOutlier] = field(default_factory=list)
    lines_processed: int = 0
    skipped: bool = False
    skip_reason: str = ""


def cluster_test_failures(
    lines: list[str],
    *,
    eps: float = DEFAULT_EPS,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    max_lines: int = DEFAULT_MAX_LINES,
) -> TestClusterResult:
    """
    Cluster test failure output lines by semantic similarity.

    Args:
        lines:       Raw test failure output lines (from pytest/jest/cargo test etc.)
        eps:         DBSCAN epsilon — cosine distance threshold. Lower = finer clusters.
                     Default 0.20 (tighter than log_cluster's 0.25) for test failures.
        min_samples: Minimum cluster size (singletons become outliers).
        max_lines:   Cap on lines to embed (bounds latency).

    Returns:
        TestClusterResult — always returns, never raises.

    Raises:
        RuntimeError if BR3_TEST_CLUSTER=off or Below offline.
        Callers must catch RuntimeError and fall back to raw lines.
    """
    if not _TEST_CLUSTER_ENABLED:
        raise RuntimeError("BR3_TEST_CLUSTER=off")

    if not lines:
        return TestClusterResult(skipped=True, skip_reason="no lines provided")

    from core.cluster.below.log_cluster import cluster_lines, ClusterResult
    from core.cluster.below.embed import BelowOfflineError

    # Track how many lines we'll actually process (after cap)
    lines_used = lines[:max_lines]

    # Delegate to the shared log_cluster library
    try:
        result: ClusterResult = cluster_lines(
            lines_used,
            eps=eps,
            min_samples=min_samples,
            max_lines=max_lines,
        )
    except BelowOfflineError as exc:
        raise RuntimeError(f"Below offline: {exc}") from exc

    # Convert ClusterResult to TestClusterResult (same shape, different type for clarity)
    test_clusters = [
        TestCluster(
            representative=c.representative,
            frequency=c.frequency,
            member_indices=c.member_indices,
        )
        for c in result.clusters
    ]
    test_outliers = [
        TestOutlier(index=o.index, text=o.text)
        for o in result.outliers
    ]

    return TestClusterResult(
        clusters=test_clusters,
        outliers=test_outliers,
        lines_processed=len(lines_used),
    )


def format_test_cluster(result: TestClusterResult, max_clusters: int = 10) -> str:
    """
    Format TestClusterResult as a compact summary for /root context injection.

    Output format mirrors format_cluster_summary() so /root and /dbg are consistent.

    Returns:
        Compact multi-line string. Empty string if result is empty/skipped.
    """
    if result.skipped or (not result.clusters and not result.outliers):
        return ""

    lines = ["### Test Failure Clusters"]

    for cluster in result.clusters[:max_clusters]:
        lines.append(f"  [{cluster.frequency}x] {cluster.representative[:120]}")

    if result.outliers:
        lines.append(f"\n### Unique Failures ({len(result.outliers)} outliers — always investigate)")
        for outlier in result.outliers:
            lines.append(f"  [1x] {outlier.text[:120]}")

    lines.append(
        f"\n({result.lines_processed} lines → {len(result.clusters)} clusters + "
        f"{len(result.outliers)} outliers)"
    )
    return "\n".join(lines)


def cluster_test_failures_safe(
    lines: list[str],
    **kwargs,
) -> Optional[str]:
    """
    Convenience wrapper: cluster and format in one call. Returns None on failure.

    Use this in ci-classifier.sh / shell scripts where fail-open is required.
    """
    try:
        result = cluster_test_failures(lines, **kwargs)
        return format_test_cluster(result) or None
    except RuntimeError:
        return None
    except Exception:  # noqa: BLE001 — fail-open
        return None
