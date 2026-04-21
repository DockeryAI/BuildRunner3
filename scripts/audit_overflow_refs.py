#!/usr/bin/env python3
"""audit_overflow_refs.py — Phase 4 guard: enforce the 7-node priority order.

Scans the codebase + ~/.buildrunner scripts for hardcoded node IPs and ensures
lockwood (10.0.1.101) PRIMARY-role references (semantic-search, intel, staging)
have been rewritten to jimmy (10.0.1.106).

Exit codes:
  0 — no violations
  1 — one or more PRIMARY-role lockwood references found
  2 — missing is_overflow_worker() classifier (dispatch-core broken)

The classifier `is_overflow_worker()` in `_dispatch-core.sh` is the single
source of truth for which nodes count as overflow (lockwood, lomax). Overflow
workers stay in worker-pool + heartbeat contexts; PRIMARY-role refs don't.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
HOME = Path.home()

# PRIMARY roles that must NEVER point at lockwood (10.0.1.101)
PRIMARY_ROLE_KEYWORDS = ("semantic-search", "semantic_search", "intel", "staging")

LOCKWOOD_IP = "10.0.1.101"
JIMMY_IP = "10.0.1.106"

SCAN_ROOTS = [
    REPO,
    HOME / ".buildrunner" / "scripts",
    HOME / ".buildrunner" / "agents-md",
]

EXCLUDE_DIRS = {
    ".venv",
    "node_modules",
    "__pycache__",
    ".git",
    "dist",
    "build",
    ".dispatch-worktrees",
    "codex-briefs",
}

SELF_PATH = Path(__file__).resolve()


def _iter_files() -> list[Path]:
    files: list[Path] = []
    for root in SCAN_ROOTS:
        if not root.exists():
            continue
        for path in root.rglob("*"):
            if not path.is_file():
                continue
            if any(part in EXCLUDE_DIRS for part in path.parts):
                continue
            if path.suffix in {".py", ".sh", ".mjs", ".js", ".ts", ".yaml", ".yml", ".json"}:
                files.append(path)
    return files


def _check_classifier() -> bool:
    core = HOME / ".buildrunner" / "scripts" / "_dispatch-core.sh"
    if not core.exists():
        return False
    return "is_overflow_worker" in core.read_text(errors="ignore")


def main() -> int:
    if not _check_classifier():
        print("ERROR: is_overflow_worker() not found in _dispatch-core.sh", file=sys.stderr)
        return 2

    violations: list[tuple[Path, int, str]] = []
    pattern = re.compile(re.escape(LOCKWOOD_IP))

    for fp in _iter_files():
        if fp.resolve() == SELF_PATH:
            continue
        try:
            text = fp.read_text(errors="ignore")
        except Exception:
            continue
        if LOCKWOOD_IP not in text:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            if not pattern.search(line):
                continue
            low = line.lower()
            if any(kw in low for kw in PRIMARY_ROLE_KEYWORDS):
                violations.append((fp, lineno, line.strip()))

    if violations:
        print(f"FAIL: {len(violations)} PRIMARY-role lockwood references found (should be jimmy {JIMMY_IP}):")
        for fp, lineno, line in violations:
            print(f"  {fp}:{lineno}: {line}")
        return 1

    print(f"OK: no PRIMARY-role lockwood references; is_overflow_worker() present; jimmy={JIMMY_IP} is authoritative for PRIMARY roles.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
