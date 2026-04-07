"""Tests for AI Context Manager"""

import pytest
import tempfile
import shutil
from pathlib import Path
from core.ai_context import AIContextManager


@pytest.fixture
def temp_project():
    """Create temporary project directory"""
    temp_dir = tempfile.mkdtemp()
    yield temp_dir
    shutil.rmtree(temp_dir)


@pytest.fixture
def context_manager(temp_project):
    """Create AIContextManager instance"""
    return AIContextManager(temp_project)


class TestAIContextManager:
    """Test AIContextManager class"""

    def test_init_creates_structure(self, context_manager):
        """Test initialization creates context directory structure"""
        assert context_manager.context_dir.exists()
        assert context_manager.buildrunner_dir.exists()

    def test_context_files_defined(self, context_manager):
        """Test all expected context files are defined"""
        expected_files = ["architecture", "current-work", "blockers", "test-results"]
        for file_type in expected_files:
            assert file_type in context_manager.context_files

    def test_update_context_file(self, context_manager):
        """Test updating a specific context file"""
        content = "# Test Content\n\nThis is a test."
        context_manager.update_context_file("architecture", content)

        arch_file = context_manager.context_files["architecture"]
        assert arch_file.exists()

        with open(arch_file, "r") as f:
            saved_content = f.read()

        assert saved_content == content

    def test_update_invalid_context_type_raises_error(self, context_manager):
        """Test updating invalid context type raises ValueError"""
        with pytest.raises(ValueError, match="Invalid context type"):
            context_manager.update_context_file("invalid", "content")

    def test_pipe_output(self, context_manager):
        """Test piping output to context"""
        output = "Test output from command"
        context_manager.pipe_output(output, "test-results")

        results_file = context_manager.context_files["test-results"]
        assert results_file.exists()

        with open(results_file, "r") as f:
            content = f.read()

        assert "Test output from command" in content
        assert "## Output: test-results" in content

    def test_load_context_all(self, context_manager):
        """Test loading all context"""
        # Create some context
        context_manager.update_context_file("architecture", "# Architecture\nTest")
        context_manager.update_context_file("blockers", "# Blockers\nNone")

        context = context_manager.load_context()

        assert "# architecture.md" in context
        assert "# blockers.md" in context
        assert "Test" in context

    def test_load_context_specific_tags(self, context_manager):
        """Test loading specific context tags"""
        context_manager.update_context_file("architecture", "# Architecture\nTest")
        context_manager.update_context_file("blockers", "# Blockers\nNone")

        context = context_manager.load_context(tags=["architecture"])

        assert "# architecture.md" in context
        assert "# blockers.md" not in context

    def test_add_blocker(self, context_manager):
        """Test adding a blocker"""
        # Create initial blockers file
        context_manager.update_context_file("blockers", "# Blockers\n\n## Active Blockers\n\n")

        context_manager.add_blocker(
            title="Test Blocker",
            description="This is a test blocker",
            issue="Error: Something went wrong",
        )

        blockers_file = context_manager.context_files["blockers"]
        with open(blockers_file, "r") as f:
            content = f.read()

        assert "### Test Blocker" in content
        assert "This is a test blocker" in content
        assert "Error: Something went wrong" in content

    def test_update_memory_new_section(self, context_manager):
        """Test updating CLAUDE.md with new section"""
        # Create default CLAUDE.md
        context_manager._create_default_claude_md()

        context_manager.update_memory("Test Section", "This is test content")

        with open(context_manager.claude_md, "r") as f:
            content = f.read()

        assert "## Test Section" in content
        assert "This is test content" in content

    def test_update_memory_existing_section(self, context_manager):
        """Test updating existing section in CLAUDE.md"""
        # Create default CLAUDE.md
        context_manager._create_default_claude_md()

        # Update once
        context_manager.update_memory("Current Work", "First content")

        # Update again
        context_manager.update_memory("Current Work", "Updated content")

        with open(context_manager.claude_md, "r") as f:
            content = f.read()

        assert "Updated content" in content
        assert "First content" not in content

    def test_create_default_claude_md(self, context_manager):
        """Test creating default CLAUDE.md"""
        context_manager._create_default_claude_md()

        assert context_manager.claude_md.exists()

        with open(context_manager.claude_md, "r") as f:
            content = f.read()

        assert "# CLAUDE.md" in content
        assert "## Current Work" in content
        assert "## Architecture Decisions" in content
        assert "## Lessons Learned" in content
