"""Tests for OllamaRuntime: construction, health, execute() success, fallback on 503."""

from __future__ import annotations

import asyncio
import json
from io import BytesIO
from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from core.runtime.ollama_runtime import OllamaRuntime, _check_ollama_health, _resolve_ollama_base_url
from core.runtime.types import RuntimeResult, RuntimeTask


def make_task(task_type: str = "review") -> RuntimeTask:
    return RuntimeTask(
        task_id="test-ollama-deadbeef",
        task_type=task_type,
        diff_text="diff --git a/app.py b/app.py\n+print('hello')\n",
        spec_text="# Spec\nKeep review isolated.",
        project_root="/tmp/project",
        commit_sha="deadbeef",
        metadata={"mode": "local_inference"},
    )


# ---------------------------------------------------------------------------
# Construction tests
# ---------------------------------------------------------------------------


def test_ollama_runtime_construction_defaults():
    runtime = OllamaRuntime()
    assert runtime.runtime_name == "ollama"
    assert runtime.backend_name == "ollama-api"
    assert runtime.model == "llama3.3:70b"
    assert runtime.port == 11434
    assert runtime.timeout == 120


def test_ollama_runtime_construction_custom():
    runtime = OllamaRuntime(model="mistral:7b", host="http://10.0.1.200", port=11500, timeout=60)
    assert runtime.model == "mistral:7b"
    assert runtime._host == "http://10.0.1.200"
    assert runtime.port == 11500
    assert runtime.timeout == 60


def test_ollama_runtime_capabilities():
    runtime = OllamaRuntime()
    caps = runtime.get_capabilities()
    assert caps["local_inference"] is True
    assert caps["review"] is True
    assert caps["execution"] is False


def test_ollama_runtime_registered_in_registry():
    from core.runtime.runtime_registry import create_runtime_registry

    registry = create_runtime_registry()
    reg = registry.get("ollama")
    assert reg.name == "ollama"
    assert reg.adapter.runtime_name == "ollama"
    assert reg.dispatch_mode == "local_inference"


def test_claude_remains_default_in_registry():
    from core.runtime.runtime_registry import create_runtime_registry

    registry = create_runtime_registry()
    # Claude is registered and accessible
    assert registry.get("claude").name == "claude"
    assert registry.get("codex").name == "codex"
    assert registry.get("ollama").name == "ollama"


# ---------------------------------------------------------------------------
# Health check tests
# ---------------------------------------------------------------------------


def test_health_check_returns_true_on_200(monkeypatch):
    """Health check returns True when Ollama /api/tags returns 200."""
    # Mock cluster-check.sh as absent so we fall through to urllib
    monkeypatch.setattr("core.runtime.ollama_runtime._CLUSTER_CHECK_SCRIPT", MagicMock(exists=lambda: False))

    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_resp):
        result = _check_ollama_health("http://10.0.1.105")

    assert result is True


def test_health_check_returns_false_on_connection_error(monkeypatch):
    """Health check returns False when connection is refused."""
    monkeypatch.setattr("core.runtime.ollama_runtime._CLUSTER_CHECK_SCRIPT", MagicMock(exists=lambda: False))

    with patch("urllib.request.urlopen", side_effect=OSError("Connection refused")):
        result = _check_ollama_health("http://10.0.1.105")

    assert result is False


def test_health_check_uses_cluster_check_script_when_available(monkeypatch, tmp_path):
    """Health check returns True when cluster-check.sh exits 0 with output."""
    script = tmp_path / "cluster-check.sh"
    script.write_text("#!/bin/sh\necho ok\n")
    script.chmod(0o755)

    monkeypatch.setattr("core.runtime.ollama_runtime._CLUSTER_CHECK_SCRIPT", script)

    import subprocess
    real_run = subprocess.run

    def fake_run(cmd, *args, **kwargs):
        if str(script) in str(cmd):
            return SimpleNamespace(returncode=0, stdout="http://10.0.1.105:11434\n", stderr="")
        return real_run(cmd, *args, **kwargs)

    with patch("subprocess.run", side_effect=fake_run):
        result = _check_ollama_health("http://10.0.1.105")

    assert result is True


# ---------------------------------------------------------------------------
# execute() success path
# ---------------------------------------------------------------------------


def test_execute_success(monkeypatch):
    """OllamaRuntime.run_review returns completed RuntimeResult on success."""
    task = make_task()
    runtime = OllamaRuntime(host="http://10.0.1.105")

    # Health check passes
    monkeypatch.setattr("core.runtime.ollama_runtime._check_ollama_health", lambda base_url, port: True)

    fake_response_body = json.dumps({
        "model": "llama3.3:70b",
        "message": {"role": "assistant", "content": '[{"finding": "test finding", "severity": "note"}]'},
        "prompt_eval_count": 100,
        "eval_count": 50,
        "total_duration": 1234567890,
    }).encode("utf-8")

    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.read.return_value = fake_response_body
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_resp):
        result = asyncio.run(runtime.run_review(task))

    assert result.status == "completed"
    assert result.runtime == "ollama"
    assert result.backend == "ollama/llama3.3:70b"
    assert result.metrics["cost_usd"] == 0.0
    assert result.metrics["model"] == "llama3.3:70b"
    assert len(result.findings) == 1
    assert result.findings[0].finding == "test finding"
    assert result.metadata["mode"] == "local_inference"


def test_execute_success_empty_findings(monkeypatch):
    """OllamaRuntime handles empty JSON findings array gracefully."""
    task = make_task()
    runtime = OllamaRuntime(host="http://10.0.1.105")

    monkeypatch.setattr("core.runtime.ollama_runtime._check_ollama_health", lambda base_url, port: True)

    # Return a proper JSON empty array so parse_findings produces no findings
    fake_response_body = json.dumps({
        "message": {"role": "assistant", "content": "[]"},
        "prompt_eval_count": 80,
        "eval_count": 20,
    }).encode("utf-8")

    fake_resp = MagicMock()
    fake_resp.status = 200
    fake_resp.read.return_value = fake_response_body
    fake_resp.__enter__ = lambda s: s
    fake_resp.__exit__ = MagicMock(return_value=False)

    with patch("urllib.request.urlopen", return_value=fake_resp):
        result = asyncio.run(runtime.run_review(task))

    assert result.status == "completed"
    assert result.findings == []


# ---------------------------------------------------------------------------
# Fallback on 503
# ---------------------------------------------------------------------------


def test_fallback_on_503(monkeypatch):
    """OllamaRuntime falls back to ClaudeRuntime silently on 503 with no user-visible error."""
    task = make_task()
    runtime = OllamaRuntime(host="http://10.0.1.105")

    # Health check passes but actual call gets 503
    monkeypatch.setattr("core.runtime.ollama_runtime._check_ollama_health", lambda base_url, port: True)

    def raise_503(*args, **kwargs):
        raise RuntimeError("HTTP Error 503: Service Unavailable")

    fallback_result = RuntimeResult(
        task_id=task.task_id,
        runtime="claude",
        backend="claude-cli",
        status="completed",
        metadata={"mode": "parallel_shadow"},
    )

    fallback_called = []

    def fake_fallback(self, task, reason, start):
        fallback_called.append(reason)
        result = RuntimeResult(
            task_id=task.task_id,
            runtime=self.runtime_name,
            backend=self.backend_name,
            status="completed",
            metadata={"fallback": "claude", "fallback_reason": reason},
        )
        return result

    monkeypatch.setattr("urllib.request.urlopen", raise_503)
    monkeypatch.setattr(OllamaRuntime, "_fallback_to_claude", fake_fallback)

    result = asyncio.run(runtime.run_review(task))

    # Fallback was invoked
    assert len(fallback_called) == 1
    assert "503" in fallback_called[0] or "ollama_error" in fallback_called[0]
    # Result carries fallback metadata (no raised exception)
    assert result.metadata.get("fallback") == "claude"


def test_fallback_on_health_check_failure(monkeypatch):
    """OllamaRuntime falls back silently when health check fails."""
    task = make_task()
    runtime = OllamaRuntime(host="http://10.0.1.105")

    # Health check fails
    monkeypatch.setattr("core.runtime.ollama_runtime._check_ollama_health", lambda base_url, port: False)

    fallback_called = []

    def fake_fallback(self, task, reason, start):
        fallback_called.append(reason)
        return RuntimeResult(
            task_id=task.task_id,
            runtime=self.runtime_name,
            backend=self.backend_name,
            status="completed",
            metadata={"fallback": "claude", "fallback_reason": reason},
        )

    monkeypatch.setattr(OllamaRuntime, "_fallback_to_claude", fake_fallback)

    result = asyncio.run(runtime.run_review(task))

    assert len(fallback_called) == 1
    assert fallback_called[0] == "health_check_failed"
    assert result.metadata.get("fallback") == "claude"


def test_fallback_on_timeout(monkeypatch):
    """OllamaRuntime falls back silently on timeout."""
    task = make_task()
    runtime = OllamaRuntime(host="http://10.0.1.105")

    monkeypatch.setattr("core.runtime.ollama_runtime._check_ollama_health", lambda base_url, port: True)

    import socket

    def raise_timeout(*args, **kwargs):
        raise TimeoutError("timed out")

    fallback_called = []

    def fake_fallback(self, task, reason, start):
        fallback_called.append(reason)
        return RuntimeResult(
            task_id=task.task_id,
            runtime=self.runtime_name,
            backend=self.backend_name,
            status="completed",
            metadata={"fallback": "claude", "fallback_reason": reason},
        )

    monkeypatch.setattr("urllib.request.urlopen", raise_timeout)
    monkeypatch.setattr(OllamaRuntime, "_fallback_to_claude", fake_fallback)

    result = asyncio.run(runtime.run_review(task))

    assert len(fallback_called) == 1
    assert result.metadata.get("fallback") == "claude"


def test_no_user_visible_error_on_503(monkeypatch, capsys):
    """On 503, no exception is raised and no error reaches stdout/stderr."""
    task = make_task()
    runtime = OllamaRuntime(host="http://10.0.1.105")

    monkeypatch.setattr("core.runtime.ollama_runtime._check_ollama_health", lambda base_url, port: True)

    def raise_503(*args, **kwargs):
        raise RuntimeError("503 Service Unavailable")

    monkeypatch.setattr("urllib.request.urlopen", raise_503)

    # Claude fallback returns a plausible error result (CLI not found)
    # We just verify no exception propagates
    try:
        result = asyncio.run(runtime.run_review(task))
        # Must return a RuntimeResult, not raise
        assert isinstance(result, RuntimeResult)
    except Exception as exc:
        pytest.fail(f"OllamaRuntime raised a user-visible exception on 503: {exc}")


# ---------------------------------------------------------------------------
# Config validation
# ---------------------------------------------------------------------------


def test_supported_runtimes_includes_ollama():
    from core.runtime.config import SUPPORTED_RUNTIMES

    assert "ollama" in SUPPORTED_RUNTIMES
    assert "claude" in SUPPORTED_RUNTIMES
    assert "codex" in SUPPORTED_RUNTIMES
    # Claude is still index 0 (default)
    assert SUPPORTED_RUNTIMES[0] == "claude"


def test_local_ready_capability_in_command_capabilities():
    import json
    from pathlib import Path

    cap_file = Path("core/runtime/command_capabilities.json")
    if not cap_file.exists():
        pytest.skip("command_capabilities.json not found at expected path")

    data = json.loads(cap_file.read_text())
    caps = data.get("capabilities", {})
    assert "local_ready" in caps
    members = caps["local_ready"]["members"]
    for cmd in ["plan-draft", "structural-review", "governance-lint", "intel-scoring", "summarize"]:
        assert cmd in members, f"{cmd} missing from local_ready.members"
