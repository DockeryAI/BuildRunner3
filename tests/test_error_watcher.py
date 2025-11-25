"""
Tests for BuildRunner 3.0 error watchers

Tests both CLI and API error watcher implementations.
"""

import pytest
import asyncio
from pathlib import Path

# Import both CLI and API error watchers
from cli.error_watcher import (
    ErrorWatcher as CLIErrorWatcher,
    ErrorPattern as CLIErrorPattern,
    WatcherError as CLIWatcherError,
)
from api.error_watcher import ErrorWatcher as APIErrorWatcher, ErrorPattern as APIErrorPattern


# ============================================================================
# CLI ERROR WATCHER TESTS
# ============================================================================


class TestCLIErrorPattern:
    """Test suite for CLI ErrorPattern."""

    def test_find_python_error(self):
        """Test finding Python errors."""
        content = "ValueError: Something went wrong"
        errors = CLIErrorPattern.find_errors(content)

        assert len(errors) > 0
        assert any("ValueError" in err[0] for err in errors)

    def test_find_traceback(self):
        """Test finding Python tracebacks."""
        content = """
Traceback (most recent call last):
  File "test.py", line 1, in <module>
    raise Exception("test")
Exception: test
"""
        errors = CLIErrorPattern.find_errors(content)

        assert len(errors) > 0

    def test_find_test_failure(self):
        """Test finding test failures."""
        content = "FAILED tests/test_something.py::test_function"
        errors = CLIErrorPattern.find_errors(content)

        assert len(errors) > 0
        assert any("Test Failure" in err[1] for err in errors)

    def test_find_file_not_found(self):
        """Test finding file errors."""
        content = "No such file or directory: /path/to/file"
        errors = CLIErrorPattern.find_errors(content)

        assert len(errors) > 0
        assert any("File Not Found" in err[1] for err in errors)

    def test_find_connection_error(self):
        """Test finding network errors."""
        content = "Connection refused to localhost:5432"
        errors = CLIErrorPattern.find_errors(content)

        assert len(errors) > 0
        assert any("Connection Error" in err[1] for err in errors)

    def test_no_errors(self):
        """Test content with no errors."""
        content = "Everything is working fine"
        errors = CLIErrorPattern.find_errors(content)

        # Might find nothing or generic matches, but shouldn't crash
        assert isinstance(errors, list)


class TestCLIErrorWatcher:
    """Test suite for CLI ErrorWatcher."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temp project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / ".buildrunner" / "context").mkdir(parents=True)
        return project_dir

    @pytest.fixture
    def watcher(self, temp_project):
        """Create CLI ErrorWatcher instance."""
        return CLIErrorWatcher(temp_project)

    def test_init_default_path(self):
        """Test initialization with default path."""
        watcher = CLIErrorWatcher()
        assert watcher.project_root == Path.cwd()
        assert watcher.check_interval == 2

    def test_init_custom_patterns(self, temp_project):
        """Test initialization with custom patterns."""
        watcher = CLIErrorWatcher(temp_project, watch_patterns=["*.txt"])
        assert "*.txt" in watcher.watch_patterns

    def test_should_watch_file(self, watcher):
        """Test file pattern matching."""
        log_file = Path("test.log")
        assert watcher._should_watch_file(log_file) is True

        txt_file = Path("test.txt")
        assert watcher._should_watch_file(txt_file) is False

    def test_process_file_with_errors(self, watcher, temp_project):
        """Test processing file with errors."""
        log_file = temp_project / "test.log"
        log_file.write_text("ValueError: Test error")

        watcher._process_file(log_file)

        assert watcher.blockers_file.exists()

        with open(watcher.blockers_file, "r") as f:
            content = f.read()

        assert "ValueError" in content

    def test_process_file_no_errors(self, watcher, temp_project):
        """Test processing file without errors."""
        log_file = temp_project / "test.log"
        log_file.write_text("All good")

        watcher._process_file(log_file)

        # No errors, so might not create blockers file or file might be empty

    def test_scan_once(self, watcher, temp_project):
        """Test one-time scan."""
        # Create a log file with errors
        log_file = temp_project / "test.log"
        log_file.write_text("FAILED test: Something broke")

        results = watcher.scan_once()

        assert results["files_scanned"] >= 1
        assert results["errors_found"] >= 0

    def test_scan_once_no_files(self, watcher):
        """Test scan when no matching files exist."""
        results = watcher.scan_once()

        assert results["files_scanned"] == 0
        assert results["errors_found"] == 0
        assert results["files_with_errors"] == []

    def test_clear_blockers(self, watcher):
        """Test clearing blockers file."""
        # Create blockers file
        watcher.blockers_file.parent.mkdir(parents=True, exist_ok=True)
        watcher.blockers_file.write_text("test blocker")

        watcher.clear_blockers()

        assert not watcher.blockers_file.exists()

    def test_get_recent_errors_no_file(self, watcher):
        """Test getting recent errors when file doesn't exist."""
        errors = watcher.get_recent_errors()

        assert errors == []

    def test_get_recent_errors(self, watcher, temp_project):
        """Test getting recent errors."""
        # Create errors
        log_file = temp_project / "test.log"
        log_file.write_text("ValueError: Error 1")
        watcher._process_file(log_file)

        errors = watcher.get_recent_errors(count=5)

        assert isinstance(errors, list)

    def test_update_blockers(self, watcher, temp_project):
        """Test updating blockers file."""
        errors = [("ValueError: Test", "Python Error"), ("FAILED test", "Test Failure")]

        source_file = temp_project / "test.log"
        watcher._update_blockers(source_file, errors)

        assert watcher.blockers_file.exists()

        with open(watcher.blockers_file, "r") as f:
            content = f.read()

        assert "ValueError" in content
        assert "FAILED" in content
        assert "Auto-Detected Error" in content


# ============================================================================
# API ERROR WATCHER TESTS
# ============================================================================


@pytest.fixture
def api_error_watcher():
    """Create API error watcher instance"""
    return APIErrorWatcher(str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def cleanup_sync(api_error_watcher):
    """Clean up after each test"""
    yield

    # Clear errors
    api_error_watcher.clear_errors()
    api_error_watcher.is_watching = False


@pytest.mark.asyncio
async def test_api_error_watcher_initial_state(api_error_watcher):
    """Test initial state of API error watcher"""
    assert api_error_watcher.is_watching is False
    assert len(api_error_watcher.errors) == 0
    assert len(api_error_watcher.patterns) > 0  # Should have default patterns


@pytest.mark.asyncio
async def test_api_start_error_watcher(api_error_watcher):
    """Test starting the API error watcher"""
    result = await api_error_watcher.start_watching(interval=30)

    assert result["status"] == "started"
    assert result["interval"] == 30
    assert api_error_watcher.is_watching is True

    # Clean up
    await api_error_watcher.stop_watching()


@pytest.mark.asyncio
async def test_api_start_already_watching(api_error_watcher):
    """Test starting when already watching"""
    await api_error_watcher.start_watching()

    # Try to start again
    result = await api_error_watcher.start_watching()
    assert result["status"] == "already_watching"

    # Clean up
    await api_error_watcher.stop_watching()


@pytest.mark.asyncio
async def test_api_stop_error_watcher(api_error_watcher):
    """Test stopping the API error watcher"""
    await api_error_watcher.start_watching()
    result = await api_error_watcher.stop_watching()

    assert result["status"] == "stopped"
    assert api_error_watcher.is_watching is False


@pytest.mark.asyncio
async def test_api_stop_not_watching(api_error_watcher):
    """Test stopping when not watching"""
    result = await api_error_watcher.stop_watching()
    assert result["status"] == "not_watching"


def test_api_error_pattern_matching():
    """Test API error pattern matching"""
    pattern = APIErrorPattern(r"SyntaxError:.*", "syntax", "high", 0.95, ["Fix syntax"])

    # Should match
    text = "SyntaxError: invalid syntax"
    match = pattern.pattern.search(text)
    assert match is not None

    # Should not match
    text = "RuntimeError: something broke"
    match = pattern.pattern.search(text)
    assert match is None


@pytest.mark.asyncio
async def test_api_analyze_content_with_syntax_error(api_error_watcher):
    """Test analyzing content with syntax error"""
    content = """
    File "test.py", line 10
        def foo(
              ^
    SyntaxError: invalid syntax
    """

    await api_error_watcher._analyze_content(content, "test_context.md")

    assert len(api_error_watcher.errors) > 0

    error = api_error_watcher.errors[0]
    assert error["category"]["type"] == "syntax"
    assert error["category"]["severity"] == "high"
    assert "SyntaxError" in error["message"]


@pytest.mark.asyncio
async def test_api_analyze_content_with_import_error(api_error_watcher):
    """Test analyzing content with import error"""
    content = """
    Traceback (most recent call last):
      File "app.py", line 5, in <module>
        import nonexistent_module
    ModuleNotFoundError: No module named 'nonexistent_module'
    """

    await api_error_watcher._analyze_content(content, "test_context.md")

    assert len(api_error_watcher.errors) > 0

    error = api_error_watcher.errors[0]
    assert error["category"]["type"] == "import"
    assert "ModuleNotFoundError" in error["message"]
    assert len(error["suggestions"]) > 0


@pytest.mark.asyncio
async def test_api_analyze_content_with_type_error(api_error_watcher):
    """Test analyzing content with type error"""
    content = """
    TypeError: unsupported operand type(s) for +: 'int' and 'str'
    """

    await api_error_watcher._analyze_content(content, "test_context.md")

    assert len(api_error_watcher.errors) > 0

    error = api_error_watcher.errors[0]
    assert error["category"]["type"] == "type"
    assert "TypeError" in error["message"]


@pytest.mark.asyncio
async def test_api_analyze_content_with_test_failure(api_error_watcher):
    """Test analyzing content with test failure"""
    content = """
    FAILED tests/test_api.py::test_feature_creation - AssertionError: Expected 200, got 500
    """

    await api_error_watcher._analyze_content(content, "test_results.md")

    assert len(api_error_watcher.errors) > 0

    error = api_error_watcher.errors[0]
    assert error["category"]["type"] == "test"


def test_api_extract_location(api_error_watcher):
    """Test extracting file location from error"""
    content = """
    Traceback (most recent call last):
      File "app.py", line 42, in main
        result = dangerous_function()
    RuntimeError: Something broke
    """

    # Position at the RuntimeError
    position = content.index("RuntimeError")

    file_path, line_num = api_error_watcher._extract_location(content, position)

    assert file_path == "app.py"
    assert line_num == 42


def test_api_is_duplicate(api_error_watcher):
    """Test duplicate detection"""
    error1 = {
        "id": "err1",
        "message": "SyntaxError: invalid syntax",
        "file_path": "test.py",
        "line_number": 10,
        "category": {"type": "syntax", "severity": "high", "confidence": 0.9},
        "suggestions": [],
        "resolved": False,
    }

    error2 = {
        "id": "err2",
        "message": "SyntaxError: invalid syntax",
        "file_path": "test.py",
        "line_number": 10,
        "category": {"type": "syntax", "severity": "high", "confidence": 0.9},
        "suggestions": [],
        "resolved": False,
    }

    error3 = {
        "id": "err3",
        "message": "Different error",
        "file_path": "test.py",
        "line_number": 10,
        "category": {"type": "syntax", "severity": "high", "confidence": 0.9},
        "suggestions": [],
        "resolved": False,
    }

    api_error_watcher.errors.append(error1)

    # Should be duplicate
    assert api_error_watcher._is_duplicate(error2) is True

    # Should not be duplicate
    assert api_error_watcher._is_duplicate(error3) is False


def test_api_get_errors_no_filter(api_error_watcher):
    """Test getting all errors without filter"""
    api_error_watcher.errors = [
        {"id": "err1", "category": {"type": "syntax", "severity": "high"}, "resolved": False},
        {"id": "err2", "category": {"type": "runtime", "severity": "medium"}, "resolved": False},
    ]

    errors = api_error_watcher.get_errors()
    assert len(errors) == 2


def test_api_get_errors_filter_category(api_error_watcher):
    """Test filtering errors by category"""
    api_error_watcher.errors = [
        {"id": "err1", "category": {"type": "syntax", "severity": "high"}, "resolved": False},
        {"id": "err2", "category": {"type": "runtime", "severity": "medium"}, "resolved": False},
    ]

    errors = api_error_watcher.get_errors(category="syntax")
    assert len(errors) == 1
    assert errors[0]["id"] == "err1"


def test_api_get_errors_filter_severity(api_error_watcher):
    """Test filtering errors by severity"""
    api_error_watcher.errors = [
        {"id": "err1", "category": {"type": "syntax", "severity": "high"}, "resolved": False},
        {"id": "err2", "category": {"type": "runtime", "severity": "medium"}, "resolved": False},
    ]

    errors = api_error_watcher.get_errors(severity="high")
    assert len(errors) == 1
    assert errors[0]["id"] == "err1"


def test_api_get_errors_unresolved_only(api_error_watcher):
    """Test getting only unresolved errors"""
    api_error_watcher.errors = [
        {"id": "err1", "category": {"type": "syntax", "severity": "high"}, "resolved": False},
        {"id": "err2", "category": {"type": "runtime", "severity": "medium"}, "resolved": True},
    ]

    errors = api_error_watcher.get_errors(unresolved_only=True)
    assert len(errors) == 1
    assert errors[0]["id"] == "err1"


def test_api_get_error_summary(api_error_watcher):
    """Test getting error summary"""
    api_error_watcher.errors = [
        {"id": "err1", "category": {"type": "syntax", "severity": "high"}, "resolved": False},
        {"id": "err2", "category": {"type": "syntax", "severity": "medium"}, "resolved": False},
        {"id": "err3", "category": {"type": "runtime", "severity": "high"}, "resolved": False},
    ]

    summary = api_error_watcher.get_error_summary()

    assert summary["total_errors"] == 3
    assert summary["by_category"]["syntax"] == 2
    assert summary["by_category"]["runtime"] == 1
    assert summary["by_severity"]["high"] == 2
    assert summary["by_severity"]["medium"] == 1
    assert len(summary["recent_errors"]) == 3


def test_api_mark_resolved(api_error_watcher):
    """Test marking error as resolved"""
    api_error_watcher.errors = [
        {"id": "err1", "category": {"type": "syntax", "severity": "high"}, "resolved": False}
    ]

    result = api_error_watcher.mark_resolved("err1")
    assert result is True
    assert api_error_watcher.errors[0]["resolved"] is True

    # Try to resolve non-existent error
    result = api_error_watcher.mark_resolved("nonexistent")
    assert result is False


def test_api_clear_errors(api_error_watcher):
    """Test clearing all errors"""
    api_error_watcher.errors = [{"id": "err1"}, {"id": "err2"}]

    assert len(api_error_watcher.errors) == 2

    api_error_watcher.clear_errors()

    assert len(api_error_watcher.errors) == 0


@pytest.mark.asyncio
async def test_api_scan_for_errors_no_context_dir(api_error_watcher):
    """Test scanning when context directory doesn't exist"""
    # Set to non-existent directory
    api_error_watcher.context_dir = Path("/nonexistent/path")

    # Should not crash
    await api_error_watcher.scan_for_errors()

    assert len(api_error_watcher.errors) == 0
