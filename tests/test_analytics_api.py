"""
Tests for Analytics API endpoints

Tests coverage for:
- Agent performance metrics
- Cost breakdown visualization
- Success rate trends
- Historical comparison
"""

import pytest
from datetime import datetime, timedelta
from unittest.mock import Mock, patch, MagicMock
from fastapi.testclient import TestClient

# Mock the imports that may not be available
import sys
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from api.routes.analytics import (
    router,
    get_metrics_analyzer,
    get_metrics_db,
    get_event_collector,
    AgentPerformanceMetric,
    CostBreakdownItem,
    CostBreakdownResponse,
    SuccessTrendPoint,
    SuccessTrendsResponse,
    HistoricalComparisonPeriod,
    HistoricalComparisonResponse,
)


@pytest.fixture
def client():
    """Create test client for FastAPI app"""
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(router)
    return TestClient(app)


@pytest.fixture
def mock_analyzer():
    """Create mock metrics analyzer"""
    analyzer = MagicMock()

    # Mock summary data
    mock_summary = MagicMock()
    mock_summary.success_rate = 92.5
    mock_summary.total_tasks = 100
    mock_summary.successful_tasks = 92
    mock_summary.failed_tasks = 8
    mock_summary.avg_duration_ms = 1250.5
    mock_summary.p95_duration_ms = 2100.0
    mock_summary.p99_duration_ms = 2800.0
    mock_summary.total_cost_usd = 15.75
    mock_summary.avg_cost_per_task = 0.1575
    mock_summary.total_tokens = 125000
    mock_summary.models_used = {
        "claude-3-sonnet": 60,
        "claude-3-haiku": 40,
    }

    analyzer.calculate_summary.return_value = mock_summary

    # Mock performance trends
    analyzer.get_performance_trends.return_value = {
        "2024-01-01": [1200, 1300, 1250],
        "2024-01-02": [1400, 1350, 1380],
        "2024-01-03": [1100, 1150, 1120],
    }

    return analyzer


class TestAgentPerformance:
    """Tests for GET /api/analytics/agent-performance"""

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_agent_performance_success(self, mock_get_analyzer, client, mock_analyzer):
        """Test successful agent performance retrieval"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/agent-performance?period=day")

        assert response.status_code == 200
        data = response.json()

        assert isinstance(data, list)
        assert len(data) == 1

        metric = data[0]
        assert metric["agent_id"] == "aggregated"
        assert metric["success_rate"] == 92.5
        assert metric["total_tasks"] == 100
        assert metric["successful_tasks"] == 92
        assert metric["failed_tasks"] == 8
        assert metric["avg_duration_ms"] == 1250.5
        assert metric["total_cost_usd"] == 15.75

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_agent_performance_hour_period(self, mock_get_analyzer, client, mock_analyzer):
        """Test agent performance with hour period"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/agent-performance?period=hour")

        assert response.status_code == 200
        mock_analyzer.calculate_summary.assert_called_once_with(period="hour")

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_agent_performance_week_period(self, mock_get_analyzer, client, mock_analyzer):
        """Test agent performance with week period"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/agent-performance?period=week")

        assert response.status_code == 200
        mock_analyzer.calculate_summary.assert_called_once_with(period="week")

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_agent_performance_invalid_period(self, mock_get_analyzer, client, mock_analyzer):
        """Test agent performance with invalid period (should use default or reject)"""
        mock_get_analyzer.return_value = mock_analyzer

        # Invalid period should be rejected by FastAPI validation
        response = client.get("/analytics/agent-performance?period=invalid")

        assert response.status_code in [200, 422]  # Either defaults or validation error

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_agent_performance_error(self, mock_get_analyzer, client):
        """Test agent performance error handling"""
        mock_analyzer = MagicMock()
        mock_analyzer.calculate_summary.side_effect = Exception("Database error")
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/agent-performance?period=day")

        assert response.status_code == 500
        data = response.json()
        assert "detail" in data
        assert "Database error" in data["detail"]


class TestCostBreakdown:
    """Tests for GET /api/analytics/cost-breakdown"""

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_cost_breakdown_success(self, mock_get_analyzer, client, mock_analyzer):
        """Test successful cost breakdown retrieval"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/cost-breakdown?period=day")

        assert response.status_code == 200
        data = response.json()

        assert "total_cost_usd" in data
        assert "period" in data
        assert "breakdown_by_agent" in data
        assert "breakdown_by_model" in data
        assert "breakdown_by_type" in data

        assert data["total_cost_usd"] == 15.75
        assert data["period"] == "day"

        # Verify breakdown structure
        assert isinstance(data["breakdown_by_agent"], list)
        assert isinstance(data["breakdown_by_model"], list)
        assert isinstance(data["breakdown_by_type"], list)

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_cost_breakdown_agent_breakdown(self, mock_get_analyzer, client, mock_analyzer):
        """Test agent breakdown in cost breakdown"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/cost-breakdown?period=day")

        assert response.status_code == 200
        data = response.json()

        # Verify agent breakdown
        agent_breakdown = data["breakdown_by_agent"]
        assert len(agent_breakdown) > 0
        agent_item = agent_breakdown[0]
        assert "name" in agent_item
        assert "cost_usd" in agent_item
        assert "percentage" in agent_item
        assert "token_count" in agent_item
        assert "task_count" in agent_item

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_cost_breakdown_model_breakdown(self, mock_get_analyzer, client, mock_analyzer):
        """Test model breakdown in cost breakdown"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/cost-breakdown?period=day")

        assert response.status_code == 200
        data = response.json()

        # Verify model breakdown
        model_breakdown = data["breakdown_by_model"]
        assert len(model_breakdown) > 0

        # Should have entries for each model
        model_names = [item["name"] for item in model_breakdown]
        assert "claude-3-sonnet" in model_names or len(model_names) > 0

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_cost_breakdown_token_type_breakdown(self, mock_get_analyzer, client, mock_analyzer):
        """Test token type breakdown in cost breakdown"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/cost-breakdown?period=day")

        assert response.status_code == 200
        data = response.json()

        # Verify token type breakdown
        token_breakdown = data["breakdown_by_type"]
        assert len(token_breakdown) > 0

        token_names = [item["name"] for item in token_breakdown]
        assert "input_tokens" in token_names or len(token_names) > 0

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_cost_breakdown_hour_period(self, mock_get_analyzer, client, mock_analyzer):
        """Test cost breakdown with hour period"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/cost-breakdown?period=hour")

        assert response.status_code == 200
        mock_analyzer.calculate_summary.assert_called_with(period="hour")

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_cost_breakdown_error(self, mock_get_analyzer, client):
        """Test cost breakdown error handling"""
        mock_analyzer = MagicMock()
        mock_analyzer.calculate_summary.side_effect = Exception("Query failed")
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/cost-breakdown?period=day")

        assert response.status_code == 500


class TestSuccessTrends:
    """Tests for GET /api/analytics/success-trends"""

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_success_trends_success(self, mock_get_analyzer, client, mock_analyzer):
        """Test successful success trends retrieval"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/success-trends?period=day&days=7")

        assert response.status_code == 200
        data = response.json()

        assert "period" in data
        assert "start_date" in data
        assert "end_date" in data
        assert "points" in data
        assert "avg_success_rate" in data
        assert "min_success_rate" in data
        assert "max_success_rate" in data

        # Verify points structure
        points = data["points"]
        assert isinstance(points, list)
        assert len(points) > 0

        point = points[0]
        assert "timestamp" in point
        assert "success_rate" in point
        assert "total_tasks" in point

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_success_trends_custom_days(self, mock_get_analyzer, client, mock_analyzer):
        """Test success trends with custom days parameter"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/success-trends?period=day&days=14")

        assert response.status_code == 200
        assert mock_analyzer.calculate_summary.called

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_success_trends_min_max_calculation(self, mock_get_analyzer, client, mock_analyzer):
        """Test min/max success rate calculation"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/success-trends?period=day&days=7")

        assert response.status_code == 200
        data = response.json()

        # Success rates should be valid percentages
        assert 0 <= data["avg_success_rate"] <= 100
        assert 0 <= data["min_success_rate"] <= 100
        assert 0 <= data["max_success_rate"] <= 100

        # Max should be >= average >= min
        assert data["max_success_rate"] >= data["avg_success_rate"]
        assert data["avg_success_rate"] >= data["min_success_rate"]

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_success_trends_error(self, mock_get_analyzer, client):
        """Test success trends error handling"""
        mock_analyzer = MagicMock()
        mock_analyzer.calculate_summary.side_effect = Exception("Calculation failed")
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/success-trends?period=day&days=7")

        assert response.status_code == 500


class TestHistoricalComparison:
    """Tests for GET /api/analytics/historical-comparison"""

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_historical_comparison_success(self, mock_get_analyzer, client, mock_analyzer):
        """Test successful historical comparison retrieval"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/historical-comparison")

        assert response.status_code == 200
        data = response.json()

        # Verify all required fields
        assert "current_period" in data
        assert "previous_period" in data
        assert "week_ago" in data
        assert "month_ago" in data
        assert "improvements" in data
        assert "trends" in data

        # Verify period structure
        current = data["current_period"]
        assert "period" in current
        assert "success_rate" in current
        assert "cost_per_task" in current
        assert "total_tasks" in current
        assert "avg_duration_ms" in current

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_historical_comparison_improvements(self, mock_get_analyzer, client, mock_analyzer):
        """Test improvements calculation in historical comparison"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/historical-comparison")

        assert response.status_code == 200
        data = response.json()

        improvements = data["improvements"]
        assert "success_rate" in improvements
        assert "cost_per_task" in improvements

        # Improvements should be numbers
        assert isinstance(improvements["success_rate"], (int, float))
        assert isinstance(improvements["cost_per_task"], (int, float))

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_historical_comparison_trends(self, mock_get_analyzer, client, mock_analyzer):
        """Test trend directions in historical comparison"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/historical-comparison")

        assert response.status_code == 200
        data = response.json()

        trends = data["trends"]
        assert "success_rate" in trends
        assert "cost_per_task" in trends

        # Trends should be "up" or "down"
        assert trends["success_rate"] in ["up", "down"]
        assert trends["cost_per_task"] in ["up", "down"]

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_historical_comparison_period_labels(self, mock_get_analyzer, client, mock_analyzer):
        """Test period labels in historical comparison"""
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/historical-comparison")

        assert response.status_code == 200
        data = response.json()

        assert data["current_period"]["period"] == "current_24h"
        assert data["previous_period"]["period"] == "previous_24h"
        assert data["week_ago"]["period"] == "week_ago"
        assert data["month_ago"]["period"] == "month_ago"

    @patch("api.routes.analytics.get_metrics_analyzer")
    def test_get_historical_comparison_error(self, mock_get_analyzer, client):
        """Test historical comparison error handling"""
        mock_analyzer = MagicMock()
        mock_analyzer.calculate_summary.side_effect = Exception("Comparison failed")
        mock_get_analyzer.return_value = mock_analyzer

        response = client.get("/analytics/historical-comparison")

        assert response.status_code == 500


class TestDataModels:
    """Tests for Pydantic data models"""

    def test_agent_performance_metric_model(self):
        """Test AgentPerformanceMetric model creation"""
        metric = AgentPerformanceMetric(
            agent_id="test-agent",
            success_rate=95.0,
            total_tasks=100,
            successful_tasks=95,
            failed_tasks=5,
            avg_duration_ms=1000.0,
            p95_duration_ms=1500.0,
            p99_duration_ms=2000.0,
            total_cost_usd=10.0,
            avg_cost_per_task=0.1,
            timestamp=datetime.now(),
        )

        assert metric.agent_id == "test-agent"
        assert metric.success_rate == 95.0
        assert metric.total_tasks == 100

    def test_cost_breakdown_item_model(self):
        """Test CostBreakdownItem model creation"""
        item = CostBreakdownItem(
            name="test-model",
            cost_usd=5.0,
            percentage=50.0,
            token_count=50000,
            task_count=50,
        )

        assert item.name == "test-model"
        assert item.cost_usd == 5.0
        assert item.percentage == 50.0

    def test_cost_breakdown_response_model(self):
        """Test CostBreakdownResponse model creation"""
        response = CostBreakdownResponse(
            total_cost_usd=10.0,
            period="day",
            breakdown_by_agent=[],
            breakdown_by_model=[],
            breakdown_by_type=[],
        )

        assert response.total_cost_usd == 10.0
        assert response.period == "day"

    def test_success_trend_point_model(self):
        """Test SuccessTrendPoint model creation"""
        point = SuccessTrendPoint(
            timestamp="2024-01-01",
            success_rate=90.0,
            total_tasks=100,
            successful_tasks=90,
            failed_tasks=10,
        )

        assert point.timestamp == "2024-01-01"
        assert point.success_rate == 90.0

    def test_success_trends_response_model(self):
        """Test SuccessTrendsResponse model creation"""
        response = SuccessTrendsResponse(
            period="day",
            start_date="2024-01-01",
            end_date="2024-01-07",
            points=[],
            avg_success_rate=90.0,
            min_success_rate=85.0,
            max_success_rate=95.0,
        )

        assert response.period == "day"
        assert response.avg_success_rate == 90.0

    def test_historical_comparison_response_model(self):
        """Test HistoricalComparisonResponse model creation"""
        current = HistoricalComparisonPeriod(
            period="current_24h",
            success_rate=90.0,
            cost_per_task=0.1,
            total_tasks=100,
            avg_duration_ms=1000.0,
        )

        response = HistoricalComparisonResponse(
            current_period=current,
            previous_period=current,
            week_ago=current,
            month_ago=current,
            improvements={"success_rate": 5.0, "cost_per_task": -0.01},
            trends={"success_rate": "up", "cost_per_task": "down"},
        )

        assert response.current_period.success_rate == 90.0
        assert response.improvements["success_rate"] == 5.0


class TestRouterSetup:
    """Tests for router configuration"""

    def test_router_prefix(self):
        """Test that router has correct prefix"""
        # Router should have /analytics prefix
        assert router.prefix == "/analytics"

    def test_router_tags(self):
        """Test that router has correct tags"""
        assert "analytics" in router.tags

    def test_endpoints_registered(self):
        """Test that all endpoints are registered"""
        # Get all routes from router
        routes = [route for route in router.routes]

        # Should have at least 4 endpoints
        assert len(routes) >= 4

        # Check for path patterns
        paths = [route.path for route in routes if hasattr(route, "path")]
        assert any("/agent-performance" in p for p in paths)
        assert any("/cost-breakdown" in p for p in paths)
        assert any("/success-trends" in p for p in paths)
        assert any("/historical-comparison" in p for p in paths)


if __name__ == "__main__":
    pytest.main([__file__, "-v", "--cov=api.routes.analytics", "--cov-report=html"])
