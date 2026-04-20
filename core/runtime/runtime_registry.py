"""Runtime adapter registry for the Phase 1 scaffold."""

from __future__ import annotations

from dataclasses import dataclass

from core.runtime.base import BaseRuntime
from core.runtime.claude_runtime import ClaudeRuntime
from core.runtime.codex_runtime import CodexRuntime
from core.runtime.ollama_runtime import OllamaRuntime

SUPPORTED_RUNTIME_NAMES = ("claude", "codex", "ollama")


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
    """Opt-in runtime registry used by the non-live review spike path."""

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
