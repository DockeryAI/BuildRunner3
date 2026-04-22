from __future__ import annotations

import datetime as dt  # noqa: TC003
from typing import Literal

from pydantic import BaseModel, ConfigDict, model_validator


class DispatchMetrics(BaseModel):
    model_config = ConfigDict(frozen=True)

    timestamp: dt.datetime
    session_id: str
    bucket: str
    builder: Literal["claude", "codex", "ollama"]
    model: str
    effort: Literal["xhigh", "high", "medium", "low"]
    prompt_tokens: int
    output_tokens: int
    latency_ms: int
    done_when_passed: bool
    verdict: Literal["passed", "blocked", "overridden"]
    override_reason: str | None = None

    @model_validator(mode="after")
    def validate_override_reason(self) -> DispatchMetrics:
        if self.verdict == "overridden" and not self.override_reason:
            raise ValueError("override_reason is required when verdict is overridden")
        return self
