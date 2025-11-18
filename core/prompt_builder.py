"""
Prompt Builder for Claude Execution

Generates focused, high-quality prompts from task batches that maximize
Claude's performance. Includes task descriptions, relevant context, file paths,
and explicit stop points.
"""

from dataclasses import dataclass
from typing import List, Dict, Optional
from pathlib import Path


@dataclass
class PromptContext:
    """Context information for prompt generation"""
    project_spec: Optional[str] = None
    architecture_patterns: List[str] = None
    dependencies: Dict[str, str] = None
    completed_tasks: List[str] = None
    current_state: Optional[str] = None

    def __post_init__(self):
        if self.architecture_patterns is None:
            self.architecture_patterns = []
        if self.dependencies is None:
            self.dependencies = {}
        if self.completed_tasks is None:
            self.completed_tasks = []


class PromptBuilder:
    """
    Builds focused Claude prompts from task batches.

    Optimizes for Claude's performance by:
    - Clear, specific task descriptions
    - Relevant context only (max 4000 tokens)
    - Explicit file paths
    - Stop points for verification
    - Structured format
    """

    MAX_CONTEXT_TOKENS = 4000
    CHARS_PER_TOKEN = 4  # Approximate

    def __init__(self):
        self.prompts_generated = 0

    def build_prompt(
        self,
        batch,  # TaskBatch
        context: Optional[PromptContext] = None,
        include_tests: bool = True,
        include_docs: bool = False,
    ) -> str:
        """
        Generate a complete Claude prompt from a task batch.

        Args:
            batch: TaskBatch to generate prompt for
            context: Optional context information
            include_tests: Whether to request tests
            include_docs: Whether to request documentation

        Returns:
            Formatted prompt string ready for Claude

        Raises:
            ValueError: If batch is empty or invalid
        """
        if not batch or not batch.tasks:
            raise ValueError("Cannot build prompt from empty batch")

        self.prompts_generated += 1

        # Build prompt sections
        sections = []

        # Header
        sections.append(self._build_header(batch))

        # Context section
        if context:
            sections.append(self._build_context_section(context))

        # Task descriptions
        sections.append(self._build_tasks_section(batch, include_tests, include_docs))

        # Acceptance criteria
        sections.append(self._build_acceptance_section(batch))

        # Stop point
        sections.append(self._build_stop_point(batch))

        # Combine all sections
        prompt = "\n\n".join(sections)

        # Validate token count
        if not self._is_within_token_limit(prompt):
            # Trim context if needed
            prompt = self._trim_to_fit(sections, context)

        return prompt

    def _build_header(self, batch) -> str:
        """Build prompt header with batch information"""
        task_count = len(batch.tasks)
        domain = batch.domain.value
        complexity = batch.complexity_level.value

        header = f"""You are building Batch {batch.id}: {domain.title()} Domain

CONTEXT:
This batch contains {task_count} {'task' if task_count == 1 else 'tasks'} in the {domain} domain.
Complexity level: {complexity}
Estimated time: {batch.total_minutes} minutes

CRITICAL RULES:
1. Complete ALL tasks in this batch
2. Create files EXACTLY at the specified paths
3. Include comprehensive docstrings
4. Write tests for all new code
5. Update CLAUDE.md after completing this batch
6. STOP at the verification gate"""

        return header

    def _build_context_section(self, context: PromptContext) -> str:
        """Build context section with relevant project information"""
        sections = []

        if context.project_spec:
            sections.append(f"PROJECT SPEC:\n{self._truncate(context.project_spec, 1000)}")

        if context.architecture_patterns:
            patterns = ", ".join(context.architecture_patterns)
            sections.append(f"ARCHITECTURE PATTERNS:\n{patterns}")

        if context.dependencies:
            deps = "\n".join(f"- {k}: {v}" for k, v in context.dependencies.items())
            sections.append(f"DEPENDENCIES:\n{deps}")

        if context.completed_tasks:
            completed = "\n".join(f"- {task}" for task in context.completed_tasks[-5:])  # Last 5
            sections.append(f"COMPLETED TASKS:\n{completed}")

        if not sections:
            return ""

        return "CONTEXT INFORMATION:\n" + "\n\n".join(sections)

    def _build_tasks_section(self, batch, include_tests: bool, include_docs: bool) -> str:
        """Build detailed task descriptions"""
        task_descriptions = []

        for i, task in enumerate(batch.tasks, 1):
            desc = self._build_task_description(task, i, include_tests, include_docs)
            task_descriptions.append(desc)

        return "TASKS TO COMPLETE:\n\n" + "\n\n".join(task_descriptions)

    def _build_task_description(
        self,
        task,  # Task
        task_number: int,
        include_tests: bool,
        include_docs: bool,
    ) -> str:
        """Build a single task description"""
        lines = [
            f"## Task {task_number}: {task.name}",
            f"**File:** `{task.file_path}`",
            f"**Estimated Time:** {task.estimated_minutes} minutes",
            f"**Complexity:** {task.complexity.value}",
            "",
            f"**Description:**",
            task.description,
        ]

        # Dependencies
        if task.dependencies:
            lines.append("")
            lines.append("**Dependencies:**")
            for dep in task.dependencies:
                lines.append(f"- {dep}")

        # Acceptance criteria
        if task.acceptance_criteria:
            lines.append("")
            lines.append("**Acceptance Criteria:**")
            for criteria in task.acceptance_criteria:
                lines.append(f"- {criteria}")

        # Testing requirements
        if include_tests:
            lines.append("")
            test_file = self._get_test_path(task.file_path)
            lines.append(f"**Tests:** Create comprehensive tests in `{test_file}`")

        # Documentation requirements
        if include_docs:
            lines.append("")
            lines.append("**Documentation:** Include detailed docstrings and usage examples")

        return "\n".join(lines)

    def _build_acceptance_section(self, batch) -> str:
        """Build overall acceptance criteria for the batch"""
        lines = [
            "ACCEPTANCE CRITERIA FOR THIS BATCH:",
            ""
        ]

        # File creation checks
        for task in batch.tasks:
            lines.append(f"- [ ] File created: {task.file_path}")

        # Test checks
        lines.append("")
        for task in batch.tasks:
            test_file = self._get_test_path(task.file_path)
            lines.append(f"- [ ] Tests created: {test_file}")

        # General quality checks
        lines.extend([
            "",
            "QUALITY CHECKS:",
            "- [ ] All files have comprehensive docstrings",
            "- [ ] All tests passing",
            "- [ ] No import errors",
            "- [ ] Code follows project patterns",
            f"- [ ] {len(batch.tasks)} tasks completed",
        ])

        return "\n".join(lines)

    def _build_stop_point(self, batch) -> str:
        """Build explicit stop point"""
        return f"""VERIFICATION GATE:

After completing all {len(batch.tasks)} tasks, STOP and report:

---
✅ Batch {batch.id} Complete

Files Created:
{self._format_file_list(batch.tasks)}

Tests Created:
{self._format_test_list(batch.tasks)}

Tests: X passing
Coverage: X%

Ready for next batch: YES/NO
---

DO NOT proceed past this point. Wait for verification."""

    def _format_file_list(self, tasks) -> str:
        """Format file list for report"""
        return "\n".join(f"- {task.file_path} (X lines)" for task in tasks)

    def _format_test_list(self, tasks) -> str:
        """Format test file list for report"""
        return "\n".join(f"- {self._get_test_path(task.file_path)} (X lines)" for task in tasks)

    def _get_test_path(self, file_path: str) -> str:
        """Convert source file path to test file path"""
        path = Path(file_path)

        # core/foo.py -> tests/test_foo.py
        if path.parent.name in ["core", "cli", "api"]:
            test_name = f"test_{path.stem}.py"
            return f"tests/{test_name}"

        # Other paths
        return f"tests/test_{path.stem}.py"

    def _truncate(self, text: str, max_chars: int) -> str:
        """Truncate text to max characters"""
        if len(text) <= max_chars:
            return text
        return text[:max_chars] + "\n... (truncated)"

    def _is_within_token_limit(self, prompt: str) -> bool:
        """Check if prompt is within token limit"""
        estimated_tokens = len(prompt) // self.CHARS_PER_TOKEN
        return estimated_tokens <= self.MAX_CONTEXT_TOKENS

    def _trim_to_fit(self, sections: List[str], context: Optional[PromptContext]) -> str:
        """Trim prompt to fit within token limit"""
        # Start by removing context section or trimming it
        trimmed_sections = []

        for section in sections:
            # Keep header, tasks, acceptance, and stop point
            # Truncate only context section
            if "CONTEXT INFORMATION:" in section:
                # Trim context more aggressively
                trimmed_sections.append(self._truncate(section, 500))
            else:
                trimmed_sections.append(section)

        return "\n\n".join(trimmed_sections)

    def build_batch_series_prompt(self, batches: List, context: Optional[PromptContext] = None) -> List[str]:
        """
        Generate prompts for a series of batches.

        Args:
            batches: List of TaskBatch objects
            context: Optional context information

        Returns:
            List of prompt strings, one per batch
        """
        prompts = []

        for i, batch in enumerate(batches):
            # Update context with completed batches
            if context and i > 0:
                # Add previous batch tasks to completed
                for prev_batch in batches[:i]:
                    for task in prev_batch.tasks:
                        if task.name not in context.completed_tasks:
                            context.completed_tasks.append(task.name)

            prompt = self.build_prompt(batch, context)
            prompts.append(prompt)

        return prompts

    def generate_handoff_context(self, batch) -> str:
        """
        Generate compact context for handing off to next batch.

        Returns minimal context needed for next batch to continue.
        """
        lines = [
            f"# Handoff from Batch {batch.id}",
            "",
            "## Completed Files:",
        ]

        for task in batch.tasks:
            lines.append(f"- {task.file_path} - {task.name}")

        lines.extend([
            "",
            "## Key Patterns:",
            "- Follow established code patterns from completed files",
            "- Maintain consistent naming conventions",
            "- Keep test coverage above 90%",
            "",
            "## Next Steps:",
            "- Continue with next batch",
            "- Ensure integration with completed files",
            "- Run full test suite after completion",
        ])

        return "\n".join(lines)

    def get_stats(self) -> Dict[str, int]:
        """Get prompt generation statistics"""
        return {
            "prompts_generated": self.prompts_generated,
        }
