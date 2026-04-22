"""Tests for runtime_registry CLI entry point.

python -m core.runtime.runtime_registry execute <builder> <spec_path>

Exit codes:
  0 — success
  2 — unknown builder
  3 — malformed spec / spec file not found
"""

from __future__ import annotations

import json
import sqlite3
import subprocess
import sys
import tempfile
from pathlib import Path

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _run_cli(*args: str, env: dict | None = None) -> subprocess.CompletedProcess:
    """Run runtime_registry as a module CLI."""
    import os
    full_env = {**os.environ, **(env or {})}
    return subprocess.run(
        [sys.executable, "-m", "core.runtime.runtime_registry", *args],
        capture_output=True,
        text=True,
        env=full_env,
        cwd=str(Path(__file__).parent.parent.parent),
    )


def _write_spec(content: str) -> Path:
    """Write a spec file and return the path."""
    tmp = tempfile.NamedTemporaryFile(
        mode="w", suffix=".md", delete=False, prefix="test_spec_"
    )
    tmp.write(content)
    tmp.close()
    return Path(tmp.name)


def _create_telemetry_db(project_root: Path) -> Path:
    db_path = project_root / ".buildrunner" / "telemetry.db"
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
                session_id TEXT,
                metadata TEXT,
                success BOOLEAN DEFAULT 1
            );
            """
        )
        conn.commit()
    finally:
        conn.close()
    return db_path


VALID_SPEC = """\
# Test Spec

## Phase 1
builder: claude
task: run a simple test
"""


# ---------------------------------------------------------------------------
# Exit code 2 — unknown builder
# ---------------------------------------------------------------------------


def test_unknown_builder_exits_2() -> None:
    """CLI must exit 2 when the builder name is not registered."""
    spec_path = _write_spec(VALID_SPEC)
    try:
        result = _run_cli("execute", "notabuilder", str(spec_path))
        assert result.returncode == 2, (
            f"Expected exit 2 for unknown builder, got {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
    finally:
        spec_path.unlink(missing_ok=True)


def test_unknown_builder_prints_error_message() -> None:
    """CLI must print a useful error for unknown builder."""
    spec_path = _write_spec(VALID_SPEC)
    try:
        result = _run_cli("execute", "notabuilder", str(spec_path))
        assert "notabuilder" in result.stderr.lower() or "unknown" in result.stderr.lower(), (
            f"Expected error message mentioning builder name. stderr: {result.stderr}"
        )
    finally:
        spec_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Exit code 3 — malformed / missing spec
# ---------------------------------------------------------------------------


def test_missing_spec_file_exits_3() -> None:
    """CLI must exit 3 when spec_path does not exist."""
    result = _run_cli("execute", "claude", "/tmp/nonexistent-spec-99999.md")
    assert result.returncode == 3, (
        f"Expected exit 3 for missing spec, got {result.returncode}\n"
        f"stderr: {result.stderr}"
    )


def test_missing_spec_file_emits_runtime_dispatched_failure(tmp_path: Path) -> None:
    """Malformed spec path must record runtime_dispatched with success=0."""
    project_root = tmp_path / "runtime-dispatch-failure"
    telemetry_db = _create_telemetry_db(project_root)

    result = _run_cli(
        "execute",
        "claude",
        "/tmp/nonexistent-spec-99999.md",
        env={"BR3_PROJECT_ROOT": str(project_root)},
    )

    assert result.returncode == 3

    conn = sqlite3.connect(str(telemetry_db))
    try:
        row = conn.execute(
            "SELECT success, metadata FROM events WHERE event_type='runtime_dispatched' ORDER BY id DESC LIMIT 1"
        ).fetchone()
    finally:
        conn.close()

    assert row is not None, "expected runtime_dispatched row for malformed spec"
    assert row[0] == 0, "runtime_dispatched.success must be 0 on CLI failure"

    metadata = json.loads(row[1])
    assert metadata["returncode"] == 3
    assert metadata["runtime"] == "claude"


def test_empty_spec_file_exits_3() -> None:
    """CLI must exit 3 when spec file is empty (malformed)."""
    spec_path = _write_spec("")
    try:
        result = _run_cli("execute", "claude", str(spec_path))
        assert result.returncode == 3, (
            f"Expected exit 3 for empty spec, got {result.returncode}\n"
            f"stderr: {result.stderr}"
        )
    finally:
        spec_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# Exit code 0 — success path (dry-run / mock)
# ---------------------------------------------------------------------------


def test_valid_builder_and_spec_exits_0(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI must exit 0 when builder is valid and spec file exists with content."""
    spec_path = _write_spec(VALID_SPEC)
    try:
        # We use BR3_DISPATCH_DRY_RUN=1 to skip actual LLM call in tests
        result = _run_cli(
            "execute", "claude", str(spec_path),
            env={"BR3_DISPATCH_DRY_RUN": "1"},
        )
        assert result.returncode == 0, (
            f"Expected exit 0 for valid dispatch (dry-run), got {result.returncode}\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )
    finally:
        spec_path.unlink(missing_ok=True)


def test_dry_run_stdout_contains_json() -> None:
    """Dry-run mode must emit a JSON result envelope on stdout."""
    spec_path = _write_spec(VALID_SPEC)
    try:
        result = _run_cli(
            "execute", "claude", str(spec_path),
            env={"BR3_DISPATCH_DRY_RUN": "1"},
        )
        assert result.returncode == 0
        # stdout should contain a JSON object with at least "status"
        data = json.loads(result.stdout.strip())
        assert "status" in data, f"No 'status' in JSON output: {data}"
        assert data["status"] in ("success", "dry_run"), f"Unexpected status: {data['status']}"
    finally:
        spec_path.unlink(missing_ok=True)


# ---------------------------------------------------------------------------
# CLI help / no args
# ---------------------------------------------------------------------------


def test_no_args_exits_nonzero() -> None:
    """Running with no args should exit non-zero (usage error)."""
    result = _run_cli()
    assert result.returncode != 0


def test_help_flag_exits_0() -> None:
    """--help flag should exit 0."""
    result = _run_cli("--help")
    assert result.returncode == 0


# ---------------------------------------------------------------------------
# Supported builders list
# ---------------------------------------------------------------------------


def test_all_supported_builders_exit_0_dry_run() -> None:
    """All supported builders (claude, codex, ollama) must exit 0 in dry-run mode."""
    spec_path = _write_spec(VALID_SPEC)
    try:
        for builder in ("claude", "codex", "ollama"):
            result = _run_cli(
                "execute", builder, str(spec_path),
                env={"BR3_DISPATCH_DRY_RUN": "1"},
            )
            assert result.returncode == 0, (
                f"Builder '{builder}' exited {result.returncode} in dry-run mode.\n"
                f"stdout: {result.stdout}\nstderr: {result.stderr}"
            )
    finally:
        spec_path.unlink(missing_ok=True)
