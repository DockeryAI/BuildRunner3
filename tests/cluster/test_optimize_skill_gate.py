"""
tests/cluster/test_optimize_skill_gate.py

Phase 3: Decision-gate + plateau + hard-cap tests for /optimize-skill.

The decision gate keeps v2 only when ALL FOUR axes hold:
  score_gain      >= 0.05
  diversity_delta >= -0.20
  cost_delta      <= +0.30
  length_delta    <= +0.50

This file exhaustively tests the 16-cell truth table (each axis above/below threshold)
plus plateau detection (2 consecutive <5% gains) and hard-cap (max-iter).
"""

from __future__ import annotations

from itertools import product

import pytest


# --- Reference implementation ---


def decision_gate(
    score_gain: float,
    diversity_delta: float,
    cost_delta: float,
    length_delta: float,
) -> tuple[bool, list[str]]:
    """
    Returns (keep_v2, reasons). reasons lists which axes failed when keep_v2 is False.
    """
    failed: list[str] = []
    if score_gain < 0.05:
        failed.append(f"score_gain {score_gain:.3f} < 0.05")
    if diversity_delta < -0.20:
        failed.append(f"diversity_delta {diversity_delta:.3f} < -0.20 (collapse)")
    if cost_delta > 0.30:
        failed.append(f"cost_delta {cost_delta:.3f} > 0.30")
    if length_delta > 0.50:
        failed.append(f"length_delta {length_delta:.3f} > 0.50")
    return (len(failed) == 0, failed)


def plateau_triggered(consecutive_gains: list[float], threshold: float = 0.05) -> bool:
    """Returns True if the last 2 consecutive gains are both < threshold."""
    if len(consecutive_gains) < 2:
        return False
    return consecutive_gains[-1] < threshold and consecutive_gains[-2] < threshold


def hard_cap_reached(iter_count: int, max_iter: int = 3) -> bool:
    return iter_count >= max_iter


# --- 16-cell truth table on the gate ---


@pytest.mark.parametrize(
    "score_above,div_above,cost_below,len_below",
    list(product([True, False], repeat=4)),
)
def test_gate_truth_table_16_cells(score_above, div_above, cost_below, len_below):
    """All 16 combinations of (score, diversity, cost, length) above/below threshold."""
    score = 0.10 if score_above else 0.02
    div = -0.10 if div_above else -0.30
    cost = 0.20 if cost_below else 0.40
    length = 0.30 if len_below else 0.60

    keep, failed = decision_gate(score, div, cost, length)
    expected_keep = all([score_above, div_above, cost_below, len_below])
    assert keep is expected_keep, (
        f"axes (score={score_above}, div={div_above}, cost={cost_below}, len={len_below}) "
        f"expected keep={expected_keep}, got {keep}; failed={failed}"
    )


def test_gate_pass_all_four():
    keep, failed = decision_gate(0.08, 0.05, 0.10, 0.20)
    assert keep is True
    assert failed == []


def test_gate_fail_score_only():
    keep, failed = decision_gate(0.03, 0.05, 0.10, 0.20)
    assert keep is False
    assert any("score_gain" in f for f in failed)


def test_gate_fail_diversity_collapse():
    keep, failed = decision_gate(0.10, -0.30, 0.10, 0.20)
    assert keep is False
    assert any("diversity_delta" in f for f in failed)


def test_gate_fail_cost_blowup():
    keep, failed = decision_gate(0.10, 0.05, 0.50, 0.20)
    assert keep is False
    assert any("cost_delta" in f for f in failed)


def test_gate_fail_length_blowup():
    keep, failed = decision_gate(0.10, 0.05, 0.10, 0.80)
    assert keep is False
    assert any("length_delta" in f for f in failed)


def test_gate_fail_multiple_axes():
    keep, failed = decision_gate(0.02, -0.30, 0.50, 0.80)
    assert keep is False
    assert len(failed) == 4


def test_gate_score_exactly_at_threshold():
    # 0.05 is the boundary — gain < 0.05 fails, == 0.05 passes
    keep, _ = decision_gate(0.05, 0.0, 0.0, 0.0)
    assert keep is True


def test_gate_diversity_exactly_at_threshold():
    keep, _ = decision_gate(0.10, -0.20, 0.0, 0.0)
    assert keep is True


def test_gate_cost_exactly_at_threshold():
    keep, _ = decision_gate(0.10, 0.0, 0.30, 0.0)
    assert keep is True


def test_gate_length_exactly_at_threshold():
    keep, _ = decision_gate(0.10, 0.0, 0.0, 0.50)
    assert keep is True


# --- Plateau detection ---


def test_plateau_not_triggered_one_iter():
    assert plateau_triggered([0.01]) is False


def test_plateau_not_triggered_one_low_one_high():
    assert plateau_triggered([0.01, 0.10]) is False
    assert plateau_triggered([0.10, 0.01]) is False


def test_plateau_triggered_two_consecutive_low():
    assert plateau_triggered([0.10, 0.04, 0.03]) is True


def test_plateau_not_triggered_three_iters_one_low():
    assert plateau_triggered([0.10, 0.10, 0.04]) is False


def test_plateau_uses_last_two_only():
    # Even if early gains were low, only the last two matter for stopping
    assert plateau_triggered([0.01, 0.02, 0.10, 0.10]) is False


# --- Hard cap ---


def test_hard_cap_default_three():
    assert hard_cap_reached(2) is False
    assert hard_cap_reached(3) is True
    assert hard_cap_reached(4) is True


def test_hard_cap_configurable():
    assert hard_cap_reached(4, max_iter=5) is False
    assert hard_cap_reached(5, max_iter=5) is True


def test_hard_cap_zero_iter():
    assert hard_cap_reached(0) is False
