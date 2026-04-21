"""Tests for RuntimeRegistry.execute() shim.

Verifies:
- execute() routes to the correct runtime adapter
- Falls back to claude when requested runtime is not registered
- cache_control passed verbatim (not stripped)
- execute_async() works in an async context
- Unknown task_type returns error envelope without raising
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from core.runtime.runtime_registry import (
    RuntimeRegistry,
    RuntimeRegistration,
    create_runtime_registry,
)
from core.runtime.types import RuntimeResult, RuntimeTask


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_task(
    task_type: str = "review",
    authoritative_runtime: str | None = None,
    cache_control: str | None = None,
    skill: str = "review",
    phase: str = "7",
) -> RuntimeTask:
    meta: dict = {"skill": skill, "phase": phase}
    if cache_control is not None:
        meta["cache_control"] = cache_control
    return RuntimeTask(
        task_id="test-shim-abc123",
        task_type=task_type,
        diff_text="diff --git a/x.py b/x.py\n+pass\n",
        spec_text="# spec",
        project_root="/tmp/project",
        commit_sha="abc123",
        authoritative_runtime=authoritative_runtime,
        metadata=meta,
    )


def _make_result(runtime: str = "claude", task_id: str = "test-shim-abc123") -> RuntimeResult:
    return RuntimeResult(
        task_id=task_id,
        runtime=runtime,
        backend=f"{runtime}-api",
        status="success",
        metrics={
            "model": f"{runtime}-model",
            "input_tokens": 800,
            "output_tokens": 300,
        },
    )


def _make_mock_adapter(runtime_name: str) -> MagicMock:
    adapter = MagicMock()
    adapter.runtime_name = runtime_name
    adapter.backend_name = f"{runtime_name}-api"
    adapter.run_review = AsyncMock(return_value=_make_result(runtime_name))
    adapter.run_plan = AsyncMock(return_value=_make_result(runtime_name))
    adapter.run_execution_step = AsyncMock(return_value=_make_result(runtime_name))
    adapter.run_analysis = AsyncMock(return_value=_make_result(runtime_name))
    return adapter


def _make_registry_with_mock_adapters() -> tuple[RuntimeRegistry, MagicMock, MagicMock]:
    """Return (registry, claude_adapter, ollama_adapter)."""
    registry = RuntimeRegistry()
    claude_adapter = _make_mock_adapter("claude")
    ollama_adapter = _make_mock_adapter("ollama")
    registry.register(RuntimeRegistration(name="claude", adapter=claude_adapter))
    registry.register(RuntimeRegistration(name="ollama", adapter=ollama_adapter))
    return registry, claude_adapter, ollama_adapter


# ---------------------------------------------------------------------------
# execute() routing tests
# ---------------------------------------------------------------------------


def test_execute_routes_to_authoritative_runtime() -> None:
    """execute() must call the adapter matching task.authoritative_runtime."""
    registry, claude_adapter, ollama_adapter = _make_registry_with_mock_adapters()

    task = _make_task(task_type="review", authoritative_runtime="ollama")
    result = registry.execute(task)

    ollama_adapter.run_review.assert_called_once_with(task)
    claude_adapter.run_review.assert_not_called()
    assert result.runtime == "ollama"


def test_execute_defaults_to_claude() -> None:
    """execute() must fall back to claude when authoritative_runtime is None."""
    registry, claude_adapter, ollama_adapter = _make_registry_with_mock_adapters()

    task = _make_task(task_type="review", authoritative_runtime=None)
    result = registry.execute(task)

    claude_adapter.run_review.assert_called_once_with(task)
    ollama_adapter.run_review.assert_not_called()
    assert result.runtime == "claude"


def test_execute_falls_back_to_claude_on_unknown_runtime() -> None:
    """execute() must fall back to claude when the requested runtime is not registered."""
    registry, claude_adapter, _ = _make_registry_with_mock_adapters()

    task = _make_task(authoritative_runtime="nonexistent")
    result = registry.execute(task)

    claude_adapter.run_review.assert_called_once_with(task)
    assert result.runtime == "claude"


def test_execute_routes_plan_task() -> None:
    registry, claude_adapter, _ = _make_registry_with_mock_adapters()

    task = _make_task(task_type="plan")
    registry.execute(task)

    claude_adapter.run_plan.assert_called_once_with(task)
    claude_adapter.run_review.assert_not_called()


def test_execute_routes_execution_task() -> None:
    registry, claude_adapter, _ = _make_registry_with_mock_adapters()

    task = _make_task(task_type="execution")
    registry.execute(task)

    claude_adapter.run_execution_step.assert_called_once_with(task)


def test_execute_unknown_task_type_returns_error_envelope() -> None:
    """Unknown task_type must return an error RuntimeResult, NOT raise."""
    registry, _, _ = _make_registry_with_mock_adapters()

    task = _make_task(task_type="unknown_type_xyz")
    result = registry.execute(task)

    assert result.status == "error"
    assert result.error_class == "UnsupportedTaskType"


# ---------------------------------------------------------------------------
# cache_control passthrough
# ---------------------------------------------------------------------------


def test_execute_passes_cache_control_verbatim() -> None:
    """cache_control must not be stripped from task.metadata."""
    registry, claude_adapter, _ = _make_registry_with_mock_adapters()

    task = _make_task(cache_control="ephemeral")
    registry.execute(task)

    called_task: RuntimeTask = claude_adapter.run_review.call_args[0][0]
    assert called_task.metadata.get("cache_control") == "ephemeral"


# ---------------------------------------------------------------------------
# execute_async() tests
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_execute_async_routes_correctly() -> None:
    registry, claude_adapter, _ = _make_registry_with_mock_adapters()

    task = _make_task(task_type="review")
    result = await registry.execute_async(task)

    claude_adapter.run_review.assert_called_once_with(task)
    assert result.runtime == "claude"


# ---------------------------------------------------------------------------
# Integration: create_runtime_registry returns a registry with execute()
# ---------------------------------------------------------------------------


def test_create_runtime_registry_has_execute() -> None:
    """create_runtime_registry() must return a RuntimeRegistry with execute()."""
    registry = create_runtime_registry()
    assert hasattr(registry, "execute")
    assert callable(registry.execute)
    assert "claude" in registry.list_names()
    assert "ollama" in registry.list_names()
    assert "codex" in registry.list_names()
