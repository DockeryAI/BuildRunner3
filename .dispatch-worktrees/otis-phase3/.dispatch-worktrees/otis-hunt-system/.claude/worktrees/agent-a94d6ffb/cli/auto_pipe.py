"""
Auto-Piping Module for BuildRunner 3.0

Captures command stdout/stderr and automatically pipes to context files.
Enables debugging workflow where command outputs are preserved for AI analysis.
"""

import subprocess
import sys
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple
import shlex


class PipeError(Exception):
    """Raised when piping operations fail."""

    pass


class CommandPiper:
    """
    Captures command output and pipes to context files.

    Automatically writes timestamped command outputs to
    .buildrunner/context/command-outputs.md for AI consumption.

    Attributes:
        project_root: Root directory of project
        context_file: Path to command-outputs.md
        max_output_size: Maximum output size to capture (chars)
    """

    def __init__(
        self,
        project_root: Optional[Path] = None,
        context_file: Optional[Path] = None,
        max_output_size: int = 100000,
    ):
        """
        Initialize CommandPiper.

        Args:
            project_root: Root directory. Defaults to current directory.
            context_file: Custom context file path. Defaults to command-outputs.md.
            max_output_size: Maximum output to capture in characters.
        """
        self.project_root = Path(project_root) if project_root else Path.cwd()
        self.max_output_size = max_output_size

        if context_file:
            self.context_file = Path(context_file)
        else:
            self.context_file = (
                self.project_root / ".buildrunner" / "context" / "command-outputs.md"
            )

    def run_and_pipe(
        self, command: str, shell: bool = True, capture_errors: bool = True
    ) -> Tuple[int, str, str]:
        """
        Run command and capture output.

        Args:
            command: Command to execute
            shell: Whether to use shell execution
            capture_errors: Whether to capture stderr separately

        Returns:
            Tuple of (return_code, stdout, stderr)

        Raises:
            PipeError: If command execution fails critically
        """
        try:
            if shell:
                result = subprocess.run(
                    command,
                    shell=True,
                    capture_output=True,
                    text=True,
                    timeout=300,  # 5 minute timeout
                )
            else:
                args = shlex.split(command)
                result = subprocess.run(args, capture_output=True, text=True, timeout=300)

            stdout = result.stdout[: self.max_output_size] if result.stdout else ""
            stderr = result.stderr[: self.max_output_size] if result.stderr else ""

            return (result.returncode, stdout, stderr)

        except subprocess.TimeoutExpired:
            raise PipeError(f"Command timed out after 300 seconds: {command}")
        except Exception as e:
            raise PipeError(f"Failed to execute command: {e}")

    def pipe_to_context(
        self, command: str, stdout: str, stderr: str, return_code: int, tags: Optional[list] = None
    ) -> None:
        """
        Write command output to context file.

        Args:
            command: The command that was executed
            stdout: Standard output
            stderr: Standard error
            return_code: Command return code
            tags: Optional tags for categorization

        Raises:
            PipeError: If writing fails
        """
        try:
            # Ensure context directory exists
            self.context_file.parent.mkdir(parents=True, exist_ok=True)

            # Prepare entry
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            tags_str = f" [{', '.join(tags)}]" if tags else ""

            entry = f"""
---
## Command Output - {timestamp}{tags_str}

**Command:** `{command}`
**Return Code:** {return_code}
**Status:** {'✅ SUCCESS' if return_code == 0 else '❌ FAILED'}

### Standard Output
```
{stdout if stdout else '(no output)'}
```

### Standard Error
```
{stderr if stderr else '(no errors)'}
```

"""

            # Append to context file
            with open(self.context_file, "a") as f:
                f.write(entry)

        except Exception as e:
            raise PipeError(f"Failed to write to context: {e}")

    def run_with_piping(
        self, command: str, show_output: bool = True, tags: Optional[list] = None
    ) -> int:
        """
        Run command, show output in real-time, and pipe to context.

        Args:
            command: Command to execute
            show_output: Whether to print output to console
            tags: Optional tags for the command

        Returns:
            Command return code

        Raises:
            PipeError: If execution fails
        """
        return_code, stdout, stderr = self.run_and_pipe(command)

        # Show output if requested
        if show_output:
            if stdout:
                print(stdout, end="")
            if stderr:
                print(stderr, end="", file=sys.stderr)

        # Pipe to context
        self.pipe_to_context(command, stdout, stderr, return_code, tags)

        return return_code

    def clear_context(self) -> None:
        """
        Clear the command outputs context file.

        Raises:
            PipeError: If clearing fails
        """
        try:
            if self.context_file.exists():
                self.context_file.unlink()
        except Exception as e:
            raise PipeError(f"Failed to clear context: {e}")

    def get_recent_outputs(self, count: int = 5) -> str:
        """
        Get recent command outputs from context file.

        Args:
            count: Number of recent outputs to retrieve

        Returns:
            String containing recent outputs

        Raises:
            PipeError: If reading fails
        """
        try:
            if not self.context_file.exists():
                return "No command outputs captured yet."

            with open(self.context_file, "r") as f:
                content = f.read()

            # Split by separator and get last N entries
            entries = content.split("---\n")
            recent = entries[-count:] if len(entries) >= count else entries

            return "\n---\n".join(recent)

        except Exception as e:
            raise PipeError(f"Failed to read context: {e}")

    def analyze_failures(self) -> dict:
        """
        Analyze failed commands in context.

        Returns:
            Dictionary with failure statistics and patterns

        Raises:
            PipeError: If analysis fails
        """
        if not self.context_file.exists():
            return {
                "total_commands": 0,
                "failed_commands": 0,
                "failure_rate": 0.0,
                "common_errors": [],
            }

        try:
            with open(self.context_file, "r") as f:
                content = f.read()

            # Count total and failed commands
            total = content.count("**Return Code:**")
            failed = content.count("❌ FAILED")

            failure_rate = (failed / total * 100) if total > 0 else 0.0

            # Extract common error patterns
            common_errors = []
            if "command not found" in content.lower():
                common_errors.append("Command not found errors")
            if "permission denied" in content.lower():
                common_errors.append("Permission errors")
            if "no such file" in content.lower():
                common_errors.append("File not found errors")
            if "connection refused" in content.lower():
                common_errors.append("Network connection errors")

            return {
                "total_commands": total,
                "failed_commands": failed,
                "failure_rate": round(failure_rate, 2),
                "common_errors": common_errors,
            }

        except Exception as e:
            raise PipeError(f"Failed to analyze failures: {e}")


def auto_pipe_command(
    command: str,
    project_root: Optional[Path] = None,
    show_output: bool = True,
    tags: Optional[list] = None,
) -> int:
    """
    Convenience function to pipe a command.

    Args:
        command: Command to execute
        project_root: Project root directory
        show_output: Whether to show output
        tags: Optional tags

    Returns:
        Command return code
    """
    piper = CommandPiper(project_root)
    return piper.run_with_piping(command, show_output, tags)
