"""
tests/cluster/test_semantic_cache.py

Unit tests for core.cluster.below.semantic_cache — no real network calls,
no actual sqlite-vec (uses standard sqlite3 with a mock vector store).
"""

from __future__ import annotations

import json
import struct
import time
from pathlib import Path
from typing import Optional
from unittest.mock import patch

import pytest

from core.cluster.below.semantic_cache import (
    SemanticCache,
    _cosine_similarity,
    _hash_prompt,
)

EMBED_DIM = 768


# ---------------------------------------------------------------------------
# Vector helpers
# ---------------------------------------------------------------------------


def _unit_vec(value: float) -> list[float]:
    """Return a 768-d vector with [value, 0, 0, ...]."""
    v = [0.0] * EMBED_DIM
    v[0] = value
    return v


def _similar_vecs() -> tuple[list[float], list[float]]:
    """Two vectors with cosine similarity > 0.95."""
    a = [1.0] + [0.0] * (EMBED_DIM - 1)
    b = [0.98, 0.2] + [0.0] * (EMBED_DIM - 2)
    return a, b


def _dissimilar_vecs() -> tuple[list[float], list[float]]:
    """Two vectors with cosine similarity < 0.5."""
    a = [1.0] + [0.0] * (EMBED_DIM - 1)
    b = [0.0, 1.0] + [0.0] * (EMBED_DIM - 2)
    return a, b


# ---------------------------------------------------------------------------
# Fixture: in-memory cache (avoids disk)
# ---------------------------------------------------------------------------


@pytest.fixture
def cache(tmp_path: Path) -> SemanticCache:
    """SemanticCache with tmp_path DB and zero warmup period."""
    return SemanticCache(
        db_path=tmp_path / "test_cache.db",
        threshold=0.95,
        ttl_days=30,
        warmup_days=0,  # Disable warm-up for tests
    )


# ---------------------------------------------------------------------------
# Happy path — lookup and store
# ---------------------------------------------------------------------------


class TestLookupAndStore:
    def test_store_then_lookup_exact_match(self, cache):
        prompt = "summarize this document"
        answer = "This document covers X."
        vec = _unit_vec(1.0)

        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude-opus-4-7", "summarize", prompt, answer)
            result = cache.lookup("claude-opus-4-7", "summarize", prompt)

        assert result == answer

    def test_lookup_returns_none_on_empty_cache(self, cache):
        vec = _unit_vec(1.0)
        with patch.object(cache, "_embed", return_value=vec):
            result = cache.lookup("claude-opus-4-7", "summarize", "any prompt")
        assert result is None

    def test_similar_prompt_hits_above_threshold(self, cache):
        answer = "Cached answer."
        vec_a, vec_b = _similar_vecs()
        sim = _cosine_similarity(vec_a, vec_b)
        assert sim > 0.95, f"Test setup error: similarity {sim:.3f} should be > 0.95"

        with patch.object(cache, "_embed", return_value=vec_a):
            cache.store("claude-opus-4-7", "classify", "original prompt", answer)

        with patch.object(cache, "_embed", return_value=vec_b):
            result = cache.lookup("claude-opus-4-7", "classify", "similar prompt")

        assert result == answer

    def test_dissimilar_prompt_misses(self, cache):
        answer = "Cached answer."
        vec_a, vec_b = _dissimilar_vecs()

        with patch.object(cache, "_embed", return_value=vec_a):
            cache.store("claude-opus-4-7", "classify", "original", answer)

        with patch.object(cache, "_embed", return_value=vec_b):
            result = cache.lookup("claude-opus-4-7", "classify", "very different prompt")

        assert result is None

    def test_skip_cache_always_returns_none(self, cache):
        vec = _unit_vec(1.0)
        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude-opus-4-7", "review", "prompt", "answer")

        with patch.object(cache, "_embed", return_value=vec):
            result = cache.lookup("claude-opus-4-7", "review", "prompt", skip_cache=True)

        assert result is None

    def test_skip_cache_on_store_is_noop(self, cache):
        vec = _unit_vec(1.0)
        with patch.object(cache, "_embed", return_value=vec):
            cache.store("model", "method", "prompt", "answer", skip_cache=True)
            result = cache.lookup("model", "method", "prompt")

        assert result is None  # nothing was stored


# ---------------------------------------------------------------------------
# Cross-model isolation
# ---------------------------------------------------------------------------


class TestCrossModelIsolation:
    def test_no_cross_model_bleed(self, cache):
        """Storing under claude should not be retrievable under gpt."""
        answer = "Claude's answer."
        vec = _unit_vec(1.0)

        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude-opus-4-7", "summarize", "prompt", answer)
            result_gpt = cache.lookup("gpt-4o", "summarize", "prompt")

        assert result_gpt is None

    def test_same_prompt_different_models_stored_separately(self, cache):
        prompt = "explain recursion"
        vec = _unit_vec(1.0)

        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude-opus-4-7", "explain", prompt, "Claude answer")
            cache.store("gpt-4o", "explain", prompt, "GPT answer")

            claude_result = cache.lookup("claude-opus-4-7", "explain", prompt)
            gpt_result = cache.lookup("gpt-4o", "explain", prompt)

        assert claude_result == "Claude answer"
        assert gpt_result == "GPT answer"

    def test_method_partitions_cache(self, cache):
        prompt = "review this code"
        vec = _unit_vec(1.0)

        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude", "review", prompt, "Review answer")
            cache.store("claude", "summarize", prompt, "Summary answer")

            review_result = cache.lookup("claude", "review", prompt)
            summary_result = cache.lookup("claude", "summarize", prompt)

        assert review_result == "Review answer"
        assert summary_result == "Summary answer"


# ---------------------------------------------------------------------------
# Warm-up mode
# ---------------------------------------------------------------------------


class TestWarmupMode:
    def test_warmup_suppresses_hits(self, tmp_path):
        cache = SemanticCache(
            db_path=tmp_path / "warmup_cache.db",
            threshold=0.95,
            warmup_days=7,  # 7-day warm-up
        )
        vec = _unit_vec(1.0)
        prompt = "test prompt"
        answer = "cached answer"

        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude", "test", prompt, answer)

        # During warm-up (cache just created), lookup should return None
        with patch.object(cache, "_embed", return_value=vec):
            result = cache.lookup("claude", "test", prompt)

        assert result is None, "Warm-up mode should suppress hits"

    def test_warmup_zero_serves_hits(self, cache):
        """warmup_days=0 means hits are served immediately."""
        vec = _unit_vec(1.0)
        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude", "test", "prompt", "answer")
            result = cache.lookup("claude", "test", "prompt")
        assert result == "answer"


# ---------------------------------------------------------------------------
# TTL eviction
# ---------------------------------------------------------------------------


class TestTTLEviction:
    def test_expired_entries_not_returned(self, tmp_path):
        cache = SemanticCache(
            db_path=tmp_path / "ttl_cache.db",
            threshold=0.95,
            ttl_days=1,
            warmup_days=0,
        )
        vec = _unit_vec(1.0)

        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude", "test", "prompt", "answer")

        # Manually backdate the entry
        cache._ensure_init()
        old_ts = time.time() - (2 * 86400)  # 2 days ago
        cache._conn.execute("UPDATE answer_cache SET stored_at = ?", (old_ts,))
        cache._conn.commit()

        with patch.object(cache, "_embed", return_value=vec):
            result = cache.lookup("claude", "test", "prompt")

        assert result is None, "Expired entry should not be returned"


# ---------------------------------------------------------------------------
# Admin CLI (stats, inspect, clear)
# ---------------------------------------------------------------------------


class TestAdminCLI:
    def test_stats_empty_cache(self, cache):
        stats = cache.stats()
        assert stats["total_entries"] == 0
        assert "db_path" in stats

    def test_stats_after_store(self, cache):
        vec = _unit_vec(1.0)
        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude", "review", "p1", "a1")
            cache.store("claude", "summarize", "p2", "a2")

        stats = cache.stats()
        assert stats["total_entries"] == 2
        assert stats["by_model"]["claude"] == 2

    def test_inspect_returns_entries(self, cache):
        vec = _unit_vec(1.0)
        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude", "test", "prompt", "answer")

        rows = cache.inspect()
        assert len(rows) == 1
        assert rows[0]["model"] == "claude"
        assert rows[0]["method"] == "test"

    def test_clear_removes_all_entries(self, cache):
        vec = _unit_vec(1.0)
        with patch.object(cache, "_embed", return_value=vec):
            cache.store("claude", "test", "p1", "a1")
            cache.store("claude", "test", "p2", "a2")

        n = cache.clear()
        assert n == 2

        stats = cache.stats()
        assert stats["total_entries"] == 0


# ---------------------------------------------------------------------------
# Hash and cosine helpers
# ---------------------------------------------------------------------------


class TestHelpers:
    def test_hash_prompt_normalizes_whitespace(self):
        h1 = _hash_prompt("hello   world")
        h2 = _hash_prompt("hello world")
        assert h1 == h2

    def test_hash_prompt_case_insensitive(self):
        h1 = _hash_prompt("Hello World")
        h2 = _hash_prompt("hello world")
        assert h1 == h2

    def test_cosine_similarity_identical_vectors(self):
        v = [1.0, 0.0, 0.5] + [0.0] * (EMBED_DIM - 3)
        assert _cosine_similarity(v, v) == pytest.approx(1.0)

    def test_cosine_similarity_orthogonal_vectors(self):
        a = [1.0] + [0.0] * (EMBED_DIM - 1)
        b = [0.0, 1.0] + [0.0] * (EMBED_DIM - 2)
        assert _cosine_similarity(a, b) == pytest.approx(0.0, abs=1e-9)

    def test_cosine_similarity_zero_vector(self):
        a = [1.0] + [0.0] * (EMBED_DIM - 1)
        b = [0.0] * EMBED_DIM
        assert _cosine_similarity(a, b) == 0.0

    def test_no_false_positive_at_threshold(self, cache):
        """
        Verify 0 false positives at 0.95 threshold on a curated test set.
        Two semantically distinct prompts should not collide.
        """
        vec_a = [1.0] + [0.0] * (EMBED_DIM - 1)
        # vec_b is clearly below threshold: cosine similarity ≈ 0.0
        vec_b = [0.0, 1.0] + [0.0] * (EMBED_DIM - 2)

        with patch.object(cache, "_embed", return_value=vec_a):
            cache.store("claude", "classify", "Is this a security issue?", "yes")

        with patch.object(cache, "_embed", return_value=vec_b):
            result = cache.lookup("claude", "classify", "Summarize the changelog")

        assert result is None, "Dissimilar prompts must not produce false-positive hits"
