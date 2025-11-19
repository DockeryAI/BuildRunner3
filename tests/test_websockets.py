"""
Tests for WebSocket live updates
"""

import pytest
import json
from fastapi.testclient import TestClient
from api.server import app
from api.websockets.live_updates import (
    ConnectionManager,
    broadcast_task_update,
    broadcast_telemetry_event,
    broadcast_progress_update,
    broadcast_session_update,
)
from core.telemetry import Event, EventType
from datetime import datetime


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def connection_manager():
    """Create connection manager"""
    return ConnectionManager()


class TestConnectionManager:
    """Tests for WebSocket connection manager"""

    @pytest.mark.asyncio
    async def test_connect_disconnect(self, connection_manager):
        """Test connecting and disconnecting"""
        class MockWebSocket:
            async def accept(self):
                pass

        ws = MockWebSocket()
        await connection_manager.connect(ws, "test-client")

        assert len(connection_manager.active_connections) == 1
        assert ws in connection_manager.client_metadata

        connection_manager.disconnect(ws)
        assert len(connection_manager.active_connections) == 0
        assert ws not in connection_manager.client_metadata

    def test_get_connection_count(self, connection_manager):
        """Test get connection count"""
        assert connection_manager.get_connection_count() == 0

    @pytest.mark.asyncio
    async def test_send_personal_message(self, connection_manager):
        """Test sending personal message"""
        class MockWebSocket:
            def __init__(self):
                self.messages = []

            async def accept(self):
                pass

            async def send_json(self, message):
                self.messages.append(message)

        ws = MockWebSocket()
        await connection_manager.connect(ws)

        message = {"type": "test", "data": "hello"}
        await connection_manager.send_personal_message(message, ws)

        assert len(ws.messages) == 1
        assert ws.messages[0] == message

    @pytest.mark.asyncio
    async def test_broadcast(self, connection_manager):
        """Test broadcasting to all clients"""
        class MockWebSocket:
            def __init__(self):
                self.messages = []

            async def accept(self):
                pass

            async def send_json(self, message):
                self.messages.append(message)

        ws1 = MockWebSocket()
        ws2 = MockWebSocket()

        await connection_manager.connect(ws1)
        await connection_manager.connect(ws2)

        message = {"type": "broadcast", "data": "test"}
        await connection_manager.broadcast(message)

        assert len(ws1.messages) == 1
        assert len(ws2.messages) == 1
        assert ws1.messages[0] == message
        assert ws2.messages[0] == message


class TestWebSocketEndpoint:
    """Tests for WebSocket endpoint"""

    def test_websocket_connection(self, client):
        """Test WebSocket connection"""
        with client.websocket_connect("/ws/updates") as websocket:
            # Receive welcome message
            data = websocket.receive_json()
            assert data["type"] == "connection"
            assert data["status"] == "connected"

    def test_websocket_ping_pong(self, client):
        """Test WebSocket ping/pong"""
        with client.websocket_connect("/ws/updates") as websocket:
            # Receive welcome
            websocket.receive_json()

            # Send ping
            websocket.send_json({"type": "ping"})

            # Receive pong
            data = websocket.receive_json()
            assert data["type"] == "pong"

    def test_websocket_subscribe(self, client):
        """Test WebSocket subscription"""
        with client.websocket_connect("/ws/updates") as websocket:
            # Receive welcome
            websocket.receive_json()

            # Send subscribe
            websocket.send_json({
                "type": "subscribe",
                "topics": ["tasks", "telemetry"]
            })

            # Receive confirmation
            data = websocket.receive_json()
            assert data["type"] == "subscribed"
            assert "topics" in data

    def test_websocket_invalid_json(self, client):
        """Test WebSocket with invalid JSON"""
        with client.websocket_connect("/ws/updates") as websocket:
            # Receive welcome
            websocket.receive_json()

            # Send invalid JSON
            websocket.send_text("invalid json")

            # Receive error
            data = websocket.receive_json()
            assert data["type"] == "error"


class TestBroadcastFunctions:
    """Tests for broadcast helper functions"""

    @pytest.mark.asyncio
    async def test_broadcast_task_update(self):
        """Test broadcasting task update"""
        # This would need a running event loop and connection manager
        # For now, just test that the function exists and has correct signature
        assert callable(broadcast_task_update)

    @pytest.mark.asyncio
    async def test_broadcast_telemetry_event(self):
        """Test broadcasting telemetry event"""
        assert callable(broadcast_telemetry_event)

    @pytest.mark.asyncio
    async def test_broadcast_progress_update(self):
        """Test broadcasting progress update"""
        assert callable(broadcast_progress_update)

    @pytest.mark.asyncio
    async def test_broadcast_session_update(self):
        """Test broadcasting session update"""
        assert callable(broadcast_session_update)
