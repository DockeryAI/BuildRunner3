"""Versioned BR3 runtime task/result schema support."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


RUNTIME_TASK_SCHEMA_VERSION = "br3.runtime.task.v1"
RUNTIME_RESULT_SCHEMA_VERSION = "br3.runtime.result.v1"
RUNTIME_STREAM_EVENT_SCHEMA_VERSION = "br3.runtime.stream_event.v1"
RUNTIME_CHECKPOINT_SCHEMA_VERSION = "br3.runtime.checkpoint.v1"
RUNTIME_OBSERVED_CHANGE_SCHEMA_VERSION = "br3.runtime.observed_change.v1"


@dataclass
class StreamEvent:
    """Buffered or streaming progress event emitted by a runtime."""

    event_type: str
    sequence: int = 0
    message: str = ""
    payload: dict[str, Any] = field(default_factory=dict)
    timestamp: str | None = None
    schema_version: str = RUNTIME_STREAM_EVENT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class CheckpointRecord:
    """BR3-owned orchestration checkpoint, not a model-internal continuation handle."""

    checkpoint_id: str
    task_id: str
    runtime: str
    status: str
    current_step: str
    timestamp: str
    log_entries: list[dict[str, Any]] = field(default_factory=list)
    workspace_diff: str = ""
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = RUNTIME_CHECKPOINT_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ObservedChange:
    """Observed file impact inferred from workspace diff or tool/shell payloads."""

    path: str
    change_type: str
    source: str
    metadata: dict[str, Any] = field(default_factory=dict)
    schema_version: str = RUNTIME_OBSERVED_CHANGE_SCHEMA_VERSION

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)
