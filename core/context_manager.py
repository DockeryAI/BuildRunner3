"""
Context Manager for Task Orchestration

Manages context windows for Claude execution, ensuring relevant information
is available without exceeding token limits. Tracks completed components,
gathers dependencies, and compresses context when needed.
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import List, Dict, Optional, Set
import json
from datetime import datetime


@dataclass
class ContextEntry:
    """Represents a single context entry"""

    id: str
    type: str  # "file", "task", "dependency", "pattern"
    content: str
    priority: int  # Higher = more important
    timestamp: datetime = field(default_factory=datetime.now)
    size_chars: int = 0

    def __post_init__(self):
        if self.size_chars == 0:
            self.size_chars = len(self.content)


class ContextManager:
    """
    Manages context windows for Claude task execution.

    Responsibilities:
    - Track completed files and tasks
    - Gather relevant dependencies
    - Maintain 4000-token limit
    - Compress context when needed
    - Persist context to disk
    """

    MAX_TOKENS = 4000
    CHARS_PER_TOKEN = 4  # Approximate
    MAX_CHARS = MAX_TOKENS * CHARS_PER_TOKEN  # 16,000 characters

    CONTEXT_DIR = Path(".buildrunner/context")

    def __init__(self, project_root: Optional[Path] = None):
        self.project_root = project_root or Path.cwd()
        self.context_dir = self.project_root / self.CONTEXT_DIR

        # Context storage
        self.entries: List[ContextEntry] = []
        self.completed_files: Set[str] = set()
        self.completed_tasks: List[str] = []
        self.dependencies: Dict[str, str] = {}
        self.patterns: List[str] = []

        # Statistics
        self.compressions_count = 0
        self.entries_added = 0

        # Ensure context directory exists
        self._ensure_context_dir()

    def _ensure_context_dir(self):
        """Ensure context directory exists"""
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def add_context(
        self,
        id: str,
        type: str,
        content: str,
        priority: int = 5,
    ) -> bool:
        """
        Add context entry.

        Args:
            id: Unique identifier for this entry
            type: Type of context ("file", "task", "dependency", "pattern")
            content: The context content
            priority: Priority level (1-10, higher = more important)

        Returns:
            True if added successfully, False if would exceed limit
        """
        # Check if adding this would exceed limit
        entry = ContextEntry(id=id, type=type, content=content, priority=priority)

        if not self._can_add_entry(entry):
            # Try to compress to make room
            self._compress_context()

            # Check again
            if not self._can_add_entry(entry):
                return False

        self.entries.append(entry)
        self.entries_added += 1
        return True

    def add_completed_file(self, file_path: str, summary: Optional[str] = None):
        """
        Track a completed file.

        Args:
            file_path: Path to the completed file
            summary: Optional summary of what the file does
        """
        self.completed_files.add(file_path)

        # Add to context
        content = f"Completed: {file_path}"
        if summary:
            content += f"\n{summary}"

        self.add_context(
            id=f"file:{file_path}",
            type="file",
            content=content,
            priority=7,
        )

    def add_completed_task(self, task_name: str, description: Optional[str] = None):
        """
        Track a completed task.

        Args:
            task_name: Name of the completed task
            description: Optional description of what was accomplished
        """
        self.completed_tasks.append(task_name)

        # Add to context
        content = f"Completed Task: {task_name}"
        if description:
            content += f"\n{description}"

        self.add_context(
            id=f"task:{task_name}",
            type="task",
            content=content,
            priority=6,
        )

    def add_dependency(self, name: str, version: str, notes: Optional[str] = None):
        """
        Track a dependency.

        Args:
            name: Dependency name
            version: Version string
            notes: Optional notes about usage
        """
        self.dependencies[name] = version

        # Add to context
        content = f"Dependency: {name} ({version})"
        if notes:
            content += f"\n{notes}"

        self.add_context(
            id=f"dep:{name}",
            type="dependency",
            content=content,
            priority=4,
        )

    def add_pattern(self, pattern_name: str, description: str):
        """
        Track an architecture pattern.

        Args:
            pattern_name: Pattern name (e.g., "MVC", "Repository")
            description: Description of how it's used
        """
        if pattern_name not in self.patterns:
            self.patterns.append(pattern_name)

        self.add_context(
            id=f"pattern:{pattern_name}",
            type="pattern",
            content=f"Pattern: {pattern_name}\n{description}",
            priority=8,
        )

    def get_context(self, max_chars: Optional[int] = None) -> str:
        """
        Get current context as string.

        Args:
            max_chars: Optional character limit (defaults to MAX_CHARS)

        Returns:
            Formatted context string
        """
        max_chars = max_chars or self.MAX_CHARS

        # Sort by priority (high to low) and timestamp (recent first)
        sorted_entries = sorted(self.entries, key=lambda e: (e.priority, e.timestamp), reverse=True)

        # Build context string
        sections = []
        current_size = 0

        for entry in sorted_entries:
            if current_size + entry.size_chars > max_chars:
                # Would exceed limit
                break

            sections.append(entry.content)
            current_size += entry.size_chars

        return "\n\n".join(sections)

    def get_context_summary(self) -> Dict:
        """
        Get summary of current context.

        Returns:
            Dictionary with context statistics
        """
        total_chars = sum(e.size_chars for e in self.entries)
        total_tokens = total_chars // self.CHARS_PER_TOKEN

        return {
            "total_entries": len(self.entries),
            "total_chars": total_chars,
            "estimated_tokens": total_tokens,
            "token_limit": self.MAX_TOKENS,
            "utilization_percent": (total_tokens / self.MAX_TOKENS) * 100,
            "completed_files": len(self.completed_files),
            "completed_tasks": len(self.completed_tasks),
            "dependencies": len(self.dependencies),
            "patterns": len(self.patterns),
            "compressions": self.compressions_count,
        }

    def clear_context(self):
        """Clear all context entries"""
        self.entries = []
        self.completed_files = set()
        self.completed_tasks = []
        self.dependencies = {}
        self.patterns = []

    def save_context(self, filename: str = "context.json"):
        """
        Save context to disk.

        Args:
            filename: Filename to save to (in context directory)
        """
        filepath = self.context_dir / filename

        data = {
            "timestamp": datetime.now().isoformat(),
            "entries": [
                {
                    "id": e.id,
                    "type": e.type,
                    "content": e.content,
                    "priority": e.priority,
                    "timestamp": e.timestamp.isoformat(),
                }
                for e in self.entries
            ],
            "completed_files": list(self.completed_files),
            "completed_tasks": self.completed_tasks,
            "dependencies": self.dependencies,
            "patterns": self.patterns,
            "stats": self.get_context_summary(),
        }

        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    def load_context(self, filename: str = "context.json"):
        """
        Load context from disk.

        Args:
            filename: Filename to load from (in context directory)
        """
        filepath = self.context_dir / filename

        if not filepath.exists():
            raise FileNotFoundError(f"Context file not found: {filepath}")

        with open(filepath, "r") as f:
            data = json.load(f)

        # Restore entries
        self.entries = [
            ContextEntry(
                id=e["id"],
                type=e["type"],
                content=e["content"],
                priority=e["priority"],
                timestamp=datetime.fromisoformat(e["timestamp"]),
            )
            for e in data["entries"]
        ]

        # Restore other data
        self.completed_files = set(data["completed_files"])
        self.completed_tasks = data["completed_tasks"]
        self.dependencies = data["dependencies"]
        self.patterns = data["patterns"]

    def _can_add_entry(self, entry: ContextEntry) -> bool:
        """Check if entry can be added without exceeding limit"""
        current_size = sum(e.size_chars for e in self.entries)
        return (current_size + entry.size_chars) <= self.MAX_CHARS

    def _compress_context(self):
        """
        Compress context by removing low-priority entries.

        Removes lowest 20% by priority to make room.
        """
        if not self.entries:
            return

        # Sort by priority (low to high)
        sorted_entries = sorted(self.entries, key=lambda e: e.priority)

        # Remove lowest 20%
        remove_count = max(1, len(sorted_entries) // 5)
        self.entries = sorted_entries[remove_count:]

        self.compressions_count += 1

    def get_relevant_context_for_task(self, task) -> str:
        """
        Get relevant context for a specific task.

        Args:
            task: Task object to get context for

        Returns:
            Filtered context string
        """
        relevant_entries = []

        for entry in self.entries:
            # Include if:
            # - High priority (>= 7)
            # - Related to task dependencies
            # - Related to task domain
            # - Pattern-related

            if entry.priority >= 7:
                relevant_entries.append(entry)
            elif entry.type == "dependency" and any(
                dep in entry.content for dep in task.dependencies
            ):
                relevant_entries.append(entry)
            elif entry.type == "pattern":
                relevant_entries.append(entry)

        # Sort by priority
        relevant_entries.sort(key=lambda e: e.priority, reverse=True)

        # Build context string
        return "\n\n".join(e.content for e in relevant_entries[:10])  # Top 10

    def prune_old_entries(self, keep_recent_count: int = 50):
        """
        Prune old context entries, keeping only recent ones.

        Args:
            keep_recent_count: Number of recent entries to keep
        """
        # Sort by timestamp (recent first)
        sorted_entries = sorted(self.entries, key=lambda e: e.timestamp, reverse=True)

        # Keep only recent entries
        self.entries = sorted_entries[:keep_recent_count]

    def get_stats(self) -> Dict:
        """Get context manager statistics"""
        return {
            "entries_added": self.entries_added,
            "current_entries": len(self.entries),
            "compressions": self.compressions_count,
            **self.get_context_summary(),
        }
