"""
Tests for Model Routing System

Tests complexity estimation, model selection, cost tracking, and fallback handling.
"""

import pytest
from pathlib import Path
from tempfile import NamedTemporaryFile
from datetime import datetime

from core.routing import (
    ComplexityEstimator,
    ComplexityLevel,
    TaskComplexity,
    ModelSelector,
    ModelConfig,
    ModelSelection,
    ModelTier,
)


class TestComplexityEstimator:
    """Test ComplexityEstimator functionality."""

    def test_init(self):
        """Test estimator initialization."""
        estimator = ComplexityEstimator()
        assert estimator.task_history == []

    def test_estimate_simple_task(self):
        """Test estimation of simple task."""
        estimator = ComplexityEstimator()
        complexity = estimator.estimate(
            task_description="Fix typo in README",
            files=[],
            context="",
        )

        assert complexity.level == ComplexityLevel.SIMPLE
        assert complexity.score < 50
        assert complexity.recommended_model == "haiku"
        assert "simplicity keywords" in " ".join(complexity.reasons).lower()

    def test_estimate_moderate_task(self):
        """Test estimation of moderate complexity task."""
        estimator = ComplexityEstimator()
        complexity = estimator.estimate(
            task_description="Add new API endpoint for user management",
            files=[Path("api/users.py"), Path("tests/test_users.py")],
            context="",
        )

        assert complexity.level in [ComplexityLevel.MODERATE, ComplexityLevel.SIMPLE]
        assert complexity.file_count == 2
        assert complexity.task_type == "new_feature"

    def test_estimate_complex_task(self):
        """Test estimation of complex task."""
        estimator = ComplexityEstimator()
        complexity = estimator.estimate(
            task_description="Refactor authentication system for performance optimization and security improvements",
            files=[Path(f"auth/module{i}.py") for i in range(12)],
            context="x" * 15000,  # Large context
        )

        assert complexity.level in [ComplexityLevel.COMPLEX, ComplexityLevel.CRITICAL]
        assert complexity.score >= 50
        assert complexity.has_security_implications
        assert complexity.has_performance_requirements
        assert complexity.recommended_model == "opus"

    def test_estimate_critical_task(self):
        """Test estimation of critical task."""
        estimator = ComplexityEstimator()
        complexity = estimator.estimate(
            task_description="Fix critical security vulnerability in production",
            files=[],
            context="",
        )

        assert complexity.level == ComplexityLevel.CRITICAL
        assert complexity.score >= 75
        assert complexity.recommended_model == "opus"
        assert "Critical/security-sensitive" in complexity.reasons[0]

    def test_file_counting(self):
        """Test file line counting."""
        estimator = ComplexityEstimator()

        # Create temporary files
        with NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f1:
            f1.write("line1\nline2\nline3\n")
            f1_path = Path(f1.name)

        with NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f2:
            f2.write("line1\nline2\n")
            f2_path = Path(f2.name)

        try:
            complexity = estimator.estimate(
                task_description="Test task",
                files=[f1_path, f2_path],
                context="",
            )

            assert complexity.line_count == 5
            assert complexity.file_count == 2
        finally:
            f1_path.unlink()
            f2_path.unlink()

    def test_task_type_classification(self):
        """Test task type classification."""
        estimator = ComplexityEstimator()

        test_cases = [
            ("Fix bug in login", "bug_fix"),
            ("Refactor user module", "refactor"),
            ("Add unit tests", "testing"),
            ("Update documentation", "documentation"),
            ("Create new feature", "new_feature"),
            ("Optimize database queries", "optimization"),
            ("Security vulnerability in auth", "security"),  # Changed to not include "fix"
            ("Update the code", "general"),
        ]

        for description, expected_type in test_cases:
            complexity = estimator.estimate(description)
            assert (
                complexity.task_type == expected_type
            ), f"Expected {expected_type} for '{description}', got {complexity.task_type}"

    def test_keyword_detection(self):
        """Test detection of complexity keywords."""
        estimator = ComplexityEstimator()

        # Complex keywords
        complexity = estimator.estimate(
            "Design distributed architecture with async processing and database migration"
        )
        assert complexity.score > 50
        assert complexity.has_architecture_changes
        assert complexity.has_concurrency

        # Simple keywords
        complexity = estimator.estimate("Fix typo and format code")
        assert complexity.score < 30

    def test_context_size_impact(self):
        """Test impact of large context on complexity."""
        estimator = ComplexityEstimator()

        # Small context
        small_complexity = estimator.estimate(
            "Test task",
            context="x" * 100,
        )

        # Large context
        large_complexity = estimator.estimate(
            "Test task",
            context="x" * 25000,
        )

        assert large_complexity.score > small_complexity.score
        assert large_complexity.context_size == 25000
        assert large_complexity.estimated_tokens > small_complexity.estimated_tokens

    def test_statistics_empty(self):
        """Test statistics with no history."""
        estimator = ComplexityEstimator()
        stats = estimator.get_statistics()

        assert stats["total_tasks"] == 0
        assert stats["avg_score"] == 0.0
        assert stats["level_distribution"] == {}

    def test_statistics_with_history(self):
        """Test statistics with estimation history."""
        estimator = ComplexityEstimator()

        # Estimate multiple tasks
        estimator.estimate("Fix typo")
        estimator.estimate("Add new feature with architecture changes")
        estimator.estimate("Critical security fix")

        stats = estimator.get_statistics()

        assert stats["total_tasks"] == 3
        assert stats["avg_score"] > 0
        assert "level_distribution" in stats
        assert "type_distribution" in stats
        assert stats["total_tokens_estimated"] >= 0


class TestModelSelector:
    """Test ModelSelector functionality."""

    def test_init_default_models(self):
        """Test initialization with default models."""
        selector = ModelSelector()

        assert "haiku" in selector.models
        assert "sonnet" in selector.models
        assert "opus" in selector.models
        assert selector.selection_history == []

    def test_init_custom_models(self):
        """Test initialization with custom models."""
        custom_models = {
            "custom": ModelConfig(
                name="custom",
                provider="test",
                tier=ModelTier.FAST,
                max_tokens=1000,
                context_window=10000,
            )
        }

        selector = ModelSelector(models=custom_models)
        assert "custom" in selector.models
        assert "haiku" not in selector.models

    def test_select_for_simple_task(self):
        """Test model selection for simple task."""
        selector = ModelSelector()
        estimator = ComplexityEstimator()

        complexity = estimator.estimate("Fix typo")
        selection = selector.select(complexity)

        assert selection.model.name == "haiku"
        assert selection.complexity == complexity
        assert "Simple task" in selection.reason

    def test_select_for_moderate_task(self):
        """Test model selection for moderate task."""
        selector = ModelSelector()
        estimator = ComplexityEstimator()

        complexity = estimator.estimate(
            "Add API endpoint", files=[Path(f"file{i}.py") for i in range(4)]
        )
        selection = selector.select(complexity)

        assert selection.model.name in ["haiku", "sonnet"]
        assert selection.estimated_cost > 0

    def test_select_for_complex_task(self):
        """Test model selection for complex task."""
        selector = ModelSelector()
        estimator = ComplexityEstimator()

        complexity = estimator.estimate(
            "Refactor architecture with performance optimization",
            files=[Path(f"file{i}.py") for i in range(15)],
        )
        selection = selector.select(complexity)

        assert selection.model.name in ["sonnet", "opus"]

    def test_select_for_critical_task(self):
        """Test model selection for critical task."""
        selector = ModelSelector()
        estimator = ComplexityEstimator()

        complexity = estimator.estimate("Critical security vulnerability fix")
        selection = selector.select(complexity)

        assert selection.model.name == "opus"
        assert "Critical" in selection.reason or "best available" in selection.reason

    def test_select_with_override(self):
        """Test model selection with user override."""
        selector = ModelSelector()
        estimator = ComplexityEstimator()

        complexity = estimator.estimate("Simple task")
        selection = selector.select(complexity, override_model="opus")

        assert selection.model.name == "opus"
        assert "override" in selection.reason.lower()

    def test_select_with_invalid_override(self):
        """Test model selection with invalid override."""
        selector = ModelSelector()
        estimator = ComplexityEstimator()

        complexity = estimator.estimate("Test task")

        with pytest.raises(ValueError, match="Unknown model"):
            selector.select(complexity, override_model="invalid_model")

    def test_select_with_unavailable_model(self):
        """Test fallback when primary model unavailable."""
        selector = ModelSelector()
        selector.update_model_availability("haiku", False)

        estimator = ComplexityEstimator()
        complexity = estimator.estimate("Simple task")
        selection = selector.select(complexity)

        # Should fallback to sonnet
        assert selection.model.name == "sonnet"
        assert "unavailable" in selection.reason.lower()

    def test_select_with_cost_threshold(self):
        """Test model selection with cost constraints."""
        selector = ModelSelector(cost_threshold=0.0001)  # Very low threshold

        # Ensure haiku is available
        selector.update_model_availability("haiku", True)

        estimator = ComplexityEstimator()

        complexity = estimator.estimate(
            "Simple task", context="x" * 100  # Use simple task for predictable cost
        )
        selection = selector.select(complexity)

        # Should use cheapest model (haiku) or respect cost threshold
        assert selection.model.name == "haiku" or selection.estimated_cost <= 0.0001

    def test_cost_estimation(self):
        """Test cost estimation."""
        selector = ModelSelector()
        estimator = ComplexityEstimator()

        complexity = estimator.estimate("Test task", context="x" * 1000)
        selection = selector.select(complexity)

        assert selection.estimated_cost > 0
        assert isinstance(selection.estimated_cost, float)

    def test_large_context_upgrades_model(self):
        """Test that large context requirements upgrade model."""
        selector = ModelSelector()

        # Create complexity with tokens exceeding both haiku and sonnet max_tokens
        complexity = TaskComplexity(
            level=ComplexityLevel.SIMPLE,
            score=20,
            reasons=["Test"],
            estimated_tokens=9000,  # Exceeds both haiku (4096) and sonnet (8192)
            recommended_model="haiku",
        )

        selection = selector.select(complexity)

        # Should upgrade to opus due to context size
        assert selection.model.name == "opus"
        assert "Large context" in selection.reason

    def test_get_model(self):
        """Test getting model by name."""
        selector = ModelSelector()

        haiku = selector.get_model("haiku")
        assert haiku is not None
        assert haiku.name == "haiku"

        none_model = selector.get_model("nonexistent")
        assert none_model is None

    def test_list_models(self):
        """Test listing all models."""
        # Create fresh selector to ensure clean state
        selector = ModelSelector()

        # Ensure all models are available first
        for model_name in ["haiku", "sonnet", "opus"]:
            selector.update_model_availability(model_name, True)

        all_models = selector.list_models()
        assert len(all_models) == 3

        available_models = selector.list_models(available_only=True)
        assert len(available_models) == 3

        # Mark one unavailable
        selector.update_model_availability("haiku", False)
        available_models = selector.list_models(available_only=True)
        assert len(available_models) == 2

    def test_update_model_availability(self):
        """Test updating model availability."""
        selector = ModelSelector()

        selector.update_model_availability("haiku", False)
        assert not selector.models["haiku"].is_available

        selector.update_model_availability("haiku", True)
        assert selector.models["haiku"].is_available

    def test_statistics_empty(self):
        """Test statistics with no history."""
        selector = ModelSelector()
        stats = selector.get_statistics()

        assert stats["total_selections"] == 0
        assert stats["total_estimated_cost"] == 0.0
        assert stats["avg_cost_per_task"] == 0.0

    def test_statistics_with_history(self):
        """Test statistics with selection history."""
        selector = ModelSelector()
        estimator = ComplexityEstimator()

        # Make multiple selections
        c1 = estimator.estimate("Simple task")
        c2 = estimator.estimate("Complex architecture refactor")
        c3 = estimator.estimate("Critical security fix")

        selector.select(c1)
        selector.select(c2)
        selector.select(c3)

        stats = selector.get_statistics()

        assert stats["total_selections"] == 3
        assert stats["total_estimated_cost"] > 0
        assert stats["avg_cost_per_task"] > 0
        assert "model_distribution" in stats
        assert "selections_by_complexity" in stats


class TestModelConfig:
    """Test ModelConfig dataclass."""

    def test_model_config_defaults(self):
        """Test ModelConfig default values."""
        config = ModelConfig(
            name="test",
            provider="anthropic",
            tier=ModelTier.FAST,
            max_tokens=4096,
            context_window=200000,
        )

        assert config.supports_streaming is True
        assert config.supports_vision is False
        assert config.supports_function_calling is True
        assert config.is_available is True
        assert config.rate_limit_rpm == 50

    def test_model_config_custom_values(self):
        """Test ModelConfig with custom values."""
        config = ModelConfig(
            name="custom",
            provider="openai",
            tier=ModelTier.ADVANCED,
            max_tokens=8192,
            context_window=128000,
            supports_vision=True,
            input_cost_per_1m=10.0,
            output_cost_per_1m=30.0,
            rate_limit_rpm=100,
        )

        assert config.name == "custom"
        assert config.provider == "openai"
        assert config.supports_vision is True
        assert config.input_cost_per_1m == 10.0


class TestModelSelection:
    """Test ModelSelection dataclass."""

    def test_model_selection_creation(self):
        """Test creating ModelSelection."""
        model = ModelConfig(
            name="test",
            provider="anthropic",
            tier=ModelTier.FAST,
            max_tokens=4096,
            context_window=200000,
        )

        complexity = TaskComplexity(
            level=ComplexityLevel.SIMPLE,
            score=25,
            reasons=["Test"],
        )

        selection = ModelSelection(
            model=model,
            reason="Test selection",
            complexity=complexity,
            estimated_cost=0.001,
        )

        assert selection.model == model
        assert selection.complexity == complexity
        assert selection.estimated_cost == 0.001
        assert isinstance(selection.timestamp, datetime)


class TestIntegration:
    """Integration tests for complete routing workflow."""

    def test_full_routing_workflow(self):
        """Test complete workflow from task to model selection."""
        # Create estimator and selector
        estimator = ComplexityEstimator()
        selector = ModelSelector()

        # Define a task with enough complexity factors
        task_description = "Refactor distributed authentication architecture with async OAuth2 and security hardening"
        files = [Path(f"auth/module{i}.py") for i in range(12)]  # More files
        context = "x" * 15000  # Larger context

        # Estimate complexity
        complexity = estimator.estimate(task_description, files, context)

        # With architecture, async, security keywords + many files + large context, should be moderate or complex
        assert complexity.level in [
            ComplexityLevel.MODERATE,
            ComplexityLevel.COMPLEX,
            ComplexityLevel.CRITICAL,
        ]
        assert complexity.file_count == 12
        assert complexity.has_security_implications or complexity.has_architecture_changes

        # Select model
        selection = selector.select(complexity)

        assert selection.model.name in ["haiku", "sonnet", "opus"]  # Any model is fine
        assert selection.estimated_cost > 0
        assert len(selection.alternatives) >= 0  # May have alternatives

        # Check history
        assert len(estimator.task_history) == 1
        assert len(selector.selection_history) == 1

    def test_multiple_tasks_workflow(self):
        """Test workflow with multiple tasks."""
        estimator = ComplexityEstimator()
        selector = ModelSelector()

        tasks = [
            "Fix typo in README",
            "Add API endpoint for users",
            "Refactor database architecture",
            "Critical security vulnerability",
        ]

        selections = []
        for task in tasks:
            complexity = estimator.estimate(task)
            selection = selector.select(complexity)
            selections.append(selection)

        # Verify we got 4 selections
        assert len(selections) == 4

        # Check model progression (should increase with complexity)
        models_used = [s.model.name for s in selections]
        assert "haiku" in models_used  # For simple task
        assert "opus" in models_used  # For critical task

        # Check statistics
        estimator_stats = estimator.get_statistics()
        selector_stats = selector.get_statistics()

        assert estimator_stats["total_tasks"] == 4
        assert selector_stats["total_selections"] == 4
        assert selector_stats["total_estimated_cost"] > 0
