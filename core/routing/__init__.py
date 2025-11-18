"""
Model Routing System for BuildRunner 3.1

This module provides intelligent model selection and routing:
- Complexity estimation for tasks
- Model selection based on task requirements
- Cost tracking and optimization
- Fallback handling for model failures
"""

from .complexity_estimator import ComplexityEstimator, ComplexityLevel, TaskComplexity
from .model_selector import ModelSelector, ModelConfig, ModelSelection, ModelTier
from .cost_tracker import CostTracker, CostEntry, CostSummary
from .fallback_handler import FallbackHandler, FallbackStrategy, FailureReason, FailureEvent

__all__ = [
    'ComplexityEstimator',
    'ComplexityLevel',
    'TaskComplexity',
    'ModelSelector',
    'ModelConfig',
    'ModelSelection',
    'ModelTier',
    'CostTracker',
    'CostEntry',
    'CostSummary',
    'FallbackHandler',
    'FallbackStrategy',
    'FailureReason',
    'FailureEvent',
]
