"""
Complexity Estimator - Analyzes tasks to determine model requirements

Estimates task complexity based on:
- Lines of code to analyze
- Number of files involved
- Task type (refactor, new feature, bug fix, etc.)
- Context requirements
- Language and framework complexity
"""

from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Dict, List, Optional, Set
import re


class ComplexityLevel(str, Enum):
    """Task complexity levels mapped to model capabilities."""

    SIMPLE = "simple"  # Haiku - straightforward tasks
    MODERATE = "moderate"  # Sonnet - standard development
    COMPLEX = "complex"  # Opus - advanced reasoning
    CRITICAL = "critical"  # Opus - critical/sensitive tasks


@dataclass
class TaskComplexity:
    """Complexity analysis result for a task."""

    level: ComplexityLevel
    score: float  # 0-100 complexity score
    reasons: List[str]
    file_count: int = 0
    line_count: int = 0
    context_size: int = 0
    task_type: str = "unknown"

    # Complexity factors
    has_architecture_changes: bool = False
    has_security_implications: bool = False
    has_performance_requirements: bool = False
    has_concurrency: bool = False
    requires_deep_reasoning: bool = False

    # Recommendations
    recommended_model: str = "sonnet"
    estimated_tokens: int = 0


class ComplexityEstimator:
    """Estimates task complexity to determine appropriate model selection."""

    # Complexity thresholds
    SIMPLE_THRESHOLD = 25
    MODERATE_THRESHOLD = 50
    COMPLEX_THRESHOLD = 75

    # Line count thresholds
    SIMPLE_LINES = 50
    MODERATE_LINES = 200
    COMPLEX_LINES = 500

    # File count thresholds
    SIMPLE_FILES = 2
    MODERATE_FILES = 5
    COMPLEX_FILES = 10

    # Keywords that indicate complexity
    COMPLEX_KEYWORDS = {
        "architecture",
        "refactor",
        "redesign",
        "migration",
        "upgrade",
        "performance",
        "optimization",
        "scale",
        "distributed",
        "concurrent",
        "security",
        "authentication",
        "authorization",
        "encryption",
        "database",
        "schema",
        "migration",
        "transaction",
        "async",
        "parallel",
        "threading",
        "multiprocess",
        "algorithm",
        "optimization",
        "complexity",
        "efficiency",
    }

    SIMPLE_KEYWORDS = {
        "typo",
        "rename",
        "format",
        "style",
        "comment",
        "documentation",
        "logging",
        "print",
        "simple",
        "trivial",
        "minor",
    }

    # Critical task patterns
    CRITICAL_PATTERNS = [
        r"security.*fix",
        r"production.*issue",
        r"critical.*bug",
        r"data.*loss",
        r"breach",
        r"vulnerability",
    ]

    def __init__(self):
        """Initialize complexity estimator with heuristic-based analysis."""
        self.task_history: List[TaskComplexity] = []

    def estimate(
        self,
        task_description: str,
        files: Optional[List[Path]] = None,
        context: Optional[str] = None,
    ) -> TaskComplexity:
        """
        Estimate task complexity using heuristic analysis.

        Args:
            task_description: Description of the task
            files: Files involved in the task
            context: Additional context (code snippets, specs, etc.)

        Returns:
            TaskComplexity with estimated level and details
        """
        files = files or []
        context = context or ""

        # Initialize complexity tracking
        score = 0.0
        reasons = []

        # Analyze task description
        desc_lower = task_description.lower()

        # Check for critical patterns
        is_critical = any(re.search(pattern, desc_lower) for pattern in self.CRITICAL_PATTERNS)

        if is_critical:
            score += 80
            reasons.append("Critical/security-sensitive task")

        # Analyze keywords
        complex_count = sum(1 for kw in self.COMPLEX_KEYWORDS if kw in desc_lower)
        simple_count = sum(1 for kw in self.SIMPLE_KEYWORDS if kw in desc_lower)

        if complex_count > 2:
            score += 30
            reasons.append(f"Contains {complex_count} complexity keywords")
        elif simple_count > 0:
            score -= 10
            reasons.append("Contains simplicity keywords")

        # Analyze file count
        file_count = len(files)
        if file_count == 0:
            # No files specified - assume moderate
            score += 25
        elif file_count > self.COMPLEX_FILES:
            score += 40
            reasons.append(f"High file count ({file_count} files)")
        elif file_count > self.MODERATE_FILES:
            score += 25
            reasons.append(f"Moderate file count ({file_count} files)")
        elif file_count <= self.SIMPLE_FILES:
            score += 5
            reasons.append(f"Low file count ({file_count} files)")

        # Analyze lines of code
        line_count = self._count_lines(files)
        if line_count > self.COMPLEX_LINES:
            score += 30
            reasons.append(f"Large code change ({line_count} lines)")
        elif line_count > self.MODERATE_LINES:
            score += 15
            reasons.append(f"Moderate code change ({line_count} lines)")
        elif line_count > 0 and line_count <= self.SIMPLE_LINES:
            score += 5
            reasons.append(f"Small code change ({line_count} lines)")

        # Analyze context size
        context_size = len(context)
        estimated_tokens = context_size // 4  # Rough estimate: 4 chars per token

        if context_size > 20000:
            score += 20
            reasons.append("Large context requirement")
        elif context_size > 10000:
            score += 10
            reasons.append("Moderate context requirement")

        # Detect complexity factors
        has_architecture = any(
            kw in desc_lower for kw in ["architecture", "design", "refactor", "redesign"]
        )
        has_security = any(
            kw in desc_lower for kw in ["security", "auth", "encryption", "credential"]
        )
        has_performance = any(
            kw in desc_lower for kw in ["performance", "optimize", "slow", "bottleneck"]
        )
        has_concurrency = any(
            kw in desc_lower for kw in ["async", "concurrent", "parallel", "thread"]
        )
        requires_reasoning = any(
            kw in desc_lower for kw in ["algorithm", "complex", "solve", "design"]
        )

        if has_architecture:
            score += 20
            reasons.append("Involves architecture changes")
        if has_security:
            score += 25
            reasons.append("Has security implications")
        if has_performance:
            score += 15
            reasons.append("Performance requirements")
        if has_concurrency:
            score += 20
            reasons.append("Involves concurrency")
        if requires_reasoning:
            score += 15
            reasons.append("Requires deep reasoning")

        # Determine task type
        task_type = self._classify_task_type(desc_lower)

        # Calculate complexity level
        if is_critical or score >= self.COMPLEX_THRESHOLD:
            level = ComplexityLevel.CRITICAL if is_critical else ComplexityLevel.COMPLEX
            recommended_model = "opus"
        elif score >= self.MODERATE_THRESHOLD:
            level = ComplexityLevel.MODERATE
            recommended_model = "sonnet"
        else:
            level = ComplexityLevel.SIMPLE
            recommended_model = "haiku"

        # Cap score at 100
        score = min(100.0, score)

        complexity = TaskComplexity(
            level=level,
            score=score,
            reasons=reasons,
            file_count=file_count,
            line_count=line_count,
            context_size=context_size,
            task_type=task_type,
            has_architecture_changes=has_architecture,
            has_security_implications=has_security,
            has_performance_requirements=has_performance,
            has_concurrency=has_concurrency,
            requires_deep_reasoning=requires_reasoning,
            recommended_model=recommended_model,
            estimated_tokens=estimated_tokens,
        )

        # Store in history
        self.task_history.append(complexity)

        return complexity

    def _count_lines(self, files: List[Path]) -> int:
        """
        Count total lines in files.

        Args:
            files: List of file paths

        Returns:
            Total line count
        """
        total = 0
        for file_path in files:
            try:
                if file_path.exists():
                    with open(file_path, "r", encoding="utf-8") as f:
                        total += len(f.readlines())
            except Exception:
                # If we can't read the file, assume moderate size
                total += 100

        return total

    def _classify_task_type(self, description: str) -> str:
        """
        Classify task type based on description.

        Args:
            description: Task description (lowercase)

        Returns:
            Task type classification
        """
        if any(kw in description for kw in ["fix", "bug", "error", "issue"]):
            return "bug_fix"
        elif any(kw in description for kw in ["refactor", "cleanup", "improve"]):
            return "refactor"
        elif any(kw in description for kw in ["test", "coverage", "spec"]):
            return "testing"
        elif any(kw in description for kw in ["document", "comment", "readme"]):
            return "documentation"
        elif any(kw in description for kw in ["add", "new", "create", "implement"]):
            return "new_feature"
        elif any(kw in description for kw in ["performance", "optimize", "speed"]):
            return "optimization"
        elif any(kw in description for kw in ["security", "vulnerability", "auth"]):
            return "security"
        else:
            return "general"

    def get_statistics(self) -> Dict[str, any]:
        """
        Get statistics on estimated tasks.

        Returns:
            Statistics dictionary
        """
        if not self.task_history:
            return {
                "total_tasks": 0,
                "avg_score": 0.0,
                "level_distribution": {},
                "type_distribution": {},
            }

        total = len(self.task_history)
        avg_score = sum(t.score for t in self.task_history) / total

        # Count by level
        level_dist = {}
        for level in ComplexityLevel:
            count = sum(1 for t in self.task_history if t.level == level)
            level_dist[level.value] = count

        # Count by type
        type_dist = {}
        for task in self.task_history:
            type_dist[task.task_type] = type_dist.get(task.task_type, 0) + 1

        return {
            "total_tasks": total,
            "avg_score": avg_score,
            "avg_files": sum(t.file_count for t in self.task_history) / total,
            "avg_lines": sum(t.line_count for t in self.task_history) / total,
            "level_distribution": level_dist,
            "type_distribution": type_dist,
            "total_tokens_estimated": sum(t.estimated_tokens for t in self.task_history),
        }
