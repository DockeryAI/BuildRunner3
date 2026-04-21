"""Runtime adapter registry.

RuntimeRegistry.execute(task) is the SINGLE dispatch path for all local-model calls.
Direct ollama / requests.post / curl calls to cluster nodes are FORBIDDEN — the
pre-commit hook in .git/hooks/pre-commit enforces this at commit time.

CLI entry (Phase 2 — unified dispatcher):
    python -m core.runtime.runtime_registry execute <builder> <spec_path>

Exit codes:
    0 — success
    2 — unknown builder (not registered)
    3 — malformed spec (file not found or empty)
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import sys
from dataclasses import dataclass
from pathlib import Path

from core.runtime.base import BaseRuntime
from core.runtime.claude_runtime import ClaudeRuntime
from core.runtime.codex_runtime import CodexRuntime
from core.runtime.ollama_runtime import OllamaRuntime
from core.runtime.types import RuntimeResult, RuntimeTask

logger = logging.getLogger(__name__)

SUPPORTED_RUNTIME_NAMES = ("claude", "codex", "ollama")


@dataclass
class RuntimeRegistration:
    """Registered runtime adapter plus static metadata used by the scaffold."""

    name: str
    adapter: BaseRuntime
    dispatch_mode: str = "direct"

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
    and always honours ``cache_control`` metadata from the task envelope verbatim.
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

    def execute(self, task: RuntimeTask) -> RuntimeResult:
        """Synchronous shim — the ONLY authorised path to dispatch a local-model task.

        Routing:
          1. Use ``task.authoritative_runtime`` when set and registered.
          2. Fall back to ``claude`` (always available).

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
        return asyncio.run(self._dispatch_to_adapter(registration.adapter, task))

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
        return await self._dispatch_to_adapter(registration.adapter, task)

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
        return RuntimeResult(
            task_id=task.task_id,
            runtime=getattr(adapter, "runtime_name", "unknown"),
            backend=getattr(adapter, "backend_name", "unknown"),
            status="error",
            error_class="UnsupportedTaskType",
            error_message=f"Unknown task_type: {task.task_type!r}",
        )


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


# ---------------------------------------------------------------------------
# CLI entry — python -m core.runtime.runtime_registry execute <builder> <spec_path>
# ---------------------------------------------------------------------------

_CLI_USAGE = """\
Usage: python -m core.runtime.runtime_registry <command> [args]

Commands:
  execute <builder> <spec_path>
      Dispatch a spec file to the named builder runtime.
      builder: one of claude, codex, ollama
      spec_path: path to a non-empty Markdown spec file

Exit codes:
  0 — success
  2 — unknown builder
  3 — malformed spec (file not found or empty)
"""


def _cli_execute(builder: str, spec_path_str: str) -> None:
    """Core logic for the `execute` sub-command.  Exits directly."""
    import argparse  # noqa: F401 (stdlib — already imported at top of stdlib chain)

    # ── Validate spec ─────────────────────────────────────────────────────
    spec_path = Path(spec_path_str)
    if not spec_path.exists():
        print(
            f"ERROR: spec file not found: {spec_path_str}",
            file=sys.stderr,
        )
        sys.exit(3)

    spec_text = spec_path.read_text(encoding="utf-8").strip()
    if not spec_text:
        print(
            f"ERROR: spec file is empty (malformed): {spec_path_str}",
            file=sys.stderr,
        )
        sys.exit(3)

    # ── Validate builder ──────────────────────────────────────────────────
    if builder not in SUPPORTED_RUNTIME_NAMES:
        print(
            f"ERROR: unknown builder {builder!r}. "
            f"Supported: {', '.join(SUPPORTED_RUNTIME_NAMES)}",
            file=sys.stderr,
        )
        sys.exit(2)

    # ── Dry-run mode (tests/CI) ───────────────────────────────────────────
    if os.environ.get("BR3_DISPATCH_DRY_RUN") == "1":
        result = {
            "status": "dry_run",
            "builder": builder,
            "spec_path": spec_path_str,
            "spec_len": len(spec_text),
        }
        print(json.dumps(result))
        sys.exit(0)

    # ── Real dispatch ─────────────────────────────────────────────────────
    registry = create_runtime_registry()

    task = RuntimeTask(
        task_id=f"cli-{builder}-{spec_path.stem}",
        task_type="execution",
        diff_text="",
        spec_text=spec_text,
        project_root=str(Path.cwd()),
        commit_sha="",
        authoritative_runtime=builder,
    )

    result_obj: RuntimeResult = registry.execute(task)
    output = {
        "status": result_obj.status,
        "builder": builder,
        "spec_path": spec_path_str,
        "runtime": result_obj.runtime,
        "backend": result_obj.backend,
    }
    if result_obj.error_message:
        output["error"] = result_obj.error_message
    print(json.dumps(output))
    sys.exit(0 if result_obj.status == "success" else 1)


def _cli_main(argv: list[str] | None = None) -> None:
    """Entry point for `python -m core.runtime.runtime_registry`."""
    import argparse

    args = argv if argv is not None else sys.argv[1:]

    parser = argparse.ArgumentParser(
        prog="python -m core.runtime.runtime_registry",
        description="BR3 runtime dispatcher CLI",
        add_help=True,
    )
    subparsers = parser.add_subparsers(dest="command")

    exec_parser = subparsers.add_parser(
        "execute",
        help="Dispatch a spec to a builder runtime",
    )
    exec_parser.add_argument(
        "builder",
        help=f"Runtime builder name. One of: {', '.join(SUPPORTED_RUNTIME_NAMES)}",
    )
    exec_parser.add_argument(
        "spec_path",
        help="Path to a non-empty Markdown spec file",
    )

    parsed = parser.parse_args(args)

    if parsed.command == "execute":
        _cli_execute(parsed.builder, parsed.spec_path)
    else:
        print(_CLI_USAGE, file=sys.stderr)
        sys.exit(2)


if __name__ == "__main__":  # pragma: no cover
    _cli_main()
