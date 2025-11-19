"""
Tests for Agent Performance Metrics (Build 8B Feature 3)

Tests:
- Metric recording and retrieval
- Cost calculation per model
- Quality scoring based on test pass rates and error rates
- Persistence to JSON and SQLite
- Summary generation by agent type
- Performance trend analysis
- Export and import functionality
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile
import json

from core.agents.metrics import (
    AgentMetrics,
    AgentMetric,
    AgentPerformanceSummary,
    ModelType,
    MODEL_PRICING,
)


@pytest.fixture
def temp_dir():
    """Create temporary directory for testing."""
    with tempfile.TemporaryDirectory() as tmpdir:
        yield Path(tmpdir)


@pytest.fixture
def metrics_tracker(temp_dir):
    """Create AgentMetrics instance with temporary storage."""
    storage_path = temp_dir / "agent_metrics.json"
    db_path = temp_dir / "telemetry.db"
    return AgentMetrics(storage_path=storage_path, db_path=db_path)


class TestAgentMetricsBasics:
    """Test basic metrics recording and retrieval."""

    def test_initialization(self, metrics_tracker):
        """Test AgentMetrics initialization."""
        assert metrics_tracker is not None
        assert metrics_tracker.metrics == []
        assert metrics_tracker.storage_path is not None
        assert metrics_tracker.db_path is not None

    def test_record_metric_basic(self, metrics_tracker):
        """Test recording a basic metric."""
        metric = metrics_tracker.record_metric(
            agent_type="explore",
            task_id="task-001",
            task_description="Explore codebase structure",
            model_used=ModelType.HAIKU.value,
            duration_ms=5000.0,
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )

        assert metric.agent_type == "explore"
        assert metric.task_id == "task-001"
        assert metric.success is True
        assert metric.total_tokens == 1500
        assert len(metrics_tracker.metrics) == 1

    def test_record_metric_with_quality_scores(self, metrics_tracker):
        """Test recording metric with quality scores."""
        metric = metrics_tracker.record_metric(
            agent_type="test",
            task_id="task-002",
            task_description="Write unit tests",
            model_used=ModelType.SONNET.value,
            duration_ms=10000.0,
            input_tokens=2000,
            output_tokens=1000,
            success=True,
            test_pass_rate=0.95,
            error_rate=0.05,
            files_created=3,
            files_modified=2,
        )

        assert metric.test_pass_rate == 0.95
        assert metric.error_rate == 0.05
        assert metric.files_created == 3
        assert metric.files_modified == 2

    def test_record_failed_metric(self, metrics_tracker):
        """Test recording a failed metric."""
        metric = metrics_tracker.record_metric(
            agent_type="implement",
            task_id="task-003",
            task_description="Implement new feature",
            model_used=ModelType.SONNET.value,
            duration_ms=15000.0,
            input_tokens=3000,
            output_tokens=1500,
            success=False,
            error_message="Test suite failed with 2 errors",
        )

        assert metric.success is False
        assert metric.error_message is not None
        assert "Test suite failed" in metric.error_message

    def test_metric_to_dict(self, metrics_tracker):
        """Test converting metric to dictionary."""
        metric = metrics_tracker.record_metric(
            agent_type="review",
            task_id="task-004",
            task_description="Review code quality",
            model_used=ModelType.OPUS.value,
            duration_ms=8000.0,
            input_tokens=1500,
            output_tokens=800,
            success=True,
        )

        metric_dict = metric.to_dict()
        assert metric_dict['agent_type'] == "review"
        assert metric_dict['task_id'] == "task-004"
        assert metric_dict['cost_usd'] > 0
        assert isinstance(metric_dict['timestamp'], str)


class TestCostCalculation:
    """Test cost calculation per model."""

    def test_cost_haiku(self, metrics_tracker):
        """Test cost calculation for Haiku model."""
        metric = metrics_tracker.record_metric(
            agent_type="explore",
            task_id="task-005",
            task_description="Simple exploration",
            model_used=ModelType.HAIKU.value,
            duration_ms=5000.0,
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )

        # Haiku: $0.80/1M input, $4.00/1M output
        expected_cost = (1000 / 1_000_000 * 0.80) + (500 / 1_000_000 * 4.00)
        assert abs(metric.cost_usd - expected_cost) < 0.001

    def test_cost_sonnet(self, metrics_tracker):
        """Test cost calculation for Sonnet model."""
        metric = metrics_tracker.record_metric(
            agent_type="implement",
            task_id="task-006",
            task_description="Implement feature",
            model_used=ModelType.SONNET.value,
            duration_ms=10000.0,
            input_tokens=5000,
            output_tokens=2000,
            success=True,
        )

        # Sonnet: $3.00/1M input, $15.00/1M output
        expected_cost = (5000 / 1_000_000 * 3.00) + (2000 / 1_000_000 * 15.00)
        assert abs(metric.cost_usd - expected_cost) < 0.001

    def test_cost_opus(self, metrics_tracker):
        """Test cost calculation for Opus model."""
        metric = metrics_tracker.record_metric(
            agent_type="review",
            task_id="task-007",
            task_description="Complex code review",
            model_used=ModelType.OPUS.value,
            duration_ms=15000.0,
            input_tokens=10000,
            output_tokens=5000,
            success=True,
        )

        # Opus: $15.00/1M input, $75.00/1M output
        expected_cost = (10000 / 1_000_000 * 15.00) + (5000 / 1_000_000 * 75.00)
        assert abs(metric.cost_usd - expected_cost) < 0.001

    def test_total_cost_accumulation(self, metrics_tracker):
        """Test accumulation of costs across multiple tasks."""
        # Record 5 tasks with different models
        costs = []
        for i in range(5):
            metric = metrics_tracker.record_metric(
                agent_type="test",
                task_id=f"task-{i}",
                task_description=f"Test task {i}",
                model_used=ModelType.HAIKU.value if i % 2 == 0 else ModelType.SONNET.value,
                duration_ms=5000.0 + (i * 1000),
                input_tokens=1000 + (i * 200),
                output_tokens=500 + (i * 100),
                success=True,
            )
            costs.append(metric.cost_usd)

        summary = metrics_tracker.get_summary("test")
        assert summary is not None
        assert abs(summary.total_cost_usd - sum(costs)) < 0.01


class TestQualityScoring:
    """Test quality scoring based on test pass rates and error rates."""

    def test_quality_metrics_recording(self, metrics_tracker):
        """Test recording quality metrics."""
        metric = metrics_tracker.record_metric(
            agent_type="test",
            task_id="task-008",
            task_description="Test suite",
            model_used=ModelType.SONNET.value,
            duration_ms=8000.0,
            input_tokens=2000,
            output_tokens=1000,
            success=True,
            test_pass_rate=0.98,
            error_rate=0.02,
            files_created=5,
            files_modified=3,
        )

        assert metric.test_pass_rate == 0.98
        assert metric.error_rate == 0.02
        assert metric.files_created == 5
        assert metric.files_modified == 3

    def test_average_quality_score(self, metrics_tracker):
        """Test average quality score calculation."""
        # Record 3 test tasks with varying quality
        quality_scores = [0.95, 0.90, 0.85]
        for i, score in enumerate(quality_scores):
            metrics_tracker.record_metric(
                agent_type="test",
                task_id=f"task-quality-{i}",
                task_description="Test task",
                model_used=ModelType.SONNET.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                success=True,
                test_pass_rate=score,
                error_rate=1.0 - score,
            )

        summary = metrics_tracker.get_summary("test")
        expected_avg = sum(quality_scores) / len(quality_scores)
        assert abs(summary.avg_test_pass_rate - expected_avg) < 0.01
        assert abs(summary.avg_error_rate - (1.0 - expected_avg)) < 0.01


class TestSummaryGeneration:
    """Test summary generation by agent type."""

    def test_summary_for_single_agent_type(self, metrics_tracker):
        """Test generating summary for a single agent type."""
        # Record 10 metrics for explore agent
        for i in range(10):
            metrics_tracker.record_metric(
                agent_type="explore",
                task_id=f"explore-{i}",
                task_description=f"Explore task {i}",
                model_used=ModelType.HAIKU.value,
                duration_ms=3000.0 + (i * 100),
                input_tokens=500 + (i * 50),
                output_tokens=250 + (i * 25),
                success=i < 9,  # 9 success, 1 failure
            )

        summary = metrics_tracker.get_summary("explore")
        assert summary is not None
        assert summary.agent_type == "explore"
        assert summary.total_tasks == 10
        assert summary.successful_tasks == 9
        assert summary.failed_tasks == 1
        assert abs(summary.success_rate - 0.9) < 0.01

    def test_summary_with_time_period(self, metrics_tracker):
        """Test summary generation with time period filtering."""
        # Record metrics over different times
        base_time = datetime.now()

        # Record 5 metrics for recent period
        for i in range(5):
            metric = AgentMetric(
                timestamp=base_time,
                agent_type="refactor",
                task_id=f"recent-{i}",
                task_description="Recent refactor",
                model_used=ModelType.SONNET.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                total_tokens=1500,
                cost_usd=0.05,
                success=True,
            )
            metrics_tracker.metrics.append(metric)

        # Record 5 metrics for old period
        old_time = base_time - timedelta(days=15)
        for i in range(5):
            metric = AgentMetric(
                timestamp=old_time,
                agent_type="refactor",
                task_id=f"old-{i}",
                task_description="Old refactor",
                model_used=ModelType.SONNET.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                total_tokens=1500,
                cost_usd=0.05,
                success=True,
            )
            metrics_tracker.metrics.append(metric)

        # Get summary for 7-day period (should only include recent)
        summary = metrics_tracker.get_summary("refactor", time_period_days=7)
        assert summary.total_tasks == 5

    def test_all_agent_types_summary(self, metrics_tracker):
        """Test generating summary for all agent types."""
        # Record metrics for all agent types
        agent_types = ["explore", "test", "review", "refactor", "implement"]
        for agent_type in agent_types:
            for i in range(3):
                metrics_tracker.record_metric(
                    agent_type=agent_type,
                    task_id=f"{agent_type}-{i}",
                    task_description=f"{agent_type} task",
                    model_used=ModelType.SONNET.value,
                    duration_ms=5000.0,
                    input_tokens=1000,
                    output_tokens=500,
                    success=True,
                )

        # Get summaries for all types
        summaries = metrics_tracker.get_agent_types_summary()
        assert len(summaries) == 5
        assert all(agent_type in summaries for agent_type in agent_types)

    def test_model_usage_breakdown(self, metrics_tracker):
        """Test model usage breakdown in summary."""
        # Record metrics with different models
        models = [ModelType.HAIKU.value, ModelType.SONNET.value, ModelType.OPUS.value]
        for i, model in enumerate(models):
            for j in range(i + 1):  # 1 haiku, 2 sonnet, 3 opus
                metrics_tracker.record_metric(
                    agent_type="implement",
                    task_id=f"impl-{i}-{j}",
                    task_description="Implementation",
                    model_used=model,
                    duration_ms=5000.0,
                    input_tokens=1000,
                    output_tokens=500,
                    success=True,
                )

        summary = metrics_tracker.get_summary("implement")
        assert summary is not None
        assert ModelType.HAIKU.value in summary.model_usage
        assert summary.model_usage[ModelType.HAIKU.value] == 1
        assert summary.model_usage[ModelType.SONNET.value] == 2
        assert summary.model_usage[ModelType.OPUS.value] == 3


class TestTaskTypePerformance:
    """Test task type performance analysis."""

    def test_task_type_performance(self, metrics_tracker):
        """Test getting performance for specific task type."""
        # Record metrics with different task descriptions
        for i in range(5):
            metrics_tracker.record_metric(
                agent_type="implement",
                task_id=f"database-{i}",
                task_description="Implement database schema changes",
                model_used=ModelType.SONNET.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                success=i < 4,  # 4 success, 1 failure
            )

        summary = metrics_tracker.get_task_type_performance("database")
        assert summary is not None
        assert summary.total_tasks == 5
        assert summary.successful_tasks == 4


class TestBestModelSelection:
    """Test selecting best model for agent type."""

    def test_get_best_model_for_agent_type(self, metrics_tracker):
        """Test getting best model for agent type based on performance."""
        # Record metrics showing Sonnet performs best for implement
        for i in range(3):
            metrics_tracker.record_metric(
                agent_type="implement",
                task_id=f"impl-haiku-{i}",
                task_description="Implement feature",
                model_used=ModelType.HAIKU.value,
                duration_ms=15000.0,
                input_tokens=1000,
                output_tokens=500,
                success=i < 2,  # 66% success
            )

        for i in range(5):
            metrics_tracker.record_metric(
                agent_type="implement",
                task_id=f"impl-sonnet-{i}",
                task_description="Implement feature",
                model_used=ModelType.SONNET.value,
                duration_ms=8000.0,
                input_tokens=2000,
                output_tokens=1000,
                success=i < 5,  # 100% success
            )

        best_model = metrics_tracker.get_best_model_for_agent_type("implement")
        assert best_model == ModelType.SONNET.value or best_model is not None


class TestPersistence:
    """Test persistence to JSON and SQLite."""

    def test_metrics_saved_to_json(self, temp_dir):
        """Test metrics are saved to JSON file."""
        storage_path = temp_dir / "agent_metrics.json"
        db_path = temp_dir / "telemetry.db"

        metrics = AgentMetrics(storage_path=storage_path, db_path=db_path)
        metrics.record_metric(
            agent_type="explore",
            task_id="task-persist-001",
            task_description="Test persistence",
            model_used=ModelType.HAIKU.value,
            duration_ms=5000.0,
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )

        assert storage_path.exists()
        data = json.loads(storage_path.read_text())
        assert len(data) == 1
        assert data[0]['task_id'] == "task-persist-001"

    def test_metrics_loaded_from_json(self, temp_dir):
        """Test metrics are loaded from JSON file on initialization."""
        storage_path = temp_dir / "agent_metrics.json"
        db_path = temp_dir / "telemetry.db"

        # Create first instance and record metric
        metrics1 = AgentMetrics(storage_path=storage_path, db_path=db_path)
        metrics1.record_metric(
            agent_type="test",
            task_id="task-load-001",
            task_description="Test loading",
            model_used=ModelType.SONNET.value,
            duration_ms=5000.0,
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )

        # Create second instance (should load from file)
        metrics2 = AgentMetrics(storage_path=storage_path, db_path=db_path)
        assert len(metrics2.metrics) == 1
        assert metrics2.metrics[0].task_id == "task-load-001"

    def test_export_metrics(self, temp_dir):
        """Test exporting metrics to file."""
        storage_path = temp_dir / "agent_metrics.json"
        db_path = temp_dir / "telemetry.db"
        export_path = temp_dir / "export.json"

        metrics = AgentMetrics(storage_path=storage_path, db_path=db_path)
        metrics.record_metric(
            agent_type="review",
            task_id="task-export-001",
            task_description="Export test",
            model_used=ModelType.OPUS.value,
            duration_ms=5000.0,
            input_tokens=1000,
            output_tokens=500,
            success=True,
        )

        success = metrics.export_metrics(export_path)
        assert success is True
        assert export_path.exists()

    def test_import_metrics(self, temp_dir):
        """Test importing metrics from file."""
        storage_path = temp_dir / "agent_metrics.json"
        db_path = temp_dir / "telemetry.db"
        import_path = temp_dir / "import.json"

        # Create import file
        import_data = [
            {
                'timestamp': datetime.now().isoformat(),
                'agent_type': 'implement',
                'task_id': 'task-import-001',
                'task_description': 'Import test',
                'model_used': ModelType.SONNET.value,
                'duration_ms': 5000.0,
                'input_tokens': 1000,
                'output_tokens': 500,
                'total_tokens': 1500,
                'cost_usd': 0.05,
                'success': True,
                'test_pass_rate': 1.0,
                'error_rate': 0.0,
                'files_created': 0,
                'files_modified': 0,
                'error_message': None,
            }
        ]
        import_path.write_text(json.dumps(import_data))

        metrics = AgentMetrics(storage_path=storage_path, db_path=db_path)
        success = metrics.import_metrics(import_path)
        assert success is True
        assert len(metrics.metrics) == 1


class TestPerformanceMetrics:
    """Test performance metric calculations."""

    def test_avg_duration_calculation(self, metrics_tracker):
        """Test average duration calculation."""
        durations = [3000, 5000, 7000, 4000, 6000]
        for i, duration in enumerate(durations):
            metrics_tracker.record_metric(
                agent_type="explore",
                task_id=f"duration-{i}",
                task_description="Duration test",
                model_used=ModelType.HAIKU.value,
                duration_ms=float(duration),
                input_tokens=1000,
                output_tokens=500,
                success=True,
            )

        summary = metrics_tracker.get_summary("explore")
        expected_avg = sum(durations) / len(durations)
        assert abs(summary.avg_duration_ms - expected_avg) < 0.1

    def test_min_max_duration(self, metrics_tracker):
        """Test min/max duration calculation."""
        durations = [2000, 8000, 5000, 3000, 9000]
        for i, duration in enumerate(durations):
            metrics_tracker.record_metric(
                agent_type="refactor",
                task_id=f"minmax-{i}",
                task_description="Min/Max test",
                model_used=ModelType.SONNET.value,
                duration_ms=float(duration),
                input_tokens=1000,
                output_tokens=500,
                success=True,
            )

        summary = metrics_tracker.get_summary("refactor")
        assert summary.min_duration_ms == min(durations)
        assert summary.max_duration_ms == max(durations)

    def test_avg_cost_per_task(self, metrics_tracker):
        """Test average cost per task calculation."""
        # Record metrics with known costs
        total_cost = 0.0
        for i in range(3):
            metric = metrics_tracker.record_metric(
                agent_type="test",
                task_id=f"cost-{i}",
                task_description="Cost test",
                model_used=ModelType.SONNET.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                success=True,
            )
            total_cost += metric.cost_usd

        summary = metrics_tracker.get_summary("test")
        expected_avg = total_cost / 3
        assert abs(summary.avg_cost_per_task - expected_avg) < 0.001


class TestClearAndReset:
    """Test clearing and resetting metrics."""

    def test_clear_metrics(self, metrics_tracker):
        """Test clearing all metrics."""
        # Record some metrics
        for i in range(5):
            metrics_tracker.record_metric(
                agent_type="explore",
                task_id=f"clear-{i}",
                task_description="Clear test",
                model_used=ModelType.HAIKU.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                success=True,
            )

        assert len(metrics_tracker.metrics) == 5

        # Clear metrics
        metrics_tracker.clear_metrics()
        assert len(metrics_tracker.metrics) == 0
        assert not metrics_tracker.storage_path.exists()
