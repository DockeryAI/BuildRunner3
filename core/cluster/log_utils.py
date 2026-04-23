"""log_utils.py — Shared helpers for decisions.log path resolution and writes.

Single source of truth for decisions.log location.  All callers that previously
resolved the path inline (arbiter.py, cross_model_review.py, context_bundle.py,
dashboard_stream.py) now import from here.

Path resolution order:
    1. ``BR3_DECISIONS_LOG`` env var (tests / CI override)
    2. ``<cwd>/.buildrunner/decisions.log`` when the directory exists (repo-local)
    3. ``~/Projects/BuildRunner3/.buildrunner/decisions.log`` (canonical home path)

Writes are serialized via ``fcntl.flock(LOCK_EX)`` so concurrent callers cannot
interleave partial lines.
"""

from __future__ import annotations

import fcntl
import os
import time
from pathlib import Path


def get_decisions_log_path() -> Path:
    """Return the resolved path to decisions.log.

    Callers should not cache the result across long-running processes because the
    working directory may change.  For short-lived helpers the result is stable.
    """
    env_override = os.environ.get("BR3_DECISIONS_LOG")
    if env_override:
        return Path(env_override)

    # Prefer repo-local .buildrunner/ when it already exists (standard dev layout).
    repo_local = Path.cwd() / ".buildrunner" / "decisions.log"
    if repo_local.parent.exists():
        return repo_local

    # Canonical absolute fallback — works from any CWD.
    return Path.home() / "Projects" / "BuildRunner3" / ".buildrunner" / "decisions.log"


def _append_decision_log(prefix: str, event: str, details: str = "") -> None:
    """Append one line to decisions.log with an ISO-8601 timestamp.

    Thread-safe and process-safe: the file is opened in append mode and the
    write is wrapped in ``fcntl.flock(LOCK_EX)``.

    Args:
        prefix:   Caller tag, e.g. ``"ARBITER"``, ``"THREE_WAY_REVIEW"``,
                  ``"CONTEXT_BUNDLE"``, ``"DASHBOARD"``.
        event:    Short event description.
        details:  Optional trailing detail string (appended after a space).
    """
    path = get_decisions_log_path()
    path.parent.mkdir(parents=True, exist_ok=True)

    timestamp = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
    line = f"[{timestamp}] {prefix} {event}"
    if details:
        line += f" {details}"
    line += "\n"

    with path.open("a", encoding="utf-8") as fh:
        fcntl.flock(fh.fileno(), fcntl.LOCK_EX)
        try:
            fh.write(line)
        finally:
            fcntl.flock(fh.fileno(), fcntl.LOCK_UN)
