"""Runtime contract error classes and retryability metadata."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any


@dataclass
class RuntimeErrorInfo:
    """Structured runtime error metadata for BR3 result envelopes."""

    error_class: str
    message: str
    retryable: bool
    metadata: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


class RuntimeContractError(Exception):
    """Base class for runtime contract failures."""

    retryable: bool = False


class RuntimeCompatibilityError(RuntimeContractError):
    retryable = False


class RuntimeValidationError(RuntimeContractError):
    retryable = False


class RuntimeExecutionError(RuntimeContractError):
    retryable = True


class RuntimeConflictError(RuntimeContractError):
    retryable = False


def build_error_info(error: Exception) -> RuntimeErrorInfo:
    """Convert an exception into structured runtime error metadata."""
    retryable = bool(getattr(error, "retryable", False))
    return RuntimeErrorInfo(
        error_class=error.__class__.__name__,
        message=str(error),
        retryable=retryable,
    )
