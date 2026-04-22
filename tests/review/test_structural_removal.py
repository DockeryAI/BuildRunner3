from pathlib import Path

from core.cluster import cross_model_review


async def _ok_reviewers(_prompt, _config, timeout_seconds=60):
    return [
        {"name": "sonnet-4-6", "findings": [], "duration_ms": 10, "status": "ok"},
        {"name": "gpt-5.4", "findings": [], "duration_ms": 12, "status": "ok"},
    ]


def test_structural_removal_and_import(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cross_model_review, "_THREE_WAY_DECISIONS_LOG", tmp_path / "decisions.log")
    monkeypatch.setattr(cross_model_review, "_run_parallel_reviewers_one_round", _ok_reviewers)

    result = cross_model_review.run_three_way_review(
        diff_text="### Phase 6: sample\n\nImplement one-round review.\n",
        spec_text="",
        commit_sha="fixture-sha",
        project_root=str(tmp_path),
    )

    assert result["verdict"] == "PASS"
    assert result["review_round"] == 1
    assert result["escalated"] is False

    forbidden = ("_run_rebuttal", "rebuttal_round", "escalate_to_user", "max_rebuttal_rounds")
    for path in Path("core/cluster").rglob("*.py"):
        content = path.read_text(encoding="utf-8", errors="replace")
        for token in forbidden:
            assert token not in content, f"{token} still present in {path}"
