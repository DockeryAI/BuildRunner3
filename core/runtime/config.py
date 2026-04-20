"""Runtime config resolution for BR3."""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any


RUNTIME_CONFIG_SCHEMA_VERSION = "br3.runtime.config.v1"
SUPPORTED_RUNTIMES = ("claude", "codex")
PROJECT_RUNTIME_CONFIG_RELATIVE_PATH = Path(".buildrunner/runtime.json")


class RuntimeConfigError(ValueError):
    """Raised when runtime selection config is invalid."""


@dataclass
class RuntimeResolution:
    """Resolved runtime plus provenance."""

    runtime: str
    source: str
    explicit_runtime: str | None = None
    project_config_path: str | None = None
    user_config_path: str | None = None
    schema_version: str = RUNTIME_CONFIG_SCHEMA_VERSION
    available_runtimes: list[str] = field(default_factory=lambda: list(SUPPORTED_RUNTIMES))

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


def _validate_runtime(runtime: str | None) -> str | None:
    if runtime is None:
        return None
    normalized = runtime.strip().lower()
    if normalized not in SUPPORTED_RUNTIMES:
        raise RuntimeConfigError(
            f"Unsupported runtime '{runtime}'. Expected one of: {', '.join(SUPPORTED_RUNTIMES)}"
        )
    return normalized


def load_runtime_config(path: Path) -> dict[str, Any]:
    """Load one runtime config file."""
    payload = json.loads(path.read_text(encoding="utf-8"))
    runtime = _validate_runtime(payload.get("default_runtime") or payload.get("runtime"))
    if runtime is None:
        raise RuntimeConfigError(f"Runtime config at {path} does not define default_runtime")
    return {
        "runtime": runtime,
        "schema_version": payload.get("schema_version", RUNTIME_CONFIG_SCHEMA_VERSION),
        "raw": payload,
    }


def resolve_runtime_selection(
    *,
    explicit_runtime: str | None = None,
    project_root: str | Path | None = None,
    user_home: str | Path | None = None,
) -> RuntimeResolution:
    """Resolve runtime precedence exactly: explicit flag, project config, user config, default."""
    explicit = _validate_runtime(explicit_runtime)
    project_path = Path(project_root) if project_root else Path.cwd()
    home_path = Path(user_home) if user_home else Path.home()

    project_config_path = project_path / PROJECT_RUNTIME_CONFIG_RELATIVE_PATH
    user_config_path = home_path / ".buildrunner/runtime.json"

    if explicit:
        return RuntimeResolution(
            runtime=explicit,
            source="explicit",
            explicit_runtime=explicit,
            project_config_path=str(project_config_path) if project_config_path.exists() else None,
            user_config_path=str(user_config_path) if user_config_path.exists() else None,
        )

    if project_config_path.exists():
        project_config = load_runtime_config(project_config_path)
        return RuntimeResolution(
            runtime=project_config["runtime"],
            source="project_config",
            project_config_path=str(project_config_path),
            user_config_path=str(user_config_path) if user_config_path.exists() else None,
        )

    if user_config_path.exists():
        user_config = load_runtime_config(user_config_path)
        return RuntimeResolution(
            runtime=user_config["runtime"],
            source="user_config",
            user_config_path=str(user_config_path),
        )

    return RuntimeResolution(runtime="claude", source="default")


def apply_runtime_selection(resolution: RuntimeResolution) -> None:
    """Expose resolved runtime through process environment for downstream commands."""
    os.environ["BR3_RUNTIME"] = resolution.runtime
    os.environ["BR3_RUNTIME_SOURCE"] = resolution.source
