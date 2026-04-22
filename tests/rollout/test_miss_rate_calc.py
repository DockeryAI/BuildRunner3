from __future__ import annotations

import contextlib
import datetime as dt
import importlib.util
import io
import sqlite3
import sys
from pathlib import Path

SCRIPT_PATH = Path.home() / ".buildrunner" / "scripts" / "miss-rate-calc.py"


def load_module():
    spec = importlib.util.spec_from_file_location("miss_rate_calc", SCRIPT_PATH)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def iso(hours_ago: int) -> str:
    now = dt.datetime.now(dt.timezone.utc)
    return (now - dt.timedelta(hours=hours_ago)).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def test_empty_rows_returns_zero() -> None:
    module = load_module()

    assert module.calculate_miss_rate([]) == 0.0


def test_one_override_in_ten_rows_is_ten_percent() -> None:
    module = load_module()
    rows = [{"timestamp": iso(1), "verdict": "overridden"}] + [
        {"timestamp": iso(1), "verdict": "passed"} for _ in range(9)
    ]

    assert module.calculate_miss_rate(rows) == 0.1


def test_two_overrides_in_ten_rows_is_twenty_percent() -> None:
    module = load_module()
    rows = [{"timestamp": iso(1), "verdict": "overridden"} for _ in range(2)] + [
        {"timestamp": iso(1), "verdict": "passed"} for _ in range(8)
    ]

    assert module.calculate_miss_rate(rows) == 0.2


def test_rows_outside_twenty_four_hours_are_filtered() -> None:
    module = load_module()
    rows = [
        {"timestamp": iso(1), "verdict": "passed"},
        {"timestamp": iso(2), "verdict": "overridden"},
        {"timestamp": iso(25), "verdict": "overridden"},
        {"timestamp": iso(30), "verdict": "overridden"},
    ]

    assert module.calculate_miss_rate(rows) == 0.5


def test_cli_reads_sqlite_source(tmp_path: Path) -> None:
    module = load_module()
    db_path = tmp_path / "dispatch.db"
    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            """
            CREATE TABLE dispatch_metrics (
              timestamp TEXT NOT NULL,
              session_id TEXT NOT NULL,
              bucket TEXT NOT NULL,
              builder TEXT NOT NULL,
              model TEXT NOT NULL,
              effort TEXT NOT NULL,
              prompt_tokens INTEGER NOT NULL DEFAULT 0,
              output_tokens INTEGER NOT NULL DEFAULT 0,
              latency_ms INTEGER NOT NULL DEFAULT 0,
              done_when_passed INTEGER NOT NULL DEFAULT 0,
              verdict TEXT NOT NULL,
              override_reason TEXT,
              route_file_path TEXT NOT NULL DEFAULT ''
            )
            """
        )
        fresh_rows = [
            (iso(1), "session-a", "build", "codex", "gpt-5.4", "xhigh", 1, 1, 1, 1, "overridden", "manual", ""),
            (iso(2), "session-b", "build", "codex", "gpt-5.4", "xhigh", 1, 1, 1, 1, "passed", None, ""),
            (iso(26), "session-c", "build", "codex", "gpt-5.4", "xhigh", 1, 1, 1, 1, "overridden", "old", ""),
        ]
        conn.executemany(
            """
            INSERT INTO dispatch_metrics (
              timestamp, session_id, bucket, builder, model, effort,
              prompt_tokens, output_tokens, latency_ms, done_when_passed,
              verdict, override_reason, route_file_path
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            fresh_rows,
        )
        conn.commit()
    finally:
        conn.close()

    stdout = io.StringIO()
    argv = sys.argv[:]
    try:
        sys.argv = [str(SCRIPT_PATH), "--source", f"sqlite://{db_path}"]
        with contextlib.redirect_stdout(stdout):
            exit_code = module.main()
    finally:
        sys.argv = argv

    assert exit_code == 0
    assert stdout.getvalue().strip() == "0.500000"
