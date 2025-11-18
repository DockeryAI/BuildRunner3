"""
Tests for cli.auto_pipe module
"""

import pytest
from pathlib import Path

from cli.auto_pipe import (
    CommandPiper,
    PipeError,
    auto_pipe_command
)


class TestCommandPiper:
    """Test suite for CommandPiper."""

    @pytest.fixture
    def temp_project(self, tmp_path):
        """Create temp project directory."""
        project_dir = tmp_path / "test_project"
        project_dir.mkdir()
        (project_dir / ".buildrunner" / "context").mkdir(parents=True)
        return project_dir

    @pytest.fixture
    def piper(self, temp_project):
        """Create CommandPiper instance."""
        return CommandPiper(temp_project)

    def test_init_default_path(self):
        """Test initialization with default path."""
        piper = CommandPiper()
        assert piper.project_root == Path.cwd()
        assert piper.max_output_size == 100000

    def test_init_custom_path(self, temp_project):
        """Test initialization with custom path."""
        piper = CommandPiper(temp_project)
        assert piper.project_root == temp_project

    def test_init_custom_context_file(self, temp_project):
        """Test initialization with custom context file."""
        custom_file = temp_project / "custom.md"
        piper = CommandPiper(temp_project, context_file=custom_file)
        assert piper.context_file == custom_file

    def test_run_and_pipe_success(self, piper):
        """Test running successful command."""
        return_code, stdout, stderr = piper.run_and_pipe("echo 'test'")

        assert return_code == 0
        assert 'test' in stdout
        assert stderr == ''

    def test_run_and_pipe_failure(self, piper):
        """Test running failed command."""
        return_code, stdout, stderr = piper.run_and_pipe("exit 1")

        assert return_code == 1

    def test_run_and_pipe_with_stderr(self, piper):
        """Test command with stderr output."""
        # Use a command that writes to stderr
        return_code, stdout, stderr = piper.run_and_pipe(
            "python3 -c \"import sys; sys.stderr.write('error')\"",
            shell=True
        )

        assert 'error' in stderr

    def test_run_and_pipe_max_output(self, temp_project):
        """Test output is truncated to max size."""
        piper = CommandPiper(temp_project, max_output_size=10)
        return_code, stdout, stderr = piper.run_and_pipe("echo '1234567890123456789'")

        assert len(stdout) <= 10

    def test_pipe_to_context(self, piper):
        """Test writing output to context file."""
        piper.pipe_to_context(
            command="echo test",
            stdout="test output",
            stderr="",
            return_code=0
        )

        assert piper.context_file.exists()

        with open(piper.context_file, 'r') as f:
            content = f.read()

        assert 'echo test' in content
        assert 'test output' in content
        assert '✅ SUCCESS' in content

    def test_pipe_to_context_failure(self, piper):
        """Test piping failed command."""
        piper.pipe_to_context(
            command="exit 1",
            stdout="",
            stderr="error",
            return_code=1
        )

        with open(piper.context_file, 'r') as f:
            content = f.read()

        assert '❌ FAILED' in content
        assert 'error' in content

    def test_pipe_to_context_with_tags(self, piper):
        """Test piping with tags."""
        piper.pipe_to_context(
            command="echo test",
            stdout="test",
            stderr="",
            return_code=0,
            tags=['test', 'debug']
        )

        with open(piper.context_file, 'r') as f:
            content = f.read()

        assert '[test, debug]' in content

    def test_run_with_piping(self, piper):
        """Test end-to-end run with piping."""
        return_code = piper.run_with_piping("echo test", show_output=False)

        assert return_code == 0
        assert piper.context_file.exists()

        with open(piper.context_file, 'r') as f:
            content = f.read()

        assert 'echo test' in content

    def test_clear_context(self, piper):
        """Test clearing context file."""
        # Create context file
        piper.context_file.parent.mkdir(parents=True, exist_ok=True)
        piper.context_file.write_text("test content")

        piper.clear_context()

        assert not piper.context_file.exists()

    def test_get_recent_outputs(self, piper):
        """Test getting recent outputs."""
        # Add some outputs
        for i in range(3):
            piper.pipe_to_context(
                command=f"echo test{i}",
                stdout=f"output{i}",
                stderr="",
                return_code=0
            )

        recent = piper.get_recent_outputs(count=2)

        assert 'output' in recent

    def test_get_recent_outputs_no_file(self, piper):
        """Test getting recent outputs when file doesn't exist."""
        recent = piper.get_recent_outputs()

        assert 'No command outputs' in recent

    def test_analyze_failures_no_file(self, piper):
        """Test analyzing failures when no file exists."""
        analysis = piper.analyze_failures()

        assert analysis['total_commands'] == 0
        assert analysis['failed_commands'] == 0
        assert analysis['failure_rate'] == 0.0

    def test_analyze_failures_with_failures(self, piper):
        """Test analyzing failures."""
        # Add successful and failed commands
        piper.pipe_to_context("echo success", "output", "", 0)
        piper.pipe_to_context("exit 1", "", "error", 1)
        piper.pipe_to_context("command not found", "", "bash: command not found", 127)

        analysis = piper.analyze_failures()

        assert analysis['total_commands'] == 3
        assert analysis['failed_commands'] == 2
        assert analysis['failure_rate'] > 0
        assert 'Command not found errors' in analysis['common_errors']


class TestConvenienceFunction:
    """Test convenience function."""

    def test_auto_pipe_command(self, tmp_path):
        """Test auto_pipe_command function."""
        project_dir = tmp_path / "project"
        project_dir.mkdir()
        (project_dir / ".buildrunner" / "context").mkdir(parents=True)

        return_code = auto_pipe_command(
            "echo test",
            project_root=project_dir,
            show_output=False
        )

        assert return_code == 0

        context_file = project_dir / ".buildrunner" / "context" / "command-outputs.md"
        assert context_file.exists()
