"""AI Context Manager for BuildRunner 3.0

Manages persistent AI context across sessions with CLAUDE.md and segmented
context files.
"""

from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class AIContextManager:
    """Manages AI context and persistent memory"""

    def __init__(self, project_root: str = "."):
        """Initialize AI context manager

        Args:
            project_root: Root directory of the project
        """
        self.project_root = Path(project_root)
        self.buildrunner_dir = self.project_root / ".buildrunner"
        self.claude_md = self.buildrunner_dir / "CLAUDE.md"
        self.context_dir = self.buildrunner_dir / "context"

        # Context file paths
        self.context_files = {
            "architecture": self.context_dir / "architecture.md",
            "current-work": self.context_dir / "current-work.md",
            "blockers": self.context_dir / "blockers.md",
            "test-results": self.context_dir / "test-results.md"
        }

        self._ensure_structure()

    def _ensure_structure(self):
        """Ensure context directory structure exists"""
        self.context_dir.mkdir(parents=True, exist_ok=True)

    def update_memory(self, section: str, content: str):
        """Update a specific section of CLAUDE.md

        Args:
            section: Section name to update (e.g., "Current Work", "Lessons Learned")
            content: New content for the section
        """
        if not self.claude_md.exists():
            self._create_default_claude_md()

        # Read existing content
        with open(self.claude_md, 'r') as f:
            lines = f.readlines()

        # Find and update section
        updated_lines = []
        in_section = False
        section_found = False

        for line in lines:
            if line.startswith(f"## {section}"):
                in_section = True
                section_found = True
                updated_lines.append(line)
                updated_lines.append("\n")
                updated_lines.append(content)
                updated_lines.append("\n\n")
            elif in_section and line.startswith("##"):
                in_section = False
                updated_lines.append(line)
            elif not in_section:
                updated_lines.append(line)

        # If section not found, append it
        if not section_found:
            updated_lines.append(f"## {section}\n\n")
            updated_lines.append(content)
            updated_lines.append("\n\n")

        # Update timestamp
        final_lines = []
        for line in updated_lines:
            if "*Last Updated:" in line:
                final_lines.append(f"*Last Updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}*\n")
            else:
                final_lines.append(line)

        # Write back
        with open(self.claude_md, 'w') as f:
            f.writelines(final_lines)

    def pipe_output(self, output: str, tag: str):
        """Pipe command output to context

        Args:
            output: Command output to save
            tag: Tag/category for the output (e.g., "test-results", "build-output")
        """
        # Determine which context file based on tag
        if tag in self.context_files:
            context_file = self.context_files[tag]
        else:
            # Default to test-results for unknown tags
            context_file = self.context_files["test-results"]

        # Append to context file with timestamp
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        with open(context_file, 'a') as f:
            f.write(f"\n\n## Output: {tag}\n")
            f.write(f"**Timestamp:** {timestamp}\n\n")
            f.write("```\n")
            f.write(output)
            f.write("\n```\n")

    def load_context(self, tags: Optional[List[str]] = None) -> str:
        """Load specific context for AI

        Args:
            tags: List of context tags to load (None = load all)

        Returns:
            Combined context as markdown string
        """
        if tags is None:
            # Load all context
            tags = list(self.context_files.keys())

        context_parts = []

        # Load CLAUDE.md
        if self.claude_md.exists():
            with open(self.claude_md, 'r') as f:
                context_parts.append("# CLAUDE.md\n")
                context_parts.append(f.read())
                context_parts.append("\n---\n")

        # Load specific context files
        for tag in tags:
            if tag in self.context_files:
                context_file = self.context_files[tag]
                if context_file.exists():
                    with open(context_file, 'r') as f:
                        context_parts.append(f"# {tag}.md\n")
                        context_parts.append(f.read())
                        context_parts.append("\n---\n")

        return "\n".join(context_parts)

    def update_context_file(self, context_type: str, content: str):
        """Update a specific context file

        Args:
            context_type: Type of context (architecture, current-work, blockers, test-results)
            content: Content to write

        Raises:
            ValueError: If context_type is invalid
        """
        if context_type not in self.context_files:
            raise ValueError(f"Invalid context type: {context_type}. "
                           f"Valid types: {list(self.context_files.keys())}")

        context_file = self.context_files[context_type]

        with open(context_file, 'w') as f:
            f.write(content)

    def add_blocker(self, title: str, description: str, issue: Optional[str] = None):
        """Add a blocker to blockers.md

        Args:
            title: Blocker title
            description: Blocker description
            issue: Optional issue/error message
        """
        blockers_file = self.context_files["blockers"]

        timestamp = datetime.now().strftime('%Y-%m-%d')
        blocker_entry = f"\n### {title}\n"
        blocker_entry += f"**Date:** {timestamp}\n"
        blocker_entry += f"**Status:** Active\n\n"
        blocker_entry += f"{description}\n"

        if issue:
            blocker_entry += f"\n**Details:**\n```\n{issue}\n```\n"

        # Insert under "## Active Blockers"
        if blockers_file.exists():
            with open(blockers_file, 'r') as f:
                content = f.read()

            if "## Active Blockers" in content:
                parts = content.split("## Active Blockers")
                new_content = parts[0] + "## Active Blockers\n" + blocker_entry
                if len(parts) > 1:
                    new_content += "\n" + parts[1]

                with open(blockers_file, 'w') as f:
                    f.write(new_content)
            else:
                # Append if section doesn't exist
                with open(blockers_file, 'a') as f:
                    f.write("\n## Active Blockers\n")
                    f.write(blocker_entry)

    def _create_default_claude_md(self):
        """Create default CLAUDE.md structure"""
        default_content = """# CLAUDE.md - Persistent AI Memory

This file maintains context across AI sessions.

## Current Work

*No current work tracked*

## Architecture Decisions

*No decisions recorded yet*

## Lessons Learned

*No lessons learned yet*

## Next Steps

*No next steps defined*

---

*Last Updated: {datetime}*
*This file is read/written by AI assistants to maintain project context*
""".replace("{datetime}", datetime.now().strftime('%Y-%m-%d %H:%M:%S'))

        with open(self.claude_md, 'w') as f:
            f.write(default_content)
