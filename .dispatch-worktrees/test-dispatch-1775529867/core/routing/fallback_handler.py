"""
Fallback Handler - Manages model failures and fallback strategies

Handles:
- Model unavailability
- Rate limit errors
- API errors
- Automatic retries with exponential backoff
- Fallback to alternative models
"""

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from typing import Callable, Dict, List, Optional
import time


class FallbackStrategy(str, Enum):
    """Fallback strategies for handling model failures."""

    RETRY = "retry"  # Retry same model with backoff
    DOWNGRADE = "downgrade"  # Use cheaper/faster model
    UPGRADE = "upgrade"  # Use better model (if original failed on capability)
    ROUND_ROBIN = "round_robin"  # Try alternatives in order
    BEST_AVAILABLE = "best_available"  # Pick best available alternative


class FailureReason(str, Enum):
    """Reasons for model failure."""

    UNAVAILABLE = "unavailable"  # Model/API unavailable
    RATE_LIMIT = "rate_limit"  # Rate limit exceeded
    TIMEOUT = "timeout"  # Request timed out
    CONTEXT_LENGTH = "context_length"  # Context too long for model
    INVALID_REQUEST = "invalid_request"  # Bad request format
    SERVER_ERROR = "server_error"  # Server-side error
    UNKNOWN = "unknown"  # Unknown error


@dataclass
class FailureEvent:
    """Record of a model failure."""

    timestamp: datetime
    model: str
    reason: FailureReason
    error_message: str
    task_id: str
    retry_count: int = 0
    succeeded_after_retry: bool = False
    fallback_model: Optional[str] = None


class FallbackHandler:
    """Handles model failures and implements fallback strategies."""

    # Retry configuration
    MAX_RETRIES = 3
    INITIAL_BACKOFF_SECONDS = 1.0
    MAX_BACKOFF_SECONDS = 60.0
    BACKOFF_MULTIPLIER = 2.0

    # Rate limit tracking
    RATE_LIMIT_WINDOW_SECONDS = 60

    def __init__(
        self,
        default_strategy: FallbackStrategy = FallbackStrategy.BEST_AVAILABLE,
        max_retries: int = MAX_RETRIES,
    ):
        """
        Initialize fallback handler.

        Args:
            default_strategy: Default fallback strategy
            max_retries: Maximum retry attempts
        """
        self.default_strategy = default_strategy
        self.max_retries = max_retries

        self.failure_history: List[FailureEvent] = []
        self.rate_limit_tracker: Dict[str, List[datetime]] = {}

    def handle_failure(
        self,
        model: str,
        error: Exception,
        task_id: str,
        alternatives: List[str],
        retry_count: int = 0,
        strategy: Optional[FallbackStrategy] = None,
    ) -> tuple[str, bool]:
        """
        Handle model failure and determine next action.

        Args:
            model: Model that failed
            error: Exception that occurred
            task_id: Task identifier
            alternatives: List of alternative models
            retry_count: Current retry count
            strategy: Fallback strategy (uses default if None)

        Returns:
            Tuple of (next_model_to_try, should_retry)
        """
        strategy = strategy or self.default_strategy

        # Classify failure
        reason = self._classify_failure(error)

        # Record failure
        failure = FailureEvent(
            timestamp=datetime.now(),
            model=model,
            reason=reason,
            error_message=str(error),
            task_id=task_id,
            retry_count=retry_count,
        )
        self.failure_history.append(failure)

        # Handle rate limits
        if reason == FailureReason.RATE_LIMIT:
            self._record_rate_limit(model)

        # Determine action based on failure reason and strategy
        if reason == FailureReason.RATE_LIMIT:
            # Always switch to alternative on rate limit
            if alternatives:
                # Find alternative not rate limited
                for alt in alternatives:
                    if not self._is_rate_limited(alt):
                        return alt, False

            # All alternatives rate limited, wait and retry
            if retry_count < self.max_retries:
                self._wait_for_backoff(retry_count)
                return model, True
            else:
                raise RuntimeError(f"All models rate limited and max retries exceeded")

        elif reason == FailureReason.CONTEXT_LENGTH:
            # Need to upgrade to model with larger context
            if strategy == FallbackStrategy.UPGRADE and alternatives:
                # Find model with larger context (assume alternatives are ordered)
                return alternatives[0], False
            else:
                raise RuntimeError(f"Context too large for model: {model}")

        elif reason == FailureReason.UNAVAILABLE:
            # Model unavailable, try alternative immediately
            if alternatives:
                return alternatives[0], False
            elif retry_count < self.max_retries:
                self._wait_for_backoff(retry_count)
                return model, True
            else:
                raise RuntimeError(f"Model unavailable and no alternatives")

        elif reason in [FailureReason.TIMEOUT, FailureReason.SERVER_ERROR]:
            # Transient errors - retry with backoff
            if retry_count < self.max_retries:
                self._wait_for_backoff(retry_count)
                return model, True
            elif alternatives:
                # Max retries exceeded, try alternative
                return alternatives[0], False
            else:
                raise RuntimeError(f"Max retries exceeded and no alternatives")

        elif reason == FailureReason.INVALID_REQUEST:
            # Don't retry invalid requests
            if alternatives:
                # Maybe different model will accept it
                return alternatives[0], False
            else:
                raise RuntimeError(f"Invalid request: {error}")

        else:  # UNKNOWN
            # Generic retry strategy
            if retry_count < self.max_retries:
                self._wait_for_backoff(retry_count)
                return model, True
            elif alternatives:
                return alternatives[0], False
            else:
                raise RuntimeError(f"Unknown error and no fallback: {error}")

    def execute_with_fallback(
        self,
        model: str,
        task_id: str,
        execute_fn: Callable[[str], any],
        alternatives: List[str],
        strategy: Optional[FallbackStrategy] = None,
    ) -> any:
        """
        Execute a function with automatic fallback handling.

        Args:
            model: Initial model to use
            task_id: Task identifier
            execute_fn: Function that takes model name and executes task
            alternatives: List of alternative models
            strategy: Fallback strategy

        Returns:
            Result from execute_fn

        Raises:
            RuntimeError: If all attempts fail
        """
        current_model = model
        retry_count = 0
        attempted_models = set()

        while True:
            # Prevent infinite loops
            if len(attempted_models) > 10:
                raise RuntimeError("Too many fallback attempts")

            attempted_models.add(current_model)

            try:
                # Execute the function
                result = execute_fn(current_model)

                # Success! Record if we had to fallback
                if current_model != model:
                    # Update the original failure to note we succeeded with fallback
                    if self.failure_history:
                        self.failure_history[-1].succeeded_after_retry = True
                        self.failure_history[-1].fallback_model = current_model

                return result

            except Exception as error:
                # Get remaining alternatives (not yet attempted)
                remaining_alternatives = [
                    alt for alt in alternatives if alt not in attempted_models
                ]

                # Handle the failure
                next_model, should_retry = self.handle_failure(
                    model=current_model,
                    error=error,
                    task_id=task_id,
                    alternatives=remaining_alternatives,
                    retry_count=retry_count,
                    strategy=strategy,
                )

                if should_retry:
                    # Retry same model
                    retry_count += 1
                else:
                    # Switch to different model
                    current_model = next_model
                    retry_count = 0

    def _classify_failure(self, error: Exception) -> FailureReason:
        """
        Classify failure reason from exception.

        Args:
            error: Exception that occurred

        Returns:
            FailureReason classification
        """
        error_str = str(error).lower()

        if "rate" in error_str and "limit" in error_str:
            return FailureReason.RATE_LIMIT
        elif "timeout" in error_str or "timed out" in error_str:
            return FailureReason.TIMEOUT
        elif "context" in error_str or "token" in error_str and "limit" in error_str:
            return FailureReason.CONTEXT_LENGTH
        elif "unavailable" in error_str or "not found" in error_str:
            return FailureReason.UNAVAILABLE
        elif "invalid" in error_str or "bad request" in error_str:
            return FailureReason.INVALID_REQUEST
        elif "server error" in error_str or "500" in error_str or "503" in error_str:
            return FailureReason.SERVER_ERROR
        else:
            return FailureReason.UNKNOWN

    def _wait_for_backoff(self, retry_count: int):
        """
        Wait for exponential backoff.

        Args:
            retry_count: Current retry attempt number
        """
        wait_time = min(
            self.INITIAL_BACKOFF_SECONDS * (self.BACKOFF_MULTIPLIER**retry_count),
            self.MAX_BACKOFF_SECONDS,
        )
        print(f"⏳ Waiting {wait_time:.1f}s before retry {retry_count + 1}/{self.max_retries}...")
        time.sleep(wait_time)

    def _record_rate_limit(self, model: str):
        """
        Record a rate limit hit.

        Args:
            model: Model that was rate limited
        """
        now = datetime.now()

        if model not in self.rate_limit_tracker:
            self.rate_limit_tracker[model] = []

        self.rate_limit_tracker[model].append(now)

        # Clean old entries
        cutoff = now - timedelta(seconds=self.RATE_LIMIT_WINDOW_SECONDS)
        self.rate_limit_tracker[model] = [
            ts for ts in self.rate_limit_tracker[model] if ts >= cutoff
        ]

    def _is_rate_limited(self, model: str) -> bool:
        """
        Check if model is currently rate limited.

        Args:
            model: Model to check

        Returns:
            True if model is rate limited
        """
        if model not in self.rate_limit_tracker:
            return False

        now = datetime.now()
        cutoff = now - timedelta(seconds=self.RATE_LIMIT_WINDOW_SECONDS)

        # Clean old entries
        self.rate_limit_tracker[model] = [
            ts for ts in self.rate_limit_tracker[model] if ts >= cutoff
        ]

        # Check if we hit rate limit recently (heuristic: 3+ failures in window)
        return len(self.rate_limit_tracker[model]) >= 3

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics on failures and fallbacks.

        Returns:
            Statistics dictionary
        """
        if not self.failure_history:
            return {
                "total_failures": 0,
                "failures_by_model": {},
                "failures_by_reason": {},
                "success_rate_after_fallback": 0.0,
            }

        total = len(self.failure_history)

        # Count by model
        by_model = {}
        for failure in self.failure_history:
            by_model[failure.model] = by_model.get(failure.model, 0) + 1

        # Count by reason
        by_reason = {}
        for failure in self.failure_history:
            by_reason[failure.reason.value] = by_reason.get(failure.reason.value, 0) + 1

        # Success after fallback
        successes = sum(1 for f in self.failure_history if f.succeeded_after_retry)
        success_rate = (successes / total) * 100 if total > 0 else 0.0

        return {
            "total_failures": total,
            "failures_by_model": by_model,
            "failures_by_reason": by_reason,
            "success_rate_after_fallback": success_rate,
            "most_common_failure": (
                max(by_reason.keys(), key=lambda k: by_reason[k]) if by_reason else None
            ),
            "avg_retries_per_failure": sum(f.retry_count for f in self.failure_history) / total,
        }
