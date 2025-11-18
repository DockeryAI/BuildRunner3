"""
Tests for cli.main module

Basic tests for CLI commands. Full integration testing would require
mocking typer and testing command execution.
"""

import pytest
from pathlib import Path
from cli.main import get_project_root, retry_with_backoff


class TestHelperFunctions:
    """Test helper functions."""

    def test_get_project_root(self):
        """Test getting project root."""
        root = get_project_root()
        assert isinstance(root, Path)
        assert root == Path.cwd()

    def test_retry_with_backoff_success(self):
        """Test retry succeeds on first attempt."""
        call_count = [0]

        def func():
            call_count[0] += 1
            return "success"

        result = retry_with_backoff(func, max_retries=3)

        assert result == "success"
        assert call_count[0] == 1

    def test_retry_with_backoff_eventual_success(self):
        """Test retry succeeds after failures."""
        call_count = [0]

        def func():
            call_count[0] += 1
            if call_count[0] < 3:
                raise ValueError("Not yet")
            return "success"

        result = retry_with_backoff(func, max_retries=3, delays=[0.1, 0.1, 0.1])

        assert result == "success"
        assert call_count[0] == 3

    def test_retry_with_backoff_all_fail(self):
        """Test retry fails after max attempts."""
        call_count = [0]

        def func():
            call_count[0] += 1
            raise ValueError("Always fails")

        with pytest.raises(ValueError, match="Always fails"):
            retry_with_backoff(func, max_retries=3, delays=[0.1, 0.1, 0.1])

        assert call_count[0] == 3
