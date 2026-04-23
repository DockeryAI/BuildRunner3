"""
tests/cluster/test_optimize_skill_judge.py

Phase 2: Judge-panel logic tests for /optimize-skill.

Verifies (pure-Python reference impl mirroring the skill's inline aggregation):
  - swap-order averaging is symmetric (judge scored twice with order flipped → mean is the same regardless of which call came first)
  - majority vote (2-of-3) on per-criterion pass/fail
  - 3-way distinct verdicts (pass / fail / UNKNOWN) flag for human spot-check
  - UNKNOWN counts as abstain (vote is 1-of-2 → defer to majority of remaining judges)
  - all-UNKNOWN flags for spot-check
  - per-criterion CoT reasoning is preserved across aggregation
"""

from __future__ import annotations

from collections import Counter

import pytest


# --- Reference implementation (would live inside /optimize-skill at runtime) ---


def swap_order_avg(score_v1_first: float, score_v2_first: float) -> float:
    """Average the two orderings of a swap-order pair."""
    return (score_v1_first + score_v2_first) / 2.0


def majority_vote(verdicts: list[str | bool]) -> tuple[str, bool]:
    """
    Majority vote across judges for a single criterion.

    Returns (verdict, needs_human_flag):
      verdict ∈ {"pass", "fail", "UNKNOWN"}
      needs_human_flag is True when no clear majority (3-way distinct, or all UNKNOWN, or tie after UNKNOWN abstentions).
    """
    normalized = [
        "UNKNOWN" if v == "UNKNOWN" else ("pass" if v is True or v == "pass" else "fail")
        for v in verdicts
    ]
    counts = Counter(normalized)

    # All UNKNOWN → flag
    if counts["UNKNOWN"] == len(normalized):
        return "UNKNOWN", True

    # 3 distinct verdicts (pass / fail / UNKNOWN) → flag
    if len({v for v in normalized}) == 3:
        return "UNKNOWN", True

    # UNKNOWN abstains; vote among remaining
    voting = [v for v in normalized if v != "UNKNOWN"]
    vc = Counter(voting)
    if not vc:
        return "UNKNOWN", True
    top, top_n = vc.most_common(1)[0]
    if len(voting) >= 2 and top_n == 1 and len(vc) == len(voting):
        # Even split among non-UNKNOWN → flag
        return "UNKNOWN", True
    return top, False


def aggregate_criterion(per_judge_scores: list[dict]) -> dict:
    """
    per_judge_scores: [
      {"judge": "sonnet", "pass": True/False/"UNKNOWN", "reasoning": "..."},
      ...
    ]
    """
    verdicts = [s["pass"] for s in per_judge_scores]
    verdict, flag = majority_vote(verdicts)
    return {
        "verdict": verdict,
        "needs_human_flag": flag,
        "per_judge": per_judge_scores,
    }


# --- Tests ---


def test_swap_order_symmetric_identical_scores():
    assert swap_order_avg(0.7, 0.7) == 0.7


def test_swap_order_symmetric_different_scores():
    # The function output is the SAME regardless of which arg is "v1-first"
    a = swap_order_avg(0.6, 0.8)
    b = swap_order_avg(0.8, 0.6)
    assert a == b == 0.7


def test_swap_order_zero_one_extremes():
    assert swap_order_avg(0.0, 1.0) == 0.5
    assert swap_order_avg(1.0, 0.0) == 0.5


def test_majority_vote_unanimous_pass():
    v, flag = majority_vote([True, True, True])
    assert v == "pass" and flag is False


def test_majority_vote_unanimous_fail():
    v, flag = majority_vote([False, False, False])
    assert v == "fail" and flag is False


def test_majority_vote_two_pass_one_fail():
    v, flag = majority_vote([True, True, False])
    assert v == "pass" and flag is False


def test_majority_vote_two_fail_one_pass():
    v, flag = majority_vote([False, False, True])
    assert v == "fail" and flag is False


def test_majority_vote_three_way_distinct_flags():
    v, flag = majority_vote([True, False, "UNKNOWN"])
    # pass + fail + UNKNOWN = 3 distinct → human flag
    assert flag is True
    assert v == "UNKNOWN"


def test_majority_vote_all_unknown_flags():
    v, flag = majority_vote(["UNKNOWN", "UNKNOWN", "UNKNOWN"])
    assert v == "UNKNOWN" and flag is True


def test_unknown_abstains_majority_among_rest():
    # 1 UNKNOWN + 2 pass → pass (UNKNOWN abstains)
    v, flag = majority_vote([True, True, "UNKNOWN"])
    assert v == "pass" and flag is False


def test_unknown_abstains_tie_flags():
    # 1 pass + 1 fail + 1 UNKNOWN → 1-1 tie among non-UNKNOWN, NOT 3 distinct (UNKNOWN counted)
    # By design above: 3 distinct → flag. This case is the same.
    v, flag = majority_vote([True, False, "UNKNOWN"])
    assert flag is True


def test_aggregate_criterion_preserves_per_judge_reasoning():
    per_judge = [
        {"judge": "sonnet", "pass": True, "reasoning": "matches criterion exactly"},
        {"judge": "codex", "pass": True, "reasoning": "verified output shape"},
        {"judge": "gemini", "pass": False, "reasoning": "missing dark-theme default"},
    ]
    agg = aggregate_criterion(per_judge)
    assert agg["verdict"] == "pass"
    assert agg["needs_human_flag"] is False
    assert agg["per_judge"] == per_judge
    # CoT reasoning preserved per-judge
    assert agg["per_judge"][2]["reasoning"] == "missing dark-theme default"


def test_swap_order_averaging_combined_with_majority_vote():
    # Sonnet scored a pair twice with flipped order: 0.6 v1-first, 0.8 v2-first → 0.7
    sonnet_score = swap_order_avg(0.6, 0.8)
    # Threshold = 0.5 → pass
    sonnet_pass = sonnet_score >= 0.5
    # Codex scored similarly: 0.55 + 0.65 → 0.6 → pass
    codex_pass = swap_order_avg(0.55, 0.65) >= 0.5
    # Gemini abstained
    gemini_pass = "UNKNOWN"

    v, flag = majority_vote([sonnet_pass, codex_pass, gemini_pass])
    assert v == "pass" and flag is False


@pytest.mark.parametrize(
    "verdicts,expected_v,expected_flag",
    [
        ([True, True, True], "pass", False),
        ([False, False, False], "fail", False),
        ([True, True, False], "pass", False),
        ([False, False, True], "fail", False),
        (["UNKNOWN", True, True], "pass", False),
        (["UNKNOWN", False, False], "fail", False),
        ([True, False, "UNKNOWN"], "UNKNOWN", True),
        (["UNKNOWN", "UNKNOWN", "UNKNOWN"], "UNKNOWN", True),
    ],
)
def test_majority_vote_table(verdicts, expected_v, expected_flag):
    v, flag = majority_vote(verdicts)
    assert v == expected_v
    assert flag == expected_flag
