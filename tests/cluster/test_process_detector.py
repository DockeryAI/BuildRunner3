"""Unit tests for core.cluster.process_detector."""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import patch

import pytest

from core.cluster import process_detector
from core.cluster.process_detector import (
    MATCHERS,
    WorkloadMatcher,
    compute_busy_state,
    sample_host,
    warmup,
)


# --------------------------------------------------------------------------- #
# Matcher tests
# --------------------------------------------------------------------------- #

def test_matchers_cover_expected_workloads():
    names = {m.name for m in MATCHERS}
    assert {"vitest", "playwright", "tsc", "ollama"}.issubset(names)


def test_match_ignore_wins_over_pattern():
    # `vitest --version` would match by pattern but is disqualified by ignore
    m = WorkloadMatcher(name="vitest", patterns=("vitest",), ignore=("--version",))
    assert process_detector._match("node", "node /bin/vitest --version", m) is False


def test_match_pattern_case_insensitive():
    m = WorkloadMatcher(name="ollama", patterns=("ollama",))
    assert process_detector._match("Ollama.app/Contents/MacOS/Ollama", "", m) is True


# --------------------------------------------------------------------------- #
# busy_state thresholds — table-driven per spec
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize(
    "cpu_pct,load_1m,cpu_count,workloads,expected",
    [
        # idle: <30% CPU, no workloads, load below cores*0.75
        (5.0, 0.1, 8, [], "idle"),
        (29.9, 5.0, 8, [], "idle"),
        # active: 30-75% CPU
        (30.0, 1.0, 8, [], "active"),
        (74.9, 1.0, 8, [], "active"),
        # active: ≥1 workload even when CPU is tiny
        (3.0, 0.1, 8, [{"name": "vitest", "pid": 1}], "active"),
        # active: load > cores*0.75 but <=cores
        (10.0, 7.0, 8, [], "active"),
        # saturated: cpu > 75%
        (75.1, 0.0, 8, [], "saturated"),
        # saturated: load > cores
        (10.0, 8.5, 8, [], "saturated"),
        # saturated beats active when both conditions present
        (90.0, 1.0, 8, [{"name": "tsc", "pid": 2}], "saturated"),
    ],
)
def test_compute_busy_state_matrix(cpu_pct, load_1m, cpu_count, workloads, expected):
    assert compute_busy_state(cpu_pct, load_1m, cpu_count, workloads) == expected


def test_compute_busy_state_zero_cpu_count_defaults_to_one():
    # Guard against a degenerate platform that reports cpu_count=0
    assert compute_busy_state(10.0, 2.0, 0, []) in {"active", "saturated"}


# --------------------------------------------------------------------------- #
# warmup is idempotent and primes module-level flag
# --------------------------------------------------------------------------- #

def test_warmup_sets_flag():
    process_detector._WARMED_UP = False
    warmup()
    assert process_detector._WARMED_UP is True
    # Second call must not raise
    warmup()


# --------------------------------------------------------------------------- #
# sample_host returns the expected shape
# --------------------------------------------------------------------------- #

def test_sample_host_shape(monkeypatch):
    # Stub psutil to avoid filesystem/proc iteration being flaky
    def fake_cpu_percent(interval=None):
        return 42.0

    def fake_virtual_memory():
        return SimpleNamespace(percent=60.0)

    def fake_cpu_count():
        return 8

    def fake_getloadavg():
        return (2.5, 2.0, 1.5)

    def fake_process_iter(attrs=None):
        return iter([])

    monkeypatch.setattr(process_detector.psutil, "cpu_percent", fake_cpu_percent)
    monkeypatch.setattr(process_detector.psutil, "virtual_memory", fake_virtual_memory)
    monkeypatch.setattr(process_detector.psutil, "cpu_count", fake_cpu_count)
    monkeypatch.setattr(process_detector.psutil, "getloadavg", fake_getloadavg)
    monkeypatch.setattr(process_detector.psutil, "process_iter", fake_process_iter)

    out = sample_host()
    assert out["cpu_pct"] == 42.0
    assert out["load_1m"] == 2.5
    assert out["mem_avail_pct"] == 40.0
    assert out["cpu_count"] == 8
    assert out["busy_state"] == "active"  # 42% CPU
    assert out["workloads"] == []
    assert out["detector_version"] == 1


def test_sample_host_detects_vitest_workload(monkeypatch):
    class FakeProc:
        def __init__(self, pid, name, cmdline, ctime, cwd=None):
            self.pid = pid
            self.info = {
                "pid": pid,
                "name": name,
                "cmdline": cmdline,
                "create_time": ctime,
            }
            self._cwd = cwd

        def cpu_percent(self, interval=None):
            return 55.0

        def cwd(self):
            return self._cwd

    fake_procs = [
        FakeProc(
            pid=12345,
            name="node",
            cmdline=["node", "/usr/local/bin/vitest", "run"],
            ctime=1700000000.0,
            cwd="/Users/x/Projects/Synapse",
        ),
    ]

    def fake_process_iter(attrs=None):
        return iter(fake_procs)

    monkeypatch.setattr(process_detector, "_WARMED_UP", True)
    monkeypatch.setattr(process_detector.psutil, "cpu_percent", lambda interval=None: 55.0)
    monkeypatch.setattr(process_detector.psutil, "virtual_memory", lambda: SimpleNamespace(percent=30.0))
    monkeypatch.setattr(process_detector.psutil, "cpu_count", lambda: 8)
    monkeypatch.setattr(process_detector.psutil, "getloadavg", lambda: (1.0, 1.0, 1.0))
    monkeypatch.setattr(process_detector.psutil, "process_iter", fake_process_iter)
    # Patch the roots so /Users/x/Projects is recognized
    monkeypatch.setattr(
        process_detector,
        "_project_roots",
        lambda: ["/Users/x/Projects"],
    )

    out = sample_host()
    assert out["busy_state"] == "active"
    assert len(out["workloads"]) == 1
    wl = out["workloads"][0]
    assert wl["name"] == "vitest"
    assert wl["pid"] == 12345
    assert wl["cpu_pct"] == 55.0
    assert wl["project"] == "Synapse"
    assert wl["started_at"].endswith("Z")


def test_sample_host_ignores_zombie_processes(monkeypatch):
    import psutil as real_psutil

    class ZombieProc:
        pid = 1
        info = {"pid": 1, "name": "vitest", "cmdline": ["vitest"], "create_time": 0}

        def cpu_percent(self, interval=None):
            raise real_psutil.NoSuchProcess(pid=1)

    monkeypatch.setattr(process_detector, "_WARMED_UP", True)
    monkeypatch.setattr(process_detector.psutil, "cpu_percent", lambda interval=None: 10.0)
    monkeypatch.setattr(process_detector.psutil, "virtual_memory", lambda: SimpleNamespace(percent=50.0))
    monkeypatch.setattr(process_detector.psutil, "cpu_count", lambda: 4)
    monkeypatch.setattr(process_detector.psutil, "getloadavg", lambda: (0.5, 0.5, 0.5))
    monkeypatch.setattr(
        process_detector.psutil,
        "process_iter",
        lambda attrs=None: iter([ZombieProc()]),
    )

    out = sample_host()
    assert out["workloads"] == []
    assert out["busy_state"] == "idle"
