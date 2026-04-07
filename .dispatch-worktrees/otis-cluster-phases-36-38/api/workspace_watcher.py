"""
Workspace File Watcher Service
Monitors workspace directories for changes and notifies clients
"""

import asyncio
import json
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Set
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileSystemEvent
import hashlib
import logging

logger = logging.getLogger(__name__)

WORKSPACE_ROOT = Path("/Users/byronhudson/Projects/BuildRunner3/workspace")


class WorkspaceEventHandler(FileSystemEventHandler):
    """Handles file system events in workspace directories"""

    def __init__(self, callback=None):
        self.callback = callback
        self.file_hashes: Dict[str, str] = {}
        self.ignore_patterns = [".DS_Store", ".git", "__pycache__", "*.pyc"]

    def should_ignore(self, path: str) -> bool:
        """Check if file should be ignored"""
        for pattern in self.ignore_patterns:
            if pattern in path:
                return True
        return False

    def get_file_hash(self, filepath: str) -> Optional[str]:
        """Get hash of file contents"""
        try:
            with open(filepath, "rb") as f:
                return hashlib.md5(f.read()).hexdigest()
        except:
            return None

    def on_created(self, event: FileSystemEvent):
        if not event.is_directory and not self.should_ignore(event.src_path):
            self.handle_file_event("created", event.src_path)

    def on_modified(self, event: FileSystemEvent):
        if not event.is_directory and not self.should_ignore(event.src_path):
            # Check if content actually changed
            new_hash = self.get_file_hash(event.src_path)
            old_hash = self.file_hashes.get(event.src_path)

            if new_hash and new_hash != old_hash:
                self.file_hashes[event.src_path] = new_hash
                self.handle_file_event("modified", event.src_path)

    def on_deleted(self, event: FileSystemEvent):
        if not event.is_directory and not self.should_ignore(event.src_path):
            self.file_hashes.pop(event.src_path, None)
            self.handle_file_event("deleted", event.src_path)

    def handle_file_event(self, event_type: str, filepath: str):
        """Process file event and notify callback"""
        relative_path = Path(filepath).relative_to(WORKSPACE_ROOT)
        directory = relative_path.parts[0] if relative_path.parts else ""

        event_data = {
            "type": f"file_{event_type}",
            "path": str(relative_path),
            "directory": directory,
            "filename": Path(filepath).name,
            "timestamp": datetime.now().isoformat(),
        }

        # Special handling for specific directories
        if directory == "prd":
            event_data["category"] = "prd_update"
        elif directory == "output":
            event_data["category"] = "claude_output"
        elif directory == "tasks":
            event_data["category"] = "task_update"
        elif directory == "context":
            event_data["category"] = "context_update"

        if self.callback:
            asyncio.create_task(self.callback(event_data))

        logger.info(f"Workspace event: {event_type} - {relative_path}")


class WorkspaceMonitor:
    """Monitors all workspace directories"""

    def __init__(self):
        self.observer: Optional[Observer] = None
        self.event_handler: Optional[WorkspaceEventHandler] = None
        self.event_callbacks: Set = set()

    def add_callback(self, callback):
        """Add callback for events"""
        self.event_callbacks.add(callback)

    def remove_callback(self, callback):
        """Remove callback"""
        self.event_callbacks.discard(callback)

    async def broadcast_event(self, event_data: dict):
        """Broadcast event to all callbacks"""
        for callback in self.event_callbacks:
            try:
                await callback(event_data)
            except Exception as e:
                logger.error(f"Error in callback: {e}")

    def start(self):
        """Start monitoring workspace"""
        if self.observer:
            return

        # Ensure workspace directories exist
        for subdir in ["prd", "tasks", "context", "output", "logs"]:
            (WORKSPACE_ROOT / subdir).mkdir(parents=True, exist_ok=True)

        self.event_handler = WorkspaceEventHandler(callback=self.broadcast_event)
        self.observer = Observer()

        # Monitor all subdirectories
        for subdir in WORKSPACE_ROOT.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                self.observer.schedule(self.event_handler, str(subdir), recursive=True)
                logger.info(f"Monitoring: {subdir}")

        self.observer.start()
        logger.info("Workspace monitoring started")

    def stop(self):
        """Stop monitoring"""
        if self.observer:
            self.observer.stop()
            self.observer.join()
            self.observer = None
            logger.info("Workspace monitoring stopped")

    def get_workspace_state(self) -> dict:
        """Get current state of workspace"""
        state = {"directories": {}, "timestamp": datetime.now().isoformat()}

        for subdir in WORKSPACE_ROOT.iterdir():
            if subdir.is_dir() and not subdir.name.startswith("."):
                files = []
                for file in subdir.glob("**/*"):
                    if file.is_file() and not self.event_handler.should_ignore(str(file)):
                        relative_path = file.relative_to(subdir)
                        files.append(
                            {
                                "name": file.name,
                                "path": str(relative_path),
                                "size": file.stat().st_size,
                                "modified": datetime.fromtimestamp(
                                    file.stat().st_mtime
                                ).isoformat(),
                            }
                        )

                state["directories"][subdir.name] = {"file_count": len(files), "files": files}

        return state


class WorkspaceManager:
    """Manages workspace files and operations"""

    @staticmethod
    async def save_prd(project_name: str, content: str) -> dict:
        """Save PRD to workspace"""
        filepath = WORKSPACE_ROOT / "prd" / f"{project_name}.md"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        filepath.write_text(content)

        # Create trigger file for Claude
        trigger_file = WORKSPACE_ROOT / "prd" / f".{project_name}.trigger"
        trigger_file.write_text(datetime.now().isoformat())

        return {
            "success": True,
            "path": str(filepath.relative_to(WORKSPACE_ROOT)),
            "trigger": str(trigger_file.relative_to(WORKSPACE_ROOT)),
        }

    @staticmethod
    async def save_tasks(project_name: str, tasks: List[dict]) -> dict:
        """Save task list to workspace"""
        filepath = WORKSPACE_ROOT / "tasks" / f"{project_name}.json"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        filepath.write_text(json.dumps(tasks, indent=2))

        return {
            "success": True,
            "path": str(filepath.relative_to(WORKSPACE_ROOT)),
            "task_count": len(tasks),
        }

    @staticmethod
    async def save_context(project_name: str, context_type: str, content: str) -> dict:
        """Save context file for Claude"""
        filepath = WORKSPACE_ROOT / "context" / project_name / f"{context_type}.md"
        filepath.parent.mkdir(parents=True, exist_ok=True)

        filepath.write_text(content)

        return {"success": True, "path": str(filepath.relative_to(WORKSPACE_ROOT))}

    @staticmethod
    async def read_output(filename: str) -> Optional[str]:
        """Read Claude output file"""
        filepath = WORKSPACE_ROOT / "output" / filename

        if filepath.exists():
            return filepath.read_text()
        return None

    @staticmethod
    async def list_outputs(project_name: str = None) -> List[dict]:
        """List all Claude output files"""
        output_dir = WORKSPACE_ROOT / "output"
        files = []

        if output_dir.exists():
            pattern = f"{project_name}*" if project_name else "*"
            for file in output_dir.glob(pattern):
                if file.is_file():
                    files.append(
                        {
                            "name": file.name,
                            "size": file.stat().st_size,
                            "modified": datetime.fromtimestamp(file.stat().st_mtime).isoformat(),
                        }
                    )

        return files

    @staticmethod
    async def generate_claude_context(project_name: str) -> str:
        """Generate comprehensive context file for Claude"""
        context_parts = []

        # Add PRD if exists
        prd_file = WORKSPACE_ROOT / "prd" / f"{project_name}.md"
        if prd_file.exists():
            context_parts.append(f"# Project Requirements Document\n\n{prd_file.read_text()}\n")

        # Add tasks if exist
        tasks_file = WORKSPACE_ROOT / "tasks" / f"{project_name}.json"
        if tasks_file.exists():
            tasks = json.loads(tasks_file.read_text())
            context_parts.append(f"# Task List\n\n```json\n{json.dumps(tasks, indent=2)}\n```\n")

        # Add any context files
        context_dir = WORKSPACE_ROOT / "context" / project_name
        if context_dir.exists():
            for context_file in context_dir.glob("*.md"):
                context_parts.append(f"# {context_file.stem}\n\n{context_file.read_text()}\n")

        # Save combined context
        combined_file = WORKSPACE_ROOT / "context" / f"{project_name}_combined.md"
        combined_content = "\n---\n\n".join(context_parts)
        combined_file.write_text(combined_content)

        return str(combined_file)


# Global workspace monitor instance
monitor = WorkspaceMonitor()
manager = WorkspaceManager()
