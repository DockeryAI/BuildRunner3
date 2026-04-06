"""Tests for FileMonitor"""

import pytest
from core.file_monitor import FileMonitor
from pathlib import Path
import tempfile
import shutil


class TestFileMonitor:
    @pytest.fixture
    def temp_project_root(self):
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def monitor(self, temp_project_root):
        return FileMonitor(project_root=temp_project_root)

    def test_init(self, monitor, temp_project_root):
        assert monitor.project_root == temp_project_root
        assert len(monitor.expected_files) == 0

    def test_expect_file(self, monitor):
        result = monitor.expect_file("core/test.py")
        assert result is True
        assert len(monitor.expected_files) == 1

    def test_expect_files(self, monitor):
        added = monitor.expect_files(["core/test1.py", "core/test2.py"])
        assert added == 2

    def test_check_file_exists_not_found(self, monitor):
        result = monitor.check_file_exists("nonexistent.py")
        assert result is False

    def test_check_file_exists_found(self, monitor, temp_project_root):
        # Create file
        test_file = temp_project_root / "test.py"
        test_file.write_text("# test")

        result = monitor.check_file_exists("test.py")
        assert result is True

    def test_check_all_expected_files(self, monitor, temp_project_root):
        # Create one file
        test_file = temp_project_root / "exists.py"
        test_file.write_text("# test")

        # Expect two files
        monitor.expect_files(["exists.py", "missing.py"])

        result = monitor.check_all_expected_files()
        assert result["total_expected"] == 2
        assert result["created"] == 1
        assert result["missing"] == 1

    def test_clear_expectations(self, monitor):
        monitor.expect_file("test.py")
        monitor.clear_expectations()
        assert len(monitor.expected_files) == 0

    def test_get_stats(self, monitor):
        stats = monitor.get_stats()
        assert "checks_performed" in stats
        assert "files_detected" in stats
