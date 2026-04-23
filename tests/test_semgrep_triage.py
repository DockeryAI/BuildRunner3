"""
tests/test_semgrep_triage.py

Unit tests for core.cluster.below.semgrep_triage.
Semgrep subprocess and Below API calls are mocked — no real tools required.
"""

from __future__ import annotations

import json
from unittest.mock import patch, MagicMock

import pytest

from core.cluster.below.semgrep_triage import (
    SemgrepFinding,
    SemgrepTriageResult,
    SEMGREP_RULESETS,
    OWASP_CATEGORIES,
    check_owasp_coverage,
    triage_diff,
    _run_semgrep,
    _classify_via_below,
    _extract_changed_files,
)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SAMPLE_DIFF = """\
diff --git a/app.py b/app.py
index abc..def 100644
--- a/app.py
+++ b/app.py
@@ -1,5 +1,10 @@
+def get_user(user_id):
+    query = f"SELECT * FROM users WHERE id = {user_id}"
+    return db.execute(query)
+
 def process():
     pass
"""

CLEAN_DIFF = """\
diff --git a/utils.py b/utils.py
--- a/utils.py
+++ b/utils.py
@@ -1,3 +1,5 @@
+def add(a, b):
+    return a + b
"""


def _mock_below_clean():
    """Patch _classify_via_below to return 'clean'."""
    import core.cluster.below.semgrep_triage as mod
    return patch.object(mod, "_classify_via_below", return_value="clean")


def _mock_below_flagged():
    import core.cluster.below.semgrep_triage as mod
    return patch.object(mod, "_classify_via_below", return_value="flagged")


def _mock_semgrep_no_findings():
    import core.cluster.below.semgrep_triage as mod
    return patch.object(mod, "_run_semgrep", return_value=[])


def _mock_semgrep_finding(rule_id="injection.sql", severity="ERROR"):
    finding = SemgrepFinding(rule_id=rule_id, message="SQL injection", severity=severity)
    import core.cluster.below.semgrep_triage as mod
    return patch.object(mod, "_run_semgrep", return_value=[finding])


def _mock_semgrep_unavailable():
    import core.cluster.below.semgrep_triage as mod
    return patch.object(mod, "_run_semgrep", return_value=None)


# ---------------------------------------------------------------------------
# Rollback flag
# ---------------------------------------------------------------------------


class TestRollbackFlag:
    def test_rollback_returns_flagged(self):
        import core.cluster.below.semgrep_triage as mod
        orig = mod._PREFILTER_ENABLED
        mod._PREFILTER_ENABLED = False
        try:
            result = triage_diff(SAMPLE_DIFF)
            assert result.severity == "flagged"
            assert "off" in result.skip_reason.lower()
        finally:
            mod._PREFILTER_ENABLED = orig

    def test_rollback_doesnt_call_semgrep(self):
        import core.cluster.below.semgrep_triage as mod
        orig = mod._PREFILTER_ENABLED
        mod._PREFILTER_ENABLED = False
        try:
            with patch.object(mod, "_run_semgrep") as mock_sg:
                triage_diff(SAMPLE_DIFF)
                mock_sg.assert_not_called()
        finally:
            mod._PREFILTER_ENABLED = orig


# ---------------------------------------------------------------------------
# Empty diff
# ---------------------------------------------------------------------------


class TestEmptyDiff:
    def test_empty_diff_is_clean(self):
        result = triage_diff("")
        assert result.severity == "clean"

    def test_whitespace_diff_is_clean(self):
        result = triage_diff("   \n  ")
        assert result.severity == "clean"


# ---------------------------------------------------------------------------
# Large diff cap
# ---------------------------------------------------------------------------


class TestLargeDiffCap:
    def test_diff_too_large_returns_flagged(self):
        import core.cluster.below.semgrep_triage as mod
        large_diff = "+" * (mod.MAX_DIFF_CHARS + 1)
        result = triage_diff(large_diff)
        assert result.severity == "flagged"
        assert "large" in result.skip_reason.lower()


# ---------------------------------------------------------------------------
# Semgrep unavailable — fail-open
# ---------------------------------------------------------------------------


class TestSemgrepUnavailable:
    def test_semgrep_not_found_returns_flagged(self):
        with _mock_semgrep_unavailable():
            result = triage_diff(CLEAN_DIFF)
        assert result.severity == "flagged"
        assert not result.semgrep_ran

    def test_semgrep_unavailable_skip_reason(self):
        with _mock_semgrep_unavailable():
            result = triage_diff(CLEAN_DIFF)
        assert "unavailable" in result.skip_reason.lower()


# ---------------------------------------------------------------------------
# Clean path
# ---------------------------------------------------------------------------


class TestCleanPath:
    def test_no_findings_and_below_clean_returns_clean(self):
        with _mock_semgrep_no_findings(), _mock_below_clean():
            result = triage_diff(CLEAN_DIFF)
        assert result.severity == "clean"
        assert result.is_clean

    def test_clean_result_has_should_full_review_false(self):
        with _mock_semgrep_no_findings(), _mock_below_clean():
            result = triage_diff(CLEAN_DIFF)
        assert not result.should_full_review

    def test_clean_result_semgrep_ran_true(self):
        with _mock_semgrep_no_findings(), _mock_below_clean():
            result = triage_diff(CLEAN_DIFF)
        assert result.semgrep_ran


# ---------------------------------------------------------------------------
# Flagged path
# ---------------------------------------------------------------------------


class TestFlaggedPath:
    def test_error_finding_returns_flagged(self):
        with _mock_semgrep_finding(severity="ERROR"), _mock_below_flagged():
            result = triage_diff(SAMPLE_DIFF)
        assert result.severity == "flagged"
        assert result.should_full_review

    def test_flagged_result_has_findings(self):
        with _mock_semgrep_finding(severity="ERROR"), _mock_below_flagged():
            result = triage_diff(SAMPLE_DIFF)
        assert len(result.findings) == 1
        assert result.findings[0].rule_id == "injection.sql"


# ---------------------------------------------------------------------------
# Below offline fallback
# ---------------------------------------------------------------------------


class TestBelowOffline:
    def test_no_findings_below_offline_returns_clean(self):
        """No findings + Below offline → classify as clean by heuristic."""
        import core.cluster.below.semgrep_triage as mod
        with _mock_semgrep_no_findings():
            with patch.object(mod, "_classify_via_below", return_value=None):
                result = triage_diff(CLEAN_DIFF)
        assert result.severity == "clean"

    def test_error_finding_below_offline_returns_flagged(self):
        """ERROR-level finding + Below offline → flagged by heuristic."""
        import core.cluster.below.semgrep_triage as mod
        finding = SemgrepFinding(rule_id="r", message="m", severity="ERROR")
        with patch.object(mod, "_run_semgrep", return_value=[finding]):
            with patch.object(mod, "_classify_via_below", return_value=None):
                result = triage_diff(SAMPLE_DIFF)
        assert result.severity == "flagged"

    def test_warning_finding_below_offline_returns_minor(self):
        """WARNING finding + Below offline → minor by heuristic."""
        import core.cluster.below.semgrep_triage as mod
        finding = SemgrepFinding(rule_id="r", message="m", severity="WARNING")
        with patch.object(mod, "_run_semgrep", return_value=[finding]):
            with patch.object(mod, "_classify_via_below", return_value=None):
                result = triage_diff(SAMPLE_DIFF)
        assert result.severity == "minor"


# ---------------------------------------------------------------------------
# _extract_changed_files
# ---------------------------------------------------------------------------


class TestExtractChangedFiles:
    def test_extracts_added_lines(self):
        files = _extract_changed_files(CLEAN_DIFF)
        assert "utils.py" in files
        assert "def add(a, b):" in files["utils.py"]

    def test_ignores_removed_lines(self):
        diff_with_removal = (
            "diff --git a/foo.py b/foo.py\n"
            "--- a/foo.py\n"
            "+++ b/foo.py\n"
            "-removed line\n"
            "+added line\n"
        )
        files = _extract_changed_files(diff_with_removal)
        assert "foo.py" in files
        assert "removed line" not in files["foo.py"]
        assert "added line" in files["foo.py"]

    def test_empty_diff_returns_empty(self):
        files = _extract_changed_files("")
        assert files == {}


# ---------------------------------------------------------------------------
# OWASP coverage
# ---------------------------------------------------------------------------


class TestOWASPCoverage:
    def test_owasp_categories_populated(self):
        assert len(OWASP_CATEGORIES) >= 10

    def test_check_owasp_coverage_returns_empty_with_ruleset(self):
        """p/owasp-top-ten in SEMGREP_RULESETS → no uncovered categories."""
        assert "p/owasp-top-ten" in SEMGREP_RULESETS
        uncovered = check_owasp_coverage()
        assert uncovered == set(), f"Uncovered OWASP categories: {uncovered}"

    def test_owasp_injection_in_categories(self):
        assert "injection" in OWASP_CATEGORIES

    def test_owasp_xss_in_categories(self):
        assert "cross-site-scripting" in OWASP_CATEGORIES


# ---------------------------------------------------------------------------
# SemgrepTriageResult properties
# ---------------------------------------------------------------------------


class TestSemgrepTriageResultProperties:
    def test_is_clean_for_clean(self):
        r = SemgrepTriageResult(severity="clean")
        assert r.is_clean
        assert not r.should_full_review

    def test_is_clean_false_for_flagged(self):
        r = SemgrepTriageResult(severity="flagged")
        assert not r.is_clean
        assert r.should_full_review

    def test_minor_should_full_review(self):
        r = SemgrepTriageResult(severity="minor")
        assert r.should_full_review
        assert not r.is_clean


# ---------------------------------------------------------------------------
# ai_code_review.py integration
# ---------------------------------------------------------------------------


class TestAiCodeReviewIntegration:
    """Verify the prefilter is wired into CodeReviewer.review_diff."""

    def test_quick_pass_prompt_shorter_than_full(self):
        from core.ai_code_review import CodeReviewer
        reviewer = CodeReviewer.__new__(CodeReviewer)
        full = reviewer._build_diff_review_prompt("diff text", quick_pass=False)
        quick = reviewer._build_diff_review_prompt("diff text", quick_pass=True)
        assert len(quick) < len(full), "Quick-pass prompt must be shorter than full"

    def test_quick_pass_mentions_semgrep(self):
        from core.ai_code_review import CodeReviewer
        reviewer = CodeReviewer.__new__(CodeReviewer)
        quick = reviewer._build_diff_review_prompt("diff", quick_pass=True)
        assert "semgrep" in quick.lower() or "static analysis" in quick.lower()

    def test_quick_pass_still_covers_logic_bugs(self):
        from core.ai_code_review import CodeReviewer
        reviewer = CodeReviewer.__new__(CodeReviewer)
        quick = reviewer._build_diff_review_prompt("diff", quick_pass=True)
        assert "logic" in quick.lower() or "bug" in quick.lower()

    def test_review_diff_has_semgrep_triage_block(self):
        """review_diff source must reference triage_diff."""
        import inspect
        from core.ai_code_review import CodeReviewer
        src = inspect.getsource(CodeReviewer.review_diff)
        assert "triage_diff" in src or "semgrep_triage" in src
