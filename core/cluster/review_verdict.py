"""Canonical verdict schema for one-round cross-model review."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, Literal

from pydantic import BaseModel, ConfigDict, Field, field_validator

VerdictDict = dict[str, Any]


class ReviewerVerdict(BaseModel):
    name: str
    findings: list[dict[str, Any]] = Field(default_factory=list)
    duration_ms: int = 0
    status: str


class ArbiterVerdict(BaseModel):
    reasoning: str
    duration_ms: int = 0
    status: str
    reason: str | None = None


class Verdict(BaseModel):
    model_config = ConfigDict(populate_by_name=True, extra="forbid")

    pass_: bool = Field(alias="pass")
    verdict: Literal["PASS", "BLOCK"]
    reviewers: list[ReviewerVerdict] = Field(default_factory=list)
    arbiter: ArbiterVerdict
    circuit_state: Literal["closed", "open"]
    plan_hash: str
    review_round: int = 1
    escalated: bool = False
    reason: str | None = None
    fallback_logic: str | None = None
    last_opus_payload: Any | None = None
    blockers: list[dict[str, Any]] = Field(default_factory=list)
    arbiter_reasoning: str = ""

    @field_validator("review_round")
    @classmethod
    def validate_review_round(cls, value: int) -> int:
        if value != 1:
            raise ValueError("review_round must equal 1")
        return value

    @field_validator("escalated")
    @classmethod
    def validate_escalated(cls, value: bool) -> bool:
        if value is not False:
            raise ValueError("escalated must be false")
        return value

    def as_dict(self) -> VerdictDict:
        data = self.model_dump(by_alias=True)
        if not data.get("arbiter_reasoning"):
            data["arbiter_reasoning"] = self.arbiter.reasoning
        return data


def write_verdict(path: str | Path, verdict: Verdict | VerdictDict) -> Path:
    verdict_model = verdict if isinstance(verdict, Verdict) else Verdict(**verdict)
    output_path = Path(path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(verdict_model.as_dict(), indent=2) + "\n", encoding="utf-8")
    return output_path
