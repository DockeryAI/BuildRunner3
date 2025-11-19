"""
Agent Recommender - Recommends optimal agent type and model for tasks

Features:
- Task analysis to determine best agent type
- Model selection based on complexity and cost
- Historical performance-based recommendations
- Task complexity classification
- Fallback recommendations
"""

from dataclasses import dataclass, field
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Tuple
import logging
import re

from core.agents.metrics import AgentMetrics, AgentMetric, ModelType, MODEL_PRICING
from core.agents.claude_agent_bridge import AgentType

logger = logging.getLogger(__name__)


class TaskComplexity(str, Enum):
    """Task complexity classification."""
    SIMPLE = "simple"          # 60 minutes, straightforward tasks
    MEDIUM = "medium"          # 90 minutes, moderate complexity
    COMPLEX = "complex"        # 120+ minutes, difficult tasks


@dataclass
class AgentRecommendation:
    """Recommendation for agent assignment."""

    recommended_agent_type: str  # explore, test, review, refactor, implement
    recommended_model: str  # Model ID
    confidence: float  # 0.0 to 1.0

    # Reasoning
    reason: str
    supporting_metrics: Dict = field(default_factory=dict)

    # Alternatives
    alternative_agents: List[str] = field(default_factory=list)
    alternative_models: List[str] = field(default_factory=list)

    # Performance expectations
    expected_duration_ms: float = 0.0
    expected_cost_usd: float = 0.0
    expected_success_rate: float = 0.0

    timestamp: datetime = field(default_factory=datetime.now)

    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'recommended_agent_type': self.recommended_agent_type,
            'recommended_model': self.recommended_model,
            'confidence': self.confidence,
            'reason': self.reason,
            'supporting_metrics': self.supporting_metrics,
            'alternative_agents': self.alternative_agents,
            'alternative_models': self.alternative_models,
            'expected_duration_ms': self.expected_duration_ms,
            'expected_cost_usd': self.expected_cost_usd,
            'expected_success_rate': self.expected_success_rate,
            'timestamp': self.timestamp.isoformat(),
        }


class AgentRecommender:
    """Recommends optimal agent type and model for tasks."""

    # Task keywords for agent type detection
    AGENT_TYPE_KEYWORDS = {
        AgentType.EXPLORE.value: [
            'explore', 'understand', 'investigate', 'research',
            'discover', 'examine', 'scan', 'map', 'diagram', 'discover'
        ],
        AgentType.TEST.value: [
            'test', 'testing', 'unit test', 'integration test', 'e2e test',
            'verify', 'validation', 'coverage', 'debug', 'benchmark', 'load test'
        ],
        AgentType.REVIEW.value: [
            'review', 'code review', 'analysis', 'quality', 'performance',
            'security', 'best practice', 'lint', 'static analysis', 'audit'
        ],
        AgentType.REFACTOR.value: [
            'refactor', 'improve', 'optimize', 'cleanup', 'simplify',
            'restructure', 'rewrite', 'efficiency', 'maintainability'
        ],
        AgentType.IMPLEMENT.value: [
            'implement', 'build', 'create', 'add', 'feature', 'functionality',
            'write', 'develop', 'code', 'script', 'module', 'component'
        ],
    }

    # Task patterns that indicate complexity
    SIMPLE_PATTERNS = [
        r'simple',
        r'straightforward',
        r'easy',
        r'basic',
        r'single',
        r'one\s+file',
        r'small',
    ]

    COMPLEX_PATTERNS = [
        r'complex',
        r'difficult',
        r'multiple',
        r'integration',
        r'architecture',
        r'system',
        r'large',
        r'refactor',
        r'rewrite',
    ]

    def __init__(self, metrics: Optional[AgentMetrics] = None):
        """
        Initialize agent recommender.

        Args:
            metrics: AgentMetrics instance for historical analysis.
                    If None, creates a new instance.
        """
        self.metrics = metrics or AgentMetrics()

    def analyze_task(self, task_description: str) -> AgentRecommendation:
        """
        Analyze a task and recommend agent type and model.

        Args:
            task_description: Description of the task to be performed

        Returns:
            AgentRecommendation with suggested agent, model, and reasoning
        """
        # Classify complexity
        complexity = self._classify_complexity(task_description)

        # Detect agent type from keywords
        agent_type = self._detect_agent_type(task_description)

        # Get best model for this agent type
        model = self.get_best_model(agent_type, complexity)

        # Get performance expectations from historical data
        summary = self.metrics.get_summary(agent_type, time_period_days=30)

        expected_duration = 0.0
        expected_cost = 0.0
        expected_success_rate = 0.0
        confidence = 0.5

        if summary:
            expected_duration = summary.avg_duration_ms
            expected_cost = summary.avg_cost_per_task
            expected_success_rate = summary.success_rate
            confidence = min(0.95, 0.5 + (summary.success_rate * 0.4))
        else:
            # Use defaults based on complexity
            if complexity == TaskComplexity.SIMPLE:
                expected_duration = 300000  # 5 minutes
                confidence = 0.6
            elif complexity == TaskComplexity.MEDIUM:
                expected_duration = 600000  # 10 minutes
                confidence = 0.65
            else:
                expected_duration = 1200000  # 20 minutes
                confidence = 0.55

            # Estimate cost based on model and expected tokens
            expected_cost = self._estimate_cost(model, expected_duration)

        # Get alternatives
        alternative_agents = self._get_alternative_agents(agent_type, complexity)
        alternative_models = self._get_alternative_models(model, complexity)

        reason = self._generate_recommendation_reason(
            agent_type, model, complexity, summary
        )

        recommendation = AgentRecommendation(
            recommended_agent_type=agent_type,
            recommended_model=model,
            confidence=confidence,
            reason=reason,
            supporting_metrics={
                'complexity': complexity.value,
                'agent_keywords_match': self._get_keyword_matches(task_description, agent_type),
                'historical_success_rate': expected_success_rate,
            },
            alternative_agents=alternative_agents,
            alternative_models=alternative_models,
            expected_duration_ms=expected_duration,
            expected_cost_usd=expected_cost,
            expected_success_rate=expected_success_rate,
        )

        logger.info(f"Recommended {agent_type} agent with {model} "
                   f"for task: {task_description[:100]}")

        return recommendation

    def get_best_model(self, agent_type: str, task_complexity: TaskComplexity) -> str:
        """
        Get best model for a specific agent type and task complexity.

        Args:
            agent_type: Type of agent (explore, test, review, refactor, implement)
            task_complexity: Complexity of the task (simple, medium, complex)

        Returns:
            Model ID (e.g., "claude-sonnet-4-5-20250929")
        """
        # First, check if we have historical data for this agent type
        best_model = self.metrics.get_best_model_for_agent_type(agent_type)

        if best_model:
            return best_model

        # If no historical data, use heuristics
        if task_complexity == TaskComplexity.SIMPLE:
            return ModelType.HAIKU.value
        elif task_complexity == TaskComplexity.MEDIUM:
            return ModelType.SONNET.value
        else:
            return ModelType.OPUS.value

    def get_model_by_constraints(
        self,
        agent_type: str,
        task_complexity: TaskComplexity,
        max_cost_per_task: Optional[float] = None,
        prefer_speed: bool = False,
    ) -> str:
        """
        Get model based on constraints.

        Args:
            agent_type: Type of agent
            task_complexity: Task complexity
            max_cost_per_task: Maximum budget for this task (USD)
            prefer_speed: If True, prefer faster models even if more expensive

        Returns:
            Model ID
        """
        if max_cost_per_task is None:
            return self.get_best_model(agent_type, task_complexity)

        # Start with best model
        best_model = self.get_best_model(agent_type, task_complexity)

        # Check if it meets cost constraint
        estimated_cost = self._estimate_cost(best_model, 600000)  # Assume 10 min
        if estimated_cost <= max_cost_per_task:
            return best_model

        # If cost too high, try cheaper models
        if prefer_speed:
            # Prefer Sonnet over Haiku even if cheaper
            model_options = [ModelType.SONNET.value, ModelType.HAIKU.value]
        else:
            model_options = [ModelType.HAIKU.value, ModelType.SONNET.value]

        for model in model_options:
            estimated_cost = self._estimate_cost(model, 600000)
            if estimated_cost <= max_cost_per_task:
                return model

        # If still too expensive, use cheapest option
        return ModelType.HAIKU.value

    def _classify_complexity(self, task_description: str) -> TaskComplexity:
        """Classify task complexity from description."""
        description_lower = task_description.lower()

        # Check for explicit complexity patterns
        simple_score = sum(
            1 for pattern in self.SIMPLE_PATTERNS
            if re.search(pattern, description_lower, re.IGNORECASE)
        )
        complex_score = sum(
            1 for pattern in self.COMPLEX_PATTERNS
            if re.search(pattern, description_lower, re.IGNORECASE)
        )

        if complex_score > simple_score:
            return TaskComplexity.COMPLEX
        elif simple_score > 0:
            return TaskComplexity.SIMPLE

        # Check keyword count and description length
        words = task_description.split()
        if len(words) < 10:
            return TaskComplexity.SIMPLE
        elif len(words) < 30:
            return TaskComplexity.MEDIUM
        else:
            return TaskComplexity.COMPLEX

    def _detect_agent_type(self, task_description: str) -> str:
        """Detect agent type from task description."""
        description_lower = task_description.lower()

        # Score each agent type
        agent_scores = {}
        for agent_type, keywords in self.AGENT_TYPE_KEYWORDS.items():
            score = sum(
                1 for keyword in keywords
                if keyword in description_lower
            )
            agent_scores[agent_type] = score

        # Return agent type with highest score
        if max(agent_scores.values()) > 0:
            return max(agent_scores, key=agent_scores.get)

        # Default to implement if no keywords match
        return AgentType.IMPLEMENT.value

    def _get_keyword_matches(self, task_description: str, agent_type: str) -> int:
        """Count keyword matches for an agent type."""
        keywords = self.AGENT_TYPE_KEYWORDS.get(agent_type, [])
        description_lower = task_description.lower()

        return sum(
            1 for keyword in keywords
            if keyword in description_lower
        )

    def _get_alternative_agents(
        self,
        primary_agent: str,
        complexity: TaskComplexity
    ) -> List[str]:
        """Get alternative agent types for a task."""
        all_agents = [at.value for at in AgentType]
        alternatives = [a for a in all_agents if a != primary_agent]

        # For complex tasks, suggest multiple alternatives
        if complexity == TaskComplexity.COMPLEX:
            return alternatives[:3]
        else:
            return alternatives[:2]

    def _get_alternative_models(
        self,
        primary_model: str,
        complexity: TaskComplexity
    ) -> List[str]:
        """Get alternative models for a task."""
        all_models = [ModelType.HAIKU.value, ModelType.SONNET.value, ModelType.OPUS.value]
        alternatives = [m for m in all_models if m != primary_model]

        return alternatives

    def _estimate_cost(self, model: str, duration_ms: float) -> float:
        """
        Estimate cost for a task.

        Args:
            model: Model ID
            duration_ms: Expected duration in milliseconds

        Returns:
            Estimated cost in USD
        """
        # Estimate tokens based on duration
        # Assumption: ~100 tokens per second of execution
        duration_seconds = duration_ms / 1000
        estimated_tokens = max(500, min(100000, int(duration_seconds * 100)))

        # Assume 70% input, 30% output
        input_tokens = int(estimated_tokens * 0.7)
        output_tokens = int(estimated_tokens * 0.3)

        # Get model type
        model_type = self._get_model_type(model)

        if model_type not in MODEL_PRICING:
            return 0.01  # Default small cost

        pricing = MODEL_PRICING[model_type]
        input_cost = (input_tokens / 1_000_000) * pricing["input"]
        output_cost = (output_tokens / 1_000_000) * pricing["output"]

        return input_cost + output_cost

    @staticmethod
    def _get_model_type(model_str: str) -> ModelType:
        """Determine model type from model string."""
        if "haiku" in model_str.lower():
            return ModelType.HAIKU
        elif "sonnet" in model_str.lower():
            return ModelType.SONNET
        elif "opus" in model_str.lower():
            return ModelType.OPUS
        else:
            return ModelType.SONNET

    def _generate_recommendation_reason(
        self,
        agent_type: str,
        model: str,
        complexity: TaskComplexity,
        summary: Optional[Dict]
    ) -> str:
        """Generate explanation for recommendation."""
        reason = f"Recommended {agent_type} agent with {self._get_model_name(model)} "
        reason += f"for {complexity.value} complexity task. "

        if summary:
            reason += (f"Historical success rate for this agent type is "
                      f"{summary.success_rate:.1%} based on {summary.total_tasks} tasks.")
        else:
            reason += ("No historical data available. Selection based on task "
                      "keywords and complexity analysis.")

        return reason

    @staticmethod
    def _get_model_name(model_id: str) -> str:
        """Get human-readable model name."""
        if "haiku" in model_id.lower():
            return "Haiku"
        elif "sonnet" in model_id.lower():
            return "Sonnet"
        elif "opus" in model_id.lower():
            return "Opus"
        else:
            return "Unknown"

    def recommend_batch_agents(
        self,
        tasks: List[Dict]
    ) -> List[AgentRecommendation]:
        """
        Recommend agents for a batch of tasks.

        Args:
            tasks: List of task dicts with 'description' and optional 'complexity'

        Returns:
            List of AgentRecommendation objects
        """
        recommendations = []

        for task in tasks:
            description = task.get('description', '')
            if not description:
                continue

            recommendation = self.analyze_task(description)
            recommendations.append(recommendation)

        return recommendations

    def get_recommendations_summary(self) -> Dict:
        """Get summary of recommendations and their accuracy."""
        summary = {
            'total_recommendations': 0,
            'successful_recommendations': 0,
            'failed_recommendations': 0,
            'accuracy_rate': 0.0,
            'by_agent_type': {},
        }

        # Count successful vs failed recommendations
        agent_summaries = self.metrics.get_agent_types_summary(time_period_days=30)

        for agent_type, agent_summary in agent_summaries.items():
            summary['total_recommendations'] += agent_summary.total_tasks
            summary['successful_recommendations'] += agent_summary.successful_tasks
            summary['failed_recommendations'] += agent_summary.failed_tasks

            summary['by_agent_type'][agent_type] = {
                'success_rate': agent_summary.success_rate,
                'total_tasks': agent_summary.total_tasks,
                'avg_cost': agent_summary.avg_cost_per_task,
            }

        if summary['total_recommendations'] > 0:
            summary['accuracy_rate'] = (
                summary['successful_recommendations'] /
                summary['total_recommendations']
            )

        return summary
