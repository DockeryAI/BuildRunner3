"""Phase 5 autopilot classifier — below-route.sh dispatch gate.

The "autopilot classifier" is the bash routing logic in
`~/.buildrunner/scripts/below-route.sh`: it decides whether a given
skill invocation gets sent to Below (Ollama) or passes through to
Claude. These tests lock the contract surface so Phase 13 flip cannot
accidentally change dispatch semantics.

Contract (from BUILD_cluster-max.md Phase 5):
  - `BR3_RUNTIME_OLLAMA=off` → exits 2 regardless of mode (gate closed).
  - `BR3_RUNTIME_OLLAMA=on` + no prompt → exits 2 (usage error).
  - `--mode` values `summary | draft | review` all recognized.
  - Script exits 2 (not crash) when Below is unreachable, so callers
    can silently fall back to Claude.
"""

from __future__ import annotations

import os
import subprocess
from pathlib import Path

import pytest

SCRIPT = Path.home() / ".buildrunner" / "scripts" / "below-route.sh"


pytestmark = pytest.mark.skipif(
    not SCRIPT.exists(), reason="below-route.sh not installed in this environment"
)


def _run(env_overrides: dict[str, str], args: list[str], timeout: float = 10.0) -> subprocess.CompletedProcess:
    env = os.environ.copy()
    env.update(env_overrides)
    return subprocess.run(
        ["bash", str(SCRIPT), *args],
        capture_output=True,
        text=True,
        env=env,
        timeout=timeout,
    )


def test_flag_off_exits_2() -> None:
    r = _run({"BR3_RUNTIME_OLLAMA": "off"}, ["--mode", "draft", "hello"])
    assert r.returncode == 2, f"expected exit=2 when gate off, got {r.returncode}: {r.stderr}"


def test_flag_unset_exits_2() -> None:
    env = os.environ.copy()
    env.pop("BR3_RUNTIME_OLLAMA", None)
    r = subprocess.run(
        ["bash", str(SCRIPT), "--mode", "draft", "hello"],
        capture_output=True,
        text=True,
        env=env,
        timeout=10,
    )
    assert r.returncode == 2, "unset flag must be treated as off (exit 2)"


def test_flag_on_summary_mode_recognized() -> None:
    r = _run({"BR3_RUNTIME_OLLAMA": "on"}, ["--mode", "summary", "summarize this"])
    assert r.returncode in (0, 2), (
        "summary mode with flag on must exit 0 (routed) or 2 (Below offline),"
        f" never crash — got {r.returncode}: {r.stderr}"
    )


def test_flag_on_draft_mode_recognized() -> None:
    r = _run({"BR3_RUNTIME_OLLAMA": "on"}, ["--mode", "draft", "draft a fix for RLS"])
    assert r.returncode in (0, 2), (
        f"draft mode with flag on should return 0 or 2, got {r.returncode}: {r.stderr}"
    )


def test_flag_on_review_mode_recognized() -> None:
    r = _run({"BR3_RUNTIME_OLLAMA": "on"}, ["--mode", "review", "review this diff"])
    assert r.returncode in (0, 2), (
        f"review mode with flag on should return 0 or 2, got {r.returncode}: {r.stderr}"
    )


def test_flag_on_no_prompt_exits_2() -> None:
    r = _run({"BR3_RUNTIME_OLLAMA": "on"}, ["--mode", "summary"])
    assert r.returncode == 2, "missing prompt must exit 2, not crash"


def test_help_flag_exits_0() -> None:
    r = _run({"BR3_RUNTIME_OLLAMA": "on"}, ["--help"])
    assert r.returncode == 0
    assert "Usage:" in r.stderr or "Usage:" in r.stdout


def test_script_is_executable_and_not_crash_on_bad_flag() -> None:
    r = _run({"BR3_RUNTIME_OLLAMA": "on"}, ["--bogus-flag-nobody-should-pass", "x"])
    # The script is tolerant of unknown positional args; the main contract
    # is that it never returns a non-(0|2) status on malformed input.
    assert r.returncode in (0, 2), f"unexpected exit={r.returncode} stderr={r.stderr}"
