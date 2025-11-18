"""
Background test runner for BuildRunner 3.0

Runs pytest periodically and streams results via WebSocket.
Because watching tests fail in real-time is somehow more satisfying.
"""

import asyncio
import json
import subprocess
import time
from datetime import datetime
from pathlib import Path
from typing import Optional, Dict, Any, List
from uuid import uuid4


class TestRunner:
    """
    Background test runner with WebSocket streaming.

    Runs tests periodically and broadcasts results to connected clients.
    It's like CI/CD but with more anxiety.
    """

    def __init__(self, project_root: str = None):
        """
        Initialize test runner.

        Args:
            project_root: Project root directory
        """
        self.project_root = Path(project_root or ".")
        self.is_running = False
        self.task: Optional[asyncio.Task] = None
        self.latest_results: Optional[Dict[str, Any]] = None
        self.websocket_clients: List[Any] = []
        self.interval = 60  # Run every 60 seconds by default

    async def start(self, interval: int = 60):
        """
        Start background test runner.

        Args:
            interval: Seconds between test runs
        """
        if self.is_running:
            return {"status": "already_running"}

        self.interval = interval
        self.is_running = True
        self.task = asyncio.create_task(self._run_loop())

        return {
            "status": "started",
            "interval": interval,
            "message": "Background test runner started"
        }

    async def stop(self):
        """Stop background test runner."""
        if not self.is_running:
            return {"status": "not_running"}

        self.is_running = False
        if self.task:
            self.task.cancel()
            try:
                await self.task
            except asyncio.CancelledError:
                pass

        return {
            "status": "stopped",
            "message": "Background test runner stopped"
        }

    async def _run_loop(self):
        """Main test runner loop."""
        while self.is_running:
            try:
                # Run tests
                await self.broadcast_message("start", {"timestamp": datetime.now().isoformat()})

                results = await self._run_tests()
                self.latest_results = results

                await self.broadcast_message("complete", results)

                # Wait for next run
                await asyncio.sleep(self.interval)

            except asyncio.CancelledError:
                break
            except Exception as e:
                await self.broadcast_message("error", {
                    "message": str(e),
                    "timestamp": datetime.now().isoformat()
                })
                # Continue despite errors
                await asyncio.sleep(self.interval)

    async def _run_tests(self) -> Dict[str, Any]:
        """
        Run pytest and collect results.

        Returns:
            Test results dictionary
        """
        result_id = str(uuid4())[:8]
        start_time = time.time()

        try:
            # Run pytest with JSON report
            cmd = [
                "pytest",
                str(self.project_root / "tests"),
                "-v",
                "--tb=short",
                "--cov=core",
                "--cov=api",
                "--cov-report=json",
                "--json-report",
                "--json-report-file=/tmp/pytest_report.json"
            ]

            # Broadcast progress
            await self.broadcast_message("progress", {
                "message": "Running tests...",
                "command": " ".join(cmd)
            })

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_root)
            )

            stdout, stderr = await process.communicate()
            duration = time.time() - start_time

            # Parse pytest output
            output = stdout.decode()
            error_output = stderr.decode()

            # Try to load JSON report if available
            test_results = self._parse_pytest_output(output)

            # Try to load coverage data
            coverage = self._get_coverage()

            result = {
                "id": result_id,
                "timestamp": datetime.now().isoformat(),
                "total": test_results["total"],
                "passed": test_results["passed"],
                "failed": test_results["failed"],
                "skipped": test_results["skipped"],
                "errors": test_results["errors"],
                "duration": duration,
                "coverage": coverage,
                "status": "completed" if process.returncode == 0 else "failed",
                "test_cases": test_results.get("test_cases", [])
            }

            return result

        except Exception as e:
            duration = time.time() - start_time
            return {
                "id": result_id,
                "timestamp": datetime.now().isoformat(),
                "total": 0,
                "passed": 0,
                "failed": 0,
                "skipped": 0,
                "errors": 1,
                "duration": duration,
                "coverage": None,
                "status": "failed",
                "error": str(e),
                "test_cases": []
            }

    def _parse_pytest_output(self, output: str) -> Dict[str, Any]:
        """
        Parse pytest output to extract test results.

        Args:
            output: pytest stdout

        Returns:
            Parsed test results
        """
        results = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "errors": 0,
            "test_cases": []
        }

        # Look for pytest summary line
        for line in output.split("\n"):
            if "passed" in line or "failed" in line:
                # Try to extract counts
                parts = line.split()
                for i, part in enumerate(parts):
                    if "passed" in part and i > 0:
                        try:
                            results["passed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif "failed" in part and i > 0:
                        try:
                            results["failed"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif "error" in part and i > 0:
                        try:
                            results["errors"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass
                    elif "skipped" in part and i > 0:
                        try:
                            results["skipped"] = int(parts[i-1])
                        except (ValueError, IndexError):
                            pass

        results["total"] = results["passed"] + results["failed"] + results["skipped"] + results["errors"]
        return results

    def _get_coverage(self) -> Optional[float]:
        """
        Get coverage percentage from coverage report.

        Returns:
            Coverage percentage or None
        """
        try:
            coverage_file = self.project_root / "coverage.json"
            if coverage_file.exists():
                with open(coverage_file) as f:
                    data = json.load(f)
                    return data.get("totals", {}).get("percent_covered")
        except Exception:
            pass
        return None

    async def run_once(self) -> Dict[str, Any]:
        """
        Run tests once immediately.

        Returns:
            Test results
        """
        await self.broadcast_message("start", {"timestamp": datetime.now().isoformat()})
        results = await self._run_tests()
        self.latest_results = results
        await self.broadcast_message("complete", results)
        return results

    def get_latest_results(self) -> Optional[Dict[str, Any]]:
        """Get latest test results."""
        return self.latest_results

    def get_status(self) -> Dict[str, Any]:
        """Get test runner status."""
        return {
            "is_running": self.is_running,
            "interval": self.interval,
            "connected_clients": len(self.websocket_clients),
            "latest_results": self.latest_results
        }

    def add_websocket_client(self, websocket):
        """Add WebSocket client for streaming."""
        self.websocket_clients.append(websocket)

    def remove_websocket_client(self, websocket):
        """Remove WebSocket client."""
        if websocket in self.websocket_clients:
            self.websocket_clients.remove(websocket)

    async def broadcast_message(self, msg_type: str, data: Dict[str, Any]):
        """
        Broadcast message to all connected WebSocket clients.

        Args:
            msg_type: Message type
            data: Message data
        """
        message = {
            "type": msg_type,
            "timestamp": datetime.now().isoformat(),
            "data": data
        }

        # Remove disconnected clients
        disconnected = []
        for client in self.websocket_clients:
            try:
                await client.send_json(message)
            except Exception:
                disconnected.append(client)

        for client in disconnected:
            self.remove_websocket_client(client)


# Global test runner instance
_test_runner: Optional[TestRunner] = None


def get_test_runner(project_root: str = None) -> TestRunner:
    """
    Get global test runner instance.

    Args:
        project_root: Project root directory

    Returns:
        TestRunner instance
    """
    global _test_runner
    if _test_runner is None:
        _test_runner = TestRunner(project_root)
    return _test_runner
