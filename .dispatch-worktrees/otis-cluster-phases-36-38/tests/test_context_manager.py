"""
Tests for ContextManager

Ensures proper context window management, compression, and persistence.
"""

import pytest
from pathlib import Path
from datetime import datetime
from core.context_manager import ContextManager, ContextEntry
from core.batch_optimizer import Task, TaskComplexity, TaskDomain
import tempfile
import shutil


class TestContextManager:
    """Test suite for ContextManager"""

    @pytest.fixture
    def temp_project_root(self):
        """Create temporary project root directory"""
        temp_dir = tempfile.mkdtemp()
        yield Path(temp_dir)
        shutil.rmtree(temp_dir)

    @pytest.fixture
    def manager(self, temp_project_root):
        """Create ContextManager instance"""
        return ContextManager(project_root=temp_project_root)

    def test_init(self, manager, temp_project_root):
        """Test ContextManager initialization"""
        assert manager.project_root == temp_project_root
        assert manager.entries == []
        assert manager.completed_files == set()
        assert manager.completed_tasks == []
        assert manager.dependencies == {}
        assert manager.patterns == []
        assert manager.compressions_count == 0

    def test_context_dir_created(self, manager):
        """Test that context directory is created"""
        assert manager.context_dir.exists()
        assert manager.context_dir.is_dir()

    def test_add_context_simple(self, manager):
        """Test adding simple context entry"""
        result = manager.add_context(
            id="test1",
            type="file",
            content="Test content",
            priority=5,
        )

        assert result is True
        assert len(manager.entries) == 1
        assert manager.entries[0].id == "test1"
        assert manager.entries[0].type == "file"
        assert manager.entries[0].content == "Test content"
        assert manager.entries[0].priority == 5

    def test_add_context_multiple(self, manager):
        """Test adding multiple context entries"""
        for i in range(5):
            manager.add_context(
                id=f"test{i}",
                type="file",
                content=f"Content {i}",
                priority=5,
            )

        assert len(manager.entries) == 5

    def test_add_completed_file(self, manager):
        """Test tracking completed file"""
        manager.add_completed_file("core/models.py", "User model implementation")

        assert "core/models.py" in manager.completed_files
        assert len(manager.entries) == 1
        assert "core/models.py" in manager.entries[0].content

    def test_add_completed_task(self, manager):
        """Test tracking completed task"""
        manager.add_completed_task("Create User Model", "Implemented with all fields")

        assert "Create User Model" in manager.completed_tasks
        assert len(manager.entries) == 1
        assert "Create User Model" in manager.entries[0].content

    def test_add_dependency(self, manager):
        """Test tracking dependency"""
        manager.add_dependency("django", "4.2.0", "Web framework")

        assert "django" in manager.dependencies
        assert manager.dependencies["django"] == "4.2.0"
        assert len(manager.entries) == 1
        assert "django" in manager.entries[0].content

    def test_add_pattern(self, manager):
        """Test tracking architecture pattern"""
        manager.add_pattern("MVC", "Model-View-Controller pattern")

        assert "MVC" in manager.patterns
        assert len(manager.entries) == 1
        assert "MVC" in manager.entries[0].content

    def test_add_pattern_duplicate(self, manager):
        """Test that duplicate patterns are not re-added to list"""
        manager.add_pattern("MVC", "First description")
        manager.add_pattern("MVC", "Second description")

        assert manager.patterns.count("MVC") == 1
        assert len(manager.entries) == 2  # But both added to entries

    def test_get_context(self, manager):
        """Test retrieving context as string"""
        manager.add_context("test1", "file", "Content 1", priority=5)
        manager.add_context("test2", "file", "Content 2", priority=8)

        context = manager.get_context()

        assert "Content 1" in context
        assert "Content 2" in context

    def test_get_context_respects_priority(self, manager):
        """Test that get_context returns high priority items first"""
        manager.add_context("low", "file", "Low priority", priority=1)
        manager.add_context("high", "file", "High priority", priority=10)

        context = manager.get_context()

        # High priority should appear before low priority
        high_idx = context.index("High priority")
        low_idx = context.index("Low priority")
        assert high_idx < low_idx

    def test_get_context_with_max_chars(self, manager):
        """Test get_context with character limit"""
        manager.add_context("test1", "file", "x" * 1000, priority=5)
        manager.add_context("test2", "file", "y" * 1000, priority=5)

        context = manager.get_context(max_chars=500)

        # Should truncate to fit limit
        assert len(context) <= 500

    def test_get_context_summary(self, manager):
        """Test getting context summary statistics"""
        manager.add_context("test1", "file", "Content", priority=5)
        manager.add_completed_file("core/models.py")
        manager.add_dependency("django", "4.2.0")
        manager.add_pattern("MVC", "Pattern")

        summary = manager.get_context_summary()

        assert summary["total_entries"] == 4
        assert summary["completed_files"] == 1
        assert summary["dependencies"] == 1
        assert summary["patterns"] == 1
        assert "estimated_tokens" in summary
        assert "utilization_percent" in summary

    def test_clear_context(self, manager):
        """Test clearing all context"""
        manager.add_context("test", "file", "Content", priority=5)
        manager.add_completed_file("core/models.py")
        manager.add_dependency("django", "4.2.0")
        manager.add_pattern("MVC", "Pattern")

        manager.clear_context()

        assert manager.entries == []
        assert manager.completed_files == set()
        assert manager.completed_tasks == []
        assert manager.dependencies == {}
        assert manager.patterns == []

    def test_save_and_load_context(self, manager):
        """Test saving and loading context"""
        # Add some context
        manager.add_context("test1", "file", "Content 1", priority=5)
        manager.add_completed_file("core/models.py")
        manager.add_dependency("django", "4.2.0")

        # Save
        manager.save_context("test_context.json")

        # Create new manager and load
        new_manager = ContextManager(project_root=manager.project_root)
        new_manager.load_context("test_context.json")

        # Verify loaded data
        assert len(new_manager.entries) > 0
        assert "core/models.py" in new_manager.completed_files
        assert "django" in new_manager.dependencies

    def test_load_context_file_not_found(self, manager):
        """Test loading non-existent context file raises error"""
        with pytest.raises(FileNotFoundError):
            manager.load_context("nonexistent.json")

    def test_can_add_entry_within_limit(self, manager):
        """Test _can_add_entry returns True when within limit"""
        entry = ContextEntry(
            id="test",
            type="file",
            content="Small content",
            priority=5,
        )

        assert manager._can_add_entry(entry) is True

    def test_can_add_entry_exceeds_limit(self, manager):
        """Test _can_add_entry returns False when exceeding limit"""
        # Fill up context to near limit
        large_content = "x" * (ContextManager.MAX_CHARS - 100)
        manager.add_context("filler", "file", large_content, priority=5)

        # Try to add entry that would exceed limit
        entry = ContextEntry(
            id="test",
            type="file",
            content="y" * 1000,
            priority=5,
        )

        assert manager._can_add_entry(entry) is False

    def test_compress_context(self, manager):
        """Test context compression removes low-priority entries"""
        # Add entries with different priorities
        for i in range(10):
            manager.add_context(
                id=f"test{i}",
                type="file",
                content=f"Content {i}",
                priority=i % 5,  # Priorities 0-4
            )

        initial_count = len(manager.entries)
        manager._compress_context()

        # Should have removed ~20% (2 entries)
        assert len(manager.entries) < initial_count
        assert manager.compressions_count == 1

    def test_add_context_auto_compresses_when_full(self, manager):
        """Test that adding context auto-compresses when at limit"""
        # Fill up context
        large_content = "x" * 5000
        for i in range(3):
            manager.add_context(f"test{i}", "file", large_content, priority=1)

        # Add another entry (should trigger compression)
        result = manager.add_context("new", "file", large_content, priority=10)

        # Should succeed after compression
        assert result is True or manager.compressions_count > 0

    def test_get_relevant_context_for_task(self, manager):
        """Test getting relevant context for specific task"""
        # Add various context entries
        manager.add_context("high", "file", "High priority content", priority=9)
        manager.add_context("low", "file", "Low priority content", priority=2)
        manager.add_pattern("MVC", "MVC pattern")
        manager.add_dependency("django", "4.2.0")

        # Create a task
        task = Task(
            id="task1",
            name="Task 1",
            description="Description",
            file_path="core/views.py",
            estimated_minutes=60,
            complexity=TaskComplexity.MEDIUM,
            domain=TaskDomain.BACKEND,
            dependencies=["django"],
            acceptance_criteria=["Done"],
        )

        context = manager.get_relevant_context_for_task(task)

        # Should include high priority and dependency-related content
        assert "High priority content" in context
        assert "MVC pattern" in context

    def test_prune_old_entries(self, manager):
        """Test pruning old context entries"""
        # Add entries
        for i in range(100):
            manager.add_context(
                id=f"test{i}",
                type="file",
                content=f"Content {i}",
                priority=5,
            )

        manager.prune_old_entries(keep_recent_count=10)

        # Should only keep 10 most recent
        assert len(manager.entries) == 10

    def test_get_stats(self, manager):
        """Test getting context manager statistics"""
        manager.add_context("test", "file", "Content", priority=5)

        stats = manager.get_stats()

        assert "entries_added" in stats
        assert "current_entries" in stats
        assert "compressions" in stats
        assert "total_entries" in stats
        assert stats["entries_added"] >= 1

    def test_context_entry_defaults(self):
        """Test ContextEntry default values"""
        entry = ContextEntry(
            id="test",
            type="file",
            content="Test content",
            priority=5,
        )

        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, datetime)
        assert entry.size_chars == len("Test content")

    def test_multiple_managers_share_context_dir(self, temp_project_root):
        """Test that multiple managers can share context directory"""
        manager1 = ContextManager(project_root=temp_project_root)
        manager2 = ContextManager(project_root=temp_project_root)

        # Save from first manager
        manager1.add_context("test", "file", "Content", priority=5)
        manager1.save_context("shared.json")

        # Load from second manager
        manager2.load_context("shared.json")

        assert len(manager2.entries) > 0

    def test_context_priority_levels(self, manager):
        """Test various priority levels work correctly"""
        # Add entries with all priority levels 1-10
        for priority in range(1, 11):
            manager.add_context(
                id=f"priority{priority}",
                type="file",
                content=f"Priority {priority} content",
                priority=priority,
            )

        context = manager.get_context()

        # All should be included
        for priority in range(1, 11):
            assert f"Priority {priority} content" in context


class TestContextEntry:
    """Test suite for ContextEntry"""

    def test_init_with_all_fields(self):
        """Test ContextEntry initialization with all fields"""
        timestamp = datetime.now()
        entry = ContextEntry(
            id="test",
            type="file",
            content="Test content",
            priority=7,
            timestamp=timestamp,
            size_chars=12,
        )

        assert entry.id == "test"
        assert entry.type == "file"
        assert entry.content == "Test content"
        assert entry.priority == 7
        assert entry.timestamp == timestamp
        assert entry.size_chars == 12

    def test_init_auto_calculates_size(self):
        """Test that size_chars is auto-calculated if not provided"""
        entry = ContextEntry(
            id="test",
            type="file",
            content="Test content",
            priority=5,
        )

        assert entry.size_chars == len("Test content")

    def test_timestamp_auto_generated(self):
        """Test that timestamp is auto-generated if not provided"""
        entry = ContextEntry(
            id="test",
            type="file",
            content="Test content",
            priority=5,
        )

        assert entry.timestamp is not None
        assert isinstance(entry.timestamp, datetime)
