"""
Tests for Fallback Handler

Tests the model fallback strategies that work with AI routing.
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from core.routing.fallback_handler import (
    FallbackHandler,
    FallbackStrategy,
    FailureReason,
    FailureEvent,
)


class TestFallbackHandler:
    """Test suite for FallbackHandler."""

    @pytest.fixture
    def handler(self):
        """Create a FallbackHandler instance."""
        return FallbackHandler()

    def test_handle_rate_limit_switches_to_alternative(self, handler):
        """Test rate limit switches to alternative model."""
        error = Exception("Rate limit exceeded")
        alternatives = ["sonnet", "opus"]

        next_model, should_retry = handler.handle_failure(
            model="haiku", error=error, task_id="task-1", alternatives=alternatives, retry_count=0
        )

        # Should switch to first alternative
        assert next_model == "sonnet"
        assert should_retry is False

    def test_handle_context_length_upgrades_model(self, handler):
        """Test context length error upgrades to larger model."""
        error = Exception("Context length exceeded: token limit reached")
        alternatives = ["opus"]  # Larger context

        next_model, should_retry = handler.handle_failure(
            model="haiku",
            error=error,
            task_id="task-2",
            alternatives=alternatives,
            retry_count=0,
            strategy=FallbackStrategy.UPGRADE,
        )

        # Should upgrade to opus
        assert next_model == "opus"
        assert should_retry is False

    def test_handle_timeout_retries_with_backoff(self, handler):
        """Test timeout retries same model with backoff."""
        error = Exception("Request timed out")
        alternatives = ["sonnet"]

        next_model, should_retry = handler.handle_failure(
            model="haiku", error=error, task_id="task-3", alternatives=alternatives, retry_count=0
        )

        # Should retry same model
        assert next_model == "haiku"
        assert should_retry is True

    def test_handle_timeout_switches_after_max_retries(self, handler):
        """Test timeout switches to alternative after max retries."""
        error = Exception("Request timed out")
        alternatives = ["sonnet"]

        next_model, should_retry = handler.handle_failure(
            model="haiku",
            error=error,
            task_id="task-4",
            alternatives=alternatives,
            retry_count=3,  # At max retries
        )

        # Should switch to alternative
        assert next_model == "sonnet"
        assert should_retry is False

    def test_handle_unavailable_tries_alternative(self, handler):
        """Test unavailable model tries alternative immediately."""
        error = Exception("Model unavailable")
        alternatives = ["sonnet"]

        next_model, should_retry = handler.handle_failure(
            model="haiku", error=error, task_id="task-5", alternatives=alternatives, retry_count=0
        )

        # Should try alternative immediately
        assert next_model == "sonnet"
        assert should_retry is False

    def test_handle_server_error_retries(self, handler):
        """Test server error retries with backoff."""
        error = Exception("Server error: 500 Internal Server Error")
        alternatives = ["sonnet"]

        next_model, should_retry = handler.handle_failure(
            model="haiku", error=error, task_id="task-6", alternatives=alternatives, retry_count=0
        )

        # Should retry same model (transient error)
        assert next_model == "haiku"
        assert should_retry is True

    def test_failure_history_tracking(self, handler):
        """Test failures are tracked in history."""
        error = Exception("Rate limit exceeded")

        handler.handle_failure(
            model="haiku", error=error, task_id="task-7", alternatives=["sonnet"], retry_count=0
        )

        # Check history
        assert len(handler.failure_history) == 1
        failure = handler.failure_history[0]
        assert failure.model == "haiku"
        assert failure.reason == FailureReason.RATE_LIMIT
        assert failure.task_id == "task-7"

    def test_execute_with_fallback_success_first_try(self, handler):
        """Test execute_with_fallback succeeds on first try."""

        def execute_fn(model):
            return f"Success with {model}"

        result = handler.execute_with_fallback(
            model="haiku", task_id="task-8", execute_fn=execute_fn, alternatives=["sonnet", "opus"]
        )

        assert result == "Success with haiku"

    def test_execute_with_fallback_retries_on_error(self, handler):
        """Test execute_with_fallback tries alternatives on failure."""
        call_count = 0

        def execute_fn(model):
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise Exception("Rate limit exceeded")
            return f"Success with {model}"

        result = handler.execute_with_fallback(
            model="haiku", task_id="task-9", execute_fn=execute_fn, alternatives=["sonnet"]
        )

        # Should succeed with alternative
        assert "Success with sonnet" in result
        assert call_count == 2

    def test_classify_failure_rate_limit(self, handler):
        """Test failure classification detects rate limits."""
        error = Exception("Rate limit exceeded")
        reason = handler._classify_failure(error)
        assert reason == FailureReason.RATE_LIMIT

    def test_classify_failure_context_length(self, handler):
        """Test failure classification detects context length errors."""
        error = Exception("Context token limit exceeded")
        reason = handler._classify_failure(error)
        assert reason == FailureReason.CONTEXT_LENGTH

    def test_classify_failure_timeout(self, handler):
        """Test failure classification detects timeouts."""
        error = Exception("Request timed out")
        reason = handler._classify_failure(error)
        assert reason == FailureReason.TIMEOUT

    def test_classify_failure_unavailable(self, handler):
        """Test failure classification detects unavailability."""
        error = Exception("Model unavailable")
        reason = handler._classify_failure(error)
        assert reason == FailureReason.UNAVAILABLE

    def test_get_statistics(self, handler):
        """Test statistics calculation."""
        # Add some failures
        for i in range(5):
            try:
                handler.handle_failure(
                    model="haiku",
                    error=Exception("Rate limit exceeded"),
                    task_id=f"task-{i}",
                    alternatives=["sonnet"],
                    retry_count=i,
                )
            except:
                pass

        stats = handler.get_statistics()

        assert stats["total_failures"] == 5
        assert "haiku" in stats["failures_by_model"]
        assert stats["most_common_failure"] == "rate_limit"

    def test_rate_limit_tracking(self, handler):
        """Test rate limit detection and tracking."""
        # Simulate multiple rate limits
        for i in range(3):
            handler._record_rate_limit("haiku")

        # Should be detected as rate limited
        assert handler._is_rate_limited("haiku") is True

        # Other models should not be rate limited
        assert handler._is_rate_limited("sonnet") is False
