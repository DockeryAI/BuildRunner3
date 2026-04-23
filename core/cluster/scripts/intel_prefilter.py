#!/usr/bin/env python3
"""intel_prefilter.py — Below pre-filter wrapper for collect-intel.sh Phase 2.5.

Invokes the existing batch scorer (score_intel_items) synchronously. Writes a
timestamped log to ~/.buildrunner/logs/intel-prefilter-*.log. Exits 0 even if
some items can't be scored — the scorer itself flags them needs_opus_review=1
when Below is offline (fail-open), so Phase 3 synthesis still catches them.

Usage:
    python3 -m core.cluster.scripts.intel_prefilter

No flags. No args. Reads BELOW_OLLAMA_URL / BELOW_MODEL_FAST from runtime-env.
"""
from __future__ import annotations

import asyncio
import datetime as dt
import os
import pathlib
import sys


def main() -> int:
    try:
        from core.cluster.intel_scoring import score_intel_items
    except ImportError:
        here = pathlib.Path(__file__).resolve()
        repo_root = here.parents[3]
        sys.path.insert(0, str(repo_root))
        from core.cluster.intel_scoring import score_intel_items

    log_dir = pathlib.Path(os.path.expanduser("~/.buildrunner/logs"))
    log_dir.mkdir(parents=True, exist_ok=True)
    ts = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d-%H%M%S")
    log_path = log_dir / f"intel-prefilter-{ts}.log"

    start = dt.datetime.now(dt.timezone.utc)
    started_line = f"[intel_prefilter] started at {start.isoformat()} → log {log_path}"
    print(started_line)

    try:
        stats = asyncio.run(score_intel_items())
    except Exception as exc:
        err = f"[intel_prefilter] ERROR {type(exc).__name__}: {exc}"
        print(err, file=sys.stderr)
        log_path.write_text(started_line + "\n" + err + "\n")
        return 0

    elapsed = (dt.datetime.now(dt.timezone.utc) - start).total_seconds()
    summary = (
        f"[intel_prefilter] done in {elapsed:.1f}s: "
        f"total={stats.get('total', 0)} "
        f"scored={stats.get('scored', 0)} "
        f"flagged={stats.get('flagged', 0)} "
        f"duplicates={stats.get('duplicates', 0)} "
        f"errors={stats.get('errors', 0)}"
    )
    print(summary)
    log_path.write_text(started_line + "\n" + summary + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
