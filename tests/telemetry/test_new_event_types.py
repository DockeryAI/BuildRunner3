"""tests/telemetry/test_new_event_types.py — Phase 6 new event types.

Verifies emit + query roundtrip for each of the 4 new event types:
  - runtime_dispatched
  - cache_hit
  - context_bundle_served
  - adversarial_review_ran

Strategy:
  - Use a temp SQLite DB matching the telemetry.db schema
  - Patch DB discovery in each emit helper to point at the temp DB
  - Verify rows appear with correct event_type and non-empty metadata
"""

from __future__ import annotations

import json
import os
import sqlite3
import tempfile
import uuid
from pathlib import Path
from typing import Generator
from unittest import mock

import pytest


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_CREATE_SCHEMA = """
CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    event_id TEXT UNIQUE NOT NULL,
    event_type TEXT NOT NULL,
    timestamp TEXT NOT NULL,
    session_id TEXT,
    task_id TEXT,
    task_type TEXT,
    build_id TEXT,
    build_phase TEXT,
    error_type TEXT,
    error_message TEXT,
    stack_trace TEXT,
    component TEXT,
    severity TEXT,
    duration_ms REAL,
    tokens_used INTEGER,
    cost_usd REAL,
    total_cost_usd REAL,
    cpu_percent REAL,
    memory_mb REAL,
    success BOOLEAN DEFAULT 1,
    metadata TEXT,
    created_at TEXT DEFAULT (datetime('now'))
);
"""


@pytest.fixture()
def telemetry_db(tmp_path: Path) -> Generator[Path, None, None]:
    """Create a temp telemetry.db with the correct schema."""
    db_path = tmp_path / ".buildrunner" / "telemetry.db"
    db_path.parent.mkdir(parents=True)
    conn = sqlite3.connect(str(db_path))
    conn.executescript(_CREATE_SCHEMA)
    conn.commit()
    conn.close()
    yield db_path


def _read_events(db_path: Path, event_type: str) -> list[dict]:
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    try:
        cur = conn.execute(
            "SELECT * FROM events WHERE event_type=? ORDER BY id DESC", (event_type,)
        )
        return [dict(r) for r in cur.fetchall()]
    finally:
        conn.close()


# ---------------------------------------------------------------------------
# 1. runtime_dispatched — emitted by RuntimeRegistry.execute()
# ---------------------------------------------------------------------------

class TestRuntimeDispatched:
    def test_emit_roundtrip(self, telemetry_db: Path, tmp_path: Path) -> None:
        """emit inserts a runtime_dispatched row; metadata contains runtime + task_type."""
        from core.runtime.runtime_registry import _emit_runtime_dispatched
        from core.runtime.types import RuntimeTask

        task = RuntimeTask(
            task_id="test-task-1",
            task_type="execution",
            diff_text="",
            spec_text="spec",
            project_root=str(tmp_path),
            commit_sha="abc123",
            authoritative_runtime="claude",
        )

        # Patch DB discovery to use our temp DB
        with mock.patch("core.runtime.runtime_registry._emit_runtime_dispatched",
                        wraps=_emit_runtime_dispatched):
            # Call directly with patched cwd
            with mock.patch("pathlib.Path.cwd", return_value=telemetry_db.parent.parent):
                _emit_runtime_dispatched("claude", task)

        rows = _read_events(telemetry_db, "runtime_dispatched")
        assert len(rows) >= 1, "expected at least 1 runtime_dispatched row"
        meta = json.loads(rows[0]["metadata"])
        assert meta["runtime"] == "claude"
        assert meta["task_type"] == "execution"

    def test_emit_nonblocking_on_missing_db(self, tmp_path: Path) -> None:
        """emit does not raise when telemetry.db is absent."""
        from core.runtime.runtime_registry import _emit_runtime_dispatched
        from core.runtime.types import RuntimeTask

        task = RuntimeTask(
            task_id="noop",
            task_type="execution",
            diff_text="",
            spec_text="",
            project_root=str(tmp_path),
            commit_sha="",
            authoritative_runtime="claude",
        )
        # No DB exists in tmp_path — must not raise
        with mock.patch("pathlib.Path.cwd", return_value=tmp_path / "no-db-here"):
            _emit_runtime_dispatched("claude", task)  # should not raise

    def test_event_type_registered(self) -> None:
        """EventType enum includes RUNTIME_DISPATCHED."""
        from core.telemetry.event_schemas import EventType
        assert EventType.RUNTIME_DISPATCHED.value == "runtime_dispatched"


# ---------------------------------------------------------------------------
# 2. cache_hit — emitted by cache_policy.build_cached_prompt()
# ---------------------------------------------------------------------------

class TestCacheHit:
    def test_emit_roundtrip_when_flag_on(self, telemetry_db: Path) -> None:
        """cache_hit rows appear when BR3_CACHE_BREAKPOINTS=on."""
        import importlib

        # Force the flag on
        with mock.patch.dict(os.environ, {"BR3_CACHE_BREAKPOINTS": "on"}):
            # Re-import to pick up flag (module reads at import time)
            import core.runtime.cache_policy as _cp
            # Temporarily patch the module-level flag
            with mock.patch.object(_cp, "_CACHE_BREAKPOINTS_ENABLED", True):
                with mock.patch("pathlib.Path.cwd", return_value=telemetry_db.parent.parent):
                    _cp.build_cached_prompt("sys", "skill", "task")

        rows = _read_events(telemetry_db, "cache_hit")
        assert len(rows) >= 2, "expected 2 cache_hit rows (breakpoints 0+1)"
        indices = {json.loads(r["metadata"])["breakpoint"] for r in rows}
        assert 0 in indices
        assert 1 in indices

    def test_no_emit_when_flag_off(self, telemetry_db: Path) -> None:
        """No cache_hit rows when BR3_CACHE_BREAKPOINTS=off."""
        import core.runtime.cache_policy as _cp

        with mock.patch.object(_cp, "_CACHE_BREAKPOINTS_ENABLED", False):
            with mock.patch("pathlib.Path.cwd", return_value=telemetry_db.parent.parent):
                _cp.build_cached_prompt("sys", "skill", "task")

        rows = _read_events(telemetry_db, "cache_hit")
        assert len(rows) == 0, "expected no cache_hit rows when flag off"

    def test_event_type_registered(self) -> None:
        from core.telemetry.event_schemas import EventType
        assert EventType.CACHE_HIT.value == "cache_hit"


# ---------------------------------------------------------------------------
# 3. context_bundle_served — emitted by codex-bridge.sh via br-emit-event.sh
# ---------------------------------------------------------------------------

class TestContextBundleServed:
    def test_event_type_registered(self) -> None:
        from core.telemetry.event_schemas import EventType
        assert EventType.CONTEXT_BUNDLE_SERVED.value == "context_bundle_served"

    def test_br_emit_script_inserts_row(self, telemetry_db: Path) -> None:
        """br-emit-event.sh writes a context_bundle_served row to telemetry.db."""
        import subprocess

        script = Path(__file__).resolve().parents[2] / "scripts" / "br-emit-event.sh"
        if not script.exists():
            pytest.skip("br-emit-event.sh not found")

        env = os.environ.copy()
        env["BR3_PROJECT_ROOT"] = str(telemetry_db.parent.parent)
        result = subprocess.run(
            [str(script), "context_bundle_served", '{"phase":"2","task":"test"}'],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0, f"br-emit-event.sh failed: {result.stderr}"

        rows = _read_events(telemetry_db, "context_bundle_served")
        assert len(rows) >= 1, "expected at least 1 context_bundle_served row"
        meta = json.loads(rows[0]["metadata"])
        assert meta.get("phase") == "2"

    def test_br_emit_truncates_long_strings(self, telemetry_db: Path) -> None:
        """br-emit-event.sh truncates values >256 chars."""
        import subprocess

        script = Path(__file__).resolve().parents[2] / "scripts" / "br-emit-event.sh"
        if not script.exists():
            pytest.skip("br-emit-event.sh not found")

        long_val = "x" * 512
        env = os.environ.copy()
        env["BR3_PROJECT_ROOT"] = str(telemetry_db.parent.parent)
        result = subprocess.run(
            [str(script), "context_bundle_served", json.dumps({"phase": long_val})],
            env=env,
            capture_output=True,
            text=True,
            timeout=10,
        )
        assert result.returncode == 0

        rows = _read_events(telemetry_db, "context_bundle_served")
        if rows:
            meta = json.loads(rows[0]["metadata"])
            for v in meta.values():
                if isinstance(v, str):
                    assert len(v) <= 256, f"metadata value not truncated: len={len(v)}"


# ---------------------------------------------------------------------------
# 4. adversarial_review_ran — emitted by cross_model_review.run_three_way_review()
# ---------------------------------------------------------------------------

class TestAdversarialReviewRan:
    def test_event_type_registered(self) -> None:
        from core.telemetry.event_schemas import EventType
        assert EventType.ADVERSARIAL_REVIEW_RAN.value == "adversarial_review_ran"

    def test_emit_roundtrip(self, telemetry_db: Path) -> None:
        """_emit_adversarial_review_ran inserts row with mode + verdict."""
        from core.cluster.cross_model_review import _emit_adversarial_review_ran

        with mock.patch("pathlib.Path.cwd", return_value=telemetry_db.parent.parent):
            _emit_adversarial_review_ran(
                mode="3-way",
                verdict="APPROVED",
                findings_count=3,
                commit_sha="deadbeef",
            )

        rows = _read_events(telemetry_db, "adversarial_review_ran")
        assert len(rows) >= 1, "expected at least 1 adversarial_review_ran row"
        meta = json.loads(rows[0]["metadata"])
        assert meta["mode"] == "3-way"
        assert meta["verdict"] == "APPROVED"
        assert meta["findings_count"] == 3
        assert meta["commit_sha"] == "deadbeef"

    def test_emit_nonblocking_on_missing_db(self, tmp_path: Path) -> None:
        """emit does not raise when telemetry.db is absent."""
        from core.cluster.cross_model_review import _emit_adversarial_review_ran

        with mock.patch("pathlib.Path.cwd", return_value=tmp_path / "no-db-here"):
            _emit_adversarial_review_ran("2-way", "ESCALATED", 0, "")  # must not raise

    def test_metadata_no_pii_long_strings(self, telemetry_db: Path) -> None:
        """mode/verdict/commit_sha are all truncated to safe lengths."""
        from core.cluster.cross_model_review import _emit_adversarial_review_ran

        # Artificially long values should be truncated
        with mock.patch("pathlib.Path.cwd", return_value=telemetry_db.parent.parent):
            _emit_adversarial_review_ran(
                mode="3-way" * 20,
                verdict="APPROVED" * 20,
                findings_count=1,
                commit_sha="a" * 100,
            )

        rows = _read_events(telemetry_db, "adversarial_review_ran")
        if rows:
            meta = json.loads(rows[0]["metadata"])
            assert len(meta.get("mode", "")) <= 64
            assert len(meta.get("verdict", "")) <= 64
            assert len(meta.get("commit_sha", "")) <= 64
