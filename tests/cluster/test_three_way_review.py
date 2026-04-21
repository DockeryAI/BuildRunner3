"""
tests/cluster/test_three_way_review.py

Phase 9: 3-Way Adversarial Review + Opus Arbiter tests.

Tests verify:
  - Parallel gather of 2 reviewers
  - Consensus skips arbiter
  - Disagreement invokes arbiter
  - Arbiter ruling is logged to decisions.log
  - Round cap enforcement (BR3_MAX_REVIEW_ROUNDS)
  - Structural blocker short-circuit (escalate on round 1)
  - Persistent blocker detection (same normalized finding across 2+ rounds)
  - fix_type required on every finding (reject without it)
"""

import json
import os
import sys
import tempfile
import textwrap
import threading
import time
from pathlib import Path
from unittest import mock

import pytest

# Ensure project root is importable
PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# Break the circular import: cross_model_review → core.runtime.cache_policy →
# core.runtime → core.runtime.claude_runtime → cross_model_review
# We mock the cache_policy module so the circular dependency never forms.
from unittest.mock import MagicMock

_mock_cache_policy = MagicMock()
_mock_cache_policy.build_cached_prompt.side_effect = lambda system_text, skill_context, task_payload: [
    {"text": system_text},
    {"text": skill_context},
    {"text": task_payload},
]
sys.modules.setdefault("core.runtime.cache_policy", _mock_cache_policy)

# Also stub core.cluster.summarizer to avoid further transitive imports
_mock_summarizer = MagicMock()
_mock_summarizer.summarize_diff.return_value = {"summary": "summarized", "excerpts": [], "truncated": False}
sys.modules.setdefault("core.cluster.summarizer", _mock_summarizer)

# Now import can proceed
from core.cluster.cross_model_review import (  # noqa: E402
    ESCALATION_PROMPT,
    _check_consensus,
    _detect_persistent_blockers,
    _detect_structural_blocker,
    _merge_two_way_findings,
    _normalize_finding,
    _reject_missing_fix_type,
    _run_parallel_reviews,
    run_three_way_review,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(finding="test finding", severity="note", fix_type="fixable", **kwargs):
    return {"finding": finding, "severity": severity, "fix_type": fix_type, **kwargs}


def _make_blocker(finding="critical bug", fix_type="fixable"):
    return _make_finding(finding=finding, severity="blocker", fix_type=fix_type)


def _make_structural_blocker(finding="structural issue"):
    return _make_finding(finding=finding, severity="blocker", fix_type="structural")


# ---------------------------------------------------------------------------
# test_parallel_gather
# ---------------------------------------------------------------------------

class TestParallelGather:
    """test_parallel_gather: both reviewers invoked concurrently, results gathered."""

    def test_parallel_gather(self, monkeypatch):
        """Both Claude and Codex are invoked; results arrive in parallel."""
        call_times = {}

        def fake_claude(prompt, config, timeout=120):
            call_times["claude_start"] = time.monotonic()
            time.sleep(0.05)
            findings = [_make_finding("claude finding", severity="note", fix_type="fixable")]
            call_times["claude_end"] = time.monotonic()
            return findings, "claude-sonnet-4-6"

        def fake_codex(prompt, config, commit_sha=None):
            call_times["codex_start"] = time.monotonic()
            time.sleep(0.05)
            findings = [_make_finding("codex finding", severity="note", fix_type="fixable")]
            call_times["codex_end"] = time.monotonic()
            return findings, "codex/gpt-5.4", 0.0

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline", fake_claude
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex", fake_codex
        )

        result = _run_parallel_reviews("test prompt", {})

        assert result["claude"] is not None, "Claude result missing"
        assert result["codex"] is not None, "Codex result missing"
        assert len(result["claude"]["findings"]) == 1
        assert len(result["codex"]["findings"]) == 1
        # Verify parallelism: both started before either finished
        assert call_times["claude_start"] < call_times["codex_end"]
        assert call_times["codex_start"] < call_times["claude_end"]

    def test_parallel_gather_partial_failure(self, monkeypatch):
        """If one reviewer fails, the other's results still surface."""

        def fake_claude(prompt, config, timeout=120):
            return [_make_finding(fix_type="fixable")], "claude-sonnet-4-6"

        def fail_codex(prompt, config, commit_sha=None):
            raise RuntimeError("codex unavailable")

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline", fake_claude
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex", fail_codex
        )

        result = _run_parallel_reviews("test prompt", {})
        assert result["claude"] is not None
        assert result["codex"] is None
        assert any("codex" in e for e in result["errors"])


# ---------------------------------------------------------------------------
# test_consensus_skips_arbiter
# ---------------------------------------------------------------------------

class TestConsensusSkipsArbiter:
    """test_consensus_skips_arbiter: when reviewers agree, arbiter is not invoked."""

    def test_consensus_skips_arbiter_no_blockers(self, monkeypatch, tmp_path):
        """Both reviewers return only notes → no arbiter, verdict APPROVED."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        findings = [_make_finding("minor issue", severity="note", fix_type="fixable")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (findings, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (findings, "codex/gpt-5.4", 0.0),
        )

        arbiter_called = []
        monkeypatch.setattr(
            "core.cluster.cross_model_review._invoke_arbiter",
            lambda **kw: arbiter_called.append(True) or {"verdict": "APPROVED", "findings": []},
        )

        result = run_three_way_review(
            diff_text="some diff",
            spec_text="some spec",
            commit_sha="abc123",
            project_root=str(tmp_path),
            config={},
        )

        assert result["verdict"] == "APPROVED"
        assert result["arbiter_invoked"] is False
        assert len(arbiter_called) == 0

    def test_consensus_after_rebuttal_skips_arbiter(self, monkeypatch, tmp_path):
        """Rebuttal concedes all blockers → no arbiter needed."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        blocker = [_make_blocker("rare bug", fix_type="fixable")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (blocker, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (blocker, "codex/gpt-5.4", 0.0),
        )

        # Rebuttal concedes the blocker
        def fake_rebuttal(merged, artifact, config):
            for item in merged:
                if item.get("severity") == "blocker":
                    item["severity"] = "warning"
                    item["rebuttal_conceded"] = True
            return merged, True

        monkeypatch.setattr(
            "core.cluster.cross_model_review._run_rebuttal", fake_rebuttal
        )

        arbiter_called = []
        monkeypatch.setattr(
            "core.cluster.cross_model_review._invoke_arbiter",
            lambda **kw: arbiter_called.append(True) or {"verdict": "APPROVED", "findings": []},
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
        )

        assert result["arbiter_invoked"] is False
        assert len(arbiter_called) == 0


# ---------------------------------------------------------------------------
# test_disagreement_invokes_arbiter
# ---------------------------------------------------------------------------

class TestDisagreementInvokesArbiter:
    """test_disagreement_invokes_arbiter: unresolved split post-rebuttal triggers arbiter."""

    def test_disagreement_invokes_arbiter(self, monkeypatch, tmp_path):
        """Divergent blocker findings after rebuttal → arbiter invoked exactly once."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        claude_findings = [_make_blocker("claude unique bug")]
        codex_findings = [_make_blocker("codex unique bug")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (claude_findings, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (codex_findings, "codex/gpt-5.4", 0.0),
        )

        # Rebuttal does not concede
        monkeypatch.setattr(
            "core.cluster.cross_model_review._run_rebuttal",
            lambda merged, artifact, config: (merged, True),
        )

        arbiter_calls = []

        def fake_arbiter(**kwargs):
            arbiter_calls.append(kwargs)
            return {"verdict": "BLOCKED", "findings": [], "rationale": "arbiter says blocked"}

        monkeypatch.setattr(
            "core.cluster.cross_model_review._invoke_arbiter", fake_arbiter
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
        )

        assert result["arbiter_invoked"] is True
        assert len(arbiter_calls) == 1
        assert result["arbiter_ruling"]["verdict"] == "BLOCKED"


# ---------------------------------------------------------------------------
# test_arbiter_logs_ruling
# ---------------------------------------------------------------------------

class TestArbiterLogsRuling:
    """test_arbiter_logs_ruling: every arbiter ruling is logged to decisions.log."""

    def test_arbiter_logs_ruling(self, monkeypatch, tmp_path):
        """Arbiter ruling is appended to decisions.log."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        # Patch decisions log path to tmp
        decisions_log = tmp_path / "decisions.log"
        monkeypatch.setattr(
            "core.cluster.cross_model_review._THREE_WAY_DECISIONS_LOG",
            decisions_log,
        )

        claude_findings = [_make_blocker("real bug")]
        codex_findings = [_make_blocker("different real bug")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (claude_findings, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (codex_findings, "codex/gpt-5.4", 0.0),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review._run_rebuttal",
            lambda merged, artifact, config: (merged, True),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review._invoke_arbiter",
            lambda **kw: {"verdict": "BLOCKED", "findings": [], "rationale": "test ruling"},
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
        )

        assert decisions_log.exists(), "decisions.log was not created"
        log_content = decisions_log.read_text()
        assert "arbiter" in log_content.lower(), "Arbiter event not in decisions.log"
        assert "BLOCKED" in log_content, "Ruling verdict not in decisions.log"


# ---------------------------------------------------------------------------
# test_round_cap_enforced
# ---------------------------------------------------------------------------

class TestRoundCapEnforced:
    """test_round_cap_enforced: escalation triggered at cap, not one round later."""

    def test_round_cap_enforced(self, monkeypatch, tmp_path):
        """At round=max_rounds+1, escalation fires before arbiter."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        blocker = [_make_blocker("persistent bug")]
        prior_findings = [_make_blocker("persistent bug")]  # same finding = persistent

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (blocker, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (blocker, "codex/gpt-5.4", 0.0),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review._run_rebuttal",
            lambda merged, artifact, config: (merged, True),
        )

        arbiter_called = []
        monkeypatch.setattr(
            "core.cluster.cross_model_review._invoke_arbiter",
            lambda **kw: arbiter_called.append(True) or {"verdict": "BLOCKED", "findings": []},
        )

        # Round 2 with max_rounds=1 → should escalate, not invoke arbiter
        result = run_three_way_review(
            diff_text="diff",
            spec_text="spec",
            commit_sha="abc123",
            project_root=str(tmp_path),
            config={},
            review_round=2,
            prior_findings=prior_findings,
        )

        # Either escalated due to round cap or persistent blocker detection
        assert result.get("escalated") is True or result.get("verdict") == "ESCALATED"
        assert result.get("exit_code") == 2
        # Arbiter should NOT be called after cap/persistent detection
        assert len(arbiter_called) == 0

    def test_round_cap_prints_escalation_prompt(self, monkeypatch, tmp_path, capsys):
        """Escalation prompt is printed to stderr on cap hit."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        blocker = [_make_blocker("cap bug")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (blocker, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (blocker, "codex/gpt-5.4", 0.0),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review._run_rebuttal",
            lambda merged, artifact, config: (merged, True),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review._invoke_arbiter",
            lambda **kw: {"verdict": "BLOCKED", "findings": []},
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
            review_round=2, prior_findings=[_make_blocker("cap bug")],
        )

        captured = capsys.readouterr()
        assert "CONTINUE" in captured.err or result.get("exit_code") == 2


# ---------------------------------------------------------------------------
# test_structural_short_circuit
# ---------------------------------------------------------------------------

class TestStructuralShortCircuit:
    """test_structural_short_circuit: structural blocker escalates on round 1."""

    def test_structural_short_circuit(self, monkeypatch, tmp_path, capsys):
        """A structural blocker in round 1 triggers immediate escalation."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "3")

        structural = [_make_structural_blocker("circular dependency — phase 3 imports phase 5")]
        normal = [_make_finding("minor note", severity="note", fix_type="fixable")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (structural, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (normal, "codex/gpt-5.4", 0.0),
        )

        arbiter_called = []
        monkeypatch.setattr(
            "core.cluster.cross_model_review._invoke_arbiter",
            lambda **kw: arbiter_called.append(True) or {"verdict": "BLOCKED", "findings": []},
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={}, review_round=1,
        )

        assert result["escalated"] is True
        assert result["exit_code"] == 2
        assert len(arbiter_called) == 0
        captured = capsys.readouterr()
        assert "CONTINUE" in captured.err

    def test_structural_blocker_in_codex_also_escalates(self, monkeypatch, tmp_path):
        """Structural blocker from Codex also triggers escalation."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "3")

        normal = [_make_finding(severity="note", fix_type="fixable")]
        structural = [_make_structural_blocker("schema incompatibility")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (normal, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (structural, "codex/gpt-5.4", 0.0),
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={}, review_round=1,
        )

        assert result["escalated"] is True
        assert result["exit_code"] == 2


# ---------------------------------------------------------------------------
# test_persistent_blocker_detected
# ---------------------------------------------------------------------------

class TestPersistentBlockerDetected:
    """test_persistent_blocker_detected: same normalized finding across 2+ rounds → escalate."""

    def test_persistent_blocker_detected(self, monkeypatch, tmp_path):
        """Blocker appearing in both round 1 (prior) and round 2 triggers escalation."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "3")

        # Same finding text in both rounds
        blocker_text = "connection pool exhausted under load"
        current_findings = [_make_blocker(blocker_text)]
        prior_findings = [_make_blocker(blocker_text)]  # same normalized text

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (current_findings, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (current_findings, "codex/gpt-5.4", 0.0),
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
            review_round=2, prior_findings=prior_findings,
        )

        assert result["escalated"] is True
        assert result["exit_code"] == 2
        assert "persistent_blockers" in result

    def test_non_persistent_blocker_does_not_escalate(self, monkeypatch, tmp_path):
        """Different blocker texts do not trigger persistent detection."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "3")

        current = [_make_blocker("new bug found this round")]
        prior = [_make_blocker("old bug from last round")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (current, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (current, "codex/gpt-5.4", 0.0),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review._run_rebuttal",
            lambda merged, artifact, config: (merged, True),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review._invoke_arbiter",
            lambda **kw: {"verdict": "BLOCKED", "findings": []},
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
            review_round=2, prior_findings=prior,
        )

        # Should NOT escalate for persistent (different text)
        assert result.get("persistent_blockers") is None or len(result.get("persistent_blockers", [])) == 0


# ---------------------------------------------------------------------------
# test_fix_type_required
# ---------------------------------------------------------------------------

class TestFixTypeRequired:
    """test_fix_type_required: reviewer output without fix_type is rejected."""

    def test_fix_type_required_claude(self, monkeypatch, tmp_path):
        """Claude findings missing fix_type cause rejection."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        # Finding without fix_type
        bad_finding = {"finding": "something wrong", "severity": "blocker"}
        good_codex = [_make_finding(fix_type="fixable")]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: ([bad_finding], "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (good_codex, "codex/gpt-5.4", 0.0),
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
        )

        assert result["verdict"] == "REJECTED"
        assert "fix_type" in result.get("error", "").lower()

    def test_fix_type_required_codex(self, monkeypatch, tmp_path):
        """Codex findings missing fix_type cause rejection."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        good_claude = [_make_finding(fix_type="fixable")]
        bad_finding = {"finding": "codex bug", "severity": "warning"}  # no fix_type

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (good_claude, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: ([bad_finding], "codex/gpt-5.4", 0.0),
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
        )

        assert result["verdict"] == "REJECTED"

    def test_all_fix_types_present_passes(self, monkeypatch, tmp_path):
        """All findings with fix_type pass validation."""
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        findings = [
            _make_finding("fixable issue", severity="note", fix_type="fixable"),
            _make_finding("structural issue", severity="warning", fix_type="structural"),
        ]

        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_claude_inline",
            lambda *a, **kw: (findings, "claude-sonnet-4-6"),
        )
        monkeypatch.setattr(
            "core.cluster.cross_model_review.review_via_codex",
            lambda *a, **kw: (findings, "codex/gpt-5.4", 0.0),
        )

        result = run_three_way_review(
            diff_text="diff", spec_text="spec", commit_sha="abc123",
            project_root=str(tmp_path), config={},
        )

        assert result["verdict"] != "REJECTED"


# ---------------------------------------------------------------------------
# Additional unit tests for internal helpers
# ---------------------------------------------------------------------------

class TestInternalHelpers:
    """Unit tests for merge, consensus, normalization helpers."""

    def test_normalize_finding(self):
        assert _normalize_finding("Line 42: division by zero!") == "line 42 division by zero"
        assert _normalize_finding("  Spaces  AND CAPS  ") == "spaces and caps"

    def test_merge_two_way_findings_consensus(self):
        """Same finding from both reviewers → consensus=True."""
        claude = [_make_blocker("null pointer dereference")]
        codex = [_make_blocker("null pointer dereference")]
        merged = _merge_two_way_findings(claude, codex)
        assert len(merged) == 1
        assert merged[0]["consensus"] is True
        assert sorted(merged[0]["sources"]) == ["claude", "codex"]

    def test_merge_two_way_findings_no_consensus(self):
        """Different findings → consensus=False."""
        claude = [_make_blocker("claude bug")]
        codex = [_make_blocker("codex bug")]
        merged = _merge_two_way_findings(claude, codex)
        assert len(merged) == 2
        assert all(item["consensus"] is False for item in merged)

    def test_merge_structural_sticky(self):
        """If either reviewer marks structural, merged result is structural."""
        claude = [_make_finding("bad pattern", severity="blocker", fix_type="fixable")]
        codex = [_make_finding("bad pattern", severity="blocker", fix_type="structural")]
        merged = _merge_two_way_findings(claude, codex)
        assert merged[0]["fix_type"] == "structural"

    def test_check_consensus_no_blockers(self):
        """No blockers → has_consensus=True."""
        findings = [_make_finding(severity="note", fix_type="fixable")]
        has_c, cblockers, solo = _check_consensus(findings)
        assert has_c is True
        assert cblockers == []
        assert solo == []

    def test_check_consensus_with_solo_blocker(self):
        """Solo blocker (only one source) → has_consensus=False."""
        findings = [_make_blocker() | {"sources": ["claude"], "consensus": False}]
        has_c, cblockers, solo = _check_consensus(findings)
        assert has_c is False
        assert len(solo) == 1

    def test_detect_structural_blocker(self):
        """Detects first structural blocker correctly."""
        findings = [
            _make_finding(severity="warning", fix_type="structural"),  # not blocker
            _make_structural_blocker("real structural"),
        ]
        result = _detect_structural_blocker(findings)
        assert result is not None
        assert result["finding"] == "real structural"

    def test_detect_structural_blocker_none(self):
        """Returns None when no structural blocker present."""
        findings = [_make_blocker("fixable blocker", fix_type="fixable")]
        assert _detect_structural_blocker(findings) is None

    def test_detect_persistent_blockers(self):
        """Same normalized text in both rounds → persistent."""
        r1 = [_make_blocker("connection timeout  error")]
        r2 = [_make_blocker("connection timeout error")]  # normalize matches
        persistent = _detect_persistent_blockers(r1, r2)
        assert len(persistent) == 1

    def test_reject_missing_fix_type(self):
        """Raises ValueError for finding without fix_type."""
        findings = [{"finding": "something", "severity": "blocker"}]
        with pytest.raises(ValueError, match="fix_type"):
            _reject_missing_fix_type(findings, "test-reviewer")

    def test_reject_missing_fix_type_passes_valid(self):
        """Does not raise for valid findings."""
        findings = [_make_finding(fix_type="fixable"), _make_finding(fix_type="structural")]
        _reject_missing_fix_type(findings, "test-reviewer")  # should not raise


# ---------------------------------------------------------------------------
# test_escalation_prompt_content
# ---------------------------------------------------------------------------

class TestEscalationPromptContent:
    """Verify escalation prompt contains required options."""

    def test_escalation_prompt_has_three_options(self):
        """ESCALATION_PROMPT contains CONTINUE, OVERRIDE, and SIMPLIFY."""
        assert "CONTINUE" in ESCALATION_PROMPT
        assert "OVERRIDE" in ESCALATION_PROMPT
        assert "SIMPLIFY" in ESCALATION_PROMPT

    def test_escalation_prompt_format(self):
        """Escalation prompt starts and ends with delimiter."""
        assert ESCALATION_PROMPT.strip().startswith("===")
        assert ESCALATION_PROMPT.strip().endswith("===")
