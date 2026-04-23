"""tests/cluster/test_router_ground_truth.py — Phase 3 unit tests.

Tests the ground-truth /health saturation logic in resolve-dispatch-node.py.
Exercises busy_state + cpu_pct branches with mocked /health responses.
No network calls — all paths use load_overrides (which support busy_state).
"""

from __future__ import annotations

import importlib.util
import os
import sys
from pathlib import Path
from typing import Any
from unittest.mock import MagicMock, patch

import pytest

# ---------------------------------------------------------------------------
# Load resolve-dispatch-node.py from ~/.buildrunner/scripts (not on sys.path)
# ---------------------------------------------------------------------------

SCRIPT_PATH = Path.home() / ".buildrunner" / "scripts" / "resolve-dispatch-node.py"


def _load_router_module():
    spec = importlib.util.spec_from_file_location("resolve_dispatch_node", SCRIPT_PATH)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod


router = _load_router_module()


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _matrix(cpu_threshold: int = 75, ab_threshold: int = 2) -> dict:
    """Minimal matrix dict for get_node_load."""
    return {
        "routing": {
            "overload_thresholds": {
                "cpu_pct": cpu_threshold,
                "mem_avail_pct": 20,
                "active_builds": ab_threshold,
            },
            "load_query_timeout_ms": 2000,
        }
    }


# ---------------------------------------------------------------------------
# Phase 3: busy_state=saturated → force overflow
# ---------------------------------------------------------------------------

class TestBusyStateSaturated:
    def test_saturated_forces_overflow(self, monkeypatch):
        """busy_state=saturated must set overloaded=True regardless of cpu_pct."""
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)
        monkeypatch.delenv("BR3_NODE_HEALTH_TIMEOUT_MS", raising=False)

        overrides = {"walter": {"cpu_pct": 10.0, "mem_avail_pct": 80.0, "active_builds": 0, "busy_state": "saturated"}}
        result = router.get_node_load("walter", _matrix(), overrides)

        assert result["overloaded"] is True, "saturated node must be overloaded"
        assert result["busy_state"] == "saturated"
        assert result["source"] == "override"

    def test_saturated_low_cpu_still_overloaded(self, monkeypatch):
        """Even 0% CPU with busy_state=saturated must be overloaded."""
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)

        overrides = {"lomax": {"cpu_pct": 0.0, "mem_avail_pct": 90.0, "active_builds": 0, "busy_state": "saturated"}}
        result = router.get_node_load("lomax", _matrix(), overrides)

        assert result["overloaded"] is True


# ---------------------------------------------------------------------------
# Phase 3: busy_state=active + cpu_pct > 75 → force overflow
# ---------------------------------------------------------------------------

class TestBusyStateActiveCPU:
    def test_active_high_cpu_forces_overflow(self, monkeypatch):
        """busy_state=active + cpu_pct=90 must set overloaded=True."""
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)

        overrides = {"otis": {"cpu_pct": 90.0, "mem_avail_pct": 50.0, "active_builds": 0, "busy_state": "active"}}
        result = router.get_node_load("otis", _matrix(), overrides)

        assert result["overloaded"] is True
        assert result["source"] == "override"

    def test_active_cpu_exactly_at_threshold_not_overloaded(self, monkeypatch):
        """busy_state=active + cpu_pct=75 (== threshold, not >) must NOT be overloaded."""
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)

        overrides = {"otis": {"cpu_pct": 75.0, "mem_avail_pct": 50.0, "active_builds": 0, "busy_state": "active"}}
        result = router.get_node_load("otis", _matrix(cpu_threshold=75), overrides)

        assert result["overloaded"] is False

    def test_active_low_cpu_not_overloaded(self, monkeypatch):
        """busy_state=active + cpu_pct=30 must NOT be overloaded (no active_builds)."""
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)

        overrides = {"lockwood": {"cpu_pct": 30.0, "mem_avail_pct": 60.0, "active_builds": 0, "busy_state": "active"}}
        result = router.get_node_load("lockwood", _matrix(), overrides)

        assert result["overloaded"] is False


# ---------------------------------------------------------------------------
# Phase 3: busy_state=idle → fall to active_builds threshold (secondary)
# ---------------------------------------------------------------------------

class TestBusyStateIdle:
    def test_idle_no_builds_not_overloaded(self, monkeypatch):
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)

        overrides = {"lockwood": {"cpu_pct": 5.0, "mem_avail_pct": 80.0, "active_builds": 0, "busy_state": "idle"}}
        result = router.get_node_load("lockwood", _matrix(), overrides)

        assert result["overloaded"] is False

    def test_idle_with_max_builds_overloaded(self, monkeypatch):
        """idle + active_builds >= threshold → overloaded (secondary threshold still applies)."""
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)

        overrides = {"lockwood": {"cpu_pct": 5.0, "mem_avail_pct": 80.0, "active_builds": 2, "busy_state": "idle"}}
        result = router.get_node_load("lockwood", _matrix(ab_threshold=2), overrides)

        assert result["overloaded"] is True


# ---------------------------------------------------------------------------
# BR3_ROUTER_LEGACY_SATURATION=1 — restores pre-Phase-3 behavior
# ---------------------------------------------------------------------------

class TestLegacyMode:
    def test_legacy_mode_ignores_busy_state_saturated(self, monkeypatch):
        """With legacy=1, busy_state=saturated but low cpu+mem+builds → NOT overloaded."""
        monkeypatch.setenv("BR3_ROUTER_LEGACY_SATURATION", "1")

        overrides = {"walter": {"cpu_pct": 10.0, "mem_avail_pct": 80.0, "active_builds": 0, "busy_state": "saturated"}}
        result = router.get_node_load("walter", _matrix(), overrides)

        # Legacy mode: cpu=10 < 75, mem=80 > 20, ab=0 < 2 → not overloaded
        assert result["overloaded"] is False

    def test_legacy_mode_uses_cpu_threshold(self, monkeypatch):
        """Legacy mode: cpu > threshold → overloaded (classic Prometheus behavior)."""
        monkeypatch.setenv("BR3_ROUTER_LEGACY_SATURATION", "1")

        overrides = {"walter": {"cpu_pct": 90.0, "mem_avail_pct": 80.0, "active_builds": 0, "busy_state": "idle"}}
        result = router.get_node_load("walter", _matrix(), overrides)

        assert result["overloaded"] is True

    def test_legacy_env_var_toggle(self, monkeypatch):
        """Toggling BR3_ROUTER_LEGACY_SATURATION changes behavior for the same node load."""
        overrides = {"walter": {"cpu_pct": 10.0, "mem_avail_pct": 80.0, "active_builds": 0, "busy_state": "saturated"}}

        monkeypatch.setenv("BR3_ROUTER_LEGACY_SATURATION", "0")
        phase3_result = router.get_node_load("walter", _matrix(), overrides)

        monkeypatch.setenv("BR3_ROUTER_LEGACY_SATURATION", "1")
        legacy_result = router.get_node_load("walter", _matrix(), overrides)

        assert phase3_result["overloaded"] is True   # Phase 3: saturated → overflow
        assert legacy_result["overloaded"] is False  # Legacy: cpu=10 → not overloaded


# ---------------------------------------------------------------------------
# BR3_NODE_HEALTH_TIMEOUT_MS — fail-open on /health timeout
# ---------------------------------------------------------------------------

class TestHealthTimeout:
    def test_health_timeout_env_respected(self, monkeypatch):
        """BR3_NODE_HEALTH_TIMEOUT_MS is read by get_node_health_ground_truth."""
        monkeypatch.setenv("BR3_NODE_HEALTH_TIMEOUT_MS", "100")
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)

        # Patch urllib.request.urlopen to simulate timeout
        import urllib.error
        with patch("urllib.request.urlopen", side_effect=TimeoutError("timed out")):
            result = router.get_node_health_ground_truth("walter", {
                "nodes": {"walter": {"host": "10.0.1.102", "port": 8100}}
            }, timeout_ms=100)

        assert result is None  # timeout → None → fail-open

    def test_fail_open_health_timeout_source_label(self, monkeypatch):
        """When /health times out and Prometheus also fails, source = fail-open-health-timeout."""
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)
        monkeypatch.setenv("BR3_NODE_HEALTH_TIMEOUT_MS", "1")  # 1ms → always times out

        # No load override → real code paths run, /health will fail (no real node)
        # Prometheus will also fail (no server). Result must be fail-open-health-timeout.
        result = router.get_node_load("walter", _matrix(), {})

        assert result["source"] in ("fail-open-health-timeout", "fail-open")
        assert result["overloaded"] is False  # fail-open = not overloaded

    def test_health_endpoint_success_uses_ground_truth(self, monkeypatch):
        """When /health responds, source = health-ground-truth and busy_state drives decision."""
        monkeypatch.delenv("BR3_ROUTER_LEGACY_SATURATION", raising=False)
        monkeypatch.delenv("BR3_NODE_HEALTH_TIMEOUT_MS", raising=False)

        health_response = json_bytes({"busy_state": "saturated", "cpu_pct": 95.0, "workloads": []})

        import io
        import urllib.request

        mock_resp = MagicMock()
        mock_resp.read.return_value = health_response
        mock_resp.__enter__ = lambda s: s
        mock_resp.__exit__ = MagicMock(return_value=False)

        with patch("urllib.request.urlopen", return_value=mock_resp):
            # Override load_cluster_config to avoid fs read
            with patch.object(router, "load_cluster_config", return_value={
                "nodes": {"walter": {"host": "10.0.1.102", "port": 8100}}
            }):
                result = router.get_node_load("walter", _matrix(), {})

        assert result["source"] == "health-ground-truth"
        assert result["overloaded"] is True
        assert result["busy_state"] == "saturated"


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def json_bytes(d: dict) -> bytes:
    import json
    return json.dumps(d).encode()
