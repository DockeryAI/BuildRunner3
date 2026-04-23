"""
tests/cluster/test_optimize_skill_diversity.py

Phase 2: Diversity-metric tests for /optimize-skill.

Verifies the diversity metric used by the skill (token-shingle Jaccard, optionally combined with embedding entropy):
  - identical outputs → 0.0 (no diversity)
  - fully-distinct outputs → close to 1.0 (high diversity)
  - known-distance pairs match expected Jaccard values
  - empty corpus / single output → 0.0 (no pairs to compare)
  - metric is symmetric (j(a,b) == j(b,a))
"""

from __future__ import annotations

from itertools import combinations

import pytest


# --- Reference implementation ---


def shingle(text: str, k: int = 3) -> set[str]:
    """k-shingle of whitespace-tokenized text."""
    tokens = text.split()
    if len(tokens) < k:
        return {" ".join(tokens)} if tokens else set()
    return {" ".join(tokens[i : i + k]) for i in range(len(tokens) - k + 1)}


def jaccard(a: set, b: set) -> float:
    if not a and not b:
        return 1.0  # both empty = identical
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def diversity(outputs: list[str], k: int = 3) -> float:
    """
    Diversity = 1 - mean(pairwise jaccard) across all output pairs.
    Range: [0.0, 1.0]. 0 = identical corpus, 1 = no shared k-shingles.
    """
    if len(outputs) < 2:
        return 0.0
    shingles = [shingle(o, k) for o in outputs]
    pairs = list(combinations(range(len(outputs)), 2))
    if not pairs:
        return 0.0
    mean_j = sum(jaccard(shingles[i], shingles[j]) for i, j in pairs) / len(pairs)
    return 1.0 - mean_j


# --- Tests ---


def test_identical_outputs_zero_diversity():
    outs = ["the quick brown fox jumps over the lazy dog"] * 5
    assert diversity(outs) == 0.0


def test_fully_distinct_outputs_high_diversity():
    outs = [
        "alpha beta gamma delta epsilon zeta",
        "one two three four five six seven",
        "red orange yellow green blue indigo violet",
        "spring summer autumn winter equinox solstice",
    ]
    d = diversity(outs)
    assert d > 0.95, f"expected near-1 diversity for distinct outputs, got {d}"


def test_known_jaccard_pair():
    a = shingle("the quick brown fox jumps")
    b = shingle("the quick brown fox runs")
    # 5 tokens each, k=3 → shingles: {"the quick brown","quick brown fox","brown fox X"}
    # Overlap on first two → intersection = 2, union = 4 → 0.5
    assert jaccard(a, b) == pytest.approx(0.5, abs=0.01)


def test_empty_corpus_zero_diversity():
    assert diversity([]) == 0.0
    assert diversity(["only one"]) == 0.0


def test_jaccard_symmetric():
    a = shingle("the quick brown fox jumps over")
    b = shingle("the lazy dog walks under fences")
    assert jaccard(a, b) == jaccard(b, a)


def test_jaccard_both_empty_treated_as_identical():
    assert jaccard(set(), set()) == 1.0


def test_jaccard_one_empty_zero():
    a = shingle("hello world example")
    assert jaccard(a, set()) == 0.0
    assert jaccard(set(), a) == 0.0


def test_diversity_partial_overlap_intermediate():
    # Two outputs share half their shingles → diversity ≈ 0.5
    outs = [
        "alpha beta gamma delta epsilon zeta",
        "alpha beta gamma omega psi chi",
    ]
    d = diversity(outs)
    # Shingles: {"alpha beta gamma","beta gamma delta","gamma delta epsilon","delta epsilon zeta"} vs
    #          {"alpha beta gamma","beta gamma omega","gamma omega psi","omega psi chi"}
    # Intersection: 1 shingle. Union: 7. Jaccard = 1/7 ≈ 0.143. Diversity = 1 - 0.143 ≈ 0.857.
    assert 0.80 < d < 0.90


def test_diversity_two_identical_outputs():
    outs = ["alpha beta gamma delta", "alpha beta gamma delta"]
    assert diversity(outs) == 0.0


def test_shingle_short_text():
    # Fewer tokens than k → return single-shingle of whatever tokens exist
    s = shingle("hi", k=3)
    assert s == {"hi"}


def test_diversity_in_unit_interval():
    import random

    random.seed(42)
    words = ["foo", "bar", "baz", "qux", "quux", "corge", "grault"]
    outs = [" ".join(random.choices(words, k=8)) for _ in range(10)]
    d = diversity(outs)
    assert 0.0 <= d <= 1.0
