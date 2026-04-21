"""Tests for CostLedger — JSONL shape, field count, rotation, read_window."""

from __future__ import annotations

import json
import tempfile
from datetime import datetime, timezone
from pathlib import Path

import pytest

from core.cluster.cost_ledger import CostLedger, LEDGER_FIELDS, LEDGER_FIELD_COUNT


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture()
def tmp_ledger(tmp_path: Path) -> CostLedger:
    """CostLedger writing to a temp directory."""
    return CostLedger(ledger_dir=tmp_path)


def _sample_append(ledger: CostLedger, **overrides) -> None:
    """Append one record with sensible defaults."""
    defaults = dict(
        runtime="claude",
        model="claude-sonnet-4-6",
        input_tokens=1000,
        cache_read_tokens=200,
        cache_write_tokens=50,
        output_tokens=400,
        cost_usd=0.0025,
        latency_ms=830,
        skill="review",
        phase="7",
    )
    defaults.update(overrides)
    ledger.append(**defaults)


# ---------------------------------------------------------------------------
# test_jsonl_shape — 11 fields
# ---------------------------------------------------------------------------


def test_jsonl_shape(tmp_ledger: CostLedger, tmp_path: Path) -> None:
    """Each written record must have exactly 11 fields matching LEDGER_FIELDS."""
    _sample_append(tmp_ledger)

    # Find the written JSONL file
    jsonl_files = list(tmp_path.glob("cost-*.jsonl"))
    assert len(jsonl_files) == 1, "Expected exactly one ledger file after one append"

    lines = jsonl_files[0].read_text().strip().splitlines()
    assert len(lines) == 1

    record = json.loads(lines[0])

    # Verify exactly 11 fields
    assert len(record) == 11, f"Expected 11 fields, got {len(record)}: {list(record.keys())}"

    # Verify all 11 field names are present
    for field in LEDGER_FIELDS:
        assert field in record, f"Missing field: {field!r}"

    # Verify LEDGER_FIELD_COUNT constant matches
    assert LEDGER_FIELD_COUNT == 11


def test_field_types(tmp_ledger: CostLedger, tmp_path: Path) -> None:
    """Each field must be the correct JSON type."""
    _sample_append(tmp_ledger, input_tokens=999, cost_usd=0.0012, latency_ms=500)

    jsonl_files = list(tmp_path.glob("cost-*.jsonl"))
    record = json.loads(jsonl_files[0].read_text().strip())

    assert isinstance(record["ts"], str)
    assert isinstance(record["runtime"], str)
    assert isinstance(record["model"], str)
    assert isinstance(record["input_tokens"], int)
    assert isinstance(record["cache_read_tokens"], int)
    assert isinstance(record["cache_write_tokens"], int)
    assert isinstance(record["output_tokens"], int)
    assert isinstance(record["cost_usd"], float)
    assert isinstance(record["latency_ms"], int)
    assert isinstance(record["skill"], str)
    assert isinstance(record["phase"], str)


def test_multiple_appends_produce_multiple_lines(tmp_ledger: CostLedger, tmp_path: Path) -> None:
    """Each call to append() must write exactly one new line."""
    for i in range(5):
        _sample_append(tmp_ledger, input_tokens=i * 100)

    jsonl_files = list(tmp_path.glob("cost-*.jsonl"))
    assert len(jsonl_files) == 1
    lines = [l for l in jsonl_files[0].read_text().splitlines() if l.strip()]
    assert len(lines) == 5


def test_ts_is_utc_iso(tmp_ledger: CostLedger, tmp_path: Path) -> None:
    """'ts' field must be a parseable UTC ISO datetime."""
    _sample_append(tmp_ledger)
    jsonl_files = list(tmp_path.glob("cost-*.jsonl"))
    record = json.loads(jsonl_files[0].read_text().strip())
    ts = datetime.fromisoformat(record["ts"])
    assert ts.tzinfo is not None, "ts must be timezone-aware"


def test_field_values_match_input(tmp_ledger: CostLedger, tmp_path: Path) -> None:
    """Written fields must match the values passed to append()."""
    _sample_append(
        tmp_ledger,
        runtime="ollama",
        model="llama3.3:70b",
        input_tokens=1234,
        cache_read_tokens=321,
        cache_write_tokens=99,
        output_tokens=567,
        cost_usd=0.0,
        latency_ms=1200,
        skill="summarize",
        phase="8",
    )
    jsonl_files = list(tmp_path.glob("cost-*.jsonl"))
    record = json.loads(jsonl_files[0].read_text().strip())

    assert record["runtime"] == "ollama"
    assert record["model"] == "llama3.3:70b"
    assert record["input_tokens"] == 1234
    assert record["cache_read_tokens"] == 321
    assert record["cache_write_tokens"] == 99
    assert record["output_tokens"] == 567
    assert record["cost_usd"] == 0.0
    assert record["latency_ms"] == 1200
    assert record["skill"] == "summarize"
    assert record["phase"] == "8"


def test_read_window_returns_records(tmp_ledger: CostLedger) -> None:
    """read_window() must return records from the last N days."""
    _sample_append(tmp_ledger, runtime="codex")
    _sample_append(tmp_ledger, runtime="claude")

    records = tmp_ledger.read_window(days=1)
    assert len(records) == 2
    runtimes = {r["runtime"] for r in records}
    assert "codex" in runtimes
    assert "claude" in runtimes


def test_read_window_zero_when_empty(tmp_ledger: CostLedger) -> None:
    """read_window() returns empty list when no records exist."""
    assert tmp_ledger.read_window(days=7) == []


def test_weekly_rotation_produces_separate_files(tmp_path: Path) -> None:
    """Records in different ISO weeks must land in different JSONL files."""
    from unittest.mock import patch
    from datetime import datetime, timezone

    ledger = CostLedger(ledger_dir=tmp_path)

    # Week 1
    ts_w1 = datetime(2026, 4, 13, 10, 0, 0, tzinfo=timezone.utc)  # Mon W16
    # Week 2
    ts_w2 = datetime(2026, 4, 20, 10, 0, 0, tzinfo=timezone.utc)  # Mon W17

    with patch("core.cluster.cost_ledger.datetime") as mock_dt:
        mock_dt.now.return_value = ts_w1
        mock_dt.fromisoformat = datetime.fromisoformat
        _sample_append(ledger)

    with patch("core.cluster.cost_ledger.datetime") as mock_dt:
        mock_dt.now.return_value = ts_w2
        mock_dt.fromisoformat = datetime.fromisoformat
        _sample_append(ledger)

    jsonl_files = sorted(tmp_path.glob("cost-*.jsonl"))
    assert len(jsonl_files) == 2, f"Expected 2 weekly files, got: {[f.name for f in jsonl_files]}"
