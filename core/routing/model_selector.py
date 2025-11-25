"""
Model Selector - Chooses appropriate model based on task complexity and constraints

Selects from available models based on:
- Task complexity level
- Cost constraints
- Availability and rate limits
- Performance requirements
- Fallback options
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional
from .complexity_estimator import ComplexityLevel, TaskComplexity


class ModelTier(str, Enum):
    """Model tier classification."""

    FAST = "fast"  # Haiku - fast, cheap
    BALANCED = "balanced"  # Sonnet - balanced performance/cost
    ADVANCED = "advanced"  # Opus - best quality, expensive


@dataclass
class ModelConfig:
    """Configuration for a model."""

    name: str
    provider: str  # "anthropic", "openai", etc.
    tier: ModelTier

    # Capabilities
    max_tokens: int
    context_window: int
    supports_streaming: bool = True
    supports_vision: bool = False
    supports_function_calling: bool = True

    # Performance
    avg_latency_ms: float = 0.0
    tokens_per_second: float = 0.0

    # Cost (USD per 1M tokens)
    input_cost_per_1m: float = 0.0
    output_cost_per_1m: float = 0.0

    # Availability
    is_available: bool = True
    rate_limit_rpm: int = 50  # Requests per minute
    rate_limit_tpm: int = 100000  # Tokens per minute

    # Metadata
    model_id: str = ""  # Full model ID (e.g., "claude-sonnet-4-5-20250929")
    version: str = ""


@dataclass
class ModelSelection:
    """Result of model selection."""

    model: ModelConfig
    reason: str
    complexity: TaskComplexity
    alternatives: List[ModelConfig] = field(default_factory=list)
    estimated_cost: float = 0.0  # USD
    timestamp: datetime = field(default_factory=datetime.now)


class ModelSelector:
    """Selects appropriate model based on task requirements."""

    # Default model configurations
    DEFAULT_MODELS = {
        "haiku": ModelConfig(
            name="haiku",
            provider="anthropic",
            tier=ModelTier.FAST,
            max_tokens=4096,
            context_window=200000,
            avg_latency_ms=500,
            tokens_per_second=100,
            input_cost_per_1m=0.25,
            output_cost_per_1m=1.25,
            rate_limit_rpm=50,
            rate_limit_tpm=100000,
            model_id="claude-haiku-3-5-20241022",
            version="3.5",
        ),
        "sonnet": ModelConfig(
            name="sonnet",
            provider="anthropic",
            tier=ModelTier.BALANCED,
            max_tokens=8192,
            context_window=200000,
            avg_latency_ms=1000,
            tokens_per_second=75,
            input_cost_per_1m=3.0,
            output_cost_per_1m=15.0,
            rate_limit_rpm=50,
            rate_limit_tpm=100000,
            model_id="claude-sonnet-4-5-20250929",
            version="4.5",
        ),
        "opus": ModelConfig(
            name="opus",
            provider="anthropic",
            tier=ModelTier.ADVANCED,
            max_tokens=8192,
            context_window=200000,
            avg_latency_ms=2000,
            tokens_per_second=50,
            input_cost_per_1m=15.0,
            output_cost_per_1m=75.0,
            rate_limit_rpm=50,
            rate_limit_tpm=100000,
            model_id="claude-opus-4-20250514",
            version="4.0",
        ),
    }

    def __init__(
        self,
        models: Optional[Dict[str, ModelConfig]] = None,
        cost_threshold: Optional[float] = None,
        prefer_speed: bool = False,
    ):
        """
        Initialize model selector.

        Args:
            models: Custom model configurations (uses defaults if None)
            cost_threshold: Maximum cost per task in USD
            prefer_speed: Prefer faster models when quality is comparable
        """
        self.models = models or self.DEFAULT_MODELS.copy()
        self.cost_threshold = cost_threshold
        self.prefer_speed = prefer_speed
        self.selection_history: List[ModelSelection] = []

    def select(
        self,
        complexity: TaskComplexity,
        override_model: Optional[str] = None,
    ) -> ModelSelection:
        """
        Select best model for the task.

        Args:
            complexity: Task complexity analysis
            override_model: Force specific model (for testing/debugging)

        Returns:
            ModelSelection with chosen model and reasoning
        """
        # Handle override
        if override_model:
            if override_model not in self.models:
                raise ValueError(f"Unknown model: {override_model}")

            model = self.models[override_model]
            selection = ModelSelection(
                model=model,
                reason=f"User override: {override_model}",
                complexity=complexity,
                estimated_cost=self._estimate_cost(model, complexity),
            )
            self.selection_history.append(selection)
            return selection

        # Select based on complexity level
        if complexity.level == ComplexityLevel.SIMPLE:
            primary = "haiku"
            alternatives = ["sonnet"]
            reason = "Simple task - using fast model"

        elif complexity.level == ComplexityLevel.MODERATE:
            primary = "sonnet"
            alternatives = ["haiku", "opus"]
            reason = "Moderate complexity - using balanced model"

        elif complexity.level == ComplexityLevel.COMPLEX:
            primary = "opus"
            alternatives = ["sonnet"]
            reason = "Complex task - using advanced model"

        else:  # CRITICAL
            primary = "opus"
            alternatives = ["sonnet"]
            reason = "Critical task - using best available model"

        # Get primary model
        model = self.models.get(primary)
        if not model:
            raise ValueError(f"Model not configured: {primary}")

        # Check availability
        if not model.is_available:
            # Try alternatives
            for alt_name in alternatives:
                alt_model = self.models.get(alt_name)
                if alt_model and alt_model.is_available:
                    model = alt_model
                    reason = f"Primary model unavailable - using {alt_name}"
                    break
            else:
                raise RuntimeError("No models available")

        # Check cost threshold
        estimated_cost = self._estimate_cost(model, complexity)
        if self.cost_threshold and estimated_cost > self.cost_threshold:
            # Try cheaper alternatives
            for alt_name in alternatives:
                alt_model = self.models.get(alt_name)
                if not alt_model or not alt_model.is_available:
                    continue

                alt_cost = self._estimate_cost(alt_model, complexity)
                if alt_cost <= self.cost_threshold:
                    model = alt_model
                    estimated_cost = alt_cost
                    reason = f"Cost optimization - using {alt_name} (${alt_cost:.4f})"
                    break

        # Check if task requires more tokens than model supports
        if complexity.estimated_tokens > model.max_tokens:
            # Need to upgrade to larger context model
            if primary != "opus":
                model = self.models["opus"]
                reason = "Large context requirement - upgrading to Opus"

        # Build alternative list
        alternative_models = [
            self.models[name]
            for name in alternatives
            if name in self.models and self.models[name].is_available
        ]

        selection = ModelSelection(
            model=model,
            reason=reason,
            complexity=complexity,
            alternatives=alternative_models,
            estimated_cost=estimated_cost,
        )

        self.selection_history.append(selection)
        return selection

    def _estimate_cost(self, model: ModelConfig, complexity: TaskComplexity) -> float:
        """
        Estimate cost for running task on model.

        Args:
            model: Model configuration
            complexity: Task complexity

        Returns:
            Estimated cost in USD
        """
        # Estimate input tokens (context + prompt)
        input_tokens = complexity.estimated_tokens + 500  # +500 for system prompt

        # Estimate output tokens (rough heuristic: 20% of input for code tasks)
        output_tokens = int(input_tokens * 0.2)

        # Calculate cost
        input_cost = (input_tokens / 1_000_000) * model.input_cost_per_1m
        output_cost = (output_tokens / 1_000_000) * model.output_cost_per_1m

        return input_cost + output_cost

    def get_model(self, name: str) -> Optional[ModelConfig]:
        """
        Get model configuration by name.

        Args:
            name: Model name

        Returns:
            ModelConfig or None
        """
        return self.models.get(name)

    def list_models(self, available_only: bool = False) -> List[ModelConfig]:
        """
        List all configured models.

        Args:
            available_only: Only return available models

        Returns:
            List of ModelConfig
        """
        models = list(self.models.values())
        if available_only:
            models = [m for m in models if m.is_available]
        return models

    def update_model_availability(self, model_name: str, is_available: bool):
        """
        Update model availability status.

        Args:
            model_name: Name of the model
            is_available: Availability status
        """
        if model_name in self.models:
            self.models[model_name].is_available = is_available

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics on model selections.

        Returns:
            Statistics dictionary
        """
        if not self.selection_history:
            return {
                "total_selections": 0,
                "model_distribution": {},
                "total_estimated_cost": 0.0,
                "avg_cost_per_task": 0.0,
            }

        total = len(self.selection_history)

        # Count by model
        model_dist = {}
        for selection in self.selection_history:
            name = selection.model.name
            model_dist[name] = model_dist.get(name, 0) + 1

        total_cost = sum(s.estimated_cost for s in self.selection_history)

        return {
            "total_selections": total,
            "model_distribution": model_dist,
            "total_estimated_cost": total_cost,
            "avg_cost_per_task": total_cost / total if total > 0 else 0.0,
            "selections_by_complexity": {
                level.value: sum(1 for s in self.selection_history if s.complexity.level == level)
                for level in ComplexityLevel
            },
        }
