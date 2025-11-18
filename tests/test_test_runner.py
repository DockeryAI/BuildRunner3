"""
Tests for BuildRunner 3.0 background test runner

Testing the test runner that runs tests. Recursion intensifies.
"""

import pytest
import asyncio
from pathlib import Path

from api.test_runner import TestRunner


@pytest.fixture
def test_runner():
    """Create test runner instance"""
    return TestRunner(str(Path(__file__).parent.parent))


@pytest.fixture(autouse=True)
def cleanup_sync(test_runner):
    """Clean up after each test"""
    yield

    # Clear results
    test_runner.latest_results = None
    test_runner.websocket_clients = []
    test_runner.is_running = False


@pytest.mark.asyncio
async def test_test_runner_initial_state(test_runner):
    """Test initial state of test runner"""
    assert test_runner.is_running is False
    assert test_runner.latest_results is None
    assert test_runner.interval == 60
    assert len(test_runner.websocket_clients) == 0


@pytest.mark.asyncio
async def test_start_test_runner(test_runner):
    """Test starting the background test runner"""
    result = await test_runner.start(interval=120)

    assert result["status"] == "started"
    assert result["interval"] == 120
    assert test_runner.is_running is True
    assert test_runner.interval == 120

    # Clean up
    await test_runner.stop()


@pytest.mark.asyncio
async def test_start_already_running(test_runner):
    """Test starting when already running"""
    await test_runner.start()

    # Try to start again
    result = await test_runner.start()
    assert result["status"] == "already_running"

    # Clean up
    await test_runner.stop()


@pytest.mark.asyncio
async def test_stop_test_runner(test_runner):
    """Test stopping the test runner"""
    await test_runner.start()
    result = await test_runner.stop()

    assert result["status"] == "stopped"
    assert test_runner.is_running is False


@pytest.mark.asyncio
async def test_stop_not_running(test_runner):
    """Test stopping when not running"""
    result = await test_runner.stop()
    assert result["status"] == "not_running"


@pytest.mark.asyncio
async def test_run_tests_once(test_runner):
    """Test running tests once immediately"""
    results = await test_runner.run_once()

    assert "id" in results
    assert "timestamp" in results
    assert "total" in results
    assert "passed" in results
    assert "failed" in results
    assert "skipped" in results
    assert "errors" in results
    assert "duration" in results
    assert "status" in results

    # Results should be stored
    assert test_runner.latest_results == results


@pytest.mark.asyncio
async def test_get_latest_results(test_runner):
    """Test getting latest test results"""
    # Initially None
    assert test_runner.get_latest_results() is None

    # Run tests
    await test_runner.run_once()

    # Now should have results
    results = test_runner.get_latest_results()
    assert results is not None
    assert "total" in results


@pytest.mark.asyncio
async def test_get_status(test_runner):
    """Test getting test runner status"""
    status = test_runner.get_status()

    assert "is_running" in status
    assert "interval" in status
    assert "connected_clients" in status
    assert "latest_results" in status

    assert status["is_running"] is False
    assert status["interval"] == 60
    assert status["connected_clients"] == 0


@pytest.mark.asyncio
async def test_parse_pytest_output(test_runner):
    """Test parsing pytest output"""
    output = """
    ============================= test session starts ==============================
    collected 10 items

    tests/test_api.py::test_health_check PASSED
    tests/test_api.py::test_get_features PASSED

    ========================= 8 passed, 2 failed in 5.23s ==========================
    """

    results = test_runner._parse_pytest_output(output)

    assert results["passed"] == 8
    assert results["failed"] == 2
    assert results["total"] == 10


@pytest.mark.asyncio
async def test_parse_pytest_output_all_passed(test_runner):
    """Test parsing output when all tests pass"""
    output = """
    ============================= test session starts ==============================
    collected 5 items

    tests/test_api.py ......

    ============================= 5 passed in 2.34s ================================
    """

    results = test_runner._parse_pytest_output(output)

    assert results["passed"] == 5
    assert results["failed"] == 0
    assert results["total"] == 5


@pytest.mark.asyncio
async def test_websocket_client_management(test_runner):
    """Test adding and removing WebSocket clients"""
    class MockWebSocket:
        async def send_json(self, data):
            pass

    ws1 = MockWebSocket()
    ws2 = MockWebSocket()

    # Add clients
    test_runner.add_websocket_client(ws1)
    test_runner.add_websocket_client(ws2)

    assert len(test_runner.websocket_clients) == 2

    # Remove client
    test_runner.remove_websocket_client(ws1)
    assert len(test_runner.websocket_clients) == 1

    # Remove non-existent client (should not error)
    test_runner.remove_websocket_client(ws1)
    assert len(test_runner.websocket_clients) == 1


@pytest.mark.asyncio
async def test_broadcast_message(test_runner):
    """Test broadcasting messages to WebSocket clients"""
    class MockWebSocket:
        def __init__(self):
            self.messages = []

        async def send_json(self, data):
            self.messages.append(data)

    ws = MockWebSocket()
    test_runner.add_websocket_client(ws)

    # Broadcast message
    await test_runner.broadcast_message("test", {"foo": "bar"})

    assert len(ws.messages) == 1
    assert ws.messages[0]["type"] == "test"
    assert ws.messages[0]["data"]["foo"] == "bar"


@pytest.mark.asyncio
async def test_broadcast_removes_disconnected_clients(test_runner):
    """Test that disconnected clients are removed during broadcast"""
    class MockWebSocket:
        def __init__(self, should_fail=False):
            self.should_fail = should_fail

        async def send_json(self, data):
            if self.should_fail:
                raise Exception("Connection lost")

    ws1 = MockWebSocket(should_fail=True)
    ws2 = MockWebSocket(should_fail=False)

    test_runner.add_websocket_client(ws1)
    test_runner.add_websocket_client(ws2)

    assert len(test_runner.websocket_clients) == 2

    # Broadcast - ws1 should be removed
    await test_runner.broadcast_message("test", {})

    assert len(test_runner.websocket_clients) == 1
    assert test_runner.websocket_clients[0] == ws2


@pytest.mark.asyncio
async def test_run_tests_error_handling(test_runner):
    """Test that test runner handles errors gracefully"""
    # This will likely fail to run tests, but shouldn't crash
    results = await test_runner._run_tests()

    assert "status" in results
    # May be "failed" or "completed" depending on environment
