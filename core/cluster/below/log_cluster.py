"""
log_cluster.py — Embedding + DBSCAN log clustering via Below.

Groups a list of log lines (or any text strings) into semantic clusters
using DBSCAN on nomic-embed-text embeddings from Below.

Callers: /dbg, /sdb, /diag, /device, /query skill steps (Phase 7);
         CI test failure clustering (Phase 8).

Return shape:
    ClusterResult.clusters — list of Cluster (representative, frequency, member_indices)
    ClusterResult.outliers — list of Outlier (DBSCAN label -1; singletons never dropped)

Fail-open: if Below/embed fails, raises BelowOfflineError — callers catch and
fall through to the unmodified pipeline. Rollback: BR3_LOG_CLUSTER=off.

Usage:
    from core.cluster.below.log_cluster import cluster_lines

    result = cluster_lines(lines, eps=0.3, min_samples=2)
    for cluster in result.clusters:
        print(f"[{cluster.frequency}x] {cluster.representative}")
    for outlier in result.outliers:
        print(f"[singleton] {outlier.text}")
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from typing import Optional

from core.cluster.below.embed import BelowOfflineError, embed_batch

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Config
# ---------------------------------------------------------------------------

# DBSCAN defaults tuned on BR3 log corpus (cosine distance on 768-d vectors)
DEFAULT_EPS: float = 0.25        # cosine distance threshold; smaller = tighter clusters
DEFAULT_MIN_SAMPLES: int = 2     # minimum cluster size (singletons → outliers)
DEFAULT_MAX_LINES: int = 500     # cap before embedding to limit latency

# Rollback flag
_CLUSTER_ENABLED = os.environ.get("BR3_LOG_CLUSTER", "on").lower() != "off"


# ---------------------------------------------------------------------------
# Data model
# ---------------------------------------------------------------------------


@dataclass
class Cluster:
    """A group of semantically similar log lines."""

    representative: str           # Most-central member text
    frequency: int                # Number of members in this cluster
    member_indices: list[int]     # Indices into original lines list
    centroid_idx: int             # Index of the representative member


@dataclass
class Outlier:
    """A singleton log line that DBSCAN did not assign to any cluster (label -1)."""

    index: int    # Index into original lines list
    text: str     # The log line text


@dataclass
class ClusterResult:
    """Full output of cluster_lines()."""

    clusters: list[Cluster] = field(default_factory=list)
    outliers: list[Outlier] = field(default_factory=list)
    total_lines: int = 0
    lines_clustered: int = 0
    lines_outlier: int = 0


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def cluster_lines(
    lines: list[str],
    *,
    eps: float = DEFAULT_EPS,
    min_samples: int = DEFAULT_MIN_SAMPLES,
    max_lines: int = DEFAULT_MAX_LINES,
) -> ClusterResult:
    """
    Cluster a list of log lines by semantic similarity using DBSCAN.

    Args:
        lines:       Input log lines. Duplicates allowed; empty strings skipped.
        eps:         DBSCAN neighbourhood radius (cosine distance, 0.0–2.0).
        min_samples: Minimum members for a group to be a cluster (else outliers).
        max_lines:   Hard cap on input length to bound embedding latency.

    Returns:
        ClusterResult with .clusters (groups) and .outliers (singletons/noise).

    Raises:
        BelowOfflineError: Below embed endpoint unreachable (callers fail-open).
        ValueError:        lines is empty.
        RuntimeError:      BR3_LOG_CLUSTER=off (callers should check this flag).

    Note:
        Rollback: set BR3_LOG_CLUSTER=off in the environment — this function
        raises RuntimeError immediately so callers fall through to the plain pipeline.
    """
    if not _CLUSTER_ENABLED:
        raise RuntimeError("BR3_LOG_CLUSTER=off — clustering disabled")

    if not lines:
        raise ValueError("cluster_lines requires at least one line")

    # Deduplicate while tracking original indices
    non_empty = [(i, ln) for i, ln in enumerate(lines) if ln.strip()]
    if not non_empty:
        return ClusterResult(total_lines=len(lines))

    # Cap input length
    if len(non_empty) > max_lines:
        logger.info("cluster_lines: capping %d lines to %d", len(non_empty), max_lines)
        non_empty = non_empty[:max_lines]

    indices = [i for i, _ in non_empty]
    texts = [ln for _, ln in non_empty]

    # Embed (raises BelowOfflineError on network failure — caller catches)
    vectors = embed_batch(texts)

    # DBSCAN
    labels = _dbscan(vectors, eps=eps, min_samples=min_samples)

    # Build result
    return _build_result(texts, indices, labels)


# ---------------------------------------------------------------------------
# DBSCAN implementation (scikit-learn with cosine metric)
# ---------------------------------------------------------------------------


def _dbscan(
    vectors: list[list[float]],
    eps: float,
    min_samples: int,
) -> list[int]:
    """
    Run DBSCAN and return per-vector cluster labels (-1 = outlier).

    Uses scikit-learn with cosine metric via pairwise_distances preprocessing.
    Cosine distance = 1 - cosine_similarity, so eps=0.25 means vectors within
    75% cosine similarity are neighbours.
    """
    try:
        import numpy as np
        from sklearn.cluster import DBSCAN
        from sklearn.metrics.pairwise import cosine_distances

        X = np.array(vectors, dtype=float)
        dist_matrix = cosine_distances(X)

        # Clip to [0, 2] (numerical noise can produce tiny negatives)
        dist_matrix = dist_matrix.clip(0.0, 2.0)

        db = DBSCAN(eps=eps, min_samples=min_samples, metric="precomputed")
        labels: list[int] = db.fit_predict(dist_matrix).tolist()
        return labels

    except ImportError as exc:
        raise ImportError(
            "scikit-learn is required for DBSCAN clustering. "
            "Install via: pip install scikit-learn>=1.4"
        ) from exc


# ---------------------------------------------------------------------------
# Result builder
# ---------------------------------------------------------------------------


def _build_result(
    texts: list[str],
    original_indices: list[int],
    labels: list[int],
) -> ClusterResult:
    """
    Group texts by DBSCAN label, select cluster representatives, collect outliers.

    Representative selection: the member with the shortest text that still
    shares at least the first word with the majority of cluster members (proxy
    for "most central / most shared prefix"). Falls back to the shortest member.
    """
    from collections import defaultdict

    groups: dict[int, list[int]] = defaultdict(list)
    for local_idx, label in enumerate(labels):
        groups[label].append(local_idx)

    clusters: list[Cluster] = []
    outliers: list[Outlier] = []

    for label, local_indices in sorted(groups.items()):
        member_texts = [texts[i] for i in local_indices]
        orig_indices = [original_indices[i] for i in local_indices]

        if label == -1:
            # DBSCAN outliers — expose all, never drop
            for i, (oi, text) in enumerate(zip(orig_indices, member_texts)):
                outliers.append(Outlier(index=oi, text=text))
        else:
            rep_idx, rep_text = _select_representative(member_texts, local_indices)
            clusters.append(
                Cluster(
                    representative=rep_text,
                    frequency=len(local_indices),
                    member_indices=orig_indices,
                    centroid_idx=original_indices[rep_idx],
                )
            )

    clustered = sum(c.frequency for c in clusters)
    return ClusterResult(
        clusters=clusters,
        outliers=outliers,
        total_lines=len(texts),
        lines_clustered=clustered,
        lines_outlier=len(outliers),
    )


def _select_representative(
    member_texts: list[str],
    local_indices: list[int],
) -> tuple[int, str]:
    """
    Select the representative for a cluster.

    Strategy: longest common prefix heuristic — prefer the member whose
    leading token appears most frequently across all members (most "central").
    Falls back to the shortest member if heuristic produces no winner.
    """
    if len(member_texts) == 1:
        return local_indices[0], member_texts[0]

    # Count leading token frequency
    from collections import Counter

    leading_tokens = [t.split()[0] if t.split() else "" for t in member_texts]
    most_common_token, _ = Counter(leading_tokens).most_common(1)[0]

    # Among members sharing the leading token, pick the shortest
    candidates = [
        (i, t)
        for i, t in zip(local_indices, member_texts)
        if t.split()[:1] == [most_common_token]
    ] or list(zip(local_indices, member_texts))

    best_local_idx, best_text = min(candidates, key=lambda x: len(x[1]))
    return best_local_idx, best_text


# ---------------------------------------------------------------------------
# Convenience: cluster and format for prompt injection
# ---------------------------------------------------------------------------


def format_cluster_summary(result: ClusterResult, max_clusters: int = 10) -> str:
    """
    Format a ClusterResult as a compact prompt-injectable summary.

    Preserves all outliers (never truncated). Clusters are sorted by frequency
    descending and capped at max_clusters.

    Returns a markdown-formatted string:
        ## Clustered patterns (N groups, M singletons)
        - [5x] ERROR connection refused to db host
        - [3x] WARNING retry attempt N of 3
        ...
        ## Singletons (outliers)
        - CRITICAL disk full on /dev/sda1
    """
    parts = [
        f"## Clustered patterns ({len(result.clusters)} groups, "
        f"{len(result.outliers)} singletons)"
    ]

    sorted_clusters = sorted(result.clusters, key=lambda c: c.frequency, reverse=True)
    for cluster in sorted_clusters[:max_clusters]:
        parts.append(f"- [{cluster.frequency}x] {cluster.representative}")

    if result.outliers:
        parts.append("\n## Singletons (outliers — never dropped)")
        for outlier in result.outliers:
            parts.append(f"- {outlier.text}")

    return "\n".join(parts)
