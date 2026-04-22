"""tests/integration/test_context_codex_live.py — Phase 1 live context assertions.

These tests hit Jimmy's live Context API on `10.0.1.106:4500`.

- `BR3_AUTO_CONTEXT=on`  → assert HTTP 200 and real bundle fields
- `BR3_AUTO_CONTEXT=off` → assert HTTP 503 with explicit flag-off response
"""

from __future__ import annotations

import json
import os
import urllib.error
import urllib.request

import pytest

JIMMY_HOST = "10.0.1.106"
JIMMY_PORT = 4500
CONTEXT_URL = f"http://{JIMMY_HOST}:{JIMMY_PORT}/context/codex?phase=2"
TIMEOUT_SECONDS = 5


def _is_jimmy_reachable() -> bool:
    """Quick TCP check to see if Jimmy is reachable."""
    import socket
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        result = sock.connect_ex((JIMMY_HOST, JIMMY_PORT))
        sock.close()
        return result == 0
    except Exception:
        return False


def _skip_if_jimmy_unreachable() -> None:
    if not _is_jimmy_reachable():
        pytest.skip(
            f"Jimmy ({JIMMY_HOST}:{JIMMY_PORT}) not reachable from test machine. "
            "Network was not available — documented per BUILD spec Phase 1. "
            "Run this test from a machine on the 10.0.1.0/24 cluster network."
        )


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BR3_AUTO_CONTEXT", "").strip().lower() != "on",
    reason="requires BR3_AUTO_CONTEXT=on on the target Jimmy context service",
)
def test_context_codex_returns_200_with_bundle_when_flag_on():
    """Flag ON must return HTTP 200 with bundle phase/model + budget fields."""
    _skip_if_jimmy_unreachable()

    try:
        req = urllib.request.Request(CONTEXT_URL)
        with urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS) as resp:
            status = resp.status
            body = resp.read()
    except urllib.error.HTTPError as e:
        pytest.fail(f"Jimmy returned HTTP {e.code}: {e.reason}")
    except Exception as exc:
        pytest.fail(f"Failed to reach Jimmy at {CONTEXT_URL}: {exc}")

    assert status == 200, f"Expected HTTP 200, got {status}"

    # Validate response shape
    try:
        data = json.loads(body)
    except json.JSONDecodeError as e:
        pytest.fail(f"Response is not valid JSON: {e}\nBody: {body[:200]}")

    assert "bundle" in data, f"Response missing 'bundle' key. Got keys: {list(data.keys())}"
    assert "budget" in data, f"Response missing 'budget' key. Got keys: {list(data.keys())}"
    assert data["bundle"].get("phase") == "2"
    assert data["bundle"].get("model") == "codex"
    assert set(data["budget"].keys()) >= {"limit", "used", "tokenizer"}
    assert isinstance(data["budget"]["limit"], int)
    assert isinstance(data["budget"]["used"], int)
    assert bool(data["budget"]["tokenizer"])


@pytest.mark.integration
@pytest.mark.skipif(
    os.environ.get("BR3_AUTO_CONTEXT", "").strip().lower() != "off",
    reason="requires BR3_AUTO_CONTEXT=off on the target Jimmy context service",
)
def test_context_codex_returns_503_when_flag_off():
    """Flag OFF must return HTTP 503 rather than being treated as success."""
    _skip_if_jimmy_unreachable()

    req = urllib.request.Request(CONTEXT_URL)
    with pytest.raises(urllib.error.HTTPError) as exc_info:
        urllib.request.urlopen(req, timeout=TIMEOUT_SECONDS)

    assert exc_info.value.code == 503
    detail = exc_info.value.read().decode("utf-8", errors="replace")
    assert "BR3_AUTO_CONTEXT" in detail
    assert "OFF" in detail.upper()


@pytest.mark.integration
def test_context_endpoint_mounted_on_node_semantic():
    """Verify the context router is registered in node_semantic.py source."""
    repo_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    node_path = os.path.join(repo_root, "core", "cluster", "node_semantic.py")

    with open(node_path) as f:
        content = f.read()

    assert "context" in content.lower() and "include_router" in content, (
        "node_semantic.py must include_router for context router. "
        "Context routes will not be available on :4500 without this."
    )
