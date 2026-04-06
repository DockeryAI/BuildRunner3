"""
Tests for FastAPI server and routes
"""

import pytest
from fastapi.testclient import TestClient
from api.server import app
from core.orchestrator import TaskOrchestrator, OrchestrationStatus
from core.task_queue import TaskQueue, QueuedTask, TaskStatus
from core.telemetry import EventCollector, Event, EventType
from core.parallel import SessionManager
from datetime import datetime


@pytest.fixture
def client():
    """Create test client"""
    return TestClient(app)


@pytest.fixture
def mock_task():
    """Create mock task"""
    return QueuedTask(
        id="test-task-1",
        name="Test Task",
        description="A test task",
        file_path="/test/file.py",
        estimated_minutes=60,
        complexity="medium",
        domain="backend",
        status=TaskStatus.PENDING,
    )


class TestHealthEndpoint:
    """Tests for health check endpoint"""

    def test_health_check(self, client):
        """Test health check returns 200"""
        response = client.get("/health")
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "healthy"
        assert data["service"] == "BuildRunner API"
        assert data["version"] == "3.2.0"

    def test_root_endpoint(self, client):
        """Test root endpoint"""
        response = client.get("/")
        assert response.status_code == 200
        data = response.json()
        assert data["service"] == "BuildRunner API"
        assert "docs" in data
        assert "websocket" in data


class TestOrchestratorRoutes:
    """Tests for orchestrator API routes"""

    def test_get_status(self, client):
        """Test get orchestrator status"""
        response = client.get("/api/orchestrator/status")
        assert response.status_code == 200
        data = response.json()
        assert "status" in data
        assert "batches_executed" in data
        assert "tasks_completed" in data

    def test_get_progress(self, client):
        """Test get progress"""
        response = client.get("/api/orchestrator/progress")
        assert response.status_code == 200
        data = response.json()
        assert "total" in data
        assert "completed" in data
        assert "percent_complete" in data

    def test_get_tasks(self, client):
        """Test get all tasks"""
        response = client.get("/api/orchestrator/tasks")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_tasks_with_filter(self, client):
        """Test get tasks with status filter"""
        response = client.get("/api/orchestrator/tasks?status=completed")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_tasks_invalid_status(self, client):
        """Test get tasks with invalid status"""
        response = client.get("/api/orchestrator/tasks?status=invalid")
        assert response.status_code == 400

    def test_pause_orchestration(self, client):
        """Test pause orchestration"""
        response = client.post("/api/orchestrator/control/pause")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True
        assert data["status"] == "paused"

    def test_resume_orchestration(self, client):
        """Test resume orchestration"""
        response = client.post("/api/orchestrator/control/resume")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_stop_orchestration(self, client):
        """Test stop orchestration"""
        response = client.post("/api/orchestrator/control/stop")
        assert response.status_code == 200
        data = response.json()
        assert data["success"] is True

    def test_get_batches(self, client):
        """Test get batches"""
        response = client.get("/api/orchestrator/batches")
        assert response.status_code == 200
        data = response.json()
        assert "completed" in data
        assert "failed" in data

    def test_get_stats(self, client):
        """Test get comprehensive stats"""
        response = client.get("/api/orchestrator/stats")
        assert response.status_code == 200
        data = response.json()
        assert "orchestrator" in data
        assert "queue" in data
        assert "integration" in data


class TestTelemetryRoutes:
    """Tests for telemetry API routes"""

    def test_get_events(self, client):
        """Test get telemetry events"""
        response = client.get("/api/telemetry/events")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_events_with_filter(self, client):
        """Test get events with filters"""
        response = client.get("/api/telemetry/events?limit=10")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_recent_events(self, client):
        """Test get recent events"""
        response = client.get("/api/telemetry/events/recent?count=20")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_timeline(self, client):
        """Test get telemetry timeline"""
        response = client.get("/api/telemetry/timeline")
        assert response.status_code == 200
        data = response.json()
        assert "events" in data
        assert "total" in data

    def test_get_statistics(self, client):
        """Test get telemetry statistics"""
        response = client.get("/api/telemetry/statistics")
        assert response.status_code == 200
        data = response.json()
        assert "total_events" in data
        assert "events_by_type" in data

    def test_get_metrics(self, client):
        """Test get telemetry metrics"""
        response = client.get("/api/telemetry/metrics")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_performance(self, client):
        """Test get performance metrics"""
        response = client.get("/api/telemetry/performance")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_event_count(self, client):
        """Test get event count"""
        response = client.get("/api/telemetry/events/count")
        assert response.status_code == 200
        data = response.json()
        assert "count" in data


class TestAgentsRoutes:
    """Tests for agents API routes"""

    def test_get_agent_pool(self, client):
        """Test get agent pool status"""
        response = client.get("/api/agents/pool")
        assert response.status_code == 200
        data = response.json()
        assert "total_sessions" in data
        assert "active_sessions" in data
        assert "max_concurrent" in data

    def test_get_sessions(self, client):
        """Test get all sessions"""
        response = client.get("/api/agents/sessions")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_active_sessions(self, client):
        """Test get active sessions"""
        response = client.get("/api/agents/active")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_workers(self, client):
        """Test get workers"""
        response = client.get("/api/agents/workers")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, list)

    def test_get_dashboard(self, client):
        """Test get dashboard data"""
        response = client.get("/api/agents/dashboard")
        assert response.status_code == 200
        data = response.json()
        assert isinstance(data, dict)

    def test_get_agent_metrics(self, client):
        """Test get agent metrics"""
        response = client.get("/api/agents/metrics")
        assert response.status_code == 200
        data = response.json()
        assert "sessions" in data
        assert "workers" in data


class TestCORS:
    """Tests for CORS configuration"""

    def test_cors_headers(self, client):
        """Test CORS headers are present"""
        response = client.options(
            "/api/orchestrator/status",
            headers={"Origin": "http://localhost:5173"},
        )
        # CORS middleware should add headers
        assert response.status_code in [200, 204]


class TestErrorHandling:
    """Tests for error handling"""

    def test_404_endpoint(self, client):
        """Test 404 for non-existent endpoint"""
        response = client.get("/api/nonexistent")
        assert response.status_code == 404

    def test_invalid_task_id(self, client):
        """Test 404 for invalid task ID"""
        response = client.get("/api/orchestrator/tasks/nonexistent-id")
        assert response.status_code == 404

    def test_invalid_session_id(self, client):
        """Test 404 for invalid session ID"""
        response = client.get("/api/agents/sessions/nonexistent-id")
        assert response.status_code == 404
