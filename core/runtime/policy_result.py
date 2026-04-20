"""Shared policy result types for BR3 runtime preflight and postflight stages."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


POLICY_ACTION_PASS = "pass"
POLICY_ACTION_WARN = "warn"
POLICY_ACTION_BLOCK = "block"
POLICY_ACTIONS = {POLICY_ACTION_PASS, POLICY_ACTION_WARN, POLICY_ACTION_BLOCK}


@dataclass
class PolicyResult:
    """One normalized policy decision emitted by BR3-owned governance."""

    policy_id: str
    stage: str
    action: str
    message: str
    details: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.action not in POLICY_ACTIONS:
            raise ValueError(f"Unsupported policy action: {self.action}")

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class PolicyEvaluation:
    """Collection of policy results plus derived summary state."""

    stage: str
    results: list[PolicyResult] = field(default_factory=list)
    additional_context: list[str] = field(default_factory=list)

    @property
    def blocked(self) -> bool:
        return any(result.action == POLICY_ACTION_BLOCK for result in self.results)

    @property
    def warning_count(self) -> int:
        return sum(1 for result in self.results if result.action == POLICY_ACTION_WARN)

    @property
    def block_count(self) -> int:
        return sum(1 for result in self.results if result.action == POLICY_ACTION_BLOCK)

    def add(
        self,
        *,
        policy_id: str,
        action: str,
        message: str,
        details: dict[str, Any] | None = None,
    ) -> None:
        policy = PolicyResult(
            policy_id=policy_id,
            stage=self.stage,
            action=action,
            message=message,
            details=details or {},
        )
        for index, existing in enumerate(self.results):
            if existing.policy_id == policy_id:
                self.results[index] = policy
                return
        self.results.append(policy)

    def extend_context(self, *messages: str) -> None:
        for message in messages:
            if message:
                self.additional_context.append(message)

    def to_dict(self) -> dict[str, Any]:
        return {
            "stage": self.stage,
            "blocked": self.blocked,
            "warning_count": self.warning_count,
            "block_count": self.block_count,
            "results": [result.to_dict() for result in self.results],
            "additional_context": list(self.additional_context),
        }


def build_hook_payload(message: str, event_name: str) -> dict[str, Any]:
    return {"hookSpecificOutput": {"hookEventName": event_name, "additionalContext": message}}
