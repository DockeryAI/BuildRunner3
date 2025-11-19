"""
Claude Agent Bridge Module

Provides integration between BuildRunner tasks and Claude Code's native `/agent` command.
Handles agent dispatch, response parsing, and telemetry tracking.
"""

from core.agents.claude_agent_bridge import (
    ClaudeAgentBridge,
    AgentType,
    AgentStatus,
    AgentResponse,
    AgentAssignment,
    AgentError,
    AgentDispatchError,
    AgentTimeoutError,
    AgentParseError,
)

from core.agents.chains import (
    AgentChain,
    ParallelAgentPool,
    WorkflowTemplates,
    WorkflowStatus,
    WorkflowPhase,
    AgentWorkItem,
    WorkflowCheckpoint,
)

from core.agents.aggregator import (
    ResultAggregator,
    AggregatedResult,
    ConflictStrategy,
)

from core.agents.metrics import (
    AgentMetrics,
    AgentMetric,
    AgentPerformanceSummary,
    ModelType,
    MODEL_PRICING,
)

from core.agents.recommender import (
    AgentRecommender,
    AgentRecommendation,
    TaskComplexity,
)

__all__ = [
    # Bridge classes
    "ClaudeAgentBridge",
    "AgentType",
    "AgentStatus",
    "AgentResponse",
    "AgentAssignment",
    "AgentError",
    "AgentDispatchError",
    "AgentTimeoutError",
    "AgentParseError",
    # Chain classes
    "AgentChain",
    "ParallelAgentPool",
    "WorkflowTemplates",
    "WorkflowStatus",
    "WorkflowPhase",
    "AgentWorkItem",
    "WorkflowCheckpoint",
    # Aggregator classes
    "ResultAggregator",
    "AggregatedResult",
    "ConflictStrategy",
    # Metrics classes
    "AgentMetrics",
    "AgentMetric",
    "AgentPerformanceSummary",
    "ModelType",
    "MODEL_PRICING",
    # Recommender classes
    "AgentRecommender",
    "AgentRecommendation",
    "TaskComplexity",
]
