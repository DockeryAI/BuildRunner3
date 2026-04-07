"""
Error watcher for BuildRunner 3.0

Monitors context files for errors and suggests fixes.
Because errors are like cockroaches - you need to watch for them constantly.
"""

import asyncio
import re
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Optional
from uuid import uuid4


class ErrorPattern:
    """Error pattern for matching and categorization."""

    def __init__(
        self, pattern: str, category: str, severity: str, confidence: float, suggestions: List[str]
    ):
        self.pattern = re.compile(pattern, re.IGNORECASE | re.MULTILINE)
        self.category = category
        self.severity = severity
        self.confidence = confidence
        self.suggestions = suggestions


class ErrorWatcher:
    """
    Watches for errors in context files and categorizes them.

    Monitors .buildrunner/context/ directory for error patterns.
    Basically a sophisticated grep with delusions of grandeur.
    """

    def __init__(self, project_root: str = None):
        """
        Initialize error watcher.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root or ".")
        self.context_dir = self.project_root / ".buildrunner" / "context"
        self.errors: List[Dict[str, Any]] = []
        self.is_watching = False
        self.watch_task: Optional[asyncio.Task] = None

        # Error patterns - the rogues gallery of common failures
        self.patterns = [
            ErrorPattern(
                r"SyntaxError:.*",
                "syntax",
                "high",
                0.95,
                [
                    "Check for missing colons, parentheses, or brackets",
                    "Verify indentation is consistent",
                    "Look for unclosed strings or comments",
                ],
            ),
            ErrorPattern(
                r"IndentationError:.*",
                "syntax",
                "high",
                0.95,
                [
                    "Fix indentation - Python requires consistent indentation",
                    "Use either spaces or tabs, not both",
                    "Check that indentation matches the surrounding code",
                ],
            ),
            ErrorPattern(
                r"ModuleNotFoundError:.*|ImportError:.*",
                "import",
                "high",
                0.9,
                [
                    "Install the missing package: pip install <package>",
                    "Check if the module name is correct",
                    "Verify the package is in your requirements",
                ],
            ),
            ErrorPattern(
                r"TypeError:.*",
                "type",
                "medium",
                0.8,
                [
                    "Check function arguments match expected types",
                    "Verify variable types are correct",
                    "Look for None values where objects are expected",
                ],
            ),
            ErrorPattern(
                r"AttributeError:.*",
                "runtime",
                "medium",
                0.8,
                [
                    "Check if object has the attribute you're accessing",
                    "Verify object is not None",
                    "Check for typos in attribute names",
                ],
            ),
            ErrorPattern(
                r"KeyError:.*",
                "runtime",
                "medium",
                0.8,
                [
                    "Check if dictionary key exists before accessing",
                    "Use dict.get() with a default value",
                    "Verify the data structure matches expectations",
                ],
            ),
            ErrorPattern(
                r"FileNotFoundError:.*",
                "runtime",
                "medium",
                0.9,
                [
                    "Check if the file path is correct",
                    "Verify the file exists",
                    "Check file permissions",
                ],
            ),
            ErrorPattern(
                r"FAILED.*test_.*",
                "test",
                "high",
                0.85,
                [
                    "Review the test failure message",
                    "Check if test expectations match actual behavior",
                    "Verify test data and mocks are correct",
                ],
            ),
            ErrorPattern(
                r"AssertionError:.*",
                "test",
                "medium",
                0.8,
                [
                    "Check assertion conditions",
                    "Verify expected vs actual values",
                    "Review test logic",
                ],
            ),
            ErrorPattern(
                r"ConnectionError:.*|TimeoutError:.*",
                "network",
                "high",
                0.9,
                [
                    "Check network connectivity",
                    "Verify service is running",
                    "Check if endpoint URL is correct",
                ],
            ),
        ]

    async def start_watching(self, interval: int = 30):
        """
        Start watching for errors.

        Args:
            interval: Check interval in seconds
        """
        if self.is_watching:
            return {"status": "already_watching"}

        self.is_watching = True
        self.watch_task = asyncio.create_task(self._watch_loop(interval))

        return {"status": "started", "interval": interval, "message": "Error watcher started"}

    async def stop_watching(self):
        """Stop watching for errors."""
        if not self.is_watching:
            return {"status": "not_watching"}

        self.is_watching = False
        if self.watch_task:
            self.watch_task.cancel()
            try:
                await self.watch_task
            except asyncio.CancelledError:
                pass

        return {"status": "stopped", "message": "Error watcher stopped"}

    async def _watch_loop(self, interval: int):
        """Main error watching loop."""
        while self.is_watching:
            try:
                await self.scan_for_errors()
                await asyncio.sleep(interval)
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"Error in watch loop: {e}")
                await asyncio.sleep(interval)

    async def scan_for_errors(self):
        """Scan context directory for errors."""
        if not self.context_dir.exists():
            return

        # Scan all context files
        for file_path in self.context_dir.glob("*.md"):
            try:
                content = file_path.read_text()
                await self._analyze_content(content, str(file_path))
            except Exception as e:
                print(f"Error reading {file_path}: {e}")

    async def _analyze_content(self, content: str, source: str):
        """
        Analyze content for error patterns.

        Args:
            content: File content to analyze
            source: Source file path
        """
        for pattern in self.patterns:
            matches = pattern.pattern.finditer(content)
            for match in matches:
                # Extract context around the error
                start = max(0, match.start() - 100)
                end = min(len(content), match.end() + 100)
                context = content[start:end]

                # Try to extract file and line number
                file_path, line_num = self._extract_location(content, match.start())

                error = {
                    "id": str(uuid4())[:8],
                    "timestamp": datetime.now().isoformat(),
                    "message": match.group(0),
                    "traceback": context,
                    "file_path": file_path,
                    "line_number": line_num,
                    "category": {
                        "type": pattern.category,
                        "severity": pattern.severity,
                        "confidence": pattern.confidence,
                    },
                    "context": {"source": source, "detected_at": datetime.now().isoformat()},
                    "suggestions": pattern.suggestions,
                    "resolved": False,
                }

                # Avoid duplicates
                if not self._is_duplicate(error):
                    self.errors.append(error)

    def _extract_location(self, content: str, position: int) -> tuple[Optional[str], Optional[int]]:
        """
        Extract file path and line number from error context.

        Args:
            content: Full content
            position: Error position in content

        Returns:
            Tuple of (file_path, line_number)
        """
        # Look backwards for file path pattern
        before = content[max(0, position - 200) : position]

        # Try to find "File "path", line X" pattern
        file_match = re.search(r'File "([^"]+)", line (\d+)', before)
        if file_match:
            return file_match.group(1), int(file_match.group(2))

        return None, None

    def _is_duplicate(self, error: Dict[str, Any]) -> bool:
        """
        Check if error is a duplicate of existing error.

        Args:
            error: Error to check

        Returns:
            True if duplicate exists
        """
        for existing in self.errors:
            if (
                existing["message"] == error["message"]
                and existing["file_path"] == error["file_path"]
                and existing["line_number"] == error["line_number"]
            ):
                return True
        return False

    def get_errors(
        self,
        category: Optional[str] = None,
        severity: Optional[str] = None,
        unresolved_only: bool = False,
    ) -> List[Dict[str, Any]]:
        """
        Get errors matching criteria.

        Args:
            category: Filter by category
            severity: Filter by severity
            unresolved_only: Only return unresolved errors

        Returns:
            List of matching errors
        """
        filtered = self.errors

        if unresolved_only:
            filtered = [e for e in filtered if not e["resolved"]]

        if category:
            filtered = [e for e in filtered if e["category"]["type"] == category]

        if severity:
            filtered = [e for e in filtered if e["category"]["severity"] == severity]

        return filtered

    def get_error_summary(self) -> Dict[str, Any]:
        """
        Get summary of all errors.

        Returns:
            Error summary statistics
        """
        by_category = {}
        by_severity = {}

        for error in self.errors:
            # Count by category
            cat = error["category"]["type"]
            by_category[cat] = by_category.get(cat, 0) + 1

            # Count by severity
            sev = error["category"]["severity"]
            by_severity[sev] = by_severity.get(sev, 0) + 1

        return {
            "total_errors": len(self.errors),
            "by_category": by_category,
            "by_severity": by_severity,
            "recent_errors": self.errors[-10:],  # Last 10 errors
        }

    def mark_resolved(self, error_id: str) -> bool:
        """
        Mark error as resolved.

        Args:
            error_id: ID of error to mark resolved

        Returns:
            True if error was found and marked
        """
        for error in self.errors:
            if error["id"] == error_id:
                error["resolved"] = True
                return True
        return False

    def clear_errors(self):
        """Clear all errors."""
        self.errors = []


# Global error watcher instance
_error_watcher: Optional[ErrorWatcher] = None


def get_error_watcher(project_root: str = None) -> ErrorWatcher:
    """
    Get global error watcher instance.

    Args:
        project_root: Project root directory

    Returns:
        ErrorWatcher instance
    """
    global _error_watcher
    if _error_watcher is None:
        _error_watcher = ErrorWatcher(project_root)
    return _error_watcher
