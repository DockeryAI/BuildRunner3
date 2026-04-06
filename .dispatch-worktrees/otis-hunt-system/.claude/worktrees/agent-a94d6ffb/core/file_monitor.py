"""
File Monitor for Task Orchestration

Monitors file system for task completion by watching for file creation,
modification, and deletion events.
"""

from pathlib import Path
from typing import List, Dict, Optional, Set, Callable
from datetime import datetime
import time


class FileMonitor:
    """
    Monitors file system for task-related changes.

    Responsibilities:
    - Watch for file creation
    - Detect file modifications
    - Track expected files
    - Report missing files
    - Notify on completion
    """

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.expected_files: Set[Path] = set()
        self.created_files: Set[Path] = set()
        self.modified_files: Set[Path] = set()
        self.missing_files: Set[Path] = set()

        # Statistics
        self.checks_performed = 0
        self.files_detected = 0

    def expect_file(self, file_path: str) -> bool:
        """
        Add file to watch list.

        Args:
            file_path: Path to file to watch

        Returns:
            True if added successfully
        """
        path = self.project_root / file_path
        self.expected_files.add(path)
        return True

    def expect_files(self, file_paths: List[str]) -> int:
        """
        Add multiple files to watch list.

        Args:
            file_paths: List of file paths to watch

        Returns:
            Number of files added
        """
        added = 0
        for file_path in file_paths:
            if self.expect_file(file_path):
                added += 1
        return added

    def check_file_exists(self, file_path: str) -> bool:
        """
        Check if file exists.

        Args:
            file_path: Path to check

        Returns:
            True if file exists
        """
        path = self.project_root / file_path
        return path.exists()

    def check_all_expected_files(self) -> Dict:
        """
        Check all expected files.

        Returns:
            Dictionary with check results
        """
        self.checks_performed += 1

        created = set()
        missing = set()

        for path in self.expected_files:
            if path.exists():
                created.add(path)
                if path not in self.created_files:
                    self.files_detected += 1
                self.created_files.add(path)
            else:
                missing.add(path)

        self.missing_files = missing

        return {
            "total_expected": len(self.expected_files),
            "created": len(created),
            "missing": len(missing),
            "all_created": len(missing) == 0,
            "created_files": [str(f.relative_to(self.project_root)) for f in created],
            "missing_files": [str(f.relative_to(self.project_root)) for f in missing],
        }

    def wait_for_files(
        self,
        timeout_seconds: int = 300,
        check_interval: float = 1.0,
        on_progress: Optional[Callable] = None,
    ) -> bool:
        """
        Wait for all expected files to be created.

        Args:
            timeout_seconds: Maximum time to wait
            check_interval: Seconds between checks
            on_progress: Optional progress callback

        Returns:
            True if all files created, False if timeout
        """
        start_time = time.time()

        while time.time() - start_time < timeout_seconds:
            result = self.check_all_expected_files()

            if on_progress:
                on_progress(result)

            if result["all_created"]:
                return True

            time.sleep(check_interval)

        return False

    def get_file_stats(self, file_path: str) -> Optional[Dict]:
        """
        Get file statistics.

        Args:
            file_path: Path to file

        Returns:
            Dictionary with file stats or None
        """
        path = self.project_root / file_path

        if not path.exists():
            return None

        stat = path.stat()
        return {
            "path": str(path.relative_to(self.project_root)),
            "size_bytes": stat.st_size,
            "created": datetime.fromtimestamp(stat.st_ctime),
            "modified": datetime.fromtimestamp(stat.st_mtime),
            "is_file": path.is_file(),
            "is_dir": path.is_dir(),
        }

    def scan_directory(self, directory: str, pattern: str = "*.py") -> List[str]:
        """
        Scan directory for files matching pattern.

        Args:
            directory: Directory to scan
            pattern: Glob pattern to match

        Returns:
            List of matching file paths
        """
        dir_path = self.project_root / directory

        if not dir_path.exists():
            return []

        matches = list(dir_path.glob(pattern))
        return [str(f.relative_to(self.project_root)) for f in matches]

    def clear_expectations(self):
        """Clear all expected files"""
        self.expected_files = set()
        self.created_files = set()
        self.modified_files = set()
        self.missing_files = set()

    def get_stats(self) -> Dict:
        """Get monitor statistics"""
        return {
            "checks_performed": self.checks_performed,
            "files_detected": self.files_detected,
            "expected_files": len(self.expected_files),
            "created_files": len(self.created_files),
            "missing_files": len(self.missing_files),
        }
