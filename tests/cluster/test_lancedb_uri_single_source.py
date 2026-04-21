"""tests/cluster/test_lancedb_uri_single_source.py — Phase 4 URI guard.

Asserts every code path that reads a LanceDB URI goes through
`core.cluster.lancedb_config.get_lancedb_uri()`. No hardcoded
`~/.lockwood/lancedb` or `/srv/jimmy/lancedb` strings in code outside
the config module and the migration scripts.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

HARDCODED_PATTERNS = [
    r"~/\.lockwood/lancedb",
    r"/srv/jimmy/lancedb",
    r'os\.environ\.get\(\s*["\']LANCE_DIR',
]

# Files allowed to contain hardcoded paths:
# - lancedb_config.py: the single source of truth
# - test_lancedb_uri_single_source.py: this test (references the strings)
# - migrate-lockwood-data.sh and reindex scripts: CLI migration tooling
ALLOWLIST = {
    "core/cluster/lancedb_config.py",
    "tests/cluster/test_lancedb_uri_single_source.py",
}

CODE_SUFFIXES = {".py"}


def _git_grep(pattern: str) -> list[tuple[str, int, str]]:
    out = subprocess.run(
        ["git", "grep", "-n", "-E", pattern],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        check=False,
    )
    if out.returncode not in (0, 1):
        pytest.fail(f"git grep failed: {out.stderr}")
    hits = []
    for line in out.stdout.splitlines():
        m = re.match(r"^([^:]+):(\d+):(.*)$", line)
        if not m:
            continue
        hits.append((m.group(1), int(m.group(2)), m.group(3)))
    return hits


def test_no_hardcoded_lancedb_paths_in_code() -> None:
    """Code modules must import from lancedb_config; no hardcoded paths."""
    offenders: list[tuple[str, int, str]] = []
    for pat in HARDCODED_PATTERNS:
        for path, lineno, content in _git_grep(pat):
            if path in ALLOWLIST:
                continue
            if Path(path).suffix not in CODE_SUFFIXES:
                continue
            offenders.append((path, lineno, content))
    assert not offenders, (
        "Hardcoded LanceDB paths found (must import from core.cluster.lancedb_config):\n"
        + "\n".join(f"  {p}:{n}: {c.strip()}" for p, n, c in offenders)
    )


def test_config_module_exposes_uri_resolver() -> None:
    """lancedb_config.py exports get_lancedb_uri, get_embedding_model, get_embedding_dim."""
    from core.cluster import lancedb_config

    assert callable(lancedb_config.get_lancedb_uri), "get_lancedb_uri must exist"
    uri = lancedb_config.get_lancedb_uri()
    assert isinstance(uri, str) and uri, "get_lancedb_uri must return non-empty str"
    assert callable(lancedb_config.get_embedding_model)
    assert callable(lancedb_config.get_embedding_dim)
    assert lancedb_config.get_embedding_dim() == 384, "canonical embedder is 384-dim MiniLM"


def test_env_override_respected(monkeypatch) -> None:
    """$LANCE_DIR override wins."""
    from core.cluster import lancedb_config

    monkeypatch.setenv("LANCE_DIR", "/tmp/override-lancedb")
    assert lancedb_config.get_lancedb_uri() == "/tmp/override-lancedb"
