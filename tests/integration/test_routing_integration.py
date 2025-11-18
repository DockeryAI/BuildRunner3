"""
Integration tests for routing system
"""
import pytest
from core.orchestrator import TaskOrchestrator
from core.routing import ComplexityLevel
from core.integrations.routing_integration import (
    integrate_routing,
    estimate_task_complexity,
    select_model_for_task,
    get_routing_recommendations,
    optimize_batch_routing,
)


class TestRoutingIntegration:
    """Test routing integration with orchestrator"""

    @pytest.fixture
    def orchestrator(self):
        """Create orchestrator with routing enabled"""
        return TaskOrchestrator(enable_telemetry=False, enable_routing=True, enable_parallel=False)

    @pytest.fixture
    def orchestrator_without_routing(self):
        """Create orchestrator without routing"""
        return TaskOrchestrator(enable_telemetry=False, enable_routing=False, enable_parallel=False)

    def test_integrate_routing_creates_components(self, orchestrator):
        """Test that routing integration creates estimator and selector"""
        assert orchestrator.complexity_estimator is not None
        assert orchestrator.model_selector is not None
        assert orchestrator.cost_tracker is not None

    def test_orchestrator_without_routing_has_no_components(self, orchestrator_without_routing):
        """Test that disabling routing doesn't create components"""
        assert orchestrator_without_routing.complexity_estimator is None
        assert orchestrator_without_routing.model_selector is None
        assert orchestrator_without_routing.cost_tracker is None

    def test_execute_batch_selects_model(self, orchestrator):
        """Test that executing a batch selects appropriate model"""
        tasks = [
            {'id': 'task1', 'name': 'Simple Task', 'description': 'A simple CRUD operation'},
        ]

        result = orchestrator.execute_batch(tasks)

        assert result['success'] is True
        assert 'model' in result or result.get('batches_completed', 0) > 0

    def test_estimate_task_complexity_simple_task(self, orchestrator):
        """Test complexity estimation for simple tasks"""
        complexity = estimate_task_complexity(
            orchestrator.complexity_estimator,
            task_description="Create a basic CRUD endpoint",
            files=["api/users.py"],
            requirements=["Handle GET requests"],
        )

        assert complexity is not None
        assert hasattr(complexity, 'level')
        assert hasattr(complexity, 'score')

    def test_estimate_task_complexity_complex_task(self, orchestrator):
        """Test complexity estimation for complex tasks"""
        complexity = estimate_task_complexity(
            orchestrator.complexity_estimator,
            task_description="Implement distributed transaction system with SAGA pattern",
            files=["core/transactions.py", "core/saga.py", "core/coordinator.py"],
            requirements=[
                "Implement SAGA pattern",
                "Handle distributed rollback",
                "Ensure ACID properties",
                "Add compensation logic",
            ],
        )

        assert complexity is not None
        # Complex tasks should have higher scores
        assert complexity.score > 0

    def test_select_model_for_task(self, orchestrator):
        """Test model selection based on complexity"""
        # Simple complexity
        from core.routing import TaskComplexity
        simple_complexity = TaskComplexity(level=ComplexityLevel.SIMPLE, score=0.2)

        selection = select_model_for_task(
            orchestrator.model_selector,
            complexity=simple_complexity,
        )

        assert selection is not None
        assert hasattr(selection, 'model_name')
        assert hasattr(selection, 'tier')

    def test_get_routing_recommendations(self, orchestrator):
        """Test getting routing recommendations for multiple tasks"""
        tasks = [
            {'id': 'task1', 'description': 'Simple CRUD', 'files': [], 'requirements': []},
            {'id': 'task2', 'description': 'Complex algorithm', 'files': ['algo.py'], 'requirements': ['Optimize performance']},
        ]

        recommendations = get_routing_recommendations(
            orchestrator.complexity_estimator,
            orchestrator.model_selector,
            tasks,
        )

        assert len(recommendations) == 2
        for rec in recommendations:
            assert 'task_id' in rec
            assert 'complexity_level' in rec
            assert 'selected_model' in rec

    def test_optimize_batch_routing(self, orchestrator):
        """Test batch routing optimization"""
        tasks = [
            {'id': 'task1', 'description': 'Simple task', 'files': [], 'requirements': []},
            {'id': 'task2', 'description': 'Another simple task', 'files': [], 'requirements': []},
        ]

        result = optimize_batch_routing(
            orchestrator.complexity_estimator,
            orchestrator.model_selector,
            tasks,
        )

        assert 'recommendations' in result
        assert 'by_tier' in result
        assert 'total_estimated_cost' in result
        assert len(result['recommendations']) == 2
