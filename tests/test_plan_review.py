"""
Tests for Phase 6: Dashboard Plan Review

Tests PlanReviewView class and CLI integration for plan review dashboard.
"""

import json
import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from core.dashboard_views import PlanReviewView


# --- Fixtures ---

@pytest.fixture
def plan_dir(tmp_path):
    """Create a temp .buildrunner/plans/ directory with a sample plan."""
    plans_dir = tmp_path / ".buildrunner" / "plans"
    plans_dir.mkdir(parents=True)

    plan_content = """# Phase 3: Auth Migration

## Tasks

### 3.1 Add JWT validation to middleware
- WHAT: `src/middleware/auth.ts` — add `validateJWT()` function
- WHY: Requirement AUTH-01 — all API routes require JWT
- VERIFY: test_auth_middleware.test.ts::validates JWT tokens

### 3.2 Update user session store
- WHAT: `src/stores/session.ts` — modify `refreshSession()` to use new token format
- WHY: Requirement AUTH-02 — session persistence across tabs
- VERIFY: test_session.test.ts::refreshes session with new format

### 3.3 Add logout cleanup
- WHAT: `src/auth/logout.ts` — add `cleanupTokens()` function
- WHY: Requirement AUTH-03 — clean logout clears all tokens
- VERIFY: test_logout.test.ts::cleans up tokens on logout
"""
    (plans_dir / "phase-3-plan.md").write_text(plan_content)
    return tmp_path


@pytest.fixture
def adversarial_dir(tmp_path):
    """Create adversarial findings JSON."""
    plans_dir = tmp_path / ".buildrunner" / "plans"
    plans_dir.mkdir(parents=True)

    findings = [
        {"finding": "validateJWT references non-existent jose library", "severity": "blocker"},
        {"finding": "refreshSession lacks error handling for expired tokens", "severity": "warning"},
        {"finding": "Consider adding rate limiting to auth endpoints", "severity": "note"},
    ]
    (plans_dir / "adversarial-phase-3.json").write_text(json.dumps(findings))
    return tmp_path


@pytest.fixture
def full_review_dir(plan_dir, adversarial_dir):
    """Directory with both plan and adversarial findings."""
    # Copy adversarial file to plan_dir
    adv_src = adversarial_dir / ".buildrunner" / "plans" / "adversarial-phase-3.json"
    adv_dst = plan_dir / ".buildrunner" / "plans" / "adversarial-phase-3.json"
    adv_dst.write_text(adv_src.read_text())
    return plan_dir


# --- PlanReviewView Tests ---

class TestPlanReviewView:
    """Test PlanReviewView data extraction methods."""

    def test_init_finds_latest_plan(self, plan_dir):
        """PlanReviewView finds the latest plan file."""
        view = PlanReviewView(plan_dir)
        assert view.plan_file is not None
        assert "phase-3-plan.md" in str(view.plan_file)

    def test_init_no_plans_dir(self, tmp_path):
        """PlanReviewView handles missing plans directory."""
        view = PlanReviewView(tmp_path)
        assert view.plan_file is None

    def test_get_task_table_data(self, plan_dir):
        """Parses plan file into structured task rows."""
        view = PlanReviewView(plan_dir)
        tasks = view.get_task_table_data()

        assert len(tasks) == 3
        assert tasks[0]["id"] == "3.1"
        assert "validateJWT" in tasks[0]["what"]
        assert "AUTH-01" in tasks[0]["why"]
        assert "test_auth_middleware" in tasks[0]["verify"]

    def test_get_adversarial_data(self, full_review_dir):
        """Reads and sorts adversarial findings — blockers first."""
        view = PlanReviewView(full_review_dir)
        findings = view.get_adversarial_data()

        assert len(findings) == 3
        # Blockers sorted to top
        assert findings[0]["severity"] == "blocker"
        assert findings[1]["severity"] == "warning"
        assert findings[2]["severity"] == "note"

    def test_get_adversarial_data_no_file(self, plan_dir):
        """Returns empty list when no adversarial file exists."""
        view = PlanReviewView(plan_dir)
        findings = view.get_adversarial_data()
        assert findings == []

    def test_get_test_baseline_data_offline(self, plan_dir):
        """Returns empty dict when Walter is offline."""
        view = PlanReviewView(plan_dir)
        with patch("core.dashboard_views.PlanReviewView._query_walter") as mock_walter:
            mock_walter.return_value = None
            baseline = view.get_test_baseline_data()
            assert baseline == {}

    def test_get_historical_data_offline(self, plan_dir):
        """Returns empty list when Lockwood is offline."""
        view = PlanReviewView(plan_dir)
        with patch("core.dashboard_views.PlanReviewView._query_lockwood") as mock_lockwood:
            mock_lockwood.return_value = None
            history = view.get_historical_data()
            assert history == []

    @patch("core.dashboard_views.PlanReviewView._query_lockwood")
    def test_get_historical_data_limits_to_3(self, mock_lockwood, plan_dir):
        """Historical outcomes capped at 3."""
        mock_lockwood.return_value = [
            {"plan_text": f"plan {i}", "outcome": "pass", "accuracy_pct": 90.0, "drift_notes": ""}
            for i in range(5)
        ]
        view = PlanReviewView(plan_dir)
        history = view.get_historical_data()
        assert len(history) <= 3

    def test_get_code_health_data(self, plan_dir):
        """Returns health data for planned files."""
        view = PlanReviewView(plan_dir)
        health = view.get_code_health_data()
        # Should return a dict of file → health score (or empty if files don't exist)
        assert isinstance(health, dict)

    def test_graceful_degradation_all_offline(self, full_review_dir):
        """Plan + adversarial always shown even when cluster offline."""
        view = PlanReviewView(full_review_dir)
        tasks = view.get_task_table_data()
        findings = view.get_adversarial_data()

        # These should always work — no cluster dependency
        assert len(tasks) == 3
        assert len(findings) == 3


class TestPlanReviewActions:
    """Test plan review action methods."""

    def test_get_actions(self, plan_dir):
        """Returns available actions: approve, revise, reject."""
        view = PlanReviewView(plan_dir)
        actions = view.get_actions()
        action_names = [a["name"] for a in actions]
        assert "approve" in action_names
        assert "revise" in action_names
        assert "reject" in action_names
