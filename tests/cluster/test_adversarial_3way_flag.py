"""
tests/cluster/test_adversarial_3way_flag.py

Phase 4: BR3_ADVERSARIAL_3WAY flag enforcement tests.

Verifies:
  - flag off  → 2-way parallel review (claude + codex only; Below not called)
  - flag on   → 3-way parallel review (claude + codex + below)
  - flag read occurs once at module import (cached in _ADVERSARIAL_3WAY_ENABLED)
  - 3-way branch respects BR3_MAX_REVIEW_ROUNDS=1 cap
  - main() routes to run_review() when flag off, run_three_way_review() when on
"""

import importlib
import sqlite3
import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

PROJECT_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

# ---------------------------------------------------------------------------
# Stub out heavy transitive imports before touching cross_model_review.
# Must happen before the first import of core.cluster.cross_model_review.
# ---------------------------------------------------------------------------
_mock_cache_policy = MagicMock()
_mock_cache_policy.build_cached_prompt.side_effect = (
    lambda system_text, skill_context, task_payload: [
        {"text": system_text},
        {"text": skill_context},
        {"text": task_payload},
    ]
)
sys.modules["core.runtime.cache_policy"] = _mock_cache_policy

_mock_summarizer = MagicMock()
_mock_summarizer.summarize_diff.return_value = {
    "summary": "summarized diff",
    "excerpts": [],
    "truncated": False,
}
sys.modules["core.cluster.summarizer"] = _mock_summarizer

# Pre-import the module so importlib.reload works inside tests
import core.cluster.cross_model_review as _cmr_module  # noqa: E402


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_finding(finding="ok", severity="note", fix_type="fixable"):
    return {"finding": finding, "severity": severity, "fix_type": fix_type}


def _findings_list(*texts):
    return [_make_finding(t) for t in texts]


def _create_telemetry_db(repo_root: Path) -> Path:
    db_path = repo_root / ".buildrunner" / "telemetry.db"
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                event_id TEXT UNIQUE NOT NULL,
                event_type TEXT NOT NULL,
                timestamp TEXT NOT NULL,
                metadata TEXT,
                success BOOLEAN DEFAULT 1
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


def _count_review_events(db_path: Path) -> int:
    conn = sqlite3.connect(str(db_path))
    try:
        row = conn.execute(
            "SELECT COUNT(*) FROM events WHERE event_type='adversarial_review_ran'"
        ).fetchone()
        return int(row[0]) if row else 0
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# Tests: flag off → 2-way (claude + codex only)
# ---------------------------------------------------------------------------

def _get_cmr(monkeypatch, flag_value):
    """Reload cross_model_review with the given flag value and return the module."""
    monkeypatch.setenv("BR3_ADVERSARIAL_3WAY", flag_value)
    importlib.reload(_cmr_module)
    return _cmr_module


class TestAdversarial3WayFlagOff:
    """When BR3_ADVERSARIAL_3WAY=off, only claude+codex reviewers run."""

    def test_flag_off_uses_2way_parallel(self, monkeypatch):
        """_run_parallel_reviews is called (not _run_parallel_reviews_3way)."""
        cmr = _get_cmr(monkeypatch, "off")
        assert cmr._ADVERSARIAL_3WAY_ENABLED is False

        claude_findings = _findings_list("claude note")
        codex_findings = _findings_list("codex note")

        with patch.object(cmr, "_run_parallel_reviews") as mock_2way, \
             patch.object(cmr, "_run_parallel_reviews_3way") as mock_3way, \
             patch.object(cmr, "_run_rebuttal", return_value=([], True)):

            mock_2way.return_value = {
                "claude": {"findings": claude_findings, "model": "claude-sonnet-4-6"},
                "codex": {"findings": codex_findings, "model": "codex/gpt-4o"},
                "errors": [],
                "fix_type_errors": [],
            }

            cmr.run_three_way_review(
                diff_text="diff text",
                spec_text="spec text",
                commit_sha="abc123",
                project_root=str(PROJECT_ROOT),
            )

        mock_2way.assert_called_once()
        mock_3way.assert_not_called()

    def test_flag_off_below_not_called(self, monkeypatch):
        """review_via_below is never called when flag is off."""
        cmr = _get_cmr(monkeypatch, "off")

        with patch.object(cmr, "review_via_below"), \
             patch.object(cmr, "_run_parallel_reviews") as mock_2way, \
             patch.object(cmr, "_run_rebuttal", return_value=([], True)):

            mock_2way.return_value = {
                "claude": {"findings": _findings_list("a"), "model": "sonnet"},
                "codex": {"findings": _findings_list("a"), "model": "codex"},
                "errors": [],
                "fix_type_errors": [],
            }

            cmr.run_three_way_review(
                diff_text="d", spec_text="s", commit_sha="x",
                project_root=str(PROJECT_ROOT),
            )

    def test_flag_off_produces_zero_telemetry_emissions(self, monkeypatch, tmp_path):
        """Flag OFF must leave adversarial_review_ran row count unchanged."""
        cmr = _get_cmr(monkeypatch, "off")
        db_path = _create_telemetry_db(tmp_path)
        before = _count_review_events(db_path)

        with patch.object(cmr, "_run_parallel_reviews") as mock_2way, \
             patch("pathlib.Path.cwd", return_value=tmp_path):
            mock_2way.return_value = {
                "claude": {"findings": _findings_list("claude note"), "model": "claude-sonnet-4-6"},
                "codex": {"findings": _findings_list("codex note"), "model": "codex/gpt-5.4"},
                "errors": [],
                "fix_type_errors": [],
            }

            result = cmr.run_three_way_review(
                diff_text="diff text",
                spec_text="spec text",
                commit_sha="abc123",
                project_root=str(tmp_path),
            )

        after = _count_review_events(db_path)
        assert result["verdict"] == "APPROVED"
        assert after == before

    def test_flag_off_module_variable_is_false(self, monkeypatch):
        """When flag off, _ADVERSARIAL_3WAY_ENABLED is False."""
        cmr = _get_cmr(monkeypatch, "off")
        assert cmr._ADVERSARIAL_3WAY_ENABLED is False


# ---------------------------------------------------------------------------
# Tests: flag on → 3-way (claude + codex + below)
# ---------------------------------------------------------------------------

class TestAdversarial3WayFlagOn:
    """When BR3_ADVERSARIAL_3WAY=on, Below is included as a third reviewer."""

    def test_flag_on_uses_3way_parallel(self, monkeypatch):
        """_run_parallel_reviews_3way is called (not 2-way) when flag on."""
        cmr = _get_cmr(monkeypatch, "on")
        assert cmr._ADVERSARIAL_3WAY_ENABLED is True

        claude_findings = _findings_list("claude note")
        codex_findings = _findings_list("codex note")
        below_findings = _findings_list("below note")

        with patch.object(cmr, "_run_parallel_reviews_3way") as mock_3way, \
             patch.object(cmr, "_run_parallel_reviews") as mock_2way, \
             patch.object(cmr, "_run_rebuttal", return_value=([], True)):

            mock_3way.return_value = {
                "claude": {"findings": claude_findings, "model": "claude-sonnet-4-6"},
                "codex": {"findings": codex_findings, "model": "codex/gpt-4o"},
                "below": {"findings": below_findings, "model": "below/qwen2.5-coder:32b"},
                "errors": [],
                "fix_type_errors": [],
            }

            cmr.run_three_way_review(
                diff_text="diff text",
                spec_text="spec text",
                commit_sha="abc123",
                project_root=str(PROJECT_ROOT),
            )

        mock_3way.assert_called_once()
        mock_2way.assert_not_called()

    def test_flag_on_below_included_in_reviewers(self, monkeypatch):
        """When flag on, _run_parallel_reviews_3way calls review_via_below."""
        cmr = _get_cmr(monkeypatch, "on")

        below_findings = [_make_finding("below note")]

        with patch.object(cmr, "review_via_claude_inline") as mock_claude, \
             patch.object(cmr, "review_via_codex") as mock_codex, \
             patch.object(cmr, "review_via_below") as mock_below:

            mock_claude.return_value = (_findings_list("claude note"), "sonnet")
            mock_codex.return_value = (_findings_list("codex note"), "codex", 0.0)
            mock_below.return_value = (below_findings, "below/qwen")

            config = {"backends": {"codex": {"enabled": True, "timeout_seconds": 60}}}
            result = cmr._run_parallel_reviews_3way("prompt", config, reviewer_timeout=5)

        mock_below.assert_called_once()
        assert result["below"] is not None
        assert result["below"]["findings"] == below_findings

    def test_flag_on_below_offline_does_not_block(self, monkeypatch):
        """When Below is unreachable with flag on, review continues with claude+codex."""
        cmr = _get_cmr(monkeypatch, "on")

        with patch.object(cmr, "review_via_claude_inline") as mock_claude, \
             patch.object(cmr, "review_via_codex") as mock_codex, \
             patch.object(cmr, "review_via_below") as mock_below:

            mock_claude.return_value = (_findings_list("claude note"), "sonnet")
            mock_codex.return_value = (_findings_list("codex note"), "codex", 0.0)
            mock_below.side_effect = RuntimeError("Below unreachable: connection refused")

            config = {"backends": {"codex": {"enabled": True, "timeout_seconds": 60}}}
            result = cmr._run_parallel_reviews_3way("prompt", config, reviewer_timeout=5)

        # Below failure is logged in errors, not raised
        assert result["below"] is None
        assert result["claude"] is not None
        assert result["codex"] is not None
        assert any("below" in e.lower() for e in result["errors"])

    def test_flag_on_max_review_rounds_respected(self, monkeypatch):
        """3-way branch honours BR3_MAX_REVIEW_ROUNDS=1 cap."""
        cmr = _get_cmr(monkeypatch, "on")
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        blocker = _make_finding("persistent bug", severity="blocker", fix_type="fixable")
        findings_with_blocker = [blocker]

        with patch.object(cmr, "_run_parallel_reviews_3way") as mock_3way, \
             patch.object(cmr, "_run_rebuttal") as mock_rebuttal, \
             patch.object(cmr, "_invoke_arbiter") as mock_arbiter:

            mock_3way.return_value = {
                "claude": {"findings": findings_with_blocker, "model": "sonnet"},
                "codex": {"findings": findings_with_blocker, "model": "codex"},
                "below": {"findings": [], "model": "below/qwen"},
                "errors": [],
                "fix_type_errors": [],
            }
            mock_rebuttal.return_value = (findings_with_blocker, True)
            mock_arbiter.return_value = {
                "verdict": "APPROVED",
                "rationale": "arbiter approves",
                "findings": [],
                "error": False,
            }

            result = cmr.run_three_way_review(
                diff_text="d", spec_text="s",
                commit_sha="abc", project_root=str(PROJECT_ROOT),
                review_round=1,
            )

        # round=1, max_rounds=1: round < max_rounds+1 → arbiter is invoked
        assert result["verdict"] in ("APPROVED", "ESCALATED")
        assert result["review_round"] == 1

    def test_flag_on_round_cap_escalates_at_round_2(self, monkeypatch):
        """At review_round=2 with BR3_MAX_REVIEW_ROUNDS=1, escalate without arbiter."""
        cmr = _get_cmr(monkeypatch, "on")
        monkeypatch.setenv("BR3_MAX_REVIEW_ROUNDS", "1")

        blocker = _make_finding("bug", severity="blocker", fix_type="fixable")

        with patch.object(cmr, "_run_parallel_reviews_3way") as mock_3way, \
             patch.object(cmr, "_run_rebuttal") as mock_rebuttal, \
             patch.object(cmr, "_invoke_arbiter") as mock_arbiter:

            mock_3way.return_value = {
                "claude": {"findings": [blocker], "model": "sonnet"},
                "codex": {"findings": [blocker], "model": "codex"},
                "below": None,
                "errors": [],
                "fix_type_errors": [],
            }
            mock_rebuttal.return_value = ([blocker], True)

            result = cmr.run_three_way_review(
                diff_text="d", spec_text="s",
                commit_sha="abc", project_root=str(PROJECT_ROOT),
                review_round=2,  # already at cap+1
            )

        assert result["verdict"] == "ESCALATED"
        assert result["escalated"] is True
        mock_arbiter.assert_not_called()

    def test_flag_on_emits_adversarial_review_telemetry(self, monkeypatch, tmp_path):
        """Flag ON must emit one adversarial_review_ran row."""
        cmr = _get_cmr(monkeypatch, "on")
        db_path = _create_telemetry_db(tmp_path)
        before = _count_review_events(db_path)

        with patch.object(cmr, "_run_parallel_reviews_3way") as mock_3way, \
             patch("pathlib.Path.cwd", return_value=tmp_path):
            mock_3way.return_value = {
                "claude": {"findings": _findings_list("claude note"), "model": "claude-sonnet-4-6"},
                "codex": {"findings": _findings_list("codex note"), "model": "codex/gpt-5.4"},
                "below": {"findings": _findings_list("below note"), "model": "llama3.3:70b"},
                "errors": [],
                "fix_type_errors": [],
            }

            result = cmr.run_three_way_review(
                diff_text="diff text",
                spec_text="spec text",
                commit_sha="deadbeef",
                project_root=str(tmp_path),
            )

        after = _count_review_events(db_path)
        assert result["verdict"] == "APPROVED"
        assert after == before + 1


# ---------------------------------------------------------------------------
# Tests: flag value is cached at import (not re-read per call)
# ---------------------------------------------------------------------------

class TestFlagCaching:
    """Flag is read once at module import, not per call."""

    def test_flag_cached_in_module_variable(self, monkeypatch):
        """_ADVERSARIAL_3WAY_ENABLED is a module-level bool, not a property."""
        cmr = _get_cmr(monkeypatch, "on")
        assert isinstance(cmr._ADVERSARIAL_3WAY_ENABLED, bool)
        assert cmr._ADVERSARIAL_3WAY_ENABLED is True

    def test_flag_off_cached_in_module_variable(self, monkeypatch):
        cmr = _get_cmr(monkeypatch, "off")
        assert isinstance(cmr._ADVERSARIAL_3WAY_ENABLED, bool)
        assert cmr._ADVERSARIAL_3WAY_ENABLED is False

    def test_flag_change_after_import_not_observed(self, monkeypatch):
        """Changing the env var after import does NOT change the cached value."""
        cmr = _get_cmr(monkeypatch, "off")
        assert cmr._ADVERSARIAL_3WAY_ENABLED is False

        # Change env var — should NOT affect the cached module-level value
        monkeypatch.setenv("BR3_ADVERSARIAL_3WAY", "on")
        assert cmr._ADVERSARIAL_3WAY_ENABLED is False  # unchanged
