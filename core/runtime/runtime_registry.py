"""Runtime adapter registry for the Phase 1 scaffold.

Phase 7 adds RuntimeRegistry.execute(task) as the SINGLE dispatch path for all local-model
calls. Direct ollama / requests.post / curl calls to cluster nodes are FORBIDDEN — the
pre-commit hook in .git/hooks/pre-commit enforces this at commit time.

Cost/cache observability (token counts, cache-hit rate, per-model spend) is written to
/srv/jimmy/ledger/cost.jsonl via core.cluster.cost_ledger.CostLedger when BR3_GATEWAY=on.
"""

from __future__ import annotations

import asyncio
import logging
import os
import time
from dataclasses import dataclass
from typing import Any

from core.runtime.base import BaseRuntime
from core.runtime.claude_runtime import ClaudeRuntime
from core.runtime.codex_runtime import CodexRuntime
from core.runtime.ollama_runtime import OllamaRuntime
from core.runtime.types import RuntimeResult, RuntimeTask

logger = logging.getLogger(__name__)

SUPPORTED_RUNTIME_NAMES = ("claude", "codex", "ollama")

# Feature flag — default OFF until Phase 13 cutover.
_GATEWAY_ENV_VAR = "BR3_GATEWAY"


def _gateway_enabled() -> bool:
    """Return True when BR3_GATEWAY=on (case-insensitive). Default OFF."""
    return os.environ.get(_GATEWAY_ENV_VAR, "").strip().lower() == "on"


@dataclass
class RuntimeRegistration:
    """Registered runtime adapter plus static metadata used by the scaffold."""

    name: str
    adapter: BaseRuntime
    dispatch_mode: str = "parallel_shadow"

    def describe(self) -> dict[str, object]:
        return {
            "runtime": self.name,
            "backend": self.adapter.backend_name,
            "capabilities": self.adapter.get_capability_profile().to_dict(),
            "dispatch_mode": self.dispatch_mode,
        }


class RuntimeRegistry:
    """Opt-in runtime registry.

    ``execute(task)`` is the ONLY sanctioned dispatch path for local-model calls.
    It routes by ``task.authoritative_runtime`` (or falls back to ``claude``),
    emits a cost-ledger entry when BR3_GATEWAY=on, and always honours
    ``cache_control`` metadata from the task envelope verbatim.
    """

    def __init__(self):
        self._registrations: dict[str, RuntimeRegistration] = {}

    def register(self, registration: RuntimeRegistration) -> None:
        self._registrations[registration.name] = registration

    def get(self, name: str) -> RuntimeRegistration:
        if name not in self._registrations:
            raise KeyError(name)
        return self._registrations[name]

    def list_names(self) -> list[str]:
        return list(self._registrations.keys())

    def create_many(self, names: list[str]) -> list[RuntimeRegistration]:
        missing = [name for name in names if name not in self._registrations]
        if missing:
            raise ValueError(f"Unsupported runtime requested for review spike: {', '.join(missing)}")
        return [self._registrations[name] for name in names]

    def supported_names(self) -> list[str]:
        return list(self._registrations.keys())

    # ------------------------------------------------------------------
    # Phase 7: single dispatch shim
    # ------------------------------------------------------------------

    def execute(self, task: RuntimeTask) -> RuntimeResult:
        """Synchronous shim — the ONLY authorised path to dispatch a local-model task.

        Routing:
          1. Use ``task.authoritative_runtime`` when set and registered.
          2. Fall back to ``claude`` (always available).

        Observability:
          When BR3_GATEWAY=on, writes a cost-ledger entry via
          ``core.cluster.cost_ledger.CostLedger``.  Ledger emit is best-effort:
          a failure MUST NOT bubble up and break the dispatch.

        cache_control passthrough:
          ``task.metadata.get("cache_control")`` is forwarded verbatim to the
          adapter — never stripped or modified here.
        """
        runtime_name = task.authoritative_runtime or "claude"
        if runtime_name not in self._registrations:
            logger.warning(
                "execute(): requested runtime %r not registered; falling back to claude",
                runtime_name,
            )
            runtime_name = "claude"

        registration = self._registrations[runtime_name]
        adapter = registration.adapter

        start_ts = time.time()
        result = asyncio.run(self._dispatch_to_adapter(adapter, task))
        latency_ms = int((time.time() - start_ts) * 1000)

        if _gateway_enabled():
            self._emit_cost_ledger(task, result, runtime_name, latency_ms)

        return result

    async def execute_async(self, task: RuntimeTask) -> RuntimeResult:
        """Async variant of execute() for callers already in an event loop."""
        runtime_name = task.authoritative_runtime or "claude"
        if runtime_name not in self._registrations:
            logger.warning(
                "execute_async(): requested runtime %r not registered; falling back to claude",
                runtime_name,
            )
            runtime_name = "claude"

        registration = self._registrations[runtime_name]
        adapter = registration.adapter

        start_ts = time.time()
        result = await self._dispatch_to_adapter(adapter, task)
        latency_ms = int((time.time() - start_ts) * 1000)

        if _gateway_enabled():
            self._emit_cost_ledger(task, result, runtime_name, latency_ms)

        return result

    @staticmethod
    async def _dispatch_to_adapter(adapter: BaseRuntime, task: RuntimeTask) -> RuntimeResult:
        """Route to the correct adapter method by task_type."""
        if task.task_type == "review":
            return await adapter.run_review(task)
        if task.task_type == "plan":
            return await adapter.run_plan(task)
        if task.task_type == "execution":
            return await adapter.run_execution_step(task)
        if task.task_type == "analysis":
            return await adapter.run_analysis(task)
        # Unknown task type — return error envelope rather than raising.
        return RuntimeResult(
            task_id=task.task_id,
            runtime=getattr(adapter, "runtime_name", "unknown"),
            backend=getattr(adapter, "backend_name", "unknown"),
            status="error",
            error_class="UnsupportedTaskType",
            error_message=f"Unknown task_type: {task.task_type!r}",
        )

    @staticmethod
    def _emit_cost_ledger(
        task: RuntimeTask,
        result: RuntimeResult,
        runtime_name: str,
        latency_ms: int,
    ) -> None:
        """Write a cost-ledger entry.  Best-effort — never raises."""
        try:
            from core.cluster.cost_ledger import CostLedger  # lazy import avoids circular dep

            metrics: dict[str, Any] = result.metrics or {}
            ledger = CostLedger()
            ledger.append(
                runtime=runtime_name,
                model=metrics.get("model", ""),
                input_tokens=metrics.get("input_tokens", 0),
                cache_read_tokens=metrics.get("cache_read_tokens", 0),
                cache_write_tokens=metrics.get("cache_write_tokens", 0),
                output_tokens=metrics.get("output_tokens", 0),
                cost_usd=metrics.get("cost_usd", 0.0),
                latency_ms=latency_ms,
                skill=task.metadata.get("skill", ""),
                phase=task.metadata.get("phase", ""),
            )
        except Exception as exc:  # noqa: BLE001
            logger.warning("cost_ledger emit failed (non-fatal): %s", exc)


def create_runtime_registry(config: dict | None = None) -> RuntimeRegistry:
    """Build the runtime registry used by BR3 runtime-aware paths."""
    config = config or {}
    timeout = config.get("backends", {}).get("codex", {}).get("timeout_seconds", 60)
    ollama_cfg = config.get("backends", {}).get("ollama", {})
    registry = RuntimeRegistry()
    registry.register(RuntimeRegistration(name="claude", adapter=ClaudeRuntime()))
    registry.register(RuntimeRegistration(name="codex", adapter=CodexRuntime(timeout_seconds=timeout)))
    registry.register(
        RuntimeRegistration(
            name="ollama",
            adapter=OllamaRuntime(
                model=ollama_cfg.get("model", "llama3.3:70b"),
                host=ollama_cfg.get("host"),
                port=ollama_cfg.get("port", 11434),
                timeout=ollama_cfg.get("timeout", 120),
            ),
            dispatch_mode="local_inference",
        )
    )
    return registry


def create_phase1_runtime_registry(config: dict | None = None) -> RuntimeRegistry:
    """Backward-compatible alias for the Phase 1 shadow registry."""
    return create_runtime_registry(config)
