import hashlib
import json
from types import SimpleNamespace

from core.cluster import cross_model_review


async def _passing_reviewers(_prompt, _config, timeout_seconds=60):
    return [
        {"name": "sonnet-4-6", "findings": [], "duration_ms": 10, "status": "ok"},
        {"name": "gpt-5.5", "findings": [], "duration_ms": 12, "status": "ok"},
    ]


async def _disagreeing_reviewers(_prompt, _config, timeout_seconds=60):
    return [
        {
            "name": "sonnet-4-6",
            "findings": [{"finding": "missing guard", "severity": "blocker", "fix_type": "fixable"}],
            "duration_ms": 10,
            "status": "ok",
        },
        {"name": "gpt-5.5", "findings": [], "duration_ms": 12, "status": "ok"},
    ]


def test_phase_mode_is_idempotent_within_triple(monkeypatch, tmp_path):
    run_phase_review = cross_model_review._run_phase_review  # noqa: SLF001
    calls = {"count": 0}

    async def _counting_reviewers(prompt, config, timeout_seconds=60):
        calls["count"] += 1
        return await _passing_reviewers(prompt, config, timeout_seconds)

    monkeypatch.setattr(cross_model_review, "_run_parallel_reviewers_one_round", _counting_reviewers)

    first = run_phase_review(
        build_id="test",
        phase_n=1,
        revision_count=0,
        diff_text="diff v1",
        criteria_text="criteria",
        project_root=str(tmp_path),
    )
    second = run_phase_review(
        build_id="test",
        phase_n=1,
        revision_count=0,
        diff_text="diff v2 with different content",
        criteria_text="criteria changed",
        project_root=str(tmp_path),
    )

    assert calls["count"] == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert first["tracking_artifact"] == second["tracking_artifact"]
    assert first["diff_sha256"] == hashlib.sha256(b"diff v1").hexdigest()
    assert second["diff_sha256"] == first["diff_sha256"]
    assert second["verdict"] == first["verdict"]
    assert (
        tmp_path
        / ".buildrunner"
        / "cluster-reviews"
        / "phase"
        / f"test-phase1-rev0-{first['diff_sha256'][:12]}.json"
    ).exists()


def test_phase_mode_does_not_collide_across_revisions(monkeypatch, tmp_path):
    run_phase_review = cross_model_review._run_phase_review  # noqa: SLF001
    calls = {"count": 0}

    async def _counting_reviewers(prompt, config, timeout_seconds=60):
        calls["count"] += 1
        return await _passing_reviewers(prompt, config, timeout_seconds)

    monkeypatch.setattr(cross_model_review, "_run_parallel_reviewers_one_round", _counting_reviewers)

    rev0 = run_phase_review(
        build_id="test",
        phase_n=1,
        revision_count=0,
        diff_text="same diff",
        criteria_text="criteria",
        project_root=str(tmp_path),
    )
    rev1 = run_phase_review(
        build_id="test",
        phase_n=1,
        revision_count=1,
        diff_text="same diff",
        criteria_text="criteria",
        project_root=str(tmp_path),
    )

    assert calls["count"] == 2
    assert rev0["cached"] is False
    assert rev1["cached"] is False
    assert rev0["tracking_artifact"] != rev1["tracking_artifact"]
    assert rev0["phase_review_key"] != rev1["phase_review_key"]
    written = sorted((tmp_path / ".buildrunner" / "cluster-reviews" / "phase").glob("test-phase1-rev*.json"))
    assert len(written) == 2


def test_phase_mode_arbiter_only_fires_on_second_reject(monkeypatch, tmp_path):
    run_phase_review = cross_model_review._run_phase_review  # noqa: SLF001
    called = {}

    def _fake_arbiter(plan, reviewer_findings, config):
        called["plan"] = plan
        called["model"] = config["arbiter"]["model"]
        called["reviewer_findings"] = reviewer_findings
        return {
            "pass": False,
            "verdict": "BLOCK",
            "reviewers": reviewer_findings,
            "arbiter": {"reasoning": "arbiter final", "duration_ms": 5, "status": "ok"},
            "circuit_state": "closed",
            "plan_hash": config["plan_hash"],
            "review_round": 1,
            "escalated": False,
            "blockers": [{"finding": "missing guard", "severity": "blocker", "fix_type": "fixable"}],
            "arbiter_reasoning": "arbiter final",
        }

    monkeypatch.setattr(cross_model_review, "_run_parallel_reviewers_one_round", _disagreeing_reviewers)
    monkeypatch.setattr(cross_model_review, "arbitrate", _fake_arbiter)

    first = run_phase_review(
        build_id="build-1",
        phase_n=5,
        revision_count=0,
        diff_text="diff a",
        criteria_text="criteria",
        project_root=str(tmp_path),
        config={"phase_arbiter_model": "claude-opus-4-7"},
    )
    second = run_phase_review(
        build_id="build-1",
        phase_n=5,
        revision_count=1,
        diff_text="diff b",
        criteria_text="criteria",
        project_root=str(tmp_path),
        config={"phase_arbiter_model": "claude-opus-4-7"},
    )

    assert first["arbiter_invoked"] is False
    assert first["verdict"] == "BLOCK"
    assert second["arbiter_invoked"] is True
    assert second["verdict"] == "BLOCK"
    assert called["model"] == "claude-opus-4-7"
    assert called["plan"] == "diff b"
    assert called["reviewer_findings"][0]["name"] == "sonnet-4-6"


def test_phase_mode_can_disable_auto_arbiter(monkeypatch, tmp_path):
    run_phase_review = cross_model_review._run_phase_review  # noqa: SLF001

    monkeypatch.setattr(cross_model_review, "_run_parallel_reviewers_one_round", _disagreeing_reviewers)
    monkeypatch.setenv("BR3_PHASE_DISABLE_AUTO_ARBITER", "1")

    result = run_phase_review(
        build_id="build-1",
        phase_n=5,
        revision_count=1,
        diff_text="diff b",
        criteria_text="criteria",
        project_root=str(tmp_path),
        config={"phase_arbiter_model": "claude-opus-4-7"},
    )

    assert result["arbiter_invoked"] is False
    assert result["verdict"] == "BLOCK"
    assert result["reason"] == "phase-review-disagreement"


def test_phase_arbiter_uses_both_review_artifacts(monkeypatch):
    called = {}

    def _fake_arbiter(plan, reviewer_findings, config):
        called["plan"] = plan
        called["reviewer_findings"] = reviewer_findings
        called["model"] = config["arbiter"]["model"]
        return {
            "pass": True,
            "verdict": "PASS",
            "reviewers": reviewer_findings,
            "arbiter": {"reasoning": "final approve", "duration_ms": 7, "status": "ok"},
            "circuit_state": "closed",
            "plan_hash": config["plan_hash"],
            "review_round": 1,
            "escalated": False,
            "blockers": [],
            "arbiter_reasoning": "final approve",
        }

    monkeypatch.setattr(cross_model_review, "arbitrate", _fake_arbiter)

    result = cross_model_review._run_phase_arbiter(  # noqa: SLF001
        build_id="build-1",
        phase_n=4,
        criteria_text="- all bullets satisfied",
        initial_diff_text="diff initial",
        revised_diff_text="diff revised",
        initial_review={"findings": [{"finding": "first", "severity": "blocker"}]},
        revised_review={"findings": [{"finding": "second", "severity": "blocker"}]},
        config={"phase_arbiter_model": "claude-opus-4-7"},
    )

    assert result["arbiter_invoked"] is True
    assert result["verdict"] == "PASS"
    assert result["findings"] == [
        {"finding": "first", "severity": "blocker"},
        {"finding": "second", "severity": "blocker"},
    ]
    assert called["model"] == "claude-opus-4-7"
    assert called["reviewer_findings"][0]["name"] == "phase-review-rev0"
    assert called["reviewer_findings"][1]["name"] == "phase-review-rev1"
    assert "Initial Diff:" in called["plan"]
    assert "Revised Review:" in called["plan"]


def test_plan_mode_behavior_preserved():
    compute_plan_hash = cross_model_review._compute_plan_hash  # noqa: SLF001
    plan_text = "### Phase 7: Test\n**Status:** pending\n"
    expected_hash = hashlib.sha256(plan_text.encode("utf-8")).hexdigest()[:16]

    with cross_model_review.tempfile.TemporaryDirectory(prefix="br3-plan-mode-") as temp_dir:
        plan_file = cross_model_review.Path(temp_dir) / "phase-plan.md"
        plan_file.write_text(plan_text, encoding="utf-8")

        plan_hash = compute_plan_hash("", plan_file=str(plan_file))
        written = cross_model_review.write_tracking_artifact(
            project_root=temp_dir,
            plan_file=str(plan_file),
            task_id="task-1",
            result={
                "pass": True,
                "verdict": "PASS",
                "reviewers": [],
                "arbiter": {"reasoning": "ok", "duration_ms": 0, "status": "not-needed"},
                "findings": [],
                "blockers": [],
                "arbiter_invoked": False,
                "plan_hash": plan_hash,
                "review_round": 1,
                "escalated": False,
            },
            mode="plan",
        )

        assert plan_hash == expected_hash
        assert len(written) == 1
        assert "/.buildrunner/adversarial-reviews/" in written[0]
        assert written[0].endswith(".json")
        assert json.loads(cross_model_review.Path(written[0]).read_text(encoding="utf-8"))["phase_number"] == 7


def test_codex_version_gate_accepts_0_124_0(monkeypatch):
    monkeypatch.setattr(
        cross_model_review.subprocess,
        "run",
        lambda *args, **kwargs: SimpleNamespace(returncode=0, stdout="codex-cli 0.124.0", stderr=""),
    )

    version = cross_model_review.ensure_codex_compatible()

    assert cross_model_review.is_supported_codex_version((0, 124, 0)) is True
    assert cross_model_review.is_supported_codex_version((0, 47, 9)) is False
    assert version["parsed"] == (0, 124, 0)
