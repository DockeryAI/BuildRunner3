"""Versioned runtime task/result types for BR3 runtime adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

from core.runtime.capabilities import CapabilityProfile
from core.runtime.edit_normalizer import NormalizedEdit
from core.runtime.errors import RuntimeErrorInfo
from core.runtime.result_schema import (
    CheckpointRecord,
    ObservedChange,
    RUNTIME_RESULT_SCHEMA_VERSION,
    RUNTIME_TASK_SCHEMA_VERSION,
    StreamEvent,
)


@dataclass
class RuntimeFinding:
    """Normalized review finding owned by BR3, not the runtime backend."""

    finding: str
    severity: str = "note"
    source: str = ""

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeTask:
    """Versioned BR3 task envelope shared across runtimes."""

    task_id: str
    task_type: str
    diff_text: str
    spec_text: str
    project_root: str
    commit_sha: str
    schema_version: str = RUNTIME_TASK_SCHEMA_VERSION
    conflict_boundary: str | None = None
    authoritative_runtime: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.conflict_boundary is None:
            self.conflict_boundary = self.task_id

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class RuntimeResult:
    """Versioned BR3 runtime result envelope."""

    task_id: str
    runtime: str
    backend: str
    status: str
    schema_version: str = RUNTIME_RESULT_SCHEMA_VERSION
    findings: list[RuntimeFinding] = field(default_factory=list)
    normalized_edits: list[NormalizedEdit | dict[str, Any]] = field(default_factory=list)
    observed_changes: list[ObservedChange | dict[str, Any]] = field(default_factory=list)
    raw_output: str = ""
    raw_payload: dict[str, Any] = field(default_factory=dict)
    shell_actions: list[dict[str, Any]] = field(default_factory=list)
    stream_events: list[StreamEvent | dict[str, Any]] = field(default_factory=list)
    orchestration_checkpoints: list[CheckpointRecord | dict[str, Any]] = field(default_factory=list)
    workspace_diff: str = ""
    metrics: dict[str, Any] = field(default_factory=dict)
    error_class: str | None = None
    error_message: str | None = None
    error_info: RuntimeErrorInfo | dict[str, Any] | None = None
    capability_profile: CapabilityProfile | dict[str, Any] | None = None
    conflict_state: str | None = None
    authoritative_runtime: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        payload = asdict(self)
        payload["findings"] = [
            finding.to_dict() if hasattr(finding, "to_dict") else dict(finding)
            for finding in self.findings
        ]
        payload["normalized_edits"] = [
            edit.to_dict() if hasattr(edit, "to_dict") else dict(edit)
            for edit in self.normalized_edits
        ]
        payload["observed_changes"] = [
            change.to_dict() if hasattr(change, "to_dict") else dict(change)
            for change in self.observed_changes
        ]
        payload["stream_events"] = [
            event.to_dict() if hasattr(event, "to_dict") else dict(event)
            for event in self.stream_events
        ]
        payload["orchestration_checkpoints"] = [
            checkpoint.to_dict() if hasattr(checkpoint, "to_dict") else dict(checkpoint)
            for checkpoint in self.orchestration_checkpoints
        ]
        if self.error_info is not None:
            payload["error_info"] = (
                self.error_info.to_dict()
                if hasattr(self.error_info, "to_dict")
                else dict(self.error_info)
            )
        if self.capability_profile is not None:
            payload["capability_profile"] = (
                self.capability_profile.to_dict()
                if hasattr(self.capability_profile, "to_dict")
                else dict(self.capability_profile)
            )
        return payload
