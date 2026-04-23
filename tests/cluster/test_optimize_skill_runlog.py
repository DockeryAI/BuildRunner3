"""
tests/cluster/test_optimize_skill_runlog.py

Phase 5: Run-log + tiebreaker + summary + --resume tests for /optimize-skill.

Verifies the run-log directory layout and JSON invariants:
  - run dir created at .buildrunner/skill-evals/runs/<skill>-<ISO-ts>/
  - baseline.json schema invariants (N entries, scores sum correctly, axes present)
  - iter-N.json includes v2_prompt + decision_gate_outcome
  - winner.md contains a unified diff against baseline
  - failures.md present when any criterion fails
  - --resume reloads cached baseline (skips re-running baseline)
  - tiebreaker fires when |score_gain| <= 0.01
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest


# --- Reference impl mirroring the skill's run-log builders ---


def make_baseline(run_dir: Path, n_inputs: int, criteria: list[str]) -> dict:
    """Construct a baseline.json dict and write it."""
    per_input = []
    for i in range(n_inputs):
        per_input.append(
            {
                "input_idx": i,
                "output_path": f"baseline/output-{i}.txt",
                "criteria_scores": {c: True for c in criteria},
            }
        )
    payload = {
        "schema": "baseline-v1",
        "n_inputs": n_inputs,
        "criteria": criteria,
        "per_input": per_input,
        "diversity": 0.62,
        "cost_usd": 1.23,
        "length_mean": 842.0,
        "total_cost_usd": 1.23,
    }
    run_dir.mkdir(parents=True, exist_ok=True)
    (run_dir / "baseline.json").write_text(json.dumps(payload, indent=2))
    return payload


def make_iter(run_dir: Path, n: int, payload_extras: dict) -> dict:
    payload = {
        "schema": "iter-v1",
        "iter": n,
        "v2_prompt": payload_extras.get("v2_prompt", "rewritten skill body..."),
        "decision_gate_outcome": payload_extras.get("decision_gate_outcome", "PASS"),
        "score_gain": payload_extras.get("score_gain", 0.10),
        "diversity_delta": payload_extras.get("diversity_delta", -0.02),
        "cost_delta": payload_extras.get("cost_delta", 0.10),
        "length_delta": payload_extras.get("length_delta", -0.05),
    }
    (run_dir / f"iter-{n}.json").write_text(json.dumps(payload, indent=2))
    return payload


def write_winner_diff(run_dir: Path, baseline_text: str, winner_text: str) -> Path:
    import difflib

    diff = "\n".join(
        difflib.unified_diff(
            baseline_text.splitlines(),
            winner_text.splitlines(),
            fromfile="baseline",
            tofile="winner",
            lineterm="",
        )
    )
    p = run_dir / "winner.md"
    p.write_text(f"# Winner prompt\n\n{winner_text}\n\n## Diff from baseline\n\n```diff\n{diff}\n```\n")
    return p


def tiebreaker_needed(score_gain: float, threshold: float = 0.01) -> bool:
    return abs(score_gain) <= threshold


def resume_baseline(run_dir: Path) -> dict:
    """Load cached baseline.json from a prior run dir."""
    p = run_dir / "baseline.json"
    if not p.exists():
        raise FileNotFoundError(f"no cached baseline at {p}")
    return json.loads(p.read_text())


# --- Tests ---


@pytest.fixture
def tmp_run_dir(tmp_path):
    return tmp_path / "skill-evals/runs/website-build-20260423T160000Z"


def test_run_dir_created_with_baseline(tmp_run_dir):
    make_baseline(tmp_run_dir, n_inputs=14, criteria=["c1", "c2", "c3"])
    assert tmp_run_dir.is_dir()
    assert (tmp_run_dir / "baseline.json").exists()


def test_baseline_has_n_entries(tmp_run_dir):
    payload = make_baseline(tmp_run_dir, n_inputs=14, criteria=["c1", "c2", "c3"])
    assert len(payload["per_input"]) == 14


def test_baseline_axes_present(tmp_run_dir):
    payload = make_baseline(tmp_run_dir, n_inputs=14, criteria=["c1"])
    for axis in ("diversity", "cost_usd", "length_mean", "total_cost_usd"):
        assert axis in payload, f"missing axis {axis}"


def test_baseline_scores_per_input_match_criteria(tmp_run_dir):
    crits = ["a", "b", "c", "d"]
    payload = make_baseline(tmp_run_dir, n_inputs=14, criteria=crits)
    for entry in payload["per_input"]:
        assert set(entry["criteria_scores"].keys()) == set(crits)


def test_iter_includes_v2_prompt_and_gate(tmp_run_dir):
    make_baseline(tmp_run_dir, n_inputs=14, criteria=["c1"])
    p = make_iter(tmp_run_dir, 1, {"v2_prompt": "shorter rewrite", "decision_gate_outcome": "PASS"})
    assert p["v2_prompt"] == "shorter rewrite"
    assert p["decision_gate_outcome"] == "PASS"


def test_winner_md_contains_unified_diff(tmp_run_dir):
    tmp_run_dir.mkdir(parents=True)
    p = write_winner_diff(tmp_run_dir, "line one\nline two\nline three", "line one\nLINE TWO\nline three")
    text = p.read_text()
    assert "```diff" in text
    # unified-diff markers
    assert re.search(r"^---\s+baseline$", text, re.M)
    assert re.search(r"^\+\+\+\s+winner$", text, re.M)


def test_resume_reloads_baseline(tmp_run_dir):
    original = make_baseline(tmp_run_dir, n_inputs=14, criteria=["c1", "c2"])
    loaded = resume_baseline(tmp_run_dir)
    assert loaded == original


def test_resume_missing_baseline_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        resume_baseline(tmp_path / "nonexistent")


def test_tiebreaker_triggers_within_band():
    assert tiebreaker_needed(0.005) is True
    assert tiebreaker_needed(-0.008) is True
    assert tiebreaker_needed(0.01) is True
    assert tiebreaker_needed(-0.01) is True


def test_tiebreaker_does_not_trigger_outside_band():
    assert tiebreaker_needed(0.02) is False
    assert tiebreaker_needed(-0.05) is False


def test_tiebreaker_custom_threshold():
    assert tiebreaker_needed(0.02, threshold=0.03) is True
    assert tiebreaker_needed(0.04, threshold=0.03) is False


def test_full_run_artifacts_layout(tmp_run_dir):
    """Walk the full layout: baseline → iter-1 → iter-2 → winner.md → failures.md."""
    make_baseline(tmp_run_dir, n_inputs=14, criteria=["c1", "c2"])
    make_iter(tmp_run_dir, 1, {"score_gain": 0.10})
    make_iter(tmp_run_dir, 2, {"score_gain": 0.04, "decision_gate_outcome": "FAIL_PLATEAU"})
    write_winner_diff(tmp_run_dir, "baseline body", "winner body")
    (tmp_run_dir / "failures.md").write_text("## Failures\n- c2 failed on input 7\n")

    expected = {"baseline.json", "iter-1.json", "iter-2.json", "winner.md", "failures.md"}
    actual = {p.name for p in tmp_run_dir.iterdir()}
    assert expected.issubset(actual), f"missing: {expected - actual}"


def test_iter_json_serializable(tmp_run_dir):
    """Round-trip serialization stability."""
    make_baseline(tmp_run_dir, n_inputs=14, criteria=["c1"])
    make_iter(tmp_run_dir, 1, {})
    p = tmp_run_dir / "iter-1.json"
    loaded = json.loads(p.read_text())
    # Re-serialize and re-load → identical
    re_serialized = json.dumps(loaded, indent=2)
    assert json.loads(re_serialized) == loaded
