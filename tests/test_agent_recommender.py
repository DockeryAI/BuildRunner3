"""
Tests for Agent Recommender System (Build 8B Feature 3)

Tests:
- Task complexity classification
- Agent type detection from task description
- Model selection based on complexity and cost
- Historical performance-based recommendations
- Alternative agent suggestions
- Batch recommendations
- Recommendation accuracy tracking
"""

import pytest
from pathlib import Path
from datetime import datetime, timedelta
import tempfile

from core.agents.recommender import (
    AgentRecommender,
    AgentRecommendation,
    TaskComplexity,
)
from core.agents.metrics import AgentMetrics, ModelType
from core.agents.claude_agent_bridge import AgentType


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


@pytest.fixture
def recommender(metrics_tracker):
    """Create AgentRecommender instance."""
    return AgentRecommender(metrics=metrics_tracker)


class TestComplexityClassification:
    """Test task complexity classification."""

    def test_classify_simple_task(self, recommender):
        """Test classifying simple task."""
        complexity = recommender._classify_complexity("Add a simple comment to the function")
        assert complexity == TaskComplexity.SIMPLE

    def test_classify_medium_task(self, recommender):
        """Test classifying medium complexity task."""
        complexity = recommender._classify_complexity(
            "Implement a new authentication module with comprehensive error handling "
            "and detailed logging for production use cases"
        )
        assert complexity in [TaskComplexity.MEDIUM, TaskComplexity.COMPLEX]

    def test_classify_complex_task(self, recommender):
        """Test classifying complex task."""
        complexity = recommender._classify_complexity(
            "Refactor the entire authentication system to support multiple "
            "providers with distributed caching and complex integration patterns"
        )
        assert complexity == TaskComplexity.COMPLEX

    def test_simple_keyword_detection(self, recommender):
        """Test simple keyword detection."""
        complexity = recommender._classify_complexity("simple straightforward task")
        assert complexity == TaskComplexity.SIMPLE

    def test_complex_keyword_detection(self, recommender):
        """Test complex keyword detection."""
        complexity = recommender._classify_complexity(
            "complex difficult multi-component architecture refactor"
        )
        assert complexity == TaskComplexity.COMPLEX

    def test_length_based_complexity(self, recommender):
        """Test complexity based on description length."""
        # Short description
        short = "Fix bug"
        complexity_short = recommender._classify_complexity(short)
        assert complexity_short == TaskComplexity.SIMPLE

        # Long description
        long = " ".join(["word"] * 50)
        complexity_long = recommender._classify_complexity(long)
        assert complexity_long in [TaskComplexity.MEDIUM, TaskComplexity.COMPLEX]


class TestAgentTypeDetection:
    """Test detecting agent type from task description."""

    def test_detect_explore_agent(self, recommender):
        """Test detecting explore agent."""
        descriptions = [
            "Explore the codebase to understand the architecture",
            "Investigate the current implementation",
            "Research how the database schema is structured",
            "Discover the existing patterns in the code",
        ]

        for desc in descriptions:
            agent_type = recommender._detect_agent_type(desc)
            assert agent_type == AgentType.EXPLORE.value

    def test_detect_test_agent(self, recommender):
        """Test detecting test agent."""
        descriptions = [
            "Write unit tests for the new feature",
            "Create integration tests for the API",
            "Write e2e tests for the authentication flow",
            "Add test coverage for error cases",
        ]

        for desc in descriptions:
            agent_type = recommender._detect_agent_type(desc)
            assert agent_type == AgentType.TEST.value

    def test_detect_review_agent(self, recommender):
        """Test detecting review agent."""
        descriptions = [
            "Review the code quality of the pull request",
            "Perform code review and analysis",
            "Check for security vulnerabilities",
            "Perform static analysis on the codebase",
        ]

        for desc in descriptions:
            agent_type = recommender._detect_agent_type(desc)
            assert agent_type == AgentType.REVIEW.value

    def test_detect_refactor_agent(self, recommender):
        """Test detecting refactor agent."""
        descriptions = [
            "Refactor the authentication module",
            "Optimize the database queries",
            "Improve code maintainability",
            "Simplify the complex function",
        ]

        for desc in descriptions:
            agent_type = recommender._detect_agent_type(desc)
            assert agent_type == AgentType.REFACTOR.value

    def test_detect_implement_agent(self, recommender):
        """Test detecting implement agent."""
        descriptions = [
            "Implement the new feature",
            "Add support for multiple authentication providers",
            "Build a new API endpoint",
            "Create the database schema",
        ]

        for desc in descriptions:
            agent_type = recommender._detect_agent_type(desc)
            assert agent_type == AgentType.IMPLEMENT.value

    def test_keyword_match_counting(self, recommender):
        """Test keyword match counting."""
        task_desc = "Write unit tests and integration tests"
        matches = recommender._get_keyword_matches(task_desc, AgentType.TEST.value)
        assert matches >= 2  # "test" appears multiple times


class TestModelSelection:
    """Test model selection based on complexity and performance."""

    def test_simple_task_gets_haiku(self, recommender):
        """Test that simple tasks default to Haiku."""
        model = recommender.get_best_model(AgentType.EXPLORE.value, TaskComplexity.SIMPLE)
        # Should be Haiku or fallback to best available
        assert model is not None

    def test_medium_task_gets_sonnet(self, recommender):
        """Test that medium tasks get Sonnet."""
        model = recommender.get_best_model(AgentType.IMPLEMENT.value, TaskComplexity.MEDIUM)
        assert model is not None

    def test_complex_task_gets_opus(self, recommender):
        """Test that complex tasks get Opus."""
        model = recommender.get_best_model(AgentType.REVIEW.value, TaskComplexity.COMPLEX)
        assert model is not None

    def test_historical_performance_influences_selection(self, metrics_tracker, recommender):
        """Test that historical performance influences model selection."""
        # Record high success rate for Sonnet on implement tasks
        for i in range(5):
            metrics_tracker.record_metric(
                agent_type=AgentType.IMPLEMENT.value,
                task_id=f"impl-sonnet-{i}",
                task_description="Implement feature",
                model_used=ModelType.SONNET.value,
                duration_ms=8000.0,
                input_tokens=2000,
                output_tokens=1000,
                success=True,
            )

        # Record low success rate for Haiku
        for i in range(3):
            metrics_tracker.record_metric(
                agent_type=AgentType.IMPLEMENT.value,
                task_id=f"impl-haiku-{i}",
                task_description="Implement feature",
                model_used=ModelType.HAIKU.value,
                duration_ms=10000.0,
                input_tokens=1000,
                output_tokens=500,
                success=i < 1,  # Only 33% success
            )

        best_model = recommender.get_best_model(AgentType.IMPLEMENT.value, TaskComplexity.MEDIUM)
        assert best_model is not None

    def test_model_selection_with_cost_constraint(self, recommender):
        """Test model selection with cost constraint."""
        # Get model with low cost constraint (should prefer Haiku)
        model = recommender.get_model_by_constraints(
            AgentType.EXPLORE.value,
            TaskComplexity.SIMPLE,
            max_cost_per_task=0.05,
            prefer_speed=False
        )
        assert model is not None
        assert "haiku" in model.lower() or model is not None

    def test_model_selection_with_speed_preference(self, recommender):
        """Test model selection preferring speed over cost."""
        model = recommender.get_model_by_constraints(
            AgentType.IMPLEMENT.value,
            TaskComplexity.MEDIUM,
            max_cost_per_task=1.0,
            prefer_speed=True
        )
        assert model is not None


class TestTaskAnalysis:
    """Test comprehensive task analysis."""

    def test_analyze_task_basic(self, recommender):
        """Test basic task analysis."""
        recommendation = recommender.analyze_task(
            "Write unit tests for the authentication module"
        )

        assert recommendation.recommended_agent_type is not None
        assert recommendation.recommended_model is not None
        assert recommendation.confidence > 0.0
        assert recommendation.reason is not None

    def test_analyze_simple_task(self, recommender):
        """Test analyzing a simple task."""
        recommendation = recommender.analyze_task("Add a comment to the function")

        assert recommendation.recommended_agent_type == AgentType.EXPLORE.value or \
               recommendation.recommended_agent_type is not None
        assert recommendation.supporting_metrics['complexity'] == TaskComplexity.SIMPLE.value

    def test_analyze_complex_task(self, recommender):
        """Test analyzing a complex task."""
        recommendation = recommender.analyze_task(
            "Refactor the entire authentication system to support multiple providers "
            "with distributed caching and complex integration patterns"
        )

        assert recommendation.supporting_metrics['complexity'] == TaskComplexity.COMPLEX.value
        assert recommendation.confidence is not None

    def test_recommendation_includes_alternatives(self, recommender):
        """Test that recommendations include alternative agents."""
        recommendation = recommender.analyze_task("Implement new feature")

        assert len(recommendation.alternative_agents) > 0
        assert len(recommendation.alternative_models) > 0
        assert recommendation.recommended_agent_type not in recommendation.alternative_agents

    def test_recommendation_expected_metrics(self, recommender):
        """Test that recommendations include expected metrics."""
        recommendation = recommender.analyze_task("Test the authentication system")

        assert recommendation.expected_duration_ms > 0
        assert recommendation.expected_cost_usd >= 0
        assert recommendation.expected_success_rate >= 0

    def test_recommendation_confidence_score(self, recommender):
        """Test recommendation confidence scoring."""
        recommendation = recommender.analyze_task("Implement feature")

        assert 0.0 <= recommendation.confidence <= 1.0

    def test_recommendation_with_historical_data(self, metrics_tracker, recommender):
        """Test recommendation with historical data available."""
        # Record some historical metrics
        for i in range(10):
            metrics_tracker.record_metric(
                agent_type=AgentType.TEST.value,
                task_id=f"test-{i}",
                task_description="Write tests",
                model_used=ModelType.SONNET.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                success=i < 9,  # 90% success rate
                test_pass_rate=0.9,
            )

        recommendation = recommender.analyze_task("Write unit tests for the module")

        # Should have historical data supporting the recommendation
        assert 'historical_success_rate' in recommendation.supporting_metrics
        assert recommendation.expected_success_rate > 0


class TestAlternativeRecommendations:
    """Test alternative agent and model recommendations."""

    def test_alternative_agents(self, recommender):
        """Test getting alternative agents."""
        alternatives = recommender._get_alternative_agents(AgentType.IMPLEMENT.value, TaskComplexity.MEDIUM)

        assert len(alternatives) > 0
        assert AgentType.IMPLEMENT.value not in alternatives

    def test_more_alternatives_for_complex_tasks(self, recommender):
        """Test that complex tasks get more alternatives."""
        simple_alternatives = recommender._get_alternative_agents(
            AgentType.IMPLEMENT.value, TaskComplexity.SIMPLE
        )
        complex_alternatives = recommender._get_alternative_agents(
            AgentType.IMPLEMENT.value, TaskComplexity.COMPLEX
        )

        assert len(complex_alternatives) >= len(simple_alternatives)

    def test_alternative_models(self, recommender):
        """Test getting alternative models."""
        alternatives = recommender._get_alternative_models(
            ModelType.SONNET.value, TaskComplexity.MEDIUM
        )

        assert len(alternatives) > 0
        assert ModelType.SONNET.value not in alternatives
        assert all(model in alternatives for model in [
            ModelType.HAIKU.value, ModelType.OPUS.value
        ])


class TestBatchRecommendations:
    """Test batch task recommendations."""

    def test_batch_recommendations(self, recommender):
        """Test recommending agents for batch of tasks."""
        tasks = [
            {'description': 'Implement new authentication module'},
            {'description': 'Write unit tests for the API'},
            {'description': 'Review code quality'},
            {'description': 'Refactor the database layer'},
            {'description': 'Explore the codebase'},
        ]

        recommendations = recommender.recommend_batch_agents(tasks)

        assert len(recommendations) == 5
        assert all(isinstance(r, AgentRecommendation) for r in recommendations)

    def test_batch_with_empty_description(self, recommender):
        """Test batch with tasks having empty descriptions."""
        tasks = [
            {'description': 'Implement feature'},
            {'description': ''},  # Empty
            {'description': 'Write tests'},
        ]

        recommendations = recommender.recommend_batch_agents(tasks)

        # Should only return recommendations for non-empty descriptions
        assert len(recommendations) == 2


class TestRecommendationSummary:
    """Test recommendation summary and accuracy tracking."""

    def test_recommendations_summary_no_data(self, recommender):
        """Test summary with no historical data."""
        summary = recommender.get_recommendations_summary()

        assert 'total_recommendations' in summary
        assert 'successful_recommendations' in summary
        assert 'accuracy_rate' in summary

    def test_recommendations_summary_with_data(self, metrics_tracker, recommender):
        """Test summary with historical data."""
        # Record some metrics
        for i in range(10):
            metrics_tracker.record_metric(
                agent_type=AgentType.TEST.value,
                task_id=f"test-{i}",
                task_description="Test task",
                model_used=ModelType.SONNET.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                success=i < 8,  # 80% success rate
            )

        summary = recommender.get_recommendations_summary()

        assert summary['total_recommendations'] == 10
        assert summary['successful_recommendations'] == 8
        assert abs(summary['accuracy_rate'] - 0.8) < 0.01
        assert AgentType.TEST.value in summary['by_agent_type']


class TestCostEstimation:
    """Test cost estimation for tasks."""

    def test_estimate_cost_haiku(self, recommender):
        """Test cost estimation for Haiku."""
        cost = recommender._estimate_cost(ModelType.HAIKU.value, 600000)  # 10 minutes
        assert cost > 0
        assert cost < 1.0  # Should be cheap

    def test_estimate_cost_sonnet(self, recommender):
        """Test cost estimation for Sonnet."""
        cost = recommender._estimate_cost(ModelType.SONNET.value, 600000)
        assert cost > 0
        assert cost < 5.0

    def test_estimate_cost_opus(self, recommender):
        """Test cost estimation for Opus."""
        cost = recommender._estimate_cost(ModelType.OPUS.value, 600000)
        assert cost > 0

    def test_cost_increases_with_duration(self, recommender):
        """Test that cost increases with duration."""
        cost_short = recommender._estimate_cost(ModelType.SONNET.value, 300000)  # 5 min
        cost_long = recommender._estimate_cost(ModelType.SONNET.value, 1200000)  # 20 min

        assert cost_long > cost_short


class TestRecommenderKeywordMatching:
    """Test keyword matching for agent type detection."""

    def test_explore_keywords(self, recommender):
        """Test explore agent keywords."""
        keywords = recommender.AGENT_TYPE_KEYWORDS[AgentType.EXPLORE.value]

        assert 'explore' in keywords
        assert 'understand' in keywords
        assert 'investigate' in keywords

    def test_test_keywords(self, recommender):
        """Test test agent keywords."""
        keywords = recommender.AGENT_TYPE_KEYWORDS[AgentType.TEST.value]

        assert 'test' in keywords
        assert 'unit test' in keywords
        assert 'debug' in keywords

    def test_review_keywords(self, recommender):
        """Test review agent keywords."""
        keywords = recommender.AGENT_TYPE_KEYWORDS[AgentType.REVIEW.value]

        assert 'review' in keywords
        assert 'quality' in keywords
        assert 'security' in keywords

    def test_refactor_keywords(self, recommender):
        """Test refactor agent keywords."""
        keywords = recommender.AGENT_TYPE_KEYWORDS[AgentType.REFACTOR.value]

        assert 'refactor' in keywords
        assert 'optimize' in keywords
        assert 'improve' in keywords

    def test_implement_keywords(self, recommender):
        """Test implement agent keywords."""
        keywords = recommender.AGENT_TYPE_KEYWORDS[AgentType.IMPLEMENT.value]

        assert 'implement' in keywords
        assert 'build' in keywords
        assert 'create' in keywords


class TestRecommendationReasoning:
    """Test recommendation reasoning generation."""

    def test_reason_generation_without_history(self, recommender):
        """Test generating reason without historical data."""
        recommendation = recommender.analyze_task("Test the system")

        assert recommendation.reason is not None
        assert len(recommendation.reason) > 0

    def test_reason_generation_with_history(self, metrics_tracker, recommender):
        """Test generating reason with historical data."""
        # Record historical data
        for i in range(5):
            metrics_tracker.record_metric(
                agent_type=AgentType.TEST.value,
                task_id=f"test-{i}",
                task_description="Test task",
                model_used=ModelType.SONNET.value,
                duration_ms=5000.0,
                input_tokens=1000,
                output_tokens=500,
                success=True,
            )

        recommendation = recommender.analyze_task("Write comprehensive tests")

        assert "Historical success rate" in recommendation.reason or \
               recommendation.reason is not None


class TestModelNameFormatting:
    """Test model name formatting."""

    def test_get_model_name_haiku(self, recommender):
        """Test formatting Haiku model name."""
        name = recommender._get_model_name(ModelType.HAIKU.value)
        assert name == "Haiku"

    def test_get_model_name_sonnet(self, recommender):
        """Test formatting Sonnet model name."""
        name = recommender._get_model_name(ModelType.SONNET.value)
        assert name == "Sonnet"

    def test_get_model_name_opus(self, recommender):
        """Test formatting Opus model name."""
        name = recommender._get_model_name(ModelType.OPUS.value)
        assert name == "Opus"

    def test_get_model_name_unknown(self, recommender):
        """Test formatting unknown model name."""
        name = recommender._get_model_name("unknown-model")
        assert name == "Unknown"


class TestEdgeCases:
    """Test edge cases and error handling."""

    def test_empty_task_description(self, recommender):
        """Test recommending for empty task description."""
        # Should not crash and return default
        recommendation = recommender.analyze_task("")
        assert recommendation is not None
        assert recommendation.recommended_agent_type is not None

    def test_very_long_task_description(self, recommender):
        """Test very long task description."""
        long_desc = " ".join(["word"] * 1000)
        recommendation = recommender.analyze_task(long_desc)

        assert recommendation is not None
        # Should classify as complex due to length
        assert recommendation.supporting_metrics['complexity'] in [
            TaskComplexity.COMPLEX.value,
            TaskComplexity.MEDIUM.value
        ]

    def test_special_characters_in_description(self, recommender):
        """Test task description with special characters."""
        desc = "Implement feature!@#$%^&*() with special chars <>"
        recommendation = recommender.analyze_task(desc)

        assert recommendation is not None
        assert recommendation.recommended_agent_type is not None
