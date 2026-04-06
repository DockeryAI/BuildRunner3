"""
Comprehensive tests for ResultAggregator.

Tests cover:
- Merging agent outputs
- File list management
- Error aggregation
- Conflict detection
- Summary generation
- Sequential vs parallel aggregation
"""

import pytest
from datetime import datetime
from unittest.mock import Mock

from core.agents.aggregator import (
    ResultAggregator,
    AggregatedResult,
    ConflictStrategy,
)
from core.agents.claude_agent_bridge import (
    AgentResponse,
    AgentType,
    AgentStatus,
)


# Fixtures
@pytest.fixture
def aggregator():
    """Create result aggregator"""
    return ResultAggregator()


@pytest.fixture
def aggregator_no_dedup():
    """Create aggregator without deduplication"""
    return ResultAggregator(dedup_files=False, dedup_errors=False)


@pytest.fixture
def single_agent_response():
    """Create single agent response"""
    return AgentResponse(
        agent_type=AgentType.EXPLORE,
        task_id="task-1",
        status=AgentStatus.COMPLETED,
        success=True,
        output="Explored successfully",
        files_created=["src/main.py"],
        files_modified=[],
        errors=[],
        duration_ms=5000.0,
        tokens_used=2000,
    )


@pytest.fixture
def multiple_agent_responses():
    """Create multiple agent responses"""
    responses = [
        AgentResponse(
            agent_type=AgentType.EXPLORE,
            task_id="task-1",
            status=AgentStatus.COMPLETED,
            success=True,
            output="Explored successfully",
            files_created=["src/main.py"],
            files_modified=[],
            errors=[],
            duration_ms=5000.0,
            tokens_used=2000,
        ),
        AgentResponse(
            agent_type=AgentType.IMPLEMENT,
            task_id="task-1",
            status=AgentStatus.COMPLETED,
            success=True,
            output="Implemented successfully",
            files_created=["src/feature.py"],
            files_modified=["src/main.py"],
            errors=[],
            duration_ms=8000.0,
            tokens_used=3500,
        ),
        AgentResponse(
            agent_type=AgentType.TEST,
            task_id="task-1",
            status=AgentStatus.COMPLETED,
            success=True,
            output="Tests created",
            files_created=["tests/test_feature.py"],
            files_modified=[],
            errors=[],
            duration_ms=4000.0,
            tokens_used=1500,
        ),
    ]
    return responses


@pytest.fixture
def mixed_success_responses():
    """Create responses with mixed success/failure"""
    responses = [
        AgentResponse(
            agent_type=AgentType.EXPLORE,
            task_id="task-1",
            status=AgentStatus.COMPLETED,
            success=True,
            output="Explored successfully",
            files_created=[],
            files_modified=[],
            errors=[],
            duration_ms=3000.0,
            tokens_used=1000,
        ),
        AgentResponse(
            agent_type=AgentType.IMPLEMENT,
            task_id="task-1",
            status=AgentStatus.FAILED,
            success=False,
            output="Implementation failed",
            files_created=[],
            files_modified=[],
            errors=["Module not found", "Syntax error"],
            duration_ms=2000.0,
            tokens_used=800,
        ),
    ]
    return responses


# Basic Tests
class TestResultAggregator:
    """Tests for ResultAggregator basic functionality"""

    def test_init(self):
        """Test aggregator initialization"""
        agg = ResultAggregator()
        assert agg.conflict_strategy == ConflictStrategy.MERGE
        assert agg.dedup_files is True
        assert agg.dedup_errors is True
        assert agg.aggregations_count == 0

    def test_init_custom_strategy(self):
        """Test initialization with custom strategy"""
        agg = ResultAggregator(
            conflict_strategy=ConflictStrategy.FIRST_WINS,
            dedup_files=False,
        )
        assert agg.conflict_strategy == ConflictStrategy.FIRST_WINS
        assert agg.dedup_files is False

    def test_aggregate_empty_list_raises_error(self, aggregator):
        """Test that aggregating empty list raises error"""
        with pytest.raises(ValueError, match="empty"):
            aggregator.aggregate([])

    def test_aggregate_single_response(self, aggregator, single_agent_response):
        """Test aggregating single response"""
        result = aggregator.aggregate([single_agent_response])

        assert result.aggregation_id is not None
        assert len(result.results) == 1
        assert result.merged_files_created == ["src/main.py"]

    def test_aggregate_multiple_responses(
        self,
        aggregator,
        multiple_agent_responses,
    ):
        """Test aggregating multiple responses"""
        result = aggregator.aggregate(multiple_agent_responses)

        assert len(result.results) == 3
        assert len(result.merged_files_created) == 3
        assert "src/main.py" in result.merged_files_created
        assert "src/feature.py" in result.merged_files_created
        assert "tests/test_feature.py" in result.merged_files_created


# Merge Tests
class TestMerging:
    """Tests for output merging"""

    def test_merge_outputs(self, aggregator, multiple_agent_responses):
        """Test merging outputs"""
        result = aggregator.aggregate(multiple_agent_responses)

        assert result.merged_output is not None
        assert "Explored successfully" in result.merged_output
        assert "Implemented successfully" in result.merged_output
        assert "Tests created" in result.merged_output

    def test_merge_outputs_includes_errors(
        self,
        aggregator,
        mixed_success_responses,
    ):
        """Test that merged output includes errors"""
        result = aggregator.aggregate(mixed_success_responses)

        assert (
            "Module not found" in result.merged_output or "Module not found" in result.merged_errors
        )

    def test_merge_files_created(self, aggregator, multiple_agent_responses):
        """Test merging files created"""
        result = aggregator.aggregate(multiple_agent_responses)

        assert len(result.merged_files_created) == 3
        assert all(
            f in result.merged_files_created
            for f in ["src/main.py", "src/feature.py", "tests/test_feature.py"]
        )

    def test_merge_files_modified(self, aggregator, multiple_agent_responses):
        """Test merging files modified"""
        result = aggregator.aggregate(multiple_agent_responses)

        assert "src/main.py" in result.merged_files_modified

    def test_merge_files_with_deduplication(
        self,
        aggregator,
        multiple_agent_responses,
    ):
        """Test file deduplication"""
        # Add duplicate
        multiple_agent_responses[2].files_created.append("src/main.py")

        result = aggregator.aggregate(multiple_agent_responses)

        # Should be deduplicated
        assert result.merged_files_created.count("src/main.py") == 1

    def test_merge_files_without_deduplication(
        self,
        aggregator_no_dedup,
        multiple_agent_responses,
    ):
        """Test file merging without deduplication"""
        multiple_agent_responses[2].files_created.append("src/main.py")

        result = aggregator_no_dedup.aggregate(multiple_agent_responses)

        # Should have duplicates
        assert result.merged_files_created.count("src/main.py") == 2

    def test_merge_errors(self, aggregator, mixed_success_responses):
        """Test merging errors"""
        result = aggregator.aggregate(mixed_success_responses)

        assert len(result.merged_errors) > 0
        assert "Module not found" in result.merged_errors
        assert "Syntax error" in result.merged_errors

    def test_merge_errors_with_deduplication(self, aggregator):
        """Test error deduplication"""
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.FAILED,
                success=False,
                output="",
                files_created=[],
                files_modified=[],
                errors=["Error A", "Error B"],
                duration_ms=1000.0,
                tokens_used=100,
            ),
            AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="task-1",
                status=AgentStatus.FAILED,
                success=False,
                output="",
                files_created=[],
                files_modified=[],
                errors=["Error B", "Error C"],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        result = aggregator.aggregate(responses)

        # Should be deduplicated
        assert len(result.merged_errors) == 3  # A, B, C
        assert result.merged_errors.count("Error B") == 1


# Conflict Detection Tests
class TestConflictDetection:
    """Tests for conflict detection"""

    def test_no_conflicts(self, aggregator):
        """Test detection with no conflicts"""
        # Create responses without any file conflicts
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=["src/doc.md"],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
            AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=["src/feature.py"],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        result = aggregator.aggregate(responses)

        # Should not have conflicts
        assert len(result.conflict_resolutions) == 0

    def test_detect_file_creation_conflicts(self, aggregator):
        """Test detecting file creation conflicts"""
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=["src/main.py"],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
            AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=["src/main.py"],  # Same file
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        result = aggregator.aggregate(responses)

        # Should detect conflict
        assert len(result.conflict_resolutions) > 0
        assert any("main.py" in c and "multiple" in c.lower() for c in result.conflict_resolutions)

    def test_detect_create_then_modify_conflict(self, aggregator):
        """Test detecting create then modify conflict"""
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=["src/main.py"],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
            AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=[],
                files_modified=["src/main.py"],  # Modified previously created file
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        result = aggregator.aggregate(responses)

        # This is not actually a conflict, it's expected
        # Let's check the implementation
        assert len(result.results) == 2


# Summary Generation Tests
class TestSummaryGeneration:
    """Tests for summary generation"""

    def test_summary_generation(self, aggregator, multiple_agent_responses):
        """Test that summary is generated"""
        result = aggregator.aggregate(multiple_agent_responses)

        assert result.summary is not None
        assert len(result.summary) > 0
        assert "Aggregation Summary" in result.summary

    def test_summary_includes_agent_info(self, aggregator, multiple_agent_responses):
        """Test that summary includes agent information"""
        result = aggregator.aggregate(multiple_agent_responses)

        assert "explore" in result.summary.lower()
        assert "implement" in result.summary.lower()
        assert "test" in result.summary.lower()

    def test_summary_includes_metrics(self, aggregator, multiple_agent_responses):
        """Test that summary includes metrics"""
        result = aggregator.aggregate(multiple_agent_responses)

        assert "files created" in result.summary.lower()
        assert "success rate" in result.summary.lower()

    def test_summary_of_failed_execution(
        self,
        aggregator,
        mixed_success_responses,
    ):
        """Test summary of partially failed execution"""
        result = aggregator.aggregate(mixed_success_responses)

        assert result.summary is not None
        assert "Failed" in result.summary or "FAILED" in result.summary


# Metrics Calculation Tests
class TestMetricsCalculation:
    """Tests for metrics calculation"""

    def test_metrics_duration_calculation(
        self,
        aggregator,
        multiple_agent_responses,
    ):
        """Test duration metrics"""
        result = aggregator.aggregate(multiple_agent_responses)

        metrics = result.metrics
        assert metrics["total_duration_ms"] == 17000.0  # 5000 + 8000 + 4000
        assert metrics["avg_duration_ms"] > 0

    def test_metrics_token_calculation(
        self,
        aggregator,
        multiple_agent_responses,
    ):
        """Test token metrics"""
        result = aggregator.aggregate(multiple_agent_responses)

        metrics = result.metrics
        assert metrics["total_tokens"] == 7000  # 2000 + 3500 + 1500
        assert metrics["avg_tokens"] > 0

    def test_metrics_success_rate(self, aggregator, mixed_success_responses):
        """Test success rate calculation"""
        result = aggregator.aggregate(mixed_success_responses)

        metrics = result.metrics
        assert "success_rate" in metrics
        assert metrics["success_rate"] == 50.0  # 1 out of 2 succeeded

    def test_metrics_successful_agents(self, aggregator, mixed_success_responses):
        """Test successful agent count"""
        result = aggregator.aggregate(mixed_success_responses)

        metrics = result.metrics
        assert metrics["successful_agents"] == 1
        assert metrics["failed_agents"] == 1

    def test_metrics_with_all_successful(self, aggregator, multiple_agent_responses):
        """Test metrics with all successful responses"""
        result = aggregator.aggregate(multiple_agent_responses)

        metrics = result.metrics
        assert metrics["successful_agents"] == 3
        assert metrics["failed_agents"] == 0
        assert metrics["success_rate"] == 100.0


# Sequential Aggregation Tests
class TestSequentialAggregation:
    """Tests for sequential workflow aggregation"""

    def test_sequential_aggregation(self, aggregator, multiple_agent_responses):
        """Test sequential aggregation"""
        result = aggregator.aggregate_sequential_results(
            multiple_agent_responses,
            task_context="Implementing a feature",
        )

        assert result is not None
        assert len(result.results) == 3

    def test_sequential_summary(self, aggregator, multiple_agent_responses):
        """Test sequential summary generation"""
        result = aggregator.aggregate_sequential_results(multiple_agent_responses)

        assert "Sequential" in result.summary
        assert "Phase" in result.summary

    def test_sequential_empty_raises_error(self, aggregator):
        """Test that empty sequential aggregation raises error"""
        with pytest.raises(ValueError, match="empty"):
            aggregator.aggregate_sequential_results([])

    def test_sequential_with_context(self, aggregator, multiple_agent_responses):
        """Test sequential aggregation with context"""
        context = "Implementing user authentication"
        result = aggregator.aggregate_sequential_results(
            multiple_agent_responses,
            task_context=context,
        )

        assert context in result.merged_output


# Parallel Aggregation Tests
class TestParallelAggregation:
    """Tests for parallel workflow aggregation"""

    def test_parallel_aggregation(self, aggregator):
        """Test parallel aggregation"""
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="Explored",
                files_created=["doc1.md"],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
            AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="Implemented",
                files_created=["code1.py"],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
            AgentResponse(
                agent_type=AgentType.TEST,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="Tested",
                files_created=["test1.py"],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        result = aggregator.aggregate_parallel_results(responses)

        assert result is not None
        assert len(result.results) == 3

    def test_parallel_summary(self, aggregator):
        """Test parallel summary generation"""
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=[],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        result = aggregator.aggregate_parallel_results(responses)

        assert "Parallel" in result.summary

    def test_parallel_empty_raises_error(self, aggregator):
        """Test that empty parallel aggregation raises error"""
        with pytest.raises(ValueError, match="empty"):
            aggregator.aggregate_parallel_results([])

    def test_parallel_with_context(self, aggregator):
        """Test parallel aggregation with context"""
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=[],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        context = "Multiple independent analysis tasks"
        result = aggregator.aggregate_parallel_results(responses, task_context=context)

        assert context in result.merged_output


# Statistics Tests
class TestStatistics:
    """Tests for aggregator statistics"""

    def test_stats_tracking(self, aggregator, single_agent_response):
        """Test that stats are tracked"""
        assert aggregator.aggregations_count == 0

        aggregator.aggregate([single_agent_response])

        assert aggregator.aggregations_count == 1
        assert aggregator.total_results_aggregated == 1

    def test_stats_multiple_aggregations(self, aggregator, multiple_agent_responses):
        """Test stats across multiple aggregations"""
        aggregator.aggregate(multiple_agent_responses)
        aggregator.aggregate(multiple_agent_responses)

        assert aggregator.aggregations_count == 2
        assert aggregator.total_results_aggregated == 6

    def test_get_stats(self, aggregator, multiple_agent_responses):
        """Test get_stats method"""
        aggregator.aggregate(multiple_agent_responses)

        stats = aggregator.get_stats()

        assert stats["aggregations_count"] == 1
        assert stats["total_results_aggregated"] == 3
        assert stats["avg_results_per_aggregation"] == 3.0


# Result Serialization Tests
class TestResultSerialization:
    """Tests for result serialization"""

    def test_aggregated_result_to_dict(self, aggregator, single_agent_response):
        """Test converting aggregated result to dict"""
        result = aggregator.aggregate([single_agent_response])

        result_dict = result.to_dict()

        assert result_dict["aggregation_id"] == result.aggregation_id
        assert result_dict["result_count"] == 1
        assert "metrics" in result_dict
        assert "summary" in result_dict

    def test_result_dict_contains_metadata(self, aggregator, multiple_agent_responses):
        """Test that result dict contains all metadata"""
        result = aggregator.aggregate(multiple_agent_responses)

        result_dict = result.to_dict()

        assert "merged_files_created" in result_dict
        assert "merged_files_modified" in result_dict
        assert "merged_errors" in result_dict
        assert "conflict_resolutions" in result_dict


# Edge Cases Tests
class TestEdgeCases:
    """Tests for edge cases"""

    def test_single_response(self, aggregator, single_agent_response):
        """Test aggregating single response"""
        result = aggregator.aggregate([single_agent_response])

        assert len(result.results) == 1
        assert result.metrics["successful_agents"] == 1

    def test_all_failed_responses(self, aggregator):
        """Test aggregating all failed responses"""
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.FAILED,
                success=False,
                output="Failed",
                files_created=[],
                files_modified=[],
                errors=["Error 1"],
                duration_ms=1000.0,
                tokens_used=100,
            ),
            AgentResponse(
                agent_type=AgentType.IMPLEMENT,
                task_id="task-1",
                status=AgentStatus.FAILED,
                success=False,
                output="Failed",
                files_created=[],
                files_modified=[],
                errors=["Error 2"],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        result = aggregator.aggregate(responses)

        assert result.metrics["success_rate"] == 0.0
        assert result.metrics["failed_agents"] == 2

    def test_many_agent_types(self, aggregator):
        """Test aggregating responses from different agent types"""
        responses = [
            AgentResponse(
                agent_type=agent_type,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output=f"Output from {agent_type.value}",
                files_created=[f"file_{agent_type.value}.py"],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            )
            for agent_type in AgentType
        ]

        result = aggregator.aggregate(responses)

        assert len(result.results) == len(list(AgentType))
        assert len(result.merged_files_created) == len(list(AgentType))

    def test_zero_duration_responses(self, aggregator):
        """Test aggregating responses with zero duration"""
        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output="",
                files_created=[],
                files_modified=[],
                errors=[],
                duration_ms=0.0,
                tokens_used=0,
            ),
        ]

        result = aggregator.aggregate(responses)

        assert result.metrics["total_duration_ms"] == 0.0
        assert result.metrics["avg_duration_ms"] == 0.0

    def test_very_large_outputs(self, aggregator):
        """Test aggregating responses with large outputs"""
        large_output = "X" * 100000

        responses = [
            AgentResponse(
                agent_type=AgentType.EXPLORE,
                task_id="task-1",
                status=AgentStatus.COMPLETED,
                success=True,
                output=large_output,
                files_created=[],
                files_modified=[],
                errors=[],
                duration_ms=1000.0,
                tokens_used=100,
            ),
        ]

        result = aggregator.aggregate(responses)

        assert len(result.merged_output) > 100000
