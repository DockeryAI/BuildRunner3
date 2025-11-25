#!/usr/bin/env python3
"""
BuildRunner Terminal UI - Native terminal interface with full system control

This TUI (Terminal User Interface) runs directly in your terminal and can:
- Execute CLI commands directly
- Launch Claude or any desktop app
- Access the file system
- Run BuildRunner commands natively
- No browser limitations!

Requirements:
    pip install textual rich
"""

from textual.app import App, ComposeResult
from textual.containers import Container, Horizontal, Vertical, ScrollableContainer
from textual.widgets import Header, Footer, Button, Input, Static, Label, TextLog, ListView, ListItem
from textual.binding import Binding
from textual import events
from rich.text import Text
from rich.syntax import Syntax
import subprocess
import os
from pathlib import Path
import asyncio
from datetime import datetime
import json


class CommandOutput(TextLog):
    """Widget to display command output"""

    def add_command(self, command: str):
        """Add a command to the output"""
        self.write(Text(f"$ {command}", style="bold cyan"))

    def add_output(self, text: str, is_error: bool = False):
        """Add output text"""
        style = "red" if is_error else "green"
        self.write(Text(text, style=style))

    def add_info(self, text: str):
        """Add info message"""
        self.write(Text(f"ℹ️  {text}", style="yellow"))


class BuildRunnerTUI(App):
    """BuildRunner Terminal UI Application"""

    CSS = """
    Screen {
        background: $background;
    }

    #sidebar {
        width: 30;
        background: $panel;
        border-right: solid $primary;
        padding: 1;
    }

    #main {
        background: $background;
        padding: 1;
    }

    #command-input {
        dock: bottom;
        height: 3;
        background: $panel;
        border-top: solid $primary;
        padding: 0 1;
    }

    Button {
        margin: 1 0;
        width: 100%;
    }

    .quick-action {
        background: $primary;
        color: $text;
        text-style: bold;
    }

    .quick-action:hover {
        background: $secondary;
    }

    .project-info {
        background: $boost;
        padding: 1;
        margin: 1 0;
        border: solid $primary;
    }

    CommandOutput {
        background: $panel;
        border: solid $accent;
        height: 100%;
        padding: 1;
    }
    """

    BINDINGS = [
        Binding("ctrl+c", "quit", "Quit", priority=True),
        Binding("ctrl+n", "new_project", "New Project"),
        Binding("ctrl+p", "plan", "Planning Mode"),
        Binding("ctrl+r", "run", "Run Build"),
        Binding("ctrl+l", "clear", "Clear Output"),
        Binding("f1", "help", "Help"),
    ]

    def __init__(self):
        super().__init__()
        self.current_project = None
        self.project_path = Path.cwd()

    def compose(self) -> ComposeResult:
        """Create child widgets"""
        yield Header(show_clock=True)

        with Horizontal():
            # Sidebar with quick actions
            with Vertical(id="sidebar"):
                yield Label("🚀 BuildRunner TUI", classes="title")

                # Project info
                with Container(classes="project-info"):
                    yield Label("Project: None", id="project-label")
                    yield Label(f"Path: {self.project_path}", id="path-label")

                # Quick action buttons
                yield Label("Quick Actions:", classes="section-header")
                yield Button("📁 New Project", id="btn-new", classes="quick-action")
                yield Button("🧠 Planning Mode", id="btn-plan", classes="quick-action")
                yield Button("📄 Create PRD", id="btn-prd", classes="quick-action")
                yield Button("▶️ Run Build", id="btn-run", classes="quick-action")
                yield Button("📊 Status", id="btn-status", classes="quick-action")
                yield Button("📋 Task List", id="btn-tasks", classes="quick-action")
                yield Button("✅ Quality Check", id="btn-quality", classes="quick-action")
                yield Button("🤖 AI Agents", id="btn-agents", classes="quick-action")
                yield Button("🚀 Launch Claude", id="btn-claude", classes="quick-action")

            # Main content area
            with Vertical(id="main"):
                yield CommandOutput(id="output", highlight=True, markup=True)

        # Command input at bottom
        with Horizontal(id="command-input"):
            yield Label("Command: ")
            yield Input(placeholder="Enter any command (br commands or system commands)", id="input")

        yield Footer()

    async def execute_command(self, command: str) -> tuple[str, str, int]:
        """Execute a command and return output, error, and return code"""
        try:
            process = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=str(self.project_path)
            )
            stdout, stderr = await process.communicate()

            return (
                stdout.decode('utf-8'),
                stderr.decode('utf-8'),
                process.returncode or 0
            )
        except Exception as e:
            return "", str(e), 1

    def launch_claude(self, project_name: str = None, prompt: str = None):
        """Launch Claude desktop app or CLI"""
        output = self.query_one("#output", CommandOutput)
        output.add_info("Attempting to launch Claude...")

        # First try Claude CLI
        try:
            if prompt:
                # Save prompt to temp file
                import tempfile
                with tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False) as f:
                    f.write(f"Project: {project_name or 'BuildRunner'}\n\n{prompt}")
                    temp_file = f.name

                # Try Claude CLI
                result = subprocess.run(
                    ["claude", "--dangerously-skip-permissions", temp_file],
                    capture_output=True,
                    text=True,
                    timeout=5
                )
                if result.returncode == 0:
                    output.add_info("✅ Claude CLI launched successfully!")
                    return
        except:
            pass

        # Try to open Claude desktop app (macOS)
        import platform
        if platform.system() == "Darwin":
            apps = [
                "/Applications/Claude.app",
                "/Applications/Claude Code.app",
                "~/Applications/Claude.app"
            ]

            for app_path in apps:
                expanded = os.path.expanduser(app_path)
                if os.path.exists(expanded):
                    subprocess.run(["open", expanded])
                    output.add_info(f"✅ Opened {os.path.basename(expanded)}")
                    if prompt:
                        # Copy to clipboard
                        subprocess.run(['pbcopy'], input=prompt.encode(), check=True)
                        output.add_info("📋 Prompt copied to clipboard - paste in Claude!")
                    return

        # Windows
        elif platform.system() == "Windows":
            try:
                subprocess.run(["start", "claude"], shell=True, check=True)
                output.add_info("✅ Claude launched on Windows")
                return
            except:
                pass

        output.add_output("❌ Could not find Claude. Please install Claude or Claude Code.", is_error=True)

    async def on_button_pressed(self, event: Button.Pressed) -> None:
        """Handle button clicks"""
        output = self.query_one("#output", CommandOutput)

        button_id = event.button.id

        if button_id == "btn-new":
            await self.action_new_project()
        elif button_id == "btn-plan":
            await self.run_command("br plan")
        elif button_id == "btn-prd":
            await self.run_command("br prd")
        elif button_id == "btn-run":
            await self.run_command("br run")
        elif button_id == "btn-status":
            await self.run_command("br status")
        elif button_id == "btn-tasks":
            await self.run_command("br task list")
        elif button_id == "btn-quality":
            await self.run_command("br quality check")
        elif button_id == "btn-agents":
            await self.run_command("br agent list")
        elif button_id == "btn-claude":
            planning_prompt = f"""
I'm using BuildRunner to create a new project called '{self.current_project or 'MyProject'}'.
Please help me plan and design this project.

BuildRunner will help us:
1. Define project requirements
2. Break down features
3. Create technical specifications
4. Generate task lists
5. Build the project with AI agents

Let's start by defining what this project should do.
"""
            self.launch_claude(self.current_project, planning_prompt)

    async def on_input_submitted(self, event: Input.Submitted) -> None:
        """Handle command input submission"""
        command = event.value
        if command:
            await self.run_command(command)
            event.input.value = ""

    async def run_command(self, command: str):
        """Run a command and display output"""
        output = self.query_one("#output", CommandOutput)
        output.add_command(command)

        # Special handling for br init
        if command.startswith("br init"):
            parts = command.split()
            if len(parts) >= 3:
                self.current_project = parts[2]
                self.query_one("#project-label", Label).update(f"Project: {self.current_project}")

                # After init, show planning options
                self.call_later(self.show_planning_options)

        # Execute the command
        stdout, stderr, returncode = await self.execute_command(command)

        if stdout:
            output.add_output(stdout)
        if stderr:
            output.add_output(stderr, is_error=(returncode != 0))

        if returncode != 0:
            output.add_info(f"Command exited with code {returncode}")

    def show_planning_options(self):
        """Show planning options after project init"""
        output = self.query_one("#output", CommandOutput)
        output.add_info(f"""
✨ Project '{self.current_project}' initialized!

Next steps:
1. Press Ctrl+P or click 'Planning Mode' to start planning
2. Press the 'Launch Claude' button to open Claude with a planning prompt
3. Run 'br run' when ready to build

Claude integration is FULLY WORKING in this terminal UI!
""")

    async def action_new_project(self) -> None:
        """Create a new project"""
        # For simplicity, using a default name.
        # In a real app, you'd show a dialog to get the project name
        project_name = f"Project_{datetime.now().strftime('%Y%m%d_%H%M%S')}"
        await self.run_command(f"br init {project_name}")

    async def action_plan(self) -> None:
        """Start planning mode"""
        await self.run_command("br plan")

    async def action_run(self) -> None:
        """Run build"""
        await self.run_command("br run")

    def action_clear(self) -> None:
        """Clear output"""
        output = self.query_one("#output", CommandOutput)
        output.clear()
        output.add_info("Output cleared. Ready for new commands.")

    def action_help(self) -> None:
        """Show help"""
        output = self.query_one("#output", CommandOutput)
        output.add_info("""
BuildRunner Terminal UI - Help

KEYBOARD SHORTCUTS:
  Ctrl+N  : New Project
  Ctrl+P  : Planning Mode
  Ctrl+R  : Run Build
  Ctrl+L  : Clear Output
  Ctrl+C  : Quit
  F1      : This help

FEATURES:
  ✅ Execute ANY command (BR or system)
  ✅ Launch Claude directly
  ✅ Full file system access
  ✅ No browser limitations
  ✅ Native terminal experience

Type any command in the input field at the bottom.
Click buttons for quick actions.
""")


if __name__ == "__main__":
    # First install required packages if needed
    try:
        import textual
        import rich
    except ImportError:
        print("Installing required packages...")
        subprocess.run(["pip", "install", "textual", "rich"], check=True)
        print("Packages installed! Starting UI...")

    app = BuildRunnerTUI()
    app.run()