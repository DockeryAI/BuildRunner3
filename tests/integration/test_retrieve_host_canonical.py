"""tests/integration/test_retrieve_host_canonical.py — Phase 7 live-host guard.

Asserts the /retrieve endpoint points at Jimmy (the canonical read-only
mirror per Phase 1). The test is skipped when Jimmy is not reachable —
CI environments without cluster access shouldn't fail on network.

Opt in live:
    RETRIEVE_LIVE=1 RETRIEVE_URL=http://10.0.1.106:8787/retrieve pytest ...
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path
from urllib.parse import urlparse

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VERIFY_SH = Path.home() / ".buildrunner" / "scripts" / "verify-retrieve-host.sh"

CANONICAL_HOST = "10.0.1.106"  # Jimmy (per .buildrunner/cluster-max/CANONICALIZATION_DECISION.md)
CANONICAL_NAME = "jimmy"


def test_verify_retrieve_host_script_exists_and_executable() -> None:
    """verify-retrieve-host.sh must be installed and executable."""
    assert VERIFY_SH.exists(), f"missing: {VERIFY_SH}"
    assert os.access(VERIFY_SH, os.X_OK), f"not executable: {VERIFY_SH}"


def test_retrieve_url_host_is_canonical() -> None:
    """If RETRIEVE_URL is set, its host must be Jimmy."""
    url = os.environ.get("RETRIEVE_URL", f"http://{CANONICAL_HOST}:8787/retrieve")
    host = urlparse(url).hostname
    assert host in {CANONICAL_HOST, CANONICAL_NAME, f"{CANONICAL_NAME}.local"}, (
        f"RETRIEVE_URL host '{host}' is not canonical "
        f"('{CANONICAL_HOST}' or '{CANONICAL_NAME}'). "
        "See .buildrunner/cluster-max/CANONICALIZATION_DECISION.md."
    )


@pytest.mark.skipif(
    os.environ.get("RETRIEVE_LIVE") != "1",
    reason="RETRIEVE_LIVE=1 not set — skipping live cluster check",
)
def test_verify_retrieve_host_against_live_endpoint() -> None:
    """Hit the live /retrieve endpoint and assert Jimmy answered."""
    assert shutil.which("bash"), "bash required to run verify-retrieve-host.sh"
    result = subprocess.run(
        ["bash", str(VERIFY_SH)],
        capture_output=True,
        text=True,
        timeout=15,
        env={**os.environ},
    )
    assert result.returncode == 0, (
        f"verify-retrieve-host.sh exit={result.returncode}\n"
        f"stdout: {result.stdout}\nstderr: {result.stderr}"
    )
