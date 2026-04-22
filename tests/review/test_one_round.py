import pytest
from pydantic import ValidationError

from core.cluster import cross_model_review
from core.cluster.review_verdict import Verdict


async def _passing_reviewers(_prompt, _config, timeout_seconds=60):
    return [
        {"name": "sonnet-4-6", "findings": [], "duration_ms": 10, "status": "ok"},
        {"name": "gpt-5.4", "findings": [], "duration_ms": 14, "status": "ok"},
    ]


async def _timeout_reviewers(_prompt, _config, timeout_seconds=60):
    return [
        {
            "name": "sonnet-4-6",
            "findings": [{"finding": "needs migration", "severity": "blocker", "fix_type": "fixable"}],
            "duration_ms": 30000,
            "status": "ok",
        },
        {"name": "gpt-5.4", "findings": [], "duration_ms": 60000, "status": "timeout"},
    ]


def test_rerun_same_hash_exits_three(monkeypatch, tmp_path, capsys):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cross_model_review, "_THREE_WAY_DECISIONS_LOG", tmp_path / "decisions.log")
    monkeypatch.setattr(cross_model_review, "_run_parallel_reviewers_one_round", _passing_reviewers)

    cross_model_review.run_three_way_review(
        diff_text="same plan body",
        spec_text="",
        commit_sha="sha-1",
        project_root=str(tmp_path),
    )

    with pytest.raises(SystemExit) as exc_info:
        cross_model_review.run_three_way_review(
            diff_text="same plan body",
            spec_text="",
            commit_sha="sha-2",
            project_root=str(tmp_path),
        )

    assert exc_info.value.code == 3
    assert "ONE-REVIEW-PER-PLAN: rerun not permitted" in capsys.readouterr().err


def test_timeout_is_abstention_and_arbiter_runs(monkeypatch, tmp_path):
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setattr(cross_model_review, "_THREE_WAY_DECISIONS_LOG", tmp_path / "decisions.log")
    monkeypatch.setattr(cross_model_review, "_run_parallel_reviewers_one_round", _timeout_reviewers)

    called = {}

    def _fake_arbiter(plan, reviewer_findings, config):
        called["reviewer_findings"] = reviewer_findings
        return Verdict(
            pass_=False,
            verdict="BLOCK",
            reviewers=reviewer_findings,
            arbiter={"reasoning": "Timeout treated as abstention.", "duration_ms": 15, "status": "ok"},
            circuit_state="closed",
            plan_hash=config["plan_hash"],
            review_round=1,
            escalated=False,
            blockers=[{"finding": "needs migration", "severity": "blocker", "fix_type": "fixable"}],
            arbiter_reasoning="Timeout treated as abstention.",
        ).as_dict()

    monkeypatch.setattr(cross_model_review, "arbitrate", _fake_arbiter)

    result = cross_model_review.run_three_way_review(
        diff_text="new plan body",
        spec_text="",
        commit_sha="sha-timeout",
        project_root=str(tmp_path),
    )

    assert result["arbiter_invoked"] is True
    assert result["reviewers"][0]["name"] == "sonnet-4-6"
    assert result["reviewers"][1]["status"] == "timeout"
    assert called["reviewer_findings"][1]["status"] == "timeout"
    assert result["verdict"] == "BLOCK"


def test_verdict_rejects_invalid_round_and_escalation():
    with pytest.raises(ValidationError):
        Verdict(
            pass_=True,
            verdict="PASS",
            reviewers=[],
            arbiter={"reasoning": "ok", "duration_ms": 1, "status": "ok"},
            circuit_state="closed",
            plan_hash="abc",
            review_round=2,
            escalated=False,
        )

    with pytest.raises(ValidationError):
        Verdict(
            pass_=True,
            verdict="PASS",
            reviewers=[],
            arbiter={"reasoning": "ok", "duration_ms": 1, "status": "ok"},
            circuit_state="closed",
            plan_hash="abc",
            review_round=1,
            escalated=True,
        )
