"""
Error Watcher Daemon for BuildRunner 3.0

Monitors log files and command outputs for errors, automatically updating
.buildrunner/context/blockers.md when issues are detected.
"""

import re
import time
from datetime import datetime
from pathlib import Path
from typing import List, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


class WatcherError(Exception):
    """Raised when error watcher operations fail."""

    pass


class ErrorPattern:
    """Common error patterns to detect."""

    PATTERNS = [
        # Python errors
        (r"(Traceback \(most recent call last\):.*?)(?=\n\n|\Z)", "Python Exception"),
        (r"(\w+Error: .*)", "Python Error"),
        (r"(AssertionError: .*)", "Assertion Failed"),
        # Test failures
        (r"(FAILED .*)", "Test Failure"),
        (r"(ERROR .*)", "Test Error"),
        (r"(\d+ failed.*)", "Multiple Test Failures"),
        # Build/compilation errors
        (r"(error: .*)", "Build Error"),
        (r"(fatal error: .*)", "Fatal Build Error"),
        # Network/connection errors
        (r"(Connection refused.*)", "Connection Error"),
        (r"(Timeout.*)", "Timeout Error"),
        (r"(Host not found.*)", "DNS Error"),
        # File system errors
        (r"(No such file or directory: .*)", "File Not Found"),
        (r"(Permission denied: .*)", "Permission Error"),
        (r"(cannot open file.*)", "File Access Error"),
        # Git errors
        (r"(git: .*)", "Git Error"),
        (r"(merge conflict.*)", "Merge Conflict"),
        # Generic errors
        (r"(\[ERROR\] .*)", "Generic Error"),
        (r"(Exception: .*)", "Exception"),
    ]

    @classmethod
    def find_errors(cls, content: str) -> List[tuple]:
        """
        Find all error patterns in content.

        Args:
            content: Text content to search

        Returns:
            List of (error_text, error_type) tuples
        """
        errors = []
        for pattern, error_type in cls.PATTERNS:
            matches = re.finditer(pattern, content, re.MULTILINE | re.DOTALL)
            for match in matches:
                errors.append((match.group(1).strip(), error_type))

        return errors


class LogFileHandler(FileSystemEventHandler):
    """Handles file system events for log monitoring."""

    def __init__(self, watcher: "ErrorWatcher"):
        """
        Initialize handler.

        Args:
            watcher: Parent ErrorWatcher instance
        """
        self.watcher = watcher
        self.processed_files: Set[str] = set()

    def on_modified(self, event):
        """Handle file modification events."""
        if isinstance(event, FileModifiedEvent) and not event.is_directory:
            file_path = Path(event.src_path)

            # Check if file matches watch patterns
            if self.watcher._should_watch_file(file_path):
                self.watcher._process_file(file_path)


class ErrorWatcher:
    """
    Daemon that monitors logs for errors and updates blockers.

    Watches log files and command outputs, automatically detecting
    errors and updating .buildrunner/context/blockers.md.

    Attributes:
        project_root: Root directory of project
        blockers_file: Path to blockers.md
        watch_patterns: File patterns to watch
        check_interval: Seconds between checks
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        watch_patterns: Optional[List[str]] = None,
        check_interval: int = 2,
    ):
        """
        Initialize ErrorWatcher.

        Args:
            project_root: Root directory. Defaults to current directory.
            watch_patterns: File patterns to watch (e.g., ['*.log', '*.err'])
            check_interval: Seconds between file checks
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.blockers_file = self.project_root / ".buildrunner" / "context" / "blockers.md"
        self.watch_patterns = watch_patterns or ["*.log", "*.err", "pytest.out"]
        self.check_interval = check_interval

        self.observer: Optional[Observer] = None
        self.is_running = False
        self.errors_detected = []

    def _should_watch_file(self, file_path: Path) -> bool:
        """
        Check if file should be watched.

        Args:
            file_path: Path to check

        Returns:
            True if file matches watch patterns
        """
        for pattern in self.watch_patterns:
            if file_path.match(pattern):
                return True
        return False

    def _process_file(self, file_path: Path) -> None:
        """
        Process file for errors.

        Args:
            file_path: Path to file to process
        """
        try:
            with open(file_path, "r") as f:
                content = f.read()

            errors = ErrorPattern.find_errors(content)

            if errors:
                self._update_blockers(file_path, errors)

        except Exception as e:
            print(f"Error processing {file_path}: {e}")

    def _update_blockers(self, source_file: Path, errors: List[tuple]) -> None:
        """
        Update blockers.md with detected errors.

        Args:
            source_file: Source file where errors were found
            errors: List of (error_text, error_type) tuples
        """
        try:
            # Ensure context directory exists
            self.blockers_file.parent.mkdir(parents=True, exist_ok=True)

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            # Build entry
            entry = f"""
---
## Auto-Detected Error - {timestamp}

**Source:** `{source_file}`
**Detected By:** Error Watcher Daemon

"""

            for error_text, error_type in errors:
                entry += f"""
### {error_type}
```
{error_text}
```

"""

            # Append to blockers file
            with open(self.blockers_file, "a") as f:
                f.write(entry)

            self.errors_detected.extend(errors)

        except Exception as e:
            raise WatcherError(f"Failed to update blockers: {e}")

    def start(self, daemon: bool = False) -> None:
        """
        Start error watcher.

        Args:
            daemon: If True, run in background. If False, block until stopped.

        Raises:
            WatcherError: If start fails
        """
        try:
            # Setup watchdog observer
            self.observer = Observer()
            handler = LogFileHandler(self)

            # Watch project root
            self.observer.schedule(handler, str(self.project_root), recursive=True)
            self.observer.start()

            self.is_running = True

            print(f"Error watcher started. Monitoring: {', '.join(self.watch_patterns)}")
            print(f"Blockers will be written to: {self.blockers_file}")

            if not daemon:
                # Block until stopped
                try:
                    while self.is_running:
                        time.sleep(self.check_interval)
                except KeyboardInterrupt:
                    self.stop()

        except Exception as e:
            raise WatcherError(f"Failed to start watcher: {e}")

    def stop(self) -> None:
        """Stop error watcher."""
        if self.observer:
            self.observer.stop()
            self.observer.join()

        self.is_running = False
        print("Error watcher stopped.")

    def scan_once(self) -> dict:
        """
        Perform one-time scan of all matching files.

        Returns:
            Dictionary with scan results

        Raises:
            WatcherError: If scan fails
        """
        scan_results = {"files_scanned": 0, "errors_found": 0, "files_with_errors": []}

        try:
            # Find all matching files
            for pattern in self.watch_patterns:
                for file_path in self.project_root.rglob(pattern):
                    if file_path.is_file():
                        scan_results["files_scanned"] += 1

                        with open(file_path, "r") as f:
                            content = f.read()

                        errors = ErrorPattern.find_errors(content)

                        if errors:
                            scan_results["errors_found"] += len(errors)
                            scan_results["files_with_errors"].append(str(file_path))
                            self._update_blockers(file_path, errors)

            return scan_results

        except Exception as e:
            raise WatcherError(f"Scan failed: {e}")

    def get_recent_errors(self, count: int = 5) -> List[dict]:
        """
        Get recent errors from blockers file.

        Args:
            count: Number of recent errors to retrieve

        Returns:
            List of error dictionaries

        Raises:
            WatcherError: If reading fails
        """
        if not self.blockers_file.exists():
            return []

        try:
            with open(self.blockers_file, "r") as f:
                content = f.read()

            # Parse entries
            entries = content.split("---\n")
            recent = entries[-count:] if len(entries) >= count else entries

            errors = []
            for entry in recent:
                if "## Auto-Detected Error" in entry:
                    errors.append({"content": entry, "timestamp": self._extract_timestamp(entry)})

            return errors

        except Exception as e:
            raise WatcherError(f"Failed to read recent errors: {e}")

    def _extract_timestamp(self, entry: str) -> Optional[str]:
        """Extract timestamp from blocker entry."""
        match = re.search(r"## Auto-Detected Error - ([\d\-: ]+)", entry)
        return match.group(1) if match else None

    def clear_blockers(self) -> None:
        """
        Clear the blockers file.

        Raises:
            WatcherError: If clearing fails
        """
        try:
            if self.blockers_file.exists():
                self.blockers_file.unlink()
        except Exception as e:
            raise WatcherError(f"Failed to clear blockers: {e}")


def start_watcher(
    project_root: Optional[Path] = None, daemon: bool = False, patterns: Optional[List[str]] = None
) -> ErrorWatcher:
    """
    Convenience function to start error watcher.

    Args:
        project_root: Project root directory
        daemon: Run in background
        patterns: File patterns to watch

    Returns:
        Started ErrorWatcher instance
    """
    watcher = ErrorWatcher(project_root, patterns)
    watcher.start(daemon=daemon)
    return watcher
