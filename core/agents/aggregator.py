"""
Result Aggregator for Multi-Agent Workflows

Merges and synthesizes results from multiple agents:
- Conflict resolution between agent outputs
- Result deduplication
- Summary generation
- Metadata consolidation
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional, Any, Tuple, Set
from datetime import datetime
from pathlib import Path
import json

from core.agents.claude_agent_bridge import AgentResponse, AgentType


class ConflictStrategy(str, Enum):
    """Strategy for resolving conflicts between agent results"""
    FIRST_WINS = "first_wins"         # Take first result
    LAST_WINS = "last_wins"           # Take last result
    MERGE = "merge"                   # Merge results
    UNION = "union"                   # Union of all results
    INTERSECTION = "intersection"     # Intersection of all results
    CONSENSUS = "consensus"           # Require consensus


@dataclass
class AggregatedResult:
    """Result of aggregating multiple agent responses"""
    aggregation_id: str
    aggregated_at: datetime
    results: List[AgentResponse]
    merged_output: str
    merged_files_created: List[str]
    merged_files_modified: List[str]
    merged_errors: List[str]
    summary: str
    conflict_resolutions: List[str] = field(default_factory=list)
    metrics: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary"""
        return {
            'aggregation_id': self.aggregation_id,
            'aggregated_at': self.aggregated_at.isoformat(),
            'result_count': len(self.results),
            'merged_output': self.merged_output,
            'merged_files_created': self.merged_files_created,
            'merged_files_modified': self.merged_files_modified,
            'merged_errors': self.merged_errors,
            'summary': self.summary,
            'conflict_resolutions': self.conflict_resolutions,
            'metrics': self.metrics,
        }


class ResultAggregator:
    """
    Aggregates results from multiple agents.

    Responsibilities:
    - Merge outputs from multiple agents
    - Resolve conflicts between results
    - Deduplicate files and errors
    - Generate summary
    - Track aggregation metrics
    """

    def __init__(
        self,
        conflict_strategy: ConflictStrategy = ConflictStrategy.MERGE,
        dedup_files: bool = True,
        dedup_errors: bool = True,
    ):
        """
        Initialize ResultAggregator.

        Args:
            conflict_strategy: Strategy for resolving conflicts
            dedup_files: Deduplicate file lists
            dedup_errors: Deduplicate error lists
        """
        self.conflict_strategy = conflict_strategy
        self.dedup_files = dedup_files
        self.dedup_errors = dedup_errors

        # Statistics
        self.aggregations_count = 0
        self.total_results_aggregated = 0

    def aggregate(
        self,
        results: List[AgentResponse],
        aggregation_id: Optional[str] = None,
    ) -> AggregatedResult:
        """
        Aggregate multiple agent results.

        Args:
            results: List of agent responses to aggregate
            aggregation_id: Optional ID for tracking

        Returns:
            AggregatedResult with merged outputs

        Raises:
            ValueError: If results list is empty
        """
        if not results:
            raise ValueError("Cannot aggregate empty results list")

        aggregation_id = aggregation_id or self._generate_id()

        # Merge outputs
        merged_output = self._merge_outputs(results)

        # Merge files
        merged_files_created = self._merge_files(
            [r.files_created for r in results]
        )
        merged_files_modified = self._merge_files(
            [r.files_modified for r in results]
        )

        # Merge errors
        merged_errors = self._merge_errors(results)

        # Generate summary
        summary = self._generate_summary(results, merged_output)

        # Track conflicts
        conflicts = self._detect_conflicts(results)

        # Create aggregated result
        aggregated = AggregatedResult(
            aggregation_id=aggregation_id,
            aggregated_at=datetime.now(),
            results=results,
            merged_output=merged_output,
            merged_files_created=merged_files_created,
            merged_files_modified=merged_files_modified,
            merged_errors=merged_errors,
            summary=summary,
            conflict_resolutions=conflicts,
            metrics=self._calculate_metrics(results),
        )

        # Update statistics
        self.aggregations_count += 1
        self.total_results_aggregated += len(results)

        return aggregated

    def _merge_outputs(self, results: List[AgentResponse]) -> str:
        """Merge outputs from multiple agents"""
        sections = []

        for i, result in enumerate(results, 1):
            agent_name = result.agent_type.value.upper()
            section = f"## Agent {i}: {agent_name}\n\n"

            if result.output:
                section += result.output

            if result.errors:
                section += f"\n\n### Errors:\n"
                for error in result.errors:
                    section += f"- {error}\n"

            sections.append(section)

        return "\n\n---\n\n".join(sections)

    def _merge_files(self, file_lists: List[List[str]]) -> List[str]:
        """Merge file lists with deduplication"""
        merged = []
        seen = set()

        for file_list in file_lists:
            for file_path in file_list:
                if self.dedup_files:
                    if file_path not in seen:
                        merged.append(file_path)
                        seen.add(file_path)
                else:
                    merged.append(file_path)

        return merged

    def _merge_errors(self, results: List[AgentResponse]) -> List[str]:
        """Merge errors from all results"""
        merged = []
        seen = set()

        for result in results:
            for error in result.errors:
                if self.dedup_errors:
                    if error not in seen:
                        merged.append(error)
                        seen.add(error)
                else:
                    merged.append(error)

        return merged

    def _generate_summary(
        self,
        results: List[AgentResponse],
        merged_output: str,
    ) -> str:
        """Generate summary of aggregation"""
        lines = [
            "# Aggregation Summary",
            "",
            f"Total agents: {len(results)}",
            f"Aggregation timestamp: {datetime.now().isoformat()}",
            "",
            "## Results by Agent",
            "",
        ]

        for i, result in enumerate(results, 1):
            agent_name = result.agent_type.value
            status = "SUCCESS" if result.success else "FAILED"
            lines.append(f"{i}. {agent_name}: {status}")

            if result.files_created:
                lines.append(f"   - Files created: {len(result.files_created)}")

            if result.errors:
                lines.append(f"   - Errors: {len(result.errors)}")

        # Add metrics
        lines.extend([
            "",
            "## Metrics",
            "",
            f"Total files created: {len(set().union(*(r.files_created for r in results)))}",
            f"Total files modified: {len(set().union(*(r.files_modified for r in results)))}",
            f"Total errors: {len(self._merge_errors(results))}",
        ])

        # Calculate success rate
        successful = sum(1 for r in results if r.success)
        success_rate = (successful / len(results)) * 100 if results else 0
        lines.append(f"Success rate: {success_rate:.1f}%")

        return "\n".join(lines)

    def _detect_conflicts(self, results: List[AgentResponse]) -> List[str]:
        """Detect conflicts between agent results"""
        conflicts = []

        # Check for conflicting file modifications
        all_files_created = {}
        all_files_modified = {}

        for result in results:
            for file_path in result.files_created:
                if file_path in all_files_modified:
                    conflicts.append(
                        f"File {file_path} created by {result.agent_type.value} "
                        f"but modified by another agent"
                    )
                all_files_created[file_path] = result.agent_type.value

            for file_path in result.files_modified:
                if file_path in all_files_created:
                    conflicts.append(
                        f"File {file_path} created by {all_files_created[file_path]} "
                        f"but modified by {result.agent_type.value}"
                    )
                all_files_modified[file_path] = result.agent_type.value

        # Check for multiple agents creating same files
        for file_path, creators in all_files_created.items():
            creator_count = len([r for r in results if file_path in r.files_created])
            if creator_count > 1:
                conflicts.append(f"File {file_path} created by multiple agents")

        return conflicts

    def _calculate_metrics(self, results: List[AgentResponse]) -> Dict[str, Any]:
        """Calculate aggregation metrics"""
        total_duration_ms = sum(r.duration_ms for r in results)
        total_tokens = sum(r.tokens_used for r in results)
        successful_count = sum(1 for r in results if r.success)
        failed_count = len(results) - successful_count

        return {
            'total_duration_ms': total_duration_ms,
            'avg_duration_ms': (
                total_duration_ms / len(results) if results else 0
            ),
            'total_tokens': total_tokens,
            'avg_tokens': (
                total_tokens / len(results) if results else 0
            ),
            'successful_agents': successful_count,
            'failed_agents': failed_count,
            'success_rate': (
                (successful_count / len(results)) * 100 if results else 0
            ),
        }

    def aggregate_sequential_results(
        self,
        results: List[AgentResponse],
        task_context: Optional[str] = None,
    ) -> AggregatedResult:
        """
        Aggregate results from sequential workflow execution.

        Each result builds on the previous one, so merge in order.

        Args:
            results: List of results in execution order
            task_context: Context about the task being executed

        Returns:
            AggregatedResult
        """
        if not results:
            raise ValueError("Cannot aggregate empty results")

        aggregation_id = self._generate_id()

        # For sequential results, focus on final outputs
        # but track progression through phases
        merged_output = self._create_sequential_narrative(results, task_context)
        merged_files_created = self._merge_files(
            [r.files_created for r in results]
        )
        merged_files_modified = self._merge_files(
            [r.files_modified for r in results]
        )
        merged_errors = self._merge_errors(results)

        summary = self._generate_sequential_summary(results)

        aggregated = AggregatedResult(
            aggregation_id=aggregation_id,
            aggregated_at=datetime.now(),
            results=results,
            merged_output=merged_output,
            merged_files_created=merged_files_created,
            merged_files_modified=merged_files_modified,
            merged_errors=merged_errors,
            summary=summary,
            metrics=self._calculate_metrics(results),
        )

        self.aggregations_count += 1
        self.total_results_aggregated += len(results)

        return aggregated

    def aggregate_parallel_results(
        self,
        results: List[AgentResponse],
        task_context: Optional[str] = None,
    ) -> AggregatedResult:
        """
        Aggregate results from parallel workflow execution.

        Multiple independent agents, consolidate findings.

        Args:
            results: List of results from parallel execution
            task_context: Context about the task

        Returns:
            AggregatedResult
        """
        if not results:
            raise ValueError("Cannot aggregate empty results")

        aggregation_id = self._generate_id()

        # For parallel results, group by agent type
        results_by_type = self._group_results_by_agent_type(results)
        merged_output = self._create_parallel_summary(results_by_type, task_context)
        merged_files_created = self._merge_files(
            [r.files_created for r in results]
        )
        merged_files_modified = self._merge_files(
            [r.files_modified for r in results]
        )
        merged_errors = self._merge_errors(results)

        summary = self._generate_parallel_summary(results_by_type)

        aggregated = AggregatedResult(
            aggregation_id=aggregation_id,
            aggregated_at=datetime.now(),
            results=results,
            merged_output=merged_output,
            merged_files_created=merged_files_created,
            merged_files_modified=merged_files_modified,
            merged_errors=merged_errors,
            summary=summary,
            conflict_resolutions=self._detect_conflicts(results),
            metrics=self._calculate_metrics(results),
        )

        self.aggregations_count += 1
        self.total_results_aggregated += len(results)

        return aggregated

    def _group_results_by_agent_type(
        self,
        results: List[AgentResponse],
    ) -> Dict[str, List[AgentResponse]]:
        """Group results by agent type"""
        grouped = {}

        for result in results:
            agent_type = result.agent_type.value
            if agent_type not in grouped:
                grouped[agent_type] = []
            grouped[agent_type].append(result)

        return grouped

    def _create_sequential_narrative(
        self,
        results: List[AgentResponse],
        task_context: Optional[str] = None,
    ) -> str:
        """Create narrative of sequential progression"""
        lines = ["# Sequential Workflow Progression", ""]

        if task_context:
            lines.extend([task_context, ""])

        phases = [
            "Exploration",
            "Implementation",
            "Testing",
            "Review",
        ]

        for i, (phase, result) in enumerate(zip(phases, results), 1):
            lines.extend([
                f"## Phase {i}: {phase}",
                f"Agent: {result.agent_type.value.upper()}",
                f"Status: {'SUCCESS' if result.success else 'FAILED'}",
                "",
            ])

            if result.output:
                lines.append(result.output)

            if result.files_created:
                lines.append(f"\nFiles created: {', '.join(result.files_created)}")

            lines.append("")

        return "\n".join(lines)

    def _create_parallel_summary(
        self,
        results_by_type: Dict[str, List[AgentResponse]],
        task_context: Optional[str] = None,
    ) -> str:
        """Create summary of parallel execution"""
        lines = ["# Parallel Execution Summary", ""]

        if task_context:
            lines.extend([task_context, ""])

        for agent_type, results in sorted(results_by_type.items()):
            lines.extend([
                f"## {agent_type.upper()}",
                f"Results: {len(results)}",
                "",
            ])

            for result in results:
                status = "SUCCESS" if result.success else "FAILED"
                lines.append(f"- Status: {status}")

                if result.files_created:
                    lines.append(f"  Files created: {', '.join(result.files_created)}")

            lines.append("")

        return "\n".join(lines)

    def _generate_sequential_summary(
        self,
        results: List[AgentResponse],
    ) -> str:
        """Generate summary for sequential execution"""
        lines = [
            "# Sequential Execution Summary",
            "",
            f"Total phases: {len(results)}",
            "",
            "## Phase Results",
            "",
        ]

        phases = ["Exploration", "Implementation", "Testing", "Review"]
        for phase, result in zip(phases, results):
            status = "SUCCESS" if result.success else "FAILED"
            lines.append(f"- {phase}: {status}")

        # Overall status
        overall_success = all(r.success for r in results)
        lines.extend([
            "",
            f"Overall Status: {'SUCCESS' if overall_success else 'FAILED'}",
        ])

        return "\n".join(lines)

    def _generate_parallel_summary(
        self,
        results_by_type: Dict[str, List[AgentResponse]],
    ) -> str:
        """Generate summary for parallel execution"""
        lines = [
            "# Parallel Execution Summary",
            "",
            f"Total agents: {sum(len(r) for r in results_by_type.values())}",
            "",
            "## Agent Summary",
            "",
        ]

        for agent_type, results in sorted(results_by_type.items()):
            successful = sum(1 for r in results if r.success)
            total = len(results)
            lines.append(f"- {agent_type.upper()}: {successful}/{total} succeeded")

        # Overall status
        all_results = [r for results in results_by_type.values() for r in results]
        all_successful = all(r.success for r in all_results)
        lines.extend([
            "",
            f"Overall Success: {all_successful}",
        ])

        return "\n".join(lines)

    def _generate_id(self) -> str:
        """Generate unique aggregation ID"""
        from uuid import uuid4
        return str(uuid4())[:8]

    def get_stats(self) -> Dict[str, Any]:
        """Get aggregator statistics"""
        return {
            'aggregations_count': self.aggregations_count,
            'total_results_aggregated': self.total_results_aggregated,
            'avg_results_per_aggregation': (
                self.total_results_aggregated / self.aggregations_count
                if self.aggregations_count > 0
                else 0
            ),
        }
