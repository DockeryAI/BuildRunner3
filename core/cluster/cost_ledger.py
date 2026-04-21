"""CostLedger — per-call cost/cache observability for RuntimeRegistry.execute().

Writes JSONL to /srv/jimmy/ledger/cost.jsonl (direct path or via SSH mount).
Weekly rotation: new file each Monday (ISO week boundary).

Schema — exactly 11 fields:
    ts, runtime, model, input_tokens, cache_read_tokens, cache_write_tokens,
    output_tokens, cost_usd, latency_ms, skill, phase

Feature-gated by BR3_GATEWAY=on (RuntimeRegistry handles the gate;
CostLedger itself is always available but only called when the flag is on).
"""

from __future__ import annotations

import json
import logging
import os
import threading
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

logger = logging.getLogger(__name__)

# Primary ledger directory — /srv/jimmy/ledger/ via direct mount or SSH mount.
# Falls back to a local path when Jimmy is not mounted.
_PRIMARY_LEDGER_DIR = Path("/srv/jimmy/ledger")
_FALLBACK_LEDGER_DIR = Path.home() / ".buildrunner" / "ledger"

# Exactly 11 fields — changing this breaks the cross-check in AGENTS.md and tests.
LEDGER_FIELDS = (
    "ts",
    "runtime",
    "model",
    "input_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "output_tokens",
    "cost_usd",
    "latency_ms",
    "skill",
    "phase",
)
LEDGER_FIELD_COUNT = len(LEDGER_FIELDS)  # Must equal 11


def _resolve_ledger_dir() -> Path:
    """Return the best available ledger directory, creating it if needed."""
    if _PRIMARY_LEDGER_DIR.exists():
        return _PRIMARY_LEDGER_DIR
    # Try to create the primary path (works when /srv/jimmy is a local mount)
    try:
        _PRIMARY_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
        return _PRIMARY_LEDGER_DIR
    except OSError:
        pass
    # Fallback to local ~/.buildrunner/ledger/
    _FALLBACK_LEDGER_DIR.mkdir(parents=True, exist_ok=True)
    logger.debug(
        "CostLedger: /srv/jimmy/ledger not writable; using fallback %s",
        _FALLBACK_LEDGER_DIR,
    )
    return _FALLBACK_LEDGER_DIR


def _week_suffix(ts: datetime) -> str:
    """Return ISO week string like '2026-W16' for weekly rotation."""
    year, week, _ = ts.isocalendar()
    return f"{year}-W{week:02d}"


class CostLedger:
    """Thread-safe JSONL writer with weekly file rotation.

    Usage::

        ledger = CostLedger()
        ledger.append(
            runtime="ollama",
            model="llama3.3:70b",
            input_tokens=1200,
            cache_read_tokens=300,
            cache_write_tokens=0,
            output_tokens=450,
            cost_usd=0.0,
            latency_ms=840,
            skill="review",
            phase="7",
        )
    """

    _lock = threading.Lock()

    def __init__(self, ledger_dir: Union[Path, str, None] = None) -> None:
        if ledger_dir is not None:
            self._ledger_dir = Path(ledger_dir)
            self._ledger_dir.mkdir(parents=True, exist_ok=True)
        else:
            self._ledger_dir = _resolve_ledger_dir()

    def _current_path(self, ts: datetime) -> Path:
        """Return the JSONL file path for this week."""
        week = _week_suffix(ts)
        return self._ledger_dir / f"cost-{week}.jsonl"

    def append(
        self,
        *,
        runtime: str,
        model: str,
        input_tokens: int,
        cache_read_tokens: int,
        cache_write_tokens: int,
        output_tokens: int,
        cost_usd: float,
        latency_ms: int,
        skill: str,
        phase: str,
    ) -> None:
        """Append one 11-field JSONL record.  Thread-safe.  Never raises."""
        ts = datetime.now(tz=timezone.utc)
        record = {
            "ts": ts.isoformat(),
            "runtime": runtime,
            "model": model,
            "input_tokens": int(input_tokens),
            "cache_read_tokens": int(cache_read_tokens),
            "cache_write_tokens": int(cache_write_tokens),
            "output_tokens": int(output_tokens),
            "cost_usd": float(cost_usd),
            "latency_ms": int(latency_ms),
            "skill": skill,
            "phase": str(phase),
        }
        # Verify field count matches the schema constant (safety net)
        assert len(record) == LEDGER_FIELD_COUNT, (
            f"CostLedger record has {len(record)} fields; expected {LEDGER_FIELD_COUNT}"
        )

        line = json.dumps(record, separators=(",", ":"))
        path = self._current_path(ts)

        try:
            with self._lock:
                with path.open("a", encoding="utf-8") as fh:
                    fh.write(line + "\n")
        except OSError as exc:
            logger.warning("CostLedger: failed to write %s: %s", path, exc)

    def read_window(self, days: int = 7) -> list[dict]:
        """Return all records from the last ``days`` days, newest-first.

        Reads only weekly files that overlap the requested window; safe for
        large ledgers because it never loads more than 2 weekly files.
        """
        from datetime import timedelta

        now = datetime.now(tz=timezone.utc)
        cutoff = now - timedelta(days=days)
        records: list[dict] = []

        # Collect candidate files (current week + previous if window spans boundary)
        weeks_to_check: set[str] = set()
        for offset in range(days + 8):  # +8 covers the full previous week
            candidate_ts = now - timedelta(days=offset)
            weeks_to_check.add(_week_suffix(candidate_ts))

        for week in weeks_to_check:
            path = self._ledger_dir / f"cost-{week}.jsonl"
            if not path.exists():
                continue
            try:
                with path.open("r", encoding="utf-8") as fh:
                    for raw_line in fh:
                        raw_line = raw_line.strip()
                        if not raw_line:
                            continue
                        try:
                            rec = json.loads(raw_line)
                            rec_ts = datetime.fromisoformat(rec["ts"])
                            if rec_ts >= cutoff:
                                records.append(rec)
                        except (json.JSONDecodeError, KeyError, ValueError):
                            continue
            except OSError:
                continue

        records.sort(key=lambda r: r["ts"], reverse=True)
        return records
