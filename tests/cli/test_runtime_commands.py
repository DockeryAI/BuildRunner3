from __future__ import annotations

import subprocess

from typer.testing import CliRunner

from cli.main import app as cli_app

runner = CliRunner()


def test_runtime_get_invokes_helper_script(monkeypatch, tmp_path) -> None:
    script_path = tmp_path / "br-runtime.sh"
    script_path.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr("cli.runtime_commands._RUNTIME_SCRIPT", script_path)
    captured = {}

    def fake_run(command, capture_output, text, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="project default: codex\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = runner.invoke(cli_app, ["runtime", "get"])

    assert result.exit_code == 0
    assert captured["command"] == ["/bin/bash", str(script_path), "get"]
    assert "project default: codex" in result.stdout


def test_runtime_set_invokes_helper_script(monkeypatch, tmp_path) -> None:
    script_path = tmp_path / "br-runtime.sh"
    script_path.write_text("#!/bin/sh\n", encoding="utf-8")
    monkeypatch.setattr("cli.runtime_commands._RUNTIME_SCRIPT", script_path)
    captured = {}

    def fake_run(command, capture_output, text, check):
        captured["command"] = command
        return subprocess.CompletedProcess(command, 0, stdout="project default: claude -> codex\n", stderr="")

    monkeypatch.setattr(subprocess, "run", fake_run)

    result = runner.invoke(cli_app, ["runtime", "set", "codex"])

    assert result.exit_code == 0
    assert captured["command"] == ["/bin/bash", str(script_path), "set", "codex"]
    assert "claude -> codex" in result.stdout
