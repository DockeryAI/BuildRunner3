from __future__ import annotations

import json

from typer.testing import CliRunner

from cli.main import app as cli_app

runner = CliRunner()


class _FakeRegistry:
    def alias_exists(self, alias: str) -> bool:
        return False

    def register_project(self, alias: str, project_path, editor: str, spec_path: str):
        return {
            "alias": alias,
            "project_path": str(project_path),
            "editor": editor,
            "spec_path": spec_path,
        }


class _FakeShellIntegration:
    def add_alias(self, alias: str, project_path: str, editor: str) -> None:
        return None

    def get_primary_config(self) -> str:
        return "~/.zshrc"


def _fake_registry() -> _FakeRegistry:
    return _FakeRegistry()


def _fake_shell_integration() -> _FakeShellIntegration:
    return _FakeShellIntegration()


def test_project_init_skip_planning_writes_codex_runtime(monkeypatch, tmp_path) -> None:
    project_root = tmp_path / "sandbox-project"
    project_root.mkdir()

    monkeypatch.setattr("cli.project_commands.get_project_registry", _fake_registry)
    monkeypatch.setattr("cli.project_commands.get_shell_integration", _fake_shell_integration)

    class _CompletedProcess:
        returncode = 0
        stdout = ""
        stderr = ""

    monkeypatch.setattr("subprocess.run", lambda *args, **kwargs: _CompletedProcess())

    result = runner.invoke(
        cli_app,
        ["project", "init", "sandbox-project", "--dir", str(project_root), "--skip-planning"],
    )

    assert result.exit_code == 0
    runtime_data = json.loads(
        (project_root / ".buildrunner" / "runtime.json").read_text(encoding="utf-8")
    )
    assert runtime_data == {
        "schema_version": "br3.runtime.config.v1",
        "default_runtime": "codex",
    }
