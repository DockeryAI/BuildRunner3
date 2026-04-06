"""
Routing Integration Module

Provides helper functions for integrating model routing into the orchestrator.
Handles complexity estimation, model selection, and cost tracking.
"""

from typing import Dict, Any, Optional, List
from pathlib import Path

from core.routing import (
    ComplexityEstimator,
    ComplexityLevel,
    TaskComplexity,
    ModelSelector,
    ModelSelection,
    ModelTier,
    CostTracker,
    CostEntry,
)


def integrate_routing(orchestrator, enable_cost_tracking: bool = True) -> Dict[str, Any]:
    """
    Integrate routing system into an orchestrator instance.

    Args:
        orchestrator: The TaskOrchestrator instance
        enable_cost_tracking: Whether to enable cost tracking

    Returns:
        Dictionary with integrated components
    """
    estimator = ComplexityEstimator()
    selector = ModelSelector()
    cost_tracker = CostTracker() if enable_cost_tracking else None

    orchestrator.complexity_estimator = estimator
    orchestrator.model_selector = selector
    orchestrator.cost_tracker = cost_tracker

    return {
        "estimator": estimator,
        "selector": selector,
        "cost_tracker": cost_tracker,
    }


def estimate_task_complexity(
    estimator: ComplexityEstimator,
    task_description: str,
    files: Optional[List[str]] = None,
    requirements: Optional[List[str]] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> TaskComplexity:
    """
    Estimate complexity of a task.

    Args:
        estimator: ComplexityEstimator instance
        task_description: Description of the task
        files: List of files involved
        requirements: List of requirements (used in context)
        metadata: Additional metadata

    Returns:
        TaskComplexity with level and score
    """
    # Build context from requirements and metadata
    context_parts = []

    if requirements:
        context_parts.append(f"Requirements: {', '.join(requirements)}")

    if metadata:
        context_parts.append(f"Metadata: {str(metadata)}")

    context = "\n".join(context_parts) if context_parts else None

    # Convert file strings to Path objects if needed
    from pathlib import Path

    file_paths = [Path(f) if isinstance(f, str) else f for f in (files or [])]

    complexity = estimator.estimate(
        task_description=task_description,
        files=file_paths,
        context=context,
    )

    return complexity


def select_model_for_task(
    selector: ModelSelector,
    complexity: TaskComplexity,
    override_model: Optional[str] = None,
) -> ModelSelection:
    """
    Select appropriate model for a task based on complexity.

    Args:
        selector: ModelSelector instance
        complexity: TaskComplexity from estimation
        override_model: Optional model override

    Returns:
        ModelSelection with selected model and reasoning
    """
    selection = selector.select(
        complexity=complexity,
        override_model=override_model,
    )

    return selection


def track_model_cost(
    cost_tracker: Optional[CostTracker],
    model_name: str,
    input_tokens: int,
    output_tokens: int,
    task_id: Optional[str] = None,
    metadata: Optional[Dict[str, Any]] = None,
) -> Optional[CostEntry]:
    """
    Track cost of model usage.

    Args:
        cost_tracker: CostTracker instance (can be None)
        model_name: Name of the model used
        input_tokens: Number of input tokens
        output_tokens: Number of output tokens
        task_id: Optional task identifier
        metadata: Additional metadata

    Returns:
        CostEntry if cost_tracker is enabled, None otherwise
    """
    if not cost_tracker:
        return None

    entry = cost_tracker.track_usage(
        model_name=model_name,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        task_id=task_id,
        metadata=metadata or {},
    )

    return entry


def get_routing_recommendations(
    estimator: ComplexityEstimator,
    selector: ModelSelector,
    tasks: List[Dict[str, Any]],
) -> List[Dict[str, Any]]:
    """
    Get model recommendations for a list of tasks.

    Args:
        estimator: ComplexityEstimator instance
        selector: ModelSelector instance
        tasks: List of task dictionaries

    Returns:
        List of recommendations with task_id, complexity, and selected_model
    """
    recommendations = []

    for task in tasks:
        task_id = task.get("id", "unknown")
        description = task.get("description", "")
        files = task.get("files", [])
        requirements = task.get("requirements", [])

        # Estimate complexity
        complexity = estimate_task_complexity(
            estimator,
            task_description=description,
            files=files,
            requirements=requirements,
        )

        # Select model
        selection = select_model_for_task(selector, complexity)

        recommendations.append(
            {
                "task_id": task_id,
                "complexity_level": complexity.level.value,
                "complexity_score": complexity.score,
                "selected_model": selection.model.name,
                "model_tier": selection.model.tier.value,
                "reasoning": selection.reason,
            }
        )

    return recommendations


def optimize_batch_routing(
    estimator: ComplexityEstimator,
    selector: ModelSelector,
    tasks: List[Dict[str, Any]],
    cost_limit: Optional[float] = None,
) -> Dict[str, Any]:
    """
    Optimize model routing for a batch of tasks.

    Groups tasks by recommended model tier to enable batch processing.

    Args:
        estimator: ComplexityEstimator instance
        selector: ModelSelector instance
        tasks: List of tasks
        cost_limit: Optional cost limit for the batch

    Returns:
        Dictionary with optimized routing plan
    """
    recommendations = get_routing_recommendations(estimator, selector, tasks)

    # Group by model tier
    by_tier = {}
    for rec in recommendations:
        tier = rec["model_tier"]
        if tier not in by_tier:
            by_tier[tier] = []
        by_tier[tier].append(rec)

    # Calculate estimated costs
    total_estimated_cost = 0.0
    tier_costs = {}

    for tier, tier_tasks in by_tier.items():
        # Rough cost estimation
        tier_cost = len(tier_tasks) * _estimate_tier_cost(tier)
        tier_costs[tier] = tier_cost
        total_estimated_cost += tier_cost

    # Check if within cost limit
    within_budget = True
    if cost_limit and total_estimated_cost > cost_limit:
        within_budget = False

    return {
        "recommendations": recommendations,
        "by_tier": by_tier,
        "tier_counts": {tier: len(tasks) for tier, tasks in by_tier.items()},
        "tier_costs": tier_costs,
        "total_estimated_cost": total_estimated_cost,
        "within_budget": within_budget,
        "cost_limit": cost_limit,
    }


def _estimate_tier_cost(tier: str) -> float:
    """Estimate cost per task for a model tier."""
    tier_costs = {
        "haiku": 0.01,
        "sonnet": 0.05,
        "opus": 0.15,
    }
    return tier_costs.get(tier, 0.05)


def get_routing_summary(cost_tracker: Optional[CostTracker]) -> Dict[str, Any]:
    """
    Get summary of routing and costs.

    Args:
        cost_tracker: CostTracker instance (can be None)

    Returns:
        Dictionary with routing statistics
    """
    if not cost_tracker:
        return {
            "cost_tracking_enabled": False,
            "total_cost": 0.0,
            "total_requests": 0,
        }

    summary = cost_tracker.get_summary()

    return {
        "cost_tracking_enabled": True,
        "total_cost": summary.total_cost,
        "total_requests": summary.request_count,
        "total_input_tokens": summary.total_input_tokens,
        "total_output_tokens": summary.total_output_tokens,
        "average_cost_per_request": summary.average_cost,
        "by_model": summary.by_model,
    }
