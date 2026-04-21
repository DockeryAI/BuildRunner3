"""Integration tests: bash runtime-dispatch.sh → Python runtime_registry CLI.

Verifies:
- scripts/runtime-dispatch.sh shells into python -m core.runtime.runtime_registry
- Both paths produce structurally equivalent output for the same spec
- below-route.sh no longer contains direct Ollama curl calls
- BR3_LOCAL_ROUTING flag alias for BR3_RUNTIME_OLLAMA documented
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parent.parent.parent
RUNTIME_DISPATCH_SH = PROJECT_ROOT / "scripts" / "runtime-dispatch.sh"
BELOW_ROUTE_SH = Path.home() / ".buildrunner" / "scripts" / "below-route.sh"


def _run_sh(script: Path, *args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        ["bash", str(script), *args],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(PROJECT_ROOT),
    )


def _run_py_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, "-m", "core.runtime.runtime_registry", *args],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(PROJECT_ROOT),
    )


def _write_spec(content: str) -> Path:
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, prefix="test_spec_"
    )
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


VALID_SPEC = """\
# Test Spec Phase 2 Integration

## Phase 2
builder: claude
task: verify bash-to-python dispatch bridge
"""


# ---------------------------------------------------------------------------
# runtime-dispatch.sh existence and basic shape
# ---------------------------------------------------------------------------


def test_runtime_dispatch_sh_exists() -> None:
    """scripts/runtime-dispatch.sh must exist in the project."""
    assert RUNTIME_DISPATCH_SH.exists(), (
        f"scripts/runtime-dispatch.sh not found at {RUNTIME_DISPATCH_SH}"
    )


def test_runtime_dispatch_sh_is_executable() -> None:
    """scripts/runtime-dispatch.sh must be executable."""
    assert os.access(RUNTIME_DISPATCH_SH, os.X_OK), (
        f"scripts/runtime-dispatch.sh is not executable"
    )


def test_runtime_dispatch_sh_shells_into_python() -> None:
    """runtime-dispatch.sh must contain python -m core.runtime.runtime_registry."""
    content = RUNTIME_DISPATCH_SH.read_text()
    assert "core.runtime.runtime_registry" in content, (
        "runtime-dispatch.sh does not shell into python -m core.runtime.runtime_registry"
    )


# ---------------------------------------------------------------------------
# bash dispatch path: unknown builder exits 2
# ---------------------------------------------------------------------------


def test_bash_unknown_builder_exits_2() -> None:
    """runtime-dispatch.sh must exit 2 for unknown builder."""
    if not RUNTIME_DISPATCH_SH.exists():
        pytest.skip("runtime-dispatch.sh not yet created")
    spec_path = _write_spec(VALID_SPEC)
    try:
        result = _run_sh(RUNTIME_DISPATCH_SH, "notabuilder", str(spec_path),
                         env={"BR3_DISPATCH_DRY_RUN": "1"})
        assert result.returncode == 2, (
            f"Expected exit 2, got {result.returncode}. stderr: {result.stderr}"
        )
    finally:
        spec_path.unlink(missing_ok=True)


def test_bash_missing_spec_exits_3() -> None:
    """runtime-dispatch.sh must exit 3 for missing spec file."""
    if not RUNTIME_DISPATCH_SH.exists():
        pytest.skip("runtime-dispatch.sh not yet created")
    result = _run_sh(RUNTIME_DISPATCH_SH, "claude", "/tmp/no-such-spec-99999.md",
                     env={"BR3_DISPATCH_DRY_RUN": "1"})
    assert result.returncode == 3, (
        f"Expected exit 3, got {result.returncode}. stderr: {result.stderr}"
    )


# ---------------------------------------------------------------------------
# Output equivalence: bash path and Python path produce same structure
# ---------------------------------------------------------------------------


def test_bash_and_python_produce_equivalent_output() -> None:
    """Bash dispatch and Python CLI must produce structurally equivalent JSON.

    Both must include 'status' field. In dry-run mode, both should be success.
    """
    if not RUNTIME_DISPATCH_SH.exists():
        pytest.skip("runtime-dispatch.sh not yet created")
    spec_path = _write_spec(VALID_SPEC)
    try:
        env = {"BR3_DISPATCH_DRY_RUN": "1"}
        bash_result = _run_sh(RUNTIME_DISPATCH_SH, "claude", str(spec_path), env=env)
        py_result = _run_py_cli("execute", "claude", str(spec_path), env=env)

        assert bash_result.returncode == 0, f"bash path failed: {bash_result.stderr}"
        assert py_result.returncode == 0, f"python path failed: {py_result.stderr}"

        bash_data = json.loads(bash_result.stdout.strip())
        py_data = json.loads(py_result.stdout.strip())

        # Both must have 'status' key
        assert "status" in bash_data, f"bash output missing 'status': {bash_data}"
        assert "status" in py_data, f"python output missing 'status': {py_data}"

        # Status values must match
        assert bash_data["status"] == py_data["status"], (
            f"Status mismatch: bash={bash_data['status']} py={py_data['status']}"
        )
    finally:
        spec_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# below-route.sh: no direct Ollama curl
# ---------------------------------------------------------------------------


def test_below_route_sh_no_direct_ollama_curl() -> None:
    """below-route.sh must not contain direct curl to Ollama /api/chat or /api/generate."""
    if not BELOW_ROUTE_SH.exists():
        pytest.skip("below-route.sh not found (cluster node not present)")

    content = BELOW_ROUTE_SH.read_text()

    # Must not have direct Ollama curl patterns
    forbidden_patterns = [
        "/api/chat",
        "/api/generate",
    ]

    # The new below-route.sh should call runtime-dispatch.sh instead
    for pattern in forbidden_patterns:
        assert pattern not in content, (
            f"below-route.sh still contains direct Ollama curl pattern: '{pattern}'\n"
            "Expected: thin wrapper around scripts/runtime-dispatch.sh"
        )


def test_below_route_sh_calls_runtime_dispatch() -> None:
    """below-route.sh must delegate to scripts/runtime-dispatch.sh."""
    if not BELOW_ROUTE_SH.exists():
        pytest.skip("below-route.sh not found (cluster node not present)")

    content = BELOW_ROUTE_SH.read_text()
    assert "runtime-dispatch.sh" in content, (
        "below-route.sh does not call runtime-dispatch.sh. "
        "Expected thin wrapper delegation."
    )


# ---------------------------------------------------------------------------
# Flag alias: BR3_RUNTIME_OLLAMA → BR3_LOCAL_ROUTING
# ---------------------------------------------------------------------------


def test_runtime_dispatch_supports_br3_local_routing() -> None:
    """runtime-dispatch.sh must gate on BR3_LOCAL_ROUTING (canonical flag)."""
    if not RUNTIME_DISPATCH_SH.exists():
        pytest.skip("runtime-dispatch.sh not yet created")
    content = RUNTIME_DISPATCH_SH.read_text()
    assert "BR3_LOCAL_ROUTING" in content, (
        "runtime-dispatch.sh must reference BR3_LOCAL_ROUTING (canonical flag name)"
    )


def test_br3_runtime_ollama_alias_documented_in_agents_md() -> None:
    """AGENTS.md must document BR3_RUNTIME_OLLAMA as deprecated alias for BR3_LOCAL_ROUTING."""
    agents_md = PROJECT_ROOT / "AGENTS.md"
    content = agents_md.read_text()
    # Must mention both the canonical name and the alias relationship
    assert "BR3_LOCAL_ROUTING" in content, "AGENTS.md missing canonical flag BR3_LOCAL_ROUTING"
    # Alias documentation should mention the old name in context of migration
    assert "BR3_RUNTIME_OLLAMA" in content, "AGENTS.md should mention BR3_RUNTIME_OLLAMA alias"
