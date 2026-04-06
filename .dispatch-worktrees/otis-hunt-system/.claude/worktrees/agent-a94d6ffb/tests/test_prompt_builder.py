"""
Tests for PromptBuilder

Ensures high-quality Claude prompts with proper structure, context management,
and token limits.
"""

import pytest
from core.prompt_builder import PromptBuilder, PromptContext
from core.batch_optimizer import Task, TaskBatch, TaskComplexity, TaskDomain


class TestPromptBuilder:
    """Test suite for PromptBuilder"""

    def test_init(self):
        """Test PromptBuilder initialization"""
        builder = PromptBuilder()
        assert builder.prompts_generated == 0

    def test_build_prompt_empty_batch_raises(self):
        """Test that empty batch raises error"""
        builder = PromptBuilder()
        empty_batch = TaskBatch(
            id=1,
            tasks=[],
            total_minutes=0,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        with pytest.raises(ValueError, match="empty batch"):
            builder.build_prompt(empty_batch)

    def test_build_prompt_single_task(self):
        """Test building prompt for single task"""
        builder = PromptBuilder()
        task = Task(
            id="task1",
            name="Create User Model",
            description="Create a User model with basic fields",
            file_path="core/models.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["User model created", "All fields present"],
        )

        batch = TaskBatch(
            id=1,
            tasks=[task],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompt = builder.build_prompt(batch)

        # Check header
        assert "Batch 1" in prompt
        assert "Backend Domain" in prompt
        assert "1 task" in prompt
        assert "60 minutes" in prompt

        # Check task description
        assert "Create User Model" in prompt
        assert "core/models.py" in prompt
        assert "User model created" in prompt

        # Check stop point
        assert "VERIFICATION GATE" in prompt
        assert "DO NOT proceed" in prompt

        # Check prompts generated counter
        assert builder.prompts_generated == 1

    def test_build_prompt_multiple_tasks(self):
        """Test building prompt for multiple tasks"""
        builder = PromptBuilder()
        tasks = [
            Task(
                id=f"task{i}",
                name=f"Task {i}",
                description=f"Description {i}",
                file_path=f"core/file{i}.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Done"],
            )
            for i in range(1, 4)
        ]

        batch = TaskBatch(
            id=1,
            tasks=tasks,
            total_minutes=180,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompt = builder.build_prompt(batch)

        # Check all tasks mentioned
        assert "Task 1" in prompt
        assert "Task 2" in prompt
        assert "Task 3" in prompt
        assert "3 tasks" in prompt

    def test_build_prompt_with_context(self):
        """Test building prompt with context information"""
        builder = PromptBuilder()
        context = PromptContext(
            project_spec="This is the project spec",
            architecture_patterns=["MVC", "Repository"],
            dependencies={"django": "4.2", "pytest": "7.4"},
            completed_tasks=["Setup database", "Create migrations"],
        )

        task = Task(
            id="task1",
            name="Task 1",
            description="Description",
            file_path="core/file.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Done"],
        )

        batch = TaskBatch(
            id=1,
            tasks=[task],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompt = builder.build_prompt(batch, context)

        # Check context is included
        assert "CONTEXT INFORMATION" in prompt
        assert "PROJECT SPEC" in prompt
        assert "ARCHITECTURE PATTERNS" in prompt
        assert "MVC" in prompt
        assert "DEPENDENCIES" in prompt
        assert "django" in prompt
        assert "COMPLETED TASKS" in prompt
        assert "Setup database" in prompt

    def test_build_prompt_without_tests(self):
        """Test building prompt without test requirement"""
        builder = PromptBuilder()
        task = Task(
            id="task1",
            name="Task 1",
            description="Description",
            file_path="core/file.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Done"],
        )

        batch = TaskBatch(
            id=1,
            tasks=[task],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompt = builder.build_prompt(batch, include_tests=False)

        # Should not request tests
        assert "Tests:" not in prompt or "Create comprehensive tests" not in prompt

    def test_build_prompt_with_docs(self):
        """Test building prompt with documentation requirement"""
        builder = PromptBuilder()
        task = Task(
            id="task1",
            name="Task 1",
            description="Description",
            file_path="core/file.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Done"],
        )

        batch = TaskBatch(
            id=1,
            tasks=[task],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompt = builder.build_prompt(batch, include_docs=True)

        # Should request documentation
        assert "Documentation:" in prompt
        assert "docstrings" in prompt.lower()

    def test_get_test_path_core_file(self):
        """Test converting core file to test path"""
        builder = PromptBuilder()
        test_path = builder._get_test_path("core/models.py")
        assert test_path == "tests/test_models.py"

    def test_get_test_path_cli_file(self):
        """Test converting CLI file to test path"""
        builder = PromptBuilder()
        test_path = builder._get_test_path("cli/commands.py")
        assert test_path == "tests/test_commands.py"

    def test_get_test_path_other_file(self):
        """Test converting other file to test path"""
        builder = PromptBuilder()
        test_path = builder._get_test_path("utils/helpers.py")
        assert test_path == "tests/test_helpers.py"

    def test_truncate_short_text(self):
        """Test truncating text that's already short"""
        builder = PromptBuilder()
        text = "Short text"
        result = builder._truncate(text, 100)
        assert result == text
        assert "truncated" not in result

    def test_truncate_long_text(self):
        """Test truncating long text"""
        builder = PromptBuilder()
        text = "x" * 1000
        result = builder._truncate(text, 100)
        assert len(result) < len(text)
        assert "truncated" in result

    def test_is_within_token_limit_small_prompt(self):
        """Test token limit check for small prompt"""
        builder = PromptBuilder()
        small_prompt = "This is a small prompt"
        assert builder._is_within_token_limit(small_prompt)

    def test_is_within_token_limit_large_prompt(self):
        """Test token limit check for large prompt"""
        builder = PromptBuilder()
        # Create prompt exceeding token limit
        large_prompt = "x" * (
            PromptBuilder.MAX_CONTEXT_TOKENS * PromptBuilder.CHARS_PER_TOKEN + 1000
        )
        assert not builder._is_within_token_limit(large_prompt)

    def test_build_batch_series_prompt(self):
        """Test generating prompts for multiple batches"""
        builder = PromptBuilder()
        tasks1 = [
            Task(
                id="task1",
                name="Task 1",
                description="First task",
                file_path="core/file1.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Done"],
            )
        ]

        tasks2 = [
            Task(
                id="task2",
                name="Task 2",
                description="Second task",
                file_path="core/file2.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Done"],
            )
        ]

        batch1 = TaskBatch(
            id=1,
            tasks=tasks1,
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        batch2 = TaskBatch(
            id=2,
            tasks=tasks2,
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompts = builder.build_batch_series_prompt([batch1, batch2])

        assert len(prompts) == 2
        assert "Batch 1" in prompts[0]
        assert "Batch 2" in prompts[1]

    def test_build_batch_series_with_context_propagation(self):
        """Test that completed tasks propagate through batch series"""
        builder = PromptBuilder()
        context = PromptContext(completed_tasks=[])

        task1 = Task(
            id="task1",
            name="First Task",
            description="Description",
            file_path="core/file1.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Done"],
        )

        task2 = Task(
            id="task2",
            name="Second Task",
            description="Description",
            file_path="core/file2.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Done"],
        )

        batch1 = TaskBatch(
            id=1,
            tasks=[task1],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )
        batch2 = TaskBatch(
            id=2,
            tasks=[task2],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompts = builder.build_batch_series_prompt([batch1, batch2], context)

        # Second prompt should mention first task as completed
        assert "First Task" in prompts[1]

    def test_generate_handoff_context(self):
        """Test generating handoff context for next batch"""
        builder = PromptBuilder()
        tasks = [
            Task(
                id="task1",
                name="Create Model",
                description="Description",
                file_path="core/models.py",
                estimated_minutes=60,
                complexity=TaskComplexity.SIMPLE,
                domain=TaskDomain.BACKEND,
                dependencies=[],
                acceptance_criteria=["Done"],
            )
        ]

        batch = TaskBatch(
            id=1,
            tasks=tasks,
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        handoff = builder.generate_handoff_context(batch)

        assert "Handoff from Batch 1" in handoff
        assert "Completed Files" in handoff
        assert "core/models.py" in handoff
        assert "Create Model" in handoff
        assert "Next Steps" in handoff

    def test_get_stats_initial(self):
        """Test stats when no prompts generated"""
        builder = PromptBuilder()
        stats = builder.get_stats()
        assert stats["prompts_generated"] == 0

    def test_get_stats_after_generation(self):
        """Test stats after generating prompts"""
        builder = PromptBuilder()
        task = Task(
            id="task1",
            name="Task 1",
            description="Description",
            file_path="core/file.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Done"],
        )

        batch = TaskBatch(
            id=1,
            tasks=[task],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        builder.build_prompt(batch)
        builder.build_prompt(batch)

        stats = builder.get_stats()
        assert stats["prompts_generated"] == 2

    def test_prompt_includes_acceptance_criteria(self):
        """Test that prompt includes task acceptance criteria"""
        builder = PromptBuilder()
        task = Task(
            id="task1",
            name="Task 1",
            description="Description",
            file_path="core/file.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Criteria 1", "Criteria 2", "Criteria 3"],
        )

        batch = TaskBatch(
            id=1,
            tasks=[task],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompt = builder.build_prompt(batch)

        assert "Criteria 1" in prompt
        assert "Criteria 2" in prompt
        assert "Criteria 3" in prompt

    def test_prompt_includes_task_dependencies(self):
        """Test that prompt includes task dependencies"""
        builder = PromptBuilder()
        task = Task(
            id="task1",
            name="Task 1",
            description="Description",
            file_path="core/file.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=["core/models.py", "core/utils.py"],
            acceptance_criteria=["Done"],
        )

        batch = TaskBatch(
            id=1,
            tasks=[task],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompt = builder.build_prompt(batch)

        assert "Dependencies:" in prompt
        assert "core/models.py" in prompt
        assert "core/utils.py" in prompt

    def test_prompt_critical_rules_present(self):
        """Test that critical rules are in prompt"""
        builder = PromptBuilder()
        task = Task(
            id="task1",
            name="Task 1",
            description="Description",
            file_path="core/file.py",
            estimated_minutes=60,
            complexity=TaskComplexity.SIMPLE,
            domain=TaskDomain.BACKEND,
            dependencies=[],
            acceptance_criteria=["Done"],
        )

        batch = TaskBatch(
            id=1,
            tasks=[task],
            total_minutes=60,
            domain=TaskDomain.BACKEND,
            complexity_level=TaskComplexity.SIMPLE,
        )

        prompt = builder.build_prompt(batch)

        assert "CRITICAL RULES:" in prompt
        assert "Complete ALL tasks" in prompt
        assert "EXACTLY at the specified paths" in prompt
        assert "STOP at the verification gate" in prompt


class TestPromptContext:
    """Test suite for PromptContext"""

    def test_init_defaults(self):
        """Test PromptContext initialization with defaults"""
        context = PromptContext()
        assert context.project_spec is None
        assert context.architecture_patterns == []
        assert context.dependencies == {}
        assert context.completed_tasks == []
        assert context.current_state is None

    def test_init_with_values(self):
        """Test PromptContext initialization with values"""
        context = PromptContext(
            project_spec="Spec",
            architecture_patterns=["MVC"],
            dependencies={"django": "4.2"},
            completed_tasks=["Task 1"],
            current_state="In progress",
        )

        assert context.project_spec == "Spec"
        assert context.architecture_patterns == ["MVC"]
        assert context.dependencies == {"django": "4.2"}
        assert context.completed_tasks == ["Task 1"]
        assert context.current_state == "In progress"
