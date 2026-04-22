"""tests/cluster/test_flag_canonical.py — Phase 5 canonical flag guard.

Asserts the deprecated multi-model context flag has been fully canonicalized to
`BR3_AUTO_CONTEXT`. Code files (.py/.sh/.mjs/.ts/.js) and every `AGENTS.md`
must contain zero references to the deprecated name.

Historical audit files (`decisions.log*`) and build/plan docs that
describe the migration itself are excluded — they legitimately record
the old name as "what was renamed from what".
"""

from __future__ import annotations

import os
import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
DEPRECATED = "BR3_MULTI_" "MODEL_CONTEXT"

CODE_EXTENSIONS = {".py", ".sh", ".mjs", ".ts", ".js"}

# Files that are allowed to reference the deprecated name.
# These are historical audit trails or migration descriptions.
ALLOWLIST = {
    "tests/cluster/test_flag_canonical.py",
    ".buildrunner/decisions.log",
}
ALLOWLIST_PREFIXES = (
    ".buildrunner/decisions.log.",  # rotated audit logs
)


def _is_allowlisted(rel_path: str) -> bool:
    if rel_path in ALLOWLIST:
        return True
    return any(rel_path.startswith(p) for p in ALLOWLIST_PREFIXES)


def _grep_deprecated() -> list[tuple[str, int, str]]:
    """Return (rel_path, line_no, line) tuples where the deprecated name appears."""
    try:
        out = subprocess.run(
            ["git", "grep", "-n", DEPRECATED],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        pytest.skip("git not available")

    if out.returncode not in (0, 1):
        pytest.fail(f"git grep failed: {out.stderr}")

    results: list[tuple[str, int, str]] = []
    for raw in out.stdout.splitlines():
        # Format: path:lineno:content
        m = re.match(r"^([^:]+):(\d+):(.*)$", raw)
        if not m:
            continue
        path, lineno, content = m.group(1), int(m.group(2)), m.group(3)
        results.append((path, lineno, content))
    return results


def test_no_deprecated_flag_in_code() -> None:
    """Code files must never reference the deprecated flag."""
    hits = [
        (p, n, c) for (p, n, c) in _grep_deprecated()
        if Path(p).suffix in CODE_EXTENSIONS and not _is_allowlisted(p)
    ]
    assert not hits, (
        f"Deprecated flag {DEPRECATED} found in code:\n"
        + "\n".join(f"  {p}:{n}: {c.strip()}" for p, n, c in hits)
    )


def test_no_deprecated_flag_in_agents_md() -> None:
    """Every AGENTS.md must use the canonical flag name."""
    hits = [
        (p, n, c) for (p, n, c) in _grep_deprecated()
        if Path(p).name == "AGENTS.md" and not _is_allowlisted(p)
    ]
    assert not hits, (
        f"Deprecated flag {DEPRECATED} found in AGENTS.md files:\n"
        + "\n".join(f"  {p}:{n}: {c.strip()}" for p, n, c in hits)
    )


def test_canonical_flag_is_used() -> None:
    """At least one code file must read BR3_AUTO_CONTEXT (sanity)."""
    try:
        out = subprocess.run(
            ["git", "grep", "-l", "BR3_AUTO_CONTEXT"],
            cwd=REPO_ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
    except FileNotFoundError:
        pytest.skip("git not available")
    lines = out.stdout.strip().splitlines()
    code_hits = [p for p in lines if Path(p).suffix in CODE_EXTENSIONS]
    assert code_hits, "No code file references canonical flag BR3_AUTO_CONTEXT"
