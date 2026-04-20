"""Capability profiles for BR3 runtime adapters."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class CapabilityProfile:
    """Versioned capability flags exposed by a runtime adapter."""

    schema_version: str = "br3.runtime.capability.v1"
    review: bool = False
    analysis: bool = False
    plan: bool = False
    execution: bool = False
    subagents: bool = False
    streaming: bool = False
    shell: bool = False
    browser: bool = False
    orchestration_checkpoint: bool = False
    cluster_suitable: bool = False
    isolated_workspace_only: bool = False
    edit_formats: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_legacy(cls, payload: dict[str, Any] | None) -> "CapabilityProfile":
        payload = dict(payload or {})
        return cls(
            review=bool(payload.get("review", False)),
            analysis=bool(payload.get("analysis", False)),
            plan=bool(payload.get("plan", False)),
            execution=bool(payload.get("execution", False)),
            subagents=bool(payload.get("subagents", False)),
            streaming=bool(payload.get("streaming", payload.get("json_events", False))),
            shell=bool(payload.get("shell", False)),
            browser=bool(payload.get("browser", False)),
            orchestration_checkpoint=bool(payload.get("orchestration_checkpoint", False)),
            cluster_suitable=bool(payload.get("cluster_suitable", False)),
            isolated_workspace_only=bool(payload.get("isolated_workspace_only", False)),
            edit_formats=list(payload.get("edit_formats", [])),
            metadata={k: v for k, v in payload.items() if k not in {
                "review",
                "analysis",
                "plan",
                "execution",
                "subagents",
                "streaming",
                "shell",
                "browser",
                "orchestration_checkpoint",
                "cluster_suitable",
                "isolated_workspace_only",
                "edit_formats",
                "json_events",
            }},
        )
